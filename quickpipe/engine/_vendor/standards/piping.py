"""
Piping standards lookup tables.

Sources:
    EN 10220:2002 / EN ISO 1127    — European pipe ODs and wall thickness basis
    EN 10216-2 / EN 10217-2        — Carbon steel seamless/welded pipe
    EN 10216-5 / EN 10217-7        — Stainless steel seamless/welded pipe
    Swagelok MS-01-181 (metric)    — 316SS instrument tubing
    Crane TP-410                   — material roughness, fitting Le/D factors
    ASME B16.5-2017                — pressure-temperature class ratings
"""

# ── EN Pipe OD table (EN 10220 Series 1 / EN ISO 1127) ───────────────────────
# Outside diameters in mm.
# CS     runs DN15 – DN300 (EN 10220 Series 1).
# SS316L runs DN15 – DN300 (EN 10220 / EN 10216-5 / EN 10217-7).
EN_PIPE_OD_MM: dict[str, dict[str, float]] = {
    "CS": {
        "DN15":  21.3,  "DN20":  26.9,  "DN25":  33.7,  "DN32":  42.4,
        "DN40":  48.3,  "DN50":  60.3,  "DN65":  76.1,  "DN80":  88.9,
        "DN100": 114.3, "DN125": 139.7, "DN150": 168.3,
        "DN200": 219.1, "DN250": 273.0, "DN300": 323.9,
    },
    "SS316L": {
        "DN15":  21.3,  "DN20":  26.9,  "DN25":  33.7,  "DN32":  42.4,
        "DN40":  48.3,  "DN50":  60.3,  "DN65":  76.1,  "DN80":  88.9,
        "DN100": 114.3, "DN125": 139.7, "DN150": 168.3, "DN200": 219.1,
        "DN250": 273.0, "DN300": 323.9,
    },
}

# ── EN Pipe wall thickness lookup table (project piping class) ────────────────
# Wall thickness in mm for [material][pn_class][dn].
# Basis:
#   CS      — EN 10220 Series 1 ODs; wall selected from corrosion-allowance-driven
#             process piping practice (1.0 mm CA, EN 10216-2/EN 10217-2 delivery).
#   SS316L  — EN ISO 1127 Series ODs; wall from EN ISO 1127 (zero corrosion allowance,
#             EN 10216-5/EN 10217-7 delivery).
# PN class applies to the piping class (flanges, fittings, valves per EN 1092-1).
# PN alone does NOT define pipe wall thickness — this table is a project lookup.
# Use wall override for project-specific piping class requirements.
EN_PIPE_WALL_MM: dict[str, dict[str, dict[str, float]]] = {
    "CS": {
        "PN16": {
            "DN15":  2.6, "DN20":  2.6, "DN25":  2.9, "DN32":  2.9,
            "DN40":  2.9, "DN50":  3.2, "DN65":  3.2, "DN80":  3.6,
            "DN100": 4.0, "DN125": 4.0, "DN150": 4.5,
            "DN200": 5.0, "DN250": 5.6, "DN300": 6.3,
        },
        "PN25": {
            "DN15":  2.9, "DN20":  2.9, "DN25":  3.6, "DN32":  3.6,
            "DN40":  3.6, "DN50":  4.0, "DN65":  4.0, "DN80":  4.5,
            "DN100": 5.0, "DN125": 5.0, "DN150": 5.6,
            "DN200": 6.3, "DN250": 7.1, "DN300": 8.0,
        },
        "PN40": {
            "DN15":  3.2, "DN20":  3.2, "DN25":  4.0, "DN32":  4.0,
            "DN40":  4.0, "DN50":  5.0, "DN65":  5.0, "DN80":  5.6,
            "DN100": 6.3, "DN125": 6.3, "DN150": 7.1,
            "DN200": 8.0, "DN250": 8.8, "DN300": 10.0,
        },
    },
    "SS316L": {
        "PN16": {
            "DN15":  1.6, "DN20":  1.6, "DN25":  1.6, "DN32":  1.6,
            "DN40":  1.6, "DN50":  2.0, "DN65":  2.0, "DN80":  2.0,
            "DN100": 2.0, "DN125": 2.0, "DN150": 2.0, "DN200": 3.2,
            "DN250": 3.6, "DN300": 4.0,
        },
        "PN25": {
            "DN15":  2.0, "DN20":  2.0, "DN25":  2.0, "DN32":  2.0,
            "DN40":  2.0, "DN50":  2.6, "DN65":  2.6, "DN80":  2.6,
            "DN100": 3.2, "DN125": 3.2, "DN150": 3.2, "DN200": 4.0,
            "DN250": 4.5, "DN300": 6.3,
        },
        "PN40": {
            "DN15":  2.0, "DN20":  2.0, "DN25":  2.6, "DN32":  2.6,
            "DN40":  2.6, "DN50":  3.2, "DN65":  3.2, "DN80":  3.2,
            "DN100": 4.0, "DN125": 4.0, "DN150": 4.0, "DN200": 5.0,
            "DN250": 6.3, "DN300": 8.0,
        },
    },
}

