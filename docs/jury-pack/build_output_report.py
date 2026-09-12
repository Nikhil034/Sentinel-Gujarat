#!/usr/bin/env python3
"""Government-feed + own-feed analytics output report for submission item 4."""

import csv
import json
from collections import Counter
from datetime import datetime, timezone, timedelta
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

ROOT = Path(__file__).resolve().parents[2]
PACK = Path(__file__).resolve().parent
NAVY = colors.HexColor("#1B3A5C")
GOLD = colors.HexColor("#D4A843")
LINE = colors.HexColor("#C5D0DC")
IST = timezone(timedelta(hours=5, minutes=30))


def cell(text, bold=False, color=None):
    st = ParagraphStyle(
        "c",
        fontName="Times-Bold" if bold else "Times-Roman",
        fontSize=8,
        leading=10,
        textColor=color or (NAVY if bold else colors.HexColor("#1E2D3D")),
    )
    return Paragraph(str(text if text is not None else "—"), st)


def head(text):
    return cell(text, bold=True, color=colors.white)


def when(ev):
    raw = ev.get("captured_at") or ev.get("created_at")
    if raw:
        try:
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            return dt.astimezone(IST).strftime("%d %b %Y %H:%M:%S IST")
        except Exception:
            pass
    t = ev.get("t_sec")
    if t is None:
        return "—"
    t = float(t)
    return f"clip {int(t // 60)}:{int(t % 60):02d}"


