"""Quickpipe — line-sizing / hydraulic tool (Streamlit UI).

Run:  python launch.py   (or)   streamlit run quickpipe_app.py --server.port 8502
"""
from __future__ import annotations

import streamlit as st

st.set_page_config(page_title="Quickpipe — Line Sizing", page_icon="🧭",
                   layout="wide", initial_sidebar_state="expanded")

from quickpipe.engine import march                                          # noqa: E402
from quickpipe.ui import (state, sidebar, editor, table, sketch,            # noqa: E402
                          report_panel, overview)

_CSS = """
<style>
.block-container { padding-top: 2.2rem; padding-bottom: 2rem; }
h1, h2, h3 { color: #0F172A; letter-spacing: -0.01em; }
[data-testid="stSidebar"] { background: #F8FAFC; border-right: 1px solid #E2E8F0; }
[data-testid="stSidebar"] .stButton button { font-size: 0.86rem; padding: 0.3rem 0.6rem; }
[data-testid="stMarkdownContainer"] p { color: #1E293B; }
[data-testid="stCaptionContainer"] p { color: #64748B; }
hr { margin: 0.6rem 0; }
.qp-tagline { color:#64748B; font-size:0.9rem; margin-top:-0.4rem; }
.qp-status-ok   { color:#16a34a; font-weight:600; }
.qp-status-warn { color:#b45309; font-weight:600; }
</style>
"""


def _safe_march(line):
    try:
        return march(line["inlet"], line["sections"],
                     correlation=st.session_state.get(state.K_CORR, "Beggs-Brill"),
                     voidage_method=st.session_state.get(state.K_VOID, "Homogeneous"),
                     substep_gas=st.session_state.get(state.K_SUBSTEP, False)), None
    except Exception as e:
        return None, e


def main():
    state.init_state()
    st.markdown(_CSS, unsafe_allow_html=True)

    # March every line (cheap) for sidebar status + project report.
    all_results = {ln["id"]: _safe_march(ln) for ln in state.lines()}

    active = state.active_line()
    pre_result, _ = all_results.get(active["id"], (None, None))

    # ── Header ───────────────────────────────────────────────────────────────
    proj = state.meta().get("project_name") or "Untitled project"
    tag = active.get("tag") or active["id"]
    svc = active.get("service") or ""
    st.markdown(f"### {tag}" + (f"  ·  {svc}" if svc else ""))
    st.markdown(f"<div class='qp-tagline'>{proj} — Rev {state.meta().get('rev','')} "
                f"· {len(state.lines())} line(s)</div>", unsafe_allow_html=True)
    st.divider()

    # Project overview slot at the top — filled after the active line re-marches
    # so its row is fresh.
    overview_slot = st.container()

    # ── Body ─────────────────────────────────────────────────────────────────
    col_ed, col_res = st.columns([10, 11], gap="large")
    with col_ed:
        editor.render(pre_result)

    # Re-march the active line AFTER edits so the table reflects them with no lag.
    result, err = _safe_march(active)
    all_results[active["id"]] = (result, err)

    with overview_slot:
        if len(state.lines()) > 1:
            with st.expander(f"📋  Project line list — {len(state.lines())} lines", expanded=True):
                overview.render(all_results)

    with col_res:
        if err is not None:
            st.error(f"Calculation error: {err}")
        elif result is not None:
            table.render(result)
            with st.expander("Sketch", expanded=False):
                sketch.render(result)
            with st.expander("Export & report", expanded=True):
                report_panel.render(active, result, all_results)

    # Sidebar last, so the active line's status chip is fresh.
    sidebar.render(all_results)


if __name__ == "__main__":
    main()
