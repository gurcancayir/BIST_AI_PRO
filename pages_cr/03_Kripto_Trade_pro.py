# ============================================================
# CRYPTO AI PRO
# 02_Kripto_Gunluk_Trade_PRO_FINAL_V3.py
#
# PROFESYONEL TAM TARAMA + SETUP QUALITY + MARKET CONTEXT
#
# AMAÇ
# ------------------------------------------------------------
# Sadece "güçlü coin" bulmak değildir.
#
# Sistem birlikte değerlendirir:
#   1) Master coin evreni
#   2) Market Regime
#   3) Market Breadth
#   4) BTC / ETH piyasa bağlamı
#   5) 24s momentum
#   6) Likidite
#   7) 15D + 1S trend
#   8) EMA 9 / 20 / 50
#   9) RSI
#  10) VWAP
#  11) Hacim teyidi
#  12) Support / Resistance
#  13) Pullback / Breakout
#  14) Entry Quality
#  15) Gerçek Risk / Ödül
#  16) Chase riski
#  17) Volatilite riski
#  18) Setup Quality
#  19) FINAL Trade Score
#
# KARARLAR
# ------------------------------------------------------------
# 🟢 GÜÇLÜ AL
# 🟢 AL
# 🟢 GERİ ÇEKİLMEDE AL
# 🟡 TUT / TEYİT
# 🟡 TUT / GERİ ÇEKİLME BEKLE
# 🔵 KIRILIM BEKLE
# 🟠 İZLE
# 🟠 AZALT
# 🔴 SAT / UZAK DUR
# 🔴 KOVALAMA
# 🔴 DÜŞÜŞ BICAĞI
# 🔴 LİKİDİTE YETERSİZ
# ⚪ VERİ YETERSİZ
#
# MİMARİ
# ------------------------------------------------------------
# crypto_engine.get_all_try_universe()
#            ↓
# MASTER EVREN
#            ↓
# TÜM COINLER GÖRÜNÜR
#            ↓
# MARKET CONTEXT
#            ↓
# DERİN ANALİZ HAVUZU
#            ↓
# 15D + 1S
#            ↓
# SETUP + ENTRY + R/R
#            ↓
# FINAL KARAR
#
# ÖNEMLİ
# ------------------------------------------------------------
# - Ayrı coin evreni oluşturmaz.
# - İlk 60 / ilk 80 gibi gizli limit YOKTUR.
# - Coinler sessizce kaybolmaz.
# - Derin analize girmeyen coin teşhis tablosunda görünür.
# - Otomatik emir göndermez.
# ============================================================

from __future__ import annotations

import importlib
import math
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

import numpy as np
import pandas as pd
import streamlit as st

import crypto_engine


# ============================================================
# SAYFA
# ============================================================

st.set_page_config(
    page_title="Crypto AI PRO - Günlük Trade PRO",
    page_icon="⚡",
    layout="wide",
)

try:
    crypto_engine = importlib.reload(crypto_engine)
except Exception:
    pass


# ============================================================
# SABİTLER
# ============================================================

CACHE_TTL = 60
KLINE_LIMIT = 180
MIN_TECH_CANDLES = 55

DEFAULT_TRADE_MIN_VOLUME = 10_000_000
DEFAULT_DEEP_SCAN_MIN_VOLUME = 1_000_000

DEFAULT_MIN_CHANGE = -25.0
DEFAULT_MAX_CHANGE = 35.0

# FINAL karar eşikleri
STRONG_BUY_SCORE = 82.0
BUY_SCORE = 74.0
PULLBACK_BUY_SCORE = 66.0
HOLD_SCORE = 58.0

# Market regime eşikleri
MARKET_STRONG = 70.0
MARKET_POSITIVE = 60.0
MARKET_WEAK = 45.0


# ============================================================
# YARDIMCI FONKSİYONLAR
# ============================================================

def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default

        if isinstance(value, str):
            value = (
                value.replace(",", "")
                .replace("%", "")
                .replace("₺", "")
                .strip()
            )

        result = float(value)

        if not np.isfinite(result):
            return default

        return result

    except Exception:
        return default


def clamp(
    value: Any,
    low: float = 0.0,
    high: float = 100.0,
) -> float:
    return max(
        low,
        min(
            high,
            safe_float(value),
        ),
    )


def fmt_price(value: Any) -> str:
    value = safe_float(value)

    if value >= 1000:
        return f"{value:,.2f}"

    if value >= 100:
        return f"{value:,.3f}"

    if value >= 1:
        return f"{value:,.4f}"

    if value >= 0.01:
        return f"{value:,.5f}"

    if value >= 0.0001:
        return f"{value:,.8f}"

    return f"{value:,.10f}"


def fmt_money(value: Any) -> str:
    value = safe_float(value)

    if value >= 1_000_000_000:
        return f"₺{value / 1_000_000_000:.2f} Mr"

    if value >= 1_000_000:
        return f"₺{value / 1_000_000:.1f} Mn"

    if value >= 1_000:
        return f"₺{value / 1_000:.1f} Bin"

    return f"₺{value:,.0f}"


def fmt_pct(value: Any) -> str:
    return f"{safe_float(value):+.2f}%"


def normalize_symbol(value: Any) -> str:
    return (
        str(value or "")
        .upper()
        .strip()
        .replace("/", "")
        .replace("_", "")
        .replace("-", "")
    )


def first_existing(
    df: pd.DataFrame,
    names: list[str],
    default: Any = np.nan,
) -> pd.Series:
    for name in names:
        if name in df.columns:
            return df[name]

    return pd.Series(
        [default] * len(df),
        index=df.index,
    )


def weighted_average(
    values: list[Tuple[float, float]],
    default: float = 50.0,
) -> float:
    total_weight = sum(
        max(0.0, safe_float(weight))
        for _, weight in values
    )

    if total_weight <= 0:
        return default

    total = sum(
        safe_float(value) * max(0.0, safe_float(weight))
        for value, weight in values
    )

    return total / total_weight


# ============================================================
# MASTER MARKET EVRENİ
# ============================================================

@st.cache_data(
    ttl=CACHE_TTL,
    show_spinner=False,
)
def load_master_market() -> pd.DataFrame:
    raw = crypto_engine.get_all_try_universe()

    if raw is None:
        return pd.DataFrame()

    if isinstance(raw, pd.DataFrame):
        df = raw.copy()

    elif isinstance(raw, list):
        if not raw:
            return pd.DataFrame()

        if isinstance(raw[0], dict):
            df = pd.DataFrame(raw)
        else:
            df = pd.DataFrame(
                {"symbol": raw}
            )

    else:
        return pd.DataFrame()

    if df.empty:
        return pd.DataFrame()

    result = pd.DataFrame(
        index=df.index
    )

    result["symbol"] = (
        first_existing(
            df,
            ["symbol", "pair", "code", "name"],
            "",
        )
        .astype(str)
        .map(normalize_symbol)
    )

    result["base_asset"] = (
        first_existing(
            df,
            ["base_asset", "coin", "base", "asset"],
            "",
        )
        .astype(str)
        .str.upper()
        .str.strip()
    )

    missing_base = (
        result["base_asset"]
        .isin(
            ["", "NAN", "NONE"]
        )
    )

    result.loc[
        missing_base,
        "base_asset"
    ] = (
        result.loc[
            missing_base,
            "symbol"
        ]
        .str.replace(
            "TRY",
            "",
            regex=False,
        )
        .str.replace(
            "USDT",
            "",
            regex=False,
        )
    )

    result["price_try"] = pd.to_numeric(
        first_existing(
            df,
            [
                "price_try",
                "price",
                "last_price",
                "lastPrice",
                "close",
            ],
        ),
        errors="coerce",
    )

    result["change_24h"] = pd.to_numeric(
        first_existing(
            df,
            [
                "change_24h",
                "change",
                "priceChangePercent",
                "price_change_percent",
            ],
            0.0,
        ),
        errors="coerce",
    ).fillna(0.0)

    result["volume_try"] = pd.to_numeric(
        first_existing(
            df,
            [
                "volume_try",
                "quoteVolume",
                "quote_volume",
                "volume",
            ],
            0.0,
        ),
        errors="coerce",
    ).fillna(0.0)

    result["high_24h"] = pd.to_numeric(
        first_existing(
            df,
            [
                "high_24h",
                "high",
                "highPrice",
            ],
        ),
        errors="coerce",
    )

    result["low_24h"] = pd.to_numeric(
        first_existing(
            df,
            [
                "low_24h",
                "low",
                "lowPrice",
            ],
        ),
        errors="coerce",
    )

    result["source"] = (
        first_existing(
            df,
            ["source"],
            "",
        )
        .astype(str)
        .str.upper()
        .str.strip()
    )

    result["analysis_symbol"] = (
        first_existing(
            df,
            ["analysis_symbol"],
            "",
        )
        .astype(str)
        .map(normalize_symbol)
    )

    missing_analysis = (
        result["analysis_symbol"]
        .isin(
            ["", "NAN", "NONE"]
        )
    )

    result.loc[
        missing_analysis,
        "analysis_symbol"
    ] = result.loc[
        missing_analysis,
        "symbol"
    ]

    result["has_price"] = (
        result["price_try"]
        .fillna(0)
        .gt(0)
    )

    # Coin adı olmayan satırı gösteremeyiz.
    result = result[
        ~result["base_asset"].isin(
            ["", "NAN", "NONE"]
        )
    ].copy()

    # Aynı base asset iki kaynaktan geldiyse crypto_engine zaten
    # TR öncelikli seçiyor. Burada tekrar tekilleştiriyoruz.
    result = (
        result
        .drop_duplicates(
            subset=["base_asset"],
            keep="first",
        )
        .reset_index(drop=True)
    )

    return result


# ============================================================
# MARKET CONTEXT
# ============================================================

def change_quality_score(change: float) -> float:
    change = safe_float(change)

    if change <= -12:
        return 10

    if change <= -7:
        return 25

    if change < -3:
        return 40

    if change < 0:
        return 50

    if change < 2:
        return 62

    if change < 5:
        return 75

    if change < 8:
        return 86

    if change < 12:
        return 92

    if change < 18:
        return 78

    return 55


