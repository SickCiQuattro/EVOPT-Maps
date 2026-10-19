import logging
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

import osmnx as ox
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from osmnx._errors import InsufficientResponseError, ResponseStatusCodeError
from pydantic import BaseModel, Field, field_validator, model_validator

from evopt.cache import CACHE_DIR
from evopt.data import load_network
from evopt.graph import nearest_nodes, path_coords
from evopt.planner import ALGORITHM_INFO, ALGORITHMS, Planner
from evopt.router import NoRouteError
from evopt.vehicle import VEHICLES

log = logging.getLogger("evopt")
MAX_SNAP_M = 2000  # beyond this distance from the nearest road a point is outside the area
JOB_TTL_S = 3600
NETWORK_TTL_S = 3600  # in memory; on disk the graph and stations last longer (evopt.data)
MAX_NETWORKS = 4
MAX_PLANNERS = 16
PLUG_IN_S = 180  # plugging in and starting the charge: nobody stops for one minute
EXACT_MAX_NODES = 2500  # the exact reference is slow: above this size the comparison skips it
WEB_DIR = Path(__file__).resolve().parent.parent / "web"


class NotFound(Exception):
    pass


def geocode(query):
    try:
        return ox.geocode(query)
    except InsufficientResponseError as e:
        raise NotFound(query) from e


class PlanRequest(BaseModel):
    area: str = Field(min_length=2, max_length=200)
    start: str = Field(min_length=2, max_length=200)
    goal: str = Field(min_length=2, max_length=200)
    vehicle: str
    temp_c: float = Field(20, ge=-30, le=50)
    start_soc: float = Field(1.0, gt=0, le=1)
    min_soc: float = Field(0.1, ge=0, le=0.5)
    algorithm: str = "astar"
    legs: str = "fastest"  # "pareto": slower but does not miss efficient legs
    compare: bool = False  # also run all the other algorithms and report the comparison
    elevation: bool = True  # account for climbs and descents (if the map has elevations)

    @field_validator("area", "start", "goal")
    @classmethod
    def _strip(cls, v):
        return v.strip()

    @field_validator("vehicle")
    @classmethod
    def _known_vehicle(cls, v):
        if v not in VEHICLES:
            raise ValueError("unknown vehicle")
        return v

    @field_validator("algorithm")
    @classmethod
    def _known_algorithm(cls, v):
        if v not in ALGORITHMS:
            raise ValueError(f"unknown algorithm, choose one of {ALGORITHMS}")
        return v

    @field_validator("legs")
    @classmethod
    def _known_legs(cls, v):
        if v not in ("fastest", "pareto"):
            raise ValueError("legs must be 'fastest' or 'pareto'")
        return v

    @model_validator(mode="after")
    def _start_above_arrival(self):
        if self.start_soc <= self.min_soc:
            raise ValueError("start charge must be above the arrival charge")
        return self


@dataclass
class Job:
    status: str = "running"  # running | done | error
    stage: str = "locating"
    result: dict | None = None
    error: dict | None = None
    started: float = 0.0
    compare: str | None = None  # None | running | done | error: the comparison starts after the route
    compare_progress: tuple = (0, 0)
    comparison: list | None = None
    context: tuple | None = None  # (planner, start, goal) for the comparison


class JobError(Exception):
    def __init__(self, code, message):
        self.code, self.message = code, message


JOBS: dict[str, Job] = {}
_pool = ThreadPoolExecutor(max_workers=2)
_network_lock = threading.Lock()  # one download at a time: the second request finds the cache
_plan_lock = threading.Lock()  # Planners share a legs table
NETWORKS: dict[str, tuple[float, object]] = {}  # area -> (time, graph with stations)
PLANNERS: dict[
    tuple, Planner
] = {}  # (area, vehicle, temperature, legs, elevation) -> Planner with its legs table

app = FastAPI(title="EVOPT Maps")


@app.get("/api/vehicles")
def vehicles():
    return [
        {"name": n, "capacity_kwh": v.capacity_kwh, "max_charge_kw": v.max_charge_kw, "source": v.source}
        for n, v in VEHICLES.items()
    ]


@app.get("/api/algorithms")
def algorithms():
    return [{"id": a, "name": ALGORITHM_INFO[a][0], "summary": ALGORITHM_INFO[a][1]} for a in ALGORITHMS]


