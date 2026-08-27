from __future__ import annotations

import math
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf


# ============================================================
# BIST AI PRO - GUNLUK TRADE PRO V3
#
# Veri akisi:
# borsa.db/stocks -> BIST evreni
# Yahoo 1D       -> trend, momentum, goreceli guc, likidite
# Yahoo 15m      -> yalnizca en iyi adaylarda giris teyidi
# XU100.IS       -> piyasa rejimi
#
# Bu sayfa yatirim tavsiyesi degildir. Karar destek aracidir.
# ============================================================

st.set_page_config(
    page_title="BIST AI PRO - Günlük Trade V3",
    page_icon="⚡",
    layout="wide",
)

st.title("⚡ Günlük Trade Merkezi PRO V3")
st.caption(
    "Piyasa rejimi + göreceli güç + trend kalitesi + hacim + "
    "setup + gerçek risk/ödül + 15 dakikalık giriş teyidi"
)


# ============================================================
# SABITLER
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "borsa.db"
BENCHMARK = "XU100.IS"
DAILY_PERIOD = "6mo"

DEFAULT_MIN_LIQUIDITY = 30_000_000
DEFAULT_MIN_PRICE = 2.0
DEFAULT_MIN_SCORE = 58.0
DEFAULT_MIN_RR = 1.35
MAX_INTRADAY_CHECK = 60
MAX_BATCH_SIZE = 120


# ============================================================
# GENEL YARDIMCILAR
# ============================================================

def finite(value: Any, default: float = np.nan) -> float:
    try:
        if isinstance(value, pd.Series):
            value = value.iloc[-1]
        number = float(value)
        return number if np.isfinite(number) else default
    except (TypeError, ValueError, IndexError):
        return default


def clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return float(min(max(finite(value, low), low), high))


def linear_score(value: float, bad: float, good: float) -> float:
    """bad=0, good=100 olacak sekilde surekli skor."""
    value = finite(value, bad)
    if math.isclose(bad, good):
        return 50.0
    return clamp((value - bad) / (good - bad) * 100.0)


def normalize_ticker(value: Any) -> str | None:
    if value is None:
        return None
    ticker = str(value).upper().strip()
    for text in (".IS", " BIST", "$", " "):
        ticker = ticker.replace(text, "")
    ticker = ticker.rstrip(".")
    return ticker or None


def yahoo_symbol(ticker: str) -> str:
    return f"{normalize_ticker(ticker)}.IS"


def clean_ohlcv(data: pd.DataFrame | None) -> pd.DataFrame | None:
    if data is None or data.empty:
        return None
    data = data.copy()
    if isinstance(data.columns, pd.MultiIndex):
        # Tek sembollu yfinance cevabi.
        if "Close" in data.columns.get_level_values(0):
            data.columns = data.columns.get_level_values(0)
        elif "Close" in data.columns.get_level_values(-1):
            data.columns = data.columns.get_level_values(-1)
    required = ["Open", "High", "Low", "Close", "Volume"]
    if not all(column in data.columns for column in required):
        return None
    for column in required:
        data[column] = pd.to_numeric(data[column], errors="coerce")
    data = data.replace([np.inf, -np.inf], np.nan)
    data = data.dropna(subset=["High", "Low", "Close"])
    return data if len(data) else None


# ============================================================
# VERITABANI - SADECE HISSE EVRENI
# ============================================================

@st.cache_data(ttl=60, show_spinner=False)
def get_universe(db_mtime: float) -> list[str]:
    del db_mtime  # Dosya degisince cache anahtari degissin diye parametre.
    if not DB_PATH.exists():
        return []
    try:
        with sqlite3.connect(DB_PATH) as connection:
            tables = pd.read_sql_query(
                "SELECT name FROM sqlite_master WHERE type='table'", connection
            )["name"].tolist()
            if "stocks" not in tables:
                return []
            stocks = pd.read_sql_query("SELECT * FROM stocks", connection)
    except (sqlite3.Error, pd.errors.DatabaseError):
        return []

    candidates = ["symbol", "ticker", "code", "hisse", "hisse_kodu"]
    column = next((name for name in candidates if name in stocks.columns), None)
    if column is None:
        return []

    result: list[str] = []
    seen: set[str] = set()
    for raw in stocks[column].dropna():
        ticker = normalize_ticker(raw)
        if ticker and ticker not in seen:
            seen.add(ticker)
            result.append(ticker)
    return result


