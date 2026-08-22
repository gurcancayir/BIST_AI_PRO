# ============================================================
# CRYPTO AI PRO
# 08_Crypto_Gunluk_Trade.py
#
# PROFESYONEL GÜNLÜK TRADE KARAR MOTORU
#
# ANA PRENSİP
# ------------------------------------------------------------
# GÜÇLÜ COİN ≠ OTOMATİK AL
#
# Sistem:
#
# Ortak TRY Evreni
#       ↓
# Likidite
#       ↓
# Momentum
#       ↓
# Trend
#       ↓
# RSI
#       ↓
# Hacim
#       ↓
# Giriş Kalitesi
#       ↓
# Breakout
#       ↓
# Kovalama Riski
#       ↓
# Risk / Ödül
#       ↓
# Fırsat Havuzu
#       ↓
# Final Karar
#
# KARARLAR
# ------------------------------------------------------------
# 🟢 GÜNLÜK AL
# 🟢 BREAKOUT AL
# 🟡 GİRİŞ BEKLE
# 🟡 BREAKOUT TEYİDİ BEKLE
# 🟡 TEYİT BEKLE
# 🔴 KOVALAMA
# 🔴 İŞLEM YOK
#
# ÖNEMLİ
# ------------------------------------------------------------
# Coin evreni crypto_engine.get_all_try_universe()
# üzerinden gelir.
#
# Böylece Günlük Trade ile Kripto Piyasa aynı coin
# evrenini kullanır.
#
# ============================================================

import streamlit as st
import pandas as pd
import numpy as np
import requests
import importlib
from datetime import datetime

import crypto_engine


# ============================================================
# SAYFA AYARLARI
# ============================================================

st.set_page_config(
    page_title="Kripto Günlük Trade PRO",
    page_icon="⚡",
    layout="wide",
)


# ============================================================
# ENGINE YENİLE
# ============================================================

crypto_engine = importlib.reload(
    crypto_engine
)


# ============================================================
# BAŞLIK
# ============================================================

st.title("⚡ Kripto Günlük Trade PRO")

st.caption(
    "CRYPTO AI PRO | Ortak TRY Evreni | "
    "Profesyonel Günlük Trade Karar Motoru"
)

st.write(
    "Amaç sadece en güçlü coinleri bulmak değil; "
    "aynı zamanda işlem yapılabilir giriş bölgesindeki "
    "coinleri tespit etmektir."
)


# ============================================================
# AYARLAR
# ============================================================

MIN_VOLUME_TRY = 100_000_000

MAX_ANALYSIS = 50

KLINE_INTERVAL = "15m"
KLINE_LIMIT = 100

FINAL_BUY_SCORE = 80
BREAKOUT_BUY_SCORE = 78

OPPORTUNITY_SCORE = 65
WATCH_SCORE = 55

MIN_VOLUME_RATIO = 1.15
MIN_BREAKOUT_VOLUME_RATIO = 1.25

MAX_CHASE_FOR_BUY = 55

MAX_DAILY_CHANGE_FOR_NORMAL_ENTRY = 18

KLINE_URL = (
    "https://api.binance.me/api/v3/klines"
)


# ============================================================
# CACHE TEMİZLEME
# ============================================================

with st.sidebar:

    st.subheader("⚙️ Trade Ayarları")

    st.caption(
        "Motor ortak TRY evreni üzerinden çalışır."
    )

    if st.button(
        "🔄 Veriyi Yenile",
        use_container_width=True
    ):

        st.cache_data.clear()

        st.rerun()


# ============================================================
# YARDIMCI FONKSİYONLAR
# ============================================================

def safe_float(value, default=0.0):

    try:

        if value is None:
            return default

        value = float(value)

        if np.isnan(value):
            return default

        return value

    except Exception:

        return default


def clamp(
    value,
    low=0,
    high=100
):

    return max(
        low,
        min(
            high,
            safe_float(value)
        )
    )


def fmt_price(price):

    price = safe_float(price)

    if price >= 1000:

        return f"{price:,.2f}"

    if price >= 100:

        return f"{price:,.3f}"

    if price >= 1:

        return f"{price:,.4f}"

    if price >= 0.01:

        return f"{price:.5f}"

    return f"{price:.8f}"


def fmt_money(value):

    value = safe_float(value)

    if value >= 1_000_000_000:

        return (
            f"₺{value / 1_000_000_000:.2f} Mr"
        )

    if value >= 1_000_000:

        return (
            f"₺{value / 1_000_000:.1f} Mn"
        )

    if value >= 1_000:

        return (
            f"₺{value / 1_000:.0f} Bin"
        )

    return f"₺{value:,.0f}"


# ============================================================
# RSI
# ============================================================

def calculate_rsi(
    series,
    period=14
):

    series = pd.Series(
        series
    ).astype(float)

    delta = series.diff()

    gain = delta.clip(
        lower=0
    )

    loss = -delta.clip(
        upper=0
    )

    avg_gain = gain.rolling(
        period
    ).mean()

    avg_loss = loss.rolling(
        period
    ).mean()

    rs = (
        avg_gain /
        avg_loss.replace(
            0,
            np.nan
        )
    )

    return (
        100 -
        (
            100 /
            (1 + rs)
        )
    )


# ============================================================
# EMA
# ============================================================

def calculate_ema(
    series,
    period
):

    return pd.Series(
        series
    ).ewm(
        span=period,
        adjust=False
    ).mean()


# ============================================================
# ATR
# ============================================================

def calculate_atr(
    df,
    period=14
):

    high = df["high"]
    low = df["low"]
    close = df["close"]

    prev_close = close.shift(1)

    tr1 = high - low

    tr2 = (
        high -
        prev_close
    ).abs()

    tr3 = (
        low -
        prev_close
    ).abs()

    tr = pd.concat(
        [
            tr1,
            tr2,
            tr3
        ],
        axis=1
    ).max(axis=1)

    return tr.rolling(
        period
    ).mean()


# ============================================================
# ORTAK TRY EVRENİ
# ============================================================

