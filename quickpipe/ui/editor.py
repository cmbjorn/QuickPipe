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


def _pipe(el: dict, inlet_p_bara: float) -> None:
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

    pipe_type = st.radio(
        "Type", state.PIPE_TYPES,
        index=_idx(state.PIPE_TYPES, el.get("pipe_type", "DN Pipe")),
        horizontal=True, key=f"{el['id']}_ptype")
    el["pipe_type"] = pipe_type

    c1, c2 = st.columns(2)
    if pipe_type == "Tubing":
        tube_size = el.get("tube_size", "T25")
        el["tube_size"] = c1.selectbox("Tube size (OD)", state.TUBE_LIST,
                                       index=_idx(state.TUBE_LIST, tube_size),
                                       key=f"{el['id']}_tsz")
        walls = state.tube_walls(el["tube_size"])
        cur_wall = el.get("tube_wall", walls[0]) if el.get("tube_wall") in walls else walls[0]
        el["tube_wall"] = c2.selectbox("Wall thickness", walls,
                                       index=_idx(walls, cur_wall),
                                       key=f"{el['id']}_tw")
    else:
        el["dn"] = c1.selectbox("DN", state.DN_LIST,
                                index=_idx(state.DN_LIST, el.get("dn", "DN50")),
                                key=f"{el['id']}_dn")
        el["schedule"] = c2.selectbox("Schedule (ASME B36.19M)", state.SCHEDULE_LIST,
                                      index=_idx(state.SCHEDULE_LIST, el.get("schedule", "40S")),
                                      key=f"{el['id']}_sched")
        _od = state.PIPE_OD_MM.get(el.get("dn", "DN50"))
        _id_m = state.PIPE_DATABASE.get(el.get("dn", "DN50"), {}).get(el.get("schedule", "40S"))
        if _od and _id_m:
            _t = (_od - _id_m * 1000) / 2
            c2.caption(f"t = {_t:.2f} mm  ·  {state.SCHEDULE_DESCRIPTIONS.get(el['schedule'], '')}")
    c3, c4 = st.columns(2)
    el["length_m"] = c3.number_input("Length / height (m)", 0.0, 1e5,
                                     float(el.get("length_m", 10.0)), 1.0, key=f"{el['id']}_L",
                                     help="Horizontal: run length. Vertical: rise/fall height.")
    el["orientation"] = c4.selectbox(
        "Orientation", state.ORIENTATIONS,
        index=_idx(state.ORIENTATIONS, el.get("orientation", "Horizontal")),
        key=f"{el['id']}_or")
    if pipe_type == "DN Pipe":
        el["material"] = st.selectbox("Material", state.MATERIALS,
                                      index=_idx(state.MATERIALS, el.get("material", "SS316L")),
                                      key=f"{el['id']}_mat")
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
    if el.get("pipe_type", "DN Pipe") == "Tubing" and el["fittings_list"]:
        st.caption("⚠ L_e/D values are calibrated for standard pipe fittings. "
                   "For Swagelok compression fittings use manufacturer Cv data — "
                   "these values will overestimate losses.")

    if el.get("pipe_type", "DN Pipe") == "DN Pipe":
        render_suggest_dn(el, inlet_p_bara)


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
                inlet_p = rows[i].p_in_bara if i < len(rows) else state.inlet().get("P_in_bara", 10.0)
                _pipe(el, inlet_p)
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
