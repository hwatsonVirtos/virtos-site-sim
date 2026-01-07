import streamlit as st

from virtos_ui.inputs import build_site_from_sidebar
from virtos_ui.charts import line_chart
from virtos_ui.summaries import render_metrics, render_costs, render_sanity_warnings
from virtos_ui.explain_ui import render_explain
from virtos_ui.library_ui import render_library_tab

from virtos_engine.library import load_library, apply_library_to_schemas
from virtos_engine.core import simulate_virtos, simulate_grid_only, simulate_ac_coupled


st.set_page_config(page_title="Virtos Site Simulator (UI Batch 2.1)", layout="wide")
st.title("Virtos Site Simulator (UI Batch 2.1)")
st.caption("Internal v1 workbench. Physics-first: power flows → service → costs. Libraries and tariffs are simplified placeholders.")

# Load component library (editable via Library tab) and apply to in-memory schemas
_payload, _lib_hash = load_library()
apply_library_to_schemas(_payload)
st.sidebar.caption(f"Library: {_lib_hash}")

site = build_site_from_sidebar()

tabs = st.tabs(["Library", "Virtos (DC-coupled, shared PCS)", "Grid-only", "AC-coupled BESS", "Compare"])

with tabs[0]:
    render_library_tab()

with tabs[1]:
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

    res = simulate_virtos(site)
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
    from virtos_engine.explain import topology_text, constraint_stack, power_flow_ledger, binding_constraint_hint
    st.code(topology_text("virtos"))
    st.write("Constraints")
    st.write(constraint_stack(site, "virtos"))
    ledger = power_flow_ledger(res, site.demand.dt_hours)
    st.write("Power flow ledger (first 20 steps)")
    st.table(ledger[:20])
    st.info(binding_constraint_hint(ledger))


with tabs[2]:
    res = simulate_grid_only(site)
    st.subheader("Power flows")
    st.pyplot(line_chart("Grid import (kW)", res["timeseries"]["grid_import_kw_ts"], ylabel="kW"))
    st.subheader("Service")
    render_metrics(res["metrics"])

    render_sanity_warnings(res, site, architecture="grid_only")
    st.subheader("Costs (Tariff v1)")
    render_costs(res["costs"], site)

    st.subheader("Explain")
    render_explain(site, "grid", res, max_rows=20)

    st.subheader("Explain")
    from virtos_engine.explain import topology_text, constraint_stack, power_flow_ledger, binding_constraint_hint
    st.code(topology_text("virtos"))
    st.write("Constraints")
    st.write(constraint_stack(site, "virtos"))
    ledger = power_flow_ledger(res, site.demand.dt_hours)
    st.write("Power flow ledger (first 20 steps)")
    st.table(ledger[:20])
    st.info(binding_constraint_hint(ledger))


with tabs[3]:
    res = simulate_ac_coupled(site)
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

    st.subheader("Explain")
    from virtos_engine.explain import topology_text, constraint_stack, power_flow_ledger, binding_constraint_hint
    st.code(topology_text("virtos"))
    st.write("Constraints")
    st.write(constraint_stack(site, "virtos"))
    ledger = power_flow_ledger(res, site.demand.dt_hours)
    st.write("Power flow ledger (first 20 steps)")
    st.table(ledger[:20])
    st.info(binding_constraint_hint(ledger))


with tabs[4]:
    st.subheader("Compare architectures")
    from virtos_engine.explain import value_prop_delta
    v = simulate_virtos(site)
    g = simulate_grid_only(site)
    a = simulate_ac_coupled(site)

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