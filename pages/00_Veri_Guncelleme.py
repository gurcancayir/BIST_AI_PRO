# ============================================================
# BIST AI PRO
# 00_Veri_Guncelleme.py
#
# BIST 500 VERİ GÜNCELLEME MOTORU
#
# BIST 500
#      ↓
# bist500_universe
#      ↓
# stocks
#      ↓
# Yahoo Finance
#      ↓
# stock_prices
#      ↓
# technical_analysis
#      ↓
# data_update_status
#      ↓
# Dinamik Portföy
#
# ÖNEMLİ:
# stocks tablosundaki hisse sayısı tarama evrenini belirlemez.
# Gerçek tarama evreni bist500_universe tablosudur.
# ============================================================

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
# DOSYA
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "borsa.db"


# ============================================================
# AYARLAR
# ============================================================

MIN_BARS = 220

PERIODS = {
    "1 Yıl": "1y",
    "2 Yıl": "2y",
    "5 Yıl": "5y",
}

DEFAULT_PAUSE = 0.10


# ============================================================
# DB BAĞLANTISI
# ============================================================

def get_connection():

    conn = sqlite3.connect(
        DB_PATH,
        check_same_thread=False,
        timeout=60,
    )

    conn.row_factory = sqlite3.Row

    return conn


# ============================================================
# TABLO KONTROL
# ============================================================

def table_exists(conn, table_name):

    row = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name = ?
        """,
        (table_name,),
    ).fetchone()

    return row is not None


# ============================================================
# KOLON KONTROL
# ============================================================

def table_columns(conn, table_name):

    if not table_exists(conn, table_name):
        return []

    rows = conn.execute(
        f"PRAGMA table_info({table_name})"
    ).fetchall()

    return [
        row["name"]
        for row in rows
    ]


# ============================================================
# VERİTABANINI HAZIRLA
# ============================================================

def ensure_database():

    conn = get_connection()

    try:

        cur = conn.cursor()

        # ====================================================
        # STOCKS
        # ====================================================

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

                created_at TEXT
                    DEFAULT CURRENT_TIMESTAMP,

                updated_at TEXT
                    DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        # ====================================================
        # BIST 500 UNIVERSE
        # ====================================================

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

        # ====================================================
        # STOCK PRICES
        # ====================================================

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

                created_at TEXT
                    DEFAULT CURRENT_TIMESTAMP,

                UNIQUE(symbol, price_date)
            )
            """
        )

        # ====================================================
        # TECHNICAL ANALYSIS
        # ====================================================

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

                created_at TEXT
                    DEFAULT CURRENT_TIMESTAMP,

                UNIQUE(symbol, analysis_date)
            )
            """
        )

        # ====================================================
        # DİNAMİK PORTFÖY İÇİN EK KOLONLAR
        # ====================================================

        existing = set(
            table_columns(
                conn,
                "technical_analysis",
            )
        )

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
                    f"""
                    ALTER TABLE technical_analysis
                    ADD COLUMN {column} {dtype}
                    """
                )

        # ====================================================
        # DATA UPDATE STATUS
        # ====================================================

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

        status_columns = set(
            table_columns(
                conn,
                "data_update_status",
            )
        )

        if "universe" not in status_columns:

            cur.execute(
                """
                ALTER TABLE data_update_status
                ADD COLUMN universe TEXT
                """
            )

        cur.execute(
            """
            INSERT OR IGNORE INTO data_update_status (
                id,
                status
            )
            VALUES (
                1,
                'NEVER'
            )
            """
        )

        conn.commit()

    finally:

        conn.close()


# ============================================================
# YAHOO SEMBOLÜ
# ============================================================

def yahoo_symbol(symbol):

    symbol = (
        str(symbol)
        .upper()
        .strip()
    )

    if not symbol:
        return ""

    if symbol.endswith(".IS"):
        return symbol

    return f"{symbol}.IS"


# ============================================================
# BIST 500 EVRENİNİ OKU
# ============================================================

def get_bist500_symbols():

    conn = get_connection()

    try:

        if not table_exists(
            conn,
            "bist500_universe",
        ):

            return pd.DataFrame()

        df = pd.read_sql_query(
            """
            SELECT

                symbol,
                company,
                sector,
                industry

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

    df["symbol"] = (
        df["symbol"]
        .astype(str)
        .str.upper()
        .str.strip()
        .str.replace(
            ".IS",
            "",
            regex=False,
        )
    )

    df = df[
        df["symbol"] != ""
    ]

    df = df[
        df["symbol"] != "NAN"
    ]

    df = df.drop_duplicates(
        subset=["symbol"]
    )

    return df.reset_index(
        drop=True
    )


# ============================================================
# BIST 500 → STOCKS SENKRONİZASYONU
# ============================================================

