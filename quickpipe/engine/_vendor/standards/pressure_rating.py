"""EN 13480-3 pressure-rating helpers: minimum wall, pressure rating, and a
"snap to a real EN ISO 1127 wall" recommender.

Why the snap matters
--------------------
The hoop-stress formula alone gives structurally absurd (sub-millimetre) walls
for moderate pressures — e.g. SS316L DN50 at 20 barg / 100 °C needs only ~0.5 mm
to *contain* the pressure. Nobody installs 0.5 mm pipe: it can't be handled,
welded, supported, or threaded. So ``recommend_wall`` always snaps the
calculated minimum UP to the nearest standard EN ISO 1127 wall for the size, and
never below the lightest standard wall (the structural floor). The pressure math
only governs once P/T is high enough to climb above that floor.

Formulas (EN 13480-3, metallic industrial piping)
-------------------------------------------------
Minimum wall, straight pipe under internal pressure (clause 6.1):

    e = (P_c · D_o) / (2 · f · z + P_c)

    e   = minimum required wall (mm)
    P_c = calculation (design) pressure (MPa, gauge)
    D_o = outside diameter (mm)
    f   = allowable design stress (MPa) at design temperature
    z   = weld joint coefficient (1.0 seamless / fully-radiographed weld)

Allowable design stress f (clause 5):

    austenitic stainless (A ≥ 30 %, e.g. 1.4404):  f = Rp1.0(T) / 1.5
    ferritic carbon steel (e.g. P235GH):           f = min(Rp0.2(T)/1.5, Rm/2.4)

The conservative austenitic branch (Rp1.0/1.5) is used — it errs thicker, which
is the safe direction for a guidance tool.

Proof-strength vs temperature data: EN 10216-5 grade 1.4404 (SS316L) and
EN 10216-2 grade P235GH (CS). Values are linearly interpolated between table
points and clamped beyond the ends.
"""
from __future__ import annotations

# ── Proof strength vs temperature (MPa) ──────────────────────────────────────
# SS316L / 1.4404 — 1.0 % proof strength Rp1.0 (EN 10216-5 / EN 10088-3).
_SS316L_RP10: dict[int, float] = {
    20: 225, 100: 200, 150: 180, 200: 165, 250: 153,
    300: 145, 350: 139, 400: 135, 450: 130, 500: 128, 550: 127,
}
# CS / P235GH — 0.2 % proof strength Rp0.2 (EN 10216-2).
_CS_RP02: dict[int, float] = {
    20: 235, 100: 198, 150: 187, 200: 170, 250: 152,
    300: 132, 350: 120, 400: 112, 450: 108,
}
_CS_RM = 360.0  # P235GH tensile strength Rm (MPa), minimum

# ── EN ISO 1127 light Serie-1 stock walls per OD (mm) — the structural floor ──
# Verbatim from a real ISO 1127 Serie 1 (304L/316L) tube catalogue
# (gillain.com/en/tubes-and-components ... industrial-tubes-iso-1127). This is
# the *light commercial* range; its lightest wall per size sets the structural
# floor (the "don't go thinner than real tube" guard).
_ISO_1127_SERIE1: dict[str, list[float]] = {
    "DN15":  [1.6, 2.0, 2.6],
    "DN20":  [1.6, 2.0, 2.6],
    "DN25":  [1.6, 2.0, 3.2],
    "DN32":  [1.6, 2.0, 3.2],
    "DN40":  [1.6, 2.0, 3.2],
    "DN50":  [1.6, 2.0, 3.6],
    "DN65":  [1.6, 2.0, 3.6],
    "DN80":  [1.6, 2.0, 4.0],
    "DN100": [2.0],
    "DN125": [2.0],
    "DN150": [2.0],
    "DN200": [2.0],
    "DN250": [2.6, 3.6],
    "DN300": [3.6, 4.5],
}