# PN class label descriptions for UI.
PN_DESCRIPTIONS: dict[str, str] = {
    "PN16": "PN16 — 16 bar rated system (flanges, fittings, valves per EN 1092-1)",
    "PN25": "PN25 — 25 bar rated system (flanges, fittings, valves per EN 1092-1)",
    "PN40": "PN40 — 40 bar rated system (flanges, fittings, valves per EN 1092-1)",
}

# ── 316SS metric tubing (Swagelok-style, OD × wall → metadata) ───────────────
# Keys: tube OD in mm (int-like str for legacy compat), then wall label.
# Inner dict: id_m (inner diameter, metres), order (Swagelok part number),
#             weight_kg_m (kg per metre), wp_bar (working pressure, bar), note.
# Pressure basis: ASME B31.3/B31.1, stress 137.8 MPa, tensile 516.4 MPa.
TUBING_DATABASE: dict[str, dict[str, dict]] = {
    "T3": {
        "0.5 mm wall": {"id_m": 0.0020, "order": "SS-T3M-S-0,5M-6ME",  "weight_kg_m": 0.021, "wp_bar": 330, "note": "Not recommended for use with Swagelok tube fittings."},
        "0.7 mm wall": {"id_m": 0.0016, "order": "SS-T3M-S-0,7M-6ME",  "weight_kg_m": 0.027, "wp_bar": 560, "note": ""},
    },
    "T6": {
        "1.0 mm wall": {"id_m": 0.0040, "order": "SS-T6M-S-1,0M-6ME",  "weight_kg_m": 0.125, "wp_bar": 420, "note": ""},
        "1.5 mm wall": {"id_m": 0.0030, "order": "SS-T6M-S-1,5M-6ME",  "weight_kg_m": 0.169, "wp_bar": 710, "note": ""},
    },
    "T8": {
        "1.0 mm wall": {"id_m": 0.0060, "order": "SS-T8M-S-1,0M-6ME",  "weight_kg_m": 0.175, "wp_bar": 310, "note": ""},
        "1.5 mm wall": {"id_m": 0.0050, "order": "SS-T8M-S-1,5M-6ME",  "weight_kg_m": 0.244, "wp_bar": 520, "note": ""},
    },
    "T10": {
        "1.0 mm wall": {"id_m": 0.0080, "order": "SS-T10M-S-1,0M-6ME", "weight_kg_m": 0.225, "wp_bar": 240, "note": ""},
        "1.5 mm wall": {"id_m": 0.0070, "order": "SS-T10M-S-1,5M-6ME", "weight_kg_m": 0.319, "wp_bar": 400, "note": ""},
    },
    "T12": {
        "1.0 mm wall": {"id_m": 0.0100, "order": "SS-T12M-S-1,0M-6ME", "weight_kg_m": 0.275, "wp_bar": 200, "note": ""},
        "1.5 mm wall": {"id_m": 0.0090, "order": "SS-T12M-S-1,5M-6ME", "weight_kg_m": 0.394, "wp_bar": 330, "note": ""},
        "2.0 mm wall": {"id_m": 0.0080, "order": "SS-T12M-S-2,0M-6ME", "weight_kg_m": 0.500, "wp_bar": 470, "note": ""},
    },
    "T16": {
        "1.0 mm wall": {"id_m": 0.0140, "order": "SS-T16M-S-1,0M-6ME", "weight_kg_m": 0.375, "wp_bar": 140, "note": "Not recommended for use with Swagelok tube fittings."},
        "1.5 mm wall": {"id_m": 0.0130, "order": "SS-T16M-S-1,5M-6ME", "weight_kg_m": 0.507, "wp_bar": 230, "note": ""},
        "2.0 mm wall": {"id_m": 0.0120, "order": "SS-T16M-S-2,0M-6ME", "weight_kg_m": 0.651, "wp_bar": 330, "note": ""},
    },
    "T18": {
        "1.0 mm wall": {"id_m": 0.0160, "order": "SS-T18M-S-1,0M-6ME", "weight_kg_m": 0.425, "wp_bar": 120, "note": "Not recommended for use with Swagelok tube fittings."},
        "1.5 mm wall": {"id_m": 0.0150, "order": "SS-T18M-S-1,5M-6ME", "weight_kg_m": 0.619, "wp_bar": 200, "note": ""},
        "2.0 mm wall": {"id_m": 0.0140, "order": "SS-T18M-S-2,0M-6ME", "weight_kg_m": 0.801, "wp_bar": 290, "note": ""},
    },
    "T20": {
        "2.0 mm wall": {"id_m": 0.0160, "order": "SS-T20M-S-2,0M-6ME", "weight_kg_m": 0.901, "wp_bar": 260, "note": ""},
    },
    "T22": {
        "2.0 mm wall": {"id_m": 0.0180, "order": "SS-T22M-S-2,0M-6ME", "weight_kg_m": 1.00,  "wp_bar": 230, "note": ""},
    },
    "T25": {
        "2.0 mm wall": {"id_m": 0.0210, "order": "SS-T25M-S-2,0M-6ME", "weight_kg_m": 1.15,  "wp_bar": 200, "note": "Not recommended for use with Swagelok tube fittings in gas service."},
        "2.5 mm wall": {"id_m": 0.0200, "order": "SS-T25M-S-2,5M-6ME", "weight_kg_m": 1.41,  "wp_bar": 260, "note": ""},
    },
}

