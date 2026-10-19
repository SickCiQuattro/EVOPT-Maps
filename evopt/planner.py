"""Trip planning for an electric car with charging stops: several algorithms on the same problem.

The problem: start, goal and chargers form a reduced graph; a state is (node, charge level).
Driving between two points spends levels and takes time; charging at a station adds a level and takes time.
Dijkstra, A*, Weighted A* and ARA* solve this graph; "greedy" is a naive driver kept for comparison
and "exact" is a label search on the road network (no reduced graph, unrounded per-edge energy), a reference.
"""

import hashlib
import heapq
import math
import pickle
import time
from collections import namedtuple

from evopt.router import NoRouteError, Route
from evopt.search import INF, _hav, ara, search, straight_speed, time_heuristic

ALGORITHMS = ("dijkstra", "astar", "astar_energy", "astar_potential", "wastar", "ara", "greedy", "exact")
ALGORITHM_INFO = {
    "dijkstra": ("Dijkstra", "Optimal. Uninformed: expands states in order of cost only."),
    "astar": ("A*", "Optimal. Guided by the straight-line travel time to the destination."),
    "astar_energy": ("A*, energy-aware", "Optimal. Also counts the minimum charging time still needed to cover the distance."),
    "astar_potential": ("A*, exact potentials", "Optimal. Uses the true minimum drive time and energy to the goal, from a backward search."),
    "wastar": ("Weighted A* (w=1.5)", "Faster, at most 1.5x the optimal trip. Inflates the heuristic."),
    "ara": ("ARA*", "Anytime: a quick answer first, then improved step by step until provably optimal."),
    "greedy": ("Naive driver", "Baseline: heads for the charger nearest the destination and charges to 80% every time."),
    "exact": ("Exact reference", "Label search on the full road network, no reduced graph. Slow: for checking the others."),
}  # fmt: skip
Leg = namedtuple("Leg", "time_s kwh meters path")
MAX_GRADE = 0.12  # highest plausible average grade on a stretch between two junctions
GOAL = (-1, -1, False)  # terminal state: goal reached with any charge


