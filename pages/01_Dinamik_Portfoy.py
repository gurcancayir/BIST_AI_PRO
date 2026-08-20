# ============================================================
# BIST AI PRO
# Dinamik_Portfoy.py
#
# YENİ NESİL DİNAMİK PORTFÖY MOTORU v3
#
# AMAÇ
# ------------------------------------------------------------
# BIST500
#    ↓
# VERİ KALİTESİ
#    ↓
# LİKİDİTE
#    ↓
# TEKNİK GÖSTERGELER
#    ↓
# MOMENTUM
#    ↓
# KAP / FİNANSAL KALİTE
#    ↓
# SEKTÖR GÜCÜ
#    ↓
# PİYASA UYUMU
#    ↓
# RİSK
#    ↓
# DİNAMİK SKOR
#    ↓
# ADAY HAVUZU
#    ↓
# SEKTÖR ÇEŞİTLENDİRME
#    ↓
# DİNAMİK PORTFÖY
#
# ÖNEMLİ
# ------------------------------------------------------------
# - SQLite veritabanına hiçbir değişiklik yapmaz.
# - Tablo oluşturmaz.
# - Veri yazmaz.
# - technical_analysis içindeki hazır göstergeleri keşfeder.
# - Eksik teknik gösterge varsa mevcut göstergelerle devam eder.
# - Finansal veri eksikliği ayrıca gösterilir.
# - Tek bir kriter yüzünden kaliteli hisse otomatik öldürülmez.
# ============================================================

import sqlite3
import math
import os
from datetime import datetime

import numpy as np
import pandas as pd
import streamlit as st


# ============================================================
# AYARLAR
# ============================================================

DB_PATH = "borsa.db"

DEFAULT_POOL = "BIST500"
DEFAULT_PORTFOLIO_SIZE = 10

MIN_HISTORY = 60
MIN_PRICE = 1.0

# ------------------------------------------------------------
# ANA AĞIRLIKLAR
# ------------------------------------------------------------
#
# Yeni mimari:
#
# Finansal      %25
# Teknik        %25
# Sektör        %15
# Momentum      %15
# Likidite      %10
# Piyasa        %10
#
# TOPLAM        %100
# ------------------------------------------------------------

WEIGHT_FINANCIAL = 0.25
WEIGHT_TECHNICAL = 0.25
WEIGHT_SECTOR = 0.15
WEIGHT_MOMENTUM = 0.15
WEIGHT_LIQUIDITY = 0.10
WEIGHT_MARKET = 0.10


# ============================================================
# ADAY FİLTRELERİ
# ============================================================
#
# Bunlar artık eski sistemdeki gibi 5 ayrı sert kapı değildir.
#
# Ana amaç:
# 1) Çok kötü teknik yapıyı ele
# 2) Çok kötü finansalı ele
# 3) Sonra toplam skora göre sırala
#
# ============================================================

MIN_DYNAMIC_SCORE = 50

MIN_TECHNICAL_SCORE = 35
MIN_MOMENTUM_SCORE = 30
MIN_FINANCIAL_SCORE = 25

# Çok kötü finansal yapı
HARD_FINANCIAL_FLOOR = 15

# Çok kötü teknik yapı
HARD_TECHNICAL_FLOOR = 20

# Çok kötü momentum
HARD_MOMENTUM_FLOOR = 15


# ============================================================
# LİKİDİTE
# ============================================================

MIN_AVG_VOLUME_TL = 5_000_000


# ============================================================
# PORTFÖY ÇEŞİTLENDİRME
# ============================================================

MAX_SECTOR_WEIGHT = 0.30
MAX_STOCKS_PER_SECTOR = 3

SECTOR_CONCENTRATION_PENALTY = 5.0


# ============================================================
# RİSK CEZALARI
# ============================================================

PENALTY_EMA50 = 6
PENALTY_EMA20 = 3
PENALTY_RSI_HIGH = 4
PENALTY_RSI_LOW = 2
PENALTY_LOW_VOLUME = 4
PENALTY_HIGH_VOLATILITY = 5
PENALTY_MACD_NEGATIVE = 3
PENALTY_ADX_WEAK = 2
PENALTY_BELOW_120_HIGH = 3


# ============================================================
# SEKTÖR
# ============================================================

SECTOR_UNKNOWN = "Diğer"


CUSTOM_SECTOR_MAP = {

    "ASELS": "Savunma",
    "SDTTR": "Savunma",
    "ALTNY": "Savunma",

    "FORTE": "Teknoloji",
    "MIATK": "Teknoloji",
    "ATATP": "Teknoloji",
    "ARDYZ": "Teknoloji",

    "TUPRS": "Enerji",
    "AKSEN": "Enerji",
    "AKFYE": "Enerji",
    "GESAN": "Enerji",
    "EUPWR": "Enerji",

    "TKFEN": "İnşaat",
    "ENKAI": "İnşaat",

    "RYSAS": "Lojistik",

    "THYAO": "Ulaştırma",

    "BIMAS": "Perakende",
    "MGROS": "Perakende",

    "CCOLA": "Gıda",

    "FROTO": "Otomotiv",

    "KCHOL": "Holding",
}


# ============================================================
# GENEL YARDIMCI FONKSİYONLAR
# ============================================================

def clamp(value, low=0, high=100):

    try:

        if value is None or pd.isna(value):
            return low

        value = float(value)

        if not np.isfinite(value):
            return low

        return max(low, min(high, value))

    except Exception:

        return low


def safe_float(value, default=np.nan):

    try:

        if value is None:
            return default

        if isinstance(value, str):

            value = (
                value
                .replace("%", "")
                .replace("TL", "")
                .replace("₺", "")
                .replace("Mr", "")
                .replace("Mn", "")
                .replace(",", ".")
                .strip()
            )

        value = float(value)

        if not np.isfinite(value):
            return default

        return value

    except Exception:

        return default


def normalize_column_name(name):

    return (
        str(name)
        .strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
        .replace("/", "_")
        .replace("(", "")
        .replace(")", "")
        .replace("%", "pct")
    )


def find_column(df, candidates):

    if df is None or df.empty:
        return None

    normalized = {
        normalize_column_name(c): c
        for c in df.columns
    }

    # Exact
    for candidate in candidates:

        c = normalize_column_name(candidate)

        if c in normalized:
            return normalized[c]

    # Fuzzy
    for candidate in candidates:

        c = normalize_column_name(candidate)

        for existing in normalized:

            if c in existing or existing in c:
                return normalized[existing]

    return None


def clean_symbol(value):

    if value is None:
        return None

    s = str(value).upper().strip()

    s = s.replace(".IS", "")

    return s


# ============================================================
# DATABASE
# ============================================================

@st.cache_resource
def get_connection():

    if not os.path.exists(DB_PATH):
        return None

    return sqlite3.connect(
        DB_PATH,
        check_same_thread=False
    )


def get_tables():

    conn = get_connection()

    if conn is None:
        return []

    try:

        q = """
        SELECT name
        FROM sqlite_master
        WHERE type='table'
        ORDER BY name
        """

        return pd.read_sql_query(
            q,
            conn
        )["name"].tolist()

    except Exception:

        return []


def read_table(table_name):

    conn = get_connection()

    if conn is None:
        return pd.DataFrame()

    if table_name not in get_tables():
        return pd.DataFrame()

    try:

        return pd.read_sql_query(
            f'SELECT * FROM "{table_name}"',
            conn
        )

    except Exception:

        return pd.DataFrame()


def find_existing_table(possible_names):

    tables = get_tables()

    normalized_tables = {
        normalize_column_name(t): t
        for t in tables
    }

    for name in possible_names:

        n = normalize_column_name(name)

        if n in normalized_tables:
            return normalized_tables[n]

    return None


# ============================================================
# TABLOLARI YÜKLE
# ============================================================

def load_stocks():

    table = find_existing_table([
        "stocks",
        "stock",
        "bist500_universe",
        "bist500",
        "universe"
    ])

    if table is None:
        return pd.DataFrame()

    return read_table(table)


def load_prices():

    table = find_existing_table([
        "stock_prices",
        "prices",
        "price_history"
    ])

    if table is None:
        return pd.DataFrame()

    return read_table(table)


def load_technical():

    table = find_existing_table([
        "technical_analysis",
        "technical",
        "technical_data"
    ])

    if table is None:
        return pd.DataFrame()

    return read_table(table)


def load_fundamentals():

    table = find_existing_table([
        "fundamentals",
        "financials",
        "financial_analysis",
        "kap_financials",
        "kap_data"
    ])

    if table is None:
        return pd.DataFrame()

    return read_table(table)


# ============================================================
# KOLON BULMA
# ============================================================

def detect_symbol_column(df):

    return find_column(
        df,
        [
            "symbol",
            "ticker",
            "code",
            "stock_code",
            "hisse",
            "hisse_kodu",
            "kod",
            "ticker_symbol"
        ]
    )


def detect_sector_column(df):

    return find_column(
        df,
        [
            "sector",
            "sektor",
            "sector_name",
            "sektor_adi",
            "industry"
        ]
    )


# ============================================================
# SEKTÖR
# ============================================================

def get_sector(symbol, stocks_df):

    symbol = clean_symbol(symbol)

    if symbol in CUSTOM_SECTOR_MAP:

        return CUSTOM_SECTOR_MAP[symbol]

    if not stocks_df.empty:

        symbol_col = detect_symbol_column(
            stocks_df
        )

        sector_col = detect_sector_column(
            stocks_df
        )

        if symbol_col and sector_col:

            rows = stocks_df[
                stocks_df[symbol_col]
                .astype(str)
                .str.upper()
                .str.replace(
                    ".IS",
                    "",
                    regex=False
                )
                == symbol
            ]

            if not rows.empty:

                sector = rows.iloc[0][
                    sector_col
                ]

                if pd.notna(sector):

                    return str(sector)

    return SECTOR_UNKNOWN


# ============================================================
# BIST EVRENİ
# ============================================================

def detect_index_columns(df):

    return [
        c for c in df.columns
        if any(
            x in normalize_column_name(c)
            for x in [
                "index",
                "endeks",
                "bist"
            ]
        )
    ]


