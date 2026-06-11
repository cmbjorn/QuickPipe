"""Flow regime maps for two-phase sections.

Reuses FlowBench's Taitel-Dukler + Mandhane-Gregory-Aziz classification
(horizontal) and Wallis + void-fraction thresholds (vertical upflow).
"""
from __future__ import annotations

import numpy as np
import plotly.graph_objects as go

from fluids.two_phase import (
    Taitel_Dukler_regime as _TD_regime,
    Mandhane_Gregory_Aziz_regime as _MGA_regime)

G = 9.80665

_REGIME_COLORS = {
    "bubble": "#10b981",
    "slug": "#f59e0b",
    "churn": "#ef4444",
    "annular": "#8b5cf6",
    "mist": "#6366f1",
    "mist / annular": "#6366f1",
    "intermittent": "#f97316",
    "stratified": "#06b6d4",
    "wavy": "#14b8a6",
}

_REGIME_LINE_KW = [
    ("bubble", _REGIME_COLORS["bubble"]),
    ("slug", _REGIME_COLORS["slug"]),
    ("churn", _REGIME_COLORS["churn"]),
    ("intermittent", _REGIME_COLORS["intermittent"]),
    ("annular", _REGIME_COLORS["annular"]),
    ("stratified", _REGIME_COLORS["stratified"]),
    ("wavy", _REGIME_COLORS["wavy"]),
]


def _regime_color(regime_str: str, kw_list: list, default: str) -> str:
    for k, v in kw_list:
        if k.lower() in regime_str.lower():
            return v
    return default


def compute_regime_grid(
    rhol: float, rhog: float, mul: float, mug: float,
    sigma: float, D: float, roughness: float, use_horiz: bool,
) -> tuple:
    """Sweep a 50×50 log-log V_sl × V_sg grid and classify each cell.

    Returns (td_grid, full_grid, vsl_list, vsg_list) — all plain Python
    lists so Streamlit can cache them cleanly.
    """
    N = 50
    vsl_arr = np.logspace(-3, 1, N)   # V_sl: 0.001 → 10 m/s
    vsg_arr = np.logspace(-3, 2, N)   # V_sg: 0.001 → 100 m/s
    A = np.pi / 4 * D ** 2

    td_grid = [[""] * N for _ in range(N)]
    full_grid = [[""] * N for _ in range(N)]

    if use_horiz:
        for i, vsg in enumerate(vsg_arr):
            for j, vsl in enumerate(vsl_arr):
                ml = vsl * rhol * A
                mg = vsg * rhog * A
                m = ml + mg
                x = mg / m if m > 0 else 0.0
                try:
                    td = _TD_regime(m=m, x=x, rhol=rhol, rhog=rhog,
                                    mul=mul, mug=mug, D=D,
                                    angle=0.0, roughness=roughness)[0]
                    mga = _MGA_regime(m=m, x=x, rhol=rhol, rhog=rhog,
                                      mul=mul, mug=mug, sigma=sigma, D=D)[0]
                    td_grid[i][j] = td
                    full_grid[i][j] = f"{td} / {mga}"
                except Exception:
                    td_grid[i][j] = "intermittent"
                    full_grid[i][j] = "intermittent / slug"
    else:
        # Vertical upflow: Wallis annular onset + homogeneous void fraction
        try:
            V_ann = 3.1 * (G * sigma * (rhol - rhog) / rhog ** 2) ** 0.25
        except Exception:
            V_ann = 1e9
        for i, vsg in enumerate(vsg_arr):
            for j, vsl in enumerate(vsl_arr):
                mg = vsg * rhog * A
                ml = vsl * rhol * A
                m = ml + mg
                x = mg / m if m > 0 else 0.0
                alpha_h = vsg / (vsg + vsl) if (vsg + vsl) > 0 else 0.0
                if x > 0.90:
                    reg = "mist / annular"
                elif vsg >= V_ann:
                    reg = "annular"
                elif alpha_h >= 0.52:
                    reg = "churn"
                elif alpha_h >= 0.25:
                    reg = "slug"
                else:
                    reg = "bubble"
                td_grid[i][j] = reg
                full_grid[i][j] = reg

    return td_grid, full_grid, vsl_arr.tolist(), vsg_arr.tolist()


