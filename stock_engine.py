# ============================================================
# BIST AI PRO
# stock_engine.py
#
# ORTAK HİSSE ANALİZ MOTORU
#
# V4 - DATABASE FIRST / OPPORTUNITY CENTER READY
#
# KULLANAN SAYFALAR:
#   - Günlük Trade
#   - Dinamik Portföy
#   - Tarama
#   - Hisse Fırsat Merkezi
#
# VERİ ÖNCELİĞİ:
#
#     borsa.db
#          ↓
#     stock_prices
#          ↓
#     technical_analysis
#          ↓
#     finansal skor
#          ↓
#     sektör skor
#          ↓
#     piyasa skor
#          ↓
#     teknik skor
#          ↓
#     4 VADE
#
# Yahoo Finance:
#     SADECE DB'de yeterli veri bulunamazsa fallback
#
# ============================================================

import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf


# ============================================================
# AYARLAR
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "borsa.db"

HISTORY_PERIOD = "1y"

DEFAULT_MIN_LIQUIDITY = 10_000_000

# DB'de yeterli veri yoksa Yahoo kullanılabilir.
ALLOW_YAHOO_FALLBACK = True

# Minimum teknik veri
MIN_HISTORY_ROWS = 60

# Opportunity Center için minimum veri
MIN_OPPORTUNITY_ROWS = 60


# ============================================================
# TICKER
# ============================================================

def normalize_ticker(value):

    if value is None:
        return None

    try:
        ticker = str(value).upper().strip()
    except Exception:
        return None

    ticker = ticker.replace(".IS", "")
    ticker = ticker.replace(" BIST", "")
    ticker = ticker.replace("$", "")
    ticker = ticker.replace(" ", "")

    if ticker.endswith("."):
        ticker = ticker[:-1]

    return ticker or None


def yahoo_symbol(ticker):

    ticker = normalize_ticker(ticker)

    if not ticker:
        return None

    return f"{ticker}.IS"


# ============================================================
# DB BAĞLANTISI
# ============================================================

def db_connect():

    if not DB_PATH.exists():
        return None

    try:
        return sqlite3.connect(DB_PATH)
    except Exception:
        return None


# ============================================================
# TABLO İSİMLERİ
# ============================================================

def get_table_names():

    conn = db_connect()

    if conn is None:
        return []

    try:

        df = pd.read_sql_query(
            """
            SELECT name
            FROM sqlite_master
            WHERE type='table'
            """,
            conn,
        )

        conn.close()

        if df.empty:
            return []

        return df["name"].astype(str).tolist()

    except Exception:

        try:
            conn.close()
        except Exception:
            pass

        return []


# ============================================================
# TABLO SÜTUNLARI
# ============================================================

def get_table_columns(table_name):

    if not table_name:
        return []

    conn = db_connect()

    if conn is None:
        return []

    try:

        df = pd.read_sql_query(
            f'PRAGMA table_info("{table_name}")',
            conn,
        )

        conn.close()

        if df.empty:
            return []

        return df["name"].astype(str).tolist()

    except Exception:

        try:
            conn.close()
        except Exception:
            pass

        return []


# ============================================================
# SÜTUN BULUCU
# ============================================================

def find_column(
    columns,
    candidates,
):

    if columns is None:
        return None

    try:
        if len(columns) == 0:
            return None
    except Exception:
        return None

    if candidates is None:
        return None

    try:
        if len(candidates) == 0:
            return None
    except Exception:
        return None

    lower_map = {
        str(c).lower(): c
        for c in columns
    }

    # Tam eşleşme
    for candidate in candidates:

        key = str(candidate).lower()

        if key in lower_map:
            return lower_map[key]

    # Normalize edilmiş eşleşme
    def normalize_name(value):

        return (
            str(value)
            .lower()
            .replace("_", "")
            .replace(" ", "")
            .replace("-", "")
            .replace(".", "")
        )

    normalized = {
        normalize_name(c): c
        for c in columns
    }

    for candidate in candidates:

        key = normalize_name(candidate)

        if key in normalized:
            return normalized[key]

    return None
    # --------------------------------------------------------
    # TAM EŞLEŞME
    # --------------------------------------------------------

    for candidate in candidates:

        key = str(candidate).lower()

        if key in lower_map:
            return lower_map[key]

    # --------------------------------------------------------
    # NORMALİZE EŞLEŞME
    # --------------------------------------------------------

    def normalize_name(value):

        return (
            str(value)
            .lower()
            .replace("_", "")
            .replace(" ", "")
            .replace("-", "")
            .replace(".", "")
            .replace("/", "")
        )

    normalized = {
        normalize_name(c): c
        for c in columns
    }

    for candidate in candidates:

        key = normalize_name(candidate)

        if key in normalized:
            return normalized[key]

    return None


# ============================================================
# GÜVENLİ FLOAT
# ============================================================

def scalar(value, default=np.nan):

    try:

        if isinstance(value, pd.Series):

            if value.empty:
                return default

            value = value.iloc[0]

        if isinstance(value, np.ndarray):

            if value.size == 0:
                return default

            value = value.flatten()[0]

        value = float(value)

        if np.isfinite(value):
            return value

    except Exception:
        pass

    return default


# ============================================================
# SKOR SINIRLAMA
# ============================================================

def clamp_score(value, default=50.0):

    try:

        value = float(value)

        if not np.isfinite(value):
            return default

        return float(
            np.clip(
                value,
                0,
                100,
            )
        )

    except Exception:

        return default


# ============================================================
# OHLCV TEMİZLE
# ============================================================

