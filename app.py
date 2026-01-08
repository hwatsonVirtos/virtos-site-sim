# app.py — hardened Streamlit entrypoint
# Goals:
# - Fast, deterministic boot on Streamlit Cloud
# - No heavy imports at module load
# - UI built lazily inside functions
# - Engine runs only after explicit Apply

import streamlit as st

# ---------- App config ----------
st.set_page_config(
    page_title="Virtos Site Simulator",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------- Utilities ----------
def _lazy_imports():
    """Import heavy modules only when needed."""
    from virtos_ui.layout import render_topology_and_columns
    from virtos_ui.library import render_library_tab
    from virtos_ui.results_spine import render_results_spine
    from virtos_ui.powerflow import render_powerflow_diagram
    from virtos_ui.diagnostics import render_diagnostics
    from virtos_engine.core import run_engine
    return {
        "render_topology_and_columns": render_topology_and_columns,
        "render_library_tab": render_library_tab,
        "render_results_spine": render_results_spine,
        "render_powerflow_diagram": render_powerflow_diagram,
        "render_diagnostics": render_diagnostics,
        "run_engine": run_engine,
    }

def _init_state():
    defaults = {
        "applied": False,
        "inputs": {},
        "results": None,
        "active_tab": "Simulator",
    }
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)

# ---------- Sidebar ----------
def render_sidebar():
    with st.sidebar:
        st.markdown("### Run control")
        st.checkbox("Auto-run after Apply", key="autorun", value=True)
        if st.button("Apply & Run", type="primary"):
            st.session_state.applied = True
        st.divider()
        st.markdown("Library")
        st.caption("SKUs • costs • limits")

# ---------- Main ----------
def main():
    _init_state()
    render_sidebar()

    tabs = st.tabs(["Simulator", "Library", "Diagnostics"])
    imports = _lazy_imports()

    # --- Simulator ---
    with tabs[0]:
        st.markdown("# Virtos Site Simulator")
        st.caption(
            "Physics-first: demand → constraints → power flows → service → costs."
        )

        # Power-flow diagram (lightweight; no engine)
        imports["render_powerflow_diagram"]()

        # Multi-column expandable dashboard (Utility → Grid → PCS → Battery → Charge Array → Dispensers → Revenue → Vehicles)
        inputs = imports["render_topology_and_columns"]()
        st.session_state.inputs = inputs

        # Results spine (always renders, empty until run)
        imports["render_results_spine"](st.session_state.get("results"))

        # Run engine only after Apply (or autorun)
        if st.session_state.applied or st.session_state.get("autorun"):
            with st.spinner("Running simulation…"):
                results = imports["run_engine"](st.session_state.inputs)
                st.session_state.results = results
                st.session_state.applied = False

    # --- Library ---
    with tabs[1]:
        imports["render_library_tab"]()

    # --- Diagnostics ---
    with tabs[2]:
        imports["render_diagnostics"]()

# ---------- Entry ----------
if __name__ == "__main__":
    main()