# ============================================================
# YAHOO TOPLU INDIRME
# ============================================================

def split_download(data: pd.DataFrame, symbols: list[str]) -> dict[str, pd.DataFrame]:
    result: dict[str, pd.DataFrame] = {}
    if data is None or data.empty:
        return result
    if not isinstance(data.columns, pd.MultiIndex):
        if len(symbols) == 1:
            cleaned = clean_ohlcv(data)
            if cleaned is not None:
                result[symbols[0]] = cleaned
        return result

    level0 = set(data.columns.get_level_values(0))
    level1 = set(data.columns.get_level_values(1))
    fields = {"Open", "High", "Low", "Close", "Volume"}

    for symbol in symbols:
        try:
            if symbol in level0 and fields.intersection(level1):
                part = data[symbol].copy()
            elif symbol in level1 and fields.intersection(level0):
                part = data.xs(symbol, axis=1, level=1).copy()
            else:
                continue
            cleaned = clean_ohlcv(part)
            if cleaned is not None:
                result[symbol] = cleaned
        except (KeyError, ValueError):
            continue
    return result


@st.cache_data(ttl=300, show_spinner=False)
def download_daily(tickers: tuple[str, ...]) -> dict[str, pd.DataFrame]:
    all_data: dict[str, pd.DataFrame] = {}
    symbols = [yahoo_symbol(ticker) for ticker in tickers]
    for start in range(0, len(symbols), MAX_BATCH_SIZE):
        group = symbols[start : start + MAX_BATCH_SIZE]
        try:
            raw = yf.download(
                group,
                period=DAILY_PERIOD,
                interval="1d",
                group_by="ticker",
                auto_adjust=False,
                progress=False,
                threads=True,
            )
            all_data.update(split_download(raw, group))
        except Exception:
            continue
    return all_data


@st.cache_data(ttl=300, show_spinner=False)
def download_benchmark() -> pd.DataFrame | None:
    try:
        return clean_ohlcv(
            yf.download(
                BENCHMARK,
                period=DAILY_PERIOD,
                interval="1d",
                auto_adjust=False,
                progress=False,
                threads=False,
            )
        )
    except Exception:
        return None


# ============================================================
# TEKNIK GOSTERGELER
# ============================================================

def add_indicators(data: pd.DataFrame) -> pd.DataFrame | None:
    data = clean_ohlcv(data)
    if data is None or len(data) < 70:
        return None
    df = data.copy()
    close, high, low, volume = df["Close"], df["High"], df["Low"], df["Volume"]

    for span in (5, 9, 20, 50):
        df[f"EMA{span}"] = close.ewm(span=span, adjust=False).mean()

    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    rs = gain / loss.replace(0, np.nan)
    df["RSI"] = (100 - 100 / (1 + rs)).clip(0, 100)

    previous_close = close.shift(1)
    true_range = pd.concat(
        [(high - low), (high - previous_close).abs(), (low - previous_close).abs()],
        axis=1,
    ).max(axis=1)
    df["ATR"] = true_range.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    df["ATR_PCT"] = df["ATR"] / close.replace(0, np.nan) * 100

    up_move = high.diff()
    down_move = -low.diff()
    plus_dm = pd.Series(np.where((up_move > down_move) & (up_move > 0), up_move, 0.0), index=df.index)
    minus_dm = pd.Series(np.where((down_move > up_move) & (down_move > 0), down_move, 0.0), index=df.index)
    atr14 = true_range.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    plus_di = 100 * plus_dm.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean() / atr14.replace(0, np.nan)
    minus_di = 100 * minus_dm.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean() / atr14.replace(0, np.nan)
    dx = ((plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)) * 100
    df["ADX"] = dx.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    df["PLUS_DI"] = plus_di
    df["MINUS_DI"] = minus_di

    df["VOL20"] = volume.rolling(20, min_periods=10).mean()
    df["VOL_RATIO"] = volume / df["VOL20"].replace(0, np.nan)
    df["TURNOVER20"] = (close * volume).rolling(20, min_periods=10).mean()
    df["RET1"] = close.pct_change(1) * 100
    df["RET5"] = close.pct_change(5) * 100
    df["RET20"] = close.pct_change(20) * 100
    df["EMA9_SLOPE"] = df["EMA9"].pct_change(5) * 100
    df["EMA20_SLOPE"] = df["EMA20"].pct_change(10) * 100
    df["PREV20_HIGH"] = high.shift(1).rolling(20, min_periods=15).max()
    df["PREV10_LOW"] = low.shift(1).rolling(10, min_periods=7).min()
    df["PREV20_LOW"] = low.shift(1).rolling(20, min_periods=15).min()
    df["BREAKOUT_PCT"] = (close / df["PREV20_HIGH"] - 1) * 100
    df["DIST_EMA9"] = (close / df["EMA9"] - 1) * 100
    df["RANGE_POS20"] = (close - df["PREV20_LOW"]) / (df["PREV20_HIGH"] - df["PREV20_LOW"]).replace(0, np.nan) * 100
    return df.replace([np.inf, -np.inf], np.nan)


