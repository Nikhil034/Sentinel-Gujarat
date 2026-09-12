"""Printable coverage gap analysis for Gujarat Police (A4 PDF)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    Flowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

NAVY = colors.HexColor("#1B3A5C")
GOLD = colors.HexColor("#D4A843")
LINE = colors.HexColor("#C5D0DC")
MUTED = colors.HexColor("#4A5A6A")
INK = colors.HexColor("#1E2D3D")
SILENT = colors.HexColor("#3D7EBB")
WARN = colors.HexColor("#C45C26")
OK = colors.HexColor("#2E7D4F")
_IST = timezone(timedelta(hours=5, minutes=30))


def _styles():
    return {
        "title": ParagraphStyle(
            "title", fontName="Times-Bold", fontSize=16, leading=20,
            textColor=NAVY, alignment=TA_LEFT, spaceAfter=2,
        ),
        "sub": ParagraphStyle(
            "sub", fontName="Times-Italic", fontSize=9, leading=12,
            textColor=MUTED, spaceAfter=8,
        ),
        "h": ParagraphStyle(
            "h", fontName="Times-Bold", fontSize=11, leading=14,
            textColor=NAVY, spaceBefore=10, spaceAfter=4,
        ),
        "body": ParagraphStyle(
            "body", fontName="Times-Roman", fontSize=9, leading=12, textColor=INK,
        ),
        "small": ParagraphStyle(
            "small", fontName="Times-Roman", fontSize=8, leading=10.5, textColor=MUTED,
        ),
        "cell": ParagraphStyle(
            "cell", fontName="Times-Roman", fontSize=8, leading=10.5, textColor=INK,
        ),
        "head": ParagraphStyle(
            "head", fontName="Times-Bold", fontSize=8, leading=10.5, textColor=colors.white,
        ),
        "kpi_n": ParagraphStyle(
            "kpi_n", fontName="Times-Bold", fontSize=16, leading=18,
            textColor=colors.white, alignment=TA_CENTER,
        ),
        "kpi_l": ParagraphStyle(
            "kpi_l", fontName="Times-Roman", fontSize=7.5, leading=10,
            textColor=colors.HexColor("#D7E4F0"), alignment=TA_CENTER,
        ),
    }


class HBarChart(Flowable):
    """Horizontal bars — city or department camera counts."""

    def __init__(self, items: list[tuple[str, int]], width: float, row_h: float = 16, label_w: float = 118):
        super().__init__()
        self.items = items
        self.chart_width = width
        self.row_h = row_h
        self.label_w = label_w
        self._h = max(1, len(items)) * row_h + 2

    def wrap(self, availWidth, availHeight):
        self.width = min(self.chart_width, availWidth)
        self.height = self._h
        return self.width, self.height

    def draw(self):
        canvas = self.canv
        max_v = max((v for _, v in self.items), default=1) or 1
        bar_max = max(20, self.width - self.label_w - 28)
        y = self.height - self.row_h
        for label, value in self.items:
            canvas.setFillColor(INK)
            canvas.setFont("Times-Roman", 8)
            canvas.drawString(0, y + 4, str(label)[:30])
            canvas.setFillColor(colors.HexColor("#E8EEF4"))
            canvas.roundRect(self.label_w, y + 2, bar_max, 11, 2, fill=1, stroke=0)
            width = bar_max * (value / max_v)
            canvas.setFillColor(NAVY)
            if width > 0:
                canvas.roundRect(self.label_w, y + 2, max(3, width), 11, 2, fill=1, stroke=0)
            canvas.setFont("Times-Bold", 8)
            canvas.drawRightString(self.width, y + 4, str(value))
            y -= self.row_h


def _tbl(rows, col_widths, header=True):
    table = Table(rows, colWidths=col_widths, repeatRows=1 if header else 0)
    cmds = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("GRID", (0, 0), (-1, -1), 0.4, LINE),
    ]
    if header:
        cmds += [("BACKGROUND", (0, 0), (-1, 0), NAVY)]
    table.setStyle(TableStyle(cmds))
    return table


def _header_footer(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(NAVY)
    canvas.rect(0, A4[1] - 14 * mm, A4[0], 14 * mm, fill=1, stroke=0)
    canvas.setFillColor(GOLD)
    canvas.rect(0, A4[1] - 14 * mm, 4 * mm, 14 * mm, fill=1, stroke=0)
    canvas.setFillColor(colors.white)
    canvas.setFont("Times-Bold", 9)
    canvas.drawString(16 * mm, A4[1] - 9 * mm, "Sentinel Command  ·  Coverage gap analysis")
    canvas.setFont("Times-Roman", 8)
    canvas.drawRightString(A4[0] - 14 * mm, A4[1] - 9 * mm, "Gujarat Police Innovation Challenge 2026")
    canvas.setFillColor(NAVY)
    canvas.rect(0, 0, A4[0], 12 * mm, fill=1, stroke=0)
    canvas.setFillColor(colors.white)
    canvas.setFont("Times-Roman", 8)
    canvas.drawString(16 * mm, 5 * mm, "Hybrid Model 1 + 2  ·  GIS registry, ANPR metadata, daily CSV logs")
    canvas.drawRightString(A4[0] - 14 * mm, 5 * mm, f"Page {doc.page}")
    canvas.restoreState()


def _kpi_box(n, label, fill, st):
    inner = Table(
        [[Paragraph(str(n), st["kpi_n"])], [Paragraph(label, st["kpi_l"])]],
        colWidths=[28 * mm],
    )
    inner.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), fill),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return inner


def build_gap_pdf(path: Path | None = None) -> bytes:
    """Return PDF bytes; optionally write to path."""
    from reports import anpr_index, today_ist
    from store import gap_report

    gap = gap_report()
    plates = anpr_index()
    st = _styles()
    cell, head = st["cell"], st["head"]
    generated = datetime.now(_IST).strftime("%d %b %Y %H:%M IST")

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        topMargin=20 * mm,
        bottomMargin=16 * mm,
        title="Sentinel Command — Coverage gap analysis",
        author="Sentinel Command",
    )
    usable = A4[0] - 32 * mm
    story = [
        Paragraph("Coverage gap analysis for Gujarat Police", st["title"]),
        Paragraph(
            f"Generated {generated} · IST date {today_ist()} · "
            "Sandbox catalogue (~30 official cameras), not the statewide ~80,000 target.",
            st["sub"],
        ),
    ]

    kpis = Table(
        [
            [
                _kpi_box(gap["total"], "cameras registered", NAVY, st),
                _kpi_box(gap["official_grid"], "official grid", NAVY, st),
                _kpi_box(gap["own_recorded"], "own-feed clips", OK, st),
                _kpi_box(len(gap.get("silent") or []), "silent (no Detect)", SILENT, st),
                _kpi_box(len(gap.get("unlocated") or []), "unlocated pins", GOLD, st),
                _kpi_box(len(gap.get("no_anpr") or []), "vehicles, no plate", WARN, st),
            ]
        ],
        colWidths=[usable / 6.0] * 6,
    )
    kpis.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
    ]))
    story += [kpis, Spacer(1, 8)]
    story.append(Paragraph(gap.get("note") or "", st["body"]))

    city_items = list((gap.get("by_city") or {}).items())
    dept_items = list((gap.get("by_department") or {}).items())
    story.append(Paragraph("Cameras by city", st["h"]))
    if city_items:
        story.append(HBarChart(city_items, usable))
    story.append(Paragraph("Cameras by department", st["h"]))
    if dept_items:
        story.append(HBarChart(dept_items, usable, label_w=158))

    def name_table(title, rows, headers, widths, empty):
        story.append(Paragraph(title, st["h"]))
        if not rows:
            story.append(Paragraph(empty, st["small"]))
            return
        data = [[Paragraph(h, head) for h in headers]]
        for row in rows:
            data.append([Paragraph(str(v if v is not None else "—"), cell) for v in row])
        story.append(_tbl(data, widths))

    name_table(
        "Silent cameras — registered, no Detect events yet",
        [
            (r.get("name"), r.get("id"), r.get("city") or "—")
            for r in (gap.get("silent") or [])
        ],
        ["Camera", "Id", "City"],
        [usable * 0.5, usable * 0.25, usable * 0.25],
        "None — every camera has at least one event.",
    )
    name_table(
        "Unlocated pins — Gujarat centroid until official lat/lng exist",
        [
            (r.get("name"), r.get("id"), r.get("location") or "—")
            for r in (gap.get("unlocated") or [])
        ],
        ["Camera", "Id", "Location text"],
        [usable * 0.4, usable * 0.25, usable * 0.35],
        "None — every camera has a real coordinate.",
    )
    name_table(
        "No-ANPR cameras — vehicles seen, plate unread",
        [
            (r.get("name"), r.get("id"), f"{r.get('events') or 0} vehicles")
            for r in (gap.get("no_anpr") or [])
        ],
        ["Camera", "Id", "Detail"],
        [usable * 0.5, usable * 0.25, usable * 0.25],
        "None — every camera with vehicles has at least one plate read.",
    )

    story.append(Paragraph("ANPR metadata (unique plates)", st["h"]))
    plate_rows = (plates.get("plates") or [])[:12]
    if plate_rows:
        data = [[Paragraph(h, head) for h in ["Plate", "Hits", "Cameras", "Watchlist", "First seen"]]]
        for p in plate_rows:
            data.append(
                [
                    Paragraph(p.get("plate") or "", cell),
                    Paragraph(str(p.get("hit_count") or 0), cell),
                    Paragraph(str(len(p.get("cameras") or [])), cell),
                    Paragraph("YES" if p.get("watchlist") else "—", cell),
                    Paragraph((p.get("first_seen") or "")[:19], cell),
                ]
            )
        story.append(_tbl(data, [usable * 0.28, usable * 0.12, usable * 0.14, usable * 0.16, usable * 0.30]))
        story.append(Paragraph(f"{plates.get('count') or 0} unique plates in the index.", st["small"]))
    else:
        story.append(Paragraph("No plates read yet.", st["small"]))

    story.append(Paragraph("What this report is — and is not", st["h"]))
    story.append(
        Paragraph(
            "This sheet is a <b>coverage and metadata</b> view for Control Room / GIS staff: "
            "which cameras are on the map, which are silent, which lack coordinates, and which "
            "plates the ANPR index has seen. It is <b>not</b> a 24-hour video archive. "
            "Keep the daily CSV logs. Keep a short window of annotated JPEGs. "
            "Departmental NVRs remain the video store. Statewide scale is a GIS + metadata "
            "problem first; the sandbox only publishes about 30 official cameras.",
            st["body"],
        )
    )
    story.append(Spacer(1, 6))
    story.append(
        Paragraph(
            "Map legend in the live UI: green = online, red = offline, gold = unlocated, "
            "blue = silent (no Detect yet).",
            st["small"],
        )
    )

    doc.build(story, onFirstPage=_header_footer, onLaterPages=_header_footer)
    pdf = buf.getvalue()
    if path:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_bytes(pdf)
    return pdf
