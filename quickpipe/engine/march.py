"""Forward pressure-march engine for a line of sections.

Given the line inlet conditions and an ordered list of sections (Pipe / Misc),
march pressure from section #1's inlet onward. Fluid properties (density,
velocities, void fraction) are recomputed at each section's local pressure — so
gas compressibility is tracked between sections — and the liquid mass flow is
frozen at the inlet so mass is conserved. A section's outlet pressure is the
next section's inlet. Friction uses the vendored ``calculate_segment_pressure_drop``
with the angle forced to 0; gravity is computed separately from the in-situ
mixture density and the geometric Δz (no double-count). Two-phase (Beggs-Brill)
is supported.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import multiphase_engine as _E
from standards.piping import (
    PIPE_DATABASE, MATERIAL_ROUGHNESS, LINER_ROUGHNESS, sum_le_fit)

from .elements import section_from_dict, inlet_from_dict, ORIENT_SIGN
from .fluids import props_at, composition_str, fluid_label, to_mass_basis
from .results import QuickpipeRow

G = 9.80665
_P_FLOOR_PA = 1000.0   # 0.01 bara floor


@dataclass
class MarchResult:
    rows: list                      # list[QuickpipeRow] — one per section
    inlet_P_bara: float
    outlet_P_bara: float
    total_dp_kpa: float
    total_dp_fric_kpa: float
    total_dp_grav_kpa: float
    sketch_x: list = field(default_factory=list)   # node distances (inlet + each outlet)
    sketch_z: list = field(default_factory=list)
    sketch_P: list = field(default_factory=list)
    warnings: list = field(default_factory=list)

    def to_dicts(self) -> list:
        return [r.to_dict() for r in self.rows]


def _insitu_density(props: dict) -> float:
    x = props.get("x_gas", 0.0)
    rho_g = props.get("rho_g", 0.0) or 0.0
    rho_l = props.get("rho_l", 1000.0) or 1000.0
    if 0.0 < x < 1.0:
        alpha = props.get("alpha", 0.0) or 0.0
        return alpha * rho_g + (1.0 - alpha) * rho_l
    return rho_g if x >= 1.0 else rho_l


def pipe_geometry(pipe):
    """(D_eff_m, roughness_m, fittings_equiv_length_m) for a Pipe section."""
    D = PIPE_DATABASE[pipe.dn][pipe.pn]
    if pipe.lined:
        D_eff = D - 2.0 * pipe.liner_thickness_mm / 1000.0
        rough = LINER_ROUGHNESS[pipe.liner_material]
    else:
        D_eff = D
        rough = MATERIAL_ROUGHNESS.get(pipe.material, MATERIAL_ROUGHNESS["SS316L"])
    le_fit = sum_le_fit({"fittings_list": pipe.fittings_list}, D_eff)
    return D_eff, rough, le_fit


def _friction_segment(props, D_eff, rough, L_eff, correlation, voidage_method):
    return _E.calculate_segment_pressure_drop(
        props, D_eff, rough, L_eff, 0.0,
        correlation=correlation, voidage_method=voidage_method)


def _pipe_hydraulics(pipe, fluid, P_in, T_C, correlation, voidage_method,
                     substep_gas, max_substeps):
    D_eff, rough, le_fit = pipe_geometry(pipe)
    L_eff = pipe.length_m + le_fit
    # Vertical section: the length IS the elevation change. Horizontal: Δz = 0.
    dz = ORIENT_SIGN.get(pipe.orientation, 0.0) * pipe.length_m
    props_in = props_at(fluid, P_in, T_C)

    n = 1
    if substep_gas and props_in.get("x_gas", 0.0) > 0.5:
        seg0 = _friction_segment(props_in, D_eff, rough, L_eff, correlation, voidage_method)
        if seg0.get("mach_gas", 0.0) > 0.1 or seg0.get("out_of_range"):
            n = min(max_substeps, max(2, int(seg0.get("mach_gas", 0.1) / 0.05)))

    dP_fric = dP_grav = 0.0
    V_max = 0.0
    V_e_min = float("inf")
    regime = ""
    oor = False
    mach = 0.0
    P = P_in
    L_sub = L_eff / n
    dz_sub = dz / n
    V_sg_last = V_sl_last = 0.0
    for i in range(n):
        props = props_in if i == 0 else props_at(fluid, P, T_C)
        seg = _friction_segment(props, D_eff, rough, L_sub, correlation, voidage_method)
        df = seg["dP_fric_Pa"]
        rho_is = _insitu_density(props)
        dg = rho_is * G * dz_sub
        dP_fric += df
        dP_grav += dg
        V = seg["Vsg"] + seg["Vsl"]
        V_sg_last = seg.get("Vsg", 0.0)
        V_sl_last = seg.get("Vsl", 0.0)
        V_e, _ = _E.calculate_erosion_velocity(props["rho_g"], props["rho_l"], props["x_gas"])
        V_max = max(V_max, V)
        V_e_min = min(V_e_min, V_e if V_e > 0 else V_e_min)
        if i == 0:
            regime = seg["regime"]
        oor = oor or bool(seg.get("out_of_range"))
        mach = max(mach, seg.get("mach_gas", 0.0))
        P = max(_P_FLOOR_PA, P - df - dg)

    if V_e_min == float("inf"):
        V_e_min = 0.0
    return {
        "dP_fric_Pa": dP_fric, "dP_grav_Pa": dP_grav, "dz": dz,
        "V_ms": V_max, "V_e_ms": V_e_min, "regime": regime,
        "out_of_range": oor, "mach_gas": mach,
        "props_in": props_in, "D_eff": D_eff, "L_eff": L_eff,
        "V_sg_ms": V_sg_last, "V_sl_ms": V_sl_last,
    }


def _flow_cols(props):
    m_kgh = props.get("m_total_kgs", 0.0) * 3600.0
    rho_is = _insitu_density(props)
    q_m3h = m_kgh / rho_is if rho_is > 0 else 0.0
    return m_kgh, q_m3h


def march(inlet, sections, *, correlation="Beggs-Brill", voidage_method="Homogeneous",
          substep_gas=False, max_substeps=20) -> MarchResult:
    """March pressure through the sections from the line inlet conditions."""
    inl = inlet_from_dict(inlet) if isinstance(inlet, dict) else inlet
    secs = [section_from_dict(s) if isinstance(s, dict) else s for s in sections]
    if not secs:
        raise ValueError("march requires at least 1 section")

    P = inl.P_in_bara * 1e5
    T_C = inl.T_C
    fluid = to_mass_basis(inl.fluid, P, T_C)   # freeze mass → conserve along line
    z = 0.0
    x_h = 0.0

    rows: list = []
    warns: list = []
    total = total_f = total_g = 0.0
    # Sketch nodes: the inlet, then each section's outlet (not table rows).
    sketch_x = [0.0]
    sketch_z = [0.0]
    sketch_P = [P / 1e5]
    P_in_first = P / 1e5

    for el in secs:
        P_in = P
        if el.kind == "pipe":
            h = _pipe_hydraulics(el, fluid, P_in, T_C, correlation, voidage_method,
                                 substep_gas, max_substeps)
            dP_f, dP_g, dz = h["dP_fric_Pa"], h["dP_grav_Pa"], h["dz"]
            P = max(_P_FLOOR_PA, P_in - dP_f - dP_g)
            # Horizontal sections advance distance; vertical sections advance height.
            if el.orientation == "Horizontal":
                x_h += el.length_m
            else:
                z += dz
            v_e, v = h["V_e_ms"], h["V_ms"]
            ratio = v / v_e if v_e > 0 else 0.0
            m_kgh, q_m3h = _flow_cols(h["props_in"])
            # Superficial velocities for regime map
            v_sg = h.get("V_sg_ms", 0.0)
            v_sl = h.get("V_sl_ms", 0.0)
            row = QuickpipeRow(
                element=el.name, type="Pipe", pipe=f"{el.dn}/{el.pn}",
                id_mm=round(h["D_eff"] * 1000, 1), l_m=el.length_m,
                l_eff_m=round(h["L_eff"], 2), dz_m=dz,
                fluid=fluid_label(fluid, h["props_in"]),
                composition=composition_str(h["props_in"]),
                flow_kgh=m_kgh, flow_m3h=q_m3h, p_in_bara=P_in / 1e5,
                dp_fric_kpa=dP_f / 1000.0, dp_grav_kpa=dP_g / 1000.0,
                dp_kpa=(dP_f + dP_g) / 1000.0, p_out_bara=P / 1e5,
                v_ms=round(v, 3), v_e_ms=round(v_e, 2), v_over_ve=round(ratio, 3),
                regime=h["regime"], v_sg_ms=round(v_sg, 4), v_sl_ms=round(v_sl, 4))
            total += dP_f + dP_g
            total_f += dP_f
            total_g += dP_g
            if h["out_of_range"]:
                warns.append(f"{el.name}: gas Mach {h['mach_gas']:.2f} — beyond correlation validity (ΔP uncertain).")
            if ratio > 1.0:
                warns.append(f"{el.name}: V/V_e = {ratio:.2f} > 1 — exceeds API RP 14E erosion limit.")
            if P <= _P_FLOOR_PA * 1.001:
                warns.append(f"{el.name}: pressure hit the 0.01 bara floor — line infeasible (too long / undersized).")

        elif el.kind == "misc":
            props = props_at(fluid, P_in, T_C)
            dP_eq = el.dp_kpa * 1000.0
            P = max(_P_FLOOR_PA, P_in - dP_eq)
            m_kgh, q_m3h = _flow_cols(props)
            row = QuickpipeRow(
                element=el.name, type="Misc", pipe="", id_mm=0.0, l_m=0.0,
                l_eff_m=0.0, dz_m=0.0, fluid=fluid_label(fluid, props),
                composition=composition_str(props), flow_kgh=m_kgh, flow_m3h=q_m3h,
                p_in_bara=P_in / 1e5, dp_fric_kpa=0.0, dp_grav_kpa=0.0,
                dp_kpa=dP_eq / 1000.0, p_out_bara=P / 1e5,
                v_ms=0.0, v_e_ms=0.0, v_over_ve=0.0,
                regime=("pressure boost" if el.dp_kpa < 0 else "Δp element"))
            total += dP_eq
        else:
            continue

        rows.append(row)
        sketch_x.append(x_h)
        sketch_z.append(z)
        sketch_P.append(P / 1e5)

    return MarchResult(
        rows=rows, inlet_P_bara=P_in_first, outlet_P_bara=P / 1e5,
        total_dp_kpa=total / 1000.0, total_dp_fric_kpa=total_f / 1000.0,
        total_dp_grav_kpa=total_g / 1000.0,
        sketch_x=sketch_x, sketch_z=sketch_z, sketch_P=sketch_P, warnings=warns)
