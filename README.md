# Quickpipe

A standalone line-sizing / pressure-march tool. Build a pipe line from ordered
elements (**Source → Pipes / Equipment → Sink**), march pressure segment by
segment, and read off velocities, ΔP and the outlet pressure in a live table —
with a piping sketch and Excel export. Supports gas, liquid and two-phase
(Beggs-Brill) flow, explicit elevation changes, lining, fittings, and an
auto-DN suggestion.

## Run

```bash
python launch.py            # first run creates .venv, installs deps, opens browser
# or
bash run.sh                 # installs deps, runs on port 8502
# or
streamlit run quickpipe_app.py --server.port 8502
```

Opens at http://127.0.0.1:8502 (FlowBench uses 8501, so both run side by side).

## Structure (engine / UI split)

```
quickpipe/
  engine/        # pure Python, no Streamlit
    elements.py  # Source / Pipe / Misc / Sink dataclasses
    fluids.py    # property adapter (CoolProp + KOH)
    march.py     # forward pressure march (the core)
    sizing.py    # auto-DN suggestion
    results.py   # QuickpipeRow table schema
    _vendor/     # unmodified copies of FlowBench engine modules (see VENDORED_FROM.md)
  ui/            # Streamlit layer (editor / table / sketch / sizing / excel)
quickpipe_app.py # entry point
```

The physics is reused from **FlowBench** (`multiphase_engine`, `standards.piping`,
`physics.friction`, `models.pipe`) — vendored under `quickpipe/engine/_vendor/`
so this app runs fully standalone. Vendored files are never edited; to refresh
them, re-copy from FlowBench and update `_vendor/VENDORED_FROM.md`.

## Engineering notes

- **Pressure marching**: fluid properties (density, velocities, void fraction)
  are recomputed at each element's local pressure, so gas compressibility is
  tracked between elements. Liquid mass flow is frozen at the source so mass is
  conserved (volumetric flow varies with density).
- **Elevation**: gravity ΔP is `ρ_insitu · g · Δz` using the geometric Δz, kept
  separate from friction (which uses the fitting-inclusive `L_eff`) — no
  double-count.
- **Validity**: incompressible two-phase correlations are reliable below ~Mach
  0.3 in the gas phase; beyond that an element is flagged. ±20–30% correlation
  uncertainty applies.

## Test

```bash
python -m quickpipe._smoke_test     # pure-engine checks, no Streamlit
```
