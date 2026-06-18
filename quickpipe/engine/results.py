"""QuickpipeRow — one result row per line element.

Mirrors the FlowBench ``models/pipe.py`` SegmentRow pattern (dataclass +
``to_dict()`` with display-key columns) but tailored to the line-sizing brief:
includes explicit Δz, composition, and both mass and in-situ volumetric flow.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class QuickpipeRow:
    element: str
    type: str
    pipe: str            # "DN/PN" (EN) or "NPS/Sch" (ASME); blank for non-pipe
    material: str        # e.g. "SS316L" or "CS" (blank for non-pipe)
    pn_class: str        # EN PN class or ASME schedule; "—" for tubing / non-pipe
    id_mm: float
    l_m: float
    l_eff_m: float
    dz_m: float
    fluid: str
    composition: str
    flow_kgh: float
    flow_m3h: float       # in-situ (actual at local P)
    p_in_bara: float
    dp_fric_kpa: float
    dp_grav_kpa: float
    dp_kpa: float
    p_out_bara: float
    v_ms: float
    v_e_ms: float
    v_over_ve: float
    regime: str
    lining: str = "—"     # "<liner> <t> mm" for lined pipe, else "—"
    dp_fit_kpa: float = 0.0  # minor losses (fittings) extracted from dp_fric
    v_sg_ms: float = 0.0  # superficial gas velocity (two-phase)
    v_sl_ms: float = 0.0  # superficial liquid velocity (two-phase)
    warning: str = ""     # not a column; surfaced separately

    def to_dict(self) -> dict:
        # `type`, `composition`, `v_e_ms` are intentionally not columns: type is
        # used for filtering (overview/sketch/report), composition is shown in
        # the report header, and V_e is implied by V and the V/V_e ratio.
        return {
            "Element":        self.element,
            "Pipe":           self.pipe,
            "Material":       self.material,
            "Class / Sch":    self.pn_class,
            "ID (mm)":        self.id_mm,
            "Lining":         self.lining,
            "L (m)":          self.l_m,
            "L_eff (m)":      self.l_eff_m,
            "Δz (m)":         self.dz_m,
            "Fluid":          self.fluid,
            "Flow (kg/h)":    self.flow_kgh,
            "Flow (m³/h)":    self.flow_m3h,
            "P_in (bara)":    self.p_in_bara,
            "ΔP_fric (kPa)":  self.dp_fric_kpa,
            "ΔP_fit (kPa)":   self.dp_fit_kpa,
            "ΔP_grav (kPa)":  self.dp_grav_kpa,
            "ΔP (kPa)":       self.dp_kpa,
            "P_out (bara)":   self.p_out_bara,
            "V (m/s)":        self.v_ms,
            "V/V_e":          self.v_over_ve,
            "Regime":         self.regime,
        }


# Column order for DataFrame / Excel rendering.
COLUMNS = list(QuickpipeRow(
    "", "", "", "", "", 0, 0, 0, 0, "", "", 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, "").to_dict().keys())
# Columns: Element, Pipe, Material, Class / Sch, ID (mm), Lining, L (m), L_eff (m),
#          Δz (m), Fluid, Flow (kg/h), Flow (m³/h), P_in (bara), ΔP_fric (kPa),
#          ΔP_fit (kPa), ΔP_grav (kPa), ΔP (kPa), P_out (bara), V (m/s), V/V_e, Regime
