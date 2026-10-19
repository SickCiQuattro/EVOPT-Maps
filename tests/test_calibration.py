import pytest

from benchmarks.calibrate import REFERENCE, compare
from evopt.vehicle import VEHICLES


@pytest.mark.parametrize("name", REFERENCE)
def test_calibrated_vehicles_reproduce_the_reference_consumption(name):
    rows = compare(name, VEHICLES[name])
    for point in ("autostrada mite (adattato)", "autostrada freddo (adattato)"):
        got, want = rows[point]
        assert got == pytest.approx(want, rel=0.01), point
    for point in ("autonomia autostrada mite (km)", "autonomia autostrada freddo (km)"):
        got, want = rows[point]
        assert got == pytest.approx(want, rel=0.02), point


@pytest.mark.parametrize("name", REFERENCE)
def test_calibration_holds_on_points_it_was_not_fitted_on(name):
    """Il consumo urbano al freddo non entra nell'adattamento: lo prevede il modello."""
    got, want = compare(name, VEHICLES[name])["città freddo, a 50 km/h (verifica)"]
    assert got == pytest.approx(want, rel=0.06)


def test_the_uncalibrated_vehicle_is_marked_as_such():
    assert VEHICLES["Renault Twizy"].source is None
    assert all(VEHICLES[n].source for n in REFERENCE)
