# ============================================================
# BIST AI PRO
# 00_Veri_Guncelleme.py
#
# BIST 500 VERİ GÜNCELLEME MOTORU — FINAL
#
# AKIŞ:
# BIST 500
#    ↓
# bist500_universe
#    ↓
# Yahoo Finance
#    ↓
# stock_prices
#    ↓
# technical_analysis
#    ↓
# dynamic_portfolio_cache  ← HER BAŞARILI GÜNCELLEMEDE YENİLENİR
#    ↓
# Dinamik Portföy
#
# ÖNEMLİ:
# - Gerçek tarama evreni bist500_universe'dur.
# - stocks yalnızca senkronizasyon tablosudur.
# - Teknik veri Yahoo Finance'tan gelir.
# - KAP/financial_scores verisi bu motor tarafından silinmez.
# - dynamic_portfolio_cache içindeki Fundamental/KAP alanı korunur.
# - Teknik snapshot değiştiğinde cache'teki Teknik/Momentum/Trend/
#   Fiyat vb. alanlar yeniden yazılır ve Genel Skor yeniden hesaplanır.
# - Başarısız/eksik bir güncelleme eski cache'i bozmaz.
# ============================================================

import json
import sqlite3
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf


# ============================================================
# SAYFA
# ============================================================

st.set_page_config(
    page_title="BIST AI PRO - Veri Güncelleme",
    page_icon="🔄",
    layout="wide",
)


# ============================================================
# DOSYA / AYARLAR
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "borsa.db"

MIN_BARS = 220

PERIODS = {
    "1 Yıl": "1y",
    "2 Yıl": "2y",
    "5 Yıl": "5y",
}

DEFAULT_PAUSE = 0.10

# Dinamik Portföy ile aynı ağırlıklar.
W_TECH = 0.50
W_FUND = 0.20
W_MOM = 0.15
W_MARKET = 0.15

CACHE_UNIVERSE = "BIST500"


# ============================================================
# DB
# ============================================================

def get_connection():
    conn = sqlite3.connect(
        DB_PATH,
        check_same_thread=False,
        timeout=60,
    )
    conn.row_factory = sqlite3.Row
    return conn


def table_exists(conn, table_name):
    row = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table' AND name = ?
        """,
        (table_name,),
    ).fetchone()
    return row is not None


def table_columns(conn, table_name):
    if not table_exists(conn, table_name):
        return []
    return [
        row["name"]
        for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    ]


def normalize_symbol(symbol):
    symbol = str(symbol or "").upper().strip()
    if symbol.endswith(".IS"):
        symbol = symbol[:-3]
    return symbol


def safe_float(value, default=50.0):
    try:
        value = float(value)
        if np.isfinite(value):
            return value
    except Exception:
        pass
    return default


def clamp(value, low=0.0, high=100.0, default=50.0):
    value = safe_float(value, default)
    return float(np.clip(value, low, high))


# ============================================================
# VERİTABANI HAZIRLIK
# ============================================================

def ensure_database():
    conn = get_connection()
    try:
        cur = conn.cursor()

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS stocks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT UNIQUE NOT NULL,
                company TEXT,
                sector TEXT,
                industry TEXT,
                market_cap REAL,
                currency TEXT DEFAULT 'TRY',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS bist500_universe (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT UNIQUE NOT NULL,
                company TEXT,
                sector TEXT,
                industry TEXT,
                active INTEGER DEFAULT 1,
                updated_at TEXT
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS stock_prices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                price_date TEXT,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(symbol, price_date)
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS technical_analysis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                analysis_date TEXT,
                price REAL,
                ema20 REAL,
                ema50 REAL,
                ema200 REAL,
                rsi REAL,
                macd REAL,
                signal REAL,
                bollinger_upper REAL,
                bollinger_lower REAL,
                atr REAL,
                momentum REAL,
                volatility REAL,
                support REAL,
                resistance REAL,
                trend TEXT,
                trend_strength REAL,
                ai_score REAL,
                radar_score REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(symbol, analysis_date)
            )
            """
        )

        existing = set(table_columns(conn, "technical_analysis"))
        extra_columns = {
            "score": "REAL",
            "technical_score": "REAL",
            "momentum_60_score": "REAL",
            "momentum_score": "REAL",
            "trend_score": "REAL",
            "volume_ratio": "REAL",
            "year_return": "REAL",
            "return_1y": "REAL",
            "change": "REAL",
            "change_percent": "REAL",
            "last_price": "REAL",
            "close": "REAL",
            "updated_at": "TEXT",
        }
        for column, dtype in extra_columns.items():
            if column not in existing:
                cur.execute(
                    f"ALTER TABLE technical_analysis ADD COLUMN {column} {dtype}"
                )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS data_update_status (
                id INTEGER PRIMARY KEY,
                status TEXT,
                last_attempt_at TEXT,
                last_success_at TEXT,
                source TEXT,
                period TEXT,
                universe TEXT,
                symbols_total INTEGER DEFAULT 0,
                symbols_success INTEGER DEFAULT 0,
                symbols_failed INTEGER DEFAULT 0,
                price_rows INTEGER DEFAULT 0,
                technical_rows INTEGER DEFAULT 0,
                error TEXT
            )
            """
        )

        # --------------------------------------------------------
        # DİNAMİK PORTFÖY CACHE
        # --------------------------------------------------------
        # Mevcut uygulamanın beklediği şema:
        # symbol + universe benzersiz.
        # --------------------------------------------------------
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS dynamic_portfolio_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                universe TEXT NOT NULL,
                market_score REAL DEFAULT 50,
                analysis_json TEXT NOT NULL,
                analysis_time TEXT,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(symbol, universe)
            )
            """
        )

        status_columns = set(table_columns(conn, "data_update_status"))
        if "universe" not in status_columns:
            cur.execute(
                "ALTER TABLE data_update_status ADD COLUMN universe TEXT"
            )

        cur.execute(
            """
            INSERT OR IGNORE INTO data_update_status (id, status)
            VALUES (1, 'NEVER')
            """
        )

        conn.commit()
    finally:
        conn.close()


# ============================================================
# YAHOO SEMBOLÜ
# ============================================================

def yahoo_symbol(symbol):
    symbol = normalize_symbol(symbol)
    return f"{symbol}.IS" if symbol else ""


# ============================================================
# BIST500 EVRENİ
# ============================================================

def get_bist500_symbols():
    conn = get_connection()
    try:
        if not table_exists(conn, "bist500_universe"):
            return pd.DataFrame()
        df = pd.read_sql_query(
            """
            SELECT symbol, company, sector, industry
            FROM bist500_universe
            WHERE active = 1
              AND symbol IS NOT NULL
              AND TRIM(symbol) <> ''
            ORDER BY symbol
            """,
            conn,
        )
    finally:
        conn.close()

    if df.empty:
        return df

    df["symbol"] = df["symbol"].map(normalize_symbol)
    df = df[(df["symbol"] != "") & (df["symbol"] != "NAN")]
    df = df[df["symbol"].str.len() <= 10]
    return df.drop_duplicates("symbol").reset_index(drop=True)


