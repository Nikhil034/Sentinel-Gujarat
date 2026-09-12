#!/usr/bin/env python3
"""One-page (plus) judge demo script — print and keep beside the laptop."""

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

PACK = Path(__file__).resolve().parent
NAVY = colors.HexColor("#1B3A5C")
GOLD = colors.HexColor("#D4A843")
LINE = colors.HexColor("#C5D0DC")


def C(text, bold=False, color=None):
    st = ParagraphStyle(
        "x",
        fontName="Times-Bold" if bold else "Times-Roman",
        fontSize=8.5,
        leading=11,
        textColor=color or colors.HexColor("#1E2D3D"),
    )
    return Paragraph(str(text), st)


def build():
    styles = getSampleStyleSheet()
    title = ParagraphStyle("t", parent=styles["Title"], fontName="Times-Bold", fontSize=16, textColor=NAVY, alignment=0)
    h = ParagraphStyle("h", parent=styles["Heading2"], fontName="Times-Bold", fontSize=11, textColor=NAVY, spaceBefore=8)
    body = ParagraphStyle("b", parent=styles["BodyText"], fontName="Times-Roman", fontSize=9.5, leading=13)

    story = []
    story.append(Paragraph("Sentinel Command — 8-minute jury demo script", title))
    story.append(Paragraph(
        "Print this. Laptop: API http://127.0.0.1:8000 and UI <b>http://localhost:5174</b> already running. "
        "Grid password already in local .env. Do not show .env to the room.",
        body,
    ))
    story.append(Paragraph("Timed run", h))
    rows = [[C("Time", True), C("Click", True), C("Say", True), C("If it fails", True)]]
    demo = [
        ("0:00–0:40", "Map of Gujarat pins", "Hybrid Model 1 + 2. We do not replace departmental VMS. Registry first, then analytics.", "Refresh UI."),
        ("0:40–1:20", "Fetch Sentinel grid", "Catalogue from official cameras.json. Thirty sandbox cameras. Export registry CSV.", "Use cached 30 pins; say catalogue was imported."),
        ("1:20–2:10", "Camera 4 or 12 — player", "Unified viewing: HLS in one UI, same grid as the portal.", "Open cctv.corp8.cloud in a tab; same password session."),
        ("2:10–3:20", "Cam-AHM-Gate: Extract → Detect", "Own feed. Close plates. YOLO boxes, RapidOCR.", "Events already in store — scroll the list."),
        ("3:20–4:00", "Watchlist GJ01AB1234", "Representative stolen list, allowed by the brief. Red banner is events ∩ watchlist.", "Add the plate again; banner uses existing events."),
        ("4:00–5:00", "Hunt GJ01AB1234 → Export CSV", "This is the scoring test: number in, route + timestamps + evidence.", "CSV file hunt-GJ01AB1234.csv is in the jury pack."),
        ("5:00–6:20", "Camera 4 live: Capture → Detect", "Government RTSP TCP per integrator guide. Vehicles + IST times. If plate unread, distance — not a missing model.", "Show Paldi rows in the output report."),
        ("6:20–7:20", "Architecture / scale slide", "Same APIs. Postgres, zone workers, VAHAN adapter later. 80k is more machines, not a rewrite.", "HLD PDF in the pack."),
        ("7:20–8:00", "Stop. Ask for their number", "Paste designated registration into Hunt.", "Capture 4, 5, 12 then Detect, Hunt again. Do not freeze."),
    ]
    for r in demo:
        rows.append([C(r[0], True, NAVY), C(r[1]), C(r[2]), C(r[3])])
    t = Table(rows, colWidths=[28 * mm, 40 * mm, 62 * mm, 40 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.4, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F6F8")]),
    ]))
    story.append(t)
    story.append(Paragraph("Lines to say", h))
    story.append(Paragraph(
        "“Model 1 is the GIS foundation; Model 2 is viewing and ANPR on feeds we are given.” "
        "“We consume standard RTSP and HLS; we do not replace MediaMTX.” "
        "“Watchlist is ours for the sandbox; VAHAN is an API adapter in Phase 2.” "
        "“Short samples, not a 24-hour DVR.”",
        body,
    ))
    story.append(Paragraph("Do not say", h))
    story.append(Paragraph(
        "We integrated 80,000 cameras. We have face or live VAHAN. ANPR always reads Paldi. We built Model 3 and 4.",
        body,
    ))
    story.append(Paragraph("Backup media", h))
    story.append(Paragraph(
        "If live RTSP/HLS blips: Gate + Paldi + Visat MP4s. Same Extract / Detect / Hunt pipeline. "
        "Output report and hunt CSV are already generated from the working store.",
        body,
    ))

    out = PACK / "jury-demo-script.pdf"

    def hf(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(NAVY)
        canvas.rect(0, A4[1] - 12 * mm, A4[0], 12 * mm, fill=1, stroke=0)
        canvas.setFillColor(GOLD)
        canvas.rect(0, A4[1] - 12 * mm, 3 * mm, 12 * mm, fill=1, stroke=0)
        canvas.setFillColor(colors.white)
        canvas.setFont("Times-Bold", 8)
        canvas.drawString(14 * mm, A4[1] - 8 * mm, "Keep this page beside the laptop")
        canvas.restoreState()

    doc = SimpleDocTemplate(
        str(out), pagesize=A4,
        leftMargin=14 * mm, rightMargin=14 * mm, topMargin=18 * mm, bottomMargin=14 * mm,
        title="Jury demo script", author="Nikhil",
    )
    doc.build(story, onFirstPage=hf, onLaterPages=hf)
    print("Wrote", out)


if __name__ == "__main__":
    build()