def calculate_market_context(
    market: pd.DataFrame,
) -> Dict[str, Any]:
    if market is None or market.empty:
        return {
            "market_score": 50.0,
            "breadth": 50.0,
            "regime": "🟡 NÖTR",
            "positive_pct": 0.0,
            "strong_positive_pct": 0.0,
            "weak_pct": 0.0,
            "btc_change": 0.0,
            "eth_change": 0.0,
            "btc_score": 50.0,
            "eth_score": 50.0,
            "volume_weighted_change": 0.0,
        }

    x = market.copy()

    x["change_24h"] = pd.to_numeric(
        x["change_24h"],
        errors="coerce",
    ).fillna(0.0)

    x["volume_try"] = pd.to_numeric(
        x["volume_try"],
        errors="coerce",
    ).fillna(0.0)

    valid = x[
        x["has_price"]
    ].copy()

    if valid.empty:
        valid = x.copy()

    positive_pct = (
        (valid["change_24h"] > 0)
        .mean()
        * 100
    )

    strong_positive_pct = (
        (valid["change_24h"] >= 3)
        .mean()
        * 100
    )

    weak_pct = (
        (valid["change_24h"] <= -3)
        .mean()
        * 100
    )

    # Breadth:
    # % pozitif + güçlü pozitif - belirgin negatif.
    breadth = clamp(
        positive_pct * 0.65
        + strong_positive_pct * 0.45
        - weak_pct * 0.25
        + 25
    )

    total_volume = safe_float(
        valid["volume_try"].sum()
    )

    if total_volume > 0:
        volume_weighted_change = safe_float(
            (
                valid["change_24h"]
                * valid["volume_try"]
            ).sum()
            / total_volume
        )
    else:
        volume_weighted_change = safe_float(
            valid["change_24h"].mean()
        )

    def coin_change(symbol: str) -> float:
        row = valid[
            valid["base_asset"] == symbol
        ]

        if row.empty:
            return 0.0

        return safe_float(
            row.iloc[0]["change_24h"]
        )

    btc_change = coin_change("BTC")
    eth_change = coin_change("ETH")

    btc_score = change_quality_score(
        btc_change
    )

    eth_score = change_quality_score(
        eth_change
    )

    vw_change_score = clamp(
        50
        + volume_weighted_change * 5
    )

    market_score = weighted_average(
        [
            (breadth, 0.40),
            (btc_score, 0.25),
            (eth_score, 0.15),
            (vw_change_score, 0.20),
        ],
        default=50,
    )

    if market_score >= MARKET_STRONG:
        regime = "🟢 GÜÇLÜ / RISK-ON"

    elif market_score >= MARKET_POSITIVE:
        regime = "🟢 POZİTİF"

    elif market_score >= MARKET_WEAK:
        regime = "🟡 NÖTR"

    elif market_score >= 35:
        regime = "🟠 ZAYIF"

    else:
        regime = "🔴 RISK-OFF"

    return {
        "market_score": round(
            market_score,
            1,
        ),
        "breadth": round(
            breadth,
            1,
        ),
        "regime": regime,
        "positive_pct": round(
            positive_pct,
            1,
        ),
        "strong_positive_pct": round(
            strong_positive_pct,
            1,
        ),
        "weak_pct": round(
            weak_pct,
            1,
        ),
        "btc_change": round(
            btc_change,
            2,
        ),
        "eth_change": round(
            eth_change,
            2,
        ),
        "btc_score": round(
            btc_score,
            1,
        ),
        "eth_score": round(
            eth_score,
            1,
        ),
        "volume_weighted_change": round(
            volume_weighted_change,
            2,
        ),
    }


# ============================================================
# HIZLI MARKET / COIN ÖN SKOR
# ============================================================

def liquidity_score(
    volume: Any,
) -> float:
    volume = safe_float(volume)

    if volume >= 2_000_000_000:
        return 100

    if volume >= 1_000_000_000:
        return 96

    if volume >= 500_000_000:
        return 90

    if volume >= 250_000_000:
        return 84

    if volume >= 100_000_000:
        return 76

    if volume >= 50_000_000:
        return 68

    if volume >= 20_000_000:
        return 60

    if volume >= 10_000_000:
        return 52

    if volume >= 5_000_000:
        return 44

    if volume >= 1_000_000:
        return 35

    return 20


def momentum_score(
    change: Any,
) -> float:
    change = safe_float(change)

    if change <= -20:
        return 5

    if change <= -15:
        return 12

    if change <= -10:
        return 22

    if change < -5:
        return 35

    if change < -2:
        return 45

    if change < 0:
        return 52

    if change < 2:
        return 62

    if change < 5:
        return 76

    if change < 8:
        return 88

    if change < 12:
        return 94

    if change < 16:
        return 82

    if change < 20:
        return 68

    if change < 25:
        return 54

    return 35


def calculate_range_features(
    price: Any,
    high: Any,
    low: Any,
) -> Tuple[float, float]:
    price = safe_float(price)
    high = safe_float(high)
    low = safe_float(low)

    if not (
        price > 0
        and high > low > 0
    ):
        return 50.0, 0.0

    position = (
        (price - low)
        / (high - low)
        * 100
    )

    range_pct = (
        (high - low)
        / low
        * 100
    )

    return (
        clamp(position),
        max(
            0.0,
            range_pct,
        ),
    )


def location_score(
    position: Any,
) -> float:
    position = safe_float(
        position,
        50,
    )

    if position < 10:
        return 55

    if position < 25:
        return 74

    if position < 45:
        return 90

    if position < 65:
        return 92

    if position < 80:
        return 78

    if position < 90:
        return 58

    return 32


def volatility_quality(
    range_pct: Any,
) -> float:
    value = safe_float(
        range_pct
    )

    if value <= 0:
        return 50

    if value < 2:
        return 55

    if value < 5:
        return 72

    if value < 10:
        return 92

    if value < 15:
        return 88

    if value < 22:
        return 72

    if value < 30:
        return 52

    if value < 40:
        return 35

    return 20


def build_universe_scores(
    market: pd.DataFrame,
    min_change: float,
    max_change: float,
    trade_min_volume: float,
    deep_scan_min_volume: float,
) -> pd.DataFrame:
    if market is None or market.empty:
        return pd.DataFrame()

    df = market.copy()

    features = df.apply(
        lambda row:
            calculate_range_features(
                row["price_try"],
                row["high_24h"],
                row["low_24h"],
            ),
        axis=1,
        result_type="expand",
    )

    features.columns = [
        "range_position",
        "range_pct",
    ]

    df = pd.concat(
        [
            df.reset_index(drop=True),
            features.reset_index(drop=True),
        ],
        axis=1,
    )

    df["liquidity_score"] = (
        df["volume_try"]
        .apply(
            liquidity_score
        )
    )

    df["momentum_score"] = (
        df["change_24h"]
        .apply(
            momentum_score
        )
    )

    df["location_score"] = (
        df["range_position"]
        .apply(
            location_score
        )
    )

    df["volatility_quality"] = (
        df["range_pct"]
        .apply(
            volatility_quality
        )
    )

    df["quick_score"] = (
        df["liquidity_score"] * 0.35
        + df["momentum_score"] * 0.30
        + df["location_score"] * 0.20
        + df["volatility_quality"] * 0.15
    ).clip(
        0,
        100,
    )

    df["trade_liquidity_ok"] = (
        df["volume_try"]
        >= trade_min_volume
    )

    df["deep_scan_ok"] = (
        df["has_price"]
        & (
            df["volume_try"]
            >= deep_scan_min_volume
        )
        & df["change_24h"].between(
            min_change,
            max_change,
            inclusive="both",
        )
    )

    def scan_reason(
        row: pd.Series,
    ) -> str:
        if not bool(
            row["has_price"]
        ):
            return "FİYAT YOK"

        if (
            safe_float(
                row["volume_try"]
            )
            < deep_scan_min_volume
        ):
            return "ÇOK DÜŞÜK HACİM"

        if not (
            min_change
            <= safe_float(
                row["change_24h"]
            )
            <= max_change
        ):
            return "24S AŞIRI HAREKET"

        return "DERİN ANALİZ"

    df["scan_status"] = df.apply(
        scan_reason,
        axis=1,
    )

    return (
        df.sort_values(
            [
                "deep_scan_ok",
                "quick_score",
                "volume_try",
            ],
            ascending=[
                False,
                False,
                False,
            ],
        )
        .reset_index(drop=True)
    )


# ============================================================
# TEKNİK HESAPLAR
# ============================================================

def calc_rsi(
    series: pd.Series,
    period: int = 14,
) -> pd.Series:
    delta = series.diff()

    gain = delta.clip(
        lower=0
    )

    loss = -delta.clip(
        upper=0
    )

    avg_gain = gain.ewm(
        alpha=1 / period,
        adjust=False,
    ).mean()

    avg_loss = loss.ewm(
        alpha=1 / period,
        adjust=False,
    ).mean()

    rs = (
        avg_gain
        / avg_loss.replace(
            0,
            np.nan,
        )
    )

    rsi = (
        100
        - (
            100
            / (1 + rs)
        )
    )

    return (
        rsi
        .replace(
            [
                np.inf,
                -np.inf,
            ],
            np.nan,
        )
        .fillna(50)
    )


def calc_vwap(
    df: pd.DataFrame,
) -> pd.Series:
    typical = (
        df["high"]
        + df["low"]
        + df["close"]
    ) / 3

    cumulative_volume = (
        df["volume"]
        .cumsum()
    )

    cumulative_value = (
        typical
        * df["volume"]
    ).cumsum()

    return (
        cumulative_value
        / cumulative_volume.replace(
            0,
            np.nan,
        )
    ).fillna(
        df["close"]
    )


