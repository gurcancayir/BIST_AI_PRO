import streamlit as st
import yfinance as yf

from modules.teknik import analiz_et

st.set_page_config(
    page_title="Hisse Analiz Merkezi",
    page_icon="📈",
    layout="wide"
)

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

    sonuc = analiz_et(veri)

    st.subheader(f"📊 {symbol} Teknik Analizi")

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Güncel Fiyat",
        f"{sonuc['fiyat']:.2f} TL"
    )

    c2.metric(
        "RSI",
        f"{sonuc['rsi']:.2f}"
    )

    c3.metric(
        "MACD",
        f"{sonuc['macd']:.2f}"
    )

    c4.metric(
        "Teknik Puan",
        f"{sonuc['puan']}/100"
    )

    st.divider()

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "📍 Destek",
        f"{sonuc['destek']:.2f}"
    )

    c2.metric(
        "🚧 Direnç",
        f"{sonuc['direnc']:.2f}"
    )

    c3.metric(
        "🎯 Güven",
        f"%{sonuc['guven']}"
    )

    st.divider()

    if "AL" in sonuc["karar"]:

        st.success(sonuc["karar"])

    elif "TUT" in sonuc["karar"]:

        st.warning(sonuc["karar"])

    else:

        st.error(sonuc["karar"])

    st.info(
        f"Trend : {sonuc['trend']}"
    )

    st.divider()

    st.subheader("📈 Fiyat Grafiği")

    grafik = veri[
        [
            "Close"
        ]
    ]
    grafik["MA20"] = veri["MA20"]

    grafik["MA50"] = veri["MA50"]

    grafik["MA200"] = veri["MA200"]

    st.line_chart(
        grafik,
        use_container_width=True
    )

    st.divider()

    st.subheader("🤖 AI Yorumu")

    for yorum in sonuc["yorumlar"]:

        st.write(f"✅ {yorum}")

    st.divider()

    st.subheader("📊 Teknik Göstergeler")

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "MA20",
        f"{sonuc['ma20']:.2f}"
    )

    c2.metric(
        "MA50",
        f"{sonuc['ma50']:.2f}"
    )

    c3.metric(
        "MA200",
        f"{sonuc['ma200']:.2f}"
    )

    st.divider()

    st.subheader("📝 Genel Değerlendirme")

    if sonuc["puan"] >= 85:

        st.success(
            "Teknik göstergelerin büyük bölümü olumlu. Trend güçlü, momentum yüksek ve mevcut görünüm yükseliş yönünde."
        )

    elif sonuc["puan"] >= 70:

        st.info(
            "Teknik görünüm pozitif. Trend yukarı yönlü ancak direnç seviyelerinde fiyat davranışı izlenmeli."
        )

    elif sonuc["puan"] >= 55:

        st.warning(
            "Hisse nötr-pozitif görünümde. Yeni pozisyon için ek teyit sinyalleri beklenebilir."
        )

    else:

        st.error(
            "Teknik görünüm zayıf. Risk yönetimi ön planda tutulmalı ve destek seviyeleri dikkatle takip edilmeli."
        )