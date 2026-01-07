import json
import warnings
from dataclasses import asdict
from typing import Literal, Dict, Any

import streamlit as st

from virtos_ui.topology_ui import render_site_inputs_form
from virtos_ui.charts import line_chart
from virtos_ui.summaries import render_metrics, render_costs, render_sanity_warnings
from virtos_ui.explain_ui import render_explain
from virtos_ui.library_ui import render_library_tab

from virtos_engine.library import load_library, apply_library_to_schemas
from virtos_engine.core import simulate_virtos, simulate_grid_only, simulate_ac_coupled
from virtos_engine.schemas import SiteSpec, DemandProfile, TariffSpec


st.set_page_config(page_title="Virtos Site Simulator (UI Batch 2.2)", layout="wide")

# Streamlit Cloud can emit extremely noisy deprecation warnings in some
# environments (notably around `use_container_width`). These warnings are UI-only
# and do not affect simulator physics. If they spam logs, they can materially
# slow provisioning and make debugging impossible.
warnings.filterwarnings(
    "ignore",
    message=r"Please replace `use_container_width` with `width`\.",
)
st.title("Virtos Site Simulator (UI Batch 2.2)")
st.caption("Internal v1 workbench. Physics-first: power flows → service → costs. Libraries and tariffs are simplified placeholders.")

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

# Main-page inputs (under topology). Values update only on submit (v1) to avoid rerun storms.
with st.form("site_form", clear_on_submit=False):
    site = render_site_inputs_form(default_n_strings=2)
    applied = st.form_submit_button("Apply inputs", type="primary")

site_fp = _fingerprint_site(site)

st.sidebar.divider()
st.sidebar.subheader("Run control")

auto_run = st.sidebar.checkbox("Auto-run after Apply", value=True, help="Since inputs only change on Apply, this is safe.")
run_clicked = st.sidebar.button("Run / refresh results", type="primary", help="Runs simulation for the currently applied inputs.")

if "last_run_fp" not in st.session_state:
    st.session_state["last_run_fp"] = None

# Auto-run triggers whenever inputs are applied (site_fp changes only on Apply).
if auto_run and (st.session_state.get("last_run_fp") != site_fp):
    st.session_state["last_run_fp"] = site_fp
elif run_clicked:
    st.session_state["last_run_fp"] = site_fp

ready_to_run = (st.session_state.get("last_run_fp") == site_fp)

tabs = st.tabs(["Library", "Virtos (DC-coupled, shared PCS)", "Grid-only", "AC-coupled BESS", "Compare"])

with tabs[0]:
    render_library_tab()

with tabs[1]:
    if not ready_to_run:
        st.info("Inputs changed. Press **Run / refresh results** in the sidebar (or enable Auto-run).")
        st.stop()
    st.subheader("Site overview")
    st.write({
        "super-strings": site.n_superstrings,
        "grid connection cap (kW)": site.grid_connection_kw,
        "shared PCS cap (kW)": site.shared_pcs_kw,
        "PCS SKU": site.pcs_sku,
        "Battery SKU": site.battery_sku,
        "DC-DC modules/string": site.dcdc_modules,
        "Cable type": site.cable_type,
        "allow grid charge": site.allow_grid_charge,
        "grid charge target SOC (%)": site.grid_charge_target_soc_pct,
        "grid charge power (kW)": site.grid_charge_power_kw,
        "timestep (min)": site.demand.timestep_minutes,
        "utilisation curve": site.demand.utilisation_curve,
    })

    res = _simulate_cached(site_fp, "virtos")
    ts = res["timeseries"]

    st.subheader("Power flows")
    st.pyplot(line_chart("Grid import (kW)", ts["grid_import_kw_ts"], ylabel="kW"))
    st.pyplot(line_chart("PCS used total (kW)", ts["pcs_used_kw_ts"], ylabel="kW"))

    n = len(site.demand.utilisation_curve)
    batt_dis_sum = [0.0]*n
    batt_chg_sum = [0.0]*n
    soc_sum = [0.0]*n
    for s in res["state"].values():
        for i, v in enumerate(s["battery_discharge_kw_ts"]):
            batt_dis_sum[i] += v
        for i, v in enumerate(s["battery_charge_kw_ts"]):
            batt_chg_sum[i] += v
        for i, v in enumerate(s["soc_ts_kwh"]):
            soc_sum[i] += v

    st.pyplot(line_chart("Battery discharge total (kW)", batt_dis_sum, ylabel="kW"))
    st.pyplot(line_chart("Battery charge total (kW)", batt_chg_sum, ylabel="kW"))
    st.pyplot(line_chart("SOC total (kWh)", soc_sum, ylabel="kWh"))

    st.subheader("Service")
    render_metrics(res["metrics"])

    render_sanity_warnings(res, site, architecture="virtos")

    st.subheader("Costs (Tariff v1)")
    render_costs(res["costs"], site)

    st.subheader("Explain")
    render_explain(site, "virtos", res, max_rows=20)


