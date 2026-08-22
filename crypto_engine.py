# ============================================================
# CRYPTO AI PRO
# crypto_engine.py
#
# TEK KRİPTO ANALİZ MOTORU
#
# VERİ KAYNAĞI:
#   Binance TR
#
# PARİTE:
#   TRY
#
# TIMEFRAME:
#   15m
#
# ANALİZ:
#   EMA 9 / 20 / 50
#   RSI
#   VWAP
#   Volume Ratio
#   Momentum
#   Support / Resistance
#   Risk / Reward
#
# ÇIKTI:
#   Trade Score
#   A / B / C
#   Trade Decision
#
# ============================================================

import requests
import pandas as pd
import numpy as np
from datetime import datetime


# ============================================================
# AYARLAR
# ============================================================

BINANCE_TR_BASE_URL = "https://www.binance.tr"

# Market data için
BINANCE_TR_API_URL = "https://api.binance.me"

INTERVAL = "15m"

KLINE_LIMIT = 200

# Minimum 24 saatlik TRY hacmi
MIN_VOLUME_TRY = 20_000_000

# Analiz edilecek maksimum coin
MAX_ANALYSIS_COINS = 80


# ============================================================
# EXCLUDED COINS
# ============================================================

EXCLUDED_COINS = {
    "USDT",
    "USDC",
    "FDUSD",
    "TUSD",
    "DAI",
    "EUR",
    "TRY",
}


# ============================================================
# SESSION
# ============================================================

SESSION = requests.Session()

SESSION.headers.update({
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
})


# ============================================================
# SAFE FLOAT
# ============================================================

def safe_float(value, default=0.0):

    try:

        value = float(value)

        if np.isnan(value) or np.isinf(value):
            return default

        return value

    except Exception:

        return default


# ============================================================
# SYMBOL NORMALIZE
# ============================================================

def normalize_symbol(symbol):

    if symbol is None:
        return ""

    symbol = str(symbol).upper().strip()

    symbol = symbol.replace("/", "")
    symbol = symbol.replace("_", "")
    symbol = symbol.replace("-", "")

    return symbol


# ============================================================
# BASE ASSET
# ============================================================

def get_base_asset(symbol):

    symbol = normalize_symbol(symbol)

    if symbol.endswith("TRY"):

        return symbol[:-3]

    return ""


# ============================================================
# BINANCE TR - MARKET TICKER
# ============================================================

