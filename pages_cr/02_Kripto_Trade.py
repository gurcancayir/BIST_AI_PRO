# ============================================================
# CRYPTO AI PRO
# 02_Kripto_Trade.py
#
# GELİŞMİŞ CRYPTO TRADE RADAR - ORTAK TRY EVRENİ SÜRÜMÜ
#
# YENİ SİSTEM
# ------------------------------------------------------------
# 1) 24S momentum
# 2) 15D trend
# 3) 1S trend
# 4) EMA 9 / 20 / 50
# 5) RSI
# 6) VWAP
# 7) Hacim oranı
# 8) Likidite
# 9) Destek / direnç
# 10) Geri çekilme
# 11) Kırılım
# 12) Kovalama
# 13) Risk / ödül
#
# KARARLAR
# ------------------------------------------------------------
# 🟢 AL
# 🟢 GERİ ÇEKİLMEDE AL
# 🔵 KIRILIM BEKLE
# 🟡 TEYİT BEKLE
# 🟠 İZLE
# 🔴 KOVALAMA
# 🔴 DÜŞÜŞ BICAĞI
# 🔴 LİKİDİTE YETERSİZ
#
# NOT:
# Emir göndermez.
# Sadece analiz ve trade planı üretir.
# ============================================================

import math
import requests
import pandas as pd
import numpy as np
import streamlit as st
import importlib
import crypto_engine


# ============================================================
# SAYFA AYARLARI
# ============================================================

st.set_page_config(
    page_title="Kripto Trade",
    page_icon="⚡",
    layout="wide",
)


# ============================================================
# AYARLAR
# ============================================================

TIMEOUT = 8

# Minimum 24S TRY hacmi
MIN_VOLUME_TRY = 50_000_000

# Ana trade filtresi
MIN_TRADE_SCORE = 68

# Güç filtresi
MIN_STRENGTH = 60

# Kovalama
CHASE_WARNING = 7.0
CHASE_DANGER = 12.0
CHASE_EXTREME = 18.0

# Minimum RR
MIN_RR = 2.0

# Tüm TRY coinleri evrene alınır.
# Likiditesi yeterli coinlerde 15D + 1S mum analizi yapılır.
# Böylece hacim sıralamasında ilk 60 dışında kalan coinler kaybolmaz.
ANALYZE_ALL_TRY_PAIRS = True

# Mum sayısı
CANDLE_LIMIT = 120

# Cache
CACHE_TTL = 60


# ============================================================
# API ENDPOINTLERİ
# ============================================================

TICKER_ENDPOINTS = [
    "https://api.binance.me/api/v3/ticker/24hr",
    "https://www.binance.tr/api/v3/ticker/24hr",
    "https://www.binance.tr/open/v1/market/ticker",
]

KLINE_BASES = [
    "https://api.binance.me/api/v3/klines",
    "https://www.binance.tr/api/v3/klines",
]


# ============================================================
# YARDIMCI FONKSİYONLAR
# ============================================================

def safe_float(value, default=0.0):

    try:

        if value is None:
            return default

        if isinstance(value, str):
            value = (
                value
                .replace(",", "")
                .replace("%", "")
                .strip()
            )

        result = float(value)

        if not np.isfinite(result):
            return default

        return result

    except Exception:

        return default


def clamp(value, low=0.0, high=100.0):

    try:
        return max(low, min(high, float(value)))
    except Exception:
        return low


def fmt_price(price):

    price = safe_float(price)

    if price >= 1000:
        return f"{price:,.2f}"

    if price >= 100:
        return f"{price:,.3f}"

    if price >= 1:
        return f"{price:,.4f}"

    if price >= 0.01:
        return f"{price:,.5f}"

    if price >= 0.0001:
        return f"{price:,.8f}"

    return f"{price:,.10f}"


def fmt_try(value):

    value = safe_float(value)

    if value >= 1_000_000_000:
        return f"₺{value / 1_000_000_000:.2f} Mr"

    if value >= 1_000_000:
        return f"₺{value / 1_000_000:.1f} Mn"

    if value >= 1_000:
        return f"₺{value / 1_000:.1f} B"

    return f"₺{value:,.0f}"


def pct(value):

    return f"{safe_float(value):+.2f}%"


# ============================================================
# TEKNİK FONKSİYONLAR
# ============================================================

def calculate_ema(series, period):

    return series.ewm(
        span=period,
        adjust=False
    ).mean()


def calculate_rsi(series, period=14):

    delta = series.diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(
        alpha=1 / period,
        adjust=False
    ).mean()

    avg_loss = loss.ewm(
        alpha=1 / period,
        adjust=False
    ).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)

    rsi = 100 - (100 / (1 + rs))

    return rsi.fillna(50)


def calculate_vwap(df):

    typical_price = (
        df["high"]
        + df["low"]
        + df["close"]
    ) / 3

    volume = df["volume"]

    cumulative_volume = volume.cumsum()

    cumulative_value = (
        typical_price * volume
    ).cumsum()

    return (
        cumulative_value
        / cumulative_volume.replace(0, np.nan)
    ).fillna(df["close"])


def prepare_candles(raw):

    if raw is None or len(raw) == 0:
        return pd.DataFrame()

    try:

        df = pd.DataFrame(
            raw,
            columns=[
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
                "ignore",
            ]
        )

        numeric_cols = [
            "open",
            "high",
            "low",
            "close",
            "volume",
            "quote_volume",
        ]

        for col in numeric_cols:

            df[col] = pd.to_numeric(
                df[col],
                errors="coerce"
            )

        df = df.dropna(
            subset=[
                "open",
                "high",
                "low",
                "close",
                "volume",
            ]
        ).copy()

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

        df["vwap"] = calculate_vwap(df)

        df["vol_ma20"] = (
            df["volume"]
            .rolling(20)
            .mean()
        )

        df["volume_ratio"] = (
            df["volume"]
            / df["vol_ma20"].replace(0, np.nan)
        )

        return df

    except Exception:

        return pd.DataFrame()


# ============================================================
# ORTAK TRY EVRENİ
# ============================================================

