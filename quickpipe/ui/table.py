"""Right column — live results table + summary metrics + warnings."""
from __future__ import annotations

import streamlit as st
import pandas as pd

from quickpipe.engine.results import COLUMNS


def render(result, line: dict | None = None) -> None:
    tag = (line or {}).get("tag", "")
    svc = (line or {}).get("service", "")
    label = tag or "Results"
    if svc:
        label += f"  ·  {svc}"
    st.subheader(label)

    # Line-list layout: one COLUMN per segment, properties as rows.
    records = [r.to_dict() for r in result.rows]
    props = [c for c in COLUMNS if c != "Element"]
    col_labels = [f"#{i+1}  {rec['Element']}" for i, rec in enumerate(records)]

    raw = pd.DataFrame(
        {col_labels[i]: [records[i][p] for p in props] for i in range(len(records))},
        index=props)

    disp = raw.copy()
    for p in props:
        f = _FMT.get(p)
        if f:
            disp.loc[p] = [f % v if isinstance(v, (int, float)) else v for v in raw.loc[p]]

    def _style(_df):
        styles = pd.DataFrame("", index=_df.index, columns=_df.columns)
        # Headline numbers: total ΔP and velocity in bold across all segments.
        for rowname in ("ΔP (kPa)", "V (m/s)"):
            if rowname in styles.index:
                styles.loc[rowname] = "font-weight:bold"
        if "V/V_e" in raw.index:
            for c in raw.columns:
                try:
                    v = float(raw.loc["V/V_e", c])
                except (TypeError, ValueError):
                    continue
                if v > 1.0:
                    styles.loc["V/V_e", c] = "background-color:#fee2e2;font-weight:bold"
                elif v > 0.8:
                    styles.loc["V/V_e", c] = "background-color:#fef3c7"
        return styles

    try:
        styled = disp.style.apply(_style, axis=None)
    except Exception:
        styled = disp          # fall back to unstyled if Styler fails
    st.dataframe(styled, use_container_width=True,
                 height=min(1100, 60 + 36 * len(props)))
    st.caption("Each column is a segment (line-list format). Flow (m³/h) is in-situ "
               "(actual at local pressure). Red V/V_e > 1 (erosion), amber > 0.8.")

    for w in result.warnings:
        st.warning(w)


# Per-property display formats — one decimal throughout (strings pass through).
_FMT = {
    "ID (mm)": "%.1f", "L (m)": "%.1f", "L_eff (m)": "%.1f", "Δz (m)": "%.1f",
    "Flow (kg/h)": "%.1f", "Flow (m³/h)": "%.1f",
    "P_in (bara)": "%.1f", "P_out (bara)": "%.1f",
    "ΔP_fric (kPa)": "%.1f", "ΔP_fit (kPa)": "%.1f", "ΔP_grav (kPa)": "%.1f", "ΔP (kPa)": "%.1f",
    "V (m/s)": "%.1f", "V/V_e": "%.1f",
}
