"""PDF service - printable one-file summary of a billing month.

Renders meter consumption, bill components, redistribution rules, and the
final per-participant computation with the same numbers the web views show.
Uses bundled DejaVu fonts so the peso sign prints correctly.
"""
from __future__ import annotations

import io
import os
from datetime import date
from typing import Any, Dict

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

MONTH_NAMES = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]

METHOD_DESC = {
    "usage": "By usage split",
    "equal": "Split equally",
    "amount": "Custom amounts",
    "percentage": "Custom percentages",
}

ACCENT = colors.HexColor("#416180")
ACCENT_LIGHT = colors.HexColor("#5980a6")
INK = colors.HexColor("#1d1f20")
MUTED = colors.HexColor("#6b6d6f")
HAIRLINE = colors.HexColor("#c9c9cc")
ROW_TINT = colors.HexColor("#f2f5f8")

_FONTS_REGISTERED = False


def _register_fonts() -> None:
    global _FONTS_REGISTERED
    if _FONTS_REGISTERED:
        return
    fonts_dir = os.path.join(os.path.dirname(__file__), "..", "static", "fonts")
    pdfmetrics.registerFont(TTFont("DejaVu", os.path.join(fonts_dir, "DejaVuSans.ttf")))
    pdfmetrics.registerFont(TTFont("DejaVu-Bold", os.path.join(fonts_dir, "DejaVuSans-Bold.ttf")))
    _FONTS_REGISTERED = True


def _php(value: float) -> str:
    return f"₱{value:,.2f}"


def _styles() -> Dict[str, ParagraphStyle]:
    base = dict(fontName="DejaVu", textColor=INK)
    return {
        "brand": ParagraphStyle("brand", fontName="DejaVu-Bold", fontSize=9,
                                textColor=ACCENT_LIGHT, spaceAfter=1,
                                # blueprint kicker: uppercase tracking
                                ),
        "title": ParagraphStyle("title", fontName="DejaVu-Bold", fontSize=22,
                                leading=26, textColor=INK, spaceAfter=3),
        "subtitle": ParagraphStyle("subtitle", fontSize=8, textColor=MUTED, **{k: v for k, v in base.items() if k != "textColor"}),
        "h2": ParagraphStyle("h2", fontName="DejaVu-Bold", fontSize=12,
                             textColor=INK, spaceBefore=14, spaceAfter=5),
        "cell": ParagraphStyle("cell", fontSize=8.5, leading=11, **base),
        "cell_muted": ParagraphStyle("cell_muted", fontName="DejaVu", fontSize=8,
                                     leading=10, textColor=MUTED),
        "note": ParagraphStyle("note", fontSize=7.5, textColor=MUTED,
                               fontName="DejaVu", leading=9),
    }


def _base_table_style(header_rows: int = 1) -> TableStyle:
    return TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "DejaVu"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("FONTNAME", (0, 0), (-1, header_rows - 1), "DejaVu-Bold"),
        ("FONTSIZE", (0, 0), (-1, header_rows - 1), 7.5),
        ("TEXTCOLOR", (0, 0), (-1, header_rows - 1), MUTED),
        ("LINEBELOW", (0, 0), (-1, header_rows - 1), 0.75, HAIRLINE),
        ("LINEBELOW", (0, header_rows), (-1, -2), 0.25, HAIRLINE),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TEXTCOLOR", (0, header_rows), (-1, -1), INK),
    ])