def prepare_tf(
    df: pd.DataFrame,
) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    x = df.copy()

    required = [
        "open",
        "high",
        "low",
        "close",
        "volume",
    ]

    if not all(
        col in x.columns
        for col in required
    ):
        return pd.DataFrame()

    for col in required:
        x[col] = pd.to_numeric(
            x[col],
            errors="coerce",
        )

    x = x.dropna(
        subset=required,
    ).copy()

    if x.empty:
        return x

    x["ema9"] = (
        x["close"]
        .ewm(
            span=9,
            adjust=False,
        )
        .mean()
    )

    x["ema20"] = (
        x["close"]
        .ewm(
            span=20,
            adjust=False,
        )
        .mean()
    )

    x["ema50"] = (
        x["close"]
        .ewm(
            span=50,
            adjust=False,
        )
        .mean()
    )

    x["rsi"] = calc_rsi(
        x["close"],
        14,
    )

    x["vwap"] = calc_vwap(
        x
    )

    x["vol_ma20"] = (
        x["volume"]
        .rolling(20)
        .mean()
    )

    x["volume_ratio"] = (
        x["volume"]
        / x["vol_ma20"].replace(
            0,
            np.nan,
        )
    )

    # ATR benzeri gerçek volatilite ölçüsü.
    previous_close = (
        x["close"]
        .shift(1)
    )

    true_range = pd.concat(
        [
            (
                x["high"]
                - x["low"]
            ).abs(),
            (
                x["high"]
                - previous_close
            ).abs(),
            (
                x["low"]
                - previous_close
            ).abs(),
        ],
        axis=1,
    ).max(
        axis=1
    )

    x["atr14"] = (
        true_range
        .rolling(14)
        .mean()
    )

    return x


def timeframe_metrics(
    df: pd.DataFrame,
) -> Dict[str, Any]:
    if (
        df is None
        or df.empty
    ):
        return {
            "ok": False,
            "candles": 0,
            "price": 0.0,
            "ema9": 0.0,
            "ema20": 0.0,
            "ema50": 0.0,
            "rsi": 50.0,
            "vwap": 0.0,
            "volume_ratio": 1.0,
            "atr_pct": 0.0,
            "trend_score": 50.0,
            "support": 0.0,
            "resistance": 0.0,
            "support2": 0.0,
            "resistance2": 0.0,
        }

    x = prepare_tf(
        df
    )

    if (
        x.empty
        or len(x) < MIN_TECH_CANDLES
    ):
        return {
            "ok": False,
            "candles": len(x),
            "price": 0.0,
            "ema9": 0.0,
            "ema20": 0.0,
            "ema50": 0.0,
            "rsi": 50.0,
            "vwap": 0.0,
            "volume_ratio": 1.0,
            "atr_pct": 0.0,
            "trend_score": 50.0,
            "support": 0.0,
            "resistance": 0.0,
            "support2": 0.0,
            "resistance2": 0.0,
        }

    last = x.iloc[-1]

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
        50,
    )

    vwap = safe_float(
        last["vwap"]
    )

    volume_ratio = safe_float(
        last["volume_ratio"],
        1,
    )

    atr14 = safe_float(
        last["atr14"]
    )

    atr_pct = (
        atr14
        / price
        * 100
        if price > 0
        else 0
    )

    trend_score = 0.0

    if price > ema9:
        trend_score += 12

    if ema9 > ema20:
        trend_score += 16

    if ema20 > ema50:
        trend_score += 18

    if price > ema20:
        trend_score += 12

    if price > ema50:
        trend_score += 14

    if price > vwap:
        trend_score += 10

    if 50 <= rsi <= 68:
        trend_score += 12

    elif 45 <= rsi < 50:
        trend_score += 6

    elif 68 < rsi <= 75:
        trend_score += 5

    if volume_ratio >= 1.5:
        trend_score += 6

    elif volume_ratio >= 1.1:
        trend_score += 4

    recent60 = x.tail(
        60
    )

    recent30 = x.tail(
        30
    )

    support = safe_float(
        recent60["low"].min(),
        price * 0.97,
    )

    resistance = safe_float(
        recent60["high"].max(),
        price * 1.03,
    )

    support2 = safe_float(
        recent30["low"].min(),
        support,
    )

    resistance2 = safe_float(
        recent30["high"].max(),
        resistance,
    )

    return {
        "ok": True,
        "candles": len(x),
        "price": price,
        "ema9": ema9,
        "ema20": ema20,
        "ema50": ema50,
        "rsi": rsi,
        "vwap": vwap,
        "volume_ratio": volume_ratio,
        "atr_pct": atr_pct,
        "trend_score": clamp(
            trend_score
        ),
        "support": support,
        "resistance": resistance,
        "support2": support2,
        "resistance2": resistance2,
    }


# ============================================================
# ENTRY QUALITY
# ============================================================

def calculate_entry_quality(
    price: float,
    ema20: float,
    vwap: float,
    support: float,
    resistance: float,
    rsi: float,
    range_position: float,
    chase_score: float,
) -> Tuple[float, Dict[str, float]]:
    price = safe_float(price)

    if price <= 0:
        return 0.0, {}

    def distance_pct(
        level: float,
    ) -> float:
        level = safe_float(level)

        if level <= 0:
            return 999.0

        return abs(
            price - level
        ) / price * 100

    ema20_dist = distance_pct(
        ema20
    )

    vwap_dist = distance_pct(
        vwap
    )

    support_dist = (
        (
            price
            - safe_float(support)
        )
        / price
        * 100
        if (
            safe_float(support) > 0
            and price >= safe_float(support)
        )
        else 999.0
    )

    resistance_dist = (
        (
            safe_float(resistance)
            - price
        )
        / price
        * 100
        if safe_float(resistance) > price
        else 0.0
    )

    # EMA20 yakınlığı
    if ema20_dist <= 0.8:
        ema_score = 100

    elif ema20_dist <= 1.8:
        ema_score = 90

    elif ema20_dist <= 3:
        ema_score = 76

    elif ema20_dist <= 5:
        ema_score = 58

    else:
        ema_score = 35

    # VWAP yakınlığı
    if vwap_dist <= 0.6:
        vwap_entry_score = 100

    elif vwap_dist <= 1.5:
        vwap_entry_score = 88

    elif vwap_dist <= 3:
        vwap_entry_score = 70

    elif vwap_dist <= 5:
        vwap_entry_score = 50

    else:
        vwap_entry_score = 32

    # Desteğe yakınlık
    if support_dist <= 1:
        support_score = 96

    elif support_dist <= 2.5:
        support_score = 88

    elif support_dist <= 5:
        support_score = 72

    elif support_dist <= 8:
        support_score = 55

    else:
        support_score = 35

    # Dirence çok yakınsa giriş kalitesi düşer.
    if resistance_dist <= 0:
        resistance_room_score = 35

    elif resistance_dist < 1:
        resistance_room_score = 40

    elif resistance_dist < 2:
        resistance_room_score = 55

    elif resistance_dist < 4:
        resistance_room_score = 72

    elif resistance_dist < 7:
        resistance_room_score = 88

    else:
        resistance_room_score = 95

    # RSI giriş bölgesi
    if 50 <= rsi <= 64:
        rsi_entry_score = 95

    elif 45 <= rsi < 50:
        rsi_entry_score = 78

    elif 64 < rsi <= 70:
        rsi_entry_score = 78

    elif 40 <= rsi < 45:
        rsi_entry_score = 58

    elif 70 < rsi <= 75:
        rsi_entry_score = 50

    else:
        rsi_entry_score = 30

    # Günlük range konumu:
    # orta bölge ideal, zirveye yapışmak kötü.
    range_score = location_score(
        range_position
    )

    entry_quality = weighted_average(
        [
            (ema_score, 0.18),
            (vwap_entry_score, 0.17),
            (support_score, 0.18),
            (resistance_room_score, 0.18),
            (rsi_entry_score, 0.14),
            (range_score, 0.10),
            (100 - chase_score, 0.05),
        ],
        default=50,
    )

    return (
        clamp(entry_quality),
        {
            "ema20_distance_pct":
                round(
                    ema20_dist,
                    2,
                ),
            "vwap_distance_pct":
                round(
                    vwap_dist,
                    2,
                ),
            "support_distance_pct":
                round(
                    support_dist
                    if support_dist < 900
                    else 0,
                    2,
                ),
            "resistance_distance_pct":
                round(
                    resistance_dist,
                    2,
                ),
        },
    )


# ============================================================
# TRADE PLAN + REAL R/R
# ============================================================

def calculate_trade_plan(
    price: float,
    ema20: float,
    vwap: float,
    support: float,
    support2: float,
    resistance: float,
    resistance2: float,
    atr_pct: float,
) -> Dict[str, float]:
    price = safe_float(price)

    if price <= 0:
        return {
            "entry_low": 0.0,
            "entry_high": 0.0,
            "stop": 0.0,
            "target1": 0.0,
            "target2": 0.0,
            "target3": 0.0,
            "rr": 0.0,
            "risk_pct": 0.0,
            "reward_pct": 0.0,
        }

    atr_pct = max(
        safe_float(atr_pct),
        0.8,
    )

    pullback_levels = [
        safe_float(ema20),
        safe_float(vwap),
        safe_float(support),
        price * (
            1
            - min(
                max(
                    atr_pct * 0.35,
                    0.8,
                ),
                3.0,
            )
            / 100
        ),
    ]

    valid = [
        x
        for x in pullback_levels
        if (
            x > 0
            and x < price
            and x >= price * 0.88
        )
    ]

    if valid:
        entry_low = max(
            min(valid),
            price * 0.90,
        )

        entry_high = min(
            max(valid),
            price * 0.992,
        )

    else:
        entry_low = price * 0.97
        entry_high = price * 0.987

    if entry_low >= entry_high:
        entry_low = price * 0.97
        entry_high = price * 0.987

    # Stop: destek + ATR birlikte.
    stop_candidates = [
        safe_float(support2) * 0.992,
        safe_float(support) * 0.985,
        price * (
            1
            - min(
                max(
                    atr_pct * 1.25,
                    2.0,
                ),
                9.0,
            )
            / 100
        ),
    ]

    valid_stops = [
        x
        for x in stop_candidates
        if (
            x > 0
            and x < price
        )
    ]

    stop = (
        max(valid_stops)
        if valid_stops
        else price * 0.94
    )

    # Stop çok dar ya da çok geniş olmasın.
    stop = min(
        stop,
        price * 0.992,
    )

    stop = max(
        stop,
        price * 0.90,
    )

    # Gerçek giriş için mevcut fiyat değil,
    # entry_high kullanılır (konservatif yaklaşım).
    planned_entry = min(
        price,
        entry_high
    )

    risk = max(
        planned_entry
        - stop,
        planned_entry * 0.005,
    )

    # Hedefler: teknik direnç + risk bazlı hedef.
    rr_target2 = (
        planned_entry
        + risk * 2.2
    )

    rr_target3 = (
        planned_entry
        + risk * 3.2
    )

    target1 = max(
        planned_entry
        + risk * 1.4,
        safe_float(resistance)
        if safe_float(resistance) > planned_entry
        else 0.0,
    )

    target2 = max(
        rr_target2,
        safe_float(resistance) * 1.02
        if safe_float(resistance) > planned_entry
        else 0.0,
    )

    target3 = max(
        rr_target3,
        safe_float(resistance2)
        if safe_float(resistance2) > planned_entry
        else 0.0,
    )

    rr = (
        (
            target2
            - planned_entry
        )
        / risk
        if risk > 0
        else 0.0
    )

    risk_pct = (
        risk
        / planned_entry
        * 100
        if planned_entry > 0
        else 0
    )

    reward_pct = (
        (
            target2
            - planned_entry
        )
        / planned_entry
        * 100
        if planned_entry > 0
        else 0
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
        "target3":
            target3,
        "rr":
            round(
                rr,
                2,
            ),
        "risk_pct":
            round(
                risk_pct,
                2,
            ),
        "reward_pct":
            round(
                reward_pct,
                2,
            ),
    }