# Absolute roughness (m) for seamless drawn SS instrument tubing.
TUBING_ROUGHNESS: float = 1.5e-6

# ── Absolute roughness (m) — Crane TP-410 / ASHRAE ──────────────────────────
MATERIAL_ROUGHNESS: dict[str, float] = {
    "SS316L":            1.5e-5,
    "CS":                4.6e-5,   # carbon steel (EN 10216-2 / EN 10217-2)
    "Carbon Steel":      4.6e-5,   # legacy alias
    "Duplex SS 2205":    1.5e-5,
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


def en_pipe_id_m(material: str, pn_class: str, dn: str,
                 wall_override: bool = False,
                 wall_override_mm: float = 0.0) -> float:
    """Return the EN pipe internal diameter in metres.

    Looks up OD from EN_PIPE_OD_MM and wall from EN_PIPE_WALL_MM, then
    computes ID = OD − 2 × wall.  If wall_override is True, uses
    wall_override_mm instead of the table value.
    """
    od_mm  = EN_PIPE_OD_MM[material][dn]
    if wall_override:
        wall_mm = wall_override_mm
    else:
        wall_mm = EN_PIPE_WALL_MM[material][pn_class][dn]
    return (od_mm - 2.0 * wall_mm) / 1000.0


# ── ASME pipe dimensions (B36.10M carbon/alloy, B36.19M stainless) ────────────
# Many engineers size lines in NPS + schedule. Outside diameters (mm) by NPS are
# shared by B36.10M and B36.19M, but note they differ slightly from the EN/ISO
# ODs for some sizes (e.g. 2-1/2" = 73.0 mm here vs DN65 = 76.1 mm in EN).
ASME_PIPE_OD_MM: dict[str, float] = {
    '1/2"':   21.3,  '3/4"':   26.7,  '1"':    33.4,  '1-1/4"': 42.2,
    '1-1/2"': 48.3,  '2"':     60.3,  '2-1/2"': 73.0, '3"':     88.9,
    '4"':    114.3,  '5"':    141.3,  '6"':   168.3,  '8"':    219.1,
    '10"':   273.0,  '12"':   323.9,
}

# Wall thickness (mm) by [material][nps][schedule].
#   CS     → ASME B36.10M (carbon/alloy steel) schedules
#   SS316L → ASME B36.19M (stainless) S-schedules
# STD and XS are kept separate from Sch 40 / Sch 80 because they diverge at the
# large end: STD caps at 9.53 mm (≥12"), XS caps at 12.70 mm (≥10"), whereas
# Sch 40 / Sch 80 keep climbing.
ASME_WALL_MM: dict[str, dict[str, dict[str, float]]] = {
    "CS": {
        '1/2"':   {"Sch 10": 2.11, "Sch 40": 2.77, "STD": 2.77, "Sch 80": 3.73, "XS": 3.73, "Sch 160": 4.78,  "XXS": 7.47},
        '3/4"':   {"Sch 10": 2.11, "Sch 40": 2.87, "STD": 2.87, "Sch 80": 3.91, "XS": 3.91, "Sch 160": 5.56,  "XXS": 7.82},
        '1"':     {"Sch 10": 2.77, "Sch 40": 3.38, "STD": 3.38, "Sch 80": 4.55, "XS": 4.55, "Sch 160": 6.35,  "XXS": 9.09},
        '1-1/4"': {"Sch 10": 2.77, "Sch 40": 3.56, "STD": 3.56, "Sch 80": 4.85, "XS": 4.85, "Sch 160": 6.35,  "XXS": 9.70},
        '1-1/2"': {"Sch 10": 2.77, "Sch 40": 3.68, "STD": 3.68, "Sch 80": 5.08, "XS": 5.08, "Sch 160": 7.14,  "XXS": 10.15},
        '2"':     {"Sch 10": 2.77, "Sch 40": 3.91, "STD": 3.91, "Sch 80": 5.54, "XS": 5.54, "Sch 160": 8.74,  "XXS": 11.07},
        '2-1/2"': {"Sch 10": 3.05, "Sch 40": 5.16, "STD": 5.16, "Sch 80": 7.01, "XS": 7.01, "Sch 160": 9.53,  "XXS": 14.02},
        '3"':     {"Sch 10": 3.05, "Sch 40": 5.49, "STD": 5.49, "Sch 80": 7.62, "XS": 7.62, "Sch 160": 11.13, "XXS": 15.24},
        '4"':     {"Sch 10": 3.05, "Sch 40": 6.02, "STD": 6.02, "Sch 80": 8.56, "XS": 8.56, "Sch 160": 13.49, "XXS": 17.12},
        '5"':     {"Sch 10": 3.40, "Sch 40": 6.55, "STD": 6.55, "Sch 80": 9.53, "XS": 9.53, "Sch 160": 15.88, "XXS": 19.05},
        '6"':     {"Sch 10": 3.40, "Sch 40": 7.11, "STD": 7.11, "Sch 80": 10.97, "XS": 10.97, "Sch 160": 18.26, "XXS": 21.95},
        '8"':     {"Sch 10": 3.76, "Sch 40": 8.18, "STD": 8.18, "Sch 80": 12.70, "XS": 12.70, "Sch 160": 23.01, "XXS": 22.23},
        '10"':    {"Sch 10": 4.19, "Sch 40": 9.27, "STD": 9.27, "Sch 80": 15.09, "XS": 12.70, "Sch 160": 28.58, "XXS": 25.40},
        '12"':    {"Sch 10": 4.57, "Sch 40": 10.31, "STD": 9.53, "Sch 80": 17.48, "XS": 12.70, "Sch 160": 33.32, "XXS": 25.40},
    },
    "SS316L": {
        '1/2"':   {"5S": 1.65, "10S": 2.11, "40S": 2.77, "80S": 3.73},
        '3/4"':   {"5S": 1.65, "10S": 2.11, "40S": 2.87, "80S": 3.91},
        '1"':     {"5S": 1.65, "10S": 2.77, "40S": 3.38, "80S": 4.55},
        '1-1/4"': {"5S": 1.65, "10S": 2.77, "40S": 3.56, "80S": 4.85},
        '1-1/2"': {"5S": 1.65, "10S": 2.77, "40S": 3.68, "80S": 5.08},
        '2"':     {"5S": 1.65, "10S": 2.77, "40S": 3.91, "80S": 5.54},
        '2-1/2"': {"5S": 2.11, "10S": 3.05, "40S": 5.16, "80S": 7.01},
        '3"':     {"5S": 2.11, "10S": 3.05, "40S": 5.49, "80S": 7.62},
        '4"':     {"5S": 2.11, "10S": 3.05, "40S": 6.02, "80S": 8.56},
        '5"':     {"5S": 2.77, "10S": 3.40, "40S": 6.55, "80S": 9.53},
        '6"':     {"5S": 2.77, "10S": 3.40, "40S": 7.11, "80S": 10.97},
        '8"':     {"5S": 2.77, "10S": 3.76, "40S": 8.18, "80S": 12.70},
        '10"':    {"5S": 3.40, "10S": 4.19, "40S": 9.27, "80S": 12.70},
        '12"':    {"5S": 3.96, "10S": 4.57, "40S": 9.53, "80S": 12.70},
    },
}

# Schedule pick-lists per material (thin → thick), and human-readable notes.
ASME_CS_SCHEDULES: list[str] = ["Sch 10", "Sch 40", "STD", "Sch 80", "XS", "Sch 160", "XXS"]
ASME_SS_SCHEDULES: list[str] = ["5S", "10S", "40S", "80S"]
ASME_SCHEDULE_DESCRIPTIONS: dict[str, str] = {
    "Sch 10":  "Sch 10 — light wall, large-bore economy / low pressure",
    "Sch 40":  'Sch 40 — general service (= STD up to 10")',
    "STD":     'Standard wall (= Sch 40 up to 10"; caps at 9.53 mm)',
    "Sch 80":  'Sch 80 — higher pressure (= XS up to 8")',
    "XS":      'Extra Strong (= Sch 80 up to 8"; caps at 12.70 mm)',
    "Sch 160": "Sch 160 — high pressure",
    "XXS":     "Double Extra Strong — heaviest wall",
    "5S":      "B36.19M 5S — extra-light stainless",
    "10S":     "B36.19M 10S — light stainless",
    "40S":     "B36.19M 40S — standard stainless",
    "80S":     "B36.19M 80S — heavy stainless",
}


def asme_pipe_id_m(material: str, nps: str, schedule: str) -> float:
    """Return the ASME pipe internal diameter in metres (ID = OD − 2 × wall)."""
    od_mm   = ASME_PIPE_OD_MM[nps]
    wall_mm = ASME_WALL_MM[material][nps][schedule]
    return (od_mm - 2.0 * wall_mm) / 1000.0