def clean_ohlcv(df):

    if df is None or df.empty:
        return None

    df = df.copy()

    # --------------------------------------------------------
    # MULTIINDEX
    # --------------------------------------------------------

    if isinstance(df.columns, pd.MultiIndex):

        df.columns = [
            str(c[0])
            for c in df.columns
        ]

    # --------------------------------------------------------
    # SÜTUN İSİMLERİ
    # --------------------------------------------------------

    rename_map = {}

    for column in df.columns:

        low = str(column).lower().strip()

        if low == "open":
            rename_map[column] = "Open"

        elif low == "high":
            rename_map[column] = "High"

        elif low == "low":
            rename_map[column] = "Low"

        elif low == "close":
            rename_map[column] = "Close"

        elif low in [
            "adj close",
            "adj_close",
        ]:
            rename_map[column] = "Adj Close"

        elif low == "volume":
            rename_map[column] = "Volume"

    df = df.rename(
        columns=rename_map
    )

    # --------------------------------------------------------
    # GEREKLİ SÜTUNLAR
    # --------------------------------------------------------

    required = [
        "Open",
        "High",
        "Low",
        "Close",
        "Volume",
    ]

    # Eksik OHLC sütunları varsa Close ile tamamla
    if "Close" not in df.columns:
        return None

    if "Open" not in df.columns:
        df["Open"] = df["Close"]

    if "High" not in df.columns:
        df["High"] = df["Close"]

    if "Low" not in df.columns:
        df["Low"] = df["Close"]

    if "Volume" not in df.columns:
        df["Volume"] = 0

    # --------------------------------------------------------
    # NUMERİK
    # --------------------------------------------------------

    for column in required:

        if column not in df.columns:
            continue

        df[column] = pd.to_numeric(
            df[column],
            errors="coerce",
        )

    df = df.dropna(
        subset=["Close"]
    )

    if df.empty:
        return None

    # --------------------------------------------------------
    # TARİH
    # --------------------------------------------------------

    if not isinstance(
        df.index,
        pd.DatetimeIndex,
    ):

        date_column = find_column(
            df.columns,
            [
                "date",
                "datetime",
                "timestamp",
                "tarih",
                "price_date",
            ],
        )

        if date_column:

            df[date_column] = pd.to_datetime(
                df[date_column],
                errors="coerce",
            )

            df = df.dropna(
                subset=[date_column]
            )

            if not df.empty:
                df = df.set_index(
                    date_column
                )

    try:
        df = df.sort_index()
    except Exception:
        pass

    return df


# ============================================================
# EVREN
# ============================================================

def get_universe():

    tables = get_table_names()

    preferred_tables = [
        "bist500_universe",
        "stocks",
    ]

    table = next(
        (
            t
            for t in preferred_tables
            if t in tables
        ),
        None,
    )

    if table is None:
        return []

    conn = db_connect()

    if conn is None:
        return []

    try:

        df = pd.read_sql_query(
            f'SELECT * FROM "{table}"',
            conn,
        )

        conn.close()

    except Exception:

        try:
            conn.close()
        except Exception:
            pass

        return []

    if df.empty:
        return []

    symbol_column = find_column(
        df.columns,
        [
            "symbol",
            "ticker",
            "code",
            "hisse",
            "hisse_kodu",
            "stock",
            "stock_code",
        ],
    )

    if symbol_column is None:
        return []

    result = []

    for value in df[symbol_column].dropna():

        ticker = normalize_ticker(value)

        if ticker and ticker not in result:
            result.append(ticker)

    return result


# ============================================================
# DB'DEN HAM FİYAT VERİSİ
# ============================================================

def load_price_history_from_db(ticker):

    ticker = normalize_ticker(ticker)

    if not ticker:
        return None

    tables = get_table_names()

    if "stock_prices" not in tables:
        return None

    columns = get_table_columns(
        "stock_prices"
    )

    if not columns:
        return None

    symbol_column = find_column(
        columns,
        [
            "symbol",
            "ticker",
            "code",
            "hisse",
            "hisse_kodu",
            "stock",
        ],
    )

    date_column = find_column(
        columns,
        [
            "date",
            "datetime",
            "timestamp",
            "tarih",
            "price_date",
        ],
    )

    open_column = find_column(
        columns,
        [
            "Open",
            "open",
            "acilis",
        ],
    )

    high_column = find_column(
        columns,
        [
            "High",
            "high",
            "yuksek",
        ],
    )

    low_column = find_column(
        columns,
        [
            "Low",
            "low",
            "dusuk",
        ],
    )

    close_column = find_column(
        columns,
        [
            "Close",
            "close",
            "kapanis",
            "price",
            "fiyat",
        ],
    )

    volume_column = find_column(
        columns,
        [
            "Volume",
            "volume",
            "hacim",
        ],
    )

    if (
        symbol_column is None
        or date_column is None
        or close_column is None
    ):
        return None

    select_columns = [
        f'"{date_column}" AS Date',
        f'"{close_column}" AS Close',
    ]

    if open_column:

        select_columns.append(
            f'"{open_column}" AS Open'
        )

    else:

        select_columns.append(
            f'"{close_column}" AS Open'
        )

    if high_column:

        select_columns.append(
            f'"{high_column}" AS High'
        )

    else:

        select_columns.append(
            f'"{close_column}" AS High'
        )

    if low_column:

        select_columns.append(
            f'"{low_column}" AS Low'
        )

    else:

        select_columns.append(
            f'"{close_column}" AS Low'
        )

    if volume_column:

        select_columns.append(
            f'"{volume_column}" AS Volume'
        )

    else:

        select_columns.append(
            "0 AS Volume"
        )

    conn = db_connect()

    if conn is None:
        return None

    try:

        query = f"""
            SELECT
                {", ".join(select_columns)}
            FROM "stock_prices"
            WHERE UPPER(
                REPLACE(
                    REPLACE(
                        REPLACE(
                            "{symbol_column}",
                            '.IS',
                            ''
                        ),
                        ' BIST',
                        ''
                    ),
                    ' ',
                    ''
                )
            ) = ?
            ORDER BY "{date_column}" ASC
        """

        df = pd.read_sql_query(
            query,
            conn,
            params=[ticker],
        )

        conn.close()

    except Exception:

        try:
            conn.close()
        except Exception:
            pass

        return None

    if df.empty:
        return None

    df["Date"] = pd.to_datetime(
        df["Date"],
        errors="coerce",
    )

    df = df.dropna(
        subset=["Date"]
    )

    if df.empty:
        return None

    df = df.set_index(
        "Date"
    )

    return clean_ohlcv(df)


