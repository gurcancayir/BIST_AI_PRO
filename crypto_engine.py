# ============================================================
# BIST AI PRO
# crypto_engine.py
#
# TÜRKİYE CRYPTO MOTORU
#
# EVREN:
#   BtcTurk TRY spot pariteleri
#
# VADeler:
#   Günlük Trade
#   Kısa Vade
#   Orta Vade
#   Uzun Vade
#
# ÖNEMLİ:
#   - Sadece TRY pariteleri
#   - USDT / USD / BTC pariteleri yok
#   - Sadece spot piyasalar
#   - Minimum likidite filtresi
#   - Teknik skor
#   - BTC piyasa rejimi
#   - Her vade için ayrı skor
# ============================================================

import requests
import pandas as pd
import numpy as np

from datetime import datetime
from functools import lru_cache


# ============================================================
# AYARLAR
# ============================================================

BASE_URL = "https://api.btcturk.com/api/v2"

TIMEOUT = 15

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 "
        "BIST-AI-PRO-Crypto"
    )
}

# Türkiye pazarında çok düşük hacimli coinleri ele
MIN_VOLUME_TRY = 2_000_000

# İlk aşamada taranacak maksimum coin
MAX_COINS = 100

# API OHLC geçmişi
OHLC_LIMIT = 250


# ============================================================
# HTTP
# ============================================================

def api_get(endpoint, params=None):

    try:

        response = requests.get(
            f"{BASE_URL}/{endpoint}",
            params=params,
            headers=HEADERS,
            timeout=TIMEOUT,
        )

        response.raise_for_status()

        data = response.json()

        if isinstance(data, dict):

            return data.get(
                "data",
                data
            )

        return data

    except Exception:

        return None


# ============================================================
# TÜRKİYE / TRY EVRENİ
# ============================================================

@lru_cache(maxsize=1)
def get_try_markets():

    data = api_get(
        "server/exchangeinfo"
    )

    if not data:
        return []

    markets = []

    if isinstance(data, dict):

        data = data.get(
            "symbols",
            data.get("data", [])
        )

    if not isinstance(data, list):

        return []

    for item in data:

        if not isinstance(item, dict):
            continue

        numerator = str(
            item.get(
                "numerator",
                ""
            )
        ).upper()

        denominator = str(
            item.get(
                "denominator",
                ""
            )
        ).upper()

        status = str(
            item.get(
                "status",
                "TRADING"
            )
        ).upper()

        if denominator != "TRY":
            continue

        if status not in (
            "",
            "TRADING",
            "1",
            "ACTIVE",
        ):
            continue

        if not numerator:
            continue

        symbol = f"{numerator}TRY"

        markets.append(
            {
                "symbol": symbol,
                "coin": numerator,
            }
        )

    # Tekilleştir
    unique = {}

    for market in markets:

        unique[
            market["symbol"]
        ] = market

    return list(
        unique.values()
    )


# ============================================================
# TICKER
# ============================================================

@lru_cache(maxsize=1)
def get_all_tickers():

    data = api_get(
        "ticker"
    )

    if not data:
        return []

    if isinstance(data, dict):

        data = data.get(
            "data",
            []
        )

    if not isinstance(data, list):

        return []

    return data


# ============================================================
# TRY TICKER EVRENİ
# ============================================================

def get_try_tickers():

    markets = {
        x["symbol"]
        for x in get_try_markets()
    }

    tickers = get_all_tickers()

    result = []

    for ticker in tickers:

        symbol = str(
            ticker.get(
                "pair",
                ticker.get(
                    "pairSymbol",
                    ""
                )
            )
        ).upper()

        if symbol not in markets:
            continue

        if not symbol.endswith("TRY"):
            continue

        try:

            price = float(
                ticker.get(
                    "last",
                    0
                )
            )

            volume = float(
                ticker.get(
                    "volume",
                    0
                )
            )

            change = float(
                ticker.get(
                    "dailyPercent",
                    0
                )
            )

        except Exception:

            continue

        if price <= 0:
            continue

        result.append(
            {
                "symbol": symbol,
                "price": price,
                "volume": volume,
                "change_24h": change,
            }
        )

    return result


