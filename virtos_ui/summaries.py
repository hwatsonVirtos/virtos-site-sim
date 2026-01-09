import streamlit as st

def render_metrics(metrics: dict):
    c1, c2, c3 = st.columns(3)
    c1.metric("Time satisfied (%)", f"{metrics['time_satisfied_pct']:.1f}")
    c2.metric("Power satisfied (%)", f"{metrics['power_satisfied_pct']:.1f}")
    c3.metric("Energy not served (kWh)", f"{metrics['energy_not_served_kwh']:.1f}")

def render_costs(costs: dict):
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Energy (kWh)", f"{costs['energy_kwh']:.1f}")
    c2.metric("Energy cost ($)", f"{costs['energy_cost_$']:.2f}")
    c3.metric("Demand cost ($/mo)", f"{costs['demand_cost_$']:.2f}")
    c4.metric("Peak kW", f"{costs['peak_kw']:.1f}")

    st.metric("Total ($/mo)", f"{costs['total_cost_$']:.2f}")
