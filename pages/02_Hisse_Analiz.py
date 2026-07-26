import streamlit as st
import yfinance as yf

from modules.teknik import analiz_et
from modules.data.yahoo_data import get_stock_analysis

st.set_page_config(
    page_title="Hisse Analiz Merkezi",
    page_icon="📈",
    layout="wide"
)

st.write("TEST ÇALIŞIYOR")

st.title("📈 Hisse Analiz Merkezi")

symbol = st.text_input(
    "Hisse Kodu",
    placeholder="Örn: BIMAS"
)

if st.button("Analiz Et"):

    if not symbol:

        st.warning("Hisse kodu giriniz.")
        st.stop()

    symbol = symbol.upper()

    try:

        ticker = yf.Ticker(symbol + ".IS")

        veri = ticker.history(period="1y")

    except Exception as e:

        st.error(e)
        st.stop()

    if veri.empty:

        st.error("Veri bulunamadı.")
        st.stop()

    sonuc = get_stock_analysis(symbol)
    if sonuc is None:
        st.error("Analiz verisi alınamadı.")
        st.stop()

    st.write("KONTROL DESTEK:", sonuc["support"])
    st.write("KONTROL DİRENÇ:", sonuc["resistance"])


    st.subheader(f"📊 {symbol} Teknik Analizi")

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "📍 Destek",
        f"{sonuc['support']:.2f} TL"
    )

    c2.metric(
        "🚧 Direnç",
        f"{sonuc['resistance']:.2f} TL"
    )

    c3.metric(
        "MACD",
        f"{sonuc['macd']:.2f}"
    )

    c4.metric(
        "Teknik Puan",
        f"{sonuc['score']}/100"
    )

    st.divider()

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "📍 Destek",
        f"{sonuc['support']:.2f} TL"
    )

    c2.metric(
        "🚧 Direnç",
        f"{sonuc['resistance']:.2f} TL"
    )

    c3.metric(
        "🤖 AI Skor",
        f"{sonuc['score']}/100"
    )
    
    st.divider()

    if "Güçlü Al" in sonuc["recommendation"]:

        st.success(sonuc["recommendation"])

    elif "Al" in sonuc["recommendation"]:

        st.success(sonuc["recommendation"])

    elif "Tut" in sonuc["recommendation"]:

        st.warning(sonuc["recommendation"])

    else:

        st.error(sonuc["recommendation"])
        st.info(
        f"Trend : {sonuc['trend']}"
    )

    st.divider()

    st.subheader("📈 Fiyat Grafiği")

    grafik = veri[["Close"]].copy()

    grafik["MA20"] = veri["Close"].rolling(20).mean()

    grafik["MA50"] = veri["Close"].rolling(50).mean()

    grafik["MA200"] = veri["Close"].rolling(200).mean()
    st.line_chart(

        grafik,
        use_container_width=True
    )

    st.divider()

    st.subheader("🤖 AI Yorumu")

    st.write(
        "Karar:",
        sonuc["recommendation"]
    )

    st.write(
        "Trend:",
        sonuc["trend"]
    )

    st.write(
        "AI Skor:",
        f"{sonuc['score']}/100"
    )

    st.divider()

    st.subheader("📊 Teknik Göstergeler")

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "EMA20",
        f"{sonuc['ema20']:.2f}"
    )

    c2.metric(
        "EMA50",
        f"{sonuc['ema50']:.2f}"
    )

    c3.metric(
        "EMA200",
        f"{sonuc['ema200']:.2f}"
    )

    st.divider()

    st.subheader("📝 Genel Değerlendirme")

    if sonuc["score"] >= 85:

        st.success(
        "Teknik göstergelerin büyük bölümü olumlu. Trend güçlü ve görünüm pozitif."
    )

    elif sonuc["score"] >= 70:

        st.info(
        "Teknik görünüm pozitif. Direnç seviyeleri takip edilmeli."
    )

    elif sonuc["score"] >= 55:

        st.warning(
        "Hisse nötr-pozitif görünümde. Yeni alım için teyit beklenebilir."
    )

    else:

        st.error(
        "Teknik görünüm zayıf. Risk yönetimi ön planda tutulmalı."
    )

        st.error(
            "Teknik görünüm zayıf. Risk yönetimi ön planda tutulmalı ve destek seviyeleri dikkatle takip edilmeli."
        )