# ============================================================
# PIYASA REJIMI
# ============================================================

def market_regime(benchmark: pd.DataFrame | None) -> dict[str, Any]:
    if benchmark is None:
        return {"label": "⚪ VERİ YOK", "score": np.nan, "multiplier": 0.90, "ret20": np.nan}
    df = add_indicators(benchmark)
    if df is None:
        return {"label": "⚪ VERİ YOK", "score": np.nan, "multiplier": 0.90, "ret20": np.nan}
    row = df.iloc[-1]
    price = finite(row["Close"])
    ema20 = finite(row["EMA20"])
    ema50 = finite(row["EMA50"])
    ret20 = finite(row["RET20"], 0)
    score = 0.0
    score += 30 if price > ema20 else 8
    score += 25 if ema20 > ema50 else 5
    score += linear_score(ret20, -8, 8) * 0.25
    score += linear_score(finite(row["RSI"], 50), 38, 62) * 0.20
    score = clamp(score)
    if score >= 72:
        return {"label": "🟢 POZİTİF", "score": score, "multiplier": 1.03, "ret20": ret20}
    if score >= 48:
        return {"label": "🟡 NÖTR", "score": score, "multiplier": 1.00, "ret20": ret20}
    return {"label": "🔴 NEGATİF", "score": score, "multiplier": 0.90, "ret20": ret20}


# ============================================================
# SETUP, RISK VE SKOR
# ============================================================

def identify_setup(row: pd.Series) -> tuple[str, float]:
    breakout = finite(row["BREAKOUT_PCT"], -99)
    volume_ratio = finite(row["VOL_RATIO"], 0)
    distance9 = finite(row["DIST_EMA9"], 99)
    close = finite(row["Close"])
    ema9 = finite(row["EMA9"])
    ema20 = finite(row["EMA20"])
    ret1 = finite(row["RET1"], 0)

    if -0.6 <= breakout <= 2.2 and volume_ratio >= 1.15 and close > ema9 > ema20:
        quality = 65 + linear_score(volume_ratio, 1.0, 2.0) * 0.25
        return "🚀 KIRILIM", clamp(quality)
    if -1.5 <= distance9 <= 2.5 and close >= ema20 and ema9 >= ema20 * 0.995:
        quality = 72 + linear_score(ret1, -2, 2) * 0.15
        return "↩️ PULLBACK", clamp(quality)
    if close > ema9 > ema20 and 0 <= distance9 <= 4:
        return "📈 TREND DEVAMI", clamp(62 + linear_score(finite(row["ADX"], 15), 15, 35) * 0.22)
    return "⚪ BELİRSİZ", 35.0


