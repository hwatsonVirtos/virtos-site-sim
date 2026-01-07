import streamlit as st
from virtos_engine.library import load_library
from virtos_engine.schemas import SiteSpec

def render_metrics(metrics: dict):
    c1, c2, c3 = st.columns(3)
    c1.metric("Time satisfied (%)", f"{metrics['time_satisfied_pct']:.1f}")
    c2.metric("Power satisfied (%)", f"{metrics['power_satisfied_pct']:.1f}")
    c3.metric("Energy not served (kWh)", f"{metrics['energy_not_served_kwh']:.1f}")

def render_costs(costs: dict, site: SiteSpec | None = None):
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Energy (kWh)", f"{costs['energy_kwh']:.1f}")
    c2.metric("Energy cost ($)", f"{costs['energy_cost_$']:.2f}")
    c3.metric("Demand cost ($/mo)", f"{costs['demand_cost_$']:.2f}")
    c4.metric("Peak kW", f"{costs['peak_kw']:.1f}")

    st.metric("Total ($/mo)", f"{costs['total_cost_$']:.2f}")

    if site is not None:
        payload, _ = load_library()
        # Build a quick lookup by component_id
        lookup = {r.get("component_id"): r for r in payload.get("records", [])}
        capex_lines = []
        total_capex = 0.0
        for cid in [site.pcs_sku, site.battery_sku, site.cable_type]:
            r = lookup.get(cid)
            if not r:
                continue
            capex = float((r.get("costs") or {}).get("capex_aud", 0.0) or 0.0)
            total_capex += capex
            capex_lines.append((cid, r.get("name",""), capex))
        st.divider()
        st.subheader("CapEx proxy (library)")
        if capex_lines:
            st.table([{"component_id": cid, "name": name, "capex_aud": capex} for cid, name, capex in capex_lines])
        st.metric("Total CapEx proxy (AUD)", f"{total_capex:.0f}")
        st.caption("Out-of-scope for v1 detailed CapEx. This is a placeholder sum of selected component records.")


def render_sanity_warnings(result: dict, site: SiteSpec, architecture: str):
    """Non-blocking warnings to highlight pathological runs. No auto-fixes."""
    metrics = result.get("metrics", {})
    costs = result.get("costs", {})
    ts = (result.get("timeseries") or {})
    state = (result.get("state") or {})

    warnings = []

    # Service degradation
    time_sat = float(metrics.get("time_satisfied_pct", 100.0) or 0.0)
    power_sat = float(metrics.get("power_satisfied_pct", 100.0) or 0.0)
    if time_sat < 99.0:
        warnings.append(f"Service time satisfied is {time_sat:.1f}%, below the 99% expectation (v1 soft expectation).")
    if power_sat < 99.0:
        warnings.append(f"Service power satisfied is {power_sat:.1f}%, below the 99% expectation (v1 soft expectation).")

    # PCS saturation (where applicable)
    pcs_used = ts.get("pcs_used_kw_ts") or []
    eff_cap = None
    try:
        eff_cap = float((result.get('site') or {}).get('effective_site_pcs_cap_kw'))
    except Exception:
        eff_cap = None
    if eff_cap and eff_cap > 0 and pcs_used:
        sat_steps = sum(1 for v in pcs_used if float(v) >= 0.999 * eff_cap)
        frac = sat_steps / max(1, len(pcs_used))
        if frac >= 0.10:
            warnings.append(f"PCS is saturated (≥99.9% of cap) for {frac*100:.1f}% of timesteps; delivery is likely PCS-limited.")

    # Grid cap saturation (all architectures)
    grid_ts = ts.get("grid_import_kw_ts") or []
    grid_cap = float(site.grid_connection_kw or 0.0)
    if grid_cap > 0 and grid_ts:
        sat_steps = sum(1 for v in grid_ts if float(v) >= 0.999 * grid_cap)
        frac = sat_steps / max(1, len(grid_ts))
        if frac >= 0.10:
            warnings.append(f"Grid import is capped for {frac*100:.1f}% of timesteps; delivery is likely grid-connection-limited.")

    # Battery SOC rail-hitting (architectures with battery state)
    soc_series = []
    soc_cap = None
    for s in state.values():
        series = s.get("soc_ts_kwh") or []
        if series:
            soc_series.append(series)
        # derived battery_kwh exists
        d = s.get("derived") or {}
        if soc_cap is None and d.get("battery_kwh") is not None:
            soc_cap = float(d.get("battery_kwh") or 0.0)
    if soc_series and soc_cap and soc_cap > 0:
        # total SOC across strings
        n = min(len(x) for x in soc_series)
        total = [0.0]*n
        for series in soc_series:
            for i in range(n):
                total[i] += float(series[i])
        near_empty = sum(1 for v in total if v <= 0.001 * soc_cap)
        near_full = sum(1 for v in total if v >= 0.999 * soc_cap)
        if near_empty / max(1, n) >= 0.10:
            warnings.append("Battery SOC is near-empty for ≥10% of timesteps; delivery is likely energy-limited (battery depleted).")
        if near_full / max(1, n) >= 0.10 and getattr(site, "allow_grid_charge", False):
            warnings.append("Battery SOC is near-full for ≥10% of timesteps while grid charging is enabled; charging headroom may be wasted.")

    if warnings:
        st.subheader("Sanity checks")
        for w in warnings:
            st.warning(w)
        st.caption("Warnings only. No behaviour changes are applied.")