@st.cache_data(ttl=60)
def get_common_universe():

    try:

        raw = (
            crypto_engine
            .get_all_try_universe()
        )

    except Exception as e:

        st.error(
            "Kripto piyasa verisi alınamadı."
        )

        st.caption(
            f"Engine hatası: {e}"
        )

        return pd.DataFrame()

    if raw is None:

        return pd.DataFrame()

    if isinstance(
        raw,
        pd.DataFrame
    ):

        df = raw.copy()

    elif isinstance(
        raw,
        list
    ):

        if not raw:

            return pd.DataFrame()

        if isinstance(
            raw[0],
            dict
        ):

            df = pd.DataFrame(
                raw
            )

        else:

            df = pd.DataFrame(
                {
                    "symbol": raw
                }
            )

    else:

        return pd.DataFrame()

    if df.empty:

        return df

    # --------------------------------------------------------
    # SYMBOL
    # --------------------------------------------------------

    if "symbol" not in df.columns:

        possible = [
            "pair",
            "name",
            "code"
        ]

        found = None

        for col in possible:

            if col in df.columns:

                found = col
                break

        if found:

            df["symbol"] = (
                df[found]
                .astype(str)
            )

        else:

            return pd.DataFrame()

    # --------------------------------------------------------
    # SYMBOL TEMİZLE
    # --------------------------------------------------------

    df["symbol"] = (
        df["symbol"]
        .astype(str)
        .str.upper()
        .str.strip()
    )

    # --------------------------------------------------------
    # SADECE TRY
    # --------------------------------------------------------

    df = df[
        df["symbol"].str.contains(
            "TRY",
            na=False
        )
    ].copy()

    # --------------------------------------------------------
    # BASE ASSET
    # --------------------------------------------------------

    if "base_asset" not in df.columns:

        df["base_asset"] = (
            df["symbol"]
            .str.replace(
                "_TRY",
                "",
                regex=False
            )
            .str.replace(
                "TRY",
                "",
                regex=False
            )
            .str.replace(
                "/",
                "",
                regex=False
            )
        )

    # --------------------------------------------------------
    # TEKRARLARI SİL
    # --------------------------------------------------------

    df = df.drop_duplicates(
        subset=["symbol"]
    )

    # --------------------------------------------------------
    # SADECE GEÇERLİ FİYAT
    # --------------------------------------------------------

    if "price_try" in df.columns:

        df["price_try"] = pd.to_numeric(
            df["price_try"],
            errors="coerce"
        )

        df = df[
            df["price_try"] > 0
        ]

    # --------------------------------------------------------
    # HACİM
    # --------------------------------------------------------

    if "volume_try" in df.columns:

        df["volume_try"] = pd.to_numeric(
            df["volume_try"],
            errors="coerce"
        ).fillna(0)

        df = df[
            df["volume_try"] >=
            MIN_VOLUME_TRY
        ]

    # --------------------------------------------------------
    # DEĞİŞİM
    # --------------------------------------------------------

    if "change_24h" in df.columns:

        df["change_24h"] = pd.to_numeric(
            df["change_24h"],
            errors="coerce"
        ).fillna(0)

    # --------------------------------------------------------
    # HACME GÖRE SIRALA
    # --------------------------------------------------------

    if "volume_try" in df.columns:

        df = df.sort_values(
            "volume_try",
            ascending=False
        )

    return (
        df.head(MAX_ANALYSIS)
        .reset_index(drop=True)
    )


# ============================================================
# SYMBOL'Ü KLINE FORMATINA ÇEVİR
# ============================================================

def normalize_kline_symbol(
    symbol
):

    symbol = (
        str(symbol)
        .upper()
        .strip()
    )

    symbol = (
        symbol
        .replace(
            "_TRY",
            "TRY"
        )
        .replace(
            "/TRY",
            "TRY"
        )
        .replace(
            "-TRY",
            "TRY"
        )
    )

    if not symbol.endswith("TRY"):

        symbol += "TRY"

    return symbol


# ============================================================
# KLINE
# ============================================================

@st.cache_data(ttl=60)
def get_klines(symbol):

    try:

        api_symbol = (
            normalize_kline_symbol(
                symbol
            )
        )

        params = {

            "symbol": api_symbol,

            "interval":
                KLINE_INTERVAL,

            "limit":
                KLINE_LIMIT,
        }

        response = requests.get(
            KLINE_URL,
            params=params,
            timeout=8
        )

        response.raise_for_status()

        data = response.json()

        if not isinstance(
            data,
            list
        ):

            return pd.DataFrame()

        if not data:

            return pd.DataFrame()

        rows = []

        for item in data:

            if len(item) < 6:

                continue

            rows.append(
                {
                    "open_time":
                        item[0],

                    "open":
                        safe_float(item[1]),

                    "high":
                        safe_float(item[2]),

                    "low":
                        safe_float(item[3]),

                    "close":
                        safe_float(item[4]),

                    "volume":
                        safe_float(item[5]),
                }
            )

        df = pd.DataFrame(
            rows
        )

        if df.empty:

            return df

        df["ema9"] = calculate_ema(
            df["close"],
            9
        )

        df["ema20"] = calculate_ema(
            df["close"],
            20
        )

        df["ema50"] = calculate_ema(
            df["close"],
            50
        )

        df["rsi"] = calculate_rsi(
            df["close"],
            14
        )

        df["atr"] = calculate_atr(
            df,
            14
        )

        return df

    except Exception:

        return pd.DataFrame()


# ============================================================
# TEKNİK YAPI
# ============================================================

