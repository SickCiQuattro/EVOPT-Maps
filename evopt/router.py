from dataclasses import dataclass, field


class NoRouteError(Exception):
    pass


@dataclass
class Route:
    path: list  # nodi dalla partenza all'arrivo
    time_s: float  # guida + ricariche
    distance_m: float
    charges: list  # (nodo, kWh caricati, secondi, carica prima, carica dopo)
    arrival_soc: float
    stats: dict = field(default_factory=dict)  # algoritmo, stati espansi, millisecondi...
    history: list = field(default_factory=list)  # giri di ARA*: eps, bound, tempo


def plan_route(G, start, goal, vehicle, *, temp_c=20, start_soc=1.0, min_soc=0.1, steps=100):
    """Percorso più veloce con soste (A* sul grafo ridotto). Per scegliere l'algoritmo usa `Planner`."""
    from evopt.planner import Planner

    return Planner(G, vehicle, temp_c, steps).plan(start, goal, start_soc, min_soc, algorithm="astar")