def build_universe(
    stocks_df,
    selected_pool
):

    if stocks_df.empty:
        return []

    symbol_col = detect_symbol_column(
        stocks_df
    )

    if symbol_col is None:
        return []

    df = stocks_df.copy()

    df["__symbol"] = (
        df[symbol_col]
        .astype(str)
        .str.upper()
        .str.replace(
            ".IS",
            "",
            regex=False
        )
        .str.strip()
    )

    df = df[
        df["__symbol"].notna()
        & (df["__symbol"] != "")
    ]

    index_cols = detect_index_columns(
        df
    )

    target_patterns = {

        "BIST500": "BIST500|BIST 500|XU500",

        "BIST100": "BIST100|BIST 100|XU100",

        "BIST50": "BIST50|BIST 50|XU050",

        "BIST30": "BIST30|BIST 30|XU030"
    }

    pattern = target_patterns.get(
        selected_pool.upper()
    )

    if pattern:

        for col in index_cols:

            mask = (
                df[col]
                .astype(str)
                .str.upper()
                .str.contains(
                    pattern,
                    regex=True
                )
            )

            if mask.any():

                df = df[mask]

                break

    return (
        df["__symbol"]
        .drop_duplicates()
        .tolist()
    )


# ============================================================
# FİYAT VERİSİ
# ============================================================

def get_price_data(
    prices_df,
    symbol
):

    if prices_df.empty:
        return pd.DataFrame()

    symbol_col = detect_symbol_column(
        prices_df
    )

    if symbol_col is None:
        return pd.DataFrame()

    symbol = clean_symbol(symbol)

    df = prices_df[
        prices_df[symbol_col]
        .astype(str)
        .str.upper()
        .str.replace(
            ".IS",
            "",
            regex=False
        )
        .str.strip()
        == symbol
    ].copy()

    if df.empty:
        return pd.DataFrame()

    date_col = find_column(
        df,
        [
            "date",
            "datetime",
            "timestamp",
            "tarih",
            "time"
        ]
    )

    close_col = find_column(
        df,
        [
            "close",
            "adj_close",
            "kapanis",
            "fiyat"
        ]
    )

    volume_col = find_column(
        df,
        [
            "volume",
            "hacim",
            "volume_tl"
        ]
    )

    if close_col is None:
        return pd.DataFrame()

    df["close"] = pd.to_numeric(
        df[close_col],
        errors="coerce"
    )

    if volume_col:

        df["volume"] = pd.to_numeric(
            df[volume_col],
            errors="coerce"
        )

    else:

        df["volume"] = np.nan

    if date_col:

        df["date"] = pd.to_datetime(
            df[date_col],
            errors="coerce"
        )

        df = df.sort_values(
            "date"
        )

    df = df.dropna(
        subset=["close"]
    )

    return df


# ============================================================
# TEKNİK ANALİZ TABLOSU İÇİN SATIR BULMA
# ============================================================

def find_technical_row(
    technical_df,
    symbol
):

    if technical_df.empty:
        return pd.Series(
            dtype=object
        )

    symbol_col = detect_symbol_column(
        technical_df
    )

    if symbol_col is None:
        return pd.Series(
            dtype=object
        )

    symbol = clean_symbol(symbol)

    rows = technical_df[
        technical_df[symbol_col]
        .astype(str)
        .str.upper()
        .str.replace(
            ".IS",
            "",
            regex=False
        )
        .str.strip()
        == symbol
    ]

    if rows.empty:
        return pd.Series(
            dtype=object
        )

    # Eğer tarih varsa son satır
    date_col = find_column(
        rows,
        [
            "date",
            "datetime",
            "tarih",
            "timestamp"
        ]
    )

    if date_col:

        temp = rows.copy()

        temp["__date"] = pd.to_datetime(
            temp[date_col],
            errors="coerce"
        )

        temp = temp.sort_values(
            "__date"
        )

        return temp.iloc[-1]

    return rows.iloc[-1]


# ============================================================
# TEKNİK KOLON KEŞFİ
# ============================================================

TECH_COLUMNS = {

    "macd": [
        "macd",
        "macd_line",
        "macd_degeri"
    ],

    "adx": [
        "adx",
        "adx_14"
    ],

    "atr_pct": [
        "atr_pct",
        "atr_percent",
        "atr_yuzde",
        "atr%"
    ],

    "bollinger_position": [
        "bollinger_position",
        "bollinger_pozisyon",
        "bb_position",
        "bollinger_pos"
    ],

    "bollinger_width": [
        "bollinger_width",
        "bollinger_genisligi",
        "bb_width"
    ],

    "stochastic": [
        "stochastic",
        "stoch",
        "stochastic_k",
        "stoch_k"
    ],

    "momentum20": [
        "20g_momentum",
        "momentum_20",
        "momentum20",
        "20d_momentum"
    ],

    "momentum60": [
        "60g_momentum",
        "momentum_60",
        "momentum60",
        "60d_momentum"
    ],

    "momentum120": [
        "120g_momentum",
        "momentum_120",
        "momentum120",
        "120d_momentum"
    ],

    "high20": [
        "20g_zirve_uzakligi",
        "20g_zirve",
        "distance_from_20d_high",
        "20d_high_distance"
    ],

    "high60": [
        "60g_zirve_uzakligi",
        "60g_zirve",
        "distance_from_60d_high",
        "60d_high_distance"
    ],

    "high120": [
        "120g_zirve_uzakligi",
        "120g_zirve",
        "distance_from_120d_high",
        "120d_high_distance"
    ],

    "ema9_distance": [
        "ema9_mesafesi",
        "ema9_distance",
        "distance_ema9"
    ],

    "ema20_distance": [
        "ema20_mesafesi",
        "ema20_distance",
        "distance_ema20"
    ],

    "ema50_distance": [
        "ema50_mesafesi",
        "ema50_distance",
        "distance_ema50"
    ],

    "ema20_50": [
        "ema20_50",
        "ema20_50_spread",
        "ema20_50_fark"
    ],

    "ema50_100": [
        "ema50_100",
        "ema50_100_spread",
        "ema50_100_fark"
    ],

    "volume20": [
        "20g_hacim_orani",
        "hacim_orani_20",
        "volume_ratio_20",
        "20d_volume_ratio"
    ],

    "volume60": [
        "60g_hacim_orani",
        "hacim_orani_60",
        "volume_ratio_60",
        "60d_volume_ratio"
    ],

    "volume_trend": [
        "hacim_trendi",
        "volume_trend",
        "volume_trend_score"
    ],

    "obv_trend": [
        "obv_trendi",
        "obv_trend",
        "obv_trend_score"
    ]
}


def get_technical_value(
    row,
    indicator_name
):

    if row is None or len(row) == 0:
        return np.nan

    candidates = TECH_COLUMNS.get(
        indicator_name,
        []
    )

    return value_from_row(
        row,
        candidates
    )


# ============================================================
# SATIR DEĞERİ
# ============================================================

def value_from_row(
    row,
    candidates
):

    if row is None or len(row) == 0:
        return np.nan

    normalized = {
        normalize_column_name(c): c
        for c in row.index
    }

    for candidate in candidates:

        c = normalize_column_name(
            candidate
        )

        if c in normalized:

            return safe_float(
                row[normalized[c]]
            )

    for candidate in candidates:

        c = normalize_column_name(
            candidate
        )

        for existing in normalized:

            if c in existing:

                return safe_float(
                    row[normalized[existing]]
                )

    return np.nan


# ============================================================
# 0-100 NORMALİZASYON
# ============================================================

def score_positive(
    value,
    weak,
    good,
    excellent
):

    if pd.isna(value):
        return np.nan

    value = float(value)

    if value <= weak:
        return 20.0

    if value >= excellent:
        return 100.0

    if value >= good:

        return (
            60
            + (
                (value - good)
                / (excellent - good)
            )
            * 40
        )

    return (
        20
        + (
            (value - weak)
            / (good - weak)
        )
        * 40
    )


def score_negative(
    value,
    excellent,
    good,
    bad
):

    if pd.isna(value):
        return np.nan

    value = float(value)

    if value <= excellent:
        return 100.0

    if value >= bad:
        return 20.0

    if value <= good:

        return (
            60
            + (
                (good - value)
                / (good - excellent)
            )
            * 40
        )

    return (
        20
        + (
            (bad - value)
            / (bad - good)
        )
        * 40
    )


# ============================================================
# TEKNİK SKOR
# ============================================================

