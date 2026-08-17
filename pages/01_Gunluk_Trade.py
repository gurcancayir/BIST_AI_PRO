# ============================================================
# BIST AI PRO
# 05_Gunluk_Trade.py
#
# GÜNLÜK TRADE MERKEZİ
#
# BIST500
#   ↓
# Likidite Filtresi
#   ↓
# Teknik Ön Filtre
#   ↓
# 9 EMA / Pullback
#   ↓
# 15 Dakika Trend
#   ↓
# VWAP
#   ↓
# RSI
#   ↓
# Hacim
#   ↓
# Destek / Direnç
#   ↓
# Risk / Reward
#   ↓
# TRADE SKORU
#   ↓
# GÜNLÜK AL / İZLE / UYGUN DEĞİL
#
# ============================================================

import sqlite3
import math
import time
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf


# ============================================================
# SAYFA AYARLARI
# ============================================================

st.set_page_config(
    page_title="BIST AI PRO - Günlük Trade Merkezi",
    page_icon="⚡",
    layout="wide",
)


# ============================================================
# AYARLAR
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "borsa.db"

MIN_LIQUIDITY = 20_000_000

HISTORY_PERIOD = "1mo"

TRADE_THRESHOLD = 80
PULLBACK_THRESHOLD = 65
INTRADAY_THRESHOLD = 65

GENERAL_WEIGHT = 0.20
CONFIRMATION_WEIGHT = 0.15
PULLBACK_WEIGHT = 0.30
INTRADAY_WEIGHT = 0.20
VWAP_WEIGHT = 0.10
VOLUME_WEIGHT = 0.05


# ============================================================
# BAŞLIK
# ============================================================

st.title("⚡ Günlük Trade Merkezi")

st.markdown(
    """
    **BIST500 → Likidite → Pullback → 15 Dakika Trend → VWAP → RSI → Hacim → Risk/Reward**
    
    Bu sayfa kısa vadeli günlük trade fırsatlarını tarar.
    """
)


# ============================================================
# VERİTABANI
# ============================================================

@st.cache_data(ttl=60)
def get_db_stocks():

    if not DB_PATH.exists():
        return pd.DataFrame()

    conn = sqlite3.connect(DB_PATH)

    tables = pd.read_sql_query(
        """
        SELECT name
        FROM sqlite_master
        WHERE type='table'
        """,
        conn,
    )["name"].tolist()

    if "stocks" not in tables:
        conn.close()
        return pd.DataFrame()

    df = pd.read_sql_query(
        "SELECT * FROM stocks",
        conn,
    )

    conn.close()

    return df


# ============================================================
# TICKER TEMİZLEME
# ============================================================

def normalize_ticker(value):

    if value is None:
        return None

    ticker = str(value).upper().strip()

    ticker = ticker.replace(".IS", "")
    ticker = ticker.replace(" BIST", "")
    ticker = ticker.replace("$", "")

    if ticker.endswith("."):
        ticker = ticker[:-1]

    if not ticker:
        return None

    return ticker


# ============================================================
# BIST500 EVRENİ
# ============================================================

def get_universe():

    df = get_db_stocks()

    if df.empty:
        return []

    possible_columns = [
        "symbol",
        "ticker",
        "code",
        "hisse",
        "hisse_kodu",
    ]

    column = None

    for c in possible_columns:
        if c in df.columns:
            column = c
            break

    if column is None:
        return []

    tickers = []

    for value in df[column].dropna():

        ticker = normalize_ticker(value)

        if ticker and ticker not in tickers:
            tickers.append(ticker)

    return tickers


# ============================================================
# YAHOO TICKER
# ============================================================

def yahoo_symbol(ticker):

    return f"{ticker}.IS"


# ============================================================
# TEKNİK GÖSTERGELER
# ============================================================

