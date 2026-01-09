import streamlit as st
import pandas as pd
from .powerflow import render_powerflow_diagram

def init_state():
    # Canonical (v1.4)
    st.session_state.setdefault("timestep_h", 0.25)
    st.session_state.setdefault("vehicle_voltage_v", 800.0)

    # Architecture
    st.session_state.setdefault("architecture", "Virtos (DC-coupled)")

    # Grid / PCS
    st.session_state.setdefault("grid_connection_kw", 1000.0)
    st.session_state.setdefault("pcs_shared_kw", 300.0)  # site-level cap (Virtos) or charger PCS cap (baselines)

    # Battery (Virtos + AC-coupled)
    st.session_state.setdefault("battery_power_kw", 0.0)
    st.session_state.setdefault("battery_energy_kwh", 0.0)
    st.session_state.setdefault("battery_initial_soc_frac", 1.0)  # v1: time-local, no look-ahead charging
    st.session_state.setdefault("ac_inverter_kw", 0.0)  # AC-coupled only

    # Super-Strings / Charge Array
    st.session_state.setdefault("super_strings", 2)
    st.session_state.setdefault("dc_dc_modules_per_string", 10)

    # Dispensers / cables
    st.session_state.setdefault("cable_imax_a", 250.0)
    st.session_state.setdefault("dispenser_max_kw", 350.0)

    # Demand model (email scenario defaults)
    st.session_state.setdefault("qty_ac", 523)
    st.session_state.setdefault("ac_kw", 22.0)
    st.session_state.setdefault("qty_dc", 39)
    st.session_state.setdefault("dc_kw", 150.0)

    # Tariffs / revenue (placeholders)
    st.session_state.setdefault("tou_offpeak_per_kwh", 0.12)
    st.session_state.setdefault("tou_shoulder_per_kwh", 0.20)
    st.session_state.setdefault("tou_peak_per_kwh", 0.35)
    st.session_state.setdefault("demand_charge_per_kw_month", 0.0)

    st.session_state.setdefault("price_hpc_per_kwh", 0.65)
    st.session_state.setdefault("price_hpc_per_min", 0.0)

    if "util_curve" not in st.session_state:
        # 96 rows = 24h at 15 min. Seed curve is intentionally simple.
        base = [0.15,0.25,0.35,0.55,0.75,0.90,1.00,0.85,0.70,0.55,0.40,0.25]
        vals = (base * 8)[:96]
        st.session_state["util_curve"] = pd.DataFrame({"t": list(range(96)), "utilisation": vals})

def render_topology_and_columns():
    init_state()

    st.subheader("Site configuration")

    # Topology (visual anchor)
    render_powerflow_diagram({
        "architecture": st.session_state["architecture"],
        "grid_connection_kw": st.session_state["grid_connection_kw"],
        "pcs_shared_kw": st.session_state["pcs_shared_kw"],
        "battery_power_kw": st.session_state["battery_power_kw"],
        "battery_energy_kwh": st.session_state["battery_energy_kwh"],
        "ac_inverter_kw": st.session_state["ac_inverter_kw"],
        "super_strings": st.session_state["super_strings"],
        "dc_dc_modules_per_string": st.session_state["dc_dc_modules_per_string"],
        "cable_imax_a": st.session_state["cable_imax_a"],
        "vehicle_voltage_v": st.session_state["vehicle_voltage_v"],
        "dispenser_max_kw": st.session_state["dispenser_max_kw"],
    })

    c1,c2,c3,c4,c5,c6,c7,c8 = st.columns([1.15,1,1,1,1,1,1,1], gap="medium")

    with c1:
        st.markdown("### Utility")
        st.number_input("Off-peak $/kWh", min_value=0.0, step=0.01, format="%.3f", key="tou_offpeak_per_kwh")
        st.number_input("Shoulder $/kWh", min_value=0.0, step=0.01, format="%.3f", key="tou_shoulder_per_kwh")
        st.number_input("Peak $/kWh", min_value=0.0, step=0.01, format="%.3f", key="tou_peak_per_kwh")
        st.number_input("Demand charge $/kW/month", min_value=0.0, step=1.0, format="%.2f", key="demand_charge_per_kw_month")

    with c2:
        st.markdown("### Grid")
        st.number_input("Grid connection cap (kW)", min_value=0.0, step=50.0, format="%.1f", key="grid_connection_kw")

    with c3:
        st.markdown("### Architecture")
        st.selectbox(
            "Architecture",
            ["Virtos (DC-coupled)", "Grid-only", "AC-coupled BESS"],
            key="architecture",
        )

    with c4:
        st.markdown("### PCS")
        st.number_input("PCS cap (kW)", min_value=0.0, step=25.0, format="%.1f", key="pcs_shared_kw")

    with c5:
        st.markdown("### Battery")
        st.number_input("Battery power (kW)", min_value=0.0, step=50.0, format="%.1f", key="battery_power_kw")
        st.number_input("Battery energy (kWh)", min_value=0.0, step=100.0, format="%.1f", key="battery_energy_kwh")
        st.slider("Initial SOC", min_value=0.0, max_value=1.0, step=0.05, key="battery_initial_soc_frac")
        if st.session_state.get("architecture") == "AC-coupled BESS":
            st.number_input("AC inverter (kW)", min_value=0.0, step=50.0, format="%.1f", key="ac_inverter_kw")
        else:
            st.caption("Inverter applies only to AC-coupled.")

    with c6:
        st.markdown("### Charge Array")
        st.number_input("Super-strings", min_value=0, step=1, key="super_strings")
        st.number_input("DC-DC modules / string", min_value=0, step=1, key="dc_dc_modules_per_string")

    with c7:
        st.markdown("### Dispensers")
        st.number_input("Cable Imax (A)", min_value=0.0, step=10.0, format="%.0f", key="cable_imax_a")
        st.number_input("Dispenser max (kW)", min_value=0.0, step=10.0, format="%.0f", key="dispenser_max_kw")
        st.number_input("Vehicle voltage (V)", min_value=0.0, step=50.0, format="%.0f", key="vehicle_voltage_v")

    with c8:
        st.markdown("### Revenue")
        st.number_input("HPC $/kWh", min_value=0.0, step=0.05, format="%.2f", key="price_hpc_per_kwh")
        st.number_input("HPC $/min", min_value=0.0, step=0.05, format="%.2f", key="price_hpc_per_min")

    with st.expander("Demand model (utilisation ∈ [0,1])", expanded=False):
        st.caption("This is an aggregate utilisation envelope (behavioural). 96 rows = 24h at 15 min.")
        cc1, cc2, cc3 = st.columns([1,1,1])
        with cc1:
            st.number_input("AC chargers (qty)", min_value=0, step=1, key="qty_ac")
            st.number_input("AC charger kW", min_value=0.0, step=1.0, format="%.1f", key="ac_kw")
        with cc2:
            st.number_input("DC chargers (qty)", min_value=0, step=1, key="qty_dc")
            st.number_input("DC charger kW", min_value=0.0, step=5.0, format="%.1f", key="dc_kw")
        with cc3:
            st.caption("Derived peak nameplate (kW)")
            peak = (st.session_state["qty_ac"]*st.session_state["ac_kw"] + st.session_state["qty_dc"]*st.session_state["dc_kw"])
            st.metric("Nameplate sum", f"{peak:,.0f} kW")

        edited = st.data_editor(
            st.session_state["util_curve"],
            num_rows="fixed",
            width="stretch",
            hide_index=True,
        )
        st.session_state["util_curve"] = edited
