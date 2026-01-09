import streamlit as st

def render_metric_card(title: str, lines: list[str]) -> None:
    st.markdown(
        f"""<div style="border:1px solid rgba(0,0,0,0.08); border-radius:10px; padding:10px; margin-top:6px;">
        <div style="font-weight:600; margin-bottom:6px;">{title}</div>
        {''.join(f'<div style="font-size:0.92rem; opacity:0.85;">{l}</div>' for l in lines)}
        </div>""",
        unsafe_allow_html=True,
    )
