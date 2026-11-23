# PDDL and PDDL+ for EVOPT Maps: models, planners, prior work and a test plan

How the EVOPT problem (fastest trip with charging stops, over states `(charger, battery level)`) can be written in PDDL and PDDL+, which planners can run it here, what is already known, and a small experiment to find out whether it is worth doing. Every claim about papers, tools and companies links to a source that was opened; anything else is marked "not verified". Numbers marked **measured** come from runs on this Mac (Apple Silicon, one run each, so indicative only); the files are in the scratchpad, not in the repo.

**Verdict in one paragraph.** A generic planner will not beat the dedicated search on speed. Dedicated EV algorithms already solve country-scale and continental instances optimally in seconds ([Baum et al.](https://arxiv.org/abs/1910.09812)), and in my tests the classical encoding stopped scaling at 100 chargers. PDDL+ is a good fit for the *semantics*: charging is a continuous process whose rate depends on the charge, and the planner decides when to unplug. ENHSP solved a 4-place PDDL+ instance to within 1 s of the analytic optimum. It got there only after three modelling fixes, and blind optimal search already expanded about a million states on 3 places. Do it as a bounded, honest comparison with open code (one to two weeks), not as a replacement for the planner.

## 1. Modelling

The three models below are tested: each parses and solves with the planner named. Units: kWh and seconds. The tiny instances use a 50 kWh battery, chargers `a` (50 kW) and `b` (100 kW, vehicle limit), 180 s plug-in time, a 5 kWh (10%) arrival floor, and the EVOPT curve: constant power up to 80%, then power falling linearly to 30% of peak at 100% (`evopt/vehicle.py`, `charge_power_kw`).

### 1a. Classical PDDL with discretised levels (Fast Downward, SymK)

A direct copy of the EVOPT state graph. Battery levels are objects, leg feasibility is precomputed (static `drive-ok` facts only exist where the arrival level is at or above the floor), and the taper is baked into a per-charger, per-level step cost. Plug-in time is paid by a separate action; driving away unplugs.

```pddl
(define (domain ev-levels)
  (:requirements :strips :typing :action-costs)
  (:types place level)
  (:predicates
    (at ?p - place) (charger ?p - place) (plugged ?p - place)
    (charge ?l - level) (succ ?l1 ?l2 - level)
    (drive-ok ?from ?to - place ?l1 ?l2 - level))   ; static: leg feasible from l1, arrives at l2 >= min
  (:functions
    (total-cost) - number
    (leg-time ?from ?to - place) - number           ; seconds, integer
    (step-time ?c - place ?l - level) - number      ; seconds to charge one level above ?l at ?c (taper baked in)
    (plug-time) - number)
  (:action drive
    :parameters (?from ?to - place ?l1 ?l2 - level)
    :precondition (and (at ?from) (charge ?l1) (drive-ok ?from ?to ?l1 ?l2))
    :effect (and (not (at ?from)) (at ?to) (not (plugged ?from))
                 (not (charge ?l1)) (charge ?l2)
                 (increase (total-cost) (leg-time ?from ?to))))
  (:action plug-in
    :parameters (?c - place)
    :precondition (and (at ?c) (charger ?c))
    :effect (and (plugged ?c) (increase (total-cost) (plug-time))))
  (:action charge-step
    :parameters (?c - place ?l1 ?l2 - level)
    :precondition (and (at ?c) (plugged ?c) (charge ?l1) (succ ?l1 ?l2))
    :effect (and (not (charge ?l1)) (charge ?l2)
                 (increase (total-cost) (step-time ?c ?l1)))))
```

```pddl
(define (problem tiny-levels) (:domain ev-levels)
  ;; 50 kWh battery in 5 levels of 10 kWh; start at l4 (80%), arrive at >= l1 (10% rounded up)
  (:objects s a b g - place  l0 l1 l2 l3 l4 l5 - level)
  (:init (at s) (charge l4) (charger a) (charger b)
    (succ l0 l1) (succ l1 l2) (succ l2 l3) (succ l3 l4) (succ l4 l5)
    (= (total-cost) 0) (= (plug-time) 180)
    ;; a: 50 kW, b: 100 kW; the step above l4 is in the taper (power at 90% = 65% of peak)
    (= (step-time a l0) 720) (= (step-time a l1) 720) (= (step-time a l2) 720)
    (= (step-time a l3) 720) (= (step-time a l4) 1108)
    (= (step-time b l0) 360) (= (step-time b l1) 360) (= (step-time b l2) 360)
    (= (step-time b l3) 360) (= (step-time b l4) 554)
    ;; legs: s-a 20 kWh (2 levels), s-b 25 kWh (3), a-g 30 kWh (3), b-g 22 kWh (3)
    (= (leg-time s a) 3600) (drive-ok s a l3 l1) (drive-ok s a l4 l2) (drive-ok s a l5 l3)
    (= (leg-time s b) 4000) (drive-ok s b l4 l1) (drive-ok s b l5 l2)
    (= (leg-time a g) 3000) (drive-ok a g l4 l1) (drive-ok a g l5 l2)
    (= (leg-time b g) 2400) (drive-ok b g l4 l1) (drive-ok b g l5 l2))
  (:goal (at g))
  (:metric minimize (total-cost)))
```

**Measured:** SymK returns `drive s b, plug-in b, 3 x charge-step b, drive b g`, cost 7660 s, which is the hand-computed optimum. On a second generated instance (10 levels) Fast Downward A\* with LM-cut and SymK both return 7300 s, equal to a Python Dijkstra over `(node, level, plugged)`.

### 1b. Numeric PDDL 2.1 (ENHSP)

Charge becomes a real-valued fluent, so leg energy is exact rather than rounded up to a level. Charging stays in fixed steps of `unit` kWh, because numeric PDDL has no continuous action parameters.

```pddl
(define (domain ev-numeric)
  (:requirements :typing :numeric-fluents :action-costs)
  (:types place)
  (:predicates (at ?p - place) (charger ?p - place) (plugged ?p - place) (road ?from ?to - place))
  (:functions (soc) (cap) (min-soc) (knee) (taper-to) (unit) (plug-time) (total-cost)
              (leg-time ?from ?to - place) (leg-kwh ?from ?to - place) (peak ?c - place))
  (:action drive
    :parameters (?from ?to - place)
    :precondition (and (at ?from) (road ?from ?to) (>= (- (soc) (leg-kwh ?from ?to)) (min-soc)))
    :effect (and (not (at ?from)) (at ?to) (not (plugged ?from))
                 (decrease (soc) (leg-kwh ?from ?to)) (increase (total-cost) (leg-time ?from ?to))))
  (:action plug-in
    :parameters (?c - place)
    :precondition (and (at ?c) (charger ?c))
    :effect (and (plugged ?c) (increase (total-cost) (plug-time))))
  (:action charge-flat                           ; below the knee the cost of one unit is static
    :parameters (?c - place)
    :precondition (and (at ?c) (plugged ?c) (<= (+ (soc) (unit)) (* (knee) (cap))))
    :effect (and (increase (soc) (unit)) (increase (total-cost) (/ (* (unit) 3600) (peak ?c))))))
```

The taper step needs a cost that depends on `soc`:

```pddl
  (:action charge-taper
    :parameters (?c - place)
    :precondition (and (at ?c) (plugged ?c) (> (+ (soc) (unit)) (* (knee) (cap))) (<= (+ (soc) (unit)) (cap)))
    :effect (and (increase (soc) (unit))
                 (increase (total-cost) (/ (* (unit) 3600)
                   (* (peak ?c) (- 1 (* (- 1 (taper-to))
                     (/ (- (+ (soc) (/ (unit) 2)) (* (knee) (cap))) (* (- 1 (knee)) (cap))))))))))
```

The problem file is the PDDL+ one in 1c with `(= (soc) 45) (= (unit) 5) (= (total-cost) 0)`, `(:metric minimize (total-cost))` and without the timers.

**Measured (ENHSP 20, the build bundled in `up-enhsp` 0.1.1):** without `charge-taper`, `sat-hmrp`, `opt-hrmax` and `opt-blind` all return 7120 s, the exact optimum of this model (it is lower than the 7300 s of the level model because energy is not rounded up). With the exact `charge-taper` above, every configuration stops with a `NullPointerException` while evaluating the action cost. A taper cost written as a *linear* function of `soc` runs. The UP integration's optimal engine also declares that it does not accept fluents in action costs ([up-enhsp source](https://pypi.org/project/up-enhsp/), `ENHSPOptEngine.supported_kind`). So the 80% taper cannot be stated exactly in the numeric model: you approximate it, or you keep levels for charging.

### 1c. PDDL+ with processes and events (ENHSP)

PDDL+ ([Fox and Long, JAIR 2006](https://arxiv.org/abs/1110.2200)) adds processes (continuous change while a condition holds) and events (instantaneous changes the world triggers), the "start-process-stop" model. Driving is an action that starts a process, and an event fires on arrival. Plug-in time is a timed set-up process. Charging is two processes, the second with a rate that depends on the charge (`dsoc/dt = a - b·soc`). The planner chooses when to `unplug`, so the amount charged is continuous. ENHSP does not support durative actions ([README](https://github.com/hstairs/enhsp)), which is why every duration is written as a process and an event.

```pddl
(define (domain ev-hybrid)
  (:requirements :typing :fluents :time :negative-preconditions)
  (:types place)
  (:predicates
    (at ?p - place) (charger ?p - place) (road ?from ?to - place)
    (driving ?from ?to - place) (setting-up ?c - place) (charging ?c - place)
    (idle) (used ?c - place))
  (:functions
    (soc) (cap) (min-soc) (knee) (taper-to) (plug-time)
    (leg-time ?from ?to - place) (leg-kwh ?from ?to - place)
    (peak ?c - place) (setup ?c - place) (elapsed ?from ?to - place))
  (:action start-drive
    :parameters (?from ?to - place)
    :precondition (and (idle) (at ?from) (road ?from ?to)
                       (>= (- (soc) (leg-kwh ?from ?to)) (min-soc)))
    :effect (and (not (idle)) (not (at ?from)) (driving ?from ?to)
                 (assign (elapsed ?from ?to) 0)))
  (:process drive
    :parameters (?from ?to - place)
    :precondition (driving ?from ?to)
    :effect (and (increase (elapsed ?from ?to) (* #t 1))
                 (decrease (soc) (* #t (/ (leg-kwh ?from ?to) (leg-time ?from ?to))))))
  (:event arrive
    :parameters (?from ?to - place)
    :precondition (and (driving ?from ?to) (>= (elapsed ?from ?to) (leg-time ?from ?to)))
    :effect (and (not (driving ?from ?to)) (at ?to) (idle)))
  (:action plug-in
    :parameters (?c - place)
    :precondition (and (idle) (at ?c) (charger ?c) (not (used ?c)))
    :effect (and (not (idle)) (used ?c) (setting-up ?c)))
  (:process set-up
    :parameters (?c - place)
    :precondition (setting-up ?c)
    :effect (increase (setup ?c) (* #t 1)))
  (:event ready
    :parameters (?c - place)
    :precondition (and (setting-up ?c) (>= (setup ?c) (plug-time)))
    :effect (and (not (setting-up ?c)) (charging ?c)))
  (:process charge-flat                      ; constant power up to the knee
    :parameters (?c - place)
    :precondition (and (charging ?c) (< (soc) (* (knee) (cap))))
    :effect (increase (soc) (* #t (/ (peak ?c) 3600))))
  (:process charge-taper                     ; power falls linearly with charge: dsoc/dt = a - b*soc
    :parameters (?c - place)
    :precondition (and (charging ?c) (>= (soc) (* (knee) (cap))) (< (soc) (cap)))
    :effect (increase (soc) (* #t (/ (* (peak ?c)
                                        (- 1 (* (- 1 (taper-to))
                                                (/ (- (soc) (* (knee) (cap))) (* (- 1 (knee)) (cap))))))
                                     3600))))
  (:event full
    :parameters (?c - place)
    :precondition (and (charging ?c) (>= (soc) (cap)))
    :effect (and (not (charging ?c)) (idle)))
  (:action unplug
    :parameters (?c - place)
    :precondition (charging ?c)
    :effect (and (not (charging ?c)) (idle))))
```

```pddl
(define (problem tiny-hybrid) (:domain ev-hybrid)
  (:objects s a b g - place)
  (:init (at s) (idle) (charger a) (charger b)
    (= (soc) 45) (= (cap) 50) (= (min-soc) 5) (= (knee) 0.8) (= (taper-to) 0.3) (= (plug-time) 180)
    (= (setup a) 0) (= (setup b) 0)
    (= (elapsed s a) 0) (= (elapsed s b) 0) (= (elapsed a g) 0) (= (elapsed b g) 0)
    (= (elapsed a b) 0) (= (elapsed b a) 0)
    (= (peak a) 50) (= (peak b) 100)
    (road s a) (= (leg-time s a) 3600) (= (leg-kwh s a) 30)
    (road s b) (= (leg-time s b) 4000) (= (leg-kwh s b) 32)
    (road a g) (= (leg-time a g) 3000) (= (leg-kwh a g) 28)
    (road b g) (= (leg-time b g) 2400) (= (leg-kwh b g) 22)
    (road a b) (= (leg-time a b) 900)  (= (leg-kwh a b) 6)
    (road b a) (= (leg-time b a) 900)  (= (leg-kwh b a) 6))
  (:goal (at g))
  (:metric minimize (total-time)))
```

**Measured (ENHSP 20, `-planner sat-hmrp`, default time step 1 s):** plan `start-drive s b` at 0, `plug-in b` at 4000, `unplug b` at 4684, `start-drive b g` at 4684, total 7084 s. The analytic continuous optimum is 4000 + 180 + 14 kWh/100 kW + 2400 = 7084 s. The search took 142 ms and 7,089 expansions. With a 10 s step (`-dp 10 -de 1`) the plan is 7090 s. With the `b-g` leg raised to 38 kWh, charging runs 3 kWh into the taper: ENHSP returns 7674 s against 7673.2 s from integrating the curve analytically, so the non-linear process is honoured within one time step. `-planner opt-blind` returns the same plans but expanded 1,079,303 states on a 3-place instance (1 s step) and 470,840 on the 4-place one (10 s step).

**Modelling pitfalls found on the way (measured, ENHSP 20).** None of these is documented on the pages I opened:
- A single shared `clock` fluent for all timers made ENHSP find a plan in search but fail in plan extraction (`RuntimeException: This can't be possible`). One timer per leg and per charger fixed it.
- The arrival floor as an ENHSP global `:constraint` caused the same extraction failure. A departure precondition is exact here, because consumption is linear in time along a leg.
- Without `(used ?c)` the search explores plug/unplug/re-plug cycles (millions of states in 120 s, no plan).
- On an unsolvable instance the search never terminates: waiting is always possible and time is unbounded.

### What each language can express

| Feature | Classical (1a) | Numeric (1b) | PDDL+ (1c) |
| --- | --- | --- | --- |
| Energy of a leg | rounded up to a level | exact | exact, consumed along the leg |
| 80% taper | exact per level, precomputed | not exact: state-dependent cost crashed ENHSP, linear surrogate only | exact as a process (ODE), within the time step |
| Amount charged | multiples of a level | multiples of `unit` | continuous (when to `unplug`) |
| Plug-in time | action cost | action cost | set-up process + event |
| Minimum arrival charge | in the static `drive-ok` facts | precondition | precondition at departure (or event) |
| Avoid a charger, minimum kW, known power only | drop `(charger c)` | same | same |
| Metric | `total-cost` (integer for FD/SymK) | `total-cost` | `total-time` |
| Optimality | yes (A\*/LM-cut, SymK) | yes for static costs (`opt-hrmax`) | only for the discretised model (`opt-blind`), not verified in docs |

The real gain of PDDL+ is not this problem as it stands but richer variants: time windows at chargers, prices that change with time of day, or a battery that must be warm before fast charging. Dedicated search can model these too, but each one costs code.

## 2. Planners

"Here" means macOS on Apple Silicon, Java 21, Python 3.13 via uv, no Rust toolchain, no Docker. I checked install routes on PyPI and GitHub on 23 November 2026.

| Planner | Language support | Optimality | Licence | Install route here | Maintained | Runs here |
| --- | --- | --- | --- | --- | --- | --- |
| ENHSP | numeric PDDL 2.1, PDDL+ processes and events (discretised, default step 1 s), global constraints; no durative actions ([site](https://sites.google.com/view/enhsp/), [README](https://github.com/hstairs/enhsp)) | optimal configurations for numeric planning; PDDL+ search is discretised | GPL-3.0 per GitHub sidebar, a COPYING.LESSER file is also present | `pip install up-enhsp`: the 65 MB wheel bundles `enhsp.jar` (tag `enhsp-20-0.15.0`); the sdist needs JDK 17 or newer and git | repo pushed 2026-04; ENHSP-25 listed as newest on the site | **yes, tested** |
| Nyx | full PDDL+ incl. non-linear, by discretisation; Python, no dependencies; BFS/DFS/GBFS/A\*, anytime ([paper](https://arxiv.org/html/2402.11901v1)) | none claimed | not verified | no public repository found (GitHub search, paper) | not verified | not verified |
| UPMurphi | full PDDL+, discretise and validate, no heuristic, only `minimize total-time` | not verified | not stated | Linux or Cygwin, 32-bit default ([page](https://gdellapenna.github.io/research/upmurphi)) | **no**, "no longer maintained" | no |
| DiNo | PDDL+, linear and non-linear, SRPG+ heuristic, only `minimize total-time`, typed domains ([repo](https://github.com/KCL-Planning/DiNo)) | not verified | LGPL-2.1 file plus a licence file | Linux/Cygwin, flex 2.5.39 | last push 2018 | no (not tried) |
| SMTPlan+ | all PDDL+ features, polynomial non-linear change, bounded number of happenings ([site](https://kcl-planning.github.io/SMTPlan/)) | not claimed | not stated | via planutils, which is Linux/Docker based ([planutils](https://github.com/AI-Planning/planutils)) | last push 2023-02 | no Docker here |
| Metric-FF | numeric, linear expressions only; FF.quality is weighted A\* on action costs ([home](https://fai.cs.uni-saarland.de/hoffmann/metric-ff.html)) | no optimality claim | GPL | source build, not tried on macOS | v2.1, undated | not verified |
| OPTIC | temporal PDDL 2.1 with linear continuous effects, duration inequalities, preferences; no PDDL+ processes ([planning.wiki](https://planning.wiki/ref/planners/optic)) | not stated | not stated | legacy source from KCL; CPLEX needed for preferences | OPTIC+ "not currently publicly available" | not verified |
| aries | in UP: classical, numeric (integers only), temporal, hierarchical, scheduling ([UP engines](https://unified-planning.readthedocs.io/en/latest/engines/01_available_engines.html)) | anytime, metrics listed | Apache-2.0 (Rust) / MIT (`up-aries`) | `up-aries` 0.5.0 sdist ships a prebuilt `up-aries_macos_arm64` binary, so no Rust is needed | repo active (2026-11) | likely; not tested |
| Tamer | classical, numeric, temporal, one-shot ([UP engines](https://unified-planning.readthedocs.io/en/latest/engines/01_available_engines.html)) | not verified | `pytamer`: "Free For Educational Use" (PyPI) | `pytamer` 0.1.22 has macOS wheels only for x86_64 and none for CPython 3.13 on macOS | `up-tamer` 2025-12 | **no** on arm64 + 3.13 |
| Fast Downward | classical with action costs, no numeric fluents | optimal with admissible heuristics (A\* + LM-cut) | GPL-3.0 | `pip install up-fast-downward` (macOS arm64 wheel) | active | **yes, tested** |
| SymK | classical optimal and top-k ([repo](https://github.com/speckdavid/symk)) | optimal, top-k plans | GPL-3.0 | `pip install up-symk` (macOS arm64 wheel) | active (2026-08) | **yes, tested** |
| Kairos | UP docs list processes and events; its own README says "Later: PDDL+" ([repo](https://github.com/PlanSys2/kairos)): conflicting, not verified | anytime; README shows a `ProvenOptimal` stop reason | Apache-2.0 | Linux wheels only | new (created 2026-10) | no |

Through the Unified Planning library, only Kairos is listed with process support ([UP engines](https://unified-planning.readthedocs.io/en/latest/engines/01_available_engines.html)). The `up-enhsp` engine nevertheless declares `PROCESSES` and `EVENTS` in its supported kind (source of `up_enhsp/enhsp_planner.py`). For PDDL+ I would call the jar directly, as in the tests above. Speed evidence for these planners on routing and resource domains: Nyx's paper reports expanded nodes per second on PDDL+ toy domains, with UPMurphi fastest on most and ENHSP fastest on Angry Birds ([Nyx paper, Table 2](https://arxiv.org/html/2402.11901v1)). ENHSP's repository ships numeric benchmarks with fuel and energy (Rover-Numeric, ZenoTravel). I found no published number for any of these planners on EV routing.

**Realistic here:** ENHSP (numeric and PDDL+), Fast Downward and SymK (classical), OR-tools CP-SAT (`ortools` has a CPython 3.13 macOS arm64 wheel), and probably aries. Nyx only if the code turns up.

## 3. Prior work

**PDDL and PDDL+ with batteries and fuel.**
- The PDDL+ paper's running example is a planetary lander whose battery charging "follows an inverse exponential function", with the rate proportional to the gap to full charge. That is the same shape as EVOPT's taper ([Fox and Long, JAIR 27, 2006](https://arxiv.org/abs/1110.2200)).
- Fox, Long and Magazzeni encode multiple-battery load management in PDDL+ and solve the deterministic instances with UPMurphi by discretise and validate. The resulting policies reach "more than 99% efficiency in simulation compared with the theoretical limit" ([JAIR 44, 2012](https://arxiv.org/abs/1401.5859)).
- IPC benchmarks with resources: numeric Rovers recharge "only at locations that are in the sun", and numeric ZenoTravel aircraft burn fuel at mode-dependent rates ([IPC 2002 domains](https://ipc02.icaps-conference.org/domains.html)). The IPC 2023 numeric track has a `drone` domain in which a UAV must return to base to recharge ([dataset](https://github.com/ipc2023-numeric/ipc2023-dataset/tree/main/drone)).
- Transport applications: PDDL+ for urban traffic control, with car flows as processes ([Vallati et al., AAAI 2016](https://doi.org/10.1609/aaai.v30i1.10399), metadata and abstract via Crossref). The closest to EVOPT is a PDDL+ approach to modular autonomous customised buses that covers "routes and recharges" ([Papamaximou, Guo, Percassi, Vallati, ICAART 2026](https://doi.org/10.5220/0014230600004052), abstract via OpenAlex; results not verified).
- Translating discretised PDDL+ to numeric planning lets more engines solve it ([Percassi, Scala, Vallati, JAIR 76, 2023](https://jair.org/index.php/jair/article/view/13904)). Temporal planning can also be compiled into PDDL+ ([Micheli, Scala, Valentini, 2026](https://arxiv.org/abs/2603.12188)).

I found **no paper that models single-vehicle EV trip planning with charging stops in PDDL or PDDL+** (web search, OpenAlex and Crossref queries for "PDDL electric vehicle", "PDDL+ electric vehicle", "automated planning electric vehicle charging PDDL"). The search was not exhaustive.

**Operations research and algorithms view.**
- Baum, Dibbelt, Gemsa, Wagner and Zündorf (Transportation Science 53(6), 2019, [doi:10.1287/trsc.2018.0889](https://doi.org/10.1287/trsc.2018.0889) via Crossref; full text read on [arXiv](https://arxiv.org/abs/1910.09812)) extend constrained shortest paths with charging stops at stations of varying power and with battery swaps; the problem is NP-hard. Their method, CHArge, combines a bicriteria contraction hierarchy with A\* potentials over charge and charging time, and models charging functions as piecewise linear and concave. Exact queries average "below 15 seconds" on Germany and "at most 100 seconds" on Europe; the heuristic CHArge-Hω takes 300 to 600 ms with errors of 0.1% on average and 5% in the worst case.
- Strehler, Merting and Schwan, "Energy-efficient shortest routes for electric and hybrid vehicles", TR Part B 103, 2017 ([record](https://econpapers.repec.org/RePEc:eee:transb:v:103:y:2017:i:c:p:111-135)): a constrained shortest path with convertible resources and charging stations, cycle classes, and approximation schemes with guaranteed feasibility.
- Montoya, Guéret, Mendoza and Villegas, "The electric vehicle routing problem with nonlinear charging function", TR Part B 103, 2017 ([record](https://econpapers.repec.org/RePEc:eee:transb:v:103:y:2017:i:c:p:87-110)): "neglecting nonlinear charging may lead to infeasible or overly expensive solutions". This supports EVOPT's taper.
- At ICAPS itself, EV route and charging planning is solved with dedicated search, not PDDL: multi-objective A\* with contraction hierarchies, 182,000 instances, more than 12,000 chargers, planning "in order of seconds" ([Cuchý, Vokřínek, Jakob, ICAPS 2024](https://doi.org/10.1609/icaps.v34i1.31467), abstract via Crossref). H-ANTS treats capacitated EVRP as hierarchical planning but solves it with an ant system ([ICAPS 2026](https://doi.org/10.1609/icaps.v36i1.42830), abstract via Crossref).

**What they find.** For EV trips the state of the art is dedicated label-setting or A\* search with preprocessing. EVOPT's design (reduced charger graph, charge-level states, potentials) is the same family. PDDL+ work on batteries exists, but on small hybrid systems where expressiveness matters more than scale. I found no head-to-head comparison of generic planners against dedicated EV algorithms; that gap is what section 5 is about.

## 4. Competitors

| Product | What public sources say | AI planning (PDDL)? |
| --- | --- | --- |
| Google Maps | Stations are replicated into entry/exit nodes per charge level, with charging edges between them; "Dijkstra or A\* recovers the solution". A greedy spanner prunes trips between stations, motivated by "billions of possible edges" ([Google Research, 2021](https://research.google/blog/addressing-range-anxiety-with-smart-electric-vehicle-routing/)). Routes with two or more stops in "less than 10 seconds" ([Google blog](https://blog.google/products/maps/charge-it-new-maps-features-electric-vehicles/)). A patent claims minimising driving plus charging time with non-linear vehicle and station charge curves ([US 12,479,324 B2](https://patentsgazette.uspto.gov/week47/OG/html/1540-4/US12479324-20251125.html)). | no mention |
| ABRP (Iternio, part of Rivian since June 2023, [ABRP](https://abetterrouteplanner.com/resources/article/2023-06-21_rivian-acquisition)) | Consumption starts from a "reference consumption" at 110 km/h, then elevation, temperature and speed are applied ([help](https://abrp.featurebase.app/articles/3305478-reference-consumption)). The Planning API v2 uses "the same route optimizer" as the app. It exposes minimum arrival SoC at chargers and destination, maximum charging SoC, `ChargingOverheadSec` (the plug-in time), excluded charger IDs, network preferences, and a stop-count bias whose default "gives shortest total trip time". Preliminary routes are "computed by OSRM only" ([API spec](https://api.iternio.com/swagger-ui/spec/prod/IternioPlanning.out.yaml)). The optimiser itself is **not public**. | no mention |
| Tesla | Trip Planner "selects a route and provides charging times to minimize the amount of time you spend driving and charging" (owner's manual, quoted in search results; the page returned 403 to my fetcher, so not verified directly) | not public |
| Apple Maps | Takes the vehicle's state of charge, elevation and estimated charging times into account, suggests compatible stations automatically, on supported cars ([Porsche, 2023](https://newsroom.porsche.com/en_US/2023/company/Porsche_introduces_support_for_Apple_Maps_EV_routing.html)). Algorithm **not public**. | not public |
| HERE | Routing API v8 takes a charging curve, charge limits and `ev[makeReachable]`; the route is "optimized to get the best travel time including the required charging stops" ([docs](https://docs.here.com/routing/docs/routing-v8-calculate-route-with-charging)). Algorithm **not public**. | no mention |
| TomTom | Long Distance EV Routing: a charging curve of up to 10 points, `chargingTimeOffsetInSec` (default 60 s), minimum charge at stops and at the destination; the default `automaticFastest` minimises total travel time including charging ([docs](https://docs.tomtom.com/long-distance-ev-routing-api/documentation/tomtom-maps/long-distance-ev-routing)). Algorithm **not public**. | no mention |
| Mapbox | EV routing in private preview: `ev_charging_curve`, minimum charge at stations and destination, `ev_exclude_station_ids`, preferred providers; occupied stations are penalised ([docs](https://docs.mapbox.com/api/navigation/directions)). Algorithm **not public**. | no mention |
| PlugShare | Trip planner shows recommended stops and lets the user pick stops and set charge times; ranking factors listed, method not described ([page](https://www.plugshare.com/trip-planner.html)) | no mention |
| Chargeprice | Route planner optimises mainly for price under the user's tariffs (press release, July 2026, [pv magazine](https://www.pv-magazine.de/unternehmensmeldungen/ende-des-tarif-dschungels-auf-der-langstrecke-chargeprice-launcht-intelligenten-preis-routenplaner-fuer-e-autos/)). Routing source and method **not public**. | no mention |

None of the sources I opened mentions AI planning or PDDL. The commercial APIs expose the same knobs as EVOPT (curve, plug-in overhead, arrival floor, excluded chargers), which shows EVOPT's model is the industry's model.

## 5. Innovation assessment

- **Not new:** PDDL+ for batteries (lander, multi-battery), numeric domains with recharging (Rovers, drone), PDDL+ in transport (traffic, MACB buses), and dedicated EV routing with charging curves (Baum et al., Google, Cuchý et al.).
- **Probably new, as far as I could search:** a PDDL+ model of EV trip planning with a non-linear charging process, generated from real OSM chargers and legs, run against an optimal dedicated search on the *same* reduced graph with a shared ground truth. Every model ships with open code and an instance generator. A related gap I found no paper on is the head-to-head comparison itself (generic planner against dedicated EV search).
- **Expected outcome:** the dedicated search wins on speed by orders of magnitude, as the measurements below already suggest. The publishable or presentable value is the *quantified* gap, the modelling lessons (the ENHSP pitfalls above), and a new benchmark domain with real data, not a faster planner.
- **What a reviewer would want:** correct semantics (plans validated, ideally with VAL), the same objective everywhere, honest time-outs, more than one PDDL+ planner, and the scaling curve. **What a recruiter would see:** formal modelling across three languages, reproducible benchmarks, and a willingness to publish a negative result with numbers.

## 6. Experiment plan

Same objective everywhere: total time in seconds, including 180 s per stop, arrival floor 10%. Ground truth: EVOPT's Dijkstra on the same reduced graph, with levels set so that the PDDL levels equal EVOPT's `steps`. Each phase has a time box; stop the phase when it runs out.

**(0) Exporter, 1 day.** Add `benchmarks/pddl_export.py` (outside `evopt/`): from a `Planner`, write stations, `charger_kw`, and the legs table (time, kWh) for start, goal and the chargers the search reached, as JSON. Write generators for the three PDDL variants from that JSON. Success: the classical model of the tiny instance gives the same cost as `Planner.plan(algorithm="dijkstra")` on the exported graph.

**(a) Classical, Fast Downward A\*/LM-cut and SymK, 2 days.** Synthetic corridors with 10, 30 and 100 chargers on a 600 km line, then the real Milano–Torino reduced graph. Success: cost equal to Dijkstra on every solved instance. Already **measured** on synthetic corridors with 100 levels:

| Chargers | Legs | Ground operators | FD A\*/LM-cut | SymK | Python Dijkstra (naive) |
| --- | --- | --- | --- | --- | --- |
| 10 | 42 | 2,570 | 0.8 s, optimal | about 1 s, optimal | 3.6 ms |
| 30 | 297 | 15,544 | 54.6 s, optimal | 5.8 s, optimal | 35 ms |
| 100 | 3,486 | 166,977 (translate 11.8 s) | no plan in 300 s | no plan in 300 s (lower bound 26,160 against optimum 26,161) | 1.4 s |

The real corridor is much larger: the cached legs table for the 859-charger Milano–Torino run holds 448,645 legs from 747 expanded chargers (measured from `cache/legs-0288e6e358aa7e06.pkl`). Fed in unpruned, that would be millions of ground `drive` actions (estimate, not measured). So phase (a) on real data needs the pruning in section 7.

**(b) Numeric, ENHSP, 2 days.** Same instances; `sat-hmrp`, `opt-hrmax`, `opt-blind`; taper as a linear surrogate or levels for charging only. Success: optimal configurations match Dijkstra on the flat-charging variant; report the gap the surrogate causes.

**(c) PDDL+, ENHSP, 3 days.** The model in 1c with step sizes of 60, 10 and 1 s. Validate plans with ENHSP's internal validation (`-ival`) or VAL. Success: the plan cost is within one step per event of the exact optimum, and the 30-charger corridor is solved within 300 s. Try Nyx only if its code is found, and UPMurphi or DiNo only with a Linux container.

**(d) Agreement and the OR baseline, 2 days.** On every instance compare against Dijkstra and A\* with exact potentials on the same reduced graph (the PDDL+ optimum is continuous, so compare it against EVOPT's `exact` reference too). OR baseline: CP-SAT or a MILP on the level-expanded graph. On that graph it is a shortest-path flow, so it mainly checks correctness. A more interesting OR model is a MILP with continuous SoC and a piecewise-linear charging function in the style of Montoya et al.

**Time-out policy:** 300 s and 8 GB per run, one core, 3 runs per instance, median reported. FD's `--overall-memory-limit` is not supported on macOS (measured), so use `ulimit` or run on Linux. Unsolved runs are reported as unsolved, never dropped.

**Metrics:** time to first plan, time to proven optimum, cost gap to Dijkstra (%), peak memory (macOS reports it in bytes where Linux uses KB, so check the units), ground actions and processes, expansions. **Instances:** corridors with 10, 30 and 100 chargers (3 seeds each), Milano–Torino and Torino–Courmayeur reduced graphs, cold (0 °C) and mild (20 °C).

## 7. Optimisation ideas for the PDDL side

- **Ground less.** Pass only the legs table, never the road graph, as the problem. Drop chargers outside a corridor around the straight line or the fastest route, and chargers below the vehicle's useful power. Drop dominated legs (one leg dominates another between the same chargers if it is no slower and uses no more energy).
- **Fewer levels.** Use 2% or 5% levels for a first plan, then refine near the stops chosen; or keep levels only for charging and real-valued energy for driving.
- **Remove symmetry in the model.** One plug-in per charger (`used`), as measured above. Charge only before a drive, never twice at the same place. Allow drives only towards the goal when a detour bound holds.
- **Heuristics.** Give the planner EVOPT's potentials: minimum time and energy to the goal per charger, as static fluents and extra preconditions (the potential becomes a landmark). SymK's top-k mode can produce the "if this charger is busy" alternatives in one run.
- **Hybrid use.** Use the dedicated search for the route and a planner for rich constraints on a short list of candidate stops, for example time windows, prices that change with time of day, or a busy-charger probability.
- **Caching.** Reuse the on-disk legs table and its fingerprint. Translation alone took 11.8 s at 100 chargers, so cache the translated SAS file (Fast Downward's `output.sas`) per corridor and vehicle.

## 8. Risks and recommendation

**Risks.**
- **Scale:** unpruned grounding blows up (section 6a).
- **PDDL+ planner maturity:** three undocumented modelling traps in one afternoon; UPMurphi is unmaintained; no Nyx code found; Kairos is Linux only, and its PDDL+ support is contradictory.
- **Discretisation:** plans are valid only at the chosen step, with errors per event.
- **Non-termination** on unsolvable instances.
- **Effort** that does not improve the product.

**Go** to phases (c) and (d) if, after phases (0) to (b): the exporter and the classical model agree with Dijkstra, ENHSP solves the 30-charger corridor in PDDL+ within 300 s, and the work stays within about two weeks. **No-go** if PDDL+ cannot solve the 30-charger corridor at any step size of 60 s or less, or if the costs disagree with Dijkstra in a way you cannot explain. In that case write it up and stop.

**What to say in the README if it loses** (draft):

> We also wrote the problem in classical PDDL, numeric PDDL and PDDL+ (charging as a continuous process with the 80% taper) and ran Fast Downward, SymK and ENHSP on the same reduced graph. Every plan they returned matched the dedicated search within discretisation, but they were thousands of times slower (30 chargers: 14 s to 265 s against 21 ms) and did not solve 100 chargers within 5 minutes. The models, generator and results are in `docs/PDDL.md`. The dedicated search stays the planner; PDDL+ is useful for prototyping richer constraints.

The numbers are now measured: see section 9.

## 9. Results

Run on 2026-11-23, one Mac (8 cores), one run per cell, so timings are indicative. Reproduce with `uv run --python 3.13 --group pddl python -m benchmarks.pddl_run <instance> <sizes> --planners ...` (the `pddl` group needs Python 3.13: OR-Tools has no wheel for 3.15). Every instance is exported from a `Planner` by `benchmarks/pddl_export.py`, and costs are integer milliseconds. The reference is a Dijkstra over `(charger, level, charging)` on the exported legs. It equals `Planner.plan(algorithm="dijkstra")` to 0.1 s (`tests/test_pddl.py`). Objective: total seconds including 180 s per stop, arrival at 10%. Corridors: 600 km at 110 km/h, 50 kWh car, chargers of 50, 100 or 150 kW, 100 levels.

### Phase 0 and (a): classical model, exact

| Chargers | Legs | Dijkstra (this repo) | Fast Downward A\*/LM-cut | SymK | CP-SAT (flow on levels) |
| --- | --- | --- | --- | --- | --- |
| 10 | 80 | 5 ms | 3.8 s, optimal | 1.7 s, optimal | 0.3 s, optimal |
| 30 | 592 | 21 ms | 265.1 s, optimal | 14.3 s, optimal | 4.5 s, optimal |
| 100 | 7,104 | 178 ms | timeout 300 s | timeout 300 s | 125.7 s, not proven optimal, 63,147 s against 23,588.8 s |

Every plan that finished has the same cost as Dijkstra to the millisecond. The A\* variant with exact potentials (`astar_potential`) takes 3.5, 8.6 and 65.8 ms on the same three instances.

**Cost resolution matters.** The 30-charger run took 54.6 s with costs in whole seconds (section 6) and 265.1 s with costs in milliseconds, for the same problem and the same optimum, because LM-cut gets many more distinct cost values to work with. Costs in tenths of a second looked fine on corridors but were 1.4 s off on the real Milano–Torino plan: 0.1 s rounds the same way at each of its 46 charge steps. A classical encoding therefore trades plan accuracy against search time.

**Real roads (Milano–Torino, MINI Electric, 0 °C, 90% to 10%).** The unpruned reduced graph has 506 chargers and 178,080 legs, and the dedicated search plans it in 1.4 s (Dijkstra) or 0.18 s (A\* with potentials). Fed to PDDL it would be about 16 million `drive-ok` facts at 100 levels (178,080 legs times about 90 feasible levels, an estimate). Pruning to chargers within 5 km of the straight line, and legs that do not move more than 5 km away from the goal, leaves 149 chargers and 10,415 legs, but the best plan on that graph takes 9,658 s against 5,988 s unpruned: pruning removes the fast route. On that pruned graph SymK solves 20 levels in 129.5 s (9,705.6 s, equal to Dijkstra) and nothing finishes at 100 levels in 300 s. Fast Downward times out at both.

### Phase (b): numeric PDDL, ENHSP

`opt-hrmax`, 10 chargers: 2.3 s, plan 24,300 s with charging in 5 kWh blocks and 24,085 s in 2.5 kWh blocks, against 23,900.3 s from Dijkstra and 23,872.2 s from the continuous reference, so the gap is the block size (+1.7% and +0.8%). At 30 chargers it times out at 300 s with either block size. `opt-blind` ran out of memory (3.9 GB) on the 10-charger instance. The linear taper surrogate was not isolated from the block effect.

### Phase (c): PDDL+, ENHSP

Corridors of 300 km, 1 s to 60 s time steps:

| Chargers | `sat-hmrp` (not optimal) | `opt-blind` | analytic optimum |
| --- | --- | --- | --- |
| 3 | 11,342 s at 60 s step, 11,309 s at 1 s step, 0.3 s | 11,341 s in 63.7 s, 1.7 GB | 11,306.9 s (4 chargers, computed by hand) |
| 4 | 11,341 s, 11,308 s at 1 s step, 0.3 s | timeout 180 s | |
| 5 to 10 | +200 to +387 s above Dijkstra (1.8% to 3.4%), under 2 s | timeout (5, 6) | |

On the instances where it is optimal, PDDL+ is within one step per event of the hand-computed optimum (11,308 s against 11,306.9 s at a 1 s step). The satisficing configuration is fast but returns plans 1.8% to 3.4% too slow from 5 chargers on, and `opt-hrmax` timed out at 180 s even with 3 chargers. The 30-charger corridor was never solved in PDDL+, which is the no-go condition set in section 8.

The Planner's `exact` reference is 9 s above the analytic optimum on the 3- and 4-charger instances (11,316 s), because it charges in whole levels, so it is a tighter reference than Dijkstra but not a continuous optimum.

### Conclusion

On every instance size where PDDL planners finish, they agree with Dijkstra to the millisecond (classical) or within the discretisation (numeric, PDDL+). Their time grows by orders of magnitude, they stop at about 30 chargers (classical) or 3 to 4 chargers (optimal PDDL+) and on real roads they cannot take the unpruned graph that the dedicated search handles in 1.4 s. By the criteria in section 8 this is a no-go: the dedicated search stays the planner, and the PDDL models are kept as a documented prototype for richer constraints.
