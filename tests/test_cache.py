import os
import time

import osmnx as ox

from evopt.cache import cached, slug
from evopt.stations import Station, load_stations, save_stations
from tests.test_router import line


def _counting(value="v"):
    calls = []

    def build():
        calls.append(1)
        return value

    return build, calls


def _text_io():
    return (lambda p: p.read_text()), (lambda v, p: p.write_text(v))


def test_second_call_reads_from_disk(tmp_path):
    build, calls = _counting()
    load, save = _text_io()
    for _ in range(2):
        assert cached(tmp_path / "a.txt", 7, build, load, save) == "v"
    assert len(calls) == 1


def test_expired_file_is_rebuilt(tmp_path):
    build, _ = _counting("new")
    load, save = _text_io()
    f = tmp_path / "a.txt"
    f.write_text("old")
    eight_days_ago = time.time() - 8 * 86400
    os.utime(f, (eight_days_ago, eight_days_ago))
    assert cached(f, 7, build, load, save) == "new"
    assert f.read_text() == "new"


def test_corrupt_file_is_rebuilt_instead_of_crashing(tmp_path):
    build, _ = _counting("fresh")
    f = tmp_path / "a.json"
    f.write_text("{not json")
    assert cached(f, 7, build, load_stations_text, lambda v, p: p.write_text(v)) == "fresh"


def load_stations_text(p):
    import json

    return json.loads(p.read_text())


def test_creates_missing_cache_folder(tmp_path):
    build, _ = _counting()
    load, save = _text_io()
    cached(tmp_path / "deep" / "dir" / "a.txt", 7, build, load, save)
    assert (tmp_path / "deep" / "dir" / "a.txt").exists()


def test_slug_makes_a_safe_file_name():
    assert slug("Pieve Emanuele, Italy") == "pieve-emanuele-italy"


def test_stations_roundtrip_keeps_unknown_power(tmp_path):
    stations = [Station(45.0, 9.0, 22.0), Station(45.1, 9.1, None)]
    save_stations(stations, tmp_path / "s.json")
    assert load_stations(tmp_path / "s.json") == stations


def test_graph_roundtrip_keeps_types_and_one_way_streets(tmp_path):
    G = line(3, both_ways=False)
    G.graph["crs"] = "epsg:4326"
    ox.save_graphml(G, tmp_path / "g.graphml")
    H = ox.load_graphml(tmp_path / "g.graphml")
    assert list(H.out_edges(0)) == [(0, 1)] and not H.has_edge(1, 0)
    d = next(iter(H.get_edge_data(0, 1).values()))
    assert (d["length"], d["speed_kph"], d["travel_time"]) == (10_000.0, 100.0, 360.0)