@app.post("/api/plan", status_code=202)
def plan(req: PlanRequest):
    now = time.time()
    for key in [k for k, j in JOBS.items() if now - j.started > JOB_TTL_S]:
        del JOBS[key]
    job_id = uuid.uuid4().hex
    JOBS[job_id] = job = Job(started=now)
    _pool.submit(_run, job, req)
    return {"job_id": job_id}


@app.get("/api/jobs/{job_id}")
def job_status(job_id: str):
    job = JOBS.get(job_id)
    if job is None:
        raise HTTPException(404, "unknown job")
    return {
        "status": job.status,
        "stage": job.stage,
        "elapsed_s": round(time.time() - job.started, 1),
        "result": job.result,
        "error": job.error,
        "compare": job.compare,
        "compare_progress": list(job.compare_progress),
        "comparison": job.comparison,
    }


def _elevation_summary(G, path, enabled):
    """Net climb and highest point. Not the gross climb: data noise would inflate it."""
    heights = [G.nodes[n].get("elevation") for n in path]
    if not enabled or any(h is None for h in heights):
        return {"net_climb_m": None, "highest_m": None}
    return {"net_climb_m": heights[-1] - heights[0], "highest_m": max(heights)}


def _run(job, req):
    try:
        job.result = _plan(job, req)
        if req.compare:
            job.compare = "running"  # before "done": the client must not see a comparison that will not start
        job.status = "done"
        if req.compare and job.context:
            _run_compare(job, req)
    except JobError as e:
        job.status, job.error = "error", {"code": e.code, "message": e.message}
    except (OSError, ResponseStatusCodeError):  # no network, or Overpass busy/unreachable
        log.exception("map data failed")
        job.status, job.error = (
            "error",
            {
                "code": "map_unavailable",
                "message": "Map data could not be downloaded. The public map service may be busy or refuse large "
                "areas: try a smaller area (a city, not a region) and plan again.",
            },
        )
    except Exception:
        log.exception("unexpected failure")
        job.status, job.error = (
            "error",
            {"code": "internal", "message": "Something went wrong. Please try again."},
        )


def _locate(query):
    try:
        return geocode(query)
    except NotFound as e:
        raise JobError(
            "not_found", f"Could not find “{query}”. Check the spelling or add the city name."
        ) from e


def _network(area, job):
    """Graph with stations, kept in memory: the Planners' legs tables live as long as the graph."""
    with _network_lock:
        hit = NETWORKS.get(area)
        if hit and time.time() - hit[0] < NETWORK_TTL_S:
            return hit[1]
        G = load_network(area, progress=lambda stage: setattr(job, "stage", stage))
        NETWORKS[area] = (time.time(), G)
        for key in [k for k in PLANNERS if k[0] == area]:
            del PLANNERS[key]
        while len(NETWORKS) > MAX_NETWORKS:
            oldest = min(NETWORKS, key=lambda k: NETWORKS[k][0])
            del NETWORKS[oldest]
            for key in [k for k in PLANNERS if k[0] == oldest]:
                del PLANNERS[key]
        return G


def _planner(G, req):
    key = (req.area, req.vehicle, round(req.temp_c, 1), req.legs, req.elevation)
    if key not in PLANNERS:
        if len(PLANNERS) >= MAX_PLANNERS:
            del PLANNERS[next(iter(PLANNERS))]
        planner = Planner(
            G, VEHICLES[req.vehicle], req.temp_c, legs=req.legs, plug_in_s=PLUG_IN_S, elevation=req.elevation
        )
        planner.load_table(_table_path(planner))  # legs computed in earlier sessions
        PLANNERS[key] = planner
    return PLANNERS[key]


def _table_path(planner):
    return CACHE_DIR / f"legs-{planner.fingerprint()}.pkl"


