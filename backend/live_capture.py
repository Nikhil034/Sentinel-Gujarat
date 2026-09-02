"""Live capture per Sentinel integrator guide: RTSP TCP, backoff, HLS fallback."""

from __future__ import annotations

import os
import re
import socket
import tempfile
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse

# Must be set before importing cv2 (Sentinel: force RTSP over TCP).
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"

import cv2  # noqa: E402

from sentinel import get_opener, hls_candidates, official_rtsp, rewrite_url
from store import save_frame_times, snapshot_dir

_IST = timezone(timedelta(hours=5, minutes=30))


def _parse_pdt(playlist: str) -> datetime | None:
    for line in playlist.splitlines():
        if not line.startswith("#EXT-X-PROGRAM-DATE-TIME:"):
            continue
        raw = line.split(":", 1)[1].strip()
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            continue
    return None


def _stamp_frame(frame, captured_at: datetime):
    label = captured_at.astimezone(_IST).strftime("%d %b %Y %H:%M:%S IST")
    cv2.putText(
        frame,
        label,
        (16, 36),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (0, 255, 180),
        2,
        cv2.LINE_AA,
    )
    return frame


def _rtsp_host_port(rtsp_url: str) -> tuple[str, int] | None:
    parsed = urlparse(rtsp_url)
    if not parsed.hostname:
        return None
    return parsed.hostname, parsed.port or 8554


def _port_open(host: str, port: int, timeout: float = 2.5) -> bool:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        sock.connect((host, port))
        return True
    except OSError:
        return False
    finally:
        sock.close()


def _clear_jpegs(out_dir: Path) -> None:
    for old in out_dir.glob("frame_*.jpg"):
        old.unlink()


def grab_rtsp_frames(
    rtsp_url: str,
    camera_id: str,
    *,
    duration_sec: float = 12.0,
    fps: float = 1.0,
) -> dict:
    """Sample ~fps JPEGs from live RTSP using PTS. TCP only. Backoff 2s..30s."""
    out_dir = snapshot_dir(camera_id)
    _clear_jpegs(out_dir)

    last_error = None
    delay = 2.0
    for _attempt in range(3):
        cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 2)
        if hasattr(cv2, "CAP_PROP_OPEN_TIMEOUT_MSEC"):
            cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 12000)
        if hasattr(cv2, "CAP_PROP_READ_TIMEOUT_MSEC"):
            cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 12000)
        if not cap.isOpened():
            last_error = (
                "RTSP :8554 did not open from this network. "
                "Will try HLS on 80/443 if a playlist URL exists."
            )
            cap.release()
            time.sleep(delay)
            delay = min(delay * 2, 30)
            continue

        saved = 0
        times: list[dict] = []
        last_keep_ms = -1e9
        interval_ms = 1000.0 / max(fps, 0.2)
        t_end = time.time() + duration_sec
        gaps = 0
        first_pts: float | None = None
        origin_wall = datetime.now(timezone.utc)
        while time.time() < t_end:
            ok, frame = cap.read()
            if not ok or frame is None:
                # Decoder RPS / missing POC at join is normal until first keyframe.
                gaps += 1
                if gaps > 80:
                    break
                time.sleep(0.05)
                continue
            gaps = 0
            pts_ms = float(cap.get(cv2.CAP_PROP_POS_MSEC) or 0)
            if first_pts is None:
                first_pts = pts_ms
                origin_wall = datetime.now(timezone.utc)
            if pts_ms - last_keep_ms < interval_ms * 0.7:
                continue
            last_keep_ms = pts_ms
            saved += 1
            offset = max(0.0, (pts_ms - first_pts) / 1000.0)
            captured_at = origin_wall + timedelta(seconds=offset)
            dest = out_dir / f"frame_{saved:04d}.jpg"
            cv2.imwrite(str(dest), _stamp_frame(frame, captured_at))
            times.append(
                {
                    "frame": dest.name,
                    "captured_at": captured_at.isoformat(),
                    "t_sec": round(offset, 3),
                    "clock": "pts",
                }
            )
        cap.release()
        if saved:
            save_frame_times(camera_id, times)
            return {
                "extracted": saved,
                "method": "rtsp-tcp",
                "url": rtsp_url,
                "pts": True,
                "clock": "pts",
            }
        last_error = "Opened RTSP but received no frames (waiting for keyframe)."
        time.sleep(delay)
        delay = min(delay * 2, 30)

    raise RuntimeError(last_error or "Live RTSP capture failed.")