def build_regime_figure(
    td_grid: list, full_grid: list, vsl_arr: list, vsg_arr: list,
    op_records: list, title: str
) -> go.Figure:
    """Build a flow-regime map figure with operating points overlay.

    Args:
        td_grid / full_grid: 2-D lists from compute_regime_grid
        vsl_arr / vsg_arr: velocity grids (linear values)
        op_records: list of dicts with 'V_sg (m/s)', 'V_sl (m/s)', 'Regime' keys
        title: chart title
    """
    _log_vsl = np.log10(vsl_arr)
    _log_vsg = np.log10(vsg_arr)

    _all_regs = sorted(set(r for row in td_grid for r in row if r))
    _reg_to_idx = {r: i for i, r in enumerate(_all_regs)}
    _idx_to_col = [_regime_color(r, _REGIME_LINE_KW, "#94A3B8") for r in _all_regs]
    _n_reg = len(_all_regs)

    _z = [[_reg_to_idx.get(td_grid[i][j], 0) for j in range(len(vsl_arr))]
          for i in range(len(vsg_arr))]

    _cs = []
    for _ci, _cc in enumerate(_idx_to_col):
        _cs.extend([[_ci / _n_reg, _cc], [(_ci + 1) / _n_reg, _cc]])

    fig = go.Figure()
    fig.add_trace(go.Heatmap(
        x=list(_log_vsl), y=list(_log_vsg), z=_z,
        text=full_grid,
        colorscale=_cs,
        zmin=0, zmax=_n_reg,
        showscale=False,
        opacity=0.25,
        hovertemplate="Regime: %{text}<extra></extra>",
    ))

    # Zone labels at each regime's log-space centroid
    _zone_acc = {}
    for _gi, _row in enumerate(td_grid):
        for _gj, _reg in enumerate(_row):
            if not _reg:
                continue
            if _reg not in _zone_acc:
                _zone_acc[_reg] = [0.0, 0.0, 0]
            _zone_acc[_reg][0] += float(_log_vsl[_gj])
            _zone_acc[_reg][1] += float(_log_vsg[_gi])
            _zone_acc[_reg][2] += 1

    for _zreg, (_svsl, _svsg, _cnt) in _zone_acc.items():
        if _cnt == 0:
            continue
        fig.add_annotation(
            x=_svsl / _cnt, y=_svsg / _cnt,
            xref="x", yref="y",
            text=f"<b>{_zreg}</b>",
            showarrow=False,
            font=dict(size=8, color="#1E293B"),
            bgcolor="rgba(255,255,255,0.55)",
            borderpad=2,
        )

    # Operating points — cluster identical (V_sl, V_sg) positions
    _op_clusters = {}
    for _r in op_records:
        _vsg_r = max(float(_r.get("V_sg (m/s)", 1e-4)), 1e-4)
        _vsl_r = max(float(_r.get("V_sl (m/s)", 1e-4)), 1e-4)
        _ck = (round(np.log10(_vsl_r), 2), round(np.log10(_vsg_r), 2))
        _op_clusters.setdefault(_ck, []).append(_r)

    _seen_reg_map = set()
    for _cgroup in _op_clusters.values():
        _vsl_c = float(np.mean([max(r.get("V_sl (m/s)", 1e-4), 1e-4) for r in _cgroup]))
        _vsg_c = float(np.mean([max(r.get("V_sg (m/s)", 1e-4), 1e-4) for r in _cgroup]))
        _reg_list = [r.get("Regime", "unknown") for r in _cgroup]
        _reg = max(set(_reg_list), key=_reg_list.count)
        _col = _regime_color(_reg, _REGIME_LINE_KW, "#64748B")
        _n_c = len(_cgroup)
        _lbl = ", ".join(str(r.get("Element", "")) for r in _cgroup)
        _fsz = max(6, 9 - (_n_c - 1) * 2)
        _msz = 16 + (_n_c - 1) * 4
        _show_leg = _reg not in _seen_reg_map
        _seen_reg_map.add(_reg)
        fig.add_trace(go.Scatter(
            x=[np.log10(_vsl_c)], y=[np.log10(_vsg_c)], mode="markers",
            marker=dict(size=_msz, color=_col,
                        line=dict(color="white", width=2)),
            name=_reg, legendgroup=_reg, showlegend=_show_leg,
            hovertemplate=f"<b>{_lbl}</b><br>V_sl={_vsl_c:.2f} m/s, V_sg={_vsg_c:.2f} m/s<extra></extra>",
        ))

    fig.update_layout(
        template="plotly_white", title=title,
        xaxis_title="V_sl (m/s) — log scale", yaxis_title="V_sg (m/s) — log scale",
        height=400, margin=dict(l=50, r=20, t=40, b=50),
        hovermode="closest",
        legend=dict(orientation="v", y=1.0, x=1.02, bgcolor="rgba(0,0,0,0)"),
    )
    return fig
