import streamlit as st
from virtos_ui.layout import render_topology_and_columns
from virtos_ui.library import render_library_tab
from virtos_ui.diagnostics import render_diagnostics_tab
from virtos_ui.theme import VIRTOS_GREEN
from virtos_engine.core import run_engine

st.set_page_config(page_title="Virtos Site Simulator", layout="wide")

# Enforce Virtos accent colour even if theme config is ignored in some deployments.
st.markdown(
    f"""
<style>
  :root {{ --virtos-accent: {VIRTOS_GREEN}; }}
  .stButton > button[kind="primary"], .stDownloadButton > button {{
    background-color: var(--virtos-accent) !important;
    color: #0B0D10 !important;
    border: 1px solid rgba(0,0,0,0.15) !important;
  }}
  .stButton > button[kind="primary"]:hover {{ filter: brightness(0.95); }}
</style>
""",
    unsafe_allow_html=True,
)

def sidebar_runcontrol():
    st.sidebar.header("Run control")
    st.sidebar.toggle("Auto-run after Apply", key="autorun", value=True)
    return st.sidebar.button("Apply & Run", type="primary")

def collect_cfg():
    return {
        "architecture": st.session_state.get("architecture", "Virtos (DC-coupled)"),
        "grid_connection_kw": st.session_state.get("grid_connection_kw", 1000.0),
        "pcs_cap_kw": st.session_state.get("pcs_shared_kw", 300.0),
        "super_strings": st.session_state.get("super_strings", 2),
        "dc_dc_modules_per_string": st.session_state.get("dc_dc_modules_per_string", 10),
        "cable_imax_a": st.session_state.get("cable_imax_a", 0.0),
        "vehicle_voltage_v": st.session_state.get("vehicle_voltage_v", 800.0),
        "dispenser_max_kw": st.session_state.get("dispenser_max_kw", 0.0),
        "battery_power_kw": st.session_state.get("battery_power_kw", 0.0),
        "battery_energy_kwh": st.session_state.get("battery_energy_kwh", 0.0),
        "battery_initial_soc_frac": st.session_state.get("battery_initial_soc_frac", 1.0),
        "ac_inverter_kw": st.session_state.get("ac_inverter_kw", 0.0),
        "qty_ac": st.session_state.get("qty_ac", 0),
        "ac_kw": st.session_state.get("ac_kw", 0.0),
        "qty_dc": st.session_state.get("qty_dc", 0),
        "dc_kw": st.session_state.get("dc_kw", 0.0),
        "tou_offpeak_per_kwh": st.session_state.get("tou_offpeak_per_kwh", 0.12),
        "tou_shoulder_per_kwh": st.session_state.get("tou_shoulder_per_kwh", 0.20),
        "tou_peak_per_kwh": st.session_state.get("tou_peak_per_kwh", 0.35),
        "demand_charge_per_kw_month": st.session_state.get("demand_charge_per_kw_month", 0.0),
        "util_curve": st.session_state.get("util_curve"),
    }

st.title("Virtos Site Simulator")

tabs = st.tabs(["Simulator","Library","Diagnostics"])
run_clicked = sidebar_runcontrol()

with tabs[0]:
    render_topology_and_columns()
    cfg = collect_cfg()

    should_run = run_clicked or (st.session_state.get("autorun") and st.session_state.get("util_curve") is not None)
    if should_run:
        try:
            st.session_state["last_result"] = run_engine(cfg)
        except Exception as e:
            st.error(f"Engine error: {e.__class__.__name__}: {e}")

    st.subheader("Results")
    res = st.session_state.get("last_result")
    if not res:
        st.info("No results yet. Click Apply & Run.")
    else:
        s = res["summary"]
        c1,c2,c3,c4 = st.columns(4)
        c1.metric("Energy (kWh)", f"{s['energy_kwh']:.1f}")
        c2.metric("Peak (kW)", f"{s['peak_kw']:.0f}")
        c3.metric("Energy cost ($)", f"{s['energy_cost_$']:.2f}")
        c4.metric("Power satisfied (%)", f"{s['power_satisfied_pct']:.1f}")

        ts = res["timeseries"].set_index("t")
        st.line_chart(ts[["demand_kw","served_kw"]], height=220, width="stretch")
        st.line_chart(ts[["grid_import_kw","unserved_kw"]], height=220, width="stretch")

with tabs[1]:
    render_library_tab()

with tabs[2]:
    render_diagnostics_tab()
