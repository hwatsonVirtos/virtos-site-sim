import streamlit as st
from virtos_engine.schemas import SiteSpec, DemandProfile, PCS_LIBRARY, BATTERY_LIBRARY, CABLE_LIBRARY

PRESETS = {
    "Depot (gentle peak)": [0.2,0.4,0.6,0.8,1.0,0.8,0.6,0.4],
    "Sustained high": [0.8,0.9,1.0,1.0,1.0,1.0,1.0,0.9,0.8,0.8,0.8,0.8],
    "Flat 70%": [0.7]*12,
}

def build_site_from_sidebar() -> SiteSpec:
    st.sidebar.header("Site Inputs")

    preset = st.sidebar.selectbox("Utilisation preset", list(PRESETS.keys()), index=0)
    curve = PRESETS[preset]

    n_superstrings = st.sidebar.slider("Number of super-strings", 1, 8, 2, 1)

    grid_connection_kw = st.sidebar.slider("Grid connection (site import cap, kW)", 0, 5000, 1000, 50)

    pcs_sku = st.sidebar.selectbox("Charger PCS SKU (per string)", list(PCS_LIBRARY.keys()), index=0)
    battery_sku = st.sidebar.selectbox("Virtos battery SKU (per string)", list(BATTERY_LIBRARY.keys()), index=0)
    dcdc_modules = st.sidebar.slider("DC-DC modules per string (100 kW each)", 1, 20, 10, 1)
    cable_type = st.sidebar.selectbox("Cable type", list(CABLE_LIBRARY.keys()), index=0)

    st.sidebar.subheader("Virtos (DC-coupled)")
    shared_pcs_kw = st.sidebar.slider("Shared PCS cap (site kW)", 0, 5000, 300, 50)

    allow_grid_charge = st.sidebar.checkbox("Allow grid charging of batteries (v1.1)", value=False)
    grid_charge_target_soc_pct = st.sidebar.slider("Charge target SOC (%)", 50, 100, 100, 1)
    grid_charge_power_kw = st.sidebar.slider("Max grid charging power (site kW)", 0, 3000, 200, 50)

    st.sidebar.subheader("AC-coupled competitor (grid-side BESS)")
    ac_bess_power_kw = st.sidebar.slider("AC BESS inverter power (kW)", 0, 5000, 0, 50)
    ac_bess_energy_kwh = st.sidebar.slider("AC BESS energy (kWh)", 0, 20000, 0, 250)

    site = SiteSpec(
        name="Virtos Internal Site",
        demand=DemandProfile(utilisation_curve=curve, timestep_minutes=15),
        n_superstrings=n_superstrings,
        grid_connection_kw=float(grid_connection_kw),
        shared_pcs_kw=float(shared_pcs_kw),
        pcs_sku=pcs_sku,
        battery_sku=battery_sku,
        dcdc_modules=int(dcdc_modules),
        cable_type=cable_type,
        allow_grid_charge=bool(allow_grid_charge),
        grid_charge_target_soc_pct=float(grid_charge_target_soc_pct),
        grid_charge_power_kw=float(grid_charge_power_kw),
        ac_bess_power_kw=float(ac_bess_power_kw),
        ac_bess_energy_kwh=float(ac_bess_energy_kwh),
    )
    return site