class Planner:
    """Plans trips on a graph for one vehicle and temperature, reusing the legs between chargers."""

    def __init__(
        self, G, vehicle, temp_c=20, steps=100, legs="fastest", dominance=True, plug_in_s=0.0, elevation=True
    ):
        if legs not in ("fastest", "pareto"):
            raise ValueError("legs must be 'fastest' or 'pareto'")
        self.G, self.vehicle, self.temp_c, self.steps, self.legs_mode = G, vehicle, temp_c, steps, legs
        self.stations = frozenset(n for n, d in G.nodes(data=True) if "charger_kw" in d)
        self.unit = vehicle.capacity_kwh / steps
        self.use_elevation = (
            elevation  # False: ignore elevations (for comparison, or unreliable terrain data)
        )
        self.plug_in_s = plug_in_s  # fixed time per stop: plugging in and starting the charge
        self.dominance = (
            dominance  # prune (node, level) states beaten by a closed one with more charge, no higher cost
        )
        self._potential_cache = {}
        self.leg_searches = 0  # road-graph searches run so far
        self._min_kwh_per_m = None
        self._path_cache = {}  # (from, to, time, kWh) -> path of the leg
        self._adj = None  # compact adjacency with per-edge energy, built on the first search
        self._edge_cache = {}  # charger -> reduced-graph edges towards the other chargers
        self.table_dirty = False  # new legs not saved yet
        self._table = {}  # charger -> {charger: [Leg]}; valid while graph, vehicle and temperature stay the same

    # ---------- energy ----------
    def _energy(self, d, rise_m=0.0):
        return self.vehicle.edge_energy_kwh(
            d["length"], d["speed_kph"], d["travel_time"], self.temp_c, rise_m
        )

    def _rise(self, u, v, d):
        """Elevation change of edge u->v from the node elevations, capped at a plausible grade.

        shortcut: a hole in the elevation data would give absurd climbs; above a 12% average grade over a
        stretch the rise is clipped. With no elevations (or elevation=False) the rise is zero.
        """
        if not self.use_elevation:
            return 0.0
        eu, ev = self.G.nodes[u].get("elevation"), self.G.nodes[v].get("elevation")
        if eu is None or ev is None:
            return 0.0
        limit = MAX_GRADE * d["length"]
        return max(-limit, min(limit, ev - eu))

    def _charge_secs(self, node, level):
        """Seconds to charge the unit above `level`, at the power the curve gives halfway through that unit."""
        kw = self.vehicle.charge_power_kw((level + 0.5) / self.steps, self.G.nodes[node]["charger_kw"])
        return self.unit / kw * 3600

    # ---------- legs on the road graph ----------
    def _legs(self, src, targets, reverse=False):
        """{destination: [Leg]} from `src` (or towards `src` if reverse). A single search of the road graph."""
        self.leg_searches += 1
        return self._search_legs(src, targets, reverse)

    def _search_legs(self, src, targets, reverse=False):
        search_fn = self._pareto_legs if self.legs_mode == "pareto" else self._fastest_legs
        return search_fn(src, set(targets) - {src}, reverse)

    def _edges_all(self):
        self._edges(next(iter(self.G.nodes)))  # builds the adjacency
        return self._adj[0].values()

    def _edges(self, u, reverse=False):
        """Edges (other end, seconds, metres, kWh) leaving `u` (entering if reverse), energy already computed."""
        if self._adj is None:  # once per Planner: an edge's energy does not change between searches
            out, inn = {}, {}
            for u0, v0, d in self.G.edges(data=True):
                arc = (d["travel_time"], d["length"], self._energy(d, self._rise(u0, v0, d)))
                out.setdefault(u0, []).append((v0, *arc))
                inn.setdefault(v0, []).append((u0, *arc))
            self._adj = (out, inn)
        return self._adj[1 if reverse else 0].get(u, ())

    def _fastest_legs(self, src, targets, reverse):
        # shortcut: energy of the fastest path, not of the most frugal one; legs="pareto" avoids it
        cap = self.vehicle.capacity_kwh
        best, prev, done = {src: (0.0, 0.0, 0.0)}, {}, set()
        heap = [(0.0, src)]
        while heap:
            t, u = heapq.heappop(heap)
            if u in done:
                continue
            done.add(u)
            _, kwh, dist = best[u]
            for v, tt, length, e in self._edges(u, reverse):
                nt = t + tt
                if v in done or (v in best and best[v][0] <= nt):
                    continue
                nk = kwh + e
                if nk > cap:
                    continue
                best[v], prev[v] = (nt, nk, dist + length), u
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
        """Label-setting Dijkstra on (time, energy): keeps every non-dominated trade-off, up to `max_labels` per node."""
        cap = self.vehicle.capacity_kwh
        labels = [(src, 0.0, 0.0, 0.0, -1)]  # node, time, kWh, metres, parent
        heap, best_e, settled = [(0.0, 0.0, 0)], {}, {}
        while heap:
            t, e, i = heapq.heappop(heap)
            node, _, _, m, _ = labels[i]
            if e >= best_e.get(node, INF) - 1e-9 or len(settled.get(node, ())) >= max_labels:
                continue
            best_e[node] = e
            settled.setdefault(node, []).append(i)
            for v, tt, length, ev in self._edges(node, reverse):
                ne = e + ev
                if ne > cap or ne >= best_e.get(v, INF) - 1e-9:
                    continue
                labels.append((v, t + tt, ne, m + length, i))
                heapq.heappush(heap, (t + tt, ne, len(labels) - 1))
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
            # the table keeps only time, energy and metres: paths (hundreds of nodes each) are rebuilt
            # for the legs of the chosen trip only
            self._table[s] = {
                b: [Leg(leg.time_s, leg.kwh, leg.meters, None) for leg in ls]
                for b, ls in self._legs(s, self.stations).items()
            }
            self.table_dirty = True
        return self._table[s]

    def _leg_path(self, src, dst, leg):
        """Path of a table leg: repeats the search from `src` and takes the label equal to `leg`."""
        key = (src, dst, round(leg.time_s, 6), round(leg.kwh, 9))
        if key not in self._path_cache:
            for cand in self._search_legs(src, {dst}).get(dst, ()):
                self._path_cache[(src, dst, round(cand.time_s, 6), round(cand.kwh, 9))] = cand.path
        if key in self._path_cache:
            return self._path_cache[key]
        raise RuntimeError(
            "leg changed between table and route"
        )  # cannot happen: the search is deterministic

    # ---------- legs table on disk ----------
    def fingerprint(self):
        """Fingerprint of what the legs depend on: network, chargers, vehicle, temperature, mode."""
        G = self.G
        total = round(sum(d["travel_time"] + d["length"] for *_, d in G.edges(data=True)), 3)
        spec = (
            len(G),
            G.number_of_edges(),
            total,
            sorted(self.stations),
            self.vehicle,
            self.temp_c,
            self.legs_mode,
            # elevations change the energy of every edge: without them (or switched off) the legs differ
            round(sum(d.get("elevation", 0.0) for _, d in G.nodes(data=True)))
            if self.use_elevation
            else None,
        )
        return hashlib.sha1(repr(spec).encode()).hexdigest()[:16]

    def save_table(self, path):
        """Save the legs table. Files are local and trusted (pickle): never load someone else's."""
        try:
            with open(path, "wb") as f:
                pickle.dump({"fingerprint": self.fingerprint(), "table": self._table}, f)
        except OSError:
            return False
        self.table_dirty = False
        return True

    def load_table(self, path):
        try:
            with open(path, "rb") as f:
                saved = pickle.load(f)
            if saved["fingerprint"] != self.fingerprint():
                return False
            self._table, self._edge_cache = saved["table"], {}
        except (OSError, pickle.UnpicklingError, EOFError, KeyError, TypeError, AttributeError):
            return False
        self.table_dirty = False
        return True

    # ---------- planning ----------
    def plan(self, start, goal, start_soc=1.0, min_soc=0.1, algorithm="astar", **opts):
        if algorithm not in ALGORITHMS:
            raise ValueError(f"unknown algorithm {algorithm!r}; choose one of {ALGORITHMS}")
        t0 = time.perf_counter()
        route = getattr(self, f"_plan_{algorithm}")(start, goal, start_soc, min_soc, **opts)
        route.stats.update(
            algorithm=algorithm, total_ms=(time.perf_counter() - t0) * 1000, leg_searches=self.leg_searches
        )
        return route

    def _need(self, leg):
        return max(0, math.ceil(leg.kwh / self.unit - 1e-9))

    def _reduced(self, start, goal, start_soc, min_soc):
        """Outgoing edges of a node of the reduced graph, computed when the search expands it.

        From the start and towards the goal they are recomputed for every trip; between chargers a leg is computed
        the first time a charger is expanded, then kept in the table. Chargers the search never reaches cost nothing.
        """
        goal_legs = self._legs(goal, self.stations - {goal}, reverse=True)
        start_edges = None
        if start not in self.stations:
            start_edges = [
                (b, leg, self._need(leg))
                for b, ls in self._legs(start, self.stations | {goal}).items()
                for leg in ls
            ]

        def edges(node):
            if node == start and start_edges is not None:
                return start_edges
            if node not in self._edge_cache:
                self._edge_cache[node] = [
                    (b, leg, self._need(leg)) for b, ls in self._station_legs(node).items() for leg in ls
                ]
            to_goal = goal_legs.get(node)
            if not to_goal:
                return self._edge_cache[node]
            return self._edge_cache[node] + [(goal, leg, self._need(leg)) for leg in to_goal]

        return edges, int(start_soc * self.steps + 1e-9), math.ceil(min_soc * self.steps - 1e-9)

    def _state_graph(self, start, goal, start_soc, min_soc, need_potential=False):
        t0 = time.perf_counter()
        edges, level0, min_level = self._reduced(start, goal, start_soc, min_soc)
        steps, stations = self.steps, self.stations

        def succ(state):
            node, level, charging = state
            if node == goal:
                yield GOAL, 0.0, None
                return
            if node in stations and level < steps:
                secs = self._charge_secs(node, level) + (0.0 if charging else self.plug_in_s)
                yield (node, level + 1, True), secs, ("charge", secs)
            for b, leg, need in edges(node):
                if level - need >= min_level:
                    yield (b, level - need, False), leg.time_s, ("drive", leg)

        return (
            succ,
            (start, level0, False),
            self._heuristics(goal, min_level, need_potential),
            (time.perf_counter() - t0) * 1000,
        )

    def _potentials(self, goal):
        """Minimum time and minimum energy from every node to `goal`: two backward searches on the road graph."""
        if goal not in self._potential_cache:
            self._potential_cache[goal] = (
                self._backward(goal, 0),  # seconds
                self._backward(goal, 2),  # kWh
            )
            while len(self._potential_cache) > 8:
                del self._potential_cache[next(iter(self._potential_cache))]
        return self._potential_cache[goal]

    def _backward(self, goal, field):
        """Backward Dijkstra from the goal, using edge field `field` (0 seconds, 2 kWh) as the weight."""
        dist, done, heap = {goal: 0.0}, set(), [(0.0, goal)]
        while heap:
            w, u = heapq.heappop(heap)
            if u in done:
                continue
            done.add(u)
            for p, *arc in self._edges(u, reverse=True):
                nw = w + arc[field]
                if nw < dist.get(p, INF):
                    dist[p] = nw
                    heapq.heappush(heap, (nw, p))
        return dist

    def _heuristics(self, goal, min_level, need_potential=False):
        """Consistent heuristics on the (node, level) state: time only, or time plus the minimum charging still needed."""
        G, unit = self.G, self.unit
        if self._min_kwh_per_m is None:
            self._min_kwh_per_m = min(
                e / length for out in self._edges_all() for _, _, length, e in out if length > 0
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
            node, level, _ = state
            meters = _hav(G.nodes[node]["y"], G.nodes[node]["x"], g["y"], g["x"])
            # kWh missing for a straight-line trip, beyond what is available above the arrival threshold
            deficit = e_min * meters - (level - min_level) * unit
            return meters / speed + max(0.0, deficit) / p_max * 3600

        def potential(state):
            if state == GOAL:
                return 0.0
            node, level, _ = state
            t = times.get(node)
            if t is None:
                return INF  # the goal cannot be reached from here
            deficit = energies[node] - (level - min_level) * unit
            return t + max(0.0, deficit) / p_max * 3600

        h = {"none": lambda s: 0.0, "time": time_only, "energy": with_energy}
        if need_potential:
            times, energies = self._potentials(goal)
            h["potential"] = potential
        return h

    def _run(self, start, goal, start_soc, min_soc, heuristic, weight=1.0, anytime=None):
        succ, src, hs, prep_ms = self._state_graph(start, goal, start_soc, min_soc, heuristic == "potential")
        h = hs[heuristic]
        t0 = time.perf_counter()
        history = []
        if anytime:
            found = None
            for found in ara(succ, src, GOAL, h, **anytime):
                history.append({"eps": found.eps, "bound": found.bound, "time_s": found.cost, "expanded": found.expanded,
                                "ms": (time.perf_counter() - t0) * 1000})  # fmt: skip
        else:
            found = search(succ, src, GOAL, h, weight, self._prune() if self.dominance else None)
        if found is None:
            raise NoRouteError("no route with this battery and these stations")
        route = self._build(found)
        route.history = history
        route.stats.update(expanded=found.expanded, bound=found.bound, eps=found.eps, prep_ms=prep_ms,
                           search_ms=(time.perf_counter() - t0) * 1000)  # fmt: skip
        return route

    def _prune(self):
        # per node and per "already charging": suffix minima, best[l] = least g among closed states with level >= l
        best = {}

        def prune(state, g):
            if state == GOAL:
                return False
            node, level, charging = state
            own = best.setdefault((node, charging), [INF] * (self.steps + 1))
            other = best.get((node, True))
            # a state already charging has paid the plug-in time: it beats one that has not started
            if g >= own[level] - 1e-9 or (not charging and other is not None and g >= other[level] - 1e-9):
                return True
            for lv in range(level + 1):
                own[lv] = min(own[lv], g)
            return False

        return prune

    def _build(self, found):
        path, dist, charges = [], 0.0, []
        for ((node, level, _), tag), (nxt, _, _) in zip(zip(found.states, found.tags), found.states[1:]):
            if tag is None:  # edge to the terminal state
                continue
            if tag[0] == "drive":
                leg_path = tag[1].path or self._leg_path(node, nxt, tag[1])
                path += leg_path if not path else leg_path[1:]
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

    def _plan_astar_potential(self, start, goal, start_soc, min_soc):
        return self._run(start, goal, start_soc, min_soc, heuristic="potential")

    def _plan_wastar(self, start, goal, start_soc, min_soc, weight=1.5):
        return self._run(start, goal, start_soc, min_soc, heuristic="potential", weight=weight)

    def _plan_ara(self, start, goal, start_soc, min_soc, eps=3.0, decrease=0.5):
        return self._run(
            start, goal, start_soc, min_soc, heuristic="potential", anytime={"eps": eps, "decrease": decrease}
        )

    # ---------- baselines for comparison ----------
    def _plan_greedy(self, start, goal, start_soc, min_soc, charge_to=0.8):
        """Naive driver: heads for the reachable charger nearest the goal and charges up to `charge_to`."""
        t0 = time.perf_counter()
        cap = self.vehicle.capacity_kwh
        soc, node, t, dist, visited = start_soc * cap, start, 0.0, 0.0, {start}
        path, charges, arrived = [start], [], False
        while True:
            legs = {
                b: min(ls, key=lambda leg: leg.time_s)
                for b, ls in self._legs(node, self.stations | {goal}).items()
            }
            if arrived:  # at a stop: charge to 80%, or as much as needed to arrive if that is not enough
                target = charge_to * cap
                if goal in legs:
                    target = max(target, min(cap, legs[goal].kwh + min_soc * cap))
                added = max(0.0, target - soc)
                if added > 0:
                    secs, level_kwh = self.plug_in_s, soc
                    while level_kwh < soc + added - 1e-12:  # integrate the charging curve one unit at a time
                        step = min(self.unit, soc + added - level_kwh)
                        kw = self.vehicle.charge_power_kw(
                            (level_kwh + step / 2) / cap, self.G.nodes[node]["charger_kw"]
                        )
                        secs += step / kw * 3600
                        level_kwh += step
                    charges.append((node, added, secs, soc / cap, (soc + added) / cap))
                    soc, t = soc + added, t + secs
            reachable = {b: leg for b, leg in legs.items() if soc - leg.kwh >= min_soc * cap - 1e-9}
            if goal in reachable:
                nxt = goal
            else:
                options = [b for b in reachable if b not in visited]
                if not options:
                    raise NoRouteError("the naive driver is stranded")
                # common-sense rule: do not stop at a charger much slower than the vehicle if a decent one
                # is reachable (otherwise the comparison would be against a straw man)
                decent = [
                    b for b in options if self.G.nodes[b]["charger_kw"] >= 0.5 * self.vehicle.max_charge_kw
                ]
                options = decent or options
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
        """Reference: label search on (time, charge) over the road network, with dominance.

        No reduced graph and unrounded per-edge energy; charge advances in steps of one level,
        so it is fine-grained but not an absolute optimum.
        """
        t0 = time.perf_counter()
        G, cap = self.G, self.vehicle.capacity_kwh
        min_kwh, h = min_soc * cap, time_heuristic(G, goal)
        labels = [(start, 0.0, start_soc * cap, -1, None)]  # node, time, kWh, parent, move
        heap, best_soc, expanded = [(h(start), 0.0, 0)], {}, 0

        def dominated(node, charging, soc):  # one already charging has paid the plug-in time
            keys = [(node, True)] if charging else [(node, False), (node, True)]
            return any(soc <= best_soc.get(k, -INF) + 1e-12 for k in keys)

        while heap:
            _, t, i = heapq.heappop(heap)
            node, _, soc, _, move = labels[i]
            charging = move is not None and move[0] == "charge"
            if dominated(node, charging, soc):
                continue  # dominated: a closed label has more charge (and no greater time)
            best_soc[(node, charging)] = soc
            expanded += 1
            if node == goal:
                return self._exact_route(labels, i, t, expanded, (time.perf_counter() - t0) * 1000)
            nxt = []
            for v, tt, length, e in self._edges(node):
                left = soc - e
                if left >= min_kwh - 1e-12:
                    nxt.append((v, t + tt, left, ("drive", node, v, length)))
            if node in self.stations and soc + self.unit <= cap + 1e-9:
                secs = self._charge_secs(node, (soc + self.unit / 2) / cap * self.steps - 0.5) + (
                    0.0 if charging else self.plug_in_s
                )
                nxt.append((node, t + secs, soc + self.unit, ("charge", secs)))
            for v, nt, nsoc, mv in nxt:
                if not dominated(v, mv[0] == "charge", nsoc):
                    labels.append((v, nt, nsoc, i, mv))
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
