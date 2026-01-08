import streamlit as st
import pandas as pd
from .powerflow import render_powerflow_diagram

def init_state():
    st.session_state.setdefault("grid_connection_kw", 1000.0)
    st.session_state.setdefault("pcs_shared_kw", 300.0)
    st.session_state.setdefault("super_strings", 2)
    st.session_state.setdefault("dc_dc_modules_per_string", 10)
    st.session_state.setdefault("tou_offpeak_per_kwh", 0.12)
    st.session_state.setdefault("tou_shoulder_per_kwh", 0.20)
    st.session_state.setdefault("tou_peak_per_kwh", 0.35)
    st.session_state.setdefault("allow_grid_charging", False)
    st.session_state.setdefault("price_hpc_per_kwh", 0.65)

    if "util_curve" not in st.session_state:
        base = [0.2,0.4,0.6,0.8,1.0,0.8,0.6,0.4]
        vals = (base * 12)[:96]
        st.session_state["util_curve"] = pd.DataFrame({"t": list(range(96)), "utilisation": vals})

def render_topology_and_columns():
    init_state()

    st.subheader("Site configuration")

    render_powerflow_diagram({
        "grid_connection_kw": st.session_state["grid_connection_kw"],
        "pcs_shared_kw": st.session_state["pcs_shared_kw"],
        "super_strings": st.session_state["super_strings"],
        "dc_dc_modules_per_string": st.session_state["dc_dc_modules_per_string"],
    })

    c1,c2,c3,c4,c5,c6,c7 = st.columns([1.1,1,1,1,1,1,1], gap="medium")

    with c1:
        st.markdown("### Utility")
        st.number_input("Off-peak $/kWh", min_value=0.0, step=0.01, format="%.3f", key="tou_offpeak_per_kwh")
        st.number_input("Shoulder $/kWh", min_value=0.0, step=0.01, format="%.3f", key="tou_shoulder_per_kwh")
        st.number_input("Peak $/kWh", min_value=0.0, step=0.01, format="%.3f", key="tou_peak_per_kwh")

    with c2:
        st.markdown("### Grid")
        st.number_input("Grid connection cap (kW)", min_value=0.0, step=50.0, format="%.1f", key="grid_connection_kw")

    with c3:
        st.markdown("### PCS")
        st.number_input("PCS shared cap (kW)", min_value=0.0, step=25.0, format="%.1f", key="pcs_shared_kw")

    with c4:
        st.markdown("### Battery")
        st.caption("Placeholder: wiring + SKU selection next.")
        st.toggle("Allow grid charging", key="allow_grid_charging")

    with c5:
        st.markdown("### Charge Array")
        st.number_input("Super-strings", min_value=0, step=1, key="super_strings")

    with c6:
        st.markdown("### Dispensers")
        st.number_input("DC-DC modules / string (100 kW ea)", min_value=0, step=1, key="dc_dc_modules_per_string")

    with c7:
        st.markdown("### Revenue")
        st.number_input("HPC $/kWh", min_value=0.0, step=0.05, format="%.2f", key="price_hpc_per_kwh")

    with st.expander("Demand (authoritative utilisation curve)", expanded=False):
        st.caption("96 rows = 24h at 15 min. Values are utilisation [0–1].")
        edited = st.data_editor(
            st.session_state["util_curve"],
            num_rows="fixed",
            use_container_width=True,
            hide_index=True,
        )
        st.session_state["util_curve"] = edited
