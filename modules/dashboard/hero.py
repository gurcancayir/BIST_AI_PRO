import streamlit as st
from datetime import datetime


def show_hero():

    c1, c2, c3, c4 = st.columns([3, 1, 1, 1])

    with c1:
        st.title("📈 BIST AI PRO")
        st.caption("Yapay Zeka Destekli Borsa Analiz Platformu")

    with c2:
        st.metric("🕒 Saat", datetime.now().strftime("%H:%M"))

    with c3:
        st.metric("🧠 AI", "84")

    with c4:
        st.metric("📊 Trend", "🟢")

    st.divider()