def build_month_pdf(data: Dict[str, Any]) -> bytes:
    """Build the printable month summary. `data` is MonthService.get_month_detail_data output."""
    _register_fonts()
    st = _styles()

    bill = data["bill"]
    participants = data["participants"]
    member_ids = data["member_ids"]
    members = [p for p in participants if p.id in member_ids]
    readings_by_pid = data["readings_by_pid"]
    prev_map = data.get("prev_readings_map") or {}
    components = data.get("components") or []
    contributions = data.get("dynamic_contributions") or []
    comp_adjustments = data.get("comp_adjustments") or {}
    base_maps = data.get("dynamic_base_maps") or {}
    name_by_id = data.get("participant_name_by_id") or {}

    label = f"{MONTH_NAMES[bill.month - 1]} {bill.year}"

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=16 * mm, rightMargin=16 * mm, topMargin=16 * mm, bottomMargin=16 * mm,
        title=f"Bills Online — {label}",
    )
    width = doc.width
    story = []

    # ── header ──
    status = "ARCHIVED" if bill.archived else "CURRENT PERIOD"
    story.append(Paragraph("BILLS ONLINE — SHARED UTILITIES LEDGER", st["brand"]))
    story.append(Paragraph(label, st["title"]))
    story.append(Paragraph(
        f"Billing period summary · {len(members)} participant{'s' if len(members) != 1 else ''} · "
        f"{len(components)} component{'s' if len(components) != 1 else ''} · {status} · "
        f"generated {date.today().isoformat()}", st["subtitle"]))
    story.append(Spacer(1, 4))
    story.append(HRFlowable(width=width, thickness=1, color=ACCENT_LIGHT))

    # ── meter readings ──
    usage_share_base = data.get("usage_share_base") or {}
    usage_split_total = float(data.get("usage_split_total") or 0)
    usage_rate = data.get("usage_rate")
    show_base = usage_split_total > 0

    title = "Meter Readings — Electricity Consumption (kWh)"
    if usage_rate:
        title += f" · {_php(usage_rate)}/kWh"
    story.append(Paragraph(title, st["h2"]))
    if show_base:
        story.append(Paragraph(
            f"Base cost = usage share of the {_php(usage_split_total)} usage-split bill, "
            "before any adjustments or redistribution.", st["note"]))
        story.append(Spacer(1, 3))
    header = ["Participant", "Previous", "Current", "Usage (kWh)"]
    if show_base:
        header.append("Base cost (₱)")
    rows = [header]
    total_usage = 0.0
    for p in members:
        r = readings_by_pid.get(p.id)
        prev = r.reading_previous if r and r.reading_previous is not None else prev_map.get(p.id)
        curr = r.reading_current if r else None
        usage = r.usage() if r else 0.0
        total_usage += usage
        row = [
            p.name,
            f"{prev:,.2f}".rstrip("0").rstrip(".") if prev is not None else "—",
            f"{curr:,.2f}".rstrip("0").rstrip(".") if curr is not None else "—",
            f"{usage:,.2f}",
        ]
        if show_base:
            row.append(f"{usage_share_base.get(p.id, 0.0):,.2f}")
        rows.append(row)
    footer = ["Total usage", "", "", f"{total_usage:,.2f}"]
    if show_base:
        footer.append(f"{usage_split_total:,.2f}")
    rows.append(footer)
    if show_base:
        col_widths = [width * 0.28, width * 0.18, width * 0.18, width * 0.18, width * 0.18]
    else:
        col_widths = [width * 0.34, width * 0.22, width * 0.22, width * 0.22]
    t = Table(rows, colWidths=col_widths)
    style = _base_table_style()
    style.add("ALIGN", (1, 0), (-1, -1), "RIGHT")
    style.add("FONTNAME", (0, -1), (-1, -1), "DejaVu-Bold")
    style.add("TEXTCOLOR", (-1, 1), (-1, -1), ACCENT)
    style.add("LINEABOVE", (0, -1), (-1, -1), 0.75, HAIRLINE)
    t.setStyle(style)
    story.append(t)

    # ── components ──
    story.append(Paragraph("Bill Components", st["h2"]))
    rows = [["Component", "Split method", "Custom shares", "Bill total"]]
    for comp in components:
        dist = comp.distribution or {}
        shares = "—"
        if comp.split_method in ("percentage", "amount") and dist:
            parts = []
            # Percent shares also show the derived peso amount, normalized the
            # same way the calculator splits the bill total.
            total_pct = sum(float(v or 0) for v in dist.values())
            for pid, val in dist.items():
                pname = name_by_id.get(int(str(pid)), str(pid))
                val = float(val or 0)
                if comp.split_method == "percentage":
                    derived = float(comp.amount or 0) * (val / (total_pct if total_pct > 0 else 100.0))
                    parts.append(f"{pname}: {val:,.2f}% ({_php(derived)})")
                else:
                    parts.append(f"{pname}: {_php(val)}")
            shares = ", ".join(parts)
        rows.append([
            comp.name,
            METHOD_DESC.get(comp.split_method, comp.split_method),
            Paragraph(shares, st["cell_muted"]),
            _php(float(comp.amount or 0)),
        ])
    grand = sum(float(c.amount or 0) for c in components)
    rows.append(["Grand total", "", "", _php(grand)])
    t = Table(rows, colWidths=[width * 0.22, width * 0.24, width * 0.34, width * 0.20])
    style = _base_table_style()
    style.add("ALIGN", (-1, 0), (-1, -1), "RIGHT")
    style.add("FONTNAME", (0, -1), (-1, -1), "DejaVu-Bold")
    style.add("LINEABOVE", (0, -1), (-1, -1), 0.75, HAIRLINE)
    t.setStyle(style)
    story.append(t)

    # ── redistribution (entries only) ──
    redis_rows = []
    for comp in components:
        per_comp = comp_adjustments.get(comp.id) or {}
        for p in members:
            adj = per_comp.get(p.id) or {}
            rule = adj.get("rule") or {}
            mode = rule.get("mode")
            if not mode:
                continue
            base = (base_maps.get(comp.id) or {}).get(p.id, 0.0)
            targets = rule.get("targets") or {}
            parts = []
            for tpid, val in targets.items():
                tname = name_by_id.get(int(str(tpid)), str(tpid))
                val = float(val or 0)
                if mode == "percent":
                    parts.append(f"{tname}: {val:.2f}% ({_php(base * val / 100)})")
                else:
                    parts.append(f"{tname}: {_php(val)}")
            redis_rows.append([
                comp.name, p.name, mode.capitalize(),
                Paragraph(", ".join(parts) if parts else "—", st["cell"]),
                Paragraph(adj.get("notes") or "—", st["cell_muted"]),
            ])
    if redis_rows:
        story.append(Paragraph("Advanced Redistribution", st["h2"]))
        rows = [["Component", "Participant", "Mode", "Redistributed to", "Notes"]] + redis_rows
        t = Table(rows, colWidths=[width * 0.14, width * 0.14, width * 0.10, width * 0.38, width * 0.24])
        t.setStyle(_base_table_style())
        story.append(t)

    # ── final computation ──
    story.append(Paragraph("Final Computation — Contributions per Participant", st["h2"]))
    if contributions:
        comp_names = [c.name for c in components]
        header = ["Participant"] + comp_names + ["Total"]
        rows = [header]
        for c in contributions:
            rows.append(
                [c.participant.name]
                + [f"{float(c.components.get(n, 0.0)):,.2f}" for n in comp_names]
                + [_php(float(c.total))]
            )
        rows.append(
            ["Totals"]
            + [f"{float(c.amount or 0):,.2f}" for c in components]
            + [_php(grand)]
        )
        first_w = width * 0.24
        rest_w = (width - first_w) / (len(comp_names) + 1)
        t = Table(rows, colWidths=[first_w] + [rest_w] * (len(comp_names) + 1))
        style = _base_table_style()
        style.add("ALIGN", (1, 0), (-1, -1), "RIGHT")
        style.add("FONTNAME", (0, -1), (-1, -1), "DejaVu-Bold")
        style.add("FONTNAME", (-1, 1), (-1, -1), "DejaVu-Bold")
        style.add("TEXTCOLOR", (-1, 1), (-1, -1), ACCENT)
        style.add("LINEABOVE", (0, -1), (-1, -1), 0.75, HAIRLINE)
        style.add("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, ROW_TINT])
        t.setStyle(style)
        story.append(t)
    else:
        story.append(Paragraph("No components recorded for this month.", st["cell_muted"]))

    story.append(Spacer(1, 10))
    story.append(HRFlowable(width=width, thickness=0.5, color=HAIRLINE))
    story.append(Paragraph(
        "Amounts in Philippine pesos. Contributions include split methods, custom shares and "
        "redistribution rules; columns match the CSV export.", st["note"]))

    doc.build(story)
    return buf.getvalue()
