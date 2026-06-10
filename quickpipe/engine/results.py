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
    pipe: str            # "DN/PN" (blank for non-pipe)
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
    warning: str = ""     # not a column; surfaced separately

    def to_dict(self) -> dict:
        return {
            "Element":        self.element,
            "Type":           self.type,
            "Pipe":           self.pipe,
            "ID (mm)":        self.id_mm,
            "L (m)":          self.l_m,
            "L_eff (m)":      self.l_eff_m,
            "Δz (m)":         self.dz_m,
            "Fluid":          self.fluid,
            "Composition":    self.composition,
            "Flow (kg/h)":    self.flow_kgh,
            "Flow (m³/h)":    self.flow_m3h,
            "P_in (bara)":    self.p_in_bara,
            "ΔP_fric (kPa)":  self.dp_fric_kpa,
            "ΔP_grav (kPa)":  self.dp_grav_kpa,
            "ΔP (kPa)":       self.dp_kpa,
            "P_out (bara)":   self.p_out_bara,
            "V (m/s)":        self.v_ms,
            "V_e (m/s)":      self.v_e_ms,
            "V/V_e":          self.v_over_ve,
            "Regime":         self.regime,
        }


# Column order for DataFrame / Excel rendering.
COLUMNS = list(QuickpipeRow(
    "", "", "", 0, 0, 0, 0, "", "", 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, "").to_dict().keys())
