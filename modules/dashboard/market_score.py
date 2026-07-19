import streamlit as st


def show_market_score():

    score = 84

    st.subheader("🧠 AI Market Score")

    col1, col2 = st.columns([2, 1])

    with col1:

        st.metric(
            "Genel Piyasa Puanı",
            f"{score}/100",
            "+3"
        )

        st.progress(score / 100)

        if score >= 80:
            st.success("🟢 Güçlü Pozitif Piyasa")
        elif score >= 60:
            st.warning("🟡 Temkinli Pozitif")
        else:
            st.error("🔴 Riskli Piyasa")

    with col2:

        st.markdown("### Skor Dağılımı")

        st.write("📈 Trend ............. 18/20")
        st.write("📊 Momentum ........ 9/10")
        st.write("💰 Hacim ............ 9/10")
        st.write("🌍 Makro ........... 12/15")
        st.write("🏦 Bankalar ...... 8/10")
        st.write("🌎 Jeopolitik ..... 5/10")
        st.write("🤖 AI Güveni ...... 92%")

    st.divider()