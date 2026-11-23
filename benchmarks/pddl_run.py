"""Run the PDDL planners of the `pddl` dependency group on an exported instance and compare with the references.

Usage: uv run --python 3.13 --group pddl python -m benchmarks.pddl_run corridor 10 30 --planners fd symk
Each run is a subprocess killed after `--timeout` seconds; an unsolved run is reported as such, never dropped.
"""

import argparse
import importlib.util
import os
import re
import signal
import subprocess
import sys
import tempfile
import time
from functools import partial
from pathlib import Path

from benchmarks import pddl_models as models
from benchmarks.pddl_export import CAR, SCALE, corridor, corridor_filter, export, reference
from evopt.planner import Planner


def _package(name):
    spec = importlib.util.find_spec(name)
    if spec is None:
        raise RuntimeError(f"{name} is not installed: run with `uv run --python 3.13 --group pddl`")
    return Path(spec.submodule_search_locations[0])


def _run(cmd, cwd, timeout):
    """(stdout, seconds, peak MB or None); stdout is None on timeout. The whole process group is killed."""
    timed = ["/usr/bin/time", "-l"] if sys.platform == "darwin" else ["/usr/bin/time", "-v"]
    t0 = time.perf_counter()
    proc = subprocess.Popen(
        timed + cmd,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        start_new_session=True,
    )
    try:
        out, _ = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)
        proc.communicate()
        return None, time.perf_counter() - t0, None
    secs = time.perf_counter() - t0
    mac = re.search(r"(\d+)\s+maximum resident set size", out)  # bytes
    linux = re.search(r"Maximum resident set size \(kbytes\): (\d+)", out)
    return out, secs, int(mac.group(1)) / 2**20 if mac else int(linux.group(1)) / 1024 if linux else None


def _write(directory, **files):
    for name, text in files.items():
        (Path(directory) / f"{name}.pddl").write_text(text)


def fast_downward(inst, timeout, symbolic=False):
    """Classical model with A* and LM-cut (Fast Downward) or symbolic bidirectional search (SymK)."""
    pkg = _package("up_symk" if symbolic else "up_fast_downward")
    script = pkg / ("symk" if symbolic else "downward") / "fast-downward.py"
    search = "sym_bd()" if symbolic else "astar(lmcut())"
    with tempfile.TemporaryDirectory() as tmp:
        _write(tmp, domain=models.CLASSICAL_DOMAIN, problem=models.classical(inst))
        out, secs, mb = _run(
            [
                sys.executable,
                str(script),
                "--plan-file",
                "plan",
                "--sas-file",
                "o.sas",
                "domain.pddl",
                "problem.pddl",
                "--search",
                search,
            ],
            tmp,
            timeout,
        )
        plan = Path(tmp, "plan")
        cost = re.search(r"cost = (\d+)", plan.read_text()).group(1) if plan.exists() else None
    ground = re.search(r"Translator operators: (\d+)", out or "")
    return {"cost": int(cost) / SCALE if cost else None, "seconds": secs, "peak_mb": mb,
            "timeout": out is None, "operators": int(ground.group(1)) if ground else None}  # fmt: skip


def enhsp(inst, timeout, model="hybrid", config="sat-hmrp", unit_steps=10, step=None):
    """ENHSP (bundled in up-enhsp) on the numeric or the PDDL+ model; cost is the plan's end time or total cost."""
    jar = _package("up_enhsp") / "ENHSP" / "enhsp.jar"
    domain, problem = (
        (models.NUMERIC_DOMAIN, models.numeric(inst, unit_steps)) if model == "numeric"
        else (models.HYBRID_DOMAIN, models.hybrid(inst))
    )  # fmt: skip
    extra = ["-dp", str(step), "-de", "1"] if step else []
    with tempfile.TemporaryDirectory() as tmp:
        _write(tmp, domain=domain, problem=problem)
        out, secs, mb = _run(
            ["java", "-jar", str(jar), "-o", "domain.pddl", "-f", "problem.pddl", "-planner", config, *extra],
            tmp,
            timeout,
        )
    found = re.search(r"Metric \(Search\):\s*([\d.]+)|Plan-Length:", out or "")
    cost = re.search(r"Metric \(Search\):\s*([\d.]+)", out or "")
    end = re.findall(r"^([\d.]+):\s*\(", out or "", re.MULTILINE)
    expanded = re.search(r"Expanded Nodes:\s*(\d+)", out or "")
    value = float(cost.group(1)) if cost else None
    if model == "hybrid" and end:
        value = float(
            end[-1]
        )  # a PDDL+ plan ends at the last action; the time to the goal is added by the metric
    return {"cost": value if found else None, "seconds": secs, "peak_mb": mb, "timeout": out is None,
            "expanded": int(expanded.group(1)) if expanded else None}  # fmt: skip


