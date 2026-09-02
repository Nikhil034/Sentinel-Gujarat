from __future__ import annotations

from events import list_events
from plates import normalize_plate
from store import get_camera
from watchlist import list_watchlist


def build_alerts() -> list[dict]:
    wanted = {item["plate_norm"]: item for item in list_watchlist()}
    alerts = []
    for event in list_events():
        plate = normalize_plate(event.get("plate"))
        hit = wanted.get(plate)
        if not hit:
            continue
        alerts.append(
            {
                **event,
                "reason": hit["reason"],
                "alert": True,
            }
        )
    return alerts


def hunt_plate(plate: str) -> dict:
    needle = normalize_plate(plate)
    hits = []
    for event in list_events():
        if normalize_plate(event.get("plate")) != needle:
            continue
        cam = get_camera(event["camera_id"]) or {}
        hits.append(
            {
                **event,
                "lat": cam.get("lat"),
                "lng": cam.get("lng"),
            }
        )
    hits.sort(key=lambda e: (e.get("captured_at") or "", e.get("t_sec") or 0, e.get("created_at") or ""))
    cameras = []
    seen = set()
    for hit in hits:
        cid = hit["camera_id"]
        if cid in seen:
            continue
        seen.add(cid)
        cameras.append(
            {
                "id": cid,
                "name": hit.get("camera_name"),
                "location": hit.get("location"),
                "lat": hit.get("lat"),
                "lng": hit.get("lng"),
            }
        )
    return {
        "plate": needle,
        "hit_count": len(hits),
        "cameras": cameras,
        "hits": hits,
    }