def _normalize_engine_universe(raw_data):
    """
    crypto_engine.get_all_try_universe() çıktısını Trade motorunun
    kullandığı standart kolonlara dönüştürür.

    Standart kolonlar:
        symbol, coin, price, change, volume, high, low
    """

    if raw_data is None:
        return pd.DataFrame()

    if isinstance(raw_data, pd.DataFrame):
        df = raw_data.copy()

    elif isinstance(raw_data, list):
        if not raw_data:
            return pd.DataFrame()

        if isinstance(raw_data[0], dict):
            df = pd.DataFrame(raw_data)
        else:
            df = pd.DataFrame({"symbol": raw_data})

    else:
        return pd.DataFrame()

    if df.empty:
        return pd.DataFrame()

    # Kolon isimlerini küçük harfe normalize etmeden,
    # olası isimleri tek tek destekliyoruz.
    symbol_candidates = ["symbol", "pair", "name", "code"]

    if "symbol" not in df.columns:
        found = next(
            (c for c in symbol_candidates if c in df.columns),
            None
        )
        if found is None:
            return pd.DataFrame()
        df["symbol"] = df[found]

    df["symbol"] = (
        df["symbol"]
        .astype(str)
        .str.upper()
        .str.strip()
        .str.replace("/", "", regex=False)
        .str.replace("_", "", regex=False)
        .str.replace("-", "", regex=False)
    )

    df = df[
        df["symbol"].str.endswith("TRY", na=False)
    ].copy()

    if df.empty:
        return pd.DataFrame()

    def first_existing(*names):
        for name in names:
            if name in df.columns:
                return df[name]
        return pd.Series(
            [np.nan] * len(df),
            index=df.index
        )

    if "base_asset" in df.columns:
        coin_series = df["base_asset"]
    elif "coin" in df.columns:
        coin_series = df["coin"]
    else:
        coin_series = (
            df["symbol"]
            .str.replace("TRY", "", regex=False)
        )

    out = pd.DataFrame(index=df.index)

    out["symbol"] = df["symbol"]

    out["coin"] = (
        coin_series
        .astype(str)
        .str.upper()
        .str.strip()
    )

    out["price"] = pd.to_numeric(
        first_existing(
            "price_try",
            "price",
            "lastPrice",
            "last_price",
            "close",
        ),
        errors="coerce",
    )

    out["change"] = pd.to_numeric(
        first_existing(
            "change_24h",
            "change",
            "priceChangePercent",
            "changePercent",
        ),
        errors="coerce",
    )

    out["volume"] = pd.to_numeric(
        first_existing(
            "volume_try",
            "quoteVolume",
            "quote_volume",
            "volume",
        ),
        errors="coerce",
    )

    out["high"] = pd.to_numeric(
        first_existing(
            "high_24h",
            "high",
            "highPrice",
        ),
        errors="coerce",
    )

    out["low"] = pd.to_numeric(
        first_existing(
            "low_24h",
            "low",
            "lowPrice",
        ),
        errors="coerce",
    )

    # Aynı sembol birden fazla geldiyse en güncel/ilk geçerli kaydı koru.
    out = out.drop_duplicates(
        subset=["symbol"],
        keep="first",
    )

    # Coin adı boş/NaN görünmesin.
    out["coin"] = out["coin"].replace(
        {
            "": np.nan,
            "NAN": np.nan,
            "NONE": np.nan,
        }
    )

    missing_coin = out["coin"].isna()

    out.loc[missing_coin, "coin"] = (
        out.loc[missing_coin, "symbol"]
        .str.replace("TRY", "", regex=False)
    )

    return out.reset_index(drop=True)


@st.cache_data(
    ttl=CACHE_TTL,
    show_spinner=False
)
def get_engine_market_data():
    """
    Kripto Piyasa sayfasıyla aynı ana kaynağı kullanır:
    crypto_engine.get_all_try_universe()
    """

    try:
        engine = importlib.reload(crypto_engine)
        raw_data = engine.get_all_try_universe()
        return _normalize_engine_universe(raw_data)

    except Exception:
        return pd.DataFrame()


# ============================================================
# YEDEK MARKET DATA
# ============================================================

@st.cache_data(
    ttl=CACHE_TTL,
    show_spinner=False
)
def get_market_data():

    errors = []

    for url in TICKER_ENDPOINTS:

        try:

            response = requests.get(
                url,
                timeout=TIMEOUT,
                headers={
                    "User-Agent": "Mozilla/5.0"
                },
            )

            if response.status_code != 200:

                errors.append(
                    f"{url} -> HTTP {response.status_code}"
                )

                continue

            data = response.json()

            # ------------------------------------------------
            # STANDARD
            # ------------------------------------------------

            if isinstance(data, list):

                rows = []

                for item in data:

                    symbol = str(
                        item.get(
                            "symbol",
                            ""
                        )
                    ).upper()

                    if not symbol.endswith("TRY"):
                        continue

                    price = safe_float(
                        item.get(
                            "lastPrice"
                        )
                    )

                    if price <= 0:
                        continue

                    rows.append(
                        {
                            "symbol": symbol,

                            "coin": symbol.replace(
                                "TRY",
                                ""
                            ),

                            "price": price,

                            "change": safe_float(
                                item.get(
                                    "priceChangePercent"
                                )
                            ),

                            "high": safe_float(
                                item.get(
                                    "highPrice"
                                )
                            ),

                            "low": safe_float(
                                item.get(
                                    "lowPrice"
                                )
                            ),

                            "volume": safe_float(
                                item.get(
                                    "quoteVolume"
                                )
                            ),
                        }
                    )

                if rows:

                    return pd.DataFrame(rows)

            # ------------------------------------------------
            # BINANCE TR WRAPPER
            # ------------------------------------------------

            payload = data.get(
                "data",
                data
            )

            if isinstance(payload, dict):

                payload = (
                    payload.get("list")
                    or payload.get("data")
                    or []
                )

            if isinstance(payload, list):

                rows = []

                for item in payload:

                    symbol = str(
                        item.get(
                            "symbol",
                            ""
                        )
                    ).upper()

                    if not symbol.endswith("TRY"):
                        continue

                    price = safe_float(
                        item.get("lastPrice")
                        or item.get("price")
                        or item.get("close")
                    )

                    if price <= 0:
                        continue

                    rows.append(
                        {
                            "symbol": symbol,

                            "coin": symbol.replace(
                                "TRY",
                                ""
                            ),

                            "price": price,

                            "change": safe_float(
                                item.get(
                                    "priceChangePercent"
                                )
                                or item.get(
                                    "changePercent"
                                )
                            ),

                            "high": safe_float(
                                item.get(
                                    "highPrice"
                                )
                                or item.get("high")
                            ),

                            "low": safe_float(
                                item.get(
                                    "lowPrice"
                                )
                                or item.get("low")
                            ),

                            "volume": safe_float(
                                item.get(
                                    "quoteVolume"
                                )
                                or item.get("volume")
                            ),
                        }
                    )

                if rows:

                    return pd.DataFrame(rows)

        except Exception as exc:

            errors.append(
                f"{url} -> {str(exc)}"
            )

    return pd.DataFrame()


# ============================================================
# FALLBACK MARKET DATA
# ============================================================

def fallback_market_data():

    data = [

        [
            "XRPTRY",
            "XRP",
            70.22,
            -9.16,
            2_260_000_000,
            78.20,
            68.80
        ],

        [
            "BTCTRY",
            "BTC",
            3_673_670,
            -1.77,
            631_400_000,
            3_740_000,
            3_610_000
        ],

        [
            "PEPETRY",
            "PEPE",
            0.00019175,
            -9.79,
            863_600_000,
            0.000205,
            0.000185
        ],

        [
            "ETHTRY",
            "ETH",
            114_987,
            -4.13,
            747_000_000,
            119_000,
            113_000
        ],

        [
            "SOLTRY",
            "SOL",
            4456.80,
            -5.80,
            318_600_000,
            4700,
            4300
        ],

        [
            "TRXTRY",
            "TRX",
            16.389,
            -0.83,
            97_800_000,
            16.70,
            16.10
        ],

        [
            "BNBTRY",
            "BNB",
            32845,
            -3.80,
            137_300_000,
            34000,
            32000
        ],

        [
            "AVAXTRY",
            "AVAX",
            353.60,
            -9.12,
            254_400_000,
            390,
            345
        ],

        [
            "COTITRY",
            "COTI",
            0.5831,
            5.62,
            444_600_000,
            0.61,
            0.54
        ],

        [
            "ENATRY",
            "ENA",
            7.175,
            -6.16,
            921_700_000,
            7.70,
            7.00
        ],
    ]

    return pd.DataFrame(
        data,
        columns=[
            "symbol",
            "coin",
            "price",
            "change",
            "volume",
            "high",
            "low",
        ]
    )


