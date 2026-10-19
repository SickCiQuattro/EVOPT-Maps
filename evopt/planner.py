"""Pianificazione di un viaggio elettrico con soste, con più algoritmi sullo stesso problema.

Il problema: partenza, arrivo e stazioni formano un grafo ridotto; uno stato è (nodo, livello di carica).
Guidare tra due punti consuma livelli e costa tempo, caricare in una stazione aggiunge un livello e costa tempo.
Dijkstra, A*, Weighted A* e ARA* risolvono questo grafo; "greedy" è un guidatore ingenuo di confronto
e "exact" è una ricerca a etichette sulla rete stradale, senza grafo ridotto e con energia per arco senza arrotondamenti, usata come riferimento.
"""

import heapq
import math
import time
from collections import namedtuple

from evopt.router import NoRouteError, Route
from evopt.search import INF, _hav, ara, search, straight_speed, time_heuristic

ALGORITHMS = ("dijkstra", "astar", "astar_energy", "wastar", "ara", "greedy", "exact")
ALGORITHM_INFO = {
    "dijkstra": ("Dijkstra", "Optimal. Uninformed: expands states in order of cost only."),
    "astar": ("A*", "Optimal. Guided by the straight-line travel time to the destination."),
    "astar_energy": ("A*, energy-aware", "Optimal. Also counts the minimum charging time still needed to cover the distance."),
    "wastar": ("Weighted A* (w=2)", "Fast, at most 2x the optimal trip. Inflates the heuristic."),
    "ara": ("ARA*", "Anytime: a quick answer first, then improved step by step until provably optimal."),
    "greedy": ("Naive driver", "Baseline: heads for the charger nearest the destination and charges to 80% every time."),
    "exact": ("Exact reference", "Label search on the full road network, no reduced graph. Slow: for checking the others."),
}  # fmt: skip
Leg = namedtuple("Leg", "time_s kwh meters path")
GOAL = (-1, -1)  # stato terminale: raggiunto il goal con qualunque carica


