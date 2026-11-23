import importlib.util

import pytest

from benchmarks import pddl_models as models
from benchmarks.pddl_export import CAR, Instance, corridor, export, reference
from evopt.planner import Planner


def _corridor(n):
    G, s, g = corridor(n)
    planner = Planner(G, CAR, 20, steps=100, plug_in_s=180)
    return planner, s, g, export(planner, s, g, 0.9, 0.1)


@pytest.mark.parametrize("n", [10, 30])
def test_reference_on_the_exported_instance_equals_the_planners_dijkstra(n):
    planner, s, g, inst = _corridor(n)

    route = planner.plan(s, g, algorithm="dijkstra", start_soc=0.9, min_soc=0.1)

    assert reference(inst) == pytest.approx(route.time_s, abs=1.0)  # costs are rounded to 0.1 s per action


def test_instance_round_trips_through_json():
    _, _, _, inst = _corridor(10)

    assert Instance.from_json(inst.to_json()) == inst


def test_classical_problem_lists_only_feasible_drives():
    _, _, _, inst = _corridor(10)
    u, v, _, _, need = inst.legs[0]

    text = models.classical(inst)

    assert f"(drive-ok {u} {v} l{inst.min_level + need} l{inst.min_level})" in text
    assert f"(drive-ok {u} {v} l{inst.min_level + need - 1}" not in text


def test_numeric_and_hybrid_problems_define_every_leg_and_charger():
    _, _, _, inst = _corridor(10)

    for text in (models.numeric(inst), models.hybrid(inst)):
        assert text.count("(road ") == len(inst.legs)
        assert all(f"(charger {c})" in text for c in inst.peaks)


@pytest.mark.skipif(
    importlib.util.find_spec("up_fast_downward") is None, reason="pddl dependency group not installed"
)
def test_fast_downward_finds_the_dijkstra_optimum():
    from benchmarks.pddl_run import fast_downward

    _, _, _, inst = _corridor(10)

    result = fast_downward(inst, timeout=120)

    assert result["cost"] == pytest.approx(reference(inst), abs=0.1)
