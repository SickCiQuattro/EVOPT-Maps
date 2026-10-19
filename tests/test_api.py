import time

import pytest
from fastapi.testclient import TestClient

from evopt import api
from evopt.router import NoRouteError
from tests.test_router import CAR, line

PLACES = {"Alpha": (45.0, 0.0), "Beta": (45.0, 1.1), "Far": (50.0, 5.0)}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(api, "VEHICLES", {"Test car": CAR})

    def network(place, progress=None):
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
    return TestClient(api.app)


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


def run(client, **kw):
    r = client.post("/api/plan", json=body(**kw))
    assert r.status_code == 202, r.text
    for _ in range(100):
        job = client.get(f"/api/jobs/{r.json()['job_id']}").json()
        if job["status"] != "running":
            return job
        time.sleep(0.05)
    raise AssertionError("job did not finish")


def test_vehicles_are_listed_with_specs(client):
    assert client.get("/api/vehicles").json() == [
        {"name": "Test car", "capacity_kwh": 10, "max_charge_kw": 50}
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

    monkeypatch.setattr(api, "plan_route", impossible)
    job = run(client)
    assert job["error"]["code"] == "no_route" and "start charge" in job["error"]["message"]


def test_map_service_failure_is_reported_not_raised(client, monkeypatch):
    def down(place, progress=None):
        raise OSError("overpass refused")

    monkeypatch.setattr(api, "load_network", down)
    assert run(client)["error"]["code"] == "map_unavailable"


def test_unknown_job_is_404(client):
    assert client.get("/api/jobs/nope").status_code == 404
