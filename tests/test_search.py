import itertools

import pytest

from evopt.search import ara_star, astar, dijkstra
from tests.graphs import grid

G = grid(12, seed=3)
START, GOAL = 0, 12 * 12 - 1


def cost(path):
    return sum(
        min(d["travel_time"] for d in G.get_edge_data(u, v).values()) for u, v in itertools.pairwise(path)
    )


def test_dijkstra_returns_a_valid_path_with_its_cost():
    r = dijkstra(G, START, GOAL)
    assert r.path[0] == START and r.path[-1] == GOAL
    assert r.time_s == pytest.approx(cost(r.path))


def test_astar_is_optimal_and_expands_fewer_nodes_than_dijkstra():
    d, a = dijkstra(G, START, GOAL), astar(G, START, GOAL)
    assert a.time_s == pytest.approx(d.time_s)
    assert a.expanded < d.expanded


def test_weighted_astar_trades_optimality_within_its_bound():
    d = dijkstra(G, START, GOAL)
    w = astar(G, START, GOAL, weight=3.0)
    assert d.time_s <= w.time_s <= 3.0 * d.time_s + 1e-9
    assert w.expanded <= astar(G, START, GOAL).expanded


def test_ara_star_improves_monotonically_and_ends_optimal():
    opt = dijkstra(G, START, GOAL).time_s
    steps = list(ara_star(G, START, GOAL, eps=4.0, decrease=1.0))
    times = [s.time_s for s in steps]
    assert times == sorted(times, reverse=True)
    assert times[0] <= 4.0 * opt + 1e-9
    assert times[-1] == pytest.approx(opt)
    assert [s.eps for s in steps] == [4.0, 3.0, 2.0, 1.0]
    assert all(s.bound >= 1.0 for s in steps) and steps[-1].bound == pytest.approx(1.0)


def test_ara_star_reuses_work_between_rounds():
    steps = list(ara_star(G, START, GOAL, eps=3.0, decrease=1.0))
    total = steps[-1].expanded  # contatore cumulativo
    from_scratch = sum(astar(G, START, GOAL, weight=s.eps).expanded for s in steps)
    assert total < from_scratch


@pytest.mark.parametrize("algo", [dijkstra, astar])
def test_unreachable_goal_returns_none(algo):
    H = grid(3)
    H.remove_edges_from([(u, v, k) for u, v, k in H.edges(keys=True) if v == 8])
    assert algo(H, 0, 8) is None


def test_start_equals_goal_is_a_zero_cost_path():
    r = astar(G, 5, 5)
    assert r.path == [5] and r.time_s == 0
