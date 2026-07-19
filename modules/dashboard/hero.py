import streamlit as st
from datetime import datetime


def show_hero():

    col1, col2 = st.columns([4, 1])

    with col1:
        st.markdown("""
        <div style="
            background: linear-gradient(135deg,#0E4D92,#2D7FF9);
            padding:12px 18px;
            border-radius:12px;
            color:white;
        ">
            <h2 style="margin:0;">
                📈 BIST AI PRO
            </h2>

            <div style="font-size:15px;margin-top:4px;">
                Yapay Zeka Destekli Profesyonel BIST Analiz Platformu
            </div>

        </div>
        """, unsafe_allow_html=True)

    with col2:

        st.metric(
            "Saat",
            datetime.now().strftime("%H:%M")
        )

    st.divider()