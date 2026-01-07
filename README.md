# Virtos Site Simulator – UI Batch 2.1 (Fixes 1/2/3)

Fixes:
1) Grid-only respects **grid_connection_kw** and charger-side PCS capacity.
2) AC-coupled is **grid-side BESS behind meter** with explicit inverter power + energy (shared across site).
3) Virtos supports optional **grid charging** of DC-coupled batteries using spare import/PCS headroom.

Still simplified:
- Vehicles fixed at 800 V
- DC-DC module = 100 kW
- No export; efficiencies = 1.0
- Tariff placeholder TOU + demand charge

Run (where Streamlit is available):
streamlit run app.py
