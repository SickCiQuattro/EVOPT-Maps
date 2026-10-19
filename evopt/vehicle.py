from dataclasses import dataclass

G = 9.81  # m/s²
AIR_DENSITY = 1.2  # kg/m³
STOP_GO_LIMIT_KPH = 70  # dalla velocità limite in su un tratto non ha stop-and-go


@dataclass(frozen=True)
class Vehicle:
    capacity_kwh: float
    mass_kg: float
    cda: float  # coefficiente di resistenza aerodinamica × area frontale, m²
    max_charge_kw: float
    crr: float = 0.010  # resistenza al rotolamento
    drivetrain_eff: float = 0.85
    taper_from: float = 1.0  # carica oltre cui la ricarica rapida rallenta (1.0 = mai)
    taper_to: float = 0.3  # frazione della potenza che resta al 100%
    regen_eff: float = 0.6  # quota dell'energia potenziale in discesa che si recupera in frenata
    aux_base_kw: float = 0.5  # servizi di bordo a temperatura mite
    heat_kw_per_c: float = 0.1  # potenza di riscaldamento per grado sotto 18 °C (per ora, non per km)
    cool_kw_per_c: float = 0.1  # potenza di raffrescamento per grado sopra 24 °C
    cold_kwh_per_km_per_c: float = (
        0.0  # penalità al freddo per km e per grado sotto 18 °C (dati: vedi benchmarks.calibrate)
    )
    stop_go_kwh_per_km: float = (
        0.0  # sovraccosto urbano a 50 km/h per accelerazioni e fermate; zero da 70 km/h in su
    )
    source: str | None = None  # da dove vengono i parametri; None = valori approssimativi non calibrati

    def aux_kw(self, temp_c):
        """Servizi di bordo: base più climatizzazione fuori dalla fascia 18-24 °C."""
        return (
            self.aux_base_kw
            + self.heat_kw_per_c * max(0.0, 18 - temp_c)
            + self.cool_kw_per_c * max(0.0, temp_c - 24)
        )

    def charge_power_kw(self, soc, station_kw):
        """Potenza di ricarica alla carica `soc` (0-1). In alternata (fino a 22 kW) è costante; in continua cala oltre il ginocchio."""
        peak = min(self.max_charge_kw, station_kw)
        if peak <= 22 or soc <= self.taper_from:
            return peak
        frac = min(1.0, (soc - self.taper_from) / (1.0 - self.taper_from))
        return peak * (1.0 - (1.0 - self.taper_to) * frac)

    def edge_energy_kwh(self, length_m, speed_kph, time_s, temp_c=20, rise_m=0.0):
        """Energia di un tratto. `rise_m` è il dislivello (positivo in salita).

        shortcut: velocità costante per tratto; in discesa il recupero riduce il consumo ma l'energia del tratto
        non scende sotto zero (la batteria non si ricarica scendendo). Così i pesi restano non negativi e
        Dijkstra, i limiti di batteria e le euristiche restano validi; upgrade: consumo con segno e saturazione.
        """
        v = speed_kph / 3.6
        force = self.crr * self.mass_kg * G + 0.5 * AIR_DENSITY * self.cda * v * v
        drive = force * length_m / 3.6e6 / self.drivetrain_eff
        gravity = self.mass_kg * G * rise_m / 3.6e6  # kWh di energia potenziale guadagnata o ceduta
        climb = gravity / self.drivetrain_eff if rise_m > 0 else gravity * self.regen_eff
        urban = (
            self.stop_go_kwh_per_km
            * length_m
            / 1000
            * max(0.0, (STOP_GO_LIMIT_KPH - speed_kph) / (STOP_GO_LIMIT_KPH - 50))
        )
        cold = self.cold_kwh_per_km_per_c * length_m / 1000 * max(0.0, 18 - temp_c)
        return max(0.0, drive + climb) + urban + cold + self.aux_kw(temp_c) * time_s / 3600


# Quattro veicoli sono calibrati su consumi di riferimento pubblici (EV Database): `python -m benchmarks.calibrate`
# mostra i dati, il metodo e gli errori. La Twizy non ha dati confrontabili e resta con valori approssimativi.
SOURCE = "EV Database, 2026-10-19"
VEHICLES = {
    "Tesla Model 3 Standard Range Plus": Vehicle(
        capacity_kwh=49.0, mass_kg=1684, cda=0.622, max_charge_kw=170,
        drivetrain_eff=0.9, taper_from=0.8, heat_kw_per_c=0.0,
        cold_kwh_per_km_per_c=0.00179, stop_go_kwh_per_km=0.0208, source=SOURCE,
    ),
    "MINI Electric": Vehicle(
        capacity_kwh=28.9, mass_kg=1440, cda=0.734, max_charge_kw=49,
        drivetrain_eff=0.9, taper_from=0.8, heat_kw_per_c=0.0,
        cold_kwh_per_km_per_c=0.002, stop_go_kwh_per_km=0.0252, source=SOURCE,
    ),
    "Renault Twizy": Vehicle(6.1, 474, 0.60, 3.7),  # non calibrata: valori approssimativi
    "Renault Twingo Electric": Vehicle(
        capacity_kwh=21.3, mass_kg=1186, cda=0.796, max_charge_kw=22,
        drivetrain_eff=0.9, heat_kw_per_c=0.0,
        cold_kwh_per_km_per_c=0.00211, stop_go_kwh_per_km=0.0297, source=SOURCE,
    ),
    "Fiat 500e": Vehicle(
        capacity_kwh=37.3, mass_kg=1365, cda=0.735, max_charge_kw=85,
        drivetrain_eff=0.9, taper_from=0.8, heat_kw_per_c=0.0,
        cold_kwh_per_km_per_c=0.00189, stop_go_kwh_per_km=0.0274, source=SOURCE,
    ),
}  # fmt: skip
