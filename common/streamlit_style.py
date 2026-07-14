from pathlib import Path
import streamlit as st

CSS_FILE = Path(__file__).parent / "streamlit.css"


def apply_style():
    st.markdown(
        f"<style>{CSS_FILE.read_text()}</style>",
        unsafe_allow_html=True,
    )