def build():
    events = json.loads((ROOT / "data/events.json").read_text())["events"]
    cams = json.loads((ROOT / "data/cameras.json").read_text())["cameras"]
    official = [c for c in cams if str(c.get("id", "")).startswith("sentinel-")]
    own = [c for c in cams if c.get("source_type") == "file"]
    s4 = [e for e in events if e.get("camera_id") == "sentinel-4"]
    s5 = [e for e in events if e.get("camera_id") == "sentinel-5"]
    hunt = [
        e
        for e in events
        if (e.get("plate") or "").replace("-", "").replace(" ", "").upper() == "GJ01AB1234"
    ]

    csv_path = PACK / "hunt-GJ01AB1234.csv"
    with csv_path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "plate",
                "camera_id",
                "camera_name",
                "location",
                "city",
                "t_sec",
                "label",
                "confidence",
                "created_at",
                "snapshot_url",
            ]
        )
        for e in hunt:
            w.writerow(
                [
                    "GJ01AB1234",
                    e.get("camera_id"),
                    e.get("camera_name"),
                    e.get("location"),
                    e.get("city"),
                    e.get("t_sec"),
                    e.get("label"),
                    e.get("confidence"),
                    e.get("created_at"),
                    e.get("snapshot_url"),
                ]
            )

    styles = getSampleStyleSheet()
    title = ParagraphStyle("t", parent=styles["Title"], fontName="Times-Bold", fontSize=16, textColor=NAVY, alignment=TA_LEFT)
    h = ParagraphStyle("h", parent=styles["Heading2"], fontName="Times-Bold", fontSize=11, textColor=NAVY, spaceBefore=10)
    body = ParagraphStyle("b", parent=styles["BodyText"], fontName="Times-Roman", fontSize=9.5, leading=13)
    small = ParagraphStyle("s", parent=styles["BodyText"], fontName="Times-Roman", fontSize=8, textColor=colors.HexColor("#4A5A6A"))

    story = []
    story.append(Paragraph("Sentinel Command — Analytics Output Report", title))
    story.append(Paragraph(
        "Gujarat Police Innovation Challenge 2026  ·  Government-feed and own-feed demonstration  ·  "
        "Generated from the working events store (not a mock spreadsheet).",
        small,
    ))
    story.append(Spacer(1, 8))
    story.append(Paragraph("1. Onboarding evidence", h))
    story.append(Paragraph(
        f"Registry contains <b>{len(cams)}</b> cameras: <b>{len(official)}</b> official Sentinel ids "
        f"(cam01–cam30 via cameras.json) and <b>{len(own)}</b> own-feed recordings. "
        "This is the full sandbox catalogue (the brief says “approximately 50”; the live grid currently publishes 30).",
        body,
    ))
    story.append(Paragraph("2. Government-provided feed (Camera 4 Paldi / cam04)", h))
    story.append(Paragraph(
        "Ingest: RTSP TCP <font face='Courier'>rtsp://103.250.160.189:8554/stream/cam04</font>. "
        "Method recorded as rtsp-tcp. Sample window on 01 Sep 2026 ~19:17 UTC (00:47 IST 02 Sep).",
        body,
    ))
    labels = Counter(e.get("label") for e in s4)
    story.append(Paragraph(
        f"YOLOv8n output: <b>{len(s4)}</b> vehicle events — "
        + ", ".join(f"{k} {v}" for k, v in labels.most_common())
        + ". RapidOCR readable plates on this wide junction sample: <b>0</b>. "
        "That is expected at Paldi circle distance; we still emit timestamped vehicle metadata and annotated stills.",
        body,
    ))
    if s4:
        rows = [[head("Time (IST)"), head("t_sec"), head("Class"), head("Conf"), head("Snapshot")]]
        # unique-ish sample: first of each second
        seen = set()
        for e in s4:
            key = (round(float(e.get("t_sec") or 0), 1), e.get("label"))
            if key in seen:
                continue
            seen.add(key)
            rows.append([
                cell(when(e)),
                cell(e.get("t_sec")),
                cell(e.get("label")),
                cell(e.get("confidence")),
                cell(Path(str(e.get("snapshot_url") or "")).name or "—"),
            ])
            if len(rows) >= 13:
                break
        t = Table(rows, colWidths=[42 * mm, 18 * mm, 28 * mm, 18 * mm, 64 * mm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.4, LINE),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(t)
        story.append(Paragraph("Table 1. Sample of Paldi (cam04) live detections. Full set is 61 rows in events.json.", small))

    story.append(Paragraph("3. Government feed Camera 5 Visat (cam05)", h))
    story.append(Paragraph(
        f"Earlier RTSP sample stored <b>{len(s5)}</b> vehicle events (plates unread). Same pipeline as Paldi.",
        body,
    ))

    story.append(Paragraph("4. Own-feed ANPR + watchlist hunt (GJ01AB1234)", h))
    story.append(Paragraph(
        "Close-up Gate and Paldi-style MP4s, treated as two cameras. Representative watchlist plate "
        "<b>GJ01AB1234</b> (stolen). Hunt returns the trail below. CSV sibling file: hunt-GJ01AB1234.csv.",
        body,
    ))
    rows = [[
        head("Camera"), head("Location"), head("Clip time"),
        head("Class"), head("Conf"), head("When stored (UTC)"),
    ]]
    for e in hunt:
        rows.append([
            cell(e.get("camera_name")),
            cell(e.get("location")),
            cell(f"{e.get('t_sec')}s"),
            cell(e.get("label")),
            cell(e.get("confidence")),
            cell((e.get("created_at") or "")[:19]),
        ])
    t = Table(rows, colWidths=[38 * mm, 48 * mm, 20 * mm, 18 * mm, 16 * mm, 30 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.4, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(t)
    story.append(Paragraph(
        f"Table 2. Hunt GJ01AB1234 — {len(hunt)} hits across {len({e['camera_id'] for e in hunt})} cameras (Gate boom + Paldi junction).",
        small,
    ))

    story.append(Paragraph("5. How to reproduce on jury day", h))
    story.append(Paragraph(
        "1. Start API :8000 and UI :5174. 2. Confirm grid signed in. 3. Fetch Sentinel grid. "
        "4. Select Camera 4 — HLS plays. Capture → Detect. 5. Own-feed Gate/Paldi Detect. "
        "6. Hunt the designated registration. 7. Export CSV. If Hunt is empty, capture 4/5/12 first.",
        body,
    ))
    story.append(Spacer(1, 8))
    story.append(Paragraph(
        "This report is generated from data/events.json in the prototype. Mock-ups were not used.",
        small,
    ))

    out = PACK / "government-feed-output-report.pdf"

    def hf(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(NAVY)
        canvas.rect(0, A4[1] - 12 * mm, A4[0], 12 * mm, fill=1, stroke=0)
        canvas.setFillColor(GOLD)
        canvas.rect(0, A4[1] - 12 * mm, 3 * mm, 12 * mm, fill=1, stroke=0)
        canvas.setFillColor(colors.white)
        canvas.setFont("Times-Bold", 8)
        canvas.drawString(14 * mm, A4[1] - 8 * mm, "Analytics output report  ·  Sentinel Command")
        canvas.setFillColor(NAVY)
        canvas.rect(0, 0, A4[0], 10 * mm, fill=1, stroke=0)
        canvas.setFillColor(colors.white)
        canvas.setFont("Times-Roman", 8)
        canvas.drawRightString(A4[0] - 14 * mm, 4 * mm, f"Page {doc.page}")
        canvas.restoreState()

    doc = SimpleDocTemplate(
        str(out), pagesize=A4,
        leftMargin=14 * mm, rightMargin=14 * mm, topMargin=18 * mm, bottomMargin=16 * mm,
        title="Sentinel Command analytics output report", author="Nikhil",
    )
    doc.build(story, onFirstPage=hf, onLaterPages=hf)
    print("Wrote", out)
    print("Wrote", csv_path)


if __name__ == "__main__":
    build()
