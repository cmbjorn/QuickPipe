"""Fluid-property adapter — isolates Quickpipe from the verbose vendored
``calculate_two_phase_properties`` signature and handles the KOH built-in.

Returns the standard FlowBench props dict (rho_l, rho_g, mu_l, mu_g, sigma,
x_gas, m_total_kgs, alpha, composition, ...).
"""
from __future__ import annotations

import multiphase_engine as _E   # resolved via quickpipe.engine sys.path bootstrap

from .elements import FluidSpec

_P_FLOOR_PA = 1000.0   # CoolProp can fail at sub-kPa; clamp before every call


def props_at(fluid: FluidSpec, P_pa: float, T_C: float) -> dict:
    """Evaluate fluid properties at a local marching state (P in Pa, T in °C).

    A frozen mass basis (``fluid.liquid_flows_kgh`` set) is preferred over the
    volumetric ``q_lye_m3h`` so that, once normalized at the source, mass flow is
    conserved as pressure varies along the line (only density/velocity change).
    """
    P_bara = max(_P_FLOOR_PA, P_pa) / 1e5
    gas = fluid.gas_flows_kgh or {}

    if fluid.liquid_type == "KOH solution":
        if fluid.koh_conc_wt_pct is not None:
            rho, mu, sig = _E.koh_properties(T_C, fluid.koh_conc_wt_pct)
        else:
            rho, mu, sig = 1000.0, 1.0e-3, 0.072
        custom_liquid = {"rho_kgm3": rho, "mu_mpas": mu * 1e3, "sigma_mnm": sig * 1e3,
                         "koh_conc_wt": fluid.koh_conc_wt_pct}
        if fluid.liquid_flows_kgh:
            liquid_flows = fluid.liquid_flows_kgh
        elif fluid.q_lye_m3h > 0:
            liquid_flows = {"KOH solution": fluid.q_lye_m3h * rho}
        else:
            liquid_flows = None
        return _E.calculate_two_phase_properties(
            P_bara, T_C, gas, "KOH solution", 0.0,
            custom_gas=fluid.custom_gas, custom_liquid=custom_liquid,
            use_coolprop=fluid.use_coolprop, liquid_flows_kgh=liquid_flows)

    if fluid.liquid_flows_kgh:
        # Frozen mass basis (named CoolProp liquid routed through the mixture path)
        return _E.calculate_two_phase_properties(
            P_bara, T_C, gas, fluid.liquid_type, 0.0,
            custom_gas=fluid.custom_gas, custom_liquid=fluid.custom_liquid,
            use_coolprop=fluid.use_coolprop, liquid_flows_kgh=fluid.liquid_flows_kgh)

    return _E.calculate_two_phase_properties(
        P_bara, T_C, gas, fluid.liquid_type, fluid.q_lye_m3h,
        custom_gas=fluid.custom_gas, custom_liquid=fluid.custom_liquid,
        use_coolprop=fluid.use_coolprop, liquid_flows_kgh=None)


def to_mass_basis(fluid: FluidSpec, P_pa: float, T_C: float) -> FluidSpec:
    """Return a copy of ``fluid`` with the liquid expressed as a mass flow (kg/h)
    evaluated once at (P_pa, T_C), so downstream property calls conserve mass.
    Gas is already mass-specified. Gas-only fluids are returned unchanged.
    """
    import copy
    if not fluid.has_liquid() or fluid.liquid_flows_kgh:
        return fluid
    props = props_at(fluid, P_pa, T_C)
    m_liq = props.get("m_liquid_total_kgh") or props.get("m_lye_kgh") or 0.0
    f = copy.deepcopy(fluid)
    f.q_lye_m3h = 0.0
    species = "KOH solution" if fluid.liquid_type == "KOH solution" else fluid.liquid_type
    f.liquid_flows_kgh = {species: m_liq}
    return f


def composition_str(props: dict, max_terms: int = 4) -> str:
    """Compact 'species mol-frac' string from a props dict for the table."""
    comp = props.get("composition") or {}
    parts = []
    for sp, info in comp.items():
        mf = info.get("mol_frac")
        if mf and mf > 1e-4:
            parts.append((mf, f"{sp} {mf:.3f}"))
    parts.sort(reverse=True)
    out = [p[1] for p in parts[:max_terms]]
    return " / ".join(out) if out else "—"


def fluid_label(fluid: FluidSpec, props: dict) -> str:
    """Short phase/fluid label for the table (e.g. 'Water (liq)', 'Air (gas)')."""
    x = props.get("x_gas", 0.0)
    if 0.0 < x < 1.0:
        return "two-phase"
    gas = ", ".join((fluid.gas_flows_kgh or {}).keys())
    if x >= 1.0:
        return f"{gas or 'gas'} (gas)"
    return f"{fluid.liquid_type} (liq)"