def _run_compare(job, req):
    """Comparison with the other algorithms, after the route has been delivered. One lock per algorithm."""
    planner, start, goal = job.context
    job.compare, job.compare_progress, rows = "running", (0, len(ALGORITHMS)), []
    try:
        for i, alg in enumerate(ALGORITHMS, 1):
            row = {"algorithm": alg, "time_min": None, "note": None}
            if alg == "exact" and len(planner.G) > EXACT_MAX_NODES:
                row["note"] = "Skipped: graph too large for the exact reference."
            else:
                try:
                    with _plan_lock:
                        r = planner.plan(start, goal, req.start_soc, req.min_soc, algorithm=alg)
                        _save_table(planner)
                    row |= {
                        "time_min": r.time_s / 60,
                        "stops": len(r.charges),
                        "expanded": r.stats.get("expanded", 0),
                        "search_ms": r.stats.get("search_ms", 0.0),
                        "bound": r.stats.get("bound", 1.0),
                        "anytime": r.history or None,
                    }
                except NoRouteError:
                    row["note"] = "Found no feasible route."
            rows.append(row)
            job.compare_progress = (i, len(ALGORITHMS))
        best = min((r["time_min"] for r in rows if r["time_min"] is not None), default=None)
        for r in rows:
            r["gap_pct"] = None if r["time_min"] is None else (r["time_min"] / best - 1) * 100
        job.comparison, job.compare = rows, "done"
    except Exception:
        log.exception("comparison failed")
        job.compare = "error"
    finally:
        job.context = None  # release the Planner


def _save_table(planner):
    if planner.table_dirty:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        planner.save_table(_table_path(planner))


def _plan(job, req):
    points = {"start": (req.start, _locate(req.start)), "goal": (req.goal, _locate(req.goal))}
    try:
        G = _network(req.area, job)
    except FileNotFoundError as e:  # missing local extract ("local:name")
        raise JobError("not_found", str(e)) from e
    except InsufficientResponseError as e:
        raise JobError(
            "not_found",
            f"Could not find the area \u201c{req.area}\u201d. Try a city name such as \u201cPavia, Italy\u201d.",
        ) from e
    snapped = dict(zip(points, nearest_nodes(G, [p for _, p in points.values()])))
    for which, (query, _) in points.items():
        if snapped[which][1] > MAX_SNAP_M:
            raise JobError(
                "outside_area",
                f"“{query}” is more than {MAX_SNAP_M // 1000} km from any road in “{req.area}”. "
                "Use a larger area or a closer address.",
            )
    job.stage = "planning"
    vehicle = VEHICLES[req.vehicle]
    stations = [(d["y"], d["x"], d["charger_kw"]) for _, d in G.nodes(data=True) if "charger_kw" in d]
    start, goal = snapped["start"][0], snapped["goal"][0]
    try:
        with _plan_lock:
            planner = _planner(G, req)
            route = planner.plan(start, goal, req.start_soc, req.min_soc, algorithm=req.algorithm)
            _save_table(planner)
            job.context = (planner, start, goal)
    except NoRouteError as e:
        raise JobError(
            "no_route",
            f"No route with this battery and the {len(stations)} charging stations found in “{req.area}”. "
            "Try a higher start charge, a lower arrival charge, another vehicle or a larger area.",
        ) from e
    stops = [
        {
            "lat": G.nodes[n]["y"],
            "lon": G.nodes[n]["x"],
            "kwh": kwh,
            "minutes": secs / 60,
            "power_kw": min(vehicle.max_charge_kw, G.nodes[n]["charger_kw"]),
            "label": G.nodes[n].get("charger_label"),
            "average_kw": kwh / max((secs - PLUG_IN_S) / 3600, 1e-9) if secs > PLUG_IN_S else None,
            "soc_before": before,
            "soc_after": after,
        }
        for n, kwh, secs, before, after in route.charges
    ]
    charge_min = sum(s["minutes"] for s in stops)
    return {
        "route": [list(c) for c in path_coords(G, route.path)],
        "start": {"label": req.start},
        "goal": {"label": req.goal},
        "stops": stops,
        "stations": [list(s) for s in stations],
        "algorithm": req.algorithm,
        "stats": route.stats,
        "anytime": route.history or None,
        "summary": {
            "distance_km": route.distance_m / 1000,
            "drive_min": route.time_s / 60 - charge_min,
            "charge_min": charge_min,
            "total_min": route.time_s / 60,
            "arrival_soc": route.arrival_soc,
            **_elevation_summary(G, route.path, req.elevation),
        },
    }


if WEB_DIR.exists():  # after the API routes, otherwise "/" would shadow them
    app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
