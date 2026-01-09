"""Virtos site simulator engine (v1).

Hard constraints enforced (per canonical handover + v1.4 delta):
- Fixed timestep (default 0.25 h)
- All flows obey hard caps (grid, PCS, DC-DC, cable cap at 800 V by default, dispenser cap)
- AC-coupled BESS cannot bypass charger PCS
- Virtos DC-coupled battery may bypass PCS to supply Charge Array

Model note (v1):
- Demand is an aggregate site-level utilisation envelope (0–1) applied to nameplate charging power.
- No session simulation, no look-ahead allocation, deterministic proportional allocation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class Caps:
    grid_kw: float
    pcs_kw: float
    array_kw: float
    per_string_kw: float
    batt_discharge_kw: float
    batt_energy_kwh: float
    inverter_kw: float


def _as_float(x, default=0.0) -> float:
    try:
        if x is None:
            return float(default)
        return float(x)
    except Exception:
        return float(default)


def _as_int(x, default=0) -> int:
    try:
        if x is None:
            return int(default)
        return int(x)
    except Exception:
        return int(default)


def _validate_util_curve(util_df, expected_n: int) -> np.ndarray:
    if util_df is None:
        return np.zeros(expected_n, dtype=float)
    if isinstance(util_df, pd.DataFrame):
        if "utilisation" not in util_df.columns:
            return np.zeros(expected_n, dtype=float)
        util = util_df["utilisation"].to_numpy(dtype=float)
    else:
        util = np.asarray(util_df, dtype=float)

    if util.size == 0:
        return np.zeros(expected_n, dtype=float)
    if util.size != expected_n:
        # No implicit resampling permitted. Clip/pad explicitly (deterministic).
        util2 = np.zeros(expected_n, dtype=float)
        m = min(expected_n, util.size)
        util2[:m] = util[:m]
        util = util2
    util = np.clip(util, 0.0, 1.0)
    return util


def _nameplate_kw(cfg: dict) -> float:
    qty_ac = _as_int(cfg.get("qty_ac"), 0)
    ac_kw = _as_float(cfg.get("ac_kw"), 0.0)
    qty_dc = _as_int(cfg.get("qty_dc"), 0)
    dc_kw = _as_float(cfg.get("dc_kw"), 0.0)
    return max(0.0, qty_ac * ac_kw + qty_dc * dc_kw)


def _compute_caps(cfg: dict) -> Caps:
    arch = str(cfg.get("architecture", "Virtos (DC-coupled)"))
    grid_kw = max(0.0, _as_float(cfg.get("grid_connection_kw"), 0.0))
    pcs_kw = max(0.0, _as_float(cfg.get("pcs_cap_kw"), 0.0))

    # Charge array caps
    strings = max(1, _as_int(cfg.get("super_strings"), 1))
    modules_per = max(0, _as_int(cfg.get("dc_dc_modules_per_string"), 0))
    dcdc_kw = modules_per * 100.0

    v = max(0.0, _as_float(cfg.get("vehicle_voltage_v"), 800.0))
    imax = max(0.0, _as_float(cfg.get("cable_imax_a"), 0.0))
    cable_kw = (v * imax) / 1000.0
    disp_kw = max(0.0, _as_float(cfg.get("dispenser_max_kw"), 0.0))
    per_string_kw = max(0.0, min(dcdc_kw, cable_kw if cable_kw > 0 else dcdc_kw, disp_kw if disp_kw > 0 else dcdc_kw))
    array_kw = per_string_kw * strings

    batt_p = max(0.0, _as_float(cfg.get("battery_power_kw"), 0.0))
    batt_e = max(0.0, _as_float(cfg.get("battery_energy_kwh"), 0.0))
    inverter = max(0.0, _as_float(cfg.get("ac_inverter_kw"), 0.0))

    # Enforce v1.4 bounds relationship where relevant
    if "Virtos" in arch:
        batt_p = min(batt_p, pcs_kw) if pcs_kw > 0 else 0.0
    if "AC-coupled" in arch:
        batt_p = min(batt_p, inverter) if inverter > 0 else 0.0

    return Caps(
        grid_kw=grid_kw,
        pcs_kw=pcs_kw,
        array_kw=array_kw,
        per_string_kw=per_string_kw,
        batt_discharge_kw=batt_p,
        batt_energy_kwh=batt_e,
        inverter_kw=inverter,
    )


def _tou_rate(hour: float, offpeak: float, shoulder: float, peak: float) -> float:
    """Simple fixed TOU bands (placeholder).

    Off-peak: 00:00–07:00
    Shoulder: 07:00–16:00 and 21:00–24:00
    Peak: 16:00–21:00
    """
    if hour < 7.0:
        return offpeak
    if 16.0 <= hour < 21.0:
        return peak
    return shoulder


def run_engine(cfg: dict) -> dict:
    timestep_h = _as_float(cfg.get("timestep_h"), 0.25)
    if timestep_h <= 0:
        timestep_h = 0.25

    n = 96  # 24h @ 15 min (canonical v1)
    util = _validate_util_curve(cfg.get("util_curve"), expected_n=n)

    caps = _compute_caps(cfg)
    arch = str(cfg.get("architecture", "Virtos (DC-coupled)"))

    # Demand model
    nameplate = _nameplate_kw(cfg)
    demand_kw = util * nameplate

    # Hard cap: charge array max throughput (DC-DC/cables/dispensers)
    demand_after_array_cap = np.minimum(demand_kw, caps.array_kw)
    unserved_array_kw = np.maximum(demand_kw - demand_after_array_cap, 0.0)

    # Deterministic proportional allocation (v1.4 policy):
    # We use equal per-string demand because utilisation is site-aggregate.
    strings = max(1, _as_int(cfg.get("super_strings"), 1))
    per_string_demand = demand_after_array_cap / strings
    per_string_served_cap = np.minimum(per_string_demand, caps.per_string_kw)
    demand_effective = per_string_served_cap * strings

    # Battery state
    soc0 = np.clip(_as_float(cfg.get("battery_initial_soc_frac"), 1.0), 0.0, 1.0)
    soc_kwh = caps.batt_energy_kwh * soc0

    served_kw = np.zeros(n, dtype=float)
    grid_import_kw = np.zeros(n, dtype=float)
    pcs_to_array_kw = np.zeros(n, dtype=float)
    batt_to_array_kw = np.zeros(n, dtype=float)
    soc_kwh_series = np.zeros(n, dtype=float)
    binding: List[str] = []

    for t in range(n):
        d = float(demand_effective[t])

        # Shared power ceiling through charger-side infrastructure
        charger_side_cap = min(caps.pcs_kw if caps.pcs_kw > 0 else d, caps.array_kw if caps.array_kw > 0 else d)
        if "Grid-only" in arch:
            # Grid -> PCS -> Charge Array
            p = min(d, caps.grid_kw if caps.grid_kw > 0 else d, charger_side_cap)
            pcs_to_array_kw[t] = p
            served_kw[t] = p
            grid_import_kw[t] = p

        elif "AC-coupled" in arch:
            # Grid + BESS (through inverter) -> PCS -> Charge Array
            # BESS cannot bypass PCS. Total through PCS is capped.
            through_pcs_cap = charger_side_cap

            g = min(d, caps.grid_kw if caps.grid_kw > 0 else d, through_pcs_cap)
            remaining = max(d - g, 0.0)

            # BESS discharge limited by inverter, battery power, SOC, and remaining PCS headroom.
            headroom = max(through_pcs_cap - g, 0.0)
            bess_max_energy_kw = soc_kwh / timestep_h if timestep_h > 0 else 0.0
            b = min(remaining, headroom, caps.inverter_kw, caps.batt_discharge_kw, bess_max_energy_kw)

            pcs_to_array_kw[t] = g + b
            batt_to_array_kw[t] = b
            served_kw[t] = g + b
            grid_import_kw[t] = g
            soc_kwh -= b * timestep_h

        else:
            # Virtos (DC-coupled): Grid->PCS->Array plus Battery->Array bypass.
            through_pcs_cap = min(caps.grid_kw if caps.grid_kw > 0 else d, caps.pcs_kw if caps.pcs_kw > 0 else d, caps.array_kw if caps.array_kw > 0 else d)
            p = min(d, through_pcs_cap)
            remaining = max(d - p, 0.0)

            batt_max_energy_kw = soc_kwh / timestep_h if timestep_h > 0 else 0.0
            b = min(remaining, caps.batt_discharge_kw, batt_max_energy_kw)

            pcs_to_array_kw[t] = p
            batt_to_array_kw[t] = b
            served_kw[t] = p + b
            grid_import_kw[t] = p
            soc_kwh -= b * timestep_h

        soc_kwh = float(np.clip(soc_kwh, 0.0, caps.batt_energy_kwh))
        soc_kwh_series[t] = soc_kwh

    unserved_kw = np.maximum(demand_effective - served_kw, 0.0) + unserved_array_kw

    # Binding constraints (coarse): detect if any cap frequently active
    if np.any(demand_kw > caps.array_kw + 1e-9):
        binding.append("Charge Array cap (DC-DC/cable/dispenser)")
    if caps.grid_kw > 0 and np.any(grid_import_kw >= caps.grid_kw - 1e-6):
        binding.append("Grid connection cap")
    if caps.pcs_kw > 0 and np.any(pcs_to_array_kw >= caps.pcs_kw - 1e-6):
        binding.append("PCS cap")
    if caps.batt_discharge_kw > 0 and np.any(batt_to_array_kw >= caps.batt_discharge_kw - 1e-6):
        binding.append("Battery power cap")
    if caps.batt_energy_kwh > 0 and np.any(soc_kwh_series <= 1e-6) and np.any(batt_to_array_kw > 0):
        binding.append("Battery energy (SOC) cap")
    if "AC-coupled" in arch and caps.inverter_kw > 0 and np.any(batt_to_array_kw >= caps.inverter_kw - 1e-6):
        binding.append("AC inverter cap")

    # Costs (OpEx only; placeholders)
    off = _as_float(cfg.get("tou_offpeak_per_kwh"), 0.0)
    sh = _as_float(cfg.get("tou_shoulder_per_kwh"), 0.0)
    pk = _as_float(cfg.get("tou_peak_per_kwh"), 0.0)
    demand_charge = _as_float(cfg.get("demand_charge_per_kw_month"), 0.0)

    hours = np.arange(n) * timestep_h
    rates = np.array([_tou_rate(float(h), off, sh, pk) for h in hours], dtype=float)
    energy_cost = float(np.sum(grid_import_kw * timestep_h * rates))
    demand_cost = float(np.max(grid_import_kw) * demand_charge)

    energy_kwh = float(np.sum(served_kw) * timestep_h)
    peak_kw = float(np.max(served_kw) if served_kw.size else 0.0)
    sat = float(np.sum(served_kw) / np.sum(demand_kw)) if float(np.sum(demand_kw)) > 0 else 0.0

    ts = pd.DataFrame(
        {
            "t": np.arange(n),
            "hour": hours,
            "utilisation": util,
            "nameplate_kw": nameplate,
            "demand_kw": demand_kw,
            "demand_effective_kw": demand_effective,
            "served_kw": served_kw,
            "grid_import_kw": grid_import_kw,
            "pcs_to_array_kw": pcs_to_array_kw,
            "battery_to_array_kw": batt_to_array_kw,
            "battery_soc_kwh": soc_kwh_series,
            "unserved_kw": unserved_kw,
            "unserved_array_kw": unserved_array_kw,
        }
    )

    return {
        "constraints": {
            "timestep_h": timestep_h,
            "grid_connection_kw": caps.grid_kw,
            "pcs_cap_kw": caps.pcs_kw,
            "array_cap_kw": caps.array_kw,
            "per_string_cap_kw": caps.per_string_kw,
            "battery_power_kw": caps.batt_discharge_kw,
            "battery_energy_kwh": caps.batt_energy_kwh,
            "ac_inverter_kw": caps.inverter_kw,
        },
        "binding_constraints": binding,
        "summary": {
            "architecture": arch,
            "energy_kwh": energy_kwh,
            "peak_kw": peak_kw,
            "energy_cost_$": energy_cost,
            "demand_charge_cost_$": demand_cost,
            "power_satisfied_pct": float(100.0 * sat),
        },
        "timeseries": ts,
    }
