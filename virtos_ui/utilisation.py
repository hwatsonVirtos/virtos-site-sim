import streamlit as st
import pandas as pd
import numpy as np

def _default_depot_curve():
    # 96 x 15-min; simple morning/evening peaks; bounded 0-1
    x = np.linspace(0, 1, 96)
    curve = 0.15 + 0.55*np.exp(-((x-0.35)/0.12)**2) + 0.35*np.exp(-((x-0.75)/0.10)**2)
    return np.clip(curve, 0.0, 1.0)

def render_utilisation_editor(key_prefix: str = "util"):
    profile = st.selectbox("Profile", ["Depot (default)", "High utilisation", "Custom"], key=f"{key_prefix}_profile")

    if profile == "Depot (default)":
        curve = _default_depot_curve()
    elif profile == "High utilisation":
        curve = np.clip(_default_depot_curve() + 0.25, 0.0, 1.0)
    else:
        if f"{key_prefix}_custom" not in st.session_state:
            st.session_state[f"{key_prefix}_custom"] = pd.DataFrame({"t": list(range(96)), "utilisation": _default_depot_curve()})
        df = st.data_editor(
            st.session_state[f"{key_prefix}_custom"],
            key=f"{key_prefix}_editor",
            hide_index=True,
            column_config={
                "t": st.column_config.NumberColumn(disabled=True),
                "utilisation": st.column_config.NumberColumn(min_value=0.0, max_value=1.0, step=0.01),
            },
        )
        st.session_state[f"{key_prefix}_custom"] = df
        curve = df["utilisation"].astype(float).values

    st.line_chart(pd.DataFrame({"utilisation": curve}))
    return [float(x) for x in curve]
