import streamlit as st



def show_ai_portfolio(df):

    st.divider()
    st.subheader("🤖 AI Portföy Analizi")


    if df.empty:

        st.info(
            "Analiz için portföy verisi bulunamadı."
        )

        return



    toplam_deger = df["Güncel Değer"].sum()


    agirliklar = (
        df["Güncel Değer"]
        /
        toplam_deger
        *
        100
    )



    max_agirlik = agirliklar.max()


    en_buyuk = df.loc[
        agirliklar.idxmax(),
        "symbol"
    ]



    col1,col2,col3 = st.columns(3)



    with col1:

        if max_agirlik > 30:

            st.warning(
                f"""
                ⚠️ Yoğunlaşma Riski

                {en_buyuk}
                %{max_agirlik:.1f}
                ağırlıkta.
                """
            )

        else:

            st.success(
                """
                🟢 Dağılım Dengeli

                Portföy çeşitlendirmesi iyi.
                """
            )



    with col2:

        st.info(
            """
            📊 Risk Seviyesi

            🟡 Orta

            Hisse ve sektör dengesi takip edilmeli.
            """
        )



    with col3:

        st.success(
            """
            🧠 AI Strateji

            Kademeli alım

            Kâr koruma

            Dengeli dağılım
            """
        )



    st.markdown("### 📌 AI Önerileri")


    recommendations = []


    if max_agirlik > 30:

        recommendations.append(
            f"{en_buyuk} ağırlığı azaltılarak risk düşürülebilir."
        )


    recommendations.extend(
        [

        "Teknoloji, savunma ve ihracatçı şirketler takip edilmeli.",

        "Nakit oranı fırsatlar için korunabilir.",

        "Kârda olan pozisyonlarda kademeli satış değerlendirilebilir."

        ]
    )


    for item in recommendations:

        st.write(
            "• " + item
        )