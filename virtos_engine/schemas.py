from __future__ import annotations

"""Lightweight schemas for the Streamlit UI and simple sizing engine.

Important: Streamlit Cloud currently runs Python 3.13.
To avoid runtime NameErrors from forward-referenced type annotations
in dataclasses, we enable postponed evaluation via `from __future__ import annotations`.
"""

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class DemandProfile:
    """Aggregate utilisation envelope (behavioural), 0..1, typically 96 rows for 24h at 15m."""

    # 96 values in [0,1]
    utilisation: List[float] = field(default_factory=list)
    timestep_minutes: int = 15

    def to_dict(self) -> Dict:
        return {
            "timestep_minutes": self.timestep_minutes,
            "utilisation": list(self.utilisation),
        }


@dataclass
class TariffSpec:
    offpeak_per_kwh: float = 0.12
    shoulder_per_kwh: float = 0.20
    peak_per_kwh: float = 0.35
    demand_charge_per_kw_month: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "offpeak_per_kwh": self.offpeak_per_kwh,
            "shoulder_per_kwh": self.shoulder_per_kwh,
            "peak_per_kwh": self.peak_per_kwh,
            "demand_charge_per_kw_month": self.demand_charge_per_kw_month,
        }


@dataclass
class DispenserTypeSpec:
    """A dispenser *type* (row) in the site table."""

    name: str = "HPC"
    qty: int = 1
    connector: str = "CCS"  # CCS | MCS
    imax_a: int = 250
    dispenser_max_kw: float = 350.0
    vehicle_voltage_v: int = 800

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "qty": self.qty,
            "connector": self.connector,
            "imax_a": self.imax_a,
            "dispenser_max_kw": self.dispenser_max_kw,
            "vehicle_voltage_v": self.vehicle_voltage_v,
        }


@dataclass
class VehicleRevenueSpec:
    """Revenue assumptions for the model."""

    hpc_per_kwh: float = 0.65
    hpc_per_min: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "hpc_per_kwh": self.hpc_per_kwh,
            "hpc_per_min": self.hpc_per_min,
        }


@dataclass
class SuperStringSpec:
    count: int = 1
    dc_dc_modules_per_string: int = 10
    module_kw: float = 100.0

    def to_dict(self) -> Dict:
        return {
            "count": self.count,
            "dc_dc_modules_per_string": self.dc_dc_modules_per_string,
            "module_kw": self.module_kw,
        }


@dataclass
class SiteSpec:
    """Top-level site spec used by the UI and engine."""

    name: str = "Site"

    # Site config (grid + dispensers + demand + revenue)
    grid_connection_kw: float = 300.0
    dispensers: List[DispenserTypeSpec] = field(default_factory=list)
    demand: DemandProfile = field(default_factory=DemandProfile)
    revenue: VehicleRevenueSpec = field(default_factory=VehicleRevenueSpec)
    tariff: TariffSpec = field(default_factory=TariffSpec)

    # Virtos implementation (DC-only v1)
    pcs_kw: float = 300.0
    battery_power_kw: float = 200.0
    battery_energy_kwh: float = 400.0
    initial_soc: float = 1.0
    allow_grid_charging: bool = False
    superstring: SuperStringSpec = field(default_factory=SuperStringSpec)

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "grid_connection_kw": self.grid_connection_kw,
            "dispensers": [d.to_dict() for d in self.dispensers],
            "demand": self.demand.to_dict(),
            "revenue": self.revenue.to_dict(),
            "tariff": self.tariff.to_dict(),
            "pcs_kw": self.pcs_kw,
            "battery_power_kw": self.battery_power_kw,
            "battery_energy_kwh": self.battery_energy_kwh,
            "initial_soc": self.initial_soc,
            "allow_grid_charging": self.allow_grid_charging,
            "superstring": self.superstring.to_dict(),
        }
