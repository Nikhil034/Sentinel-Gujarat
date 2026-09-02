from __future__ import annotations

import json
from datetime import datetime, timezone

from config import ROOT
from plates import normalize_plate

WATCHLIST_PATH = ROOT / "data" / "watchlist.json"


def _load() -> dict:
    if not WATCHLIST_PATH.is_file():
        return {"items": []}
    return json.loads(WATCHLIST_PATH.read_text())


def _save(data: dict) -> None:
    WATCHLIST_PATH.parent.mkdir(parents=True, exist_ok=True)
    WATCHLIST_PATH.write_text(json.dumps(data, indent=2))


def list_watchlist() -> list[dict]:
    return _load()["items"]


def add_watchlist(plate: str, reason: str = "stolen") -> dict:
    plate_n = normalize_plate(plate)
    if len(plate_n) < 4:
        raise ValueError("Plate is too short")
    data = _load()
    existing = next((i for i in data["items"] if i["plate_norm"] == plate_n), None)
    item = {
        "plate": plate_n,
        "plate_norm": plate_n,
        "reason": reason or "stolen",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    if existing:
        existing.update(item)
    else:
        data["items"].append(item)
    _save(data)
    return item


def remove_watchlist(plate: str) -> None:
    plate_n = normalize_plate(plate)
    data = _load()
    data["items"] = [i for i in data["items"] if i["plate_norm"] != plate_n]
    _save(data)


def ensure_demo_watchlist() -> list[dict]:
    if not list_watchlist():
        add_watchlist("GJ01AB1234", "stolen")
    return list_watchlist()
