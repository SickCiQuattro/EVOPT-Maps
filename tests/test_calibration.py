import pytest

from benchmarks.calibrate import REFERENCE, compare
from evopt.vehicle import VEHICLES


@pytest.mark.parametrize("name", REFERENCE)
def test_calibrated_vehicles_reproduce_the_reference_consumption(name):
    rows = compare(name, VEHICLES[name])
    for point in ("motorway, mild (fitted)", "motorway, cold (fitted)"):
        got, want = rows[point]
        assert got == pytest.approx(want, rel=0.01), point
    for point in ("motorway range, mild (km)", "motorway range, cold (km)"):
        got, want = rows[point]
        assert got == pytest.approx(want, rel=0.02), point


@pytest.mark.parametrize("name", REFERENCE)
def test_calibration_holds_on_points_it_was_not_fitted_on(name):
    """Urban consumption in the cold is not part of the fit: the model predicts it."""
    got, want = compare(name, VEHICLES[name])["city, cold, at 50 km/h (held out)"]
    assert got == pytest.approx(want, rel=0.06)


def test_the_uncalibrated_vehicle_is_marked_as_such():
    assert VEHICLES["Renault Twizy"].source is None
    assert all(VEHICLES[n].source for n in REFERENCE)
