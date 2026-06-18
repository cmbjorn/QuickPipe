"""Pure-Python engine smoke tests (no Streamlit).

Run:  python -m quickpipe._smoke_test
"""
from __future__ import annotations

import math

from quickpipe.engine import (
    FluidSpec, LineInlet, Pipe, Misc, march, suggest_dn, SizingCriteria)
from quickpipe.engine.fluids import props_at
from quickpipe.engine.march import _insitu_density, G, pipe_geometry
import multiphase_engine as E
from standards.piping import (
    EN_PIPE_OD_MM, EN_PIPE_WALL_MM, TUBING_DATABASE, en_pipe_id_m,
    ASME_PIPE_OD_MM, ASME_WALL_MM, asme_pipe_id_m)
from standards.pressure_rating import (
    allowable_stress_mpa, t_pressure_min_mm, pressure_rating_barg,
    recommend_wall, EN_ISO_1127_WALLS, _ISO_1127_SERIE1,
    ISO_1127_SERIES_2, ISO_1127_SERIES_3, ISO_1127_SERIES_DESCRIPTIONS)
from physics.friction import churchill_f

_PASS = "\033[92mPASS\033[0m"
_FAIL = "\033[91mFAIL\033[0m"
_n_fail = 0


def check(name, cond, detail=""):
    global _n_fail
    print(f"  [{_PASS if cond else _FAIL}] {name}" + (f"  — {detail}" if detail else ""))
    if not cond:
        _n_fail += 1


def water(q_m3h=50.0):
    return FluidSpec(phase="liquid", liquid_type="Water", q_lye_m3h=q_m3h,
                     gas_flows_kgh={}, use_coolprop=True)


def gas(air_kgh=100.0):
    return FluidSpec(phase="gas", liquid_type="Water", q_lye_m3h=0.0,
                     gas_flows_kgh={"Air": air_kgh}, use_coolprop=True)


def inlet(fluid, P=10.0, T=25.0):
    return LineInlet(P_in_bara=P, T_C=T, fluid=fluid)


def row_for(res, name):
    return next(r for r in res.rows if r.element == name)


# 1. Liquid line friction vs hand Darcy-Weisbach --------------------------------
print("1. Liquid section ΔP (water, DN50/SS316L/PN16, 100 m, Δz=0)")
res = march(inlet(water(50.0)), [Pipe(id="p", name="P", dn="DN50", pn_class="PN16",
                                      material="SS316L", length_m=100.0)])
r = row_for(res, "P")
props = props_at(water(50.0), 10e5, 25.0)
D = en_pipe_id_m("SS316L", "PN16", "DN50")
A = math.pi * D**2 / 4
V = props["m_total_kgs"] / props["rho_l"] / A
Re = props["rho_l"] * V * D / props["mu_l"]
f = churchill_f(Re, 1.5e-5 / D)
dp_hand = f * 100.0 / D * 0.5 * props["rho_l"] * V**2 / 1000.0
check("ΔP_fric ~ hand Darcy (±12%)", abs(r.dp_fric_kpa - dp_hand) / dp_hand < 0.12,
      f"engine {r.dp_fric_kpa:.2f} vs hand {dp_hand:.2f} kPa")
check("ΔP_grav ≈ 0", abs(r.dp_grav_kpa) < 1e-6)
check("section #1 inlet == line inlet", abs(r.p_in_bara - 10.0) < 1e-9)
check("result.inlet_P_bara == 10", abs(res.inlet_P_bara - 10.0) < 1e-9)

# 2. Gas section ---------------------------------------------------------------
print("2. Gas section (air, DN25/SS316L/PN16, 50 m)")
res = march(inlet(gas(100.0)), [Pipe(id="p", name="G", dn="DN25", pn_class="PN16",
                                     material="SS316L", length_m=50.0)])
r = row_for(res, "G")
check("friction > 0 and P_out < P_in", r.dp_fric_kpa > 0 and r.p_out_bara < r.p_in_bara)
check("regime is single-phase gas", "gas" in r.regime.lower(), r.regime)

