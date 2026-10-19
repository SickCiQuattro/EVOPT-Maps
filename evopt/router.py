from dataclasses import dataclass, field


class NoRouteError(Exception):
    pass


@dataclass
class Route:
    path: list  # nodes from start to goal
    time_s: float  # driving + charging
    distance_m: float
    charges: list  # (node, kWh charged, seconds, charge before, charge after)
    arrival_soc: float
    stats: dict = field(default_factory=dict)  # algorithm, states expanded, milliseconds...
    history: list = field(default_factory=list)  # ARA* rounds: eps, bound, time


def plan_route(G, start, goal, vehicle, *, temp_c=20, start_soc=1.0, min_soc=0.1, steps=100):
    """Fastest route with charging stops (A* on the reduced graph). Use `Planner` to pick the algorithm."""
    from evopt.planner import Planner

    return Planner(G, vehicle, temp_c, steps).plan(start, goal, start_soc, min_soc, algorithm="astar")
