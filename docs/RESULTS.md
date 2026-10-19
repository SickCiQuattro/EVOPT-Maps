# Measured results

Regenerate with `uv run python -m benchmarks.compare` (synthetic grids) and `uv run --env-file .env python -m benchmarks.compare --local milano-torino` (real roads, see [Realistic test](../README.md#realistic-test)). One laptop core, pure Python, 3 minutes of plug-in time per stop.

**Real trip: Milano Duomo to Torino Porta Nuova** (47,068 nodes, 86,195 edges, 859 charger nodes). Renault Twingo Electric (21.3 kWh usable), 0 °C, from 90% to at least 10%, planned at the speed limit (130 km/h on the motorway). The best plan takes two stops and 142.6 minutes.

Road-level search between the two points:

| Algorithm | Trip (min) | States | ms |
| --- | --- | --- | --- |
| Dijkstra | 80.84 | 40,202 | 105 |
| A\*, straight line | 80.84 | 17,580 | 120 |
| A\* + ALT (8 landmarks) | 80.84 | 4,824 | 32 |
| Weighted A\* (w=2) | 95.92 (+18.7%) | 5,024 | 15 |
| ARA\*, first answer (w=3) | 95.92 (+18.7%) | 632 | |
| ARA\*, final | 80.84 | 18,013 | 56 |

ALT needs 1.9 s of preprocessing, once per graph.

Electric trip, with charging (legs already computed):

| Algorithm | Trip (min) | Stops | States | Search (ms) |
| --- | --- | --- | --- | --- |
| Dijkstra | 142.61 | 2 | 48,638 | 17,034 (also builds the missing legs) |
| A\*, straight line | 142.61 | 2 | 41,790 | 4,090 |
| A\*, energy-aware | 142.61 | 2 | 41,265 | 3,944 |
| **A\*, exact potentials** | 142.61 | 2 | **16,040** | **1,769** |
| Weighted A\* (w=1.5) | 153.13 (+7.4%) | 4 | 4,700 | 703 |
| ARA\* | 142.61 | 2 | 52,816 | 6,076 |
| Naive driver | 195.34 (+37.0%) | 2 | 3 | 120 |

The naive driver heads for the reachable charger nearest the destination, ignoring chargers slower than half the vehicle's maximum charge power when a faster one is reachable, and charges to 80% (more if that is not enough to arrive). Without the power rule it picked a slow charger and lost 239%, which says more about the rule than about the planner, so it was added.

Weighted A\* trades quality for effort in a steep way on this trip:

| Weight | Trip | States | vs optimal states |
| --- | --- | --- | --- |
| 1.05 | +0.0% | 15,850 | 99% |
| 1.1 | +0.0% | 13,990 | 87% |
| 1.25 | +5.2% | 9,345 | 58% |
| 1.5 | +7.4% | 4,700 | 29% |
| 2.0 | +24.9% | 650 | 4% |

ARA\* anytime profile: weight 3 gives +24.7% after 115 states, weight 2 gives +14.8% after 154, weight 1.5 gives +11.1% after 7,914 states (15% of its final effort), then the optimum after 52,816.

**Synthetic grid, 60x60** (3,600 nodes, 80 stations, three stops): Dijkstra 9,521 states, A\* 9,279, A\* with exact potentials 6,954; naive driver 1.6% slower; exact reference 596,823 states in 2.8 s against 47 ms for the reduced graph, within 0.1% of its result.

What the numbers say:

- **On real roads the heuristic matters a lot.** At road level ALT expands 8 times fewer states than Dijkstra and 3.6 times fewer than straight-line A\*, because real roads are far from straight. On the electric problem the exact backward potentials expand 67% fewer states than Dijkstra and 62% fewer than A\*, and search 2.3 times faster than A\*. On a small synthetic grid the same gain is only 27%: it grows with the size of the problem.
- **The energy-aware heuristic with a per-metre bound is barely better than plain A\*** (41,265 against 41,790 states). The potentials, which use the true minimum energy to the goal, are what pays.
- **Most of the cost is the legs between chargers**, not the search: each is a road search of about 35 ms in Python. Computing them lazily, reusing them and saving them to disk is the biggest saving. The first plan on this corridor takes about 28 s including geocoding; after a restart about 9 s (the table is read from disk) and 4.5 s while the server stays up. A strong heuristic also wins because it reaches fewer stations.
- **ARA\* is useful as a progress bar, not as a shortcut here.** Its answers improve steadily and each carries a proven bound, but to land within about 11% it needs 15% of the final effort, and the final optimum costs more than plain A\*.
- **Free stops mislead.** With no plug-in time a greedy search stops at every charger (10 stops where 4 were optimal); with a realistic plug-in time the same search behaves.
- **The naive driver loses 37% on the real trip.** On the easier grid it loses under 2%.
- **The reduced graph agrees with the exact reference** within 0.1%.
- **Pareto legs cost 7 to 8 times more** to build and gave the same trip on the grids.

