import streamlit as st
from virtos_engine.schemas import SiteSpec, DemandProfile, PCS_LIBRARY, BATTERY_LIBRARY, CABLE_LIBRARY
from .inputs import PRESETS

def render_topology_banner():
    # Simple T-shape using markdown. One icon per node, per handover.
    st.markdown(
        """
<style>
.topo-row { display:flex; align-items:center; justify-content:center; gap:14px; margin: 6px 0 10px 0; }
.topo-node { padding:8px 10px; border:1px solid rgba(255,255,255,0.12); border-radius:10px; min-width:110px; text-align:center; }
.topo-link { opacity:0.55; font-size:22px; }
.topo-title { font-size:12px; opacity:0.8; margin-top:2px; }
</style>
<div class="topo-row">
  <div class="topo-node">🗼<div class="topo-title">Grid</div></div>
  <div class="topo-link">→</div>
  <div class="topo-node">⚡<div class="topo-title">PCS</div></div>
  <div class="topo-link">→</div>
  <div class="topo-node">⛽<div class="topo-title">Dispensers</div></div>
</div>
<div class="topo-row" style="margin-top:-4px;">
  <div style="width:110px;"></div>
  <div class="topo-link" style="transform: translateX(-10px);">↓</div>
  <div class="topo-node">🔋<div class="topo-title">Battery</div></div>
  <div style="width:110px;"></div>
</div>
""",
        unsafe_allow_html=True,
    )

def render_site_inputs_form(default_n_strings: int = 2) -> SiteSpec:
    """Main-page configuration UI (v1). Returns a SiteSpec.

    Design intent: inputs live under the topology nodes, not the sidebar.
    Execution intent: used inside a form so changes only apply on submit.
    """

    st.subheader("Site configuration")
    render_topology_banner()

    # Top row: demand + super-strings is conceptually separate from topology nodes
    with st.expander("Demand (utilisation curve)", expanded=True):
        preset = st.selectbox("Utilisation preset", list(PRESETS.keys()), index=0, key="inp_util_preset")
        curve = PRESETS[preset]
        st.caption("Utilisation curve is the authoritative aggregate demand input (15 min timestep).")
        st.write({"preset": preset, "points": len(curve), "curve": curve})

    cols = st.columns(4, gap="large")

    with cols[0]:
        st.markdown("#### 🗼 Grid")
        grid_connection_kw = st.number_input("Grid connection cap (kW)", min_value=0.0, value=1000.0, step=50.0, key="inp_grid_kw")
        st.caption("Hard cap: site import cannot exceed this.")

    with cols[1]:
        st.markdown("#### ⚡ PCS")
        pcs_sku = st.selectbox("Charger PCS SKU (per string)", list(PCS_LIBRARY.keys()), index=0, key="inp_pcs_sku")
        shared_pcs_kw = st.number_input("Shared PCS cap (site kW, Virtos only)", min_value=0.0, value=300.0, step=10.0, key="inp_shared_pcs_kw")
        st.caption("Virtos: shared PCS is a site-level hard cap for PCS↔Grid and PCS↔Array.")

    with cols[2]:
        st.markdown("#### 🔋 Battery")
        battery_sku = st.selectbox("Virtos battery SKU (per string)", list(BATTERY_LIBRARY.keys()), index=0, key="inp_batt_sku")
        allow_grid_charge = st.checkbox("Allow grid charging", value=False, key="inp_allow_grid_charge")
        grid_charge_target_soc_pct = st.slider("Grid charge target SOC (%)", 0.0, 100.0, 80.0, 1.0, key="inp_grid_charge_soc_pct")
        grid_charge_power_kw = st.number_input("Grid charge power (kW)", min_value=0.0, value=100.0, step=10.0, key="inp_grid_charge_kw")

    with cols[3]:
        st.markdown("#### ⛽ Dispensers")
        cable_type = st.selectbox("Cable type", list(CABLE_LIBRARY.keys()), index=0, key="inp_cable_type")
        dcdc_modules = st.slider("DC-DC modules per string (100 kW each)", 1, 24, 10, 1, key="inp_dcdc_modules")
        st.caption("Per-cable cap enforced as 800 V × Imax; per-module cap is 100 kW.")

    with st.expander("Super-strings (site)", expanded=True):
        n_superstrings = st.slider("Number of super-strings", 1, 12, int(default_n_strings), 1, key="inp_n_strings")
        st.caption("Super-strings are logical units. v1 assumes identical strings for simplicity.")

    # AC-coupled BESS params live here (only used in AC-coupled sim)
    with st.expander("AC-coupled BESS (baseline)", expanded=False):
        ac_bess_power_kw = st.number_input("AC BESS inverter power (kW)", min_value=0.0, value=500.0, step=50.0, key="inp_ac_bess_power_kw")
        ac_bess_energy_kwh = st.number_input("AC BESS energy (kWh)", min_value=0.0, value=1000.0, step=50.0, key="inp_ac_bess_energy_kwh")

    demand = DemandProfile(utilisation_curve=curve, timestep_minutes=15)

    site = SiteSpec(
        demand=demand,
        n_superstrings=int(n_superstrings),
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
