import streamlit as st
import importlib
import traceback
from pathlib import Path

st.set_page_config(page_title="Virtos Site Simulator", layout="wide")

st.title("Virtos Site Simulator")
st.caption("Boot diagnostics (temporary). If this page renders, Streamlit Cloud is healthy.")

# Basic environment info
st.write({
    "cwd": str(Path.cwd()),
    "files_in_root": sorted([p.name for p in Path.cwd().iterdir()])[:50],
})

st.divider()
st.subheader("Module import check")

modules = [
    "virtos_engine",
    "virtos_engine.core",
    "virtos_engine.explain",
    "virtos_engine.summaries",
    "virtos_ui",
    "virtos_ui.layout",
    "virtos_ui.powerflow",
    "virtos_ui.results_spine",
    "virtos_ui.library",
    "virtos_ui.diagnostics",
]

results = {}
for m in modules:
    try:
        importlib.import_module(m)
        results[m] = "OK"
    except Exception as e:
        results[m] = "FAIL"
        st.error(f"Import failed: {m}")
        st.code(traceback.format_exc())

st.write(results)

st.divider()
st.subheader("Next step")
st.info("If all imports are OK, we can switch app.py back to the real UI entry. If any FAIL, fix the missing package/__init__.py or bad imports shown above.")