# ── Standard wall ladder per DN (mm), used for snapping ───────────────────────
# Light end = ISO 1127 Serie-1 stock above (so the floor matches real tube);
# heavier rungs are the same-OD EN 10216-5 / EN 10217-7 *pressure-pipe* walls
# (ISO 4200 series), so when pressure governs the recommendation still lands on
# a wall that is actually manufactured. SS316L and CS share this OD/wall grid.
# DN250/DN300 walls from EN 10220 / EN 10216-5 (SS316L and CS).
EN_ISO_1127_WALLS: dict[str, list[float]] = {
    "DN15":  [1.6, 2.0, 2.6, 3.2],
    "DN20":  [1.6, 2.0, 2.6, 3.2],
    "DN25":  [1.6, 2.0, 2.6, 3.2, 4.0],
    "DN32":  [1.6, 2.0, 2.6, 3.2, 4.0],
    "DN40":  [1.6, 2.0, 2.6, 3.2, 4.0],
    "DN50":  [1.6, 2.0, 2.9, 3.6, 4.0, 5.0],
    "DN65":  [1.6, 2.0, 2.9, 3.6, 5.0],
    "DN80":  [1.6, 2.0, 2.6, 3.2, 4.0, 5.0, 5.6],
    "DN100": [2.0, 2.6, 3.6, 4.5, 6.3],
    "DN125": [2.0, 2.6, 3.6, 4.0, 5.0, 6.3],
    "DN150": [2.0, 2.6, 3.6, 4.5, 6.3, 7.1],
    "DN200": [2.0, 2.6, 3.6, 4.5, 6.3, 8.0],
    "DN250": [2.6, 3.6, 4.5, 6.3, 8.0],
    "DN300": [3.6, 4.5, 6.3, 8.0],
}

# ── ISO 1127 Series 2 & 3 — supplementary metric-OD tube (OD mm → wall mm) ─────
# EN ISO 1127 sorts tube ODs into three preference series (selected from
# ISO 4200). Series 1 is the pipe-OD family handled above (EN_PIPE_OD_MM /
# EN_ISO_1127_WALLS). Series 2 & 3 are supplementary *metric* ODs supplied in
# thin fixed walls — small-bore instrument/utility tube plus a few mid sizes.
# Real commercial sizes from a 304L/316L ISO 1127 catalogue (gillain.com).
ISO_1127_SERIES_2: dict[float, float] = {
    6.0: 1.0, 8.0: 1.0, 10.0: 1.0, 16.0: 1.0, 57.0: 2.0, 70.0: 2.0,
}
ISO_1127_SERIES_3: dict[float, float] = {
    30.0: 2.0, 44.5: 2.0, 54.0: 2.0,
}

ISO_1127_SERIES_DESCRIPTIONS: dict[int, str] = {
    1: ("Series 1 — pipe-size ODs (inch-derived, match DN/NPS pipe, 21.3–323.9 mm). "
        "First-choice series for process piping: connects to pipe-size flanges and "
        "fittings. Walls run from light hygienic tube up to heavy pressure-pipe walls "
        "— this is what the wall-thickness check above sizes."),
    2: ("Series 2 — supplementary metric ODs. Small-bore 6–16 mm for instrument, "
        "impulse, sample and utility lines, plus a few larger metric sizes (57, 70 mm). "
        "Thin fixed walls (~1.0–2.0 mm); use when a metric OD outside the pipe series "
        "is required."),
    3: ("Series 3 — further supplementary metric ODs (30, 44.5, 54 mm). Least-preferred "
        "series: intermediate metric sizes for mechanical/equipment connections and "
        "metric-spec tube. Thin fixed walls (~2.0 mm)."),
}

# Default EN ISO 1127 mill under-tolerance on wall (class T2, ±12.5 %): the
# thinnest delivered wall = nominal · (1 − tol). Conservative for seamless.
DEFAULT_MILL_TOL = 0.125


