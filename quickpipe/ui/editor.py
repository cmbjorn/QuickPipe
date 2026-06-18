"""Left column — line inlet conditions + an ordered list of sections."""
from __future__ import annotations

import streamlit as st

from . import state
from .sizing_panel import render_suggest_dn


def _idx(opts, val, default=0):
    try:
        return opts.index(val)
    except ValueError:
        return default


# ── Fluid sub-form (edits the inlet's nested fluid dict in place) ─────────────
def _fluid_form(fl: dict, key: str) -> None:
    phase = st.radio("Phase", ["Liquid", "Gas", "Two-phase"],
                     index=_idx(["liquid", "gas", "two-phase"], fl.get("phase", "liquid")),
                     horizontal=True, key=f"{key}_phase")
    fl["phase"] = phase.lower()
    want_gas = phase in ("Gas", "Two-phase")
    want_liq = phase in ("Liquid", "Two-phase")

    if want_liq:
        lt = st.selectbox("Liquid", state.LIQUID_LIST,
                          index=_idx(state.LIQUID_LIST, fl.get("liquid_type", "Water")),
                          key=f"{key}_lt")
        fl["liquid_type"] = lt
        if lt == "KOH solution":
            fl["koh_conc_wt_pct"] = st.number_input(
                "KOH concentration (wt%)", 0.0, 50.0,
                float(fl.get("koh_conc_wt_pct") or 30.0), 1.0, key=f"{key}_koh")
        fl["q_lye_m3h"] = st.number_input(
            "Liquid flow (m³/h)", 0.0, 1e6, float(fl.get("q_lye_m3h") or 0.0),
            1.0, key=f"{key}_q")
    else:
        fl["liquid_type"] = "Water"
        fl["q_lye_m3h"] = 0.0
        fl["koh_conc_wt_pct"] = None

    if want_gas:
        species = st.multiselect(
            "Gas species", state.GAS_LIST,
            default=list((fl.get("gas_flows_kgh") or {}).keys()) or ["Air"],
            key=f"{key}_gsp")
        gf = {}
        prev = fl.get("gas_flows_kgh") or {}
        for sp in species:
            gf[sp] = st.number_input(
                f"{sp} (kg/h)", 0.0, 1e7, float(prev.get(sp, 100.0)), 1.0,
                key=f"{key}_g_{sp}")
        fl["gas_flows_kgh"] = gf
        fl["use_coolprop"] = True
    else:
        fl["gas_flows_kgh"] = {}


def _inlet_panel(inl: dict, prefix: str) -> None:
    c1, c2 = st.columns(2)
    inl["P_in_bara"] = c1.number_input("Inlet pressure (bara)", 0.1, 600.0,
                                       float(inl.get("P_in_bara", 10.0)), 0.5, key=f"{prefix}_p")
    inl["T_C"] = c2.number_input("Temperature (°C)", -50.0, 400.0,
                                 float(inl.get("T_C", 25.0)), 1.0, key=f"{prefix}_t")
    inl.setdefault("fluid", {})
    _fluid_form(inl["fluid"], prefix)


