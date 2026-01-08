import json
import warnings
from dataclasses import asdict
from typing import Literal, Dict, Any

import streamlit as st

from virtos_ui.topology_ui import render_site_inputs_dashboard
from virtos_ui.charts import line_chart
from virtos_ui.summaries import render_metrics, render_costs, render_sanity_warnings
from virtos_ui.explain_ui import render_explain
from virtos_ui.library_ui import render_library_tab

from virtos_engine.library import load_library, apply_library_to_schemas
from virtos_engine.core import simulate_virtos, simulate_grid_only, simulate_ac_coupled
from virtos_engine.schemas import SiteSpec, DemandProfile, TariffSpec


st.set_page_config(page_title="Virtos Site Simulator", layout="wide")

# --- Virtos theme hard-override (Streamlit Cloud sometimes ignores config.toml on partial uploads)
VIRTOS_GREEN = "#84BD00"  # Pantone 376C approx
st.markdown(f"""
<style>
:root {{ --primary-color: {VIRTOS_GREEN}; }}
.stButton>button {{ background-color: {VIRTOS_GREEN} !important; border-color: {VIRTOS_GREEN} !important; }}
.stButton>button:hover {{ filter: brightness(0.95); }}
/* Slider track + fill (best-effort; Streamlit/BaseWeb DOM may change) */
div[data-baseweb="slider"] div[role="slider"] {{ background-color: {VIRTOS_GREEN} !important; }}
div[data-baseweb="slider"] div[aria-valuenow] {{ background-color: {VIRTOS_GREEN} !important; }}
</style>
""", unsafe_allow_html=True)

# Streamlit Cloud can emit extremely noisy deprecation warnings in some
# environments (notably around `use_container_width`). These warnings are UI-only
# and do not affect simulator physics. If they spam logs, they can materially
# slow provisioning and make debugging impossible.
warnings.filterwarnings(
    "ignore",
    message=r"Please replace `use_container_width` with `width`\.",
)
st.title("Virtos Site Simulator")
st.caption("Internal v1 workbench. Physics-first: demand → constraints → power flows → service → costs.")

ARCH = Literal["virtos", "grid_only", "ac_coupled"]

def _fingerprint_site(site: SiteSpec) -> str:
    # Canonical: explicit, stable fingerprint for caching and explicit run gating.
    return json.dumps(asdict(site), sort_keys=True, separators=(",", ":"))

def _site_from_dict(d: Dict[str, Any]) -> SiteSpec:
    demand = d.get("demand") or {}
    tariff = d.get("tariff") or {}
    return SiteSpec(
        name=d.get("name", "Site"),
        demand=DemandProfile(**demand),
        n_superstrings=int(d.get("n_superstrings", 2)),
        grid_connection_kw=float(d.get("grid_connection_kw", 1000.0)),
        shared_pcs_kw=float(d.get("shared_pcs_kw", 300.0)),
        pcs_sku=str(d.get("pcs_sku", "PCS_500")),
        battery_sku=str(d.get("battery_sku", "BATT_500_1000")),
        dcdc_modules=int(d.get("dcdc_modules", 10)),
        cable_type=str(d.get("cable_type", "CABLE_600A")),
        allow_grid_charge=bool(d.get("allow_grid_charge", False)),
        grid_charge_target_soc_pct=float(d.get("grid_charge_target_soc_pct", 100.0)),
        grid_charge_power_kw=float(d.get("grid_charge_power_kw", 200.0)),
        ac_bess_power_kw=float(d.get("ac_bess_power_kw", 0.0)),
        ac_bess_energy_kwh=float(d.get("ac_bess_energy_kwh", 0.0)),
        tariff=TariffSpec(**tariff),
    )

@st.cache_data(show_spinner=False)
def _simulate_cached(site_fingerprint: str, arch: ARCH) -> Dict[str, Any]:
    site = _site_from_dict(json.loads(site_fingerprint))
    if arch == "virtos":
        return simulate_virtos(site)
    if arch == "grid_only":
        return simulate_grid_only(site)
    return simulate_ac_coupled(site)


# Load component library (editable via Library tab) and apply to in-memory schemas
_payload, _lib_hash = load_library()
apply_library_to_schemas(_payload)
st.sidebar.caption(f"Library: {_lib_hash}")

# Main dashboard inputs (Variant B). Values update only on submit (v1) to avoid rerun storms.
with st.form("site_form", clear_on_submit=False):
    site = render_site_inputs_dashboard(default_n_strings=2)
    applied = st.form_submit_button("Apply & Run", type="primary")