# ============================================================
# TECHNICAL ANALYSIS SNAPSHOT
#
# Bazı sistemlerde teknik_analysis tablosu hazır snapshot
# olarak tutuluyor.
#
# Bu fonksiyon doğrudan kullanılmasa bile motorun DB-first
# mimarisini destekler.
# ============================================================

def load_technical_snapshot(ticker=None):

    tables = get_table_names()

    possible_tables = [
        "technical_analysis",
        "technical_snapshot",
    ]

    table = next(
        (
            t
            for t in possible_tables
            if t in tables
        ),
        None,
    )

    if table is None:
        return pd.DataFrame()

    conn = db_connect()

    if conn is None:
        return pd.DataFrame()

    try:

        df = pd.read_sql_query(
            f'SELECT * FROM "{table}"',
            conn,
        )

        conn.close()

    except Exception:

        try:
            conn.close()
        except Exception:
            pass

        return pd.DataFrame()

    if df.empty:
        return pd.DataFrame()

    if ticker is None:
        return df

    symbol_column = find_column(
        df.columns,
        [
            "symbol",
            "ticker",
            "code",
            "hisse",
            "hisse_kodu",
        ],
    )

    if symbol_column is None:
        return df

    target = normalize_ticker(
        ticker
    )

    mask = (
        df[symbol_column]
        .astype(str)
        .map(normalize_ticker)
        == target
    )

    return df.loc[mask].copy()


# ============================================================
# YAHOO FALLBACK
# ============================================================

def download_daily(ticker):

    if not ALLOW_YAHOO_FALLBACK:
        return None

    try:

        symbol = yahoo_symbol(
            ticker
        )

        if not symbol:
            return None

        data = yf.download(
            symbol,
            period=HISTORY_PERIOD,
            interval="1d",
            progress=False,
            auto_adjust=False,
            threads=False,
        )

        return clean_ohlcv(
            data
        )

    except Exception:

        return None


# ============================================================
# VERİYİ AL
#
# 1. DB
# 2. DB yetersizse Yahoo
# ============================================================

def get_price_history(ticker):

    df = load_price_history_from_db(
        ticker
    )

    if (
        df is not None
        and len(df) >= MIN_HISTORY_ROWS
    ):

        return df, "DB"

    yahoo_df = download_daily(
        ticker
    )

    if (
        yahoo_df is not None
        and len(yahoo_df) >= MIN_HISTORY_ROWS
    ):

        return yahoo_df, "Yahoo"

    return None, "NONE"


# ============================================================
# TEKNİK GÖSTERGELER
# ============================================================

def calculate_indicators(df):

    df = clean_ohlcv(
        df
    )

    if df is None:
        return None

    if len(df) < MIN_HISTORY_ROWS:
        return None

    df = df.copy()

    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    volume = df["Volume"]

    # ========================================================
    # EMA
    # ========================================================

    for span in [
        5,
        9,
        20,
        50,
        100,
        200,
    ]:

        df[f"EMA{span}"] = (
            close
            .ewm(
                span=span,
                adjust=False,
            )
            .mean()
        )

    # ========================================================
    # RSI 14
    # ========================================================

    delta = close.diff()

    gain = delta.clip(
        lower=0
    )

    loss = -delta.clip(
        upper=0
    )

    avg_gain = gain.ewm(
        alpha=1 / 14,
        adjust=False,
        min_periods=14,
    ).mean()

    avg_loss = loss.ewm(
        alpha=1 / 14,
        adjust=False,
        min_periods=14,
    ).mean()

    rs = (
        avg_gain
        /
        avg_loss.replace(
            0,
            np.nan,
        )
    )

    df["RSI"] = (
        100
        -
        (
            100
            /
            (1 + rs)
        )
    )

    df["RSI"] = (
        df["RSI"]
        .fillna(50)
        .clip(
            0,
            100,
        )
    )

    # ========================================================
    # HACİM
    # ========================================================

    df["VOL20"] = (
        volume
        .rolling(
            20,
            min_periods=10,
        )
        .mean()
    )

    df["VolumeRatio"] = (
        volume
        /
        df["VOL20"].replace(
            0,
            np.nan,
        )
    )

    df["VolumeRatio"] = (
        df["VolumeRatio"]
        .replace(
            [np.inf, -np.inf],
            np.nan,
        )
        .fillna(1)
    )

    # ========================================================
    # ATR 14
    # ========================================================

    prev_close = close.shift(1)

    tr = pd.concat(
        [
            high - low,

            (
                high
                - prev_close
            ).abs(),

            (
                low
                - prev_close
            ).abs(),
        ],
        axis=1,
    ).max(axis=1)

    df["ATR"] = tr.ewm(
        alpha=1 / 14,
        adjust=False,
        min_periods=14,
    ).mean()

    # ========================================================
    # GETİRİ
    # ========================================================

    df["Return_1D"] = (
        close.pct_change(1)
        * 100
    )

    df["Return_5D"] = (
        close.pct_change(5)
        * 100
    )

    df["Return_20D"] = (
        close.pct_change(20)
        * 100
    )

    df["Return_60D"] = (
        close.pct_change(60)
        * 100
    )

    # ========================================================
    # VWAP 20
    # ========================================================

    typical = (
        high
        + low
        + close
    ) / 3

    pv = (
        typical
        * volume
    ).rolling(
        20,
        min_periods=5,
    ).sum()

    vv = (
        volume
        .rolling(
            20,
            min_periods=5,
        ).sum()
    )

    df["VWAP20"] = (
        pv
        /
        vv.replace(
            0,
            np.nan,
        )
    )

    # ========================================================
    # VOLATİLİTE
    # ========================================================

    df["Volatility20"] = (
        close.pct_change()
        .rolling(
            20,
            min_periods=10,
        )
        .std()
        * 100
    )

    # ========================================================
    # DESTEK
    # ========================================================

    df["Support20"] = (
        low
        .rolling(
            20,
            min_periods=10,
        )
        .min()
    )

    df["Resistance20"] = (
        high
        .rolling(
            20,
            min_periods=10,
        )
        .max()
    )

    return df


