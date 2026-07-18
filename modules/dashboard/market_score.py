import streamlit as st


def show_market_score():

    st.subheader("🧠 AI Market Score")

    col1, col2 = st.columns([2, 1])

    with col1:

        st.metric(
            label="Genel Piyasa Puanı",
            value="84 / 100",
            delta="+3"
        )

        st.progress(84)

    with col2:

        st.info("""
**Trend**

🟢 Güçlü

**Risk**

🟡 Orta

**Likidite**

🟢 İyi

**AI Güveni**

92%
""")

    st.divider()