def sync_bist500_to_stocks():

    universe = get_bist500_symbols()

    if universe.empty:
        return 0

    conn = get_connection()

    synced = 0

    try:

        now = datetime.now().isoformat(
            timespec="seconds"
        )

        for _, row in universe.iterrows():

            symbol = row["symbol"]

            conn.execute(
                """
                INSERT INTO stocks (

                    symbol,
                    company,
                    sector,
                    industry,
                    currency,
                    updated_at

                )

                VALUES (
                    ?, ?, ?, ?, 'TRY', ?
                )

                ON CONFLICT(symbol)
                DO UPDATE SET

                    company =
                        COALESCE(
                            excluded.company,
                            stocks.company
                        ),

                    sector =
                        COALESCE(
                            excluded.sector,
                            stocks.sector
                        ),

                    industry =
                        COALESCE(
                            excluded.industry,
                            stocks.industry
                        ),

                    updated_at =
                        excluded.updated_at
                """,
                (
                    symbol,
                    row.get("company"),
                    row.get("sector"),
                    row.get("industry"),
                    now,
                ),
            )

            synced += 1

        conn.commit()

    finally:

        conn.close()

    return synced


# ============================================================
# BIST 500 DOSYA YÜKLEME
#
# CSV / XLSX / XLS
#       ↓
# bist500_universe
# ============================================================

def import_bist500_file(uploaded_file):

    if uploaded_file is None:

        return {
            "success": False,
            "message": "Dosya seçilmedi.",
            "count": 0,
        }

    try:

        filename = (
            uploaded_file.name
            .lower()
            .strip()
        )

        # ====================================================
        # DOSYA OKU
        # ====================================================

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

        elif filename.endswith(
            (".xlsx", ".xls")
        ):

            df = pd.read_excel(
                uploaded_file
            )

        else:

            return {
                "success": False,
                "message":
                    "Desteklenmeyen dosya. "
                    "CSV veya Excel kullanın.",
                "count": 0,
            }

        if df.empty:

            return {
                "success": False,
                "message": "Dosya boş.",
                "count": 0,
            }

        # ====================================================
        # KOLONLARI NORMALİZE ET
        # ====================================================

        normalized_columns = []

        for column in df.columns:

            name = (
                str(column)
                .strip()
                .lower()
                .replace("ı", "i")
                .replace("ş", "s")
                .replace("ğ", "g")
                .replace("ü", "u")
                .replace("ö", "o")
                .replace("ç", "c")
                .replace(" ", "_")
                .replace("-", "_")
            )

            normalized_columns.append(
                name
            )

        df.columns = normalized_columns

        # ====================================================
        # SEMBOL KOLONU
        # ====================================================

        symbol_candidates = [

            "symbol",
            "sembol",
            "ticker",
            "kod",
            "hisse",
            "hisse_kodu",
            "code",
        ]

        symbol_column = None

        for candidate in symbol_candidates:

            if candidate in df.columns:

                symbol_column = candidate
                break

        if symbol_column is None:

            return {
                "success": False,
                "message":
                    "Sembol kolonu bulunamadı. "
                    "Beklenen kolonlardan biri: "
                    "symbol, sembol, ticker, kod, hisse.",
                "count": 0,
            }

        # ====================================================
        # DİĞER KOLONLAR
        # ====================================================

        def find_column(candidates):

            for candidate in candidates:

                if candidate in df.columns:
                    return candidate

            return None

        company_column = find_column(
            [
                "company",
                "sirket",
                "sirket_adi",
                "firma",
                "unvan",
                "company_name",
            ]
        )

        sector_column = find_column(
            [
                "sector",
                "sektor",
                "ana_sektor",
            ]
        )

        industry_column = find_column(
            [
                "industry",
                "endustri",
                "alt_sektor",
            ]
        )

        # ====================================================
        # SEMBOLLERİ TEMİZLE
        # ====================================================

        df["symbol"] = (
            df[symbol_column]
            .astype(str)
            .str.upper()
            .str.strip()
            .str.replace(
                ".IS",
                "",
                regex=False,
            )
        )

        df = df[
            df["symbol"].notna()
        ].copy()

        df = df[
            df["symbol"] != ""
        ]

        df = df[
            df["symbol"] != "NAN"
        ]

        # Çok uzun hatalı değerleri filtrele

        df = df[
            df["symbol"].str.len() <= 10
        ]

        # Duplicate

        df = df.drop_duplicates(
            subset=["symbol"],
            keep="first",
        )

        if df.empty:

            return {
                "success": False,
                "message":
                    "Geçerli hisse sembolü bulunamadı.",
                "count": 0,
            }

        # ====================================================
        # DB'YE YAZ
        # ====================================================

        conn = get_connection()

        try:

            now = datetime.now().isoformat(
                timespec="seconds"
            )

            # ------------------------------------------------
            # Önce mevcut aktif evreni pasifleştir.
            # ------------------------------------------------

            conn.execute(
                """
                UPDATE bist500_universe
                SET active = 0
                """
            )

            inserted = 0

            for _, row in df.iterrows():

                symbol = row["symbol"]

                company = (
                    row[company_column]
                    if company_column
                    else None
                )

                sector = (
                    row[sector_column]
                    if sector_column
                    else None
                )

                industry = (
                    row[industry_column]
                    if industry_column
                    else None
                )

                if pd.isna(company):
                    company = None

                if pd.isna(sector):
                    sector = None

                if pd.isna(industry):
                    industry = None

                conn.execute(
                    """
                    INSERT INTO bist500_universe (

                        symbol,
                        company,
                        sector,
                        industry,
                        active,
                        updated_at

                    )

                    VALUES (
                        ?, ?, ?, ?, 1, ?
                    )

                    ON CONFLICT(symbol)
                    DO UPDATE SET

                        company =
                            COALESCE(
                                excluded.company,
                                bist500_universe.company
                            ),

                        sector =
                            COALESCE(
                                excluded.sector,
                                bist500_universe.sector
                            ),

                        industry =
                            COALESCE(
                                excluded.industry,
                                bist500_universe.industry
                            ),

                        active = 1,

                        updated_at =
                            excluded.updated_at
                    """,
                    (
                        symbol,
                        company,
                        sector,
                        industry,
                        now,
                    ),
                )

                inserted += 1

            conn.commit()

        finally:

            conn.close()

        return {
            "success": True,
            "message":
                f"{inserted} hisse BIST 500 evrenine yüklendi.",
            "count": inserted,
        }

    except Exception as exc:

        return {
            "success": False,
            "message":
                f"{type(exc).__name__}: {exc}",
            "count": 0,
        }


