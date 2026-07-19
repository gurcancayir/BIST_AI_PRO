import streamlit as st
from datetime import datetime

def show_hero():

    left, right = st.columns([5,1])

    with left:
        st.markdown("## 📈 BIST AI PRO")
        st.caption("Yapay Zeka Destekli Borsa Analiz Platformu")

    with right:
        st.metric("Saat", datetime.now().strftime("%H:%M"))