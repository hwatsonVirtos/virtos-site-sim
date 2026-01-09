import streamlit as st
from .theme import VIRTOS_GREEN, BORDER, TEXT_DIM

def _fmt(v, unit=""):
    try:
        if v is None:
            return "—"
        return f"{float(v):,.0f}{unit}"
    except Exception:
        return str(v)

def render_powerflow_diagram(vars: dict):
    """Lightweight SVG diagram (T-shape) with explicit caps.

    Purpose: a visual anchor + a quick, explainable read of binding limits.
    Non-goal: pixel-perfect icons (v1).
    """
    arch = str(vars.get("architecture", "Virtos (DC-coupled)"))
    grid = _fmt(vars.get("grid_connection_kw"), " kW")
    pcs  = _fmt(vars.get("pcs_shared_kw") or vars.get("pcs_cap_kw"), " kW")
    batt_p = _fmt(vars.get("battery_power_kw"), " kW")
    batt_e = _fmt(vars.get("battery_energy_kwh"), " kWh")
    inv = _fmt(vars.get("ac_inverter_kw"), " kW")
    ss   = _fmt(vars.get("super_strings"), "")
    dcdc = _fmt(vars.get("dc_dc_modules_per_string"), " ×100kW")
    imax = _fmt(vars.get("cable_imax_a"), " A")
    v = float(vars.get("vehicle_voltage_v", 800.0) or 800.0)
    try:
        cable_kw = float(vars.get("cable_imax_a", 0.0) or 0.0) * v / 1000.0
    except Exception:
        cable_kw = 0.0
    cable = _fmt(cable_kw, " kW")
    disp = _fmt(vars.get("dispenser_max_kw"), " kW")

    svg = f"""
    <svg width="100%" height="170" viewBox="0 0 1200 170" xmlns="http://www.w3.org/2000/svg">
      <style>
        .box {{ fill: rgba(255,255,255,0.03); stroke: {BORDER}; stroke-width: 1; rx: 10; }}
        .title {{ fill: #EDEFF2; font: 600 14px sans-serif; }}
        .sub {{ fill: {TEXT_DIM}; font: 12px sans-serif; }}
        .arrow {{ stroke: rgba(237,239,242,0.45); stroke-width: 2; marker-end: url(#m); }}
        .accent {{ stroke: {VIRTOS_GREEN}; stroke-width: 2; }}
      </style>
      <defs>
        <marker id="m" markerWidth="10" markerHeight="10" refX="6" refY="3" orient="auto">
          <path d="M0,0 L0,6 L6,3 z" fill="rgba(237,239,242,0.45)" />
        </marker>
      </defs>

      <rect class="box" x="10" y="20" width="200" height="95"/>
      <text class="title" x="28" y="52">Grid</text>
      <text class="sub" x="28" y="76">Cap: {grid}</text>
      <text class="sub" x="28" y="98">Arch: {arch}</text>

      <line class="arrow" x1="210" y1="67" x2="335" y2="67"/>

      <rect class="box" x="345" y="20" width="200" height="95"/>
      <text class="title" x="363" y="52">PCS</text>
      <text class="sub" x="363" y="76">Cap: {pcs}</text>
      <text class="sub" x="363" y="98">(site-level)</text>

      <line class="arrow" x1="545" y1="67" x2="670" y2="67"/>

      <rect class="box" x="675" y="20" width="220" height="95"/>
      <text class="title" x="693" y="52">Charge Array</text>
      <text class="sub" x="693" y="76">Super-strings: {ss}</text>
      <text class="sub" x="693" y="98">DC-DC / string: {dcdc}</text>

      <line class="arrow" x1="895" y1="67" x2="1010" y2="67"/>

      <rect class="box" x="1015" y="20" width="175" height="95"/>
      <text class="title" x="1033" y="52">Dispensers</text>
      <text class="sub" x="1033" y="76">Cable cap: {cable} ({imax})</text>
      <text class="sub" x="1033" y="98">Dispenser cap: {disp}</text>

      <!-- Battery branch (T-stem) -->
      <line class="arrow accent" x1="445" y1="115" x2="445" y2="148"/>
      <line class="arrow accent" x1="445" y1="148" x2="675" y2="148"/>
      <rect class="box" x="485" y="128" width="180" height="32"/>
      <text class="sub" x="500" y="149">Battery: {batt_p} / {batt_e}</text>

      <!-- AC-coupled inverter note -->
      <rect class="box" x="10" y="128" width="200" height="32"/>
      <text class="sub" x="28" y="149">AC inverter (AC-cpl): {inv}</text>
    </svg>
    """
    st.markdown(svg, unsafe_allow_html=True)
