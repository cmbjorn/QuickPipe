"""Excel export — System summary + Segments table (openpyxl → BytesIO)."""
from __future__ import annotations

from io import BytesIO

import streamlit as st

from quickpipe.engine.results import COLUMNS

_BLUE = "2563EB"
_ALT = "F1F5F9"


def _styles():
    from openpyxl.styles import Font, PatternFill, Border, Side, Alignment
    thin = Side(style="thin", color="CBD5E1")
    return {
        "hdr_font": Font(bold=True, color="FFFFFF", size=10),
        "hdr_fill": PatternFill("solid", fgColor=_BLUE),
        "alt_fill": PatternFill("solid", fgColor=_ALT),
        "border": Border(left=thin, right=thin, top=thin, bottom=thin),
        "center": Alignment(horizontal="center"),
        "label_font": Font(bold=True, size=10),
    }


def build_xlsx(result, meta: dict) -> BytesIO:
    import openpyxl
    from openpyxl.styles import Font
    s = _styles()
    wb = openpyxl.Workbook()

    # ── System sheet ─────────────────────────────────────────────────────────
    ws = wb.active
    ws.title = "System"
    ws.column_dimensions["A"].width = 30
    ws.column_dimensions["B"].width = 28
    ws["A1"] = "Quickpipe — Line Summary"
    ws["A1"].font = Font(bold=True, size=13, color=_BLUE)
    r = 3
    for label, val in [
        ("Correlation", meta.get("correlation", "")),
        ("Voidage method", meta.get("voidage", "")),
        ("Inlet pressure (bara)", round(result.inlet_P_bara, 4)),
        ("Outlet pressure (bara)", round(result.outlet_P_bara, 4)),
        ("Total ΔP (kPa)", round(result.total_dp_kpa, 3)),
        ("Total ΔP (bar)", round(result.total_dp_kpa / 100, 4)),
        ("ΔP friction (kPa)", round(result.total_dp_fric_kpa, 3)),
        ("ΔP elevation/equipment (kPa)", round(result.total_dp_grav_kpa, 3)),
        ("Total length (m)", round(sum(x.l_m for x in result.rows), 2)),
        ("Max V/V_e", round(max((x.v_over_ve for x in result.rows), default=0.0), 3)),
    ]:
        a = ws.cell(r, 1, label); a.font = s["label_font"]; a.border = s["border"]
        b = ws.cell(r, 2, val); b.border = s["border"]
        if r % 2 == 0:
            a.fill = s["alt_fill"]; b.fill = s["alt_fill"]
        r += 1
    if result.warnings:
        r += 1
        ws.cell(r, 1, "Warnings").font = Font(bold=True, color="B45309"); r += 1
        for w in result.warnings:
            ws.cell(r, 1, w); r += 1

    # ── Segments sheet — line-list layout: one column per segment ────────────
    ws2 = wb.create_sheet("Line list")
    ws2.freeze_panes = "B2"
    records = [row.to_dict() for row in result.rows]
    props = [c for c in COLUMNS if c != "Element"]

    # Header row: blank corner + one column per segment (element name).
    corner = ws2.cell(1, 1, "Segment →")
    corner.font = s["hdr_font"]; corner.fill = s["hdr_fill"]; corner.border = s["border"]
    ws2.column_dimensions["A"].width = 20
    for j, rec in enumerate(records, start=2):
        c = ws2.cell(1, j, f"#{j-1}  {rec['Element']}")
        c.font = s["hdr_font"]; c.fill = s["hdr_fill"]; c.border = s["border"]; c.alignment = s["center"]
        ws2.column_dimensions[openpyxl.utils.get_column_letter(j)].width = 16

    # One row per property; first column = property label.
    for i, prop in enumerate(props, start=2):
        lc = ws2.cell(i, 1, prop)
        lc.font = s["label_font"]; lc.border = s["border"]
        if i % 2 == 0:
            lc.fill = s["alt_fill"]
        for j, rec in enumerate(records, start=2):
            c = ws2.cell(i, j, rec[prop])
            c.border = s["border"]
            if i % 2 == 0:
                c.fill = s["alt_fill"]

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


def render(result, meta: dict) -> None:
    if st.button("📊  Generate Excel", key="qp_gen_xl", width="stretch"):
        st.session_state[st_key := "qp_xl_bytes"] = build_xlsx(result, meta).getvalue()
    data = st.session_state.get("qp_xl_bytes")
    if data:
        st.download_button(
            "⬇  Download line.xlsx", data=data, file_name="quickpipe_line.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            width="stretch", key="qp_dl_xl")