def _pipe(el: dict, inlet_p_bara: float, row=None) -> None:
    # Apply a pending DN from the auto-sizer BEFORE the selectbox is created, so
    # the widget picks it up (a keyed widget can't be set after instantiation).
    _pend = f"qp_pending_dn_{el['id']}"
    if _pend in st.session_state:
        el["dn"] = st.session_state.pop(_pend)
        # Set the widget key directly so the selectbox shows the new DN on this
        # run.  Setting it before the widget is created is the Streamlit-approved
        # way to pre-populate a keyed widget without a warning.
        st.session_state[f"{el['id']}_dn"] = el["dn"]

    el["name"] = st.text_input("Name", el.get("name", "Section"), key=f"{el['id']}_nm")

    # Piping type selector — sets both pipe_type and material together
    _PIPING_LABELS = {
        ("DN Pipe", "CS"):      "EN Pipe - Carbon Steel",
        ("DN Pipe", "SS316L"):  "EN Pipe - SS316L",
        ("NPS Pipe", "CS"):     "ASME Pipe - Carbon Steel",
        ("NPS Pipe", "SS316L"): "ASME Pipe - SS316L",
        ("Tubing",  "SS316L"):  "316SS Metric Tubing",
    }
    _PIPING_FROM_LABEL = {v: k for k, v in _PIPING_LABELS.items()}
    cur_label = _PIPING_LABELS.get(
        (el.get("pipe_type", "DN Pipe"), el.get("material", "SS316L")), "EN Pipe - SS316L")
    piping_label = st.selectbox("Piping type", state.PIPE_TYPES,
        index=_idx(state.PIPE_TYPES, cur_label), key=f"{el['id']}_ptype")
    pipe_type_raw, mat_raw = _PIPING_FROM_LABEL.get(piping_label, ("DN Pipe", "SS316L"))
    el["pipe_type"] = pipe_type_raw
    el["material"] = mat_raw

    if pipe_type_raw == "Tubing":
        c1, c2 = st.columns(2)
        tube_size = el.get("tube_size", "T25")
        el["tube_size"] = c1.selectbox("Tube size (OD)", state.TUBE_LIST,
                                       index=_idx(state.TUBE_LIST, tube_size),
                                       key=f"{el['id']}_tsz")
        walls = state.tube_walls(el["tube_size"])
        cur_wall = el.get("tube_wall", walls[0]) if el.get("tube_wall") in walls else walls[0]
        el["tube_wall"] = c2.selectbox("Wall thickness", walls,
                                       index=_idx(walls, cur_wall),
                                       key=f"{el['id']}_tw")
        _tdata = state.TUBING_DATABASE.get(el["tube_size"], {}).get(el["tube_wall"], {})
        if _tdata:
            _id_mm_t = _tdata.get("id_m", 0.0) * 1000
            c2.caption(f"ID = {_id_mm_t:.1f} mm  ·  {_tdata.get('weight_kg_m', 0):.3f} kg/m"
                       f"  ·  WP = {_tdata.get('wp_bar', 0)} bar")
    elif pipe_type_raw == "NPS Pipe":
        sch_list = state.ASME_CS_SCHEDULES if mat_raw == "CS" else state.ASME_SS_SCHEDULES
        if el.get("schedule") not in sch_list:
            el["schedule"] = "Sch 40" if mat_raw == "CS" else "40S"
        c1, c2 = st.columns(2)
        el["nps"] = c1.selectbox("NPS", state.NPS_LIST,
                                 index=_idx(state.NPS_LIST, el.get("nps", '2"')),
                                 key=f"{el['id']}_nps")
        el["schedule"] = c2.selectbox("Schedule", sch_list,
                                      index=_idx(sch_list, el.get("schedule")),
                                      key=f"{el['id']}_sch")
        _od = state.ASME_PIPE_OD_MM.get(el["nps"], 0.0)
        _wall = state.ASME_WALL_MM.get(mat_raw, {}).get(el["nps"], {}).get(el["schedule"], 0.0)
        _id_mm_n = (_od - 2.0 * _wall) if _od > 0 and _wall > 0 else 0.0
        st.caption(f"ASME {'B36.10M' if mat_raw == 'CS' else 'B36.19M'}  ·  "
                   f"OD = {_od:.1f} mm  ·  t = {_wall:.2f} mm  ·  ID = {_id_mm_n:.1f} mm  ·  "
                   f"{state.ASME_SCHEDULE_DESCRIPTIONS.get(el['schedule'], '')}")
    else:
        dn_list = state.CS_DN_LIST if mat_raw == "CS" else state.SS316L_DN_LIST
        if el.get("dn") not in dn_list:
            el["dn"] = "DN50"
        c1, c2 = st.columns(2)
        el["dn"] = c1.selectbox("DN", dn_list,
                                index=_idx(dn_list, el.get("dn", "DN50")),
                                key=f"{el['id']}_dn")
        el["pn_class"] = c2.selectbox("Pressure class", state.PN_LIST,
                                      index=_idx(state.PN_LIST, el.get("pn_class", "PN16")),
                                      key=f"{el['id']}_pn")
        _od = state.EN_PIPE_OD_MM.get(mat_raw, {}).get(el["dn"], 0.0)
        _wall_tbl = state.EN_PIPE_WALL_MM.get(mat_raw, {}).get(el["pn_class"], {}).get(el["dn"], 0.0)
        el["wall_override"] = st.checkbox("Override wall thickness",
            bool(el.get("wall_override", False)), key=f"{el['id']}_wo")
        if el["wall_override"]:
            el["wall_override_mm"] = st.number_input("Wall (mm)", 0.5, 50.0,
                float(el.get("wall_override_mm") or _wall_tbl or 3.2), 0.1,
                key=f"{el['id']}_wmm")
            _wall_used = el["wall_override_mm"]
        else:
            _wall_used = _wall_tbl
        _id_mm_dn = (_od - 2.0 * _wall_used) if _od > 0 and _wall_used > 0 else 0.0
        st.caption(f"OD = {_od:.1f} mm  ·  t = {_wall_used:.1f} mm"
                   f"  ·  ID = {_id_mm_dn:.1f} mm  ·  {state.PN_DESCRIPTIONS.get(el['pn_class'], '')}")
    c3, c4 = st.columns(2)
    el["length_m"] = c3.number_input("Length / height (m)", 0.0, 1e5,
                                     float(el.get("length_m", 10.0)), 1.0, key=f"{el['id']}_L",
                                     help="Horizontal: run length. Vertical: rise/fall height.")
    el["orientation"] = c4.selectbox(
        "Orientation", state.ORIENTATIONS,
        index=_idx(state.ORIENTATIONS, el.get("orientation", "Horizontal")),
        key=f"{el['id']}_or")
    if pipe_type_raw != "Tubing":
        el["lined"] = st.checkbox("Lined", bool(el.get("lined", False)), key=f"{el['id']}_lined")
        if el["lined"]:
            lc1, lc2 = st.columns(2)
            el["liner_material"] = lc1.selectbox("Liner", state.LINERS,
                                                 index=_idx(state.LINERS, el.get("liner_material", "PTFE")),
                                                 key=f"{el['id']}_lmat")
            el["liner_thickness_mm"] = lc2.number_input("Liner t (mm)", 0.1, 20.0,
                                                        float(el.get("liner_thickness_mm", 1.0)), 0.5,
                                                        key=f"{el['id']}_lt")
    else:
        el["lined"] = False
    import pandas as pd
    fl = el.get("fittings_list", []) or []
    df = pd.DataFrame(fl if fl else [], columns=["type", "qty"])
    edited = st.data_editor(
        df, num_rows="dynamic", hide_index=True, width="stretch",
        column_config={
            "type": st.column_config.SelectboxColumn("Fitting", options=state.FITTINGS),
            "qty": st.column_config.NumberColumn("Qty", min_value=0, step=1, format="%d"),
        }, key=f"{el['id']}_fit")
    el["fittings_list"] = [
        {"type": r["type"], "qty": int(r["qty"] or 0)}
        for r in edited.to_dict("records")
        if r.get("type") and (r.get("qty") or 0) > 0]
    if pipe_type_raw == "Tubing" and el["fittings_list"]:
        st.caption("⚠ L_e/D values are calibrated for standard pipe fittings. "
                   "For Swagelok compression fittings use manufacturer Cv data — "
                   "these values will overestimate losses.")

    if pipe_type_raw == "DN Pipe":
        render_wall_check(el, inlet_p_bara)
        render_water_hammer(el, row, inlet_p_bara)
        render_suggest_dn(el, inlet_p_bara)
        render_iso1127_reference(el)