def analyze_technical(
    row,
    klines
):

    price = safe_float(
        row.get(
            "price_try",
            0
        )
    )

    change = safe_float(
        row.get(
            "change_24h",
            0
        )
    )

    # --------------------------------------------------------
    # KLINE YOK
    # --------------------------------------------------------

    if klines.empty:

        return {

            "ema9":
                price,

            "ema20":
                price,

            "ema50":
                price,

            "rsi":
                50,

            "atr":
                price * 0.03,

            "support":
                price * 0.94,

            "resistance":
                price * 1.03,

            "volume_ratio":
                1.0,

            "trend_score":
                50,

            "breakout_score":
                0,

            "technical_score":
                50,
        }

    last = klines.iloc[-1]

    ema9 = safe_float(
        last["ema9"],
        price
    )

    ema20 = safe_float(
        last["ema20"],
        price
    )

    ema50 = safe_float(
        last["ema50"],
        price
    )

    rsi = safe_float(
        last["rsi"],
        50
    )

    atr = safe_float(
        last["atr"],
        price * 0.03
    )

    # --------------------------------------------------------
    # SON 12 SAAT
    # --------------------------------------------------------

    lookback = klines.iloc[
        -49:-1
    ]

    if lookback.empty:

        resistance = price * 1.03
        support = price * 0.94

    else:

        resistance = safe_float(
            lookback["high"].max(),
            price * 1.03
        )

        support = safe_float(
            lookback["low"].min(),
            price * 0.94
        )

    # --------------------------------------------------------
    # HACİM ORANI
    # --------------------------------------------------------

    previous_volume = (
        klines["volume"]
        .iloc[-21:-1]
        .mean()
    )

    current_volume = safe_float(
        last["volume"]
    )

    if previous_volume > 0:

        volume_ratio = (
            current_volume /
            previous_volume
        )

    else:

        volume_ratio = 1

    # --------------------------------------------------------
    # TREND
    # --------------------------------------------------------

    trend_score = 40

    if price > ema9:

        trend_score += 12

    if ema9 > ema20:

        trend_score += 16

    if ema20 > ema50:

        trend_score += 16

    if price > ema50:

        trend_score += 10

    trend_score = clamp(
        trend_score
    )

    # --------------------------------------------------------
    # RSI SKORU
    # --------------------------------------------------------

    if 55 <= rsi <= 68:

        rsi_score = 95

    elif 68 < rsi <= 73:

        rsi_score = 82

    elif 73 < rsi <= 78:

        rsi_score = 65

    elif rsi > 78:

        rsi_score = 35

    elif 45 <= rsi < 55:

        rsi_score = 65

    else:

        rsi_score = 40

    # --------------------------------------------------------
    # BREAKOUT
    # --------------------------------------------------------

    breakout_score = 0

    if price >= resistance * 1.002:

        breakout_score += 40

    elif price >= resistance * 0.997:

        breakout_score += 28

    elif price >= resistance * 0.985:

        breakout_score += 15

    if volume_ratio >= 2:

        breakout_score += 30

    elif volume_ratio >= 1.5:

        breakout_score += 24

    elif volume_ratio >= 1.25:

        breakout_score += 18

    elif volume_ratio >= 1.0:

        breakout_score += 10

    breakout_score += (
        trend_score * 0.20
    )

    if 55 <= rsi <= 72:

        breakout_score += 15

    elif 72 < rsi <= 78:

        breakout_score += 7

    elif rsi > 78:

        breakout_score -= 10

    breakout_score = clamp(
        breakout_score
    )

    # --------------------------------------------------------
    # TEKNİK SKOR
    # --------------------------------------------------------

    volume_score = clamp(
        volume_ratio * 35
    )

    technical_score = (

        trend_score * 0.45

        + rsi_score * 0.20

        + volume_score * 0.15

        + breakout_score * 0.20
    )

    technical_score = clamp(
        technical_score
    )

    return {

        "ema9":
            ema9,

        "ema20":
            ema20,

        "ema50":
            ema50,

        "rsi":
            rsi,

        "atr":
            atr,

        "support":
            support,

        "resistance":
            resistance,

        "volume_ratio":
            volume_ratio,

        "trend_score":
            trend_score,

        "breakout_score":
            breakout_score,

        "technical_score":
            technical_score,
    }


# ============================================================
# PRO GÜÇ SKORU
# ============================================================

def calculate_power_score(
    row,
    technical
):

    change = safe_float(
        row.get(
            "change_24h",
            0
        )
    )

    volume = safe_float(
        row.get(
            "volume_try",
            0
        )
    )

    technical_score = (
        technical[
            "technical_score"
        ]
    )

    # --------------------------------------------------------
    # MOMENTUM
    # --------------------------------------------------------

    if change >= 25:

        momentum = 100

    elif change >= 20:

        momentum = 96

    elif change >= 15:

        momentum = 92

    elif change >= 10:

        momentum = 86

    elif change >= 7:

        momentum = 80

    elif change >= 5:

        momentum = 74

    elif change >= 3:

        momentum = 68

    elif change >= 0:

        momentum = 58

    else:

        momentum = 40

    # --------------------------------------------------------
    # LİKİDİTE
    # --------------------------------------------------------

    if volume >= 2_000_000_000:

        liquidity = 100

    elif volume >= 1_000_000_000:

        liquidity = 95

    elif volume >= 500_000_000:

        liquidity = 90

    elif volume >= 250_000_000:

        liquidity = 82

    elif volume >= 100_000_000:

        liquidity = 70

    else:

        liquidity = 50

    score = (

        momentum * 0.35

        + liquidity * 0.25

        + technical_score * 0.40
    )

    return clamp(
        score
    )


# ============================================================
# GİRİŞ KALİTESİ
# ============================================================

