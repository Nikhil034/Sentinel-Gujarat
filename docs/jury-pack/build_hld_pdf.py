#!/usr/bin/env python3
"""Jury HLD PDF — current architecture, not the stale /api/ingest wording."""

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image,
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / "Sentinel-Command-HLD.pdf"
NAVY = colors.HexColor("#1B3A5C")
GOLD = colors.HexColor("#D4A843")
LINE = colors.HexColor("#C5D0DC")
MUTED = colors.HexColor("#4A5A6A")


def styles():
    base = getSampleStyleSheet()
    s = {
        "cover": ParagraphStyle(
            "cover", parent=base["Title"], fontName="Times-Bold", fontSize=22,
            textColor=NAVY, leading=26, spaceAfter=8, alignment=TA_LEFT,
        ),
        "h1": ParagraphStyle(
            "h1", parent=base["Heading1"], fontName="Times-Bold", fontSize=14,
            textColor=NAVY, spaceBefore=14, spaceAfter=6, leading=18,
        ),
        "h2": ParagraphStyle(
            "h2", parent=base["Heading2"], fontName="Times-Bold", fontSize=12,
            textColor=NAVY, spaceBefore=10, spaceAfter=4, leading=15,
        ),
        "body": ParagraphStyle(
            "body", parent=base["BodyText"], fontName="Times-Roman", fontSize=10,
            leading=14, alignment=TA_JUSTIFY, textColor=colors.HexColor("#1E2D3D"),
        ),
        "small": ParagraphStyle(
            "small", parent=base["BodyText"], fontName="Times-Roman", fontSize=8.5,
            leading=11, textColor=MUTED,
        ),
        "cell": ParagraphStyle(
            "cell", parent=base["BodyText"], fontName="Times-Roman", fontSize=8.5,
            leading=11, textColor=colors.HexColor("#1E2D3D"),
        ),
        "cellb": ParagraphStyle(
            "cellb", parent=base["BodyText"], fontName="Times-Bold", fontSize=8.5,
            leading=11, textColor=NAVY,
        ),
        "pitch": ParagraphStyle(
            "pitch", parent=base["BodyText"], fontName="Times-Italic", fontSize=11,
            leading=15, textColor=NAVY, alignment=TA_JUSTIFY,
        ),
    }
    return s


def P(text, st):
    return Paragraph(text, st)


def tbl(rows, col_widths, header=True):
    data = rows
    t = Table(data, colWidths=col_widths, repeatRows=1 if header else 0)
    cmds = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("GRID", (0, 0), (-1, -1), 0.4, LINE),
    ]
    if header:
        cmds += [
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Times-Bold"),
        ]
    t.setStyle(TableStyle(cmds))
    return t