def sync_bist500_to_stocks():
    universe = get_bist500_symbols()
    if universe.empty:
        return 0

    conn = get_connection()
    synced = 0
    try:
        now = datetime.now().isoformat(timespec="seconds")
        for _, row in universe.iterrows():
            conn.execute(
                """
                INSERT INTO stocks
                    (symbol, company, sector, industry, currency, updated_at)
                VALUES (?, ?, ?, ?, 'TRY', ?)
                ON CONFLICT(symbol) DO UPDATE SET
                    company = COALESCE(excluded.company, stocks.company),
                    sector = COALESCE(excluded.sector, stocks.sector),
                    industry = COALESCE(excluded.industry, stocks.industry),
                    updated_at = excluded.updated_at
                """,
                (
                    normalize_symbol(row["symbol"]),
                    None if pd.isna(row.get("company")) else row.get("company"),
                    None if pd.isna(row.get("sector")) else row.get("sector"),
                    None if pd.isna(row.get("industry")) else row.get("industry"),
                    now,
                ),
            )
            synced += 1
        conn.commit()
    finally:
        conn.close()
    return synced


# ============================================================
# BIST500 DOSYA YÜKLEME
# ============================================================

def import_bist500_file(uploaded_file):
    if uploaded_file is None:
        return {"success": False, "message": "Dosya seçilmedi.", "count": 0}

    try:
        filename = uploaded_file.name.lower().strip()

        if filename.endswith(".csv"):
            try:
                df = pd.read_csv(
                    uploaded_file,
                    sep=None,
                    engine="python",
                    encoding="utf-8-sig",
                )
            except Exception:
                uploaded_file.seek(0)
                df = pd.read_csv(
                    uploaded_file,
                    sep=None,
                    engine="python",
                    encoding="cp1254",
                )
        elif filename.endswith((".xlsx", ".xls")):
            df = pd.read_excel(uploaded_file)
        else:
            return {
                "success": False,
                "message": "Desteklenmeyen dosya. CSV veya Excel kullanın.",
                "count": 0,
            }

        if df.empty:
            return {"success": False, "message": "Dosya boş.", "count": 0}

        normalized = []
        for column in df.columns:
            name = (
                str(column).strip().lower()
                .replace("ı", "i").replace("ş", "s")
                .replace("ğ", "g").replace("ü", "u")
                .replace("ö", "o").replace("ç", "c")
                .replace(" ", "_").replace("-", "_")
            )
            normalized.append(name)
        df.columns = normalized

        symbol_candidates = [
            "symbol", "sembol", "ticker", "kod", "hisse", "hisse_kodu", "code"
        ]
        symbol_column = next((x for x in symbol_candidates if x in df.columns), None)
        if not symbol_column:
            return {
                "success": False,
                "message": "Sembol kolonu bulunamadı. Beklenen: symbol, sembol, ticker, kod, hisse.",
                "count": 0,
            }

        def find_column(candidates):
            return next((x for x in candidates if x in df.columns), None)

        company_column = find_column([
            "company", "sirket", "sirket_adi", "firma", "unvan", "company_name"
        ])
        sector_column = find_column(["sector", "sektor", "ana_sektor"])
        industry_column = find_column(["industry", "endustri", "alt_sektor"])

        df["symbol"] = df[symbol_column].map(normalize_symbol)
        df = df[(df["symbol"] != "") & (df["symbol"] != "NAN")].copy()
        df = df[df["symbol"].str.len() <= 10]
        df = df.drop_duplicates("symbol", keep="first")

        if df.empty:
            return {
                "success": False,
                "message": "Geçerli hisse sembolü bulunamadı.",
                "count": 0,
            }

        conn = get_connection()
        try:
            now = datetime.now().isoformat(timespec="seconds")
            conn.execute("UPDATE bist500_universe SET active = 0")

            inserted = 0
            for _, row in df.iterrows():
                company = row[company_column] if company_column else None
                sector = row[sector_column] if sector_column else None
                industry = row[industry_column] if industry_column else None
                company = None if pd.isna(company) else company
                sector = None if pd.isna(sector) else sector
                industry = None if pd.isna(industry) else industry

                conn.execute(
                    """
                    INSERT INTO bist500_universe
                        (symbol, company, sector, industry, active, updated_at)
                    VALUES (?, ?, ?, ?, 1, ?)
                    ON CONFLICT(symbol) DO UPDATE SET
                        company = COALESCE(excluded.company, bist500_universe.company),
                        sector = COALESCE(excluded.sector, bist500_universe.sector),
                        industry = COALESCE(excluded.industry, bist500_universe.industry),
                        active = 1,
                        updated_at = excluded.updated_at
                    """,
                    (row["symbol"], company, sector, industry, now),
                )
                inserted += 1
            conn.commit()
        finally:
            conn.close()

        return {
            "success": True,
            "message": f"{inserted} hisse BIST 500 evrenine yüklendi.",
            "count": inserted,
        }
    except Exception as exc:
        return {
            "success": False,
            "message": f"{type(exc).__name__}: {exc}",
            "count": 0,
        }


# ============================================================
# TEKNİK İNDİKATÖRLER
# ============================================================

def calculate_rsi(close, period=14):
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def calculate_atr(df, period=14):
    high = df["High"]
    low = df["Low"]
    close = df["Close"]
    previous_close = close.shift(1)
    tr = pd.concat(
        [high - low, (high - previous_close).abs(), (low - previous_close).abs()],
        axis=1,
    ).max(axis=1)
    return tr.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()


def calculate_macd(close):
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    return macd, signal


def score_rsi(rsi):
    if pd.isna(rsi):
        return 50.0
    if 50 <= rsi <= 65:
        return 100.0
    if 45 <= rsi < 50:
        return 75.0
    if 65 < rsi <= 70:
        return 85.0
    if 70 < rsi <= 80:
        return 65.0
    if rsi > 80:
        return 45.0
    if 35 <= rsi < 45:
        return 45.0
    return 25.0


