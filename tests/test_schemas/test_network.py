import pytest
from pydantic import ValidationError

from waterpath.schemas.network import Harbour, Network, Point, Route


def _harbour(hid: str, lat: float, lon: float, **kw) -> Harbour:
    return Harbour(harbour_id=hid, name=hid, lat=lat, lon=lon, **kw)


def _route(rid: str, origin: Harbour, destination: Harbour, **kw) -> Route:
    return Route(
        route_id=rid,
        origin=origin.harbour_id,
        destination=destination.harbour_id,
        path=(origin.point, destination.point),
        **kw,
    )


class TestHarbour:
    def test_country_code_normalised(self):
        assert _harbour("A", 0, 0, country_code=" ie ").country_code == "IE"

    def test_blank_country_code_is_none(self):
        assert _harbour("A", 0, 0, country_code="").country_code is None

    def test_bad_country_code_rejected(self):
        with pytest.raises(ValidationError):
            _harbour("A", 0, 0, country_code="IRL")

    def test_lat_out_of_range_rejected(self):
        with pytest.raises(ValidationError):
            _harbour("A", 91.0, 0.0)


class TestRoute:
    def test_path_needs_two_points(self):
        with pytest.raises(ValidationError):
            Route(route_id="R", origin="A", destination="B", path=(Point(lat=0, lon=0),))

    def test_origin_equals_destination_rejected(self):
        a = _harbour("A", 0, 0)
        with pytest.raises(ValidationError):
            _route("R", a, a)

    def test_n_segments_must_be_positive(self):
        a, b = _harbour("A", 0, 0), _harbour("B", 1, 1)
        with pytest.raises(ValidationError):
            _route("R", a, b, n_segments=0)


class TestNetwork:
    def test_valid_network(self):
        a = _harbour("A", 53.30, -6.20, country_code="IE")
        b = _harbour("B", 53.35, -6.10, country_code="IE")
        net = Network(harbours=(a, b), routes=(_route("R", a, b),))
        assert net.harbour("A") is a
        assert net.route("R").destination == "B"

    def test_unknown_harbour_reference_rejected(self):
        a = _harbour("A", 0, 0)
        ghost = _harbour("B", 1, 1)
        with pytest.raises(ValidationError, match="not a known harbour"):
            Network(harbours=(a,), routes=(_route("R", a, ghost),))

    def test_duplicate_harbour_id_rejected(self):
        a1 = _harbour("A", 0, 0)
        a2 = _harbour("A", 1, 1)
        b = _harbour("B", 2, 2)
        with pytest.raises(ValidationError, match="duplicate harbour_id"):
            Network(harbours=(a1, a2, b), routes=(_route("R", a1, b),))

    def test_path_endpoint_too_far_from_harbour_rejected(self):
        a = _harbour("A", 0.0, 0.0)
        b = _harbour("B", 1.0, 1.0)
        far = Route(
            route_id="R",
            origin="A",
            destination="B",
            path=(Point(lat=0.5, lon=0.5), Point(lat=1.0, lon=1.0)),
        )
        with pytest.raises(ValidationError, match="path origin is"):
            Network(harbours=(a, b), routes=(far,))