def header_footer(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(NAVY)
    canvas.rect(0, A4[1] - 14 * mm, A4[0], 14 * mm, fill=1, stroke=0)
    canvas.setFillColor(GOLD)
    canvas.rect(0, A4[1] - 14 * mm, 4 * mm, 14 * mm, fill=1, stroke=0)
    canvas.setFillColor(colors.white)
    canvas.setFont("Times-Bold", 9)
    canvas.drawString(16 * mm, A4[1] - 9 * mm, "Sentinel Command  ·  High-Level Design")
    canvas.setFont("Times-Roman", 8)
    canvas.drawRightString(A4[0] - 14 * mm, A4[1] - 9 * mm, "Gujarat Police Innovation Challenge 2026")
    canvas.setFillColor(NAVY)
    canvas.rect(0, 0, A4[0], 12 * mm, fill=1, stroke=0)
    canvas.setFillColor(colors.white)
    canvas.setFont("Times-Roman", 8)
    canvas.drawString(16 * mm, 5 * mm, "Category 1 solo  ·  Hybrid Model 1 + 2  ·  Consume official RTSP/HLS")
    canvas.drawRightString(A4[0] - 14 * mm, 5 * mm, f"Page {doc.page}")
    canvas.restoreState()


def build():
    S = styles()
    c = S["cell"]
    b = S["cellb"]
    story = []

    story.append(P("Sentinel Command", S["cover"]))
    story.append(P(
        "Technical Proposal — High-Level Design for the Gujarat Police Innovation Challenge 2026 "
        "(Sentinel CCTV). Author: Nikhil. Scope: Hybrid <b>Model 1</b> (central CCTV registry and GIS) "
        "+ <b>Model 2</b> (unified viewing, ANPR metadata, watchlist alerts, cross-camera hunt).",
        S["body"],
    ))
    story.append(Spacer(1, 6))
    story.append(P(
        "Sentinel Command unifies the official Sentinel camera catalogue on a GIS map, plays live feeds "
        "in one dashboard, runs ANPR with watchlist alerts, and produces hunt trails with CSV export — "
        "built to the official cameras.json, RTSP-TCP, and HLS contract on cctv.corp8.cloud.",
        S["pitch"],
    ))

    story.append(P("1. Problem and permitted approach", S["h1"]))
    story.append(P(
        "Twenty-six departments operate independent CCTV estates across Gujarat — analog and IP, cloud "
        "and local storage, different vendors and retention. Police lack a single map of assets, a single "
        "viewer, and a way to correlate live video with stolen/wanted records (VAHAN, SARTHI, eGujCop). "
        "The official brief allows any reference model, a hybrid, or a custom architecture. Model 1 is the "
        "mandatory GIS foundation.",
        S["body"],
    ))
    story.append(P(
        "<b>Choice:</b> Hybrid Model 1 + 2. Justification for Category 1 (solo): deliver a working registry "
        "and a working ANPR/hunt loop on the sandbox feeds, without faking Model 3 vendor adapters or a "
        "Model 4 central VMS. Departmental NVRs remain the system of record for video. We consume RTSP and HLS only.",
        S["body"],
    ))

    story.append(P("2. Overall architecture", S["h1"]))
    story.append(P(
        "Three lanes. (1) Official Sentinel/Corp8 grid: cameras, ingest hub, password portal, RTSP on "
        "103.250.160.189:8554, HLS on cctv.corp8.cloud. (2) Sentinel Command: React UI + FastAPI + JSON "
        "store + JPEG evidence. (3) AI pipeline: FFmpeg/OpenCV → YOLOv8n → RapidOCR.",
        S["body"],
    ))
    arch = ROOT / "docs/diagrams/sentinel-architecture.png"
    if arch.is_file():
        img = Image(str(arch), width=170 * mm, height=170 * mm * 680 / 1100)
        img.hAlign = "CENTER"
        story.append(Spacer(1, 4))
        story.append(img)
        story.append(P("Figure 1. System architecture — official grid (left), our app (centre), AI (right).", S["small"]))

    story.append(P("3. Integrating heterogeneous cameras", S["h1"]))
    story.append(P(
        "We do not speak every vendor SDK in this prototype. The sandbox already normalises feeds to RTSP "
        "and HLS. Our integration contract is the integrator guide on cctv.corp8.cloud/resource:",
        S["body"],
    ))
    story.append(tbl(
        [
            [P("<b>Step</b>", c), P("<b>Mechanism</b>", c)],
            [P("Authenticate", c), P("POST /auth/login; HttpOnly cookie held in a server CookieJar. Password in .env, never git.", c)],
            [P("Catalogue", c), P("GET https://cctv.corp8.cloud/cameras.json — array of {id, name} for cam01…cam30.", c)],
            [P("Watch", c), P("HLS https://cctv.corp8.cloud/camXX/index.m3u8 proxied as /live/{id}/index.m3u8 with key + segments.", c)],
            [P("AI ingest", c), P("RTSP TCP rtsp://103.250.160.189:8554/stream/camXX. OPENCV_FFMPEG_CAPTURE_OPTIONS=rtsp_transport;tcp. PTS timing. Backoff 2s–30s.", c)],
            [P("Second system", c), P("Local MP4s registered as cameras (Gate, Paldi, Visat recording) — Model 2 “two systems” proof.", c)],
            [P("Onboarding", c), P("Bulk CSV import, POST /cameras, and POST /cameras/sentinel/import.", c)],
        ],
        [38 * mm, 132 * mm],
    ))
    story.append(P(
        "Existing departmental VMS/storage are unaffected: we never record 24-hour video, never publish "
        "into the gateway, and never require replacing NVRs.",
        S["body"],
    ))

    story.append(P("4. Live stream ingest and processing", S["h1"]))
    story.append(P(
        "Watch path and AI path are deliberately different. HLS on 443 is for humans and restricted "
        "networks. RTSP on 8554 is for OpenCV. Playlists on the sandbox are AES-128 VOD loops presented "
        "as live; the UI seeks currentTime = now % duration, matching the official portal.",
        S["body"],
    ))
    story.append(P(
        "Capture samples ~1 JPEG/s for a short window (default ~12s). Times come from stream PTS (or "
        "clip position for files), not CAP_PROP_FPS. Decoder join warnings (missing POC) are not fatal. "
        "We pace load: only the selected camera is captured.",
        S["body"],
    ))

    story.append(P("5. Watchlist correlation and alerts", S["h1"]))
    hunt = ROOT / "docs/diagrams/hunt-watchlist-flow.png"
    if hunt.is_file():
        img = Image(str(hunt), width=170 * mm, height=170 * mm * 720 / 1100)
        img.hAlign = "CENTER"
        story.append(img)
        story.append(P("Figure 2. Watchlist intersection and cross-camera hunt.", S["small"]))
    story.append(P(
        "The brief allows a representative watchlist. Items live in watchlist.json (plate_norm, reason). "
        "Each ANPR event is normalised (non-alphanumerics stripped, uppercased). GET /alerts is the "
        "intersection of events ∩ watchlist — not a separate store. UI: red STOLEN PLATE banner + beep. "
        "VAHAN / SARTHI / eGujCop are designed as later HTTP adapters behind the same normalize + match "
        "interface; they are not live in this prototype.",
        S["body"],
    ))
    story.append(P(
        "Hunt: GET /hunt?plate= scans all events, sorts by captured_at then t_sec, attaches lat/lng from "
        "the registry, draws a Leaflet polyline, and exports GET /hunt.csv. If the jury plate was not yet "
        "detected, the operator captures 4–6 road cameras, detects, and hunts again.",
        S["body"],
    ))

    story.append(P("6. AI-powered video analytics", S["h1"]))
    story.append(tbl(
        [
            [P("<b>Stage</b>", c), P("<b>Technology</b>", c), P("<b>Output</b>", c)],
            [P("Decode", c), P("FFmpeg / OpenCV", c), P("JPEG stills under data/snapshots/{camera_id}/", c)],
            [P("Detect", c), P("Ultralytics YOLOv8n (nano, CPU)", c), P("Boxes for car / motorcycle / bus / truck", c)],
            [P("Read", c), P("RapidOCR ONNX on lower 45% of box", c), P("Plate string + score", c)],
            [P("Annotate", c), P("YOLO plot + plate overlay", c), P("Evidence JPEG in annotated/", c)],
            [P("Index", c), P("events.json", c), P("camera, time, label, plate, snapshot URL, confidence", c)],
        ],
        [32 * mm, 58 * mm, 80 * mm],
    ))
    story.append(P(
        "Face recognition, crowd counting, and intrusion zones are out of scope for this solo build. "
        "Measured: Paldi official cam04 RTSP sample produced 61 vehicle events and 0 readable plates "
        "(junction too distant). Own-feed Gate/Paldi clips produced 13 hits on GJ01AB1234. Both results "
        "are shown to the jury — we do not claim OCR on every statewide PTZ.",
        S["body"],
    ))

    story.append(P("7. Alert workflow", S["h1"]))
    story.append(P(
        "Prioritisation in this prototype is binary: watchlist match vs not. Visualisation is the banner, "
        "hot event rows, and hunt trail. Interaction: add/remove plates, hunt, export CSV, open snapshot. "
        "Production would add severity, acknowledgement, and audit — listed as Phase 2.",
        S["body"],
    ))

    story.append(P("8. Scalability, interoperability, security, performance", S["h1"]))
    story.append(P("8.1 Scale path (~80,000 cameras)", S["h2"]))
    story.append(tbl(
        [
            [P("<b>Phase</b>", c), P("<b>Change</b>", c)],
            [P("Hackathon now", c), P("JSON store, one node, 30–40 cameras, CPU YOLO, short samples.", c)],
            [P("Phase 2", c), P("PostgreSQL + PostGIS, Redis watchlist, object storage, simple RBAC.", c)],
            [P("Phase 3", c), P("Zone RTSP workers, queue, horizontal API, GPU batching, HLS edge cache.", c)],
            [P("Phase 4", c), P("VAHAN/eGujCop adapters, optional FRS, HA/DR, regional PoPs.", c)],
        ],
        [40 * mm, 130 * mm],
    ))
    story.append(P(
        "Principle: keep raw video near source; centralise metadata and alerts. Do not transcode 80k "
        "streams in one hall. Bandwidth: ANPR workers pull RTSP only for cameras under active analytics; "
        "officers use HLS. Storage: hot (days of snapshots), warm (object store), cold (department NVR "
        "retention 7–15 days as today).",
        S["body"],
    ))
    story.append(P("8.2 Interoperability", S["h2"]))
    story.append(P(
        "Open protocols only (RTSP, HLS, REST JSON). Catalogue is the contract. New cameras appear by "
        "re-fetching cameras.json or CSV. Vendor lock-in is avoided by not embedding a proprietary VMS.",
        S["body"],
    ))
    story.append(P("8.3 Security", S["h2"]))
    story.append(P(
        "Consume-only. Grid password not in source control. Session cookie server-side. No public write "
        "APIs. CORS limited to local UI origins. Production needs SSO/RBAC, TLS everywhere, audit logs, "
        "network segmentation — documented, not implemented in the sandbox app.",
        S["body"],
    ))

    story.append(P("9. Component map and APIs", S["h1"]))
    story.append(tbl(
        [
            [P("<b>Module</b>", c), P("<b>Responsibility</b>", c)],
            [P("main.py", c), P("REST, CORS, /media mounts, /live HLS proxy route", c)],
            [P("sentinel.py", c), P("Login, cameras.json, URL rewrite, TCP probe, cookie jar", c)],
            [P("store.py", c), P("Registry CRUD, GIS enrich, CSV, gap report", c)],
            [P("live_capture.py", c), P("RTSP TCP sampling with PTS; HLS fallback", c)],
            [P("live_proxy.py", c), P("Playlist/key/segment proxy for the browser player", c)],
            [P("ingest.py", c), P("FFmpeg frames from MP4", c)],
            [P("detect.py", c), P("YOLO + OCR + annotated JPEG + events", c)],
            [P("events.py / watchlist.py / alerts.py / plates.py", c), P("Index, stolen list, intersection, plate norm", c)],
        ],
        [48 * mm, 122 * mm],
    ))
    story.append(Spacer(1, 6))
    story.append(P(
        "Key endpoints: GET /health, /cameras, /cameras/gap, /cameras.csv, POST /cameras/sentinel/import, "
        "POST /sentinel/login, POST /cameras/{id}/extract, POST /cameras/{id}/analyze, GET /events, "
        "POST /watchlist, GET /alerts, GET /hunt, GET /hunt.csv, GET /live/{id}/index.m3u8.",
        S["body"],
    ))
    story.append(P(
        "UI: http://localhost:5174 (Vite proxies to FastAPI :8000). OpenAPI: http://127.0.0.1:8000/docs.",
        S["body"],
    ))

    story.append(P("10. Prerequisites from departments", S["h1"]))
    story.append(P(
        "To onboard a real department we need: RTSP or HLS URL (or ONVIF device URL for a future adapter), "
        "approximate lat/lng, owning department, camera type, and whether 8554/443 is reachable from the "
        "analytics zone. Official lat/lng in the catalogue would replace our name-based geocode. "
        "Watchlist APIs (VAHAN stolen vehicles) need a documented JSON contract and credentials.",
        S["body"],
    ))

    story.append(P("11. Known limitations (for evaluators)", S["h1"]))
    story.append(P(
        "Sandbox catalogue is ~30 cameras, not 50. ANPR is on-demand short samples, not a continuous "
        "30-camera worker. JSON persistence, not PostGIS. No RBAC. Live Paldi OCR often fails on distance. "
        "These are stated so the working hunt, GIS, official ingest, and own-feed plates can be trusted.",
        S["body"],
    ))

    story.append(Spacer(1, 8))
    story.append(P(
        "This HLD accompanies the working prototype, the solution presentation, the own-feed and "
        "government-feed recordings, and the analytics output report in docs/jury-pack/.",
        S["small"],
    ))

    doc = SimpleDocTemplate(
        str(OUT),
        pagesize=A4,
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        topMargin=22 * mm,
        bottomMargin=18 * mm,
        title="Sentinel Command — High-Level Design",
        author="Nikhil",
    )
    doc.build(story, onFirstPage=header_footer, onLaterPages=header_footer)
    print("Wrote", OUT)


if __name__ == "__main__":
    build()
