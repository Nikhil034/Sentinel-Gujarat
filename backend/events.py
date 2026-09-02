from __future__ import annotations

import json

from config import ROOT

EVENTS_PATH = ROOT / "data" / "events.json"


def _load() -> dict:
    if not EVENTS_PATH.is_file():
        return {"events": []}
    return json.loads(EVENTS_PATH.read_text())


def _save(data: dict) -> None:
    EVENTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    EVENTS_PATH.write_text(json.dumps(data, indent=2))


def list_events(camera_id: str | None = None) -> list[dict]:
    events = _load()["events"]
    if camera_id:
        events = [e for e in events if e["camera_id"] == camera_id]
    return events


def clear_events(camera_id: str) -> None:
    data = _load()
    data["events"] = [e for e in data["events"] if e["camera_id"] != camera_id]
    _save(data)


def append_events(items: list[dict]) -> list[dict]:
    data = _load()
    data["events"].extend(items)
    _save(data)
    return items


def prune_orphan_events(valid_camera_ids: set[str]) -> int:
    data = _load()
    before = len(data["events"])
    data["events"] = [
        e
        for e in data["events"]
        if e.get("camera_id") in valid_camera_ids and "grok-video" not in str(e.get("camera_id") or "")
    ]
    removed = before - len(data["events"])
    if removed:
        _save(data)
    return removed
