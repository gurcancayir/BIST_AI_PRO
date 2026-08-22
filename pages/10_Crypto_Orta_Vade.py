# ============================================================
# CRYPTO AI PRO
# 09_Crypto_Orta_Vade.py
#
# PROFESYONEL ORTA VADE KRİPTO ANALİZ MOTORU
#
# ORTA VADE:
# ------------------------------------------------------------
# Yaklaşık 1 - 4 haftalık hareketleri değerlendirmek amacıyla
# hazırlanmıştır.
#
# VERİ AKIŞI
# ------------------------------------------------------------
#
# crypto_engine
#       ↓
# Ortak TRY Coin Evreni
#       ↓
# 4H + Günlük Teknik Analiz
#       ↓
# Trend
# Momentum
# RSI
# Hacim
# Destek / Direnç
# Giriş Kalitesi
# Kovalama
# Risk / Ödül
#       ↓
# ORTA VADE FINAL KARAR
#
# KARARLAR
# ------------------------------------------------------------
# 🟢 ORTA VADE AL
# 🟢 GÜÇLÜ TREND
# 🟡 GERİ ÇEKİLME BEKLE
# 🟡 TEYİT BEKLE
# 🔴 AŞIRI YÜKSELMİŞ
# 🔴 İŞLEM YOK
#
# ============================================================

import streamlit as st
import pandas as pd
import numpy as np
import importlib
import crypto_engine
import requests
import time
from datetime import datetime


# ============================================================
# SAYFA AYARLARI
# ============================================================