# ============================================================
# RSI
# ============================================================

def calculate_rsi(
    close,
    period=14,
):

    delta = close.diff()

    gain = delta.clip(
        lower=0
    )

    loss = -delta.clip(
        upper=0
    )

    avg_gain = gain.ewm(
        alpha=1 / period,
        min_periods=period,
        adjust=False,
    ).mean()

    avg_loss = loss.ewm(
        alpha=1 / period,
        min_periods=period,
        adjust=False,
    ).mean()

    rs = (
        avg_gain
        /
        avg_loss.replace(
            0,
            np.nan,
        )
    )

    return (
        100
        -
        (
            100
            /
            (1 + rs)
        )
    )


# ============================================================
# ATR
# ============================================================

def calculate_atr(
    df,
    period=14,
):

    high = df["High"]

    low = df["Low"]

    close = df["Close"]

    previous_close = close.shift(1)

    tr = pd.concat(
        [
            high - low,

            (
                high
                -
                previous_close
            ).abs(),

            (
                low
                -
                previous_close
            ).abs(),
        ],
        axis=1,
    ).max(axis=1)

    return tr.ewm(
        alpha=1 / period,
        min_periods=period,
        adjust=False,
    ).mean()


# ============================================================
# MACD
# ============================================================

def calculate_macd(close):

    ema12 = close.ewm(
        span=12,
        adjust=False,
    ).mean()

    ema26 = close.ewm(
        span=26,
        adjust=False,
    ).mean()

    macd = ema12 - ema26

    signal = macd.ewm(
        span=9,
        adjust=False,
    ).mean()

    return macd, signal


# ============================================================
# CLAMP
# ============================================================

def clamp(
    value,
    low=0,
    high=100,
):

    try:

        return float(
            np.clip(
                value,
                low,
                high,
            )
        )

    except Exception:

        return 50.0


# ============================================================
# RSI SKORU
# ============================================================

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


# ============================================================
# TEKNİK SKOR
# ============================================================