def _current_wall_mm(el: dict, mat: str) -> float:
    """The wall the section is currently using — override value or PN-class table."""
    if el.get("wall_override"):
        return float(el.get("wall_override_mm") or 0.0)
    return float(state.EN_PIPE_WALL_MM.get(mat, {})
                 .get(el.get("pn_class", "PN16"), {}).get(el.get("dn", "DN50"), 0.0))


def render_wall_check(el: dict, inlet_p_bara: float) -> None:
    """EN 13480-3 wall-thickness guidance: size the wall for a service and snap
    to a real EN ISO 1127 wall (never thinner than the structural floor)."""
    with st.expander("🔧 Wall thickness check (EN 13480-3)", expanded=False):
        mat = el.get("material", "SS316L")
        dn = el.get("dn", "DN50")
        od = state.EN_PIPE_OD_MM.get(mat, {}).get(dn, 0.0)
        if od <= 0:
            st.info("Select a DN to run the wall check.")
            return

        inlet_t_C = float(state.inlet().get("T_C", 25.0))
        dflt_p = el.get("design_p_barg")
        if dflt_p is None:
            dflt_p = max(0.0, round(inlet_p_bara - 1.013, 1))   # operating bara → barg
        dflt_t = el.get("design_t_C")
        if dflt_t is None:
            dflt_t = inlet_t_C

        c1, c2 = st.columns(2)
        dp = c1.number_input("Design pressure (barg)", 0.0, 1000.0, float(dflt_p), 1.0,
                             key=f"{el['id']}_dpb",
                             help="Maximum gauge pressure the wall must contain (usually above operating).")
        dt = c2.number_input("Design temperature (°C)", -50.0, 550.0, float(dflt_t), 5.0,
                             key=f"{el['id']}_dtc",
                             help="Allowable stress is derated at this temperature.")
        c3, c4 = st.columns(2)
        ca = c3.number_input("Corrosion allowance (mm)", 0.0, 10.0,
                             float(el.get("corrosion_allow_mm", 0.0)), 0.5, key=f"{el['id']}_ca")
        seamless = c4.checkbox("Seamless pipe (z = 1.0)", el.get("weld_factor", 1.0) >= 1.0,
                               key=f"{el['id']}_seam",
                               help="Uncheck for welded pipe without full radiography (joint factor z = 0.85).")
        el["design_p_barg"] = dp
        el["design_t_C"] = dt
        el["corrosion_allow_mm"] = ca
        el["weld_factor"] = 1.0 if seamless else 0.85

        r = state.recommend_wall(mat, dn, od, dp, dt,
                                 corrosion_allow_mm=ca, weld_factor=el["weld_factor"])
        rec = r["recommended_wall_mm"]

        st.caption(f"OD {od:.1f} mm · allowable stress f = {r['f_mpa']:.0f} MPa · "
                   f"pressure-only minimum e = {r['e_pressure_mm']:.2f} mm "
                   f"(+CA, ÷mill tol → {r['t_required_mm']:.2f} mm)")
        st.markdown(f"**Recommended wall: {rec:.1f} mm** · governed by **{r['governed_by']}** · "
                    f"rated **{r['p_rated_barg']:.0f} barg** at {dt:.0f} °C")
        if r["governed_by"] == "structural floor":
            st.caption(f"↳ Pressure alone needs only {r['t_required_mm']:.2f} mm; the {r['floor_mm']:.1f} mm "
                       f"structural floor (lightest EN ISO 1127 Series 1 wall for {dn}) governs, so you don't "
                       f"get paper-thin pipe.")
            st.caption("ℹ️ That floor is light **hygienic / light-process** tube — food, pharma, clean "
                       "chemical (EN 10217-7 / EN 10216-5, typically orbital-welded and well-supported). "
                       "For **rugged industrial service** (vibration, knocks, outdoor racks, heavy supports) "
                       "step up a wall for mechanical robustness — the pressure rating already has margin.")
        if r["ladder_exceeded"]:
            st.warning(f"Design pressure exceeds even the heaviest standard wall "
                       f"({r['walls'][-1]:.1f} mm → {r['p_rated_barg']:.0f} barg). "
                       "Step up a DN, raise the pressure class, or specify a special heavy wall.")

        cur = _current_wall_mm(el, mat)
        if cur > 0:
            cur_eff = cur * (1.0 - 0.125) - ca
            cur_rated = state.pressure_rating_barg(cur_eff, od, mat, dt, el["weld_factor"])
            ok = cur >= rec - 1e-9 and cur_rated >= dp
            src = "override" if el.get("wall_override") else f"{el.get('pn_class','PN16')} table"
            st.markdown(f"{'✅' if ok else '❌'} Current wall **{cur:.1f} mm** ({src}) → "
                        f"rated **{cur_rated:.0f} barg**"
                        + ("" if ok else f" — thinner than the recommended {rec:.1f} mm"))

        def _apply_wall(el_id: str = el["id"], _rec: float = rec) -> None:
            # on_click fires before the next render — safe to set widget-bound keys here.
            st.session_state[f"{el_id}_wo"] = True
            st.session_state[f"{el_id}_wmm"] = _rec

        st.button(f"Apply {rec:.1f} mm wall (override)", key=f"{el['id']}_applywall",
                  on_click=_apply_wall, width="stretch")


