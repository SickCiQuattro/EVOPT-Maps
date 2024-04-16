(define (problem problem_electric_vehicle) (:domain domain_electric_vehicle)
(:objects 
    vehicle1 - vehicle_electric
    station1 station2 station3 station4 - charging_station
    location1 location2 - location
)

(:init
    (at vehicle1 location1)
    (= (battery_level vehicle1) 50)
    (= (distance vehicle1 location1 location2) 10)
    (= (charging_rate station1) 20)
    (= (charging_rate station2) 30)
    (= (charging_rate station3) 25)
    (= (charging_rate station4) 35)
    (connected location1 location2)
    (connected location1 station1)
    (connected station1 location2)
    (= (travel_time location1 location2) 15)
    (= (travel_time location1 station1) 5)
    (= (travel_time station1 location2) 10)
)

(:goal (and
    (at vehicle1 location2)
    (full_battery vehicle1)
))
)