def calculate_advanced_technical_score(
    technical_row,
    price
):

    result = {

        "technical": 50.0,

        "trend": 50.0,

        "technical_data_count": 0,

        "technical_available_count": 0,

        "technical_reasons": [],

        "technical_warnings": [],

        "adx": np.nan,

        "macd": np.nan,

        "atr_pct": np.nan,

        "bollinger_position": np.nan,

        "bollinger_width": np.nan,

        "stochastic": np.nan,

        "ema20_50": np.nan,

        "ema50_100": np.nan,

        "volume_trend": np.nan,

        "obv_trend": np.nan
    }

    if technical_row is None or len(
        technical_row
    ) == 0:

        return result

    scores = []

    # --------------------------------------------------------
    # EMA / TREND
    # --------------------------------------------------------

    ema_scores = []

    for key in [
        "ema9_distance",
        "ema20_distance",
        "ema50_distance",
        "ema20_50",
        "ema50_100"
    ]:

        value = get_technical_value(
            technical_row,
            key
        )

        if pd.notna(value):

            result[
                key
            ] = value

            result[
                "technical_data_count"
            ] += 1

            # Mesafe göstergelerinde pozitif olması iyidir
            if "distance" in key:

                score = score_positive(
                    value,
                    -10,
                    0,
                    10
                )

            else:

                score = score_positive(
                    value,
                    -10,
                    0,
                    10
                )

            if pd.notna(score):

                ema_scores.append(
                    score
                )

    if ema_scores:

        trend_ema = np.mean(
            ema_scores
        )

    else:

        trend_ema = 50

    # --------------------------------------------------------
    # ADX
    # --------------------------------------------------------

    adx = get_technical_value(
        technical_row,
        "adx"
    )

    result["adx"] = adx

    if pd.notna(adx):

        result[
            "technical_data_count"
        ] += 1

        result[
            "technical_available_count"
        ] += 1

        if adx >= 30:

            adx_score = 100

            result[
                "technical_reasons"
            ].append(
                "ADX güçlü trend"
            )

        elif adx >= 20:

            adx_score = 75

            result[
                "technical_reasons"
            ].append(
                "ADX yeterli"
            )

        elif adx >= 15:

            adx_score = 50

        else:

            adx_score = 30

            result[
                "technical_warnings"
            ].append(
                "ADX zayıf"
            )

    else:

        adx_score = 50

    # --------------------------------------------------------
    # MACD
    # --------------------------------------------------------

    macd = get_technical_value(
        technical_row,
        "macd"
    )

    result["macd"] = macd

    if pd.notna(macd):

        result[
            "technical_data_count"
        ] += 1

        result[
            "technical_available_count"
        ] += 1

        if macd > 0:

            macd_score = 80

            result[
                "technical_reasons"
            ].append(
                "MACD pozitif"
            )

        elif macd == 0:

            macd_score = 50

        else:

            macd_score = 25

            result[
                "technical_warnings"
            ].append(
                "MACD negatif"
            )

    else:

        macd_score = 50

    # --------------------------------------------------------
    # Bollinger Pozisyon
    # --------------------------------------------------------

    bb_pos = get_technical_value(
        technical_row,
        "bollinger_position"
    )

    result[
        "bollinger_position"
    ] = bb_pos

    if pd.notna(bb_pos):

        result[
            "technical_data_count"
        ] += 1

        result[
            "technical_available_count"
        ] += 1

        # 0.35 - 0.80 arası sağlıklı
        if 0.35 <= bb_pos <= 0.80:

            bb_score = 85

        elif 0.20 <= bb_pos <= 0.90:

            bb_score = 70

        elif bb_pos < 0.10:

            bb_score = 30

        elif bb_pos > 0.95:

            bb_score = 45

        else:

            bb_score = 55

    else:

        bb_score = 50

    # --------------------------------------------------------
    # Stochastic
    # --------------------------------------------------------

    stochastic = get_technical_value(
        technical_row,
        "stochastic"
    )

    result["stochastic"] = stochastic

    if pd.notna(stochastic):

        result[
            "technical_data_count"
        ] += 1

        result[
            "technical_available_count"
        ] += 1

        if 40 <= stochastic <= 80:

            stoch_score = 85

        elif 20 <= stochastic <= 90:

            stoch_score = 70

        elif stochastic > 90:

            stoch_score = 40

        else:

            stoch_score = 35

    else:

        stoch_score = 50

    # --------------------------------------------------------
    # ATR
    # --------------------------------------------------------

    atr = get_technical_value(
        technical_row,
        "atr_pct"
    )

    result["atr_pct"] = atr

    if pd.notna(atr):

        result[
            "technical_data_count"
        ] += 1

        result[
            "technical_available_count"
        ] += 1

        if atr <= 3:

            atr_score = 90

        elif atr <= 5:

            atr_score = 75

        elif atr <= 8:

            atr_score = 55

        elif atr <= 12:

            atr_score = 40

        else:

            atr_score = 25

    else:

        atr_score = 60

    # --------------------------------------------------------
    # Bollinger Width
    # --------------------------------------------------------

    bb_width = get_technical_value(
        technical_row,
        "bollinger_width"
    )

    result[
        "bollinger_width"
    ] = bb_width

    if pd.notna(bb_width):

        result[
            "technical_data_count"
        ] += 1

        result[
            "technical_available_count"
        ] += 1

        if bb_width < 5:

            bb_width_score = 80

        elif bb_width < 10:

            bb_width_score = 70

        elif bb_width < 20:

            bb_width_score = 55

        else:

            bb_width_score = 40

    else:

        bb_width_score = 60

    # --------------------------------------------------------
    # Teknik ağırlık
    # --------------------------------------------------------

    components = [

        (trend_ema, 0.35),

        (adx_score, 0.15),

        (macd_score, 0.15),

        (bb_score, 0.10),

        (stoch_score, 0.10),

        (atr_score, 0.05),

        (bb_width_score, 0.10)
    ]

    technical_score = sum(
        score * weight
        for score, weight
        in components
    )

    result[
        "technical"
    ] = clamp(
        technical_score
    )

    result[
        "trend"
    ] = clamp(
        trend_ema * 0.75
        + adx_score * 0.25
    )

    return result


# ============================================================
# MOMENTUM SKORU
# ============================================================

def calculate_momentum_score(
    technical_row
):

    result = {

        "momentum": 50.0,

        "momentum20": np.nan,

        "momentum60": np.nan,

        "momentum120": np.nan,

        "volume20": np.nan,

        "volume60": np.nan,

        "volume_trend": np.nan,

        "obv_trend": np.nan,

        "momentum_data_count": 0,

        "momentum_reasons": [],

        "momentum_warnings": []
    }

    if technical_row is None or len(
        technical_row
    ) == 0:

        return result

    scores = []

    # --------------------------------------------------------
    # 20G
    # --------------------------------------------------------

    m20 = get_technical_value(
        technical_row,
        "momentum20"
    )

    result["momentum20"] = m20

    if pd.notna(m20):

        result[
            "momentum_data_count"
        ] += 1

        # yüzde ise
        if m20 > 15:
            s20 = 100

        elif m20 > 8:
            s20 = 85

        elif m20 > 3:
            s20 = 70

        elif m20 > 0:
            s20 = 60

        elif m20 > -5:
            s20 = 45

        elif m20 > -10:
            s20 = 30

        else:
            s20 = 15

        scores.append(
            (s20, 0.25)
        )

        if m20 > 5:

            result[
                "momentum_reasons"
            ].append(
                "20G momentum pozitif"
            )

        elif m20 < -5:

            result[
                "momentum_warnings"
            ].append(
                "20G momentum zayıf"
            )

    # --------------------------------------------------------
    # 60G
    # --------------------------------------------------------

    m60 = get_technical_value(
        technical_row,
        "momentum60"
    )

    result["momentum60"] = m60

    if pd.notna(m60):

        result[
            "momentum_data_count"
        ] += 1

        if m60 > 30:
            s60 = 100

        elif m60 > 15:
            s60 = 90

        elif m60 > 5:
            s60 = 75

        elif m60 > 0:
            s60 = 60

        elif m60 > -10:
            s60 = 45

        elif m60 > -20:
            s60 = 30

        else:
            s60 = 15

        scores.append(
            (s60, 0.30)
        )

        if m60 > 10:

            result[
                "momentum_reasons"
            ].append(
                "60G momentum güçlü"
            )

        elif m60 < -10:

            result[
                "momentum_warnings"
            ].append(
                "60G momentum zayıf"
            )

    # --------------------------------------------------------
    # 120G
    # --------------------------------------------------------

    m120 = get_technical_value(
        technical_row,
        "momentum120"
    )

    result["momentum120"] = m120

    if pd.notna(m120):

        result[
            "momentum_data_count"
        ] += 1

        if m120 > 50:
            s120 = 100

        elif m120 > 25:
            s120 = 90

        elif m120 > 10:
            s120 = 75

        elif m120 > 0:
            s120 = 60

        elif m120 > -15:
            s120 = 45

        elif m120 > -30:
            s120 = 30

        else:
            s120 = 15

        scores.append(
            (s120, 0.20)
        )

        if m120 > 10:

            result[
                "momentum_reasons"
            ].append(
                "120G trend pozitif"
            )

    # --------------------------------------------------------
    # Hacim
    # --------------------------------------------------------

    v20 = get_technical_value(
        technical_row,
        "volume20"
    )

    result["volume20"] = v20

    if pd.notna(v20):

        result[
            "momentum_data_count"
        ] += 1

        if v20 >= 1.50:

            s = 100

        elif v20 >= 1.20:

            s = 90

        elif v20 >= 1.00:

            s = 75

        elif v20 >= 0.80:

            s = 55

        else:

            s = 35

        scores.append(
            (s, 0.08)
        )

    v60 = get_technical_value(
        technical_row,
        "volume60"
    )

    result["volume60"] = v60

    if pd.notna(v60):

        result[
            "momentum_data_count"
        ] += 1

        if v60 >= 1.30:

            s = 95

        elif v60 >= 1.00:

            s = 75

        elif v60 >= 0.80:

            s = 55

        else:

            s = 35

        scores.append(
            (s, 0.05)
        )

    # --------------------------------------------------------
    # Hacim trendi
    # --------------------------------------------------------

    vt = get_technical_value(
        technical_row,
        "volume_trend"
    )

    result["volume_trend"] = vt

    if pd.notna(vt):

        result[
            "momentum_data_count"
        ] += 1

        if vt > 0:

            volume_trend_score = 80

        elif vt == 0:

            volume_trend_score = 50

        else:

            volume_trend_score = 30

        scores.append(
            (
                volume_trend_score,
                0.04
            )
        )

    # --------------------------------------------------------
    # OBV
    # --------------------------------------------------------

    obv = get_technical_value(
        technical_row,
        "obv_trend"
    )

    result["obv_trend"] = obv

    if pd.notna(obv):

        result[
            "momentum_data_count"
        ] += 1

        if obv > 0:

            obv_score = 85

            result[
                "momentum_reasons"
            ].append(
                "OBV pozitif"
            )

        elif obv == 0:

            obv_score = 50

        else:

            obv_score = 30

            result[
                "momentum_warnings"
            ].append(
                "OBV negatif"
            )

        scores.append(
            (
                obv_score,
                0.03
            )
        )

    # --------------------------------------------------------
    # Normalize ağırlık
    # --------------------------------------------------------

    if scores:

        weight_sum = sum(
            weight
            for _, weight
            in scores
        )

        momentum = (
            sum(
                score * weight
                for score, weight
                in scores
            )
            / weight_sum
        )

    else:

        momentum = 50

    result[
        "momentum"
    ] = clamp(
        momentum
    )

    return result


# ============================================================
# FİNANSAL / KAP
# ============================================================