def calculate_entry_quality(
    row,
    technical
):

    price = safe_float(
        row.get(
            "price_try",
            0
        )
    )

    high = safe_float(
        row.get(
            "high_24h",
            price
        )
    )

    low = safe_float(
        row.get(
            "low_24h",
            price
        )
    )

    change = safe_float(
        row.get(
            "change_24h",
            0
        )
    )

    rsi = safe_float(
        technical["rsi"],
        50
    )

    # --------------------------------------------------------
    # GÜNLÜK RANGE POZİSYONU
    # --------------------------------------------------------

    if high > low:

        position = (
            (price - low)
            /
            (high - low)
        ) * 100

    else:

        position = 50

    position = clamp(
        position
    )

    if position >= 95:

        position_score = 35

    elif position >= 90:

        position_score = 48

    elif position >= 80:

        position_score = 62

    elif position >= 70:

        position_score = 72

    elif position >= 50:

        position_score = 88

    elif position >= 30:

        position_score = 82

    else:

        position_score = 70

    # --------------------------------------------------------
    # RSI
    # --------------------------------------------------------

    if 52 <= rsi <= 65:

        rsi_score = 95

    elif 65 < rsi <= 70:

        rsi_score = 88

    elif 70 < rsi <= 75:

        rsi_score = 72

    elif 75 < rsi <= 80:

        rsi_score = 50

    elif rsi > 80:

        rsi_score = 30

    else:

        rsi_score = 55

    # --------------------------------------------------------
    # GÜNLÜK MOMENTUM
    # --------------------------------------------------------

    if 3 <= change <= 8:

        momentum_score = 95

    elif 8 < change <= 12:

        momentum_score = 85

    elif 12 < change <= 15:

        momentum_score = 72

    elif 15 < change <= 20:

        momentum_score = 58

    elif change > 20:

        momentum_score = 35

    elif 0 <= change < 3:

        momentum_score = 65

    else:

        momentum_score = 45

    score = (

        position_score * 0.40

        + rsi_score * 0.30

        + momentum_score * 0.30
    )

    return clamp(
        score
    )


# ============================================================
# KOVALAMA SKORU
# ============================================================

def calculate_chase_score(
    row,
    technical
):

    change = safe_float(
        row.get(
            "change_24h",
            0
        )
    )

    price = safe_float(
        row.get(
            "price_try",
            0
        )
    )

    high = safe_float(
        row.get(
            "high_24h",
            price
        )
    )

    low = safe_float(
        row.get(
            "low_24h",
            price
        )
    )

    rsi = safe_float(
        technical["rsi"],
        50
    )

    if high > low:

        position = (
            (price - low)
            /
            (high - low)
        ) * 100

    else:

        position = 50

    score = 0

    # --------------------------------------------------------
    # GÜNLÜK YÜKSELİŞ
    # --------------------------------------------------------

    if change >= 30:

        score += 45

    elif change >= 25:

        score += 38

    elif change >= 20:

        score += 30

    elif change >= 15:

        score += 22

    elif change >= 10:

        score += 14

    elif change >= 7:

        score += 7

    # --------------------------------------------------------
    # GÜNLÜK ZİRVE
    # --------------------------------------------------------

    if position >= 95:

        score += 30

    elif position >= 90:

        score += 24

    elif position >= 80:

        score += 16

    elif position >= 70:

        score += 8

    # --------------------------------------------------------
    # RSI
    # --------------------------------------------------------

    if rsi >= 85:

        score += 30

    elif rsi >= 80:

        score += 22

    elif rsi >= 75:

        score += 12

    return clamp(
        score
    )


# ============================================================
# RİSK / ÖDÜL
# ============================================================

def calculate_trade_levels(
    row,
    technical
):

    price = safe_float(
        row.get(
            "price_try",
            0
        )
    )

    support = safe_float(
        technical["support"],
        price * 0.94
    )

    resistance = safe_float(
        technical["resistance"],
        price * 1.03
    )

    atr = safe_float(
        technical["atr"],
        price * 0.03
    )

    # --------------------------------------------------------
    # STOP
    # --------------------------------------------------------

    atr_stop = (
        price -
        atr * 1.5
    )

    support_stop = (
        support * 0.995
    )

    stop = min(
        atr_stop,
        support_stop
    )

    # Çok geniş stopu sınırlıyoruz
    max_stop = price * 0.88

    if stop < max_stop:

        stop = max_stop

    # Çok dar stopu da engelliyoruz
    min_stop = price * 0.94

    if stop > min_stop:

        stop = min_stop

    risk = (
        price -
        stop
    )

    if risk <= 0:

        risk = price * 0.06

        stop = (
            price -
            risk
        )

    # --------------------------------------------------------
    # HEDEF
    # --------------------------------------------------------

    target1 = (
        price +
        risk * 2
    )

    target2 = (
        price +
        risk * 3
    )

    # --------------------------------------------------------
    # GİRİŞ BÖLGESİ
    # --------------------------------------------------------

    entry_low = (
        price * 0.995
    )

    entry_high = (
        price * 1.005
    )

    rr = (
        target1 -
        price
    ) / risk

    return {

        "entry_low":
            entry_low,

        "entry_high":
            entry_high,

        "stop":
            stop,

        "target1":
            target1,

        "target2":
            target2,

        "resistance":
            resistance,

        "risk_pct":
            (
                risk /
                price
            ) * 100
            if price > 0
            else 0,

        "rr":
            rr,
    }


# ============================================================
# BREAKOUT MOTORU
# ============================================================

def evaluate_breakout(
    row,
    technical,
    chase_score
):

    price = safe_float(
        row.get(
            "price_try",
            0
        )
    )

    resistance = safe_float(
        technical["resistance"],
        price
    )

    volume_ratio = safe_float(
        technical["volume_ratio"],
        1
    )

    breakout_score = safe_float(
        technical["breakout_score"]
    )

    rsi = safe_float(
        technical["rsi"],
        50
    )

    trend = safe_float(
        technical["trend_score"]
    )

    broken = (
        price >
        resistance * 1.002
    )

    near_breakout = (
        price >=
        resistance * 0.995
        and
        price <=
        resistance * 1.015
    )

    volume_confirmed = (
        volume_ratio >=
        MIN_BREAKOUT_VOLUME_RATIO
    )

    rsi_ok = (
        52 <= rsi <= 78
    )

    trend_ok = (
        trend >= 70
    )

    chase_ok = (
        chase_score < 60
    )

    # --------------------------------------------------------
    # GERÇEK BREAKOUT
    # --------------------------------------------------------

    if (

        broken

        and volume_confirmed

        and rsi_ok

        and trend_ok

        and chase_ok

        and breakout_score >= 70

    ):

        return (
            "BREAKOUT",
            "Direnç kırıldı. Hacim, trend ve RSI teyidi mevcut."
        )

    # --------------------------------------------------------
    # BREAKOUT TEYİDİ
    # --------------------------------------------------------

    if (

        near_breakout

        and breakout_score >= 55

    ):

        return (
            "WAIT_BREAKOUT",
            "Direnç bölgesinde. Kırılım ve hacim teyidi bekleniyor."
        )

    return (
        "NO_BREAKOUT",
        "Breakout teyidi oluşmadı."
    )


