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

from evopt.data import load_network
from evopt.graph import nearest_nodes, path_coords
from evopt.router import NoRouteError, plan_route
from evopt.vehicle import VEHICLES

log = logging.getLogger("evopt")
MAX_SNAP_M = 2000  # oltre questa distanza dalla strada più vicina il punto è fuori area
JOB_TTL_S = 3600
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


class JobError(Exception):
    def __init__(self, code, message):
        self.code, self.message = code, message


JOBS: dict[str, Job] = {}
_pool = ThreadPoolExecutor(max_workers=2)
_network_lock = threading.Lock()  # una sola scarica alla volta: la seconda richiesta trova la cache

app = FastAPI(title="EVOPT Maps")


@app.get("/api/vehicles")
def vehicles():
    return [
        {"name": n, "capacity_kwh": v.capacity_kwh, "max_charge_kw": v.max_charge_kw}
        for n, v in VEHICLES.items()
    ]


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
    }


def _run(job, req):
    try:
        job.result = _plan(job, req)
        job.status = "done"
    except JobError as e:
        job.status, job.error = "error", {"code": e.code, "message": e.message}
    except (OSError, ResponseStatusCodeError):  # rete assente o Overpass saturo/irraggiungibile
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


def _plan(job, req):
    points = {"start": (req.start, _locate(req.start)), "goal": (req.goal, _locate(req.goal))}
    try:
        with _network_lock:
            G = load_network(req.area, progress=lambda stage: setattr(job, "stage", stage))
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
    try:
        route = plan_route(
            G, snapped["start"][0], snapped["goal"][0], vehicle,
            temp_c=req.temp_c, start_soc=req.start_soc, min_soc=req.min_soc,
        )  # fmt: skip
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
        "summary": {
            "distance_km": route.distance_m / 1000,
            "drive_min": route.time_s / 60 - charge_min,
            "charge_min": charge_min,
            "total_min": route.time_s / 60,
            "arrival_soc": route.arrival_soc,
        },
    }


if WEB_DIR.exists():  # dopo le rotte API, altrimenti "/" le oscurerebbe
    app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
