from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

import cv2

from events import append_events, clear_events
from plates import normalize_plate
from store import load_frame_times, prune_camera_media, snapshot_dir
from watchlist import list_watchlist

VEHICLE_CLASS_IDS = {2, 3, 5, 7}  # car, motorcycle, bus, truck
PLATE_RE = re.compile(r"[A-Z]{2}\s?-?\s?\d{1,2}\s?-?\s?[A-Z]{0,3}\s?-?\s?\d{3,4}")

_yolo = None
_ocr = None


def _model():
    global _yolo
    if _yolo is None:
        from ultralytics import YOLO

        _yolo = YOLO("yolov8n.pt")
    return _yolo


def _reader():
    global _ocr
    if _ocr is False:
        return None
    if _ocr is None:
        try:
            from rapidocr_onnxruntime import RapidOCR

            _ocr = RapidOCR()
        except Exception:
            _ocr = False
    return None if _ocr is False else _ocr


def _read_plate(crop) -> tuple[str | None, float]:
    reader = _reader()
    if reader is None or crop is None or crop.size == 0:
        return None, 0.0
    h, w = crop.shape[:2]
    if h < 12 or w < 24:
        return None, 0.0
    result, _ = reader(crop)
    if not result:
        return None, 0.0
    best_text, best_score = None, 0.0
    for item in result:
        text = re.sub(r"[^A-Z0-9]", "", str(item[1]).upper())
        score = float(item[2]) if len(item) > 2 else 0.0
        if len(text) < 4:
            continue
        if score > best_score:
            best_text, best_score = text, score
    if not best_text:
        return None, 0.0
    pretty = best_text
    match = PLATE_RE.search(best_text)
    if match:
        pretty = re.sub(r"\s+", "", match.group(0))
    return pretty, best_score


def analyze_frames(camera_id: str, cam: dict) -> dict:
    frames = sorted(snapshot_dir(camera_id).glob("frame_*.jpg"))
    if not frames:
        return {"analyzed": 0, "vehicles": 0, "plates": 0, "events": []}

    clear_events(camera_id)
    out_dir = snapshot_dir(camera_id) / "annotated"
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("*.jpg"):
        old.unlink()

    model = _model()
    created: list[dict] = []
    vehicles = 0
    plates = 0
    times = load_frame_times(camera_id)
    wanted = {item["plate_norm"] for item in list_watchlist()}

    for index, frame_path in enumerate(frames, start=1):
        image = cv2.imread(str(frame_path))
        if image is None:
            continue
        result = model.predict(image, verbose=False, conf=0.35)[0]
        plotted = result.plot()
        h, w = image.shape[:2]

        if result.boxes is None:
            cv2.imwrite(str(out_dir / frame_path.name), plotted)
            continue

        for box in result.boxes:
            cls_id = int(box.cls[0])
            if cls_id not in VEHICLE_CLASS_IDS:
                continue
            vehicles += 1
            x1, y1, x2, y2 = [int(v) for v in box.xyxy[0].tolist()]
            conf = float(box.conf[0])
            label = result.names.get(cls_id, "vehicle")
            y_mid = y1 + int((y2 - y1) * 0.55)
            crop = image[y_mid:y2, max(0, x1) : min(w, x2)]
            plate, plate_conf = _read_plate(crop)
            if plate:
                plates += 1
                cv2.putText(
                    plotted,
                    plate,
                    (x1, max(20, y1 - 8)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 220, 255),
                    2,
                    cv2.LINE_AA,
                )
            rel = f"/media/snapshots/{camera_id}/annotated/{frame_path.name}"
            meta = times.get(frame_path.name) or {}
            t_sec = meta.get("t_sec")
            if t_sec is None:
                t_sec = index - 1
            captured_at = meta.get("captured_at")
            clock = meta.get("clock") or ("clip" if cam.get("source_type") == "file" else "wall")
            tags = ["vehicle"]
            if plate:
                tags.append("anpr")
                if normalize_plate(plate) in wanted:
                    tags.append("watchlist")
            else:
                tags.append("unread")
            created.append(
                {
                    "id": f"{camera_id}-{index}-{vehicles}",
                    "camera_id": camera_id,
                    "camera_name": cam.get("name"),
                    "location": cam.get("location"),
                    "city": cam.get("city"),
                    "frame": frame_path.name,
                    "t_sec": t_sec,
                    "captured_at": captured_at,
                    "clock": clock,
                    "label": label,
                    "plate": plate,
                    "confidence": round(conf, 3),
                    "plate_confidence": round(plate_conf, 3),
                    "snapshot_url": rel,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "tags": tags,
                }
            )
        cv2.imwrite(str(out_dir / frame_path.name), plotted)

    append_events(created)
    prune_camera_media(camera_id, after_analyze=True)
    latest = None
    annotated = sorted(out_dir.glob("*.jpg"))
    if annotated:
        latest = f"/media/snapshots/{camera_id}/annotated/{annotated[-1].name}"
    return {
        "analyzed": len(frames),
        "vehicles": vehicles,
        "plates": plates,
        "events": created,
        "latest_annotated": latest,
    }