def rr_quality(
    rr: Any,
    risk_pct: Any,
) -> float:
    rr = safe_float(rr)
    risk_pct = safe_float(
        risk_pct
    )

    if rr >= 3:
        score = 100

    elif rr >= 2.5:
        score = 92

    elif rr >= 2:
        score = 84

    elif rr >= 1.7:
        score = 70

    elif rr >= 1.4:
        score = 55

    elif rr >= 1:
        score = 38

    else:
        score = 20

    # Stop riski aşırı genişse ceza.
    if risk_pct > 9:
        score -= 20

    elif risk_pct > 7:
        score -= 12

    elif risk_pct > 5:
        score -= 5

    return clamp(
        score
    )


# ============================================================
# CHASE + BREAKOUT + PULLBACK
# ============================================================

def calculate_chase_score(
    change: float,
    range_position: float,
    rsi: float,
    price: float,
    ema20: float,
    vwap: float,
) -> float:
    score = 0.0

    if change >= 5:
        score += 15

    if change >= 10:
        score += 18

    if change >= 15:
        score += 18

    if change >= 20:
        score += 15

    if range_position >= 80:
        score += 10

    if range_position >= 90:
        score += 10

    if range_position >= 97:
        score += 5

    if rsi >= 72:
        score += 10

    if rsi >= 78:
        score += 8

    if (
        price > 0
        and ema20 > 0
        and price > ema20 * 1.06
    ):
        score += 8

    if (
        price > 0
        and vwap > 0
        and price > vwap * 1.05
    ):
        score += 8

    return clamp(
        score
    )


def calculate_breakout_score(
    price: float,
    resistance: float,
    trend15: float,
    trend1h: float,
    volume_ratio: float,
    rsi: float,
) -> float:
    score = 0.0

    if (
        resistance > 0
        and price > 0
    ):
        distance = (
            resistance
            - price
        ) / price * 100

        if -0.5 <= distance <= 0.5:
            score += 42

        elif 0.5 < distance <= 2:
            score += 30

        elif 2 < distance <= 5:
            score += 16

    if trend15 >= 75:
        score += 18

    if trend1h >= 70:
        score += 18

    if volume_ratio >= 1.5:
        score += 18

    elif volume_ratio >= 1.2:
        score += 10

    if 52 <= rsi <= 70:
        score += 4

    return clamp(
        score
    )


def calculate_pullback_score(
    price: float,
    ema20: float,
    vwap: float,
    support: float,
    trend_alignment: float,
    rsi: float,
) -> float:
    if price <= 0:
        return 0.0

    distances = []

    for level in [
        ema20,
        vwap,
        support,
    ]:
        level = safe_float(
            level
        )

        if level > 0:
            distances.append(
                abs(
                    price - level
                )
                / price
                * 100
            )

    if not distances:
        proximity = 50

    else:
        nearest = min(
            distances
        )

        if nearest <= 0.7:
            proximity = 100

        elif nearest <= 1.5:
            proximity = 90

        elif nearest <= 3:
            proximity = 76

        elif nearest <= 5:
            proximity = 58

        else:
            proximity = 35

    if 45 <= rsi <= 62:
        rsi_pullback = 92

    elif 40 <= rsi < 45:
        rsi_pullback = 72

    elif 62 < rsi <= 68:
        rsi_pullback = 75

    else:
        rsi_pullback = 45

    return clamp(
        proximity * 0.50
        + trend_alignment * 0.35
        + rsi_pullback * 0.15
    )


# ============================================================
# DERİN COIN ANALİZİ
# ============================================================