def get_24h_ticker():

    """
    Binance TR market verilerini alır.

    TRY paritelerini döndürür.

    Öncelik:
        /api/v3/ticker/24hr

    Gerekirse:
        /api/v1/ticker/24hr
    """

    endpoints = [

        f"{BINANCE_TR_API_URL}/api/v3/ticker/24hr",

        f"{BINANCE_TR_API_URL}/api/v1/ticker/24hr",

        f"{BINANCE_TR_BASE_URL}/api/v3/ticker/24hr",

        f"{BINANCE_TR_BASE_URL}/api/v1/ticker/24hr",

    ]

    for url in endpoints:

        try:

            response = SESSION.get(
                url,
                timeout=15
            )

            # ------------------------------------------------
            # HTTP
            # ------------------------------------------------

            if response.status_code != 200:

                print(
                    f"Ticker HTTP {response.status_code}: "
                    f"{url}"
                )

                continue

            payload = response.json()

            # ------------------------------------------------
            # RESPONSE FORMAT
            # ------------------------------------------------

            if isinstance(payload, dict):

                code = payload.get("code")

                if code not in (None, 0, "0"):

                    print(
                        "Ticker API hatası:",
                        code,
                        payload.get("msg")
                    )

                    continue

                data = payload.get(
                    "data",
                    payload
                )

            else:

                data = payload

            # ------------------------------------------------
            # LIST
            # ------------------------------------------------

            if isinstance(data, dict):

                data = [data]

            if not isinstance(data, list):

                continue

            rows = []

            for item in data:

                if not isinstance(item, dict):
                    continue

                # --------------------------------------------
                # SYMBOL
                # --------------------------------------------

                raw_symbol = (
                    item.get("symbol")
                    or item.get("s")
                    or ""
                )

                symbol = normalize_symbol(
                    raw_symbol
                )

                if not symbol.endswith("TRY"):
                    continue

                base_asset = get_base_asset(
                    symbol
                )

                if not base_asset:
                    continue

                if base_asset in EXCLUDED_COINS:
                    continue

                # --------------------------------------------
                # PRICE
                # --------------------------------------------

                price = safe_float(
                    item.get(
                        "lastPrice",
                        item.get(
                            "last",
                            item.get("c", 0)
                        )
                    )
                )

                # --------------------------------------------
                # CHANGE
                # --------------------------------------------

                change = safe_float(
                    item.get(
                        "priceChangePercent",
                        item.get(
                            "priceChangePercentage",
                            item.get("P", 0)
                        )
                    )
                )

                # --------------------------------------------
                # VOLUME
                # --------------------------------------------

                volume_base = safe_float(
                    item.get(
                        "volume",
                        item.get("v", 0)
                    )
                )

                quote_volume = safe_float(
                    item.get(
                        "quoteVolume",
                        item.get("q", 0)
                    )
                )

                # --------------------------------------------
                # TRY HACİM
                # --------------------------------------------

                volume_try = quote_volume

                if volume_try <= 0:

                    volume_try = (
                        volume_base * price
                    )

                # --------------------------------------------
                # HIGH / LOW
                # --------------------------------------------

                high = safe_float(
                    item.get(
                        "highPrice",
                        item.get("h", 0)
                    )
                )

                low = safe_float(
                    item.get(
                        "lowPrice",
                        item.get("l", 0)
                    )
                )

                rows.append({

                    "symbol": symbol,

                    "base_asset": base_asset,

                    "price_try": price,

                    "change_24h": change,

                    "volume_try": volume_try,

                    "high_24h": high,

                    "low_24h": low,

                })

            if rows:

                df = pd.DataFrame(rows)

                df = (
                    df
                    .drop_duplicates(
                        subset=["symbol"]
                    )
                    .reset_index(drop=True)
                )

                print(
                    f"Binance TR ticker başarılı: "
                    f"{len(df)} TRY parite"
                )

                return df

        except Exception as e:

            print(
                f"Ticker endpoint hatası: "
                f"{url} -> {e}"
            )

            continue

    print(
        "Binance TR'den TRY piyasa verisi alınamadı."
    )

    return pd.DataFrame()


# ============================================================
# BINANCE TR - TRY EVRENİ
# ============================================================

def get_all_try_universe():

    """
    TRY evrenini doğrudan ticker verisinden oluşturur.

    Böylece /common/symbols endpointine
    bağımlılık ortadan kaldırılır.
    """

    ticker = get_24h_ticker()

    if ticker.empty:

        print(
            "Binance TR TRY evreni oluşturulamadı."
        )

        return pd.DataFrame()

    df = ticker.copy()

    df = df[
        df["symbol"]
        .astype(str)
        .str.endswith("TRY")
    ].copy()

    df = df[
        ~df["base_asset"]
        .isin(EXCLUDED_COINS)
    ].copy()

    df = (
        df
        .sort_values(
            "volume_try",
            ascending=False
        )
        .reset_index(drop=True)
    )

    print(
        f"Binance TR TRY evreni: "
        f"{len(df)} parite"
    )

    return df


# ============================================================
# TRADE UNIVERSE
# ============================================================

def get_trade_universe(
    min_volume=MIN_VOLUME_TRY
):

    df = get_all_try_universe()

    if df.empty:

        return pd.DataFrame()

    # --------------------------------------------------------
    # HACİM FİLTRESİ
    # --------------------------------------------------------

    df = df[
        pd.to_numeric(
            df["volume_try"],
            errors="coerce"
        )
        .fillna(0)
        >= min_volume
    ].copy()

    # --------------------------------------------------------
    # SIRALA
    # --------------------------------------------------------

    df = (
        df
        .sort_values(
            "volume_try",
            ascending=False
        )
        .reset_index(drop=True)
    )

    print(
        f"Likidite filtresi sonrası: "
        f"{len(df)} parite"
    )

    return df


