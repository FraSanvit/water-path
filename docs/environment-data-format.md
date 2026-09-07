# Environmental conditions file — format spec (v0.1)

`water-path` does **not** download or derive environmental conditions. A separate project
(fed by Copernicus Marine, Marine Institute, ERA5, …) produces a single standardised file;
`water-path` only reads it. This document is the contract between the two.

## Container

- **NetCDF4** (`.nc`), CF-1.8 conventions, one file per study area.
- Not human-readable by design. Zarr may be added later as an alternative container; the
  variable/coordinate schema below stays the same.
- Internal compression recommended (`zlib`, `complevel` 4) and `float32` storage.

## Coordinates (all required)

| name        | dtype            | units                    | notes |
|-------------|------------------|--------------------------|-------|
| `time`      | datetime64 (UTC) | CF `hours since <epoch>` | strictly increasing, uniform step preferred |
| `latitude`  | float            | `degrees_north`          | strictly increasing |
| `longitude` | float            | `degrees_east`           | strictly increasing, range −180…180 |

The grid is regular (a lat vector × a lon vector). It must cover every route's bounding box
with at least a one-cell margin, so segment midpoints can be interpolated without extrapolation.

## Data variables (all required), dims `(time, latitude, longitude)`

| name                   | units   | meaning |
|------------------------|---------|---------|
| `wind_speed`           | `m s-1` | wind speed at 10 m |
| `wind_from_direction`  | `degree`| direction the wind blows **from** |
| `current_speed`        | `m s-1` | surface current speed |
| `current_to_direction` | `degree`| direction the current flows **towards** |
| `wave_height`          | `m`     | significant wave height, Hs |
| `wave_from_direction`  | `degree`| mean direction waves propagate **from** |
| `wave_period`          | `s`     | mean wave period (Tm) — needed for added wave resistance |

### Direction convention

All directions: degrees in `[0, 360)`, clockwise from true north (0 = N, 90 = E).

The `from` / `to` split is deliberate — it mirrors the source products, so the upstream repo
passes values through with minimal transformation:

- **wind** / **waves** use `from` (meteorological; matches Copernicus `VMDR`, ERA5 wind dir).
- **current** uses `to` (oceanographic; matches how `uo`/`vo` components resolve).

`water-path` converts everything to eastward/northward components on read
(`waterpath.io.environment.to_components`). Given a `from` direction θ, the vector points
towards θ+180: `eastward = -speed·sin θ`, `northward = -speed·cos θ`. Given a `to` direction φ:
`eastward = speed·sin φ`, `northward = speed·cos φ`.

## Global attributes

| attribute                  | required | example |
|----------------------------|----------|---------|
| `Conventions`              | yes      | `CF-1.8` |
| `waterpath_env_schema`     | yes      | `0.1` (major bump = breaking change) |
| `title`                    | yes      | `Environmental conditions — Dublin Bay` |
| `source` / `institution`   | recommended | which products, which extractor version |
| `history`                  | recommended | provenance line(s) |
| `geospatial_*` / `time_coverage_*` | recommended | CF bounds |

## How the tool uses it

1. `open_conditions(path)` opens and validates against this schema.
2. Physics samples each route's segment midpoints at each representative timestep
   (bilinear in space, nearest/linear in time), converts to components, and resolves them
   into along-track / cross-track effects (current → speed-over-ground, wind → aerodynamic
   resistance, waves → added resistance).
3. Operational-evaluation mode replays the **full** time axis of this file against fixed
   design decisions.

## Demo

`examples/demo/environment/conditions.nc` — synthetic but physically plausible Dublin Bay
field (regenerate with `examples/demo/environment/make_demo_conditions.py`). Values are
invented; only the structure is meaningful.
