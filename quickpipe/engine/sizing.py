"""Auto-DN suggestion — sweep nominal diameters at a pipe's local conditions and
recommend the smallest size meeting velocity / ΔP / erosion criteria.

Uses the same friction + in-situ-gravity path as the march, so suggestions are
consistent with what the line table will show once the DN is applied.
"""
from __future__ import annotations

from dataclasses import dataclass

import multiphase_engine as _E
from standards.piping import (
    EN_PIPE_OD_MM, en_pipe_id_m, MATERIAL_ROUGHNESS, LINER_ROUGHNESS, sum_le_fit)

from .fluids import props_at
from .march import _insitu_density, G


@dataclass
class SizingCriteria:
    v_min: float = 0.0              # m/s
    v_max: float = 3.0              # m/s (liquids ~3, gases higher)
    dp_per_100m_max: float = 50.0   # kPa per 100 m (friction)
    erosion_C: float = 100.0        # API RP 14E constant


def suggest_dn(fluid, P_pa, T_C, *, pn_class="PN16", material="SS316L",
               lined=False, liner_material="PTFE", liner_thickness_mm=1.0,
               length_m=100.0, dz_m=0.0, fittings_list=None,
               correlation="Beggs-Brill", voidage_method="Homogeneous",
               criteria=None) -> dict:
    """Return {'table': [...per-DN dict...], 'recommended_dn': str|None}."""
    criteria = criteria or SizingCriteria()
    props = props_at(fluid, P_pa, T_C)
    fittings_list = fittings_list or []
    dn_list = list(EN_PIPE_OD_MM.get(material, EN_PIPE_OD_MM["SS316L"]).keys())

    table = []
    recommended = None
    for dn in dn_list:
        D = en_pipe_id_m(material, pn_class, dn)
        if lined:
            D_eff = D - 2.0 * liner_thickness_mm / 1000.0
            rough = LINER_ROUGHNESS[liner_material]
        else:
            D_eff = D
            rough = MATERIAL_ROUGHNESS.get(material, MATERIAL_ROUGHNESS["SS316L"])
        if D_eff <= 0:
            continue
        le_fit = sum_le_fit({"fittings_list": fittings_list}, D_eff)
        L_eff = length_m + le_fit

        seg = _E.calculate_segment_pressure_drop(
            props, D_eff, rough, L_eff, 0.0,
            correlation=correlation, voidage_method=voidage_method)
        V = seg["Vsg"] + seg["Vsl"]
        V_e, _ = _E.calculate_erosion_velocity(
            props["rho_g"], props["rho_l"], props["x_gas"], C=criteria.erosion_C)
        ratio = V / V_e if V_e > 0 else 0.0
        dp_fric_100m_kpa = (seg["dP_fric_Pa"] / L_eff * 100.0) / 1000.0 if L_eff > 0 else 0.0
        dp_grav_kpa = _insitu_density(props) * G * dz_m / 1000.0

        v_ok = criteria.v_min <= V <= criteria.v_max
        dp_ok = dp_fric_100m_kpa <= criteria.dp_per_100m_max
        ero_ok = ratio <= 1.0
        passes = v_ok and dp_ok and ero_ok

        table.append({
            "DN": dn,
            "ID (mm)": round(D_eff * 1000, 1),
            "V (m/s)": round(V, 3),
            "V/V_e": round(ratio, 3),
            "ΔP_fric/100m (kPa)": round(dp_fric_100m_kpa, 3),
            "ΔP_grav (kPa)": round(dp_grav_kpa, 3),
            "Regime": seg["regime"],
            "V ok": "✓" if v_ok else "✗",
            "ΔP ok": "✓" if dp_ok else "✗",
            "Erosion ok": "✓" if ero_ok else "✗",
            "Adequate": "✅" if passes else "—",
        })
        if passes and recommended is None:
            recommended = dn

    return {"table": table, "recommended_dn": recommended, "criteria": criteria}