# ============================================================
# FIRSAT SINIFI
# ============================================================

def classify_opportunity(
    power,
    entry,
    technical,
    chase,
    final_score
):

    trend = technical[
        "trend_score"
    ]

    volume_ratio = technical[
        "volume_ratio"
    ]

    breakout = technical[
        "breakout_score"
    ]

    if (

        final_score >= 75

        and power >= 78

        and entry >= 72

        and chase < 55

    ):

        return "🟢 A SINIFI FIRSAT"

    if (

        final_score >= 68

        and power >= 72

        and (
            entry >= 62
            or breakout >= 65
        )

        and chase < 65

    ):

        return "🟡 B SINIFI FIRSAT"

    if (

        power >= 65

        and trend >= 60

        and volume_ratio >= 1

    ):

        return "🟠 C SINIFI İZLE"

    return "⚪ ZAYIF"


# ============================================================
# FINAL KARAR MOTORU
# ============================================================

def calculate_final_decision(
    row,
    technical,
    power_score,
    entry_quality,
    chase_score,
    levels
):

    volume_ratio = safe_float(
        technical[
            "volume_ratio"
        ],
        1
    )

    technical_score = safe_float(
        technical[
            "technical_score"
        ]
    )

    # --------------------------------------------------------
    # GÜNLÜK TRADE SKORU
    # --------------------------------------------------------

    daily_trade = (

        technical_score * 0.40

        + entry_quality * 0.30

        + (
            100 -
            chase_score
        ) * 0.15

        + min(
            volume_ratio * 40,
            100
        ) * 0.15
    )

    daily_trade = clamp(
        daily_trade
    )

    # --------------------------------------------------------
    # BREAKOUT
    # --------------------------------------------------------

    breakout_status, breakout_reason = (
        evaluate_breakout(
            row,
            technical,
            chase_score
        )
    )

    # --------------------------------------------------------
    # FINAL
    # --------------------------------------------------------

    final_score = (

        power_score * 0.30

        + daily_trade * 0.30

        + entry_quality * 0.20

        + 90 * 0.10

        + (
            100 -
            chase_score
        ) * 0.10
    )

    final_score = clamp(
        final_score
    )

    # --------------------------------------------------------
    # SINIF
    # --------------------------------------------------------

    opportunity = classify_opportunity(
        power_score,
        entry_quality,
        technical,
        chase_score,
        final_score
    )

    # --------------------------------------------------------
    # KOVALAMA
    # --------------------------------------------------------

    if chase_score >= 75:

        return (
            daily_trade,
            final_score,
            opportunity,
            "🔴 KOVALAMA",
            "Fiyat güçlü ancak mevcut seviyeden giriş riski yüksek.",
            breakout_status
        )

    # --------------------------------------------------------
    # BREAKOUT AL
    # --------------------------------------------------------

    if (

        breakout_status ==
        "BREAKOUT"

        and final_score >=
        BREAKOUT_BUY_SCORE

        and power_score >= 72

    ):

        return (
            daily_trade,
            final_score,
            opportunity,
            "🟢 BREAKOUT AL",
            breakout_reason,
            breakout_status
        )

    # --------------------------------------------------------
    # BREAKOUT TEYİDİ
    # --------------------------------------------------------

    if (

        breakout_status ==
        "WAIT_BREAKOUT"

        and final_score >=
        OPPORTUNITY_SCORE

    ):

        return (
            daily_trade,
            final_score,
            opportunity,
            "🟡 BREAKOUT TEYİDİ BEKLE",
            breakout_reason,
            breakout_status
        )

    # --------------------------------------------------------
    # NORMAL GÜNLÜK AL
    # --------------------------------------------------------

    if (

        final_score >=
        FINAL_BUY_SCORE

        and power_score >= 75

        and entry_quality >= 72

        and chase_score <
        MAX_CHASE_FOR_BUY

        and levels["rr"] >= 2

    ):

        return (
            daily_trade,
            final_score,
            opportunity,
            "🟢 GÜNLÜK AL",
            "Güç, giriş kalitesi, teknik yapı ve risk/getiri birlikte uygun.",
            breakout_status
        )

    # --------------------------------------------------------
    # GİRİŞ BEKLE
    # --------------------------------------------------------

    if (

        power_score >= 75

        and entry_quality < 72

        and chase_score < 70

    ):

        return (
            daily_trade,
            final_score,
            opportunity,
            "🟡 GİRİŞ BEKLE",
            "Coin güçlü ancak mevcut fiyat daha iyi bir giriş için uygun değil.",
            breakout_status
        )

    # --------------------------------------------------------
    # TEYİT
    # --------------------------------------------------------

    if (

        final_score >=
        WATCH_SCORE

        and power_score >= 65

    ):

        return (
            daily_trade,
            final_score,
            opportunity,
            "🟡 TEYİT BEKLE",
            "Setup oluşuyor ancak işlem için ek teyit gerekiyor.",
            breakout_status
        )

    # --------------------------------------------------------
    # İŞLEM YOK
    # --------------------------------------------------------

    return (
        daily_trade,
        final_score,
        opportunity,
        "🔴 İŞLEM YOK",
        "Mevcut koşullarda yeterli trade avantajı bulunamadı.",
        breakout_status
    )


# ============================================================
# PİYASAYI ANALİZ ET
# ============================================================

