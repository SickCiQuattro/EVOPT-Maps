import urllib.error

import osmnx as ox
import pytest

from evopt import data
from evopt.stations import Station, save_stations
from tests.test_router import line


@pytest.fixture
def sources(monkeypatch):
    """Sostituisce solo i confini di rete (Overpass e OCM) e conta le chiamate."""
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
