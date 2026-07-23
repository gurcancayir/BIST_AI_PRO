import streamlit as st
import pandas as pd

from modules.data.macro_data import get_price


# ----------------------------------------------------------
# AI SCORE
# ----------------------------------------------------------

def calculate_ai_score(change):

    score = 50

    try:
        change = float(change)
    except:
        return 0

    # Momentum
    if change >= 5:
        score += 40
    elif change >= 3:
        score += 30
    elif change >= 2:
        score += 20
    elif change >= 1:
        score += 10
    elif change <= -5:
        score -= 40
    elif change <= -3:
        score -= 30
    elif change <= -2:
        score -= 20
    elif change <= -1:
        score -= 10

    return max(0, min(score, 100))


# ----------------------------------------------------------
# AI COMMENT
# ----------------------------------------------------------

def get_comment(score):

    if score >= 90:
        return "🟢 Güçlü Al"

    elif score >= 75:
        return "🟢 Al"

    elif score >= 60:
        return "🟡 Tut"

    elif score >= 40:
        return "🟠 Zayıf"

    else:
        return "🔴 Sat"


# ----------------------------------------------------------
# TOP STOCKS
# ----------------------------------------------------------

def show_ai_top_stocks():

    st.subheader("🏆 AI Top 10 Hisseler")

    hisseler = {

        "AKSEN":"AKSEN.IS",
        "ASELS":"ASELS.IS",
        "ASTOR":"ASTOR.IS",
        "BIMAS":"BIMAS.IS",
        "CCOLA":"CCOLA.IS",
        "ENKAI":"ENKAI.IS",
        "EREGL":"EREGL.IS",
        "FROTO":"FROTO.IS",
        "GARAN":"GARAN.IS",
        "ISCTR":"ISCTR.IS",
        "KCHOL":"KCHOL.IS",
        "KOZAL":"KOZAL.IS",
        "MGROS":"MGROS.IS",
        "SAHOL":"SAHOL.IS",
        "SISE":"SISE.IS",
        "TCELL":"TCELL.IS",
        "THYAO":"THYAO.IS",
        "TOASO":"TOASO.IS",
        "TUPRS":"TUPRS.IS",
        "YKBNK":"YKBNK.IS"
    }

    sonuc = []

    with st.spinner("AI hisseleri analiz ediyor..."):

        for isim, sembol in hisseler.items():

            try:

                fiyat, degisim = get_price(sembol)

                score = calculate_ai_score(degisim)

                sonuc.append({

                    "Hisse": isim,
                    "Fiyat": fiyat,
                    "Değişim": float(degisim),
                    "AI Skoru": score,
                    "Karar": get_comment(score)

                })

            except:
                pass

    if len(sonuc) == 0:

        st.warning("Veri alınamadı.")
        return

    sonuc = sorted(
        sonuc,
        key=lambda x: x["AI Skoru"],
        reverse=True
    )
    # ----------------------------------------------------------
    # TOP 10 KARTLARI
    # ----------------------------------------------------------

    top10 = sonuc[:10]

    for satir in range(0, len(top10), 5):

        cols = st.columns(5)

        for col, hisse in zip(cols, top10[satir:satir+5]):

            with col:

                score = hisse["AI Skoru"]

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

                    label=f"{renk} {hisse['Hisse']}",

                    value=f"{score}/100",

                    delta=f"%{hisse['Değişim']:.2f}"

                )

    st.divider()

    # ----------------------------------------------------------
    # DETAY TABLOSU
    # ----------------------------------------------------------

    df = pd.DataFrame(top10)

    df = df[
        [
            "Hisse",
            "Fiyat",
            "Değişim",
            "AI Skoru",
            "Karar"
        ]
    ]

    st.markdown("### 📊 AI Top 10 Detayları")

    st.dataframe(

        df,

        use_container_width=True,

        hide_index=True

    )

    st.divider()

    # ----------------------------------------------------------
    # AI YORUMU
    # ----------------------------------------------------------

    eniyi = top10[0]

    st.success(f"""

### 🤖 AI Yorumu

🏆 Günün en güçlü hissesi **{eniyi['Hisse']}**

AI Skoru : **{eniyi['AI Skoru']}/100**

Karar : **{eniyi['Karar']}**

Bu hisse mevcut analiz kriterlerine göre
bugün izlenmeye en uygun hisseler arasında yer alıyor.

""")

    st.info("""

💡 Yakında eklenecek özellikler

• RSI

• MACD

• EMA20 / EMA50

• Bollinger

• Hacim Analizi

• Trend Gücü

• FK

• PD/DD

• Bilanço Puanı

• AI Güven Oranı

• Beklenen Getiri

• Risk Skoru

""")