# 3. Elevation sign + magnitude (vertical section = elevation change) ----------
print("3. Vertical sections (water, 10 m up / down)")
props = props_at(water(50.0), 10e5, 25.0)
exp = props["rho_l"] * G * 10.0 / 1000.0
for orient, sgn in (("Vertical Upflow", +1), ("Vertical Downflow", -1)):
    res = march(inlet(water(50.0)),
                [Pipe(id="p", name="R", dn="DN50", pn_class="PN16", material="SS316L",
                      length_m=10.0, orientation=orient)])
    r = row_for(res, "R")
    check(f"ΔP_grav {orient}", abs(r.dp_grav_kpa - sgn * exp) < 0.5,
          f"{r.dp_grav_kpa:.2f} vs {sgn*exp:.2f} kPa")

# 4. No double-count (vertical riser, L_eff ≫ height) --------------------------
print("4. No gravity double-count (vertical, L_eff ≫ height)")
fit = [{"type": "90° Standard Elbow", "qty": 20}]
p = Pipe(id="p", name="F", dn="DN50", pn_class="PN16", material="SS316L",
         length_m=5.0, orientation="Vertical Upflow", fittings_list=fit)
_, _, le = pipe_geometry(p)
res = march(inlet(water(50.0)), [p])
r = row_for(res, "F")
exp5 = props["rho_l"] * G * 5.0 / 1000.0
check("L_eff ≫ height (fittings add)", le > 5 * p.length_m)
check("ΔP_grav uses geometric height only", abs(r.dp_grav_kpa - exp5) < 0.5,
      f"{r.dp_grav_kpa:.2f} vs {exp5:.2f} kPa")

# 5. Misc ±ΔP ------------------------------------------------------------------
print("5. Misc ±ΔP section")
res = march(inlet(water(50.0)),
            [Misc(id="m1", name="Valve", dp_kpa=50.0), Misc(id="m2", name="Pump", dp_kpa=-30.0)])
rv, rp = row_for(res, "Valve"), row_for(res, "Pump")
check("valve drops 50 kPa", abs((rv.p_in_bara - rv.p_out_bara) * 100 - 50) < 1e-3)
check("pump adds 30 kPa", abs((rp.p_out_bara - rp.p_in_bara) * 100 - 30) < 1e-3)
check("flow unchanged across misc", abs(rv.flow_kgh - rp.flow_kgh) < 1e-6)

# 6. March continuity ----------------------------------------------------------
print("6. March continuity (outlet of each = inlet of next)")
res = march(inlet(water(50.0)), [
    Pipe(id="p1", name="A", dn="DN50", pn_class="PN16", material="SS316L", length_m=10.0),
    Misc(id="m", name="HX", dp_kpa=20.0),
    Pipe(id="p2", name="B", dn="DN50", pn_class="PN16", material="SS316L", length_m=10.0)])
ok = all(abs(res.rows[i].p_in_bara - res.rows[i-1].p_out_bara) < 1e-9
         for i in range(1, len(res.rows)))
check("each section inlet == previous outlet", ok)
check("outlet == last section P_out", abs(res.outlet_P_bara - res.rows[-1].p_out_bara) < 1e-9)
check("only sections in rows (no source/sink)", len(res.rows) == 3)

# 7. Two-phase -----------------------------------------------------------------
print("7. Two-phase (air + water, Beggs-Brill)")
tp = FluidSpec(phase="two-phase", liquid_type="Water", q_lye_m3h=5.0,
               gas_flows_kgh={"Air": 60.0}, use_coolprop=True)
res = march(inlet(tp), [Pipe(id="p", name="TP", dn="DN50", pn_class="PN16",
                              material="SS316L", length_m=30.0)],
            correlation="Beggs-Brill")
r = row_for(res, "TP")
pr = props_at(tp, 10e5, 25.0)
check("two-phase quality 0<x<1", 0 < pr["x_gas"] < 1, f"x={pr['x_gas']:.4f}")
check("regime reported & ΔP_fric>0", bool(r.regime) and r.dp_fric_kpa > 0, r.regime)

# 8. KOH -----------------------------------------------------------------------
print("8. KOH solution")
koh = FluidSpec(phase="liquid", liquid_type="KOH solution", koh_conc_wt_pct=30.0,
                q_lye_m3h=40.0, gas_flows_kgh={}, use_coolprop=True)
prk = props_at(koh, 10e5, 60.0)
res = march(inlet(koh, T=60.0), [Pipe(id="p", name="K", dn="DN50", pn_class="PN16",
                                       material="SS316L", length_m=20.0)])
check("KOH denser than water & runs", prk["rho_l"] > 1100 and row_for(res, "K").dp_fric_kpa > 0,
      f"ρ_l={prk['rho_l']:.1f}")