# ============================================================
# KLINE
# ============================================================

def get_klines(
    symbol,
    interval=INTERVAL,
    limit=KLINE_LIMIT
):

    """
    Binance TR 15 dakika mum verisi.

    Birden fazla endpoint denenir.
    """

    symbol = normalize_symbol(
        symbol
    )

    if not symbol.endswith("TRY"):

        return pd.DataFrame()

    endpoints = [

        f"{BINANCE_TR_API_URL}/api/v3/klines",

        f"{BINANCE_TR_API_URL}/api/v1/klines",

        f"{BINANCE_TR_BASE_URL}/api/v3/klines",

        f"{BINANCE_TR_BASE_URL}/api/v1/klines",

    ]

    params = {

        "symbol": symbol,

        "interval": interval,

        "limit": limit,

    }

    for url in endpoints:

        try:

            response = SESSION.get(
                url,
                params=params,
                timeout=15
            )

            if response.status_code != 200:

                continue

            payload = response.json()

            # ------------------------------------------------
            # RESPONSE
            # ------------------------------------------------

            if isinstance(payload, dict):

                code = payload.get("code")

                if code not in (
                    None,
                    0,
                    "0"
                ):

                    continue

                data = payload.get(
                    "data",
                    []
                )

            else:

                data = payload

            if not isinstance(data, list):

                continue

            if not data:

                continue

            # ------------------------------------------------
            # DATAFRAME
            # ------------------------------------------------

            rows = []

            for item in data:

                if not isinstance(item, (list, tuple)):
                    continue

                if len(item) < 6:
                    continue

                rows.append(item)

            if not rows:

                continue

            # ------------------------------------------------
            # COLUMNS
            # ------------------------------------------------

            columns = [

                "open_time",
                "open",
                "high",
                "low",
                "close",
                "volume",
                "close_time",
                "quote_volume",
                "trades",
                "taker_buy_base",
                "taker_buy_quote",
                "ignore"

            ]

            # Binance farklı format döndürürse
            # ilk 6 alanı kullanmak yeterlidir.

            max_cols = min(
                len(rows[0]),
                len(columns)
            )

            rows = [
                list(row[:max_cols])
                for row in rows
            ]

            df = pd.DataFrame(
                rows,
                columns=columns[:max_cols]
            )

            # ------------------------------------------------
            # GEREKLİ KOLON KONTROL
            # ------------------------------------------------

            required = [

                "open_time",
                "open",
                "high",
                "low",
                "close",
                "volume",

            ]

            if not all(
                col in df.columns
                for col in required
            ):

                continue

            # ------------------------------------------------
            # NUMERIC
            # ------------------------------------------------

            numeric_cols = [

                "open",
                "high",
                "low",
                "close",
                "volume",
                "quote_volume",
                "trades",
                "taker_buy_base",
                "taker_buy_quote",

            ]

            for col in numeric_cols:

                if col in df.columns:

                    df[col] = pd.to_numeric(
                        df[col],
                        errors="coerce"
                    )

            # ------------------------------------------------
            # DATETIME
            # ------------------------------------------------

            df["open_time"] = pd.to_datetime(
                pd.to_numeric(
                    df["open_time"],
                    errors="coerce"
                ),
                unit="ms"
            )

            if "close_time" in df.columns:

                df["close_time"] = pd.to_datetime(
                    pd.to_numeric(
                        df["close_time"],
                        errors="coerce"
                    ),
                    unit="ms"
                )

            # ------------------------------------------------
            # TEMİZLE
            # ------------------------------------------------

            df = df.dropna(
                subset=[
                    "open",
                    "high",
                    "low",
                    "close",
                    "volume"
                ]
            )

            df = (
                df
                .sort_values("open_time")
                .drop_duplicates(
                    subset=["open_time"]
                )
                .reset_index(drop=True)
            )

            if len(df) < 10:

                continue

            return df

        except Exception as e:

            print(
                f"{symbol} kline endpoint hatası: "
                f"{e}"
            )

            continue

    print(
        f"{symbol} için 15m kline alınamadı."
    )

    return pd.DataFrame()


