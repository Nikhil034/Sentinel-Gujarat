from __future__ import annotations

import http.cookiejar
import json
import re
import socket
import urllib.error
import urllib.parse
import urllib.request

from config import ROOT, settings
from store import upsert_camera

INGEST_CACHE = ROOT / "data" / "sentinel_ingest.json"
LEGACY_HTTP_HOSTS = ("live.corp8.cloud", "live.sentinelgujarat.in")

_cookie_jar = http.cookiejar.CookieJar()
_opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(_cookie_jar))
_logged_in = False
_session_password = ""

# Rough pins so Model 1 GIS is useful before official lat/lng exist.
_GEO = [
    ("paldi", (23.0116, 72.5632, "Ahmedabad")),
    ("janpath", (23.033, 72.585, "Ahmedabad")),
    ("visat", (23.07, 72.57, "Ahmedabad")),
    ("chiman", (23.022, 72.571, "Ahmedabad")),
    ("o.n.g.c", (23.02, 72.55, "Ahmedabad")),
    ("ongc", (23.02, 72.55, "Ahmedabad")),
    ("adalaj", (23.17, 72.58, "Gandhinagar")),
    ("delight", (23.03, 72.56, "Ahmedabad")),
    ("suvidha", (23.04, 72.56, "Ahmedabad")),
    ("vidhyalaya", (23.03, 72.57, "Ahmedabad")),
    ("junagadh", (21.5222, 70.4579, "Junagadh")),
    ("gir-somnath", (20.888, 70.401, "Gir Somnath")),
    ("rajkot", (22.3039, 70.8022, "Rajkot")),
    ("navsari", (20.95, 72.92, "Navsari")),
    ("gandhidham", (23.0753, 70.1337, "Gandhidham")),
    ("patan", (23.8493, 72.1266, "Patan")),
    ("dehgam", (23.17, 72.82, "Dehgam")),
    ("bilimora", (20.77, 72.96, "Bilimora")),
]


DEFAULT_GEO = (22.2587, 71.1924, "Gujarat")


def _geo(location: str) -> tuple[float, float, str]:
    loc = (location or "").lower()
    for key, triple in _GEO:
        if key in loc:
            return triple
    return DEFAULT_GEO


def _department(location: str) -> str:
    loc = (location or "").lower()
    if "toll" in loc:
        return "Transport / RTO"
    if "panchayat" in loc or "gram" in loc:
        return "Rural / local body"
    if "bus port" in loc:
        return "Transport"
    return "Home / Police (sandbox)"


def portal_origin() -> str:
    return settings.sentinel_portal.rstrip("/")


def normalize_cam_id(cid: str | None) -> str:
    """Official ids are cam01..cam30. Accept 4, cam04, sentinel-4."""
    raw = str(cid or "").strip()
    if raw.lower().startswith("cam") and re.search(r"\d", raw):
        return raw.lower()
    digits = re.sub(r"\D", "", raw)
    if digits:
        return f"cam{int(digits):02d}"
    return raw


def internal_camera_id(cid: str) -> str:
    digits = re.sub(r"\D", "", cid)
    if digits:
        return f"sentinel-{int(digits)}"
    return f"sentinel-{cid}"


def official_hls(remote_id: str | None) -> str:
    cid = normalize_cam_id(remote_id)
    if not cid:
        return ""
    return f"{settings.sentinel_hls_host.rstrip('/')}/{cid}/index.m3u8"


def official_rtsp(remote_id: str | None) -> str:
    cid = normalize_cam_id(remote_id)
    if not cid:
        return ""
    host = (settings.sentinel_rtsp_host or "103.250.160.189").strip()
    return f"rtsp://{host}:8554/stream/{cid}"


def official_webrtc(remote_id: str | None) -> str:
    cid = normalize_cam_id(remote_id)
    if not cid:
        return ""
    host = (settings.sentinel_rtsp_host or "103.250.160.189").strip()
    return f"http://{host}:8889/stream/{cid}/whep"