def deep_analyze_coin(
    row: pd.Series,
    market_context: Dict[str, Any],
    trade_min_volume: float,
) -> Dict[str, Any]:
    base = str(
        row["base_asset"]
    ).upper()

    symbol = normalize_symbol(
        row["symbol"]
    )

    analysis_symbol = normalize_symbol(
        row.get(
            "analysis_symbol",
            symbol,
        )
    )

    source = str(
        row.get(
            "source",
            "",
        )
    ).upper().strip()

    source_arg: Optional[str]

    if source in [
        "BINANCE_TR",
        "BINANCE_GLOBAL",
    ]:
        source_arg = source

    else:
        source_arg = None

    # Kline çağrısında mümkünse engine'in analysis_symbol bilgisini kullan.
    kline_symbol = (
        analysis_symbol
        if analysis_symbol
        else symbol
    )

    try:
        df15 = crypto_engine.get_klines(
            kline_symbol,
            interval="15m",
            limit=KLINE_LIMIT,
            source=source_arg,
        )

    except Exception:
        df15 = pd.DataFrame()

    try:
        df1h = crypto_engine.get_klines(
            kline_symbol,
            interval="1h",
            limit=KLINE_LIMIT,
            source=source_arg,
        )

    except Exception:
        df1h = pd.DataFrame()

    tf15 = timeframe_metrics(
        df15
    )

    tf1h = timeframe_metrics(
        df1h
    )

    # Her iki timeframe yoksa coin kaybolmaz.
    if (
        not tf15["ok"]
        and not tf1h["ok"]
    ):
        return {
            "analysis_status":
                (
                    "15D + 1S VERİ YETERSİZ "
                    f"({tf15['candles']}/{tf1h['candles']})"
                ),
            "deep_ok": False,
            "trend15": 50.0,
            "trend1h": 50.0,
            "trend_alignment": 50.0,
            "rsi": 50.0,
            "volume_ratio": 1.0,
            "vwap": 0.0,
            "ema9": 0.0,
            "ema20": 0.0,
            "ema50": 0.0,
            "atr_pct": 0.0,
            "support": 0.0,
            "support2": 0.0,
            "resistance": 0.0,
            "resistance2": 0.0,
            "entry_quality": 0.0,
            "setup_quality": 0.0,
            "rr_quality": 0.0,
            "chase_score": 0.0,
            "breakout_score": 0.0,
            "pullback_score": 0.0,
            "market_factor":
                safe_float(
                    market_context[
                        "market_score"
                    ]
                ),
            "strength": 0.0,
            "final_score": 0.0,
            "decision":
                "⚪ VERİ YETERSİZ",
            "entry_low": 0.0,
            "entry_high": 0.0,
            "stop": 0.0,
            "target1": 0.0,
            "target2": 0.0,
            "target3": 0.0,
            "rr": 0.0,
            "risk_pct": 0.0,
            "reward_pct": 0.0,
            "ema20_distance_pct": 0.0,
            "vwap_distance_pct": 0.0,
            "support_distance_pct": 0.0,
            "resistance_distance_pct": 0.0,
        }

    # Tek timeframe varsa diğerinin yerine vekil kullan.
    if not tf15["ok"]:
        tf15 = tf1h.copy()

    if not tf1h["ok"]:
        tf1h = tf15.copy()

    price = safe_float(
        row["price_try"]
    )

    if price <= 0:
        price = safe_float(
            tf15["price"]
        )

    change = safe_float(
        row["change_24h"]
    )

    volume_try = safe_float(
        row["volume_try"]
    )

    quick_score = safe_float(
        row["quick_score"],
        50,
    )

    range_position = safe_float(
        row["range_position"],
        50,
    )

    range_pct = safe_float(
        row["range_pct"]
    )

    trend15 = safe_float(
        tf15["trend_score"],
        50,
    )

    trend1h = safe_float(
        tf1h["trend_score"],
        50,
    )

    trend_alignment = (
        trend15 * 0.45
        + trend1h * 0.55
    )

    rsi = safe_float(
        tf15["rsi"],
        50,
    )

    volume_ratio = safe_float(
        tf15["volume_ratio"],
        1,
    )

    vwap = safe_float(
        tf15["vwap"]
    )

    ema9 = safe_float(
        tf15["ema9"]
    )

    ema20 = safe_float(
        tf15["ema20"]
    )

    ema50 = safe_float(
        tf15["ema50"]
    )

    atr_pct = max(
        safe_float(
            tf15["atr_pct"]
        ),
        safe_float(
            tf1h["atr_pct"]
        ) * 0.6,
    )

    support = safe_float(
        tf15["support"],
        price * 0.97,
    )

    support2 = safe_float(
        tf15["support2"],
        support,
    )

    resistance = safe_float(
        tf15["resistance"],
        price * 1.03,
    )

    resistance2 = safe_float(
        tf15["resistance2"],
        resistance,
    )

    # --------------------------------------------------------
    # CHASE
    # --------------------------------------------------------

    chase_score = calculate_chase_score(
        change,
        range_position,
        rsi,
        price,
        ema20,
        vwap,
    )

    # --------------------------------------------------------
    # BREAKOUT / PULLBACK
    # --------------------------------------------------------

    breakout_score = calculate_breakout_score(
        price,
        resistance,
        trend15,
        trend1h,
        volume_ratio,
        rsi,
    )

    pullback_score = calculate_pullback_score(
        price,
        ema20,
        vwap,
        support,
        trend_alignment,
        rsi,
    )

    # --------------------------------------------------------
    # ENTRY QUALITY
    # --------------------------------------------------------

    entry_quality, distances = (
        calculate_entry_quality(
            price,
            ema20,
            vwap,
            support,
            resistance,
            rsi,
            range_position,
            chase_score,
        )
    )

    # --------------------------------------------------------
    # TRADE PLAN / REAL R/R
    # --------------------------------------------------------

    trade_plan = calculate_trade_plan(
        price,
        ema20,
        vwap,
        support,
        support2,
        resistance,
        resistance2,
        atr_pct,
    )

    rr = safe_float(
        trade_plan["rr"]
    )

    rr_score = rr_quality(
        rr,
        trade_plan["risk_pct"],
    )

    # --------------------------------------------------------
    # RSI / VOLUME / VWAP QUALITY
    # --------------------------------------------------------

    if 50 <= rsi <= 66:
        rsi_quality = 95

    elif 45 <= rsi < 50:
        rsi_quality = 78

    elif 66 < rsi <= 72:
        rsi_quality = 76

    elif 40 <= rsi < 45:
        rsi_quality = 58

    elif 72 < rsi <= 78:
        rsi_quality = 45

    else:
        rsi_quality = 28

    if volume_ratio >= 2:
        volume_quality = 100

    elif volume_ratio >= 1.5:
        volume_quality = 92

    elif volume_ratio >= 1.2:
        volume_quality = 82

    elif volume_ratio >= 1:
        volume_quality = 68

    elif volume_ratio >= 0.75:
        volume_quality = 52

    else:
        volume_quality = 35

    if vwap > 0:
        if price > vwap * 1.04:
            vwap_quality = 58

        elif price > vwap:
            vwap_quality = 92

        elif price >= vwap * 0.985:
            vwap_quality = 68

        else:
            vwap_quality = 38

    else:
        vwap_quality = 50

    # --------------------------------------------------------
    # VOLATILITY RISK
    # --------------------------------------------------------

    volatility_penalty = 0.0

    if atr_pct >= 8:
        volatility_penalty += 15

    elif atr_pct >= 6:
        volatility_penalty += 10

    elif atr_pct >= 4.5:
        volatility_penalty += 5

    if range_pct >= 35:
        volatility_penalty += 12

    elif range_pct >= 25:
        volatility_penalty += 7

    # --------------------------------------------------------
    # COIN STRENGTH
    # --------------------------------------------------------

    strength = weighted_average(
        [
            (
                trend_alignment,
                0.38,
            ),
            (
                momentum_score(
                    change
                ),
                0.15,
            ),
            (
                rsi_quality,
                0.12,
            ),
            (
                volume_quality,
                0.13,
            ),
            (
                vwap_quality,
                0.10,
            ),
            (
                safe_float(
                    row[
                        "liquidity_score"
                    ]
                ),
                0.12,
            ),
        ],
        default=50,
    )

    if change <= -10:
        strength -= 8

    if change <= -15:
        strength -= 8

    strength = clamp(
        strength
    )

    # --------------------------------------------------------
    # SETUP QUALITY
    # --------------------------------------------------------

    setup_quality = weighted_average(
        [
            (
                trend_alignment,
                0.25,
            ),
            (
                entry_quality,
                0.22,
            ),
            (
                rr_score,
                0.20,
            ),
            (
                volume_quality,
                0.10,
            ),
            (
                max(
                    breakout_score,
                    pullback_score,
                ),
                0.08,
            ),
            (
                vwap_quality,
                0.06,
            ),
            (
                rsi_quality,
                0.05,
            ),
            (
                100 - chase_score,
                0.04,
            ),
        ],
        default=50,
    )

    setup_quality = clamp(
        setup_quality
        - volatility_penalty
    )

    # --------------------------------------------------------
    # MARKET FACTOR
    # --------------------------------------------------------

    market_score = safe_float(
        market_context[
            "market_score"
        ],
        50,
    )

    breadth = safe_float(
        market_context[
            "breadth"
        ],
        50,
    )

    market_factor = weighted_average(
        [
            (
                market_score,
                0.65,
            ),
            (
                breadth,
                0.35,
            ),
        ],
        default=50,
    )

    # Market cezası/bonusu:
    # Final score tamamen market tarafından ezilmesin,
    # ama zayıf piyasada seçicilik artsın.
    market_adjustment = (
        market_factor
        - 50
    ) * 0.16

    # --------------------------------------------------------
    # FINAL SCORE
    # --------------------------------------------------------

    final_score = weighted_average(
        [
            (
                setup_quality,
                0.36,
            ),
            (
                strength,
                0.20,
            ),
            (
                entry_quality,
                0.15,
            ),
            (
                rr_score,
                0.12,
            ),
            (
                trend_alignment,
                0.08,
            ),
            (
                volume_quality,
                0.05,
            ),
            (
                quick_score,
                0.04,
            ),
        ],
        default=50,
    )

    final_score += (
        market_adjustment
    )

    final_score -= (
        chase_score
        * 0.10
    )

    final_score -= (
        volatility_penalty
        * 0.40
    )

    final_score = clamp(
        final_score
    )

    # --------------------------------------------------------
    # PROFESYONEL KARAR MOTORU
    # --------------------------------------------------------

    liquidity_ok = (
        volume_try
        >= trade_min_volume
    )

    falling_knife = (
        change <= -8
        and trend15 < 50
        and trend1h < 55
        and rsi < 45
    )

    structural_bear = (
        trend15 < 35
        and trend1h < 40
        and price < ema20
        and price < ema50
    )

    market_risk_off = (
        market_factor < 38
    )

    if not liquidity_ok:
        decision = (
            "🔴 LİKİDİTE YETERSİZ"
        )

    elif falling_knife:
        decision = (
            "🔴 DÜŞÜŞ BICAĞI"
        )

    elif (
        structural_bear
        and final_score < 42
    ):
        decision = (
            "🔴 SAT / UZAK DUR"
        )

    elif (
        chase_score >= 82
        or (
            change >= 18
            and rsi >= 73
            and range_position >= 85
        )
    ):
        decision = (
            "🔴 KOVALAMA"
        )

    elif (
        final_score >= STRONG_BUY_SCORE
        and setup_quality >= 80
        and entry_quality >= 72
        and rr >= 2
        and trend_alignment >= 72
        and chase_score < 55
        and market_factor >= 48
    ):
        decision = (
            "🟢 GÜÇLÜ AL"
        )

    elif (
        final_score >= BUY_SCORE
        and setup_quality >= 70
        and entry_quality >= 64
        and rr >= 1.7
        and trend_alignment >= 64
        and chase_score < 68
        and market_factor >= 42
    ):
        decision = (
            "🟢 AL"
        )

    elif (
        final_score >= PULLBACK_BUY_SCORE
        and setup_quality >= 63
        and trend_alignment >= 58
        and rr >= 1.5
        and pullback_score >= 60
        and chase_score < 75
    ):
        decision = (
            "🟢 GERİ ÇEKİLMEDE AL"
        )

    elif (
        breakout_score >= 76
        and trend_alignment >= 65
        and volume_ratio >= 1.2
        and chase_score < 75
    ):
        decision = (
            "🔵 KIRILIM BEKLE"
        )

    elif (
        strength >= 68
        and chase_score >= 65
    ):
        decision = (
            "🟡 TUT / GERİ ÇEKİLME BEKLE"
        )

    elif (
        final_score >= HOLD_SCORE
        and trend_alignment >= 52
    ):
        decision = (
            "🟡 TUT / TEYİT"
        )

    elif (
        final_score < 45
        and trend_alignment < 45
        and market_risk_off
    ):
        decision = (
            "🟠 AZALT"
        )

    elif (
        final_score < 42
        and trend_alignment < 40
    ):
        decision = (
            "🟠 AZALT"
        )

    else:
        decision = (
            "🟠 İZLE"
        )

    return {
        "analysis_status":
            "OK",
        "deep_ok":
            True,
        "trend15":
            round(
                trend15,
                1,
            ),
        "trend1h":
            round(
                trend1h,
                1,
            ),
        "trend_alignment":
            round(
                trend_alignment,
                1,
            ),
        "rsi":
            round(
                rsi,
                1,
            ),
        "volume_ratio":
            round(
                volume_ratio,
                2,
            ),
        "vwap":
            vwap,
        "ema9":
            ema9,
        "ema20":
            ema20,
        "ema50":
            ema50,
        "atr_pct":
            round(
                atr_pct,
                2,
            ),
        "support":
            support,
        "support2":
            support2,
        "resistance":
            resistance,
        "resistance2":
            resistance2,
        "entry_quality":
            round(
                entry_quality,
                1,
            ),
        "setup_quality":
            round(
                setup_quality,
                1,
            ),
        "rr_quality":
            round(
                rr_score,
                1,
            ),
        "chase_score":
            round(
                chase_score,
                1,
            ),
        "breakout_score":
            round(
                breakout_score,
                1,
            ),
        "pullback_score":
            round(
                pullback_score,
                1,
            ),
        "market_factor":
            round(
                market_factor,
                1,
            ),
        "strength":
            round(
                strength,
                1,
            ),
        "final_score":
            round(
                final_score,
                1,
            ),
        "decision":
            decision,
        **trade_plan,
        **distances,
    }


# ============================================================
# TAM TARAMA
# ============================================================

