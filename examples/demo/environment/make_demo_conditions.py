"""Generate the synthetic demo environmental-conditions file.

Physically *plausible* Dublin Bay field, entirely invented — only the file structure is
meaningful. See ``docs/environment-data-format.md`` for the schema this must satisfy.

Run from the repo root:

    python examples/demo/environment/make_demo_conditions.py
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

OUT = Path(__file__).with_name("conditions.nc")
SCHEMA_VERSION = "0.1"

# --- grid (covers the demo network bbox with margin) --------------------------------
time = pd.date_range("2024-01-01", periods=7 * 24, freq="1h")  # 7 days, hourly, UTC
lat = np.round(np.linspace(53.27, 53.41, 9), 4)
lon = np.round(np.linspace(-6.27, -6.04, 15), 4)

h = np.arange(time.size, dtype=float)[:, None, None]          # (t, 1, 1)
yy = ((lat[None, :, None] - lat.mean()) / np.ptp(lat))        # (1, y, 1) in ~[-0.5, 0.5]
xx = ((lon[None, None, :] - lon.mean()) / np.ptp(lon))        # (1, 1, x)

rng = np.random.default_rng(20240101)
noise = lambda amp: rng.normal(0.0, amp, size=(time.size, lat.size, lon.size))


def wrap360(a):
    return np.mod(a, 360.0)


# --- wind: SW background, diurnal wobble, a gale front around hour ~84 --------------
synoptic = 6.0 * np.sin(2 * np.pi * h / 72.0 - 1.0)
diurnal = 1.5 * np.sin(2 * np.pi * h / 24.0)
front = 9.0 * np.exp(-0.5 * ((h - 84.0) / 10.0) ** 2)
sea_exposure = 1.0 + 0.30 * xx                                # windier offshore (east)
wind_speed = np.clip((8.0 + synoptic + diurnal + front) * sea_exposure + noise(0.4), 0.0, None)
wind_from_direction = wrap360(228.0 + 35.0 * np.sin(2 * np.pi * h / 72.0) + 6.0 * yy + noise(3.0))

# --- waves: fetch-limited response to wind, propagating from ~wind direction --------
wave_height = np.clip(0.35 + 0.26 * wind_speed + noise(0.05), 0.1, None)
wave_from_direction = wrap360(wind_from_direction + 12.0 + noise(4.0))
wave_period = np.clip(2.6 + 0.34 * wind_speed + noise(0.1), 2.0, None)

# --- current: semidiurnal M2 tide, flood towards NW / ebb towards SE ---------------
phase = 2 * np.pi * h / 12.42
channel = 1.0 + 0.45 * np.cos(np.pi * yy)                     # faster mid-bay
current_speed = np.clip((0.10 + 0.48 * np.abs(np.sin(phase))) * channel + noise(0.02), 0.0, None)
current_to_direction = wrap360(
    225.0 + 90.0 * np.tanh(3.0 * np.sin(phase)) + 5.0 * xx + 3.0 * yy + noise(2.0)
)

ds = xr.Dataset(
    data_vars=dict(
        wind_speed=(("time", "latitude", "longitude"), wind_speed.astype("float32")),
        wind_from_direction=(("time", "latitude", "longitude"), wind_from_direction.astype("float32")),
        current_speed=(("time", "latitude", "longitude"), current_speed.astype("float32")),
        current_to_direction=(("time", "latitude", "longitude"), current_to_direction.astype("float32")),
        wave_height=(("time", "latitude", "longitude"), wave_height.astype("float32")),
        wave_from_direction=(("time", "latitude", "longitude"), wave_from_direction.astype("float32")),
        wave_period=(("time", "latitude", "longitude"), wave_period.astype("float32")),
    ),
    coords=dict(time=time, latitude=lat, longitude=lon),
    attrs={
        "Conventions": "CF-1.8",
        "waterpath_env_schema": SCHEMA_VERSION,
        "title": "Environmental conditions — Dublin Bay (synthetic demo)",
        "source": "water-path examples/demo/environment/make_demo_conditions.py",
        "institution": "water-path demo data",
        "history": "synthetic; values invented, structure per docs/environment-data-format.md",
    },
)

_UNITS = {
    "wind_speed": ("m s-1", "wind speed at 10 m", "wind_speed"),
    "wind_from_direction": ("degree", "direction the wind blows from", "wind_from_direction"),
    "current_speed": ("m s-1", "surface current speed", "sea_water_speed"),
    "current_to_direction": ("degree", "direction the current flows towards", "sea_water_velocity_to_direction"),
    "wave_height": ("m", "significant wave height", "sea_surface_wave_significant_height"),
    "wave_from_direction": ("degree", "mean direction waves propagate from", "sea_surface_wave_from_direction"),
    "wave_period": ("s", "mean wave period", "sea_surface_wave_mean_period"),
}
for name, (units, long_name, std) in _UNITS.items():
    ds[name].attrs.update(units=units, long_name=long_name, standard_name=std)
ds["latitude"].attrs.update(units="degrees_north", standard_name="latitude")
ds["longitude"].attrs.update(units="degrees_east", standard_name="longitude")

encoding = {n: {"zlib": True, "complevel": 4, "dtype": "float32"} for n in _UNITS}
encoding["time"] = {"units": "hours since 2024-01-01 00:00:00", "dtype": "int32"}

ds.to_netcdf(OUT, encoding=encoding)
print(f"wrote {OUT} ({OUT.stat().st_size / 1024:.0f} KiB)")
for n in _UNITS:
    print(f"  {n:22s} {float(ds[n].min()):7.2f} … {float(ds[n].max()):7.2f} {ds[n].attrs['units']}")