def find_financial_row(
    fund_df,
    symbol
):

    if fund_df.empty:

        return pd.Series(
            dtype=object
        )

    symbol_col = detect_symbol_column(
        fund_df
    )

    if symbol_col is None:

        return pd.Series(
            dtype=object
        )

    symbol = clean_symbol(symbol)

    rows = fund_df[
        fund_df[symbol_col]
        .astype(str)
        .str.upper()
        .str.replace(
            ".IS",
            "",
            regex=False
        )
        .str.strip()
        == symbol
    ]

    if rows.empty:

        return pd.Series(
            dtype=object
        )

    date_col = find_column(
        rows,
        [
            "date",
            "tarih",
            "period",
            "donem",
            "report_date"
        ]
    )

    if date_col:

        temp = rows.copy()

        temp["__date"] = pd.to_datetime(
            temp[date_col],
            errors="coerce"
        )

        temp = temp.sort_values(
            "__date"
        )

        return temp.iloc[-1]

    return rows.iloc[-1]


# ============================================================
# FİNANSAL SKOR
#
# ÖNEMLİ DÜZELTME:
#
# Eski sistem:
#
# score += 25
# score += 20
# ...
#
# fakat data_count ile normalize edilmiyordu.
#
# Yeni sistemde her metrik kendi içinde 0-100.
# Sonra ağırlıklı ortalama.
# ============================================================

def calculate_financial_score(row):

    result = {

        "financial": 50.0,

        "profitability": 50.0,

        "growth_score": 50.0,

        "leverage": 50.0,

        "liquidity": 50.0,

        "financial_data_count": 0,

        "financial_data_quality": 0,

        "reasons": [],

        "warnings": []
    }

    if row is None or len(row) == 0:

        result[
            "financial"
        ] = 40.0

        result[
            "financial_data_quality"
        ] = 0

        return result

    components = []

    # --------------------------------------------------------
    # ROE
    # --------------------------------------------------------

    roe = value_from_row(
        row,
        [
            "roe",
            "return_on_equity",
            "ozsermaye_karliligi"
        ]
    )

    if pd.notna(roe):

        result[
            "financial_data_count"
        ] += 1

        roe_score = score_positive(
            roe,
            0,
            12,
            20
        )

        result[
            "profitability"
        ] = roe_score

        components.append(
            (roe_score, 0.25)
        )

        if roe >= 20:

            result[
                "reasons"
            ].append(
                "ROE güçlü"
            )

        elif roe < 5:

            result[
                "warnings"
            ].append(
                "ROE düşük"
            )

    # --------------------------------------------------------
    # Net Margin
    # --------------------------------------------------------

    margin = value_from_row(
        row,
        [
            "net_margin",
            "profit_margin",
            "net_profit_margin",
            "net_kar_marji"
        ]
    )

    if pd.notna(margin):

        result[
            "financial_data_count"
        ] += 1

        margin_score = score_positive(
            margin,
            0,
            8,
            15
        )

        components.append(
            (margin_score, 0.20)
        )

        if margin >= 15:

            result[
                "reasons"
            ].append(
                "Net kâr marjı güçlü"
            )

        elif margin < 0:

            result[
                "warnings"
            ].append(
                "Net kâr marjı negatif"
            )

    # --------------------------------------------------------
    # Growth
    # --------------------------------------------------------

    growth = value_from_row(
        row,
        [
            "revenue_growth",
            "sales_growth",
            "growth",
            "revenue_growth_yoy",
            "ciro_buyume"
        ]
    )

    if pd.notna(growth):

        result[
            "financial_data_count"
        ] += 1

        growth_score = score_positive(
            growth,
            -10,
            10,
            30
        )

        result[
            "growth_score"
        ] = growth_score

        components.append(
            (growth_score, 0.20)
        )

        if growth >= 30:

            result[
                "reasons"
            ].append(
                "Ciro büyümesi güçlü"
            )

        elif growth < 0:

            result[
                "warnings"
            ].append(
                "Ciro büyümesi negatif"
            )

    # --------------------------------------------------------
    # Debt / Equity
    # --------------------------------------------------------

    debt_equity = value_from_row(
        row,
        [
            "debt_to_equity",
            "debt_equity",
            "borc_ozsermaye",
            "net_debt_to_equity"
        ]
    )

    if pd.notna(debt_equity):

        result[
            "financial_data_count"
        ] += 1

        debt_score = score_negative(
            debt_equity,
            0.30,
            1.00,
            2.00
        )

        result[
            "leverage"
        ] = debt_score

        components.append(
            (debt_score, 0.20)
        )

        if debt_equity < 0.50:

            result[
                "reasons"
            ].append(
                "Borçluluk düşük"
            )

        elif debt_equity > 2:

            result[
                "warnings"
            ].append(
                "Borçluluk yüksek"
            )

    # --------------------------------------------------------
    # Current Ratio
    # --------------------------------------------------------

    current_ratio = value_from_row(
        row,
        [
            "current_ratio",
            "cari_oran"
        ]
    )

    if pd.notna(current_ratio):

        result[
            "financial_data_count"
        ] += 1

        if current_ratio >= 2:

            current_score = 100

        elif current_ratio >= 1.50:

            current_score = 90

        elif current_ratio >= 1.00:

            current_score = 70

        elif current_ratio >= 0.70:

            current_score = 45

        else:

            current_score = 20

        result[
            "liquidity"
        ] = current_score

        components.append(
            (
                current_score,
                0.15
            )
        )

        if current_ratio >= 1.50:

            result[
                "reasons"
            ].append(
                "Cari oran güçlü"
            )

        elif current_ratio < 1:

            result[
                "warnings"
            ].append(
                "Cari oran zayıf"
            )

    # --------------------------------------------------------
    # Sonuç
    # --------------------------------------------------------

    if components:

        weight_sum = sum(
            weight
            for _, weight
            in components
        )

        financial = (
            sum(
                score * weight
                for score, weight
                in components
            )
            / weight_sum
        )

    else:

        # Finansal veri yoksa 0 yerine nötr.
        # Ancak veri kalitesi ayrıca 0 olarak gösterilecek.
        financial = 40

    result[
        "financial"
    ] = clamp(
        financial
    )

    result[
        "financial_data_quality"
    ] = clamp(
        result["financial_data_count"]
        / 5
        * 100
    )

    return result


# ============================================================
# LİKİDİTE
# ============================================================

def calculate_liquidity_score(
    price_df,
    technical_row=None
):

    if price_df.empty:

        return 0, np.nan

    close = pd.to_numeric(
        price_df["close"],
        errors="coerce"
    )

    volume = pd.to_numeric(
        price_df.get("volume"),
        errors="coerce"
    )

    if volume is None or volume.isna().all():

        return 40, np.nan

    value = (
        close * volume
    )

    avg20 = value.tail(20).mean()

    if pd.isna(avg20):

        return 0, np.nan

    if avg20 >= 100_000_000:

        score = 100

    elif avg20 >= 50_000_000:

        score = 90

    elif avg20 >= 25_000_000:

        score = 80

    elif avg20 >= 10_000_000:

        score = 70

    elif avg20 >= 5_000_000:

        score = 60

    elif avg20 >= 2_000_000:

        score = 45

    else:

        score = 25

    return score, avg20


# ============================================================
# PİYASA
# ============================================================

def calculate_market_score():

    for key in [
        "market_score",
        "genel_piyasa_skoru",
        "piyasa_skoru"
    ]:

        if key in st.session_state:

            value = safe_float(
                st.session_state[key]
            )

            if pd.notna(value):

                return clamp(
                    value
                )

    return 50.0


# ============================================================
# RİSK
# ============================================================

def calculate_risk_penalty(
    row
):

    penalty = 0
    reasons = []

    price = safe_float(
        row.get("price")
    )

    ema20 = safe_float(
        row.get("ema20")
    )

    ema50 = safe_float(
        row.get("ema50")
    )

    rsi = safe_float(
        row.get("rsi")
    )

    volume_ratio = safe_float(
        row.get("volume_ratio")
    )

    volatility = safe_float(
        row.get("volatility")
    )

    macd = safe_float(
        row.get("macd")
    )

    adx = safe_float(
        row.get("adx")
    )

    # --------------------------------------------------------
    # EMA50
    # --------------------------------------------------------

    if (
        pd.notna(price)
        and pd.notna(ema50)
        and price < ema50
    ):

        penalty += PENALTY_EMA50

        reasons.append(
            "Fiyat EMA50 altında"
        )

    elif (
        pd.notna(price)
        and pd.notna(ema20)
        and price < ema20
    ):

        penalty += PENALTY_EMA20

        reasons.append(
            "Fiyat EMA20 altında"
        )

    # --------------------------------------------------------
    # RSI
    # --------------------------------------------------------

    if pd.notna(rsi):

        if rsi > 78:

            penalty += PENALTY_RSI_HIGH

            reasons.append(
                "RSI aşırı yüksek"
            )

        elif rsi < 25:

            penalty += PENALTY_RSI_LOW

            reasons.append(
                "RSI aşırı düşük"
            )

    # --------------------------------------------------------
    # Hacim
    # --------------------------------------------------------

    if (
        pd.notna(volume_ratio)
        and volume_ratio < 0.50
    ):

        penalty += PENALTY_LOW_VOLUME

        reasons.append(
            "Hacim zayıf"
        )

    # --------------------------------------------------------
    # Volatilite
    # --------------------------------------------------------

    if (
        pd.notna(volatility)
        and volatility > 80
    ):

        penalty += PENALTY_HIGH_VOLATILITY

        reasons.append(
            "Volatilite yüksek"
        )

    # --------------------------------------------------------
    # MACD
    # --------------------------------------------------------

    if pd.notna(macd):

        if macd < 0:

            penalty += PENALTY_MACD_NEGATIVE

            reasons.append(
                "MACD negatif"
            )

    # --------------------------------------------------------
    # ADX
    # --------------------------------------------------------

    if pd.notna(adx):

        if adx < 15:

            penalty += PENALTY_ADX_WEAK

            reasons.append(
                "ADX çok zayıf"
            )

    return penalty, reasons


# ============================================================
# TEK HİSSE ANALİZİ
# ============================================================