class Planner:
    """Pianifica viaggi su un grafo per un veicolo e una temperatura, riusando i tratti tra stazioni."""

    def __init__(self, G, vehicle, temp_c=20, steps=100, legs="fastest"):
        if legs not in ("fastest", "pareto"):
            raise ValueError("legs must be 'fastest' or 'pareto'")
        self.G, self.vehicle, self.temp_c, self.steps, self.legs_mode = G, vehicle, temp_c, steps, legs
        self.stations = frozenset(n for n, d in G.nodes(data=True) if "charger_kw" in d)
        self.unit = vehicle.capacity_kwh / steps
        self.leg_searches = 0  # ricerche sul grafo stradale eseguite finora
        self._min_kwh_per_m = None
        self._table = {}  # stazione -> {stazione: [Leg]} (valido finché grafo, veicolo e temperatura restano gli stessi)

    # ---------- energia ----------
    def _energy(self, d):
        return self.vehicle.edge_energy_kwh(d["length"], d["speed_kph"], d["travel_time"], self.temp_c)

    def _charge_secs(self, node):
        kw = min(self.vehicle.max_charge_kw, self.G.nodes[node]["charger_kw"])
        return self.unit / kw * 3600

    # ---------- tratti sul grafo stradale ----------
    def _legs(self, src, targets, reverse=False):
        """{destinazione: [Leg]} da `src` (o verso `src` se reverse). Una sola ricerca sul grafo stradale."""
        self.leg_searches += 1
        search_fn = self._pareto_legs if self.legs_mode == "pareto" else self._fastest_legs
        return search_fn(src, set(targets) - {src}, reverse)

    def _edges(self, u, reverse):
        if reverse:
            return ((p, d) for p, _, d in self.G.in_edges(u, data=True))
        return ((v, d) for _, v, d in self.G.out_edges(u, data=True))

    def _fastest_legs(self, src, targets, reverse):
        # shortcut: energia del percorso più veloce, non del più parsimonioso; legs="pareto" lo evita
        best, prev, done = {src: (0.0, 0.0, 0.0)}, {}, set()
        heap = [(0.0, src)]
        while heap:
            t, u = heapq.heappop(heap)
            if u in done:
                continue
            done.add(u)
            _, kwh, dist = best[u]
            for v, d in self._edges(u, reverse):
                nt = t + d["travel_time"]
                if v in done or (v in best and best[v][0] <= nt):
                    continue
                nk = kwh + self._energy(d)
                if nk > self.vehicle.capacity_kwh:
                    continue
                best[v], prev[v] = (nt, nk, dist + d["length"]), u
                heapq.heappush(heap, (nt, v))
        legs = {}
        for dst in targets:
            if dst in best:
                path = [dst]
                while path[-1] != src:
                    path.append(prev[path[-1]])
                legs[dst] = [Leg(*best[dst], path if reverse else path[::-1])]
        return legs

    def _pareto_legs(self, src, targets, reverse, max_labels=6):
        """Dijkstra a etichette (tempo, energia): tiene ogni compromesso non dominato, fino a `max_labels` per nodo."""
        cap = self.vehicle.capacity_kwh
        labels = [(src, 0.0, 0.0, 0.0, -1)]  # nodo, tempo, kWh, metri, genitore
        heap, best_e, settled = [(0.0, 0.0, 0)], {}, {}
        while heap:
            t, e, i = heapq.heappop(heap)
            node, _, _, m, _ = labels[i]
            if e >= best_e.get(node, INF) - 1e-9 or len(settled.get(node, ())) >= max_labels:
                continue
            best_e[node] = e
            settled.setdefault(node, []).append(i)
            for v, d in self._edges(node, reverse):
                ne = e + self._energy(d)
                if ne > cap or ne >= best_e.get(v, INF) - 1e-9:
                    continue
                labels.append((v, t + d["travel_time"], ne, m + d["length"], i))
                heapq.heappush(heap, (t + d["travel_time"], ne, len(labels) - 1))
        legs = {}
        for dst in targets:
            for i in settled.get(dst, ()):
                _, t, e, m, _ = labels[i]
                path, j = [], i
                while j != -1:
                    path.append(labels[j][0])
                    j = labels[j][4]
                legs.setdefault(dst, []).append(Leg(t, e, m, path if reverse else path[::-1]))
        return legs

    def _station_legs(self, s):
        if s not in self._table:
            self._table[s] = self._legs(s, self.stations)
        return self._table[s]

    # ---------- piano ----------
    def plan(self, start, goal, start_soc=1.0, min_soc=0.1, algorithm="astar", **opts):
        if algorithm not in ALGORITHMS:
            raise ValueError(f"unknown algorithm {algorithm!r}; choose one of {ALGORITHMS}")
        t0 = time.perf_counter()
        route = getattr(self, f"_plan_{algorithm}")(start, goal, start_soc, min_soc, **opts)
        route.stats.update(
            algorithm=algorithm, total_ms=(time.perf_counter() - t0) * 1000, leg_searches=self.leg_searches
        )
        return route

    def _reduced(self, start, goal, start_soc, min_soc):
        """Tratti del grafo ridotto: dalla partenza e verso l'arrivo si ricalcola, tra stazioni si riusa la tabella."""
        nodes = {start, goal} | self.stations
        out = {}
        for a, legs in [(start, self._legs(start, nodes))] + [
            (s, self._station_legs(s)) for s in self.stations - {start}
        ]:
            out[a] = {b: ls for b, ls in legs.items() if b in (goal, *self.stations)}
        for s, ls in self._legs(goal, self.stations - {goal}, reverse=True).items():
            if s in out and s != start:
                out[s][goal] = ls
        unit = self.unit
        edges = {
            a: [(b, leg, max(0, math.ceil(leg.kwh / unit - 1e-9))) for b, ls in dests.items() for leg in ls]
            for a, dests in out.items()
            if a != goal
        }
        return edges, int(start_soc * self.steps + 1e-9), math.ceil(min_soc * self.steps - 1e-9)

    def _state_graph(self, start, goal, start_soc, min_soc):
        t0 = time.perf_counter()
        edges, level0, min_level = self._reduced(start, goal, start_soc, min_soc)
        steps, stations = self.steps, self.stations

        def succ(state):
            node, level = state
            if node == goal:
                yield GOAL, 0.0, None
                return
            if node in stations and level < steps:
                secs = self._charge_secs(node)
                yield (node, level + 1), secs, ("charge", secs)
            for b, leg, need in edges.get(node, ()):
                if level - need >= min_level:
                    yield (b, level - need), leg.time_s, ("drive", leg)

        return succ, (start, level0), self._heuristics(goal, min_level), (time.perf_counter() - t0) * 1000

    def _heuristics(self, goal, min_level):
        """Euristiche consistenti sullo stato (nodo, livello): solo tempo, oppure tempo + ricarica minima ancora necessaria."""
        G, unit = self.G, self.unit
        if self._min_kwh_per_m is None:
            self._min_kwh_per_m = min(
                self._energy(d) / d["length"] for _, _, d in G.edges(data=True) if d["length"] > 0
            )
        speed, g = straight_speed(G), G.nodes[goal]
        p_max = max(
            (min(self.vehicle.max_charge_kw, G.nodes[s]["charger_kw"]) for s in self.stations),
            default=self.vehicle.max_charge_kw,
        )
        e_min = self._min_kwh_per_m

        def time_only(state):
            return (
                0.0
                if state == GOAL
                else _hav(G.nodes[state[0]]["y"], G.nodes[state[0]]["x"], g["y"], g["x"]) / speed
            )

        def with_energy(state):
            if state == GOAL:
                return 0.0
            node, level = state
            meters = _hav(G.nodes[node]["y"], G.nodes[node]["x"], g["y"], g["x"])
            # kWh che mancano al viaggio in linea d'aria, oltre a quelli disponibili sopra la soglia di arrivo
            deficit = e_min * meters - (level - min_level) * unit
            return meters / speed + max(0.0, deficit) / p_max * 3600

        return {"none": lambda s: 0.0, "time": time_only, "energy": with_energy}

    def _run(self, start, goal, start_soc, min_soc, heuristic, weight=1.0, anytime=None):
        succ, src, hs, prep_ms = self._state_graph(start, goal, start_soc, min_soc)
        h = hs[heuristic]
        t0 = time.perf_counter()
        history = []
        if anytime:
            found = None
            for found in ara(succ, src, GOAL, h, **anytime):
                history.append({"eps": found.eps, "bound": found.bound, "time_s": found.cost, "expanded": found.expanded,
                                "ms": (time.perf_counter() - t0) * 1000})  # fmt: skip
        else:
            found = search(succ, src, GOAL, h, weight)
        if found is None:
            raise NoRouteError("no route with this battery and these stations")
        route = self._build(found)
        route.history = history
        route.stats.update(expanded=found.expanded, bound=found.bound, eps=found.eps, prep_ms=prep_ms,
                           search_ms=(time.perf_counter() - t0) * 1000)  # fmt: skip
        return route

    def _build(self, found):
        path, dist, charges = [], 0.0, []
        for (node, level), tag in zip(found.states, found.tags):
            if tag is None:  # arco verso lo stato terminale
                continue
            if tag[0] == "drive":
                path += tag[1].path if not path else tag[1].path[1:]
                dist += tag[1].meters
            else:
                if not charges or charges[-1][0] != node:
                    charges.append([node, 0.0, 0.0, level / self.steps, level / self.steps])
                stop = charges[-1]
                stop[1] += self.unit
                stop[2] += tag[1]
                stop[4] = (level + 1) / self.steps
        arrival = found.states[-2][1] / self.steps
        return Route(path, found.cost, dist, [tuple(c) for c in charges], arrival)

    def _plan_dijkstra(self, start, goal, start_soc, min_soc):
        return self._run(start, goal, start_soc, min_soc, heuristic="none")

    def _plan_astar(self, start, goal, start_soc, min_soc):
        return self._run(start, goal, start_soc, min_soc, heuristic="time")

    def _plan_astar_energy(self, start, goal, start_soc, min_soc):
        return self._run(start, goal, start_soc, min_soc, heuristic="energy")

    def _plan_wastar(self, start, goal, start_soc, min_soc, weight=2.0):
        return self._run(start, goal, start_soc, min_soc, heuristic="energy", weight=weight)

    def _plan_ara(self, start, goal, start_soc, min_soc, eps=3.0, decrease=0.5):
        return self._run(
            start, goal, start_soc, min_soc, heuristic="energy", anytime={"eps": eps, "decrease": decrease}
        )

    # ---------- confronti ----------
    def _plan_greedy(self, start, goal, start_soc, min_soc, charge_to=0.8):
        """Guidatore ingenuo: va alla stazione raggiungibile più vicina alla meta e carica fino a `charge_to`."""
        t0 = time.perf_counter()
        cap = self.vehicle.capacity_kwh
        soc, node, t, dist, visited = start_soc * cap, start, 0.0, 0.0, {start}
        path, charges, arrived = [start], [], False
        while True:
            legs = {
                b: min(ls, key=lambda leg: leg.time_s)
                for b, ls in self._legs(node, self.stations | {goal}).items()
            }
            if arrived:  # sosta: all'80%, o quanto serve per arrivare se non basta
                target = charge_to * cap
                if goal in legs:
                    target = max(target, min(cap, legs[goal].kwh + min_soc * cap))
                added = max(0.0, target - soc)
                if added > 0:
                    kw = min(self.vehicle.max_charge_kw, self.G.nodes[node]["charger_kw"])
                    secs = added / kw * 3600
                    charges.append((node, added, secs, soc / cap, (soc + added) / cap))
                    soc, t = soc + added, t + secs
            reachable = {b: leg for b, leg in legs.items() if soc - leg.kwh >= min_soc * cap - 1e-9}
            if goal in reachable:
                nxt = goal
            else:
                options = [b for b in reachable if b not in visited]
                if not options:
                    raise NoRouteError("the naive driver is stranded")
                g = self.G.nodes[goal]
                nxt = min(
                    options, key=lambda b: _hav(self.G.nodes[b]["y"], self.G.nodes[b]["x"], g["y"], g["x"])
                )
            leg = reachable[nxt]
            path += leg.path[1:]
            soc, t, dist, node = soc - leg.kwh, t + leg.time_s, dist + leg.meters, nxt
            if node == goal:
                break
            visited.add(node)
            arrived = True
        route = Route(path, t, dist, charges, soc / cap)
        route.stats.update(expanded=len(visited), search_ms=(time.perf_counter() - t0) * 1000)
        return route

    def _plan_exact(self, start, goal, start_soc, min_soc):
        """Riferimento: ricerca a etichette (tempo, carica) sulla rete stradale, con dominanza.

        Nessun grafo ridotto, energia per arco senza arrotondamenti; la carica avanza a passi di un livello,
        quindi a granularità fine ma non un ottimo assoluto.
        """
        t0 = time.perf_counter()
        G, cap = self.G, self.vehicle.capacity_kwh
        min_kwh, h = min_soc * cap, time_heuristic(G, goal)
        labels = [(start, 0.0, start_soc * cap, -1, None)]  # nodo, tempo, kWh, genitore, mossa
        heap, best_soc, expanded = [(h(start), 0.0, 0)], {}, 0
        while heap:
            _, t, i = heapq.heappop(heap)
            node, _, soc, _, _ = labels[i]
            if soc <= best_soc.get(node, -INF) + 1e-12:
                continue  # dominata: esiste un'etichetta già chiusa con più carica (e tempo minore o uguale)
            best_soc[node] = soc
            expanded += 1
            if node == goal:
                return self._exact_route(labels, i, t, expanded, (time.perf_counter() - t0) * 1000)
            nxt = []
            for _, v, d in G.out_edges(node, data=True):
                left = soc - self._energy(d)
                if left >= min_kwh - 1e-12:
                    nxt.append((v, t + d["travel_time"], left, ("drive", node, v, d["length"])))
            if node in self.stations and soc + self.unit <= cap + 1e-9:
                secs = self._charge_secs(node)
                nxt.append((node, t + secs, soc + self.unit, ("charge", secs)))
            for v, nt, nsoc, move in nxt:
                if nsoc > best_soc.get(v, -INF) + 1e-12:
                    labels.append((v, nt, nsoc, i, move))
                    heapq.heappush(heap, (nt + h(v), nt, len(labels) - 1))
        raise NoRouteError("no route with this battery and these stations")

    def _exact_route(self, labels, i, t, expanded, ms):
        cap, chain = self.vehicle.capacity_kwh, []
        arrival = labels[i][2] / cap
        while i != -1:
            chain.append(labels[i])
            i = labels[i][3]
        chain.reverse()
        path, dist, charges = [chain[0][0]], 0.0, []
        for k in range(1, len(chain)):
            node, _, soc, _, move = chain[k]
            if move[0] == "drive":
                path.append(node)
                dist += move[3]
            else:
                if not charges or charges[-1][0] != node:
                    charges.append([node, 0.0, 0.0, (soc - self.unit) / cap, 0.0])
                stop = charges[-1]
                stop[1] += self.unit
                stop[2] += move[1]
                stop[4] = soc / cap
        route = Route(path, t, dist, [tuple(c) for c in charges], arrival)
        route.stats.update(expanded=expanded, search_ms=ms)
        return route