def _hls_opener(referer: str):
    opener = get_opener()

    def fetch(url: str) -> bytes:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "SentinelCommand/0.8",
                "Referer": referer,
                "Accept": "*/*",
            },
        )
        with opener.open(req, timeout=20) as resp:
            body = resp.read()
            if body.lstrip()[:15].lower().startswith(b"<!doctype html") or b"Access Password" in body[:800]:
                raise RuntimeError(
                    "HLS hit the Sentinel login wall. Sign in with SENTINEL_PASSWORD first."
                )
            return body

    return fetch


def _playlist_urls(text: str, base: str) -> list[str]:
    urls = []
    for line in text.splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            urls.append(urljoin(base, line))
    return urls


def _hls_init_and_parts(text: str, base: str) -> tuple[str | None, list[str]]:
    init = None
    mapped = re.search(r'URI="([^"]+)"', text)
    if mapped and "init" in mapped.group(1):
        init = urljoin(base, mapped.group(1))
    parts = [urljoin(base, uri) for uri in re.findall(r"#EXT-X-PART:[^\n]*URI=\"([^\"]+)\"", text)]
    segs: list[str] = []
    pending = False
    for line in text.splitlines():
        if line.startswith("#EXTINF"):
            pending = True
            continue
        if pending and line.strip() and not line.startswith("#"):
            segs.append(urljoin(base, line.strip()))
            pending = False
    return init, parts or segs