# ============================================================
# FİNANSAL SKOR
# ============================================================

def get_financial_scores():

    tables = get_table_names()

    possible_tables = [
        "financial_analysis",
        "financial_scores",
        "fundamental_analysis",
        "fundamental_scores",
    ]

    table = next(
        (
            t
            for t in possible_tables
            if t in tables
        ),
        None,
    )

    if table is None:
        return {}

    conn = db_connect()

    if conn is None:
        return {}

    try:

        df = pd.read_sql_query(
            f'SELECT * FROM "{table}"',
            conn,
        )

        conn.close()

    except Exception:

        try:
            conn.close()
        except Exception:
            pass

        return {}

    if df.empty:
        return {}

    symbol_column = find_column(
        df.columns,
        [
            "symbol",
            "ticker",
            "code",
            "hisse",
            "hisse_kodu",
        ],
    )

    score_column = find_column(
        df.columns,
        [
            "financial_score",
            "fundamental_score",
            "score",
            "skor",
            "Finansal Skor",
        ],
    )

    if (
        symbol_column is None
        or score_column is None
    ):
        return {}

    result = {}

    for _, row in df.iterrows():

        ticker = normalize_ticker(
            row[symbol_column]
        )

        if not ticker:
            continue

        result[ticker] = clamp_score(
            row[score_column]
        )

    return result


# ============================================================
# SEKTÖR SKORU
# ============================================================

def get_sector_scores():

    tables = get_table_names()

    possible_tables = [
        "sector_scores",
        "sector_analysis",
        "sector_strength",
        "sector_score",
    ]

    table = next(
        (
            t
            for t in possible_tables
            if t in tables
        ),
        None,
    )

    if table is None:
        return {}

    conn = db_connect()

    if conn is None:
        return {}

    try:

        df = pd.read_sql_query(
            f'SELECT * FROM "{table}"',
            conn,
        )

        conn.close()

    except Exception:

        try:
            conn.close()
        except Exception:
            pass

        return {}

    if df.empty:
        return {}

    symbol_column = find_column(
        df.columns,
        [
            "symbol",
            "ticker",
            "code",
            "hisse",
            "hisse_kodu",
        ],
    )

    score_column = find_column(
        df.columns,
        [
            "sector_score",
            "sector_strength",
            "score",
            "skor",
            "Sektör Skoru",
            "Sektor Skoru",
        ],
    )

    if (
        symbol_column is None
        or score_column is None
    ):
        return {}

    result = {}

    for _, row in df.iterrows():

        ticker = normalize_ticker(
            row[symbol_column]
        )

        if not ticker:
            continue

        result[ticker] = clamp_score(
            row[score_column]
        )

    return result


# ============================================================
# PİYASA SKORU
# ============================================================

def get_market_score():

    tables = get_table_names()

    possible_tables = [
        "market_score",
        "market_scores",
        "market_analysis",
    ]

    table = next(
        (
            t
            for t in possible_tables
            if t in tables
        ),
        None,
    )

    if table is None:
        return 50.0

    conn = db_connect()

    if conn is None:
        return 50.0

    try:

        df = pd.read_sql_query(
            f'SELECT * FROM "{table}"',
            conn,
        )

        conn.close()

    except Exception:

        try:
            conn.close()
        except Exception:
            pass

        return 50.0

    if df.empty:
        return 50.0

    score_column = find_column(
        df.columns,
        [
            "market_score",
            "score",
            "skor",
            "Piyasa Skoru",
            "Piyasa",
        ],
    )

    if score_column is None:
        return 50.0

    return clamp_score(
        df.iloc[-1][score_column]
    )


# ============================================================
# TREND SKORU
# ============================================================

def trend_score(row):

    price = scalar(
        row.get("Close"),
        0,
    )

    ema9 = scalar(
        row.get("EMA9"),
        0,
    )

    ema20 = scalar(
        row.get("EMA20"),
        0,
    )

    ema50 = scalar(
        row.get("EMA50"),
        0,
    )

    ema200 = scalar(
        row.get("EMA200"),
        0,
    )

    score = 0

    # Fiyat / EMA20
    if price > ema20:
        score += 25

    elif price >= ema20 * 0.985:
        score += 15

    # EMA9 / EMA20
    if ema9 > ema20:
        score += 20

    # EMA20 / EMA50
    if ema20 > ema50:
        score += 20

    # EMA50 / EMA200
    if ema50 > ema200:
        score += 20

    # 20 günlük momentum
    ret20 = scalar(
        row.get("Return_20D"),
        0,
    )

    if ret20 > 5:
        score += 15

    elif ret20 > 0:
        score += 10

    return float(
        min(
            score,
            100,
        )
    )