st.set_page_config(
    page_title="Kripto Orta Vade PRO",
    page_icon="📈",
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

st.title("📈 Kripto Orta Vade PRO")

st.caption(
    "CRYPTO AI PRO | Ortak TRY Coin Evreni | "
    "1–4 Haftalık Trend ve Giriş Analizi"
)

st.info(
    "Bu sayfa yalnızca Kripto Piyasa Merkezi'nin "
    "ortak TRY coin evrenini analiz eder. "
    "Sisteme dışarıdan yeni coin eklenmez."
)


# ============================================================
# AYARLAR
# ============================================================

MIN_VOLUME_TRY = 50_000_000

MAX_COINS = 50

# Öncelikli orta vade zaman dilimi
INTERVAL_PRIMARY = "4h"

# Daha uzun trend teyidi
INTERVAL_SECONDARY = "1d"

KLINE_LIMIT = 150

BUY_SCORE = 78

STRONG_TREND_SCORE = 72

WATCH_SCORE = 62

CHASE_LIMIT = 70


# ============================================================
# YARDIMCI FONKSİYONLAR
# ============================================================

def safe_float(value, default=0.0):

    try:

        if value is None:
            return default

        result = float(value)

        if np.isnan(result):
            return default

        return result

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
# EMA
# ============================================================

def ema(series, period):

    return (
        pd.Series(series)
        .astype(float)
        .ewm(
            span=period,
            adjust=False
        )
        .mean()
    )


# ============================================================
# RSI
# ============================================================

def rsi(series, period=14):

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

    result = 100 - (
        100 / (1 + rs)
    )

    return result


# ============================================================
# ATR
# ============================================================

def atr(df, period=14):

    high = df["high"]

    low = df["low"]

    close = df["close"]

    prev_close = close.shift(1)

    tr = pd.concat(
        [
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1
    ).max(
        axis=1
    )

    return tr.ewm(
        alpha=1 / period,
        adjust=False
    ).mean()


# ============================================================
# ROC
# ============================================================

def roc(series, periods):

    series = pd.Series(
        series
    ).astype(float)

    if len(series) <= periods:

        return 0

    old = safe_float(
        series.iloc[-periods - 1]
    )

    current = safe_float(
        series.iloc[-1]
    )

    if old <= 0:

        return 0

    return (
        (current - old)
        / old
    ) * 100


# ============================================================
# DATAFRAME NORMALİZASYONU
# ============================================================

def normalize_kline_data(data):

    if data is None:

        return pd.DataFrame()

    if isinstance(data, pd.DataFrame):

        df = data.copy()

    elif isinstance(data, list):

        if not data:

            return pd.DataFrame()

        # Binance klasik kline formatı
        if isinstance(
            data[0],
            (list, tuple)
        ):

            rows = []

            for item in data:

                if len(item) < 6:
                    continue

                rows.append(
                    {
                        "open_time": item[0],
                        "open": safe_float(item[1]),
                        "high": safe_float(item[2]),
                        "low": safe_float(item[3]),
                        "close": safe_float(item[4]),
                        "volume": safe_float(item[5]),
                    }
                )

            df = pd.DataFrame(rows)

        elif isinstance(
            data[0],
            dict
        ):

            df = pd.DataFrame(
                data
            )

        else:

            return pd.DataFrame()

    else:

        return pd.DataFrame()

    if df.empty:

        return df

    # --------------------------------------------------------
    # Kolon isimlerini normalize et
    # --------------------------------------------------------

    aliases = {

        "Open": "open",
        "OPEN": "open",

        "High": "high",
        "HIGH": "high",

        "Low": "low",
        "LOW": "low",

        "Close": "close",
        "CLOSE": "close",

        "Volume": "volume",
        "VOLUME": "volume",

        "openPrice": "open",
        "highPrice": "high",
        "lowPrice": "low",
        "closePrice": "close",

    }

    df = df.rename(
        columns=aliases
    )

    required = [
        "open",
        "high",
        "low",
        "close",
        "volume"
    ]

    if not all(
        col in df.columns
        for col in required
    ):

        return pd.DataFrame()

    for col in required:

        df[col] = pd.to_numeric(
            df[col],
            errors="coerce"
        )

    df = df.dropna(
        subset=required
    ).copy()

    if df.empty:

        return df

    df = df.sort_index()

    return df.reset_index(
        drop=True
    )


# ============================================================
# ENGINE'DAN KLINE AL
#
# Engine içinde farklı fonksiyon isimleri olabilir.
# Birkaç yaygın isim desteklenmektedir.
# ============================================================

def get_engine_klines(symbol, interval):

    candidates = [
        "get_klines",
        "get_kline_data",
        "get_ohlcv",
        "get_ohlcv_data",
        "fetch_klines",
        "fetch_ohlcv",
    ]

    # --------------------------------------------------------
    # Önce engine fonksiyonlarını dene
    # --------------------------------------------------------

    for func_name in candidates:

        func = getattr(
            crypto_engine,
            func_name,
            None
        )

        if not callable(func):

            continue

        attempts = [

            lambda: func(
                symbol,
                interval=interval,
                limit=KLINE_LIMIT
            ),

            lambda: func(
                symbol=symbol,
                interval=interval,
                limit=KLINE_LIMIT
            ),

            lambda: func(
                symbol,
                interval,
                KLINE_LIMIT
            ),

            lambda: func(
                symbol,
                interval
            ),

        ]

        for attempt in attempts:

            try:

                result = attempt()

                df = normalize_kline_data(
                    result
                )

                if not df.empty:

                    return df

            except Exception:

                continue

    return pd.DataFrame()


# ============================================================
# FALLBACK
#
# Engine kline fonksiyonu yoksa ortak TRY evrenindeki
# sembol ile Binance TR API denenir.
# ============================================================

@st.cache_data(
    ttl=300,
    show_spinner=False
)
def fallback_klines(
    symbol,
    interval
):

    endpoints = [

        "https://api.binance.me/api/v3/klines",

        "https://api.binance.com/api/v3/klines",

    ]

    # --------------------------------------------------------
    # Sembol normalizasyonu
    # --------------------------------------------------------

    clean_symbol = (
        str(symbol)
        .upper()
        .replace(
            "_",
            ""
        )
        .replace(
            "-",
            ""
        )
    )

    if not clean_symbol.endswith(
        "TRY"
    ):

        if "_TRY" in str(symbol).upper():

            clean_symbol = (
                str(symbol)
                .upper()
                .replace(
                    "_",
                    ""
                )
            )

        else:

            clean_symbol += "TRY"

    params = {

        "symbol": clean_symbol,

        "interval": interval,

        "limit": KLINE_LIMIT,

    }

    for endpoint in endpoints:

        try:

            response = requests.get(
                endpoint,
                params=params,
                timeout=8
            )

            if response.status_code != 200:

                continue

            data = response.json()

            df = normalize_kline_data(
                data
            )

            if not df.empty:

                return df

        except Exception:

            continue

    return pd.DataFrame()


# ============================================================
# KLINE GETİR
# ============================================================

def get_klines(symbol, interval):

    df = get_engine_klines(
        symbol,
        interval
    )

    if not df.empty:

        return df

    return fallback_klines(
        symbol,
        interval
    )


# ============================================================
# TEKNİK ANALİZ
# ============================================================

def analyze_timeframe(df):

    if df.empty or len(df) < 60:

        return None

    df = df.copy()

    df["ema20"] = ema(
        df["close"],
        20
    )

    df["ema50"] = ema(
        df["close"],
        50
    )

    df["ema100"] = ema(
        df["close"],
        100
    )

    df["rsi"] = rsi(
        df["close"],
        14
    )

    df["atr"] = atr(
        df,
        14
    )

    last = df.iloc[-1]

    price = safe_float(
        last["close"]
    )

    ema20 = safe_float(
        last["ema20"],
        price
    )

    ema50 = safe_float(
        last["ema50"],
        price
    )

    ema100 = safe_float(
        last["ema100"],
        price
    )

    current_rsi = safe_float(
        last["rsi"],
        50
    )

    current_atr = safe_float(
        last["atr"],
        price * 0.05
    )

    # --------------------------------------------------------
    # Hacim
    # --------------------------------------------------------

    avg_volume = safe_float(
        df["volume"]
        .iloc[-21:-1]
        .mean(),
        1
    )

    current_volume = safe_float(
        last["volume"]
    )

    volume_ratio = (
        current_volume /
        avg_volume
        if avg_volume > 0
        else 1
    )

    # --------------------------------------------------------
    # Destek / Direnç
    # --------------------------------------------------------

    lookback = df.iloc[
        -60:-1
    ]

    resistance = safe_float(
        lookback["high"].max(),
        price
    )

    support = safe_float(
        lookback["low"].min(),
        price * 0.90
    )

    # --------------------------------------------------------
    # Momentum
    # --------------------------------------------------------

    momentum_7 = roc(
        df["close"],
        7
    )

    momentum_14 = roc(
        df["close"],
        14
    )

    # --------------------------------------------------------
    # TREND SKORU
    # --------------------------------------------------------

    trend_score = 0

    if price > ema20:
        trend_score += 20

    if ema20 > ema50:
        trend_score += 25

    if ema50 > ema100:
        trend_score += 25

    if price > ema50:
        trend_score += 15

    if price > ema100:
        trend_score += 15

    trend_score = clamp(
        trend_score
    )

    # --------------------------------------------------------
    # RSI SKORU
    # --------------------------------------------------------

    if 52 <= current_rsi <= 68:

        rsi_score = 95

    elif 68 < current_rsi <= 73:

        rsi_score = 82

    elif 45 <= current_rsi < 52:

        rsi_score = 68

    elif 73 < current_rsi <= 78:

        rsi_score = 62

    elif current_rsi > 78:

        rsi_score = 35

    elif current_rsi < 35:

        rsi_score = 30

    else:

        rsi_score = 50

    # --------------------------------------------------------
    # MOMENTUM SKORU
    # --------------------------------------------------------

    momentum_score = 50

    if momentum_7 > 10:
        momentum_score += 20

    elif momentum_7 > 5:
        momentum_score += 15

    elif momentum_7 > 0:
        momentum_score += 8

    elif momentum_7 < -10:
        momentum_score -= 20

    elif momentum_7 < -5:
        momentum_score -= 10

    if momentum_14 > 15:
        momentum_score += 20

    elif momentum_14 > 5:
        momentum_score += 12

    elif momentum_14 > 0:
        momentum_score += 5

    elif momentum_14 < -10:
        momentum_score -= 15

    momentum_score = clamp(
        momentum_score
    )

    # --------------------------------------------------------
    # HACİM SKORU
    # --------------------------------------------------------

    if volume_ratio >= 2:
        volume_score = 100

    elif volume_ratio >= 1.5:
        volume_score = 90

    elif volume_ratio >= 1.2:
        volume_score = 80

    elif volume_ratio >= 1:
        volume_score = 70

    elif volume_ratio >= 0.7:
        volume_score = 55

    else:
        volume_score = 40

    # --------------------------------------------------------
    # TEKNİK SKOR
    # --------------------------------------------------------

    technical_score = (
        trend_score * 0.45
        + momentum_score * 0.25
        + rsi_score * 0.15
        + volume_score * 0.15
    )

    technical_score = clamp(
        technical_score
    )

    return {

        "price": price,

        "ema20": ema20,

        "ema50": ema50,

        "ema100": ema100,

        "rsi": current_rsi,

        "atr": current_atr,

        "volume_ratio": volume_ratio,

        "momentum_7": momentum_7,

        "momentum_14": momentum_14,

        "trend_score": trend_score,

        "momentum_score": momentum_score,

        "volume_score": volume_score,

        "technical_score": technical_score,

        "support": support,

        "resistance": resistance,

    }


# ============================================================
# GİRİŞ KALİTESİ
# ============================================================

def calculate_entry_quality(
    price,
    technical
):

    support = technical["support"]

    resistance = technical["resistance"]

    rsi_value = technical["rsi"]

    # --------------------------------------------------------
    # Dirence uzaklık
    # --------------------------------------------------------

    if resistance > 0:

        resistance_distance = (
            (resistance - price)
            / resistance
        ) * 100

    else:

        resistance_distance = 0

    # --------------------------------------------------------
    # Desteğe uzaklık
    # --------------------------------------------------------

    if support > 0:

        support_distance = (
            (price - support)
            / price
        ) * 100

    else:

        support_distance = 10

    # --------------------------------------------------------
    # Pozisyon skoru
    # --------------------------------------------------------

    if resistance_distance >= 12:

        position_score = 95

    elif resistance_distance >= 8:

        position_score = 90

    elif resistance_distance >= 5:

        position_score = 82

    elif resistance_distance >= 3:

        position_score = 72

    elif resistance_distance >= 1:

        position_score = 60

    else:

        position_score = 45

    # --------------------------------------------------------
    # RSI
    # --------------------------------------------------------

    if 52 <= rsi_value <= 65:

        rsi_entry = 95

    elif 65 < rsi_value <= 72:

        rsi_entry = 80

    elif 72 < rsi_value <= 78:

        rsi_entry = 60

    elif rsi_value > 78:

        rsi_entry = 35

    else:

        rsi_entry = 60

    # --------------------------------------------------------
    # Desteğe yakınlık
    # --------------------------------------------------------

    if support_distance <= 5:

        support_score = 95

    elif support_distance <= 10:

        support_score = 85

    elif support_distance <= 15:

        support_score = 72

    else:

        support_score = 55

    result = (
        position_score * 0.45
        + rsi_entry * 0.30
        + support_score * 0.25
    )

    return clamp(
        result
    )


# ============================================================
# KOVALAMA
# ============================================================

def calculate_chase(
    change_24h,
    momentum_7,
    rsi_value,
    price,
    high_24h
):

    score = 0

    # --------------------------------------------------------
    # 24 saatlik hareket
    # --------------------------------------------------------

    if change_24h >= 25:

        score += 40

    elif change_24h >= 20:

        score += 32

    elif change_24h >= 15:

        score += 24

    elif change_24h >= 10:

        score += 15

    elif change_24h >= 7:

        score += 8

    # --------------------------------------------------------
    # 7 günlük momentum
    # --------------------------------------------------------

    if momentum_7 >= 30:

        score += 25

    elif momentum_7 >= 20:

        score += 18

    elif momentum_7 >= 12:

        score += 12

    elif momentum_7 >= 7:

        score += 6

    # --------------------------------------------------------
    # RSI
    # --------------------------------------------------------

    if rsi_value >= 85:

        score += 30

    elif rsi_value >= 80:

        score += 23

    elif rsi_value >= 75:

        score += 14

    # --------------------------------------------------------
    # Günlük zirve
    # --------------------------------------------------------

    if high_24h > 0:

        distance_high = (
            (high_24h - price)
            / high_24h
        ) * 100

        if distance_high <= 1:

            score += 15

        elif distance_high <= 2:

            score += 10

        elif distance_high <= 4:

            score += 5

    return clamp(
        score
    )


# ============================================================
# RİSK / ÖDÜL
# ============================================================

def calculate_levels(
    price,
    technical
):

    support = safe_float(
        technical["support"],
        price * 0.90
    )

    resistance = safe_float(
        technical["resistance"],
        price * 1.10
    )

    atr_value = safe_float(
        technical["atr"],
        price * 0.05
    )

    # --------------------------------------------------------
    # Stop
    # --------------------------------------------------------

    atr_stop = (
        price -
        atr_value * 1.7
    )

    support_stop = (
        support * 0.985
    )

    stop = max(
        atr_stop,
        support_stop
    )

    # Stop mevcut fiyatın üstünde kalmasın
    if stop >= price:

        stop = price * 0.94

    risk = price - stop

    if risk <= 0:

        risk = price * 0.06

        stop = price - risk

    # --------------------------------------------------------
    # Hedefler
    # --------------------------------------------------------

    target1 = price + (
        risk * 2
    )

    target2 = price + (
        risk * 3
    )

    # Eğer direnç daha yakınsa hedef1 direnci
    if resistance > price:

        if resistance > target1:

            target1 = resistance

    rr1 = (
        (target1 - price)
        / risk
        if risk > 0
        else 0
    )

    rr2 = (
        (target2 - price)
        / risk
        if risk > 0
        else 0
    )

    return {

        "stop": stop,

        "target1": target1,

        "target2": target2,

        "risk_pct": (
            risk / price
        ) * 100,

        "rr1": rr1,

        "rr2": rr2,

        "resistance": resistance,

        "support": support,

    }


# ============================================================
# FINAL KARAR
# ============================================================

def final_decision(
    row,
    technical,
    entry_quality,
    chase,
    levels
):

    technical_score = technical[
        "technical_score"
    ]

    trend_score = technical[
        "trend_score"
    ]

    momentum_score = technical[
        "momentum_score"
    ]

    volume_ratio = technical[
        "volume_ratio"
    ]

    # --------------------------------------------------------
    # Orta vade final
    # --------------------------------------------------------

    final = (
        technical_score * 0.45
        + trend_score * 0.20
        + entry_quality * 0.20
        + momentum_score * 0.10
        + (100 - chase) * 0.05
    )

    # R/R bonus
    if levels["rr1"] >= 2:

        final += 3

    elif levels["rr1"] >= 1.5:

        final += 1

    final = clamp(
        final
    )

    # --------------------------------------------------------
    # Aşırı yükselmiş
    # --------------------------------------------------------

    if chase >= CHASE_LIMIT:

        return (
            final,
            "🔴 AŞIRI YÜKSELMİŞ",
            "Trend güçlü ancak mevcut fiyatı kovalamak "
            "orta vadeli risk/getiri açısından uygun değil."
        )

    # --------------------------------------------------------
    # Orta vadeli AL
    # --------------------------------------------------------

    if (
        final >= BUY_SCORE
        and trend_score >= 70
        and entry_quality >= 68
        and chase < 60
        and levels["rr1"] >= 1.8
    ):

        return (
            final,
            "🟢 ORTA VADE AL",
            "Trend, momentum, giriş kalitesi ve "
            "risk/getiri birlikte olumlu."
        )

    # --------------------------------------------------------
    # Güçlü trend
    # --------------------------------------------------------

    if (
        final >= STRONG_TREND_SCORE
        and trend_score >= 75
        and momentum_score >= 65
    ):

        if entry_quality < 65:

            return (
                final,
                "🟡 GERİ ÇEKİLME BEKLE",
                "Orta vadeli trend güçlü ancak mevcut "
                "giriş bölgesi yeterince avantajlı değil."
            )

        return (
            final,
            "🟢 GÜÇLÜ TREND",
            "Orta vadeli trend ve momentum güçlü."
        )

    # --------------------------------------------------------
    # Geri çekilme
    # --------------------------------------------------------

    if (
        technical_score >= 70
        and entry_quality < 65
    ):

        return (
            final,
            "🟡 GERİ ÇEKİLME BEKLE",
            "Coin güçlü fakat daha avantajlı giriş "
            "için geri çekilme bekleniyor."
        )

    # --------------------------------------------------------
    # Teyit
    # --------------------------------------------------------

    if final >= WATCH_SCORE:

        return (
            final,
            "🟡 TEYİT BEKLE",
            "Orta vadeli potansiyel var ancak "
            "trend teyidi henüz yeterince güçlü değil."
        )

    # --------------------------------------------------------
    # İşlem yok
    # --------------------------------------------------------

    return (
        final,
        "🔴 İŞLEM YOK",
        "Mevcut koşullarda orta vadeli işlem avantajı "
        "yeterli değil."
    )


# ============================================================
# ORTA VADE ANALİZ
# ============================================================

def analyze_market(df):

    results = []

    progress = st.progress(
        0,
        text="Orta vadeli analiz hazırlanıyor..."
    )

    total = len(df)

    for index, (_, row) in enumerate(
        df.iterrows()
    ):

        symbol = str(
            row.get(
                "symbol",
                ""
            )
        )

        coin = str(
            row.get(
                "base_asset",
                symbol
            )
        )

        # ----------------------------------------------------
        # TRY evreni filtresi
        # ----------------------------------------------------

        symbol_upper = symbol.upper()

        if (
            "TRY" not in symbol_upper
            and "_TRY" not in symbol_upper
        ):

            continue

        # ----------------------------------------------------
        # 4H
        # ----------------------------------------------------

        df_4h = get_klines(
            symbol,
            INTERVAL_PRIMARY
        )

        # ----------------------------------------------------
        # Günlük
        # ----------------------------------------------------

        df_1d = get_klines(
            symbol,
            INTERVAL_SECONDARY
        )

        technical_4h = analyze_timeframe(
            df_4h
        )

        technical_1d = analyze_timeframe(
            df_1d
        )

        # ----------------------------------------------------
        # 4H yoksa günlük kullan
        # ----------------------------------------------------

        technical = (
            technical_4h
            if technical_4h is not None
            else technical_1d
        )

        if technical is None:

            progress.progress(
                (index + 1) / total,
                text=f"{coin} veri bekleniyor..."
            )

            continue

        price = safe_float(
            row.get(
                "price_try",
                technical["price"]
            ),
            technical["price"]
        )

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

        high_24h = safe_float(
            row.get(
                "high_24h",
                price
            ),
            price
        )

        low_24h = safe_float(
            row.get(
                "low_24h",
                price
            ),
            price
        )

        # ----------------------------------------------------
        # Günlük teyit
        # ----------------------------------------------------

        daily_trend = 50

        if technical_1d is not None:

            daily_trend = (
                technical_1d[
                    "trend_score"
                ]
            )

        # ----------------------------------------------------
        # Giriş
        # ----------------------------------------------------

        entry_quality = calculate_entry_quality(
            price,
            technical
        )

        # ----------------------------------------------------
        # Kovalama
        # ----------------------------------------------------

        chase = calculate_chase(
            change,
            technical["momentum_7"],
            technical["rsi"],
            price,
            high_24h
        )

        # ----------------------------------------------------
        # Risk / Ödül
        # ----------------------------------------------------

        levels = calculate_levels(
            price,
            technical
        )

        # ----------------------------------------------------
        # Final
        # ----------------------------------------------------

        final, decision, reason = final_decision(
            row,
            technical,
            entry_quality,
            chase,
            levels
        )

        # ----------------------------------------------------
        # Trend durumu
        # ----------------------------------------------------

        if technical["trend_score"] >= 80:

            trend_label = "🟢 ÇOK GÜÇLÜ"

        elif technical["trend_score"] >= 70:

            trend_label = "🟢 GÜÇLÜ"

        elif technical["trend_score"] >= 55:

            trend_label = "🟡 POZİTİF"

        else:

            trend_label = "🔴 ZAYIF"

        results.append(
            {

                "Coin": coin,

                "Parite": symbol,

                "Fiyat": price,

                "24s %": change,

                "Hacim": volume,

                "Trend": round(
                    technical["trend_score"],
                    1
                ),

                "Momentum": round(
                    technical["momentum_score"],
                    1
                ),

                "RSI": round(
                    technical["rsi"],
                    1
                ),

                "Hacim Oranı": round(
                    technical["volume_ratio"],
                    2
                ),

                "Giriş Kalitesi": round(
                    entry_quality,
                    1
                ),

                "Kovalama": round(
                    chase,
                    1
                ),

                "Destek": technical[
                    "support"
                ],

                "Direnç": technical[
                    "resistance"
                ],

                "EMA20": technical[
                    "ema20"
                ],

                "EMA50": technical[
                    "ema50"
                ],

                "EMA100": technical[
                    "ema100"
                ],

                "Günlük Trend": round(
                    daily_trend,
                    1
                ),

                "Stop": levels[
                    "stop"
                ],

                "Hedef 1": levels[
                    "target1"
                ],

                "Hedef 2": levels[
                    "target2"
                ],

                "Risk %": levels[
                    "risk_pct"
                ],

                "R/R": levels[
                    "rr1"
                ],

                "Final": round(
                    final,
                    1
                ),

                "Trend Durumu": trend_label,

                "Karar": decision,

                "Açıklama": reason,

            }
        )

        progress.progress(
            (index + 1) / total,
            text=f"{coin} analiz ediliyor..."
        )

        time.sleep(
            0.02
        )

    progress.empty()

    result = pd.DataFrame(
        results
    )

    if result.empty:

        return result

    return result.sort_values(
        "Final",
        ascending=False
    ).reset_index(
        drop=True
    )


# ============================================================
# ORTAK EVRENİ AL
# ============================================================

try:

    raw_data = (
        crypto_engine
        .get_all_try_universe()
    )

except Exception as e:

    st.error(
        "Kripto piyasa evreni alınamadı."
    )

    st.exception(e)

    st.stop()


# ============================================================
# DATAFRAME NORMALİZASYONU
# ============================================================

if raw_data is None:

    st.error(
        "Kripto piyasa motoru veri döndürmedi."
    )

    st.stop()


if isinstance(
    raw_data,
    pd.DataFrame
):

    df_market = raw_data.copy()


elif isinstance(
    raw_data,
    list
):

    if not raw_data:

        st.warning(
            "TRY coin evreni boş."
        )

        st.stop()

    df_market = pd.DataFrame(
        raw_data
    )


else:

    st.error(
        f"Beklenmeyen veri tipi: "
        f"{type(raw_data).__name__}"
    )

    st.stop()


# ============================================================
# DATAFRAME KONTROL
# ============================================================

if df_market.empty:

    st.warning(
        "Analiz edilecek TRY coin bulunamadı."
    )

    st.stop()


# ============================================================
# KOLONLARI HAZIRLA
# ============================================================

if "symbol" not in df_market.columns:

    st.error(
        "Ortak piyasa evreninde symbol kolonu bulunamadı."
    )

    st.stop()


if "base_asset" not in df_market.columns:

    df_market["base_asset"] = (
        df_market["symbol"]
        .astype(str)
        .str.upper()
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
    )


# ============================================================
# SADECE TRY
# ============================================================

df_market["symbol"] = (
    df_market["symbol"]
    .astype(str)
    .str.upper()
    .str.strip()
)

df_market = df_market[
    df_market["symbol"].str.contains(
        "TRY",
        na=False
    )
].copy()


# ============================================================
# HACİM FİLTRESİ
# ============================================================

if "volume_try" in df_market.columns:

    df_market["volume_try"] = pd.to_numeric(
        df_market["volume_try"],
        errors="coerce"
    ).fillna(0)

    df_market = df_market[
        df_market["volume_try"]
        >= MIN_VOLUME_TRY
    ].copy()


# ============================================================
# MAX COIN
# ============================================================

if len(df_market) > MAX_COINS:

    if "volume_try" in df_market.columns:

        df_market = (
            df_market
            .sort_values(
                "volume_try",
                ascending=False
            )
            .head(
                MAX_COINS
            )
            .copy()
        )

    else:

        df_market = df_market.head(
            MAX_COINS
        )


# ============================================================
# ÜST BİLGİ
# ============================================================

st.caption(
    f"Ortak piyasa evreni aktif | "
    f"Analiz edilen evren: {len(df_market)} coin | "
    f"Son güncelleme: "
    f"{datetime.now().strftime('%d.%m.%Y %H:%M:%S')}"
)


# ============================================================
# ANALİZ
# ============================================================

with st.spinner(
    "Orta vadeli coin analizi yapılıyor..."
):

    df_result = analyze_market(
        df_market
    )


if df_result.empty:

    st.warning(
        "Yeterli teknik geçmiş verisi bulunan coin "
        "bulunamadı."
    )

    st.info(
        "Kripto Piyasa Merkezi'ni açıp verinin "
        "güncellenmesini sağlayın."
    )

    st.stop()


# ============================================================
# ÜST METRİKLER
# ============================================================

buy_count = len(
    df_result[
        df_result["Karar"]
        == "🟢 ORTA VADE AL"
    ]
)

strong_count = len(
    df_result[
        df_result["Karar"]
        == "🟢 GÜÇLÜ TREND"
    ]
)

pullback_count = len(
    df_result[
        df_result["Karar"]
        == "🟡 GERİ ÇEKİLME BEKLE"
    ]
)

avg_final = safe_float(
    df_result["Final"].mean()
)


c1, c2, c3, c4 = st.columns(4)


with c1:

    st.metric(
        "Analiz Edilen",
        len(df_result)
    )


with c2:

    st.metric(
        "🟢 Orta Vade AL",
        buy_count
    )


with c3:

    st.metric(
        "🟢 Güçlü Trend",
        strong_count
    )


with c4:

    st.metric(
        "Ortalama Final",
        f"{avg_final:.1f}"
    )


# ============================================================
# EN İYİ ORTA VADE ADAYLARI
# ============================================================

st.divider()

st.subheader(
    "🏆 Orta Vadede En Güçlü Coinler"
)

top_df = df_result[
    df_result["Karar"].isin(
        [
            "🟢 ORTA VADE AL",
            "🟢 GÜÇLÜ TREND"
        ]
    )
].copy()


if not top_df.empty:

    for _, row in top_df.head(5).iterrows():

        with st.container(
            border=True
        ):

            c1, c2, c3, c4, c5 = st.columns(5)

            with c1:

                st.markdown(
                    f"### 🪙 {row['Coin']}"
                )

                st.metric(
                    "FINAL",
                    f"{row['Final']:.1f}"
                )

                st.markdown(
                    f"**{row['Karar']}**"
                )

            with c2:

                st.metric(
                    "Trend",
                    f"{row['Trend']:.1f}"
                )

                st.metric(
                    "Momentum",
                    f"{row['Momentum']:.1f}"
                )

            with c3:

                st.metric(
                    "Giriş Kalitesi",
                    f"{row['Giriş Kalitesi']:.1f}"
                )

                st.metric(
                    "Kovalama",
                    f"{row['Kovalama']:.1f}"
                )

            with c4:

                st.metric(
                    "RSI",
                    f"{row['RSI']:.1f}"
                )

                st.metric(
                    "Hacim",
                    f"{row['Hacim Oranı']:.2f}x"
                )

            with c5:

                st.metric(
                    "R/R",
                    f"1 : {row['R/R']:.1f}"
                )

                st.metric(
                    "24s",
                    f"{row['24s %']:+.2f}%"
                )

            st.write(
                f"**Fiyat:** "
                f"{fmt_price(row['Fiyat'])}"
            )

            st.write(
                f"**Destek:** "
                f"{fmt_price(row['Destek'])}"
                f"  |  "
                f"**Direnç:** "
                f"{fmt_price(row['Direnç'])}"
            )

            st.write(
                f"**Stop:** "
                f"{fmt_price(row['Stop'])}"
                f"  |  "
                f"**Hedef 1:** "
                f"{fmt_price(row['Hedef 1'])}"
                f"  |  "
                f"**Hedef 2:** "
                f"{fmt_price(row['Hedef 2'])}"
            )

            st.caption(
                row["Açıklama"]
            )

else:

    st.info(
        "Şu anda orta vadeli kriterlerin tamamını "
        "karşılayan güçlü coin bulunamadı."
    )


# ============================================================
# GERİ ÇEKİLME FIRSATLARI
# ============================================================

st.divider()

st.subheader(
    "🟡 Güçlü Ama Geri Çekilme Beklenenler"
)

pullback_df = df_result[
    df_result["Karar"]
    == "🟡 GERİ ÇEKİLME BEKLE"
].copy()


if not pullback_df.empty:

    st.dataframe(
        pullback_df[
            [
                "Coin",
                "Fiyat",
                "24s %",
                "Trend",
                "Momentum",
                "Giriş Kalitesi",
                "Kovalama",
                "RSI",
                "Final",
                "R/R",
            ]
        ],
        use_container_width=True,
        hide_index=True
    )

else:

    st.success(
        "Geri çekilme beklenen güçlü coin bulunamadı."
    )


# ============================================================
# TEYİT BEKLEYENLER
# ============================================================

st.divider()

st.subheader(
    "🟡 Teyit Bekleyenler"
)

confirm_df = df_result[
    df_result["Karar"]
    == "🟡 TEYİT BEKLE"
].copy()


if not confirm_df.empty:

    st.dataframe(
        confirm_df[
            [
                "Coin",
                "Fiyat",
                "24s %",
                "Trend",
                "Momentum",
                "RSI",
                "Giriş Kalitesi",
                "Final",
            ]
        ],
        use_container_width=True,
        hide_index=True
    )

else:

    st.success(
        "Teyit bekleyen coin bulunamadı."
    )


# ============================================================
# AŞIRI YÜKSELENLER
# ============================================================

st.divider()

st.subheader(
    "🔴 Aşırı Yükselmiş / Kovalama Riski"
)

chase_df = df_result[
    df_result["Karar"]
    == "🔴 AŞIRI YÜKSELMİŞ"
].copy()


if not chase_df.empty:

    st.dataframe(
        chase_df[
            [
                "Coin",
                "Fiyat",
                "24s %",
                "Trend",
                "Momentum",
                "RSI",
                "Kovalama",
                "Giriş Kalitesi",
                "Final",
            ]
        ],
        use_container_width=True,
        hide_index=True
    )

else:

    st.success(
        "Orta vadede aşırı kovalama riski taşıyan "
        "coin bulunamadı."
    )


# ============================================================
# TÜM COİNLER
# ============================================================

st.divider()

st.subheader(
    "📊 Tüm Coinler — Orta Vade Karar Tablosu"
)

all_columns = [
    "Coin",
    "Fiyat",
    "24s %",
    "Trend",
    "Momentum",
    "RSI",
    "Hacim Oranı",
    "Giriş Kalitesi",
    "Kovalama",
    "Günlük Trend",
    "Final",
    "R/R",
    "Karar",
]

st.dataframe(
    df_result[
        all_columns
    ],
    use_container_width=True,
    hide_index=True,
    height=650
)


# ============================================================
# COİN DETAY ANALİZİ
# ============================================================

st.divider()

st.subheader(
    "🔎 Orta Vadeli Coin Analizi"
)

coin_list = (
    df_result["Coin"]
    .drop_duplicates()
    .tolist()
)

selected_coin = st.selectbox(
    "Analiz etmek istediğiniz coin",
    coin_list
)

selected = df_result[
    df_result["Coin"]
    == selected_coin
].iloc[0]


st.markdown(
    f"## 🪙 {selected['Coin']}"
)


if "🟢" in selected["Karar"]:

    st.success(
        selected["Karar"]
    )

elif "🟡" in selected["Karar"]:

    st.warning(
        selected["Karar"]
    )

else:

    st.error(
        selected["Karar"]
    )


# ============================================================
# SKORLAR
# ============================================================

c1, c2, c3, c4, c5, c6 = st.columns(6)


with c1:

    st.metric(
        "FINAL",
        f"{selected['Final']:.1f}"
    )


with c2:

    st.metric(
        "Trend",
        f"{selected['Trend']:.1f}"
    )


with c3:

    st.metric(
        "Momentum",
        f"{selected['Momentum']:.1f}"
    )


with c4:

    st.metric(
        "Giriş",
        f"{selected['Giriş Kalitesi']:.1f}"
    )


with c5:

    st.metric(
        "Kovalama",
        f"{selected['Kovalama']:.1f}"
    )


with c6:

    st.metric(
        "R/R",
        f"1 : {selected['R/R']:.1f}"
    )


# ============================================================
# İŞLEM PLANI
# ============================================================

st.markdown(
    "### 🎯 Orta Vadeli İşlem Planı"
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
        "Destek",
        fmt_price(
            selected["Destek"]
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
        "Direnç",
        fmt_price(
            selected["Direnç"]
        )
    )


st.write(
    f"**Hedef 1:** "
    f"{fmt_price(selected['Hedef 1'])}"
    f"  |  "
    f"**Hedef 2:** "
    f"{fmt_price(selected['Hedef 2'])}"
)

st.write(
    f"**Risk:** "
    f"{selected['Risk %']:.2f}%"
    f"  |  "
    f"**R/R:** "
    f"1 : {selected['R/R']:.2f}"
)


# ============================================================
# TEKNİK YAPI
# ============================================================

st.markdown(
    "### 📐 Teknik Yapı"
)

t1, t2, t3, t4, t5 = st.columns(5)


with t1:

    st.metric(
        "EMA20",
        fmt_price(
            selected["EMA20"]
        )
    )


with t2:

    st.metric(
        "EMA50",
        fmt_price(
            selected["EMA50"]
        )
    )


with t3:

    st.metric(
        "EMA100",
        fmt_price(
            selected["EMA100"]
        )
    )


with t4:

    st.metric(
        "RSI",
        f"{selected['RSI']:.1f}"
    )


with t5:

    st.metric(
        "Hacim",
        f"{selected['Hacim Oranı']:.2f}x"
    )


st.info(
    selected["Açıklama"]
)


# ============================================================
# KARAR MOTORU
# ============================================================

with st.expander(
    "🧠 Orta Vade Karar Motoru Nasıl Çalışıyor?"
):

    st.markdown(
        """
### 1. Trend

Orta vadede:

- EMA20
- EMA50
- EMA100
- Fiyat / EMA ilişkisi

kontrol edilir.

EMA20 > EMA50 > EMA100 yapısı
orta vadeli yükseliş trendinin önemli
teyitlerinden biridir.

---

### 2. Momentum

7 günlük ve 14 günlük momentum
birlikte değerlendirilir.

Amaç yalnızca bugün yükselen coinleri
değil, trendi devam eden coinleri bulmaktır.

---

### 3. RSI

RSI tek başına AL sinyali değildir.

Örneğin RSI 85 olan bir coin çok güçlü
olabilir ancak mevcut fiyatı kovalamak
orta vadede riskli olabilir.

---

### 4. Giriş Kalitesi

Sistem şu soruya cevap arar:

**"Coin güçlü mü?"**

değil,

**"Coin güçlü ve şu anda alınabilir bir bölgede mi?"**

---

### 5. Kovalama

Kovalama skoru:

**0 → düşük risk**

**100 → çok yüksek risk**

şeklindedir.

24 saatlik aşırı yükseliş,
7 günlük güçlü momentum,
yüksek RSI ve günlük zirveye yakınlık
kovalama skorunu yükseltir.

---

### 6. Risk / Ödül

Her aday için:

- Destek
- Stop
- Hedef 1
- Hedef 2
- R/R

hesaplanır.

Amaç yalnızca yüksek skor değil,
**makul risk karşılığında yeterli potansiyel**
bulmaktır.

---

### 7. Nihai prensip

**Güçlü coin ≠ otomatik AL**

Orta vadeli ideal aday:

**Güçlü trend**
+
**Pozitif momentum**
+
**Uygun giriş**
+
**Kontrollü kovalama**
+
**İyi risk/getiri**

kombinasyonudur.
"""
    )


# ============================================================
# SON UYARI
# ============================================================

st.divider()

st.caption(
    "⚠️ Bu sayfa teknik karar desteği sağlar. "
    "Orta vadeli karar öncesinde likidite, spread, "
    "emir gerçekleşmesi ve piyasa koşulları ayrıca "
    "kontrol edilmelidir."
)