# ============================================================
# KLINE
# ============================================================

@st.cache_data(
    ttl=120,
    show_spinner=False
)
def get_klines(symbol, interval):

    for base in KLINE_BASES:

        try:

            response = requests.get(
                base,
                params={
                    "symbol": symbol,
                    "interval": interval,
                    "limit": CANDLE_LIMIT,
                },
                timeout=TIMEOUT,
                headers={
                    "User-Agent": "Mozilla/5.0"
                },
            )

            if response.status_code != 200:
                continue

            data = response.json()

            if isinstance(data, list):

                df = prepare_candles(data)

                if not df.empty:
                    return df

        except Exception:

            continue

    return pd.DataFrame()


# ============================================================
# TEKNİK PUANLAMA
# ============================================================

def calculate_trend_score(df):

    if df.empty or len(df) < 55:

        return {
            "trend_score": 50,
            "trend_state": "VERİ YETERSİZ",
            "ema9": 0,
            "ema20": 0,
            "ema50": 0,
            "rsi": 50,
            "vwap": 0,
            "volume_ratio": 1,
        }

    last = df.iloc[-1]

    price = safe_float(
        last["close"]
    )

    ema9 = safe_float(
        last["ema9"]
    )

    ema20 = safe_float(
        last["ema20"]
    )

    ema50 = safe_float(
        last["ema50"]
    )

    rsi = safe_float(
        last["rsi"],
        50
    )

    vwap = safe_float(
        last["vwap"]
    )

    volume_ratio = safe_float(
        last["volume_ratio"],
        1
    )

    score = 0

    # EMA sıralaması
    if price > ema9:
        score += 15

    if ema9 > ema20:
        score += 15

    if ema20 > ema50:
        score += 15

    if price > ema20:
        score += 10

    if price > ema50:
        score += 10

    # VWAP
    if price > vwap:
        score += 10

    # RSI
    if 52 <= rsi <= 68:
        score += 15

    elif 45 <= rsi < 52:
        score += 8

    elif 68 < rsi <= 75:
        score += 7

    elif rsi > 75:
        score += 2

    # Hacim
    if volume_ratio >= 1.5:
        score += 10

    elif volume_ratio >= 1.1:
        score += 6

    elif volume_ratio >= 0.8:
        score += 3

    score = clamp(score)

    if score >= 80:

        state = "GÜÇLÜ YÜKSELİŞ"

    elif score >= 68:

        state = "POZİTİF"

    elif score >= 55:

        state = "NÖTR"

    elif score >= 40:

        state = "ZAYIF"

    else:

        state = "NEGATİF"

    return {
        "trend_score": round(score, 1),
        "trend_state": state,
        "ema9": ema9,
        "ema20": ema20,
        "ema50": ema50,
        "rsi": rsi,
        "vwap": vwap,
        "volume_ratio": volume_ratio,
    }


# ============================================================
# DESTEK / DİRENÇ
# ============================================================

def calculate_support_resistance(df, price):

    if df.empty:

        return {
            "support": price * 0.97,
            "resistance": price * 1.03,
            "support2": price * 0.94,
            "resistance2": price * 1.06,
        }

    recent = df.tail(60)

    support = safe_float(
        recent["low"].min(),
        price * 0.97
    )

    resistance = safe_float(
        recent["high"].max(),
        price * 1.03
    )

    support2 = safe_float(
        recent["low"].tail(30).min(),
        support
    )

    resistance2 = safe_float(
        recent["high"].tail(30).max(),
        resistance
    )

    return {
        "support": support,
        "resistance": resistance,
        "support2": support2,
        "resistance2": resistance2,
    }


# ============================================================
# ANA COIN ANALİZİ
# ============================================================