# ============================================================
# MOMENTUM
# ============================================================

def momentum_score(row):

    r5 = scalar(
        row.get("Return_5D"),
        0,
    )

    r20 = scalar(
        row.get("Return_20D"),
        0,
    )

    r60 = scalar(
        row.get("Return_60D"),
        0,
    )

    score = 50

    if r5 > 5:
        score += 15

    elif r5 > 0:
        score += 8

    elif r5 < -5:
        score -= 15

    if r20 > 10:
        score += 15

    elif r20 > 0:
        score += 8

    elif r20 < -10:
        score -= 10

    if r60 > 15:
        score += 20

    elif r60 > 0:
        score += 10

    elif r60 < -15:
        score -= 15

    return float(
        np.clip(
            score,
            0,
            100,
        )
    )


# ============================================================
# RSI SKORU
# ============================================================

def rsi_score(row):

    rsi = scalar(
        row.get("RSI"),
        50,
    )

    if 50 <= rsi <= 68:
        return 100

    if 45 <= rsi < 50:
        return 80

    if 68 < rsi <= 75:
        return 75

    if 40 <= rsi < 45:
        return 60

    if 75 < rsi <= 80:
        return 45

    return 30


# ============================================================
# HACİM SKORU
# ============================================================

def volume_score(row):

    vr = scalar(
        row.get("VolumeRatio"),
        1,
    )

    if vr >= 1.50:
        return 100

    if vr >= 1.20:
        return 90

    if vr >= 1.00:
        return 80

    if vr >= 0.80:
        return 65

    return 45


# ============================================================
# VWAP SKORU
# ============================================================

def vwap_score(row):

    price = scalar(
        row.get("Close"),
        0,
    )

    vwap = scalar(
        row.get("VWAP20"),
        price,
    )

    if price >= vwap:
        return 100

    if price >= vwap * 0.99:
        return 75

    if price >= vwap * 0.97:
        return 55

    return 35


# ============================================================
# TEKNİK GENEL SKOR
# ============================================================

def technical_score(row):

    trend = trend_score(row)

    momentum = momentum_score(row)

    rsi = rsi_score(row)

    volume = volume_score(row)

    vwap = vwap_score(row)

    score = (
        trend * 0.30
        + momentum * 0.25
        + rsi * 0.10
        + volume * 0.15
        + vwap * 0.20
    )

    return round(
        float(
            np.clip(
                score,
                0,
                100,
            )
        ),
        1,
    )


# ============================================================
# FIRSAT SKORU
#
# Fırsat Merkezi için ana skor.
#
# Teknik + Finansal + Sektör + Piyasa
#
# Özellikle tek bir teknik göstergeye aşırı bağımlılığı
# azaltır.
# ============================================================

def opportunity_score(
    row,
    financial_score=50,
    sector_score=50,
    market_score=50,
):

    technical = technical_score(
        row
    )

    financial_score = clamp_score(
        financial_score
    )

    sector_score = clamp_score(
        sector_score
    )

    market_score = clamp_score(
        market_score
    )

    score = (
        technical * 0.45
        + financial_score * 0.20
        + sector_score * 0.20
        + market_score * 0.15
    )

    return round(
        float(
            np.clip(
                score,
                0,
                100,
            )
        ),
        1,
    )


# ============================================================
# VADE SKORU
# ============================================================

def calculate_horizon_score(
    row,
    horizon,
    financial_score=50,
    sector_score=50,
    market_score=50,
):

    trend = trend_score(
        row
    )

    momentum = momentum_score(
        row
    )

    rsi = rsi_score(
        row
    )

    volume = volume_score(
        row
    )

    vwap = vwap_score(
        row
    )

    financial_score = clamp_score(
        financial_score
    )

    sector_score = clamp_score(
        sector_score
    )

    market_score = clamp_score(
        market_score
    )

    # ========================================================
    # GÜNLÜK
    # ========================================================

    if horizon == "Günlük":

        score = (
            trend * 0.25
            + momentum * 0.20
            + rsi * 0.10
            + volume * 0.15
            + vwap * 0.15
            + sector_score * 0.05
            + market_score * 0.10
        )

    # ========================================================
    # KISA VADE
    # ========================================================

    elif horizon == "Kısa Vade":

        score = (
            trend * 0.25
            + momentum * 0.25
            + rsi * 0.10
            + volume * 0.10
            + vwap * 0.10
            + financial_score * 0.05
            + sector_score * 0.10
            + market_score * 0.05
        )

    # ========================================================
    # ORTA VADE
    # ========================================================

    elif horizon == "Orta Vade":

        score = (
            trend * 0.30
            + momentum * 0.25
            + rsi * 0.05
            + volume * 0.05
            + vwap * 0.10
            + financial_score * 0.10
            + sector_score * 0.10
            + market_score * 0.05
        )

    # ========================================================
    # UZUN VADE
    # ========================================================

    else:

        score = (
            trend * 0.30
            + momentum * 0.20
            + rsi * 0.05
            + volume * 0.05
            + vwap * 0.05
            + financial_score * 0.20
            + sector_score * 0.10
            + market_score * 0.05
        )

    return round(
        float(
            np.clip(
                score,
                0,
                100,
            )
        ),
        1,
    )


# ============================================================
# KARAR
# ============================================================