site_fp = _fingerprint_site(site)

st.sidebar.divider()
st.sidebar.subheader("Run control")

auto_run = st.sidebar.checkbox("Auto-run after Apply", value=True, help="Inputs only change on Apply, so this is safe.")
run_clicked = st.sidebar.button("Run / refresh results", type="primary")

if "last_run_fp" not in st.session_state:
    st.session_state["last_run_fp"] = None

# Auto-run triggers whenever inputs are applied (site_fp changes only on Apply).
if auto_run and (st.session_state.get("last_run_fp") != site_fp):
    st.session_state["last_run_fp"] = site_fp
elif run_clicked:
    st.session_state["last_run_fp"] = site_fp

ready_to_run = (st.session_state.get("last_run_fp") == site_fp)

st.divider()

# Drill-down: component library (keep out of main render path)
with st.expander("Component library (edit SKUs, costs, limits)", expanded=False):
    render_library_tab()

st.subheader("Results")
results_tabs = st.tabs(["Virtos", "Grid-only", "AC-coupled", "Compare"])

def _needs_run():
    if not ready_to_run:
        st.info("Inputs changed. Press **Run / refresh results** in the sidebar (or enable Auto-run).")
        st.stop()

with results_tabs[0]:
    _needs_run()
    res = _simulate_cached(site_fp, "virtos")
    render_metrics(res["metrics"])
    render_costs(res["costs"], site)
    render_sanity_warnings(res, site, architecture="virtos")
    with st.expander("Power flow charts", expanded=False):
        ts = res["timeseries"]
        st.pyplot(line_chart("Grid import (kW)", ts["grid_import_kw_ts"], ylabel="kW"))
        st.pyplot(line_chart("PCS used total (kW)", ts["pcs_used_kw_ts"], ylabel="kW"))
    with st.expander("Explain", expanded=False):
        render_explain(site, "virtos", res, max_rows=25)

with results_tabs[1]:
    _needs_run()
    res = _simulate_cached(site_fp, "grid_only")
    render_metrics(res["metrics"])
    render_costs(res["costs"], site)
    render_sanity_warnings(res, site, architecture="grid_only")
    with st.expander("Power flow charts", expanded=False):
        st.pyplot(line_chart("Grid import (kW)", res["timeseries"]["grid_import_kw_ts"], ylabel="kW"))
    with st.expander("Explain", expanded=False):
        render_explain(site, "grid", res, max_rows=25)

with results_tabs[2]:
    _needs_run()
    res = _simulate_cached(site_fp, "ac_coupled")
    render_metrics(res["metrics"])
    render_costs(res["costs"], site)
    render_sanity_warnings(res, site, architecture="ac_coupled")
    with st.expander("Power flow charts", expanded=False):
        st.pyplot(line_chart("Grid import (kW)", res["timeseries"]["grid_import_kw_ts"], ylabel="kW"))
        st.pyplot(line_chart("AC BESS discharge (kW)", res["timeseries"]["bess_discharge_kw_ts"], ylabel="kW"))
    with st.expander("Explain", expanded=False):
        render_explain(site, "ac", res, max_rows=25)

with results_tabs[3]:
    _needs_run()
    from virtos_engine.explain import value_prop_delta
    v = _simulate_cached(site_fp, "virtos")
    g = _simulate_cached(site_fp, "grid_only")
    a = _simulate_cached(site_fp, "ac_coupled")

    rows = [
        ("Virtos", v["costs"]["total_cost_$"], v["costs"]["peak_kw"], v["metrics"]["power_satisfied_pct"]),
        ("Grid-only", g["costs"]["total_cost_$"], g["costs"]["peak_kw"], g["metrics"]["power_satisfied_pct"]),
        ("AC-coupled", a["costs"]["total_cost_$"], a["costs"]["peak_kw"], a["metrics"]["power_satisfied_pct"]),
    ]

    st.table({
        "Architecture": [r[0] for r in rows],
        "Total $/mo": [round(r[1], 2) for r in rows],
        "Peak kW": [round(r[2], 1) for r in rows],
        "Power satisfied (%)": [round(r[3], 1) for r in rows],
    })

    st.subheader("Virtos delta vs Grid-only")
    st.write(value_prop_delta(v["costs"], v["metrics"], g["costs"], g["metrics"]))
    st.subheader("Virtos delta vs AC-coupled")
    st.write(value_prop_delta(v["costs"], v["metrics"], a["costs"], a["metrics"]))