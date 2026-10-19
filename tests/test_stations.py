import geopandas as gpd
import pytest
from shapely.geometry import Point, box

from evopt.router import NoRouteError, plan_route
from evopt.stations import Station, apply_stations, merge, osm_to_stations, parse_ocm, power_kw
from tests.test_router import CAR, line


def test_power_kw_takes_the_max_output_tag():
    tags = {"socket:type2:output": "22 kW", "socket:chademo:output": "50 kW", "capacity": "4"}
    assert power_kw(tags) == 50


@pytest.mark.parametrize("raw", ["", "fast", None, float("nan")])
def test_power_kw_ignores_unparsable_values(raw):
    assert power_kw({"charging_station:output": raw}) is None


def test_power_kw_accepts_decimal_comma_and_bare_numbers():
    assert power_kw({"charging_station:output": "7,4 kW"}) == 7.4
    assert power_kw({"charging_station:output": "11"}) == 11


def test_osm_polygon_becomes_a_point_station():
    gdf = gpd.GeoDataFrame(
        {"socket:type2:output": ["22 kW", None]},
        geometry=[Point(9.0, 45.0), box(9.1, 45.1, 9.2, 45.2)],
        crs=4326,
    )
    a, b = osm_to_stations(gdf)
    assert (a.lat, a.lon, a.kw) == (45.0, 9.0, 22)
    assert b.kw is None and 9.1 < b.lon < 9.2 and 45.1 < b.lat < 45.2


def test_parse_ocm_takes_max_connector_power_and_tolerates_missing_data():
    items = [
        {
            "AddressInfo": {"Latitude": 45.0, "Longitude": 9.0},
            "Connections": [{"PowerKW": 11}, {"PowerKW": 50}],
        },
        {"AddressInfo": {"Latitude": 45.1, "Longitude": 9.1}, "Connections": [{"PowerKW": None}]},
        {"AddressInfo": {"Latitude": 45.2, "Longitude": 9.2}},
    ]
    assert [s.kw for s in parse_ocm(items)] == [50, None, None]


def test_merge_fills_missing_power_from_ocm_and_adds_unknown_stations():
    osm = [Station(45.0, 9.0, None), Station(45.5, 9.5, 22)]
    ocm = [Station(45.0001, 9.0001, 50), Station(46.0, 10.0, 11)]
    merged = merge(osm, ocm, match_m=100)
    assert sorted((s.lat, s.kw) for s in merged) == [(45.0, 50), (45.5, 22), (46.0, 11)]


def test_apply_stations_snaps_to_nodes_keeps_max_and_defaults_unknown_power():
    G = line(5)  # nodi a lon 0, 0.1 ... 0.4, lat 45.0
    apply_stations(
        G, [Station(45.0, 0.1, 7), Station(45.0, 0.1001, 50), Station(45.0, 0.3, None)], default_kw=22
    )
    assert G.nodes[1]["charger_kw"] == 50
    assert G.nodes[3]["charger_kw"] == 22
    assert "charger_kw" not in G.nodes[0]


def test_apply_stations_drops_stations_far_from_any_road():
    G = line(3)
    apply_stations(G, [Station(46.0, 0.1, 50)], max_snap_m=200)
    assert not any("charger_kw" in d for _, d in G.nodes(data=True))


def test_stations_from_sources_make_a_long_trip_possible():
    G = line(12)
    with pytest.raises(NoRouteError):
        plan_route(G, 0, 11, CAR)
    apply_stations(G, [Station(45.0, 0.6, 50)])
    assert [c[0] for c in plan_route(G, 0, 11, CAR).charges] == [6]
