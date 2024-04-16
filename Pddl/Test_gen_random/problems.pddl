(define (problem ${instance_name})
    (:domain ${domain_name})
    (:objects
        ${vehicle_name} - vehicle_electric
        ${station_name_list} - charging_station
        ${location_name_list} - location
    )
    (:init ${vehicle_position} ${station_charging_rates} ${location_distances}
    )
    (:goal
        (and ${vehicle_at_destination} ${vehicle_full_battery}
        )
    )
)