# ============================================================
# HACİM FİLTRESİ
# ============================================================

def get_liquid_try_universe():

    tickers = get_try_tickers()

    candidates = []

    for row in tickers:

        # Yaklaşık TRY işlem hacmi
        turnover = (
            row["volume"]
            * row["price"]
        )

        if turnover < MIN_VOLUME_TRY:
            continue

        row["turnover_try"] = turnover

        candidates.append(
            row
        )

    candidates.sort(
        key=lambda x:
        x["turnover_try"],
        reverse=True
    )

    return candidates[:MAX_COINS]


# ============================================================
# OHLC
# ============================================================

def get_ohlc(
    symbol,
    interval="1d",
    limit=250,
):

    # BtcTurk API interval değerleri
    interval_map = {
        "15m": 15,
        "1h": 60,
        "4h": 240,
        "1d": 1440,
        "1w": 10080,
    }

    minutes = interval_map.get(
        interval,
        1440
    )

    data = api_get(
        "ohlc",
        params={
            "pair": symbol,
            "timeframe": minutes,
            "limit": limit,
        },
    )

    if not data:
        return pd.DataFrame()

    if isinstance(data, dict):

        data = data.get(
            "data",
            []
        )

    if not isinstance(data, list):

        return pd.DataFrame()

    rows = []

    for item in data:

        if not isinstance(item, dict):
            continue

        try:

            rows.append(
                {
                    "timestamp": item.get(
                        "time",
                        item.get(
                            "timestamp"
                        )
                    ),
                    "open": float(
                        item.get("open", 0)
                    ),
                    "high": float(
                        item.get("high", 0)
                    ),
                    "low": float(
                        item.get("low", 0)
                    ),
                    "close": float(
                        item.get("close", 0)
                    ),
                    "volume": float(
                        item.get("volume", 0)
                    ),
                }
            )

        except Exception:

            continue

    df = pd.DataFrame(rows)

    if df.empty:
        return df

    df = df.dropna()

    df = df[
        df["close"] > 0
    ]

    return df.reset_index(
        drop=True
    )


# ============================================================
# EMA
# ============================================================

def ema(series, period):

    return series.ewm(
        span=period,
        adjust=False
    ).mean()


# ============================================================
# RSI
# ============================================================

def calculate_rsi(
    series,
    period=14,
):

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

    rs = avg_gain / avg_loss.replace(
        0,
        np.nan
    )

    rsi = (
        100
        - (
            100
            / (1 + rs)
        )
    )

    return rsi.fillna(50)


# ============================================================
# ATR
# ============================================================