def analyze_stock(
    symbol,
    stocks_df,
    prices_df,
    technical_df,
    fundamentals_df
):

    symbol = clean_symbol(
        symbol
    )

    price_df = get_price_data(
        prices_df,
        symbol
    )

    if price_df.empty:

        return None

    if len(price_df) < MIN_HISTORY:

        return None

    last_price = safe_float(
        price_df["close"].iloc[-1]
    )

    if pd.isna(last_price):

        return None

    if last_price < MIN_PRICE:

        return None

    # --------------------------------------------------------
    # Teknik tablodan son snapshot
    # --------------------------------------------------------

    technical_row = find_technical_row(
        technical_df,
        symbol
    )

    # --------------------------------------------------------
    # Teknik
    # --------------------------------------------------------

    technical = (
        calculate_advanced_technical_score(
            technical_row,
            last_price
        )
    )

    # --------------------------------------------------------
    # Momentum
    # --------------------------------------------------------

    momentum = (
        calculate_momentum_score(
            technical_row
        )
    )

    # --------------------------------------------------------
    # Fiyat bazlı teknik değerler
    # --------------------------------------------------------

    close = price_df[
        "close"
    ].astype(float)

    ema9 = close.ewm(
        span=9,
        adjust=False
    ).mean().iloc[-1]

    ema20 = close.ewm(
        span=20,
        adjust=False
    ).mean().iloc[-1]

    ema50 = close.ewm(
        span=50,
        adjust=False
    ).mean().iloc[-1]

    ema100 = close.ewm(
        span=100,
        adjust=False
    ).mean().iloc[-1]

    # RSI
    delta = close.diff()

    gain = delta.clip(
        lower=0
    )

    loss = -delta.clip(
        upper=0
    )

    avg_gain = gain.rolling(
        14
    ).mean()

    avg_loss = loss.rolling(
        14
    ).mean()

    rs = (
        avg_gain
        / avg_loss.replace(
            0,
            np.nan
        )
    )

    rsi_series = (
        100
        - (
            100
            / (1 + rs)
        )
    )

    rsi = (
        float(rsi_series.iloc[-1])
        if pd.notna(
            rsi_series.iloc[-1]
        )
        else 50
    )

    # Volume ratio
    volume_ratio = np.nan

    if "volume" in price_df.columns:

        volume = pd.to_numeric(
            price_df["volume"],
            errors="coerce"
        )

        if volume.notna().sum() >= 20:

            avg20 = volume.rolling(
                20
            ).mean().iloc[-1]

            current = volume.iloc[-1]

            if (
                pd.notna(current)
                and pd.notna(avg20)
                and avg20 > 0
            ):

                volume_ratio = (
                    current / avg20
                )

    # Volatilite
    returns = close.pct_change()

    volatility = (
        returns
        .rolling(20)
        .std()
        .iloc[-1]
        * math.sqrt(252)
        * 100
    )

    # --------------------------------------------------------
    # Finansal
    # --------------------------------------------------------

    financial_row = find_financial_row(
        fundamentals_df,
        symbol
    )

    financial = (
        calculate_financial_score(
            financial_row
        )
    )

    # --------------------------------------------------------
    # Likidite
    # --------------------------------------------------------

    liquidity_score, avg_volume_tl = (
        calculate_liquidity_score(
            price_df,
            technical_row
        )
    )

    # --------------------------------------------------------
    # Sektör
    # --------------------------------------------------------

    sector = get_sector(
        symbol,
        stocks_df
    )

    return {

        "symbol": symbol,

        "sector": sector,

        "price": last_price,

        "technical_score":
            technical["technical"],

        "trend_score":
            technical["trend"],

        "momentum_score":
            momentum["momentum"],

        "financial_score":
            financial["financial"],

        "financial_data_count":
            financial[
                "financial_data_count"
            ],

        "financial_data_quality":
            financial[
                "financial_data_quality"
            ],

        "liquidity_score":
            liquidity_score,

        "avg_volume_tl":
            avg_volume_tl,

        "rsi":
            rsi,

        "ema9":
            ema9,

        "ema20":
            ema20,

        "ema50":
            ema50,

        "ema100":
            ema100,

        "volume_ratio":
            volume_ratio,

        "volatility":
            volatility,

        # Advanced technical
        "macd":
            technical["macd"],

        "adx":
            technical["adx"],

        "atr_pct":
            technical["atr_pct"],

        "bollinger_position":
            technical[
                "bollinger_position"
            ],

        "bollinger_width":
            technical[
                "bollinger_width"
            ],

        "stochastic":
            technical[
                "stochastic"
            ],

        "ema20_50":
            technical[
                "ema20_50"
            ],

        "ema50_100":
            technical[
                "ema50_100"
            ],

        # Momentum
        "momentum20":
            momentum["momentum20"],

        "momentum60":
            momentum["momentum60"],

        "momentum120":
            momentum["momentum120"],

        "volume20":
            momentum["volume20"],

        "volume60":
            momentum["volume60"],

        "volume_trend":
            momentum["volume_trend"],

        "obv_trend":
            momentum["obv_trend"],

        "technical_data_count":
            technical[
                "technical_data_count"
            ],

        "technical_reasons":
            technical[
                "technical_reasons"
            ],

        "technical_warnings":
            technical[
                "technical_warnings"
            ],

        "momentum_reasons":
            momentum[
                "momentum_reasons"
            ],

        "momentum_warnings":
            momentum[
                "momentum_warnings"
            ],

        "financial_reasons":
            financial[
                "reasons"
            ],

        "financial_warnings":
            financial[
                "warnings"
            ]
    }


# ============================================================
# SEKTÖR SKORU
#
# Sektör artık sadece finansal skordan oluşmuyor.
#
# %40 Teknik
# %30 Momentum
# %20 Finansal
# %10 Likidite
# ============================================================

def calculate_sector_scores(
    all_rows
):

    if all_rows.empty:

        return {}

    scores = {}

    for sector, group in all_rows.groupby(
        "sector"
    ):

        if sector == SECTOR_UNKNOWN:

            continue

        components = []

        for col, weight in [

            ("technical_score", 0.40),

            ("momentum_score", 0.30),

            ("financial_score", 0.20),

            ("liquidity_score", 0.10)
        ]:

            if col not in group.columns:

                continue

            values = pd.to_numeric(
                group[col],
                errors="coerce"
            ).dropna()

            if not values.empty:

                components.append(
                    (
                        values.median(),
                        weight
                    )
                )

        if components:

            weight_sum = sum(
                w
                for _, w
                in components
            )

            scores[sector] = clamp(
                sum(
                    score * weight
                    for score, weight
                    in components
                )
                / weight_sum
            )

    return scores


def attach_sector_scores(df):

    if df.empty:

        return df

    sector_scores = (
        calculate_sector_scores(
            df
        )
    )

    df = df.copy()

    df[
        "sector_score"
    ] = df[
        "sector"
    ].map(
        sector_scores
    )

    # Sektör bulunamıyorsa nötr.
    df[
        "sector_score"
    ] = df[
        "sector_score"
    ].fillna(50)

    return df


# ============================================================
# DİNAMİK SKOR
# ============================================================

def calculate_dynamic_scores(
    df
):

    if df.empty:

        return df

    df = df.copy()

    market_score = (
        calculate_market_score()
    )

    df[
        "market_score"
    ] = market_score

    # --------------------------------------------------------
    # HAM SKOR
    # --------------------------------------------------------

    df[
        "dynamic_raw"
    ] = (

        df[
            "financial_score"
        ]
        * WEIGHT_FINANCIAL

        +

        df[
            "technical_score"
        ]
        * WEIGHT_TECHNICAL

        +

        df[
            "sector_score"
        ]
        * WEIGHT_SECTOR

        +

        df[
            "momentum_score"
        ]
        * WEIGHT_MOMENTUM

        +

        df[
            "liquidity_score"
        ]
        * WEIGHT_LIQUIDITY

        +

        df[
            "market_score"
        ]
        * WEIGHT_MARKET
    )

    # --------------------------------------------------------
    # Risk
    # --------------------------------------------------------

    penalties = []

    risk_reasons = []

    for _, row in df.iterrows():

        penalty, reasons = (
            calculate_risk_penalty(
                row.to_dict()
            )
        )

        penalties.append(
            penalty
        )

        risk_reasons.append(
            reasons
        )

    df[
        "risk_penalty"
    ] = penalties

    df[
        "risk_reasons"
    ] = risk_reasons

    df[
        "dynamic_score"
    ] = (
        df[
            "dynamic_raw"
        ]
        - df[
            "risk_penalty"
        ]
    ).clip(
        0,
        100
    )

    return df


# ============================================================
# ADAY SINIFLANDIRMA
# ============================================================

def classify_candidate(
    row
):

    score = row[
        "dynamic_score"
    ]

    financial = row[
        "financial_score"
    ]

    sector = row[
        "sector_score"
    ]

    technical = row[
        "technical_score"
    ]

    momentum = row[
        "momentum_score"
    ]

    if (
        score >= 75
        and financial >= 55
        and technical >= 60
        and momentum >= 55
    ):

        return "🟢 GÜÇLÜ PORTFÖY ADAYI"

    if (
        score >= 65
        and financial >= 45
        and technical >= 50
        and momentum >= 45
    ):

        return "🟢 PORTFÖY ADAYI"

    if (
        score >= 58
        and (
            technical >= 45
            or momentum >= 45
        )
    ):

        return "🟡 GELİŞEN ADAY"

    if score >= 50:

        return "🟠 İZLE"

    return "🔴 ZAYIF"


# ============================================================
# ADAY FİLTRESİ
#
# Burada artık 5 ayrı sert kapı yok.
# ============================================================

def apply_basic_filters(
    df
):

    if df.empty:

        return df

    result = df.copy()

    # --------------------------------------------------------
    # 1. Dinamik skor
    # --------------------------------------------------------

    result = result[
        result[
            "dynamic_score"
        ] >= MIN_DYNAMIC_SCORE
    ]

    if result.empty:
        return result

    # --------------------------------------------------------
    # 2. Çok kötü teknik yapı
    # --------------------------------------------------------

    result = result[
        result[
            "technical_score"
        ] >= HARD_TECHNICAL_FLOOR
    ]

    if result.empty:
        return result

    # --------------------------------------------------------
    # 3. Çok kötü momentum
    # --------------------------------------------------------

    result = result[
        result[
            "momentum_score"
        ] >= HARD_MOMENTUM_FLOOR
    ]

    if result.empty:
        return result

    # --------------------------------------------------------
    # 4. Çok kötü finansal yapı
    #
    # Finansal veri yoksa 40 nötr veriliyor.
    # Böylece veri eksikliği otomatik ölüm değil.
    # --------------------------------------------------------

    result = result[
        result[
            "financial_score"
        ] >= HARD_FINANCIAL_FLOOR
    ]

    return result.reset_index(
        drop=True
    )


