from dataclasses import dataclass

G = 9.81  # m/s²
AIR_DENSITY = 1.2  # kg/m³
STOP_GO_LIMIT_KPH = 70  # from this speed up, a stretch has no stop-and-go


@dataclass(frozen=True)
class Vehicle:
    capacity_kwh: float
    mass_kg: float
    cda: float  # drag coefficient × frontal area, m²
    max_charge_kw: float
    crr: float = 0.010  # rolling resistance coefficient
    drivetrain_eff: float = 0.85
    taper_from: float = 1.0  # charge above which fast charging slows down (1.0 = never)
    taper_to: float = 0.3  # fraction of the power left at 100%
    regen_eff: float = 0.6  # share of the potential energy of a descent recovered by regenerative braking
    aux_base_kw: float = 0.5  # auxiliary load in mild weather
    heat_kw_per_c: float = 0.1  # heating power per degree below 18 °C (per hour, not per km)
    cool_kw_per_c: float = 0.1  # cooling power per degree above 24 °C
    cold_kwh_per_km_per_c: float = (
        0.0  # cold penalty per km and per degree below 18 °C (see benchmarks.calibrate)
    )
    stop_go_kwh_per_km: float = (
        0.0  # urban overhead at 50 km/h for acceleration and stops; zero from 70 km/h up
    )
    source: str | None = None  # where the parameters come from; None = approximate, uncalibrated values

    def aux_kw(self, temp_c):
        """Auxiliary load: a base plus climate control outside the 18-24 °C band."""
        return (
            self.aux_base_kw
            + self.heat_kw_per_c * max(0.0, 18 - temp_c)
            + self.cool_kw_per_c * max(0.0, temp_c - 24)
        )

    def charge_power_kw(self, soc, station_kw):
        """Charging power at charge `soc` (0-1). Constant on AC (up to 22 kW); on DC it falls above the knee."""
        peak = min(self.max_charge_kw, station_kw)
        if peak <= 22 or soc <= self.taper_from:
            return peak
        frac = min(1.0, (soc - self.taper_from) / (1.0 - self.taper_from))
        return peak * (1.0 - (1.0 - self.taper_to) * frac)

    def edge_energy_kwh(self, length_m, speed_kph, time_s, temp_c=20, rise_m=0.0):
        """Energy of a stretch. `rise_m` is the elevation change (positive uphill).

        shortcut: constant speed per stretch; on a descent regeneration lowers consumption but the stretch's
        energy never goes below zero (descending does not charge the battery). This keeps weights non-negative
        so Dijkstra, battery limits and heuristics stay valid; upgrade: signed consumption with saturation.
        """
        v = speed_kph / 3.6
        force = self.crr * self.mass_kg * G + 0.5 * AIR_DENSITY * self.cda * v * v
        drive = force * length_m / 3.6e6 / self.drivetrain_eff
        gravity = self.mass_kg * G * rise_m / 3.6e6  # kWh of potential energy gained or given up
        climb = gravity / self.drivetrain_eff if rise_m > 0 else gravity * self.regen_eff
        urban = (
            self.stop_go_kwh_per_km
            * length_m
            / 1000
            * max(0.0, (STOP_GO_LIMIT_KPH - speed_kph) / (STOP_GO_LIMIT_KPH - 50))
        )
        cold = self.cold_kwh_per_km_per_c * length_m / 1000 * max(0.0, 18 - temp_c)
        return max(0.0, drive + climb) + urban + cold + self.aux_kw(temp_c) * time_s / 3600


# Four vehicles are calibrated on public reference consumption (EV Database): `python -m benchmarks.calibrate`
# shows the data, the method and the errors. The Twizy has no comparable data and keeps approximate values.
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
    "Renault Twizy": Vehicle(6.1, 474, 0.60, 3.7),  # uncalibrated: approximate values
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