# ============================================================
# EMA
# ============================================================

def calculate_ema(
    df,
    period
):

    return (
        df["close"]
        .ewm(
            span=period,
            adjust=False
        )
        .mean()
    )


# ============================================================
# RSI
# ============================================================

def calculate_rsi(
    df,
    period=14
):

    delta = df["close"].diff()

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

    rsi = (
        100 -
        (
            100 /
            (1 + rs)
        )
    )

    return (
        rsi
        .replace(
            [np.inf, -np.inf],
            np.nan
        )
        .fillna(50)
    )


# ============================================================
# VWAP
# ============================================================

def calculate_vwap(df):

    typical_price = (
        df["high"] +
        df["low"] +
        df["close"]
    ) / 3

    cumulative_volume = (
        df["volume"]
        .cumsum()
    )

    cumulative_pv = (
        typical_price *
        df["volume"]
    ).cumsum()

    return (
        cumulative_pv /
        cumulative_volume.replace(
            0,
            np.nan
        )
    )


# ============================================================
# VOLUME RATIO
# ============================================================

def calculate_volume_ratio(
    df,
    period=20
):

    avg_volume = (
        df["volume"]
        .rolling(period)
        .mean()
    )

    return (
        df["volume"] /
        avg_volume.replace(
            0,
            np.nan
        )
    )


# ============================================================
# SUPPORT / RESISTANCE
# ============================================================

def calculate_support_resistance(
    df,
    lookback=50
):

    recent = df.tail(
        lookback
    )

    if recent.empty:

        return 0.0, 0.0

    support = safe_float(
        recent["low"].min()
    )

    resistance = safe_float(
        recent["high"].max()
    )

    return support, resistance


# ============================================================
# MOMENTUM
# ============================================================

def calculate_momentum(
    df,
    period=20
):

    if len(df) < period:

        return 0.0

    current = safe_float(
        df["close"].iloc[-1]
    )

    previous = safe_float(
        df["close"].iloc[-period]
    )

    if previous <= 0:

        return 0.0

    return (
        (
            current /
            previous
        ) - 1
    ) * 100


# ============================================================
# TREND SCORE
# ============================================================

def calculate_trend_score(
    price,
    ema9,
    ema20,
    ema50
):

    score = 0

    if price > ema9:
        score += 20

    if ema9 > ema20:
        score += 25

    if ema20 > ema50:
        score += 25

    if price > ema50:
        score += 30

    return min(
        score,
        100
    )


# ============================================================
# RSI SCORE
# ============================================================

def calculate_rsi_score(
    rsi
):

    rsi = safe_float(
        rsi,
        50
    )

    if 50 <= rsi <= 65:
        return 100

    if 45 <= rsi < 50:
        return 75

    if 65 < rsi <= 70:
        return 70

    if 40 <= rsi < 45:
        return 55

    if 70 < rsi <= 75:
        return 40

    if rsi > 75:
        return 15

    return 30


# ============================================================
# VOLUME SCORE
# ============================================================

def calculate_volume_score(
    volume_ratio
):

    volume_ratio = safe_float(
        volume_ratio
    )

    if volume_ratio >= 2.0:
        return 100

    if volume_ratio >= 1.5:
        return 90

    if volume_ratio >= 1.2:
        return 75

    if volume_ratio >= 1.0:
        return 60

    if volume_ratio >= 0.8:
        return 40

    return 20


# ============================================================
# VWAP SCORE
# ============================================================

def calculate_vwap_score(
    price,
    vwap
):

    price = safe_float(
        price
    )

    vwap = safe_float(
        vwap
    )

    if vwap <= 0:

        return 50

    if price > vwap * 1.02:

        return 90

    if price > vwap:

        return 80

    if price >= vwap * 0.98:

        return 50

    return 20


