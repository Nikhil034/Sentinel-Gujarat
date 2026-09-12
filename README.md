# Sentinel Command

Solo prototype for **Gujarat Police Innovation Challenge 2026** — Hybrid **Model 1** (GIS registry) + **Model 2** (unified view, ANPR, watchlist, hunt).

- Problem: https://sentinel.gujarat.gov.in/problems
- Phases: https://sentinel.gujarat.gov.in/phases
- Integrator guide: https://sentinel.gujarat.gov.in/resource
- Live grid (password): https://cctv.corp8.cloud/resource

## Run locally

From the repo root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
cp -n .env.example .env
# If you already registered on the grid, paste the password:
# SENTINEL_PASSWORD=XXXX-XXXX-XXXX
uvicorn main:app --reload --host 127.0.0.1 --port 8000 --app-dir backend
```

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

| What | URL |
|---|---|
| UI | http://localhost:5174 |
| API health | http://localhost:8000/health |
| OpenAPI | http://localhost:8000/docs |
| Learning page (architecture, files, terms) | `docs/sentinel-learning.html` |
| Jury pack (PPT, HLD PDF, output report, demo script) | `docs/jury-pack/` |
| Gap report (JSON) | http://localhost:8000/cameras/gap |
| Gap analysis PDF (for Gujarat Police) | http://localhost:8000/cameras/gap.pdf |
| Daily activity CSV | http://localhost:8000/reports/daily.csv?date=all |
| Frame log CSV | http://localhost:8000/reports/frames.csv?date=all |
| ANPR metadata CSV | http://localhost:8000/metadata/plates.csv |
| Camera index CSV | http://localhost:8000/index/cameras.csv |

## Test script (8 minutes)

**A. Own feed (works without government login)**

1. Open the UI. You should see Gate / Paldi / Visat clips plus cached Sentinel pins on the map.
2. Select **Cam-AHM-Gate ANPR** → **Extract frames** → **Detect vehicles + plates**.
3. Repeat on **Cam-AHM-Paldi ANPR**.
4. Watchlist: add `GJ01AB1234` (or leave the demo seed) → red **STOLEN PLATE** banner.
5. Hunt `GJ01AB1234` → trail on the map → **Export CSV**.
6. **Import CSV** with `data/cameras.sample.csv` if you want a bulk-onboard demo.
7. **Export registry CSV** from the coverage line (Model 1 export).

**B. Government grid (needs access password)**

1. Register: https://cctv.corp8.cloud/auth/register
2. Sign in on the dashboard (or set `SENTINEL_PASSWORD` in `.env`).
3. **Fetch Sentinel grid** — pulls `https://cctv.corp8.cloud/cameras.json`.
4. Open a road camera (Paldi 4, Visat 5, Adalaj 12). If the iframe shows Sign In, log in at https://cctv.corp8.cloud/auth/login in the same browser, then use **Open live portal camera**.
5. **Capture frames (RTSP TCP, then HLS)** → **Detect**. Official RTSP is `rtsp://103.250.160.189:8554/stream/camXX` (open from this network). HLS is `https://cctv.corp8.cloud/camXX/index.m3u8` with the session cookie.
6. **Show 4-up wall** for unified viewing.

## How data moves

```
Official cameras → MediaMTX (their side)
    ├─ GET /api/ingest          → our registry + Leaflet map
    ├─ HTTPS camera page / HLS  → live watch (password cookie)
    └─ RTSP :8554               → AI capture when the port is open
Local MP4 in data/videos/       → same Extract → YOLO → RapidOCR → events
events ∩ watchlist              → alerts
GET /hunt?plate=                → GIS trail + CSV
```

## Integrator checklist (https://sentinel.gujarat.gov.in/resource)

| Rule | Status |
|---|---|
| Catalogue from `cameras.json`, do not hard-code camera ids | Yes |
| RTSP over TCP (`OPENCV_FFMPEG_CAPTURE_OPTIONS=rtsp_transport;tcp`) | Yes |
| If 8554 blocked, use HLS | Yes |
| Timing from PTS, not `CAP_PROP_FPS` / per-frame wall clock | Yes |
| Inter-frame gaps are not fatal | Yes |
| Reconnect backoff 2s → 30s | Yes |
| Decoder join warnings are not fatal | Yes |
| Mixed H.264 / H.265 after decode | Yes (OpenCV) |
| Consume only — never publish to the gateway | Yes |
| Password session for `cctv.corp8.cloud` | Yes (`SENTINEL_PASSWORD` or UI login) |

## Honest limits (Phase 1 sandbox)

- Official HTTP grid is now **password-gated** at `cctv.corp8.cloud`. Old `live.sentinelgujarat.in` / `live.corp8.cloud` URLs 301 into that login.
- Public **RTSP :8554** and **WHEP :8889** time out from the open internet. On-site event network may open them.
- ANPR is a **short sample** per camera, not a 24h DVR and not a continuous 30-camera worker.
- Model 3 (VMS federation) and Model 4 (central VMS, face, VAHAN) are roadmap only.
- Persistence is JSON files (solo speed). PostgreSQL + PostGIS is the scale path in `HLD.md`.

## Daily logs and storage (what we keep)

This app is **not** a DVR. Departmental NVRs keep the video. Sentinel Command keeps **metadata**.

| Keep every day | Do not keep here |
|---|---|
| `data/reports/daily-YYYY-MM-DD.csv` — one row per camera (events, plates, watchlist, notes) | 24-hour video |
| `data/reports/daily-all.csv` — rollup across recorded IST days | Raw extract JPEGs after Detect (deleted automatically) |
| `data/reports/frames-YYYY-MM-DD.csv` — one row per sampled frame | Unbounded snapshot folders |
| `anpr-metadata.csv` + `camera-index.csv` | |
| Last **8** annotated JPEGs per camera (evidence window) | |

In the UI: **Close day — write CSVs + gap PDF**. That writes the sheets above plus `gap-analysis.pdf` for Control Room / GIS staff. Event tags: `vehicle`, `anpr`, `unread`, `watchlist`. Filter them on the camera detail pane.
