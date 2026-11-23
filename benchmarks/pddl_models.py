"""PDDL models of an `Instance` (see pddl_export): classical with levels, numeric, and PDDL+ with processes.

The domains are the ones explained and measured in docs/PDDL.md. Classical costs are integers (1/SCALE seconds);
numeric and PDDL+ use real seconds and kWh.
"""

from benchmarks.pddl_export import SCALE

CLASSICAL_DOMAIN = """(define (domain ev-levels)
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
"""

NUMERIC_DOMAIN = """(define (domain ev-numeric)
  (:requirements :typing :numeric-fluents :action-costs :negative-preconditions)
  (:types place)
  (:predicates (at ?p - place) (charger ?p - place) (plugged ?p - place) (used ?p - place) (road ?from ?to - place))
  (:functions
    (soc) (cap) (min-soc) (knee) (unit) (plug-time) (total-cost) (slope)
    (leg-time ?from ?to - place) (leg-kwh ?from ?to - place)
    (peak ?c - place))
  (:action drive
    :parameters (?from ?to - place)
    :precondition (and (at ?from) (road ?from ?to)
                       (>= (- (soc) (leg-kwh ?from ?to)) (min-soc)))
    :effect (and (not (at ?from)) (at ?to) (not (plugged ?from))
                 (decrease (soc) (leg-kwh ?from ?to))
                 (increase (total-cost) (leg-time ?from ?to))))
  (:action plug-in
    :parameters (?c - place)
    :precondition (and (at ?c) (charger ?c) (not (used ?c)))
    :effect (and (plugged ?c) (used ?c) (increase (total-cost) (plug-time))))
  (:action charge-flat
    :parameters (?c - place)
    :precondition (and (at ?c) (plugged ?c) (<= (+ (soc) (unit)) (* (knee) (cap))))
    :effect (and (increase (soc) (unit))
                 (increase (total-cost) (/ (* (unit) 3600) (peak ?c)))))
  (:action charge-taper                  ; cost linear in soc: a surrogate of the 1/power curve
    :parameters (?c - place)
    :precondition (and (at ?c) (plugged ?c) (> (+ (soc) (unit)) (* (knee) (cap))) (<= (+ (soc) (unit)) (cap)))
    :effect (and (increase (soc) (unit))
                 (increase (total-cost) (* (/ (* (unit) 3600) (peak ?c))
                                           (+ 1 (* (slope) (- (+ (soc) (/ (unit) 2)) (* (knee) (cap))))))))))
"""

HYBRID_DOMAIN = """(define (domain ev-hybrid)
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
"""


def classical(inst):
    """Problem of the levels domain; costs in 1/SCALE seconds."""
    places = sorted({p for leg in inst.legs for p in leg[:2]} | set(inst.peaks))
    levels = [f"l{i}" for i in range(inst.steps + 1)]
    init = [
        "(at s)",
        f"(charge l{inst.level0})",
        "(= (total-cost) 0)",
        f"(= (plug-time) {round(inst.plug_s * SCALE)})",
    ]
    init += [f"(succ l{i} l{i + 1})" for i in range(inst.steps)]
    for c, steps in inst.charge_s.items():
        init.append(f"(charger {c})")
        init += [f"(= (step-time {c} l{i}) {round(t * SCALE)})" for i, t in enumerate(steps)]
    for u, v, t, _, need in inst.legs:
        init.append(f"(= (leg-time {u} {v}) {round(t * SCALE)})")
        init += [f"(drive-ok {u} {v} l{i} l{i - need})" for i in range(inst.min_level + need, inst.steps + 1)]
    return (
        f"(define (problem trip) (:domain ev-levels)\n  (:objects {' '.join(places)} - place {' '.join(levels)} - level)\n"
        "  (:init\n    " + "\n    ".join(init) + ")\n  (:goal (at g))\n  (:metric minimize (total-cost)))\n"
    )


def _common(inst, unit_steps):
    cap = inst.capacity_kwh
    facts = [
        f"(= (cap) {cap})",
        f"(= (min-soc) {inst.min_level * cap / inst.steps})",
        f"(= (knee) {inst.knee})",
        f"(= (plug-time) {inst.plug_s})",
        f"(= (taper-to) {inst.taper_to})",
        f"(= (slope) {(1 / inst.taper_to - 1) / ((1 - inst.knee) * cap) if inst.knee < 1 else 0})",
        f"(= (unit) {cap / unit_steps})",
        f"(= (soc) {inst.level0 * cap / inst.steps})",
    ]
    for c, kw in inst.peaks.items():
        facts += [f"(charger {c})", f"(= (peak {c}) {kw})", f"(= (setup {c}) 0)"]
    for u, v, t, kwh, _ in inst.legs:
        facts += [
            f"(road {u} {v})",
            f"(= (leg-time {u} {v}) {t})",
            f"(= (leg-kwh {u} {v}) {kwh})",
            f"(= (elapsed {u} {v}) 0)",
        ]
    return facts


def _places(inst):
    return " ".join(sorted({p for leg in inst.legs for p in leg[:2]} | set(inst.peaks)))


def numeric(inst, unit_steps=10):
    """Problem of the numeric domain: charge in `unit_steps` blocks of the battery, legs with exact energy."""
    facts = [
        f
        for f in _common(inst, unit_steps)
        if "(setup " not in f and "(elapsed " not in f and "(taper-to" not in f
    ]
    return (
        f"(define (problem trip) (:domain ev-numeric)\n  (:objects {_places(inst)} - place)\n"
        "  (:init (at s) (= (total-cost) 0)\n    " + "\n    ".join(facts) + ")\n"
        "  (:goal (at g))\n  (:metric minimize (total-cost)))\n"
    )


def hybrid(inst):
    """Problem of the PDDL+ domain: charging is a continuous process, the planner chooses when to unplug."""
    facts = [f for f in _common(inst, 1) if "(unit)" not in f and "(slope)" not in f]
    return (
        f"(define (problem trip) (:domain ev-hybrid)\n  (:objects {_places(inst)} - place)\n"
        "  (:init (at s) (idle)\n    " + "\n    ".join(facts) + ")\n"
        "  (:goal (at g))\n  (:metric minimize (total-time)))\n"
    )