# ============================================================
# RISK / REWARD
# ============================================================

def calculate_rr(
    price,
    support,
    resistance
):

    price = safe_float(
        price
    )

    support = safe_float(
        support
    )

    resistance = safe_float(
        resistance
    )

    if price <= 0:
        return 0.0

    if support <= 0:
        return 0.0

    if resistance <= 0:
        return 0.0

    if price <= support:

        return 0.0

    risk = price - support

    reward = resistance - price

    if risk <= 0:
        return 0.0

    if reward <= 0:
        return 0.0

    return reward / risk


# ============================================================
# MOMENTUM SCORE
# ============================================================

def calculate_momentum_score(
    momentum
):

    momentum = safe_float(
        momentum
    )

    if momentum >= 10:
        return 100

    if momentum >= 5:
        return 90

    if momentum >= 2:
        return 75

    if momentum >= 0:
        return 60

    if momentum >= -3:
        return 40

    return 20


# ============================================================
# R/R SCORE
# ============================================================

def calculate_rr_score(
    rr
):

    rr = safe_float(
        rr
    )

    if rr >= 3:
        return 100

    if rr >= 2:
        return 90

    if rr >= 1.5:
        return 75

    if rr >= 1:
        return 55

    return 20


# ============================================================
# TRADE SCORE
# ============================================================

def calculate_trade_score(
    trend_score,
    rsi_score,
    volume_score,
    vwap_score,
    momentum,
    rr
):

    momentum_score = (
        calculate_momentum_score(
            momentum
        )
    )

    rr_score = (
        calculate_rr_score(
            rr
        )
    )

    score = (

        trend_score * 0.30

        + rsi_score * 0.15

        + volume_score * 0.15

        + vwap_score * 0.15

        + momentum_score * 0.10

        + rr_score * 0.15

    )

    return round(
        min(
            max(
                score,
                0
            ),
            100
        ),
        2
    )


# ============================================================
# CLASSIFICATION
# ============================================================

def classify_trade(
    score
):

    score = safe_float(
        score
    )

    if score >= 80:

        return "🟢 A"

    if score >= 65:

        return "🟡 B"

    if score >= 50:

        return "🟠 C"

    return "🔴 ZAYIF"


# ============================================================
# TRADE DECISION
# ============================================================

def trade_decision(
    score,
    trend_score,
    rsi,
    price,
    vwap,
    rr,
    volume_ratio
):

    score = safe_float(
        score
    )

    trend_score = safe_float(
        trend_score
    )

    rsi = safe_float(
        rsi
    )

    price = safe_float(
        price
    )

    vwap = safe_float(
        vwap
    )

    rr = safe_float(
        rr
    )

    volume_ratio = safe_float(
        volume_ratio
    )

    # ========================================================
    # GÜÇLÜ TRADE
    # ========================================================

    if (

        score >= 80

        and trend_score >= 70

        and 50 <= rsi <= 70

        and price > vwap

        and rr >= 1.5

        and volume_ratio >= 1.2

    ):

        return "🟢 GÜÇLÜ TRADE"

    # ========================================================
    # TRADE ADAYI
    # ========================================================

    if (

        score >= 65

        and trend_score >= 60

        and price > vwap

        and rr >= 1

    ):

        return "🟡 TRADE ADAYI"

    # ========================================================
    # İZLE
    # ========================================================

    if score >= 50:

        return "🟠 İZLE"

    return "🔴 UYGUN DEĞİL"


# ============================================================
# TEK COIN ANALİZ
# ============================================================

