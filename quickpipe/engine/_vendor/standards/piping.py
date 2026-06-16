"""
Piping standards lookup tables.

Sources:
    ASME B36.19M-2004       — stainless steel pipe schedules and bore dimensions
    Crane TP-410            — material roughness, fitting Le/D factors
    ASME B16.5-2017         — pressure-temperature class ratings
"""

# ── Pipe bore database — ASME B36.19M (stainless steel pipe) ─────────────────
# Inner diameters in metres, derived from OD − 2 × wall thickness.
# Schedule designations per ASME B36.19M:
#   5S  — Extra-light; instrument/low-pressure service
#   10S — Light-duty; low-pressure systems          (e.g. DN20: t = 2.11 mm)
#   40S — Standard; general water/gas distribution  (e.g. DN20: t = 2.87 mm)
#   80S — Heavy-duty; high-pressure fluid service   (e.g. DN20: t = 3.91 mm)
#
# OD (outside diameter, mm) per ASME B36.19M / B36.10M:
#   DN15=21.34  DN20=26.67  DN25=33.40  DN32=42.16  DN40=48.26
#   DN50=60.33  DN65=73.03  DN80=88.90  DN100=114.30 DN150=168.28
#   DN200=219.08 DN250=273.05
PIPE_DATABASE: dict[str, dict[str, float]] = {
    # DN15  OD 21.34 mm
    "DN15":  {"5S": 0.01804, "10S": 0.01712, "40S": 0.01580, "80S": 0.01388},
    # DN20  OD 26.67 mm
    "DN20":  {"5S": 0.02337, "10S": 0.02245, "40S": 0.02093, "80S": 0.01885},
    # DN25  OD 33.40 mm
    "DN25":  {"5S": 0.03010, "10S": 0.02786, "40S": 0.02664, "80S": 0.02430},
    # DN32  OD 42.16 mm
    "DN32":  {"5S": 0.03886, "10S": 0.03662, "40S": 0.03504, "80S": 0.03246},
    # DN40  OD 48.26 mm
    "DN40":  {"5S": 0.04496, "10S": 0.04272, "40S": 0.04090, "80S": 0.03810},
    # DN50  OD 60.33 mm
    "DN50":  {"5S": 0.05703, "10S": 0.05479, "40S": 0.05251, "80S": 0.04925},
    # DN65  OD 73.03 mm
    "DN65":  {"5S": 0.06881, "10S": 0.06693, "40S": 0.06271, "80S": 0.05901},
    # DN80  OD 88.90 mm
    "DN80":  {"5S": 0.08468, "10S": 0.08280, "40S": 0.07792, "80S": 0.07366},
    # DN100 OD 114.30 mm
    "DN100": {"5S": 0.11008, "10S": 0.10820, "40S": 0.10226, "80S": 0.09718},
    # DN150 OD 168.28 mm
    "DN150": {"5S": 0.16274, "10S": 0.16148, "40S": 0.15406, "80S": 0.14634},
    # DN200 OD 219.08 mm
    "DN200": {"5S": 0.21354, "10S": 0.21156, "40S": 0.20272, "80S": 0.19368},
    # DN250 OD 273.05 mm
    "DN250": {"5S": 0.26625, "10S": 0.26467, "40S": 0.25451, "80S": 0.24765},
}

# Nominal outside diameter (mm) per ASME B36.19M / B36.10M.
PIPE_OD_MM: dict[str, float] = {
    "DN15": 21.34, "DN20": 26.67, "DN25": 33.40, "DN32": 42.16,
    "DN40": 48.26, "DN50": 60.33, "DN65": 73.03, "DN80": 88.90,
    "DN100": 114.30, "DN150": 168.28, "DN200": 219.08, "DN250": 273.05,
}

# Human-readable schedule descriptions for UI tooltips.
SCHEDULE_DESCRIPTIONS: dict[str, str] = {
    "5S":  "Extra-light — instrument & low-pressure service",
    "10S": "Light-duty — low-pressure systems",
    "40S": "Standard — general water/gas distribution",
    "80S": "Heavy-duty — high-pressure fluid service",
}

