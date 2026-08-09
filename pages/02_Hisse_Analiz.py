import streamlit as st
import yfinance as yf

from modules.teknik import analiz_et
from modules.data.yahoo_data import get_stock_analysis

from modules.data.fundamental import (
    get_fundamental_data,
    calculate_fundamental_score
)

from modules.ai.market_ai import get_market_score
from modules.data.financial_score import calculate_financial_score
from modules.data.financial_score import get_financial_statement

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

    sonuc = get_stock_analysis(symbol)


    if sonuc is None:
        st.error("Analiz verisi alınamadı.")
        st.stop()

# -------------------------------
# TEMEL ANALİZ
# -------------------------------

fundamental = get_fundamental_data(symbol)

fund_score = calculate_fundamental_score(
    fundamental
)

market_score, market_reasons = get_market_score()

# -------------------------------
# KAP FİNANSAL ANALİZ
# -------------------------------

kap_data = get_financial_statement(
    symbol
)

kap_financial = calculate_financial_score(
    symbol
)

if kap_financial:
    kap_score = kap_financial["total_score"]
    kap_signal = kap_financial["signal"]
else:
    kap_score = None
    kap_signal = "Veri Yok"

if kap_score is not None:
    st.metric(
        "🧾 KAP Finansal Skor",
        f"{kap_score:.1f}/100"
    )

    st.caption(
        f"Finansal Durum: {kap_signal}"
    )
else:
    st.metric(
        "🧾 KAP Finansal Skor",
        "Veri Yok"
    )

# -------------------------------
# KAP FİNANSAL VERİLER
# -------------------------------

if kap_data:

    st.markdown(
        "### 💰 KAP Finansal Veriler"
    )

    col1, col2, col3 = st.columns(3)

    with col1:

        revenue = kap_data.get(
            "revenue"
        )

        if revenue is not None:
            st.metric(
                "Hasılat",
                f"{revenue / 1_000_000_000:.2f} Mlyr TL"
            )
        else:
            st.metric(
                "Hasılat",
                "Veri Yok"
            )

    with col2:

        net_profit = kap_data.get(
            "net_profit"
        )

        if net_profit is not None:
            st.metric(
                "Net Kâr",
                f"{net_profit / 1_000_000_000:.2f} Mlyr TL"
            )
        else:
            st.metric(
                "Net Kâr",
                "Veri Yok"
            )

    with col3:

        cash = kap_data.get(
            "cash"
        )

        if cash is not None:
            st.metric(
                "Nakit",
                f"{cash / 1_000_000_000:.2f} Mlyr TL"
            )
        else:
            st.metric(
                "Nakit",
                "Veri Yok"
            )

    col4, col5 = st.columns(2)

    with col4:

        equity = kap_data.get(
            "equity"
        )

        if equity is not None:
            st.metric(
                "Özkaynak",
                f"{equity / 1_000_000_000:.2f} Mlyr TL"
            )
        else:
            st.metric(
                "Özkaynak",
                "Veri Yok"
            )

    with col5:

        operating_cash_flow = kap_data.get(
            "operating_cash_flow"
        )

        if operating_cash_flow is not None:
            st.metric(
                "Faaliyet Nakit Akışı",
                f"{operating_cash_flow / 1_000_000_000:.2f} Mlyr TL"
            )
        else:
            st.metric(
                "Faaliyet Nakit Akışı",
                "Veri Yok"
            )

    st.caption(
        f"KAP Dönemi: {kap_data.get('period')} "
        f"({kap_data.get('period_end')})"
    )    
    st.divider()

    st.subheader("📊 Temel Analiz")

    st.write(
        "🟢 Sektör:",
        fundamental.get("sector")
    )

    market_cap = fundamental.get("market_cap")

    if market_cap is not None:

        if market_cap >= 1_000_000_000:
            market_cap_text = f"{market_cap / 1_000_000_000:.1f} Milyar TL"

        elif market_cap >= 1_000_000:
            market_cap_text = f"{market_cap / 1_000_000:.1f} Milyon TL"

        else:
            market_cap_text = f"{market_cap:,.0f} TL"

    else:
        market_cap_text = "-"

    st.write(
        "💰 Piyasa Değeri:",
        market_cap_text
    )

    c1, c2 = st.columns(2)

    c1.metric(
        "📌 F/K",
        f'{fundamental.get("pe_ratio", "-")}'
    )

    c2.metric(
        "📌 PD/DD",
        f'{fundamental.get("pb_ratio", "-")}'
    )

    st.write(
        "📈 Kâr Marjı:",
        fundamental.get("profit_margin")
    )

    st.write(
        "📈 Ciro Büyümesi:",
        fundamental.get("revenue_growth")
    )

    st.write(
        "💳 Borç/Özsermaye:",
        fundamental.get("debt_to_equity")
    )

    st.divider()

    st.metric(
        "💰 Güncel Değer",
        f'{sonuc["price"]:.2f} TL',
        f'{sonuc["change"]:.2f}%'
    )

    genel_skor = (
    sonuc["score"] * 0.50 +
    fund_score * 0.20 +
    sonuc["momentum_60_score"] * 0.15 +
    market_score * 0.15
    )

    st.divider()

    st.subheader("🏆 Genel Yatırım Skoru")

    c1, c2, c3, c4, c5 = st.columns(5)

    c1.metric(
        "📈 Teknik Skor",
        f"{sonuc['score']}/100"
    )

    c2.metric(
    "📊 Temel Skor",
    f"{fund_score}/100"
    )

    if kap_score is not None:
        st.metric("🏦 KAP Finansal Skor", f"{kap_score:.1f}/100")
        st.caption(f"Finansal Durum: {kap_signal}")
    else:
        st.metric("🏦 KAP Finansal Skor", "Veri Yok")

    c3.metric(
        "🏆 Genel Skor",
        f"{genel_skor:.0f}/100"
    )
    c4.metric(
        "🚀 60G Momentum",
        f"{sonuc['momentum_60_score']}/100"
    )
    c5.metric(
    "🌍 Market Score",
    f"{market_score}/100"
    )

    st.subheader(f"📊 {symbol} Teknik Analizi")

    c1, c2, c3, c4, c5 = st.columns(5)

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
        "RSI",
        f"{sonuc['rsi']:.2f}"
    )

    c5.metric(
        "📈 Teknik Skor",
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
            "Teknik görünüm zayıf. Risk yönetimi ön planda tutulmalı ve destek seviyeleri dikkatle takip edilmeli."
        )