import streamlit as st
import importlib

CHECKS = [
  ("virtos_ui.layout", "render_topology_and_columns"),
  ("virtos_ui.powerflow", "render_powerflow_diagram"),
  ("virtos_ui.library", "render_library_tab"),
  ("virtos_engine.core", "run_engine"),
]

def render_diagnostics_tab():
    st.subheader("Import resolution report")
    rows = []
    for mod, attr in CHECKS:
        try:
            m = importlib.import_module(mod)
            ok = hasattr(m, attr)
            rows.append({"module": mod, "attr": attr, "status": "OK" if ok else "MISSING_ATTR"})
        except Exception as e:
            rows.append({"module": mod, "attr": attr, "status": f"IMPORT_FAIL: {e.__class__.__name__}: {e}"})
    st.dataframe(rows, width="stretch", hide_index=True)

    st.subheader("Last run (engine outputs)")
    res = st.session_state.get("last_result")
    if not res:
        st.info("No engine run yet.")
        return
    st.json({
        "constraints": res.get("constraints"),
        "binding_constraints": res.get("binding_constraints"),
        "summary": res.get("summary"),
    }, expanded=False)
