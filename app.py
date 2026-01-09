import os
import sys
import traceback

import streamlit as st
import pandas as pd
import numpy as np

# Ensure repo root is on sys.path (Streamlit Cloud should do this, but be defensive).
REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

try:
    from virtos_engine.core import run_engine
except Exception as e:
    st.error("Boot failed: could not import virtos_engine.core.run_engine")
    st.code("\n".join(sys.path), language="text")
    st.exception(e)
    st.code(traceback.format_exc(), language="text")
    st.stop()

try:
    from virtos_ui.layout import render_simulator_tab
    from virtos_ui.library import render_library_tab
    from virtos_ui.diagnostics import render_diagnostics_tab
except Exception as e:
    st.error("Boot failed: could not import UI modules")
    st.exception(e)
    st.code(traceback.format_exc(), language="text")
    st.stop()


def main():
    st.set_page_config(page_title="Virtos Site Simulator", layout="wide")
    st.title("Virtos Site Simulator")

    tabs = st.tabs(["Simulator", "Library", "Diagnostics"])
    with tabs[0]:
        render_simulator_tab(run_engine=run_engine)
    with tabs[1]:
        render_library_tab()
    with tabs[2]:
        render_diagnostics_tab()


if __name__ == "__main__":
    main()
