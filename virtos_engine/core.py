from __future__ import annotations
from typing import Dict, List

from .schemas import SiteSpec, SuperStringSpec


def _site_nameplate_kw(site: SiteSpec) -> float:
    return float(sum(d.nameplate_kw for d in site.dispensers))


def _tou_price_series(site: SiteSpec) -> List[float]:
    curve_len = len(site.demand.utilisation_curve)
    t = site.tariff
    prices: List[float] = []
    for i in range(curve_len):
        if t.peak_start_idx <= i <= t.peak_end_idx:
            prices.append(t.peak_price_per_kwh)
        elif i in t.shoulder_indices:
            prices.append(t.shoulder_price_per_kwh)
        else:
            prices.append(t.offpeak_price_per_kwh)
    return prices

def _cost_from_grid_ts(grid_kw_ts: List[float], dt_hours: float, price_ts: List[float], demand_charge_per_kw_month: float) -> Dict[str, float]:
    energy_kwh = sum(g * dt_hours for g in grid_kw_ts)
    energy_cost = sum(g * dt_hours * p for g, p in zip(grid_kw_ts, price_ts))
    peak_kw = max(grid_kw_ts) if grid_kw_ts else 0.0
    demand_cost = peak_kw * demand_charge_per_kw_month
    return {
        "energy_kwh": energy_kwh,
        "energy_cost_$": energy_cost,
        "peak_kw": peak_kw,
        "demand_cost_$": demand_cost,
        "total_cost_$": energy_cost + demand_cost,
    }

