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

    def aux_kw(self, temp_c):
        """Servizi di bordo: base 0.5 kW più climatizzazione fuori dalla fascia 18-24 °C."""
        return 0.5 + 0.1 * max(0.0, 18 - temp_c, temp_c - 24)

    def edge_energy_kwh(self, length_m, speed_kph, time_s, temp_c=20):
        # shortcut: velocità costante per tratto, niente pendenza né recupero, upgrade con dati di quota
        v = speed_kph / 3.6
        force = self.crr * self.mass_kg * G + 0.5 * AIR_DENSITY * self.cda * v * v
        drive = force * length_m / 3.6e6 / self.drivetrain_eff
        return drive + self.aux_kw(temp_c) * time_s / 3600


# valori approssimativi da schede tecniche pubbliche
VEHICLES = {
    "Tesla Model 3 Standard Range Plus": Vehicle(54, 1700, 0.51, 170),
    "MINI Electric": Vehicle(32.6, 1365, 0.64, 50),
    "Renault Twizy": Vehicle(6.1, 474, 0.60, 3.7),
    "Renault Twingo Electric": Vehicle(22, 1100, 0.62, 22),
    "Fiat 500e": Vehicle(42, 1365, 0.62, 85),
}
