import json
import os
from datetime import datetime

import streamlit as st


LIB_PATH = os.path.join("data", "component_library.json")


def _seed_library() -> dict:
    # v1: ad hoc, single-user. Persisted to local filesystem in the Streamlit container.
    return {
        "meta": {
            "version": "v1",
            "last_saved_utc": None,
            "notes": "Local-only. Use export/import to persist across redeploys.",
        },
        "pcs": [
            {"id": "PCS_500", "rated_kw": 500, "capex_aud": 150000, "opex_aud_per_year": 0, "notes": "Shared PCS"},
            {"id": "PCS_1000", "rated_kw": 1000, "capex_aud": 250000, "opex_aud_per_year": 0, "notes": "Shared PCS"},
        ],
        "batteries": [
            {"id": "BATT_500_1000", "power_kw": 500, "energy_kwh": 1000, "capex_aud": 400000, "opex_aud_per_year": 0, "notes": "DC-coupled"},
        ],
        "inverters": [
            {"id": "INV_500", "rated_kw": 500, "capex_aud": 120000, "opex_aud_per_year": 0, "notes": "AC-coupled"},
        ],
        "dc_dc_modules": [
            {"id": "DCDC_100", "rated_kw": 100, "capex_aud": 12000, "opex_aud_per_year": 0, "notes": "Locked 100 kW/module"},
        ],
        "dispensers": [
            {"id": "HPC_150", "max_kw": 150, "cable_imax_a": 250, "capex_aud": 80000, "opex_aud_per_year": 0, "notes": "Short dwell"},
            {"id": "AC_22", "max_kw": 22, "cable_imax_a": 32, "capex_aud": 6000, "opex_aud_per_year": 0, "notes": "Trickle"},
        ],
        "tariffs": [
            {"id": "DEFAULT", "offpeak_per_kwh": 0.12, "shoulder_per_kwh": 0.20, "peak_per_kwh": 0.35, "demand_charge_per_kw_month": 0.0, "notes": "Placeholder"},
        ],
        "pricing": [
            {"id": "HPC_DEFAULT", "price_per_kwh": 0.65, "price_per_min": 0.0, "notes": "Placeholder"},
        ],
        "vehicles": [
            {"id": "800V_DEFAULT", "voltage_v": 800, "notes": "v1 locked"},
        ],
    }


def _load_library() -> dict:
    if not os.path.exists(LIB_PATH):
        os.makedirs(os.path.dirname(LIB_PATH), exist_ok=True)
        data = _seed_library()
        with open(LIB_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return data
    with open(LIB_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_library(data: dict) -> None:
    data = dict(data)
    meta = dict(data.get("meta", {}))
    meta["last_saved_utc"] = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    data["meta"] = meta
    os.makedirs(os.path.dirname(LIB_PATH), exist_ok=True)
    with open(LIB_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def _editor(label: str, rows: list, help_text: str = "") -> list:
    st.markdown(f"### {label}")
    if help_text:
        st.caption(help_text)
    return st.data_editor(rows, num_rows="dynamic", width="stretch", hide_index=True)


def render_library_tab():
    st.subheader("Component library")
    st.caption("v1 local library. Edit + export/import. Streamlit Cloud may not persist file writes across redeploys, so export regularly.")

    data = _load_library()

    # Export / Import
    c1, c2, c3 = st.columns([1, 1, 2])
    with c1:
        st.download_button(
            "Export library.json",
            data=json.dumps(data, indent=2).encode("utf-8"),
            file_name="component_library.json",
            mime="application/json",
            type="primary",
        )
    with c2:
        upl = st.file_uploader("Import library.json", type=["json"], label_visibility="collapsed")
        if upl is not None:
            try:
                imported = json.loads(upl.read().decode("utf-8"))
                _save_library(imported)
                st.success("Imported and saved.")
                st.rerun()
            except Exception as e:
                st.error(f"Import failed: {e.__class__.__name__}: {e}")
    with c3:
        st.json(data.get("meta", {}), expanded=False)

    tabs = st.tabs(["PCS", "Battery", "Inverter", "DC-DC", "Dispensers", "Tariffs", "Pricing", "Vehicles"])

    with tabs[0]:
        data["pcs"] = _editor("PCS SKUs", data.get("pcs", []), "Include rating, capex, and optional opex.")
    with tabs[1]:
        data["batteries"] = _editor("Battery SKUs", data.get("batteries", []), "DC-coupled batteries: power + energy limits.")
    with tabs[2]:
        data["inverters"] = _editor("Inverter SKUs", data.get("inverters", []), "AC-coupled only.")
    with tabs[3]:
        data["dc_dc_modules"] = _editor("DC-DC modules", data.get("dc_dc_modules", []), "v1 assumes 100 kW/module.")
    with tabs[4]:
        data["dispensers"] = _editor("Dispenser + cable presets", data.get("dispensers", []), "Cable cap = V×Imax. Dispenser cap is an independent ceiling.")
    with tabs[5]:
        data["tariffs"] = _editor("Tariff presets", data.get("tariffs", []), "Placeholder TOU bands in engine. Demand charge uses max grid kW.")
    with tabs[6]:
        data["pricing"] = _editor("Charging prices", data.get("pricing", []), "Revenue modelling is not yet wired into engine outputs.")
    with tabs[7]:
        data["vehicles"] = _editor("Vehicle presets", data.get("vehicles", []), "v1 locked at 800 V for comparability.")

    if st.button("Save library", type="primary"):
        _save_library(data)
        st.success("Saved to local /data.")