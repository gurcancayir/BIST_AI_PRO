"""
BIST AI PRO - DÖVİZ VE ÇAPRAZ KUR ANALİZ MOTORU V1

Sinyal üretir; aracı kuruma emir göndermez. Yahoo Finance verileri gecikmeli
olabilir. AL ve SAT planları ayrı stop/hedef yönleriyle hesaplanır.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional

import numpy as np
import pandas as pd
import yfinance as yf


PAIR_SYMBOLS: Dict[str, str] = {
    "USD/TRY": "USDTRY=X",
    "EUR/TRY": "EURTRY=X",
    "GBP/TRY": "GBPTRY=X",
    "JPY/TRY": "JPYTRY=X",
    "EUR/USD": "EURUSD=X",
    "GBP/USD": "GBPUSD=X",
    "EUR/GBP": "EURGBP=X",
    "USD/JPY": "USDJPY=X",
    "EUR/JPY": "EURJPY=X",
    "GBP/JPY": "GBPJPY=X",
}

DEFAULT_PAIRS = tuple(PAIR_SYMBOLS)
MIN_DAILY_ROWS = 120
MIN_HOURLY_ROWS = 180


@dataclass
class ForexAnalysisResult:
    ok: bool
    error: Optional[str]
    data: pd.DataFrame
    result: Dict[str, Any]


def _clean(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    out = df.copy()
    if isinstance(out.columns, pd.MultiIndex):
        out.columns = [c[0] if isinstance(c, tuple) else c for c in out.columns]
    required = ["Open", "High", "Low", "Close"]
    if any(c not in out.columns for c in required):
        return pd.DataFrame()
    for column in required + ["Volume"]:
        if column in out.columns:
            out[column] = pd.to_numeric(out[column], errors="coerce")
    if "Volume" not in out.columns:
        out["Volume"] = 0.0
    return (
        out.dropna(subset=required)
        .loc[lambda x: ~x.index.duplicated(keep="last")]
        .sort_index()
    )


def _fetch(symbol: str, period: str, interval: str) -> pd.DataFrame:
    try:
        return _clean(
            yf.Ticker(symbol).history(
                period=period,
                interval=interval,
                auto_adjust=False,
                actions=False,
            )
        )
    except Exception:
        return pd.DataFrame()


def _resample_4h(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    try:
        return _clean(
            df.resample("4h").agg(
                {
                    "Open": "first",
                    "High": "max",
                    "Low": "min",
                    "Close": "last",
                    "Volume": "sum",
                }
            )
        )
    except Exception:
        return pd.DataFrame()


def _ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def _rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return (100 - 100 / (1 + rs)).replace([np.inf, -np.inf], np.nan)


def _atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    previous = df["Close"].shift(1)
    true_range = pd.concat(
        [
            df["High"] - df["Low"],
            (df["High"] - previous).abs(),
            (df["Low"] - previous).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return true_range.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()


def _indicators(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    close = out["Close"]
    for period in (9, 20, 50, 100, 200):
        out[f"EMA{period}"] = _ema(close, period)
    out["RSI"] = _rsi(close)
    out["ATR"] = _atr(out)
    ema12 = _ema(close, 12)
    ema26 = _ema(close, 26)
    out["MACD"] = ema12 - ema26
    out["MACD_SIGNAL"] = _ema(out["MACD"], 9)
    out["MOMENTUM_10"] = close.pct_change(10) * 100
    out["MOMENTUM_20"] = close.pct_change(20) * 100
    out["CHANGE_1"] = close.pct_change() * 100
    out["VOLATILITY_20"] = close.pct_change().rolling(20).std() * np.sqrt(252) * 100
    return out.replace([np.inf, -np.inf], np.nan)


def _timeframe_score(row: pd.Series) -> Dict[str, float]:
    trend = 50.0
    for condition, weight in (
        (row["Close"] > row["EMA9"], 8),
        (row["EMA9"] > row["EMA20"], 12),
        (row["EMA20"] > row["EMA50"], 14),
        (row["EMA50"] > row["EMA100"], 10),
        (row["EMA100"] > row["EMA200"], 6),
    ):
        trend += weight if condition else -weight

    momentum = 50.0
    for condition, weight in (
        (row["MOMENTUM_10"] > 0, 15),
        (row["MOMENTUM_20"] > 0, 15),
        (row["MACD"] > row["MACD_SIGNAL"], 12),
    ):
        momentum += weight if condition else -weight
    rsi = float(row["RSI"])
    if 52 <= rsi <= 68:
        momentum += 8
    elif 32 <= rsi <= 48:
        momentum -= 8

    technical = 50.0
    technical += 20 if row["Close"] > row["EMA20"] else -20
    technical += 15 if row["Close"] > row["EMA50"] else -15
    technical += 15 if row["MACD"] > 0 else -15
    return {
        "trend": float(np.clip(trend, 0, 100)),
        "momentum": float(np.clip(momentum, 0, 100)),
        "technical": float(np.clip(technical, 0, 100)),
    }


def _levels(df: pd.DataFrame, current: float, atr: float, direction: str) -> Dict[str, float]:
    recent = df.tail(80)
    lows = recent["Low"].rolling(5, center=True).min()
    highs = recent["High"].rolling(5, center=True).max()
    supports = sorted({float(x) for x in lows.dropna() if x < current}, reverse=True)
    resistances = sorted({float(x) for x in highs.dropna() if x > current})
    support = supports[0] if supports else current - 1.2 * atr
    resistance = resistances[0] if resistances else current + 1.2 * atr

    if direction == "AL":
        stop = min(support - 0.15 * atr, current - 0.8 * atr)
        risk = max(current - stop, 0.5 * atr)
        technical_targets = [x for x in resistances if x >= current + risk]
        target1 = technical_targets[0] if technical_targets else current + 1.6 * risk
        target2 = technical_targets[1] if len(technical_targets) > 1 else current + 2.5 * risk
        rr1 = (target1 - current) / risk
        rr2 = (target2 - current) / risk
    elif direction == "SAT":
        stop = max(resistance + 0.15 * atr, current + 0.8 * atr)
        risk = max(stop - current, 0.5 * atr)
        technical_targets = [x for x in supports if x <= current - risk]
        target1 = technical_targets[0] if technical_targets else current - 1.6 * risk
        target2 = technical_targets[1] if len(technical_targets) > 1 else current - 2.5 * risk
        rr1 = (current - target1) / risk
        rr2 = (current - target2) / risk
    else:
        stop = np.nan
        target1 = np.nan
        target2 = np.nan
        rr1 = np.nan
        rr2 = np.nan

    return {
        "support": support,
        "resistance": resistance,
        "entry": current,
        "stop": stop,
        "target1": target1,
        "target2": target2,
        "rr1": rr1,
        "rr2": rr2,
    }


def _decision(score: float, rsi: float, price: float, ema20: float, atr: float) -> Dict[str, Any]:
    atr_distance = abs(price - ema20) / atr if atr > 0 else 0.0
    if score >= 76:
        if rsi >= 74 or atr_distance > 1.8:
            return {"direction": "AL", "decision": "🟡 AL İÇİN GERİ ÇEKİLME BEKLE", "tradeable": False,
                    "reason": "Yükseliş güçlü; mevcut fiyat aşırı veya EMA20'den fazla uzak."}
        return {"direction": "AL", "decision": "🟢 GÜÇLÜ AL", "tradeable": True,
                "reason": "Günlük, 4 saatlik ve 1 saatlik yapı yükselişi birlikte destekliyor."}
    if score >= 62:
        return {"direction": "AL", "decision": "🟢 KADEMELİ AL", "tradeable": True,
                "reason": "Yükseliş yönü avantajlı; teyit ve risk sınırı korunmalı."}
    if score <= 24:
        if rsi <= 26 or atr_distance > 1.8:
            return {"direction": "SAT", "decision": "🟡 SAT İÇİN TEPKİ BEKLE", "tradeable": False,
                    "reason": "Düşüş güçlü; mevcut fiyat aşırı satım veya EMA20'den fazla uzak."}
        return {"direction": "SAT", "decision": "🔴 GÜÇLÜ SAT", "tradeable": True,
                "reason": "Günlük, 4 saatlik ve 1 saatlik yapı düşüşü birlikte destekliyor."}
    if score <= 38:
        return {"direction": "SAT", "decision": "🔴 KADEMELİ SAT", "tradeable": True,
                "reason": "Düşüş yönü avantajlı; teyit ve risk sınırı korunmalı."}
    return {"direction": "BEKLE", "decision": "🟡 İŞLEM YOK / TEYİT BEKLE", "tradeable": False,
            "reason": "Alıcılar ile satıcılar arasında yeterli yön üstünlüğü oluşmadı."}


def _digits(pair: str) -> int:
    if pair.endswith("/JPY"):
        return 3
    if pair.endswith("/TRY"):
        return 4
    return 5


def analyze_forex(pair: str, period: str = "2y") -> ForexAnalysisResult:
    pair = str(pair).upper().strip()
    symbol = PAIR_SYMBOLS.get(pair)
    if not symbol:
        return ForexAnalysisResult(False, f"Desteklenmeyen parite: {pair}", pd.DataFrame(), {})

    daily = _fetch(symbol, period if period in {"1y", "2y", "5y"} else "2y", "1d")
    hourly = _fetch(symbol, "60d", "1h")
    four_hour = _resample_4h(hourly)
    if len(daily) < MIN_DAILY_ROWS or len(hourly) < MIN_HOURLY_ROWS or len(four_hour) < 80:
        return ForexAnalysisResult(
            False,
            f"Yetersiz veri: günlük={len(daily)}, 1s={len(hourly)}, 4s={len(four_hour)}.",
            pd.DataFrame(),
            {},
        )

    frames = {"daily": _indicators(daily), "h4": _indicators(four_hour), "h1": _indicators(hourly)}
    rows = {name: frame.iloc[-1] for name, frame in frames.items()}
    scores = {name: _timeframe_score(row) for name, row in rows.items()}
    weights = {"daily": 0.45, "h4": 0.35, "h1": 0.20}
    trend_score = sum(scores[k]["trend"] * weights[k] for k in weights)
    momentum_score = sum(scores[k]["momentum"] * weights[k] for k in weights)
    technical_score = sum(scores[k]["technical"] * weights[k] for k in weights)
    general_score = trend_score * 0.50 + momentum_score * 0.30 + technical_score * 0.20

    row = rows["daily"]
    current = float(row["Close"])
    atr = float(row["ATR"])
    decision = _decision(general_score, float(row["RSI"]), current, float(row["EMA20"]), atr)
    levels = _levels(frames["daily"], current, atr, decision["direction"])
    if not decision["tradeable"]:
        levels.update({"entry": np.nan, "stop": np.nan, "target1": np.nan, "target2": np.nan, "rr1": np.nan, "rr2": np.nan})

    bullish = {
        "Günlük trend yukarı": scores["daily"]["trend"] >= 60,
        "4 saatlik trend yukarı": scores["h4"]["trend"] >= 60,
        "1 saatlik trend yukarı": scores["h1"]["trend"] >= 60,
        "Günlük MACD olumlu": row["MACD"] > row["MACD_SIGNAL"],
        "RSI alım için uygun": 45 <= row["RSI"] < 74,
    }
    bearish = {
        "Günlük trend aşağı": scores["daily"]["trend"] <= 40,
        "4 saatlik trend aşağı": scores["h4"]["trend"] <= 40,
        "1 saatlik trend aşağı": scores["h1"]["trend"] <= 40,
        "Günlük MACD olumsuz": row["MACD"] < row["MACD_SIGNAL"],
        "RSI satış için uygun": 26 < row["RSI"] <= 55,
    }

    result = {
        "pair": pair,
        "symbol": symbol,
        "price": current,
        "digits": _digits(pair),
        "change_1d": float(row["CHANGE_1"]),
        "general_score": round(general_score, 1),
        "trend_score": round(trend_score, 1),
        "momentum_score": round(momentum_score, 1),
        "technical_score": round(technical_score, 1),
        "daily_score": round(scores["daily"]["trend"], 1),
        "h4_score": round(scores["h4"]["trend"], 1),
        "h1_score": round(scores["h1"]["trend"], 1),
        "rsi": float(row["RSI"]),
        "ema9": float(row["EMA9"]),
        "ema20": float(row["EMA20"]),
        "ema50": float(row["EMA50"]),
        "ema100": float(row["EMA100"]),
        "ema200": float(row["EMA200"]),
        "macd": float(row["MACD"]),
        "macd_signal": float(row["MACD_SIGNAL"]),
        "momentum_20": float(row["MOMENTUM_20"]),
        "atr": atr,
        "volatility_20": float(row["VOLATILITY_20"]),
        "direction": decision["direction"],
        "decision": decision["decision"],
        "reason": decision["reason"],
        "tradeable": decision["tradeable"],
        "buy_checks": bullish,
        "sell_checks": bearish,
        "buy_count": sum(bullish.values()),
        "sell_count": sum(bearish.values()),
        "support": levels["support"],
        "resistance": levels["resistance"],
        "entry": levels["entry"],
        "trade_stop": levels["stop"],
        "target1": levels["target1"],
        "target2": levels["target2"],
        "risk_reward_target1": levels["rr1"],
        "risk_reward_target2": levels["rr2"],
        "data_source": f"Yahoo Finance: {symbol}",
        "data_timestamp": str(daily.index[-1]),
        "data_status": "Historical OHLC; gerçek zaman ve işlem fiyatı garanti edilmez.",
    }
    return ForexAnalysisResult(True, None, frames["daily"], result)


def scan_forex(pairs: Iterable[str] = DEFAULT_PAIRS, period: str = "2y") -> List[ForexAnalysisResult]:
    return [analyze_forex(pair, period=period) for pair in pairs]

