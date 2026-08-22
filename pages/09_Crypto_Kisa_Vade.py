# ============================================================
# CRYPTO AI PRO
# 09_Crypto_Kisa_Vade.py
#
# PROFESYONEL KISA VADE KRİPTO ANALİZ MOTORU
#
# VADE:
#   1 - 7 GÜN
#
# VERİ EVRENİ:
#   crypto_engine.get_all_try_universe()
#
# ÖNEMLİ:
#   Bu sayfa kendi başına coin keşfetmez.
#   Sadece Binance TR TRY evrenini kullanır.
#
# ============================================================

import streamlit as st
import pandas as pd
import numpy as np
import requests
import importlib
from datetime import datetime


# ============================================================
# SAYFA AYARLARI
# ============================================================

st.set_page_config(
    page_title="Kripto Kısa Vade PRO",
    page_icon="📈",
    layout="wide",
)


# ============================================================
# ENGINE
# ============================================================

import crypto_engine

crypto_engine = importlib.reload(
    crypto_engine
)


# ============================================================
# AYARLAR
# ============================================================

KLINE_URL = "https://api.binance.com/api/v3/klines"

KLINE_INTERVAL = "1h"
KLINE_LIMIT = 250

MIN_VOLUME_TRY = 50_000_000

MAX_ANALYSIS = 50


# ============================================================
# BAŞLIK
# ============================================================

st.title("📈 Kripto Kısa Vade PRO")

st.caption(
    "CRYPTO AI PRO | 1–7 Günlük Profesyonel Kısa Vade "
    "Fırsat ve Giriş Karar Motoru"
)

st.info(
    "Bu sayfa güçlü coinleri seçmekle kalmaz; "
    "kısa vadede mevcut fiyatın işlem için uygun olup "
    "olmadığını da analiz eder."
)


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


def clamp(value, low=0, high=100):

    return max(
        low,
        min(
            high,
            safe_float(value)
        )
    )


def fmt_price(value):

    value = safe_float(value)

    if value >= 1000:
        return f"{value:,.2f}"

    if value >= 100:
        return f"{value:,.3f}"

    if value >= 1:
        return f"{value:,.4f}"

    if value >= 0.01:
        return f"{value:.5f}"

    return f"{value:.8f}"


def fmt_volume(value):

    value = safe_float(value)

    if value >= 1_000_000_000:
        return f"₺{value / 1_000_000_000:.2f} Mr"

    if value >= 1_000_000:
        return f"₺{value / 1_000_000:.1f} Mn"

    if value >= 1_000:
        return f"₺{value / 1_000:.0f} Bin"

    return f"₺{value:,.0f}"


# ============================================================
# TEKNİK FONKSİYONLAR
# ============================================================

def ema(series, period):

    return (
        pd.Series(series)
        .ewm(
            span=period,
            adjust=False
        )
        .mean()
    )


def rsi(series, period=14):

    series = pd.Series(series).astype(float)

    delta = series.diff()

    gain = delta.clip(
        lower=0
    )

    loss = -delta.clip(
        upper=0
    )

    avg_gain = gain.ewm(
        alpha=1 / period,
        adjust=False
    ).mean()

    avg_loss = loss.ewm(
        alpha=1 / period,
        adjust=False
    ).mean()

    rs = (
        avg_gain /
        avg_loss.replace(
            0,
            np.nan
        )
    )

    result = (
        100 -
        (
            100 /
            (1 + rs)
        )
    )

    return result


def atr(df, period=14):

    high = df["high"]

    low = df["low"]

    close = df["close"]

    prev_close = close.shift(1)

    tr = pd.concat(
        [
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs()
        ],
        axis=1
    ).max(axis=1)

    return tr.ewm(
        alpha=1 / period,
        adjust=False
    ).mean()


# ============================================================
# COIN SEMBOLÜNÜ NORMALLEŞTİR
# ============================================================

def normalize_symbol(symbol):

    symbol = str(
        symbol
    ).upper().strip()

    replacements = [
        "_TRY",
        "-TRY",
        "/TRY",
        "TRY"
    ]

    for suffix in replacements:

        if symbol.endswith(suffix):

            symbol = symbol[
                :-len(suffix)
            ]

            break

    return symbol


# ============================================================
# MARKET DATA
# ============================================================

