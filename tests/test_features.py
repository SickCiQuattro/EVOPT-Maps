import io
import json

import pytest

from evopt import api, weather
from evopt.planner import Planner
from evopt.router import NoRouteError
from evopt.stations import power_kw
from tests.test_api import body, client, run  # noqa: F401  (the client fixture)
from tests.test_router import CAR, line


def plan(G, **kw):
    opts = {k: kw.pop(k) for k in ("avoid", "algorithm") if k in kw}
    return Planner(G, CAR, 20, **kw).plan(0, len(G) - 1, algorithm=opts.pop("algorithm", "astar"), **opts)


def test_a_zero_kw_charger_is_no_power_not_a_crash():
    assert power_kw({"socket:type2:output": "0 kW"}) is None
    G = line(12, stations=[6])
    G.nodes[6]["charger_kw"] = 0.0  # what an old cache or a bad import could hold
    assert plan(G).time_s > 0  # slow (the floor is 1 kW), but it plans


def test_a_speed_cap_slows_every_road_and_keeps_the_route():
    free, capped = plan(line(4)), plan(line(4), max_speed_kph=50)
    assert capped.path == free.path
    assert capped.time_s == pytest.approx(2 * free.time_s)  # 100 -> 50 km/h


def test_a_speed_cap_above_the_limit_changes_nothing():
    assert plan(line(4), max_speed_kph=130).time_s == pytest.approx(plan(line(4)).time_s)


def test_charger_preferences_filter_the_stations():
    G = line(12, stations=[5, 6])
    G.nodes[5]["charger_kw"], G.nodes[6]["charger_kw"] = 22, 50
    G.nodes[6]["charger_known"] = False  # estimated power
    assert Planner(G, CAR, 20).stations == {5, 6}
    assert Planner(G, CAR, 20, min_kw=50).stations == {6}
    assert Planner(G, CAR, 20, known_power=True).stations == frozenset()


def test_the_battery_profile_climbs_at_the_stop_and_ends_at_the_arrival_charge():
    r = plan(line(12, stations=[6]))
    km, soc = zip(*r.profile, strict=True)
    assert (
        r.profile[0] == (0.0, 1.0)
        and km[-1] == pytest.approx(110)
        and soc[-1] == pytest.approx(r.arrival_soc)
    )
    assert list(km) == sorted(km)
    jumps = [(a, b) for a, b in zip(r.profile, r.profile[1:], strict=False) if a[0] == b[0] and b[1] > a[1]]
    assert len(jumps) == 1 and jumps[0][0][0] == pytest.approx(60)  # one stop, at node 6


def test_avoiding_a_charger_uses_the_other_one_and_forgets_it_afterwards():
    G = line(12, stations=[5, 6])
    planner = Planner(G, CAR, 20)
    best = planner.plan(0, 11, algorithm="astar_potential")
    other = planner.plan(0, 11, algorithm="astar_potential", avoid=(best.charges[0][0],))
    assert other.charges[0][0] != best.charges[0][0] and other.time_s >= best.time_s - 1e-6
    with pytest.raises(NoRouteError):
        planner.plan(0, 11, algorithm="astar_potential", avoid=(5, 6))
    assert planner.plan(0, 11, algorithm="astar_potential").charges[0][0] == best.charges[0][0]


# ---------- API ----------
@pytest.fixture
def two_stations(client, monkeypatch):  # noqa: F811
    monkeypatch.setattr(api, "load_network", lambda place, progress=None: line(12, stations=[5, 6]))
    return client


def test_busy_gives_the_extra_minutes_without_a_stop(two_stations):
    job = run(two_stations)
    assert job["status"] == "done" and job["result"]["profile"][0] == [0.0, 1.0]
    r = two_stations.post(f"/api/jobs/{job['id']}/busy/1").json()
    assert r["extra_min"] >= 0 and r["stops"] >= 1


def test_busy_with_no_other_charger_says_there_is_no_alternative(client):  # noqa: F811
    job = run(client)  # one station only
    assert client.post(f"/api/jobs/{job['id']}/busy/1").json() == {"extra_min": None}


def test_busy_rejects_unknown_jobs_and_stops(two_stations):
    job = run(two_stations)
    assert two_stations.post(f"/api/jobs/{job['id']}/busy/9").status_code == 404
    assert two_stations.post("/api/jobs/nope/busy/1").status_code == 404


def test_the_exact_reference_is_refused_on_a_large_graph(client, monkeypatch):  # noqa: F811
    monkeypatch.setattr(api, "EXACT_MAX_NODES", 5)
    job = run(client, algorithm="exact")
    assert job["status"] == "error" and job["error"]["code"] == "too_large"


def test_speed_and_charger_options_are_validated_and_reach_the_planner(client):  # noqa: F811
    assert client.post("/api/plan", json=body(max_speed_kph=10)).status_code == 422
    slow = run(client, max_speed_kph=60)["result"]["summary"]["drive_min"]
    assert slow > run(client)["result"]["summary"]["drive_min"]
    assert run(client, min_kw=100)["error"]["code"] == "no_route"  # the only station is 50 kW


def test_temperature_endpoint(client, monkeypatch):  # noqa: F811
    monkeypatch.setattr(api, "current_temperature", lambda lat, lon: 7)
    assert client.get("/api/temperature", params={"place": "Alpha"}).json() == {"temp_c": 7}
    assert client.get("/api/temperature", params={"place": "Nowhere"}).status_code == 404


def test_open_meteo_answer_is_read(monkeypatch):
    seen = {}

    def urlopen(req, timeout):
        seen["url"] = req.full_url
        return io.BytesIO(json.dumps({"current": {"temperature_2m": 11.6}}).encode())

    monkeypatch.setattr(weather.urllib.request, "urlopen", urlopen)
    assert weather.current_temperature(45.07, 7.69) == 12
    assert "latitude=45.0700" in seen["url"] and "temperature_2m" in seen["url"]