def calculate_indicators(df):

    if df is None or df.empty:
        return None

    df = df.copy()

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    required = ["Open", "High", "Low", "Close", "Volume"]

    for col in required:
        if col not in df.columns:
            return None

    df = df.dropna(subset=["Close"])

    if len(df) < 30:
        return None

    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    volume = df["Volume"]

    # --------------------------------------------------------
    # EMA
    # --------------------------------------------------------

    df["EMA5"] = close.ewm(span=5, adjust=False).mean()
    df["EMA9"] = close.ewm(span=9, adjust=False).mean()
    df["EMA20"] = close.ewm(span=20, adjust=False).mean()
    df["EMA50"] = close.ewm(span=50, adjust=False).mean()

    # --------------------------------------------------------
    # RSI
    # --------------------------------------------------------

    delta = close.diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)

    df["RSI"] = 100 - (100 / (1 + rs))

    # --------------------------------------------------------
    # Hacim
    # --------------------------------------------------------

    df["VOL20"] = volume.rolling(20).mean()

    df["VolumeRatio"] = (
        volume / df["VOL20"].replace(0, np.nan)
    )

    # --------------------------------------------------------
    # ATR
    # --------------------------------------------------------

    prev_close = close.shift(1)

    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()

    true_range = pd.concat(
        [tr1, tr2, tr3],
        axis=1
    ).max(axis=1)

    df["ATR"] = true_range.rolling(14).mean()

    # --------------------------------------------------------
    # VWAP
    # --------------------------------------------------------

    typical_price = (high + low + close) / 3

    cumulative_volume = volume.cumsum()

    cumulative_pv = (
        typical_price * volume
    ).cumsum()

    df["VWAP"] = (
        cumulative_pv /
        cumulative_volume.replace(0, np.nan)
    )

    return df


# ============================================================
# PULLBACK SKORU
# ============================================================

def calculate_pullback_score(row):

    price = float(row["Close"])
    ema9 = float(row["EMA9"])
    ema20 = float(row["EMA20"])

    score = 0

    # Fiyat EMA9 üzerinde
    if price >= ema9:
        score += 25

    # EMA9 - EMA20 trend
    if ema9 > ema20:
        score += 25

    # EMA9'a yakınlık
    distance = abs(price - ema9) / price * 100

    if distance <= 0.50:
        score += 30

    elif distance <= 1.00:
        score += 25

    elif distance <= 2.00:
        score += 15

    elif distance <= 3.00:
        score += 5

    # Fiyat EMA20 üzerinde
    if price > ema20:
        score += 20

    return min(score, 100)


# ============================================================
# 15 DAKİKA TREND
# ============================================================

def calculate_intraday():

    try:

        data = yf.download(
            period="5d",
            interval="15m",
            progress=False,
            auto_adjust=False,
            threads=False,
        )

        if data is None or data.empty:
            return None

        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)

        required = ["Open", "High", "Low", "Close", "Volume"]

        if not all(c in data.columns for c in required):
            return None

        data = data.dropna(subset=["Close"])

        if len(data) < 30:
            return None

        close = data["Close"]

        data["EMA9"] = close.ewm(
            span=9,
            adjust=False
        ).mean()

        data["EMA20"] = close.ewm(
            span=20,
            adjust=False
        ).mean()

        typical = (
            data["High"]
            + data["Low"]
            + data["Close"]
        ) / 3

        data["VWAP"] = (
            typical * data["Volume"]
        ).cumsum() / data["Volume"].cumsum()

        last = data.iloc[-1]

        score = 0

        if last["EMA9"] > last["EMA20"]:
            score += 40

        if last["Close"] > last["EMA9"]:
            score += 25

        if last["Close"] > last["VWAP"]:
            score += 25

        if len(data) >= 2:

            previous = data.iloc[-2]

            if last["Close"] > previous["Close"]:
                score += 10

        return {
            "score": min(score, 100),
            "price": float(last["Close"]),
            "ema9": float(last["EMA9"]),
            "ema20": float(last["EMA20"]),
            "vwap": float(last["VWAP"]),
        }

    except Exception:
        return None


# ============================================================
# TEKNİK SKOR
# ============================================================

def calculate_confirmation(row):

    score = 0

    price = float(row["Close"])
    ema9 = float(row["EMA9"])
    ema20 = float(row["EMA20"])
    ema50 = float(row["EMA50"])
    rsi = float(row["RSI"])
    volume_ratio = float(row["VolumeRatio"])

    # Trend
    if price > ema9:
        score += 20

    if ema9 > ema20:
        score += 20

    if ema20 > ema50:
        score += 15

    # RSI
    if 50 <= rsi <= 70:
        score += 20

    elif 45 <= rsi < 50:
        score += 10

    # Hacim
    if volume_ratio >= 1.50:
        score += 15

    elif volume_ratio >= 1.20:
        score += 10

    elif volume_ratio >= 1.00:
        score += 5

    # Momentum
    if price > float(row["Close"]) * 0.995:
        score += 10

    return min(score, 100)