def calculate_atr(
    df,
    period=14,
):

    high = df["high"]
    low = df["low"]
    close = df["close"]

    previous_close = close.shift(1)

    tr = pd.concat(
        [
            high - low,
            (high - previous_close).abs(),
            (low - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)

    return tr.ewm(
        alpha=1 / period,
        adjust=False
    ).mean()


# ============================================================
# TEKNİK ANALİZ
# ============================================================

def analyze_dataframe(df):

    if df is None:
        return None

    if len(df) < 60:
        return None

    df = df.copy()

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

    df["ema100"] = ema(
        df["close"],
        100
    )

    df["ema200"] = ema(
        df["close"],
        200
    )

    df["rsi"] = calculate_rsi(
        df["close"]
    )

    df["atr"] = calculate_atr(
        df
    )

    df["atr_pct"] = (
        df["atr"]
        / df["close"]
        * 100
    )

    df["volume_ma20"] = (
        df["volume"]
        .rolling(20)
        .mean()
    )

    df["volume_ratio"] = (
        df["volume"]
        / df["volume_ma20"]
    )

    df["momentum_7"] = (
        df["close"]
        .pct_change(7)
        * 100
    )

    df["momentum_30"] = (
        df["close"]
        .pct_change(30)
        * 100
    )

    df["momentum_90"] = (
        df["close"]
        .pct_change(90)
        * 100
    )

    return df


# ============================================================
# TREND SKORU
# ============================================================

def trend_score(row):

    score = 0

    close = row["close"]

    if close > row["ema20"]:
        score += 20

    if close > row["ema50"]:
        score += 20

    if close > row["ema100"]:
        score += 20

    if close > row["ema200"]:
        score += 20

    if row["ema20"] > row["ema50"]:
        score += 10

    if row["ema50"] > row["ema100"]:
        score += 10

    return float(
        min(score, 100)
    )


# ============================================================
# MOMENTUM SKORU
# ============================================================

def momentum_score(row):

    values = [
        row.get(
            "momentum_7",
            0
        ),
        row.get(
            "momentum_30",
            0
        ),
        row.get(
            "momentum_90",
            0
        ),
    ]

    score = 50

    for value in values:

        if value > 0:
            score += 10

        if value > 5:
            score += 5

        if value < -5:
            score -= 10

    return float(
        max(
            0,
            min(
                100,
                score
            )
        )
    )


# ============================================================
# RSI SKORU
# ============================================================

def rsi_score(rsi):

    if 50 <= rsi <= 65:
        return 100

    if 45 <= rsi < 50:
        return 75

    if 65 < rsi <= 72:
        return 80

    if 40 <= rsi < 45:
        return 55

    if 72 < rsi <= 80:
        return 50

    if rsi > 80:
        return 30

    return 35


# ============================================================
# HACİM SKORU
# ============================================================

def volume_score(volume_ratio):

    if volume_ratio >= 2:
        return 100

    if volume_ratio >= 1.5:
        return 90

    if volume_ratio >= 1.2:
        return 80

    if volume_ratio >= 1:
        return 65

    if volume_ratio >= 0.7:
        return 50

    return 30


# ============================================================
# BTC REJİMİ
# ============================================================

@lru_cache(maxsize=1)
def get_btc_regime():

    df = get_ohlc(
        "BTCTRY",
        "1d",
        250
    )

    df = analyze_dataframe(
        df
    )

    if df is None or df.empty:

        return {
            "score": 50,
            "label": "⚪ BİLİNMİYOR",
        }

    row = df.iloc[-1]

    score = trend_score(
        row
    )

    if score >= 80:

        label = "🟢 GÜÇLÜ"

    elif score >= 65:

        label = "🟢 POZİTİF"

    elif score >= 45:

        label = "🟡 NÖTR"

    else:

        label = "🔴 ZAYIF"

    return {
        "score": score,
        "label": label,
    }


# ============================================================
# VADE SKORU
# ============================================================

def calculate_score(
    daily,
    short_df=None,
    medium_df=None,
    long_df=None,
    mode="short",
):

    row = daily.iloc[-1]

    trend = trend_score(
        row
    )

    momentum = momentum_score(
        row
    )

    rsi = rsi_score(
        row["rsi"]
    )

    volume = volume_score(
        row["volume_ratio"]
    )

    btc = get_btc_regime()

    btc_score = btc["score"]


    # --------------------------------------------------------
    # GÜNLÜK
    # --------------------------------------------------------

    if mode == "daily":

        score = (
            trend * 0.30
            + momentum * 0.25
            + rsi * 0.15
            + volume * 0.20
            + btc_score * 0.10
        )


    # --------------------------------------------------------
    # KISA
    # --------------------------------------------------------

    elif mode == "short":

        score = (
            trend * 0.30
            + momentum * 0.30
            + rsi * 0.15
            + volume * 0.15
            + btc_score * 0.10
        )


    # --------------------------------------------------------
    # ORTA
    # --------------------------------------------------------

    elif mode == "medium":

        score = (
            trend * 0.40
            + momentum * 0.25
            + rsi * 0.10
            + volume * 0.10
            + btc_score * 0.15
        )


    # --------------------------------------------------------
    # UZUN
    # --------------------------------------------------------

    else:

        score = (
            trend * 0.50
            + momentum * 0.20
            + rsi * 0.05
            + volume * 0.05
            + btc_score * 0.20
        )


    return {
        "score": float(
            max(
                0,
                min(
                    100,
                    score
                )
            )
        ),
        "trend": trend,
        "momentum": row["momentum_30"],
        "rsi": row["rsi"],
        "volume_ratio": row["volume_ratio"],
        "atr_pct": row["atr_pct"],
        "btc_score": btc_score,
        "btc_label": btc["label"],
    }


# ============================================================
# TEK COIN ANALİZİ
# ============================================================

def analyze_coin(
    market,
    mode="short",
):

    symbol = market["symbol"]

    # Günlük ana veri
    daily = get_ohlc(
        symbol,
        "1d",
        OHLC_LIMIT
    )

    daily = analyze_dataframe(
        daily
    )

    if daily is None or daily.empty:
        return None

    result = calculate_score(
        daily,
        mode=mode
    )

    ticker_data = None

    for ticker in get_try_tickers():

        if ticker["symbol"] == symbol:

            ticker_data = ticker
            break

    if ticker_data is None:
        return None

    timeframe_map = {
        "daily": "15m + 1H",
        "short": "1H + 4H",
        "medium": "4H + 1D",
        "long": "1D + 1W",
    }

    return {
        "symbol": symbol,
        "price": ticker_data["price"],
        "change_24h": ticker_data["change_24h"],
        "score": result["score"],
        "trend": result["trend"],
        "momentum": result["momentum"],
        "rsi": result["rsi"],
        "volume_ratio": result["volume_ratio"],
        "atr_pct": result["atr_pct"],
        "btc_score": result["btc_score"],
        "btc_label": result["btc_label"],
        "timeframe": timeframe_map[
            mode
        ],
    }


# ============================================================
# GENEL TARAMA
# ============================================================

def scan_candidates(
    mode,
    top_n=5,
):

    # Cache'i yenile
    get_all_tickers.cache_clear()
    get_try_markets.cache_clear()
    get_btc_regime.cache_clear()

    universe = (
        get_liquid_try_universe()
    )

    results = []

    for market in universe:

        try:

            result = analyze_coin(
                market,
                mode=mode
            )

            if result is not None:

                results.append(
                    result
                )

        except Exception:

            continue

    if not results:

        return pd.DataFrame()

    df = pd.DataFrame(
        results
    )

    df = df.sort_values(
        "score",
        ascending=False
    )

    df = df.head(
        top_n
    ).copy()

    df.insert(
        0,
        "rank",
        range(
            1,
            len(df) + 1
        )
    )

    return df.reset_index(
        drop=True
    )


# ============================================================
# SAYFALARIN ÇAĞIRDIĞI FONKSİYONLAR
# ============================================================

def get_daily_trade_candidates(
    top_n=5
):

    return scan_candidates(
        "daily",
        top_n
    )


def get_short_term_candidates(
    top_n=5
):

    return scan_candidates(
        "short",
        top_n
    )


def get_medium_term_candidates(
    top_n=5
):

    return scan_candidates(
        "medium",
        top_n
    )


def get_long_term_candidates(
    top_n=5
):

    return scan_candidates(
        "long",
        top_n
    )


# ============================================================
# GÜNCELLEME ZAMANI
# ============================================================

def get_update_time():

    return datetime.now().strftime(
        "%d.%m.%Y %H:%M:%S"
    )
# ============================================================
# GERİYE DÖNÜK UYUMLULUK
# ============================================================

def get_daily_candidates(top_n=5):
    """
    Eski sayfalar için uyumluluk fonksiyonu.
    Günlük Trade adaylarını döndürür.
    """
    return get_daily_trade_candidates(
        top_n=top_n
    )