# ============================================================
# PORTFÖY SEÇİMİ
# ============================================================

def select_balanced_portfolio(
    df,
    portfolio_size=10,
    max_sector_weight=0.30,
    max_per_sector=3
):

    if df.empty:

        return pd.DataFrame()

    working = df.copy()

    working = working.sort_values(
        [
            "dynamic_score",
            "technical_score",
            "momentum_score"
        ],
        ascending=False
    ).reset_index(
        drop=True
    )

    selected = []

    sector_counts = {}

    sector_count_limit = max(
        1,
        math.ceil(
            portfolio_size
            * max_sector_weight
        )
    )

    # --------------------------------------------------------
    # İlk tur
    # Her sektörden mümkün olduğunca birer güçlü aday.
    # --------------------------------------------------------

    for _, row in working.iterrows():

        if len(selected) >= portfolio_size:

            break

        sector = row[
            "sector"
        ]

        count = sector_counts.get(
            sector,
            0
        )

        if (
            sector != SECTOR_UNKNOWN
            and count >= max_per_sector
        ):

            continue

        if (
            sector != SECTOR_UNKNOWN
            and count >= sector_count_limit
        ):

            continue

        base_score = row[
            "dynamic_score"
        ]

        concentration_penalty = (
            count
            * SECTOR_CONCENTRATION_PENALTY
        )

        portfolio_score = (
            base_score
            - concentration_penalty
        )

        selected_row = row.copy()

        selected_row[
            "portfolio_score"
        ] = portfolio_score

        selected_row[
            "sector_selection_count"
        ] = count + 1

        selected.append(
            selected_row
        )

        sector_counts[
            sector
        ] = count + 1

    if not selected:

        return pd.DataFrame()

    result = pd.DataFrame(
        selected
    )

    result = result.sort_values(
        "portfolio_score",
        ascending=False
    ).reset_index(
        drop=True
    )

    # --------------------------------------------------------
    # Ağırlık
    # --------------------------------------------------------

    result[
        "portfolio_weight"
    ] = (
        result[
            "portfolio_score"
        ]
        .clip(
            lower=1
        )
    )

    total = result[
        "portfolio_weight"
    ].sum()

    if total > 0:

        result[
            "portfolio_weight_pct"
        ] = (
            result[
                "portfolio_weight"
            ]
            / total
            * 100
        )

    return result


# ============================================================
# SEÇİM GEREKÇESİ
# ============================================================

def build_reason_text(
    row
):

    reasons = []

    # --------------------------------------------------------
    # Finansal
    # --------------------------------------------------------

    if row[
        "financial_score"
    ] >= 70:

        reasons.append(
            "Finansal kalite güçlü"
        )

    elif row[
        "financial_score"
    ] >= 50:

        reasons.append(
            "Finansal kalite yeterli"
        )

    # --------------------------------------------------------
    # Teknik
    # --------------------------------------------------------

    if row[
        "technical_score"
    ] >= 75:

        reasons.append(
            "Teknik yapı güçlü"
        )

    elif row[
        "technical_score"
    ] >= 55:

        reasons.append(
            "Teknik yapı pozitif"
        )

    # --------------------------------------------------------
    # Momentum
    # --------------------------------------------------------

    if row[
        "momentum_score"
    ] >= 75:

        reasons.append(
            "Momentum güçlü"
        )

    elif row[
        "momentum_score"
    ] >= 55:

        reasons.append(
            "Momentum pozitif"
        )

    # --------------------------------------------------------
    # Sektör
    # --------------------------------------------------------

    if row[
        "sector_score"
    ] >= 70:

        reasons.append(
            "Sektör güçlü"
        )

    elif row[
        "sector_score"
    ] >= 55:

        reasons.append(
            "Sektör olumlu"
        )

    # --------------------------------------------------------
    # Hacim
    # --------------------------------------------------------

    if row[
        "liquidity_score"
    ] >= 70:

        reasons.append(
            "Likidite güçlü"
        )

    # --------------------------------------------------------
    # ADX
    # --------------------------------------------------------

    adx = row.get(
        "adx"
    )

    if (
        pd.notna(adx)
        and adx >= 25
    ):

        reasons.append(
            "Trend gücü yüksek"
        )

    # --------------------------------------------------------
    # MACD
    # --------------------------------------------------------

    macd = row.get(
        "macd"
    )

    if (
        pd.notna(macd)
        and macd > 0
    ):

        reasons.append(
            "MACD pozitif"
        )

    # --------------------------------------------------------
    # OBV
    # --------------------------------------------------------

    obv = row.get(
        "obv_trend"
    )

    if (
        pd.notna(obv)
        and obv > 0
    ):

        reasons.append(
            "OBV pozitif"
        )

    # --------------------------------------------------------
    # Risk
    # --------------------------------------------------------

    if row[
        "risk_penalty"
    ] > 0:

        reasons.append(
            "Risk düzeltmesi uygulandı"
        )

    return (
        " • ".join(
            reasons
        )
        if reasons
        else "Genel skor sıralaması"
    )


# ============================================================
# FORMAT
# ============================================================

def format_score(value):

    if pd.isna(value):

        return "-"

    return (
        f"{float(value):.1f}"
    )


def format_money(value):

    if pd.isna(value):

        return "-"

    value = float(value)

    if value >= 1_000_000_000:

        return (
            f"{value / 1_000_000_000:.2f} Mr TL"
        )

    if value >= 1_000_000:

        return (
            f"{value / 1_000_000:.2f} Mn TL"
        )

    return (
        f"{value:,.0f} TL"
    )


# ============================================================
# TEŞHİS PANELİ
# ============================================================

def build_diagnostic_counts(
    analysis_df,
    candidate_df,
    portfolio_df
):

    if analysis_df.empty:

        return {}

    counts = {}

    counts[
        "Analiz"
    ] = len(
        analysis_df
    )

    counts[
        "Dinamik ≥ 50"
    ] = int(
        (
            analysis_df[
                "dynamic_score"
            ] >= MIN_DYNAMIC_SCORE
        ).sum()
    )

    counts[
        "Teknik ≥ 20"
    ] = int(
        (
            analysis_df[
                "technical_score"
            ] >= HARD_TECHNICAL_FLOOR
        ).sum()
    )

    counts[
        "Momentum ≥ 15"
    ] = int(
        (
            analysis_df[
                "momentum_score"
            ] >= HARD_MOMENTUM_FLOOR
        ).sum()
    )

    counts[
        "Finansal ≥ 15"
    ] = int(
        (
            analysis_df[
                "financial_score"
            ] >= HARD_FINANCIAL_FLOOR
        ).sum()
    )

    counts[
        "Aday Havuzu"
    ] = len(
        candidate_df
    )

    counts[
        "Portföy"
    ] = len(
        portfolio_df
    )

    return counts


# ============================================================
# STREAMLIT
# ============================================================

st.set_page_config(
    page_title=(
        "BIST AI PRO - Dinamik Portföy"
    ),
    page_icon="📊",
    layout="wide"
)

st.title(
    "📊 BIST AI PRO - Dinamik Portföy"
)

st.caption(
    "v3 • KAP + Teknik + Momentum + Sektör + Likidite + Piyasa + Risk"
)


# ============================================================
# DB
# ============================================================

if not os.path.exists(DB_PATH):

    st.error(
        f"❌ {DB_PATH} bulunamadı."
    )

    st.stop()


tables = get_tables()

with st.expander(
    "🗄️ Veritabanı Kontrolü",
    expanded=False
):

    st.write(
        "Bulunan tablolar:"
    )

    st.write(
        tables
    )


# ============================================================
# VERİLER
# ============================================================

stocks_df = load_stocks()

prices_df = load_prices()

technical_df = load_technical()

fundamentals_df = load_fundamentals()


# ============================================================
# VERİ DURUMU
# ============================================================

c1, c2, c3, c4 = st.columns(4)

with c1:

    st.metric(
        "Stocks",
        len(stocks_df)
    )

with c2:

    st.metric(
        "Fiyat Satırı",
        len(prices_df)
    )

with c3:

    st.metric(
        "Teknik Satır",
        len(technical_df)
    )

with c4:

    st.metric(
        "Finansal Satır",
        len(fundamentals_df)
    )


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.header(
    "⚙️ Dinamik Portföy Ayarları"
)

pool = st.sidebar.selectbox(
    "Hisse Evreni",
    [
        "BIST500",
        "BIST100",
        "BIST50",
        "BIST30"
    ],
    index=0
)

portfolio_size = st.sidebar.slider(
    "Portföy Hisse Sayısı",
    5,
    15,
    10
)

max_sector_weight = st.sidebar.slider(
    "Maksimum Sektör Payı",
    0.20,
    0.50,
    0.30,
    0.05
)

max_per_sector = st.sidebar.slider(
    "Sektör Başına Maksimum Hisse",
    1,
    5,
    3
)

run_scan = st.sidebar.button(
    "🚀 DİNAMİK PORTFÖYÜ OLUŞTUR",
    use_container_width=True,
    type="primary"
)


# ============================================================
# GÖSTERGE DURUMU
# ============================================================

with st.expander(
    "🔬 Teknik Gösterge Veri Durumu",
    expanded=False
):

    if technical_df.empty:

        st.warning(
            "technical_analysis tablosu bulunamadı."
        )

    else:

        indicator_rows = []

        total_symbols = len(
            technical_df
        )

        for indicator, candidates in (
            TECH_COLUMNS.items()
        ):

            col = find_column(
                technical_df,
                candidates
            )

            if col:

                values = pd.to_numeric(
                    technical_df[col],
                    errors="coerce"
                )

                valid = int(
                    values.notna().sum()
                )

                missing = (
                    total_symbols
                    - valid
                )

                coverage = (
                    valid
                    / total_symbols
                    * 100
                    if total_symbols
                    else 0
                )

            else:

                valid = 0
                missing = total_symbols
                coverage = 0

            indicator_rows.append({

                "Gösterge":
                    indicator,

                "Kolon":
                    col
                    if col
                    else "BULUNAMADI",

                "Veri":
                    valid,

                "Eksik":
                    missing,

                "Kapsama %":
                    coverage
            })

        indicator_df = pd.DataFrame(
            indicator_rows
        )

        st.dataframe(
            indicator_df.style.format(
                {
                    "Kapsama %":
                        "{:.1f}"
                }
            ),
            use_container_width=True,
            hide_index=True
        )


