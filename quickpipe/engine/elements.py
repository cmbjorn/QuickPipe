"""Quickpipe line model — line inlet conditions + an ordered list of sections.

A line is organized like a line list: a single set of **inlet conditions**
(pressure, temperature, fluid/composition) feeding **section #1**, then an
ordered list of sections. Each section is a Pipe or a Misc (signed ΔP) element;
a section's outlet pressure is the next section's inlet — there are no separate
source/sink nodes. Sections carry a stable ``id`` for UI reorder/delete and a
``kind`` discriminator, and round-trip to/from plain dicts for session state.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Optional


# ── Fluid specification (set once at the line inlet; passes through unchanged) ─
@dataclass
class FluidSpec:
    phase: str = "liquid"                 # "liquid" | "gas" | "two-phase" (hint)
    gas_flows_kgh: dict = field(default_factory=dict)
    use_coolprop: bool = True
    custom_gas: Optional[dict] = None
    liquid_type: str = "Water"            # CoolProp name or "KOH solution"
    liquid_flows_kgh: Optional[dict] = None
    q_lye_m3h: float = 0.0
    koh_conc_wt_pct: Optional[float] = None
    custom_liquid: Optional[dict] = None

    def has_gas(self) -> bool:
        return any(v > 0 for v in (self.gas_flows_kgh or {}).values())

    def has_liquid(self) -> bool:
        return self.q_lye_m3h > 0 or bool(
            self.liquid_flows_kgh and any(v > 0 for v in self.liquid_flows_kgh.values()))


@dataclass
class LineInlet:
    """Conditions feeding section #1 (inlet pressure, temperature, fluid)."""
    P_in_bara: float = 10.0
    T_C: float = 25.0
    fluid: FluidSpec = field(default_factory=FluidSpec)


# A section runs either horizontally or vertically; for a vertical section the
# length IS the rise (up) or fall (down), i.e. the elevation change.
ORIENTATIONS = ["Horizontal", "Vertical Upflow", "Vertical Downflow"]
ORIENT_SIGN = {"Horizontal": 0.0, "Vertical Upflow": 1.0, "Vertical Downflow": -1.0}


@dataclass
class Pipe:
    kind: str = "pipe"
    id: str = "p1"
    name: str = "Section"
    pipe_type: str = "DN Pipe"             # "DN Pipe" | "Tubing"
    dn: str = "DN50"
    pn_class: str = "PN16"                 # "PN16" | "PN40"
    wall_override: bool = False            # True → use wall_override_mm instead of table
    wall_override_mm: float = 3.2          # used when wall_override is True
    tube_size: str = "T25"                 # used when pipe_type == "Tubing"
    tube_wall: str = "2.0 mm wall"
    length_m: float = 10.0                 # run (horizontal) or height (vertical)
    orientation: str = "Horizontal"        # see ORIENTATIONS
    material: str = "SS316L"               # "SS316L" | "CS"
    lined: bool = False
    liner_material: str = "PTFE"
    liner_thickness_mm: float = 1.0
    fittings_list: list = field(default_factory=list)

    def dz(self) -> float:
        return ORIENT_SIGN.get(self.orientation, 0.0) * self.length_m


@dataclass
class Misc:
    kind: str = "misc"
    id: str = "m1"
    name: str = "Equipment ΔP"
    dp_kpa: float = 0.0                    # signed: + drops P, − adds P (pump)


_KIND_CLS = {"pipe": Pipe, "misc": Misc}


# ── dict <-> dataclass round-tripping ────────────────────────────────────────
def element_to_dict(el) -> dict:
    return asdict(el)


def section_from_dict(d: dict):
    """Rebuild a section dataclass (Pipe/Misc) from a plain dict."""
    cls = _KIND_CLS[d.get("kind", "pipe")]
    data = {k: v for k, v in d.items() if k in cls.__dataclass_fields__}
    return cls(**data)


def inlet_to_dict(inl: LineInlet) -> dict:
    return asdict(inl)


def inlet_from_dict(d: dict) -> LineInlet:
    data = {k: v for k, v in d.items() if k in LineInlet.__dataclass_fields__}
    fl = data.get("fluid") or {}
    if isinstance(fl, dict):
        fl = {k: v for k, v in fl.items() if k in FluidSpec.__dataclass_fields__}
        data["fluid"] = FluidSpec(**fl)
    return LineInlet(**data)


def default_inlet() -> dict:
    return inlet_to_dict(LineInlet(
        P_in_bara=10.0, T_C=25.0,
        fluid=FluidSpec(phase="liquid", liquid_type="Water", q_lye_m3h=50.0,
                        gas_flows_kgh={}, use_coolprop=True)))


def default_sections() -> list:
    return [
        element_to_dict(Pipe(
            id="p1", name="Section 1", dn="DN50", pn_class="PN16",
            length_m=20.0, orientation="Horizontal", material="SS316L",
            fittings_list=[{"type": "90° Standard Elbow", "qty": 2}])),
    ]
