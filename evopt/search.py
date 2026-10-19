"""Percorso più veloce tra due nodi della rete stradale: Dijkstra, A*, Weighted A* e ARA* (anytime)."""

import heapq
import math
from dataclasses import dataclass

INF = math.inf


@dataclass
class PathResult:
    path: list
    time_s: float
    expanded: int  # nodi espansi (per ARA*: cumulativo su tutti i giri)
    eps: float = 1.0  # inflazione dell'euristica usata
    bound: float = 1.0  # garanzia: time_s <= bound * ottimo


def _hav(lat1, lon1, lat2, lon2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = (
        math.sin((p2 - p1) / 2) ** 2
        + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    )
    return 2 * 6371000 * math.asin(math.sqrt(a))


def straight_speed(G):
    """Massima velocità 'in linea d'aria' (m/s) su un arco: rende l'euristica ammissibile e consistente per costruzione."""
    if "_straight_speed" not in G.graph:
        best = 0.0
        for u, v, d in G.edges(data=True):
            if d["travel_time"] > 0:
                a, b = G.nodes[u], G.nodes[v]
                best = max(best, _hav(a["y"], a["x"], b["y"], b["x"]) / d["travel_time"])
        G.graph["_straight_speed"] = best or 1.0
    return G.graph["_straight_speed"]


def time_heuristic(G, goal):
    """Tempo minimo possibile verso `goal`: distanza in linea d'aria alla massima velocità."""
    speed, g = straight_speed(G), G.nodes[goal]
    return lambda n: _hav(G.nodes[n]["y"], G.nodes[n]["x"], g["y"], g["x"]) / speed


def _succ(G, u):
    for _, v, d in G.out_edges(u, data=True):
        yield v, d["travel_time"], None


def _walk(parent, src, dst):
    """Stati e mosse dal sorgente a `dst` seguendo i genitori."""
    states, tags = [dst], []
    while states[-1] != src:
        prev, tag = parent[states[-1]]
        states.append(prev)
        tags.append(tag)
    return states[::-1], tags[::-1]


@dataclass
class Found:
    """Esito della ricerca su un grafo implicito: `succ(stato)` produce (successore, costo, etichetta)."""

    states: list
    tags: list
    cost: float
    expanded: int
    eps: float = 1.0
    bound: float = 1.0


def search(succ, src, dst, h, weight=1.0):
    """A* / Weighted A* su un grafo implicito. Con h=0 è Dijkstra. L'euristica deve essere consistente."""
    g, parent, closed, expanded = {src: 0.0}, {}, set(), 0
    heap = [(weight * h(src), 0.0, src)]
    while heap:
        _, gu, u = heapq.heappop(heap)
        if u in closed or gu > g[u]:
            continue
        if u == dst:
            states, tags = _walk(parent, src, dst)
            return Found(states, tags, gu, expanded, weight, weight)
        closed.add(u)
        expanded += 1
        for v, c, tag in succ(u):
            if v not in closed and gu + c < g.get(v, INF):
                g[v], parent[v] = gu + c, (u, tag)
                heapq.heappush(heap, (g[v] + weight * h(v), g[v], v))
    return None


def ara(succ, src, dst, h, eps=3.0, decrease=0.5):
    """ARA* (Likhachev et al.): soluzione subito con `eps`, poi la migliora riusando il lavoro fatto.

    Produce un Found per ogni giro, con la garanzia `bound` (<= eps) sulla distanza dall'ottimo.
    """
    g, parent = {src: 0.0}, {}
    heap = [(eps * h(src), 0.0, src)]
    closed, incons, expanded = set(), set(), 0
    while True:
        # ImprovePath: espande finché il goal non è meglio di ogni chiave aperta
        while heap:
            key, gu, u = heap[0]
            if u in closed or gu > g[u]:
                heapq.heappop(heap)
                continue
            if g.get(dst, INF) <= key:
                break
            heapq.heappop(heap)
            closed.add(u)
            expanded += 1
            for v, c, tag in succ(u):
                if gu + c < g.get(v, INF):
                    g[v], parent[v] = gu + c, (u, tag)
                    if v in closed:
                        incons.add(v)  # già espanso con un g peggiore: si riapre al giro dopo
                    else:
                        heapq.heappush(heap, (g[v] + eps * h(v), g[v], v))
        if dst not in g:
            return
        open_nodes = {u for _, gu, u in heap if u not in closed and gu == g[u]} | incons
        lower = min((g[u] + h(u) for u in open_nodes), default=g[dst])
        bound = max(1.0, min(eps, g[dst] / lower)) if lower > 0 else eps
        states, tags = _walk(parent, src, dst)
        yield Found(states, tags, g[dst], expanded, eps, bound)
        if eps <= 1.0:
            return
        eps = max(1.0, eps - decrease)
        heap = [(g[u] + eps * h(u), g[u], u) for u in open_nodes]
        heapq.heapify(heap)
        closed, incons = set(), set()


def _as_path(f):
    return PathResult(f.states, f.cost, f.expanded, f.eps, f.bound)


def dijkstra(G, src, dst):
    f = search(lambda u: _succ(G, u), src, dst, lambda n: 0.0, 1.0)
    return f and _as_path(f)


def astar(G, src, dst, weight=1.0):
    """weight=1 è A* ottimo; weight>1 è Weighted A*: più veloce, al più `weight` volte l'ottimo."""
    f = search(lambda u: _succ(G, u), src, dst, time_heuristic(G, dst), weight)
    return f and _as_path(f)


def ara_star(G, src, dst, eps=3.0, decrease=0.5):
    for f in ara(lambda u: _succ(G, u), src, dst, time_heuristic(G, dst), eps, decrease):
        yield _as_path(f)
