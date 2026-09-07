import json

import pytest

from waterpath.io.routes import NetworkInputError, load_network


def test_load_demo_network(demo_network_dir):
    net = load_network(demo_network_dir)

    assert {h.harbour_id for h in net.harbours} == {"DCC", "DUN", "HOW"}
    assert net.harbour("DCC").country_code == "IE"

    assert {r.route_id for r in net.routes} == {"DCC-DUN", "DCC-HOW"}
    dcc_dun = net.route("DCC-DUN")
    assert dcc_dun.origin == "DCC"
    assert dcc_dun.destination == "DUN"
    assert dcc_dun.n_segments == 12
    assert len(dcc_dun.path) == 4
    # GeoJSON (lon, lat) mapped to named fields correctly.
    assert dcc_dun.start.lat == pytest.approx(53.3467)
    assert dcc_dun.start.lon == pytest.approx(-6.2431)
    # optional n_segments absent -> None
    assert net.route("DCC-HOW").n_segments is None


def test_missing_harbours_file(tmp_path):
    (tmp_path / "routes.geojson").write_text("{}")
    with pytest.raises(NetworkInputError, match="harbours file not found"):
        load_network(tmp_path)


def test_missing_required_column(tmp_path):
    (tmp_path / "harbours.csv").write_text("harbour_id,name,lat\nA,A,0\n")
    (tmp_path / "routes.geojson").write_text("{}")
    with pytest.raises(NetworkInputError, match="missing required column"):
        load_network(tmp_path)


def test_non_numeric_coordinate(tmp_path):
    (tmp_path / "harbours.csv").write_text(
        "harbour_id,name,lat,lon\nA,A,0,x\n"
    )
    (tmp_path / "routes.geojson").write_text("{}")
    with pytest.raises(NetworkInputError, match="not a number"):
        load_network(tmp_path)


def test_route_geometry_must_be_linestring(tmp_path):
    (tmp_path / "harbours.csv").write_text(
        "harbour_id,name,lat,lon\nA,A,0,0\nB,B,1,1\n"
    )
    doc = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"route_id": "R", "origin": "A", "destination": "B"},
                "geometry": {"type": "Point", "coordinates": [0, 0]},
            }
        ],
    }
    (tmp_path / "routes.geojson").write_text(json.dumps(doc))
    with pytest.raises(NetworkInputError, match="must be a LineString"):
        load_network(tmp_path)


def test_route_references_unknown_harbour(tmp_path):
    (tmp_path / "harbours.csv").write_text(
        "harbour_id,name,lat,lon\nA,A,0,0\n"
    )
    doc = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"route_id": "R", "origin": "A", "destination": "B"},
                "geometry": {
                    "type": "LineString",
                    "coordinates": [[0.0, 0.0], [1.0, 1.0]],
                },
            }
        ],
    }
    (tmp_path / "routes.geojson").write_text(json.dumps(doc))
    with pytest.raises(NetworkInputError, match="not a known harbour"):
        load_network(tmp_path)