# ============================================================
# TARAMA
# ============================================================

if (
    "dynamic_portfolio_result"
    not in st.session_state
    or run_scan
):

    with st.spinner(
        "BIST evreni gelişmiş motor ile analiz ediliyor..."
    ):

        universe = build_universe(
            stocks_df,
            pool
        )

        if not universe:

            st.error(
                "❌ Hisse evreni oluşturulamadı."
            )

            st.stop()

        analysis_rows = []

        progress = st.progress(
            0
        )

        total = len(
            universe
        )

        for i, symbol in enumerate(
            universe
        ):

            try:

                row = analyze_stock(
                    symbol,
                    stocks_df,
                    prices_df,
                    technical_df,
                    fundamentals_df
                )

                if row is not None:

                    analysis_rows.append(
                        row
                    )

            except Exception as exc:

                # Tek hisse hatası tüm taramayı bozmaz.
                pass

            progress.progress(
                min(
                    (i + 1)
                    / total,
                    1.0
                )
            )

        progress.empty()

        analysis_df = pd.DataFrame(
            analysis_rows
        )

        if analysis_df.empty:

            st.error(
                "❌ Analiz edilebilecek yeterli hisse bulunamadı."
            )

            st.stop()

        # ----------------------------------------------------
        # Sektör
        # ----------------------------------------------------

        analysis_df = (
            attach_sector_scores(
                analysis_df
            )
        )

        # ----------------------------------------------------
        # Dinamik
        # ----------------------------------------------------

        analysis_df = (
            calculate_dynamic_scores(
                analysis_df
            )
        )

        # ----------------------------------------------------
        # Sınıflandırma
        # ----------------------------------------------------

        analysis_df[
            "classification"
        ] = analysis_df.apply(
            classify_candidate,
            axis=1
        )

        # ----------------------------------------------------
        # Filtre
        # ----------------------------------------------------

        candidate_df = (
            apply_basic_filters(
                analysis_df
            )
        )

        # ----------------------------------------------------
        # Portföy
        # ----------------------------------------------------

        portfolio_df = (
            select_balanced_portfolio(
                candidate_df,
                portfolio_size,
                max_sector_weight,
                max_per_sector
            )
        )

        # ----------------------------------------------------
        # Gerekçe
        # ----------------------------------------------------

        if not portfolio_df.empty:

            portfolio_df[
                "selection_reason"
            ] = portfolio_df.apply(
                build_reason_text,
                axis=1
            )

        # ----------------------------------------------------
        # Session
        # ----------------------------------------------------

        st.session_state[
            "dynamic_portfolio_result"
        ] = analysis_df

        st.session_state[
            "dynamic_portfolio_candidates"
        ] = candidate_df

        st.session_state[
            "dynamic_portfolio_selected"
        ] = portfolio_df


# ============================================================
# SONUÇLAR
# ============================================================

analysis_df = st.session_state.get(
    "dynamic_portfolio_result",
    pd.DataFrame()
)

candidate_df = st.session_state.get(
    "dynamic_portfolio_candidates",
    pd.DataFrame()
)

portfolio_df = st.session_state.get(
    "dynamic_portfolio_selected",
    pd.DataFrame()
)


if analysis_df.empty:

    st.warning(
        "Henüz analiz sonucu yok."
    )

    st.stop()


# ============================================================
# TEŞHİS
# ============================================================

st.divider()

st.subheader(
    "🔬 Seçim Motoru Teşhis Paneli"
)

diag = build_diagnostic_counts(
    analysis_df,
    candidate_df,
    portfolio_df
)

diag_cols = st.columns(
    len(diag)
)

for col, (
    label,
    value
) in zip(
    diag_cols,
    diag.items()
):

    with col:

        st.metric(
            label,
            value
        )

st.caption(
    "Bu panel hangi aşamada kaç hissenin kaldığını gösterir."
)


# ============================================================
# SKOR İSTATİSTİKLERİ
# ============================================================

st.subheader(
    "📊 Skor Dağılımı"
)

score_cols = st.columns(6)

metrics = [

    (
        "Ort. Dinamik",
        analysis_df[
            "dynamic_score"
        ].mean()
    ),

    (
        "Ort. Finansal",
        analysis_df[
            "financial_score"
        ].mean()
    ),

    (
        "Ort. Teknik",
        analysis_df[
            "technical_score"
        ].mean()
    ),

    (
        "Ort. Momentum",
        analysis_df[
            "momentum_score"
        ].mean()
    ),

    (
        "Ort. Sektör",
        analysis_df[
            "sector_score"
        ].mean()
    ),

    (
        "En Yüksek",
        analysis_df[
            "dynamic_score"
        ].max()
    )
]

for col, (
    label,
    value
) in zip(
    score_cols,
    metrics
):

    with col:

        st.metric(
            label,
            f"{value:.1f}"
        )


# ============================================================
# PORTFÖY ÖZET
# ============================================================

st.divider()

st.subheader(
    "🎯 Dinamik Portföy Özeti"
)

s1, s2, s3, s4, s5 = st.columns(5)

with s1:

    st.metric(
        "Taranan",
        len(analysis_df)
    )

with s2:

    st.metric(
        "Aday Havuzu",
        len(candidate_df)
    )

with s3:

    st.metric(
        "Seçilen",
        len(portfolio_df)
    )

with s4:

    st.metric(
        "En Yüksek Skor",
        f"{analysis_df['dynamic_score'].max():.1f}"
    )

with s5:

    if not portfolio_df.empty:

        st.metric(
            "Portföy Ort. Skor",
            f"{portfolio_df['portfolio_score'].mean():.1f}"
        )

    else:

        st.metric(
            "Portföy Ort. Skor",
            "-"
        )


# ============================================================
# PORTFÖY
# ============================================================

st.divider()

st.subheader(
    "🏆 Önerilen Dinamik Portföy"
)

if portfolio_df.empty:

    st.warning(
        "Bu taramada minimum kalite seviyesini geçen dengeli portföy oluşturulamadı."
    )

    st.info(
        "Aşağıdaki 'En İyi Alternatifler' tablosu "
        "sistemin neden aday üretemediğini gösterir."
    )

else:

    display = portfolio_df[
        [
            "symbol",
            "sector",
            "portfolio_score",
            "dynamic_score",
            "financial_score",
            "sector_score",
            "technical_score",
            "momentum_score",
            "market_score",
            "liquidity_score",
            "risk_penalty",
            "portfolio_weight_pct"
        ]
    ].copy()

    display.columns = [

        "Hisse",
        "Sektör",
        "Portföy Skoru",
        "Dinamik",
        "Finansal",
        "Sektör Skoru",
        "Teknik",
        "Momentum",
        "Piyasa",
        "Likidite",
        "Risk",
        "Önerilen %"
    ]

    _fmt_cols = [
        "Portföy Skoru", "Dinamik", "Finansal", "Sektör Skoru",
        "Teknik", "Momentum", "Piyasa", "Likidite", "Risk",
        "Önerilen %"
    ]
    for _c in _fmt_cols:
        if _c in display.columns:
            display[_c] = pd.to_numeric(display[_c], errors="coerce")

    st.dataframe(
        display.style.format(
            {
                "Portföy Skoru":
                    "{:.1f}",

                "Dinamik":
                    "{:.1f}",

                "Finansal":
                    "{:.1f}",

                "Sektör Skoru":
                    "{:.1f}",

                "Teknik":
                    "{:.1f}",

                "Momentum":
                    "{:.1f}",

                "Piyasa":
                    "{:.1f}",

                "Likidite":
                    "{:.1f}",

                "Risk":
                    "{:.1f}",

                "Önerilen %":
                    "{:.1f}"
            }
        ),
        use_container_width=True,
        hide_index=True
    )


# ============================================================
# EN İYİ ALTERNATİFLER
# ============================================================

st.divider()

st.subheader(
    "🥈 En İyi Alternatifler"
)

alternatives = (
    analysis_df
    .sort_values(
        [
            "dynamic_score",
            "technical_score",
            "momentum_score"
        ],
        ascending=False
    )
    .head(20)
    .copy()
)

alt_display = alternatives[
    [
        "symbol",
        "sector",
        "classification",
        "dynamic_score",
        "financial_score",
        "sector_score",
        "technical_score",
        "momentum_score",
        "liquidity_score",
        "risk_penalty"
    ]
].copy()

alt_display.columns = [

    "Hisse",
    "Sektör",
    "Durum",
    "Dinamik",
    "Finansal",
    "Sektör Skoru",
    "Teknik",
    "Momentum",
    "Likidite",
    "Risk"
]

_fmt_cols = ["Dinamik", "Finansal", "Sektör Skoru", "Teknik", "Momentum", "Likidite", "Risk"]
for _c in _fmt_cols:
    if _c in alt_display.columns:
        alt_display[_c] = pd.to_numeric(alt_display[_c], errors="coerce")

st.dataframe(
    alt_display.style.format(
        {
            "Dinamik": "{:.1f}",
            "Finansal": "{:.1f}",
            "Sektör Skoru": "{:.1f}",
            "Teknik": "{:.1f}",
            "Momentum": "{:.1f}",
            "Likidite": "{:.1f}",
            "Risk": "{:.1f}"
        }
    ),
    use_container_width=True,
    hide_index=True
)


# ============================================================
# DETAYLI PORTFÖY GEREKÇESİ
# ============================================================

