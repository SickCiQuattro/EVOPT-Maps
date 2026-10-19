"""Calibra il modello energetico dei veicoli su consumi di riferimento pubblici e riporta gli errori.

Fonte dei dati: EV Database (https://ev-database.org), pagine dei singoli modelli, consultate il 19/10/2026.
Sono stime costruite a partire da prove e dal ciclo WLTP, non misure strumentate di questo progetto:
"mite" = 23 °C senza aria condizionata, "freddo" = -10 °C con riscaldamento, "autostrada" = 110 km/h costanti.
Tutti i numeri sono Wh/km nell'ordine (città, autostrada, misto).

Per ogni veicolo si adattano tre parametri:
  - il CdA effettivo, sul consumo in autostrada con tempo mite (massa, Crr e rendimento restano fissi);
  - la penalità del freddo per km, sulla differenza freddo/mite in autostrada;
  - il sovraccosto urbano (accelerazioni e fermate), sul consumo in città con tempo mite.
Verifiche su punti non usati: consumo in città al freddo e differenza freddo/mite in città.

    uv run python -m benchmarks.calibrate
"""

from evopt.vehicle import VEHICLES, G, Vehicle

CRR, ETA, BASE_KW, COLD_SPAN = 0.010, 0.90, 0.5, 28  # COLD_SPAN: gradi da 18 a -10 °C
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

# i parametri approssimativi usati prima della calibrazione (capacità lorda, massa e CdA da schede tecniche)
UNCALIBRATED = {
    "Tesla Model 3 Standard Range Plus": Vehicle(54, 1700, 0.51, 170, taper_from=0.8),
    "Renault Twingo Electric": Vehicle(22, 1100, 0.62, 22),
    "Fiat 500e": Vehicle(42, 1365, 0.62, 85, taper_from=0.8),
    "MINI Electric": Vehicle(32.6, 1365, 0.64, 50, taper_from=0.8),
}


def fit(name):
    ref = REFERENCE[name]
    drive = ref["mild"][1] / 1000 - BASE_KW / 110  # kWh/km di sola trazione a 110 km/h
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
    stop_go = (ref["mild"][0] - wh_per_km(smooth, 50, 23)) / 1000  # kWh/km mancanti in città a 50 km/h
    return Vehicle(
        ref["usable_kwh"], ref["kerb_kg"], round(cda, 3), ref["dc_kw"], crr=CRR, drivetrain_eff=ETA,
        taper_from=ref["taper_from"], heat_kw_per_c=0.0, cold_kwh_per_km_per_c=round(cold, 5),
        stop_go_kwh_per_km=round(stop_go, 4),
        source="EV Database, 2026-10-19",
    )  # fmt: skip


def wh_per_km(vehicle, kph, temp_c):
    """Consumo a velocità e temperatura costanti, su terreno piano."""
    return vehicle.edge_energy_kwh(1000, kph, 3600 / kph, temp_c) * 1000


def compare(name, vehicle):
    ref = REFERENCE[name]
    rows = {
        "autostrada mite (adattato)": (wh_per_km(vehicle, 110, 23), ref["mild"][1]),
        "autostrada freddo (adattato)": (wh_per_km(vehicle, 110, -10), ref["cold"][1]),
        "città mite, a 50 km/h (adattato)": (wh_per_km(vehicle, 50, 23), ref["mild"][0]),
        "città freddo, a 50 km/h (verifica)": (wh_per_km(vehicle, 50, -10), ref["cold"][0]),
        "diff. freddo-mite in città (verifica)": (
            wh_per_km(vehicle, 50, -10) - wh_per_km(vehicle, 50, 23), ref["cold"][0] - ref["mild"][0]
        ),
        "autonomia autostrada mite (km)": (vehicle.capacity_kwh / wh_per_km(vehicle, 110, 23) * 1000, ref["range_hwy_mild"]),
        "autonomia autostrada freddo (km)": (vehicle.capacity_kwh / wh_per_km(vehicle, 110, -10) * 1000, ref["range_hwy_cold"]),
    }  # fmt: skip
    return rows


def main():
    for name in REFERENCE:
        before, after = UNCALIBRATED[name], fit(name)
        print(f"\n### {name}  ({REFERENCE[name]['url']})")
        print(f"CdA {before.cda} -> {after.cda}, penalità freddo {after.cold_kwh_per_km_per_c} kWh/km/°C, "
              f"capacità {before.capacity_kwh} -> {after.capacity_kwh} kWh, massa {before.mass_kg} -> {after.mass_kg} kg")  # fmt: skip
        print(f"{'punto':40s} {'riferimento':>12s} {'prima':>9s} {'errore':>8s} {'dopo':>9s} {'errore':>8s}")
        old, new = compare(name, before), compare(name, after)
        for key, (_, want) in new.items():
            b, a = old[key][0], new[key][0]
            print(
                f"{key:40s} {want:12.1f} {b:9.1f} {100 * (b / want - 1):+7.0f}% {a:9.1f} {100 * (a / want - 1):+7.0f}%"
            )
    print("\nVEHICLES attuali (vehicle.py) per confronto:")
    for name in REFERENCE:
        v = VEHICLES[name]
        print(f"  {name}: capacità {v.capacity_kwh} kWh, CdA {v.cda}, fonte {v.source}")


if __name__ == "__main__":
    main()
