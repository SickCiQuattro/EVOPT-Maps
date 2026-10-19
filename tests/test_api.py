import time

import pytest
from fastapi.testclient import TestClient
from osmnx._errors import InsufficientResponseError, ResponseStatusCodeError

from evopt import api
from evopt.planner import ALGORITHMS
from evopt.router import NoRouteError
from tests.test_router import CAR, line

PLACES = {"Alpha": (45.0, 0.0), "Beta": (45.0, 1.1), "Far": (50.0, 5.0)}


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setattr(api, "VEHICLES", {"Test car": CAR})
    api.NETWORKS.clear()
    api.PLANNERS.clear()
    monkeypatch.setattr(api, "CACHE_DIR", tmp_path)
    loads = []

    def network(place, progress=None):
        loads.append(place)
        for stage in ("roads", "stations", "power"):
            progress and progress(stage)
        G = line(12, stations=[6])
        return G

    def geocode(query):
        if query not in PLACES:
            raise api.NotFound(query)
        return PLACES[query]

    monkeypatch.setattr(api, "load_network", network)
    monkeypatch.setattr(api, "geocode", geocode)
    c = TestClient(api.app)
    c.loads = loads
    return c


def body(**kw):
    return {
        "area": "Test",
        "start": "Alpha",
        "goal": "Beta",
        "vehicle": "Test car",
        "temp_c": 20,
        "start_soc": 1.0,
        "min_soc": 0.1,
    } | kw


def run_compare(client, **kw):
    """Plan with comparison: the route arrives first, the comparison right after."""
    job = run(client, compare=True, **kw)
    for _ in range(200):
        if job["compare"] in ("done", "error"):
            return job
        time.sleep(0.05)
        job = client.get(f"/api/jobs/{job['id']}").json()
    raise AssertionError("comparison did not finish")


def run(client, **kw):
    r = client.post("/api/plan", json=body(**kw))
    assert r.status_code == 202, r.text
    for _ in range(100):
        job = client.get(f"/api/jobs/{r.json()['job_id']}").json()
        if job["status"] != "running":
            job["id"] = r.json()["job_id"]
            return job
        time.sleep(0.05)
    raise AssertionError("job did not finish")


def test_vehicles_are_listed_with_specs(client):
    assert client.get("/api/vehicles").json() == [
        {"name": "Test car", "capacity_kwh": 10, "max_charge_kw": 50, "source": None}
    ]


def test_plan_returns_route_stop_and_summary(client):
    job = run(client)
    assert job["status"] == "done", job
    res = job["result"]
    assert res["route"][0] == [45.0, 0.0] and res["route"][-1] == [45.0, 1.1]
    (stop,) = res["stops"]
    assert (stop["lat"], stop["lon"]) == pytest.approx((45.0, 0.6))
    assert stop["power_kw"] == 50
    assert 0.1 <= stop["soc_before"] < stop["soc_after"] <= 1.0 and stop["minutes"] > 0
    assert res["stations"] == [pytest.approx([45.0, 0.6, 50])]
    s = res["summary"]
    assert s["distance_km"] == pytest.approx(110) and s["arrival_soc"] >= 0.1
    assert s["total_min"] == pytest.approx(s["drive_min"] + s["charge_min"])


def test_unknown_vehicle_is_rejected(client):
    assert client.post("/api/plan", json=body(vehicle="Nope")).status_code == 422


def test_start_charge_must_exceed_arrival_charge(client):
    assert client.post("/api/plan", json=body(start_soc=0.1, min_soc=0.1)).status_code == 422


def test_unknown_place_names_the_field(client):
    job = run(client, goal="Nowhere")
    assert (
        job["status"] == "error"
        and job["error"]["code"] == "not_found"
        and "Nowhere" in job["error"]["message"]
    )


def test_place_outside_the_downloaded_area_is_reported(client):
    job = run(client, goal="Far")
    assert job["error"]["code"] == "outside_area"


def test_unreachable_trip_explains_what_to_change(client, monkeypatch):
    def impossible(*a, **k):
        raise NoRouteError("x")

    monkeypatch.setattr(api.Planner, "plan", impossible)
    job = run(client)
    assert job["error"]["code"] == "no_route" and "start charge" in job["error"]["message"]


def test_map_service_failure_is_reported_not_raised(client, monkeypatch):
    def down(place, progress=None):
        raise OSError("overpass refused")

    monkeypatch.setattr(api, "load_network", down)
    assert run(client)["error"]["code"] == "map_unavailable"


def test_unknown_job_is_404(client):
    assert client.get("/api/jobs/nope").status_code == 404