def calculate_scores(df):

    close = df["Close"]

    volume = df["Volume"]

    price = float(
        close.iloc[-1]
    )

    ema20 = float(
        df["EMA20"].iloc[-1]
    )

    ema50 = float(
        df["EMA50"].iloc[-1]
    )

    ema200 = float(
        df["EMA200"].iloc[-1]
    )

    rsi = float(
        df["RSI"].iloc[-1]
    )

    # ========================================================
    # MOMENTUM 20
    # ========================================================

    if len(close) > 21:

        momentum_20 = (
            (
                close.iloc[-1]
                /
                close.iloc[-21]
                - 1
            )
            * 100
        )

    else:

        momentum_20 = 0.0

    # ========================================================
    # MOMENTUM 60
    # ========================================================

    if len(close) > 61:

        momentum_60 = (
            (
                close.iloc[-1]
                /
                close.iloc[-61]
                - 1
            )
            * 100
        )

    else:

        momentum_60 = 0.0

    # ========================================================
    # 1 YILLIK GETİRİ
    # ========================================================

    if len(close) > 253:

        year_return = (
            (
                close.iloc[-1]
                /
                close.iloc[-253]
                - 1
            )
            * 100
        )

    else:

        year_return = (
            (
                close.iloc[-1]
                /
                close.iloc[0]
                - 1
            )
            * 100
        )

    # ========================================================
    # TREND SKORU
    # ========================================================

    trend_score = 0.0

    if price > ema20:
        trend_score += 25

    if ema20 > ema50:
        trend_score += 25

    if ema50 > ema200:
        trend_score += 25

    if price > ema200:
        trend_score += 25

    # ========================================================
    # MOMENTUM SKORU
    # ========================================================

    momentum_score = 50.0

    momentum_score += np.clip(
        momentum_20 * 2.0,
        -25,
        25,
    )

    momentum_score += np.clip(
        momentum_60,
        -25,
        25,
    )

    momentum_score = clamp(
        momentum_score
    )

    # ========================================================
    # RSI
    # ========================================================

    rsi_score = score_rsi(
        rsi
    )

    # ========================================================
    # CONFIRMATION
    # ========================================================

    confirmation = (
        trend_score * 0.50
        +
        rsi_score * 0.25
        +
        momentum_score * 0.25
    )

    confirmation = clamp(
        confirmation
    )

    # ========================================================
    # TECHNICAL SCORE
    # ========================================================

    technical_score = (
        trend_score * 0.50
        +
        confirmation * 0.25
        +
        momentum_score * 0.25
    )

    technical_score = clamp(
        technical_score
    )

    # ========================================================
    # HACİM
    # ========================================================

    average_volume_20 = (
        volume
        .tail(20)
        .mean()
    )

    if (
        pd.notna(average_volume_20)
        and average_volume_20 > 0
    ):

        volume_ratio = (
            float(volume.iloc[-1])
            /
            float(average_volume_20)
        )

    else:

        volume_ratio = 0.0

    # ========================================================
    # VOLATİLİTE
    # ========================================================

    volatility = (
        close
        .pct_change()
        .tail(20)
        .std()
        *
        np.sqrt(252)
        *
        100
    )

    if pd.isna(volatility):
        volatility = 0.0

    # ========================================================
    # TREND DURUMU
    # ========================================================

    if (
        price > ema20
        and ema20 > ema50
        and ema50 > ema200
    ):

        trend = "Yükseliş"

    elif (
        price < ema20
        and ema20 < ema50
        and ema50 < ema200
    ):

        trend = "Düşüş"

    else:

        trend = "Nötr"

    # ========================================================
    # DESTEK
    # ========================================================

    support = float(
        df["Low"]
        .tail(20)
        .min()
    )

    # ========================================================
    # DİRENÇ
    # ========================================================

    resistance = float(
        df["High"]
        .tail(20)
        .max()
    )

    # ========================================================
    # MACD
    # ========================================================

    macd = float(
        df["MACD"].iloc[-1]
    )

    signal = float(
        df["MACD_SIGNAL"].iloc[-1]
    )

    # ========================================================
    # BOLLINGER
    # ========================================================

    bb_mid = (
        close
        .rolling(20)
        .mean()
    )

    bb_std = (
        close
        .rolling(20)
        .std()
    )

    bb_upper = (
        bb_mid
        +
        2 * bb_std
    ).iloc[-1]

    bb_lower = (
        bb_mid
        -
        2 * bb_std
    ).iloc[-1]

    # ========================================================
    # ATR
    # ========================================================

    atr = float(
        df["ATR"].iloc[-1]
    )

    # ========================================================
    # RADAR SCORE
    # ========================================================

    volume_score = clamp(
        volume_ratio * 50
    )

    radar_score = (
        technical_score * 0.50
        +
        momentum_score * 0.25
        +
        volume_score * 0.15
        +
        rsi_score * 0.10
    )

    radar_score = clamp(
        radar_score
    )

    # ========================================================
    # GÜNLÜK DEĞİŞİM
    # ========================================================

    if len(close) >= 2:

        change_percent = (
            (
                close.iloc[-1]
                /
                close.iloc[-2]
                - 1
            )
            * 100
        )

    else:

        change_percent = 0.0

    # ========================================================
    # SONUÇ
    # ========================================================

    return {

        "price": price,

        "ema20": ema20,

        "ema50": ema50,

        "ema200": ema200,

        "rsi": rsi,

        "macd": macd,

        "signal": signal,

        "bollinger_upper": float(
            bb_upper
        ),

        "bollinger_lower": float(
            bb_lower
        ),

        "atr": atr,

        "momentum": float(
            momentum_20
        ),

        "volatility": float(
            volatility
        ),

        "support": support,

        "resistance": resistance,

        "trend": trend,

        "trend_strength": float(
            trend_score
        ),

        "ai_score": float(
            technical_score
        ),

        "radar_score": float(
            radar_score
        ),

        "score": float(
            technical_score
        ),

        "technical_score": float(
            technical_score
        ),

        "momentum_60_score": float(
            momentum_score
        ),

        "momentum_score": float(
            momentum_score
        ),

        "trend_score": float(
            trend_score
        ),

        "volume_ratio": float(
            volume_ratio
        ),

        "year_return": float(
            year_return
        ),

        "return_1y": float(
            year_return
        ),

        "change": float(
            change_percent
        ),

        "change_percent": float(
            change_percent
        ),

        "last_price": price,

        "close": price,
    }


# ============================================================
# YAHOO FINANCE VERİSİ
# ============================================================

