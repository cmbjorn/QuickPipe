"""Auto-DN suggestion panel, rendered inside a Pipe element."""
from __future__ import annotations

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from . import state
from quickpipe.engine import suggest_dn, SizingCriteria
from quickpipe.engine.elements import inlet_from_dict, ORIENT_SIGN


def _source_fluid():
    inl = inlet_from_dict(state.inlet())
    return inl.fluid, inl.T_C


def _window(tbl, rec):
    """Rows within ±2 sizes of the recommended DN (5 total), so the chart and
    table stay focused on the step-up / step-down trade-off. Falls back to the
    full sweep when there is no recommendation."""
    dns = [r["DN"] for r in tbl]
    if rec in dns:
        i = dns.index(rec)
        return tbl[max(0, i - 2): i + 3]
    return tbl


def _sweep_figure(out):
    """Velocity (left) and ΔP/100m (right) vs DN — with a shaded velocity target
    band, the ΔP limit, and a ▼ marker on the recommended size, so it sits
    visibly bracketed by the next size up and down (FlowBench line-size style)."""
    crit = out["criteria"]
    rec = out["recommended_dn"]
    tbl = _window(out["table"], rec)

    dns = [r["DN"] for r in tbl]
    V = [r["V (m/s)"] for r in tbl]
    dp = [r["ΔP_fric/100m (kPa)"] for r in tbl]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=dns, y=V, name="Velocity (m/s)", mode="lines+markers",
                             line=dict(color="#2563EB", width=2.5),
                             marker=dict(size=7), yaxis="y1"))
    fig.add_trace(go.Scatter(x=dns, y=dp, name="ΔP/100m (kPa)", mode="lines+markers",
                             line=dict(color="#D97706", width=2, dash="dash"),
                             marker=dict(size=6), yaxis="y2"))

    # Velocity target band (between v_min and v_max) — gives the "in / out of
    # band" perspective as you step across sizes.
    fig.add_hrect(y0=crit.v_min, y1=crit.v_max,
                  fillcolor="rgba(37,99,235,0.08)", line_width=0,
                  annotation_text="v target", annotation_position="top left",
                  yref="y1")
    # ΔP/100m limit line.
    fig.add_hline(y=crit.dp_per_100m_max,
                  line=dict(color="#D97706", dash="dot", width=1.5),
                  annotation_text=f"ΔP limit {crit.dp_per_100m_max:.1f} kPa",
                  annotation_position="bottom right", yref="y2")

    # Recommended size marker (vertical line — add_vline can't do categorical x).
    if rec in dns:
        fig.add_shape(type="line", x0=rec, x1=rec, y0=0, y1=1, yref="paper",
                      line=dict(color="#16A34A", dash="dot", width=2))
        fig.add_annotation(x=rec, y=1.02, yref="paper", text=f"▼ {rec}",
                           showarrow=False, yanchor="bottom",
                           font=dict(color="#16A34A", size=12))

    fig.update_layout(
        template="plotly_white", height=300,
        margin=dict(l=50, r=55, t=30, b=40),
        xaxis=dict(title="Pipe size"),
        yaxis=dict(title=dict(text="Velocity (m/s)", font=dict(color="#2563EB"))),
        yaxis2=dict(title=dict(text="ΔP/100m (kPa)", font=dict(color="#D97706")),
                    overlaying="y", side="right"),
        legend=dict(orientation="h", y=1.12, x=0.0, bgcolor="rgba(0,0,0,0)"))
    return fig


def render_suggest_dn(pipe: dict, inlet_p_bara: float) -> None:
    with st.expander("🔎 Suggest DN", expanded=False):
        c1, c2, c3 = st.columns(3)
        v_max = c1.number_input("Max velocity (m/s)", 0.1, 100.0, 3.0, 0.5,
                                key=f"{pipe['id']}_vmax")
        dp_max = c2.number_input("Max ΔP/100m (kPa)", 0.1, 1e4, 50.0, 5.0,
                                 key=f"{pipe['id']}_dpmax")
        v_min = c3.number_input("Min velocity (m/s)", 0.0, 100.0, 0.0, 0.5,
                                key=f"{pipe['id']}_vmin")
        # Auto-compute every run (the sweep is cheap) — no button to press.
        fluid, T_C = _source_fluid()
        crit = SizingCriteria(v_min=v_min, v_max=v_max, dp_per_100m_max=dp_max)
        out = suggest_dn(
            fluid, inlet_p_bara * 1e5, T_C,
            pn_class=pipe.get("pn_class", "PN16"), material=pipe.get("material", "SS316L"),
            lined=pipe.get("lined", False),
            liner_material=pipe.get("liner_material", "PTFE"),
            liner_thickness_mm=pipe.get("liner_thickness_mm", 1.0),
            length_m=pipe.get("length_m", 10.0),
            dz_m=ORIENT_SIGN.get(pipe.get("orientation", "Horizontal"), 0.0)
            * pipe.get("length_m", 10.0),
            fittings_list=pipe.get("fittings_list", []),
            correlation=st.session_state.get(state.K_CORR, "Beggs-Brill"),
            voidage_method=st.session_state.get(state.K_VOID, "Homogeneous"),
            criteria=crit)

        rec = out["recommended_dn"]
        if rec:
            st.success(f"Recommended: **{rec}** (smallest size meeting all criteria)")
            if st.button(f"Apply {rec}", key=f"{pipe['id']}_apply", width="stretch"):
                # The DN selectbox is keyed and already instantiated this run, so
                # we can't set its value now — hand it off and let the editor
                # apply it next run, before the selectbox renders.
                st.session_state[f"qp_pending_dn_{pipe['id']}"] = rec
                st.rerun()
        else:
            st.warning("No DN meets all criteria — relax the limits or split the flow.")
        st.plotly_chart(_sweep_figure(out), use_container_width=True,
                        config={"displayModeBar": False},
                        key=f"{pipe['id']}_sweepfig")
        df = pd.DataFrame(_window(out["table"], rec))
        st.dataframe(df, hide_index=True, use_container_width=True,
                     column_config={
                         "V (m/s)": st.column_config.NumberColumn(format="%.2f"),
                         "V/V_e": st.column_config.NumberColumn(format="%.3f"),
                         "ΔP_fric/100m (kPa)": st.column_config.NumberColumn(format="%.2f"),
                     })