def cookie_header() -> str:
    return "; ".join(f"{c.name}={c.value}" for c in _cookie_jar)


def rewrite_url(url: str | None) -> str:
    """Map retired public hosts onto the current password-gated portal / RTSP IP."""
    if not url:
        return ""
    parsed = urllib.parse.urlparse(url)
    if url.startswith("rtsp://") or parsed.port in {8554, 8889}:
        cid = parsed.path.rstrip("/").rsplit("/", 1)[-1]
        if parsed.port == 8889:
            return official_webrtc(cid)
        return official_rtsp(cid)
    host = settings.sentinel_hls_host.rstrip("/")
    portal = settings.sentinel_portal.rstrip("/")
    out = url
    for old in LEGACY_HTTP_HOSTS:
        out = out.replace(f"https://{old}", host if "corp8" in old else portal)
        out = out.replace(f"http://{old}", host if "corp8" in old else portal)
    return out


def _is_login_page(body: bytes | str) -> bool:
    text = body.decode("utf-8", "replace") if isinstance(body, (bytes, bytearray)) else body
    low = text[:4000].lower()
    return "access password" in low or ("sign in" in low and "/auth/login" in low)


def _headers(accept: str = "application/json") -> dict:
    origin = portal_origin()
    return {
        "User-Agent": "SentinelCommand/0.8",
        "Accept": accept,
        "Accept-Encoding": "identity",
        "Referer": f"{origin}/",
        "Origin": origin,
    }


def get_opener():
    ensure_session()
    return _opener


def auth_status() -> dict:
    origin = portal_origin()
    password = (_session_password or settings.sentinel_password or "").strip()
    return {
        "required": True,
        "logged_in": _logged_in,
        "has_password": bool(password),
        "login_url": f"{origin}/auth/login",
        "register_url": f"{origin}/auth/register",
        "resource_url": f"{origin}/resource",
        "detail": (
            "Signed in to the Sentinel camera grid."
            if _logged_in
            else "Grid is on cctv.corp8.cloud and needs the access password from /auth/register."
        ),
    }


def login(password: str | None = None) -> dict:
    global _logged_in, _session_password
    secret = (password or _session_password or settings.sentinel_password or "").strip()
    if not secret:
        _logged_in = False
        return {
            "ok": False,
            "detail": "No grid password. Register at https://cctv.corp8.cloud/auth/register then set SENTINEL_PASSWORD.",
        }
    url = f"{portal_origin()}/auth/login"
    data = urllib.parse.urlencode({"password": secret}).encode()
    req = urllib.request.Request(url, data=data, method="POST", headers=_headers("text/html"))
    try:
        with _opener.open(req, timeout=20) as resp:
            body = resp.read()
            final = resp.geturl()
    except urllib.error.HTTPError as exc:
        _logged_in = False
        return {"ok": False, "detail": f"Login failed: HTTP {exc.code}"}
    except Exception as exc:
        _logged_in = False
        return {"ok": False, "detail": f"Login failed: {exc}"}
    if "/auth/login" in (final or "") or _is_login_page(body):
        _logged_in = False
        return {"ok": False, "detail": "Sentinel rejected the access password."}
    _logged_in = True
    _session_password = secret
    return {"ok": True, "logged_in": True, "detail": "Signed in to cctv.corp8.cloud"}


def ensure_session() -> None:
    if _logged_in:
        return
    password = (_session_password or settings.sentinel_password or "").strip()
    if password:
        login(password)


def _get_json(url: str) -> dict:
    ensure_session()
    req = urllib.request.Request(url, headers=_headers())
    with _opener.open(req, timeout=20) as resp:
        raw = resp.read()
        head = raw.lstrip()[:20].lower()
        if _is_login_page(raw) or head.startswith(b"<!doctype") or head.startswith(b"<html"):
            raise PermissionError(
                "Sentinel catalogue redirected to login. "
                "Set SENTINEL_PASSWORD or POST /sentinel/login."
            )
        try:
            return json.loads(raw.decode())
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Ingest did not return JSON from {url}") from exc


