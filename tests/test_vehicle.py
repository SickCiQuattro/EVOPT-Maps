import pytest

from evopt.vehicle import VEHICLES, Vehicle


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


def test_dc_charging_power_tapers_above_the_knee_and_ac_does_not():
    from evopt.vehicle import Vehicle

    car = Vehicle(capacity_kwh=50, mass_kg=1500, cda=0.6, max_charge_kw=100, taper_from=0.8, taper_to=0.3)
    assert car.charge_power_kw(0.5, 100) == 100 and car.charge_power_kw(0.8, 100) == 100
    assert car.charge_power_kw(0.9, 100) == pytest.approx(65) and car.charge_power_kw(
        1.0, 100
    ) == pytest.approx(30)
    assert car.charge_power_kw(0.95, 100) < car.charge_power_kw(0.85, 100)
    assert car.charge_power_kw(0.95, 22) == 22  # in alternata la potenza resta costante
    assert car.charge_power_kw(0.5, 50) == 50  # limitata dalla colonnina


def test_no_taper_by_default():
    from evopt.vehicle import Vehicle

    assert Vehicle(50, 1500, 0.6, 100).charge_power_kw(0.99, 100) == 100


def test_climbing_costs_potential_energy_over_drivetrain_efficiency():
    car = Vehicle(capacity_kwh=50, mass_kg=1500, cda=0.6, max_charge_kw=100)
    flat = car.edge_energy_kwh(5000, 90, 200)
    up = car.edge_energy_kwh(5000, 90, 200, rise_m=100)
    assert up - flat == pytest.approx(1500 * 9.81 * 100 / 3.6e6 / 0.85, rel=1e-6)  # circa 0,48 kWh


def test_descending_recovers_part_of_the_energy_but_never_goes_negative():
    car = Vehicle(capacity_kwh=50, mass_kg=1500, cda=0.6, max_charge_kw=100)
    flat = car.edge_energy_kwh(5000, 90, 200)
    down = car.edge_energy_kwh(5000, 90, 200, rise_m=-20)
    assert 0 < down < flat
    # shortcut: in discesa la trazione non ricarica la batteria; restano solo i servizi di bordo
    assert car.edge_energy_kwh(5000, 90, 200, rise_m=-500) == pytest.approx(car.aux_kw(20) * 200 / 3600)
    assert flat - down == pytest.approx(1500 * 9.81 * 20 / 3.6e6 * car.regen_eff, rel=1e-6)


def test_a_round_trip_over_a_hill_costs_more_than_the_flat_equivalent():
    car = Vehicle(capacity_kwh=50, mass_kg=1500, cda=0.6, max_charge_kw=100)
    flat = car.edge_energy_kwh(5000, 90, 200)
    assert (
        car.edge_energy_kwh(5000, 90, 200, rise_m=60) + car.edge_energy_kwh(5000, 90, 200, rise_m=-60)
        > 2 * flat
    )
