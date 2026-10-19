from dataclasses import dataclass

G = 9.81  # m/s²
AIR_DENSITY = 1.2  # kg/m³


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

    def aux_kw(self, temp_c):
        """Servizi di bordo: base 0.5 kW più climatizzazione fuori dalla fascia 18-24 °C."""
        return 0.5 + 0.1 * max(0.0, 18 - temp_c, temp_c - 24)

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
        return max(0.0, drive + climb) + self.aux_kw(temp_c) * time_s / 3600


# valori approssimativi da schede tecniche pubbliche
VEHICLES = {
    "Tesla Model 3 Standard Range Plus": Vehicle(54, 1700, 0.51, 170, taper_from=0.8),
    "MINI Electric": Vehicle(32.6, 1365, 0.64, 50, taper_from=0.8),
    "Renault Twizy": Vehicle(6.1, 474, 0.60, 3.7),
    "Renault Twingo Electric": Vehicle(22, 1100, 0.62, 22),
    "Fiat 500e": Vehicle(42, 1365, 0.62, 85, taper_from=0.8),
}
