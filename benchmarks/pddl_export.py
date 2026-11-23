"""Export the reduced graph of a Planner as a plain instance, the common input of the PDDL models.

The instance holds what the search itself uses: the chargers, the legs between them (seconds, kWh, levels needed) and
the seconds to charge each level. `reference` solves it with Dijkstra over (node, level, charging), the same model as
`Planner.plan(algorithm="dijkstra")`, so every PDDL plan can be checked against it. See docs/PDDL.md.
"""

import heapq
import math
import random
from dataclasses import asdict, dataclass
from itertools import pairwise

import networkx as nx

from evopt.vehicle import Vehicle

SCALE = 10  # PDDL costs are integers: tenths of a second


@dataclass
class Instance:
    steps: int
    capacity_kwh: float
    level0: int
    min_level: int
    plug_s: float
    knee: float  # charge above which the power falls (1.0: never)
    taper_to: float  # fraction of the power left at 100 %
    peaks: dict  # charger -> kW the car can draw there
    charge_s: dict  # charger -> seconds to charge level l -> l+1, for l in 0..steps-1
    legs: list  # (from, to, seconds, kWh, levels needed); "s" is the start, "g" the goal

    @property
    def unit(self):
        return self.capacity_kwh / self.steps

    def to_json(self):
        return asdict(self)

    @classmethod
    def from_json(cls, d):
        return cls(**{**d, "legs": [tuple(leg) for leg in d["legs"]]})


def export(planner, start, goal, soc=0.9, min_soc=0.1, keep=None):
    """Instance of the reduced graph from `start` to `goal`; `keep(node)` may drop chargers (default: all)."""
    assert start not in planner.stations and goal not in planner.stations, (
        "start and goal must not be chargers"
    )
    edges, level0, min_level = planner._reduced(start, goal, soc, min_soc)
    stations = {s for s in planner.stations if keep is None or keep(s)}
    name = {start: "s", goal: "g"}
    legs, seen, todo = [], {start}, [start]
    while todo:
        u = todo.pop()
        for b, leg, need in edges(u):
            if b != goal and b not in stations or need > planner.steps - min_level:
                continue
            name.setdefault(b, f"c{len(name) - 2}")
            legs.append((name[u], name[b], leg.time_s, leg.kwh, need))
            if b not in seen and b != goal:
                seen.add(b)
                todo.append(b)
    chargers = {n: v for v, n in name.items() if n not in ("s", "g")}
    car = planner.vehicle
    return Instance(
        steps=planner.steps, capacity_kwh=car.capacity_kwh, level0=level0, min_level=min_level,
        plug_s=planner.plug_in_s, knee=car.taper_from, taper_to=car.taper_to,
        peaks={n: max(1.0, min(car.max_charge_kw, planner.G.nodes[v]["charger_kw"])) for n, v in chargers.items()},
        charge_s={n: [planner._charge_secs(v, level) for level in range(planner.steps)] for n, v in chargers.items()},
        legs=legs,
    )  # fmt: skip


def reference(inst, scale=SCALE):
    """Least total seconds of the instance: Dijkstra over (node, level, charging) with costs in 1/scale seconds."""
    out = {}
    for u, v, t, _, need in inst.legs:
        out.setdefault(u, []).append((v, round(t * scale), need))
    plug = round(inst.plug_s * scale)
    step = {c: [round(s * scale) for s in ls] for c, ls in inst.charge_s.items()}
    src = ("s", inst.level0, False)
    dist, heap = {src: 0}, [(0, src)]
    while heap:
        d, state = heapq.heappop(heap)
        if d > dist[state]:
            continue
        node, level, charging = state
        if node == "g":
            return d / scale
        nxt = []
        if node in step and level < inst.steps:
            nxt.append(((node, level + 1, True), step[node][level] + (0 if charging else plug)))
        nxt += [
            ((v, level - need, False), t)
            for v, t, need in out.get(node, ())
            if level - need >= inst.min_level
        ]
        for s, w in nxt:
            if d + w < dist.get(s, math.inf):
                dist[s] = d + w
                heapq.heappush(heap, (d + w, s))
    return None


# ---------- synthetic corridor ----------
CAR = Vehicle(capacity_kwh=50.0, mass_kg=1500, cda=0.6, max_charge_kw=150, taper_from=0.8, taper_to=0.3)
LENGTH_KM, SPEED_KPH = 600, 110


def corridor(n, seed=None):
    """(graph, start, goal): a 600 km road at 110 km/h with `n` chargers (50, 100 or 150 kW) at random places.

    The road is a chain of nodes, so the leg between two chargers is the sum of the pieces between them.
    """
    rnd = random.Random(n if seed is None else seed)
    xs = sorted(rnd.uniform(10, LENGTH_KM - 10) for _ in range(n))
    G = nx.MultiDiGraph()
    places = [(0.0, "start")] + [(x, k) for k, x in enumerate(xs)] + [(float(LENGTH_KM), "goal")]
    for (a, _), (b, _) in pairwise(places):
        length = (b - a) * 1000 * 1.1
        for u, v in ((a, b), (b, a)):
            G.add_edge(u, v, length=length, speed_kph=SPEED_KPH, travel_time=length / (SPEED_KPH / 3.6))
    for x, _ in places:
        G.nodes[x].update(
            x=9.0, y=40.0 + x / 111.19
        )  # on a meridian: the straight line is shorter than the road
    for x in xs:
        G.nodes[x]["charger_kw"] = rnd.choice((50.0, 100.0, 150.0))
    return G, 0.0, float(LENGTH_KM)