def run_full_scan(
    scan_pool: pd.DataFrame,
    market_context: Dict[str, Any],
    trade_min_volume: float,
) -> pd.DataFrame:
    if (
        scan_pool is None
        or scan_pool.empty
    ):
        return pd.DataFrame()

    rows = []

    total = len(
        scan_pool
    )

    progress = st.progress(
        0,
        text=(
            "Profesyonel tam tarama "
            "başlatılıyor..."
        ),
    )

    for i, (_, row) in enumerate(
        scan_pool.iterrows(),
        start=1,
    ):
        base = str(
            row["base_asset"]
        )

        try:
            result = deep_analyze_coin(
                row,
                market_context,
                trade_min_volume,
            )

        except Exception as exc:
            result = {
                "analysis_status":
                    f"HATA: {str(exc)}",
                "deep_ok":
                    False,
                "trend15":
                    50.0,
                "trend1h":
                    50.0,
                "trend_alignment":
                    50.0,
                "rsi":
                    50.0,
                "volume_ratio":
                    1.0,
                "vwap":
                    0.0,
                "ema9":
                    0.0,
                "ema20":
                    0.0,
                "ema50":
                    0.0,
                "atr_pct":
                    0.0,
                "support":
                    0.0,
                "support2":
                    0.0,
                "resistance":
                    0.0,
                "resistance2":
                    0.0,
                "entry_quality":
                    0.0,
                "setup_quality":
                    0.0,
                "rr_quality":
                    0.0,
                "chase_score":
                    0.0,
                "breakout_score":
                    0.0,
                "pullback_score":
                    0.0,
                "market_factor":
                    safe_float(
                        market_context[
                            "market_score"
                        ]
                    ),
                "strength":
                    0.0,
                "final_score":
                    0.0,
                "decision":
                    "⚪ VERİ YETERSİZ",
                "entry_low":
                    0.0,
                "entry_high":
                    0.0,
                "stop":
                    0.0,
                "target1":
                    0.0,
                "target2":
                    0.0,
                "target3":
                    0.0,
                "rr":
                    0.0,
                "risk_pct":
                    0.0,
                "reward_pct":
                    0.0,
                "ema20_distance_pct":
                    0.0,
                "vwap_distance_pct":
                    0.0,
                "support_distance_pct":
                    0.0,
                "resistance_distance_pct":
                    0.0,
            }

        rows.append(
            {
                **row.to_dict(),
                **result,
            }
        )

        progress.progress(
            i / max(
                total,
                1,
            ),
            text=(
                f"{base} analiz ediliyor "
                f"({i}/{total})"
            ),
        )

    progress.empty()

    result_df = pd.DataFrame(
        rows
    )

    if result_df.empty:
        return result_df

    return (
        result_df
        .sort_values(
            [
                "final_score",
                "setup_quality",
                "entry_quality",
                "rr_quality",
                "volume_try",
            ],
            ascending=[
                False,
                False,
                False,
                False,
                False,
            ],
        )
        .reset_index(drop=True)
    )


# ============================================================
# BAŞLIK
# ============================================================

st.title(
    "⚡ Crypto AI PRO — Profesyonel Günlük Trade Merkezi"
)

st.caption(
    "Amaç sadece güçlü coinleri bulmak değil; "
    "uygun giriş, gerçek risk/ödül ve piyasa koşullarını "
    "birlikte değerlendirerek işlem kalitesi yüksek setup'ları bulmaktır."
)


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.header(
        "⚙️ Profesyonel Filtreler"
    )

    trade_min_volume = st.number_input(
        "Trade İçin Min. 24s TRY Hacim",
        key="crypto_trade_v3_trade_min_volume",
        min_value=0,
        value=DEFAULT_TRADE_MIN_VOLUME,
        step=5_000_000,
        format="%d",
    )

    deep_scan_min_volume = st.number_input(
        "Derin Tarama İçin Min. Hacim",
        key="crypto_trade_v3_deep_scan_min_volume",
        min_value=0,
        value=DEFAULT_DEEP_SCAN_MIN_VOLUME,
        step=1_000_000,
        format="%d",
        help=(
            "Bu değer trade tavsiyesi eşiği değildir. "
            "Sadece aşırı düşük hacimli coinlerde gereksiz API yükünü azaltır."
        ),
    )

    min_change = st.slider(
        "Derin Tarama Min. 24s %",
        key="crypto_trade_v3_min_change",
        min_value=-60,
        max_value=0,
        value=int(
            DEFAULT_MIN_CHANGE
        ),
        step=1,
    )

    max_change = st.slider(
        "Derin Tarama Max. 24s %",
        key="crypto_trade_v3_max_change",
        min_value=5,
        max_value=100,
        value=int(
            DEFAULT_MAX_CHANGE
        ),
        step=1,
    )

    scan_limit = st.number_input(
        "Tarama Limiti (0 = TÜMÜ)",
        key="crypto_trade_v3_scan_limit",
        min_value=0,
        value=0,
        step=10,
        help=(
            "0 seçildiğinde uygun tüm coinler derin analiz edilir. "
            "Gizli limit yoktur."
        ),
    )

    st.divider()

    if st.button(
        "🔄 VERİYİ YENİLE",
        key="crypto_trade_v3_refresh",
        use_container_width=True,
    ):
        st.cache_data.clear()

        if (
            "crypto_trade_full_scan"
            in st.session_state
        ):
            del st.session_state[
                "crypto_trade_full_scan"
            ]

        st.rerun()


# ============================================================
# VERİYİ YÜKLE
# ============================================================

market = load_master_market()

if market.empty:
    st.error(
        "❌ crypto_engine master piyasa evreni alınamadı."
    )
    st.stop()

market_context = calculate_market_context(
    market
)

universe = build_universe_scores(
    market,
    min_change=float(
        min_change
    ),
    max_change=float(
        max_change
    ),
    trade_min_volume=float(
        trade_min_volume
    ),
    deep_scan_min_volume=float(
        deep_scan_min_volume
    ),
)

scan_pool = universe[
    universe["deep_scan_ok"]
].copy()

if int(
    scan_limit
) > 0:
    scan_pool = (
        scan_pool
        .head(
            int(
                scan_limit
            )
        )
        .copy()
    )


# ============================================================
# MARKET CONTEXT PANEL
# ============================================================

st.markdown(
    "### 🌍 Market Context"
)

mc1, mc2, mc3, mc4, mc5, mc6 = st.columns(
    6
)

mc1.metric(
    "Market Regime",
    market_context[
        "regime"
    ],
)

mc2.metric(
    "Market Score",
    (
        f"{market_context['market_score']:.1f}/100"
    ),
)

mc3.metric(
    "Market Breadth",
    (
        f"{market_context['breadth']:.1f}/100"
    ),
)

mc4.metric(
    "Pozitif Coin",
    (
        f"%{market_context['positive_pct']:.1f}"
    ),
)

mc5.metric(
    "BTC 24s",
    fmt_pct(
        market_context[
            "btc_change"
        ]
    ),
)

mc6.metric(
    "ETH 24s",
    fmt_pct(
        market_context[
            "eth_change"
        ]
    ),
)


# ============================================================
# EVREN PANELİ
# ============================================================

st.markdown(
    "### 🧭 Tarama Evreni"
)

e1, e2, e3, e4, e5 = st.columns(
    5
)

e1.metric(
    "Master Evren",
    len(
        universe
    ),
)

e2.metric(
    "Geçerli Fiyat",
    int(
        universe[
            "has_price"
        ].sum()
    ),
)

e3.metric(
    "Trade Likiditesi",
    int(
        universe[
            "trade_liquidity_ok"
        ].sum()
    ),
)

e4.metric(
    "Derin Tarama Havuzu",
    int(
        universe[
            "deep_scan_ok"
        ].sum()
    ),
)

e5.metric(
    "Bu Çalıştırmada",
    len(
        scan_pool
    ),
)

st.caption(
    f"Son veri yükleme: "
    f"{datetime.now().strftime('%d.%m.%Y %H:%M:%S')} | "
    f"Tarama limiti: "
    f"{'TÜMÜ' if int(scan_limit) == 0 else int(scan_limit)}"
)


# ============================================================
# TABS
# ============================================================

(
    tab_setup,
    tab_all,
    tab_market,
    tab_diag,
) = st.tabs(
    [
        "🏆 Setup Merkezi",
        "📊 Tüm Analiz",
        "🌍 Master Evren",
        "🧪 Teşhis",
    ]
)


# ============================================================
# SETUP MERKEZİ
# ============================================================