@st.cache_data(ttl=60)
def load_universe():

    try:

        raw = (
            crypto_engine
            .get_all_try_universe()
        )

    except Exception as e:

        return pd.DataFrame(), str(e)

    if raw is None:

        return pd.DataFrame(), (
            "Crypto engine veri döndürmedi."
        )

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

            return (
                pd.DataFrame(),
                "TRY evreni boş."
            )

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

        return (
            pd.DataFrame(),
            f"Beklenmeyen veri tipi: "
            f"{type(raw).__name__}"
        )

    if df.empty:

        return (
            pd.DataFrame(),
            "TRY evreni boş."
        )

    # --------------------------------------------------------
    # SYMBOL
    # --------------------------------------------------------

    if "symbol" not in df.columns:

        possible = [
            "pair",
            "code",
            "name"
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

            return (
                pd.DataFrame(),
                "Sembol bilgisi bulunamadı."
            )

    df["symbol"] = (
        df["symbol"]
        .astype(str)
        .str.upper()
        .str.strip()
    )

    # --------------------------------------------------------
    # BASE ASSET
    # --------------------------------------------------------

    if "base_asset" not in df.columns:

        df["base_asset"] = (
            df["symbol"]
            .apply(
                normalize_symbol
            )
        )

    else:

        df["base_asset"] = (
            df["base_asset"]
            .astype(str)
            .str.upper()
            .str.strip()
        )

    # --------------------------------------------------------
    # FİYAT
    # --------------------------------------------------------

    if "price_try" not in df.columns:

        possible_price = [
            "price",
            "lastPrice",
            "last_price"
        ]

        for col in possible_price:

            if col in df.columns:

                df["price_try"] = (
                    pd.to_numeric(
                        df[col],
                        errors="coerce"
                    )
                )

                break

    # --------------------------------------------------------
    # DEĞİŞİM
    # --------------------------------------------------------

    if "change_24h" not in df.columns:

        possible_change = [
            "change",
            "priceChangePercent",
            "change_percent"
        ]

        for col in possible_change:

            if col in df.columns:

                df["change_24h"] = (
                    pd.to_numeric(
                        df[col],
                        errors="coerce"
                    )
                )

                break

    # --------------------------------------------------------
    # HACİM
    # --------------------------------------------------------

    if "volume_try" not in df.columns:

        possible_volume = [
            "volume",
            "quoteVolume",
            "quote_volume"
        ]

        for col in possible_volume:

            if col in df.columns:

                df["volume_try"] = (
                    pd.to_numeric(
                        df[col],
                        errors="coerce"
                    )
                )

                break

    # --------------------------------------------------------
    # HIGH / LOW
    # --------------------------------------------------------

    for target, candidates in {

        "high_24h": [
            "high",
            "highPrice"
        ],

        "low_24h": [
            "low",
            "lowPrice"
        ]

    }.items():

        if target not in df.columns:

            for col in candidates:

                if col in df.columns:

                    df[target] = (
                        pd.to_numeric(
                            df[col],
                            errors="coerce"
                        )
                    )

                    break

    # --------------------------------------------------------
    # SAYISALLAR
    # --------------------------------------------------------

    numeric_columns = [
        "price_try",
        "change_24h",
        "volume_try",
        "high_24h",
        "low_24h"
    ]

    for col in numeric_columns:

        if col in df.columns:

            df[col] = pd.to_numeric(
                df[col],
                errors="coerce"
            )

    # --------------------------------------------------------
    # GEÇERLİ COİNLER
    # --------------------------------------------------------

    if "price_try" not in df.columns:

        return (
            pd.DataFrame(),
            "Fiyat verisi bulunamadı."
        )

    df = df[
        df["price_try"] > 0
    ].copy()

    if "volume_try" in df.columns:

        df = df[
            df["volume_try"]
            .fillna(0)
            >= MIN_VOLUME_TRY
        ].copy()

    # --------------------------------------------------------
    # DUPLICATE TEMİZLE
    # --------------------------------------------------------

    df = (
        df
        .drop_duplicates(
            subset=["base_asset"]
        )
        .reset_index(
            drop=True
        )
    )

    # --------------------------------------------------------
    # HACME GÖRE
    # --------------------------------------------------------

    if "volume_try" in df.columns:

        df = df.sort_values(
            "volume_try",
            ascending=False
        )

    return (
        df.head(
            MAX_ANALYSIS
        ).reset_index(
            drop=True
        ),
        None
    )


# ============================================================
# KLINE
# ============================================================

@st.cache_data(ttl=120)
def get_klines(symbol):

    try:

        params = {

            "symbol": symbol,

            "interval":
                KLINE_INTERVAL,

            "limit":
                KLINE_LIMIT
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

        rows = []

        for item in data:

            if len(item) < 6:
                continue

            rows.append(
                {
                    "time": item[0],
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

        df["ema9"] = ema(
            df["close"],
            9
        )

        df["ema20"] = ema(
            df["close"],
            20
        )

        df["ema50"] = ema(
            df["close"],
            50
        )

        df["rsi"] = rsi(
            df["close"]
        )

        df["atr"] = atr(
            df
        )

        return df

    except Exception:

        return pd.DataFrame()


# ============================================================
# TEKNİK ANALİZ
# ============================================================

def analyze_coin(row, klines):

    price = safe_float(
        row.get(
            "price_try"
        )
    )

    change = safe_float(
        row.get(
            "change_24h"
        )
    )

    high24 = safe_float(
        row.get(
            "high_24h"
        ),
        price
    )

    low24 = safe_float(
        row.get(
            "low_24h"
        ),
        price
    )

    # --------------------------------------------------------
    # KLINE YOK
    # --------------------------------------------------------

    if klines.empty:

        return {

            "trend": 50,
            "momentum": 50,
            "rsi": 50,
            "volume_ratio": 1.0,
            "technical": 50,
            "support": price * 0.94,
            "resistance": price * 1.05,
            "atr": price * 0.03
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

    current_rsi = safe_float(
        last["rsi"],
        50
    )

    current_atr = safe_float(
        last["atr"],
        price * 0.03
    )

    # --------------------------------------------------------
    # DESTEK / DİRENÇ
    # --------------------------------------------------------

    recent = klines.iloc[
        -72:-1
    ]

    if recent.empty:

        support = price * 0.94
        resistance = price * 1.05

    else:

        support = safe_float(
            recent["low"].min(),
            price * 0.94
        )

        resistance = safe_float(
            recent["high"].max(),
            price * 1.05
        )

    # --------------------------------------------------------
    # HACİM
    # --------------------------------------------------------

    if len(klines) >= 21:

        avg_volume = safe_float(
            klines["volume"]
            .iloc[-21:-1]
            .mean(),
            0
        )

        last_volume = safe_float(
            last["volume"]
        )

        if avg_volume > 0:

            volume_ratio = (
                last_volume /
                avg_volume
            )

        else:

            volume_ratio = 1

    else:

        volume_ratio = 1

    # --------------------------------------------------------
    # TREND
    # --------------------------------------------------------

    trend = 50

    if price > ema9:
        trend += 10

    if ema9 > ema20:
        trend += 15

    if ema20 > ema50:
        trend += 15

    if price > ema50:
        trend += 10

    trend = clamp(
        trend
    )

    # --------------------------------------------------------
    # MOMENTUM
    # --------------------------------------------------------

    if change >= 20:

        momentum = 100

    elif change >= 15:

        momentum = 92

    elif change >= 10:

        momentum = 85

    elif change >= 7:

        momentum = 78

    elif change >= 4:

        momentum = 70

    elif change >= 0:

        momentum = 58

    elif change >= -5:

        momentum = 42

    else:

        momentum = 25

    # --------------------------------------------------------
    # RSI SKORU
    # --------------------------------------------------------

    if 52 <= current_rsi <= 68:

        rsi_score = 95

    elif 68 < current_rsi <= 73:

        rsi_score = 85

    elif 73 < current_rsi <= 78:

        rsi_score = 68

    elif current_rsi > 78:

        rsi_score = 40

    elif 45 <= current_rsi < 52:

        rsi_score = 60

    else:

        rsi_score = 35

    # --------------------------------------------------------
    # HACİM SKORU
    # --------------------------------------------------------

    volume_score = clamp(
        volume_ratio * 45
    )

    # --------------------------------------------------------
    # TEKNİK
    # --------------------------------------------------------

    technical = (
        trend * 0.40 +
        momentum * 0.20 +
        rsi_score * 0.20 +
        volume_score * 0.20
    )

    return {

        "trend": trend,

        "momentum": momentum,

        "rsi": current_rsi,

        "rsi_score": rsi_score,

        "volume_ratio":
            volume_ratio,

        "technical":
            clamp(technical),

        "support":
            support,

        "resistance":
            resistance,

        "atr":
            current_atr,

        "ema9":
            ema9,

        "ema20":
            ema20,

        "ema50":
            ema50
    }


# ============================================================
# GİRİŞ SKORU
# ============================================================

def calculate_entry_score(
    row,
    tech
):

    price = safe_float(
        row["price_try"]
    )

    high = safe_float(
        row.get(
            "high_24h"
        ),
        price
    )

    low = safe_float(
        row.get(
            "low_24h"
        ),
        price
    )

    change = safe_float(
        row.get(
            "change_24h"
        )
    )

    # --------------------------------------------------------
    # GÜNLÜK RANGE POZİSYONU
    # --------------------------------------------------------

    if high > low:

        position = (
            (price - low) /
            (high - low)
        ) * 100

    else:

        position = 50

    position = clamp(
        position
    )

    # Zirveye yakınsa puan düşür
    if position >= 95:

        position_score = 35

    elif position >= 90:

        position_score = 48

    elif position >= 80:

        position_score = 62

    elif position >= 70:

        position_score = 75

    elif position >= 50:

        position_score = 88

    else:

        position_score = 80

    # --------------------------------------------------------
    # RSI
    # --------------------------------------------------------

    r = safe_float(
        tech["rsi"]
    )

    if 52 <= r <= 68:

        rsi_score = 95

    elif 68 < r <= 73:

        rsi_score = 82

    elif 73 < r <= 78:

        rsi_score = 65

    elif r > 78:

        rsi_score = 35

    else:

        rsi_score = 55

    # --------------------------------------------------------
    # GÜNLÜK HAREKET
    # --------------------------------------------------------

    if 3 <= change <= 8:

        momentum_entry = 95

    elif 8 < change <= 12:

        momentum_entry = 85

    elif 12 < change <= 15:

        momentum_entry = 72

    elif 15 < change <= 20:

        momentum_entry = 58

    elif change > 20:

        momentum_entry = 35

    else:

        momentum_entry = 55

    return clamp(
        position_score * 0.40 +
        rsi_score * 0.25 +
        momentum_entry * 0.35
    )


# ============================================================
# KOVALAMA
# ============================================================

def calculate_chase(
    row,
    tech
):

    change = safe_float(
        row.get(
            "change_24h"
        )
    )

    price = safe_float(
        row["price_try"]
    )

    high = safe_float(
        row.get(
            "high_24h"
        ),
        price
    )

    low = safe_float(
        row.get(
            "low_24h"
        ),
        price
    )

    rsi_value = safe_float(
        tech["rsi"]
    )

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
    # ZİRVEYE YAKINLIK
    # --------------------------------------------------------

    if high > low:

        position = (
            (price - low) /
            (high - low)
        ) * 100

    else:

        position = 50

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

    if rsi_value >= 85:

        score += 30

    elif rsi_value >= 80:

        score += 22

    elif rsi_value >= 75:

        score += 12

    return clamp(
        score
    )


# ============================================================
# RİSK / ÖDÜL
# ============================================================

def calculate_levels(
    row,
    tech
):

    price = safe_float(
        row["price_try"]
    )

    support = safe_float(
        tech["support"],
        price * 0.94
    )

    atr_value = safe_float(
        tech["atr"],
        price * 0.03
    )

    # ATR tabanlı stop
    atr_stop = (
        price -
        atr_value * 1.5
    )

    # Destek altı
    support_stop = (
        support * 0.995
    )

    stop = min(
        atr_stop,
        support_stop
    )

    # Stop çok uzak olmasın
    stop = max(
        stop,
        price * 0.88
    )

    # Stop çok yakın olmasın
    stop = min(
        stop,
        price * 0.96
    )

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

    target1 = (
        price +
        risk * 2
    )

    target2 = (
        price +
        risk * 3
    )

    entry_low = (
        price -
        price * 0.005
    )

    entry_high = (
        price +
        price * 0.005
    )

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

        "risk_pct":
            risk / price * 100,

        "rr":
            2.0
    }


# ============================================================
# KARAR MOTORU
# ============================================================

def decision_engine(
    row,
    tech,
    entry_score,
    chase_score,
    levels
):

    technical = safe_float(
        tech["technical"]
    )

    trend = safe_float(
        tech["trend"]
    )

    momentum = safe_float(
        tech["momentum"]
    )

    volume_ratio = safe_float(
        tech["volume_ratio"],
        1
    )

    resistance = safe_float(
        tech["resistance"]
    )

    price = safe_float(
        row["price_try"]
    )

    change = safe_float(
        row.get(
            "change_24h"
        )
    )

    # --------------------------------------------------------
    # BREAKOUT
    # --------------------------------------------------------

    breakout = (

        price >
        resistance * 1.002

        and
        volume_ratio >= 1.25

        and
        trend >= 70

        and
        50 <= tech["rsi"] <= 78

        and
        chase_score < 60
    )

    # --------------------------------------------------------
    # KISA VADE SKORU
    # --------------------------------------------------------

    short_score = (

        technical * 0.35 +

        entry_score * 0.30 +

        momentum * 0.15 +

        min(
            volume_ratio * 40,
            100
        ) * 0.10 +

        (100 - chase_score) * 0.10
    )

    short_score = clamp(
        short_score
    )

    # --------------------------------------------------------
    # KOVALAMA
    # --------------------------------------------------------

    if chase_score >= 75:

        return (
            short_score,
            "🔴 KOVALAMA",
            "Coin güçlü ancak mevcut fiyat "
            "kısa vadeli giriş açısından fazla uzamış."
        )

    # --------------------------------------------------------
    # BREAKOUT
    # --------------------------------------------------------

    if (
        breakout
        and
        short_score >= 78
    ):

        return (
            short_score,
            "🟢 BREAKOUT AL",
            "Direnç kırılmış, hacim ve trend "
            "teyidi mevcut."
        )

    # --------------------------------------------------------
    # NORMAL AL
    # --------------------------------------------------------

    if (
        short_score >= 80
        and
        entry_score >= 70
        and
        chase_score < 50
        and
        levels["rr"] >= 2
    ):

        return (
            short_score,
            "🟢 KISA VADE AL",
            "Trend, momentum, giriş kalitesi "
            "ve risk/getiri birlikte uygun."
        )

    # --------------------------------------------------------
    # GERİ ÇEKİLME
    # --------------------------------------------------------

    if (
        technical >= 75
        and
        (
            chase_score >= 45
            or
            entry_score < 70
        )
    ):

        return (
            short_score,
            "🟡 GERİ ÇEKİLME BEKLE",
            "Coin güçlü fakat mevcut fiyat "
            "avantajlı giriş bölgesinde değil."
        )

    # --------------------------------------------------------
    # TEYİT
    # --------------------------------------------------------

    if short_score >= 65:

        return (
            short_score,
            "🟡 TEYİT BEKLE",
            "Kısa vadeli potansiyel var ancak "
            "işlem için ek teyit gerekiyor."
        )

    # --------------------------------------------------------
    # İŞLEM YOK
    # --------------------------------------------------------

    return (
        short_score,
        "🔴 İŞLEM YOK",
        "Mevcut koşullarda kısa vadeli "
        "işlem avantajı yeterli değil."
    )


# ============================================================
# TÜM COİNLERİ ANALİZ ET
# ============================================================

def analyze_market(df):

    results = []

    progress = st.progress(
        0,
        text="Kısa vade coinleri analiz ediliyor..."
    )

    total = len(df)

    for index, (_, row) in enumerate(
        df.iterrows()
    ):

        symbol = str(
            row["symbol"]
        ).upper()

        # ----------------------------------------------------
        # SADECE GERÇEK TRY PARİTESİ
        # ----------------------------------------------------

        if not symbol.endswith(
            "TRY"
        ):

            symbol = (
                normalize_symbol(
                    symbol
                )
                + "TRY"
            )

        klines = get_klines(
            symbol
        )

        tech = analyze_coin(
            row,
            klines
        )

        entry_score = (
            calculate_entry_score(
                row,
                tech
            )
        )

        chase_score = (
            calculate_chase(
                row,
                tech
            )
        )

        levels = calculate_levels(
            row,
            tech
        )

        (
            short_score,
            decision,
            reason
        ) = decision_engine(
            row,
            tech,
            entry_score,
            chase_score,
            levels
        )

        results.append(
            {

                "Coin":
                    row["base_asset"],

                "Parite":
                    symbol,

                "Fiyat":
                    safe_float(
                        row["price_try"]
                    ),

                "24s %":
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

                "Kısa Vade":
                    round(
                        short_score,
                        1
                    ),

                "Teknik":
                    round(
                        tech["technical"],
                        1
                    ),

                "Trend":
                    round(
                        tech["trend"],
                        1
                    ),

                "Momentum":
                    round(
                        tech["momentum"],
                        1
                    ),

                "Giriş":
                    round(
                        entry_score,
                        1
                    ),

                "RSI":
                    round(
                        tech["rsi"],
                        1
                    ),

                "Hacim Oranı":
                    round(
                        tech["volume_ratio"],
                        2
                    ),

                "Kovalama":
                    round(
                        chase_score,
                        1
                    ),

                "Destek":
                    tech["support"],

                "Direnç":
                    tech["resistance"],

                "Giriş Alt":
                    levels["entry_low"],

                "Giriş Üst":
                    levels["entry_high"],

                "Stop":
                    levels["stop"],

                "Hedef 1":
                    levels["target1"],

                "Hedef 2":
                    levels["target2"],

                "R/R":
                    levels["rr"],

                "Karar":
                    decision,

                "Açıklama":
                    reason
            }
        )

        progress.progress(
            (index + 1) / total,
            text=(
                f"{row['base_asset']} "
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
            "Kısa Vade",
            ascending=False
        )
        .reset_index(
            drop=True
        )
    )


# ============================================================
# EVRENİ AL
# ============================================================

with st.spinner(
    "Binance TR TRY evreni hazırlanıyor..."
):

    df_market, error = (
        load_universe()
    )


if error:

    st.error(
        f"Kripto piyasa verisi alınamadı: {error}"
    )

    st.stop()


if df_market.empty:

    st.warning(
        "Analiz edilecek TRY coin bulunamadı."
    )

    st.stop()


# ============================================================
# ANALİZ
# ============================================================

with st.spinner(
    "Kısa vade analiz motoru çalışıyor..."
):

    df_result = analyze_market(
        df_market
    )


if df_result.empty:

    st.warning(
        "Kısa vade analiz sonucu oluşmadı."
    )

    st.stop()


# ============================================================
# ÜST BİLGİ
# ============================================================

st.caption(
    "Son güncelleme: "
    +
    datetime.now().strftime(
        "%d.%m.%Y %H:%M:%S"
    )
)

c1, c2, c3, c4 = st.columns(4)

with c1:

    st.metric(
        "Analiz Edilen",
        len(df_result)
    )

with c2:

    count_buy = len(
        df_result[
            df_result["Karar"].isin(
                [
                    "🟢 KISA VADE AL",
                    "🟢 BREAKOUT AL"
                ]
            )
        ]
    )

    st.metric(
        "İşlem Adayı",
        count_buy
    )

with c3:

    count_wait = len(
        df_result[
            df_result["Karar"].isin(
                [
                    "🟡 GERİ ÇEKİLME BEKLE",
                    "🟡 TEYİT BEKLE"
                ]
            )
        ]
    )

    st.metric(
        "Bekleyen",
        count_wait
    )

with c4:

    st.metric(
        "En Yüksek Skor",
        f"{df_result['Kısa Vade'].max():.1f}"
    )


# ============================================================
# EN İYİ KISA VADE ADAYLARI
# ============================================================

st.divider()

st.subheader(
    "🎯 En Güçlü Kısa Vade Adayları"
)

top_df = df_result.head(5)


for _, row in top_df.iterrows():

    karar = row["Karar"]

    with st.container(
        border=True
    ):

        c1, c2, c3, c4 = st.columns(4)

        with c1:

            st.markdown(
                f"### {row['Coin']}"
            )

            st.metric(
                "Kısa Vade Skoru",
                f"{row['Kısa Vade']:.1f}"
            )

            st.write(
                f"**{karar}**"
            )

        with c2:

            st.metric(
                "Teknik",
                f"{row['Teknik']:.1f}"
            )

            st.metric(
                "Trend",
                f"{row['Trend']:.1f}"
            )

        with c3:

            st.metric(
                "Giriş Kalitesi",
                f"{row['Giriş']:.1f}"
            )

            st.metric(
                "Momentum",
                f"{row['Momentum']:.1f}"
            )

        with c4:

            st.metric(
                "Kovalama",
                f"{row['Kovalama']:.1f}"
            )

            st.metric(
                "RSI",
                f"{row['RSI']:.1f}"
            )

        st.write(
            f"**Fiyat:** "
            f"{fmt_price(row['Fiyat'])} ₺"
            f"  |  "
            f"**24s:** "
            f"{row['24s %']:+.2f}%"
        )

        st.write(
            f"**Giriş:** "
            f"{fmt_price(row['Giriş Alt'])}"
            f" – "
            f"{fmt_price(row['Giriş Üst'])}"
            f"  |  "
            f"**Stop:** "
            f"{fmt_price(row['Stop'])}"
        )

        st.write(
            f"**Hedef 1:** "
            f"{fmt_price(row['Hedef 1'])}"
            f"  |  "
            f"**Hedef 2:** "
            f"{fmt_price(row['Hedef 2'])}"
            f"  |  "
            f"**R/R:** "
            f"1 : {row['R/R']:.1f}"
        )

        st.caption(
            row["Açıklama"]
        )


# ============================================================
# GÜÇLÜ AMA PAHALI
# ============================================================

st.divider()

st.subheader(
    "🟡 Güçlü Ama Geri Çekilme Beklenmeli"
)

pullback = df_result[
    df_result["Karar"]
    ==
    "🟡 GERİ ÇEKİLME BEKLE"
].copy()


if not pullback.empty:

    st.dataframe(
        pullback[
            [
                "Coin",
                "Fiyat",
                "24s %",
                "Kısa Vade",
                "Giriş",
                "Kovalama",
                "RSI",
                "Karar"
            ]
        ],
        use_container_width=True,
        hide_index=True
    )

else:

    st.success(
        "Şu anda güçlü fakat geri çekilmesi "
        "beklenen coin bulunmuyor."
    )


# ============================================================
# BREAKOUT
# ============================================================

st.divider()

st.subheader(
    "🚀 Kısa Vade Breakout Adayları"
)

breakout = df_result[
    df_result["Karar"]
    ==
    "🟢 BREAKOUT AL"
].copy()


if not breakout.empty:

    st.dataframe(
        breakout[
            [
                "Coin",
                "Fiyat",
                "24s %",
                "Kısa Vade",
                "Trend",
                "Hacim Oranı",
                "RSI",
                "Kovalama",
                "Karar"
            ]
        ],
        use_container_width=True,
        hide_index=True
    )

else:

    st.info(
        "Şu anda teyitli kısa vade breakout "
        "bulunmuyor."
    )


# ============================================================
# TÜM SONUÇLAR
# ============================================================

st.divider()

st.subheader(
    "📊 Kısa Vade Tüm Coinler"
)

display_columns = [

    "Coin",
    "Fiyat",
    "24s %",
    "Kısa Vade",
    "Teknik",
    "Trend",
    "Momentum",
    "Giriş",
    "RSI",
    "Hacim Oranı",
    "Kovalama",
    "Karar"
]

st.dataframe(
    df_result[
        display_columns
    ],
    use_container_width=True,
    hide_index=True
)


# ============================================================
# COİN ANALİZİ
# ============================================================

st.divider()

st.subheader(
    "🔎 Coin Analizi"
)

st.caption(
    "Bir coin seçerek kısa vadeli işlem planını "
    "detaylı olarak inceleyebilirsiniz."
)

coin_list = (
    df_result["Coin"]
    .tolist()
)

selected_coin = st.selectbox(
    "Analiz edilecek coin",
    coin_list
)

selected = df_result[
    df_result["Coin"]
    ==
    selected_coin
].iloc[0]


# ============================================================
# COİN BAŞLIĞI
# ============================================================

st.markdown(
    f"## {selected['Coin']}"
)

decision = selected["Karar"]

if decision.startswith("🟢"):

    st.success(
        decision
    )

elif decision.startswith("🟡"):

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
        "Kısa Vade",
        f"{selected['Kısa Vade']:.1f}"
    )

with c2:

    st.metric(
        "Teknik",
        f"{selected['Teknik']:.1f}"
    )

with c3:

    st.metric(
        "Trend",
        f"{selected['Trend']:.1f}"
    )

with c4:

    st.metric(
        "Giriş",
        f"{selected['Giriş']:.1f}"
    )

with c5:

    st.metric(
        "Kovalama",
        f"{selected['Kovalama']:.1f}"
    )

with c6:

    st.metric(
        "RSI",
        f"{selected['RSI']:.1f}"
    )


# ============================================================
# FİYAT
# ============================================================

st.markdown(
    "### 💰 Fiyat ve İşlem Planı"
)

c1, c2, c3, c4 = st.columns(4)

with c1:

    st.metric(
        "Mevcut Fiyat",
        f"{fmt_price(selected['Fiyat'])} ₺"
    )

with c2:

    st.metric(
        "24s Değişim",
        f"{selected['24s %']:+.2f}%"
    )

with c3:

    st.metric(
        "Destek",
        fmt_price(
            selected["Destek"]
        )
    )

with c4:

    st.metric(
        "Direnç",
        fmt_price(
            selected["Direnç"]
        )
    )


# ============================================================
# İŞLEM PLANI
# ============================================================

st.markdown(
    "### 🎯 Kısa Vade İşlem Planı"
)

p1, p2, p3, p4 = st.columns(4)

with p1:

    st.metric(
        "Giriş Alt",
        fmt_price(
            selected["Giriş Alt"]
        )
    )

with p2:

    st.metric(
        "Giriş Üst",
        fmt_price(
            selected["Giriş Üst"]
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


p1, p2 = st.columns(2)

with p1:

    st.metric(
        "Hedef 1",
        fmt_price(
            selected["Hedef 1"]
        )
    )

with p2:

    st.metric(
        "Hedef 2",
        fmt_price(
            selected["Hedef 2"]
        )
    )


# ============================================================
# TEKNİK YAPI
# ============================================================

st.markdown(
    "### 📐 Teknik Yapı"
)

c1, c2, c3, c4 = st.columns(4)

with c1:

    st.metric(
        "EMA 9",
        fmt_price(
            selected.get(
                "EMA9",
                0
            )
        )
    )

with c2:

    st.metric(
        "RSI",
        f"{selected['RSI']:.1f}"
    )

with c3:

    st.metric(
        "Hacim",
        f"{selected['Hacim Oranı']:.2f}x"
    )

with c4:

    st.metric(
        "Momentum",
        f"{selected['Momentum']:.1f}"
    )


# ============================================================
# KARAR AÇIKLAMASI
# ============================================================

st.markdown(
    "### 🧠 Karar Motoru Yorumu"
)

st.info(
    selected["Açıklama"]
)


# ============================================================
# PROFESYONEL YORUM
# ============================================================

with st.expander(
    "📚 Bu skorları nasıl yorumlamalıyım?"
):

    st.markdown(
        """
### Kısa Vade Skoru

**80+**

Güçlü kısa vadeli işlem adayı.

**70–79**

İyi yapı ancak giriş bölgesi ve teyit
kontrol edilmeli.

**60–69**

İzlenebilir fakat doğrudan işlem için
yeterli avantaj yok.

**60 altı**

Kısa vadeli işlem önceliği düşük.

---

### Giriş Skoru

Yüksek olması fiyatın mevcut seviyede
işleme daha uygun olduğunu gösterir.

---

### Kovalama Skoru

Bu skorun **düşük olması iyidir.**

**0–30:** Kovalama riski düşük

**31–50:** Normal

**51–70:** Dikkat

**71–100:** Kovalama riski yüksek

---

### En önemli prensip

**Güçlü coin ≠ hemen AL**

Kısa vadede hedefimiz:

**GÜÇ + MOMENTUM + UYGUN GİRİŞ + TEYİT
+ KONTROLLÜ RİSK**

kombinasyonunu bulmaktır.
"""
    )


# ============================================================
# SON UYARI
# ============================================================

st.divider()

st.caption(
    "⚠️ Bu sayfa teknik karar destek sistemidir. "
    "Gerçek işlem öncesinde Binance TR'deki güncel fiyat, "
    "spread, likidite ve emir gerçekleşmesi ayrıca kontrol "
    "edilmelidir."
)