def make_decision(
    score,
    trend,
    momentum,
    sector,
    financial,
):

    score = clamp_score(
        score
    )

    trend = clamp_score(
        trend
    )

    momentum = clamp_score(
        momentum
    )

    sector = clamp_score(
        sector
    )

    financial = clamp_score(
        financial
    )

    # --------------------------------------------------------
    # GÜÇLÜ
    # --------------------------------------------------------

    if (
        score >= 80
        and trend >= 60
        and momentum >= 60
    ):

        return "🟢 GÜÇLÜ ADAY"

    # --------------------------------------------------------
    # AL
    # --------------------------------------------------------

    if (
        score >= 72
        and trend >= 50
        and momentum >= 50
    ):

        return "🟢 AL"

    # --------------------------------------------------------
    # TEYİT
    # --------------------------------------------------------

    if (
        score >= 60
        and sector >= 50
    ):

        return "🟡 TEYİT BEKLE"

    # --------------------------------------------------------
    # İZLE
    # --------------------------------------------------------

    if score >= 45:

        return "🟠 İZLE"

    return "🔴 ZAYIF"


# ============================================================
# TEK HİSSE ANALİZİ
# ============================================================

def analyze_stock(
    ticker,
    min_liquidity=DEFAULT_MIN_LIQUIDITY,
    financial_scores=None,
    sector_scores=None,
    market_score=50,
    return_source=False,
):

    ticker = normalize_ticker(
        ticker
    )

    if not ticker:
        return None

    # --------------------------------------------------------
    # VERİ
    # --------------------------------------------------------

    df, source = get_price_history(
        ticker
    )

    if df is None:
        return None

    # --------------------------------------------------------
    # GÖSTERGELER
    # --------------------------------------------------------

    df = calculate_indicators(
        df
    )

    if df is None:
        return None

    row = df.iloc[-1]

    # --------------------------------------------------------
    # FİYAT
    # --------------------------------------------------------

    price = scalar(
        row.get("Close"),
        0,
    )

    if price <= 0:
        return None

    # --------------------------------------------------------
    # LİKİDİTE
    # --------------------------------------------------------

    avg_volume = scalar(
        row.get("VOL20"),
        0,
    )

    liquidity = (
        price
        *
        avg_volume
    )

    if (
        min_liquidity is not None
        and liquidity < min_liquidity
    ):
        return None

    # --------------------------------------------------------
    # DIŞ SKORLAR
    # --------------------------------------------------------

    if financial_scores is None:
        financial_scores = {}

    if sector_scores is None:
        sector_scores = {}

    financial = clamp_score(
        financial_scores.get(
            ticker,
            50,
        )
    )

    sector = clamp_score(
        sector_scores.get(
            ticker,
            50,
        )
    )

    market = clamp_score(
        market_score,
        50,
    )

    # --------------------------------------------------------
    # TEKNİK
    # --------------------------------------------------------

    trend = trend_score(
        row
    )

    momentum = momentum_score(
        row
    )

    rsi = scalar(
        row.get("RSI"),
        50,
    )

    volume_ratio = scalar(
        row.get("VolumeRatio"),
        1,
    )

    vwap = vwap_score(
        row
    )

    technical = technical_score(
        row
    )

    opportunity = opportunity_score(
        row,
        financial,
        sector,
        market,
    )

    # --------------------------------------------------------
    # VADELER
    # --------------------------------------------------------

    daily = calculate_horizon_score(
        row,
        "Günlük",
        financial,
        sector,
        market,
    )

    short = calculate_horizon_score(
        row,
        "Kısa Vade",
        financial,
        sector,
        market,
    )

    medium = calculate_horizon_score(
        row,
        "Orta Vade",
        financial,
        sector,
        market,
    )

    long = calculate_horizon_score(
        row,
        "Uzun Vade",
        financial,
        sector,
        market,
    )

    # --------------------------------------------------------
    # KARAR
    # --------------------------------------------------------

    decision = make_decision(
        opportunity,
        trend,
        momentum,
        sector,
        financial,
    )

    # --------------------------------------------------------
    # SONUÇ
    # --------------------------------------------------------

    result = {

        "Hisse": ticker,

        "Fiyat": round(
            price,
            2,
        ),

        "Likidite": round(
            liquidity,
            0,
        ),

        "Trend": round(
            trend,
            1,
        ),

        "Momentum": round(
            momentum,
            1,
        ),

        "Teknik Skor": round(
            technical,
            1,
        ),

        "RSI": round(
            rsi,
            1,
        ),

        "Hacim Oranı": round(
            volume_ratio,
            2,
        ),

        "VWAP Skor": round(
            vwap,
            1,
        ),

        "Finansal Skor": round(
            financial,
            1,
        ),

        "Sektör Skoru": round(
            sector,
            1,
        ),

        "Piyasa Skoru": round(
            market,
            1,
        ),

        "Fırsat Skoru": round(
            opportunity,
            1,
        ),

        "Karar": decision,

        "Günlük": daily,

        "Kısa Vade": short,

        "Orta Vade": medium,

        "Uzun Vade": long,

        "Getiri 1G": round(
            scalar(
                row.get("Return_1D"),
                0,
            ),
            2,
        ),

        "Getiri 5G": round(
            scalar(
                row.get("Return_5D"),
                0,
            ),
            2,
        ),

        "Getiri 20G": round(
            scalar(
                row.get("Return_20D"),
                0,
            ),
            2,
        ),

        "Getiri 60G": round(
            scalar(
                row.get("Return_60D"),
                0,
            ),
            2,
        ),

        "EMA9": round(
            scalar(
                row.get("EMA9"),
                0,
            ),
            2,
        ),

        "EMA20": round(
            scalar(
                row.get("EMA20"),
                0,
            ),
            2,
        ),

        "EMA50": round(
            scalar(
                row.get("EMA50"),
                0,
            ),
            2,
        ),

        "EMA200": round(
            scalar(
                row.get("EMA200"),
                0,
            ),
            2,
        ),

        "ATR": round(
            scalar(
                row.get("ATR"),
                0,
            ),
            2,
        ),

        "VWAP20": round(
            scalar(
                row.get("VWAP20"),
                0,
            ),
            2,
        ),

        "Destek20": round(
            scalar(
                row.get("Support20"),
                0,
            ),
            2,
        ),

        "Direnç20": round(
            scalar(
                row.get("Resistance20"),
                0,
            ),
            2,
        ),

        "Volatilite20": round(
            scalar(
                row.get("Volatility20"),
                0,
            ),
            2,
        ),

        "Veri Kaynağı": source,
    }

    if return_source:
        return result, source

    return result


