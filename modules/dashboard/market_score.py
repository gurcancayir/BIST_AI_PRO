import streamlit as st
from modules.ai.market_ai import (
    get_market_score,
    get_market_comment
)
from modules.ai.market_ai import get_market_score
def show_market_score():

    st.markdown("### 🧠 AI Market Score")

    score, reasons = get_market_score()
    comment = get_market_comment(score)
    col1, col2 = st.columns([2, 1])

    with col1:

        st.metric(
            label="Genel Piyasa Puanı",
            value=f"{score} / 100"
        
        )

        st.progress(score / 100)


    with col2:

        if score >= 75:

            st.success(comment)

        elif score >= 35:

            st.warning(comment)

        else:

            st.error(comment)
    