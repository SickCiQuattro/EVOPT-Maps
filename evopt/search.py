"""Fastest route between two nodes of the road network: Dijkstra, A*, Weighted A* and ARA* (anytime)."""

import heapq
import math
from dataclasses import dataclass

INF = math.inf


@dataclass
class PathResult:
    path: list
    time_s: float
    expanded: int  # nodes expanded (for ARA*: cumulative over all rounds)
    eps: float = 1.0  # heuristic inflation used
    bound: float = 1.0  # guarantee: time_s <= bound * optimum


def _hav(lat1, lon1, lat2, lon2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = (
        math.sin((p2 - p1) / 2) ** 2
        + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    )
    return 2 * 6371000 * math.asin(math.sqrt(a))


def straight_speed(G):
    """Highest straight-line speed (m/s) over any edge; it makes the heuristic admissible and consistent by construction."""
    if "_straight_speed" not in G.graph:
        best = 0.0
        for u, v, d in G.edges(data=True):
            if d["travel_time"] > 0:
                a, b = G.nodes[u], G.nodes[v]
                best = max(best, _hav(a["y"], a["x"], b["y"], b["x"]) / d["travel_time"])
        G.graph["_straight_speed"] = best or 1.0
    return G.graph["_straight_speed"]


def time_heuristic(G, goal):
    """Lower bound on the time to `goal`: straight-line distance at the highest straight-line speed."""
    speed, g = straight_speed(G), G.nodes[goal]
    return lambda n: _hav(G.nodes[n]["y"], G.nodes[n]["x"], g["y"], g["x"]) / speed


def _succ(G, u):
    for _, v, d in G.out_edges(u, data=True):
        yield v, d["travel_time"], None


def _walk(parent, src, dst):
    """States and moves from the source to `dst`, following the parents."""
    states, tags = [dst], []
    while states[-1] != src:
        prev, tag = parent[states[-1]]
        states.append(prev)
        tags.append(tag)
    return states[::-1], tags[::-1]


@dataclass
class Found:
    """Outcome of a search on an implicit graph: `succ(state)` yields (successor, cost, tag)."""

    states: list
    tags: list
    cost: float
    expanded: int
    eps: float = 1.0
    bound: float = 1.0


def search(succ, src, dst, h, weight=1.0, prune=None):
    """A* / Weighted A* on an implicit graph. With h=0 it is Dijkstra. The heuristic must be consistent.

    `prune(state, g)` may drop a freshly popped state (e.g. dominated by a closed one); it must record the state if it keeps it.
    """
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
        if prune and prune(u, gu):
            continue
        expanded += 1
        for v, c, tag in succ(u):
            if v not in closed and gu + c < g.get(v, INF):
                g[v], parent[v] = gu + c, (u, tag)
                heapq.heappush(heap, (g[v] + weight * h(v), g[v], v))
    return None


def ara(succ, src, dst, h, eps=3.0, decrease=0.5):
    """ARA* (Likhachev et al.): a first answer fast with `eps`, then improved while reusing the work done.

    Yields one Found per round, with the guarantee `bound` (<= eps) on the distance from the optimum.
    """
    g, parent = {src: 0.0}, {}
    heap = [(eps * h(src), 0.0, src)]
    closed, incons, expanded = set(), set(), 0
    while True:
        # ImprovePath: expand until the goal is no worse than every open key
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
                        incons.add(v)  # already expanded with a worse g: reopened next round
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


def _distances(G, src, reverse=False):
    """Minimum times from `src` to every node (or towards `src` if reverse)."""
    dist, done, heap = {src: 0.0}, set(), [(0.0, src)]
    edges = (
        (lambda u: ((p, d) for p, _, d in G.in_edges(u, data=True)))
        if reverse
        else (lambda u: ((v, d) for _, v, d in G.out_edges(u, data=True)))
    )
    while heap:
        t, u = heapq.heappop(heap)
        if u in done:
            continue
        done.add(u)
        for v, d in edges(u):
            nt = t + d["travel_time"]
            if nt < dist.get(v, INF):
                dist[v] = nt
                heapq.heappush(heap, (nt, v))
    return dist


def alt_landmarks(G, k=8):
    """ALT (Goldberg and Harrelson): k landmarks chosen as far apart as possible, with times to and from each.

    shortcut: farthest-first choice from an arbitrary node; for disconnected graphs start from the largest component.
    """
    first = next(iter(G.nodes))
    far = _distances(G, first)
    chosen, nearest = [], {n: INF for n in far}
    pick = max(far, key=far.get)
    while len(chosen) < k:
        d_from = _distances(G, pick)
        chosen.append((pick, d_from, _distances(G, pick, reverse=True)))
        for n, value in nearest.items():
            nearest[n] = min(value, d_from.get(n, INF))
        nxt = max((n for n in nearest if nearest[n] < INF), key=nearest.get)
        if nxt in {c[0] for c in chosen}:
            break
        pick = nxt
    return chosen


def alt_heuristic(G, goal, landmarks):
    """Consistent lower bound on the time to `goal`, from the triangle inequality on the landmarks."""
    pairs = [(d_from, d_to, d_from.get(goal), d_to.get(goal)) for _, d_from, d_to in landmarks]

    def h(n):
        best = 0.0
        for d_from, d_to, from_goal, to_goal in pairs:
            if from_goal is not None and n in d_from:
                best = max(best, from_goal - d_from[n])
            if to_goal is not None and n in d_to:
                best = max(best, d_to[n] - to_goal)
        return best

    return h


def _as_path(f):
    return PathResult(f.states, f.cost, f.expanded, f.eps, f.bound)


def dijkstra(G, src, dst):
    f = search(lambda u: _succ(G, u), src, dst, lambda n: 0.0, 1.0)
    return f and _as_path(f)


def astar(G, src, dst, weight=1.0, landmarks=None):
    """weight=1 is optimal A*; weight>1 is Weighted A*: faster, at most `weight` times the optimum.

    With `landmarks` (see alt_landmarks) the heuristic is the maximum of straight line and ALT: still consistent.
    """
    h = time_heuristic(G, dst)
    if landmarks:
        straight, alt = h, alt_heuristic(G, dst, landmarks)
        h = lambda n: max(straight(n), alt(n))
    f = search(lambda u: _succ(G, u), src, dst, h, weight)
    return f and _as_path(f)


def ara_star(G, src, dst, eps=3.0, decrease=0.5):
    for f in ara(lambda u: _succ(G, u), src, dst, time_heuristic(G, dst), eps, decrease):
        yield _as_path(f)
