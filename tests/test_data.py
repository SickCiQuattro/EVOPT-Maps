import urllib.error

import osmnx as ox
import pytest

from evopt import data
from evopt.stations import Station, save_stations
from tests.test_router import line


@pytest.fixture
def sources(monkeypatch):
    """Replaces only the network boundaries (Overpass and OCM) and counts the calls."""
    calls = {"graph": 0, "osm": 0, "ocm": 0}

    def graph(place):
        calls["graph"] += 1
        G = line(12)
        G.graph["crs"] = "epsg:4326"
        return G

    def osm(place):
        calls["osm"] += 1
        return [Station(45.0, 0.6, 50)]

    def ocm(lat, lon, radius_km):
        calls["ocm"] += 1
        return [Station(45.0, 0.2, 150)]

    def flat_dem(G, cache_dir, **kw):  # tests download no tiles: fixed elevation on nodes that lack one
        for _, d in G.nodes(data=True):
            d.setdefault("elevation", 5.0)

    monkeypatch.setattr(data, "add_node_elevations", flat_dem)
    monkeypatch.setattr(data, "load_graph", graph)
    monkeypatch.setattr(data, "fetch_osm", osm)
    monkeypatch.setattr(data, "fetch_ocm", ocm)
    monkeypatch.delenv("OCM_API_KEY", raising=False)
    return calls


def chargers(G):
    return {n: d["charger_kw"] for n, d in G.nodes(data=True) if "charger_kw" in d}


def test_network_has_stations_and_second_call_hits_the_cache(sources, tmp_path):
    for _ in range(2):
        G = data.load_network("Test, Italy", cache_dir=tmp_path)
        assert chargers(G) == {6: 50}
    assert sources == {"graph": 1, "osm": 1, "ocm": 0}


def test_ocm_is_merged_when_a_key_is_set(sources, tmp_path, monkeypatch):
    monkeypatch.setenv("OCM_API_KEY", "k")
    G = data.load_network("Test, Italy", cache_dir=tmp_path)
    assert chargers(G) == {2: 150, 6: 50}


def test_ocm_outage_falls_back_to_osm_with_a_warning(sources, tmp_path, monkeypatch):
    monkeypatch.setenv("OCM_API_KEY", "k")

    def down(*a):
        raise urllib.error.URLError("offline")

    monkeypatch.setattr(data, "fetch_ocm", down)
    with pytest.warns(UserWarning, match="Open Charge Map"):
        G = data.load_network("Test, Italy", cache_dir=tmp_path)
    assert chargers(G) == {6: 50}


def test_progress_reports_each_stage_in_order(sources, tmp_path, monkeypatch):
    monkeypatch.setenv("OCM_API_KEY", "k")
    stages = []
    data.load_network("Test, Italy", cache_dir=tmp_path, progress=stages.append)
    assert stages == ["roads", "stations", "power"]


def test_local_extract_is_loaded_from_disk_without_any_network_call(sources, tmp_path):
    G = line(12)
    G.graph["crs"] = "epsg:4326"
    ox.save_graphml(G, tmp_path / "corridor.graphml")
    save_stations([Station(45.0, 0.6, 50)], tmp_path / "corridor-stations.json")
    net = data.load_network("local:corridor", cache_dir=tmp_path / "cache", data_dir=tmp_path)
    assert chargers(net) == {6: 50}
    assert sources == {"graph": 0, "osm": 0, "ocm": 0}


def test_missing_local_extract_explains_how_to_make_it(sources, tmp_path):
    with pytest.raises(FileNotFoundError, match="benchmarks.extract"):
        data.load_network("local:nothing", data_dir=tmp_path)


def local_corridor(tmp_path):
    G = line(12)
    G.graph["crs"] = "epsg:4326"
    ox.save_graphml(G, tmp_path / "corridor.graphml")
    save_stations([Station(45.0, 0.6, None, "Enel X")], tmp_path / "corridor-stations.json")


def test_local_extract_is_completed_with_open_charge_map_tiles(sources, tmp_path, monkeypatch):
    local_corridor(tmp_path)
    monkeypatch.setenv("OCM_API_KEY", "k")
    calls = []

    def tile(lat, lon, radius_km):
        calls.append((round(lat, 2), round(lon, 2), radius_km))
        return [
            Station(45.0, 0.6, 150.0),
            Station(45.0, 0.2, 50.0),
        ]  # the same station in every tile: it must be deduplicated

    monkeypatch.setattr(data, "fetch_ocm", tile)
    G = data.load_network("local:corridor", cache_dir=tmp_path / "cache", data_dir=tmp_path)
    assert len(calls) > 1  # covers the corridor in tiles, not with a single circle
    assert chargers(G) == {
        2: 50.0,
        6: 150.0,
    }  # OCM power where the extract had none, extra station added
    assert G.nodes[6]["charger_label"] == "Enel X"
    before = len(calls)
    data.load_network("local:corridor", cache_dir=tmp_path / "cache", data_dir=tmp_path)
    assert len(calls) == before  # second time: the tiles come from the cache


def test_local_extract_survives_an_open_charge_map_outage(sources, tmp_path, monkeypatch):
    local_corridor(tmp_path)
    monkeypatch.setenv("OCM_API_KEY", "k")

    def down(*a):
        raise urllib.error.URLError("offline")

    monkeypatch.setattr(data, "fetch_ocm", down)
    with pytest.warns(UserWarning, match="Open Charge Map"):
        G = data.load_network("local:corridor", cache_dir=tmp_path / "cache", data_dir=tmp_path)
    assert chargers(G) == {6: 22.0}  # the extract only, with the default power


def test_elevation_is_added_once_and_survives_the_graph_cache(sources, tmp_path, monkeypatch):
    seen = []

    def dem(G, cache_dir, **kw):
        todo = [n for n, d in G.nodes(data=True) if "elevation" not in d]
        seen.append(len(todo))
        for n in todo:
            G.nodes[n]["elevation"] = 100.0 + n

    monkeypatch.setattr(data, "add_node_elevations", dem)
    G = data.load_network("Test, Italy", cache_dir=tmp_path)
    assert G.nodes[3]["elevation"] == 103.0 and sum(seen) == 12  # 12 nodes annotated, once only
    again = data.load_network(
        "Test, Italy", cache_dir=tmp_path
    )  # from the cache: elevations are already in the saved graph
    assert again.nodes[3]["elevation"] == 103.0 and sum(seen) == 12  # no node left to annotate


def test_missing_elevation_data_does_not_stop_planning(sources, tmp_path, monkeypatch):
    def down(G, cache_dir, **kw):
        raise urllib.error.URLError("offline")

    monkeypatch.setattr(data, "add_node_elevations", down)
    with pytest.warns(UserWarning, match="flat"):
        G = data.load_network("Test, Italy", cache_dir=tmp_path)
    assert chargers(G) == {6: 50} and not any("elevation" in d for _, d in G.nodes(data=True))


def test_local_extract_gets_elevation_too(sources, tmp_path):
    local_corridor(tmp_path)
    G = data.load_network("local:corridor", cache_dir=tmp_path / "cache", data_dir=tmp_path)
    assert all(d["elevation"] == 5.0 for _, d in G.nodes(data=True))