# 9. suggest_dn ----------------------------------------------------------------
print("9. Auto-DN suggestion")
out = suggest_dn(water(80.0), 10e5, 25.0, pn_class="PN16", material="SS316L",
                 criteria=SizingCriteria(v_max=3.0, dp_per_100m_max=50.0))
vs = [r["V (m/s)"] for r in out["table"]]
check("velocity decreases with larger DN", all(vs[i] >= vs[i+1] for i in range(len(vs)-1)))
check("a DN is recommended", out["recommended_dn"] is not None, str(out["recommended_dn"]))

# 10. EN piping data spot-checks -----------------------------------------------
print("10. EN piping data spot-checks")
# DN50/SS316L/PN16 → OD=60.3mm, t=2.0mm → ID=56.3mm
check("DN50/SS316L OD = 60.3 mm", abs(EN_PIPE_OD_MM["SS316L"]["DN50"] - 60.3) < 0.01)
check("DN50/SS316L/PN16 wall = 2.0 mm", abs(EN_PIPE_WALL_MM["SS316L"]["PN16"]["DN50"] - 2.0) < 0.01)
id_ss_pn16 = en_pipe_id_m("SS316L", "PN16", "DN50")
check("DN50/SS316L/PN16 ID = 56.3 mm", abs(id_ss_pn16 * 1000 - 56.3) < 0.1,
      f"got {id_ss_pn16*1000:.1f} mm")
# DN50/CS/PN40 → OD=60.3mm, t=5.0mm → ID=50.3mm
id_cs_pn40 = en_pipe_id_m("CS", "PN40", "DN50")
check("DN50/CS/PN40 ID = 50.3 mm", abs(id_cs_pn40 * 1000 - 50.3) < 0.1,
      f"got {id_cs_pn40*1000:.1f} mm")
# CS has DN300, SS316L does not
check("CS DN list has DN300", "DN300" in EN_PIPE_OD_MM["CS"])
check("SS316L DN list has no DN300", "DN300" not in EN_PIPE_OD_MM["SS316L"])
# PN40 wall always ≥ PN16 wall for same material/DN
wall_errs = []
for mat in ("CS", "SS316L"):
    for dn in EN_PIPE_WALL_MM[mat]["PN16"]:
        t16 = EN_PIPE_WALL_MM[mat]["PN16"][dn]
        t40 = EN_PIPE_WALL_MM[mat]["PN40"][dn]
        if t40 < t16:
            wall_errs.append(f"{mat}/{dn}: PN40={t40} < PN16={t16}")
check("PN40 wall ≥ PN16 wall for all DN/material", not wall_errs,
      ", ".join(wall_errs) if wall_errs else "")

# 11. Tubing march + dict access + weight/pressure -----------------------------
print("11. Tubing march and ΔP_fit (minor losses)")
tw = FluidSpec(phase="liquid", liquid_type="Water", q_lye_m3h=2.0,
               gas_flows_kgh={}, use_coolprop=True)
tube = Pipe(id="t", name="T", pipe_type="Tubing", tube_size="T16", tube_wall="1.5 mm wall",
            length_m=5.0, orientation="Horizontal",
            fittings_list=[{"type": "90° Standard Elbow", "qty": 2}])
res = march(inlet(tw), [tube])
r = row_for(res, "T")
tdata = TUBING_DATABASE["T16"]["1.5 mm wall"]
expected_id = tdata["id_m"] * 1000
check("tubing ID correct", abs(r.id_mm - expected_id) < 0.01,
      f"got {r.id_mm:.1f} mm, expected {expected_id:.1f} mm")
check("tubing dp_fric > 0", r.dp_fric_kpa > 0)
check("dp_fit > 0 when fittings present", r.dp_fit_kpa > 0,
      f"dp_fit={r.dp_fit_kpa:.3f} kPa")
check("dp_fit < dp_fric", r.dp_fit_kpa < r.dp_fric_kpa)
check("tubing dict has weight_kg_m", tdata.get("weight_kg_m", 0) > 0,
      f"weight={tdata.get('weight_kg_m')}")
check("tubing dict has wp_bar", tdata.get("wp_bar", 0) > 0,
      f"wp_bar={tdata.get('wp_bar')}")