# ── Swagelok metric SS tubing (316/316L seamless, OD × wall → ID) ────────────
# Inner diameters in metres.  Source: Swagelok catalog MS-01-181 (metric sizes).
# Ordering number pattern: SS-T{OD}M-S-{wall}M-6ME  (e.g. SS-T12M-S-2,0M-6ME)
TUBING_DATABASE: dict[str, dict[str, float]] = {
    "T3":  {"0.5 mm wall": 0.0020, "0.7 mm wall": 0.0016},
    "T6":  {"1.0 mm wall": 0.0040, "1.5 mm wall": 0.0030},
    "T8":  {"1.0 mm wall": 0.0060, "1.5 mm wall": 0.0050},
    "T10": {"1.0 mm wall": 0.0080, "1.5 mm wall": 0.0070},
    "T12": {"1.0 mm wall": 0.0100, "1.5 mm wall": 0.0090, "2.0 mm wall": 0.0080},
    "T16": {"1.0 mm wall": 0.0140, "1.5 mm wall": 0.0130, "2.0 mm wall": 0.0120},
    "T18": {"1.0 mm wall": 0.0160, "1.5 mm wall": 0.0150, "2.0 mm wall": 0.0140},
    "T20": {"2.0 mm wall": 0.0160},
    "T22": {"2.0 mm wall": 0.0180},
    "T25": {"2.0 mm wall": 0.0210, "2.5 mm wall": 0.0200},
}

# Absolute roughness (m) for seamless drawn SS instrument tubing.
# Swagelok SS-T catalog: Ra ≤ 0.8 µm → ε ≈ 1.5 µm (approx. 10× smoother than pipe).
TUBING_ROUGHNESS: float = 1.5e-6

# ── Absolute roughness (m) — Crane TP-410 / ASHRAE ──────────────────────────
MATERIAL_ROUGHNESS: dict[str, float] = {
    "SS316L":            1.5e-5,
    "Duplex SS 2205":    1.5e-5,
    "Carbon Steel":      4.6e-5,
    "Hastelloy C-276":   1.5e-5,
    "Titanium Gr. 2":    1.5e-5,
}

# Absolute roughness (m) for fluoropolymer pipe liners.
LINER_ROUGHNESS: dict[str, float] = {
    "PTFE":  5.0e-8,
    "FEP":   5.0e-8,
    "PFA":   5.0e-8,
    "PVDF":  1.5e-7,
}

# ── Fitting equivalent-length factors (Le/D) — Crane TP-410 ─────────────────
FITTING_Le_over_D: dict[str, int] = {
    "90° Standard Elbow":                    30,
    "90° Long Radius Elbow (1.5D)":          16,
    "45° Elbow":                             16,
    "180° Return Bend":                      50,
    "Tee — Branch Flow":                     60,
    "Tee — Run Through":                     20,
    "Gate Valve — Fully Open":                8,
    "Globe Valve — Fully Open":             340,
    "Ball Valve — Fully Open":                3,
    "Butterfly Valve":                       45,
    "Swing Check Valve":                    100,
    "Lift Check Valve":                     600,
    "Concentric Reducer — Gradual (15°)":     5,
    "Concentric Reducer — Sudden":           26,
    "Eccentric Reducer — Gradual (15°)":      5,
    "Expansion — Gradual (15°)":             10,
    "Expansion — Sudden":                    30,
}

# ── NPS (inches) → DN (mm) — ASME B36.10M standard designations ─────────────
_NPS_TO_DN: dict[float, int] = {
    0.5: 15, 0.75: 20, 1.0: 25, 1.25: 32, 1.5: 40,
    2.0: 50, 2.5: 65, 3.0: 80, 4.0: 100, 6.0: 150,
    8.0: 200, 10.0: 250, 12.0: 300,
}


def nps_to_dn(nps_inch: float) -> int:
    """Convert NPS (inches) to DN (mm). Returns nearest known DN."""
    return _NPS_TO_DN.get(nps_inch, round(nps_inch * 25.0))


