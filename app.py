
import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(layout="wide", page_title="Virtos Site Simulator v1")

st.markdown("""
<style>
:root { --virtos-green:#7ED957; }
h1,h2,h3 { color: var(--virtos-green); }
</style>
""", unsafe_allow_html=True)

st.title("Virtos Site Simulator — DC Only (v1)")

# ---- Layout ----
cols = st.columns([1.2,1.5,1.5,1.2,1.2,1.2,1.5])

# Grid
with cols[0]:
    st.subheader("Grid")
    grid_cap_kw = st.number_input("Grid cap (kW)", 0, 50000, 11380)

# Dispensers
with cols[1]:
    st.subheader("Dispensers")
    disp = st.data_editor(
        {
            "type":["CCS"],
            "qty":[39],
            "imax_a":[250],
            "voltage_v":[800]
        },
        key="disp",
        num_rows="dynamic",
        hide_index=True
    )
    disp["per_unit_kw"] = disp.imax_a * disp.voltage_v / 1000
    disp["nameplate_kw"] = disp.qty * disp.per_unit_kw
    total_nameplate_kw = disp.nameplate_kw.sum()
    st.metric("Installed fast charge (kW)", int(total_nameplate_kw))

# Vehicles & Utilisation
with cols[2]:
    st.subheader("Vehicles & Utilisation")
    profile = st.selectbox("Profile", ["Depot","Custom"])
    util = pd.DataFrame({
        "t": range(96),
        "utilisation": np.clip(np.sin(np.linspace(0,3.14,96)),0,1)
    })
    if profile=="Custom":
        util = st.data_editor(util, key="util", hide_index=True)
    st.line_chart(util.utilisation)

# PCS
with cols[3]:
    st.subheader("PCS")
    pcs_kw = st.number_input("PCS (kW)", 0, 20000, 300)

# Battery
with cols[4]:
    st.subheader("Battery")
    batt_p = st.number_input("Battery power (kW)", 0, 20000, 200)
    batt_e = st.number_input("Battery energy (kWh)", 0, 100000, 400)
    soc0 = st.slider("Initial SOC", 0.0, 1.0, 0.5)

# Charge Array
with cols[5]:
    st.subheader("Charge Array")
    ss = st.number_input("Super-strings", 1, 20, 2)
    dcdc = st.number_input("DC-DC / string", 1, 50, 10)
    array_kw = ss*dcdc*100
    st.metric("Array cap (kW)", array_kw)

# Results
with cols[6]:
    st.subheader("Results")
    demand_kw = total_nameplate_kw * util.utilisation.values
    served_kw = np.minimum(demand_kw, pcs_kw + batt_p)
    st.metric("Peak demand (kW)", int(demand_kw.max()) if len(demand_kw)>0 else 0)
    st.metric("Peak served (kW)", int(served_kw.max()) if len(served_kw)>0 else 0)
    st.metric("Energy served (kWh/day)", round(served_kw.sum()*0.25,1))

st.divider()
st.subheader("Power Traces")
st.line_chart(pd.DataFrame({
    "Demand (kW)": demand_kw,
    "Served (kW)": served_kw
}))
