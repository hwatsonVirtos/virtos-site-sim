import streamlit as st
from virtos_engine.explain import topology_text, constraint_stack, power_flow_ledger, binding_constraint_hint, binding_summary

def render_explain(site, arch: str, sim_result: dict, max_rows: int = 20):
    st.code(topology_text(arch))
    st.write("Constraints")
    st.write(constraint_stack(site, arch))

    ledger = power_flow_ledger(sim_result, site.demand.dt_hours)
    st.write(f"Power flow ledger (first {max_rows} steps)")
    st.table(ledger[:max_rows])

    st.info(binding_constraint_hint(ledger))
    st.write("Peak summary")
    st.write(binding_summary(ledger))
