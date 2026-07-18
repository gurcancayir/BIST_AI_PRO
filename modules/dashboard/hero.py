import streamlit as st
from datetime import datetime


def show_hero():
    st.markdown(
        """
        <div style="
            background: linear-gradient(135deg,#0E4D92,#2D7FF9);
            padding:25px;
            border-radius:15px;
            color:white;
        ">
            <h1 style="margin:0;">📈 BIST AI PRO</h1>
            <p style="font-size:18px;margin-top:8px;">
                Yapay Zeka Destekli Profesyonel BIST Analiz Platformu
            </p>
            <p style="margin-top:15px;font-size:14px;">
                Veriyi değil, fırsatı gösterir.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.caption(datetime.now().strftime("%d.%m.%Y  |  %H:%M"))

    st.divider()