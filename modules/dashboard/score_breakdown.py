import streamlit as st


def show_score_breakdown():

    st.markdown("### 📊 Skor Dağılımı")

    scores = [
        ("📈 Trend", "18 / 20"),
        ("📊 Momentum", "9 / 10"),
        ("💰 Hacim", "9 / 10"),
        ("🌍 Makro", "12 / 15"),
        ("⚠️ Jeopolitik Risk", "5 / 10"),
        ("🤖 AI Güveni", "%92"),
    ]


    col1, col2 = st.columns(2)


    for i, item in enumerate(scores):

        with col1 if i % 2 == 0 else col2:

            st.metric(
                label=item[0],
                value=item[1]
            )


    st.caption(
        "AI puanı; teknik görünüm, piyasa momentumu ve makro koşullar dikkate alınarak hesaplanır."
    )