def simulate_virtos(site: SiteSpec) -> Dict:
    dt = site.demand.dt_hours
    curve = site.demand.utilisation_curve
    price_ts = _tou_price_series(site)

    superstrings = [
        SuperStringSpec(
            name=f"SS{i+1}",
            pcs_sku=site.pcs_sku,
            battery_sku=site.battery_sku,
            dcdc_modules=site.dcdc_modules,
            cable_type=site.cable_type,
        )
        for i in range(site.n_superstrings)
    ]

    state: Dict[str, Dict] = {}
    for ss in superstrings:
        d = ss.derived()
        state[ss.name] = {
            "derived": d,
            "soc_kwh": d["battery_kwh"],
            "soc_ts_kwh": [],
            "battery_discharge_kw_ts": [],
            "battery_charge_kw_ts": [],
            "pcs_alloc_kw_ts": [],
            "delivered_kw_ts": [],
            "demand_kw_ts": [],
        }

    pcs_used_ts: List[float] = []
    grid_import_ts: List[float] = []
    energy_not_served_kwh = 0.0

    effective_site_pcs_cap = float(min(site.shared_pcs_kw, site.grid_connection_kw))

    for u in curve:
        pcs_requests: Dict[str, float] = {}

        # Serve each string with battery first, then request PCS
        for ss in superstrings:
            s = state[ss.name]
            d = s["derived"]

            demand_kw = u * d["cable_kw"]
            deliverable_kw = min(demand_kw, d["dcdc_kw"], d["cable_kw"])

            batt_energy_limit_kw = (s["soc_kwh"] / dt) if s["soc_kwh"] > 0 else 0.0
            batt_discharge_kw = min(deliverable_kw, d["battery_kw"], batt_energy_limit_kw)

            s["soc_kwh"] = max(s["soc_kwh"] - batt_discharge_kw * dt, 0.0)

            remaining_kw = deliverable_kw - batt_discharge_kw
            pcs_request_kw = min(remaining_kw, d["pcs_kw"])

            pcs_requests[ss.name] = pcs_request_kw

            s["demand_kw_ts"].append(demand_kw)
            s["battery_discharge_kw_ts"].append(batt_discharge_kw)
            s["battery_charge_kw_ts"].append(0.0)
            s["soc_ts_kwh"].append(s["soc_kwh"])

        total_request = sum(pcs_requests.values())
        cap = effective_site_pcs_cap

        if total_request <= cap:
            allocations = pcs_requests
            pcs_used_for_load = total_request
        else:
            allocations = {k: (pcs_requests[k] / total_request) * cap for k in pcs_requests}
            pcs_used_for_load = cap

        for ss in superstrings:
            s = state[ss.name]
            demand_kw = s["demand_kw_ts"][-1]
            pcs_kw = allocations[ss.name]
            delivered_kw = s["battery_discharge_kw_ts"][-1] + pcs_kw

            s["pcs_alloc_kw_ts"].append(pcs_kw)
            s["delivered_kw_ts"].append(delivered_kw)

            if delivered_kw < demand_kw:
                energy_not_served_kwh += (demand_kw - delivered_kw) * dt

        # Optional: grid charge into batteries with spare cap
        pcs_used_total = pcs_used_for_load
        if site.allow_grid_charge:
            spare_kw = max(cap - pcs_used_for_load, 0.0)
            spare_kw = min(spare_kw, float(site.grid_charge_power_kw))

            if spare_kw > 0:
                targets: Dict[str, float] = {}
                for ss in superstrings:
                    s = state[ss.name]
                    d = s["derived"]
                    soc_target_kwh = d["battery_kwh"] * (float(site.grid_charge_target_soc_pct) / 100.0)
                    if s["soc_kwh"] < soc_target_kwh:
                        targets[ss.name] = soc_target_kwh - s["soc_kwh"]

                total_need = sum(targets.values())
                if total_need > 0:
                    for ss in superstrings:
                        s = state[ss.name]
                        d = s["derived"]
                        if ss.name in targets:
                            share = targets[ss.name] / total_need
                            charge_kw = spare_kw * share
                            charge_kw = min(charge_kw, d["battery_kw"])
                            headroom_kw = (targets[ss.name] / dt) if dt > 0 else 0.0
                            charge_kw = min(charge_kw, headroom_kw)

                            s["soc_kwh"] = min(s["soc_kwh"] + charge_kw * dt, d["battery_kwh"])
                            s["battery_charge_kw_ts"][-1] = charge_kw
                            s["soc_ts_kwh"][-1] = s["soc_kwh"]
                            pcs_used_total += charge_kw

        pcs_used_ts.append(pcs_used_total)
        grid_import_ts.append(pcs_used_total)

    costs = _cost_from_grid_ts(grid_import_ts, dt, price_ts, site.tariff.demand_charge_per_kw_month)

    total_demand_kwh = sum(s["demand_kw_ts"][i] * dt for s in state.values() for i in range(len(curve)))
    total_delivered_kwh = sum(s["delivered_kw_ts"][i] * dt for s in state.values() for i in range(len(curve)))
    time_satisfied = sum(
        1 for s in state.values() for i in range(len(curve))
        if s["delivered_kw_ts"][i] >= s["demand_kw_ts"][i]
    )
    total_steps = len(curve) * len(state)

    metrics = {
        "time_satisfied_pct": (time_satisfied / total_steps) * 100.0 if total_steps else 0.0,
        "power_satisfied_pct": (total_delivered_kwh / total_demand_kwh) * 100.0 if total_demand_kwh > 0 else 0.0,
        "energy_not_served_kwh": energy_not_served_kwh,
    }

    return {
        "site": {
            "shared_pcs_kw": site.shared_pcs_kw,
            "grid_connection_kw": site.grid_connection_kw,
            "effective_site_pcs_cap_kw": effective_site_pcs_cap,
            "allow_grid_charge": site.allow_grid_charge,
            "grid_charge_target_soc_pct": site.grid_charge_target_soc_pct,
            "grid_charge_power_kw": site.grid_charge_power_kw,
        },
        "state": state,
        "timeseries": {
            "pcs_used_kw_ts": pcs_used_ts,
            "grid_import_kw_ts": grid_import_ts,
        },
        "metrics": metrics,
        "costs": costs,
    }

def simulate_grid_only(site: SiteSpec) -> Dict:
    dt = site.demand.dt_hours
    curve = site.demand.utilisation_curve
    price_ts = _tou_price_series(site)

    ss = SuperStringSpec(
        name="SS",
        pcs_sku=site.pcs_sku,
        battery_sku=site.battery_sku,
        dcdc_modules=site.dcdc_modules,
        cable_type=site.cable_type,
    )
    d = ss.derived()

    demand_kw_ts: List[float] = []
    grid_import_kw_ts: List[float] = []
    delivered_kw_ts: List[float] = []
    energy_not_served_kwh = 0.0

    charger_cap_kw = d["pcs_kw"] * site.n_superstrings
    cable_cap_kw = d["cable_kw"] * site.n_superstrings
    dcdc_cap_kw = d["dcdc_kw"] * site.n_superstrings
    grid_cap_kw = float(site.grid_connection_kw)

    for u in curve:
        demand_kw = u * cable_cap_kw
        deliverable_kw = min(demand_kw, cable_cap_kw, dcdc_cap_kw, charger_cap_kw)

        grid_kw = min(deliverable_kw, grid_cap_kw)
        delivered_kw = grid_kw

        if delivered_kw < demand_kw:
            energy_not_served_kwh += (demand_kw - delivered_kw) * dt

        demand_kw_ts.append(demand_kw)
        grid_import_kw_ts.append(grid_kw)
        delivered_kw_ts.append(delivered_kw)

    costs = _cost_from_grid_ts(grid_import_kw_ts, dt, price_ts, site.tariff.demand_charge_per_kw_month)

    total_demand_kwh = sum(d * dt for d in demand_kw_ts)
    total_delivered_kwh = sum(d * dt for d in delivered_kw_ts)
    time_satisfied = sum(1 for i in range(len(curve)) if delivered_kw_ts[i] >= demand_kw_ts[i])

    metrics = {
        "time_satisfied_pct": (time_satisfied / len(curve)) * 100.0 if curve else 0.0,
        "power_satisfied_pct": (total_delivered_kwh / total_demand_kwh) * 100.0 if total_demand_kwh > 0 else 0.0,
        "energy_not_served_kwh": energy_not_served_kwh,
    }

    return {
        "site": {"grid_connection_kw": grid_cap_kw},
        "timeseries": {
            "grid_import_kw_ts": grid_import_kw_ts,
            "demand_kw_ts": demand_kw_ts,
        },
        "metrics": metrics,
        "costs": costs,
    }