REAL = {  # extract -> (origin, target) as lat,lon
    "milano-torino": ((45.4642, 9.1900), (45.0620, 7.6780)),
    "torino-courmayeur": ((45.0703, 7.6869), (45.7840, 6.9760)),
}


def instance(
    kind,
    n,
    length_km=600,
    corridor_km=None,
    min_kw=0.0,
    forward_km=None,
    vehicle="MINI Electric",
    temp_c=0.0,
    steps=100,
):
    """(planner, instance, (start, goal)); `n` is the number of chargers of a synthetic corridor, ignored on real roads."""
    if kind == "corridor":
        G, s, g = corridor(n, length_km=length_km)
        planner = Planner(G, CAR, 20, steps=steps, plug_in_s=180)
        return planner, export(planner, s, g, 0.9, 0.1), (s, g)
    from evopt.api import _table_path
    from evopt.data import load_network
    from evopt.graph import nearest_node
    from evopt.vehicle import VEHICLES

    G = load_network(f"local:{kind}")
    (a, b) = REAL[kind]
    s, g = nearest_node(G, *a), nearest_node(G, *b)
    planner = Planner(G, VEHICLES[vehicle], temp_c, steps=steps, plug_in_s=180)
    planner.load_table(_table_path(planner))
    keep = corridor_filter(G, s, g, corridor_km, min_kw) if corridor_km else None
    return planner, export(planner, s, g, 0.9, 0.1, keep, forward_km), (s, g)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("kind", choices=["corridor", *REAL])
    ap.add_argument("sizes", type=int, nargs="+")
    ap.add_argument(
        "--planners", nargs="+", default=["fd", "symk"], choices=["fd", "symk", "numeric", "hybrid"]
    )
    ap.add_argument(
        "--corridor-km", type=float, default=None, help="real roads: keep chargers this close to the line"
    )
    ap.add_argument("--min-kw", type=float, default=0.0, help="real roads: drop chargers below this power")
    ap.add_argument(
        "--forward-km",
        type=float,
        default=None,
        help="real roads: drop legs that move this far from the goal",
    )
    ap.add_argument("--steps", type=int, default=100, help="charge levels")
    ap.add_argument("--length-km", type=float, default=600, help="synthetic corridor: road length")
    ap.add_argument("--vehicle", default="MINI Electric")
    ap.add_argument("--temp", type=float, default=0.0)
    ap.add_argument("--timeout", type=float, default=300)
    ap.add_argument(
        "--config", default=None, help="ENHSP configuration (numeric: opt-hrmax, hybrid: sat-hmrp)"
    )
    ap.add_argument("--unit-steps", type=int, default=10, help="numeric model: charging blocks per battery")
    ap.add_argument(
        "--step", type=float, default=None, help="PDDL+ model: time step in seconds (ENHSP default 1)"
    )
    args = ap.parse_args()
    print("| chargers | legs | Dijkstra (s) | exact (s) | planner | cost (s) | wall (s) | peak MB | note |")
    print("|---|---|---|---|---|---|---|---|---|")
    for n in args.sizes:
        planner, inst, (s, g) = instance(
            args.kind,
            n,
            args.length_km,
            args.corridor_km,
            args.min_kw,
            args.forward_km,
            args.vehicle,
            args.temp,
            args.steps,
        )
        ref = reference(inst)
        exact = planner.plan(s, g, algorithm="exact", start_soc=0.9, min_soc=0.1).time_s  # continuous charge
        runs = {
            "fd": partial(fast_downward, inst, args.timeout),
            "symk": partial(fast_downward, inst, args.timeout, True),
            "numeric": partial(
                enhsp, inst, args.timeout, "numeric", args.config or "opt-hrmax", args.unit_steps
            ),
            "hybrid": partial(enhsp, inst, args.timeout, "hybrid", args.config or "sat-hmrp", step=args.step),
        }
        for name in args.planners:
            r = runs[name]()
            note = (
                "timeout"
                if r["timeout"]
                else "no plan"
                if r["cost"] is None
                else f"{r['cost'] - ref:+.1f} s vs Dijkstra"
            )
            cost = "-" if r["cost"] is None else f"{r['cost']:.1f}"
            mb = "-" if r["peak_mb"] is None else f"{r['peak_mb']:.0f}"
            print(
                f"| {len(inst.peaks)} | {len(inst.legs)} | {ref:.1f} | {exact:.1f} | {name} | {cost} | {r['seconds']:.1f} | {mb} | {note} |",
                flush=True,
            )


if __name__ == "__main__":
    main()
