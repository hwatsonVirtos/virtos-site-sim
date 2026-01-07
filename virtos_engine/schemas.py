from dataclasses import dataclass, field
from typing import List, Dict

VEHICLE_VOLTAGE_V = 800
DC_DC_MODULE_KW = 100

PCS_LIBRARY: Dict[str, float] = {
    "PCS_500": 500.0,
    "PCS_1000": 1000.0,
}

BATTERY_LIBRARY: Dict[str, Dict[str, float]] = {
    "BATT_500_1000": {"power_kw": 500.0, "energy_kwh": 1000.0},
    "BATT_1000_2000": {"power_kw": 1000.0, "energy_kwh": 2000.0},
}

CABLE_LIBRARY: Dict[str, Dict[str, float]] = {
    "CABLE_375A": {"amps": 375.0},
    "CABLE_600A": {"amps": 600.0},
    "CABLE_1500A": {"amps": 1500.0},
}

@dataclass
class TariffSpec:
    offpeak_price_per_kwh: float = 0.12
    shoulder_price_per_kwh: float = 0.20
    peak_price_per_kwh: float = 0.35
    demand_charge_per_kw_month: float = 25.0
    peak_start_idx: int = 3
    peak_end_idx: int = 8
    shoulder_indices: List[int] = field(default_factory=lambda: [2, 9])

@dataclass
class DemandProfile:
    utilisation_curve: List[float] = field(default_factory=lambda: [0.2,0.4,0.6,0.8,1.0,0.8,0.6,0.4])
    timestep_minutes: int = 15

    @property
    def dt_hours(self) -> float:
        return self.timestep_minutes / 60.0

@dataclass
class SuperStringSpec:
    name: str
    pcs_sku: str = "PCS_500"
    battery_sku: str = "BATT_500_1000"
    dcdc_modules: int = 10
    cable_type: str = "CABLE_600A"

    def derived(self) -> Dict[str, float]:
        pcs_kw = PCS_LIBRARY[self.pcs_sku]
        batt = BATTERY_LIBRARY[self.battery_sku]
        amps = CABLE_LIBRARY[self.cable_type]["amps"]
        cable_kw = amps * VEHICLE_VOLTAGE_V / 1000.0
        return {
            "pcs_kw": float(pcs_kw),
            "battery_kw": float(batt["power_kw"]),
            "battery_kwh": float(batt["energy_kwh"]),
            "dcdc_kw": float(self.dcdc_modules * DC_DC_MODULE_KW),
            "cable_kw": float(cable_kw),
        }

@dataclass
class SiteSpec:
    name: str = "Site"
    demand: DemandProfile = field(default_factory=DemandProfile)
    n_superstrings: int = 2

    # Site import cap
    grid_connection_kw: float = 1000.0

    # Virtos: shared PCS cap across strings (hard cap) — effective cap is min(shared PCS, grid cap)
    shared_pcs_kw: float = 300.0

    # Charger-side selections
    pcs_sku: str = "PCS_500"
    battery_sku: str = "BATT_500_1000"
    dcdc_modules: int = 10
    cable_type: str = "CABLE_600A"

    # Virtos v1.1: optional grid charging using spare import/PCS headroom
    allow_grid_charge: bool = False
    grid_charge_target_soc_pct: float = 100.0
    grid_charge_power_kw: float = 200.0

    # AC-coupled competitor: grid-side BESS behind meter
    ac_bess_power_kw: float = 0.0
    ac_bess_energy_kwh: float = 0.0

    tariff: TariffSpec = field(default_factory=TariffSpec)
