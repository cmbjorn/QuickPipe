"""Right column — live results table + summary metrics + warnings."""
from __future__ import annotations

import streamlit as st
import pandas as pd

from quickpipe.engine.results import COLUMNS


def render(result) -> None:
    st.subheader("Results")

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

    st.dataframe(disp.style.apply(_style, axis=None), width="stretch",
                 height=min(720, 60 + 36 * len(props)))
    st.caption("Each column is a segment (line-list format). Flow (m³/h) is in-situ "
               "(actual at local pressure). Red V/V_e > 1 (erosion), amber > 0.8.")

    for w in result.warnings:
        st.warning(w)


# Per-property display formats (strings pass through unformatted).
_FMT = {
    "ID (mm)": "%.1f", "L (m)": "%.1f", "L_eff (m)": "%.2f", "Δz (m)": "%.1f",
    "Flow (kg/h)": "%.1f", "Flow (m³/h)": "%.2f",
    "P_in (bara)": "%.4f", "P_out (bara)": "%.4f",
    "ΔP_fric (kPa)": "%.3f", "ΔP_grav (kPa)": "%.3f", "ΔP (kPa)": "%.3f",
    "V (m/s)": "%.3f", "V_e (m/s)": "%.2f", "V/V_e": "%.3f",
}
