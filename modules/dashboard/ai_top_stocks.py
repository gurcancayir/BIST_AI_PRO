import streamlit as st
import pandas as pd

from modules.data.yahoo_data import get_stock_analysis
from modules.data.bist_lists import BIST30, BIST50, BIST100, BIST500



# ----------------------------------------------------------
# ŞİMDİLİK AYNI LİSTEYİ KULLANIYORUZ
# ----------------------------------------------------------

# Daha sonra gerçek BIST50 / BIST100 / BIST500
# listelerini ekleyeceğiz.


# ----------------------------------------------------------
# AI TOP HİSSELER
# ----------------------------------------------------------

def show_ai_top_stocks():

    st.subheader("🏆 AI Top Hisseler")

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
    with st.spinner("🤖 AI hisseleri analiz ediyor..."):

        for hisse in hisseler:

            analysis = get_stock_analysis(hisse)

            if analysis is None:
                continue

            sonuc.append(analysis)


    if len(sonuc) == 0:

        st.warning("Hiç veri alınamadı.")

        return


    # ----------------------------------------------------------
    # AI SKORUNA GÖRE SIRALA
    # ----------------------------------------------------------

    sonuc = sorted(

        sonuc,

        key=lambda x: x["score"],

        reverse=True

    )


    top10 = sonuc[:10]
    # ----------------------------------------------------------
    # TOP 10 KARTLARI
    # ----------------------------------------------------------

    st.markdown("### 🏆 AI Top 10")

    for satir in range(0, len(top10), 5):

        cols = st.columns(5)

        for col, hisse in zip(cols, top10[satir:satir+5]):

            with col:

                score = hisse["score"]

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

                    value=f'{score}/100',

                    delta=f'{hisse["change"]:.2f}%'

                )

                st.caption(hisse["recommendation"])

                st.caption(f'📈 {hisse["trend"]}')
    st.divider()

    # ----------------------------------------------------------
    # DETAY TABLOSU
    # ----------------------------------------------------------

    tablo = []

    for hisse in top10:

        tablo.append({

            "Hisse": hisse["symbol"],

            "Şirket": hisse["company"],

            "Fiyat": round(hisse["price"], 2),

            "Değişim %": round(hisse["change"], 2),

            "Trend": hisse["trend"],

            "RSI": round(hisse["rsi"], 1) if hisse["rsi"] else "-",

            "AI Skoru": hisse["score"],

            "Karar": hisse["recommendation"]

        })


    df = pd.DataFrame(tablo)

    st.markdown("### 📊 AI Top 10 Detay Analizi")

    def renk_degisim(val):

        if val < 0:
            return "color: red"

        elif val > 0:
            return "color: green"

        return ""
    st.divider()

    # ----------------------------------------------------------
    # AI İSTATİSTİKLERİ
    # ----------------------------------------------------------

    ortalama = round(df["AI Skoru"].mean(), 1)

    guclu_al = (df["Karar"] == "🟢 Güçlü Al").sum()

    al = (df["Karar"] == "🟢 Al").sum()

    tut = (df["Karar"] == "🟡 Tut").sum()

    sat = (df["Karar"] == "🔴 Sat").sum()


    c1, c2, c3, c4, c5 = st.columns(5)

    c1.metric("⭐ Ortalama AI", ortalama)

    c2.metric("🟢 Güçlü Al", guclu_al)

    c3.metric("🟢 Al", al)

    c4.metric("🟡 Tut", tut)

    c5.metric("🔴 Sat", sat)


    st.divider()

    # ----------------------------------------------------------
    # GÜNÜN EN GÜÇLÜ HİSSESİ
    # ----------------------------------------------------------

    eniyi = top10[0]

    st.success(f"""
## 🏆 Günün En Güçlü Hissesi

**{eniyi["symbol"]}**

🏢 Şirket : {eniyi["company"]}

💰 Fiyat : {eniyi["price"]:.2f} TL

📈 Günlük Değişim : %{eniyi["change"]:.2f}

📊 AI Skoru : **{eniyi["score"]}/100**

🎯 Karar : **{eniyi["recommendation"]}**

📈 Trend : **{eniyi["trend"]}**

📉 RSI : **{eniyi["rsi"]:.1f}**
""")


    st.info("""
🤖 AI Yorumu

• AI puanı; trend, RSI, MACD, EMA ve hacim verileri kullanılarak hesaplanmaktadır.

• Bu liste yatırım tavsiyesi değildir.

• Analizler günlük olarak değişebilir.
""")