import streamlit as st
from modules.ai.market_ai import get_market_score
def get_ai_allocation(score, total_money):

    if score >= 80:

        oranlar = {
            "BIST Hisse":0.55,
            "Yabancı Fon":0.15,
            "Altın":0.10,
            "Gümüş":0.05,
            "Para Piyasası Fonu":0.10,
            "Nakit":0.05
        }


    elif score >= 60:

        oranlar = {
            "BIST Hisse":0.45,
            "Yabancı Fon":0.15,
            "Altın":0.15,
            "Gümüş":0.05,
            "Para Piyasası Fonu":0.15,
            "Nakit":0.05
        }


    elif score >= 40:

        oranlar = {
            "BIST Hisse":0.35,
            "Yabancı Fon":0.10,
            "Altın":0.25,
            "Gümüş":0.10,
            "Para Piyasası Fonu":0.15,
            "Nakit":0.05
        }


    else:

        oranlar = {
            "BIST Hisse":0.25,
            "Yabancı Fon":0.10,
            "Altın":0.30,
            "Gümüş":0.10,
            "Para Piyasası Fonu":0.20,
            "Nakit":0.05
        }


    return {
        k:int(total_money*v)
        for k,v in oranlar.items()
    }

def show_ai_portfolio(df):
    score, reasons = get_market_score()
    st.markdown("### 🌍 AI Piyasa Bazlı Varlık Dağılımı")

para = st.number_input(
    "Yatırım Tutarı",
    value=300000,
    step=10000
)


allocation = get_ai_allocation(
    score,
    para
)


for varlik,tutar in allocation.items():

    st.write(
        f"**{varlik}** : {tutar:,.0f} TL"
    )
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