def analyze_coin(
    symbol,
    market_data=None
):

    """
    Tek TRY paritesini analiz eder.
    """

    symbol = normalize_symbol(
        symbol
    )

    if not symbol.endswith("TRY"):

        return None

    base_asset = get_base_asset(
        symbol
    )

    if base_asset in EXCLUDED_COINS:

        return None

    # ========================================================
    # MARKET DATA
    # ========================================================

    market = {}

    if market_data is not None:

        if isinstance(
            market_data,
            pd.DataFrame
        ):

            if "symbol" in market_data.columns:

                match = market_data[
                    market_data["symbol"]
                    .astype(str)
                    .map(normalize_symbol)
                    == symbol
                ]

                if not match.empty:

                    market = (
                        match
                        .iloc[0]
                        .to_dict()
                    )

        elif isinstance(
            market_data,
            dict
        ):

            market = market_data

    # ========================================================
    # VOLUME
    # ========================================================

    volume_try = safe_float(
        market.get(
            "volume_try",
            0
        )
    )

    if (

        volume_try > 0

        and volume_try < MIN_VOLUME_TRY

    ):

        return None

    # ========================================================
    # KLINE
    # ========================================================

    df = get_klines(
        symbol
    )

    if df.empty:

        return None

    if len(df) < 60:

        return None

    # ========================================================
    # INDICATORS
    # ========================================================

    df["ema9"] = calculate_ema(
        df,
        9
    )

    df["ema20"] = calculate_ema(
        df,
        20
    )

    df["ema50"] = calculate_ema(
        df,
        50
    )

    df["rsi"] = calculate_rsi(
        df
    )

    df["vwap"] = calculate_vwap(
        df
    )

    df["volume_ratio"] = (
        calculate_volume_ratio(
            df
        )
    )

    # ========================================================
    # CURRENT ROW
    # ========================================================

    row = df.iloc[-1]

    price = safe_float(
        row["close"]
    )

    ema9 = safe_float(
        row["ema9"]
    )

    ema20 = safe_float(
        row["ema20"]
    )

    ema50 = safe_float(
        row["ema50"]
    )

    rsi = safe_float(
        row["rsi"],
        50
    )

    vwap = safe_float(
        row["vwap"]
    )

    volume_ratio = safe_float(
        row["volume_ratio"],
        0
    )

    # ========================================================
    # MOMENTUM
    # ========================================================

    momentum = calculate_momentum(
        df
    )

    # ========================================================
    # SUPPORT / RESISTANCE
    # ========================================================

    support, resistance = (
        calculate_support_resistance(
            df,
            lookback=50
        )
    )

    # ========================================================
    # R/R
    # ========================================================

    rr = calculate_rr(
        price,
        support,
        resistance
    )

    # ========================================================
    # SCORES
    # ========================================================

    trend_score = (
        calculate_trend_score(
            price,
            ema9,
            ema20,
            ema50
        )
    )

    rsi_score = (
        calculate_rsi_score(
            rsi
        )
    )

    volume_score = (
        calculate_volume_score(
            volume_ratio
        )
    )

    vwap_score = (
        calculate_vwap_score(
            price,
            vwap
        )
    )

    trade_score = (
        calculate_trade_score(
            trend_score,
            rsi_score,
            volume_score,
            vwap_score,
            momentum,
            rr
        )
    )

    # ========================================================
    # CLASS
    # ========================================================

    classification = classify_trade(
        trade_score
    )

    # ========================================================
    # DECISION
    # ========================================================

    decision = trade_decision(
        trade_score,
        trend_score,
        rsi,
        price,
        vwap,
        rr,
        volume_ratio
    )

    # ========================================================
    # 15M CHANGE
    # ========================================================

    change_15m = 0.0

    if len(df) >= 2:

        previous = safe_float(
            df["close"].iloc[-2]
        )

        if previous > 0:

            change_15m = (
                (
                    price /
                    previous
                ) - 1
            ) * 100

    # ========================================================
    # RESULT
    # ========================================================

    return {

        "symbol": base_asset,

        "pair": symbol,

        "price": price,

        "change_15m": round(
            change_15m,
            2
        ),

        "change_24h": round(
            safe_float(
                market.get(
                    "change_24h",
                    0
                )
            ),
            2
        ),

        "volume_try": round(
            volume_try,
            2
        ),

        "momentum": round(
            momentum,
            2
        ),

        "ema9": round(
            ema9,
            8
        ),

        "ema20": round(
            ema20,
            8
        ),

        "ema50": round(
            ema50,
            8
        ),

        "rsi": round(
            rsi,
            2
        ),

        "vwap": round(
            vwap,
            8
        ),

        "volume_ratio": round(
            volume_ratio,
            2
        ),

        "support": round(
            support,
            8
        ),

        "resistance": round(
            resistance,
            8
        ),

        "rr": round(
            rr,
            2
        ),

        "trend_score": round(
            trend_score,
            2
        ),

        "rsi_score": round(
            rsi_score,
            2
        ),

        "volume_score": round(
            volume_score,
            2
        ),

        "vwap_score": round(
            vwap_score,
            2
        ),

        "trade_score": trade_score,

        "class": classification,

        "decision": decision,

        "analysis_time": datetime.now(),

    }


