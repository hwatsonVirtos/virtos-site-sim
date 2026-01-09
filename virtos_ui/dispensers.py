import streamlit as st
import pandas as pd

def render_dispensers_table(key_prefix: str = "disp"):
    default = pd.DataFrame([
        {"name":"Fast DC", "connector":"CCS", "qty":39, "imax_a":250},
    ])

    df = st.data_editor(
        default if f"{key_prefix}_df" not in st.session_state else st.session_state[f"{key_prefix}_df"],
        key=f"{key_prefix}_editor",
        num_rows="dynamic",
        hide_index=True,
        column_config={
            "name": st.column_config.TextColumn(),
            "connector": st.column_config.SelectboxColumn(options=["CCS","MCS"]),
            "qty": st.column_config.NumberColumn(min_value=0, step=1),
            "imax_a": st.column_config.NumberColumn(min_value=0, step=10),
        },
    )
    # persist
    st.session_state[f"{key_prefix}_df"] = df

    # derived
    df = df.copy()
    df["per_unit_kw"] = (800.0 * df["imax_a"].astype(float) / 1000.0).round(1)
    df["nameplate_kw"] = (df["qty"].astype(float) * df["per_unit_kw"]).round(0)

    summary = {
        "total_units": int(df["qty"].sum()) if len(df) else 0,
        "total_nameplate_kw": float(df["nameplate_kw"].sum()) if len(df) else 0.0,
    }

    st.dataframe(df[["name","connector","qty","imax_a","per_unit_kw","nameplate_kw"]], width='stretch', hide_index=True)

    return df, summary