# ============================================================
# DESTEK / DİRENÇ
# ============================================================

def calculate_support_resistance(df):

    recent = df.tail(20)

    support = float(recent["Low"].min())
    resistance = float(recent["High"].max())

    return support, resistance


# ============================================================
# RISK / REWARD
# ============================================================

def calculate_risk_reward(price, support, resistance, atr):

    if price <= 0:
        return 0, 0, 0, 0

    if atr <= 0:
        atr = price * 0.02

    stop = min(
        support,
        price - (1.2 * atr)
    )

    if stop <= 0 or stop >= price:
        stop = price * 0.97

    target = resistance

    if target <= price:
        target = price + (2 * atr)

    risk = price - stop
    reward = target - price

    if risk <= 0:
        rr = 0
    else:
        rr = reward / risk

    return (
        stop,
        target,
        risk,
        rr,
    )


# ============================================================
# TEK HİSSE ANALİZ
# ============================================================

def analyze_stock(ticker):

    try:

        symbol = yahoo_symbol(ticker)

        daily = yf.download(
            symbol,
            period=HISTORY_PERIOD,
            interval="1d",
            progress=False,
            auto_adjust=False,
            threads=False,
        )

        if daily is None or daily.empty:
            return None

        if isinstance(daily.columns, pd.MultiIndex):
            daily.columns = daily.columns.get_level_values(0)

        daily = calculate_indicators(daily)

        if daily is None or daily.empty:
            return None

        row = daily.iloc[-1]

        price = float(row["Close"])

        avg_volume = float(row["VOL20"])

        liquidity = price * avg_volume

        if liquidity < MIN_LIQUIDITY:
            return None

        pullback_score = calculate_pullback_score(row)

        confirmation_score = calculate_confirmation(row)

        intraday = calculate_intraday()

        if intraday is None:
            return None

        intraday_score = intraday["score"]

        vwap_score = 100 if price > float(row["VWAP"]) else 0

        volume_ratio = float(row["VolumeRatio"])

        if volume_ratio >= 1.50:
            volume_score = 100

        elif volume_ratio >= 1.20:
            volume_score = 80

        elif volume_ratio >= 1.00:
            volume_score = 60

        elif volume_ratio >= 0.80:
            volume_score = 40

        else:
            volume_score = 20

        # ----------------------------------------------------
        # DESTEK / DİRENÇ
        # ----------------------------------------------------

        support, resistance = calculate_support_resistance(
            daily
        )

        atr = float(row["ATR"])

        stop, target, risk, rr = calculate_risk_reward(
            price,
            support,
            resistance,
            atr,
        )

        # ----------------------------------------------------
        # GENEL SKOR
        # ----------------------------------------------------

        general_score = confirmation_score

        trade_score = (
            general_score * GENERAL_WEIGHT
            + confirmation_score * CONFIRMATION_WEIGHT
            + pullback_score * PULLBACK_WEIGHT
            + intraday_score * INTRADAY_WEIGHT
            + vwap_score * VWAP_WEIGHT
            + volume_score * VOLUME_WEIGHT
        )

        # ----------------------------------------------------
        # RISK/REWARD BONUS
        # ----------------------------------------------------

        if rr >= 3:
            trade_score += 5

        elif rr >= 2:
            trade_score += 3

        trade_score = min(trade_score, 100)

        # ----------------------------------------------------
        # KARAR
        # ----------------------------------------------------

        if (
            trade_score >= TRADE_THRESHOLD
            and pullback_score >= PULLBACK_THRESHOLD
            and intraday_score >= INTRADAY_THRESHOLD
            and price > float(row["EMA9"])
            and price > float(row["VWAP"])
            and rr >= 1.5
        ):
            decision = "🟢 GÜNLÜK AL"

        elif (
            trade_score >= 70
            and pullback_score >= 55
            and intraday_score >= 55
        ):
            decision = "🟡 İZLE"

        else:
            decision = "🔴 UYGUN DEĞİL"

        return {
            "Hisse": ticker,
            "Fiyat": price,
            "Likidite": liquidity,
            "Trade Skoru": round(trade_score, 1),
            "Pullback": round(pullback_score, 1),
            "15D Trend": round(intraday_score, 1),
            "Teyit": round(confirmation_score, 1),
            "VWAP": "ÜSTÜNDE" if price > float(row["VWAP"]) else "ALTINDA",
            "RSI": round(float(row["RSI"]), 1),
            "Hacim Oranı": round(volume_ratio, 2),
            "Destek": support,
            "Direnç": resistance,
            "Stop": stop,
            "Hedef": target,
            "R/R": round(rr, 2),
            "Karar": decision,
        }

    except Exception:
        return None


