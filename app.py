# app.py — Streamlit Cloud hardened entrypoint (import-resilient)
import importlib
import traceback
import streamlit as st

st.set_page_config(page_title="Virtos Site Simulator", layout="wide", initial_sidebar_state="expanded")


def _init_state():
    st.session_state.setdefault("applied", False)
    st.session_state.setdefault("autorun", True)
    st.session_state.setdefault("inputs", {})
    st.session_state.setdefault("results", None)


def _try_import(module_name: str, attr: str | None = None):
    """
    Returns (obj, err_str). If attr is None, obj is module.
    """
    try:
        mod = importlib.import_module(module_name)
        if attr is None:
            return mod, None
        if not hasattr(mod, attr):
            return None, f"{module_name}.{attr} not found"
        return getattr(mod, attr), None
    except Exception as e:
        return None, f"{module_name} import failed: {e.__class__.__name__}: {e}"


def _resolve_ui_entrypoints():
    """
    Attempts to resolve UI functions from whatever your repo currently provides.
    We accept multiple legacy names to avoid breaking boot.
    """
    report = []

    # layout / inputs renderer (multiple possible names)
    candidates_layout = [
        ("virtos_ui.layout", "render_topology_and_columns"),
        ("virtos_ui.layout", "render_site_configuration"),
        ("virtos_ui.layout", "render_inputs"),
        ("virtos_ui.layout", "render_layout"),
        ("virtos_ui", "render_topology_and_columns"),
    ]
    render_inputs = None
    for m, a in candidates_layout:
        obj, err = _try_import(m, a)
        if obj:
            render_inputs = obj
            report.append(f"✅ Inputs renderer: {m}.{a}")
            break
        report.append(f"❌ Inputs renderer: {m}.{a} — {err}")

    # powerflow diagram
    powerflow_candidates = [
        ("virtos_ui.powerflow", "render_powerflow_diagram"),
        ("virtos_ui.powerflow", "render_powerflow"),
        ("virtos_ui.powerflow", "render_diagram"),
    ]
    render_powerflow = None
    for m, a in powerflow_candidates:
        obj, err = _try_import(m, a)
        if obj:
            render_powerflow = obj
            report.append(f"✅ Powerflow: {m}.{a}")
            break
        report.append(f"❌ Powerflow: {m}.{a} — {err}")

    # results
    results_candidates = [
        ("virtos_ui.results_spine", "render_results_spine"),
        ("virtos_ui.results", "render_results"),
        ("virtos_ui.results", "render_results_spine"),
    ]
    render_results = None
    for m, a in results_candidates:
        obj, err = _try_import(m, a)
        if obj:
            render_results = obj
            report.append(f"✅ Results: {m}.{a}")
            break
        report.append(f"❌ Results: {m}.{a} — {err}")

    # library tab
    library_candidates = [
        ("virtos_ui.library", "render_library_tab"),
        ("virtos_ui.library", "render_library"),
    ]
    render_library = None
    for m, a in library_candidates:
        obj, err = _try_import(m, a)
        if obj:
            render_library = obj
            report.append(f"✅ Library: {m}.{a}")
            break
        report.append(f"❌ Library: {m}.{a} — {err}")

    # diagnostics tab
    diag_candidates = [
        ("virtos_ui.diagnostics", "render_diagnostics"),
        ("virtos_ui.diagnostics", "render_diag"),
    ]
    render_diag = None
    for m, a in diag_candidates:
        obj, err = _try_import(m, a)
        if obj:
            render_diag = obj
            report.append(f"✅ Diagnostics: {m}.{a}")
            break
        report.append(f"❌ Diagnostics: {m}.{a} — {err}")

    # engine
    engine_candidates = [
        ("virtos_engine.core", "run_engine"),
        ("virtos_engine.core", "run"),
        ("virtos_engine", "run_engine"),
    ]
    run_engine = None
    for m, a in engine_candidates:
        obj, err = _try_import(m, a)
        if obj:
            run_engine = obj
            report.append(f"✅ Engine: {m}.{a}")
            break
        report.append(f"❌ Engine: {m}.{a} — {err}")

    return {
        "render_inputs": render_inputs,
        "render_powerflow": render_powerflow,
        "render_results": render_results,
        "render_library": render_library,
        "render_diag": render_diag,
        "run_engine": run_engine,
        "report": report,
    }


def _fallback_inputs_ui():
    st.warning("UI module missing or renamed. Showing fallback inputs so app remains usable.")
    c1, c2, c3 = st.columns([1, 1, 1])
    with c1:
        grid_kw = st.number_input("Grid connection cap (kW)", min_value=0.0, value=1000.0, step=50.0)
    with c2:
        pcs_kw = st.number_input("PCS shared cap (kW)", min_value=0.0, value=300.0, step=10.0)
    with c3:
        modules = st.number_input("DC-DC modules per string (100 kW ea)", min_value=0, value=10, step=1)
    return {
        "grid_connection_kw": float(grid_kw),
        "pcs_shared_kw": float(pcs_kw),
        "dc_dc_modules_per_string": int(modules),
    }


def render_sidebar():
    with st.sidebar:
        st.markdown("### Run control")
        st.checkbox("Auto-run after Apply", key="autorun")
        if st.button("Apply & Run", type="primary"):
            st.session_state.applied = True
        st.divider()
        st.markdown("Library")
        st.caption("SKUs • costs • limits")


def main():
    _init_state()
    render_sidebar()

    resolved = _resolve_ui_entrypoints()

    # Tabs always exist even if modules missing
    t_sim, t_lib, t_diag = st.tabs(["Simulator", "Library", "Diagnostics"])

    with t_sim:
        st.markdown("# Virtos Site Simulator")

        # Powerflow (optional)
        if resolved["render_powerflow"]:
            try:
                resolved["render_powerflow"]()
            except Exception:
                st.error("Powerflow renderer crashed (non-fatal).")
                st.code(traceback.format_exc())
        else:
            st.info("Powerflow renderer not found yet.")

        # Inputs UI
        if resolved["render_inputs"]:
            try:
                inputs = resolved["render_inputs"]()
            except Exception:
                st.error("Inputs renderer crashed; falling back.")
                st.code(traceback.format_exc())
                inputs = _fallback_inputs_ui()
        else:
            inputs = _fallback_inputs_ui()

        st.session_state.inputs = inputs

        # Run engine only when applied/autorun
        if resolved["run_engine"] and (st.session_state.applied or st.session_state.autorun):
            with st.spinner("Running simulation…"):
                try:
                    st.session_state.results = resolved["run_engine"](st.session_state.inputs)
                except Exception:
                    st.error("Engine crashed.")
                    st.code(traceback.format_exc())
            st.session_state.applied = False

        # Results
        if resolved["render_results"]:
            try:
                resolved["render_results"](st.session_state.get("results"))
            except Exception:
                st.error("Results renderer crashed (non-fatal).")
                st.code(traceback.format_exc())
        else:
            st.subheader("Results")
            st.json(st.session_state.get("results") or {"status": "no results yet"})

    with t_lib:
        if resolved["render_library"]:
            try:
                resolved["render_library"]()
            except Exception:
                st.error("Library renderer crashed.")
                st.code(traceback.format_exc())
        else:
            st.info("Library UI not wired yet (module missing/renamed).")

    with t_diag:
        st.subheader("Import resolution report")
        st.code("\n".join(resolved["report"]))
        if resolved["render_diag"]:
            try:
                resolved["render_diag"]()
            except Exception:
                st.error("Diagnostics renderer crashed.")
                st.code(traceback.format_exc())


if __name__ == "__main__":
    main()
