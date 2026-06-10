"""Sidebar — project metadata, the line list (with status), and solver settings."""
from __future__ import annotations

import streamlit as st

from . import state


def render(results: dict) -> None:
    """results: {line_id: (MarchResult|None, error|None)} for status chips."""
    sb = st.sidebar
    sb.markdown("## 🧭 Quickpipe")
    sb.caption("Line sizing & hydraulics")

    # ── Project metadata ─────────────────────────────────────────────────────
    with sb.expander("📋  Project details", expanded=False):
        m = state.meta()
        m["project_name"] = st.text_input("Project", m.get("project_name", ""), key="meta_proj")
        m["client"] = st.text_input("Client", m.get("client", ""), key="meta_client")
        c1, c2 = st.columns(2)
        m["rev"] = c1.text_input("Rev", m.get("rev", "A"), key="meta_rev")
        m["date"] = c2.text_input("Date", m.get("date", ""), key="meta_date")
        m["calc_by"] = c1.text_input("Calc by", m.get("calc_by", ""), key="meta_calcby")
        m["checked_by"] = c2.text_input("Checked", m.get("checked_by", ""), key="meta_chk")
        m["notes"] = st.text_area("Assumptions / notes", m.get("notes", ""),
                                  key="meta_notes", height=80)

    # ── Line list ────────────────────────────────────────────────────────────
    sb.markdown("#### Lines")
    for ln in state.lines():
        res, err = results.get(ln["id"], (None, None))
        if err or res is None:
            chip = "🔴"
        elif res.warnings:
            chip = "🟠"
        else:
            chip = "🟢"
        is_active = ln["id"] == state.active_id()
        label = f"{chip}  {ln.get('tag') or ln['id']}"
        if sb.button(label, key=f"sel_{ln['id']}", width="stretch",
                     type="primary" if is_active else "secondary"):
            state.set_active(ln["id"])
            st.rerun()
        if is_active and res is not None and not err:
            sb.caption(f"&nbsp;&nbsp;{res.outlet_P_bara:.3f} bara out · "
                       f"ΔP {res.total_dp_kpa:.1f} kPa" +
                       (f" · ⚠ {len(res.warnings)}" if res.warnings else ""),
                       unsafe_allow_html=True)

    b1, b2, b3 = sb.columns(3)
    if b1.button("➕ Add", key="ln_add", width="stretch"):
        state.add_line(); st.rerun()
    if b2.button("⧉ Dup", key="ln_dup", width="stretch"):
        state.duplicate_line(state.active_id()); st.rerun()
    if b3.button("🗑 Del", key="ln_del", width="stretch",
                 disabled=len(state.lines()) <= 1):
        state.delete_line(state.active_id()); st.rerun()

    # ── Save / load project ──────────────────────────────────────────────────
    sb.divider()
    with sb.expander("💾  Save / load project", expanded=False):
        import hashlib
        import json
        meta = state.meta()
        fname = (meta.get("project_name") or "quickpipe_project").strip().replace(" ", "_")
        st.download_button("⬇  Save project (.json)", state.export_project_json(),
                           file_name=f"{fname or 'quickpipe_project'}.json",
                           mime="application/json", width="stretch", key="proj_save")
        up = st.file_uploader("Load project (.json)", type="json", key="proj_uploader")
        if up is not None:
            raw = up.getvalue()
            sig = hashlib.md5(raw).hexdigest()
            if st.session_state.get("proj_load_sig") != sig:
                try:
                    state.import_project(json.loads(raw))
                    st.session_state["proj_load_sig"] = sig
                    st.success("Project loaded.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Could not load: {e}")
        else:
            st.session_state.pop("proj_load_sig", None)

    # ── Solver settings ──────────────────────────────────────────────────────
    sb.divider()
    with sb.expander("⚙  Solver settings", expanded=False):
        st.session_state[state.K_CORR] = st.selectbox(
            "Two-phase correlation", state.CORRELATIONS,
            index=state.CORRELATIONS.index(st.session_state.get(state.K_CORR, "Beggs-Brill")),
            key="solver_corr")
        st.session_state[state.K_VOID] = st.selectbox(
            "Voidage method", state.VOIDAGE_METHODS,
            index=state.VOIDAGE_METHODS.index(st.session_state.get(state.K_VOID, "Homogeneous")),
            key="solver_void")
        st.session_state[state.K_SUBSTEP] = st.checkbox(
            "Sub-step gas pipes (accuracy)", st.session_state.get(state.K_SUBSTEP, False),
            key="solver_substep")
