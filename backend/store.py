from __future__ import annotations

import csv
import io
import json
import re
from pathlib import Path

from config import ROOT, settings

STORE_PATH = ROOT / "data" / "cameras.json"


def _slug(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "camera"


def _load() -> dict:
    if not STORE_PATH.is_file():
        return {"cameras": []}
    return json.loads(STORE_PATH.read_text())


def _save(data: dict) -> None:
    STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STORE_PATH.write_text(json.dumps(data, indent=2))


def list_cameras() -> list[dict]:
    return _load()["cameras"]


def get_camera(camera_id: str) -> dict | None:
    for cam in list_cameras():
        if cam["id"] == camera_id:
            return cam
    return None


def snapshot_dir(camera_id: str) -> Path:
    path = settings.snapshots_dir / camera_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def latest_snapshot(camera_id: str) -> str | None:
    files = sorted(snapshot_dir(camera_id).glob("frame_*.jpg"))
    if not files:
        return None
    return f"/media/snapshots/{camera_id}/{files[-1].name}"


def snapshot_count(camera_id: str) -> int:
    raw = list(snapshot_dir(camera_id).glob("frame_*.jpg"))
    annotated = list((snapshot_dir(camera_id) / "annotated").glob("frame_*.jpg"))
    return len(annotated) if annotated else len(raw)


def frame_times_path(camera_id: str) -> Path:
    return snapshot_dir(camera_id) / "times.json"


def save_frame_times(camera_id: str, items: list[dict]) -> None:
    frame_times_path(camera_id).write_text(json.dumps(items, indent=2))


def load_frame_times(camera_id: str) -> dict[str, dict]:
    path = frame_times_path(camera_id)
    if not path.is_file():
        return {}
    try:
        items = json.loads(path.read_text())
    except json.JSONDecodeError:
        return {}
    if isinstance(items, dict):
        items = items.get("frames") or []
    return {row["frame"]: row for row in items if isinstance(row, dict) and row.get("frame")}


def prune_camera_media(camera_id: str, *, after_analyze: bool = False) -> None:
    """Keep a short evidence window. This app is not a 24-hour video archive."""
    folder = snapshot_dir(camera_id)
    if after_analyze and settings.delete_raw_after_analyze:
        for raw in folder.glob("frame_*.jpg"):
            raw.unlink(missing_ok=True)
    else:
        keep_raw = max(1, settings.snapshot_keep_file_frames)
        raws = sorted(folder.glob("frame_*.jpg"))
        for old in raws[:-keep_raw]:
            old.unlink(missing_ok=True)
    keep = max(1, settings.snapshot_keep_annotated)
    annotated = sorted((folder / "annotated").glob("frame_*.jpg"))
    for old in annotated[:-keep]:
        old.unlink(missing_ok=True)


def latest_annotated(camera_id: str) -> str | None:
    files = sorted((snapshot_dir(camera_id) / "annotated").glob("frame_*.jpg"))
    if not files:
        return None
    return f"/media/snapshots/{camera_id}/annotated/{files[-1].name}"


def public_video_url(cam: dict) -> str | None:
    if cam.get("source_type") != "file":
        return cam.get("preview_url") or cam.get("hls_url")
    path = Path(cam["source_url"])
    if path.is_file() and path.parent.resolve() == settings.videos_dir.resolve():
        return f"/media/videos/{path.name}"
    return None


def migrate_legacy_hosts(cam: dict) -> dict:
    from sentinel import rewrite_url

    for key in ("hls_url", "preview_url", "webrtc_url", "source_url"):
        if cam.get(key):
            cam[key] = rewrite_url(cam[key])
    if cam.get("remote_id") or (cam.get("id") or "").startswith("sentinel-"):
        from sentinel import official_hls, official_rtsp, official_webrtc

        rid = cam.get("remote_id") or cam.get("id")
        cam["source_url"] = official_rtsp(rid) or cam.get("source_url")
        cam["hls_url"] = official_hls(rid) or cam.get("hls_url")
        cam["webrtc_url"] = official_webrtc(rid) or cam.get("webrtc_url")
        cam["preview_url"] = "https://cctv.corp8.cloud/"
    return cam


def enrich(cam: dict) -> dict:
    from events import list_events

    cam = migrate_legacy_hosts(dict(cam))
    source_type = cam.get("source_type", "file")
    path = Path(cam["source_url"])
    if source_type == "file":
        ready = path.is_file()
        status = "online" if ready else "offline"
        camera_type = cam.get("camera_type") or "recorded clip"
        department = cam.get("department") or "Own feed (demo)"
    else:
        from sentinel import _department

        ready = bool(cam.get("live", True) and cam.get("source_url"))
        status = "online" if ready else "offline"
        camera_type = cam.get("camera_type") or "IP CCTV"
        department = cam.get("department") or _department(cam.get("location") or "")
    return {
        **cam,
        "city": cam.get("city") or "",
        "department": department,
        "camera_type": camera_type,
        "ready": ready,
        "status": status,
        "video_url": public_video_url(cam),
        "snapshot_count": snapshot_count(cam["id"]),
        "latest_snapshot": latest_snapshot(cam["id"]),
        "latest_annotated": latest_annotated(cam["id"]),
        "event_count": len(list_events(cam["id"])),
    }


def upsert_camera(
    *,
    name: str,
    source_url: str,
    location: str = "Dev feed",
    city: str = "",
    lat: float = 23.0225,
    lng: float = 72.5714,
    camera_id: str | None = None,
    source_type: str = "file",
    overwrite_meta: bool = True,
    extra: dict | None = None,
) -> dict:
    source_type = source_type if source_type in {"file", "http", "rtsp"} else "file"
    path = Path(source_url)
    if source_type == "file":
        if not path.is_absolute():
            path = (ROOT / path).resolve()
        if not path.is_file():
            raise FileNotFoundError(f"Video not found: {path}")
        source_url = str(path)

    data = _load()
    cid = camera_id or _slug(name)
    existing = next((c for c in data["cameras"] if c["id"] == cid), None)
    cam = {
        "id": cid,
        "name": name,
        "location": location,
        "city": city,
        "lat": float(lat),
        "lng": float(lng),
        "source_type": source_type,
        "source_url": source_url,
    }
    if extra:
        cam.update({k: v for k, v in extra.items() if v is not None})
    if existing:
        if overwrite_meta:
            existing.update(cam)
        else:
            for key in ("source_url", "source_type"):
                existing[key] = cam[key]
    else:
        data["cameras"].append(cam)
    _save(data)
    return enrich(get_camera(cid))


def import_csv(text: str) -> dict:
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise ValueError("CSV has no header row")
    created, updated = 0, 0
    for row in reader:
        cid = (row.get("id") or "").strip() or None
        name = (row.get("name") or "").strip()
        if not name:
            continue
        existed = bool(cid and get_camera(cid))
        upsert_camera(
            name=name,
            source_url=(row.get("source_url") or "").strip(),
            location=(row.get("location") or "").strip() or name,
            city=(row.get("city") or "").strip(),
            lat=float(row.get("lat") or 23.0225),
            lng=float(row.get("lng") or 72.5714),
            camera_id=cid,
            source_type=(row.get("source_type") or "file").strip() or "file",
        )
        if existed:
            updated += 1
        else:
            created += 1
    return {
        "created": created,
        "updated": updated,
        "cameras": [enrich(c) for c in list_cameras()],
    }


def prune_synthetic_cameras() -> None:
    """Drop Grok/YouTube placeholders and duplicate ANPR rows."""
    data = _load()
    drop_ids = {"cam-jnd-01", "cam-sentinel-09", "anpr-gate", "anpr-paldi"}
    kept = []
    changed = False
    for cam in data["cameras"]:
        blob = f"{cam.get('id','')} {cam.get('source_url','')} {cam.get('name','')}".lower()
        if cam["id"] in drop_ids or "grok-video" in blob:
            changed = True
            continue
        before = json.dumps(cam, sort_keys=True)
        cam = migrate_legacy_hosts(cam)
        if json.dumps(cam, sort_keys=True) != before:
            changed = True
        kept.append(cam)
    if changed or len(kept) != len(data["cameras"]):
        data["cameras"] = kept
        _save(data)


def sync_videos_folder() -> list[dict]:
    """Register local ANPR MP4s only — skip generated Grok clips and duplicates."""
    existing_sources = {Path(c.get("source_url") or "").resolve() for c in list_cameras() if c.get("source_url")}
    for mp4 in sorted(settings.videos_dir.glob("*.mp4")):
        if "grok" in mp4.name.lower() or mp4.name == "sample.mp4":
            continue
        if mp4.resolve() in existing_sources:
            continue
        name = f"Cam-{mp4.stem[:24]}"
        cid = _slug(mp4.stem)[:40]
        if get_camera(cid) is None:
            upsert_camera(name=name, source_url=str(mp4), camera_id=cid, city="Ahmedabad")
            existing_sources.add(mp4.resolve())
    return [enrich(c) for c in list_cameras()]


def ensure_demo_registry() -> list[dict]:
    prune_synthetic_cameras()
    sync_videos_folder()
    from events import prune_orphan_events

    prune_orphan_events({c["id"] for c in list_cameras()})
    return [enrich(c) for c in list_cameras()]


def gap_report() -> dict:
    """Model 1 gap-analysis for Gujarat Police: coverage, silent cameras, missing plates."""
    from collections import defaultdict

    from events import list_events

    cams = [enrich(c) for c in list_cameras()]
    evs = list_events()
    by_cam: dict[str, list] = defaultdict(list)
    for e in evs:
        by_cam[e.get("camera_id") or ""].append(e)
    by_city: dict[str, int] = {}
    by_department: dict[str, int] = {}
    unlocated = []
    no_codec = []
    official = []
    recorded = []
    silent = []
    no_anpr = []
    for cam in cams:
        city = cam.get("city") or "Unknown"
        dept = cam.get("department") or "Unknown"
        by_city[city] = by_city.get(city, 0) + 1
        by_department[dept] = by_department.get(dept, 0) + 1
        if abs(float(cam.get("lat") or 0) - 22.2587) < 0.0001 and abs(float(cam.get("lng") or 0) - 71.1924) < 0.0001:
            unlocated.append({"id": cam["id"], "name": cam.get("name"), "location": cam.get("location")})
        if cam.get("source_type") != "file" and not cam.get("codec"):
            no_codec.append(cam["id"])
        if str(cam.get("id", "")).startswith("sentinel-"):
            official.append(cam["id"])
        if cam.get("source_type") == "file":
            recorded.append(cam["id"])
        cam_ev = by_cam.get(cam["id"]) or []
        if not cam_ev:
            silent.append({"id": cam["id"], "name": cam.get("name"), "city": cam.get("city")})
        elif not any(e.get("plate") for e in cam_ev):
            no_anpr.append({"id": cam["id"], "name": cam.get("name"), "events": len(cam_ev)})
    online = sum(1 for c in cams if c["status"] == "online")
    return {
        "total": len(cams),
        "online": online,
        "offline": len(cams) - online,
        "official_grid": len(official),
        "own_recorded": len(recorded),
        "by_city": dict(sorted(by_city.items(), key=lambda kv: (-kv[1], kv[0]))),
        "by_department": dict(sorted(by_department.items(), key=lambda kv: (-kv[1], kv[0]))),
        "unlocated": unlocated,
        "unlocated_ids": [u["id"] for u in unlocated],
        "silent": silent,
        "silent_ids": [s["id"] for s in silent],
        "no_anpr": no_anpr,
        "no_codec": no_codec,
        "note": (
            "Unlocated pins use a Gujarat centroid until official coordinates exist. "
            "Silent cameras have no Detect events yet. "
            "No-ANPR cameras have vehicles but no readable plate. "
            "Sandbox publishes ~30 official cameras; statewide target is ~80,000."
        ),
    }
