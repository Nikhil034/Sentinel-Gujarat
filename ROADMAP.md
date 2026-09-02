# Sentinel Command — solo build roadmap

**Locked scope:** Hybrid Model 1 (GIS registry) + Model 2 (unified viewing + ANPR + alerts).  
**Dev feeds:** YouTube / local MP4 with visible vehicles (fast).  
**Jury feeds:** swap URL to `https://live.sentinelgujarat.in/stream/{id}` without rewriting the app.

Official portal streams are slow and 12-hour looping MP4s. Do **not** wait on them to start. Plug them in at Milestone 6.

---

## Tech stack (do not expand)

| Layer | Choice | Why |
|---|---|---|
| UI | React + Vite + Leaflet | Map + live wall + hunt screen |
| API | Python FastAPI | Fast to write, matches their suggested stack |
| DB | SQLite first → PostgreSQL+PostGIS if time | Solo speed; PostGIS only if map queries need it |
| Video ingest | FFmpeg (local file or HTTP MP4) | Same pipeline for YouTube file and Sentinel `/stream/{id}` |
| YouTube → file | `yt-dlp` once, then treat as camera | No live YouTube in the AI loop |
| Detect | YOLOv8n (vehicles) | Light enough for CPU |
| Plates | Plate crop + EasyOCR / PaddleOCR | Good enough for demo plates |
| Auth | Single admin login | Skip SSO |

**Out of scope:** Kafka, Kubernetes, face ID, live VAHAN, Model 3/4 as running code.

---

## How a “camera” works in our app

Every camera is one row:

- `id`, `name`, `location`, `lat`, `lng`
- `source_type`: `file` | `http`
- `source_url`: path to MP4 **or** `https://live.sentinelgujarat.in/stream/9`

Ingest worker: FFmpeg → 1 frame/sec → YOLO → OCR → `events` table.

YouTube is only a **download step**. The product never depends on YouTube staying up.

Use traffic/junction clips you are allowed to use (your own recording is safest).

---

## Milestones

### M0 — Repo skeleton (half day)

- Folders: `backend/`, `frontend/`, `data/videos/`, `data/snapshots/`
- FastAPI hello + React hello
- `.env` for paths
- README: how to run

**Done when:** `localhost:8000/health` and `localhost:5173` both load.

### M1 — Treat a video as a camera (1 day) — START HERE

- Download 1–2 vehicle videos into `data/videos/`
- API: `POST /cameras` with file path
- FFmpeg extracts JPEG frames to `data/snapshots/{camera_id}/`
- UI: play the video (HTML5 `<video>`) + show latest snapshot

**Done when:** you add “Cam-YT-01” and see video + frames without touching Sentinel.

### M2 — Registry + GIS (Model 1) (1 day)

- Camera table: name, city, lat/lng (hardcode Ahmedabad / Junagadh pins for demo)
- Leaflet map with green pins
- List + filter
- CSV import (so later we import 30 Sentinel cameras in one shot)

**Done when:** map shows 3 fake cameras (2 YouTube, 1 placeholder Sentinel).

### M3 — Vehicle detect + ANPR (2 days)

- YOLO on sampled frames
- If vehicle: try plate OCR
- Save event: `plate, camera_id, time, snapshot_path, confidence`
- UI overlay: box + plate text on snapshot

**Done when:** a known plate in your YouTube clip appears in the events list.

### M4 — Watchlist + alerts (1 day)

- Watchlist table (add `GJ-01-AB-1234` manually)
- If event plate matches → alert row + red banner
- Simple sound optional

**Done when:** putting a detected plate on the watchlist fires an alert on the next loop. *(Built: `GJ01AB1234` seeds as stolen; matches existing events without re-YOLO.)*

### M5 — Hunt screen (the jury test) (1–1.5 days)

- Search box: vehicle number
- Results: camera, time, snapshot
- Map polyline if 2+ cameras (use two YouTube clips as two locations)
- Export CSV: plate, camera, location, timestamp

**Done when:** you type a plate and get a 2-stop “route” from two videos. *(Built: Hunt box + polyline + CSV on Gate/Paldi.)*

### M6 — Swap official feeds (0.5–1 day, after M5 works)

- Worker accepts `http` source: `/stream/9` etc.
- Import from `/api/cameras` **once** (cache JSON locally so we do not refetch every second)
- Process 4–6 road cameras only (Paldi, Visat, Adalaj toll, Junagadh bypass / Cam 9)
- Same hunt UI

**Done when:** one Sentinel camera produces at least vehicle events; plate if readable. *(Built: `POST /cameras/sentinel/import` + RTSP TCP capture. Port 8554 must be open on your network.)*

### M7 — Jury pack (1–1.5 days)

- Own-feed demo video (2–3 min screen record of YouTube path)
- Government-feed screen record + timestamp report
- PPT: Hybrid 1+2, why, architecture, 80k roadmap
- HLD PDF: ingest, GIS, ANPR, security, scale, cost
- Hosted URL or local demo script + GitHub

**Done when:** a stranger can follow an 8-minute script and see hunt + alert.

---

## Calendar (today = 19 Aug 2026 → event 1–2 Sep)

| When | Milestone |
|---|---|
| 19–20 Aug | M0 + M1 |
| 21 Aug | M2 |
| 22–23 Aug | M3 |
| 24 Aug | M4 |
| 25–26 Aug | M5 |
| 27 Aug | M6 (Sentinel swap) |
| 28–30 Aug | M7 + buffer |
| 1–2 Sep | On-site: paste their vehicle number into Hunt |

If slipping: **cut live wall of 30 tiles**, keep map + hunt + 2 videos. Hunt is the score.

---

## 8-minute demo script (target)

1. Map with cameras (Model 1).  
2. Open live/file wall — real video (Model 2).  
3. Alert: stolen plate match.  
4. Hunt: type number → trail + timestamps.  
5. Export report.  
6. One slide: same URLs tomorrow = 80k with more GPUs + adapters.

---

## Start command (M0 next)

When you say go: scaffold FastAPI + Vite React, one sample camera pointing at `data/videos/sample.mp4`. You drop a YouTube-downloaded MP4 in that folder and we wire M1.