def risk_plan(df: pd.DataFrame, minimum_rr: float) -> dict[str, float]:
    row = df.iloc[-1]
    price = finite(row["Close"])
    atr = finite(row["ATR"], price * 0.025)
    ema20 = finite(row["EMA20"], price - atr)
    swing_low = finite(df["Low"].iloc[-11:-1].min(), price - atr)

    # Stop ne cok dar ne de asiri genis olsun.
    technical_stop = min(ema20, swing_low) - 0.15 * atr
    atr_stop = price - 1.35 * atr
    stop = max(technical_stop, atr_stop)
    stop = min(stop, price - 0.60 * atr)
    stop = max(stop, price * 0.90)
    risk = price - stop

    previous_highs = df["High"].iloc[-61:-1]
    valid_resistance = previous_highs[previous_highs > price * 1.003]
    resistance = finite(valid_resistance.min(), np.nan) if len(valid_resistance) else np.nan
    target_2r = price + risk * 2.0
    if np.isfinite(resistance) and resistance >= price + risk * minimum_rr:
        target = min(target_2r, resistance)
    else:
        target = target_2r
    rr = (target - price) / risk if risk > 0 else 0
    stop_pct = risk / price * 100 if price > 0 else np.nan
    return {"stop": stop, "target": target, "rr": rr, "stop_pct": stop_pct, "resistance": resistance}


def analyze_stock(
    ticker: str,
    raw: pd.DataFrame,
    benchmark_ret20: float,
    regime: dict[str, Any],
    min_liquidity: float,
    min_price: float,
    minimum_rr: float,
) -> tuple[dict[str, Any] | None, str]:
    df = add_indicators(raw)
    if df is None:
        return None, "veri_yetersiz"
    row = df.iloc[-1]
    price = finite(row["Close"])
    liquidity = finite(row["TURNOVER20"], 0)
    if price < min_price:
        return None, "fiyat"
    if liquidity < min_liquidity:
        return None, "likidite"

    ema9, ema20, ema50 = finite(row["EMA9"]), finite(row["EMA20"]), finite(row["EMA50"])
    rsi, adx = finite(row["RSI"], 50), finite(row["ADX"], 0)
    plus_di, minus_di = finite(row["PLUS_DI"], 0), finite(row["MINUS_DI"], 0)
    ret5, ret20 = finite(row["RET5"], 0), finite(row["RET20"], 0)
    volume_ratio = finite(row["VOL_RATIO"], 0)
    atr_pct = finite(row["ATR_PCT"], 0)
    distance9 = finite(row["DIST_EMA9"], 99)
    rs20 = ret20 - finite(benchmark_ret20, 0)

    trend = 0.0
    trend += 28 if price > ema20 else linear_score(price / ema20 - 1, -0.04, 0) * 0.20
    trend += 24 if ema9 > ema20 else 5
    trend += 22 if ema20 > ema50 else 5
    trend += linear_score(finite(row["EMA20_SLOPE"], -3), -2, 5) * 0.16
    trend += (linear_score(adx, 12, 35) * 0.10) if plus_di > minus_di else 0
    trend = clamp(trend)

    momentum = clamp(
        linear_score(ret5, -4, 8) * 0.35
        + linear_score(rs20, -8, 12) * 0.40
        + linear_score(rsi, 42, 67) * 0.25
    )
    volume = clamp(linear_score(volume_ratio, 0.55, 1.80))
    relative_strength = clamp(linear_score(rs20, -10, 15))

    if 1.2 <= atr_pct <= 5.5:
        volatility = 100.0
    elif 0.8 <= atr_pct < 1.2:
        volatility = linear_score(atr_pct, 0.5, 1.2)
    elif 5.5 < atr_pct <= 8.0:
        volatility = linear_score(atr_pct, 9.0, 5.5)
    else:
        volatility = 25.0

    setup, setup_quality = identify_setup(row)
    plan = risk_plan(df, minimum_rr)
    rr_quality = linear_score(plan["rr"], 0.8, 2.2)

    raw_score = (
        trend * 0.25
        + relative_strength * 0.18
        + momentum * 0.14
        + setup_quality * 0.17
        + volume * 0.10
        + volatility * 0.06
        + rr_quality * 0.10
    )

    penalties: list[str] = []
    penalty = 0.0
    if distance9 > 5.5:
        penalty += min(18.0, (distance9 - 5.5) * 2.5)
        penalties.append("EMA9'dan uzak")
    if rsi >= 76:
        penalty += 12.0
        penalties.append("RSI aşırı alım")
    if finite(row["RET1"], 0) > 7:
        penalty += 10.0
        penalties.append("günlük yükseliş aşırı")
    if volume_ratio < 0.60:
        penalty += 8.0
        penalties.append("hacim zayıf")
    if plan["stop_pct"] > 6.5:
        penalty += 7.0
        penalties.append("stop mesafesi geniş")
    if plan["rr"] < minimum_rr:
        penalty += 12.0
        penalties.append("R/R yetersiz")
    if setup == "⚪ BELİRSİZ":
        penalty += 8.0
        penalties.append("net setup yok")

    score = clamp((raw_score - penalty) * finite(regime["multiplier"], 0.9))
    return {
        "Hisse": ticker,
        "Fiyat": price,
        "Setup": setup,
        "Ana Skor": round(score, 1),
        "Trend": round(trend, 1),
        "Göreceli Güç": round(relative_strength, 1),
        "RS 20G %": round(rs20, 2),
        "Momentum": round(momentum, 1),
        "Setup Kalitesi": round(setup_quality, 1),
        "ADX": round(adx, 1),
        "RSI": round(rsi, 1),
        "Hacim Oranı": round(volume_ratio, 2),
        "Likidite": liquidity,
        "ATR %": round(atr_pct, 2),
        "EMA9 Uzaklık %": round(distance9, 2),
        "5G %": round(ret5, 2),
        "20G %": round(ret20, 2),
        "Stop": plan["stop"],
        "Hedef": plan["target"],
        "R/R": round(plan["rr"], 2),
        "Risk %": round(plan["stop_pct"], 2),
        "15D Skor": np.nan,
        "15D VWAP": "KONTROL EDİLMEDİ",
        "Final Skor": round(score, 1),
        "Ceza": round(penalty, 1),
        "Uyarılar": ", ".join(penalties) if penalties else "—",
        "Karar": "BEKLENİYOR",
    }, "ok"


