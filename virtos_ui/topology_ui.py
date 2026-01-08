import streamlit as st
from virtos_engine.schemas import SiteSpec, DemandProfile, PCS_LIBRARY, BATTERY_LIBRARY, CABLE_LIBRARY
from .inputs import PRESETS


def render_topology_strip_variant_b():
    """Orientation-only topology strip (Variant B).

    Visual anchor only. No controls.
    """
    st.markdown(
        """
<style>
.topoB-wrap{margin:6px 0 10px 0;}
.topoB-row{display:flex;align-items:center;justify-content:center;gap:10px;flex-wrap:wrap;}
.topoB-node{padding:7px 10px;border:1px solid rgba(255,255,255,0.12);border-radius:12px;min-width:118px;text-align:center;}
.topoB-link{opacity:0.55;font-size:18px;}
.topoB-title{font-size:12px;opacity:0.85;margin-top:2px;}
.topoB-sub{font-size:11px;opacity:0.65;margin-top:-2px;}
</style>
<div class="topoB-wrap">
  <div class="topoB-row">
    <div class="topoB-node">💲<div class="topoB-title">Utility</div><div class="topoB-sub">tariffs</div></div>
    <div class="topoB-link">→</div>
    <div class="topoB-node">🗼<div class="topoB-title">Grid</div><div class="topoB-sub">connection</div></div>
    <div class="topoB-link">→</div>
    <div class="topoB-node">⚡<div class="topoB-title">PCS</div><div class="topoB-sub">shared cap</div></div>
    <div class="topoB-link">→</div>
    <div class="topoB-node">🧱<div class="topoB-title">Charge Array</div><div class="topoB-sub">DC-DC</div></div>
    <div class="topoB-link">→</div>
    <div class="topoB-node">⛽<div class="topoB-title">Dispensers</div><div class="topoB-sub">cables</div></div>
    <div class="topoB-link">→</div>
    <div class="topoB-node">🧾<div class="topoB-title">Revenue</div><div class="topoB-sub">pricing</div></div>
    <div class="topoB-link">→</div>
    <div class="topoB-node">🚚<div class="topoB-title">Vehicles</div><div class="topoB-sub">mix</div></div>
  </div>
  <div class="topoB-row" style="margin-top:4px;">
    <div style="min-width:118px;"></div>
    <div style="min-width:118px;"></div>
    <div class="topoB-link" style="transform: translateX(-8px);">↓</div>
    <div class="topoB-node">🔋<div class="topoB-title">Battery</div><div class="topoB-sub">power/energy</div></div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


def _demand_curve_editor(default_curve):
    """15-min utilisation curve editor (authoritative demand).

    Returns a list[float] length N.
    """
    import pandas as pd

    st.caption("Authoritative demand input. 15 min timestep (0.25 h). Values are utilisation [0–1].")
    preset = st.selectbox("Preset", list(PRESETS.keys()), index=0, key="inp_util_preset")
    curve = list(PRESETS.get(preset, default_curve))

    # Allow inline edits (v1) without introducing session-level simulation.
    df = pd.DataFrame({"timestep": list(range(len(curve))), "utilisation": curve})
    edited = st.data_editor(
        df,
        hide_index=True,
        width="stretch",
        column_config={
            "timestep": st.column_config.NumberColumn("t", disabled=True),
            "utilisation": st.column_config.NumberColumn("utilisation", min_value=0.0, max_value=1.0, step=0.01),
        },
        key="inp_util_editor",
    )
    out = [float(x) for x in edited["utilisation"].tolist()]
    return out


def render_site_inputs_dashboard(default_n_strings: int = 2) -> SiteSpec:
    """Variant B dashboard inputs.

    Returns SiteSpec (engine inputs). UI-only extras (revenue, vehicle mix, dispenser mix)
    are stored in st.session_state under keys prefixed with ui_.
    """
    render_topology_strip_variant_b()

    # Demand is drill-down (collapsed by default): keep it out of the main dashboard density.
    default_curve = PRESETS[list(PRESETS.keys())[0]]
    with st.expander("Demand (authoritative utilisation curve)", expanded=False):
        curve = _demand_curve_editor(default_curve)

    # --- Row A: Utility | Grid | PCS | Battery
    row_a = st.columns(4, gap="small")

    with row_a[0]:
        st.markdown("### 💲 Utility")
        offpeak = st.number_input("Off-peak $/kWh", min_value=0.0, value=0.12, step=0.01, key="inp_t_off")
        shoulder = st.number_input("Shoulder $/kWh", min_value=0.0, value=0.20, step=0.01, key="inp_t_sh")
        peak = st.number_input("Peak $/kWh", min_value=0.0, value=0.35, step=0.01, key="inp_t_pk")
        demand_charge = st.number_input("Demand $/kW-month", min_value=0.0, value=25.0, step=1.0, key="inp_t_dc")

    with row_a[1]:
        st.markdown("### 🗼 Grid")
        grid_connection_kw = st.number_input("Grid connection cap (kW)", min_value=0.0, value=1000.0, step=50.0, key="inp_grid_kw")

    with row_a[2]:
        st.markdown("### ⚡ PCS")
        pcs_sku = st.selectbox("Charger PCS SKU (per string)", list(PCS_LIBRARY.keys()), index=0, key="inp_pcs_sku")
        shared_pcs_kw = st.number_input("Shared PCS cap (site kW, Virtos)", min_value=0.0, value=300.0, step=10.0, key="inp_shared_pcs_kw")

    with row_a[3]:
        st.markdown("### 🔋 Battery")
        battery_sku = st.selectbox("Battery SKU (per string)", list(BATTERY_LIBRARY.keys()), index=0, key="inp_batt_sku")
        allow_grid_charge = st.checkbox("Allow grid charging", value=False, key="inp_allow_grid_charge")
        grid_charge_target_soc_pct = st.slider("Grid charge target SOC (%)", 0.0, 100.0, 80.0, 1.0, key="inp_grid_charge_soc_pct")
        grid_charge_power_kw = st.number_input("Grid charge power (kW)", min_value=0.0, value=100.0, step=10.0, key="inp_grid_charge_kw")

    # --- Row B: Charge Array | Dispensers | Revenue | Vehicles
    row_b = st.columns(4, gap="small")

    with row_b[0]:
        st.markdown("### 🧱 Charge Array")
        n_superstrings = st.number_input("Super-strings", min_value=1, value=int(default_n_strings), step=1, key="inp_n_strings")
        dcdc_modules = st.number_input("DC-DC modules / string (100 kW ea)", min_value=1, value=10, step=1, key="inp_dcdc_modules")

    with row_b[1]:
        st.markdown("### ⛽ Dispensers")
        cable_type = st.selectbox("Cable type", list(CABLE_LIBRARY.keys()), index=0, key="inp_cable_type")
        st.caption("v1: dispenser mix is UI-only (engine uses cable + DC-DC aggregate).")
        # UI-only: dispenser mix table
        import pandas as pd
        default_mix = st.session_state.get("ui_dispenser_mix")
        if default_mix is None:
            default_mix = [{"type": "HPC", "qty": 4}, {"type": "MCS", "qty": 0}]
        df = pd.DataFrame(default_mix)
        mix = st.data_editor(
            df,
            hide_index=True,
            width="stretch",
            column_config={
                "type": st.column_config.TextColumn("type"),
                "qty": st.column_config.NumberColumn("qty", min_value=0, step=1),
            },
            key="inp_disp_mix",
        )
        st.session_state["ui_dispenser_mix"] = mix.to_dict(orient="records")

    with row_b[2]:
        st.markdown("### 🧾 Revenue")
        st.caption("v1: pricing is UI-only; not yet in engine cost model.")
        import pandas as pd
        default_prices = st.session_state.get("ui_pricing")
        if default_prices is None:
            default_prices = [{"type": "HPC", "$/kWh": 0.65, "$/min": 0.00}, {"type": "MCS", "$/kWh": 0.85, "$/min": 0.00}]
        pdf = pd.DataFrame(default_prices)
        prices = st.data_editor(
            pdf,
            hide_index=True,
            width="stretch",
            column_config={
                "type": st.column_config.TextColumn("type"),
                "$/kWh": st.column_config.NumberColumn("$/kWh", min_value=0.0, step=0.01),
                "$/min": st.column_config.NumberColumn("$/min", min_value=0.0, step=0.01),
            },
            key="inp_prices",
        )
        st.session_state["ui_pricing"] = prices.to_dict(orient="records")

    with row_b[3]:
        st.markdown("### 🚚 Vehicles")
        st.caption("v1: vehicle mix is UI-only; demand remains authoritative via utilisation curve.")
        import pandas as pd
        default_vmix = st.session_state.get("ui_vehicle_mix")
        if default_vmix is None:
            default_vmix = [{"vehicle": "Rigid", "share": 0.5}, {"vehicle": "Prime mover", "share": 0.5}]
        vdf = pd.DataFrame(default_vmix)
        vmix = st.data_editor(
            vdf,
            hide_index=True,
            width="stretch",
            column_config={
                "vehicle": st.column_config.TextColumn("vehicle"),
                "share": st.column_config.NumberColumn("share", min_value=0.0, max_value=1.0, step=0.05),
            },
            key="inp_vehicle_mix",
        )
        st.session_state["ui_vehicle_mix"] = vmix.to_dict(orient="records")

    # AC-coupled BESS params (keep, but not in dashboard surface)
    with st.expander("AC-coupled baseline (BESS behind-the-meter)", expanded=False):
        ac_bess_power_kw = st.number_input("AC BESS inverter power (kW)", min_value=0.0, value=500.0, step=50.0, key="inp_ac_bess_power_kw")
        ac_bess_energy_kwh = st.number_input("AC BESS energy (kWh)", min_value=0.0, value=1000.0, step=50.0, key="inp_ac_bess_energy_kwh")

    demand = DemandProfile(utilisation_curve=curve, timestep_minutes=15)

    from virtos_engine.schemas import TariffSpec
    tariff = TariffSpec(
        offpeak_price_per_kwh=float(offpeak),
        shoulder_price_per_kwh=float(shoulder),
        peak_price_per_kwh=float(peak),
        demand_charge_per_kw_month=float(demand_charge),
    )

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
        tariff=tariff,
    )
    return site

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