# ============================================================
# TÜM COINLERİ SIRALA
# ============================================================

def rank_coins(
    symbols=None,
    min_volume=MIN_VOLUME_TRY
):

    """
    Binance TR TRY evrenini tarar.
    Trade Score'a göre sıralar.
    """

    # ========================================================
    # MARKET
    # ========================================================

    market_df = get_trade_universe(
        min_volume=min_volume
    )

    if market_df.empty:

        print(
            "Trade universe boş."
        )

        return pd.DataFrame()

    # ========================================================
    # SYMBOL LIST
    # ========================================================

    if symbols is None:

        symbols = (
            market_df[
                "symbol"
            ]
            .dropna()
            .tolist()
        )

    else:

        symbols = [

            normalize_symbol(s)

            for s in symbols

            if normalize_symbol(s)

        ]

    # ========================================================
    # HACME GÖRE SINIRLA
    # ========================================================

    if len(symbols) > MAX_ANALYSIS_COINS:

        market_symbols = (
            market_df[
                "symbol"
            ]
            .tolist()
        )

        symbols = [
            s
            for s in market_symbols
            if s in symbols
        ][:MAX_ANALYSIS_COINS]

    # ========================================================
    # ANALİZ
    # ========================================================

    results = []

    total = len(symbols)

    print(
        "=========================================="
    )

    print(
        "CRYPTO AI PRO TARAMA"
    )

    print(
        f"Analiz edilecek parite: {total}"
    )

    print(
        "=========================================="
    )

    for i, symbol in enumerate(
        symbols,
        start=1
    ):

        print(
            f"[{i}/{total}] {symbol}"
        )

        try:

            result = analyze_coin(
                symbol,
                market_data=market_df
            )

            if result is not None:

                results.append(
                    result
                )

        except Exception as e:

            print(
                f"{symbol} analiz hatası: "
                f"{e}"
            )

            continue

    # ========================================================
    # SONUÇ
    # ========================================================

    if not results:

        print(
            "Hiçbir coin analiz edilemedi."
        )

        return pd.DataFrame()

    result_df = pd.DataFrame(
        results
    )

    # ========================================================
    # SORT
    # ========================================================

    result_df = (
        result_df
        .sort_values(
            [
                "trade_score",
                "volume_try"
            ],
            ascending=[
                False,
                False
            ]
        )
        .reset_index(
            drop=True
        )
    )

    print(
        "=========================================="
    )

    print(
        "CRYPTO AI TARAMA TAMAMLANDI"
    )

    print(
        f"{len(result_df)} coin analiz edildi"
    )

    print(
        "=========================================="
    )

    return result_df


# ============================================================
# TRADE ADAYLARI
# ============================================================

def get_trade_candidates(
    symbols=None
):

    df = rank_coins(
        symbols
    )

    if df.empty:

        return df

    candidates = df[
        df["trade_score"] >= 65
    ].copy()

    return (
        candidates
        .reset_index(drop=True)
    )


# ============================================================
# A SINIFI
# ============================================================