def analyze_market(df):

    results = []

    progress = st.progress(
        0,
        text="50 coin analiz ediliyor..."
    )

    total = len(df)

    for index, (_, row) in enumerate(
        df.iterrows()
    ):

        symbol = row[
            "symbol"
        ]

        klines = get_klines(
            symbol
        )

        technical = analyze_technical(
            row,
            klines
        )

        power_score = calculate_power_score(
            row,
            technical
        )

        entry_quality = calculate_entry_quality(
            row,
            technical
        )

        chase_score = calculate_chase_score(
            row,
            technical
        )

        levels = calculate_trade_levels(
            row,
            technical
        )

        (
            daily_trade,
            final_score,
            opportunity,
            decision,
            reason,
            breakout_status
        ) = calculate_final_decision(

            row,

            technical,

            power_score,

            entry_quality,

            chase_score,

            levels
        )

        results.append(

            {
                "Coin":
                    row.get(
                        "base_asset",
                        symbol
                    ),

                "Parite":
                    symbol,

                "Fiyat":
                    safe_float(
                        row.get(
                            "price_try"
                        )
                    ),

                "Günlük %":
                    safe_float(
                        row.get(
                            "change_24h"
                        )
                    ),

                "Hacim":
                    safe_float(
                        row.get(
                            "volume_try"
                        )
                    ),

                "PRO Güç":
                    round(
                        power_score,
                        1
                    ),

                "Günlük Trade":
                    round(
                        daily_trade,
                        1
                    ),

                "Giriş Kalitesi":
                    round(
                        entry_quality,
                        1
                    ),

                "Trend":
                    round(
                        technical[
                            "trend_score"
                        ],
                        1
                    ),

                "Breakout":
                    round(
                        technical[
                            "breakout_score"
                        ],
                        1
                    ),

                "Hacim Oranı":
                    round(
                        technical[
                            "volume_ratio"
                        ],
                        2
                    ),

                "RSI":
                    round(
                        technical[
                            "rsi"
                        ],
                        1
                    ),

                "Kovalama":
                    round(
                        chase_score,
                        1
                    ),

                "Direnç":
                    technical[
                        "resistance"
                    ],

                "Destek":
                    technical[
                        "support"
                    ],

                "Final":
                    round(
                        final_score,
                        1
                    ),

                "R/R":
                    round(
                        levels[
                            "rr"
                        ],
                        1
                    ),

                "Fırsat":
                    opportunity,

                "Karar":
                    decision,

                "Giriş Alt":
                    levels[
                        "entry_low"
                    ],

                "Giriş Üst":
                    levels[
                        "entry_high"
                    ],

                "Stop":
                    levels[
                        "stop"
                    ],

                "Hedef 1":
                    levels[
                        "target1"
                    ],

                "Hedef 2":
                    levels[
                        "target2"
                    ],

                "Breakout Durumu":
                    breakout_status,

                "Açıklama":
                    reason,
            }
        )

        progress.progress(
            (index + 1) / total,
            text=(
                f"{row.get('base_asset', symbol)} "
                f"analiz ediliyor..."
            )
        )

    progress.empty()

    result = pd.DataFrame(
        results
    )

    if result.empty:

        return result

    return (
        result
        .sort_values(
            "Final",
            ascending=False
        )
        .reset_index(
            drop=True
        )
    )


# ============================================================
# VERİYİ AL
# ============================================================

with st.spinner(
    "Ortak TRY evreni hazırlanıyor..."
):

    df_market = (
        get_common_universe()
    )


if df_market.empty:

    st.error(
        "❌ Ortak kripto piyasa evreni alınamadı."
    )

    st.info(
        "Önce Kripto Piyasa sayfasını açıp "
        "verinin yüklenmesini sağlayın."
    )

    st.stop()


# ============================================================
# ANALİZ
# ============================================================

df_result = analyze_market(
    df_market
)


if df_result.empty:

    st.error(
        "Analiz sonucunda veri oluşmadı."
    )

    st.stop()


# ============================================================
# ÜST BİLGİ
# ============================================================

st.caption(
    "Ortak piyasa evreni aktif. "
    "Günlük Trade motoru kendi başına coin keşfetmez."
)

st.caption(
    f"Analiz edilen evren: "
    f"{len(df_result)} coin"
)

st.caption(
    "Son analiz: "
    +
    datetime.now().strftime(
        "%d.%m.%Y %H:%M:%S"
    )
)


# ============================================================
# ANA İSTATİSTİKLER
# ============================================================

buy_df = df_result[
    df_result["Karar"].isin(
        [
            "🟢 GÜNLÜK AL",
            "🟢 BREAKOUT AL"
        ]
    )
]

entry_df = df_result[
    df_result["Karar"]
    ==
    "🟡 GİRİŞ BEKLE"
]

confirm_df = df_result[
    df_result["Karar"].isin(
        [
            "🟡 TEYİT BEKLE",
            "🟡 BREAKOUT TEYİDİ BEKLE"
        ]
    )
]

chase_df = df_result[
    df_result["Karar"]
    ==
    "🔴 KOVALAMA"
]


c1, c2, c3, c4, c5 = st.columns(5)


with c1:

    st.metric(
        "Analiz",
        len(df_result)
    )


with c2:

    st.metric(
        "🟢 İşlem",
        len(buy_df)
    )


with c3:

    st.metric(
        "🟡 Giriş Bekle",
        len(entry_df)
    )


with c4:

    st.metric(
        "🟡 Teyit",
        len(confirm_df)
    )


with c5:

    st.metric(
        "🔴 Kovalama",
        len(chase_df)
    )


st.divider()


# ============================================================
# 1 — KESİN İŞLEM ADAYLARI
# ============================================================

st.subheader(
    "🎯 1. Bugünün Kesin İşlem Adayları"
)

st.caption(
    "Buradaki coinler sistemin doğrudan işlem kriterlerini karşılamıştır."
)