def fetch_ingest(cache: bool = True) -> dict:
    url = settings.sentinel_ingest_url.rstrip("/")
    try:
        data = _get_json(url)
        if isinstance(data, list):
            data = {"cameras": data}
        INGEST_CACHE.parent.mkdir(parents=True, exist_ok=True)
        INGEST_CACHE.write_text(json.dumps(data, indent=2))
        return data
    except PermissionError:
        if cache and INGEST_CACHE.is_file():
            return json.loads(INGEST_CACHE.read_text())
        raise
    except Exception:
        if cache and INGEST_CACHE.is_file():
            return json.loads(INGEST_CACHE.read_text())
        raise


def _hls_url(raw: str | None) -> str | None:
    if not raw:
        return None
    if raw.startswith("http"):
        return raw
    host = settings.sentinel_hls_host.rstrip("/")
    return f"{host}{raw if raw.startswith('/') else '/' + raw}"


def catalogue_cameras(data: dict | None = None) -> list[dict]:
    data = data or fetch_ingest()
    rows = data.get("cameras") or []
    out = []
    for row in rows:
        loc = row.get("location") or row.get("name") or ""
        lat, lng, city = _geo(loc)
        raw_id = str(row.get("id") or row.get("number") or "")
        remote = normalize_cam_id(raw_id)
        live = bool(row.get("live") if "live" in row else True)
        codec = (row.get("codec") or "").lower()
        out.append(
            {
                "id": internal_camera_id(remote or raw_id),
                "remote_id": remote or raw_id,
                "name": row.get("name") or f"Camera {remote or raw_id}",
                "location": loc,
                "city": city,
                "department": _department(loc),
                "camera_type": "IP CCTV",
                "lat": lat,
                "lng": lng,
                "source_type": "rtsp",
                "source_url": row.get("rtsp_url") or official_rtsp(remote),
                "hls_url": rewrite_url(_hls_url(row.get("hls_live_url"))) or official_hls(remote),
                "webrtc_url": row.get("webrtc_url") or official_webrtc(remote),
                "codec": codec,
                "live": live,
                "width": row.get("width") or 0,
                "height": row.get("height") or 0,
                "fps": row.get("fps") or 0,
                "bitrate_kbps": row.get("bitrate_kbps") or 0,
                "preview_url": f"{portal_origin()}/",
            }
        )
    return out


def import_ingest(*, limit: int | None = None) -> dict:
    data = fetch_ingest(cache=False)
    cams = catalogue_cameras(data)
    if limit:
        cams = cams[:limit]
    created, updated = 0, 0
    for cam in cams:
        existed = True
        from store import get_camera

        existed = get_camera(cam["id"]) is not None
        upsert_camera(
            name=cam["name"],
            source_url=cam["source_url"],
            location=cam["location"],
            city=cam["city"],
            lat=cam["lat"],
            lng=cam["lng"],
            camera_id=cam["id"],
            source_type="rtsp",
            extra={
                "hls_url": cam["hls_url"],
                "webrtc_url": cam["webrtc_url"],
                "codec": cam["codec"],
                "live": cam["live"],
                "preview_url": cam["preview_url"],
                "remote_id": cam["remote_id"],
                "department": cam["department"],
                "camera_type": cam["camera_type"],
                "width": cam["width"],
                "height": cam["height"],
                "fps": cam["fps"],
                "bitrate_kbps": cam["bitrate_kbps"],
            },
        )
        if existed:
            updated += 1
        else:
            created += 1
    from store import enrich, list_cameras

    return {
        "created": created,
        "updated": updated,
        "imported": len(cams),
        "cameras": [enrich(c) for c in list_cameras()],
    }


def _ingest_origin() -> str:
    parsed = urllib.parse.urlparse(settings.sentinel_ingest_url)
    return f"{parsed.scheme}://{parsed.netloc}"