# ============================================================
# 15 DAKIKALIK GIRIS TEYIDI
# ============================================================

@st.cache_data(ttl=180, show_spinner=False)
def intraday_confirmation(ticker: str) -> dict[str, Any] | None:
    try:
        data = clean_ohlcv(
            yf.download(
                yahoo_symbol(ticker),
                period="5d",
                interval="15m",
                auto_adjust=False,
                progress=False,
                threads=False,
            )
        )
        if data is None or len(data) < 35:
            return None
        df = data.copy()
        close, volume = df["Close"], df["Volume"]
        df["EMA9"] = close.ewm(span=9, adjust=False).mean()
        df["EMA20"] = close.ewm(span=20, adjust=False).mean()

        # Her seans yeniden baslayan intraday VWAP.
        session = pd.Series(df.index.date, index=df.index)
        typical = (df["High"] + df["Low"] + df["Close"]) / 3
        cumulative_pv = (typical * volume).groupby(session).cumsum()
        cumulative_volume = volume.groupby(session).cumsum().replace(0, np.nan)
        df["VWAP"] = cumulative_pv / cumulative_volume
        df["VOL20"] = volume.rolling(20, min_periods=10).mean()
        df["VR"] = volume / df["VOL20"].replace(0, np.nan)
        last, previous = df.iloc[-1], df.iloc[-2]

        score = 0.0
        score += 28 if last["EMA9"] > last["EMA20"] else 5
        score += 25 if last["Close"] > last["EMA9"] else 8
        score += 25 if last["Close"] > last["VWAP"] else 5
        score += linear_score(finite(last["VR"], 0), 0.5, 1.8) * 0.12
        score += 10 if last["Close"] > previous["Close"] else 2
        return {
            "score": clamp(score),
            "vwap": "ÜSTÜNDE" if last["Close"] >= last["VWAP"] else "ALTINDA",
        }
    except Exception:
        return None


def finalize(row: dict[str, Any], regime: dict[str, Any], minimum_rr: float) -> dict[str, Any]:
    intraday = intraday_confirmation(str(row["Hisse"]))
    if intraday is None:
        row["15D Skor"] = np.nan
        row["15D VWAP"] = "VERİ YOK"
        final_score = float(row["Ana Skor"])  # Veri yok diye sahte 50 ekleme.
    else:
        row["15D Skor"] = round(float(intraday["score"]), 1)
        row["15D VWAP"] = str(intraday["vwap"])
        final_score = float(row["Ana Skor"]) * 0.82 + float(intraday["score"]) * 0.18
        if intraday["vwap"] == "ALTINDA":
            final_score -= 4

    final_score = clamp(final_score)
    row["Final Skor"] = round(final_score, 1)
    warnings = str(row["Uyarılar"])
    rr = float(row["R/R"])

    if "EMA9'dan uzak" in warnings or "RSI aşırı alım" in warnings:
        decision = "🟠 KOVALAMA / GERİ ÇEKİLME BEKLE"
    elif regime["label"] == "🔴 NEGATİF" and final_score < 78:
        decision = "🔴 PİYASA RİSKİ / İŞLEM YOK"
    elif final_score >= 78 and rr >= max(1.50, minimum_rr) and row["15D VWAP"] == "ÜSTÜNDE":
        decision = "🟢 A SINIFI TRADE"
    elif final_score >= 68 and rr >= minimum_rr:
        decision = "🟡 B SINIFI / TEYİTLE GİR"
    elif final_score >= 58:
        decision = "🔵 C SINIFI / İZLE"
    else:
        decision = "⚪ İŞLEM YOK"
    row["Karar"] = decision
    return row


