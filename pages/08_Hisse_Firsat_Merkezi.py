# ============================================================
# BIST AI PRO
# fırsat_analizi.py
#
# HİSSE FIRSAT ANALİZ MOTORU
#
# AMAÇ
# ------------------------------------------------------------
# Bu modül BIST evrenindeki hisseleri:
#
#   Teknik
#   Momentum
#   Finansal
#   Temel
#   Sektör
#   Piyasa
#   Likidite
#   Günlük Trade
#   Risk / Ödül
#
# kriterleriyle analiz eder.
#
# FIRSAT MERKEZİ MANTIĞI
# ------------------------------------------------------------
# 1. Önce mümkün olan en geniş aday havuzu oluşturulur.
# 2. Hisseler skorlanır.
# 3. Kalite ve veri yeterliliği kontrol edilir.
# 4. A / B / C fırsat sınıfı belirlenir.
# 5. Hisseler fırsat skoruna göre sıralanır.
#
# ÖNEMLİ
# ------------------------------------------------------------
# Bu modül günlük trade motorunun yerine geçmez.
#
# Günlük Trade:
#     kısa vadeli işlem
#
# Fırsat Merkezi:
#     kaliteli hisse + teknik yapı + momentum
#     + sektör + finansal + temel + risk/ödül
#
# ============================================================

from __future__ import annotations

import os
import sqlite3
import warnings
from typing import Any, Dict, Optional, Tuple, List

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")


# ============================================================
# AYARLAR
# ============================================================

DEFAULT_DB_PATH = "borsa.db"

MIN_HISTORY = 60

DEFAULT_MIN_OPPORTUNITY = 50.0

# Bunlar SERT ELEME değildir.
# Aday havuzu oluştururken kullanılabilecek başlangıç
# değerleridir.
DEFAULT_MIN_DYNAMIC = 45.0
DEFAULT_MIN_SECTOR = 35.0
DEFAULT_MIN_TECHNICAL = 35.0
DEFAULT_MIN_LIQUIDITY = 5_000_000

# ============================================================
# FIRSAT SKOR AĞIRLIKLARI
# ============================================================

OPPORTUNITY_WEIGHTS = {
    "dynamic": 0.30,
    "technical": 0.18,
    "momentum": 0.14,
    "financial": 0.10,
    "fundamental": 0.08,
    "sector": 0.08,
    "market": 0.04,
    "liquidity": 0.04,
    "trade": 0.04,
}

# Toplam:
# 30 + 18 + 14 + 10 + 8 + 8 + 4 + 4 + 4 = 100


# ============================================================
# GENEL YARDIMCI FONKSİYONLAR
# ============================================================

def clamp(
    value: Any,
    low: float = 0.0,
    high: float = 100.0,
) -> float:

    try:
        value = float(value)
    except Exception:
        return low

    if np.isnan(value) or np.isinf(value):
        return low

    return max(low, min(high, value))


def safe_float(
    value: Any,
    default: float = 0.0,
) -> float:

    try:

        if value is None:
            return default

        value = float(value)

        if np.isnan(value) or np.isinf(value):
            return default

        return value

    except Exception:

        return default


def clean_symbol(
    symbol: Any,
) -> str:

    if symbol is None:
        return ""

    return (
        str(symbol)
        .upper()
        .strip()
        .replace(".IS", "")
    )


def normalize_columns(
    df: pd.DataFrame,
) -> pd.DataFrame:

    if df is None or df.empty:
        return pd.DataFrame()

    result = df.copy()

    result.columns = [
        str(c).strip()
        for c in result.columns
    ]

    return result


# ============================================================
# DB
# ============================================================

def get_db_path(
    db_path: Optional[str] = None,
) -> str:

    if db_path:
        return db_path

    candidates = [
        DEFAULT_DB_PATH,
        os.path.join(
            os.path.dirname(
                os.path.abspath(__file__)
            ),
            DEFAULT_DB_PATH,
        ),
    ]

    for path in candidates:

        if os.path.exists(path):
            return path

    return DEFAULT_DB_PATH


def get_connection(
    db_path: Optional[str] = None,
):

    return sqlite3.connect(
        get_db_path(db_path)
    )