def download_symbol(
    symbol,
    period,
):

    ticker = yahoo_symbol(
        symbol
    )

    if not ticker:

        return (
            None,
            "Geçersiz sembol",
        )

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

            return (
                None,
                "Yahoo Finance veri döndürmedi",
            )

        # ====================================================
        # MULTIINDEX
        # ====================================================

        if isinstance(
            data.columns,
            pd.MultiIndex,
        ):

            data.columns = (
                data.columns
                .get_level_values(0)
            )

        # ====================================================
        # GEREKLİ KOLONLAR
        # ====================================================

        required = [

            "Open",
            "High",
            "Low",
            "Close",
            "Volume",
        ]

        missing = [

            column

            for column in required

            if column not in data.columns
        ]

        if missing:

            return (
                None,
                f"Eksik kolon: {missing}",
            )

        data = data[
            required
        ].copy()

        # ====================================================
        # SAYISAL
        # ====================================================

        for column in required:

            data[column] = pd.to_numeric(
                data[column],
                errors="coerce",
            )

        data = data.dropna(
            subset=["Close"]
        )

        # ====================================================
        # MINIMUM VERİ
        # ====================================================

        if len(data) < MIN_BARS:

            return (
                None,
                f"Yetersiz veri: {len(data)} bar",
            )

        # ====================================================
        # EMA 20
        # ====================================================

        data["EMA20"] = (
            data["Close"]
            .ewm(
                span=20,
                adjust=False,
            )
            .mean()
        )

        # ====================================================
        # EMA 50
        # ====================================================

        data["EMA50"] = (
            data["Close"]
            .ewm(
                span=50,
                adjust=False,
            )
            .mean()
        )

        # ====================================================
        # EMA 200
        # ====================================================

        data["EMA200"] = (
            data["Close"]
            .ewm(
                span=200,
                adjust=False,
            )
            .mean()
        )

        # ====================================================
        # RSI
        # ====================================================

        data["RSI"] = calculate_rsi(
            data["Close"]
        )

        # ====================================================
        # ATR
        # ====================================================

        data["ATR"] = calculate_atr(
            data
        )

        # ====================================================
        # MACD
        # ====================================================

        (
            data["MACD"],
            data["MACD_SIGNAL"],
        ) = calculate_macd(
            data["Close"]
        )

        # ====================================================
        # TEKNİK NULL SATIRLARI
        # ====================================================

        data = data.dropna(
            subset=[

                "EMA20",
                "EMA50",
                "EMA200",
                "RSI",
                "ATR",
                "MACD",
                "MACD_SIGNAL",
            ]
        )

        if data.empty:

            return (
                None,
                "Teknik indikatörler üretilemedi",
            )

        return (
            data,
            None,
        )

    except Exception as exc:

        return (
            None,
            f"{type(exc).__name__}: {exc}",
        )


# ============================================================
# FİYAT GEÇMİŞİNİ KAYDET
# ============================================================

def save_price_history(
    conn,
    symbol,
    data,
):

    rows = 0

    for index, row in data.iterrows():

        try:

            if hasattr(
                index,
                "date",
            ):

                price_date = (
                    index
                    .date()
                    .isoformat()
                )

            else:

                price_date = str(
                    index
                )[:10]

            conn.execute(
                """
                INSERT OR REPLACE INTO stock_prices (

                    symbol,
                    price_date,

                    open,
                    high,
                    low,
                    close,
                    volume,

                    created_at

                )

                VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?
                )
                """,
                (
                    symbol,
                    price_date,

                    float(row["Open"]),

                    float(row["High"]),

                    float(row["Low"]),

                    float(row["Close"]),

                    (
                        float(row["Volume"])
                        if pd.notna(
                            row["Volume"]
                        )
                        else 0.0
                    ),

                    datetime.now().isoformat(
                        timespec="seconds"
                    ),
                ),
            )

            rows += 1

        except Exception:

            continue

    return rows


# ============================================================
# TEKNİK SNAPSHOT KAYDET
# ============================================================

def save_technical_snapshot(
    conn,
    symbol,
    data,
    scores,
):

    last_index = data.index[-1]

    if hasattr(
        last_index,
        "date",
    ):

        analysis_date = (
            last_index
            .date()
            .isoformat()
        )

    else:

        analysis_date = str(
            last_index
        )[:10]

    now = datetime.now().isoformat(
        timespec="seconds"
    )

    columns = [

        "symbol",

        "analysis_date",

        "price",

        "ema20",

        "ema50",

        "ema200",

        "rsi",

        "macd",

        "signal",

        "bollinger_upper",

        "bollinger_lower",

        "atr",

        "momentum",

        "volatility",

        "support",

        "resistance",

        "trend",

        "trend_strength",

        "ai_score",

        "radar_score",

        "score",

        "technical_score",

        "momentum_60_score",

        "momentum_score",

        "trend_score",

        "volume_ratio",

        "year_return",

        "return_1y",

        "change",

        "change_percent",

        "last_price",

        "close",

        "updated_at",

        "created_at",
    ]

    values = (

        symbol,

        analysis_date,

        scores["price"],

        scores["ema20"],

        scores["ema50"],

        scores["ema200"],

        scores["rsi"],

        scores["macd"],

        scores["signal"],

        scores["bollinger_upper"],

        scores["bollinger_lower"],

        scores["atr"],

        scores["momentum"],

        scores["volatility"],

        scores["support"],

        scores["resistance"],

        scores["trend"],

        scores["trend_strength"],

        scores["ai_score"],

        scores["radar_score"],

        scores["score"],

        scores["technical_score"],

        scores["momentum_60_score"],

        scores["momentum_score"],

        scores["trend_score"],

        scores["volume_ratio"],

        scores["year_return"],

        scores["return_1y"],

        scores["change"],

        scores["change_percent"],

        scores["last_price"],

        scores["close"],

        now,

        now,
    )

    placeholders = ",".join(
        ["?"] * len(columns)
    )

    conn.execute(
        f"""
        INSERT OR REPLACE INTO technical_analysis (

            {",".join(columns)}

        )

        VALUES (

            {placeholders}

        )
        """,
        values,
    )


