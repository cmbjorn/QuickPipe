"""Auto-DN suggestion panel, rendered inside a Pipe element."""
from __future__ import annotations

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from . import state
from quickpipe.engine import suggest_dn, SizingCriteria
from quickpipe.engine.elements import inlet_from_dict


def _source_fluid():
    inl = inlet_from_dict(state.inlet())
    return inl.fluid, inl.T_C


def _sweep_figure(out):
    """Velocity (left) and ΔP/100m (right) vs DN, with criteria limits and the
    recommended size highlighted — mirrors the classic line-size sweep chart."""
    tbl = out["table"]
    crit = out["criteria"]
    rec = out["recommended_dn"]
    dns = [r["DN"] for r in tbl]
    V = [r["V (m/s)"] for r in tbl]
    dp = [r["ΔP_fric/100m (kPa)"] for r in tbl]
    log_ok = all(v > 0 for v in V) and all(d > 0 for d in dp)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=dns, y=V, name="Velocity", mode="lines+markers",
                             line=dict(color="#2563EB", width=2.5),
                             marker=dict(size=7), yaxis="y1"))
    fig.add_trace(go.Scatter(x=dns, y=dp, name="ΔP/100m", mode="lines+markers",
                             line=dict(color="#D97706", width=2, dash="dash"),
                             marker=dict(size=6), yaxis="y2"))
    # Criteria limit lines (flat traces so each sits on the correct axis)
    fig.add_trace(go.Scatter(x=dns, y=[crit.v_max] * len(dns), name="V max",
                             mode="lines", line=dict(color="#2563EB", width=1, dash="dot"),
                             yaxis="y1", hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=dns, y=[crit.dp_per_100m_max] * len(dns), name="ΔP max",
                             mode="lines", line=dict(color="#D97706", width=1, dash="dot"),
                             yaxis="y2", hoverinfo="skip"))
    if rec in dns:
        i = dns.index(rec)
        fig.add_trace(go.Scatter(x=[rec], y=[V[i]], mode="markers+text",
                                 name="Recommended", text=[f"  {rec}"], textposition="top right",
                                 marker=dict(symbol="star", size=16, color="#16a34a"),
                                 yaxis="y1", hoverinfo="skip"))
    fig.update_layout(
        template="plotly_white", height=300,
        margin=dict(l=50, r=55, t=30, b=40),
        xaxis=dict(title="Nominal diameter"),
        yaxis=dict(title="Velocity (m/s)", color="#2563EB",
                   type="log" if log_ok else "linear"),
        yaxis2=dict(title="ΔP/100m (kPa)", color="#D97706", overlaying="y",
                    side="right", type="log" if log_ok else "linear"),
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
        if st.button("Suggest DN", key=f"{pipe['id']}_suggest", width="stretch"):
            fluid, T_C = _source_fluid()
            crit = SizingCriteria(v_min=v_min, v_max=v_max, dp_per_100m_max=dp_max)
            out = suggest_dn(
                fluid, inlet_p_bara * 1e5, T_C,
                pn=pipe.get("pn", "PN40"), material=pipe.get("material", "SS316L"),
                lined=pipe.get("lined", False),
                liner_material=pipe.get("liner_material", "PTFE"),
                liner_thickness_mm=pipe.get("liner_thickness_mm", 1.0),
                length_m=pipe.get("length_m", 10.0), dz_m=pipe.get("dz_m", 0.0),
                fittings_list=pipe.get("fittings_list", []),
                correlation=st.session_state.get(state.K_CORR, "Beggs-Brill"),
                voidage_method=st.session_state.get(state.K_VOID, "Homogeneous"),
                criteria=crit)
            st.session_state[f"{pipe['id']}_suggest_out"] = out

        out = st.session_state.get(f"{pipe['id']}_suggest_out")
        if out:
            rec = out["recommended_dn"]
            if rec:
                st.success(f"Recommended: **{rec}** (smallest size meeting all criteria)")
                if st.button(f"Apply {rec}", key=f"{pipe['id']}_apply", width="stretch"):
                    # The DN selectbox is keyed and already instantiated this run,
                    # so we can't set its value now — hand it off and let the
                    # editor apply it next run, before the selectbox renders.
                    st.session_state[f"qp_pending_dn_{pipe['id']}"] = rec
                    st.session_state.pop(f"{pipe['id']}_suggest_out", None)
                    st.rerun()
            else:
                st.warning("No DN meets all criteria — relax the limits or split the flow.")
            st.plotly_chart(_sweep_figure(out), width="stretch",
                            config={"displayModeBar": False},
                            key=f"{pipe['id']}_sweepfig")
            df = pd.DataFrame(out["table"])
            st.dataframe(df, hide_index=True, width="stretch",
                         column_config={
                             "V (m/s)": st.column_config.NumberColumn(format="%.2f"),
                             "V/V_e": st.column_config.NumberColumn(format="%.3f"),
                             "ΔP_fric/100m (kPa)": st.column_config.NumberColumn(format="%.2f"),
                         })
