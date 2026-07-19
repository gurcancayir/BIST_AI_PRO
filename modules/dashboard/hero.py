import streamlit as st
from datetime import datetime
from modules.ai.market_ai import get_market_score

def show_hero():
    score, reasons = get_market_score()
    
    left, center, right = st.columns([6, 2, 2])

    with left:

        st.markdown(
            """
            <div style="height:20px;"></div>
            """,
            unsafe_allow_html=True
        )

        st.markdown("## 📈 BIST AI PRO")

        st.caption(
            "Yapay Zeka Destekli Profesyonel BIST Analiz Platformu"
        )


    with center:

        st.metric(
    "🧠 AI Score",
    f"{score}/100"
)


    with right:

        st.metric(
            "🧠 AI Score",
            "84"
        )


    st.markdown("---")