if not buy_df.empty:

    for _, row in buy_df.head(5).iterrows():

        with st.container(
            border=True
        ):

            c1, c2, c3, c4 = st.columns(4)

            with c1:

                st.markdown(
                    f"### 🟢 {row['Coin']}"
                )

                st.metric(
                    "FINAL",
                    f"{row['Final']:.1f}"
                )

                st.write(
                    row["Karar"]
                )

            with c2:

                st.metric(
                    "PRO Güç",
                    f"{row['PRO Güç']:.1f}"
                )

                st.metric(
                    "Günlük Trade",
                    f"{row['Günlük Trade']:.1f}"
                )

            with c3:

                st.metric(
                    "Giriş",
                    f"{row['Giriş Kalitesi']:.1f}"
                )

                st.metric(
                    "Trend",
                    f"{row['Trend']:.1f}"
                )

            with c4:

                st.metric(
                    "Breakout",
                    f"{row['Breakout']:.1f}"
                )

                st.metric(
                    "Kovalama",
                    f"{row['Kovalama']:.1f}"
                )

            st.write(
                f"**Fiyat:** "
                f"{fmt_price(row['Fiyat'])}"
            )

            st.write(
                f"**Giriş:** "
                f"{fmt_price(row['Giriş Alt'])}"
                f" – "
                f"{fmt_price(row['Giriş Üst'])}"
            )

            st.write(
                f"**Stop:** "
                f"{fmt_price(row['Stop'])}"
                f" | "
                f"**Hedef 1:** "
                f"{fmt_price(row['Hedef 1'])}"
                f" | "
                f"**Hedef 2:** "
                f"{fmt_price(row['Hedef 2'])}"
            )

            st.write(
                f"**R/R:** "
                f"1 : {row['R/R']:.1f}"
                f" | "
                f"**RSI:** "
                f"{row['RSI']:.1f}"
                f" | "
                f"**Hacim:** "
                f"{row['Hacim Oranı']:.2f}x"
            )

            st.caption(
                row["Açıklama"]
            )

else:

    st.info(
        "Şu anda doğrudan AL kriterlerini karşılayan "
        "coin yok. Bu normaldir."
    )


# ============================================================
# 2 — FIRSAT HAVUZU
# ============================================================

st.divider()

st.subheader(
    "💎 2. Fırsat Havuzu"
)

st.caption(
    "Henüz doğrudan AL olmayan ancak profesyonel "
    "izleme listesine girmeye değer coinler."
)

opportunity_df = df_result[
    df_result["Fırsat"].isin(
        [
            "🟢 A SINIFI FIRSAT",
            "🟡 B SINIFI FIRSAT"
        ]
    )
].copy()

if not opportunity_df.empty:

    st.dataframe(
        opportunity_df[
            [
                "Coin",
                "Fiyat",
                "Günlük %",
                "PRO Güç",
                "Günlük Trade",
                "Giriş Kalitesi",
                "Trend",
                "Breakout",
                "Hacim Oranı",
                "RSI",
                "Kovalama",
                "Final",
                "Fırsat",
                "Karar",
            ]
        ],
        use_container_width=True,
        hide_index=True
    )

else:

    st.info(
        "Şu anda güçlü bir fırsat havuzu oluşmadı."
    )


# ============================================================
# 3 — GİRİŞ BEKLEYENLER
# ============================================================

st.divider()

st.subheader(
    "🟡 3. Güçlü Ama Giriş Beklenmeli"
)

if not entry_df.empty:

    st.dataframe(
        entry_df[
            [
                "Coin",
                "Fiyat",
                "Günlük %",
                "PRO Güç",
                "Giriş Kalitesi",
                "RSI",
                "Kovalama",
                "Final",
                "Karar",
            ]
        ],
        use_container_width=True,
        hide_index=True
    )

else:

    st.success(
        "Şu anda giriş beklenmesi gereken güçlü coin yok."
    )


# ============================================================
# 4 — BREAKOUT MERKEZİ
# ============================================================

st.divider()

st.subheader(
    "🚀 4. Breakout Merkezi"
)

breakout_df = df_result[
    df_result["Karar"].isin(
        [
            "🟢 BREAKOUT AL",
            "🟡 BREAKOUT TEYİDİ BEKLE"
        ]
    )
]

if not breakout_df.empty:

    st.dataframe(
        breakout_df[
            [
                "Coin",
                "Fiyat",
                "Direnç",
                "Breakout",
                "Trend",
                "Hacim Oranı",
                "RSI",
                "Kovalama",
                "Final",
                "Karar",
            ]
        ],
        use_container_width=True,
        hide_index=True
    )

else:

    st.info(
        "Şu anda güçlü bir breakout setup'ı yok."
    )


# ============================================================
# 5 — TEYİT BEKLEYENLER
# ============================================================

st.divider()

st.subheader(
    "🟡 5. Teyit Bekleyen Coinler"
)

if not confirm_df.empty:

    st.dataframe(
        confirm_df[
            [
                "Coin",
                "Fiyat",
                "Günlük %",
                "PRO Güç",
                "Günlük Trade",
                "Trend",
                "Breakout",
                "Hacim Oranı",
                "RSI",
                "Final",
                "Karar",
            ]
        ],
        use_container_width=True,
        hide_index=True
    )

else:

    st.success(
        "Teyit bekleyen önemli coin yok."
    )


# ============================================================
# 6 — KOVALAMA
# ============================================================

st.divider()

st.subheader(
    "🔴 6. Kovalama Riski Yüksek Coinler"
)

st.caption(
    "Güçlü olabilirler; fakat mevcut seviyeden "
    "işleme girmek riskli olabilir."
)

if not chase_df.empty:

    st.dataframe(
        chase_df[
            [
                "Coin",
                "Fiyat",
                "Günlük %",
                "PRO Güç",
                "Giriş Kalitesi",
                "RSI",
                "Kovalama",
                "Final",
                "Karar",
            ]
        ],
        use_container_width=True,
        hide_index=True
    )

else:

    st.success(
        "Yüksek kovalama riski taşıyan coin yok."
    )


# ============================================================
# 7 — TÜM PİYASA
# ============================================================

st.divider()

st.subheader(
    "📊 7. Tüm Coinler"
)

all_columns = [

    "Coin",

    "Fiyat",

    "Günlük %",

    "PRO Güç",

    "Günlük Trade",

    "Giriş Kalitesi",

    "Trend",

    "Breakout",

    "Hacim Oranı",

    "RSI",

    "Kovalama",

    "Final",

    "Fırsat",

    "Karar",
]

st.dataframe(
    df_result[
        all_columns
    ],
    use_container_width=True,
    hide_index=True,
    height=600
)