with tabs[2]:
    if not ready_to_run:
        st.info("Inputs changed. Press **Run / refresh results** in the sidebar (or enable Auto-run).")
        st.stop()
    res = _simulate_cached(site_fp, "grid_only")
    st.subheader("Power flows")
    st.pyplot(line_chart("Grid import (kW)", res["timeseries"]["grid_import_kw_ts"], ylabel="kW"))
    st.subheader("Service")
    render_metrics(res["metrics"])

    render_sanity_warnings(res, site, architecture="grid_only")
    st.subheader("Costs (Tariff v1)")
    render_costs(res["costs"], site)

    st.subheader("Explain")
    render_explain(site, "grid", res, max_rows=20)


with tabs[3]:
    if not ready_to_run:
        st.info("Inputs changed. Press **Run / refresh results** in the sidebar (or enable Auto-run).")
        st.stop()
    res = _simulate_cached(site_fp, "ac_coupled")
    st.subheader("Power flows")
    st.pyplot(line_chart("Grid import (kW)", res["timeseries"]["grid_import_kw_ts"], ylabel="kW"))
    st.pyplot(line_chart("AC BESS discharge (kW)", res["timeseries"]["bess_discharge_kw_ts"], ylabel="kW"))
    st.subheader("Service")
    render_metrics(res["metrics"])

    render_sanity_warnings(res, site, architecture="ac_coupled")
    st.subheader("Costs (Tariff v1)")
    render_costs(res["costs"], site)

    st.subheader("Explain")
    render_explain(site, "ac", res, max_rows=20)


with tabs[4]:
    st.subheader("Compare architectures")
    from virtos_engine.explain import value_prop_delta
    if not ready_to_run:
        st.info("Inputs changed. Press **Run / refresh results** in the sidebar (or enable Auto-run).")
        st.stop()

    v = _simulate_cached(site_fp, "virtos")
    g = _simulate_cached(site_fp, "grid_only")
    a = _simulate_cached(site_fp, "ac_coupled")

    rows = [
        ("Virtos", v["costs"]["total_cost_$"], v["costs"]["peak_kw"], v["metrics"]["power_satisfied_pct"]),
        ("Grid-only", g["costs"]["total_cost_$"], g["costs"]["peak_kw"], g["metrics"]["power_satisfied_pct"]),
        ("AC-coupled", a["costs"]["total_cost_$"], a["costs"]["peak_kw"], a["metrics"]["power_satisfied_pct"]),
    ]
    d_v_g = value_prop_delta(v["costs"], v["metrics"], g["costs"], g["metrics"])
    d_v_a = value_prop_delta(v["costs"], v["metrics"], a["costs"], a["metrics"])
    st.subheader("Virtos delta vs Grid-only")
    st.write(d_v_g)
    st.subheader("Virtos delta vs AC-coupled")
    st.write(d_v_a)

    st.table({
        "Architecture": [r[0] for r in rows],
        "Total $/mo": [round(r[1], 2) for r in rows],
        "Peak kW": [round(r[2], 1) for r in rows],
        "Power satisfied (%)": [round(r[3], 1) for r in rows],
    })