# 12. dp_fit = 0 with no fittings ----------------------------------------------
print("12. ΔP_fit = 0 when no fittings")
res_nf = march(inlet(water(50.0)),
               [Pipe(id="p", name="NF", dn="DN80", pn_class="PN16",
                     material="SS316L", length_m=20.0)])
check("dp_fit is zero (no fittings)", row_for(res_nf, "NF").dp_fit_kpa == 0.0)

# 13. EN 13480-3 pressure rating + allowable stress -----------------------------
print("13. EN 13480-3 pressure rating")
# SS316L allowable stress at 100 C = Rp1.0(100)/1.5 = 200/1.5 = 133.3 MPa
check("SS316L f(100C) = 133.3 MPa", abs(allowable_stress_mpa("SS316L", 100.0) - 133.33) < 0.5,
      f"got {allowable_stress_mpa('SS316L', 100.0):.1f}")
# Allowable stress decreases with temperature
check("f decreases with temperature", allowable_stress_mpa("SS316L", 300.0) < allowable_stress_mpa("SS316L", 100.0))
# pressure_rating is the exact inverse of t_pressure_min
od50 = EN_PIPE_OD_MM["SS316L"]["DN50"]
e = t_pressure_min_mm(20.0, od50, "SS316L", 100.0)
p_back = pressure_rating_barg(e, od50, "SS316L", 100.0)
check("rating(t_min(P)) round-trips to P", abs(p_back - 20.0) < 0.05, f"got {p_back:.3f} barg")

# 14. Wall recommendation — structural floor vs pressure governing --------------
print("14. Wall recommendation (no paper-thin pipe)")
# H2 case: 20 barg / 100 C on DN50 SS316L → pressure ~0.45 mm, floor must govern
rH2 = recommend_wall("SS316L", "DN50", od50, 20.0, 100.0)
check("H2 20barg/100C governed by structural floor", rH2["governed_by"] == "structural floor",
      rH2["governed_by"])
check("recommended wall = lightest ISO 1127 wall (1.6 mm)", abs(rH2["recommended_wall_mm"] - 1.6) < 1e-9,
      f"got {rH2['recommended_wall_mm']} mm")
check("recommended wall NOT paper-thin (≥ 1.5 mm)", rH2["recommended_wall_mm"] >= 1.5)
check("recommended wall rated above design P", rH2["p_rated_barg"] > 20.0,
      f"{rH2['p_rated_barg']:.0f} barg")
# High pressure: 150 barg / 200 C → pressure must govern and snap to a heavier wall
rHP = recommend_wall("SS316L", "DN50", od50, 150.0, 200.0)
check("150barg/200C governed by pressure", rHP["governed_by"] == "pressure + allowances",
      rHP["governed_by"])
check("high-pressure wall thicker than floor", rHP["recommended_wall_mm"] > rH2["recommended_wall_mm"],
      f"{rHP['recommended_wall_mm']} mm")
check("recommended wall is a real ISO 1127 wall", rHP["recommended_wall_mm"] in EN_ISO_1127_WALLS["DN50"])
# Corrosion allowance pushes the required wall up
rCA = recommend_wall("CS", "DN100", EN_PIPE_OD_MM["CS"]["DN100"], 40.0, 150.0, corrosion_allow_mm=3.0)
rNoCA = recommend_wall("CS", "DN100", EN_PIPE_OD_MM["CS"]["DN100"], 40.0, 150.0, corrosion_allow_mm=0.0)
check("corrosion allowance increases required wall", rCA["t_required_mm"] > rNoCA["t_required_mm"],
      f"CA={rCA['t_required_mm']:.2f} vs noCA={rNoCA['t_required_mm']:.2f} mm")
# Ladder floor must equal the lightest real ISO 1127 Serie-1 wall (catalogue cross-check)
floor_errs = [f"{dn}: floor {EN_ISO_1127_WALLS[dn][0]} ≠ Serie1 min {min(s1)}"
              for dn, s1 in _ISO_1127_SERIE1.items()
              if abs(EN_ISO_1127_WALLS[dn][0] - min(s1)) > 1e-9]
check("ladder floor = lightest ISO 1127 Serie-1 wall", not floor_errs,
      ", ".join(floor_errs) if floor_errs else "all DN floors match catalogue")
# Every ladder must be strictly ascending (snap-up relies on it)
asc_errs = [dn for dn, ws in EN_ISO_1127_WALLS.items()
            if any(ws[i] >= ws[i+1] for i in range(len(ws)-1))]
