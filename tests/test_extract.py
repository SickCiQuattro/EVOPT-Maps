import networkx as nx
import pytest

from benchmarks.extract import _oneway, _speed, build


def way(*nodes, **tags):
    """nodes: (id, lon, lat); tags: highway and the rest."""
    return list(nodes), tags


def test_speed_uses_maxspeed_or_the_road_class_default():
    assert _speed({"highway": "primary", "maxspeed": "50"}) == 50
    assert _speed({"highway": "primary"}) == 70
    assert _speed({"highway": "motorway"}) == 130
    assert _speed({"highway": "primary", "maxspeed": "30 mph"}) == 70  # mph not handled: class default
    assert _speed({"highway": "secondary", "maxspeed": "IT:urban"}) == 60


def test_motorways_and_oneway_tags_are_one_directional():
    assert _oneway({"highway": "motorway"}) and _oneway({"highway": "primary", "oneway": "yes"})
    assert not _oneway({"highway": "primary"})


def test_build_contracts_degree_two_nodes_and_keeps_junctions():
    a = way((1, 9.00, 45.0), (2, 9.01, 45.0), (3, 9.02, 45.0), (4, 9.03, 45.0), highway="primary")
    b = way((3, 9.02, 45.0), (5, 9.02, 45.01), highway="secondary")  # junction at 3
    G = build([a, b])
    assert set(G.nodes) == {1, 3, 4, 5}  # 2 is not a junction: contracted
    assert G.has_edge(1, 3) and G.has_edge(3, 1) and G.has_edge(3, 5)
    d = next(iter(G.get_edge_data(1, 3).values()))
    assert (
        d["length"] > 1500
        and d["speed_kph"] == 70
        and d["travel_time"] == pytest.approx(d["length"] / (70 / 3.6))
    )
    assert len(d["geometry"].coords) == 3  # the geometry keeps the contracted node


def test_build_respects_one_way_streets_and_drops_disconnected_islands():
    one = way((1, 9.0, 45.0), (2, 9.01, 45.0), highway="primary", oneway="yes")
    back = way((2, 9.01, 45.0), (1, 9.0, 45.0), highway="primary", oneway="yes")
    island = way((8, 10.0, 46.0), (9, 10.01, 46.0), highway="primary", oneway="yes")
    G = build([one, back, island])
    assert set(G.nodes) == {1, 2} and nx.is_strongly_connected(nx.DiGraph(G))