# ============================================================
# ARAYUZ
# ============================================================

mtime = DB_PATH.stat().st_mtime if DB_PATH.exists() else 0.0
universe = get_universe(mtime)
if not universe:
    st.error("`borsa.db/stocks` tablosunda kullanılabilir hisse evreni bulunamadı.")
    st.stop()

with st.expander("⚙️ Profesyonel Tarama Ayarları", expanded=False):
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        min_liquidity = st.number_input(
            "Min. 20G likidite (TL)", 1_000_000, 500_000_000,
            DEFAULT_MIN_LIQUIDITY, 5_000_000, key="trade_v3_min_liquidity"
        )
    with c2:
        min_price = st.number_input(
            "Min. fiyat", 0.5, 1_000.0, DEFAULT_MIN_PRICE, 0.5,
            key="trade_v3_min_price"
        )
    with c3:
        pool_score = st.slider(
            "Havuz skoru", 40.0, 75.0, DEFAULT_MIN_SCORE, 1.0,
            key="trade_v3_pool_score"
        )
    with c4:
        minimum_rr = st.slider(
            "Minimum R/R", 1.0, 2.5, DEFAULT_MIN_RR, 0.05,
            key="trade_v3_min_rr"
        )
    with c5:
        max_results = st.slider(
            "Gösterilecek", 5, 50, 20, 5, key="trade_v3_max_results"
        )
    st.info(
        "Önerilen başlangıç: likidite 30 Mn TL, havuz 58, minimum R/R 1.35. "
        "Piyasa negatifken sistem otomatik olarak daha seçici davranır."
    )

benchmark = download_benchmark()
regime = market_regime(benchmark)

m1, m2, m3, m4 = st.columns(4)
m1.metric("BIST Evreni", len(universe))
m2.metric("Piyasa Rejimi", regime["label"])
m3.metric("Piyasa Skoru", "—" if not np.isfinite(regime["score"]) else f"{regime['score']:.1f}")
m4.metric("BIST 20G", "—" if not np.isfinite(regime["ret20"]) else f"%{regime['ret20']:.2f}")