# ============================================================
# EVREN
# ============================================================

universe = get_universe()

if not universe:

    st.error(
        """
        ❌ `stocks` tablosunda hisse evreni bulunamadı.

        Önce **Veri Güncelleme** sayfasından BIST500 evrenini
        SQLite veritabanına yükleyin.
        """
    )

    st.stop()


# ============================================================
# ÜST PANEL
# ============================================================

c1, c2, c3, c4 = st.columns(4)

c1.metric(
    "BIST500 Evreni",
    f"{len(universe)}"
)

c2.metric(
    "Min. Likidite",
    f"{MIN_LIQUIDITY / 1_000_000:.0f} Mn TL"
)

c3.metric(
    "Trade Eşiği",
    f"{TRADE_THRESHOLD}"
)

c4.metric(
    "Tarama Tarihi",
    datetime.now().strftime("%d.%m.%Y %H:%M")
)


# ============================================================
# AYARLAR
# ============================================================

with st.expander("⚙️ Tarama Ayarları", expanded=False):

    col1, col2, col3 = st.columns(3)

    with col1:

        min_liquidity = st.number_input(
            "Minimum 20G Ortalama İşlem Hacmi (TL)",
            min_value=1_000_000,
            max_value=500_000_000,
            value=MIN_LIQUIDITY,
            step=5_000_000,
        )

    with col2:

        trade_threshold = st.slider(
            "Günlük AL Skoru",
            60,
            95,
            TRADE_THRESHOLD,
        )

    with col3:

        max_results = st.slider(
            "Gösterilecek Hisse",
            5,
            50,
            20,
        )


# ============================================================
# TARAMA
# ============================================================

st.markdown("---")

