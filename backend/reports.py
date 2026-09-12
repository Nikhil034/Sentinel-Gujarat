"""Daily activity CSVs, ANPR metadata index, camera-wise event index."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from alerts import build_alerts
from config import settings
from events import list_events
from plates import normalize_plate
from store import enrich, list_cameras, load_frame_times, snapshot_count
from watchlist import list_watchlist

_IST = timezone(timedelta(hours=5, minutes=30))


def today_ist() -> str:
    return datetime.now(_IST).strftime("%Y-%m-%d")


def event_day(event: dict) -> str:
    raw = event.get("captured_at") or event.get("created_at") or ""
    if not raw:
        return ""
    try:
        dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        return dt.astimezone(_IST).strftime("%Y-%m-%d")
    except ValueError:
        return str(raw)[:10]


def derive_tags(event: dict, wanted: set[str] | None = None) -> list[str]:
    tags = [str(t) for t in (event.get("tags") or []) if t]
    if event.get("label"):
        tags.append("vehicle")
    if event.get("plate"):
        tags.append("anpr")
    else:
        tags.append("unread")
    plate_n = normalize_plate(event.get("plate"))
    if wanted is None:
        wanted = {item["plate_norm"] for item in list_watchlist()}
    if plate_n and plate_n in wanted:
        tags.append("watchlist")
    return sorted(set(tags))


def tagged_events(camera_id: str | None = None, tag: str | None = None, day: str | None = None) -> list[dict]:
    wanted = {item["plate_norm"] for item in list_watchlist()}
    out = []
    for event in list_events(camera_id):
        if day and day != "all":
            d = event_day(event)
            if d and d != day:
                continue
        tags = derive_tags(event, wanted)
        row = {**event, "tags": tags}
        if tag and tag not in tags:
            continue
        out.append(row)
    return out


def csv_cell(value) -> str:
    text = str(value if value is not None else "").replace('"', '""')
    return f'"{text}"'


def daily_activity(day: str | None = None) -> dict:
    day = day or today_ist()
    filter_day = None if day == "all" else day
    wanted = {item["plate_norm"] for item in list_watchlist()}
    alerts = build_alerts()
    if day == "all":
        alert_ids = {a.get("id") for a in alerts}
    else:
        alert_ids = {a.get("id") for a in alerts if event_day(a) in {day, ""}}
    rows = []
    totals = {
        "cameras": 0,
        "events": 0,
        "vehicles": 0,
        "plates": 0,
        "watchlist_hits": 0,
        "silent": 0,
    }
    for cam in [enrich(c) for c in list_cameras()]:
        evs = [e for e in tagged_events(cam["id"], day=filter_day)]
        plates = [normalize_plate(e.get("plate")) for e in evs if e.get("plate")]
        unique = sorted({p for p in plates if p})
        hits = sum(1 for e in evs if e.get("id") in alert_ids or "watchlist" in (e.get("tags") or []))
        times = [event_day(e) and (e.get("captured_at") or e.get("created_at")) for e in evs]
        times = [t for t in times if t]
        notes = []
        if not evs:
            notes.append("no detections this day")
            totals["silent"] += 1
        if evs and not unique:
            notes.append("vehicles seen, no plate read")
        lat, lng = float(cam.get("lat") or 0), float(cam.get("lng") or 0)
        if abs(lat - 22.2587) < 0.0001 and abs(lng - 71.1924) < 0.0001:
            notes.append("unlocated pin")
        row = {
            "date": day,
            "camera_id": cam["id"],
            "name": cam.get("name"),
            "location": cam.get("location"),
            "city": cam.get("city"),
            "department": cam.get("department"),
            "source_type": cam.get("source_type"),
            "status": cam.get("status"),
            "frames_on_disk": snapshot_count(cam["id"]),
            "events": len(evs),
            "vehicles": sum(1 for e in evs if e.get("label")),
            "plates_read": len(plates),
            "unique_plates": "|".join(unique),
            "unique_plate_count": len(unique),
            "watchlist_hits": hits,
            "first_event": min(times) if times else "",
            "last_event": max(times) if times else "",
            "notes": "; ".join(notes),
        }
        rows.append(row)
        totals["cameras"] += 1
        totals["events"] += row["events"]
        totals["vehicles"] += row["vehicles"]
        totals["plates"] += row["plates_read"]
        totals["watchlist_hits"] += hits
    return {"date": day, "totals": totals, "rows": rows}


def frame_log(day: str | None = None) -> list[dict]:
    """One row per captured/analyzed frame — not a video archive."""
    day = day or today_ist()
    filter_day = None if day == "all" else day
    rows = []
    for cam in list_cameras():
        cid = cam["id"]
        times = load_frame_times(cid)
        evs = tagged_events(cid, day=filter_day)
        by_frame: dict[str, list[dict]] = defaultdict(list)
        for e in evs:
            by_frame[e.get("frame") or ""].append(e)
        frames = set(by_frame) | set(times)
        for frame in sorted(f for f in frames if f):
            bunch = by_frame.get(frame) or []
            meta = times.get(frame) or {}
            stamp_src = ""
            if bunch:
                stamp_src = bunch[0].get("captured_at") or bunch[0].get("created_at") or ""
            if not stamp_src:
                stamp_src = meta.get("captured_at") or ""
            stamp = event_day({"captured_at": stamp_src}) if stamp_src else ""
            if filter_day and stamp != filter_day:
                continue
            plates = [normalize_plate(e.get("plate")) for e in bunch if e.get("plate")]
            rows.append(
                {
                    "date": stamp or (filter_day or day),
                    "camera_id": cid,
                    "camera_name": cam.get("name"),
                    "frame": frame,
                    "captured_at": meta.get("captured_at") or (bunch[0].get("captured_at") if bunch else ""),
                    "t_sec": meta.get("t_sec") if meta.get("t_sec") is not None else (bunch[0].get("t_sec") if bunch else ""),
                    "clock": meta.get("clock") or (bunch[0].get("clock") if bunch else ""),
                    "vehicles": len(bunch),
                    "plates_read": len(plates),
                    "plate_texts": "|".join(p for p in plates if p),
                    "tags": "|".join(sorted({t for e in bunch for t in (e.get("tags") or [])})),
                    "snapshot_url": (bunch[0].get("snapshot_url") if bunch else f"/media/snapshots/{cid}/{frame}"),
                }
            )
    return rows


def anpr_index() -> dict:
    """Searchable plate metadata: first/last seen, cameras, counts."""
    wanted = {item["plate_norm"]: item for item in list_watchlist()}
    plates: dict[str, dict] = {}
    for event in tagged_events():
        plate = normalize_plate(event.get("plate"))
        if not plate:
            continue
        row = plates.setdefault(
            plate,
            {
                "plate": plate,
                "watchlist": plate in wanted,
                "reason": (wanted.get(plate) or {}).get("reason") or "",
                "hit_count": 0,
                "cameras": [],
                "first_seen": "",
                "last_seen": "",
                "latest_snapshot": "",
            },
        )
        row["hit_count"] += 1
        cam = event.get("camera_id")
        if cam and cam not in row["cameras"]:
            row["cameras"].append(cam)
        when = event.get("captured_at") or event.get("created_at") or ""
        if when and (not row["first_seen"] or when < row["first_seen"]):
            row["first_seen"] = when
        if when and when >= row["last_seen"]:
            row["last_seen"] = when
            row["latest_snapshot"] = event.get("snapshot_url") or ""
    items = sorted(plates.values(), key=lambda r: (-r["hit_count"], r["plate"]))
    return {"plates": items, "count": len(items)}


def camera_index() -> dict:
    """Camera-wise event index for Model 2 tagging/indexing."""
    cameras = []
    for cam in [enrich(c) for c in list_cameras()]:
        evs = tagged_events(cam["id"])
        tag_counts: dict[str, int] = defaultdict(int)
        for e in evs:
            for t in e.get("tags") or []:
                tag_counts[t] += 1
        cameras.append(
            {
                "id": cam["id"],
                "name": cam.get("name"),
                "city": cam.get("city"),
                "department": cam.get("department"),
                "status": cam.get("status"),
                "event_count": len(evs),
                "anpr": tag_counts.get("anpr", 0),
                "unread": tag_counts.get("unread", 0),
                "watchlist": tag_counts.get("watchlist", 0),
                "vehicle": tag_counts.get("vehicle", 0),
                "tags": dict(tag_counts),
            }
        )
    return {"cameras": cameras}


def activity_csv(payload: dict) -> str:
    header = (
        "date,camera_id,name,location,city,department,source_type,status,"
        "frames_on_disk,events,vehicles,plates_read,unique_plate_count,unique_plates,"
        "watchlist_hits,first_event,last_event,notes"
    )
    lines = [header]
    for row in payload["rows"]:
        lines.append(
            ",".join(
                [
                    csv_cell(row.get("date")),
                    csv_cell(row.get("camera_id")),
                    csv_cell(row.get("name")),
                    csv_cell(row.get("location")),
                    csv_cell(row.get("city")),
                    csv_cell(row.get("department")),
                    csv_cell(row.get("source_type")),
                    csv_cell(row.get("status")),
                    str(row.get("frames_on_disk") or 0),
                    str(row.get("events") or 0),
                    str(row.get("vehicles") or 0),
                    str(row.get("plates_read") or 0),
                    str(row.get("unique_plate_count") or 0),
                    csv_cell(row.get("unique_plates")),
                    str(row.get("watchlist_hits") or 0),
                    csv_cell(row.get("first_event")),
                    csv_cell(row.get("last_event")),
                    csv_cell(row.get("notes")),
                ]
            )
        )
    return "\n".join(lines) + "\n"


def frames_csv(rows: list[dict]) -> str:
    header = (
        "date,camera_id,camera_name,frame,captured_at,t_sec,clock,"
        "vehicles,plates_read,plate_texts,tags,snapshot_url"
    )
    lines = [header]
    for row in rows:
        lines.append(
            ",".join(
                [
                    csv_cell(row.get("date")),
                    csv_cell(row.get("camera_id")),
                    csv_cell(row.get("camera_name")),
                    csv_cell(row.get("frame")),
                    csv_cell(row.get("captured_at")),
                    str(row.get("t_sec") if row.get("t_sec") is not None else ""),
                    csv_cell(row.get("clock")),
                    str(row.get("vehicles") or 0),
                    str(row.get("plates_read") or 0),
                    csv_cell(row.get("plate_texts")),
                    csv_cell(row.get("tags")),
                    csv_cell(row.get("snapshot_url")),
                ]
            )
        )
    return "\n".join(lines) + "\n"


def plates_csv(payload: dict) -> str:
    header = "plate,watchlist,reason,hit_count,cameras,first_seen,last_seen,latest_snapshot"
    lines = [header]
    for row in payload["plates"]:
        lines.append(
            ",".join(
                [
                    csv_cell(row.get("plate")),
                    str(bool(row.get("watchlist"))),
                    csv_cell(row.get("reason")),
                    str(row.get("hit_count") or 0),
                    csv_cell("|".join(row.get("cameras") or [])),
                    csv_cell(row.get("first_seen")),
                    csv_cell(row.get("last_seen")),
                    csv_cell(row.get("latest_snapshot")),
                ]
            )
        )
    return "\n".join(lines) + "\n"


def camera_index_csv(payload: dict) -> str:
    header = "id,name,city,department,status,event_count,vehicle,anpr,unread,watchlist"
    lines = [header]
    for row in payload.get("cameras") or []:
        tags = row.get("tags") or {}
        lines.append(
            ",".join(
                [
                    csv_cell(row.get("id")),
                    csv_cell(row.get("name")),
                    csv_cell(row.get("city")),
                    csv_cell(row.get("department")),
                    csv_cell(row.get("status")),
                    str(row.get("event_count") or 0),
                    str(row.get("vehicle") or tags.get("vehicle") or 0),
                    str(row.get("anpr") or 0),
                    str(row.get("unread") or 0),
                    str(row.get("watchlist") or 0),
                ]
            )
        )
    return "\n".join(lines) + "\n"


def gap_analysis_csv(gap: dict) -> str:
    lines = ["kind,id,name,city,detail"]
    for city, n in (gap.get("by_city") or {}).items():
        lines.append(",".join(["city", "", csv_cell(city), csv_cell(city), csv_cell(f"{n} cameras")]))
    for dept, n in (gap.get("by_department") or {}).items():
        lines.append(",".join(["department", "", csv_cell(dept), "", csv_cell(f"{n} cameras")]))
    for row in gap.get("unlocated") or []:
        lines.append(
            ",".join(
                ["unlocated", csv_cell(row.get("id")), csv_cell(row.get("name")), "", csv_cell(row.get("location"))]
            )
        )
    for row in gap.get("silent") or []:
        lines.append(
            ",".join(
                [
                    "silent",
                    csv_cell(row.get("id")),
                    csv_cell(row.get("name")),
                    csv_cell(row.get("city")),
                    csv_cell("no detections"),
                ]
            )
        )
    for row in gap.get("no_anpr") or []:
        lines.append(
            ",".join(
                [
                    "no_anpr",
                    csv_cell(row.get("id")),
                    csv_cell(row.get("name")),
                    "",
                    csv_cell(f"{row.get('events')} vehicles, no plate"),
                ]
            )
        )
    return "\n".join(lines) + "\n"


def event_days() -> list[str]:
    return sorted({d for e in list_events() if (d := event_day(e))})


def storage_policy() -> dict:
    return {
        "summary": (
            "Keep daily CSV logs (activity + one row per sampled frame). "
            "Keep a short window of annotated JPEGs. "
            "Do not store 24-hour video in this app — departmental NVRs remain the archive."
        ),
        "keep": [
            "daily-YYYY-MM-DD.csv — one row per camera with events, plates, watchlist hits, notes",
            "daily-all.csv — rollup across every recorded IST day",
            "frames-YYYY-MM-DD.csv — one row per sampled/analyzed frame (metadata, not pixels)",
            "anpr-metadata.csv — unique plates, first/last seen, cameras",
            "camera-index.csv — event tags rolled up per camera",
            f"last {settings.snapshot_keep_annotated} annotated JPEGs per camera (evidence window)",
        ],
        "do_not_keep": [
            "24-hour video inside Sentinel Command",
            "raw extract frames after Detect (deleted automatically)",
            "unbounded snapshot folders",
        ],
        "video_archive": "Departmental NVRs / existing VMS remain the video archive.",
        "snapshot_keep_annotated": settings.snapshot_keep_annotated,
        "snapshot_keep_file_frames": settings.snapshot_keep_file_frames,
        "delete_raw_after_analyze": settings.delete_raw_after_analyze,
        "reports_dir": str(settings.reports_dir),
    }


def close_day(day: str | None = None) -> dict:
    """Write end-of-day CSVs + gap PDF under data/reports/. JPEGs stay pruned; CSVs are the durable log."""
    from gap_pdf import build_gap_pdf
    from store import gap_report, prune_camera_media

    requested = day or today_ist()
    settings.reports_dir.mkdir(parents=True, exist_ok=True)
    for cam in list_cameras():
        prune_camera_media(cam["id"], after_analyze=False)

    files: list[str] = []
    days = {requested, "all", *event_days()}
    frame_rows = 0
    for d in sorted(days, key=lambda x: (x != "all", x)):
        activity = daily_activity(d)
        frames = frame_log(d)
        daily_path = settings.reports_dir / f"daily-{d}.csv"
        frames_path = settings.reports_dir / f"frames-{d}.csv"
        daily_path.write_text(activity_csv(activity))
        frames_path.write_text(frames_csv(frames))
        files += [daily_path.name, frames_path.name]
        if d == requested:
            frame_rows = len(frames)

    plates_path = settings.reports_dir / "anpr-metadata.csv"
    plates_path.write_text(plates_csv(anpr_index()))
    index_path = settings.reports_dir / "camera-index.csv"
    index_path.write_text(camera_index_csv(camera_index()))
    gap = gap_report()
    gap_csv_path = settings.reports_dir / "gap-analysis.csv"
    gap_csv_path.write_text(gap_analysis_csv(gap))
    pdf_path = settings.reports_dir / "gap-analysis.pdf"
    build_gap_pdf(pdf_path)
    files += [plates_path.name, index_path.name, gap_csv_path.name, pdf_path.name]
    all_totals = daily_activity("all")["totals"]
    return {
        "date": requested,
        "daily_csv": f"/reports/daily.csv?date={requested}",
        "frames_csv": f"/reports/frames.csv?date={requested}",
        "gap_pdf": "/cameras/gap.pdf",
        "files": files,
        "totals": all_totals,
        "day_totals": daily_activity(requested)["totals"],
        "frame_rows": frame_rows,
        "event_days": event_days(),
        "policy": storage_policy()["summary"],
    }
