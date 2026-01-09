import streamlit as st

def render_powerflow_strip(grid_kw: float, pcs_kw: float, batt_kw: float, batt_kwh: float, array_kw: float, disp_kw: float, binding: list[str]):
    st.markdown("#### Power flow (v1)")
    cols = st.columns(6, gap="small")
    cols[0].markdown(f"**Grid**\n\n{grid_kw:.0f} kW")
    cols[1].markdown(f"**PCS**\n\n{pcs_kw:.0f} kW")
    cols[2].markdown(f"**Battery**\n\n{batt_kw:.0f} kW\n\n{batt_kwh:.0f} kWh")
    cols[3].markdown(f"**Charge Array**\n\n{array_kw:.0f} kW")
    cols[4].markdown(f"**Dispensers**\n\n{disp_kw:.0f} kW")
    cols[5].markdown("**Binding constraints**\n\n" + ("\n".join(binding) if binding else "None"))