def analyze_coin(
    row,
    df15=None,
    df1h=None
):

    price = safe_float(
        row["price"]
    )

    change = safe_float(
        row["change"]
    )

    high = safe_float(
        row["high"]
    )

    low = safe_float(
        row["low"]
    )

    volume = safe_float(
        row["volume"]
    )

    # ========================================================
    # 1. 24S RANGE
    # ========================================================

    if high > low > 0:

        range_pct = (
            (high - low)
            / low
        ) * 100

        position = (
            (price - low)
            / (high - low)
        ) * 100

    else:

        range_pct = 0
        position = 50

    position = clamp(position)

    # ========================================================
    # 2. MOMENTUM
    # ========================================================

    if change <= -15:

        momentum = 10

    elif change <= -10:

        momentum = 20

    elif change < -5:

        momentum = 35

    elif change < 0:

        momentum = 45

    elif change < 3:

        momentum = 55

    elif change < 7:

        momentum = 70

    elif change < 12:

        momentum = 82

    elif change < 18:

        momentum = 72

    else:

        momentum = 55

    # ========================================================
    # 3. RANGE LOCATION
    # ========================================================

    if position < 15:

        location_score = 70

    elif position < 30:

        location_score = 82

    elif position < 50:

        location_score = 90

    elif position < 65:

        location_score = 84

    elif position < 80:

        location_score = 68

    elif position < 90:

        location_score = 48

    else:

        location_score = 28

    # ========================================================
    # 4. LIKİDİTE
    # ========================================================

    if volume >= 2_000_000_000:

        liquidity_score = 100

    elif volume >= 1_000_000_000:

        liquidity_score = 94

    elif volume >= 500_000_000:

        liquidity_score = 86

    elif volume >= 250_000_000:

        liquidity_score = 78

    elif volume >= 100_000_000:

        liquidity_score = 70

    elif volume >= 50_000_000:

        liquidity_score = 58

    else:

        liquidity_score = 35

    # ========================================================
    # 5. KOVALAMA
    # ========================================================

    chase_score = 0

    if change >= 5:
        chase_score += 20

    if change >= 10:
        chase_score += 20

    if change >= 15:
        chase_score += 20

    if change >= 20:
        chase_score += 15

    if position >= 80:
        chase_score += 10

    if position >= 90:
        chase_score += 10

    if position >= 97:
        chase_score += 5

    chase_score = clamp(
        chase_score
    )

    # ========================================================
    # 6. VOLATİLİTE
    # ========================================================

    volatility_score = clamp(
        100 - min(
            range_pct * 3.0,
            70
        )
    )

    # ========================================================
    # 7. 15 DAKİKA TREND
    # ========================================================

    trend15 = calculate_trend_score(
        df15
    )

    # ========================================================
    # 8. 1 SAAT TREND
    # ========================================================

    trend1h = calculate_trend_score(
        df1h
    )

    trend15_score = trend15[
        "trend_score"
    ]

    trend1h_score = trend1h[
        "trend_score"
    ]

    # ========================================================
    # 9. TREND UYUMU
    # ========================================================

    trend_alignment = (
        trend15_score * 0.45
        + trend1h_score * 0.55
    )

    # ========================================================
    # 10. RSI
    # ========================================================

    rsi = trend15["rsi"]

    if 52 <= rsi <= 68:

        rsi_score = 90

    elif 45 <= rsi < 52:

        rsi_score = 65

    elif 68 < rsi <= 75:

        rsi_score = 72

    elif rsi > 75:

        rsi_score = 40

    elif 35 <= rsi < 45:

        rsi_score = 45

    else:

        rsi_score = 25

    # ========================================================
    # 11. VWAP
    # ========================================================

    vwap = trend15["vwap"]

    if vwap > 0:

        if price > vwap * 1.02:

            vwap_score = 72

        elif price > vwap:

            vwap_score = 90

        elif price > vwap * 0.98:

            vwap_score = 60

        else:

            vwap_score = 35

    else:

        vwap_score = 50

    # ========================================================
    # 12. HACİM
    # ========================================================

    volume_ratio = trend15[
        "volume_ratio"
    ]

    if volume_ratio >= 2:

        volume_score = 100

    elif volume_ratio >= 1.5:

        volume_score = 90

    elif volume_ratio >= 1.2:

        volume_score = 78

    elif volume_ratio >= 1:

        volume_score = 65

    elif volume_ratio >= 0.7:

        volume_score = 50

    else:

        volume_score = 35

    # ========================================================
    # 13. GÜÇ SKORU
    # ========================================================

    strength = (

        momentum * 0.15

        + liquidity_score * 0.10

        + location_score * 0.10

        + volatility_score * 0.05

        + trend_alignment * 0.35

        + rsi_score * 0.10

        + vwap_score * 0.05

        + volume_score * 0.10

    )

    # Sert düşüş cezası
    if change <= -10:

        strength -= 8

    if change <= -15:

        strength -= 8

    # Çok düşük RSI cezası
    if rsi < 35:

        strength -= 8

    strength = clamp(
        strength
    )

    # ========================================================
    # 14. DESTEK / DİRENÇ
    # ========================================================

    sr = calculate_support_resistance(
        df15,
        price
    )

    support = sr["support"]
    resistance = sr["resistance"]

    support2 = sr["support2"]
    resistance2 = sr["resistance2"]

    # ========================================================
    # 15. DİRENCE UZAKLIK
    # ========================================================

    if resistance > price:

        resistance_distance = (
            (resistance - price)
            / price
        ) * 100

    else:

        resistance_distance = 0

    # ========================================================
    # 16. KIRILIM PUANI
    # ========================================================

    breakout_score = 0

    if resistance > 0:

        if price >= resistance * 0.995:

            breakout_score += 40

        elif price >= resistance * 0.98:

            breakout_score += 25

        elif price >= resistance * 0.95:

            breakout_score += 15

    if trend15_score >= 75:

        breakout_score += 20

    if trend1h_score >= 70:

        breakout_score += 20

    if volume_ratio >= 1.5:

        breakout_score += 20

    breakout_score = clamp(
        breakout_score
    )

    # ========================================================
    # 17. GERİ ÇEKİLME
    # ========================================================

    if high > low:

        fib382 = (
            high
            - (high - low) * 0.382
        )

        fib500 = (
            high
            - (high - low) * 0.500
        )

        fib618 = (
            high
            - (high - low) * 0.618
        )

    else:

        fib382 = price * 0.985
        fib500 = price * 0.96
        fib618 = price * 0.93

    # ========================================================
    # 18. İDEAL GİRİŞ
    # ========================================================

    # Trend pozitifse EMA20 / fib bölgesi
    ema20 = trend15["ema20"]

    candidates = [
        fib382,
        fib500,
        ema20,
        support,
    ]

    valid_candidates = [
        x for x in candidates
        if x > 0 and x < price
    ]

    if valid_candidates:

        entry_low = min(
            valid_candidates
        )

        entry_high = max(
            valid_candidates
        )

        # Çok geniş bölgeyi daralt
        if entry_high > price * 0.98:

            entry_high = price * 0.98

    else:

        entry_low = price * 0.97
        entry_high = price * 0.985

    # Çok uzak giriş bölgesi engeli
    entry_low = max(
        entry_low,
        price * 0.85
    )

    entry_high = min(
        entry_high,
        price * 0.99
    )

    if entry_low >= entry_high:

        entry_low = price * 0.97
        entry_high = price * 0.985

    # ========================================================
    # 19. STOP
    # ========================================================

    stop_candidates = [
        support2 * 0.985,
        fib618 * 0.985,
        price * 0.93,
    ]

    stop_candidates = [
        x for x in stop_candidates
        if x > 0 and x < price
    ]

    if stop_candidates:

        stop = max(
            stop_candidates
        )

    else:

        stop = price * 0.93

    # Stop maksimum %12
    stop = max(
        stop,
        price * 0.88
    )

    # ========================================================
    # 20. RİSK
    # ========================================================

    risk = max(
        price - stop,
        price * 0.005
    )

    # ========================================================
    # 21. HEDEFLER
    # ========================================================

    target1 = price + risk * 2
    target2 = price + risk * 3
    target3 = price + risk * 4

    # Direnç hedeflerden daha anlamlıysa
    if resistance > price:

        target1 = max(
            target1,
            resistance
        )

        target2 = max(
            target2,
            resistance * 1.03
        )

        target3 = max(
            target3,
            resistance * 1.07
        )

    rr = (
        target2 - price
    ) / risk

    # ========================================================
    # 22. R/R SKORU
    # ========================================================

    if rr >= 3:

        rr_score = 100

    elif rr >= 2.5:

        rr_score = 90

    elif rr >= 2:

        rr_score = 80

    elif rr >= 1.5:

        rr_score = 60

    else:

        rr_score = 35

    # ========================================================
    # 23. GİRİŞ SKORU
    # ========================================================

    entry_score = (

        strength * 0.30

        + trend_alignment * 0.25

        + location_score * 0.10

        + liquidity_score * 0.05

        + (100 - chase_score) * 0.10

        + rr_score * 0.10

        + volume_score * 0.05

        + vwap_score * 0.05

    )

    entry_score = clamp(
        entry_score
    )

    # ========================================================
    # 24. DÜŞÜŞ BICAĞI
    # ========================================================

    falling_knife = (

        change <= -8
        and trend15_score < 50
        and trend1h_score < 55
    )

    # ========================================================
    # 25. KARAR MOTORU
    # ========================================================

    if volume < MIN_VOLUME_TRY:

        decision = (
            "🔴 LİKİDİTE YETERSİZ"
        )

    elif falling_knife:

        decision = (
            "🔴 DÜŞÜŞ BICAĞI"
        )

    elif (
        change >= CHASE_EXTREME
        and chase_score >= 75
    ):

        decision = (
            "🔴 KOVALAMA"
        )

    elif (
        chase_score >= 75
        and trend_alignment >= 70
    ):

        decision = (
            "🟡 GERİ ÇEKİLME BEKLE"
        )

    elif (
        breakout_score >= 75
        and trend_alignment >= 72
        and volume_ratio >= 1.3
    ):

        decision = (
            "🔵 KIRILIM BEKLE"
        )

    elif (
        entry_score >= 78
        and strength >= 72
        and trend_alignment >= 70
        and rr >= MIN_RR
        and chase_score < 60
    ):

        decision = (
            "🟢 AL"
        )

    elif (
        entry_score >= 68
        and strength >= 62
        and trend_alignment >= 65
        and rr >= MIN_RR
        and chase_score < 70
    ):

        decision = (
            "🟢 GERİ ÇEKİLMEDE AL"
        )

    elif (
        strength >= 68
        and trend_alignment >= 60
    ):

        decision = (
            "🟡 TEYİT BEKLE"
        )

    else:

        decision = (
            "🟠 İZLE"
        )

    # ========================================================
    # 26. SINIF
    # ========================================================

    if strength >= 80:

        grade = "🟢 A SINIFI"

    elif strength >= 70:

        grade = "🟡 B SINIFI"

    elif strength >= 60:

        grade = "🟠 C SINIFI"

    else:

        grade = "🔴 ZAYIF"

    # ========================================================
    # 27. MESAJ
    # ========================================================

    if decision == "🟢 AL":

        message = (
            "Trend, momentum, hacim ve risk/getiri "
            "aynı yönde. Mevcut fiyat trade için uygun."
        )

    elif decision == "🟢 GERİ ÇEKİLMEDE AL":

        message = (
            "Trend pozitif. Mevcut seviyede kovalamak "
            "yerine destek/EMA bölgesine geri çekilme "
            "daha iyi risk/getiri sağlayabilir."
        )

    elif decision == "🔵 KIRILIM BEKLE":

        message = (
            "Coin direnç bölgesine yaklaşıyor. "
            "Hacimli kırılım teyidi gelmeden pozisyon "
            "açmak yerine kırılım beklenmeli."
        )

    elif decision == "🟡 GERİ ÇEKİLME BEKLE":

        message = (
            "Momentum güçlü ancak fiyat fazla yükselmiş. "
            "Mevcut seviyeden kovalamak yerine geri çekilme "
            "beklenmeli."
        )

    elif decision == "🔴 KOVALAMA":

        message = (
            "Fiyat kısa sürede aşırı yükselmiş. "
            "Risk/getiri bozulduğu için mevcut seviyeden "
            "pozisyon açılması uygun değil."
        )

    elif decision == "🔴 DÜŞÜŞ BICAĞI":

        message = (
            "Fiyat sert düşüyor ve kısa/orta vadeli trend "
            "henüz toparlanmış değil. Sırf ucuzladı diye "
            "pozisyon açılmamalı."
        )

    elif decision == "🟡 TEYİT BEKLE":

        message = (
            "Bazı olumlu sinyaller var ancak trend teyidi "
            "henüz yeterince güçlü değil."
        )

    elif decision == "🔴 LİKİDİTE YETERSİZ":

        message = (
            "İşlem hacmi profesyonel trade için yeterli değil."
        )

    else:

        message = (
            "Şimdilik izleme bölgesinde."
        )

    # ========================================================
    # 28. RETURN
    # ========================================================

    return {

        "strength": round(
            strength,
            1
        ),

        "entry_score": round(
            entry_score,
            1
        ),

        "trend15": round(
            trend15_score,
            1
        ),

        "trend1h": round(
            trend1h_score,
            1
        ),

        "trend_alignment": round(
            trend_alignment,
            1
        ),

        "rsi": round(
            rsi,
            1
        ),

        "volume_ratio": round(
            volume_ratio,
            2
        ),

        "vwap": vwap,

        "chase_score": round(
            chase_score,
            1
        ),

        "breakout_score": round(
            breakout_score,
            1
        ),

        "position": round(
            position,
            1
        ),

        "range_pct": round(
            range_pct,
            2
        ),

        "momentum": round(
            momentum,
            1
        ),

        "liquidity_score": round(
            liquidity_score,
            1
        ),

        "ema9": trend15["ema9"],

        "ema20": trend15["ema20"],

        "ema50": trend15["ema50"],

        "support": support,

        "support2": support2,

        "resistance": resistance,

        "resistance2": resistance2,

        "resistance_distance": round(
            resistance_distance,
            2
        ),

        "grade": grade,

        "decision": decision,

        "entry_low": entry_low,

        "entry_high": entry_high,

        "stop": stop,

        "target1": target1,

        "target2": target2,

        "target3": target3,

        "rr": round(
            rr,
            2
        ),

        "message": message,
    }


