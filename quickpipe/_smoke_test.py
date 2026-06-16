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
from standards.piping import PIPE_DATABASE
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
print("1. Liquid section ΔP (water, DN50/40S, 100 m, Δz=0)")
res = march(inlet(water(50.0)), [Pipe(id="p", name="P", dn="DN50", schedule="40S", length_m=100.0)])
r = row_for(res, "P")
props = props_at(water(50.0), 10e5, 25.0)
D = PIPE_DATABASE["DN50"]["40S"]
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
print("2. Gas section (air, DN25, 50 m)")
res = march(inlet(gas(100.0)), [Pipe(id="p", name="G", dn="DN25", schedule="40S", length_m=50.0)])
r = row_for(res, "G")
check("friction > 0 and P_out < P_in", r.dp_fric_kpa > 0 and r.p_out_bara < r.p_in_bara)
check("regime is single-phase gas", "gas" in r.regime.lower(), r.regime)

# 3. Elevation sign + magnitude (vertical section = elevation change) ----------
print("3. Vertical sections (water, 10 m up / down)")
props = props_at(water(50.0), 10e5, 25.0)
exp = props["rho_l"] * G * 10.0 / 1000.0
for orient, sgn in (("Vertical Upflow", +1), ("Vertical Downflow", -1)):
    res = march(inlet(water(50.0)),
                [Pipe(id="p", name="R", dn="DN50", schedule="40S", length_m=10.0, orientation=orient)])
    r = row_for(res, "R")
    check(f"ΔP_grav {orient}", abs(r.dp_grav_kpa - sgn * exp) < 0.5,
          f"{r.dp_grav_kpa:.2f} vs {sgn*exp:.2f} kPa")

# 4. No double-count (vertical riser, L_eff ≫ height) --------------------------
print("4. No gravity double-count (vertical, L_eff ≫ height)")
fit = [{"type": "90° Standard Elbow", "qty": 20}]
p = Pipe(id="p", name="F", dn="DN50", schedule="40S", length_m=5.0,
         orientation="Vertical Upflow", fittings_list=fit)
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
    Pipe(id="p1", name="A", dn="DN50", schedule="40S", length_m=10.0),
    Misc(id="m", name="HX", dp_kpa=20.0),
    Pipe(id="p2", name="B", dn="DN50", schedule="40S", length_m=10.0)])
ok = all(abs(res.rows[i].p_in_bara - res.rows[i-1].p_out_bara) < 1e-9
         for i in range(1, len(res.rows)))
check("each section inlet == previous outlet", ok)
check("outlet == last section P_out", abs(res.outlet_P_bara - res.rows[-1].p_out_bara) < 1e-9)
check("only sections in rows (no source/sink)", len(res.rows) == 3)

# 7. Two-phase -----------------------------------------------------------------
print("7. Two-phase (air + water, Beggs-Brill)")
tp = FluidSpec(phase="two-phase", liquid_type="Water", q_lye_m3h=5.0,
               gas_flows_kgh={"Air": 60.0}, use_coolprop=True)
res = march(inlet(tp), [Pipe(id="p", name="TP", dn="DN50", schedule="40S", length_m=30.0)],
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
res = march(inlet(koh, T=60.0), [Pipe(id="p", name="K", dn="DN50", schedule="40S", length_m=20.0)])
check("KOH denser than water & runs", prk["rho_l"] > 1100 and row_for(res, "K").dp_fric_kpa > 0,
      f"ρ_l={prk['rho_l']:.1f}")

# 9. suggest_dn ----------------------------------------------------------------
print("9. Auto-DN suggestion")
out = suggest_dn(water(80.0), 10e5, 25.0, schedule="40S",
                 criteria=SizingCriteria(v_max=3.0, dp_per_100m_max=50.0))
vs = [r["V (m/s)"] for r in out["table"]]
check("velocity decreases with larger DN", all(vs[i] >= vs[i+1] for i in range(len(vs)-1)))
check("a DN is recommended", out["recommended_dn"] is not None, str(out["recommended_dn"]))

# 10. ASME B36.19M schedule bore ordering (lighter schedule → larger bore) ------
print("10. Schedule bore ordering (5S ≥ 10S ≥ 40S ≥ 80S)")
from standards.piping import PIPE_DATABASE
errors = []
for dn, scheds in PIPE_DATABASE.items():
    d5s  = scheds.get("5S")
    d10s = scheds.get("10S")
    d40s = scheds.get("40S")
    d80s = scheds.get("80S")
    if d5s and d10s and d5s < d10s:
        errors.append(f"{dn}: 5S < 10S")
    if d10s and d40s and d10s < d40s:
        errors.append(f"{dn}: 10S < 40S")
    if d40s and d80s and d40s < d80s:
        errors.append(f"{dn}: 40S < 80S")
check("5S ≥ 10S ≥ 40S ≥ 80S bore for all DNs", not errors, ", ".join(errors) if errors else "")
d10s_dn80 = PIPE_DATABASE["DN80"]["10S"]
d80s_dn80 = PIPE_DATABASE["DN80"]["80S"]
check("DN80: 10S bore > 80S bore", d10s_dn80 > d80s_dn80,
      f"10S={d10s_dn80*1000:.1f} mm  80S={d80s_dn80*1000:.1f} mm")

# 11. Tubing march + dp_fit ----------------------------------------------------
print("11. Tubing march and ΔP_fit (minor losses)")
from standards.piping import TUBING_DATABASE
tw = FluidSpec(phase="liquid", liquid_type="Water", q_lye_m3h=2.0,
               gas_flows_kgh={}, use_coolprop=True)
tube = Pipe(id="t", name="T", pipe_type="Tubing", tube_size="T16", tube_wall="1.5 mm wall",
            length_m=5.0, orientation="Horizontal",
            fittings_list=[{"type": "90° Standard Elbow", "qty": 2}])
res = march(inlet(tw), [tube])
r = row_for(res, "T")
expected_id = TUBING_DATABASE["T16"]["1.5 mm wall"] * 1000
check("tubing ID correct", abs(r.id_mm - expected_id) < 0.01,
      f"got {r.id_mm:.1f} mm, expected {expected_id:.1f} mm")
check("tubing dp_fric > 0", r.dp_fric_kpa > 0)
check("dp_fit > 0 when fittings present", r.dp_fit_kpa > 0,
      f"dp_fit={r.dp_fit_kpa:.3f} kPa")
check("dp_fit < dp_fric", r.dp_fit_kpa < r.dp_fric_kpa)

# 12. dp_fit = 0 with no fittings ----------------------------------------------
print("12. ΔP_fit = 0 when no fittings")
res_nf = march(inlet(water(50.0)),
               [Pipe(id="p", name="NF", dn="DN80", schedule="10S", length_m=20.0)])
check("dp_fit is zero (no fittings)", row_for(res_nf, "NF").dp_fit_kpa == 0.0)

print()
print(f"\033[92mAll smoke tests passed.\033[0m" if _n_fail == 0
      else f"\033[91m{_n_fail} check(s) failed.\033[0m")
import sys
sys.exit(1 if _n_fail else 0)