def test_overpass_status_errors_are_map_unavailable(client, monkeypatch):
    def at_capacity(place, progress=None):
        raise ResponseStatusCodeError("502 Bad Gateway")

    monkeypatch.setattr(api, "load_network", at_capacity)
    assert run(client)["error"]["code"] == "map_unavailable"


def test_unknown_area_names_the_area(client, monkeypatch):
    def nothing(place, progress=None):
        raise InsufficientResponseError("no geocode")

    monkeypatch.setattr(api, "load_network", nothing)
    job = run(client, area="Atlantis")
    assert job["error"]["code"] == "not_found" and "Atlantis" in job["error"]["message"]


@pytest.mark.parametrize("algorithm", ALGORITHMS)
def test_every_algorithm_can_be_requested(client, algorithm):
    job = run(client, algorithm=algorithm)
    assert job["status"] == "done", job
    assert job["result"]["algorithm"] == algorithm and job["result"]["stats"]["total_ms"] > 0


def test_unknown_algorithm_is_rejected(client):
    assert client.post("/api/plan", json=body(algorithm="magic")).status_code == 422


def test_algorithms_are_described_for_the_interface(client):
    info = client.get("/api/algorithms").json()
    assert [a["id"] for a in info] == list(ALGORITHMS) and all(a["name"] and a["summary"] for a in info)


def test_compare_returns_one_row_per_algorithm_with_gaps_to_the_best(client):
    job = run_compare(client)
    assert "comparison" not in job["result"] and job["compare_progress"] == [len(ALGORITHMS), len(ALGORITHMS)]
    rows = job["comparison"]
    assert [r["algorithm"] for r in rows] == list(ALGORITHMS)
    gaps = [r["gap_pct"] for r in rows if r["time_min"] is not None]
    assert min(gaps) == pytest.approx(0, abs=0.01) and all(g >= -0.01 for g in gaps)
    ara = next(r for r in rows if r["algorithm"] == "ara")
    assert ara["anytime"] and ara["anytime"][-1]["bound"] == pytest.approx(1.0)


def test_compare_skips_the_exact_reference_on_large_graphs(client, monkeypatch):
    monkeypatch.setattr(api, "EXACT_MAX_NODES", 5)
    rows = run_compare(client)["comparison"]
    exact = next(r for r in rows if r["algorithm"] == "exact")
    assert exact["time_min"] is None and "too large" in exact["note"]


def test_network_and_station_legs_are_reused_across_requests(client):
    run(client)
    run(client, temp_c=20)
    assert client.loads == ["Test"] and len(api.PLANNERS) == 1
    run(client, temp_c=5)
    assert len(api.PLANNERS) == 2 and client.loads == ["Test"]


def test_pareto_legs_can_be_requested(client):
    assert run(client, legs="pareto")["status"] == "done"


def test_missing_local_extract_is_reported_with_how_to_fix_it(client, monkeypatch):
    def missing(place, progress=None):
        raise FileNotFoundError("no local extract 'x': make it with `python -m benchmarks.extract`")

    monkeypatch.setattr(api, "load_network", missing)
    job = run(client, area="local:x")
    assert job["error"]["code"] == "not_found" and "benchmarks.extract" in job["error"]["message"]


def test_station_legs_survive_a_restart(client):
    run(client)
    assert list(api.CACHE_DIR.glob("legs-*.pkl"))
    api.PLANNERS.clear()  # as after a server restart
    run(client)
    (planner,) = api.PLANNERS.values()
    assert planner.leg_searches == 2  # start and goal only; the legs between chargers come from disk


def test_without_compare_there_is_no_comparison_state(client):
    job = run(client)
    assert job["compare"] is None and job["comparison"] is None


def test_summary_reports_net_climb_and_highest_point_when_the_map_has_elevation(client, monkeypatch):
    def hilly(place, progress=None):
        G = line(12, stations=[6])
        for n in G.nodes:
            G.nodes[n]["elevation"] = 10.0 * n  # climbs 10 m per node: 0 m at the start, 110 m at the goal
        return G

    monkeypatch.setattr(api, "load_network", hilly)
    s = run(client)["result"]["summary"]
    assert s["net_climb_m"] == pytest.approx(110.0) and s["highest_m"] == pytest.approx(110.0)


def test_summary_has_no_elevation_figures_on_a_flat_map(client):
    s = run(client)["result"]["summary"]
    assert s["net_climb_m"] is None and s["highest_m"] is None


def test_elevation_can_be_switched_off_per_request(client):
    run(client)
    run(client, elevation=False)
    assert len(api.PLANNERS) == 2  # one Planner with elevations and one without: different leg tables
