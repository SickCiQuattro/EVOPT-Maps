(define (domain domain_electric_vehicle)
    (:requirements :strips :fluents :durative-actions :timed-initial-literals :typing :conditional-effects :negative-preconditions :duration-inequalities :equality)
    (:types
        vehicle_electric - vehicle
        charging_station - charging_station
        location - location
    )
    (:predicates
        (at ?v - vehicle_electric ?l - location)
        (charging ?v - vehicle_electric ?s - charging_station)
        (full_battery ?v - vehicle_electric)
        (connected ?from - location ?to - location)
    )
    (:functions
        (battery_level ?v - vehicle_electric) - number
        (distance ?from - location ?to - location) - number
        (charging_rate ?s - charging_station) - number
        (travel_time ?from - location ?to - location) - number
    )
    (:action move
        :parameters (?v - vehicle_electric ?from - location ?to - location)
        :duration (= ?duration (travel_time ?from ?to))
        :condition (and (at ?v ?from) (>= (battery_level ?v) (travel_time ?from ?to)))
        :effect (and (at ?v ?to) (not (at ?v ?from)) (decrease
                (battery_level ?v)
                (travel_time ?from ?to)))
    )
)
(:action charge
    :parameters (?v - vehicle_electric ?s - charging_station ?l - location)
    :duration (= ?duration (/ (- 100 (battery_level ?v)) (charging_rate ?s)))
    :condition (and (at ?v ?l) (charging ?v ?s) (not (full_battery ?v)))
    :effect (and (full_battery ?v) (not (charging ?v ?s)))
)