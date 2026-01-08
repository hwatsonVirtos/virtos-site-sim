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
    """Lightweight SVG diagram (clear flow + key caps)."""
    grid = _fmt(vars.get("grid_connection_kw"), " kW")
    pcs  = _fmt(vars.get("pcs_shared_kw"), " kW")
    ss   = _fmt(vars.get("super_strings"), "")
    dcdc = _fmt(vars.get("dc_dc_modules_per_string"), "×100kW")

    svg = f"""
    <svg width="100%" height="120" viewBox="0 0 1100 120" xmlns="http://www.w3.org/2000/svg">
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

      <rect class="box" x="10" y="20" width="190" height="80"/>
      <text class="title" x="30" y="52">Utility / Grid</text>
      <text class="sub" x="30" y="76">Connection cap: {grid}</text>

      <line class="arrow" x1="200" y1="60" x2="330" y2="60"/>

      <rect class="box" x="340" y="20" width="190" height="80"/>
      <text class="title" x="360" y="52">PCS</text>
      <text class="sub" x="360" y="76">Shared cap: {pcs}</text>

      <line class="arrow" x1="530" y1="60" x2="660" y2="60"/>

      <rect class="box" x="670" y="20" width="190" height="80"/>
      <text class="title" x="690" y="52">Charge Array</text>
      <text class="sub" x="690" y="76">Super-strings: {ss}</text>

      <line class="arrow" x1="860" y1="60" x2="990" y2="60"/>

      <rect class="box" x="1000" y="20" width="90" height="80"/>
      <text class="title" x="1010" y="52">Disp.</text>
      <text class="sub" x="1010" y="76">{dcdc}</text>

      <line class="arrow accent" x1="435" y1="100" x2="435" y2="112"/>
      <line class="arrow accent" x1="435" y1="112" x2="530" y2="112"/>
      <rect class="box" x="540" y="86" width="170" height="28"/>
      <text class="sub" x="555" y="106">Battery (next)</text>
    </svg>
    """
    st.markdown(svg, unsafe_allow_html=True)