def _tcp_probe(host: str, port: int, timeout: float = 3.0) -> dict:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        sock.connect((host, port))
        return {"ok": True, "detail": "connected"}
    except TimeoutError:
        return {"ok": False, "detail": "timeout — firewall / proxy dropping packets"}
    except ConnectionRefusedError:
        return {"ok": False, "detail": "connection refused — port reachable, nothing listening"}
    except OSError as exc:
        return {"ok": False, "detail": str(exc)}
    finally:
        sock.close()


def _http_probe(url: str, timeout: float = 8.0) -> dict:
    req = urllib.request.Request(url, headers=_headers("*/*"))
    try:
        with _opener.open(req, timeout=timeout) as resp:
            body = resp.read(240)
            if _is_login_page(body):
                return {"ok": False, "status": 401, "detail": "login wall"}
            return {
                "ok": 200 <= resp.status < 400,
                "status": resp.status,
                "detail": body[:80].decode("utf-8", "replace"),
            }
    except urllib.error.HTTPError as exc:
        return {"ok": False, "status": exc.code, "detail": str(exc.reason)}
    except Exception as exc:
        return {"ok": False, "status": None, "detail": str(exc)}


def hls_candidates(cam: dict) -> list[str]:
    urls: list[str] = []
    primary = cam.get("hls_url") or ""
    if primary:
        urls.append(primary)
    remote = cam.get("remote_id") or cam.get("id") or ""
    built = official_hls(remote)
    if built:
        urls.append(built)
    seen: set[str] = set()
    out: list[str] = []
    for url in urls:
        if url and url not in seen:
            seen.add(url)
            out.append(url)
    return out


def probe_path() -> dict:
    """Diagnose catalogue login, RTSP on the public ingest IP, and HLS on the CDN."""
    ingest_url = settings.sentinel_ingest_url.rstrip("/")
    rtsp_host = (settings.sentinel_rtsp_host or "103.250.160.189").strip()

    ingest: dict = {"ok": False, "url": ingest_url}
    try:
        data = fetch_ingest(cache=False)
        cams = data.get("cameras") or []
        live = sum(1 for c in cams if c.get("live", True))
        ingest = {
            "ok": True,
            "url": ingest_url,
            "cameras": len(cams),
            "live": live,
            "detail": f"{len(cams)} cameras from cameras.json",
        }
        sample = cams[0] if cams else None
    except PermissionError as exc:
        ingest = {"ok": False, "url": ingest_url, "detail": str(exc), "auth_required": True}
        sample = None
    except Exception as exc:
        ingest["detail"] = str(exc)
        sample = None

    rtsp = _tcp_probe(rtsp_host, 8554)
    webrtc = _tcp_probe(rtsp_host, 8889)
    hls = {"ok": False, "detail": "no camera id for HLS probe"}
    if sample:
        fake = {"remote_id": str(sample.get("id") or sample.get("number") or "")}
        for candidate in hls_candidates(fake):
            probed = _http_probe(candidate)
            probed["url"] = candidate
            hls = probed
            if probed.get("ok"):
                break

    auth = auth_status()
    if not ingest.get("ok") and not _logged_in:
        capture = "auth"
        summary = (
            "Official grid is at cctv.corp8.cloud and is password-gated. "
            "Sign in on this dashboard, then Fetch Sentinel grid."
        )
    elif rtsp["ok"]:
        capture = "rtsp"
        summary = f"RTSP {rtsp_host}:8554 is open. Capture uses TCP per the integrator guide."
    elif hls.get("ok"):
        capture = "hls"
        summary = "RTSP is blocked here. HLS on cctv.corp8.cloud is reachable with the session cookie."
    else:
        capture = "blocked"
        summary = "Catalogue may work, but RTSP and HLS are not usable from this network yet."

    return {
        "ingest": ingest,
        "gateway": {"ok": True, "detail": "not used — catalogue is cameras.json"},
        "auth": auth,
        "rtsp_8554": {"host": rtsp_host, "port": 8554, **rtsp},
        "webrtc_8889": {"host": rtsp_host, "port": 8889, **webrtc},
        "hls": hls,
        "capture_path": capture,
        "summary": summary,
    }