# ============================================================
# MARKET DATA
# ============================================================

# 1) Öncelik: Kripto Piyasa ile AYNI crypto_engine TRY evreni
df = get_engine_market_data()

data_source = "crypto_engine"
using_fallback = False

# 2) crypto_engine veri vermezse mevcut canlı ticker yapısına dön
if df.empty:

    df = get_market_data()
    data_source = "ticker_api"

# 3) Canlı kaynakların ikisi de boşsa son çare fallback
if df.empty:

    df = fallback_market_data()
    data_source = "fallback"
    using_fallback = True


# ============================================================
# TEMİZLİK
# ============================================================

numeric_cols = [
    "price",
    "change",
    "volume",
    "high",
    "low",
]

for col in numeric_cols:

    if col not in df.columns:
        df[col] = np.nan

    df[col] = pd.to_numeric(
        df[col],
        errors="coerce"
    )

# Eksik 24s alanları güvenli varsayımlarla tamamla.
# Fiyatı olmayan coin analiz edilemez; diğer alanlar coin'i evrenden düşürmez.
df["change"] = df["change"].fillna(0.0)
df["volume"] = df["volume"].fillna(0.0)
df["high"] = df["high"].fillna(df["price"])
df["low"] = df["low"].fillna(df["price"])

df = df.dropna(
    subset=["price"]
)

df = df[
    df["price"] > 0
].copy()


# ============================================================
# LİKİDİTEYE GÖRE ÖN FİLTRE
# ============================================================

df = df.sort_values(
    "volume",
    ascending=False
).reset_index(
    drop=True
)


# ============================================================
# ANALİZ
# ============================================================

analysis_rows = []

progress = st.progress(
    0,
    text="Kripto piyasası analiz ediliyor..."
)

total = len(df)