def grab_hls_frames(
    hls_url: str,
    camera_id: str,
    *,
    duration_sec: float = 12.0,
    fps: float = 1.0,
) -> dict:
    """Same live bitstream as RTSP, on HTTP 80/443. Uses cookieCheck + LL-HLS parts."""
    out_dir = snapshot_dir(camera_id)
    _clear_jpegs(out_dir)

    hls_url = rewrite_url(hls_url)
    parsed = urlparse(hls_url)
    referer = f"{parsed.scheme}://{parsed.netloc}/"
    fetch = _hls_opener(referer)

    master = fetch(hls_url).decode("utf-8", "replace")
    if "#EXTM3U" not in master:
        raise RuntimeError(f"HLS playlist is not M3U8: {hls_url}")
    media_url = hls_url
    variants = _playlist_urls(master, hls_url)
    if variants and "EXT-X-STREAM-INF" in master:
        media_url = variants[0]

    init_url = None
    blob = b""
    seen: set[str] = set()
    origin_pdt: datetime | None = None
    deadline = time.time() + max(duration_sec, 4.0)
    while time.time() < deadline:
        playlist = fetch(media_url).decode("utf-8", "replace")
        pdt = _parse_pdt(playlist)
        init, chunks = _hls_init_and_parts(playlist, media_url)
        if init and init_url is None:
            init_url = init
            blob = fetch(init)
        for url in chunks:
            if url in seen:
                continue
            seen.add(url)
            try:
                blob += fetch(url)
                if origin_pdt is None and pdt is not None:
                    origin_pdt = pdt
            except Exception:
                continue
        time.sleep(0.4)

    if len(blob) < 2000:
        raise RuntimeError(f"HLS capture failed (got {len(blob)} bytes). Playlist: {hls_url}")

    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        tmp.write(blob)
        clip = tmp.name
    saved = 0
    times: list[dict] = []
    try:
        cap = cv2.VideoCapture(clip, cv2.CAP_FFMPEG)
        if not cap.isOpened():
            raise RuntimeError("HLS fragments downloaded but decoder could not open them.")
        last_keep_ms = -1e9
        interval_ms = 1000.0 / max(fps, 0.2)
        gaps = 0
        first_pts: float | None = None
        while True:
            ok, frame = cap.read()
            if not ok or frame is None:
                gaps += 1
                if gaps > 30:
                    break
                continue
            gaps = 0
            pts_ms = float(cap.get(cv2.CAP_PROP_POS_MSEC) or 0)
            if first_pts is None:
                first_pts = pts_ms
            if saved and pts_ms - last_keep_ms < interval_ms * 0.7:
                continue
            last_keep_ms = pts_ms
            offset = max(0.0, (pts_ms - (first_pts or 0)) / 1000.0)
            if origin_pdt is not None:
                captured_at = origin_pdt + timedelta(seconds=offset)
                clock = "stream"
            else:
                captured_at = datetime.now(timezone.utc)
                clock = "wall"
            saved += 1
            dest = out_dir / f"frame_{saved:04d}.jpg"
            cv2.imwrite(str(dest), _stamp_frame(frame, captured_at))
            times.append(
                {
                    "frame": dest.name,
                    "captured_at": captured_at.isoformat(),
                    "t_sec": round(offset, 3),
                    "clock": clock,
                }
            )
        cap.release()
    finally:
        Path(clip).unlink(missing_ok=True)

    if not saved:
        raise RuntimeError(f"HLS downloaded but no frames decoded. Playlist: {hls_url}")
    save_frame_times(camera_id, times)
    return {
        "extracted": saved,
        "method": "hls",
        "url": hls_url,
        "pts": True,
        "chunks": len(seen),
        "clock": times[0]["clock"] if times else "wall",
    }


def extract_camera(cam: dict, fps: float = 1.0, duration_sec: float = 12.0) -> dict:
    source_type = cam.get("source_type") or "file"
    if source_type == "file":
        from ingest import extract_frames

        count = extract_frames(cam["source_url"], cam["id"], fps=fps)
        return {"extracted": count, "method": "file"}

    rtsp = cam.get("source_url") or ""
    errors: list[str] = []
    rtsp_urls = []
    built = official_rtsp(cam.get("remote_id") or cam.get("id"))
    if built:
        rtsp_urls.append(built)
    if rtsp.startswith("rtsp://"):
        rewritten = rewrite_url(rtsp)
        if rewritten and rewritten not in rtsp_urls:
            rtsp_urls.append(rewritten)
        if rtsp not in rtsp_urls:
            rtsp_urls.append(rtsp)

    for rtsp_url in rtsp_urls:
        hop = _rtsp_host_port(rtsp_url)
        rtsp_reachable = hop is not None and _port_open(*hop)
        if not rtsp_reachable:
            errors.append(f"RTSP: {hop[0] if hop else rtsp_url} port not reachable")
            continue
        try:
            return grab_rtsp_frames(rtsp_url, cam["id"], duration_sec=duration_sec, fps=fps)
        except Exception as exc:
            errors.append(f"RTSP: {exc}")

    for hls in hls_candidates(cam):
        try:
            result = grab_hls_frames(hls, cam["id"], duration_sec=duration_sec, fps=fps)
            result["rtsp_error"] = errors[0] if errors else None
            return result
        except Exception as exc:
            errors.append(f"HLS: {exc}")

    if not rtsp.startswith("rtsp://") and not hls_candidates(cam):
        raise RuntimeError("Camera has no RTSP or HLS URL from /api/ingest.")

    raise RuntimeError(
        "Live capture failed. "
        + " | ".join(errors)
        + " Catalogue and dashboard can still work on 443 while RTSP :8554 is blocked."
    )
