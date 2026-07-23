import streamlit as st


# --------------------------------------------------
# AI Skor Hesaplama
# --------------------------------------------------
def calculate_ai_score(rsi, trend):

    score = 50

    # RSI Analizi
    if 50 <= rsi <= 70:
        score += 20
    elif 30 <= rsi < 50:
        score += 10
    elif rsi > 70:
        score -= 10
    else:
        score -= 15

    # Trend Analizi
    if trend == "🟢 Yukarı":
        score += 20
    elif trend == "🟢 Pozitif":
        score += 15
    elif trend == "🟡 Yatay":
        score += 5
    else:
        score -= 10

    return max(0, min(score, 100))


# --------------------------------------------------
# AI Kararı
# --------------------------------------------------
def calculate_signal(score):

    if score >= 90:
        return "🟢 GÜÇLÜ AL"

    elif score >= 80:
        return "🟢 AL"

    elif score >= 70:
        return "🟡 TUT"

    elif score >= 60:
        return "🟠 İZLE"

    else:
        return "🔴 SAT"


# --------------------------------------------------
# Portföy Aksiyonu
# --------------------------------------------------
def calculate_action(signal):

    if signal == "🟢 GÜÇLÜ AL":
        return "➕ Ekle"

    elif signal == "🟢 AL":
        return "✅ Tut"

    elif signal == "🟡 TUT":
        return "👀 İzle"

    elif signal == "🟠 İZLE":
        return "⚠️ Azalt"

    else:
        return "❌ Sat"


# --------------------------------------------------
# Ana Ekran
# --------------------------------------------------
def show_stock_ai_signal(df):

    st.divider()

    st.subheader("🤖 Hisse AI Analizi")

    if df.empty:
        st.info("Analiz edilecek hisse bulunamadı.")
        return

    results = []

    for hisse in df["symbol"]:

        # ----------------------------------------
        # Şimdilik örnek veriler
        # Sonra gerçek teknik analiz bağlanacak
        # ----------------------------------------

        if hisse == "FROTO":
            trend = "🟢 Yukarı"
            rsi = 63

        elif hisse == "BIMAS":
            trend = "🟢 Yukarı"
            rsi = 61

        elif hisse == "ASELS":
            trend = "🟢 Yukarı"
            rsi = 65

        elif hisse == "TUPRS":
            trend = "🟢 Pozitif"
            rsi = 58

        elif hisse == "MGROS":
            trend = "🟡 Yatay"
            rsi = 52

        elif hisse == "AKSEN":
            trend = "🟢 Pozitif"
            rsi = 56

        elif hisse == "THYAO":
            trend = "🟢 Pozitif"
            rsi = 60

        else:
            trend = "🟡 Yatay"
            rsi = 50

        score = calculate_ai_score(rsi, trend)

        signal = calculate_signal(score)

        action = calculate_action(signal)

        results.append(
            {
                "Hisse": hisse,
                "Trend": trend,
                "RSI": rsi,
                "AI Skor": score,
                "Sinyal": signal,
                "Önerilen İşlem": action
            }
        )

    st.dataframe(
        results,
        use_container_width=True,
        hide_index=True
    )

    st.caption(
        "AI Skoru şu an örnek verilerle hesaplanmaktadır. "
        "Sonraki sürümde RSI, MACD, EMA, hacim, bilanço, temettü ve haber analizleri otomatik eklenecektir."
    )