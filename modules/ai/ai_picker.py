import streamlit as st

from modules.data.yahoo_data import get_stock_analysis

# AI'nin tarayacağı hisse evreni
AI_UNIVERSE = [

    "AKBNK","GARAN","YKBNK","ISCTR",

    "KCHOL","SAHOL","ALARK",

    "TUPRS","AKSEN","ENJSA",

    "BIMAS","MGROS","SOKM",

    "ASELS","ASTOR","SDTTR",

    "THYAO","PGSUS",

    "FROTO","TOASO",

    "SISE","EREGL","KRDMD",

    "CCOLA","ULKER",

    "TCELL","TTKOM",

    "OYAKC","CIMSA",

    "LOGO","MIA"
]
def calculate_recommendation_score(analysis):

    score = 0

    # Trend
    if analysis["trend"] == "Güçlü Yükseliş":
        score += 25

    elif analysis["trend"] == "Yükseliş":
        score += 18

    # Momentum
    if analysis["momentum"] > 0:
        score += 20

    # Hacim
    if analysis["volume"] > analysis["avg_volume"]:
        score += 15

    # RSI
    rsi = analysis["rsi"]

    if 45 <= rsi <= 65:
        score += 10

    elif rsi < 30:
        score += 5

    # MACD

    if analysis["macd"] > analysis["signal"]:
        score += 10

    # EMA

    if analysis["price"] > analysis["ema20"]:
        score += 10

    # Volatilite

    if analysis["volatility"] < 3:
        score += 10

    return score
def generate_ai_comment(analysis):

    comments = []

    # Trend
    if analysis["trend"] == "Güçlü Yükseliş":
        comments.append("🟢 Güçlü yükseliş trendi devam ediyor.")

    elif analysis["trend"] == "Yükseliş":
        comments.append("🟢 Pozitif trend korunuyor.")

    elif analysis["trend"] == "Düşüş":
        comments.append("🟠 Kısa vadeli baskı devam ediyor.")

    # Momentum
    if analysis["momentum"] > 0:
        comments.append("🚀 Momentum pozitif.")

    else:
        comments.append("⚠ Momentum zayıf.")

    # Hacim
    if analysis["volume"] > analysis["avg_volume"]:
        comments.append("📈 Hacim ortalamanın üzerinde.")

    else:
        comments.append("📉 Hacim desteği zayıf.")

    # RSI
    rsi = analysis["rsi"]

    if rsi > 70:
        comments.append("⚠ RSI yüksek, kâr satışları görülebilir.")

    elif rsi < 35:
        comments.append("💡 RSI düşük seviyelerde, tepki potansiyeli oluşabilir.")

    return comments
def get_top_ai_picks():

    results = []

    for symbol in AI_UNIVERSE:

        try:

            analysis = get_stock_analysis(symbol)

            if analysis is None:
                continue

            recommendation_score = calculate_recommendation_score(
                analysis
            )

            analysis["recommendation_score"] = recommendation_score

            analysis["ai_comment"] = generate_ai_comment(
                analysis
            )

            results.append(analysis)

        except:
            pass

    results.sort(
        key=lambda x: x["recommendation_score"],
        reverse=True
    )

    return results[:10]
def show_ai_picks():

    st.title("⭐ AI Seçimleri")

    st.caption(
        "AI; teknik analiz, momentum, hacim ve trend verilerini birlikte değerlendirerek günün öne çıkan hisselerini listeler."
    )

    picks = get_top_ai_picks()

    if len(picks) == 0:

        st.warning("Hisse bulunamadı.")

        return

    medals = ["🥇","🥈","🥉","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣","🔟"]

    for i, stock in enumerate(picks):

        with st.container():

            st.subheader(
                f"{medals[i]} {stock['symbol'].replace('.IS','')}"
            )

            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric(
                    "AI Öneri",
                    f"{stock['recommendation_score']}/100"
                )

            with col2:
                st.metric(
                    "Trend",
                    stock["trend"]
                )

            with col3:
                st.metric(
                    "RSI",
                    round(stock["rsi"],1)
                )

            st.write("### 🤖 AI Yorumu")

            for yorum in stock["ai_comment"]:

                st.write("•", yorum)

            c1, c2, c3 = st.columns(3)

            with c1:
                st.metric(
                    "Fiyat",
                    stock["price"]
                )

            with c2:
                st.metric(
                    "Destek",
                    stock["support"]
                )

            with c3:
                st.metric(
                    "Direnç",
                    stock["resistance"]
                )

            st.divider()