"""Piping long-section sketch — orthogonal routing (like FlowBench).

Each pipe section is drawn as an L: a horizontal run of its length, then a
vertical riser of its Δz — so the line reads like real piping (right angles),
not a diagonal. Line width scales with DN; colour flags erosion (V/V_e).
A pressure-march panel sits underneath, sharing the distance axis.
"""
from __future__ import annotations

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# DN → line width (px), mirrors the FlowBench schematic.
_DN_LW = {"DN20": 2, "DN25": 3, "DN40": 5, "DN50": 7, "DN65": 8, "DN80": 9,
          "DN100": 11, "DN150": 15, "DN200": 19, "DN250": 23}
_MISC_C = "#64748b"


def _v_color(ratio):
    if ratio > 1.0:
        return "#dc2626"      # red — over erosion limit
    if ratio > 0.8:
        return "#f59e0b"      # amber — near limit
    return "#2563EB"          # blue — ok


def figure(result):
    x, z, P = result.sketch_x, result.sketch_z, result.sketch_P
    rows = result.rows

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.10,
                        row_heights=[0.62, 0.38],
                        subplot_titles=("Piping long-section (orthogonal)",
                                        "Pressure march"))

    seen_legend = set()
    for i, row in enumerate(rows):
        x0, z0 = x[i], z[i]
        x1, z1 = x[i + 1], z[i + 1]
        if row.type == "Pipe":
            dn = (row.pipe.split("/")[0] if row.pipe else "DN50")
            lw = _DN_LW.get(dn, 8)
            col = _v_color(row.v_over_ve)
            lbl = "Erosion ⚠" if row.v_over_ve > 1 else ("Near limit" if row.v_over_ve > 0.8 else "Pipe OK")
            # Section is purely horizontal or vertical, so a straight node-to-node
            # line is already orthogonal (no diagonals).
            fig.add_trace(go.Scatter(
                x=[x0, x1], y=[z0, z1], mode="lines",
                line=dict(color=col, width=lw),
                name=lbl, legendgroup=lbl, showlegend=lbl not in seen_legend,
                hovertemplate=(f"<b>#{i+1} {row.element}</b><br>{row.pipe}<br>"
                               f"L={row.l_m:.1f} m · Δz={row.dz_m:+.1f} m<br>"
                               f"ΔP={row.dp_kpa:.2f} kPa · V={row.v_ms:.2f} m/s "
                               f"(V/V_e={row.v_over_ve:.2f})<br>{row.regime}<extra></extra>")))
            seen_legend.add(lbl)
            # Section label at the midpoint.
            fig.add_annotation(
                x=(x0 + x1) / 2, y=(z0 + z1) / 2, text=f"<b>#{i+1}</b> {dn}",
                showarrow=False, font=dict(size=9, color="#1E293B"),
                bgcolor="rgba(255,255,255,0.85)", bordercolor=col, borderwidth=1,
                borderpad=2, yshift=12, row=1, col=1)
        else:
            # Misc / equipment: a riser if it has Δz, plus a diamond marker.
            if abs(z1 - z0) > 1e-9:
                fig.add_trace(go.Scatter(
                    x=[x0, x1], y=[z0, z1], mode="lines",
                    line=dict(color=_MISC_C, width=4, dash="dot"),
                    showlegend=False, hoverinfo="skip"))
            fig.add_trace(go.Scatter(
                x=[x0], y=[(z0 + z1) / 2], mode="markers",
                marker=dict(symbol="diamond", size=13, color=_MISC_C,
                            line=dict(color="white", width=1.5)),
                name="Equipment", legendgroup="Equipment",
                showlegend="Equipment" not in seen_legend,
                hovertemplate=(f"<b>#{i+1} {row.element}</b><br>"
                               f"ΔP={row.dp_kpa:.2f} kPa<extra></extra>")))
            seen_legend.add("Equipment")

    # Inlet / outlet markers.
    fig.add_trace(go.Scatter(
        x=[x[0]], y=[z[0]], mode="markers+text", marker=dict(size=13, color="#16a34a"),
        text=["IN"], textposition="top center", textfont=dict(size=10, color="#16a34a"),
        showlegend=False, hovertemplate=f"Inlet · {P[0]:.3f} bara<extra></extra>"))
    fig.add_trace(go.Scatter(
        x=[x[-1]], y=[z[-1]], mode="markers+text", marker=dict(size=13, color="#dc2626"),
        text=["OUT"], textposition="bottom center", textfont=dict(size=10, color="#dc2626"),
        showlegend=False, hovertemplate=f"Outlet · {P[-1]:.4f} bara<extra></extra>"))

    # Pressure march (step-ish line vs distance).
    fig.add_trace(go.Scatter(
        x=x, y=P, mode="lines+markers", line=dict(color="#2563EB", width=2),
        marker=dict(size=6), showlegend=False,
        hovertemplate="x=%{x:.1f} m · P=%{y:.4f} bara<extra></extra>"), row=2, col=1)

    fig.update_yaxes(title_text="Elevation (m)", row=1, col=1, gridcolor="#eef2f7",
                     zeroline=True, zerolinecolor="#CBD5E1")
    fig.update_yaxes(title_text="Pressure (bara)", row=2, col=1, gridcolor="#eef2f7")
    fig.update_xaxes(title_text="Cumulative distance (m)", row=2, col=1, gridcolor="#eef2f7")
    fig.update_layout(template="plotly_white", height=480,
                      margin=dict(l=55, r=20, t=40, b=40), hovermode="closest",
                      legend=dict(orientation="h", y=1.08, x=0.0, bgcolor="rgba(0,0,0,0)"),
                      paper_bgcolor="white", plot_bgcolor="white")
    return fig


def render(result) -> None:
    st.plotly_chart(figure(result), width='stretch',
                    config={"displayModeBar": False})