# ============================================================
# TÜM EVRENİ TARA
# ============================================================

def scan_stocks(
    min_liquidity=DEFAULT_MIN_LIQUIDITY,
    limit=None,
):

    universe = get_universe()

    if not universe:
        return pd.DataFrame()

    # --------------------------------------------------------
    # TEST LİMİTİ
    # --------------------------------------------------------

    if limit is not None:

        try:

            limit = int(
                limit
            )

            if limit > 0:

                universe = universe[
                    :limit
                ]

        except Exception:
            pass

    # --------------------------------------------------------
    # DIŞ SKORLAR
    # SADECE BİR KEZ OKU
    # --------------------------------------------------------

    financial_scores = (
        get_financial_scores()
    )

    sector_scores = (
        get_sector_scores()
    )

    market_score = (
        get_market_score()
    )

    results = []

    db_count = 0
    yahoo_count = 0
    failed_count = 0
    liquidity_count = 0

    # --------------------------------------------------------
    # TARAMA
    # --------------------------------------------------------

    for ticker in universe:

        try:

            result_source = analyze_stock(
                ticker=ticker,
                min_liquidity=min_liquidity,
                financial_scores=financial_scores,
                sector_scores=sector_scores,
                market_score=market_score,
                return_source=True,
            )

            if not result_source:

                failed_count += 1
                continue

            result, source = result_source

            if source == "DB":
                db_count += 1

            elif source == "Yahoo":
                yahoo_count += 1

            if result is not None:

                results.append(
                    result
                )

            else:

                failed_count += 1

        except Exception:

            failed_count += 1
            continue

    # --------------------------------------------------------
    # SONUÇ YOK
    # --------------------------------------------------------

    if not results:

        empty = pd.DataFrame()

        empty.attrs[
            "scan_info"
        ] = {

            "Universe": len(
                universe
            ),

            "Successful": 0,

            "DB": db_count,

            "Yahoo": yahoo_count,

            "Failed": failed_count,

        }

        return empty

    # --------------------------------------------------------
    # DATAFRAME
    # --------------------------------------------------------

    df = pd.DataFrame(
        results
    )

    # --------------------------------------------------------
    # ÖNCE FIRSAT SKORU
    # --------------------------------------------------------

    if "Fırsat Skoru" in df.columns:

        df = df.sort_values(
            "Fırsat Skoru",
            ascending=False,
        )

    elif "Günlük" in df.columns:

        df = df.sort_values(
            "Günlük",
            ascending=False,
        )

    df = df.reset_index(
        drop=True
    )

    # --------------------------------------------------------
    # TARAMA BİLGİSİ
    # --------------------------------------------------------

    df.attrs[
        "scan_info"
    ] = {

        "Universe": len(
            universe
        ),

        "Successful": len(
            df
        ),

        "DB": db_count,

        "Yahoo": yahoo_count,

        "Failed": failed_count,

    }

    return df


# ============================================================
# TOP ADAYLAR
# ============================================================

def get_top_candidates(
    df,
    horizon,
    n=5,
):

    if df is None or df.empty:
        return pd.DataFrame()

    if horizon not in df.columns:
        return pd.DataFrame()

    try:

        n = int(
            n
        )

    except Exception:

        n = 5

    if n <= 0:
        return pd.DataFrame()

    return (
        df
        .sort_values(
            horizon,
            ascending=False,
        )
        .head(n)
        .reset_index(
            drop=True
        )
    )


# ============================================================
# FIRSAT MERKEZİ
#
# Ana kullanım:
#
#     get_opportunity_candidates()
#
# ============================================================

def get_opportunity_candidates(
    min_liquidity=DEFAULT_MIN_LIQUIDITY,
    n=20,
    min_score=60,
):

    df = scan_stocks(
        min_liquidity=min_liquidity
    )

    if df.empty:
        return df

    if "Fırsat Skoru" not in df.columns:
        return df.head(n)

    result = df[
        df["Fırsat Skoru"]
        >= float(min_score)
    ].copy()

    result = result.sort_values(
        "Fırsat Skoru",
        ascending=False,
    )

    result = result.head(
        int(n)
    ).reset_index(
        drop=True
    )

    return result


# ============================================================
# GÜNLÜK ADAYLAR
# ============================================================

def get_daily_candidates(
    min_liquidity=DEFAULT_MIN_LIQUIDITY,
    n=10,
    min_score=60,
):

    df = scan_stocks(
        min_liquidity=min_liquidity
    )

    if df.empty:
        return df

    result = df[
        df["Günlük"]
        >= float(min_score)
    ].copy()

    result = result.sort_values(
        "Günlük",
        ascending=False,
    )

    return result.head(
        int(n)
    ).reset_index(
        drop=True
    )


# ============================================================
# TÜM VADELER
# ============================================================