# ============================================================
# 8 — DETAYLI COİN ANALİZİ
# ============================================================

st.divider()

st.subheader(
    "🔎 8. Detaylı Coin Analizi"
)

coin_list = (
    df_result[
        "Coin"
    ]
    .tolist()
)

selected_coin = st.selectbox(
    "Coin seç",
    coin_list
)

selected = df_result[
    df_result["Coin"]
    ==
    selected_coin
].iloc[0]


st.markdown(
    f"## {selected['Coin']}"
)


decision = selected[
    "Karar"
]


if "🟢" in decision:

    st.success(
        decision
    )

elif "🟡" in decision:

    st.warning(
        decision
    )

else:

    st.error(
        decision
    )


# ============================================================
# SKORLAR
# ============================================================

c1, c2, c3, c4, c5, c6 = st.columns(6)

with c1:

    st.metric(
        "PRO Güç",
        f"{selected['PRO Güç']:.1f}"
    )

with c2:

    st.metric(
        "Günlük Trade",
        f"{selected['Günlük Trade']:.1f}"
    )

with c3:

    st.metric(
        "Giriş",
        f"{selected['Giriş Kalitesi']:.1f}"
    )

with c4:

    st.metric(
        "Breakout",
        f"{selected['Breakout']:.1f}"
    )

with c5:

    st.metric(
        "Kovalama",
        f"{selected['Kovalama']:.1f}"
    )

with c6:

    st.metric(
        "FINAL",
        f"{selected['Final']:.1f}"
    )


# ============================================================
# İŞLEM PLANI
# ============================================================

st.markdown(
    "### 🎯 İşlem Planı"
)

p1, p2, p3, p4 = st.columns(4)

with p1:

    st.metric(
        "Mevcut Fiyat",
        fmt_price(
            selected["Fiyat"]
        )
    )

with p2:

    st.metric(
        "Direnç",
        fmt_price(
            selected["Direnç"]
        )
    )

with p3:

    st.metric(
        "Stop",
        fmt_price(
            selected["Stop"]
        )
    )

with p4:

    st.metric(
        "R/R",
        f"1 : {selected['R/R']:.1f}"
    )


st.write(
    f"**Giriş bölgesi:** "
    f"{fmt_price(selected['Giriş Alt'])}"
    f" – "
    f"{fmt_price(selected['Giriş Üst'])}"
)

st.write(
    f"**Hedef 1:** "
    f"{fmt_price(selected['Hedef 1'])}"
)

st.write(
    f"**Hedef 2:** "
    f"{fmt_price(selected['Hedef 2'])}"
)


# ============================================================
# TEKNİK DURUM
# ============================================================

st.markdown(
    "### 📐 Teknik Durum"
)

t1, t2, t3, t4, t5 = st.columns(5)

with t1:

    st.metric(
        "Trend",
        f"{selected['Trend']:.1f}"
    )

with t2:

    st.metric(
        "RSI",
        f"{selected['RSI']:.1f}"
    )

with t3:

    st.metric(
        "Hacim",
        f"{selected['Hacim Oranı']:.2f}x"
    )

with t4:

    st.metric(
        "Breakout",
        f"{selected['Breakout']:.1f}"
    )

with t5:

    st.metric(
        "Fırsat",
        selected["Fırsat"]
    )


st.info(
    selected["Açıklama"]
)


# ============================================================
# PROFESYONEL KARAR MOTORU AÇIKLAMASI
# ============================================================

with st.expander(
    "🧠 Profesyonel Karar Motoru"
):

    st.markdown(
        """
### 1. Ortak Piyasa Evreni

Motor kendi başına coin keşfetmez.

`crypto_engine.get_all_try_universe()`

tarafından sağlanan TRY pariteleri kullanılır.

Böylece Kripto Piyasa ve Günlük Trade aynı evren üzerinde çalışır.

---

### 2. PRO Güç

Coinin genel gücünü ölçer.

- 24 saatlik momentum
- TRY işlem hacmi
- EMA trendi
- RSI
- Teknik yapı
- Breakout potansiyeli

birlikte değerlendirilir.

---

### 3. Günlük Trade

Burada soru:

**"Bu coin güçlü mü?"**

değil;

**"Bugün işlem yapılabilir mi?"**

sorusudur.

---

### 4. Giriş Kalitesi

Fiyatın günlük range içerisindeki konumu,

RSI ve günlük yükseliş miktarı birlikte değerlendirilir.

Bu nedenle %15–20 yükselmiş bir coin otomatik olarak AL değildir.

---

### 5. Kovalama

Kovalama skoru:

**0 → düşük risk**

**100 → çok yüksek risk**

demektir.

Yüksek skor doğrudan "coin kötü" anlamına gelmez.

Anlamı:

**"Coin güçlü ama mevcut fiyatı kovalamak riskli."**

---

### 6. Breakout

Breakout için:

**Direnç**

↓

**Fiyat kırılımı**

↓

**Hacim**

↓

**Trend**

↓

**RSI**

↓

**Kovalama**

kontrol edilir.

---

### 7. Fırsat Havuzu

Her gün doğrudan AL çıkması beklenmez.

Sistem güçlü fakat henüz giriş için hazır olmayan coinleri de saklar.

Bu nedenle:

**A SINIFI FIRSAT**

**B SINIFI FIRSAT**

**C SINIFI İZLE**

şeklinde ayrı bir takip havuzu vardır.

---

### 8. Nihai prensip

**En çok yükseleni almak yok.**

Amaç:

**Güç + Trend + Hacim + Uygun Giriş + Teyit + Kontrollü Risk**

kombinasyonunu bulmaktır.
"""
    )


# ============================================================
# SON UYARI
# ============================================================

st.divider()

st.caption(
    "⚠️ Bu sayfa teknik karar desteği sağlar. "
    "Gerçek işlem öncesinde Midas üzerindeki gerçek zamanlı fiyat, "
    "spread, likidite, emir gerçekleşmesi ve piyasa koşulları "
    "ayrıca kontrol edilmelidir."
)