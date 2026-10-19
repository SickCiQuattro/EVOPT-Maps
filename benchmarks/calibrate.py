"""Calibrate the vehicle energy model on public reference consumption and report the errors.

Data source: EV Database (https://ev-database.org), one page per model, read on 2026-10-19.
They are estimates built from tests and the WLTP cycle, not instrumented measurements of this project:
"mild" = 23 °C with no air conditioning, "cold" = -10 °C with heating, "motorway" = a constant 110 km/h.
All figures are Wh/km in the order (city, motorway, combined).

Three parameters are fitted per vehicle:
  - the effective drag area, on the mild-weather motorway consumption (mass, Crr and efficiency stay fixed);
  - the cold penalty per km, on the cold-minus-mild difference on the motorway;
  - the urban overhead (acceleration and stops), on the mild-weather city consumption.
Held-out checks: city consumption in the cold and the cold-minus-mild difference in town.

    uv run python -m benchmarks.calibrate
"""

from evopt.vehicle import VEHICLES, G, Vehicle

CRR, ETA, BASE_KW, COLD_SPAN = 0.010, 0.90, 0.5, 28  # COLD_SPAN: degrees from 18 to -10 °C
V110 = 110 / 3.6

REFERENCE = {
    "Tesla Model 3 Standard Range Plus": {
        "url": "https://ev-database.org/car/1177/Tesla-Model-3-Standard-Range-Plus",
        "usable_kwh": 49.0, "kerb_kg": 1684, "dc_kw": 170, "taper_from": 0.8,
        "mild": (104, 163, 132), "cold": (161, 213, 185), "range_hwy_mild": 300, "range_hwy_cold": 230,
    },
    "Renault Twingo Electric": {
        "url": "https://ev-database.org/car/1270/Renault-Twingo-Electric",
        "usable_kwh": 21.3, "kerb_kg": 1186, "dc_kw": 22, "taper_from": 1.0,
        "mild": (104, 178, 137), "cold": (158, 237, 194), "range_hwy_mild": 120, "range_hwy_cold": 90,
    },
    "Fiat 500e": {
        "url": "https://ev-database.org/car/1285/Fiat-500e-Hatchback-42-kWh",
        "usable_kwh": 37.3, "kerb_kg": 1365, "dc_kw": 85, "taper_from": 0.8,
        "mild": (105, 173, 138), "cold": (162, 226, 191), "range_hwy_mild": 215, "range_hwy_cold": 165,
    },
    "MINI Electric": {
        "url": "https://ev-database.org/car/1163/Mini-Cooper-SE",
        "usable_kwh": 28.9, "kerb_kg": 1440, "dc_kw": 49, "taper_from": 0.8,
        "mild": (105, 175, 138), "cold": (161, 231, 193), "range_hwy_mild": 165, "range_hwy_cold": 125,
    },
}  # fmt: skip

# the approximate parameters used before calibration (gross capacity, mass and CdA from data sheets)
UNCALIBRATED = {
    "Tesla Model 3 Standard Range Plus": Vehicle(54, 1700, 0.51, 170, taper_from=0.8),
    "Renault Twingo Electric": Vehicle(22, 1100, 0.62, 22),
    "Fiat 500e": Vehicle(42, 1365, 0.62, 85, taper_from=0.8),
    "MINI Electric": Vehicle(32.6, 1365, 0.64, 50, taper_from=0.8),
}


def fit(name):
    ref = REFERENCE[name]
    drive = ref["mild"][1] / 1000 - BASE_KW / 110  # kWh/km of traction alone at 110 km/h
    force = drive * 3.6e6 / 1000 * ETA  # N
    cda = (force - CRR * ref["kerb_kg"] * G) / (0.5 * 1.2 * V110**2)
    cold = (ref["cold"][1] - ref["mild"][1]) / 1000 / COLD_SPAN
    smooth = Vehicle(
        ref["usable_kwh"],
        ref["kerb_kg"],
        round(cda, 3),
        ref["dc_kw"],
        crr=CRR,
        drivetrain_eff=ETA,
        heat_kw_per_c=0.0,
    )
    stop_go = (ref["mild"][0] - wh_per_km(smooth, 50, 23)) / 1000  # kWh/km missing in town at 50 km/h
    return Vehicle(
        ref["usable_kwh"], ref["kerb_kg"], round(cda, 3), ref["dc_kw"], crr=CRR, drivetrain_eff=ETA,
        taper_from=ref["taper_from"], heat_kw_per_c=0.0, cold_kwh_per_km_per_c=round(cold, 5),
        stop_go_kwh_per_km=round(stop_go, 4),
        source="EV Database, 2026-10-19",
    )  # fmt: skip


def wh_per_km(vehicle, kph, temp_c):
    """Consumption at constant speed and temperature, on flat ground."""
    return vehicle.edge_energy_kwh(1000, kph, 3600 / kph, temp_c) * 1000


def compare(name, vehicle):
    ref = REFERENCE[name]
    rows = {
        "motorway, mild (fitted)": (wh_per_km(vehicle, 110, 23), ref["mild"][1]),
        "motorway, cold (fitted)": (wh_per_km(vehicle, 110, -10), ref["cold"][1]),
        "city, mild, at 50 km/h (fitted)": (wh_per_km(vehicle, 50, 23), ref["mild"][0]),
        "city, cold, at 50 km/h (held out)": (wh_per_km(vehicle, 50, -10), ref["cold"][0]),
        "city cold-mild difference (held out)": (
            wh_per_km(vehicle, 50, -10) - wh_per_km(vehicle, 50, 23), ref["cold"][0] - ref["mild"][0]
        ),
        "motorway range, mild (km)": (vehicle.capacity_kwh / wh_per_km(vehicle, 110, 23) * 1000, ref["range_hwy_mild"]),
        "motorway range, cold (km)": (vehicle.capacity_kwh / wh_per_km(vehicle, 110, -10) * 1000, ref["range_hwy_cold"]),
    }  # fmt: skip
    return rows


def main():
    for name in REFERENCE:
        before, after = UNCALIBRATED[name], fit(name)
        print(f"\n### {name}  ({REFERENCE[name]['url']})")
        print(f"CdA {before.cda} -> {after.cda}, cold penalty {after.cold_kwh_per_km_per_c} kWh/km/°C, "
              f"capacity {before.capacity_kwh} -> {after.capacity_kwh} kWh, mass {before.mass_kg} -> {after.mass_kg} kg")  # fmt: skip
        print(f"{'point':40s} {'reference':>12s} {'before':>9s} {'error':>8s} {'after':>9s} {'error':>8s}")
        old, new = compare(name, before), compare(name, after)
        for key, (_, want) in new.items():
            b, a = old[key][0], new[key][0]
            print(
                f"{key:40s} {want:12.1f} {b:9.1f} {100 * (b / want - 1):+7.0f}% {a:9.1f} {100 * (a / want - 1):+7.0f}%"
            )
    print("\nCurrent VEHICLES (vehicle.py), for comparison:")
    for name in REFERENCE:
        v = VEHICLES[name]
        print(f"  {name}: capacity {v.capacity_kwh} kWh, CdA {v.cda}, source {v.source}")


if __name__ == "__main__":
    main()
