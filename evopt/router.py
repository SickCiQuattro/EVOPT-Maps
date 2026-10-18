import heapq
import math
from dataclasses import dataclass


class NoRouteError(Exception):
    pass


@dataclass
class Route:
    path: list  # nodi dalla partenza all'arrivo
    time_s: float  # guida + ricariche
    distance_m: float
    charges: list  # (nodo, kWh caricati, secondi)
    arrival_soc: float


def _legs(G, src, targets, vehicle, temp_c):
    """Dijkstra sul tempo da `src`, potato oltre la capacità della batteria.

    shortcut: l'energia è quella del percorso più veloce, non del più efficiente;
    upgrade con un'etichetta Pareto (tempo, energia) per nodo.
    """
    best = {src: (0.0, 0.0, 0.0)}  # nodo -> (tempo, kWh, metri)
    prev = {}
    heap = [(0.0, src)]
    done = set()
    while heap:
        t, u = heapq.heappop(heap)
        if u in done:
            continue
        done.add(u)
        _, kwh, dist = best[u]
        for _, v, d in G.out_edges(u, data=True):
            nt = t + d["travel_time"]
            if v in done or (v in best and best[v][0] <= nt):
                continue
            nk = kwh + vehicle.edge_energy_kwh(d["length"], d["speed_kph"], d["travel_time"], temp_c)
            if nk > vehicle.capacity_kwh:
                continue
            best[v] = (nt, nk, dist + d["length"])
            prev[v] = u
            heapq.heappush(heap, (nt, v))
    legs = {}
    for dst in targets:
        if dst == src or dst not in best:
            continue
        path = [dst]
        while path[-1] != src:
            path.append(prev[path[-1]])
        legs[dst] = (*best[dst], path[::-1])
    return legs


def plan_route(G, start, goal, vehicle, *, temp_c=20, start_soc=1.0, min_soc=0.1, steps=100):
    """Percorso più veloce da `start` a `goal` con soste alle stazioni (nodi con attributo 'charger_kw').

    Ricerca di Dijkstra su (nodo, livello di carica) sul grafo ridotto di partenza, arrivo e stazioni.
    La carica è discretizzata in `steps` livelli e i consumi sono arrotondati per eccesso.
    """
    stations = {n for n, d in G.nodes(data=True) if "charger_kw" in d}
    nodes = [start, goal, *(s for s in stations if s not in (start, goal))]
    unit = vehicle.capacity_kwh / steps
    min_level = math.ceil(min_soc * steps)

    # nodo -> [(destinazione, secondi, livelli consumati, metri, percorso)]
    out = {}
    for a in nodes:
        if a == goal:
            continue
        legs = _legs(G, a, nodes, vehicle, temp_c)
        out[a] = [(b, t, math.ceil(k / unit), m, p) for b, (t, k, m, p) in legs.items()]

    s0 = (start, int(start_soc * steps))
    dist = {s0: 0.0}
    prev = {}
    heap = [(0.0, s0)]
    while heap:
        t, state = heapq.heappop(heap)
        if t > dist[state]:
            continue
        node, level = state
        if node == goal:
            return _build(state, t, prev, unit, steps)
        if node in stations and level < steps:
            secs = unit / min(vehicle.max_charge_kw, G.nodes[node]["charger_kw"]) * 3600
            _relax(dist, prev, heap, state, (node, level + 1), t + secs, ("charge", secs))
        for b, secs, need, meters, path in out.get(node, ()):
            if level - need >= min_level:
                _relax(dist, prev, heap, state, (b, level - need), t + secs, ("drive", path, meters))
    raise NoRouteError("nessun percorso con la batteria e le stazioni disponibili")


def _relax(dist, prev, heap, state, nxt, t, move):
    if t < dist.get(nxt, math.inf):
        dist[nxt] = t
        prev[nxt] = (state, move)
        heapq.heappush(heap, (t, nxt))


def _build(state, time_s, prev, unit, steps):
    arrival_soc = state[1] / steps
    moves = []
    while state in prev:
        state, move = prev[state]
        moves.append((state[0], move))
    path, distance, charges = [], 0.0, []
    for node, move in reversed(moves):
        if move[0] == "drive":
            path += move[1] if not path else move[1][1:]
            distance += move[2]
        elif charges and charges[-1][0] == node:
            charges[-1][1] += unit
            charges[-1][2] += move[1]
        else:
            charges.append([node, unit, move[1]])
    return Route(path, time_s, distance, [tuple(c) for c in charges], arrival_soc)
