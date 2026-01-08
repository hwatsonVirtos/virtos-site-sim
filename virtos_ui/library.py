import streamlit as st
import json, os

def render_library_tab():
    st.subheader("Component library")
    st.caption("Edit SKUs, proxy costs, limits. Stored as JSON in /data for now.")
    path = os.path.join("data","component_library.json")
    if not os.path.exists(path):
        seed = {"skus":[{"component_id":"PCS_500","capex_aud":100000},{"component_id":"BATT_500_1000","capex_aud":250000}]}
        os.makedirs("data", exist_ok=True)
        with open(path,"w") as f:
            json.dump(seed,f,indent=2)
    with open(path,"r") as f:
        data = json.load(f)

    edited = st.data_editor(data.get("skus", []), num_rows="dynamic", use_container_width=True)
    if st.button("Save library", type="primary"):
        data["skus"] = edited
        with open(path,"w") as f:
            json.dump(data,f,indent=2)
        st.success("Saved.")