if st.button(
    "⚡ BIST500 GÜNLÜK TARAMAYI BAŞLAT",
    type="primary",
    use_container_width=True,
):

    results = []

    progress = st.progress(0)

    status = st.empty()

    total = len(universe)

    for i, ticker in enumerate(universe):

        status.text(
            f"🔎 Taranıyor: {ticker} "
            f"({i + 1}/{total})"
        )

        result = analyze_stock(ticker)

        if result is not None:

            results.append(result)

        progress.progress(
            int((i + 1) / total * 100)
        )

    progress.empty()

    status.empty()

    if not results:

        st.warning(
            "BIST500 içinde kriterleri karşılayan hisse bulunamadı."
        )

        st.stop()

    result_df = pd.DataFrame(results)

    result_df = result_df.sort_values(
        "Trade Skoru",
        ascending=False
    ).reset_index(drop=True)

    # --------------------------------------------------------
    # AL SİNYALLERİ
    # --------------------------------------------------------

    buy_df = result_df[
        result_df["Karar"] == "🟢 GÜNLÜK AL"
    ].copy()

    watch_df = result_df[
        result_df["Karar"] == "🟡 İZLE"
    ].copy()

    # --------------------------------------------------------
    # ÖZET
    # --------------------------------------------------------

    st.success(
        f"""
        Tarama tamamlandı.

        **BIST500:** {len(universe)}  
        **Likidite sonrası:** {len(result_df)}  
        **🟢 Günlük AL:** {len(buy_df)}  
        **🟡 İzle:** {len(watch_df)}
        """
    )

    # ========================================================
    # METRİKLER
    # ========================================================

    m1, m2, m3, m4 = st.columns(4)

    m1.metric(
        "Taranan",
        len(universe)
    )

    m2.metric(
        "Uygun",
        len(result_df)
    )

    m3.metric(
        "⚡ Günlük AL",
        len(buy_df)
    )

    if not result_df.empty:

        best_score = result_df["Trade Skoru"].max()

    else:

        best_score = 0

    m4.metric(
        "🏆 En Yüksek Skor",
        f"{best_score:.1f}"
    )


    # ========================================================
    # GÜNLÜK AL
    # ========================================================

    st.markdown("---")

    st.subheader("🟢 Günlük Trade Fırsatları")

    if buy_df.empty:

        st.info(
            "Şu anda tüm kriterleri aynı anda sağlayan güçlü bir günlük AL sinyali yok."
        )

    else:

        display_buy = buy_df.head(max_results).copy()

        st.dataframe(
            display_buy[
                [
                    "Hisse",
                    "Fiyat",
                    "Trade Skoru",
                    "Pullback",
                    "15D Trend",
                    "Teyit",
                    "VWAP",
                    "RSI",
                    "Hacim Oranı",
                    "Destek",
                    "Direnç",
                    "Stop",
                    "Hedef",
                    "R/R",
                    "Karar",
                ]
            ],
            use_container_width=True,
            hide_index=True,
        )


    # ========================================================
    # EN İYİ ADAYLAR
    # ========================================================

    st.markdown("---")

    st.subheader("🏆 En Güçlü Günlük Trade Adayları")

    top_df = result_df.head(max_results).copy()

    st.dataframe(
        top_df[
            [
                "Hisse",
                "Fiyat",
                "Trade Skoru",
                "Pullback",
                "15D Trend",
                "Teyit",
                "VWAP",
                "RSI",
                "Hacim Oranı",
                "R/R",
                "Karar",
            ]
        ],
        use_container_width=True,
        hide_index=True,
    )


    # ========================================================
    # DETAYLI HİSSE
    # ========================================================

    st.markdown("---")

    st.subheader("🔍 Trade Detayı")

    selected = st.selectbox(
        "Hisse seç",
        result_df["Hisse"].tolist(),
    )

    selected_row = result_df[
        result_df["Hisse"] == selected
    ].iloc[0]

    d1, d2, d3, d4 = st.columns(4)

    d1.metric(
        "Trade Skoru",
        f"{selected_row['Trade Skoru']:.1f}"
    )

    d2.metric(
        "Pullback",
        f"{selected_row['Pullback']:.1f}"
    )

    d3.metric(
        "15D Trend",
        f"{selected_row['15D Trend']:.1f}"
    )

    d4.metric(
        "Risk / Ödül",
        f"{selected_row['R/R']:.2f}"
    )

    st.markdown("### 📌 Trade Planı")

    plan1, plan2, plan3, plan4 = st.columns(4)

    plan1.metric(
        "Giriş",
        f"{selected_row['Fiyat']:.2f} TL"
    )

    plan2.metric(
        "Stop",
        f"{selected_row['Stop']:.2f} TL"
    )

    plan3.metric(
        "Hedef",
        f"{selected_row['Hedef']:.2f} TL"
    )

    plan4.metric(
        "R/R",
        f"{selected_row['R/R']:.2f}"
    )

    # ========================================================
    # KONTROL LİSTESİ
    # ========================================================

    st.markdown("### ✅ Trade Kontrol Listesi")

    price = selected_row["Fiyat"]
    support = selected_row["Destek"]
    resistance = selected_row["Direnç"]

    checklist = {
        "Likidite yeterli": selected_row["Likidite"] >= min_liquidity,
        "Pullback güçlü": selected_row["Pullback"] >= PULLBACK_THRESHOLD,
        "15D trend pozitif": selected_row["15D Trend"] >= INTRADAY_THRESHOLD,
        "VWAP üzerinde": selected_row["VWAP"] == "ÜSTÜNDE",
        "RSI uygun": 45 <= selected_row["RSI"] <= 70,
        "Hacim destekli": selected_row["Hacim Oranı"] >= 1.0,
        "Risk / Ödül uygun": selected_row["R/R"] >= 1.5,
        "Direnç mesafesi mevcut": resistance > price,
        "Destek altında değil": support < price,
    }

    for name, passed in checklist.items():

        if passed:
            st.success(f"🟢 {name}")

        else:
            st.warning(f"🟠 {name}")


    # ========================================================
    # CSV
    # ========================================================

    csv = result_df.to_csv(
        index=False,
        encoding="utf-8-sig"
    )

    st.download_button(
        "📥 Tarama Sonuçlarını Excel/CSV İçin İndir",
        data=csv,
        file_name=(
            f"gunluk_trade_"
            f"{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
        ),
        mime="text/csv",
        use_container_width=True,
    )


# ============================================================
# ALT BİLGİ
# ============================================================

st.markdown("---")

st.caption(
    """
    ⚠️ Bu modül yatırım tavsiyesi değildir.
    Günlük trade sinyali; teknik göstergeler, likidite,
    momentum, intraday trend ve risk/ödül kriterlerinin
    birlikte değerlendirilmesiyle oluşturulur.
    """
)