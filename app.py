import streamlit as st
import pandas as pd
import numpy as np

from virtos_engine.schemas import (
    SiteSpec, DemandProfile, TariffSpec, SuperStringSpec,
    DispenserTypeSpec, VehicleRevenueSpec
)
from virtos_engine.core import run_engine
from virtos_ui.library import render_library_tab
from virtos_ui.diagnostics import render_diagnostics_tab
from virtos_ui.powerflow import render_powerflow_strip
from virtos_ui.utilisation import render_utilisation_editor
from virtos_ui.dispensers import render_dispensers_table
from virtos_ui.blocks import render_metric_card

st.set_page_config(page_title="Virtos Site Simulator (v1 DC-only)", layout="wide")

# ---- Theme: Virtos green highlights ----
VIRTOS_GREEN = "#7ED957"  # Pantone 376C approx for web
st.markdown(f"""
<style>
:root {{ --virtos-green:{VIRTOS_GREEN}; }}
h1,h2,h3 {{ color: var(--virtos-green); }}
div[data-testid="stMetricLabel"] p {{ color: var(--virtos-green) !important; }}
</style>
""", unsafe_allow_html=True)

st.title("Virtos Site Simulator — Virtos DC Only (v1)")

tabs = st.tabs(["Simulator (Virtos)", "Component Library", "Diagnostics", "Other Architectures (v1.5+)"])

with tabs[0]:
    # --- Top: Site configuration ---
    st.subheader("Site configuration")

    # 7-column spine: Utility&Tariff, Grid, Dispensers, Vehicles/Utilisation/Revenue, PCS, Battery, Charge Array
    cols = st.columns([1.2,1.1,1.6,1.8,1.1,1.2,1.2], gap="small")

    with cols[0]:
        st.markdown("#### Utility & energy costs")
        offpeak = st.number_input("Off-peak ($/kWh)", 0.0, 5.0, 0.12, key="tou_offpeak")
        shoulder = st.number_input("Shoulder ($/kWh)", 0.0, 5.0, 0.20, key="tou_shoulder")
        peak = st.number_input("Peak ($/kWh)", 0.0, 5.0, 0.35, key="tou_peak")
        demand_charge = st.number_input("Demand charge ($/kW/month)", 0.0, 500.0, 20.0, key="demand_charge")

    with cols[1]:
        st.markdown("#### Grid connection")
        grid_kw = st.number_input("Grid cap (kW)", 0.0, 200000.0, 11380.0, step=10.0, key="grid_kw")

    with cols[2]:
        st.markdown("#### Dispensers")
        disp_df, disp_summary = render_dispensers_table(key_prefix="disp")
        render_metric_card("Installed fast-charge", [
            f"Total: {disp_summary['total_units']} units",
            f"Cap: {disp_summary['total_nameplate_kw']:.0f} kW"
        ])

    with cols[3]:
        st.markdown("#### Vehicles, utilisation & revenue")
        util_curve = render_utilisation_editor(key_prefix="util")
        price_kwh = st.number_input("Revenue ($/kWh)", 0.0, 10.0, 0.65, key="rev_kwh")
        price_min = st.number_input("Revenue ($/min)", 0.0, 10.0, 0.0, key="rev_min")
        render_metric_card("Demand input", [
            "Utilisation: 0–1",
            f"Timesteps: {len(util_curve)} × 15 min"
        ])

    # --- Bottom: Virtos implementation ---
    st.subheader("Virtos implementation")

    with cols[4]:
        st.markdown("#### PCS")
        pcs_shared_kw = st.number_input("Shared PCS cap (kW)", 0.0, 200000.0, 3000.0, step=10.0, key="pcs_kw")

    with cols[5]:
        st.markdown("#### Battery")
        batt_power_kw = st.number_input("Battery power (kW)", 0.0, 200000.0, 2000.0, step=10.0, key="batt_p")
        batt_energy_kwh = st.number_input("Battery energy (kWh)", 0.0, 1000000.0, 8000.0, step=50.0, key="batt_e")
        soc0 = st.slider("Initial SOC", 0.0, 1.0, 0.5, key="soc0")

    with cols[6]:
        st.markdown("#### Charge Array")
        n_super = st.number_input("Super-strings", 1, 50, 2, step=1, key="n_super")
        dcdc_per = st.number_input("DC-DC per string", 1, 200, 10, step=1, key="dcdc_per")
        array_cap_kw = float(n_super * dcdc_per * 100.0)
        render_metric_card("Array cap", [f"{array_cap_kw:.0f} kW"])

    # ---- Run engine ----
    # Build dispenser type specs
    disp_types = []
    for _, r in disp_df.iterrows():
        disp_types.append(DispenserTypeSpec(
            name=str(r["name"]),
            connector=str(r["connector"]),
            qty=int(r["qty"]),
            imax_a=float(r["imax_a"]),
            voltage_v=800.0
        ))

    # Demand profile
    demand = DemandProfile(utilisation_curve=[float(x) for x in util_curve], timestep_minutes=15)

    # Tariff (simplified time-of-use, indices kept generic)
    tariff = TariffSpec(
        offpeak_price_per_kwh=float(offpeak),
        shoulder_price_per_kwh=float(shoulder),
        peak_price_per_kwh=float(peak),
        demand_charge_per_kw_month=float(demand_charge),
        peak_start_idx=48, peak_end_idx=72,
        shoulder_indices=list(range(36,48)) + list(range(72,84))
    )

    # Revenue spec
    revenue = VehicleRevenueSpec(price_per_kwh=float(price_kwh), price_per_min=float(price_min))

    ss_specs = []
    for i in range(int(n_super)):
        ss_specs.append(SuperStringSpec(
            name=f"SS{i+1}",
            pcs_kw=float(pcs_shared_kw),  # site cap handled in engine
            battery_power_kw=float(batt_power_kw),
            battery_energy_kwh=float(batt_energy_kwh),
            dc_dc_modules=int(dcdc_per),
            initial_soc=float(soc0),
        ))

    site = SiteSpec(
        grid_connection_kw=float(grid_kw),
        pcs_shared_kw=float(pcs_shared_kw),
        demand=demand,
        tariff=tariff,
        dispensers=disp_types,
        revenue=revenue,
        superstrings=ss_specs,
    )

    result = run_engine(site)

    # ---- Power flow strip (aligned to columns) ----
    render_powerflow_strip(
        grid_kw=float(grid_kw),
        pcs_kw=float(pcs_shared_kw),
        batt_kw=float(batt_power_kw),
        batt_kwh=float(batt_energy_kwh),
        array_kw=array_cap_kw,
        disp_kw=float(disp_summary["total_nameplate_kw"]),
        binding=result.get("binding_constraints", [])
    )

    # ---- Results (not full-width hijack) ----
    st.subheader("Results")
    m = result["metrics"]
    rcols = st.columns(4)
    rcols[0].metric("Peak demand (kW)", f"{m['peak_demand_kw']:.0f}")
    rcols[1].metric("Peak served (kW)", f"{m['peak_served_kw']:.0f}")
    rcols[2].metric("Energy served (kWh/day)", f"{m['energy_served_kwh']:.0f}")
    rcols[3].metric("Power satisfied (%)", f"{m['power_satisfied_pct']:.1f}")

    with st.expander("Detailed power traces", expanded=False):
        st.line_chart(pd.DataFrame(result["timeseries"]))

with tabs[1]:
    render_library_tab()

with tabs[2]:
    render_diagnostics_tab()

with tabs[3]:
    st.info("Grid-only and AC-coupled comparisons are intentionally out of scope for v1.\n\nThey will be implemented in a separate tab in v1.5+.")
