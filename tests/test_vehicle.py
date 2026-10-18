from evopt.vehicle import VEHICLES


def test_consumption_is_plausible_at_90_kph():
    car = VEHICLES["Tesla Model 3 Standard Range Plus"]
    kwh_per_km = car.edge_energy_kwh(1000, 90, 40)  # 1 km a 90 km/h = 40 s
    assert 0.09 < kwh_per_km < 0.18


def test_cold_and_heat_cost_more_than_mild_weather():
    car = VEHICLES["Fiat 500e"]
    mild, cold, hot = (car.edge_energy_kwh(1000, 50, 72, t) for t in (20, -5, 38))
    assert cold > mild and hot > mild


def test_faster_costs_more_per_km():
    car = VEHICLES["MINI Electric"]
    assert car.edge_energy_kwh(1000, 130, 28) > car.edge_energy_kwh(1000, 50, 72)
