import streamlit as st
from modules.ai.market_ai import get_market_score

def show_market_score():

    st.markdown("### 🧠 AI Market Score")

    score, reasons = get_market_score()

    col1, col2 = st.columns([2, 1])

    with col1:

        st.metric(
            label="Genel Piyasa Puanı",
            value=f"{score} / 100"
        
        )

        st.progress(score / 100)


    with col2:

        if score >= 80:

            st.success(
                "🟢 Güçlü Pozitif\n\n"
                "Trend destekleyici"
            )

        elif score >= 60:

            st.warning(
                "🟡 Temkinli Pozitif"
            )

        else:

            st.error(
                "🔴 Risk Seviyesi Yüksek"
            )


    