check("wall ladders strictly ascending", not asc_errs, ", ".join(asc_errs))

# 15. ISO 1127 Series 2 & 3 supplementary tube data ----------------------------
print("15. ISO 1127 Series 2 & 3 reference data")
check("Series 2 has small-bore 6 mm OD", 6.0 in ISO_1127_SERIES_2)
check("Series 2 and 3 non-empty", len(ISO_1127_SERIES_2) > 0 and len(ISO_1127_SERIES_3) > 0)
check("descriptions present for all 3 series", all(n in ISO_1127_SERIES_DESCRIPTIONS for n in (1, 2, 3)))
# Series 2/3 are metric ODs distinct from the Series 1 pipe ODs
pipe_ods = set(EN_PIPE_OD_MM["SS316L"].values())
metric_ods = set(ISO_1127_SERIES_2) | set(ISO_1127_SERIES_3)
check("Series 2/3 ODs are metric (not pipe ODs)", metric_ods.isdisjoint(pipe_ods),
      f"overlap={metric_ods & pipe_ods}")
# A Series 2 tube gives a finite positive pressure rating
r57 = pressure_rating_barg(2.0 * 0.875, 57.0, "SS316L", 20.0)
check("Series 2 OD57x2.0 rates > 0 barg", r57 > 0, f"{r57:.0f} barg")

# 16. ASME B36.10M / B36.19M pipe schedules ------------------------------------
print("16. ASME pipe schedules (NPS + schedule)")
# 2" Sch 40 CS: OD 60.3, wall 3.91 → ID 52.48 mm
id_2_40 = asme_pipe_id_m("CS", '2"', "Sch 40") * 1000
check('2" CS Sch 40 ID = 52.48 mm', abs(id_2_40 - 52.48) < 0.05, f"got {id_2_40:.2f} mm")
# STD == Sch 40 at 2" (they only diverge at the large end)
check('2" STD wall == Sch 40 wall', ASME_WALL_MM["CS"]['2"']["STD"] == ASME_WALL_MM["CS"]['2"']["Sch 40"])
# 12" divergence: Sch 40 (10.31) > STD (9.53); XS (12.70) < Sch 80 (17.48)
w12 = ASME_WALL_MM["CS"]['12"']
check('12" Sch 40 > STD (diverge)', w12["Sch 40"] > w12["STD"], f"{w12['Sch 40']} vs {w12['STD']}")
check('12" XS < Sch 80 (diverge)', w12["XS"] < w12["Sch 80"], f"{w12['XS']} vs {w12['Sch 80']}")
# B36.19 stainless 80S caps at 12.70 mm at 10" while B36.10 Sch 80 climbs to 15.09
check('10" SS 80S (12.70) < CS Sch 80 (15.09)',
      ASME_WALL_MM["SS316L"]['10"']["80S"] < ASME_WALL_MM["CS"]['10"']["Sch 80"])
# ASME ODs differ from EN for 2-1/2": 73.0 vs DN65 76.1
_asme_od_2h = ASME_PIPE_OD_MM['2-1/2"']
_en_od_dn65 = EN_PIPE_OD_MM["SS316L"]["DN65"]
check('ASME 2-1/2" OD (73.0) != EN DN65 OD (76.1)', abs(_asme_od_2h - _en_od_dn65) > 1.0,
      f"ASME {_asme_od_2h} vs EN {_en_od_dn65}")
# March an NPS pipe end-to-end and check the row carries ID + schedule label
npipe = Pipe(id="n", name="N", pipe_type="NPS Pipe", nps='2"', schedule="Sch 40",
             material="CS", length_m=20.0)
resn = march(inlet(water(50.0)), [npipe])
rn = row_for(resn, "N")
check('NPS pipe row ID matches asme_pipe_id_m', abs(rn.id_mm - round(id_2_40, 1)) < 0.05,
      f"row {rn.id_mm} vs {id_2_40:.2f}")
check('NPS pipe label is NPS/Sch', rn.pipe == '2"/Sch 40', rn.pipe)
check('NPS pipe class column = schedule', rn.pn_class == "Sch 40", rn.pn_class)
check('NPS pipe friction > 0', rn.dp_fric_kpa > 0)

print()
print(f"\033[92mAll smoke tests passed.\033[0m" if _n_fail == 0
      else f"\033[91m{_n_fail} check(s) failed.\033[0m")
import sys
sys.exit(1 if _n_fail else 0)