def calculate_scores(df):
    close = df["Close"]
    volume = df["Volume"]

    price = float(close.iloc[-1])
    ema20 = float(df["EMA20"].iloc[-1])
    ema50 = float(df["EMA50"].iloc[-1])
    ema200 = float(df["EMA200"].iloc[-1])
    rsi = float(df["RSI"].iloc[-1])

    momentum_20 = ((close.iloc[-1] / close.iloc[-21] - 1) * 100) if len(close) > 21 else 0.0
    momentum_60 = ((close.iloc[-1] / close.iloc[-61] - 1) * 100) if len(close) > 61 else 0.0
    year_return = (
        ((close.iloc[-1] / close.iloc[-253] - 1) * 100)
        if len(close) > 253
        else ((close.iloc[-1] / close.iloc[0] - 1) * 100)
    )

    trend_score = 0.0
    if price > ema20:
        trend_score += 25
    if ema20 > ema50:
        trend_score += 25
    if ema50 > ema200:
        trend_score += 25
    if price > ema200:
        trend_score += 25

    momentum_score = 50.0
    momentum_score += np.clip(momentum_20 * 2.0, -25, 25)
    momentum_score += np.clip(momentum_60, -25, 25)
    momentum_score = clamp(momentum_score)

    rsi_score = score_rsi(rsi)
    confirmation = clamp(
        trend_score * 0.50 + rsi_score * 0.25 + momentum_score * 0.25
    )
    technical_score = clamp(
        trend_score * 0.50 + confirmation * 0.25 + momentum_score * 0.25
    )

    average_volume_20 = volume.tail(20).mean()
    volume_ratio = (
        float(volume.iloc[-1]) / float(average_volume_20)
        if pd.notna(average_volume_20) and average_volume_20 > 0
        else 0.0
    )

    volatility = close.pct_change().tail(20).std() * np.sqrt(252) * 100
    volatility = 0.0 if pd.isna(volatility) else float(volatility)

    if price > ema20 and ema20 > ema50 and ema50 > ema200:
        trend = "Yükseliş"
    elif price < ema20 and ema20 < ema50 and ema50 < ema200:
        trend = "Düşüş"
    else:
        trend = "Nötr"

    support = float(df["Low"].tail(20).min())
    resistance = float(df["High"].tail(20).max())

    macd = float(df["MACD"].iloc[-1])
    signal = float(df["MACD_SIGNAL"].iloc[-1])

    bb_mid = close.rolling(20).mean()
    bb_std = close.rolling(20).std()
    bb_upper = float((bb_mid + 2 * bb_std).iloc[-1])
    bb_lower = float((bb_mid - 2 * bb_std).iloc[-1])

    atr = float(df["ATR"].iloc[-1])
    volume_score = clamp(volume_ratio * 50)
    radar_score = clamp(
        technical_score * 0.50
        + momentum_score * 0.25
        + volume_score * 0.15
        + rsi_score * 0.10
    )

    change_percent = (
        ((close.iloc[-1] / close.iloc[-2] - 1) * 100)
        if len(close) >= 2 else 0.0
    )

    return {
        "price": price,
        "ema20": ema20,
        "ema50": ema50,
        "ema200": ema200,
        "rsi": rsi,
        "macd": macd,
        "signal": signal,
        "bollinger_upper": bb_upper,
        "bollinger_lower": bb_lower,
        "atr": atr,
        "momentum": float(momentum_20),
        "volatility": volatility,
        "support": support,
        "resistance": resistance,
        "trend": trend,
        "trend_strength": float(trend_score),
        "ai_score": float(technical_score),
        "radar_score": float(radar_score),
        "score": float(technical_score),
        "technical_score": float(technical_score),
        "momentum_60_score": float(momentum_score),
        "momentum_score": float(momentum_score),
        "trend_score": float(trend_score),
        "volume_ratio": float(volume_ratio),
        "year_return": float(year_return),
        "return_1y": float(year_return),
        "change": float(change_percent),
        "change_percent": float(change_percent),
        "last_price": price,
        "close": price,
    }


# ============================================================
# YAHOO
# ============================================================

def download_symbol(symbol, period):
    ticker = yahoo_symbol(symbol)
    if not ticker:
        return None, "Geçersiz sembol"

    try:
        data = yf.download(
            ticker,
            period=period,
            interval="1d",
            auto_adjust=False,
            progress=False,
            threads=False,
        )

        if data is None or data.empty:
            return None, "Yahoo Finance veri döndürmedi"

        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)

        required = ["Open", "High", "Low", "Close", "Volume"]
        missing = [c for c in required if c not in data.columns]
        if missing:
            return None, f"Eksik kolon: {missing}"

        data = data[required].copy()
        for column in required:
            data[column] = pd.to_numeric(data[column], errors="coerce")
        data = data.dropna(subset=["Close"])

        if len(data) < MIN_BARS:
            return None, f"Yetersiz veri: {len(data)} bar"

        data["EMA20"] = data["Close"].ewm(span=20, adjust=False).mean()
        data["EMA50"] = data["Close"].ewm(span=50, adjust=False).mean()
        data["EMA200"] = data["Close"].ewm(span=200, adjust=False).mean()
        data["RSI"] = calculate_rsi(data["Close"])
        data["ATR"] = calculate_atr(data)
        data["MACD"], data["MACD_SIGNAL"] = calculate_macd(data["Close"])

        data = data.dropna(
            subset=["EMA20", "EMA50", "EMA200", "RSI", "ATR", "MACD", "MACD_SIGNAL"]
        )
        if data.empty:
            return None, "Teknik indikatörler üretilemedi"

        return data, None
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"


# ============================================================
# DB'YE FİYAT / TEKNİK SNAPSHOT
# ============================================================

def price_date_from_index(index):
    if hasattr(index, "date"):
        return index.date().isoformat()
    return str(index)[:10]


