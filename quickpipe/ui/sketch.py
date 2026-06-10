"""Plotly piping sketch — elevation profile (top) + pressure march (bottom)."""
from __future__ import annotations

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

_NODE_COLOR = {"Inlet": "#16a34a", "Pipe": "#2563EB", "Misc": "#f59e0b"}


def figure(result):
    x = result.sketch_x
    z = result.sketch_z
    P = result.sketch_P
    # Sketch nodes = inlet + each section's outlet (one more than the rows).
    types = ["Inlet"] + [r.type for r in result.rows]
    names = ["Inlet"] + [r.element for r in result.rows]
    colors = [_NODE_COLOR.get(t, "#64748b") for t in types]

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.09,
                        row_heights=[0.5, 0.5],
                        subplot_titles=("Elevation profile", "Pressure march"))

    # Elevation profile
    fig.add_trace(go.Scatter(
        x=x, y=z, mode="lines+markers",
        line=dict(color="#94a3b8", width=3),
        marker=dict(size=13, color=colors, line=dict(color="white", width=1.5)),
        text=[f"{n}<br>{p:.3f} bara" for n, p in zip(names, P)],
        hovertemplate="%{text}<br>x=%{x:.1f} m, z=%{y:.1f} m<extra></extra>",
        showlegend=False), row=1, col=1)

    # Pressure march (staircase)
    fig.add_trace(go.Scatter(
        x=x, y=P, mode="lines+markers", line=dict(color="#2563EB", width=2.5),
        marker=dict(size=7, color=colors),
        hovertemplate="x=%{x:.1f} m<br>P=%{y:.4f} bara<extra></extra>",
        showlegend=False), row=2, col=1)

    fig.update_yaxes(title_text="Elevation (m)", row=1, col=1, gridcolor="#eef2f7")
    fig.update_yaxes(title_text="Pressure (bara)", row=2, col=1, gridcolor="#eef2f7")
    fig.update_xaxes(title_text="Cumulative distance (m)", row=2, col=1, gridcolor="#eef2f7")
    fig.update_layout(template="plotly_white", height=460,
                      margin=dict(l=50, r=20, t=40, b=40),
                      paper_bgcolor="white", plot_bgcolor="white")
    return fig


def render(result) -> None:
    st.plotly_chart(figure(result), width='stretch',
                    config={"displayModeBar": False})