def get_all_candidates(
    min_liquidity=DEFAULT_MIN_LIQUIDITY,
    n=5,
):

    df = scan_stocks(
        min_liquidity=min_liquidity
    )

    if df.empty:

        return {

            "daily":
                pd.DataFrame(),

            "short":
                pd.DataFrame(),

            "medium":
                pd.DataFrame(),

            "long":
                pd.DataFrame(),

            "opportunity":
                pd.DataFrame(),

            "scan_info":
                df.attrs.get(
                    "scan_info",
                    {},
                ),
        }

    return {

        "daily":
            get_top_candidates(
                df,
                "Günlük",
                n,
            ),

        "short":
            get_top_candidates(
                df,
                "Kısa Vade",
                n,
            ),

        "medium":
            get_top_candidates(
                df,
                "Orta Vade",
                n,
            ),

        "long":
            get_top_candidates(
                df,
                "Uzun Vade",
                n,
            ),

        "opportunity":
            get_top_candidates(
                df,
                "Fırsat Skoru",
                n,
            ),

        "scan_info":
            df.attrs.get(
                "scan_info",
                {},
            ),
    }


# ============================================================
# TEK HİSSE
# ============================================================

def get_stock(
    ticker,
    min_liquidity=DEFAULT_MIN_LIQUIDITY,
):

    financial_scores = (
        get_financial_scores()
    )

    sector_scores = (
        get_sector_scores()
    )

    market_score = (
        get_market_score()
    )

    return analyze_stock(

        ticker=ticker,

        min_liquidity=min_liquidity,

        financial_scores=financial_scores,

        sector_scores=sector_scores,

        market_score=market_score,
    )


# ============================================================
# MOTOR BİLGİSİ
# ============================================================

def engine_info():

    return {

        "Engine":
            "BIST AI PRO Stock Engine",

        "Version":
            "V4 - DATABASE FIRST / OPPORTUNITY CENTER READY",

        "Database":
            str(DB_PATH),

        "History":
            HISTORY_PERIOD,

        "Min Liquidity":
            DEFAULT_MIN_LIQUIDITY,

        "Yahoo Fallback":
            ALLOW_YAHOO_FALLBACK,

        "Min History Rows":
            MIN_HISTORY_ROWS,

        "Horizons": [

            "Günlük",

            "Kısa Vade",

            "Orta Vade",

            "Uzun Vade",

        ],

        "Technical": [

            "EMA5",

            "EMA9",

            "EMA20",

            "EMA50",

            "EMA100",

            "EMA200",

            "RSI14",

            "VolumeRatio",

            "ATR14",

            "VWAP20",

            "Momentum",

            "Volatility20",

            "Support20",

            "Resistance20",

        ],

        "External Scores": [

            "Finansal",

            "Sektör",

            "Piyasa",

        ],

        "Main Scores": [

            "Teknik Skor",

            "Fırsat Skoru",

            "Günlük",

            "Kısa Vade",

            "Orta Vade",

            "Uzun Vade",

        ],

    }


# ============================================================
# DOSYA TESTİ
# ============================================================

if __name__ == "__main__":

    print()

    print(
        "=========================================="
    )

    print(
        " BIST AI PRO - STOCK ENGINE V4"
    )

    print(
        " DATABASE FIRST"
    )

    print(
        " OPPORTUNITY CENTER READY"
    )

    print(
        "=========================================="
    )

    print()

    print(
        f"DB: {DB_PATH}"
    )

    print()

    # --------------------------------------------------------
    # MOTOR BİLGİSİ
    # --------------------------------------------------------

    info = engine_info()

    for key, value in info.items():

        print(
            f"{key}: {value}"
        )

    print()

    # --------------------------------------------------------
    # TABLOLAR
    # --------------------------------------------------------

    tables = get_table_names()

    print(
        f"DB tablo sayısı: {len(tables)}"
    )

    print(
        "Tablolar:"
    )

    for table in tables:

        print(
            f"  - {table}"
        )

    print()

    # --------------------------------------------------------
    # EVREN
    # --------------------------------------------------------

    universe = get_universe()

    print(
        f"DB Evreni: {len(universe)} hisse"
    )

    print()

    # --------------------------------------------------------
    # TEST HİSSESİ
    # --------------------------------------------------------

    if universe:

        test_ticker = universe[0]

        print(
            f"Test hissesi: {test_ticker}"
        )

        result = get_stock(
            test_ticker
        )

        if result:

            print()

            for key, value in result.items():

                print(
                    f"{key}: {value}"
                )

        else:

            print(
                "Test hissesi analiz edilemedi."
            )

    else:

        print(
            "stocks / bist500_universe "
            "tablosunda evren bulunamadı."
        )

    print()

    # --------------------------------------------------------
    # FIRSAT MERKEZİ TESTİ
    # --------------------------------------------------------

    print(
        "Fırsat Merkezi test ediliyor..."
    )

    try:

        opportunity_df = (
            get_opportunity_candidates(
                min_liquidity=DEFAULT_MIN_LIQUIDITY,
                n=10,
                min_score=60,
            )
        )

        if (
            opportunity_df is not None
            and not opportunity_df.empty
        ):

            print()

            columns = [
                "Hisse",
                "Fiyat",
                "Teknik Skor",
                "Finansal Skor",
                "Sektör Skoru",
                "Piyasa Skoru",
                "Fırsat Skoru",
                "Günlük",
                "Kısa Vade",
                "Orta Vade",
                "Uzun Vade",
                "Karar",
            ]

            available_columns = [
                c
                for c in columns
                if c in opportunity_df.columns
            ]

            print(
                opportunity_df[
                    available_columns
                ].to_string(
                    index=False
                )
            )

        else:

            print(
                "Fırsat Merkezi için uygun "
                "hisse bulunamadı."
            )

    except Exception as exc:

        print(
            f"Fırsat Merkezi testi hata verdi: {exc}"
        )

    print()

    print(
        "=========================================="
    )

    print(
        " TEST TAMAMLANDI"
    )

    print(
        "=========================================="
    )