# Young's modulus (Pa) for pipe materials — used in Halliwell celerity formula.
_E_PIPE_PA: dict[str, float] = {
    "SS316L": 193e9,
    "CS":     200e9,
}


def render_water_hammer(el: dict, row, inlet_p_bara: float) -> None:
    """Joukowski surge pressure estimate for liquid-filled DN pipe segments."""
    with st.expander("🌊 Water hammer — Joukowski surge", expanded=False):
        fluid_spec = state.inlet().get("fluid", {})
        phase = fluid_spec.get("phase", "liquid")

        if phase != "liquid":
            st.info("Water hammer surge applies to liquid-filled pipe only — "
                    "gas/vapour compressibility absorbs transient pressure waves.")
            return

        if row is None or row.v_ms <= 0 or row.flow_kgh <= 0 or row.flow_m3h <= 0:
            st.info("Solve the line first — velocity and density come from the hydraulic result.")
            return

        # ── geometry ──────────────────────────────────────────────────────────
        mat   = el.get("material", "SS316L")
        dn    = el.get("dn", "DN50")
        od_mm = state.EN_PIPE_OD_MM.get(mat, {}).get(dn, 0.0)
        if od_mm <= 0:
            st.info("Select a DN to run the water hammer check.")
            return

        t_mm = (float(el.get("wall_override_mm") or 0.0) if el.get("wall_override")
                else state.EN_PIPE_WALL_MM.get(mat, {}).get(
                    el.get("pn_class", "PN16"), {}).get(dn, 0.0))
        if t_mm <= 0:
            st.info("Wall thickness unavailable for this DN/PN combination.")
            return

        d_i_m = (od_mm - 2.0 * t_mm) / 1000.0
        L_m   = float(el.get("length_m", 10.0))

        # ── fluid properties from last solve ──────────────────────────────────
        V   = row.v_ms
        rho = row.flow_kgh / row.flow_m3h       # in-situ density kg/m³

        # Speed of sound in the free liquid via CoolProp.
        import CoolProp.CoolProp as CP
        from quickpipe.engine._vendor.multiphase_engine import LIQUID_COOLPROP_ID
        cp_id = LIQUID_COOLPROP_ID.get(fluid_spec.get("liquid_type", "Water"), "Water")
        T_K  = float(state.inlet().get("T_C", 20.0)) + 273.15
        try:
            c_fluid = float(CP.PropsSI("A", "T", T_K, "P", inlet_p_bara * 1e5, cp_id))
        except Exception:
            c_fluid = 1480.0    # water at 20 °C fallback

        # ── Halliwell wave celerity (thin-wall, pipe anchored throughout) ─────
        K_f = rho * c_fluid ** 2                # Pa — liquid bulk modulus
        E_pa = _E_PIPE_PA.get(mat, 193e9)
        c   = c_fluid / (1.0 + K_f * d_i_m / (E_pa * (t_mm / 1000.0))) ** 0.5

        t_crit = 2.0 * L_m / c                  # critical closure time (s)

        # ── user input ────────────────────────────────────────────────────────
        tau = st.number_input(
            "Valve closure time τ (s)", 0.0, 600.0, 1.0, 0.05,
            key=f"{el['id']}_wh_tau",
            help="Time from fully open to fully closed. "
                 "1 s is a reasonable default for a fast actuated valve. "
                 "Check valves can slam in 0.05–0.3 s on pump trip — "
                 "use a conservative short value for those. "
                 "0 = instantaneous (absolute worst case).")

        # ── surge ΔP (linear slow-closure reduction when τ > 2L/c) ───────────
        if tau <= t_crit:
            dP_pa    = rho * c * V
            regime   = f"⚡ Rapid closure (τ ≤ 2L/c = {t_crit:.3f} s) — full Joukowski surge"
        else:
            dP_pa    = rho * c * V * (t_crit / tau)
            regime   = f"🐢 Slow closure (τ > 2L/c = {t_crit:.3f} s) — surge reduced by {t_crit/tau:.0%}"

        dP_barg      = dP_pa / 1e5
        P_peak_barg  = (inlet_p_bara - 1.013) + dP_barg   # gauge

        # ── pipe wall rating (EN 13480-3) ─────────────────────────────────────
        dt_design  = float(el.get("design_t_C") or state.inlet().get("T_C", 25.0))
        t_eff_mm   = t_mm * (1.0 - 0.125) - float(el.get("corrosion_allow_mm", 0.0))
        rated_barg = state.pressure_rating_barg(
            t_eff_mm, od_mm, mat, dt_design, el.get("weld_factor", 1.0))
        src = "override" if el.get("wall_override") else el.get("pn_class", "PN16")

        # ── output ────────────────────────────────────────────────────────────
        st.caption(
            f"Free-fluid c = {c_fluid:.0f} m/s  ·  pipe celerity c = {c:.0f} m/s "
            f"(−{100*(1 - c/c_fluid):.0f}% from wall elasticity)  ·  "
            f"ρ = {rho:.0f} kg/m³  ·  V = {V:.2f} m/s")
        st.markdown(regime)
        st.markdown(
            f"**Surge ΔP = {dP_barg:.1f} barg**  ·  "
            f"Peak = **{P_peak_barg:.1f} barg** "
            f"({inlet_p_bara - 1.013:.1f} operating + {dP_barg:.1f} surge)")

        ok = P_peak_barg <= rated_barg
        st.markdown(
            f"{'✅' if ok else '❌'} Pipe wall rated **{rated_barg:.0f} barg** "
            f"({src}, EN 13480-3 @ {dt_design:.0f} °C, t = {t_mm:.1f} mm) — "
            + ("peak within wall rating" if ok else "**peak exceeds pipe wall rating**"))

        st.caption(
            "**Conservatism:** Joukowski assumes (1) the full flow velocity arrests "
            "instantly at the valve (ΔV = V) — worst-case single closure event; "
            "(2) single straight pipe, no branching — reflections from tees, "
            "reducers, or open ends can amplify or partly cancel the wave; "
            "(3) no column separation — if the pressure wave drops below vapour "
            "pressure, a cavity forms and its collapse produces a second, sometimes "
            "larger, spike. Slow-closure reduction uses the linear Allievi "
            "approximation (conservative for τ only slightly above 2L/c). "
            "EN 13480-3 and ASME B31.3 permit a short-duration surge to 1.1× and "
            "1.33× the allowable operating pressure respectively — verify against "
            "your applicable code before acting on a marginal result.")