with tab_setup:

    st.subheader(
        "🏆 Profesyonel Setup Merkezi"
    )

    st.caption(
        "Final karar; coin gücü değil, "
        "setup kalitesi + giriş kalitesi + gerçek R/R + market context üzerinden verilir."
    )

    if scan_pool.empty:
        st.warning(
            "Derin analize gönderilecek coin bulunmuyor."
        )

    else:
        c_run, c_clear = st.columns(
            [3, 1]
        )

        with c_run:
            run_scan = st.button(
                f"⚡ TAM TARAMAYI ÇALIŞTIR "
                f"({len(scan_pool)} coin)",
                key="crypto_trade_v3_run_full_scan",
                type="primary",
                use_container_width=True,
            )

        with c_clear:
            if st.button(
                "🧹 Sonucu Temizle",
                key="crypto_trade_v3_clear_result",
                use_container_width=True,
            ):
                if (
                    "crypto_trade_full_scan"
                    in st.session_state
                ):
                    del st.session_state[
                        "crypto_trade_full_scan"
                    ]

                st.rerun()

        if run_scan:
            st.session_state[
                "crypto_trade_full_scan"
            ] = run_full_scan(
                scan_pool,
                market_context,
                float(
                    trade_min_volume
                ),
            )

        analysis = st.session_state.get(
            "crypto_trade_full_scan",
            pd.DataFrame(),
        )

        if (
            isinstance(
                analysis,
                pd.DataFrame,
            )
            and not analysis.empty
        ):
            # ---------------------------------------------
            # KARAR SAYILARI
            # ---------------------------------------------

            buy_mask = (
                analysis[
                    "decision"
                ]
                .isin(
                    [
                        "🟢 GÜÇLÜ AL",
                        "🟢 AL",
                        "🟢 GERİ ÇEKİLMEDE AL",
                    ]
                )
            )

            hold_mask = (
                analysis[
                    "decision"
                ]
                .isin(
                    [
                        "🟡 TUT / TEYİT",
                        "🟡 TUT / GERİ ÇEKİLME BEKLE",
                        "🔵 KIRILIM BEKLE",
                    ]
                )
            )

            reduce_mask = (
                analysis[
                    "decision"
                ]
                == "🟠 AZALT"
            )

            sell_mask = (
                analysis[
                    "decision"
                ]
                .isin(
                    [
                        "🔴 SAT / UZAK DUR",
                        "🔴 DÜŞÜŞ BICAĞI",
                    ]
                )
            )

            s1, s2, s3, s4, s5 = st.columns(
                5
            )

            s1.metric(
                "🟢 AL",
                int(
                    buy_mask.sum()
                ),
            )

            s2.metric(
                "🟡 TUT / BEKLE",
                int(
                    hold_mask.sum()
                ),
            )

            s3.metric(
                "🟠 AZALT",
                int(
                    reduce_mask.sum()
                ),
            )

            s4.metric(
                "🔴 SAT / UZAK DUR",
                int(
                    sell_mask.sum()
                ),
            )

            s5.metric(
                "Analiz",
                len(
                    analysis
                ),
            )

            # ---------------------------------------------
            # TOP SETUPS
            # ---------------------------------------------

            st.markdown(
                "### 🥇 En Kaliteli Setup'lar"
            )

            top_setups = analysis[
                analysis[
                    "decision"
                ].isin(
                    [
                        "🟢 GÜÇLÜ AL",
                        "🟢 AL",
                        "🟢 GERİ ÇEKİLMEDE AL",
                        "🔵 KIRILIM BEKLE",
                        "🟡 TUT / TEYİT",
                    ]
                )
            ].copy()

            if top_setups.empty:
                st.info(
                    "Mevcut koşullarda kaliteli pozitif setup bulunmuyor."
                )

            else:
                top_display = top_setups[
                    [
                        "base_asset",
                        "price_try",
                        "change_24h",
                        "volume_try",
                        "market_factor",
                        "strength",
                        "setup_quality",
                        "entry_quality",
                        "rr",
                        "risk_pct",
                        "chase_score",
                        "trend15",
                        "trend1h",
                        "final_score",
                        "decision",
                    ]
                ].copy()

                top_display.columns = [
                    "Coin",
                    "Fiyat ₺",
                    "24s %",
                    "Hacim ₺",
                    "Market",
                    "Güç",
                    "Setup",
                    "Entry",
                    "R/R",
                    "Risk %",
                    "Chase",
                    "15D",
                    "1S",
                    "FINAL",
                    "Karar",
                ]

                st.dataframe(
                    top_display,
                    use_container_width=True,
                    hide_index=True,
                    height=600,
                    column_config={
                        "Fiyat ₺":
                            st.column_config.NumberColumn(
                                format="₺%.8f",
                            ),
                        "24s %":
                            st.column_config.NumberColumn(
                                format="%.2f%%",
                            ),
                        "Hacim ₺":
                            st.column_config.NumberColumn(
                                format="₺%.0f",
                            ),
                        "Market":
                            st.column_config.ProgressColumn(
                                min_value=0,
                                max_value=100,
                                format="%.1f",
                            ),
                        "Güç":
                            st.column_config.ProgressColumn(
                                min_value=0,
                                max_value=100,
                                format="%.1f",
                            ),
                        "Setup":
                            st.column_config.ProgressColumn(
                                min_value=0,
                                max_value=100,
                                format="%.1f",
                            ),
                        "Entry":
                            st.column_config.ProgressColumn(
                                min_value=0,
                                max_value=100,
                                format="%.1f",
                            ),
                        "Chase":
                            st.column_config.ProgressColumn(
                                min_value=0,
                                max_value=100,
                                format="%.1f",
                            ),
                        "15D":
                            st.column_config.ProgressColumn(
                                min_value=0,
                                max_value=100,
                                format="%.1f",
                            ),
                        "1S":
                            st.column_config.ProgressColumn(
                                min_value=0,
                                max_value=100,
                                format="%.1f",
                            ),
                        "FINAL":
                            st.column_config.ProgressColumn(
                                min_value=0,
                                max_value=100,
                                format="%.1f",
                            ),
                    },
                )

            # ---------------------------------------------
            # GERÇEK AL ADAYLARI
            # ---------------------------------------------

            st.divider()

            st.markdown(
                "### 🟢 İşlem Kalitesi Yüksek AL Adayları"
            )

            buy_df = analysis[
                buy_mask
            ].copy()

            if buy_df.empty:
                st.info(
                    "Şu anda AL kriterlerini eksiksiz karşılayan setup yok."
                )

            else:
                for _, row in (
                    buy_df
                    .head(10)
                    .iterrows()
                ):
                    with st.container(
                        border=True
                    ):
                        st.markdown(
                            f"## {row['base_asset']} — "
                            f"{row['decision']}"
                        )

                        k1, k2, k3, k4, k5, k6 = st.columns(
                            6
                        )

                        k1.metric(
                            "FINAL",
                            f"{row['final_score']:.1f}",
                        )

                        k2.metric(
                            "Setup",
                            f"{row['setup_quality']:.1f}",
                        )

                        k3.metric(
                            "Entry",
                            f"{row['entry_quality']:.1f}",
                        )

                        k4.metric(
                            "Güç",
                            f"{row['strength']:.1f}",
                        )

                        k5.metric(
                            "R/R",
                            f"1 : {row['rr']:.2f}",
                        )

                        k6.metric(
                            "Market",
                            f"{row['market_factor']:.1f}",
                        )

                        p1, p2, p3, p4 = st.columns(
                            4
                        )

                        with p1:
                            st.markdown(
                                "#### 🎯 Giriş Planı"
                            )

                            st.write(
                                f"**Giriş Alt:** "
                                f"₺{fmt_price(row['entry_low'])}"
                            )

                            st.write(
                                f"**Giriş Üst:** "
                                f"₺{fmt_price(row['entry_high'])}"
                            )

                            st.write(
                                f"**Mevcut:** "
                                f"₺{fmt_price(row['price_try'])}"
                            )

                            st.write(
                                f"**Entry Quality:** "
                                f"{row['entry_quality']:.1f}/100"
                            )

                        with p2:
                            st.markdown(
                                "#### 🛡️ Risk"
                            )

                            st.write(
                                f"**Stop:** "
                                f"₺{fmt_price(row['stop'])}"
                            )

                            st.write(
                                f"**Risk:** "
                                f"%{row['risk_pct']:.2f}"
                            )

                            st.write(
                                f"**R/R:** "
                                f"1 : {row['rr']:.2f}"
                            )

                            st.write(
                                f"**ATR:** "
                                f"%{row['atr_pct']:.2f}"
                            )

                        with p3:
                            st.markdown(
                                "#### 🏆 Hedef"
                            )

                            st.write(
                                f"**Hedef 1:** "
                                f"₺{fmt_price(row['target1'])}"
                            )

                            st.write(
                                f"**Hedef 2:** "
                                f"₺{fmt_price(row['target2'])}"
                            )

                            st.write(
                                f"**Hedef 3:** "
                                f"₺{fmt_price(row['target3'])}"
                            )

                            st.write(
                                f"**Beklenen:** "
                                f"%{row['reward_pct']:.2f}"
                            )

                        with p4:
                            st.markdown(
                                "#### 📊 Teknik"
                            )

                            st.write(
                                f"**15D / 1S:** "
                                f"{row['trend15']:.0f} / "
                                f"{row['trend1h']:.0f}"
                            )

                            st.write(
                                f"**RSI:** "
                                f"{row['rsi']:.1f}"
                            )

                            st.write(
                                f"**Hacim:** "
                                f"{row['volume_ratio']:.2f}x"
                            )

                            st.write(
                                f"**Chase:** "
                                f"{row['chase_score']:.1f}"
                            )

            # ---------------------------------------------
            # DETAY
            # ---------------------------------------------

            st.divider()

            st.markdown(
                "### 🔎 Coin Detay Merkezi"
            )

            selected_coin = st.selectbox(
                "Coin seç",
                analysis[
                    "base_asset"
                ].astype(str).tolist(),
                key="trade_detail_coin",
            )

            detail = (
                analysis[
                    analysis[
                        "base_asset"
                    ]
                    == selected_coin
                ]
                .iloc[0]
            )

            d1, d2, d3, d4, d5 = st.columns(
                5
            )

            d1.metric(
                "Karar",
                detail[
                    "decision"
                ],
            )

            d2.metric(
                "FINAL",
                f"{detail['final_score']:.1f}",
            )

            d3.metric(
                "Setup",
                f"{detail['setup_quality']:.1f}",
            )

            d4.metric(
                "Entry",
                f"{detail['entry_quality']:.1f}",
            )

            d5.metric(
                "R/R",
                f"1 : {detail['rr']:.2f}",
            )

            detail_df = pd.DataFrame(
                {
                    "Gösterge": [
                        "Market Factor",
                        "Coin Gücü",
                        "Setup Quality",
                        "Entry Quality",
                        "FINAL Score",
                        "15D Trend",
                        "1S Trend",
                        "Trend Uyumu",
                        "RSI",
                        "VWAP",
                        "EMA9",
                        "EMA20",
                        "EMA50",
                        "Hacim Oranı",
                        "ATR %",
                        "Pullback",
                        "Breakout",
                        "Chase",
                        "Destek",
                        "Direnç",
                        "EMA20 Uzaklık %",
                        "VWAP Uzaklık %",
                        "Desteğe Uzaklık %",
                        "Dirence Uzaklık %",
                    ],
                    "Değer": [
                        f"{detail['market_factor']:.1f}",
                        f"{detail['strength']:.1f}",
                        f"{detail['setup_quality']:.1f}",
                        f"{detail['entry_quality']:.1f}",
                        f"{detail['final_score']:.1f}",
                        f"{detail['trend15']:.1f}",
                        f"{detail['trend1h']:.1f}",
                        f"{detail['trend_alignment']:.1f}",
                        f"{detail['rsi']:.1f}",
                        fmt_price(
                            detail["vwap"]
                        ),
                        fmt_price(
                            detail["ema9"]
                        ),
                        fmt_price(
                            detail["ema20"]
                        ),
                        fmt_price(
                            detail["ema50"]
                        ),
                        f"{detail['volume_ratio']:.2f}x",
                        f"{detail['atr_pct']:.2f}%",
                        f"{detail['pullback_score']:.1f}",
                        f"{detail['breakout_score']:.1f}",
                        f"{detail['chase_score']:.1f}",
                        fmt_price(
                            detail["support"]
                        ),
                        fmt_price(
                            detail["resistance"]
                        ),
                        f"{detail['ema20_distance_pct']:.2f}%",
                        f"{detail['vwap_distance_pct']:.2f}%",
                        f"{detail['support_distance_pct']:.2f}%",
                        f"{detail['resistance_distance_pct']:.2f}%",
                    ],
                }
            )

            st.dataframe(
                detail_df,
                use_container_width=True,
                hide_index=True,
            )


