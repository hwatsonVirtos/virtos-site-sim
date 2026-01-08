import streamlit as st
from virtos_ui.layout import render_topology_and_columns
from virtos_ui.library import render_library_tab
from virtos_ui.diagnostics import render_diagnostics_tab
from virtos_engine.core import run_engine

st.set_page_config(page_title="Virtos Site Simulator", layout="wide")

def sidebar_runcontrol():
    st.sidebar.header("Run control")
    st.sidebar.toggle("Auto-run after Apply", key="autorun", value=True)
    return st.sidebar.button("Apply & Run", type="primary")

def collect_cfg():
    return {
        "grid_connection_kw": st.session_state.get("grid_connection_kw", 1000.0),
        "pcs_shared_kw": st.session_state.get("pcs_shared_kw", 300.0),
        "super_strings": st.session_state.get("super_strings", 2),
        "dc_dc_modules_per_string": st.session_state.get("dc_dc_modules_per_string", 10),
        "tou_offpeak_per_kwh": st.session_state.get("tou_offpeak_per_kwh", 0.12),
        "tou_shoulder_per_kwh": st.session_state.get("tou_shoulder_per_kwh", 0.20),
        "tou_peak_per_kwh": st.session_state.get("tou_peak_per_kwh", 0.35),
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
        st.line_chart(ts[["demand_kw","served_kw"]], height=220, use_container_width=True)
        st.line_chart(ts[["grid_import_kw","unserved_kw"]], height=220, use_container_width=True)

with tabs[1]:
    render_library_tab()

with tabs[2]:
    render_diagnostics_tab()