def render_iso1127_reference(el: dict) -> None:
    """Reference panel: the three EN ISO 1127 tube series with descriptions.
    Series 1 (pipe-size) is what the wall check sizes; Series 2 & 3 are the
    supplementary metric-OD tube, shown with a live pressure rating."""
    import pandas as pd
    with st.expander("📐 ISO 1127 tube series (reference)", expanded=False):
        st.caption("EN ISO 1127 sorts stainless tube ODs into three preference series "
                   "(selected from ISO 4200). Series 1 is the pipe-OD family sized by the "
                   "wall check above; Series 2 & 3 are supplementary metric-OD tube.")
        # Rating shown for stainless tube (ISO 1127 is a stainless standard) at the
        # wall-check design temperature, falling back to the line inlet temperature.
        dt = el.get("design_t_C")
        if dt is None:
            dt = float(state.inlet().get("T_C", 20.0))

        st.markdown(f"**Series 1 — pipe size** *(sized above)*")
        st.caption(state.ISO_1127_SERIES_DESCRIPTIONS[1])
        for n, data in ((2, state.ISO_1127_SERIES_2), (3, state.ISO_1127_SERIES_3)):
            st.markdown(f"**Series {n} — supplementary metric tube**")
            st.caption(state.ISO_1127_SERIES_DESCRIPTIONS[n])
            rows = []
            for od, wall in sorted(data.items()):
                eff = wall * (1.0 - 0.125)               # no corrosion allowance on tube
                rated = state.pressure_rating_barg(eff, od, "SS316L", dt)
                rows.append({"OD (mm)": od, "Wall (mm)": wall,
                             "ID (mm)": round(od - 2 * wall, 1),
                             f"Rated @ {dt:.0f}°C (barg)": round(rated)})
            st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)