for i, (_, row) in enumerate(
    df.iterrows()
):

    symbol = row["symbol"]
    volume = safe_float(row["volume"])

    # Tüm coinler analysis tablosuna girer.
    #
    # Likiditesi MIN_VOLUME_TRY altında olan coinde pahalı 15D/1S
    # mum çağrılarını yapmaya gerek yoktur; karar motoru zaten
    # "LİKİDİTE YETERSİZ" üretecektir.
    #
    # Böylece:
    # - coin evrenden KAYBOLMAZ,
    # - düşük hacimli coinler de detay listesinde görünür,
    # - API yükü gereksiz yere artmaz.
    if volume >= MIN_VOLUME_TRY:

        df15 = get_klines(
            symbol,
            "15m"
        )

        df1h = get_klines(
            symbol,
            "1h"
        )

    else:

        df15 = pd.DataFrame()
        df1h = pd.DataFrame()

    result = analyze_coin(
        row,
        df15,
        df1h
    )

    analysis_rows.append(
        {
            **row.to_dict(),
            **result,
        }
    )

    progress.progress(
        (i + 1) / max(total, 1),
        text=(
            f"{row['coin']} analiz ediliyor "
            f"({i + 1}/{total})"
        )
    )

progress.empty()


analysis = pd.DataFrame(
    analysis_rows
)

if analysis.empty:

    st.error(
        "TRY coin evreni alındı ancak analiz edilebilir geçerli fiyat verisi bulunamadı."
    )
    st.stop()


# ============================================================
# SIRALAMA
# ============================================================

analysis = analysis.sort_values(
    [
        "entry_score",
        "strength",
        "trend_alignment",
    ],
    ascending=False
).reset_index(
    drop=True
)


# ============================================================
# BAŞLIK
# ============================================================

st.title(
    "⚡ Kripto Trade Merkezi"
)

st.caption(
    "Trend + momentum + hacim + VWAP + RSI + "
    "destek/direnç + risk/getiri tabanlı profesyonel "
    "trade radar"
)


# ============================================================
# VERİ DURUMU
# ============================================================

if using_fallback:

    st.warning(
        "⚠️ Canlı API verisine ulaşılamadı. "
        "Son sağlanan piyasa tablosu ile sınırlı analiz yapılıyor."
    )

else:

    source_text = (
        "crypto_engine / ortak TRY evreni"
        if data_source == "crypto_engine"
        else "canlı ticker API"
    )

    liquid_count = int(
        (analysis["volume"] >= MIN_VOLUME_TRY).sum()
    )

    st.success(
        f"🟢 Veri kaynağı: {source_text} — "
        f"{len(analysis)} TRY coin evrene alındı, "
        f"{liquid_count} coin 15D + 1S mum analizine girdi."
    )


# ============================================================
# EVREN TEŞHİSİ
# ============================================================

with st.expander(
    "🧪 TRY Evreni / Analiz Teşhisi"
):

    liquid_count = int(
        (analysis["volume"] >= MIN_VOLUME_TRY).sum()
    )

    low_liquidity_count = int(
        (analysis["volume"] < MIN_VOLUME_TRY).sum()
    )

    c_ev1, c_ev2, c_ev3 = st.columns(3)

    c_ev1.metric(
        "TRY Evreni",
        len(analysis)
    )

    c_ev2.metric(
        "Mum Analizi",
        liquid_count
    )

    c_ev3.metric(
        "Düşük Likidite",
        low_liquidity_count
    )

    st.caption(
        "Tüm TRY pariteleri evrene alınır. "
        "₺50 Mn altı 24s hacme sahip coinler evrenden silinmez; "
        "yalnızca pahalı 15D/1S mum analizi atlanır ve karar motorunda "
        "LİKİDİTE YETERSİZ olarak işaretlenir."
    )

    universe_debug = analysis[
        [
            "symbol",
            "coin",
            "price",
            "volume",
            "decision",
        ]
    ].copy()

    st.dataframe(
        universe_debug,
        use_container_width=True,
        hide_index=True,
    )


# ============================================================
# ÖZET
# ============================================================

trade_count = len(
    analysis[
        analysis["decision"].isin(
            [
                "🟢 AL",
                "🟢 GERİ ÇEKİLMEDE AL",
            ]
        )
    ]
)

pullback_count = len(
    analysis[
        analysis["decision"]
        == "🟡 GERİ ÇEKİLME BEKLE"
    ]
)

breakout_count = len(
    analysis[
        analysis["decision"]
        == "🔵 KIRILIM BEKLE"
    ]
)

chase_count = len(
    analysis[
        analysis["decision"]
        == "🔴 KOVALAMA"
    ]
)

falling_count = len(
    analysis[
        analysis["decision"]
        == "🔴 DÜŞÜŞ BICAĞI"
    ]
)

c1, c2, c3, c4, c5, c6 = st.columns(6)

c1.metric(
    "Analiz",
    len(analysis)
)

c2.metric(
    "🟢 Trade",
    trade_count
)

c3.metric(
    "🟡 Geri Çekilme",
    pullback_count
)

c4.metric(
    "🔵 Kırılım",
    breakout_count
)

c5.metric(
    "🔴 Kovalama",
    chase_count
)

c6.metric(
    "🔴 Düşüş Bıçağı",
    falling_count
)


# ============================================================
# EN İYİ TRADE FIRSATLARI
# ============================================================

st.divider()

st.subheader(
    "🏆 En İyi Kripto Trade Fırsatları"
)

best = analysis[
    ~analysis["decision"].isin(
        [
            "🔴 LİKİDİTE YETERSİZ",
            "🔴 DÜŞÜŞ BICAĞI",
            "🔴 KOVALAMA",
            "🟠 İZLE",
        ]
    )
].copy()

display_cols = [
    "coin",
    "price",
    "change",
    "volume",
    "strength",
    "entry_score",
    "trend15",
    "trend1h",
    "rsi",
    "volume_ratio",
    "chase_score",
    "grade",
    "decision",
]

display_df = best[
    display_cols
].head(20).copy()

display_df.columns = [
    "Coin",
    "Fiyat",
    "24S",
    "Hacim",
    "Güç",
    "Trade",
    "15D",
    "1S",
    "RSI",
    "Hacim Oranı",
    "Kovalama",
    "Sınıf",
    "Karar",
]

display_df["Fiyat"] = display_df[
    "Fiyat"
].apply(fmt_price)

display_df["24S"] = display_df[
    "24S"
].apply(pct)

display_df["Hacim"] = display_df[
    "Hacim"
].apply(fmt_try)

st.dataframe(
    display_df,
    use_container_width=True,
    hide_index=True,
)


# ============================================================
# PROFESYONEL TRADE ADAYLARI
# ============================================================

st.divider()

st.subheader(
    "🟢 Gerçek Trade Adayları"
)

trade_df = analysis[
    analysis["decision"].isin(
        [
            "🟢 AL",
            "🟢 GERİ ÇEKİLMEDE AL",
        ]
    )
].copy()

trade_df = trade_df.sort_values(
    [
        "entry_score",
        "rr",
    ],
    ascending=False
)


if trade_df.empty:

    st.info(
        "Şu anda bütün profesyonel kriterleri "
        "aynı anda karşılayan coin bulunmuyor."
    )

