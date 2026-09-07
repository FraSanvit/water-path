# water-path

## What this is
Open-source Python toolkit for optimising vessel (ferry) decarbonisation. Combines:
- **physics-based route/speed modelling** — wind, wave, current treated as physically distinct effects
- **MILP/LP capacity-expansion + scheduling optimisation** — built on `linopy` + `HiGHS`

Distribution name `water-path`; import package `waterpath` (a hyphen is not valid in a
Python module name).

## Core concept: 
1. The user provide the initial inputs: water routes, technologies, demand.
2. The objective of the software is to plan the route from an operational point of view and optimise the fleet renewal over the selected horizon.
3. The tool presents planning mode and operational mode. The planning mode focuses on the design of the service (speeds, timetables, technologies, etc) and the operational mode focuses on the evaluation of the real consumption and potential disruption of the service when the full year with the complete environmental conditions are considered.
4. The output of the tool is the roadmap of the vessel fleet renewal, the operation of the routes and the total costs. Considering that the user can add cost classes as they wish.
5. The tool is an optimisation software. Math can be customised and we keep the basic math and the custom math in separate files (see Calliope v0.7 to take inpiration from).


## Input flow
- **A. Raw inputs** — network graph (harbours + routes; multi-leg itineraries like A->B->C->A),
  vessel list (fixed and/or candidate), tidy OD demand records at the user's native resolution,
  and a prepared **environmental-conditions file** (gridded NetCDF: wind/current/wave
  speed + direction on a `time × lat × lon` grid). That file is produced by a *separate
  project*, not by `water-path`; the contract is `docs/environment-data-format.md`.
  `io/environment.py` opens and validates it.
- **B. Calendar tagging** (`preprocess/calendar_tagging.py`) — config defines named seasons as
  explicit date ranges plus a country/region code; public holidays resolved via the `holidays`
  library. `weekday`/`weekend` derived from the ISO calendar; `holiday` wins ties. The *same*
  function tags demand records and environmental series, so both land in identical
  `(season, day_type)` bins.
- **C. Two parallel preprocessing paths**
  - *C1 demand* (`demand_profiles.py`) — tag records, aggregate to typical hourly OD profiles per bin.
  - *C2 environment* (`temporal_aggregation.py`) — tag full-resolution series, cluster to a small
    weighted set of representative days per bin (typical + extreme). Independently, split each route
    into a configurable number of segments; evaluate environmental conditions per segment, per
    vessel, per representative timestep.
- **D. Physics evaluation** (`core/physics.py`, orchestrated by `core/initialize.py`) — for each
  `vessel x route x representative-period x candidate-speed`, `evaluate()` integrates
  segment-by-segment using the C2 per-segment conditions. Wind -> aerodynamic resistance;
  current -> speed-over-ground / travel-time; waves -> added wave resistance. `initialize_routes()`
  runs **once, upfront**, producing an `xarray.Dataset` performance table passed as a fixed input
  to `backend/` — **not recomputed** during MILP/LP construction.
- **E. Two operating modes**
  - *Design/Planning* — `backend/` builds and solves the MILP/LP against the performance table;
    decides scheduling, speed choice, and (multi-year mode) technology/investment.
  - *Operational Evaluation* (`core/evaluation.py`) — take the fixed Design-mode decisions, re-run
    the physics engine against the full-resolution un-aggregated environmental series for the whole
    year (no re-optimisation) to compute realistic annual energy/emissions and flag days where the
    fixed decision would be infeasible or need derating.

## Dev environment (Windows, locked down)
This machine blocks execution of `python.exe` copied into a venv (`.venv/Scripts/`,
`%TEMP%`, …) — corporate application-control. Only uv's managed interpreter under
`%APPDATA%\uv\python\...` is allowed to run. So **`uv run` / `uv venv` do not work here.**

Working pattern — install deps to a target dir, run the base interpreter with `PYTHONPATH`:
```powershell
$py  = "C:\Users\FSanvito\AppData\Roaming\uv\python\cpython-3.12-windows-x86_64-none\python.exe"
$tgt = "<scratchpad>\libs"
uv pip install --python $py --target $tgt pydantic xarray netcdf4 numpy pytest matplotlib contextily
$env:PYTHONPATH = "$tgt;$(Get-Location)\src"
& $py -m pytest -q
```
Use the **PowerShell** tool, not Bash, for anything that executes Python (the Bash tool
can't run these binaries either). Last run: 24 passed. (`--target` installs can emit
numpy/netcdf4 binary-compat warnings — harmless; a real `uv sync` env resolves them.)

## Conventions
- `src/` layout, **hatchling** build backend. Import package `waterpath`.
- `xarray.Dataset` is the interchange format for the performance table and the solved output.
- **pydantic** for all config/input validation (`schemas/`).
- `tests/` mirrors `src/` 1:1; tests read the small committed `examples/demo/` inputs, never the network.
- **Environmental conditions are built outside this tool**, by a separate repo (fed by
  Copernicus Marine, Marine Institute, ERA5, …). It emits one standardised gridded NetCDF file
  per study area; `water-path` only reads it (`io/environment.py`). Schema + direction
  conventions: `docs/environment-data-format.md`. Same split as `atlite` cutouts → `PyPSA`.
  There are **no provider classes / no `mock.py`** in `io/` — that idea is superseded.

## Current state
Built as standalone blocks, composed later.

| Area | Status |
|---|---|
| `schemas/network.py` — `Point`, `Harbour`, `Route`, `Network` (pydantic, frozen; cross-validates harbour refs + path-endpoint proximity) | ✅ |
| `io/routes.py` — `load_network(dir)` reads `harbours.csv` + `routes.geojson` (explicit LineString paths only; multi-leg itineraries deferred) | ✅ |
| `io/environment.py` — `open_conditions(path)` validates a NetCDF conditions file against the schema; `to_components(ds)` adds eastward/northward for wind/current/wave | ✅ |
| `docs/environment-data-format.md` — the conditions-file contract (v0.1) with the other repo | ✅ |
| `geo.py` — `haversine_km` | ✅ |
| `viz.py` — `plot_network()` quick-look plot with slippy-map backdrop (extra `viz`: `matplotlib` + `contextily`; backdrop = Esri WorldGrayCanvas, needs network at plot time, degrades gracefully) | ✅ |
| `examples/demo/network/` — 3-harbour Dublin Bay toy + `network.png` | ✅ |
| `examples/demo/environment/` — synthetic `conditions.nc` (486 KiB) + `make_demo_conditions.py` generator | ✅ |
| next up: sampling conditions along routes (bilinear in space, linear in time) → feeds physics | ⬜ |
| everything else (`io/vessels`, `io/demand`, `preprocess`, `core`, `math`, `backend`, `postprocess`, `cli`) | ⬜ not started |