def _interp(table: dict[int, float], T_C: float) -> float:
    """Linear interpolation of a {temp: value} table, clamped at both ends."""
    ts = sorted(table)
    if T_C <= ts[0]:
        return table[ts[0]]
    if T_C >= ts[-1]:
        return table[ts[-1]]
    for a, b in zip(ts, ts[1:]):
        if a <= T_C <= b:
            return table[a] + (table[b] - table[a]) * (T_C - a) / (b - a)
    return table[ts[-1]]


def allowable_stress_mpa(material: str, T_C: float) -> float:
    """EN 13480-3 allowable design stress f (MPa) at design temperature."""
    if material == "CS":
        return min(_interp(_CS_RP02, T_C) / 1.5, _CS_RM / 2.4)
    # SS316L (default): conservative austenitic branch Rp1.0/1.5.
    return _interp(_SS316L_RP10, T_C) / 1.5


def t_pressure_min_mm(P_barg: float, od_mm: float, material: str, T_C: float,
                      z: float = 1.0) -> float:
    """EN 13480-3 minimum wall e (mm) to contain P_barg at T_C — pressure only."""
    Pc = P_barg / 10.0                       # bar → MPa (1 bar = 0.1 MPa)
    f = allowable_stress_mpa(material, T_C)
    return (Pc * od_mm) / (2.0 * f * z + Pc)


def pressure_rating_barg(wall_mm: float, od_mm: float, material: str, T_C: float,
                         z: float = 1.0) -> float:
    """Inverse of the EN 13480-3 formula: max pressure (barg) a wall can hold.

    ``wall_mm`` is the *effective* wall actually resisting pressure (i.e. after
    corrosion allowance and mill tolerance have been removed)."""
    if wall_mm <= 0 or wall_mm >= od_mm:
        return 0.0
    f = allowable_stress_mpa(material, T_C)
    Pc = (2.0 * f * z * wall_mm) / (od_mm - wall_mm)   # MPa
    return Pc * 10.0                                    # MPa → bar


def recommend_wall(material: str, dn: str, od_mm: float, P_barg: float, T_C: float,
                   *, corrosion_allow_mm: float = 0.0, weld_factor: float = 1.0,
                   mill_tol_frac: float = DEFAULT_MILL_TOL) -> dict:
    """Recommend a real EN ISO 1127 wall for the service.

    Returns a dict describing the full chain: the pressure-only minimum, the
    required ordered wall (incl. corrosion allowance grossed up for mill
    under-tolerance), the structural floor (lightest standard wall), which of the
    two governs, the recommended standard wall, and that wall's pressure rating.
    """
    e_press = t_pressure_min_mm(P_barg, od_mm, material, T_C, weld_factor)
    # Ordered nominal wall must still leave e_press after losing the corrosion
    # allowance and the mill under-tolerance.
    t_required = (e_press + corrosion_allow_mm) / (1.0 - mill_tol_frac)

    walls = EN_ISO_1127_WALLS.get(dn, [])
    floor = walls[0] if walls else 0.0
    governing = max(t_required, floor)
    governed_by = "pressure + allowances" if t_required >= floor else "structural floor"

    # Snap UP to the thinnest standard wall ≥ governing; if none is thick enough,
    # fall back to the heaviest in the ladder and flag it (caller sees rating).
    rec = next((w for w in walls if w >= governing - 1e-9),
               walls[-1] if walls else governing)
    ladder_exceeded = bool(walls) and governing > walls[-1] + 1e-9

    e_eff = rec * (1.0 - mill_tol_frac) - corrosion_allow_mm
    p_rated = pressure_rating_barg(e_eff, od_mm, material, T_C, weld_factor)

    return {
        "f_mpa": allowable_stress_mpa(material, T_C),
        "e_pressure_mm": e_press,
        "t_required_mm": t_required,
        "floor_mm": floor,
        "governed_by": governed_by,
        "recommended_wall_mm": rec,
        "p_rated_barg": p_rated,
        "ladder_exceeded": ladder_exceeded,
        "walls": list(walls),
    }