def save_price_history(conn, symbol, data):
    rows = 0
    symbol = normalize_symbol(symbol)
    now = datetime.now().isoformat(timespec="seconds")

    for index, row in data.iterrows():
        try:
            conn.execute(
                """
                INSERT OR REPLACE INTO stock_prices
                    (symbol, price_date, open, high, low, close, volume, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    symbol,
                    price_date_from_index(index),
                    float(row["Open"]),
                    float(row["High"]),
                    float(row["Low"]),
                    float(row["Close"]),
                    float(row["Volume"]) if pd.notna(row["Volume"]) else 0.0,
                    now,
                ),
            )
            rows += 1
        except Exception:
            continue
    return rows


def save_technical_snapshot(conn, symbol, data, scores):
    symbol = normalize_symbol(symbol)
    analysis_date = price_date_from_index(data.index[-1])
    now = datetime.now().isoformat(timespec="seconds")

    columns = [
        "symbol", "analysis_date", "price", "ema20", "ema50", "ema200",
        "rsi", "macd", "signal", "bollinger_upper", "bollinger_lower", "atr",
        "momentum", "volatility", "support", "resistance", "trend", "trend_strength",
        "ai_score", "radar_score", "score", "technical_score", "momentum_60_score",
        "momentum_score", "trend_score", "volume_ratio", "year_return", "return_1y",
        "change", "change_percent", "last_price", "close", "updated_at", "created_at",
    ]

    values = (
        symbol, analysis_date, scores["price"], scores["ema20"], scores["ema50"], scores["ema200"],
        scores["rsi"], scores["macd"], scores["signal"], scores["bollinger_upper"],
        scores["bollinger_lower"], scores["atr"], scores["momentum"], scores["volatility"],
        scores["support"], scores["resistance"], scores["trend"], scores["trend_strength"],
        scores["ai_score"], scores["radar_score"], scores["score"], scores["technical_score"],
        scores["momentum_60_score"], scores["momentum_score"], scores["trend_score"],
        scores["volume_ratio"], scores["year_return"], scores["return_1y"], scores["change"],
        scores["change_percent"], scores["last_price"], scores["close"], now, now,
    )

    placeholders = ",".join(["?"] * len(columns))
    conn.execute(
        f"""
        INSERT OR REPLACE INTO technical_analysis ({','.join(columns)})
        VALUES ({placeholders})
        """,
        values,
    )


# ============================================================
# EN SON TEKNİK KAYITLAR
# ============================================================

def latest_per_symbol(conn, table, symbols=None):
    if not table_exists(conn, table):
        return pd.DataFrame()

    columns = table_columns(conn, table)
    if "symbol" not in columns:
        return pd.DataFrame()

    date_candidates = [
        "analysis_date", "updated_at", "created_at", "date", "timestamp", "price_date"
    ]
    order_cols = [x for x in date_candidates if x in columns]

    where = ""
    params = []
    if symbols:
        placeholders = ",".join(["?"] * len(symbols))
        where = f"WHERE symbol IN ({placeholders})"
        params = list(symbols)

    if not order_cols:
        return pd.read_sql_query(
            f"SELECT * FROM {table} {where}", conn, params=params
        )

    date_expr = "COALESCE(" + ",".join(order_cols) + ")"
    query = f"""
        SELECT *
        FROM (
            SELECT t.*,
                   ROW_NUMBER() OVER (
                       PARTITION BY symbol
                       ORDER BY {date_expr} DESC, rowid DESC
                   ) AS rn
            FROM {table} t
            {where}
        )
        WHERE rn = 1
    """
    try:
        return pd.read_sql_query(query, conn, params=params)
    except Exception:
        df = pd.read_sql_query(f"SELECT * FROM {table} {where}", conn, params=params)
        if df.empty:
            return df
        date_col = order_cols[0]
        df["_dt"] = pd.to_datetime(df[date_col], errors="coerce")
        return (
            df.sort_values(["symbol", "_dt"], ascending=[True, False])
            .drop_duplicates("symbol")
            .drop(columns=["_dt"])
        )


# ============================================================
# MARKET SNAPSHOT
# ============================================================

def load_market_snapshot(conn):
    if not table_exists(conn, "market_snapshot"):
        return 50.0, [], None, False

    cols = table_columns(conn, "market_snapshot")
    if "id" not in cols:
        return 50.0, [], None, False

    try:
        row = conn.execute(
            "SELECT * FROM market_snapshot WHERE id = 1 LIMIT 1"
        ).fetchone()
    except Exception:
        return 50.0, [], None, False

    if not row:
        return 50.0, [], None, False

    data = dict(row)
    score = clamp(data.get("market_score"), default=50)
    reasons = [
        x.strip()
        for x in str(data.get("reasons") or "").split("||")
        if x.strip()
    ]

    stamp = None
    for key in ("snapshot_at", "updated_at", "created_at"):
        if data.get(key):
            stamp = pd.to_datetime(data.get(key), errors="coerce")
            if pd.notna(stamp):
                break

    return score, reasons, stamp, True


# ============================================================
# FUNDAMENTAL / KAP SKORU
# ============================================================

def latest_financial_scores(conn, symbols):
    """
    financial_scores varsa symbol başına en güncel total_score'u alır.
    Bu tablo yalnızca okunur; veri güncelleme motoru buraya yazmaz/silmez.
    """
    if not symbols or not table_exists(conn, "financial_scores"):
        return {}

    cols = table_columns(conn, "financial_scores")
    if "symbol" not in cols or "total_score" not in cols:
        return {}

    placeholders = ",".join(["?"] * len(symbols))
    df = pd.read_sql_query(
        f"SELECT * FROM financial_scores WHERE symbol IN ({placeholders})",
        conn,
        params=list(symbols),
    )
    if df.empty:
        return {}

    df["Hisse"] = df["symbol"].map(normalize_symbol)
    if "fiscal_year" in df.columns:
        df["_fy"] = pd.to_numeric(df["fiscal_year"], errors="coerce")
    else:
        df["_fy"] = 0
    if "fiscal_period" in df.columns:
        df["_fp"] = pd.to_numeric(df["fiscal_period"], errors="coerce")
    else:
        df["_fp"] = 0

    df = df.sort_values(["Hisse", "_fy", "_fp"], ascending=[True, False, False])
    df = df.drop_duplicates("Hisse", keep="first")

    return {
        row["Hisse"]: clamp(row["total_score"], default=50)
        for _, row in df.iterrows()
    }


# ============================================================
# ESKİ DİNAMİK CACHE'İ OKU
# ============================================================

def load_existing_cache(conn):
    """
    Eski cache'teki JSON'u okur.
    Amaç Fundamental/KAP, sektör ve diğer mevcut alanları korumaktır.
    """
    result = {}
    if not table_exists(conn, "dynamic_portfolio_cache"):
        return result

    cols = table_columns(conn, "dynamic_portfolio_cache")
    required = {"symbol", "analysis_json"}
    if not required.issubset(cols):
        return result

    rows = conn.execute(
        """
        SELECT symbol, universe, market_score, analysis_json,
               analysis_time, updated_at
        FROM dynamic_portfolio_cache
        WHERE universe = ?
          AND analysis_json IS NOT NULL
          AND TRIM(analysis_json) <> ''
        """,
        (CACHE_UNIVERSE,),
    ).fetchall()

    for row in rows:
        symbol = normalize_symbol(row["symbol"])
        try:
            data = json.loads(row["analysis_json"])
            if not isinstance(data, dict):
                continue
        except Exception:
            continue

        data["_old_market_score"] = safe_float(row["market_score"], 50)
        data["_old_analysis_time"] = row["analysis_time"]
        data["_old_updated_at"] = row["updated_at"]
        result[symbol] = data

    return result


# ============================================================
# DİNAMİK PORTFÖY CACHE ANALİZ JSON'U
# ============================================================

def decision_from_score(score):
    score = safe_float(score, 50)
    if score >= 80:
        return "🟢 GÜÇLÜ AL"
    if score >= 70:
        return "🟢 AL"
    if score >= 60:
        return "🟡 TUT"
    if score >= 50:
        return "🟠 İZLE"
    return "🔴 SAT"


def _safe_cache_score(value, default=50.0):
    """Cache hesaplamalarında None/NaN/pd.NA gibi değerleri güvenli sayıya çevirir."""
    try:
        if value is None or pd.isna(value):
            return float(default)
    except Exception:
        pass
    try:
        value = float(value)
    except Exception:
        return float(default)
    if not np.isfinite(value):
        return float(default)
    return float(np.clip(value, 0.0, 100.0))


def build_cache_analysis(symbol, universe_row, tech, old, fundamental_score, market_score, market_time):
    """
    Teknik alanları kesinlikle yeni snapshot'tan alır.
    Fundamental/KAP alanını ise:
      1) mevcut cache'ten,
      2) yoksa financial_scores'tan,
      3) o da yoksa nötr 50
    sırasıyla korur.
    """
    symbol = normalize_symbol(symbol)

    raw_sector = universe_row.get("sector") if universe_row is not None else None
    sector = str(raw_sector or old.get("Sektör") or old.get("Sektor") or "Diğer").strip()
    if not sector:
        sector = "Diğer"

    # Eski cache'teki gerçek KAP/fundamental skoru korunur.
    old_fund = old.get("Fundamental")
    if old_fund is None:
        old_fund = old.get("fundamental_score")

    # Hiçbir durumda None doğrudan karşılaştırmaya sokulmaz.
    fundamental = _safe_cache_score(old_fund, 50.0)
    financial_value = _safe_cache_score(fundamental_score, 50.0) if fundamental_score is not None else 50.0

    # Eski cache nötr ise ve yeni finansal skor gerçekten varsa onu kullan.
    if old_fund is None:
        if fundamental_score is not None:
            fundamental = financial_value
    else:
        old_fund_num = _safe_cache_score(old_fund, 50.0)
        if abs(old_fund_num - 50.0) < 1e-9 and fundamental_score is not None:
            fundamental = financial_value

    technical = _safe_cache_score(tech.get("technical_score"), 50.0)
    momentum = _safe_cache_score(tech.get("momentum_60_score"), 50.0)
    trend = _safe_cache_score(tech.get("trend_score"), 50.0)
    market = _safe_cache_score(market_score, 50.0)

    general = clamp(
        technical * W_TECH
        + fundamental * W_FUND
        + momentum * W_MOM
        + market * W_MARKET,
        default=50,
    )

    analysis_date = tech.get("analysis_date")
    now = datetime.now().isoformat(timespec="seconds")

    analysis = dict(old)

    # İç kontrol alanlarını JSON'a taşımıyoruz.
    for key in ["_old_market_score", "_old_analysis_time", "_old_updated_at"]:
        analysis.pop(key, None)

    # Kimlik / temel alanlar
    analysis.update({
        "Hisse": symbol,
        "Sektör": sector,
        "Fundamental": round(fundamental, 1),
        "Financial Veri": bool(
            fundamental_score is not None
            or (old_fund is not None and safe_float(old_fund, 50) != 50)
        ),
        "Piyasa": round(market, 1),
        "Genel Skor": round(general, 1),
        "Karar": decision_from_score(general),

        # Yeni teknik snapshot
        "Teknik": round(technical, 1),
        "Momentum 60G": round(momentum, 1),
        "Trend": round(trend, 1),
        "Fiyat": safe_float(tech.get("price"), 0),
        "Günlük %": safe_float(tech.get("change_percent"), 0),
        "RSI": safe_float(tech.get("rsi"), 50),
        "Hacim x": safe_float(tech.get("volume_ratio"), 0),
        "1Y Getiri %": safe_float(tech.get("year_return"), 0),
        "EMA20": safe_float(tech.get("ema20"), 0),
        "EMA50": safe_float(tech.get("ema50"), 0),
        "EMA200": safe_float(tech.get("ema200"), 0),
        "MACD": safe_float(tech.get("macd"), 0),
        "MACD Signal": safe_float(tech.get("signal"), 0),
        "ATR": safe_float(tech.get("atr"), 0),
        "Destek": safe_float(tech.get("support"), 0),
        "Direnç": safe_float(tech.get("resistance"), 0),
        "Volatilite": safe_float(tech.get("volatility"), 0),
        "Radar Skoru": safe_float(tech.get("radar_score"), 50),
        "Teknik Trend": str(tech.get("trend") or "Nötr"),
        "Teknik Snapshot Tarihi": analysis_date,
        "Veri Güncelleme Zamanı": now,
    })

    if market_time is not None and pd.notna(market_time):
        analysis["Piyasa Snapshot Tarihi"] = str(market_time)

    return analysis


# ============================================================
# CACHE'İ TOPLU YENİLE
# ============================================================

def rebuild_dynamic_portfolio_cache(universe_df, successful_symbols):
    """
    Veri güncellemesi tamamlandıktan sonra çağrılır.

    Kritik güvenlik kuralı:
    Cache yalnızca başarılı teknik snapshot bulunan hisseler için yenilenir.
    Başarısız hisselerin eski cache'i silinmez.

    Böylece 500 hisseden örneğin 470'i başarılıysa 470 yeni snapshot yazılır;
    30 başarısız hissenin eski KAP/fundamental + teknik cache'i korunur.
    """
    if universe_df.empty or not successful_symbols:
        return {
            "success": False,
            "updated": 0,
            "preserved": 0,
            "message": "Yeni teknik snapshot bulunamadı.",
        }

    successful_symbols = {normalize_symbol(x) for x in successful_symbols}
    symbols = [normalize_symbol(x) for x in universe_df["symbol"].tolist()]

    conn = get_connection()
    try:
        # --------------------------------------------------------
        # 1) Güncel teknik snapshot
        # --------------------------------------------------------
        tech = latest_per_symbol(conn, "technical_analysis", symbols=symbols)
        if tech.empty:
            return {
                "success": False,
                "updated": 0,
                "preserved": 0,
                "message": "technical_analysis içinde snapshot bulunamadı.",
            }

        tech["symbol"] = tech["symbol"].map(normalize_symbol)
        tech = tech[tech["symbol"].isin(successful_symbols)].copy()
        if tech.empty:
            return {
                "success": False,
                "updated": 0,
                "preserved": 0,
                "message": "Başarılı hisseler için teknik snapshot bulunamadı.",
            }

        # --------------------------------------------------------
        # 2) Eski cache — Fundamental/KAP ve diğer alanları korumak için
        # --------------------------------------------------------
        old_cache = load_existing_cache(conn)

        # --------------------------------------------------------
        # 3) Financial scores — yalnızca okuma
        # --------------------------------------------------------
        financial_map = latest_financial_scores(conn, symbols)

        # --------------------------------------------------------
        # 4) Market snapshot
        # --------------------------------------------------------
        market_score, market_reasons, market_time, market_valid = load_market_snapshot(conn)
        if not market_valid:
            market_score = 50.0

        # --------------------------------------------------------
        # 5) Universe metadata
        # --------------------------------------------------------
        universe_map = {}
        for _, row in universe_df.iterrows():
            universe_map[normalize_symbol(row["symbol"])] = row.to_dict()

        # --------------------------------------------------------
        # 6) Transaction: başarılı hisselerin cache'i güncellenir.
        # --------------------------------------------------------
        now = datetime.now().isoformat(timespec="seconds")
        updated = 0

        conn.execute("BEGIN")

        for _, row in tech.iterrows():
            symbol = normalize_symbol(row["symbol"])
            if symbol not in successful_symbols:
                continue

            tech_dict = {
                "analysis_date": row.get("analysis_date"),
                "price": row.get("price", row.get("last_price", row.get("close"))),
                "technical_score": row.get("technical_score", row.get("score", row.get("ai_score"))),
                "momentum_60_score": row.get("momentum_60_score", row.get("momentum_score", 50)),
                "trend_score": row.get("trend_score", row.get("trend_strength", 50)),
                "change_percent": row.get("change_percent", row.get("change", 0)),
                "rsi": row.get("rsi", 50),
                "volume_ratio": row.get("volume_ratio", 0),
                "year_return": row.get("year_return", row.get("return_1y", 0)),
                "ema20": row.get("ema20", 0),
                "ema50": row.get("ema50", 0),
                "ema200": row.get("ema200", 0),
                "macd": row.get("macd", 0),
                "signal": row.get("signal", 0),
                "atr": row.get("atr", 0),
                "support": row.get("support", 0),
                "resistance": row.get("resistance", 0),
                "volatility": row.get("volatility", 0),
                "radar_score": row.get("radar_score", 50),
                "trend": row.get("trend", "Nötr"),
            }

            old = old_cache.get(symbol, {})
            fundamental_score = financial_map.get(symbol)
            try:
                analysis = build_cache_analysis(
                    symbol=symbol,
                    universe_row=universe_map.get(symbol),
                    tech=tech_dict,
                    old=old,
                    fundamental_score=fundamental_score,
                    market_score=_safe_cache_score(market_score, 50.0),
                    market_time=market_time,
                )
            except Exception as exc:
                # Tek bir bozuk/None değer bütün 500'lük cache yenilemesini durdurmasın.
                preserved = old if isinstance(old, dict) else {}
                analysis = dict(preserved)
                analysis.update({
                    "Hisse": symbol,
                    "Sektör": str((universe_map.get(symbol) or {}).get("sector") or preserved.get("Sektör") or "Diğer"),
                    "Fundamental": _safe_cache_score(fundamental_score, _safe_cache_score(preserved.get("Fundamental"), 50.0)),
                    "Piyasa": _safe_cache_score(market_score, 50.0),
                    "Teknik": _safe_cache_score(tech_dict.get("technical_score"), 50.0),
                    "Momentum 60G": _safe_cache_score(tech_dict.get("momentum_60_score"), 50.0),
                    "Trend": _safe_cache_score(tech_dict.get("trend_score"), 50.0),
                    "Fiyat": safe_float(tech_dict.get("price"), 0),
                    "Teknik Snapshot Tarihi": tech_dict.get("analysis_date"),
                    "Veri Güncelleme Zamanı": now,
                })
                tech_score = _safe_cache_score(analysis.get("Teknik"), 50.0)
                fund_score = _safe_cache_score(analysis.get("Fundamental"), 50.0)
                mom_score = _safe_cache_score(analysis.get("Momentum 60G"), 50.0)
                mkt_score = _safe_cache_score(analysis.get("Piyasa"), 50.0)
                analysis["Genel Skor"] = round(_safe_cache_score(tech_score * W_TECH + fund_score * W_FUND + mom_score * W_MOM + mkt_score * W_MARKET, 50.0), 1)
                analysis["Karar"] = decision_from_score(analysis["Genel Skor"])

            conn.execute(
                """
                INSERT INTO dynamic_portfolio_cache
                    (symbol, universe, market_score, analysis_json, analysis_time, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(symbol, universe) DO UPDATE SET
                    market_score = excluded.market_score,
                    analysis_json = excluded.analysis_json,
                    analysis_time = excluded.analysis_time,
                    updated_at = excluded.updated_at
                """,
                (
                    symbol,
                    CACHE_UNIVERSE,
                    _safe_cache_score(market_score, 50.0),
                    json.dumps(analysis, ensure_ascii=False, default=str),
                    now,
                    now,
                ),
            )
            updated += 1

        # --------------------------------------------------------
        # 7) Aktif BIST500 dışına çıkan eski BIST500 cache kayıtlarını sil.
        #    Başarısız hisseleri değil, artık evrende olmayanları siler.
        # --------------------------------------------------------
        active_symbols = set(symbols)
        existing_cache_rows = conn.execute(
            "SELECT symbol FROM dynamic_portfolio_cache WHERE universe = ?",
            (CACHE_UNIVERSE,),
        ).fetchall()
        removed = 0
        for cache_row in existing_cache_rows:
            cache_symbol = normalize_symbol(cache_row["symbol"])
            if cache_symbol not in active_symbols:
                conn.execute(
                    "DELETE FROM dynamic_portfolio_cache WHERE symbol = ? AND universe = ?",
                    (cache_symbol, CACHE_UNIVERSE),
                )
                removed += 1

        conn.commit()

        preserved = max(0, len(symbols) - updated)
        return {
            "success": True,
            "updated": updated,
            "preserved": preserved,
            "removed": removed,
            "market_score": market_score,
            "market_valid": market_valid,
            "message": f"{updated} hissenin Dinamik Portföy snapshotı yenilendi.",
        }

    except Exception as exc:
        try:
            conn.rollback()
        except Exception:
            pass
        return {
            "success": False,
            "updated": 0,
            "preserved": 0,
            "message": f"Cache yenileme hatası: {type(exc).__name__}: {exc}",
        }
    finally:
        conn.close()


# ============================================================
# UPDATE STATUS
# ============================================================

def update_status(
    status,
    period,
    universe,
    total,
    success,
    failed,
    price_rows,
    technical_rows,
    error=None,
    success_at=None,
):
    conn = get_connection()
    try:
        now = datetime.now().isoformat(timespec="seconds")
        conn.execute(
            """
            UPDATE data_update_status
            SET status = ?,
                last_attempt_at = ?,
                last_success_at = ?,
                source = ?,
                period = ?,
                universe = ?,
                symbols_total = ?,
                symbols_success = ?,
                symbols_failed = ?,
                price_rows = ?,
                technical_rows = ?,
                error = ?
            WHERE id = 1
            """,
            (
                status, now, success_at, "Yahoo Finance", universe,
                universe, total, success, failed, price_rows, technical_rows, error,
            ),
        )
        conn.commit()
    finally:
        conn.close()


# ============================================================
# GÜNCELLEME MOTORU
# ============================================================

def run_update(symbols, period, progress_bar, status_text, pause_seconds=DEFAULT_PAUSE):
    total = len(symbols)
    success_count = 0
    failed_count = 0
    price_rows = 0
    technical_rows = 0
    errors = []
    successful_symbols = []

    update_status(
        status="RUNNING",
        period=period,
        universe=CACHE_UNIVERSE,
        total=total,
        success=0,
        failed=0,
        price_rows=0,
        technical_rows=0,
        error=None,
        success_at=None,
    )

    conn = get_connection()
    try:
        for i, symbol in enumerate(symbols, start=1):
            progress_bar.progress(i / max(total, 1))
            status_text.write(
                f"🔄 **{symbol}** güncelleniyor... ({i}/{total})"
            )

            data, error = download_symbol(symbol, period)
            if data is None:
                failed_count += 1
                errors.append(f"{symbol}: {error}")
                continue

            try:
                saved_prices = save_price_history(conn, symbol, data)
                price_rows += saved_prices

                scores = calculate_scores(data)
                save_technical_snapshot(conn, symbol, data, scores)
                technical_rows += 1
                success_count += 1
                successful_symbols.append(normalize_symbol(symbol))
                conn.commit()
            except Exception as exc:
                failed_count += 1
                conn.rollback()
                errors.append(f"{symbol}: {type(exc).__name__}: {exc}")

            if pause_seconds > 0:
                time.sleep(pause_seconds)

        if success_count > 0 and failed_count == 0:
            final_status = "SUCCESS"
        elif success_count > 0:
            final_status = "PARTIAL"
        else:
            final_status = "FAILED"

        success_at = (
            datetime.now().isoformat(timespec="seconds")
            if success_count > 0 else None
        )

        update_status(
            status=final_status,
            period=period,
            universe=CACHE_UNIVERSE,
            total=total,
            success=success_count,
            failed=failed_count,
            price_rows=price_rows,
            technical_rows=technical_rows,
            error="\n".join(errors[:100]),
            success_at=success_at,
        )

        # --------------------------------------------------------
        # KRİTİK: YENİ TEKNİK SNAPSHOT → DİNAMİK CACHE
        # --------------------------------------------------------
        cache_result = rebuild_dynamic_portfolio_cache(
            universe_df=get_bist500_symbols(),
            successful_symbols=successful_symbols,
        )

        return {
            "status": final_status,
            "total": total,
            "success": success_count,
            "failed": failed_count,
            "price_rows": price_rows,
            "technical_rows": technical_rows,
            "errors": errors,
            "successful_symbols": successful_symbols,
            "cache": cache_result,
        }
    finally:
        conn.close()


# ============================================================
# DURUM / İSTATİSTİK
# ============================================================

def get_update_status():
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM data_update_status WHERE id = 1"
        ).fetchone()
        return dict(row) if row else {}
    finally:
        conn.close()


def get_snapshot_stats():
    conn = get_connection()
    try:
        technical_count = conn.execute(
            "SELECT COUNT(*) FROM technical_analysis"
        ).fetchone()[0]
        unique_symbols = conn.execute(
            "SELECT COUNT(DISTINCT symbol) FROM technical_analysis"
        ).fetchone()[0]
        latest_date = conn.execute(
            "SELECT MAX(analysis_date) FROM technical_analysis"
        ).fetchone()[0]
        price_count = conn.execute(
            "SELECT COUNT(*) FROM stock_prices"
        ).fetchone()[0]
        universe_count = conn.execute(
            "SELECT COUNT(*) FROM bist500_universe WHERE active = 1"
        ).fetchone()[0]
        cache_count = (
            conn.execute(
                "SELECT COUNT(*) FROM dynamic_portfolio_cache WHERE universe = ?",
                (CACHE_UNIVERSE,),
            ).fetchone()[0]
            if table_exists(conn, "dynamic_portfolio_cache") else 0
        )
        cache_latest = (
            conn.execute(
                "SELECT MAX(analysis_time) FROM dynamic_portfolio_cache WHERE universe = ?",
                (CACHE_UNIVERSE,),
            ).fetchone()[0]
            if table_exists(conn, "dynamic_portfolio_cache") else None
        )
        return {
            "technical_count": technical_count,
            "unique_symbols": unique_symbols,
            "latest_date": latest_date,
            "price_count": price_count,
            "universe_count": universe_count,
            "cache_count": cache_count,
            "cache_latest": cache_latest,
        }
    finally:
        conn.close()


def get_cache_health():
    conn = get_connection()
    try:
        if not table_exists(conn, "dynamic_portfolio_cache"):
            return {"count": 0, "latest": None, "oldest": None}
        row = conn.execute(
            """
            SELECT COUNT(*) AS n,
                   MAX(analysis_time) AS latest,
                   MIN(analysis_time) AS oldest
            FROM dynamic_portfolio_cache
            WHERE universe = ?
            """,
            (CACHE_UNIVERSE,),
        ).fetchone()
        return {
            "count": int(row["n"] or 0),
            "latest": row["latest"],
            "oldest": row["oldest"],
        }
    finally:
        conn.close()


# ============================================================
# BAŞLANGIÇ
# ============================================================

ensure_database()
universe_df = get_bist500_symbols()
status = get_update_status()
stats = get_snapshot_stats()


# ============================================================
# BAŞLIK
# ============================================================

st.title("🔄 BIST AI PRO — BIST 500 Veri Güncelleme")
st.caption(
    "BIST 500 → Yahoo Finance → stock_prices → technical_analysis "
    "→ dynamic_portfolio_cache → Dinamik Portföy"
)

st.info(
    """
    **Gerçek tarama evreni:** `bist500_universe`

    `stocks` yalnızca sistem içi senkronizasyon için kullanılır.

    Her başarılı BIST500 güncellemesinden sonra **dynamic_portfolio_cache**
    otomatik olarak yenilenir. KAP/financial skorları silinmez; mevcut
    Fundamental alanı korunur, teknik bileşenler yeni snapshot'tan alınır.
    """
)


# ============================================================
# ÜST METRİKLER
# ============================================================

c1, c2, c3, c4, c5, c6 = st.columns(6)
with c1:
    st.metric("BIST 500 Evren", stats["universe_count"])
with c2:
    st.metric("Teknik Hisse", stats["unique_symbols"])
with c3:
    st.metric("Fiyat Kaydı", f"{stats['price_count']:,}")
with c4:
    st.metric("Teknik Kayıt", f"{stats['technical_count']:,}")
with c5:
    st.metric("Cache Hisse", stats["cache_count"])
with c6:
    st.metric("Son Teknik Tarih", stats["latest_date"] or "Yok")


# ============================================================
# EVREN YÜKLEME
# ============================================================

st.divider()
st.subheader("📥 BIST 500 Evrenini Yükle")
st.info(
    "CSV/XLSX/XLS yükleyin. Zorunlu kolonlardan biri: "
    "`symbol`, `sembol`, `ticker`, `kod`, `hisse`. "
    "İsteğe bağlı: `company`, `sector`, `industry`."
)

uploaded_bist500 = st.file_uploader(
    "BIST 500 dosyasını seçin",
    type=["csv", "xlsx", "xls"],
    key="bist500_upload",
)

u1, u2 = st.columns(2)
with u1:
    upload_button = st.button(
        "📥 BIST 500 LİSTESİNİ YÜKLE",
        type="primary",
        use_container_width=True,
    )
with u2:
    reload_universe = st.button(
        "🔄 EVRENİ VERİTABANINDAN YENİLE",
        use_container_width=True,
    )

if upload_button:
    if uploaded_bist500 is None:
        st.warning("⚠️ Önce CSV veya Excel dosyasını seçin.")
    else:
        with st.spinner("BIST 500 evreni yükleniyor..."):
            result = import_bist500_file(uploaded_bist500)
        if result["success"]:
            st.success("🟢 " + result["message"])
            synced = sync_bist500_to_stocks()
            st.info(f"🔄 {synced} hisse stocks tablosuyla senkronize edildi.")
            st.rerun()
        else:
            st.error("🔴 " + result["message"])

if reload_universe:
    universe_df = get_bist500_symbols()
    st.success(f"🔄 Veritabanı evreni yeniden okundu: **{len(universe_df)} hisse**")

universe_df = get_bist500_symbols()
universe_count = len(universe_df)

st.subheader("📌 BIST 500 Evren Durumu")
if universe_count == 500:
    st.success(f"🟢 BIST 500 evreni hazır — **{universe_count} hisse**")
elif universe_count > 0:
    st.warning(f"🟡 BIST 500 evreni eksik — **{universe_count} hisse**")
else:
    st.warning("🟡 BIST 500 evreni boş. Önce listeyi yükleyin.")

if universe_df.empty:
    st.info("📥 Veri güncellemesini başlatmak için önce BIST 500 evrenini yükleyin.")
    st.stop()

selected_symbols = universe_df["symbol"].map(normalize_symbol).drop_duplicates().tolist()

st.write(f"🎯 Güncellenecek evren: **BIST 500**")
st.write(f"📊 Güncellenecek hisse sayısı: **{len(selected_symbols)}**")


# ============================================================
# STOCKS SENKRONİZASYONU
# ============================================================

st.divider()
st.subheader("🔄 BIST 500 → STOCKS")
st.caption(
    "stocks tablosu yalnızca sistem içi senkronizasyondur; gerçek veri taraması "
    "bist500_universe üzerinden yapılır."
)

sync_stocks = st.button(
    "🔄 BIST 500 → STOCKS SENKRONİZE ET",
    use_container_width=True,
)

if sync_stocks:
    count = sync_bist500_to_stocks()
    st.success(f"🟢 {count} BIST 500 hissesi stocks tablosuyla senkronize edildi.")


# ============================================================
# AYARLAR
# ============================================================

st.divider()
st.subheader("⚙️ Güncelleme Ayarları")

a1, a2 = st.columns(2)
with a1:
    period_label = st.selectbox(
        "Geçmiş veri",
        list(PERIODS.keys()),
        index=1,
    )
with a2:
    pause_seconds = st.number_input(
        "Hisse başına bekleme",
        min_value=0.0,
        max_value=2.0,
        value=DEFAULT_PAUSE,
        step=0.05,
    )

period = PERIODS[period_label]


# ============================================================
# GÜNCELLEME
# ============================================================

st.divider()
st.subheader("🚀 Veri Güncelleme Motoru")
st.write(f"Yahoo Finance'e gönderilecek hisse sayısı: **{len(selected_symbols)}**")
st.caption(
    "BIST500'ün tüm aktif hisseleri taranır. Başarılı teknik snapshot'lar "
    "tamamlandıktan sonra Dinamik Portföy cache'i otomatik yenilenir."
)

start_update = st.button(
    "🚀 BIST 500 VERİ GÜNCELLEMESİNİ BAŞLAT",
    type="primary",
    use_container_width=True,
)

if start_update:
    st.divider()
    st.subheader("⏳ BIST 500 taraması çalışıyor...")

    progress = st.progress(0)
    status_text = st.empty()
    start_time = time.time()

    result = run_update(
        symbols=selected_symbols,
        period=period,
        progress_bar=progress,
        status_text=status_text,
        pause_seconds=pause_seconds,
    )

    elapsed = time.time() - start_time
    progress.progress(1.0)

    st.divider()

    if result["status"] == "SUCCESS":
        st.success("✅ BIST 500 veri güncellemesi başarıyla tamamlandı.")
    elif result["status"] == "PARTIAL":
        st.warning("⚠️ BIST 500 veri güncellemesi kısmen tamamlandı.")
    else:
        st.error("❌ BIST 500 veri güncellemesi başarısız.")

    r1, r2, r3, r4, r5 = st.columns(5)
    with r1:
        st.metric("Taranan", result["total"])
    with r2:
        st.metric("Başarılı", result["success"])
    with r3:
        st.metric("Başarısız", result["failed"])
    with r4:
        st.metric("Fiyat Satırı", f"{result['price_rows']:,}")
    with r5:
        st.metric("Teknik Snapshot", result["technical_rows"])

    st.caption(f"Toplam süre: {elapsed:.1f} saniye")

    # --------------------------------------------------------
    # CACHE SONUCU
    # --------------------------------------------------------
    cache = result.get("cache", {})
    if cache.get("success"):
        st.success(
            "🟢 Dinamik Portföy cache yenilendi: "
            f"**{cache.get('updated', 0)} hisse**. "
            f"Korunan eski kayıt: **{cache.get('preserved', 0)}**. "
            f"Piyasa skoru: **{cache.get('market_score', 50):.1f}**."
        )
    else:
        st.error(
            "🔴 Teknik güncelleme tamamlandı ancak Dinamik Portföy cache "
            f"yenilenemedi: {cache.get('message', 'Bilinmeyen hata')}"
        )

    if result["errors"]:
        with st.expander(f"⚠️ Hata / Eksik Veri ({len(result['errors'])})"):
            for error in result["errors"]:
                st.write(f"- {error}")


# ============================================================
# MOTOR DURUMU
# ============================================================

st.divider()
st.subheader("📊 Veri Motoru Durumu")
status = get_update_status()

if status:
    s1, s2, s3, s4 = st.columns(4)
    with s1:
        st.metric("Durum", status.get("status", "NEVER"))
    with s2:
        st.metric("Başarılı", status.get("symbols_success", 0))
    with s3:
        st.metric("Başarısız", status.get("symbols_failed", 0))
    with s4:
        st.metric("Snapshot", status.get("technical_rows", 0))

    if status.get("last_attempt_at"):
        st.caption(f"Son deneme: **{status['last_attempt_at']}**")
    if status.get("last_success_at"):
        st.success(f"🟢 Son başarılı veri: **{status['last_success_at']}**")
    else:
        st.warning("🟡 Henüz başarılı bir veri güncellemesi yok.")


# ============================================================
# DİNAMİK PORTFÖY CACHE KONTROLÜ
# ============================================================

st.divider()
st.subheader("🧪 Dinamik Portföy Cache Kontrolü")

cache_health = get_cache_health()

if cache_health["count"] > 0:
    st.success(
        "🟢 Dinamik Portföy cache aktif — "
        f"**{cache_health['count']} hisse** / "
        f"son cache zamanı: **{cache_health['latest']}**"
    )
else:
    st.error(
        "🔴 dynamic_portfolio_cache boş. "
        "Dinamik Portföy yeni snapshot kullanamaz."
    )

# Teknik ve cache tarihlerini yan yana göster.
conn = get_connection()
try:
    tech_latest = conn.execute(
        "SELECT MAX(analysis_date) FROM technical_analysis"
    ).fetchone()[0]
    cache_latest = conn.execute(
        "SELECT MAX(analysis_time) FROM dynamic_portfolio_cache WHERE universe = ?",
        (CACHE_UNIVERSE,),
    ).fetchone()[0]
finally:
    conn.close()

x1, x2, x3 = st.columns(3)
with x1:
    st.metric("Teknik Son Piyasa Tarihi", tech_latest or "Yok")
with x2:
    st.metric("Cache Son Yenileme", cache_latest or "Yok")
with x3:
    st.metric("Cache Hisse", cache_health["count"])

if tech_latest and cache_latest:
    st.caption(
        "ℹ️ Teknik piyasa tarihi ile cache yenileme zamanı farklı formatta tutulur: "
        "technical_analysis işlem gününü, cache ise snapshot'ın oluşturulduğu zamanı gösterir."
    )


# ============================================================
# VERİ AKIŞI
# ============================================================

st.divider()
st.subheader("🔗 Veri Akışı")
st.code(
    """
BIST 500 Excel
      ↓
bist500_universe
      ↓
500 aktif sembol
      ↓
Yahoo Finance
      ↓
stock_prices
      ↓
EMA / RSI / MACD / ATR / Momentum / Trend / Hacim
      ↓
technical_analysis
      ↓
Eski Fundamental/KAP alanını koru
      ↓
Yeni Teknik + Momentum + Piyasa
      ↓
Genel Skor = Teknik %50 + Fundamental %20 + Momentum %15 + Piyasa %15
      ↓
dynamic_portfolio_cache
      ↓
Dinamik Portföy
""",
    language="text",
)

st.caption("Temel/KAP finansal skorları bu motor tarafından silinmez veya değiştirilmez.")
st.caption("Teknik veri kaynağı: Yahoo Finance")
st.caption("Tarama evreni: bist500_universe")
st.caption("stocks tablosu yalnızca sistem içi senkronizasyon içindir.")