def table_exists(
    table_name: str,
    db_path: Optional[str] = None,
) -> bool:

    try:

        conn = get_connection(db_path)

        row = conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type='table'
            AND name=?
            """,
            (table_name,),
        ).fetchone()

        conn.close()

        return row is not None

    except Exception:

        return False


def get_table_columns(
    table_name: str,
    db_path: Optional[str] = None,
) -> List[str]:

    try:

        conn = get_connection(db_path)

        rows = conn.execute(
            f"PRAGMA table_info({table_name})"
        ).fetchall()

        conn.close()

        return [
            row[1]
            for row in rows
        ]

    except Exception:

        return []


def read_table(
    table_name: str,
    db_path: Optional[str] = None,
) -> pd.DataFrame:

    if not table_exists(
        table_name,
        db_path,
    ):
        return pd.DataFrame()

    try:

        conn = get_connection(db_path)

        df = pd.read_sql_query(
            f"SELECT * FROM {table_name}",
            conn,
        )

        conn.close()

        return normalize_columns(df)

    except Exception:

        return pd.DataFrame()


# ============================================================
# HİSSE KOLONU BUL
# ============================================================

def find_symbol_column(
    df: pd.DataFrame,
) -> Optional[str]:

    if df is None or df.empty:
        return None

    candidates = [
        "symbol",
        "ticker",
        "hisse",
        "Hisse",
        "code",
        "Kod",
        "ticker_symbol",
    ]

    for col in candidates:

        if col in df.columns:
            return col

    return None


# ============================================================
# DİNAMİK CACHE
# ============================================================

def load_dynamic_cache(
    db_path: Optional[str] = None,
) -> pd.DataFrame:

    df = read_table(
        "dynamic_portfolio_cache",
        db_path,
    )

    if df.empty:
        return df

    symbol_col = find_symbol_column(df)

    if symbol_col:

        df["symbol"] = (
            df[symbol_col]
            .apply(clean_symbol)
        )

        df = df[
            df["symbol"] != ""
        ]

    return df


# ============================================================
# TEKNİK SNAPSHOT
# ============================================================

def load_technical_snapshot(
    db_path: Optional[str] = None,
) -> pd.DataFrame:

    df = read_table(
        "technical_analysis",
        db_path,
    )

    if df.empty:
        return df

    symbol_col = find_symbol_column(df)

    if symbol_col:

        df["symbol"] = (
            df[symbol_col]
            .apply(clean_symbol)
        )

        df = df[
            df["symbol"] != ""
        ]

    return df


# ============================================================
# BIST EVRENİ
# ============================================================

def load_universe(
    db_path: Optional[str] = None,
) -> pd.DataFrame:

    tables = [
        "bist500_universe",
        "stocks",
    ]

    for table in tables:

        df = read_table(
            table,
            db_path,
        )

        if df.empty:
            continue

        symbol_col = find_symbol_column(df)

        if symbol_col:

            df["symbol"] = (
                df[symbol_col]
                .apply(clean_symbol)
            )

            df = df[
                df["symbol"] != ""
            ]

            if not df.empty:
                return df

    return pd.DataFrame()

# ============================================================
# EVREN OLUŞTUR
# ============================================================

def build_analysis_universe(
    db_path: Optional[str] = None,
) -> pd.DataFrame:

    universe = load_universe(
        db_path
    )

    cache = load_dynamic_cache(
        db_path
    )

    technical = load_technical_snapshot(
        db_path
    )

    frames = []

    # --------------------------------------------------------
    # ANA EVREN
    # --------------------------------------------------------

    if (
        universe is not None
        and not universe.empty
    ):
        frames.append(
            universe.copy()
        )

    # --------------------------------------------------------
    # DİNAMİK PORTFÖY CACHE
    # --------------------------------------------------------

    if (
        cache is not None
        and not cache.empty
    ):
        frames.append(
            cache.copy()
        )

    # --------------------------------------------------------
    # TEKNİK SNAPSHOT
    # --------------------------------------------------------

    if (
        technical is not None
        and not technical.empty
    ):
        frames.append(
            technical.copy()
        )

    # --------------------------------------------------------
    # HİÇ VERİ YOK
    # --------------------------------------------------------

    if not frames:
        return pd.DataFrame()

    # ========================================================
    # İLK FRAME ANA TABLO
    # ========================================================

    result = frames[0].copy()

    # Duplicate kolonları temizle
    result = result.loc[
        :,
        ~result.columns.duplicated()
    ].copy()

    # ========================================================
    # SEMBOL KOLONU KONTROLÜ
    # ========================================================

    if "symbol" not in result.columns:

        # Alternatif kolon isimlerini bul
        symbol_candidates = [
            "ticker",
            "hisse",
            "Hisse",
            "code",
            "Symbol",
        ]

        found_symbol = None

        for candidate in symbol_candidates:

            if candidate in result.columns:
                found_symbol = candidate
                break

        if found_symbol is not None:

            result = result.rename(
                columns={
                    found_symbol: "symbol"
                }
            )

    # ========================================================
    # FRAME'LERİ BİRLEŞTİR
    # ========================================================

    for extra in frames[1:]:

        # ----------------------------------------------------
        # Geçersiz frame
        # ----------------------------------------------------

        if (
            extra is None
            or extra.empty
        ):
            continue

        extra = extra.copy()

        # ----------------------------------------------------
        # Duplicate kolonları temizle
        # ----------------------------------------------------

        extra = extra.loc[
            :,
            ~extra.columns.duplicated()
        ].copy()

        # ----------------------------------------------------
        # SYMBOL KOLONU BUL
        # ----------------------------------------------------

        if "symbol" not in extra.columns:

            symbol_candidates = [
                "ticker",
                "hisse",
                "Hisse",
                "code",
                "Symbol",
            ]

            found_symbol = None

            for candidate in symbol_candidates:

                if candidate in extra.columns:
                    found_symbol = candidate
                    break

            if found_symbol is not None:

                extra = extra.rename(
                    columns={
                        found_symbol: "symbol"
                    }
                )

        # ----------------------------------------------------
        # SYMBOL YOKSA ATLA
        # ----------------------------------------------------

        if "symbol" not in extra.columns:
            continue

        # ----------------------------------------------------
        # RESULT'TA SYMBOL YOKSA
        # ----------------------------------------------------

        if "symbol" not in result.columns:

            result = extra.copy()

            result = result.loc[
                :,
                ~result.columns.duplicated()
            ].copy()

            continue

        # ====================================================
        # SYMBOL'LERİ TEMİZLE
        # ====================================================

        result["symbol"] = (
            result["symbol"]
            .apply(clean_symbol)
        )

        extra["symbol"] = (
            extra["symbol"]
            .apply(clean_symbol)
        )

        # Boş sembolleri temizle
        result = result[
            result["symbol"] != ""
        ].copy()

        extra = extra[
            extra["symbol"] != ""
        ].copy()

        # ====================================================
        # AYNI SYMBOL İÇİN TEK KAYIT
        # ====================================================

        result = result.drop_duplicates(
            subset=["symbol"],
            keep="last",
        )

        extra = extra.drop_duplicates(
            subset=["symbol"],
            keep="last",
        )

        # ====================================================
        # ÇAKIŞAN KOLONLARI TEMİZLE
        #
        # ÖNEMLİ:
        #
        # result'ta zaten olan kolonları extra'dan
        # almıyoruz.
        #
        # Böylece:
        #
        # id_extra
        # updated_at_extra
        # vs.
        #
        # oluşmuyor.
        # ====================================================

        extra_columns = [
            col
            for col in extra.columns
            if (
                col == "symbol"
                or col not in result.columns
            )
        ]

        extra = extra[
            extra_columns
        ].copy()

        # ====================================================
        # GÜVENLİ MERGE
        # ====================================================

        if len(extra.columns) > 1:

            result = result.merge(
                extra,
                on="symbol",
                how="left",
            )

        # ====================================================
        # MERGE SONRASI DUPLICATE KOLON KONTROLÜ
        # ====================================================

        result = result.loc[
            :,
            ~result.columns.duplicated()
        ].copy()

    # ========================================================
    # SYMBOL TEMİZLE
    # ========================================================

    if "symbol" in result.columns:

        result["symbol"] = (
            result["symbol"]
            .apply(clean_symbol)
        )

        result = result[
            result["symbol"] != ""
        ].copy()

    # ========================================================
    # SON DUPLICATE TEMİZLİĞİ
    # ========================================================

    if "symbol" in result.columns:

        result = (
            result
            .drop_duplicates(
                subset=["symbol"],
                keep="first",
            )
            .reset_index(
                drop=True
            )
        )

    # ========================================================
    # KOLON DUPLICATE TEMİZLİĞİ
    # ========================================================

    result = result.loc[
        :,
        ~result.columns.duplicated()
    ].copy()

    return result
    
    # --------------------------------------------------------
    # Hiç veri yok
    # --------------------------------------------------------

    if not frames:
        return pd.DataFrame()

    # --------------------------------------------------------
    # İLK DATAFRAME
    # --------------------------------------------------------

    result = frames[0].copy()

    # Duplicate kolonları temizle
    result = result.loc[
        :,
        ~result.columns.duplicated()
    ].copy()

    # --------------------------------------------------------
    # SYMBOL KONTROLÜ
    # --------------------------------------------------------

    if "symbol" not in result.columns:

        # Alternatif kolon isimleri
        for candidate in [
            "ticker",
            "hisse",
            "code",
            "Hisse",
        ]:

            if candidate in result.columns:

                result = result.rename(
                    columns={
                        candidate: "symbol"
                    }
                )

                break

    # --------------------------------------------------------
    # DİĞER DATAFRAME'LERİ BİRLEŞTİR
    # --------------------------------------------------------

    for extra in frames[1:]:

        if (
            extra is None
            or extra.empty
        ):
            continue

        extra = extra.copy()

        # ----------------------------------------------------
        # SYMBOL KOLONU
        # ----------------------------------------------------

        if "symbol" not in extra.columns:

            for candidate in [
                "ticker",
                "hisse",
                "code",
                "Hisse",
            ]:

                if candidate in extra.columns:

                    extra = extra.rename(
                        columns={
                            candidate: "symbol"
                        }
                    )

                    break

        if "symbol" not in extra.columns:
            continue

        if "symbol" not in result.columns:

            result = extra.copy()

            result = result.loc[
                :,
                ~result.columns.duplicated()
            ].copy()

            continue

        # ----------------------------------------------------
        # SYMBOL STANDARDİZASYONU
        # ----------------------------------------------------

        result["symbol"] = (
            result["symbol"]
            .apply(clean_symbol)
        )

        extra["symbol"] = (
            extra["symbol"]
            .apply(clean_symbol)
        )

        # Boş sembolleri kaldır
        result = result[
            result["symbol"] != ""
        ].copy()

        extra = extra[
            extra["symbol"] != ""
        ].copy()

        # ----------------------------------------------------
        # DUPLICATE KOLONLARI TEMİZLE
        # ----------------------------------------------------

        result = result.loc[
            :,
            ~result.columns.duplicated()
        ].copy()

        extra = extra.loc[
            :,
            ~extra.columns.duplicated()
        ].copy()

        # ----------------------------------------------------
        # EXTRA'DAKİ AYNI SEMBOLLERİ TEKİLLEŞTİR
        # ----------------------------------------------------

        extra = (
            extra
            .drop_duplicates(
                subset=["symbol"],
                keep="last",
            )
            .reset_index(drop=True)
        )

        # ----------------------------------------------------
        # ÇAKIŞAN KOLONLARI BELİRLE
        #
        # symbol hariç result'ta zaten bulunan kolonları
        # extra'dan almıyoruz.
        #
        # Böylece:
        #
        # id
        # updated_at
        # price
        # sector
        #
        # gibi kolonların _extra versiyonları oluşmuyor.
        # ----------------------------------------------------

        extra_cols = [
            col
            for col in extra.columns
            if (
                col == "symbol"
                or col not in result.columns
            )
        ]

        extra = extra[
            extra_cols
        ].copy()

        # ----------------------------------------------------
        # GÜVENLİ MERGE
        # ----------------------------------------------------

        result = result.merge(
            extra,
            on="symbol",
            how="left",
        )

        # ----------------------------------------------------
        # MERGE SONRASI DUPLICATE KOLON KONTROLÜ
        # ----------------------------------------------------

        result = result.loc[
            :,
            ~result.columns.duplicated()
        ].copy()

    # ========================================================
    # SON SYMBOL TEMİZLİĞİ
    # ========================================================

    if "symbol" in result.columns:

        result["symbol"] = (
            result["symbol"]
            .apply(clean_symbol)
        )

        result = result[
            result["symbol"] != ""
        ].copy()

    # ========================================================
    # TEKİL HİSSE
    # ========================================================

    if "symbol" in result.columns:

        result = (
            result
            .drop_duplicates(
                subset=["symbol"],
                keep="first",
            )
            .reset_index(drop=True)
        )

    # ========================================================
    # SONUÇ
    # ========================================================

    return result

# ============================================================
# TARİHİ FİYAT VERİSİ
# ============================================================

def load_price_history(
    symbol: str,
    period: str = "6mo",
) -> pd.DataFrame:

    try:

        import yfinance as yf

    except Exception:

        return pd.DataFrame()

    symbol = clean_symbol(symbol)

    if not symbol:
        return pd.DataFrame()

    try:

        df = yf.download(
            f"{symbol}.IS",
            period=period,
            interval="1d",
            auto_adjust=False,
            progress=False,
            threads=False,
        )

        if df is None or df.empty:
            return pd.DataFrame()

        if isinstance(
            df.columns,
            pd.MultiIndex,
        ):

            df.columns = [
                c[0]
                if isinstance(c, tuple)
                else c
                for c in df.columns
            ]

        return normalize_columns(df)

    except Exception:

        return pd.DataFrame()


# ============================================================
# TEKNİK GÖSTERGELER
# ============================================================

def calculate_rsi(
    close: pd.Series,
    period: int = 14,
) -> float:

    if close is None or len(close) < period + 2:
        return 50.0

    delta = close.diff()

    gain = delta.clip(
        lower=0
    )

    loss = -delta.clip(
        upper=0
    )

    avg_gain = (
        gain
        .rolling(period)
        .mean()
    )

    avg_loss = (
        loss
        .rolling(period)
        .mean()
    )

    last_gain = safe_float(
        avg_gain.iloc[-1],
        0,
    )

    last_loss = safe_float(
        avg_loss.iloc[-1],
        0,
    )

    if last_loss == 0:

        if last_gain > 0:
            return 100.0

        return 50.0

    rs = last_gain / last_loss

    return clamp(
        100 - (
            100 / (1 + rs)
        )
    )


def calculate_vwap(
    df: pd.DataFrame,
) -> float:

    if df is None or df.empty:
        return 0.0

    required = [
        "High",
        "Low",
        "Close",
        "Volume",
    ]

    if not all(
        c in df.columns
        for c in required
    ):
        return 0.0

    data = df.copy()

    typical = (
        data["High"]
        + data["Low"]
        + data["Close"]
    ) / 3

    volume = pd.to_numeric(
        data["Volume"],
        errors="coerce",
    ).fillna(0)

    cumulative_volume = (
        volume.cumsum()
    )

    if (
        cumulative_volume.iloc[-1]
        <= 0
    ):
        return 0.0

    vwap = (
        (
            typical * volume
        ).cumsum()
        / cumulative_volume
    )

    return safe_float(
        vwap.iloc[-1],
        0,
    )


def technical_analysis(
    df: pd.DataFrame,
) -> Dict[str, Any]:

    if (
        df is None
        or df.empty
        or "Close" not in df.columns
    ):

        return {
            "price": 0,
            "ema9": 0,
            "ema20": 0,
            "ema50": 0,
            "ema200": 0,
            "rsi": 50,
            "volume_ratio": 0,
            "vwap": 0,
            "technical_score": 0,
            "momentum_score": 0,
            "support": 0,
            "resistance": 0,
        }

    data = df.copy()

    close = pd.to_numeric(
        data["Close"],
        errors="coerce",
    )

    close = close.dropna()

    if len(close) < 20:

        return {
            "price": safe_float(
                close.iloc[-1]
                if len(close)
                else 0
            ),
            "ema9": 0,
            "ema20": 0,
            "ema50": 0,
            "ema200": 0,
            "rsi": 50,
            "volume_ratio": 0,
            "vwap": 0,
            "technical_score": 0,
            "momentum_score": 0,
            "support": 0,
            "resistance": 0,
        }

    price = safe_float(
        close.iloc[-1],
        0,
    )

    ema9 = safe_float(
        close.ewm(
            span=9,
            adjust=False,
        ).mean().iloc[-1],
        price,
    )

    ema20 = safe_float(
        close.ewm(
            span=20,
            adjust=False,
        ).mean().iloc[-1],
        price,
    )

    ema50 = safe_float(
        close.ewm(
            span=50,
            adjust=False,
        ).mean().iloc[-1],
        price,
    )

    ema200 = safe_float(
        close.ewm(
            span=200,
            adjust=False,
        ).mean().iloc[-1],
        price,
    )

    rsi = calculate_rsi(
        close
    )

    volume_ratio = 0.0

    if "Volume" in data.columns:

        volume = pd.to_numeric(
            data["Volume"],
            errors="coerce",
        ).fillna(0)

        if len(volume) >= 20:

            avg_volume = safe_float(
                volume.tail(20).mean(),
                0,
            )

            current_volume = safe_float(
                volume.iloc[-1],
                0,
            )

            if avg_volume > 0:

                volume_ratio = (
                    current_volume
                    / avg_volume
                )

    vwap = calculate_vwap(
        data
    )

    # --------------------------------------------------------
    # TEKNİK SKOR
    # --------------------------------------------------------

    score = 0.0

    if price > ema9:
        score += 20

    if ema9 > ema20:
        score += 20

    if price > ema20:
        score += 15

    if ema20 > ema50:
        score += 15

    if price > ema50:
        score += 10

    if ema50 > ema200:
        score += 10

    if 50 <= rsi <= 70:
        score += 10

    technical_score = clamp(
        score
    )

    # --------------------------------------------------------
    # MOMENTUM
    # --------------------------------------------------------

    momentum_score = 50.0

    if len(close) >= 5:

        mom5 = (
            price
            / safe_float(
                close.iloc[-5],
                price,
            )
            - 1
        ) * 100

    else:
        mom5 = 0

    if len(close) >= 20:

        mom20 = (
            price
            / safe_float(
                close.iloc[-20],
                price,
            )
            - 1
        ) * 100

    else:
        mom20 = 0

    if len(close) >= 60:

        mom60 = (
            price
            / safe_float(
                close.iloc[-60],
                price,
            )
            - 1
        ) * 100

    else:
        mom60 = 0

    momentum_score = 50

    if mom5 > 0:
        momentum_score += 15
    elif mom5 < -3:
        momentum_score -= 10

    if mom20 > 0:
        momentum_score += 20
    elif mom20 < -5:
        momentum_score -= 15

    if mom60 > 0:
        momentum_score += 15
    elif mom60 < -10:
        momentum_score -= 15

    momentum_score = clamp(
        momentum_score
    )

    # --------------------------------------------------------
    # DESTEK / DİRENÇ
    # --------------------------------------------------------

    if "Low" in data.columns:

        support = safe_float(
            pd.to_numeric(
                data["Low"],
                errors="coerce",
            )
            .tail(20)
            .min(),
            price * 0.97,
        )

    else:

        support = price * 0.97

    if "High" in data.columns:

        resistance = safe_float(
            pd.to_numeric(
                data["High"],
                errors="coerce",
            )
            .tail(20)
            .max(),
            price * 1.05,
        )

    else:

        resistance = price * 1.05

    return {

        "price": price,

        "ema9": ema9,

        "ema20": ema20,

        "ema50": ema50,

        "ema200": ema200,

        "rsi": rsi,

        "volume_ratio":
            volume_ratio,

        "vwap": vwap,

        "technical_score":
            technical_score,

        "momentum_score":
            momentum_score,

        "support":
            support,

        "resistance":
            resistance,

        "mom5":
            mom5,

        "mom20":
            mom20,

        "mom60":
            mom60,
    }


# ============================================================
# CACHE DEĞERİ BUL
# ============================================================

def get_value(
    row: Dict[str, Any],
    keys: List[str],
    default: float = 0,
) -> float:

    for key in keys:

        if key not in row:
            continue

        value = safe_float(
            row.get(key),
            np.nan,
        )

        if not np.isnan(value):
            return value

    return default


# ============================================================
# FİNANSAL SKOR
# ============================================================

def calculate_financial_score(
    row: Dict[str, Any],
) -> float:

    values = []

    for keys, weight in [

        (
            [
                "roe",
                "ROE",
                "return_on_equity",
            ],
            0.30,
        ),

        (
            [
                "net_margin",
                "net_profit_margin",
                "profit_margin",
            ],
            0.25,
        ),

        (
            [
                "revenue_growth",
                "revenue_growth_pct",
            ],
            0.20,
        ),

        (
            [
                "earnings_growth",
                "profit_growth",
            ],
            0.15,
        ),

        (
            [
                "debt_to_equity",
                "debt_equity",
            ],
            0.10,
        ),

    ]:

        value = get_value(
            row,
            keys,
            np.nan,
        )

        if np.isnan(value):
            continue

        values.append(
            value
        )

    if not values:
        return 50.0

    # Basit fakat dengeli finansal kalite
    score = 50.0

    roe = get_value(
        row,
        [
            "roe",
            "ROE",
            "return_on_equity",
        ],
        np.nan,
    )

    margin = get_value(
        row,
        [
            "net_margin",
            "net_profit_margin",
            "profit_margin",
        ],
        np.nan,
    )

    growth = get_value(
        row,
        [
            "revenue_growth",
            "revenue_growth_pct",
        ],
        np.nan,
    )

    debt = get_value(
        row,
        [
            "debt_to_equity",
            "debt_equity",
        ],
        np.nan,
    )

    if not np.isnan(roe):

        if roe >= 25:
            score += 20

        elif roe >= 15:
            score += 12

        elif roe >= 10:
            score += 5

        elif roe < 0:
            score -= 15

    if not np.isnan(margin):

        if margin >= 20:
            score += 15

        elif margin >= 10:
            score += 10

        elif margin >= 5:
            score += 5

        elif margin < 0:
            score -= 15

    if not np.isnan(growth):

        if growth >= 30:
            score += 15

        elif growth >= 15:
            score += 10

        elif growth > 0:
            score += 5

        elif growth < 0:
            score -= 10

    if not np.isnan(debt):

        if debt <= 0.5:
            score += 10

        elif debt <= 1:
            score += 5

        elif debt >= 2:
            score -= 10

    return clamp(
        score
    )


# ============================================================
# TEMEL SKOR
# ============================================================

def calculate_fundamental_score(
    row: Dict[str, Any],
) -> float:

    score = 50.0

    pe = get_value(
        row,
        [
            "pe",
            "trailing_pe",
            "P/E",
        ],
        np.nan,
    )

    pb = get_value(
        row,
        [
            "pb",
            "price_to_book",
            "P/B",
        ],
        np.nan,
    )

    dividend = get_value(
        row,
        [
            "dividend_yield",
            "temettü_verimi",
        ],
        np.nan,
    )

    if not np.isnan(pe):

        if 0 < pe <= 10:
            score += 15

        elif pe <= 15:
            score += 10

        elif pe <= 25:
            score += 3

        elif pe > 50:
            score -= 10

    if not np.isnan(pb):

        if 0 < pb <= 1.5:
            score += 10

        elif pb <= 3:
            score += 5

        elif pb > 8:
            score -= 10

    if not np.isnan(dividend):

        if dividend >= 5:
            score += 10

        elif dividend >= 3:
            score += 6

        elif dividend >= 1:
            score += 3

    return clamp(
        score
    )


# ============================================================
# SEKTÖR SKORU
# ============================================================

def calculate_sector_score(
    row: Dict[str, Any],
    universe: Optional[pd.DataFrame] = None,
) -> float:

    direct = get_value(
        row,
        [
            "sector_score",
            "Sektör Skoru",
            "sector_strength",
        ],
        np.nan,
    )

    if not np.isnan(direct):
        return clamp(direct)

    # --------------------------------------------------------
    # Eğer cache içinde yoksa sektör ortalamasından üret
    # --------------------------------------------------------

    if (
        universe is not None
        and not universe.empty
        and "sector" in universe.columns
    ):

        sector = row.get(
            "sector"
        )

        if sector:

            subset = universe[
                universe["sector"]
                .astype(str)
                .str.lower()
                ==
                str(sector)
                .lower()
            ]

            if not subset.empty:

                values = []

                for col in [
                    "dynamic_score",
                    "technical_score",
                ]:

                    if col in subset.columns:

                        values.extend(
                            pd.to_numeric(
                                subset[col],
                                errors="coerce",
                            )
                            .dropna()
                            .tolist()
                        )

                if values:

                    return clamp(
                        np.mean(values)
                    )

    return 50.0


# ============================================================
# LİKİDİTE
# ============================================================

def calculate_liquidity_score(
    avg_volume_tl: float,
) -> float:

    value = safe_float(
        avg_volume_tl,
        0,
    )

    if value <= 0:
        return 25.0

    if value >= 100_000_000:
        return 100.0

    if value >= 50_000_000:
        return 90.0

    if value >= 25_000_000:
        return 80.0

    if value >= 10_000_000:
        return 70.0

    if value >= 5_000_000:
        return 55.0

    if value >= 2_000_000:
        return 40.0

    return 25.0


# ============================================================
# TRADE SKORU
# ============================================================

def calculate_trade_score(
    technical: Dict[str, Any],
) -> float:

    technical_score = safe_float(
        technical.get(
            "technical_score"
        ),
        0,
    )

    rsi = safe_float(
        technical.get(
            "rsi"
        ),
        50,
    )

    volume_ratio = safe_float(
        technical.get(
            "volume_ratio"
        ),
        0,
    )

    vwap = safe_float(
        technical.get(
            "vwap"
        ),
        0,
    )

    price = safe_float(
        technical.get(
            "price"
        ),
        0,
    )

    score = (
        technical_score * 0.45
    )

    if 50 <= rsi <= 65:
        score += 20

    elif 45 <= rsi < 50:
        score += 12

    elif 65 < rsi <= 70:
        score += 10

    elif rsi > 75:
        score -= 10

    if volume_ratio >= 1.5:
        score += 15

    elif volume_ratio >= 1.2:
        score += 10

    elif volume_ratio >= 1:
        score += 5

    if (
        vwap > 0
        and price > vwap
    ):
        score += 20

    return clamp(
        score
    )


# ============================================================
# R/R
# ============================================================

def calculate_rr(
    price: float,
    support: float,
    resistance: float,
) -> Tuple[float, float, float, float]:

    price = safe_float(
        price,
        0,
    )

    support = safe_float(
        support,
        0,
    )

    resistance = safe_float(
        resistance,
        0,
    )

    if price <= 0:
        return (
            0,
            0,
            0,
            0,
        )

    stop = support

    if (
        stop <= 0
        or stop >= price
    ):

        stop = price * 0.97

    risk = price - stop

    reward = (
        resistance - price
    )

    if risk <= 0:
        rr = 0
    else:
        rr = reward / risk

    return (
        rr,
        price,
        stop,
        resistance,
    )


# ============================================================
# FIRSAT SKORU
# ============================================================

def calculate_opportunity_score(
    dynamic_score: float,
    technical_score: float,
    momentum_score: float,
    financial_score: float,
    fundamental_score: float,
    sector_score: float,
    market_score: float,
    liquidity_score: float,
    trade_score: float,
    rr: float,
) -> float:

    score = (

        dynamic_score
        * OPPORTUNITY_WEIGHTS[
            "dynamic"
        ]

        +

        technical_score
        * OPPORTUNITY_WEIGHTS[
            "technical"
        ]

        +

        momentum_score
        * OPPORTUNITY_WEIGHTS[
            "momentum"
        ]

        +

        financial_score
        * OPPORTUNITY_WEIGHTS[
            "financial"
        ]

        +

        fundamental_score
        * OPPORTUNITY_WEIGHTS[
            "fundamental"
        ]

        +

        sector_score
        * OPPORTUNITY_WEIGHTS[
            "sector"
        ]

        +

        market_score
        * OPPORTUNITY_WEIGHTS[
            "market"
        ]

        +

        liquidity_score
        * OPPORTUNITY_WEIGHTS[
            "liquidity"
        ]

        +

        trade_score
        * OPPORTUNITY_WEIGHTS[
            "trade"
        ]
    )

    # --------------------------------------------------------
    # R/R BONUS
    # --------------------------------------------------------

    if rr >= 2.5:
        score += 5

    elif rr >= 2:
        score += 3

    elif rr >= 1.5:
        score += 1

    elif rr < 0.8:
        score -= 5

    return round(
        clamp(score),
        1,
    )


# ============================================================
# A / B / C SINIFI
# ============================================================

def opportunity_class(
    opportunity_score: float,
    dynamic_score: float,
    technical_score: float,
    sector_score: float,
    rr: float,
) -> Tuple[str, str]:

    score = safe_float(
        opportunity_score,
        0,
    )

    # --------------------------------------------------------
    # A SINIFI
    # --------------------------------------------------------

    if (
        score >= 80
        and dynamic_score >= 70
        and technical_score >= 60
        and sector_score >= 50
        and rr >= 1
    ):

        return (
            "A",
            "🟢 A SINIFI FIRSAT",
        )

    # --------------------------------------------------------
    # B SINIFI
    # --------------------------------------------------------

    if (
        score >= 65
        and dynamic_score >= 55
        and technical_score >= 50
        and rr >= 0.8
    ):

        return (
            "B",
            "🟡 B SINIFI ADAY",
        )

    # --------------------------------------------------------
    # C SINIFI
    # --------------------------------------------------------

    if score >= 50:

        return (
            "C",
            "🟠 C SINIFI İZLE",
        )

    return (
        "D",
        "🔴 ZAYIF",
    )


# ============================================================
# FIRSAT NEDENLERİ
# ============================================================

def build_reasons(
    technical: Dict[str, Any],
    dynamic_score: float,
    momentum_score: float,
    financial_score: float,
    fundamental_score: float,
    sector_score: float,
    trade_score: float,
    rr: float,
) -> List[str]:

    reasons = []

    price = technical.get(
        "price",
        0,
    )

    ema9 = technical.get(
        "ema9",
        0,
    )

    ema20 = technical.get(
        "ema20",
        0,
    )

    rsi = technical.get(
        "rsi",
        50,
    )

    volume_ratio = technical.get(
        "volume_ratio",
        0,
    )

    vwap = technical.get(
        "vwap",
        0,
    )

    if (
        dynamic_score >= 70
    ):
        reasons.append(
            "Dinamik skor güçlü"
        )

    elif dynamic_score >= 55:
        reasons.append(
            "Dinamik yapı olumlu"
        )

    if (
        price > ema9
        and ema9 > ema20
    ):
        reasons.append(
            "EMA9 > EMA20 trend yapısı"
        )

    if (
        50 <= rsi <= 65
    ):
        reasons.append(
            "RSI sağlıklı bölgede"
        )

    if volume_ratio >= 1.2:
        reasons.append(
            "Hacim destekli hareket"
        )

    if (
        vwap > 0
        and price > vwap
    ):
        reasons.append(
            "VWAP üzerinde"
        )

    if momentum_score >= 70:
        reasons.append(
            "Momentum güçlü"
        )

    if financial_score >= 70:
        reasons.append(
            "Finansal yapı güçlü"
        )

    if fundamental_score >= 70:
        reasons.append(
            "Temel görünüm güçlü"
        )

    if sector_score >= 70:
        reasons.append(
            "Sektör desteği güçlü"
        )

    if trade_score >= 70:
        reasons.append(
            "Günlük trade yapısı olumlu"
        )

    if rr >= 2:
        reasons.append(
            "Risk/ödül oranı güçlü"
        )

    return reasons[:6]


# ============================================================
# TEK HİSSE ANALİZİ
# ============================================================

def analyze_opportunity(
    row: Dict[str, Any],
    price_df: Optional[pd.DataFrame] = None,
    universe: Optional[pd.DataFrame] = None,
    market_score: float = 50,
) -> Dict[str, Any]:

    symbol = clean_symbol(
        row.get("symbol")
        or row.get("ticker")
        or row.get("hisse")
        or row.get("Hisse")
    )

    if not symbol:
        return {}

    # --------------------------------------------------------
    # TEKNİK
    # --------------------------------------------------------

    technical = technical_analysis(
        price_df
    )

    # --------------------------------------------------------
    # CACHE'DEN TEKNİK VERİ TAMAMLA
    # --------------------------------------------------------

    if (
        technical["technical_score"]
        == 0
    ):

        technical["price"] = get_value(
            row,
            [
                "price",
                "fiyat",
                "last_price",
            ],
            0,
        )

        technical["ema9"] = get_value(
            row,
            ["ema9"],
            technical["price"],
        )

        technical["ema20"] = get_value(
            row,
            ["ema20"],
            technical["price"],
        )

        technical["ema50"] = get_value(
            row,
            ["ema50"],
            technical["price"],
        )

        technical["ema200"] = get_value(
            row,
            ["ema200"],
            technical["price"],
        )

        technical["rsi"] = get_value(
            row,
            ["rsi"],
            50,
        )

        technical["volume_ratio"] = (
            get_value(
                row,
                [
                    "volume_ratio",
                    "volume_ratio_20",
                ],
                0,
            )
        )

        technical["vwap"] = get_value(
            row,
            ["vwap"],
            0,
        )

        technical["technical_score"] = (
            get_value(
                row,
                [
                    "technical_score",
                    "technical",
                ],
                0,
            )
        )

        technical["momentum_score"] = (
            get_value(
                row,
                [
                    "momentum_score",
                    "momentum",
                ],
                50,
            )
        )

        technical["support"] = (
            get_value(
                row,
                [
                    "support",
                    "destek",
                ],
                technical["price"] * 0.97,
            )
        )

        technical["resistance"] = (
            get_value(
                row,
                [
                    "resistance",
                    "direnc",
                ],
                technical["price"] * 1.05,
            )
        )

    # --------------------------------------------------------
    # SKORLAR
    # --------------------------------------------------------

    technical_score = clamp(
        get_value(
            row,
            [
                "technical_score"
            ],
            technical.get(
                "technical_score",
                0,
            ),
        )
    )

    momentum_score = clamp(
        get_value(
            row,
            [
                "momentum_score"
            ],
            technical.get(
                "momentum_score",
                50,
            ),
        )
    )

    financial_score = (
        get_value(
            row,
            [
                "financial_score",
                "finansal_score",
            ],
            np.nan,
        )
    )

    if np.isnan(financial_score):

        financial_score = (
            calculate_financial_score(
                row
            )
        )

    fundamental_score = (
        get_value(
            row,
            [
                "fundamental_score",
                "temel_score",
                "kap_score",
            ],
            np.nan,
        )
    )

    if np.isnan(fundamental_score):

        fundamental_score = (
            calculate_fundamental_score(
                row
            )
        )

    sector_score = (
        calculate_sector_score(
            row,
            universe,
        )
    )

    market_score = clamp(
        market_score
    )

    avg_volume_tl = get_value(
        row,
        [
            "avg_volume_tl",
            "average_volume_tl",
            "20g_avg_volume_tl",
            "avg_volume",
        ],
        0,
    )

    liquidity_score = (
        calculate_liquidity_score(
            avg_volume_tl
        )
    )

    # --------------------------------------------------------
    # DİNAMİK SKOR
    # --------------------------------------------------------

    dynamic_score = (
        get_value(
            row,
            [
                "dynamic_score",
                "genel_skor",
                "dynamic",
            ],
            np.nan,
        )
    )

    if np.isnan(dynamic_score):

        dynamic_score = (

            technical_score * 0.30

            + momentum_score * 0.15

            + financial_score * 0.15

            + fundamental_score * 0.10

            + sector_score * 0.15

            + market_score * 0.10

            + liquidity_score * 0.05
        )

    dynamic_score = clamp(
        dynamic_score
    )

    # --------------------------------------------------------
    # TRADE
    # --------------------------------------------------------

    trade_score = (
        get_value(
            row,
            [
                "trade_score",
            ],
            np.nan,
        )
    )

    if np.isnan(trade_score):

        trade_score = (
            calculate_trade_score(
                technical
            )
        )

    trade_score = clamp(
        trade_score
    )

    # --------------------------------------------------------
    # R/R
    # --------------------------------------------------------

    rr, entry, stop, target = (
        calculate_rr(

            technical.get(
                "price",
                0,
            ),

            technical.get(
                "support",
                0,
            ),

            technical.get(
                "resistance",
                0,
            ),
        )
    )

    # --------------------------------------------------------
    # FIRSAT SKORU
    # --------------------------------------------------------

    opportunity_score = (
        calculate_opportunity_score(

            dynamic_score,

            technical_score,

            momentum_score,

            financial_score,

            fundamental_score,

            sector_score,

            market_score,

            liquidity_score,

            trade_score,

            rr,
        )
    )

    # --------------------------------------------------------
    # SINIF
    # --------------------------------------------------------

    opportunity_class_code, (
        opportunity_label
    ) = opportunity_class(

        opportunity_score,

        dynamic_score,

        technical_score,

        sector_score,

        rr,
    )

    # --------------------------------------------------------
    # NEDENLER
    # --------------------------------------------------------

    reasons = build_reasons(

        technical,

        dynamic_score,

        momentum_score,

        financial_score,

        fundamental_score,

        sector_score,

        trade_score,

        rr,
    )

    # --------------------------------------------------------
    # VERİ KALİTESİ
    # --------------------------------------------------------

    data_points = 0
    available_points = 0

    check_values = [
        technical_score,
        momentum_score,
        financial_score,
        fundamental_score,
        sector_score,
        market_score,
        liquidity_score,
    ]

    for value in check_values:

        available_points += 1

        if value > 0:
            data_points += 1

    data_quality = (
        data_points
        / max(
            available_points,
            1,
        )
    ) * 100

    # --------------------------------------------------------
    # GÜVEN
    # --------------------------------------------------------

    confidence = (
        opportunity_score * 0.70
        + data_quality * 0.30
    )

    # Skorlar arasındaki aşırı fark güveni düşürür.

    score_values = [
        dynamic_score,
        technical_score,
        momentum_score,
        financial_score,
        fundamental_score,
        sector_score,
    ]

    spread = (
        max(score_values)
        - min(score_values)
    )

    confidence -= min(
        spread * 0.08,
        12,
    )

    confidence = clamp(
        confidence
    )

    # --------------------------------------------------------
    # SONUÇ
    # --------------------------------------------------------

    return {

        "symbol":
            symbol,

        "sector":
            row.get(
                "sector",
                row.get(
                    "sektor",
                    "Bilinmiyor",
                ),
            ),

        "price":
            round(
                technical.get(
                    "price",
                    0,
                ),
                4,
            ),

        "opportunity_score":
            opportunity_score,

        "opportunity_class":
            opportunity_class_code,

        "opportunity_label":
            opportunity_label,

        "dynamic_score":
            round(
                dynamic_score,
                1,
            ),

        "technical_score":
            round(
                technical_score,
                1,
            ),

        "momentum_score":
            round(
                momentum_score,
                1,
            ),

        "financial_score":
            round(
                financial_score,
                1,
            ),

        "fundamental_score":
            round(
                fundamental_score,
                1,
            ),

        "sector_score":
            round(
                sector_score,
                1,
            ),

        "market_score":
            round(
                market_score,
                1,
            ),

        "liquidity_score":
            round(
                liquidity_score,
                1,
            ),

        "trade_score":
            round(
                trade_score,
                1,
            ),

        "rsi":
            round(
                safe_float(
                    technical.get(
                        "rsi",
                        50,
                    ),
                    50,
                ),
                1,
            ),

        "volume_ratio":
            round(
                safe_float(
                    technical.get(
                        "volume_ratio",
                        0,
                    ),
                    0,
                ),
                2,
            ),

        "ema9":
            technical.get(
                "ema9",
                0,
            ),

        "ema20":
            technical.get(
                "ema20",
                0,
            ),

        "ema50":
            technical.get(
                "ema50",
                0,
            ),

        "ema200":
            technical.get(
                "ema200",
                0,
            ),

        "vwap":
            technical.get(
                "vwap",
                0,
            ),

        "support":
            round(
                safe_float(
                    technical.get(
                        "support",
                        0,
                    ),
                    0,
                ),
                4,
            ),

        "resistance":
            round(
                safe_float(
                    technical.get(
                        "resistance",
                        0,
                    ),
                    0,
                ),
                4,
            ),

        "entry":
            round(
                entry,
                4,
            ),

        "stop":
            round(
                stop,
                4,
            ),

        "target":
            round(
                target,
                4,
            ),

        "rr":
            round(
                rr,
                2,
            ),

        "avg_volume_tl":
            round(
                avg_volume_tl,
                0,
            ),

        "confidence":
            round(
                confidence,
                1,
            ),

        "data_quality":
            round(
                data_quality,
                1,
            ),

        "reasons":
            reasons,

        "daily_change":
            get_value(
                row,
                [
                    "daily_change",
                    "change",
                    "daily_pct",
                ],
                0,
            ),
    }


# ============================================================
# TOPLU ANALİZ
# ============================================================

def analyze_opportunity_universe(
    universe: pd.DataFrame,
    price_data: Optional[
        Dict[str, pd.DataFrame]
    ] = None,
    market_score: float = 50,
) -> pd.DataFrame:

    if (
        universe is None
        or universe.empty
    ):
        return pd.DataFrame()

    results = []

    universe = normalize_columns(
        universe
    )

    if "symbol" not in universe.columns:

        symbol_col = (
            find_symbol_column(
                universe
            )
        )

        if symbol_col is None:
            return pd.DataFrame()

        universe["symbol"] = (
            universe[symbol_col]
            .apply(clean_symbol)
        )

    for _, row in universe.iterrows():

        row_dict = row.to_dict()

        symbol = clean_symbol(
            row_dict.get(
                "symbol"
            )
        )

        if not symbol:
            continue

        hist = None

        if price_data:

            hist = (
                price_data.get(
                    symbol
                )
                or price_data.get(
                    f"{symbol}.IS"
                )
            )

        # ----------------------------------------------------
        # Eğer fiyat datası verilmediyse mevcut cache ile
        # çalış.
        # ----------------------------------------------------

        if (
            hist is None
            and (
                get_value(
                    row_dict,
                    [
                        "price",
                        "fiyat",
                    ],
                    0,
                )
                <= 0
            )
        ):
            continue

        result = analyze_opportunity(

            row_dict,

            price_df=hist,

            universe=universe,

            market_score=market_score,
        )

        if result:
            results.append(
                result
            )

    if not results:
        return pd.DataFrame()

    result_df = pd.DataFrame(
        results
    )

    # --------------------------------------------------------
    # SIRALAMA
    # --------------------------------------------------------

    sort_columns = [
        "opportunity_score",
        "dynamic_score",
        "technical_score",
        "momentum_score",
        "sector_score",
    ]

    sort_columns = [
        c
        for c in sort_columns
        if c in result_df.columns
    ]

    result_df = result_df.sort_values(
        sort_columns,
        ascending=False,
    )

    return (
        result_df
        .reset_index(
            drop=True
        )
    )


# ============================================================
# FIRSAT HAVUZU
# ============================================================

def build_opportunity_pool(
    df: pd.DataFrame,
    min_score: float = DEFAULT_MIN_OPPORTUNITY,
    min_dynamic: float = DEFAULT_MIN_DYNAMIC,
    min_sector: float = DEFAULT_MIN_SECTOR,
    min_technical: float = DEFAULT_MIN_TECHNICAL,
    min_liquidity: float = DEFAULT_MIN_LIQUIDITY,
    include_c: bool = True,
) -> pd.DataFrame:

    if (
        df is None
        or df.empty
    ):
        return pd.DataFrame()

    result = df.copy()

    numeric = [
        "opportunity_score",
        "dynamic_score",
        "technical_score",
        "momentum_score",
        "financial_score",
        "fundamental_score",
        "sector_score",
        "market_score",
        "liquidity_score",
        "trade_score",
        "rr",
        "avg_volume_tl",
        "confidence",
    ]

    for col in numeric:

        if col in result.columns:

            result[col] = pd.to_numeric(
                result[col],
                errors="coerce",
            ).fillna(0)

    # --------------------------------------------------------
    # ANA FİLTRE
    # --------------------------------------------------------

    result = result[
        result[
            "opportunity_score"
        ] >= min_score
    ].copy()

    # --------------------------------------------------------
    # DİNAMİK
    # --------------------------------------------------------

    result = result[
        result[
            "dynamic_score"
        ] >= min_dynamic
    ].copy()

    # --------------------------------------------------------
    # SEKTÖR
    # --------------------------------------------------------

    result = result[
        result[
            "sector_score"
        ] >= min_sector
    ].copy()

    # --------------------------------------------------------
    # TEKNİK
    # --------------------------------------------------------

    result = result[
        result[
            "technical_score"
        ] >= min_technical
    ].copy()

    # --------------------------------------------------------
    # LİKİDİTE
    # --------------------------------------------------------

    if (
        min_liquidity > 0
        and "avg_volume_tl"
        in result.columns
    ):

        # Likidite verisi 0 olanları otomatik silme.
        # Çünkü bazı cache kayıtlarında bu veri yok.
        known_liquidity = (
            result[
                "avg_volume_tl"
            ] > 0
        )

        result = result[
            (
                ~known_liquidity
            )
            |
            (
                result[
                    "avg_volume_tl"
                ] >= min_liquidity
            )
        ].copy()

    # --------------------------------------------------------
    # C SINIFI
    # --------------------------------------------------------

    if (
        not include_c
        and "opportunity_class"
        in result.columns
    ):

        result = result[
            result[
                "opportunity_class"
            ].isin(
                [
                    "A",
                    "B",
                ]
            )
        ]

    # --------------------------------------------------------
    # SIRALAMA
    # --------------------------------------------------------

    result = result.sort_values(
        [
            "opportunity_score",
            "dynamic_score",
            "technical_score",
            "momentum_score",
        ],
        ascending=False,
    )

    return (
        result
        .reset_index(
            drop=True
        )
    )


# ============================================================
# SINIF ÖZETİ
# ============================================================

def opportunity_summary(
    df: pd.DataFrame,
) -> Dict[str, Any]:

    if (
        df is None
        or df.empty
    ):

        return {
            "total": 0,
            "a": 0,
            "b": 0,
            "c": 0,
            "d": 0,
            "average": 0,
        }

    classes = (
        df[
            "opportunity_class"
        ]
        if "opportunity_class"
        in df.columns
        else pd.Series(
            dtype=str
        )
    )

    return {

        "total":
            len(df),

        "a":
            int(
                (
                    classes
                    == "A"
                ).sum()
            ),

        "b":
            int(
                (
                    classes
                    == "B"
                ).sum()
            ),

        "c":
            int(
                (
                    classes
                    == "C"
                ).sum()
            ),

        "d":
            int(
                (
                    classes
                    == "D"
                ).sum()
            ),

        "average":
            round(
                safe_float(
                    df[
                        "opportunity_score"
                    ].mean()
                    if
                    "opportunity_score"
                    in df.columns
                    else 0,
                    0,
                ),
                1,
            ),
    }


# ============================================================
# SEKTÖR FIRSAT ANALİZİ
# ============================================================

def sector_opportunity_analysis(
    df: pd.DataFrame,
) -> pd.DataFrame:

    if (
        df is None
        or df.empty
        or "sector"
        not in df.columns
    ):
        return pd.DataFrame()

    grouped = (
        df.groupby(
            "sector",
            dropna=False,
        )
        .agg(
            Hisse_Sayisi=(
                "symbol",
                "count",
            ),
            Ortalama_Firsat=(
                "opportunity_score",
                "mean",
            ),
            Ortalama_Dinamik=(
                "dynamic_score",
                "mean",
            ),
            Ortalama_Teknik=(
                "technical_score",
                "mean",
            ),
            Ortalama_Momentum=(
                "momentum_score",
                "mean",
            ),
            Ortalama_Trade=(
                "trade_score",
                "mean",
            ),
        )
        .reset_index()
    )

    grouped[
        "A_Sinifi"
    ] = (
        df[
            df[
                "opportunity_class"
            ]
            == "A"
        ]
        .groupby(
            "sector"
        )[
            "symbol"
        ]
        .count()
    )

    grouped[
        "A_Sinifi"
    ] = (
        grouped[
            "A_Sinifi"
        ]
        .fillna(0)
        .astype(int)
    )

    return grouped.sort_values(
        "Ortalama_Firsat",
        ascending=False,
    ).reset_index(
        drop=True
    )


# ============================================================
# EN İYİ FIRSATLAR
# ============================================================

def get_top_opportunities(
    df: pd.DataFrame,
    n: int = 20,
) -> pd.DataFrame:

    if (
        df is None
        or df.empty
    ):
        return pd.DataFrame()

    return (
        df.sort_values(
            "opportunity_score",
            ascending=False,
        )
        .head(n)
        .reset_index(
            drop=True
        )
    )


# ============================================================
# FIRSAT MERKEZİ İÇİN HAZIR TABLO
# ============================================================
# ============================================================
# FIRSAT TABLOSU HAZIRLA
# ============================================================

def prepare_opportunity_table(
    df: pd.DataFrame,
) -> pd.DataFrame:

    if (
        df is None
        or df.empty
    ):
        return pd.DataFrame()

    # ========================================================
    # KOLON EŞLEŞTİRME
    # ========================================================

    columns = {

        "symbol":
            "Hisse",

        "sector":
            "Sektör",

        "price":
            "Fiyat",

        "opportunity_score":
            "Fırsat Skoru",

        "opportunity_label":
            "Sınıf",

        "dynamic_score":
            "Dinamik",

        "technical_score":
            "Teknik",

        "momentum_score":
            "Momentum",

        "financial_score":
            "Finansal",

        "fundamental_score":
            "Temel",

        # ÖNEMLİ:
        # sector ile aynı isim olmayacak
        "sector_score":
            "Sektör Skoru",

        "market_score":
            "Piyasa",

        "liquidity_score":
            "Likidite",

        "trade_score":
            "Trade",

        "rsi":
            "RSI",

        "volume_ratio":
            "Hacim Oranı",

        "rr":
            "R/R",

        "entry":
            "Giriş",

        "stop":
            "Stop",

        "target":
            "Hedef",

        "confidence":
            "Güven",
    }

    # ========================================================
    # SADECE MEVCUT KOLONLARI AL
    # ========================================================

    available = {
        source: display
        for source, display in columns.items()
        if source in df.columns
    }

    if not available:
        return pd.DataFrame()

    # ========================================================
    # TABLOYU OLUŞTUR
    # ========================================================

    result = df[
        list(
            available.keys()
        )
    ].copy()

    # ========================================================
    # KOLON İSİMLERİNİ TÜRKÇELEŞTİR
    # ========================================================

    result = result.rename(
        columns=available
    )

    # ========================================================
    # OLASI DUPLICATE KOLONLARI TEMİZLE
    # ========================================================

    result = result.loc[
        :,
        ~result.columns.duplicated()
    ].copy()

    return result

# ============================================================
# STREAMLIT FIRSAT MERKEZİ
# ============================================================

def run_opportunity_center(
    db_path: Optional[str] = None,
):

    try:
        import streamlit as st
    except Exception:
        raise RuntimeError(
            "Streamlit kurulu değil."
        )

    st.set_page_config(
        page_title="BIST AI PRO - Hisse Fırsat Merkezi",
        page_icon="🎯",
        layout="wide",
    )

    st.title(
        "🎯 Hisse Fırsat Merkezi"
    )

    st.caption(
        "BIST hisselerini çok faktörlü fırsat skoru ile sıralayan analiz merkezi"
    )

    # ========================================================
    # VERİ
    # ========================================================

    with st.spinner(
        "Fırsat evreni hazırlanıyor..."
    ):

        universe = (
            build_analysis_universe(
                db_path
            )
        )

    if (
        universe is None
        or universe.empty
    ):

        st.error(
            "Analiz edilecek hisse evreni bulunamadı."
        )

        st.info(
            "Önce veri güncelleme motorunu çalıştır."
        )

        return

    st.success(
        f"{len(universe):,} hisse analiz evreninde."
    )

    # ========================================================
    # AYARLAR
    # ========================================================

    st.sidebar.header(
        "🎛️ Fırsat Filtreleri"
    )

    min_score = st.sidebar.slider(
        "Minimum Fırsat Skoru",
        0,
        90,
        50,
        1,
    )

    min_dynamic = st.sidebar.slider(
        "Minimum Dinamik Skor",
        0,
        90,
        45,
        1,
    )

    min_sector = st.sidebar.slider(
        "Minimum Sektör Skoru",
        0,
        90,
        35,
        1,
    )

    min_technical = st.sidebar.slider(
        "Minimum Teknik Skor",
        0,
        90,
        35,
        1,
    )

    min_liquidity_m = st.sidebar.number_input(
        "Minimum Likidite (M TL)",
        min_value=0.0,
        value=5.0,
        step=1.0,
    )

    include_c = st.sidebar.checkbox(
        "C sınıfı fırsatları göster",
        value=True,
    )

    top_n = st.sidebar.slider(
        "Gösterilecek Hisse",
        10,
        100,
        30,
        5,
    )

    # ========================================================
    # FİYAT VERİLERİ
    # ========================================================

    price_data = {}

    # Cache içinde yeterli teknik veri varsa
    # bütün evrene tek tek Yahoo sorgusu yapma.
    #
    # Yalnızca fiyat geçmişine ihtiyaç duyan kayıtlar
    # gerektiğinde çekilir.

    cache = load_dynamic_cache(
        db_path
    )

    # ========================================================
    # ANALİZ
    # ========================================================

    results = []

    progress = st.progress(
        0
    )

    total = len(universe)

    for index, row in universe.iterrows():

        symbol = clean_symbol(
            row.get(
                "symbol"
            )
        )

        if not symbol:
            continue

        row_dict = row.to_dict()

        hist = None

        # ----------------------------------------------------
        # Eğer mevcut cache yeterli ise doğrudan kullan.
        # ----------------------------------------------------

        cache_score = get_value(
            row_dict,
            [
                "dynamic_score",
                "genel_skor",
            ],
            np.nan,
        )

        technical_score = get_value(
            row_dict,
            [
                "technical_score",
            ],
            np.nan,
        )

        # ----------------------------------------------------
        # Eksik teknik veri varsa Yahoo'dan çek.
        # ----------------------------------------------------

        if (
            np.isnan(
                technical_score
            )
            or
            get_value(
                row_dict,
                [
                    "price",
                    "fiyat",
                ],
                0,
            )
            <= 0
        ):

            hist = load_price_history(
                symbol,
                period="6mo",
            )

            if not hist.empty:
                price_data[symbol] = hist

        result = analyze_opportunity(

            row_dict,

            price_df=hist,

            universe=universe,

            market_score=50,
        )

        if result:
            results.append(
                result
            )

        progress.progress(
            min(
                (index + 1)
                / max(total, 1),
                1.0,
            )
        )

    progress.empty()

    if not results:

        st.warning(
            "Analiz sonucunda hisse bulunamadı."
        )

        return

    result_df = pd.DataFrame(
        results
    )

    # ========================================================
    # HAVUZ
    # ========================================================

    pool = build_opportunity_pool(

        result_df,

        min_score=min_score,

        min_dynamic=min_dynamic,

        min_sector=min_sector,

        min_technical=min_technical,

        min_liquidity=(
            min_liquidity_m
            * 1_000_000
        ),

        include_c=include_c,
    )

    # ========================================================
    # ÖZET
    # ========================================================

    summary = opportunity_summary(
        pool
    )

    c1, c2, c3, c4, c5 = (
        st.columns(5)
    )

    c1.metric(
        "Toplam Aday",
        summary["total"],
    )

    c2.metric(
        "A Sınıfı",
        summary["a"],
    )

    c3.metric(
        "B Sınıfı",
        summary["b"],
    )

    c4.metric(
        "C Sınıfı",
        summary["c"],
    )

    c5.metric(
        "Ort. Fırsat",
        summary["average"],
    )

    # ========================================================
    # A SINIFI
    # ========================================================

    st.subheader(
        "🟢 A Sınıfı Fırsatlar"
    )

    a_df = pool[
        pool[
            "opportunity_class"
        ]
        == "A"
    ].copy()

    if a_df.empty:

        st.info(
            "Mevcut kriterlerde A sınıfı fırsat bulunamadı."
        )

    else:

        table = prepare_opportunity_table(
            a_df.head(top_n)
        )
        
        st.dataframe(
            table,
            use_container_width=True,
            hide_index=True,
        )

    # ========================================================
    # B SINIFI
    # ========================================================

    st.subheader(
        "🟡 B Sınıfı Adaylar"
    )

    b_df = pool[
        pool[
            "opportunity_class"
        ]
        == "B"
    ].copy()

    if b_df.empty:

        st.info(
            "B sınıfı aday bulunamadı."
        )

    else:

        table = prepare_opportunity_table(
            b_df.head(top_n)
        )

        st.dataframe(
            table,
            use_container_width=True,
            hide_index=True,
        )

    # ========================================================
    # C SINIFI
    # ========================================================

    if include_c:

        st.subheader(
            "🟠 C Sınıfı İzleme Havuzu"
        )

        c_df = pool[
            pool[
                "opportunity_class"
            ]
            == "C"
        ].copy()

        if not c_df.empty:

            table = prepare_opportunity_table(
                c_df.head(top_n)
            )

            st.dataframe(
                table,
                use_container_width=True,
                hide_index=True,
            )

    # ========================================================
    # SEKTÖRLER
    # ========================================================

    st.subheader(
        "🏭 Sektör Fırsat Gücü"
    )

    sector_df = (
        sector_opportunity_analysis(
            pool
        )
    )

    if not sector_df.empty:

        st.dataframe(
            sector_df,
            use_container_width=True,
            hide_index=True,
        )

    # ========================================================
    # EN İYİ FIRSATLAR
    # ========================================================

    st.subheader(
        "🏆 En Yüksek Skorlu Fırsatlar"
    )

    top_df = get_top_opportunities(
        pool,
        top_n,
    )

    if not top_df.empty:

        cols = [
            "symbol",
            "sector",
            "opportunity_score",
            "opportunity_label",
            "dynamic_score",
            "technical_score",
            "momentum_score",
            "sector_score",
            "trade_score",
            "rr",
            "confidence",
        ]

        cols = [
            c
            for c in cols
            if c in top_df.columns
        ]

        st.dataframe(
            top_df[cols],
            use_container_width=True,
            hide_index=True,
        )

    # ========================================================
    # HİSSE DETAYI
    # ========================================================

    st.subheader(
        "🔎 Hisse Detayı"
    )

    if not pool.empty:

        symbols = (
            pool["symbol"]
            .dropna()
            .astype(str)
            .tolist()
        )

        selected = st.selectbox(
            "Hisse seç",
            symbols,
        )

        selected_row = (
            pool[
                pool["symbol"]
                == selected
            ]
            .iloc[0]
        )

        d1, d2, d3, d4 = (
            st.columns(4)
        )

        d1.metric(
            "Fırsat Skoru",
            selected_row[
                "opportunity_score"
            ],
        )

        d2.metric(
            "Dinamik",
            selected_row[
                "dynamic_score"
            ],
        )

        d3.metric(
            "Teknik",
            selected_row[
                "technical_score"
            ],
        )

        d4.metric(
            "R/R",
            selected_row[
                "rr"
            ],
        )

        st.write(
            "### 📌 Analiz"
        )

        st.write(
            selected_row[
                "opportunity_label"
            ]
        )

        reasons = selected_row.get(
            "reasons",
            [],
        )

        if isinstance(
            reasons,
            list,
        ):

            for reason in reasons:

                st.write(
                    f"• {reason}"
                )

        st.write(
            "### 🎯 İşlem Seviyeleri"
        )

        levels = pd.DataFrame(
            [
                {
                    "Giriş":
                        selected_row[
                            "entry"
                        ],

                    "Stop":
                        selected_row[
                            "stop"
                        ],

                    "Hedef":
                        selected_row[
                            "target"
                        ],

                    "R/R":
                        selected_row[
                            "rr"
                        ],
                }
            ]
        )

        st.dataframe(
            levels,
            use_container_width=True,
            hide_index=True,
        )

    # ========================================================
    # CSV
    # ========================================================

    st.subheader(
        "📥 Sonuç"
    )

    export_df = (
        prepare_opportunity_table(
            pool
        )
    )

    if not export_df.empty:

        csv = export_df.to_csv(
            index=False
        ).encode(
            "utf-8-sig"
        )

        st.download_button(
            "📥 Fırsat Havuzunu CSV İndir",
            data=csv,
            file_name=(
                "bist_firsat_havuzu.csv"
            ),
            mime=(
                "text/csv"
            ),
        )


# ============================================================
# MODÜL TESTİ
# ============================================================

def main():

    run_opportunity_center()


if __name__ == "__main__":

    main()