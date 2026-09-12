from contextlib import asynccontextmanager
from io import StringIO
import urllib.error

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from alerts import build_alerts, hunt_plate
from config import settings
from detect import analyze_frames
from events import list_events
from live_capture import extract_camera
from gap_pdf import build_gap_pdf
from reports import (
    activity_csv,
    anpr_index,
    camera_index,
    camera_index_csv,
    close_day,
    daily_activity,
    frame_log,
    frames_csv,
    gap_analysis_csv,
    plates_csv,
    storage_policy,
    tagged_events,
    today_ist,
)
from live_proxy import live_asset
from sentinel import auth_status, import_ingest, login as sentinel_login, probe_path
from store import (
    enrich,
    ensure_demo_registry,
    gap_report,
    get_camera,
    import_csv,
    list_cameras,
    snapshot_dir,
    upsert_camera,
)
from watchlist import add_watchlist, ensure_demo_watchlist, list_watchlist, remove_watchlist


@asynccontextmanager
async def lifespan(_app: FastAPI):
    ensure_demo_registry()
    ensure_demo_watchlist()
    yield


app = FastAPI(title="Sentinel Command", version="0.9.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount(
    "/media/videos",
    StaticFiles(directory=str(settings.videos_dir)),
    name="videos",
)
app.mount(
    "/media/snapshots",
    StaticFiles(directory=str(settings.snapshots_dir)),
    name="snapshots",
)


class WatchlistIn(BaseModel):
    plate: str = Field(min_length=4)
    reason: str = "stolen"


class CameraIn(BaseModel):
    name: str = Field(min_length=1)
    source_url: str
    location: str = "Dev feed"
    city: str = ""
    lat: float = 23.0225
    lng: float = 72.5714
    source_type: str = "file"
    camera_id: str | None = None


class SentinelLoginIn(BaseModel):
    password: str = Field(min_length=4)


@app.get("/health")
def health():
    cams = ensure_demo_registry()
    online = sum(1 for c in cams if c["status"] == "online")
    return {
        "status": "ok",
        "service": "sentinel-command",
        "camera_count": len(cams),
        "online": online,
        "offline": len(cams) - online,
    }


@app.get("/live/{camera_id}/{name}")
def live_stream(camera_id: str, name: str):
    try:
        body, ctype = live_asset(camera_id, name)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except urllib.error.HTTPError as exc:
        raise HTTPException(status_code=exc.code, detail=f"Upstream HLS {exc.code}") from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Live proxy failed: {exc}") from exc
    return Response(content=body, media_type=ctype)


@app.get("/sentinel/status")
def sentinel_status():
    return probe_path()


@app.get("/sentinel/auth")
def sentinel_auth():
    return auth_status()


@app.post("/sentinel/login")
def sentinel_session(body: SentinelLoginIn):
    result = sentinel_login(body.password)
    if not result.get("ok"):
        raise HTTPException(status_code=401, detail=result.get("detail") or "Login failed")
    return result


@app.get("/cameras")
def cameras():
    return {"cameras": ensure_demo_registry()}


@app.get("/cameras/gap")
def cameras_gap():
    return gap_report()


@app.get("/cameras/gap.csv")
def cameras_gap_csv():
    return Response(
        content=gap_analysis_csv(gap_report()),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="gap-analysis.csv"'},
    )


@app.get("/cameras/gap.pdf")
def cameras_gap_pdf():
    return Response(
        content=build_gap_pdf(),
        media_type="application/pdf",
        headers={"Content-Disposition": 'inline; filename="gap-analysis.pdf"'},
    )


@app.get("/cameras.csv")
def cameras_csv():
    cams = [enrich(c) for c in list_cameras()]
    buf = StringIO()
    buf.write("id,name,location,city,department,camera_type,status,lat,lng,source_type,codec,live\n")
    for cam in cams:
        buf.write(
            ",".join(
                [
                    _csv(cam.get("id")),
                    _csv(cam.get("name")),
                    _csv(cam.get("location")),
                    _csv(cam.get("city")),
                    _csv(cam.get("department")),
                    _csv(cam.get("camera_type")),
                    _csv(cam.get("status")),
                    str(cam.get("lat") or ""),
                    str(cam.get("lng") or ""),
                    _csv(cam.get("source_type")),
                    _csv(cam.get("codec")),
                    str(bool(cam.get("live"))),
                ]
            )
            + "\n"
        )
    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="cameras-registry.csv"'},
    )