# ============================================================
# TÜM ANALİZ
# ============================================================

with tab_all:

    st.subheader(
        "📊 Tüm Derin Analiz Sonuçları"
    )

    analysis = st.session_state.get(
        "crypto_trade_full_scan",
        pd.DataFrame(),
    )

    if (
        not isinstance(
            analysis,
            pd.DataFrame,
        )
        or analysis.empty
    ):
        st.info(
            "Önce Setup Merkezi sekmesinden tam taramayı çalıştır."
        )

    else:
        all_display = analysis[
            [
                "base_asset",
                "price_try",
                "change_24h",
                "volume_try",
                "market_factor",
                "strength",
                "setup_quality",
                "entry_quality",
                "rr_quality",
                "rr",
                "risk_pct",
                "trend15",
                "trend1h",
                "rsi",
                "volume_ratio",
                "pullback_score",
                "breakout_score",
                "chase_score",
                "final_score",
                "decision",
                "analysis_status",
            ]
        ].copy()

        all_display.columns = [
            "Coin",
            "Fiyat ₺",
            "24s %",
            "Hacim ₺",
            "Market",
            "Güç",
            "Setup",
            "Entry",
            "R/R Skor",
            "R/R",
            "Risk %",
            "15D",
            "1S",
            "RSI",
            "Hacim x",
            "Pullback",
            "Breakout",
            "Chase",
            "FINAL",
            "Karar",
            "Veri",
        ]

        st.dataframe(
            all_display,
            use_container_width=True,
            hide_index=True,
            height=700,
            column_config={
                "Fiyat ₺":
                    st.column_config.NumberColumn(
                        format="₺%.8f",
                    ),
                "24s %":
                    st.column_config.NumberColumn(
                        format="%.2f%%",
                    ),
                "Hacim ₺":
                    st.column_config.NumberColumn(
                        format="₺%.0f",
                    ),
                "Market":
                    st.column_config.ProgressColumn(
                        min_value=0,
                        max_value=100,
                        format="%.1f",
                    ),
                "Güç":
                    st.column_config.ProgressColumn(
                        min_value=0,
                        max_value=100,
                        format="%.1f",
                    ),
                "Setup":
                    st.column_config.ProgressColumn(
                        min_value=0,
                        max_value=100,
                        format="%.1f",
                    ),
                "Entry":
                    st.column_config.ProgressColumn(
                        min_value=0,
                        max_value=100,
                        format="%.1f",
                    ),
                "R/R Skor":
                    st.column_config.ProgressColumn(
                        min_value=0,
                        max_value=100,
                        format="%.1f",
                    ),
                "15D":
                    st.column_config.ProgressColumn(
                        min_value=0,
                        max_value=100,
                        format="%.1f",
                    ),
                "1S":
                    st.column_config.ProgressColumn(
                        min_value=0,
                        max_value=100,
                        format="%.1f",
                    ),
                "Pullback":
                    st.column_config.ProgressColumn(
                        min_value=0,
                        max_value=100,
                        format="%.1f",
                    ),
                "Breakout":
                    st.column_config.ProgressColumn(
                        min_value=0,
                        max_value=100,
                        format="%.1f",
                    ),
                "Chase":
                    st.column_config.ProgressColumn(
                        min_value=0,
                        max_value=100,
                        format="%.1f",
                    ),
                "FINAL":
                    st.column_config.ProgressColumn(
                        min_value=0,
                        max_value=100,
                        format="%.1f",
                    ),
            },
        )


# ============================================================
# MASTER EVREN
# ============================================================

with tab_market:

    st.subheader(
        "🌍 Master Coin Evreni"
    )

    st.caption(
        "Bu tablo doğrudan crypto_engine.get_all_try_universe() çıktısından üretilir."
    )

    search = st.text_input(
        "Coin ara",
        placeholder="BTC, ETH, SOL...",
        key="master_coin_search",
    )

    view = universe.copy()

    if search:
        q = search.upper().strip()

        view = view[
            view[
                "base_asset"
            ]
            .astype(str)
            .str.upper()
            .str.contains(
                q,
                na=False,
            )
        ].copy()

    master_display = view[
        [
            "base_asset",
            "price_try",
            "change_24h",
            "volume_try",
            "liquidity_score",
            "momentum_score",
            "range_position",
            "range_pct",
            "quick_score",
            "trade_liquidity_ok",
            "deep_scan_ok",
            "scan_status",
            "source",
        ]
    ].copy()

    master_display.columns = [
        "Coin",
        "Fiyat ₺",
        "24s %",
        "Hacim ₺",
        "Likidite",
        "Momentum",
        "Range Konum",
        "Range %",
        "Ön Skor",
        "Trade Likidite",
        "Derin Tarama",
        "Tarama Durumu",
        "Kaynak",
    ]

    st.dataframe(
        master_display,
        use_container_width=True,
        hide_index=True,
        height=700,
    )


# ============================================================
# TEŞHİS
# ============================================================

with tab_diag:

    st.subheader(
        "🧪 Coin Kaçırmama / Filtre Teşhis Merkezi"
    )

    st.caption(
        "Hiçbir coin sessizce kaybolmaz. "
        "Derin analize girmeyen coinlerin nedeni burada görünür."
    )

    no_price_count = int(
        (~universe["has_price"]).sum()
    )

    very_low_volume_count = int(
        (
            universe["volume_try"]
            < float(
                deep_scan_min_volume
            )
        ).sum()
    )

    extreme_change_count = int(
        (
            ~universe[
                "change_24h"
            ].between(
                float(
                    min_change
                ),
                float(
                    max_change
                ),
                inclusive="both",
            )
        ).sum()
    )

    diag1, diag2, diag3, diag4 = st.columns(
        4
    )

    diag1.metric(
        "Master Evren",
        len(
            universe
        ),
    )

    diag2.metric(
        "Fiyat Yok",
        no_price_count,
    )

    diag3.metric(
        "Çok Düşük Hacim",
        very_low_volume_count,
    )

    diag4.metric(
        "Aşırı 24s Hareket",
        extreme_change_count,
    )

    diag_table = universe[
        [
            "base_asset",
            "price_try",
            "change_24h",
            "volume_try",
            "has_price",
            "trade_liquidity_ok",
            "deep_scan_ok",
            "scan_status",
            "source",
            "analysis_symbol",
        ]
    ].copy()

    diag_table.columns = [
        "Coin",
        "Fiyat ₺",
        "24s %",
        "Hacim ₺",
        "Fiyat Var",
        "Trade Likidite",
        "Derin Tarama",
        "Sebep",
        "Kaynak",
        "Analiz Sembolü",
    ]

    st.dataframe(
        diag_table,
        use_container_width=True,
        hide_index=True,
        height=650,
    )

    analysis = st.session_state.get(
        "crypto_trade_full_scan",
        pd.DataFrame(),
    )

    if (
        isinstance(
            analysis,
            pd.DataFrame,
        )
        and not analysis.empty
    ):
        st.divider()

        st.markdown(
            "### 🔬 Derin Analiz Veri Kontrolü"
        )

        deep_diag = analysis[
            [
                "base_asset",
                "analysis_status",
                "decision",
                "final_score",
                "setup_quality",
                "entry_quality",
                "rr",
            ]
        ].copy()

        deep_diag.columns = [
            "Coin",
            "Teknik Veri",
            "Karar",
            "FINAL",
            "Setup",
            "Entry",
            "R/R",
        ]

        st.dataframe(
            deep_diag,
            use_container_width=True,
            hide_index=True,
        )


# ============================================================
# MOTOR AÇIKLAMASI
# ============================================================

with st.expander(
    "🧠 FINAL Trade Motoru Nasıl Karar Veriyor?"
):

    st.markdown(
        """
### 1. Coin Gücü Tek Başına AL Değildir

Bir coin teknik olarak çok güçlü olabilir fakat:

- giriş bölgesinden uzaksa,
- dirence yapışmışsa,
- RSI aşırı yüksekse,
- kovalama riski varsa,
- stop çok genişse,
- gerçek R/R kötüyse,
- piyasa breadth zayıfsa,

**AL verilmez.**

---

### 2. Setup Quality

Setup skoru birlikte değerlendirir:

- 15D + 1S trend uyumu
- Entry Quality
- Gerçek R/R
- Hacim teyidi
- Pullback / Breakout kalitesi
- VWAP
- RSI
- Chase riski

---

### 3. Entry Quality

Giriş kalitesi özellikle ölçer:

- EMA20 uzaklığı
- VWAP uzaklığı
- desteğe uzaklık
- dirence kalan alan
- RSI giriş bölgesi
- günlük range konumu
- chase riski

Bu nedenle güçlü ama fazla yükselmiş coin otomatik **AL** olmaz.

---

### 4. Gerçek Risk / Ödül

R/R mevcut fiyat üzerinden rastgele hedef üretmez.

Planlanan giriş, teknik destek, ATR, stop ve direnç bölgeleri birlikte kullanılır.

---

### 5. Market Context

FINAL skor şu piyasa verilerinden etkilenir:

- Market Score
- Market Breadth
- BTC 24s davranışı
- ETH 24s davranışı
- hacim ağırlıklı piyasa değişimi

Zayıf piyasada AL eşiği fiilen zorlaşır.

---

### 6. Coin Kaçırmama

Gizli:

- ilk 60 coin
- ilk 80 coin

limiti yoktur.

`Tarama Limiti = 0` ise uygun bütün coinler derin analize alınır.

Derin analize alınmayan coinler **Teşhis** sekmesinde nedenleriyle görünür.
        """
    )


st.caption(
    "⚠️ Bu sistem otomatik emir göndermez. "
    "AL/TUT/AZALT/SAT etiketleri teknik karar desteğidir; "
    "kesin getiri veya yatırım sonucu garanti etmez."
)