def _misc(el: dict) -> None:
    el["name"] = st.text_input("Name", el.get("name", "Equipment"), key=f"{el['id']}_nm")
    el["dp_kpa"] = st.number_input(
        "ΔP (kPa)  — + drops, − adds", -1e5, 1e5, float(el.get("dp_kpa", 0.0)),
        1.0, key=f"{el['id']}_dp",
        help="Positive = pressure loss (valve/equipment). Negative = pressure gain (pump).")


_ICON = {"pipe": "│", "misc": "◆"}


def render(pre_result) -> None:
    """Render the active line's tag/service, inlet panel + section editor.
    pre_result supplies per-section inlet pressures for the auto-DN suggestion."""
    ln = state.active_line()
    lid = ln["id"]

    c1, c2 = st.columns([1, 2])
    ln["tag"] = c1.text_input("Line tag", ln.get("tag", ""), key=f"{lid}_tag",
                              placeholder="100-PL-001")
    ln["service"] = c2.text_input("Service", ln.get("service", ""), key=f"{lid}_svc",
                                  placeholder="e.g. Pump discharge to KO drum")

    st.subheader("Line inlet")
    st.caption("Inlet pressure, temperature and composition feeding section #1.")
    _inlet_panel(state.inlet(), f"{lid}_inlet")

    st.subheader("Sections")
    st.caption("Each section's outlet is the next section's inlet — edit here, "
               "results update live on the right.")

    secs = state.sections()
    rows = getattr(pre_result, "rows", []) if pre_result else []
    for i, el in enumerate(secs):
        kind = el.get("kind", "pipe")
        title = f"{_ICON.get(kind,'│')}  #{i+1}  {el.get('name', kind)}  ·  {kind}"
        with st.expander(title, expanded=(len(secs) <= 2 and i == 0)):
            if kind == "pipe":
                row = rows[i] if i < len(rows) else None
                inlet_p = row.p_in_bara if row else state.inlet().get("P_in_bara", 10.0)
                _pipe(el, inlet_p, row)
            elif kind == "misc":
                _misc(el)

            b1, b2, b3 = st.columns(3)
            if b1.button("▲ Up", key=f"{el['id']}_up", width="stretch"):
                state.move_section(i, -1); st.rerun()
            if b2.button("▼ Down", key=f"{el['id']}_dn_btn", width="stretch"):
                state.move_section(i, +1); st.rerun()
            if b3.button("🗑 Delete", key=f"{el['id']}_del", width="stretch"):
                state.delete_section(i); st.rerun()

    t1, t2 = st.columns(2)
    if t1.button("➕ Add Pipe Section", width="stretch", type="primary", key="qp_add_pipe"):
        state.add_pipe(); st.rerun()
    if t2.button("➕ Add Equipment (ΔP)", width="stretch", key="qp_add_misc"):
        state.add_misc(); st.rerun()