def simulate_ac_coupled(site: SiteSpec) -> Dict:
    dt = site.demand.dt_hours
    curve = site.demand.utilisation_curve
    price_ts = _tou_price_series(site)

    ss = SuperStringSpec(
        name="SS",
        pcs_sku=site.pcs_sku,
        battery_sku=site.battery_sku,
        dcdc_modules=site.dcdc_modules,
        cable_type=site.cable_type,
    )
    d = ss.derived()

    charger_cap_kw = d["pcs_kw"] * site.n_superstrings
    cable_cap_kw = d["cable_kw"] * site.n_superstrings
    dcdc_cap_kw = d["dcdc_kw"] * site.n_superstrings
    grid_cap_kw = float(site.grid_connection_kw)

    bess_power_kw = float(site.ac_bess_power_kw)
    bess_energy_kwh = float(site.ac_bess_energy_kwh)
    bess_soc_kwh = bess_energy_kwh

    grid_import_kw_ts: List[float] = []
    bess_discharge_kw_ts: List[float] = []
    demand_kw_ts: List[float] = []
    delivered_kw_ts: List[float] = []
    energy_not_served_kwh = 0.0

    for u in curve:
        demand_kw = u * cable_cap_kw
        deliverable_kw = min(demand_kw, cable_cap_kw, dcdc_cap_kw, charger_cap_kw)

        bess_energy_limit_kw = (bess_soc_kwh / dt) if bess_soc_kwh > 0 else 0.0
        bess_kw = min(deliverable_kw, bess_power_kw, bess_energy_limit_kw)

        bess_soc_kwh = max(bess_soc_kwh - bess_kw * dt, 0.0)

        remaining_kw = deliverable_kw - bess_kw
        grid_import_kw = min(remaining_kw, grid_cap_kw)

        delivered_kw = bess_kw + grid_import_kw

        if delivered_kw < demand_kw:
            energy_not_served_kwh += (demand_kw - delivered_kw) * dt

        demand_kw_ts.append(demand_kw)
        bess_discharge_kw_ts.append(bess_kw)
        grid_import_kw_ts.append(grid_import_kw)
        delivered_kw_ts.append(delivered_kw)

    costs = _cost_from_grid_ts(grid_import_kw_ts, dt, price_ts, site.tariff.demand_charge_per_kw_month)

    total_demand_kwh = sum(d * dt for d in demand_kw_ts)
    total_delivered_kwh = sum(d * dt for d in delivered_kw_ts)
    time_satisfied = sum(1 for i in range(len(curve)) if delivered_kw_ts[i] >= demand_kw_ts[i])

    metrics = {
        "time_satisfied_pct": (time_satisfied / len(curve)) * 100.0 if curve else 0.0,
        "power_satisfied_pct": (total_delivered_kwh / total_demand_kwh) * 100.0 if total_demand_kwh > 0 else 0.0,
        "energy_not_served_kwh": energy_not_served_kwh,
    }

    return {
        "site": {"grid_connection_kw": grid_cap_kw, "ac_bess_power_kw": bess_power_kw, "ac_bess_energy_kwh": bess_energy_kwh},
        "timeseries": {
            "grid_import_kw_ts": grid_import_kw_ts,
            "bess_discharge_kw_ts": bess_discharge_kw_ts,
            "demand_kw_ts": demand_kw_ts,
        },
        "metrics": metrics,
        "costs": costs,
    }
