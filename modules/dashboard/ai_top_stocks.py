import streamlit as st
import pandas as pd

from modules.dashboard.sector_strength import get_sector_scores
from modules.data.yahoo_data import get_stock_analysis
from modules.data.bist_lists import (
    BIST30,
    BIST50,
    BIST100,
    BIST500
)
def show_ai_top_stocks():

    print("AI TOP STOCKS ÇALIŞTI")

from modules.data.fundamental import (
    get_fundamental_data,
    calculate_fundamental_score
)


# ----------------------------------------------------------
# AI TOP HİSSELER
# ----------------------------------------------------------

def show_ai_top_stocks():


    sektor_skorlari = get_sector_scores()


    st.subheader(
        "🏆 Genel Yatırım Skoru Top Hisseler"
    )


    secim = st.selectbox(

        "Analiz Evreni",

        [
            "BIST30",
            "BIST50",
            "BIST100",
            "BIST500"
        ]

    )


    LISTELER = {

        "BIST30": BIST30,

        "BIST50": BIST50,

        "BIST100": BIST100,

        "BIST500": BIST500

    }


    hisseler = LISTELER[secim]


    st.info(

        f"{secim} içerisindeki "
        f"{len(hisseler)} hisse AI tarafından analiz ediliyor."

    )


    sonuc = []


    with st.spinner(
        "🤖 AI hisseleri analiz ediyor..."
    ):


        for hisse in hisseler:


            analysis = get_stock_analysis(hisse)


            if analysis is None:

                continue



            # ---------------------------------
            # SEKTÖR SKORU
            # ---------------------------------

            sektor = analysis.get(
                "sector",
                ""
            )

            analysis["sector_score"] = sektor_skorlari.get(
                sektor,
                50
            ) 

            analysis["sector_score"] = sektor_skorlari.get(

                sektor,

                50

            )



            # ---------------------------------
            # TEMEL ANALİZ
            # ---------------------------------

            fundamental = get_fundamental_data(
                hisse
            )


            fund_score = calculate_fundamental_score(
                fundamental
            )



            # ---------------------------------
            # GENEL SKOR
            # ---------------------------------

            genel_skor = (

                analysis["score"] * 0.35

                +

                analysis["trend_strength"] * 0.10

                +

                analysis["volume_score"] * 0.10

                +

                analysis["momentum_score"] * 0.10

                +

                analysis["momentum_60_score"] * 0.10

                +

                fund_score * 0.15

                +

                analysis["sector_score"] * 0.10

            )


            analysis["fund_score"] = fund_score


            analysis["genel_skor"] = round(
                genel_skor,
                1
            )


            sonuc.append(
                analysis
            )


    if len(sonuc) == 0:


        st.warning(
            "Hiç veri alınamadı."
        )


        return
    # ----------------------------------------------------------
    # AI SKORUNA GÖRE SIRALA
    # ----------------------------------------------------------

    sonuc = sorted(

        sonuc,

        key=lambda x: x["genel_skor"],

        reverse=True

    )


    top10 = sonuc[:10]


    # ----------------------------------------------------------
    # TOP 10 KARTLARI
    # ----------------------------------------------------------

    st.markdown(
        "### 🏆 AI Top 10"
    )


    for satir in range(
        0,
        len(top10),
        5
    ):


        cols = st.columns(5)


        for col, hisse in zip(
            cols,
            top10[satir:satir+5]
        ):


            with col:


                score = hisse["genel_skor"]


                if score >= 90:

                    renk = "🟢"


                elif score >= 75:

                    renk = "🟢"


                elif score >= 60:

                    renk = "🟡"


                elif score >= 40:

                    renk = "🟠"


                else:

                    renk = "🔴"



                st.metric(

                    label=f'{renk} {hisse["symbol"]}',

                    value=f'{score:.1f}/100',

                    delta=f'{hisse["change"]:.2f}%'

                )


                st.caption(
                    hisse["recommendation"]
                )


                st.caption(
                    f'📈 {hisse["trend"]}'
                )


                st.caption(
                    f"""
📊 Teknik: {hisse["score"]}/100

📈 Trend Gücü: {hisse.get("trend_strength",50)}/100

💰 Hacim: {hisse.get("volume_score",50)}/100

🚀 20 Günlük Momentum: {hisse.get("momentum_score",50)}/100

📈 60 Günlük Momentum: {hisse.get("momentum_60_score",50)}/100

🏢 Temel: {hisse.get("fund_score",50)}/100

🏭 Sektör: {hisse.get("sector_score",50)}/100
"""
                )



    st.divider()



    # ----------------------------------------------------------
    # DETAY TABLOSU
    # ----------------------------------------------------------

    tablo = []


    for hisse in top10:


        tablo.append({

            "Hisse": hisse["symbol"],

            "Şirket": hisse["company"],

            "Fiyat": round(
                hisse["price"],
                2
            ),

            "Değişim %": round(
                hisse["change"],
                2
            ),

            "Trend": hisse["trend"],

            "RSI": round(
                hisse["rsi"],
                1
            ) if hisse["rsi"] else "-",

            "Teknik Skor": hisse["score"],

            "Trend Gücü": hisse["trend_strength"],

            "Hacim Skor": hisse["volume_score"],

            "20 Gün Momentum": hisse["momentum_score"],

            "60 Gün Momentum": hisse["momentum_60_score"],

            "Temel Skor": hisse["fund_score"],

            "Sektör Skor": hisse["sector_score"],

            "Genel Skor": hisse["genel_skor"],

            "Karar": hisse["recommendation"]

        })



    df = pd.DataFrame(tablo)


    st.markdown(
        "### 📊 AI Top 10 Detay Analizi"
    )


    st.dataframe(

        df,

        use_container_width=True

    )


    st.divider()



    # ----------------------------------------------------------
    # AI İSTATİSTİKLERİ
    # ----------------------------------------------------------

    ortalama = round(
        df["Genel Skor"].mean(),
        1
    )


    guclu_al = (
        df["Karar"] == "🟢 Güçlü Al"
    ).sum()


    al = (
        df["Karar"] == "🟢 Al"
    ).sum()


    tut = (
        df["Karar"] == "🟡 Tut"
    ).sum()


    sat = (
        df["Karar"] == "🔴 Sat"
    ).sum()



    c1, c2, c3, c4, c5 = st.columns(5)


    c1.metric(
        "⭐ Ortalama Genel Skor",
        ortalama
    )


    c2.metric(
        "🟢 Güçlü Al",
        guclu_al
    )


    c3.metric(
        "🟢 Al",
        al
    )


    c4.metric(
        "🟡 Tut",
        tut
    )


    c5.metric(
        "🔴 Sat",
        sat
    )


    st.divider()



    # ----------------------------------------------------------
    # GÜNÜN EN GÜÇLÜ HİSSESİ
    # ----------------------------------------------------------

    eniyi = top10[0]


    st.success(
f"""
## 🏆 Günün En Güçlü Hissesi

**{eniyi["symbol"]}**

🏢 Şirket : {eniyi["company"]}

💰 Fiyat : {eniyi["price"]:.2f} TL

📈 Günlük Değişim : %{eniyi["change"]:.2f}

📊 Genel Skor : **{eniyi["genel_skor"]}/100**

🎯 Karar : **{eniyi["recommendation"]}**

📈 Trend : **{eniyi["trend"]}**

📉 RSI : **{eniyi["rsi"]:.1f}**

🏭 Sektör : **{eniyi["sector"]}**

🏭 Sektör Skoru : **{eniyi["sector_score"]}/100**
"""
    )



    st.info(
"""
🤖 AI Yorumu

• AI puanı; teknik analiz, trend, momentum,
hacim, temel analiz ve sektör gücü birleşimiyle hesaplanır.

• Sektör gücü artık genel skora %10 katkı yapmaktadır.

• Liste yatırım tavsiyesi değildir.
"""
    )