@app.post("/cameras")
def create_camera(body: CameraIn):
    try:
        return upsert_camera(
            name=body.name,
            source_url=body.source_url,
            location=body.location,
            city=body.city,
            lat=body.lat,
            lng=body.lng,
            camera_id=body.camera_id,
            source_type=body.source_type,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/cameras/import")
async def import_cameras(file: UploadFile = File(...)):
    raw = (await file.read()).decode("utf-8-sig")
    try:
        return import_csv(raw)
    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/cameras/sentinel/import")
def import_sentinel():
    try:
        return import_ingest()
    except PermissionError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Could not fetch /api/ingest: {exc}") from exc


@app.post("/cameras/{camera_id}/extract")
def extract(camera_id: str, fps: float = 1.0, duration: float = 12.0):
    cam = get_camera(camera_id)
    if not cam:
        raise HTTPException(status_code=404, detail="Unknown camera")
    try:
        result = extract_camera(cam, fps=fps, duration_sec=duration)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    payload = enrich(get_camera(camera_id))
    payload.update(result)
    return payload


@app.get("/events")
def events(camera_id: str | None = None, tag: str | None = None, day: str | None = None):
    if tag or day:
        return {"events": tagged_events(camera_id, tag=tag, day=day)}
    return {"events": list_events(camera_id)}


@app.get("/metadata/plates")
def metadata_plates():
    return anpr_index()


@app.get("/metadata/plates.csv")
def metadata_plates_csv():
    payload = anpr_index()
    return Response(
        content=plates_csv(payload),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="anpr-metadata.csv"'},
    )


@app.get("/index/cameras")
def index_cameras():
    return camera_index()


@app.get("/index/cameras.csv")
def index_cameras_csv():
    return Response(
        content=camera_index_csv(camera_index()),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="camera-index.csv"'},
    )


@app.get("/reports/policy")
def report_policy():
    return storage_policy()


@app.get("/reports/gap.pdf")
def report_gap_pdf():
    return cameras_gap_pdf()


@app.get("/reports/daily")
def report_daily(date: str | None = None):
    return daily_activity(date or today_ist())


@app.get("/reports/daily.csv")
def report_daily_csv(date: str | None = None):
    day = date or today_ist()
    payload = daily_activity(day)
    return Response(
        content=activity_csv(payload),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="daily-{day}.csv"'},
    )


@app.get("/reports/frames.csv")
def report_frames_csv(date: str | None = None):
    day = date or today_ist()
    return Response(
        content=frames_csv(frame_log(day)),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="frames-{day}.csv"'},
    )


@app.post("/reports/close-day")
def report_close_day(date: str | None = None):
    return close_day(date or today_ist())


@app.get("/watchlist")
def watchlist():
    return {"items": list_watchlist()}


@app.post("/watchlist")
def create_watchlist(body: WatchlistIn):
    try:
        return add_watchlist(body.plate, body.reason)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.delete("/watchlist/{plate}")
def delete_watchlist(plate: str):
    remove_watchlist(plate)
    return {"ok": True}


@app.get("/alerts")
def alerts():
    items = build_alerts()
    return {"alerts": items, "count": len(items)}


@app.get("/hunt")
def hunt(plate: str):
    return hunt_plate(plate)


@app.get("/hunt.csv")
def hunt_csv(plate: str):
    data = hunt_plate(plate)
    buf = StringIO()
    buf.write("plate,camera_id,camera_name,location,city,captured_at,t_sec,label,created_at,snapshot_url\n")
    for hit in data["hits"]:
        buf.write(
            ",".join(
                [
                    data["plate"],
                    str(hit.get("camera_id") or ""),
                    _csv(hit.get("camera_name")),
                    _csv(hit.get("location")),
                    _csv(hit.get("city")),
                    _csv(hit.get("captured_at")),
                    str(hit.get("t_sec") if hit.get("t_sec") is not None else ""),
                    _csv(hit.get("label")),
                    _csv(hit.get("created_at")),
                    _csv(hit.get("snapshot_url")),
                ]
            )
            + "\n"
        )
    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="hunt-{data["plate"] or "plate"}.csv"'},
    )


def _csv(value) -> str:
    text = str(value or "").replace('"', '""')
    return f'"{text}"'


@app.post("/cameras/{camera_id}/analyze")
def analyze(camera_id: str, duration: float = 12.0):
    cam = get_camera(camera_id)
    if not cam:
        raise HTTPException(status_code=404, detail="Unknown camera")
    if not list(snapshot_dir(camera_id).glob("frame_*.jpg")):
        extract_camera(cam, fps=1.0, duration_sec=duration)
    try:
        summary = analyze_frames(camera_id, cam)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Detect failed: {exc}") from exc
    payload = enrich(get_camera(camera_id))
    payload.update(summary)
    return payload