if st.button(
    "⚡ PROFESYONEL GÜNLÜK TRADE TARAMASINI BAŞLAT",
    type="primary",
    use_container_width=True,
    key="trade_v3_start",
):
    progress = st.progress(0)
    status = st.empty()
    status.info("Günlük fiyat verileri toplu indiriliyor…")
    daily_map = download_daily(tuple(universe))
    if not daily_map:
        st.error("Yahoo Finance günlük verileri alınamadı.")
        st.stop()

    counters = {"veri": 0, "fiyat": 0, "likidite": 0, "havuz": 0, "intra": 0}
    results: list[dict[str, Any]] = []
    for index, ticker in enumerate(universe, start=1):
        raw = daily_map.get(yahoo_symbol(ticker))
        if raw is None:
            continue
        counters["veri"] += 1
        result, reason = analyze_stock(
            ticker, raw, regime["ret20"], regime,
            float(min_liquidity), float(min_price), float(minimum_rr)
        )
        if result is None:
            if reason in counters:
                counters[reason] += 1
            continue
        if float(result["Ana Skor"]) >= float(pool_score):
            results.append(result)
            counters["havuz"] += 1
        progress.progress(min(70, int(index / max(len(universe), 1) * 70)))

    if not results:
        progress.empty()
        status.empty()
        st.warning("Seçili eşiklerde trade havuzu oluşmadı. Havuz skorunu 3–5 puan azaltabilirsiniz.")
        st.stop()

    pool = pd.DataFrame(results).sort_values("Ana Skor", ascending=False).reset_index(drop=True)
    check_count = min(MAX_INTRADAY_CHECK, len(pool))
    for count in range(check_count):
        ticker = str(pool.at[count, "Hisse"])
        status.info(f"15 dakikalık giriş teyidi: {ticker} ({count + 1}/{check_count})")
        updated = finalize(pool.loc[count].to_dict(), regime, float(minimum_rr))
        for column, value in updated.items():
            pool.at[count, column] = value
        if pd.notna(updated["15D Skor"]):
            counters["intra"] += 1
        progress.progress(70 + int((count + 1) / max(check_count, 1) * 30))

    # 15D kontrol edilmeyenler: ana skora gore izleme karari.
    for index in range(check_count, len(pool)):
        score = float(pool.at[index, "Ana Skor"])
        pool.at[index, "Karar"] = "🔵 C SINIFI / İZLE" if score >= 58 else "⚪ İŞLEM YOK"

    pool = pool.sort_values(["Final Skor", "R/R"], ascending=[False, False]).reset_index(drop=True)
    progress.empty()
    status.empty()

    a_count = int(pool["Karar"].eq("🟢 A SINIFI TRADE").sum())
    b_count = int(pool["Karar"].eq("🟡 B SINIFI / TEYİTLE GİR").sum())
    c_count = int(pool["Karar"].eq("🔵 C SINIFI / İZLE").sum())
    d1, d2, d3, d4, d5 = st.columns(5)
    d1.metric("Günlük Veri", counters["veri"])
    d2.metric("Trade Havuzu", counters["havuz"])
    d3.metric("🟢 A", a_count)
    d4.metric("🟡 B", b_count)
    d5.metric("🔵 C", c_count)

    st.subheader("🏆 En İyi Trade Adayları")
    display_columns = [
        "Hisse", "Fiyat", "Setup", "Final Skor", "Trend", "Göreceli Güç",
        "RS 20G %", "ADX", "RSI", "Hacim Oranı", "15D Skor", "15D VWAP",
        "Stop", "Hedef", "R/R", "Risk %", "Karar",
    ]
    st.dataframe(
        pool.head(int(max_results))[display_columns],
        use_container_width=True,
        hide_index=True,
        column_config={
            "Fiyat": st.column_config.NumberColumn(format="%.2f"),
            "Stop": st.column_config.NumberColumn(format="%.2f"),
            "Hedef": st.column_config.NumberColumn(format="%.2f"),
            "Final Skor": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.1f"),
            "Trend": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.1f"),
            "Göreceli Güç": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.1f"),
        },
    )

    st.subheader("🟢 İşlem Planı Oluşanlar")
    actionable = pool[pool["Karar"].isin(["🟢 A SINIFI TRADE", "🟡 B SINIFI / TEYİTLE GİR"])].copy()
    if actionable.empty:
        st.info("Bugün A veya B sınıfı işlem planı oluşmadı. İşlem yapmamak da profesyonel bir karardır.")
    else:
        st.dataframe(
            actionable.head(int(max_results))[
                ["Hisse", "Setup", "Fiyat", "Stop", "Hedef", "R/R", "Final Skor", "15D VWAP", "Karar"]
            ],
            use_container_width=True,
            hide_index=True,
        )

    with st.expander("🔬 Ayrıntılı teşhis ve uyarılar"):
        st.dataframe(
            pool.head(int(max_results))[
                ["Hisse", "Ana Skor", "Ceza", "Uyarılar", "ATR %", "EMA9 Uzaklık %", "5G %", "20G %", "Likidite"]
            ],
            use_container_width=True,
            hide_index=True,
        )
        st.caption(
            f"Tarama zamanı: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')} | "
            f"Gerçek 15D veri: {counters['intra']}/{check_count}. "
            "15D veri yoksa sisteme yapay 50 puan eklenmez."
        )

st.warning(
    "Bu ekran otomatik karar destek aracıdır; yatırım tavsiyesi değildir. "
    "Emir vermeden önce KAP haberleri, açılış gap'i, devre kesici ve güncel kademe kontrol edilmelidir."
)