# ── ASME B16.5-2017 pressure-temperature class ratings (barg at ≤ 38 °C) ────
# Tables 2-1.1, 2-2.2, 2-2.3, 2-1.4, 2-1.9
_B165_RATINGS: dict[str, dict[int, float]] = {
    "1.1 — Carbon steel (A105 / A106)": {
        150: 19.6, 300: 51.1, 600: 102.1,
        900: 153.2, 1500: 255.3, 2500: 425.5,
    },
    "2.3 — Stainless 316 / 316L": {
        150: 15.1, 300: 39.3, 600: 78.6,
        900: 117.9, 1500: 196.5, 2500: 327.6,
    },
    "2.2 — Stainless 304 / 304L": {
        150: 15.1, 300: 39.3, 600: 78.6,
        900: 117.9, 1500: 196.5, 2500: 327.6,
    },
    "1.4 — Low-temp carbon steel (A350 LF2)": {
        150: 19.6, 300: 51.1, 600: 102.1,
        900: 153.2, 1500: 255.3, 2500: 425.5,
    },
    "1.9 — Duplex SS (A182 F51)": {
        150: 20.0, 300: 51.1, 600: 102.1,
        900: 153.2, 1500: 255.3, 2500: 425.5,
    },
}

MATERIAL_GROUPS: list[str] = list(_B165_RATINGS.keys())


def ansi_class_lookup(P_design_barg: float, material_group: str) -> dict:
    """
    Return the lowest ANSI B16.5 pressure class adequate for P_design_barg.

    Returns dict with:
        class_number (int), class_label (str), rated_barg (float), adequate (bool),
        all_classes (list of dicts for table display)
    """
    ratings = _B165_RATINGS.get(material_group, list(_B165_RATINGS.values())[0])
    selected_class = None
    selected_rating = None

    all_classes = []
    for cls, rated in sorted(ratings.items()):
        adequate = rated >= P_design_barg
        all_classes.append({
            "Class":        f"ANSI {cls}",
            "Rated (barg)": rated,
            "Adequate":     "✓" if adequate else "✗",
        })
        if adequate and selected_class is None:
            selected_class  = cls
            selected_rating = rated

    if selected_class is None:
        selected_class  = 2500
        selected_rating = ratings[2500]

    return {
        "class_number": selected_class,
        "class_label":  f"ANSI {selected_class}",
        "rated_barg":   selected_rating,
        "adequate":     selected_rating >= P_design_barg,
        "all_classes":  all_classes,
    }


# ── Minimum ASME B16.5 flange class for PSV inlet (Group 1.1 CS at 38 °C) ──
# Class 300 is the industry minimum per API 526 practice.
_CLASS_LIMITS_BARA: list[tuple[int, float]] = [
    (300,   51.1),
    (600,  102.1),
    (900,  153.2),
    (1500, 255.2),
    (2500, 425.6),
]


def min_flange_class(P_bara: float) -> int:
    """Minimum ASME B16.5 flange class for the given inlet pressure (bara)."""
    for cls, limit in _CLASS_LIMITS_BARA:
        if P_bara <= limit:
            return cls
    return 2500


def sum_le_fit(seg: dict, D_eff: float) -> float:
    """Total equivalent pipe length (m) contributed by fittings in one segment.

    Accepts both the current format (``fittings_list`` list-of-dicts) and the
    legacy format (``fittings`` string + ``fitting_count`` int).
    """
    fl = seg.get("fittings_list")
    if fl is not None:
        total = 0.0
        for fit in fl:
            t = fit.get("type", "")
            q = fit.get("qty", 0)
            if t in FITTING_Le_over_D and q > 0:
                total += FITTING_Le_over_D[t] * D_eff * q
        return total
    f = seg.get("fittings", "None")
    c = seg.get("fitting_count", 0)
    if f in FITTING_Le_over_D and c > 0:
        return FITTING_Le_over_D[f] * D_eff * c
    return 0.0
