import streamlit as st

from modules.ai.ai_picker import show_ai_picks

st.set_page_config(
    page_title="AI Seçimleri",
    page_icon="⭐",
    layout="wide"
)

show_ai_picks()