if not portfolio_df.empty:

    st.divider()

    st.subheader(
        "🔎 Portföy Seçim Gerekçeleri"
    )

    for _, row in portfolio_df.iterrows():

        with st.expander(
            f"{row['symbol']} — "
            f"{row['sector']} — "
            f"Skor {row['portfolio_score']:.1f}"
        ):

            a1, a2, a3, a4, a5 = st.columns(5)

            with a1:

                st.metric(
                    "Dinamik",
                    f"{row['dynamic_score']:.1f}"
                )

            with a2:

                st.metric(
                    "Finansal",
                    f"{row['financial_score']:.1f}"
                )

            with a3:

                st.metric(
                    "Teknik",
                    f"{row['technical_score']:.1f}"
                )

            with a4:

                st.metric(
                    "Momentum",
                    f"{row['momentum_score']:.1f}"
                )

            with a5:

                st.metric(
                    "Sektör",
                    f"{row['sector_score']:.1f}"
                )

            st.write(
                "### Neden seçildi?"
            )

            reason_text = (
                row.get(
                    "selection_reason",
                    ""
                )
            )

            if reason_text:

                for reason in (
                    reason_text.split(
                        " • "
                    )
                ):

                    st.write(
                        f"✅ {reason}"
                    )

            if row.get(
                "technical_reasons"
            ):

                st.write(
                    "**Teknik:**"
                )

                for reason in row[
                    "technical_reasons"
                ]:

                    st.write(
                        f"• {reason}"
                    )

            if row.get(
                "momentum_reasons"
            ):

                st.write(
                    "**Momentum:**"
                )

                for reason in row[
                    "momentum_reasons"
                ]:

                    st.write(
                        f"• {reason}"
                    )

            if row.get(
                "financial_reasons"
            ):

                st.write(
                    "**KAP / Finansal:**"
                )

                for reason in row[
                    "financial_reasons"
                ]:

                    st.write(
                        f"• {reason}"
                    )

            if row.get(
                "risk_reasons"
            ):

                st.write(
                    "**Risk:**"
                )

                for reason in row[
                    "risk_reasons"
                ]:

                    st.write(
                        f"⚠️ {reason}"
                    )

            st.write(
                f"**Fiyat:** "
                f"{row['price']:.2f} TL"
            )

            st.write(
                f"**RSI:** "
                f"{format_score(row['rsi'])}"
            )

            st.write(
                f"**ADX:** "
                f"{format_score(row['adx'])}"
            )

            st.write(
                f"**MACD:** "
                f"{format_score(row['macd'])}"
            )

            st.write(
                f"**20G Momentum:** "
                f"{format_score(row['momentum20'])}"
            )

            st.write(
                f"**60G Momentum:** "
                f"{format_score(row['momentum60'])}"
            )

            st.write(
                f"**120G Momentum:** "
                f"{format_score(row['momentum120'])}"
            )

            st.write(
                f"**20G Hacim Oranı:** "
                f"{format_score(row['volume20'])}"
            )

            st.write(
                f"**OBV Trendi:** "
                f"{format_score(row['obv_trend'])}"
            )

            st.write(
                f"**Finansal Veri Kalitesi:** "
                f"{row['financial_data_quality']:.0f}%"
            )


# ============================================================
# TÜM ADAYLAR
# ============================================================

st.divider()

with st.expander(
    "📋 Tüm Aday Havuzunu Gör",
    expanded=False
):

    if candidate_df.empty:

        st.warning(
            "Aday havuzu boş."
        )

    else:

        candidates_display = (
            candidate_df
            .sort_values(
                "dynamic_score",
                ascending=False
            )
            [
                [
                    "symbol",
                    "sector",
                    "classification",
                    "dynamic_score",
                    "financial_score",
                    "financial_data_quality",
                    "sector_score",
                    "technical_score",
                    "momentum_score",
                    "market_score",
                    "liquidity_score",
                    "risk_penalty"
                ]
            ]
            .copy()
        )

        candidates_display.columns = [

            "Hisse",
            "Sektör",
            "Durum",
            "Dinamik",
            "Finansal",
            "Finansal Veri %",
            "Sektör Skoru",
            "Teknik",
            "Momentum",
            "Piyasa",
            "Likidite",
            "Risk"
        ]

        _fmt_cols = ["Dinamik", "Finansal", "Finansal Veri %", "Sektör Skoru", "Teknik", "Momentum", "Piyasa", "Likidite", "Risk"]
        for _c in _fmt_cols:
            if _c in candidates_display.columns:
                candidates_display[_c] = pd.to_numeric(candidates_display[_c], errors="coerce")

        st.dataframe(
            candidates_display.style.format(
                {
                    "Dinamik":
                        "{:.1f}",

                    "Finansal":
                        "{:.1f}",

                    "Finansal Veri %":
                        "{:.0f}",

                    "Sektör Skoru":
                        "{:.1f}",

                    "Teknik":
                        "{:.1f}",

                    "Momentum":
                        "{:.1f}",

                    "Piyasa":
                        "{:.1f}",

                    "Likidite":
                        "{:.1f}",

                    "Risk":
                        "{:.1f}"
                }
            ),
            use_container_width=True,
            hide_index=True
        )


# ============================================================
# ELENENLERİN NEDENLERİ
# ============================================================

with st.expander(
    "🔍 Elenen / Zayıf Hisselerin Nedenleri",
    expanded=False
):

    diagnostic_df = analysis_df.copy()

    def elimination_reason(
        row
    ):

        reasons = []

        if (
            row["technical_score"]
            < HARD_TECHNICAL_FLOOR
        ):

            reasons.append(
                "Teknik kalite çok düşük"
            )

        if (
            row["momentum_score"]
            < HARD_MOMENTUM_FLOOR
        ):

            reasons.append(
                "Momentum çok düşük"
            )

        if (
            row["financial_score"]
            < HARD_FINANCIAL_FLOOR
        ):

            reasons.append(
                "Finansal kalite çok düşük"
            )

        if (
            row["dynamic_score"]
            < MIN_DYNAMIC_SCORE
        ):

            reasons.append(
                "Dinamik skor < 50"
            )

        if not reasons:

            return "Aday havuzunda / portföy seçiminde elendi"

        return " • ".join(
            reasons
        )

    diagnostic_df[
        "elimination_reason"
    ] = diagnostic_df.apply(
        elimination_reason,
        axis=1
    )

    diagnostic_display = (
        diagnostic_df
        .sort_values(
            "dynamic_score",
            ascending=False
        )
        [
            [
                "symbol",
                "sector",
                "dynamic_score",
                "financial_score",
                "technical_score",
                "momentum_score",
                "sector_score",
                "elimination_reason"
            ]
        ]
        .head(100)
        .copy()
    )

    diagnostic_display.columns = [

        "Hisse",
        "Sektör",
        "Dinamik",
        "Finansal",
        "Teknik",
        "Momentum",
        "Sektör Skoru",
        "Sonuç / Neden"
    ]

    _fmt_cols = ["Dinamik", "Finansal", "Teknik", "Momentum", "Sektör Skoru"]
    for _c in _fmt_cols:
        if _c in diagnostic_display.columns:
            diagnostic_display[_c] = pd.to_numeric(diagnostic_display[_c], errors="coerce")

    st.dataframe(
        diagnostic_display.style.format(
            {
                "Dinamik": "{:.1f}",
                "Finansal": "{:.1f}",
                "Teknik": "{:.1f}",
                "Momentum": "{:.1f}",
                "Sektör Skoru": "{:.1f}"
            }
        ),
        use_container_width=True,
        hide_index=True
    )


# ============================================================
# SEKTÖR DAĞILIMI
# ============================================================

if not portfolio_df.empty:

    st.divider()

    st.subheader(
        "🏭 Portföy Sektör Dağılımı"
    )

    sector_distribution = (
        portfolio_df
        .groupby("sector")
        .agg(
            Hisse_Sayısı=(
                "symbol",
                "count"
            ),

            Ortalama_Skor=(
                "dynamic_score",
                "mean"
            ),

            Agirlik=(
                "portfolio_weight_pct",
                "sum"
            )
        )
        .reset_index()
        .sort_values(
            "Agirlik",
            ascending=False
        )
    )

    sector_distribution.columns = [

        "Sektör",
        "Hisse Sayısı",
        "Ortalama Skor",
        "Ağırlık %"
    ]

    st.dataframe(
        sector_distribution.style.format(
            {
                "Ortalama Skor":
                    "{:.1f}",

                "Ağırlık %":
                    "{:.1f}"
            }
        ),
        use_container_width=True,
        hide_index=True
    )


# ============================================================
# SKOR SİSTEMİ
# ============================================================

with st.expander(
    "🧠 Yeni Dinamik Portföy Skor Sistemi",
    expanded=False
):

    st.markdown(
        """
### Ana Skor

| Faktör | Ağırlık |
|---|---:|
| 💰 KAP / Finansal Kalite | **%25** |
| 📈 Teknik Kalite | **%25** |
| 🏭 Sektör Gücü | **%15** |
| 🚀 Momentum | **%15** |
| 💧 Likidite | **%10** |
| 🌍 Piyasa Uyumu | **%10** |
| **TOPLAM** | **%100** |

### Teknik kalite içinde kullanılan göstergeler

- MACD
- ADX
- ATR %
- Bollinger Pozisyonu
- Bollinger Genişliği
- Stochastic
- EMA9 Mesafesi
- EMA20 Mesafesi
- EMA50 Mesafesi
- EMA20-50
- EMA50-100

### Momentum içinde

- 20G Momentum
- 60G Momentum
- 120G Momentum
- 20G Hacim Oranı
- 60G Hacim Oranı
- Hacim Trendi
- OBV Trendi

### Sektör skoru

Sektör skoru artık sadece bilanço ile belirlenmez.

- %40 Teknik
- %30 Momentum
- %20 Finansal
- %10 Likidite

### Önemli

Finansal veri eksikliği tek başına hisseyi otomatik olarak sıfırlamaz.

Finansal veri kalitesi ayrıca gösterilir.

Ama gerçekten kötü finansal skor yine aşağı çekilir.

### Portföy mantığı

Amaç:

> **En yüksek 10 skoru körü körüne almak değil; kalite + trend + momentum + sektör + likidite + risk açısından dengeli portföy oluşturmaktır.**
"""
    )


# ============================================================
# SON
# ============================================================

st.caption(
    "Son çalışma: "
    + datetime.now().strftime(
        "%d.%m.%Y %H:%M:%S"
    )
)

st.caption(
    "BIST AI PRO — Dinamik Portföy Motoru v3"
)