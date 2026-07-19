import streamlit as st
from datetime import datetime


def show_hero():

    left, center, right = st.columns([6, 2, 2])

    with left:
        st.markdown("## 📈 BIST AI PRO")
        st.caption("Yapay Zeka Destekli Profesyonel BIST Analiz Platformu")

    with center:
        st.metric("🕒 Saat", datetime.now().strftime("%H:%M"))

    with right:
        st.metric("🧠 AI Score", "84")

    st.markdown("---")