"""On-screen project line-list overview (all lines, key results, click to open)."""
from __future__ import annotations

import streamlit as st
import pandas as pd

from . import state


def _row(ln, res, err):
    if res is None or err:
        return {"Tag": ln.get("tag") or ln["id"], "Service": ln.get("service", ""),
                "Fluid": "—", "Flow (kg/h)": None, "Inlet (bara)": None,
                "Outlet (bara)": None, "ΔP (kPa)": None, "Max V (m/s)": None,
                "V/V_e": None, "Status": "🔴 error"}
    pipes = [r for r in res.rows if r.type == "Pipe"]
    r0 = res.rows[0] if res.rows else None
    return {
        "Tag": ln.get("tag") or ln["id"],
        "Service": ln.get("service", ""),
        "Fluid": r0.fluid if r0 else "—",
        "Flow (kg/h)": round(r0.flow_kgh, 1) if r0 else None,
        "Inlet (bara)": round(res.inlet_P_bara, 3),
        "Outlet (bara)": round(res.outlet_P_bara, 3),
        "ΔP (kPa)": round(res.total_dp_kpa, 2),
        "Max V (m/s)": round(max((r.v_ms for r in pipes), default=0.0), 2),
        "V/V_e": round(max((r.v_over_ve for r in pipes), default=0.0), 3),
        "Status": "🟠 review" if res.warnings else "🟢 OK",
    }


def render(all_results: dict) -> None:
    lns = state.lines()
    df = pd.DataFrame([_row(ln, *all_results.get(ln["id"], (None, None))) for ln in lns])

    active_idx = next((i for i, ln in enumerate(lns) if ln["id"] == state.active_id()), 0)
    ev = st.dataframe(
        df, hide_index=True, use_container_width=True,
        on_select="rerun", selection_mode="single-row", key="qp_overview",
        column_config={
            "Inlet (bara)": st.column_config.NumberColumn(format="%.3f"),
            "Outlet (bara)": st.column_config.NumberColumn(format="%.3f"),
            "ΔP (kPa)": st.column_config.NumberColumn(format="%.2f"),
            "V/V_e": st.column_config.NumberColumn(format="%.3f"),
        })
    st.caption("Click a row to open that line. 🟢 OK · 🟠 review (warnings) · 🔴 error.")

    sel = getattr(ev, "selection", None)
    rows = (sel or {}).get("rows", []) if isinstance(sel, dict) else getattr(sel, "rows", [])
    if rows and rows[0] != active_idx:
        state.set_active(lns[rows[0]]["id"])
        st.rerun()