else:

    for _, row in trade_df.head(6).iterrows():

        with st.container(
            border=True
        ):

            st.markdown(
                f"## 🟢 {row['coin']} "
                f"— {row['decision']}"
            )

            a, b, c, d, e = st.columns(5)

            a.metric(
                "Fiyat",
                fmt_price(
                    row["price"]
                )
            )

            b.metric(
                "Trade Skoru",
                f"{row['entry_score']:.1f}"
            )

            c.metric(
                "Güç",
                f"{row['strength']:.1f}"
            )

            d.metric(
                "15D Trend",
                f"{row['trend15']:.1f}"
            )

            e.metric(
                "1S Trend",
                f"{row['trend1h']:.1f}"
            )

            st.markdown(
                f"""
### 🎯 Trade Planı

**Giriş Bölgesi:**  
`{fmt_price(row['entry_low'])}`
 – `{fmt_price(row['entry_high'])}`

**Stop:**  
`{fmt_price(row['stop'])}`

**Hedef 1:**  
`{fmt_price(row['target1'])}`

**Hedef 2:**  
`{fmt_price(row['target2'])}`

**Hedef 3:**  
`{fmt_price(row['target3'])}`

**Risk / Ödül:**  
`1 : {row['rr']:.2f}`

**Destek:**  
`{fmt_price(row['support'])}`

**Direnç:**  
`{fmt_price(row['resistance'])}`

**RSI:** `{row['rsi']:.1f}`  
**VWAP:** `{fmt_price(row['vwap'])}`  
**Hacim Oranı:** `{row['volume_ratio']:.2f}x`  
**Kovalama:** `{row['chase_score']:.1f}`

**Sınıf:** {row['grade']}

**Karar:** {row['decision']}
"""
            )

            st.info(
                row["message"]
            )


# ============================================================
# GERİ ÇEKİLME BEKLENENLER
# ============================================================

st.divider()

st.subheader(
    "🟡 Güçlü Ama Geri Çekilme Beklenmeli"
)

pullback_df = analysis[
    analysis["decision"]
    == "🟡 GERİ ÇEKİLME BEKLE"
].copy()

if pullback_df.empty:

    st.info(
        "Şu anda güçlü fakat kovalama riski nedeniyle "
        "geri çekilme beklenen coin yok."
    )

else:

    pullback_display = pullback_df[
        [
            "coin",
            "price",
            "change",
            "strength",
            "trend_alignment",
            "chase_score",
            "entry_low",
            "entry_high",
            "support",
            "resistance",
        ]
    ].copy()

    pullback_display.columns = [
        "Coin",
        "Fiyat",
        "24S",
        "Güç",
        "Trend",
        "Kovalama",
        "Giriş Alt",
        "Giriş Üst",
        "Destek",
        "Direnç",
    ]

    pullback_display["Fiyat"] = (
        pullback_display["Fiyat"]
        .apply(fmt_price)
    )

    pullback_display["24S"] = (
        pullback_display["24S"]
        .apply(pct)
    )

    for col in [
        "Giriş Alt",
        "Giriş Üst",
        "Destek",
        "Direnç",
    ]:

        pullback_display[col] = (
            pullback_display[col]
            .apply(fmt_price)
        )

    st.dataframe(
        pullback_display,
        use_container_width=True,
        hide_index=True,
    )


# ============================================================
# KIRILIM BEKLEYENLER
# ============================================================

st.divider()

st.subheader(
    "🔵 Kırılım Beklenen Coinler"
)

breakout_df = analysis[
    analysis["decision"]
    == "🔵 KIRILIM BEKLE"
].copy()

if breakout_df.empty:

    st.info(
        "Şu anda yeterli trend + hacim teyidiyle "
        "kırılım beklenen coin bulunmuyor."
    )

else:

    breakout_display = breakout_df[
        [
            "coin",
            "price",
            "change",
            "strength",
            "entry_score",
            "trend15",
            "trend1h",
            "volume_ratio",
            "breakout_score",
            "resistance",
        ]
    ].copy()

    breakout_display.columns = [
        "Coin",
        "Fiyat",
        "24S",
        "Güç",
        "Trade",
        "15D",
        "1S",
        "Hacim Oranı",
        "Kırılım",
        "Direnç",
    ]

    breakout_display["Fiyat"] = (
        breakout_display["Fiyat"]
        .apply(fmt_price)
    )

    breakout_display["24S"] = (
        breakout_display["24S"]
        .apply(pct)
    )

    breakout_display["Direnç"] = (
        breakout_display["Direnç"]
        .apply(fmt_price)
    )

    st.dataframe(
        breakout_display,
        use_container_width=True,
        hide_index=True,
    )


# ============================================================
# TEYİT BEKLEYENLER
# ============================================================

st.divider()

st.subheader(
    "🟡 Teyit Bekleyenler"
)

confirm_df = analysis[
    analysis["decision"]
    == "🟡 TEYİT BEKLE"
].copy()

if confirm_df.empty:

    st.success(
        "Teyit bekleyen belirgin coin yok."
    )

else:

    confirm_display = confirm_df[
        [
            "coin",
            "price",
            "change",
            "strength",
            "trend15",
            "trend1h",
            "rsi",
            "volume_ratio",
            "entry_score",
        ]
    ].copy()

    confirm_display.columns = [
        "Coin",
        "Fiyat",
        "24S",
        "Güç",
        "15D",
        "1S",
        "RSI",
        "Hacim Oranı",
        "Trade",
    ]

    confirm_display["Fiyat"] = (
        confirm_display["Fiyat"]
        .apply(fmt_price)
    )

    confirm_display["24S"] = (
        confirm_display["24S"]
        .apply(pct)
    )

    st.dataframe(
        confirm_display,
        use_container_width=True,
        hide_index=True,
    )


# ============================================================
# DÜŞÜŞ BICAĞI
# ============================================================

st.divider()

st.subheader(
    "🔴 Düşüş Bıçağı — Uzak Dur"
)

falling_df = analysis[
    analysis["decision"]
    == "🔴 DÜŞÜŞ BICAĞI"
].copy()

if falling_df.empty:

    st.success(
        "Şu anda düşüş bıçağı filtresine takılan coin yok."
    )

else:

    falling_display = falling_df[
        [
            "coin",
            "price",
            "change",
            "strength",
            "trend15",
            "trend1h",
            "rsi",
            "volume_ratio",
            "entry_score",
        ]
    ].copy()

    falling_display.columns = [
        "Coin",
        "Fiyat",
        "24S",
        "Güç",
        "15D",
        "1S",
        "RSI",
        "Hacim Oranı",
        "Trade",
    ]

    falling_display["Fiyat"] = (
        falling_display["Fiyat"]
        .apply(fmt_price)
    )

    falling_display["24S"] = (
        falling_display["24S"]
        .apply(pct)
    )

    st.dataframe(
        falling_display,
        use_container_width=True,
        hide_index=True,
    )


# ============================================================
# KOVALAMA
# ============================================================

st.divider()

st.subheader(
    "🔴 Kovalama Riski"
)

chase_df = analysis[
    analysis["decision"]
    == "🔴 KOVALAMA"
].copy()

if chase_df.empty:

    st.success(
        "Aşırı kovalama bölgesinde coin bulunmuyor."
    )