def get_a_trades(
    symbols=None
):

    df = rank_coins(
        symbols
    )

    if df.empty:

        return df

    result = df[
        (
            df["trade_score"] >= 80
        )
        &
        (
            df["decision"]
            == "🟢 GÜÇLÜ TRADE"
        )
    ].copy()

    return (
        result
        .reset_index(drop=True)
    )


# ============================================================
# TOP N
# ============================================================

def get_top_trades(
    symbols=None,
    n=10
):

    df = rank_coins(
        symbols
    )

    if df.empty:

        return df

    return (
        df
        .head(n)
        .reset_index(drop=True)
    )


# ============================================================
# STRONG TRADES
# ============================================================

def get_strong_trades(
    symbols=None
):

    df = rank_coins(
        symbols
    )

    if df.empty:

        return df

    result = df[
        df["decision"]
        == "🟢 GÜÇLÜ TRADE"
    ].copy()

    return (
        result
        .reset_index(drop=True)
    )


# ============================================================
# MARKET SUMMARY
# ============================================================

def get_market_summary():

    df = get_trade_universe()

    if df.empty:

        return {

            "total_pairs": 0,

            "liquid_pairs": 0,

            "total_volume_try": 0,

            "top_coin": None

        }

    total_volume = safe_float(
        df["volume_try"].sum()
    )

    top_coin = None

    if not df.empty:

        top_coin = (
            df.iloc[0]
            ["base_asset"]
        )

    return {

        "total_pairs": len(df),

        "liquid_pairs": len(df),

        "total_volume_try":
            total_volume,

        "top_coin":
            top_coin

    }


# ============================================================
# CONNECTION TEST
# ============================================================

def test_binance_tr():

    """
    Binance TR bağlantısını test eder.
    """

    print()
    print(
        "=========================================="
    )
    print(
        "BINANCE TR BAĞLANTI TESTİ"
    )
    print(
        "=========================================="
    )

    df = get_24h_ticker()

    if df.empty:

        print(
            "❌ Binance TR'den veri alınamadı."
        )

        return False

    print(
        f"✅ Toplam TRY parite: {len(df)}"
    )

    print()

    print(
        df[
            [
                "symbol",
                "price_try",
                "change_24h",
                "volume_try"
            ]
        ]
        .head(10)
        .to_string(
            index=False
        )
    )

    print()

    print(
        "✅ Binance TR bağlantısı çalışıyor."
    )

    return True


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    print()

    print(
        "=========================================="
    )

    print(
        "       CRYPTO AI PRO ENGINE TEST"
    )

    print(
        "=========================================="
    )

    print()

    # --------------------------------------------------------
    # 1. API TEST
    # --------------------------------------------------------

    if not test_binance_tr():

        print()
        print(
            "API testi başarısız."
        )

        raise SystemExit

    # --------------------------------------------------------
    # 2. TRADE UNIVERSE
    # --------------------------------------------------------

    market = get_trade_universe()

    print()

    print(
        f"TRY likit evreni: "
        f"{len(market)}"
    )

    # --------------------------------------------------------
    # 3. MARKET LIST
    # --------------------------------------------------------

    if not market.empty:

        print()

        print(
            "En yüksek hacimli 10 TRY paritesi:"
        )

        print()

        print(
            market[
                [
                    "symbol",
                    "price_try",
                    "change_24h",
                    "volume_try"
                ]
            ]
            .head(10)
            .to_string(
                index=False
            )
        )

    # --------------------------------------------------------
    # 4. TOP TRADES
    # --------------------------------------------------------

    print()

    top = get_top_trades(
        n=10
    )

    if top.empty:

        print(
            "Trade adayı bulunamadı."
        )

    else:

        print()

        print(
            "=========================================="
        )

        print(
            "TOP 10 CRYPTO TRADE"
        )

        print(
            "=========================================="
        )

        print()

        print(
            top[
                [
                    "symbol",
                    "price",
                    "change_24h",
                    "rsi",
                    "volume_ratio",
                    "rr",
                    "trend_score",
                    "trade_score",
                    "class",
                    "decision"
                ]
            ]
            .to_string(
                index=False
            )
        )