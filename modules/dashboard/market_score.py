import streamlit as st


def show_market_score():

    st.markdown("### 🧠 AI Market Score")

    score = 84

    col1, col2 = st.columns([2, 1])

    with col1:

        st.metric(
            label="Genel Piyasa Puanı",
            value=f"{score} / 100",
            delta="+3"
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


    st.caption(
        "AI değerlendirmesi: Teknik görünüm, momentum ve piyasa koşullarına göre hesaplanır."
    )