else:

    chase_display = chase_df[
        [
            "coin",
            "price",
            "change",
            "position",
            "chase_score",
            "strength",
            "trend_alignment",
        ]
    ].copy()

    chase_display.columns = [
        "Coin",
        "Fiyat",
        "24S",
        "24S Zirve Konumu",
        "Kovalama",
        "Güç",
        "Trend",
    ]

    chase_display["Fiyat"] = (
        chase_display["Fiyat"]
        .apply(fmt_price)
    )

    chase_display["24S"] = (
        chase_display["24S"]
        .apply(pct)
    )

    st.dataframe(
        chase_display,
        use_container_width=True,
        hide_index=True,
    )


# ============================================================
# DETAYLI COIN ANALİZİ
# ============================================================

st.divider()

st.subheader(
    "🔎 Coin Detay Analizi"
)

coin_list = analysis[
    "coin"
].tolist()

if coin_list:

    selected_coin = st.selectbox(
        "Coin seç",
        coin_list
    )

    row = analysis[
        analysis["coin"]
        == selected_coin
    ].iloc[0]

    st.markdown(
        f"## {row['coin']} — {row['decision']}"
    )

    x1, x2, x3, x4, x5 = st.columns(5)

    x1.metric(
        "Fiyat",
        fmt_price(
            row["price"]
        )
    )

    x2.metric(
        "Trade",
        f"{row['entry_score']:.1f}"
    )

    x3.metric(
        "Güç",
        f"{row['strength']:.1f}"
    )

    x4.metric(
        "15D",
        f"{row['trend15']:.1f}"
    )

    x5.metric(
        "1S",
        f"{row['trend1h']:.1f}"
    )

    st.markdown("---")

    d1, d2, d3 = st.columns(3)

    with d1:

        st.markdown(
            "### 📊 Teknik Yapı"
        )

        st.write(
            f"**24S:** "
            f"{pct(row['change'])}"
        )

        st.write(
            f"**RSI:** "
            f"{row['rsi']:.1f}"
        )

        st.write(
            f"**EMA9:** "
            f"{fmt_price(row['ema9'])}"
        )

        st.write(
            f"**EMA20:** "
            f"{fmt_price(row['ema20'])}"
        )

        st.write(
            f"**EMA50:** "
            f"{fmt_price(row['ema50'])}"
        )

        st.write(
            f"**VWAP:** "
            f"{fmt_price(row['vwap'])}"
        )

    with d2:

        st.markdown(
            "### 📈 Destek / Direnç"
        )

        st.write(
            f"**Destek 1:** "
            f"{fmt_price(row['support'])}"
        )

        st.write(
            f"**Destek 2:** "
            f"{fmt_price(row['support2'])}"
        )

        st.write(
            f"**Direnç 1:** "
            f"{fmt_price(row['resistance'])}"
        )

        st.write(
            f"**Direnç 2:** "
            f"{fmt_price(row['resistance2'])}"
        )

        st.write(
            f"**Dirence Uzaklık:** "
            f"{row['resistance_distance']:.2f}%"
        )

        st.write(
            f"**Kırılım Skoru:** "
            f"{row['breakout_score']:.1f}"
        )

    with d3:

        st.markdown(
            "### 🎯 Trade Planı"
        )

        st.write(
            f"**Giriş:** "
            f"{fmt_price(row['entry_low'])}"
            f" – "
            f"{fmt_price(row['entry_high'])}"
        )

        st.write(
            f"**Stop:** "
            f"{fmt_price(row['stop'])}"
        )

        st.write(
            f"**Hedef 1:** "
            f"{fmt_price(row['target1'])}"
        )

        st.write(
            f"**Hedef 2:** "
            f"{fmt_price(row['target2'])}"
        )

        st.write(
            f"**Hedef 3:** "
            f"{fmt_price(row['target3'])}"
        )

        st.write(
            f"**R/R:** "
            f"1 : {row['rr']:.2f}"
        )

        st.write(
            f"**Kovalama:** "
            f"{row['chase_score']:.1f}"
        )

    st.info(
        row["message"]
    )


# ============================================================
# HAM VERİ
# ============================================================

with st.expander(
    "📊 Ham Piyasa Verisi"
):

    raw = analysis[
        [
            "symbol",
            "coin",
            "price",
            "change",
            "volume",
            "high",
            "low",
        ]
    ].copy()

    st.dataframe(
        raw,
        use_container_width=True,
        hide_index=True,
    )


# ============================================================
# MOTOR MANTIĞI
# ============================================================

with st.expander(
    "🧠 Yeni Crypto Trade Motoru Nasıl Çalışıyor?"
):

    st.markdown(
        """
## 0. Ortak TRY Evreni

Kripto Trade artık **Kripto Piyasa ile aynı `crypto_engine` TRY evrenini** kullanır.

- Hacim sıralamasında ilk 60 ile sınırlama yoktur.
- Tüm geçerli TRY pariteleri evrene alınır.
- Düşük likiditeli coinler listeden kaybolmaz.
- Yalnızca gereksiz mum API çağrısı yapılmaz.

---

## 1. Güç Skoru

Coinin sadece yükselip yükselmediğine bakılmaz.

Birlikte değerlendirilir:

- 24S momentum
- 15D trend
- 1S trend
- EMA9
- EMA20
- EMA50
- RSI
- VWAP
- hacim
- likidite
- fiyatın range içindeki konumu

---

## 2. Trade Skoru

**Güçlü coin = otomatik AL değildir.**

Trade skoru ayrıca:

- trend uyumu
- giriş bölgesi
- risk/getiri
- kovalama riski
- hacim
- VWAP

üzerinden hesaplanır.

---

## 3. Düşüş Bıçağı Filtresi

Örneğin:

> XRP %10 düştü.

Bu tek başına:

> "Ucuzladı, AL"

anlamına gelmez.

Eğer:

- 15D trend zayıf
- 1S trend zayıf
- RSI zayıf

ise sistem:

**🔴 DÜŞÜŞ BICAĞI**

üretir.

---

## 4. Geri Çekilmede AL

Bu karar için:

- trend pozitif
- trade skoru yeterli
- R/R ≥ 1:2
- kovalama riski kontrol altında

olması gerekir.

---

## 5. Kırılım Bekle

Coin direnç bölgesine yaklaşıyorsa:

**🔵 KIRILIM BEKLE**

denir.

Kırılım için:

- direnç yakınlığı
- 15D trend
- 1S trend
- hacim

birlikte değerlendirilir.

---

## 6. Kovalama

Bir coin %15-20 yükselmiş olabilir.

Bu onu otomatik olarak iyi trade yapmaz.

Fiyat zirveye fazla yaklaşmışsa:

**🔴 KOVALAMA**

üretilir.

---

## 7. Nihai Soru

Sistem artık:

> "Hangi coin güçlü?"

sorusunu değil,

> **"Hangi coin şu anda trade edilebilir ve risk/getiri açısından mantıklı?"**

sorusunu cevaplar.
"""
    )


# ============================================================
# UYARI
# ============================================================

st.caption(
    "⚠️ Bu sayfa otomatik emir göndermez. "
    "Skorlar ve seviyeler teknik analiz amaçlıdır; "
    "yatırım tavsiyesi değildir."
)