"""Read a prepared environmental-conditions file.

The file is produced by a separate project, not by ``water-path``. Schema:
``docs/environment-data-format.md``. This module opens it, checks it against that
schema, and offers the wind/current/wave -> eastward/northward conversion the physics
engine needs.
"""

from __future__ import annotations

import warnings
from pathlib import Path

import numpy as np
import xarray as xr

#: Bump the major when the schema changes incompatibly.
SCHEMA_VERSION = "0.1"

REQUIRED_COORDS: tuple[str, ...] = ("time", "latitude", "longitude")

#: variable name -> expected ``units`` attribute
REQUIRED_VARS: dict[str, str] = {
    "wind_speed": "m s-1",
    "wind_from_direction": "degree",
    "current_speed": "m s-1",
    "current_to_direction": "degree",
    "wave_height": "m",
    "wave_from_direction": "degree",
    "wave_period": "s",
}

#: variable -> ("from" | "to") direction convention
_CONVENTION = {
    "wind": "from",
    "wave": "from",
    "current": "to",
}


class ConditionsInputError(ValueError):
    """Raised when an environmental-conditions file is missing or off-schema."""


def open_conditions(path: str | Path, *, validate: bool = True) -> xr.Dataset:
    """Open and (by default) validate an environmental-conditions file."""
    path = Path(path)
    if not path.is_file():
        raise ConditionsInputError(f"conditions file not found: {path}")
    try:
        ds = xr.open_dataset(path)
    except (OSError, ValueError) as exc:
        raise ConditionsInputError(f"{path}: cannot open as NetCDF: {exc}") from exc
    if validate:
        _validate(ds, path)
    return ds


def _validate(ds: xr.Dataset, path: Path) -> None:
    missing_coords = [c for c in REQUIRED_COORDS if c not in ds.coords]
    if missing_coords:
        raise ConditionsInputError(f"{path}: missing coord(s): {', '.join(missing_coords)}")

    missing_vars = [v for v in REQUIRED_VARS if v not in ds.data_vars]
    if missing_vars:
        raise ConditionsInputError(f"{path}: missing variable(s): {', '.join(missing_vars)}")

    for var, want in REQUIRED_VARS.items():
        got = ds[var].attrs.get("units")
        if got != want:
            warnings.warn(
                f"{path}: {var} has units {got!r}, expected {want!r}", stacklevel=3
            )
        if set(ds[var].dims) != set(REQUIRED_COORDS):
            raise ConditionsInputError(
                f"{path}: {var} has dims {ds[var].dims}, expected {REQUIRED_COORDS}"
            )

    for coord in REQUIRED_COORDS:
        values = ds[coord].values
        if values.size < 2 or not np.all(np.diff(values.astype("float64")) > 0):
            raise ConditionsInputError(f"{path}: coord {coord!r} must be strictly increasing")

    file_schema = str(ds.attrs.get("waterpath_env_schema", ""))
    if not file_schema:
        warnings.warn(f"{path}: no 'waterpath_env_schema' global attribute", stacklevel=3)
    elif file_schema.split(".")[0] != SCHEMA_VERSION.split(".")[0]:
        raise ConditionsInputError(
            f"{path}: schema {file_schema!r} incompatible with reader {SCHEMA_VERSION!r}"
        )


def to_components(ds: xr.Dataset) -> xr.Dataset:
    """Add ``<field>_eastward`` / ``<field>_northward`` [m s-1] for wind, current, wave.

    Uses the per-field direction convention from the schema:
    a ``from`` direction theta -> vector towards theta+180
    (``e = -v·sin theta``, ``n = -v·cos theta``); a ``to`` direction phi -> vector
    towards phi (``e = v·sin phi``, ``n = v·cos phi``).
    """
    out = ds.copy()
    speeds = {"wind": "wind_speed", "current": "current_speed", "wave": "wave_height"}
    dirs = {
        "wind": "wind_from_direction",
        "current": "current_to_direction",
        "wave": "wave_from_direction",
    }
    for field, convention in _CONVENTION.items():
        speed = ds[speeds[field]]
        rad = np.deg2rad(ds[dirs[field]])
        sign = -1.0 if convention == "from" else 1.0
        out[f"{field}_eastward"] = sign * speed * np.sin(rad)
        out[f"{field}_northward"] = sign * speed * np.cos(rad)
        out[f"{field}_eastward"].attrs.update(units="m s-1")
        out[f"{field}_northward"].attrs.update(units="m s-1")
    return out
