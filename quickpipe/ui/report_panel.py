"""Export panel — Word hydraulic report (this line / whole project) + Excel."""
from __future__ import annotations

import streamlit as st

from . import state, excel
from quickpipe.engine.report import build_report

_DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def _slug(s, default):
    s = (s or "").strip().replace(" ", "_")
    return "".join(ch for ch in s if ch.isalnum() or ch in "._-") or default


def render(active_line, active_result, all_results: dict) -> None:
    meta = state.meta()
    solver_meta = {"correlation": st.session_state.get(state.K_CORR, "Beggs-Brill"),
                   "voidage": st.session_state.get(state.K_VOID, "Homogeneous")}

    st.markdown("**Word hydraulic report**")
    c1, c2 = st.columns(2)
    if c1.button("📄  This line", width="stretch", key="rep_line"):
        if active_result is not None:
            st.session_state["rep_bytes_line"] = build_report(
                meta, [(active_line, active_result)], solver_meta, single=True).getvalue()
    if st.session_state.get("rep_bytes_line"):
        c1.download_button(
            "⬇  Download line report", st.session_state["rep_bytes_line"],
            file_name=f"{_slug(active_line.get('tag'), 'line')}_hydraulic.docx",
            mime=_DOCX, width="stretch", key="rep_dl_line")

    if c2.button("📑  Whole project", width="stretch", key="rep_proj"):
        lr = []
        for ln in state.lines():
            res, err = all_results.get(ln["id"], (None, None))
            if res is not None and not err:
                lr.append((ln, res))
        if lr:
            st.session_state["rep_bytes_proj"] = build_report(
                meta, lr, solver_meta, single=False).getvalue()
    if st.session_state.get("rep_bytes_proj"):
        c2.download_button(
            "⬇  Download project report", st.session_state["rep_bytes_proj"],
            file_name=f"{_slug(meta.get('project_name'), 'project')}_hydraulic.docx",
            mime=_DOCX, width="stretch", key="rep_dl_proj")

    st.markdown("**Excel line list (this line)**")
    excel.render(active_result, solver_meta)