# ============================================================
# DURUM GÜNCELLE
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

        now = datetime.now().isoformat(
            timespec="seconds"
        )

        conn.execute(
            """
            UPDATE data_update_status

            SET

                status = ?,

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
                status,

                now,

                success_at,

                "Yahoo Finance",

                period,

                universe,

                total,

                success,

                failed,

                price_rows,

                technical_rows,

                error,
            ),
        )

        conn.commit()

    finally:

        conn.close()


# ============================================================
# GÜNCELLEME MOTORU
# ============================================================

def run_update(
    symbols,
    period,
    progress_bar,
    status_text,
    pause_seconds=DEFAULT_PAUSE,
):

    total = len(symbols)

    success_count = 0

    failed_count = 0

    price_rows = 0

    technical_rows = 0

    errors = []

    # ========================================================
    # RUNNING
    # ========================================================

    update_status(
        status="RUNNING",

        period=period,

        universe="BIST500",

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

        # ====================================================
        # TÜM BIST 500
        # ====================================================

        for i, symbol in enumerate(
            symbols,
            start=1,
        ):

            progress = (
                i
                /
                max(total, 1)
            )

            progress_bar.progress(
                progress
            )

            status_text.write(
                f"🔄 **{symbol}** "
                f"güncelleniyor... "
                f"({i}/{total})"
            )

            # =================================================
            # YAHOO
            # =================================================

            data, error = download_symbol(
                symbol,
                period,
            )

            if data is None:

                failed_count += 1

                errors.append(
                    f"{symbol}: {error}"
                )

                continue

            # =================================================
            # DB
            # =================================================

            try:

                saved_prices = (
                    save_price_history(
                        conn,
                        symbol,
                        data,
                    )
                )

                price_rows += saved_prices

                # ---------------------------------------------
                # SKOR
                # ---------------------------------------------

                scores = calculate_scores(
                    data
                )

                # ---------------------------------------------
                # SNAPSHOT
                # ---------------------------------------------

                save_technical_snapshot(
                    conn,
                    symbol,
                    data,
                    scores,
                )

                technical_rows += 1

                success_count += 1

                conn.commit()

            except Exception as exc:

                failed_count += 1

                conn.rollback()

                errors.append(
                    f"{symbol}: "
                    f"{type(exc).__name__}: "
                    f"{exc}"
                )

            # =================================================
            # PAUSE
            # =================================================

            if pause_seconds > 0:

                time.sleep(
                    pause_seconds
                )

        # ====================================================
        # SON DURUM
        # ====================================================

        if (
            success_count > 0
            and failed_count == 0
        ):

            final_status = "SUCCESS"

        elif success_count > 0:

            final_status = "PARTIAL"

        else:

            final_status = "FAILED"

        # ====================================================
        # BAŞARI ZAMANI
        # ====================================================

        success_at = (

            datetime.now().isoformat(
                timespec="seconds"
            )

            if success_count > 0

            else None
        )

        # ====================================================
        # STATUS
        # ====================================================

        update_status(

            status=final_status,

            period=period,

            universe="BIST500",

            total=total,

            success=success_count,

            failed=failed_count,

            price_rows=price_rows,

            technical_rows=technical_rows,

            error="\n".join(
                errors[:100]
            ),

            success_at=success_at,
        )

        return {

            "status":
                final_status,

            "total":
                total,

            "success":
                success_count,

            "failed":
                failed_count,

            "price_rows":
                price_rows,

            "technical_rows":
                technical_rows,

            "errors":
                errors,
        }

    finally:

        conn.close()


# ============================================================
# GÜNCELLEME DURUMUNU OKU
# ============================================================

def get_update_status():

    conn = get_connection()

    try:

        row = conn.execute(
            """
            SELECT *

            FROM data_update_status

            WHERE id = 1
            """
        ).fetchone()

        if row:

            return dict(row)

        return {}

    finally:

        conn.close()


# ============================================================
# SNAPSHOT İSTATİSTİKLERİ
# ============================================================

def get_snapshot_stats():

    conn = get_connection()

    try:

        technical_count = conn.execute(
            """
            SELECT COUNT(*)

            FROM technical_analysis
            """
        ).fetchone()[0]

        unique_symbols = conn.execute(
            """
            SELECT COUNT(
                DISTINCT symbol
            )

            FROM technical_analysis
            """
        ).fetchone()[0]

        latest_date = conn.execute(
            """
            SELECT MAX(
                analysis_date
            )

            FROM technical_analysis
            """
        ).fetchone()[0]

        price_count = conn.execute(
            """
            SELECT COUNT(*)

            FROM stock_prices
            """
        ).fetchone()[0]

        universe_count = conn.execute(
            """
            SELECT COUNT(*)

            FROM bist500_universe

            WHERE active = 1
            """
        ).fetchone()[0]

        return {

            "technical_count":
                technical_count,

            "unique_symbols":
                unique_symbols,

            "latest_date":
                latest_date,

            "price_count":
                price_count,

            "universe_count":
                universe_count,
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

st.title(
    "🔄 BIST AI PRO — BIST 500 Veri Güncelleme"
)

st.caption(
    "BIST 500 → Yahoo Finance → "
    "stock_prices → technical_analysis → "
    "Dinamik Portföy"
)

st.info(
    """
    ℹ️ Güncelleme evreni `stocks` tablosundan
    bağımsızdır.

    Gerçek tarama evreni:
    `bist500_universe`

    Böylece `stocks` tablosunda yalnızca
    11 hisse bulunması BIST 500 taramasını
    engellemez.
    """
)


# ============================================================
# ÜST METRİKLER
# ============================================================

c1, c2, c3, c4, c5 = st.columns(5)

with c1:

    st.metric(
        "BIST 500 Evren",
        stats["universe_count"],
    )

with c2:

    st.metric(
        "Teknik Hisse",
        stats["unique_symbols"],
    )

with c3:

    st.metric(
        "Fiyat Kaydı",
        f"{stats['price_count']:,}",
    )

with c4:

    st.metric(
        "Teknik Kayıt",
        f"{stats['technical_count']:,}",
    )

with c5:

    st.metric(
        "Son Teknik Tarih",
        (
            stats["latest_date"]
            if stats["latest_date"]
            else "Yok"
        ),
    )


# ============================================================
# BIST 500 EVREN YÜKLEME
#
# ÖNEMLİ:
# Bu bölüm universe boş olsa bile çalışır.
# ============================================================

st.divider()

st.subheader(
    "📥 BIST 500 Evrenini Yükle"
)

st.info(
    """
    BIST 500 listesini CSV veya Excel dosyası
    olarak yükleyebilirsiniz.

    Zorunlu kolonlardan biri:

    `symbol`
    `sembol`
    `ticker`
    `kod`
    `hisse`

    İsteğe bağlı:

    `company`
    `sector`
    `industry`
    """
)

uploaded_bist500 = st.file_uploader(
    "BIST 500 dosyasını seçin",
    type=[
        "csv",
        "xlsx",
        "xls",
    ],
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


# ============================================================
# DOSYA YÜKLE
# ============================================================

if upload_button:

    if uploaded_bist500 is None:

        st.warning(
            "⚠️ Önce CSV veya Excel dosyasını seçin."
        )

    else:

        with st.spinner(
            "BIST 500 evreni veritabanına yükleniyor..."
        ):

            result = import_bist500_file(
                uploaded_bist500
            )

        if result["success"]:

            st.success(
                "🟢 "
                + result["message"]
            )

            # -----------------------------------------------
            # BIST500 → STOCKS
            # -----------------------------------------------

            synced = (
                sync_bist500_to_stocks()
            )

            st.info(
                f"🔄 {synced} hisse "
                "`stocks` tablosuyla senkronize edildi."
            )

            st.rerun()

        else:

            st.error(
                "🔴 "
                + result["message"]
            )


# ============================================================
# EVRENİ YENİDEN OKU
# ============================================================

if reload_universe:

    universe_df = get_bist500_symbols()

    st.success(
        f"🔄 Veritabanı evreni yeniden okundu: "
        f"**{len(universe_df)} hisse**"
    )


# ============================================================
# GÜNCEL EVREN
# ============================================================

universe_df = get_bist500_symbols()

universe_count = len(
    universe_df
)


# ============================================================
# EVREN DURUMU
# ============================================================

st.subheader(
    "📌 BIST 500 Evren Durumu"
)

if universe_count == 500:

    st.success(
        f"🟢 BIST 500 evreni hazır — "
        f"**{universe_count} hisse**"
    )

elif universe_count > 0:

    st.warning(
        f"🟡 BIST 500 evreni eksik — "
        f"**{universe_count} hisse**"
    )

else:

    st.warning(
        """
        🟡 BIST 500 evreninde henüz hisse yok.

        Yukarıdaki **BIST 500 LİSTESİNİ YÜKLE**
        butonundan CSV veya Excel dosyanızı yükleyin.
        """
    )


# ============================================================
# EVREN YOKSA BURADAN SONRA DUR
#
# ÖNEMLİ:
# Upload bölümü yukarıda olduğu için
# yükleme butonu artık kaybolmaz.
# ============================================================

if universe_df.empty:

    st.info(
        "📥 Veri güncellemesini başlatabilmek için "
        "önce BIST 500 evrenini yükleyin."
    )

    st.stop()


# ============================================================
# SEÇİLECEK HİSSELER
# ============================================================

selected_symbols = (

    universe_df["symbol"]

    .astype(str)

    .str.upper()

    .str.strip()

    .drop_duplicates()

    .tolist()
)


# ============================================================
# SEÇİM BİLGİSİ
# ============================================================

st.write(
    "🎯 Güncellenecek evren: "
    "**BIST 500**"
)

st.write(
    "📊 Güncellenecek hisse sayısı: "
    f"**{len(selected_symbols)}**"
)


# ============================================================
# STOCKS SENKRONİZASYON
# ============================================================

st.divider()

st.subheader(
    "🔄 BIST 500 → STOCKS"
)

st.caption(
    "Bu işlem BIST 500 evrenini `stocks` tablosuna "
    "senkronize eder. Veri güncelleme motorunun "
    "tarama evreni yine `bist500_universe` tablosudur."
)

sync_stocks = st.button(
    "🔄 BIST 500 → STOCKS SENKRONİZE ET",
    use_container_width=True,
)


if sync_stocks:

    count = sync_bist500_to_stocks()

    st.success(
        f"🟢 {count} BIST 500 hissesi "
        "`stocks` tablosuyla senkronize edildi."
    )


# ============================================================
# GÜNCELLEME AYARLARI
# ============================================================

st.divider()

st.subheader(
    "⚙️ Güncelleme Ayarları"
)

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


period = PERIODS[
    period_label
]


# ============================================================
# GÜNCELLEME BUTONU
# ============================================================

st.divider()

st.subheader(
    "🚀 Veri Güncelleme Motoru"
)

st.write(
    f"Yahoo Finance'e gönderilecek hisse sayısı: "
    f"**{len(selected_symbols)}**"
)

st.caption(
    "Bu işlem BIST 500 evrenindeki tüm aktif "
    "hisseleri tek tek tarar."
)

start_update = st.button(
    "🚀 BIST 500 VERİ GÜNCELLEMESİNİ BAŞLAT",
    type="primary",
    use_container_width=True,
)


# ============================================================
# GÜNCELLEME
# ============================================================

if start_update:

    st.divider()

    st.subheader(
        "⏳ BIST 500 taraması çalışıyor..."
    )

    progress = st.progress(
        0
    )

    status_text = st.empty()

    start_time = time.time()

    result = run_update(

        symbols=selected_symbols,

        period=period,

        progress_bar=progress,

        status_text=status_text,

        pause_seconds=pause_seconds,
    )

    elapsed = (
        time.time()
        -
        start_time
    )

    progress.progress(
        1.0
    )

    st.divider()

    # ========================================================
    # SONUÇ
    # ========================================================

    if result["status"] == "SUCCESS":

        st.success(
            "✅ BIST 500 veri güncellemesi "
            "başarıyla tamamlandı."
        )

    elif result["status"] == "PARTIAL":

        st.warning(
            "⚠️ BIST 500 veri güncellemesi "
            "kısmen tamamlandı."
        )

    else:

        st.error(
            "❌ BIST 500 veri güncellemesi "
            "başarısız."
        )

    # ========================================================
    # SONUÇ METRİKLERİ
    # ========================================================

    r1, r2, r3, r4, r5 = st.columns(5)

    with r1:

        st.metric(
            "Taranan",
            result["total"],
        )

    with r2:

        st.metric(
            "Başarılı",
            result["success"],
        )

    with r3:

        st.metric(
            "Başarısız",
            result["failed"],
        )

    with r4:

        st.metric(
            "Fiyat Satırı",
            f"{result['price_rows']:,}",
        )

    with r5:

        st.metric(
            "Teknik Snapshot",
            result["technical_rows"],
        )

    st.caption(
        f"Toplam süre: "
        f"{elapsed:.1f} saniye"
    )

    # ========================================================
    # HATALAR
    # ========================================================

    if result["errors"]:

        with st.expander(
            "⚠️ Hata / Eksik Veri "
            f"({len(result['errors'])})"
        ):

            for error in result["errors"]:

                st.write(
                    f"- {error}"
                )


# ============================================================
# MOTOR DURUMU
# ============================================================

st.divider()

st.subheader(
    "📊 Veri Motoru Durumu"
)

status = get_update_status()

if status:

    s1, s2, s3, s4 = st.columns(4)

    with s1:

        st.metric(
            "Durum",
            status.get(
                "status",
                "NEVER",
            ),
        )

    with s2:

        st.metric(
            "Başarılı",
            status.get(
                "symbols_success",
                0,
            ),
        )

    with s3:

        st.metric(
            "Başarısız",
            status.get(
                "symbols_failed",
                0,
            ),
        )

    with s4:

        st.metric(
            "Snapshot",
            status.get(
                "technical_rows",
                0,
            ),
        )

    last_attempt = status.get(
        "last_attempt_at"
    )

    last_success = status.get(
        "last_success_at"
    )

    if last_attempt:

        st.caption(
            f"Son deneme: **{last_attempt}**"
        )

    if last_success:

        st.success(
            "🟢 Son başarılı veri: "
            f"**{last_success}**"
        )

    else:

        st.warning(
            "🟡 Henüz başarılı bir veri güncellemesi yok."
        )


# ============================================================
# SNAPSHOT KONTROL
# ============================================================

st.divider()

st.subheader(
    "🧪 Dinamik Portföy İçin Snapshot Kontrolü"
)

conn = get_connection()

try:

    latest = conn.execute(
        """
        SELECT

            COUNT(*) AS rows_count,

            COUNT(
                DISTINCT symbol
            ) AS symbols_count,

            MAX(
                analysis_date
            ) AS latest_date

        FROM technical_analysis
        """
    ).fetchone()

    latest_rows = dict(
        latest
    )

finally:

    conn.close()


if latest_rows["symbols_count"] > 0:

    st.success(
        "🟢 Geçerli teknik snapshot mevcut. "

        f"{latest_rows['symbols_count']} hisse / "

        f"{latest_rows['rows_count']} teknik kayıt / "

        f"son piyasa tarihi: "

        f"{latest_rows['latest_date']}"
    )

else:

    st.error(
        "🔴 technical_analysis içinde "
        "henüz geçerli snapshot yok."
    )


# ============================================================
# VERİ AKIŞI
# ============================================================

st.divider()

st.subheader(
    "🔗 Veri Akışı"
)

st.code(
    """
BIST 500
   ↓
bist500_universe
   ↓
BIST 500 sembolleri
   ↓
Yahoo Finance
   ↓
stock_prices
   ↓
Teknik indikatörler
   ↓
technical_analysis
   ↓
Dinamik Portföy
""",
    language="text",
)

st.caption(
    "Temel/KAP finansal skorları bu motor "
    "tarafından silinmez veya değiştirilmez."
)

st.caption(
    "Teknik veri kaynağı: Yahoo Finance"
)

st.caption(
    "Tarama evreni: bist500_universe"
)

st.caption(
    "stocks tablosu yalnızca sistem içi "
    "senkronizasyon için kullanılır."
)