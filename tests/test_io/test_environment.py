import numpy as np
import pytest
import xarray as xr

from waterpath.io.environment import (
    REQUIRED_VARS,
    ConditionsInputError,
    open_conditions,
    to_components,
)


def test_open_demo_conditions(demo_conditions_path):
    ds = open_conditions(demo_conditions_path)

    assert set(REQUIRED_VARS).issubset(ds.data_vars)
    for coord in ("time", "latitude", "longitude"):
        assert coord in ds.coords
    assert ds.attrs["waterpath_env_schema"] == "0.1"

    # plausible physical ranges
    assert 0.0 <= float(ds.wind_speed.min())
    assert float(ds.wind_speed.max()) < 60.0
    assert 0.0 <= float(ds.wave_height.min())
    assert float(ds.wave_period.min()) > 0.0
    for d in ("wind_from_direction", "current_to_direction", "wave_from_direction"):
        assert 0.0 <= float(ds[d].min()) and float(ds[d].max()) < 360.0


def test_to_components_roundtrips_magnitude(demo_conditions_path):
    ds = to_components(open_conditions(demo_conditions_path))

    for field, speed_var in (
        ("wind", "wind_speed"),
        ("current", "current_speed"),
        ("wave", "wave_height"),
    ):
        mag = np.hypot(ds[f"{field}_eastward"], ds[f"{field}_northward"])
        np.testing.assert_allclose(mag, ds[speed_var], rtol=1e-5, atol=1e-4)


def test_to_components_direction_convention():
    # wind FROM the west (270) -> blows towards the east -> +eastward, ~0 northward
    ds = xr.Dataset(
        {
            "wind_speed": ("t", [10.0]),
            "wind_from_direction": ("t", [270.0]),
            "current_speed": ("t", [2.0]),
            "current_to_direction": ("t", [90.0]),  # flows towards east
            "wave_height": ("t", [1.0]),
            "wave_from_direction": ("t", [270.0]),
        }
    )
    out = to_components(ds)
    assert float(out.wind_eastward[0]) == pytest.approx(10.0, abs=1e-6)
    assert float(out.wind_northward[0]) == pytest.approx(0.0, abs=1e-6)
    assert float(out.current_eastward[0]) == pytest.approx(2.0, abs=1e-6)


def test_missing_file(tmp_path):
    with pytest.raises(ConditionsInputError, match="not found"):
        open_conditions(tmp_path / "nope.nc")


def test_missing_variable_rejected(tmp_path):
    ds = xr.Dataset(
        {"wind_speed": (("time", "latitude", "longitude"), np.zeros((2, 2, 2)))},
        coords={"time": [0, 1], "latitude": [0.0, 1.0], "longitude": [0.0, 1.0]},
    )
    ds.wind_speed.attrs["units"] = "m s-1"
    ds.attrs["waterpath_env_schema"] = "0.1"
    path = tmp_path / "partial.nc"
    ds.to_netcdf(path)
    with pytest.raises(ConditionsInputError, match="missing variable"):
        open_conditions(path)
