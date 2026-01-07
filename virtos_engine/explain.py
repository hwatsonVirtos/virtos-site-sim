from typing import Dict, List

def topology_text(arch: str) -> str:
    if arch == "virtos":
        return (
            "Grid\n"
            "  |\n"
            "Shared PCS\n"
            "  |\n"
            "Charge Array ---- Battery (DC-coupled)\n"
            "  |\n"
            "Dispensers\n"
            "  |\n"
            "Vehicles"
        )
    if arch == "grid":
        return (
            "Grid\n"
            "  |\n"
            "Charger PCS\n"
            "  |\n"
            "Dispensers\n"
            "  |\n"
            "Vehicles"
        )
    if arch == "ac":
        return (
            "Grid ---- AC BESS (behind meter)\n"
            "  |\n"
            "Charger PCS\n"
            "  |\n"
            "Dispensers\n"
            "  |\n"
            "Vehicles"
        )
    return "Unknown architecture"

def constraint_stack(site, arch: str) -> List[str]:
    lines = []
    lines.append(f"Cable cap: {site.cable_type} @ 800 V")
    lines.append(f"DC-DC cap: {site.dcdc_modules} × 100 kW per string")
    lines.append(f"Charger PCS cap: {site.pcs_sku} per string")
    lines.append(f"Grid import cap: {site.grid_connection_kw} kW (site)")

    if arch == "virtos":
        lines.append(f"Shared PCS cap: {site.shared_pcs_kw} kW (site, hard cap)")
        if site.allow_grid_charge:
            lines.append(f"Grid charging enabled up to {site.grid_charge_power_kw} kW")
        else:
            lines.append("Grid charging disabled")
    if arch == "ac":
        lines.append(f"AC BESS power: {site.ac_bess_power_kw} kW")
        lines.append(f"AC BESS energy: {site.ac_bess_energy_kwh} kWh")

    return lines

def power_flow_ledger(sim_result: Dict, dt_hours: float) -> List[Dict]:
    ledger = []
    ts = sim_result.get("timeseries", {})
    grid = ts.get("grid_import_kw_ts", [])
    pcs = ts.get("pcs_used_kw_ts", [None]*len(grid))

    state = sim_result.get("state", {})
    delivered = []
    demand = []
    soc = []

    if state:
        keys = list(state.keys())
        n = len(state[keys[0]]["demand_kw_ts"])
        for i in range(n):
            delivered.append(sum(state[k]["delivered_kw_ts"][i] for k in keys))
            demand.append(sum(state[k]["demand_kw_ts"][i] for k in keys))
            soc.append(sum(state[k]["soc_ts_kwh"][i] for k in keys))

    for i in range(len(grid)):
        ledger.append({
            "timestep": i,
            "demand_kw": demand[i] if demand else None,
            "delivered_kw": delivered[i] if delivered else None,
            "grid_import_kw": grid[i],
            "pcs_used_kw": pcs[i],
            "soc_kwh": soc[i] if soc else None,
            "energy_unserved_kwh": max((demand[i] - delivered[i]) * dt_hours, 0.0) if demand else None,
        })
    return ledger

def binding_constraint_hint(ledger: List[Dict]) -> str:
    if not ledger:
        return "No data"
    peak = max(ledger, key=lambda r: (r["grid_import_kw"] if r["grid_import_kw"] is not None else 0.0))
    return (
        f"Peak grid import occurs at timestep {peak['timestep']} "
        f"with {peak['grid_import_kw']:.1f} kW. "
        "This timestep is driving demand charges."
    )

def binding_summary(ledger: List[Dict]) -> Dict:
    """Return a small dict describing the peak-driving timestep."""
    if not ledger:
        return {"timestep": None, "peak_grid_import_kw": 0.0}
    peak = max(ledger, key=lambda r: (r["grid_import_kw"] if r["grid_import_kw"] is not None else 0.0))
    return {
        "timestep": peak["timestep"],
        "peak_grid_import_kw": float(peak["grid_import_kw"] or 0.0),
        "demand_kw": peak.get("demand_kw"),
        "delivered_kw": peak.get("delivered_kw"),
        "soc_kwh": peak.get("soc_kwh"),
    }

def value_prop_delta(costs_a: Dict, metrics_a: Dict, costs_b: Dict, metrics_b: Dict) -> Dict:
    """Compute simple, defensible deltas (A vs B)."""
    return {
        "delta_total_cost_$": float(costs_a["total_cost_$"] - costs_b["total_cost_$"]),
        "delta_demand_cost_$": float(costs_a["demand_cost_$"] - costs_b["demand_cost_$"]),
        "delta_energy_cost_$": float(costs_a["energy_cost_$"] - costs_b["energy_cost_$"]),
        "delta_peak_kw": float(costs_a["peak_kw"] - costs_b["peak_kw"]),
        "delta_power_satisfied_pct": float(metrics_a["power_satisfied_pct"] - metrics_b["power_satisfied_pct"]),
        "delta_time_satisfied_pct": float(metrics_a["time_satisfied_pct"] - metrics_b["time_satisfied_pct"]),
    }
