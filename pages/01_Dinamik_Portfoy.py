
import json
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

try:
    from streamlit_autorefresh import st_autorefresh
except ImportError:
    st_autorefresh = None


# ============================================================
# BIST AI PRO — DİNAMİK PORTFÖY
#
# TASARIM PRENSİPLERİ
# ------------------------------------------------------------
# 1) Bu sayfa DIŞ KAYNAK TARAMAZ.
# 2) Ana veri kaynağı borsa.db / technical_analysis snapshot'tır.
# 3) Financial score varsa KAP tabanlı financial_scores kullanılır.
# 4) Veri eksikse uygulama çökmez; nötr değer + veri güveni gösterilir.
# 5) Hedef ağırlıklar tek hisse ve sektör tavanlarına gerçekten uyar.
# 6) Hedef ağırlıklar toplamı %100'e tamamlanır.
# 7) Mevcut portföyde hedef havuzunda olmayan hisseler ayrıca riskte gösterilir.
# 8) UI yenileme veri taraması değildir.
# ============================================================

st.set_page_config(
    page_title="BIST AI PRO - Dinamik Portföy",
    page_icon="🏆",
    layout="wide",
)

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "borsa.db"

# Tarama Merkezi ile uyumlu ana ağırlıklar
W_TECH = 0.50
W_FUND = 0.20
W_MOM = 0.15
W_MARKET = 0.15

DEFAULT_SECTOR_MIN = 60.0
DEFAULT_STOCK_MIN = 70.0
DEFAULT_MAX_POSITIONS = 6
DEFAULT_STOCK_CAP = 25.0
DEFAULT_SECTOR_CAP = 40.0


# ============================================================
# GÜVENLİ YARDIMCILAR
# ============================================================

def safe_float(value, default=0.0):
    try:
        if value is None or pd.isna(value):
            return float(default)
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def clamp(value, low=0.0, high=100.0, default=50.0):
    value = safe_float(value, default)
    return max(low, min(high, value))


def normalize_symbol(value):
    value = str(value or "").upper().strip()
    if value.endswith(".IS"):
        value = value[:-3]
    return value


def money(value):
    value = safe_float(value)
    return (
        f"{value:,.2f}"
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
        + " TL"
    )


def pct(value):
    return f"{safe_float(value):.1f}%"


def decision(score):
    score = clamp(score)
    if score >= 85:
        return "🟢 GÜÇLÜ AL"
    if score >= 70:
        return "🟢 AL"
    if score >= 55:
        return "🟡 TUT"
    if score >= 40:
        return "🟠 İZLE"
    return "🔴 SAT"


def sector_status(score):
    score = clamp(score)
    if score >= 80:
        return "🟢 Çok Güçlü"
    if score >= 70:
        return "🟢 Güçlü"
    if score >= 60:
        return "🟡 Olumlu"
    if score >= 50:
        return "🟠 Nötr"
    return "🔴 Zayıf"


def open_db():
    conn = sqlite3.connect(
        DB_PATH,
        timeout=30,
        check_same_thread=False,
    )
    conn.row_factory = sqlite3.Row
    return conn


def table_exists(conn, table):
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    ).fetchone()
    return row is not None


def table_columns(conn, table):
    if not table_exists(conn, table):
        return []
    return [
        row["name"]
        for row in conn.execute(f"PRAGMA table_info({table})").fetchall()
    ]


def first_existing(columns, candidates):
    return next((x for x in candidates if x in columns), None)


def to_datetime_series(series):
    return pd.to_datetime(series, errors="coerce")


# ============================================================
# SEKTÖR EŞLEŞTİRME
# ============================================================

SECTOR_MAP = {
    # Banka
    "AKBNK": "Banka", "GARAN": "Banka", "ISCTR": "Banka",
    "YKBNK": "Banka", "VAKBN": "Banka", "HALKB": "Banka",
    "TSKB": "Banka", "SKBNK": "Banka", "ALBRK": "Banka",
    "KLNMA": "Banka", "ICBCT": "Banka",

    # Enerji
    "AKFYE": "Enerji", "AKSEN": "Enerji", "ENJSA": "Enerji",
    "GWIND": "Enerji", "GESAN": "Enerji", "EUPWR": "Enerji",
    "ODAS": "Enerji", "ZOREN": "Enerji", "AYDEM": "Enerji",
    "ALFAS": "Enerji", "ASTOR": "Enerji", "SMRTG": "Enerji",
    "YEOTK": "Enerji", "CWENE": "Enerji", "KONTR": "Enerji",
    "BIOEN": "Enerji", "MAGEN": "Enerji", "NATEN": "Enerji",
    "ESEN": "Enerji", "ENERY": "Enerji", "MOGAN": "Enerji",

    # Savunma
    "ASELS": "Savunma", "SDTTR": "Savunma", "ALTNY": "Savunma",
    "ONRYT": "Savunma",

    # Havacılık / Ulaştırma
    "THYAO": "Havacılık", "PGSUS": "Havacılık", "TAVHL": "Havacılık",
    "CLEBI": "Havacılık", "RYSAS": "Ulaştırma",

    # Perakende
    "BIMAS": "Perakende", "MGROS": "Perakende", "SOKM": "Perakende",

    # Gıda / İçecek
    "CCOLA": "Gıda/İçecek", "ULKER": "Gıda/İçecek",
    "TATGD": "Gıda/İçecek", "TUKAS": "Gıda/İçecek",
    "PETUN": "Gıda/İçecek", "PNSUT": "Gıda/İçecek",

    # Holding
    "KCHOL": "Holding", "SAHOL": "Holding", "DOHOL": "Holding",
    "AGHOL": "Holding",

    # Otomotiv
    "FROTO": "Otomotiv", "TOASO": "Otomotiv",
    "TTRAK": "Otomotiv", "OTKAR": "Otomotiv", "KARSN": "Otomotiv",

    # Metal
    "EREGL": "Metal", "KRDMD": "Metal", "BRSAN": "Metal",
    "ISDMR": "Metal",

    # Madencilik
    "KOZAL": "Madencilik", "KOZAA": "Madencilik",

    # Petrokimya
    "TUPRS": "Petrokimya", "PETKM": "Petrokimya",

    # Kimya
    "AKSA": "Kimya", "SASA": "Kimya", "HEKTS": "Kimya",

    # Çimento
    "OYAKC": "Çimento", "CIMSA": "Çimento", "BUCIM": "Çimento",
    "AKCNS": "Çimento", "KONYA": "Çimento", "NUHCM": "Çimento",
    "BSOKE": "Çimento", "GOLTS": "Çimento",

    # İnşaat
    "ENKAI": "İnşaat", "TKFEN": "İnşaat",

    # Teknoloji
    "LOGO": "Teknoloji", "MIATK": "Teknoloji", "MOBTL": "Teknoloji",
    "ARDYZ": "Teknoloji", "ALCTL": "Teknoloji",

    # GYO
    "EKGYO": "GYO", "TRGYO": "GYO", "ISGYO": "GYO",

    # Sigorta
    "ANSGR": "Sigorta", "TURSG": "Sigorta", "AGESA": "Sigorta",

    # Telekom
    "TCELL": "Telekomünikasyon", "TTKOM": "Telekomünikasyon",

    # Turizm
    "TURSG": "Sigorta",
}


def resolve_sector(symbol, raw_sector=""):
    symbol = normalize_symbol(symbol)
    if symbol in SECTOR_MAP:
        return SECTOR_MAP[symbol]
    raw_sector = str(raw_sector or "").strip()
    return raw_sector if raw_sector else "Diğer"


# ============================================================
# LATEST SNAPSHOT
# ============================================================

def latest_per_symbol(conn, table):
    """
    Teknik/finansal tablolarda symbol başına TEK son kayıt döndürür.
    MAX(...) ile aynı timestamp'e sahip birden fazla satır üretme
    problemini önlemek için ROW_NUMBER kullanılır.
    """
    if not table_exists(conn, table):
        return pd.DataFrame()

    columns = table_columns(conn, table)
    if "symbol" not in columns:
        return pd.DataFrame()

    order_candidates = [
        "analysis_date",
        "updated_at",
        "created_at",
        "date",
        "timestamp",
    ]
    order_cols = [x for x in order_candidates if x in columns]

    if not order_cols:
        return pd.read_sql_query(
            f"SELECT * FROM {table}",
            conn,
        )

    # Birden fazla tarih alanı varsa COALESCE ile en anlamlı tarih kullanılır.
    date_expr = "COALESCE(" + ",".join(order_cols) + ")"

    query = f"""
        SELECT *
        FROM (
            SELECT
                t.*,
                ROW_NUMBER() OVER (
                    PARTITION BY symbol
                    ORDER BY {date_expr} DESC, rowid DESC
                ) AS rn
            FROM {table} t
        )
        WHERE rn = 1
    """

    try:
        return pd.read_sql_query(query, conn)
    except Exception:
        # Eski SQLite/şema ihtimaline karşı güvenli fallback.
        order = order_cols[0]
        query = f"""
            SELECT t.*
            FROM {table} t
            JOIN (
                SELECT symbol, MAX({order}) AS mx
                FROM {table}
                GROUP BY symbol
            ) x
              ON x.symbol=t.symbol
             AND x.mx=t.{order}
        """
        return pd.read_sql_query(query, conn)


# ============================================================
# MARKET SNAPSHOT
# ============================================================

def load_market_snapshot(conn):
    if not table_exists(conn, "market_snapshot"):
        return 50.0, [], None, False

    columns = table_columns(conn, "market_snapshot")
    if "id" not in columns:
        return 50.0, [], None, False

    try:
        row = conn.execute(
            "SELECT * FROM market_snapshot WHERE id=1 LIMIT 1"
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
# UPDATE STATUS
# ============================================================

def load_update_status(conn):
    if not table_exists(conn, "data_update_status"):
        return {}

    try:
        row = conn.execute(
            "SELECT * FROM data_update_status WHERE id=1 LIMIT 1"
        ).fetchone()
        return dict(row) if row else {}
    except Exception:
        return {}


# ============================================================
# UNIVERSE
# ============================================================

def try_load_universe(name):
    """
    BIST listeleri yalnızca DB snapshot'ını filtrelemek için kullanılır.
    Burada dış kaynak çağrısı yoktur.
    """
    try:
        from modules.data.bist_lists import BIST30, BIST50, BIST100, BIST500

        mapping = {
            "BIST 30": BIST30,
            "BIST 50": BIST50,
            "BIST 100": BIST100,
            "BIST 500": BIST500,
        }
        return {
            normalize_symbol(x)
            for x in mapping.get(name, [])
            if normalize_symbol(x)
        }
    except Exception:
        return set()


# ============================================================
# SNAPSHOT OKUMA
# ============================================================

def load_dynamic_cache_rows(conn):
    """dynamic_portfolio_cache içindeki son BIST snapshotını okur."""
    if not table_exists(conn, "dynamic_portfolio_cache"):
        return pd.DataFrame(), None, "cache_table_yok"

    cols = table_columns(conn, "dynamic_portfolio_cache")
    if "analysis_json" not in cols or "symbol" not in cols:
        return pd.DataFrame(), None, "cache_schema_uyumsuz"

    try:
        select_cols = ["symbol", "analysis_json"]
        for col in ["market_score", "analysis_time", "updated_at", "universe"]:
            if col in cols:
                select_cols.append(col)

        df = pd.read_sql_query(
            f"SELECT {', '.join(select_cols)} "
            "FROM dynamic_portfolio_cache "
            "WHERE analysis_json IS NOT NULL "
            "AND TRIM(analysis_json) <> ''",
            conn,
        )
    except Exception:
        return pd.DataFrame(), None, "cache_okunamadi"

    if df.empty:
        return pd.DataFrame(), None, "cache_bos"

    rows = []
    for _, item in df.iterrows():
        try:
            data = json.loads(item["analysis_json"])
        except Exception:
            continue

        if not isinstance(data, dict):
            continue

        data.setdefault("Hisse", normalize_symbol(item["symbol"]))

        if "market_score" in df.columns:
            data.setdefault(
                "Piyasa",
                safe_float(item.get("market_score"), 50.0),
            )

        data["_cache_analysis_time"] = item.get("analysis_time")
        data["_cache_updated_at"] = item.get("updated_at")
        data["_cache_universe"] = item.get("universe")
        rows.append(data)

    if not rows:
        return pd.DataFrame(), None, "cache_json_gecersiz"

    out = pd.DataFrame(rows)
    out["Hisse"] = out["Hisse"].map(normalize_symbol)
    out = out[out["Hisse"].ne("")].drop_duplicates("Hisse")

    # Cache'teki alanları standardize et.
    aliases = {
        "Teknik": ["Teknik", "technical_score", "ai_score", "score"],
        "Fundamental": ["Fundamental", "fundamental_score"],
        "Momentum 60G": ["Momentum 60G", "momentum_60_score", "momentum_score"],
        "Trend": ["Trend", "trend_strength", "trend_score"],
        "Fiyat": ["Fiyat", "price", "last_price", "close"],
        "Günlük %": ["Günlük %", "change", "change_percent"],
        "RSI": ["RSI", "rsi"],
        "Hacim x": ["Hacim x", "volume_ratio"],
        "1Y Getiri %": ["1Y Getiri %", "year_return", "return_1y"],
    }

    for target, choices in aliases.items():
        source = next((c for c in choices if c in out.columns), None)
        if source is None:
            out[target] = np.nan
        else:
            out[target] = pd.to_numeric(
                out[source],
                errors="coerce",
            )

    out["Teknik"] = out["Teknik"].fillna(50).clip(0, 100)
    out["Fundamental"] = out["Fundamental"].fillna(50).clip(0, 100)
    out["Momentum 60G"] = out["Momentum 60G"].fillna(50).clip(0, 100)
    out["Trend"] = out["Trend"].fillna(50).clip(0, 100)
    out["Fiyat"] = out["Fiyat"].fillna(0)
    out["RSI"] = out["RSI"].fillna(50).clip(0, 100)
    out["Hacim x"] = out["Hacim x"].fillna(0)
    out["1Y Getiri %"] = out["1Y Getiri %"].fillna(0)

    if "Piyasa" not in out.columns:
        out["Piyasa"] = 50.0
    out["Piyasa"] = pd.to_numeric(
        out["Piyasa"], errors="coerce"
    ).fillna(50).clip(0, 100)

    # Cache'te eski Genel Skor varsa bile bileşenlerden yeniden üret.
    # Böylece karar eşikleri ve Tarama Merkezi ağırlıkları tek kaynaktan gelir.
    out["Genel Skor"] = (
        out["Teknik"] * W_TECH
        + out["Fundamental"] * W_FUND
        + out["Momentum 60G"] * W_MOM
        + out["Piyasa"] * W_MARKET
    ).clip(0, 100).round(1)

    out["Karar"] = out["Genel Skor"].map(decision)

    if "Sektör" not in out.columns:
        out["Sektör"] = "Diğer"
    out["Sektör"] = out["Sektör"].fillna("Diğer").astype(str)
    out["Financial Veri"] = (
        out["Fundamental"].notna()
        & ~out["Fundamental"].eq(50.0)
    )

    analysis_time = pd.to_datetime(
        out["_cache_analysis_time"],
        errors="coerce",
    )
    latest = (
        analysis_time.max()
        if not analysis_time.empty
        else None
    )

    return out.reset_index(drop=True), latest, "ok"


@st.cache_data(ttl=30, show_spinner=False)
def load_snapshot_data():
    conn = open_db()

    try:
        # 1) Öncelik: veri güncelleme motorunun kaydettiği cache.
        stocks, cache_time, cache_status = load_dynamic_cache_rows(conn)
        source = "dynamic_portfolio_cache"

        # 2) Cache yoksa teknik snapshot.
        if stocks.empty:
            tech = latest_per_symbol(conn, "technical_analysis")
            if tech.empty:
                return {
                    "stocks": pd.DataFrame(),
                    "market_score": 50.0,
                    "market_reasons": [],
                    "market_at": None,
                    "market_valid": False,
                    "status": load_update_status(conn),
                    "source": "YOK",
                    "data_time": None,
                    "error": (
                        "dynamic_portfolio_cache ve "
                        "technical_analysis içinde geçerli snapshot yok."
                    ),
                }

            tech["Hisse"] = tech["symbol"].map(normalize_symbol)

            def num(target, candidates, default):
                source_col = next(
                    (c for c in candidates if c in tech.columns),
                    None,
                )
                if source_col is None:
                    tech[target] = default
                else:
                    tech[target] = pd.to_numeric(
                        tech[source_col],
                        errors="coerce",
                    ).fillna(default)

            num("Teknik", ["ai_score", "score", "technical_score"], 50)
            num("Momentum 60G", ["momentum_60_score", "momentum_score", "momentum"], 50)
            num("Trend", ["trend_strength", "trend_score"], 50)
            num("Fiyat", ["price", "last_price", "close"], 0)
            num("Günlük %", ["change", "change_percent"], 0)
            num("RSI", ["rsi"], 50)
            num("Hacim x", ["volume_ratio"], 0)
            num("1Y Getiri %", ["year_return", "return_1y"], 0)

            tech["Teknik"] = tech["Teknik"].clip(0, 100)
            tech["Momentum 60G"] = tech["Momentum 60G"].clip(0, 100)
            tech["Trend"] = tech["Trend"].clip(0, 100)
            tech["RSI"] = tech["RSI"].clip(0, 100)

            # stocks tablosundan sektör metadata.
            if table_exists(conn, "stocks"):
                sm = pd.read_sql_query(
                    "SELECT * FROM stocks",
                    conn,
                )
                if not sm.empty and "symbol" in sm.columns:
                    sm["Hisse"] = sm["symbol"].map(normalize_symbol)
                    keep = [
                        x for x in
                        ["Hisse", "sector", "company", "industry"]
                        if x in sm.columns
                    ]
                    if keep:
                        tech = tech.merge(
                            sm[keep].drop_duplicates("Hisse"),
                            on="Hisse",
                            how="left",
                        )

            raw_sector = (
                tech["sector"]
                if "sector" in tech.columns
                else pd.Series("", index=tech.index)
            )
            tech["Sektör"] = [
                resolve_sector(s, r)
                for s, r in zip(tech["Hisse"], raw_sector)
            ]

            tech["Fundamental"] = 50.0
            tech["Financial Veri"] = False

            # KAP finansal skorunu ekle.
            financial = latest_per_symbol(conn, "financial_scores")
            if not financial.empty and "symbol" in financial.columns:
                financial["Hisse"] = financial["symbol"].map(normalize_symbol)
                if "total_score" in financial.columns:
                    financial["total_score"] = pd.to_numeric(
                        financial["total_score"],
                        errors="coerce",
                    )
                    fcols = [
                        x for x in
                        ["Hisse", "total_score", "fiscal_year", "fiscal_period"]
                        if x in financial.columns
                    ]
                    tech = tech.merge(
                        financial[fcols].drop_duplicates("Hisse"),
                        on="Hisse",
                        how="left",
                    )
                    tech["Financial Veri"] = tech["total_score"].notna()
                    tech["Fundamental"] = (
                        pd.to_numeric(
                            tech["total_score"],
                            errors="coerce",
                        )
                        .fillna(50)
                        .clip(0, 100)
                    )

            # Market snapshot aşağıda okunacak; şimdilik nötr.
            market_score_tmp = 50.0
            tech["Piyasa"] = market_score_tmp
            tech["Genel Skor"] = (
                tech["Teknik"] * W_TECH
                + tech["Fundamental"] * W_FUND
                + tech["Momentum 60G"] * W_MOM
                + tech["Piyasa"] * W_MARKET
            ).clip(0, 100).round(1)
            tech["Karar"] = tech["Genel Skor"].map(decision)

            stocks = (
                tech[
                    tech["Hisse"].astype(str).str.strip().ne("")
                ]
                .drop_duplicates("Hisse")
                .reset_index(drop=True)
            )
            source = "technical_analysis"
            cache_time = None

        # Sektör override'ları her kaynaktan sonra uygulanır.
        stocks["Hisse"] = stocks["Hisse"].map(normalize_symbol)

        raw_sector = (
            stocks["Sektör"]
            if "Sektör" in stocks.columns
            else pd.Series("", index=stocks.index)
        )
        stocks["Sektör"] = [
            resolve_sector(s, r)
            for s, r in zip(stocks["Hisse"], raw_sector)
        ]

        # Market snapshot.
        market_score, reasons, market_at, market_valid = (
            load_market_snapshot(conn)
        )

        # Market snapshot geçerliyse Genel Skoru tekrar üret.
        # Cache'teki eski piyasa puanı böylece bayat kalmaz.
        if market_valid:
            stocks["Piyasa"] = float(market_score)
        else:
            if "Piyasa" in stocks.columns:
                stocks["Piyasa"] = pd.to_numeric(
                    stocks["Piyasa"], errors="coerce"
                ).fillna(50).clip(0, 100)
            else:
                stocks["Piyasa"] = 50.0
        stocks["Genel Skor"] = (
            pd.to_numeric(stocks["Teknik"], errors="coerce").fillna(50)
            * W_TECH
            + pd.to_numeric(stocks["Fundamental"], errors="coerce").fillna(50)
            * W_FUND
            + pd.to_numeric(stocks["Momentum 60G"], errors="coerce").fillna(50)
            * W_MOM
            + stocks["Piyasa"] * W_MARKET
        ).clip(0, 100).round(1)
        stocks["Karar"] = stocks["Genel Skor"].map(decision)

        # Cache'ten gelmeyen kayıtlarda finansal veri güveni.
        if "Financial Veri" not in stocks.columns:
            stocks["Financial Veri"] = False

        # Snapshot zamanı.
        data_time = cache_time
        if data_time is None:
            for col in [
                "analysis_date",
                "updated_at",
                "created_at",
                "date",
                "timestamp",
            ]:
                if col in stocks.columns:
                    x = pd.to_datetime(
                        stocks[col],
                        errors="coerce",
                    ).max()
                    if pd.notna(x):
                        data_time = x
                        break

        stocks["_snapshot_time"] = data_time

        return {
            "stocks": stocks.reset_index(drop=True),
            "market_score": clamp(market_score),
            "market_reasons": reasons,
            "market_at": market_at,
            "market_valid": market_valid,
            "status": load_update_status(conn),
            "source": source,
            "data_time": data_time,
            "error": "",
        }

    except Exception as exc:
        return {
            "stocks": pd.DataFrame(),
            "market_score": 50.0,
            "market_reasons": [f"DB okuma hatası: {exc}"],
            "market_at": None,
            "market_valid": False,
            "status": {},
            "source": "HATA",
            "data_time": None,
            "error": str(exc),
        }
    finally:
        conn.close()


# ============================================================
# MEVCUT PORTFÖY
# ============================================================

@st.cache_data(ttl=15, show_spinner=False)
def load_current_portfolio():
    """
    Önce portfolio tablosunu okur.
    portfolio yok/boşsa transactions üzerinden net lot hesaplar.
    Böylece ASTOR vb. lot senkronizasyon sorunlarında ekran boş kalmaz.
    """
    conn = open_db()
    try:
        def read_position_table():
            if not table_exists(conn, "portfolio"):
                return {}

            columns = table_columns(conn, "portfolio")
            symbol_col = first_existing(
                columns,
                ["symbol", "ticker", "stock", "hisse", "hisse_kodu"],
            )
            qty_col = first_existing(
                columns,
                ["quantity", "shares", "lot", "adet", "kalan_adet"],
            )
            if not symbol_col or not qty_col:
                return {}

            df = pd.read_sql_query(
                f"SELECT {symbol_col} AS symbol, "
                f"{qty_col} AS quantity FROM portfolio",
                conn,
            )

            result = {}
            for _, row in df.iterrows():
                symbol = normalize_symbol(row["symbol"])
                qty = safe_float(row["quantity"])
                if symbol and qty > 0:
                    result[symbol] = result.get(symbol, 0.0) + qty
            return result

        result = read_position_table()
        if result:
            return result

        if not table_exists(conn, "transactions"):
            return {}

        cols = table_columns(conn, "transactions")
        symbol_col = first_existing(
            cols,
            ["symbol", "ticker", "stock", "hisse", "hisse_kodu"],
        )
        qty_col = first_existing(
            cols,
            ["quantity", "shares", "lot", "adet"],
        )
        side_col = first_existing(
            cols,
            ["type", "transaction_type", "side", "islem", "işlem",
             "action", "transaction"],
        )

        if not symbol_col or not qty_col:
            return {}

        select_cols = (
            f"{symbol_col} AS symbol, "
            f"{qty_col} AS quantity"
        )
        if side_col:
            select_cols += f", {side_col} AS side"

        df = pd.read_sql_query(
            f"SELECT {select_cols} FROM transactions",
            conn,
        )

        result = {}
        for _, row in df.iterrows():
            symbol = normalize_symbol(row["symbol"])
            qty = safe_float(row["quantity"])
            if not symbol or qty == 0:
                continue

            side = str(row.get("side", "")).upper()
            if any(x in side for x in ["SELL", "SAT", "SALE", "ÇIKIŞ", "CIKIS"]):
                qty = -abs(qty)
            elif any(x in side for x in ["BUY", "AL", "PURCHASE", "GİRİŞ", "GIRIS"]):
                qty = abs(qty)

            result[symbol] = result.get(symbol, 0.0) + qty

        return {
            symbol: qty
            for symbol, qty in result.items()
            if qty > 0
        }

    except Exception:
        return {}
    finally:
        conn.close()


# ============================================================
# SEKTÖR GÜCÜ
# ============================================================

def calculate_sector_scores(stock_df):
    """
    Sektör güç modeli

    %35 Hisse Gücü
    %25 Momentum
    %20 Trend
    %10 Genişlik
    %10 Relatif Güç

    Sektör hesabı hisse minimum skor filtresinden ÖNCE
    tüm geçerli snapshot üzerinden yapılır.
    """

    if stock_df is None or stock_df.empty:
        return pd.DataFrame()

    work = stock_df.copy()

    # --------------------------------------------------------
    # Gerekli kolonları güvenli oluştur
    # --------------------------------------------------------

    numeric_defaults = {
        "Genel Skor": 50.0,
        "Momentum 60G": 50.0,
        "Trend": 50.0,
        "1Y Getiri %": 0.0,
    }

    for col, default in numeric_defaults.items():
        if col not in work.columns:
            work[col] = default

        work[col] = pd.to_numeric(
            work[col],
            errors="coerce",
        ).fillna(default)

    if "Karar" not in work.columns:
        work["Karar"] = work["Genel Skor"].map(decision)

    if "Sektör" not in work.columns:
        work["Sektör"] = "Diğer"

    work["Sektör"] = (
        work["Sektör"]
        .fillna("Diğer")
        .astype(str)
        .str.strip()
    )

    work.loc[
        work["Sektör"].eq(""),
        "Sektör"
    ] = "Diğer"

    # --------------------------------------------------------
    # Evren ortalama 1Y getirisi
    # --------------------------------------------------------

    universe_return = safe_float(
        work["1Y Getiri %"].mean(),
        0.0,
    )

    rows = []

    # --------------------------------------------------------
    # Sektör bazında hesap
    # --------------------------------------------------------

    for sector, group in work.groupby(
        "Sektör",
        dropna=False,
    ):

        sector = str(sector or "Diğer").strip()

        if not sector:
            sector = "Diğer"

        # Hisse gücü
        average_general_score = clamp(
            group["Genel Skor"].mean(),
            default=50.0,
        )

        # Momentum
        momentum = clamp(
            group["Momentum 60G"].mean(),
            default=50.0,
        )

        # Trend
        trend = clamp(
            group["Trend"].mean(),
            default=50.0,
        )

        # ----------------------------------------------------
        # Genişlik
        #
        # AL + GÜÇLÜ AL hisselerinin sektördeki oranı
        # ----------------------------------------------------

        buy_mask = group["Karar"].isin(
            [
                "🟢 AL",
                "🟢 GÜÇLÜ AL",
            ]
        )

        breadth = (
            float(buy_mask.mean() * 100.0)
            if len(group) > 0
            else 0.0
        )

        breadth = clamp(
            breadth,
            default=0.0,
        )

        # ----------------------------------------------------
        # Sektör 1Y relatif güç
        # ----------------------------------------------------

        sector_return = safe_float(
            group["1Y Getiri %"].mean(),
            universe_return,
        )

        relative_strength = clamp(
            50.0
            + (
                sector_return
                - universe_return
            ) * 2.0,
            default=50.0,
        )

        # ----------------------------------------------------
        # Nihai sektör skoru
        # ----------------------------------------------------

        sector_score = clamp(
            average_general_score * 0.35
            + momentum * 0.25
            + trend * 0.20
            + breadth * 0.10
            + relative_strength * 0.10,
            default=50.0,
        )

        # ----------------------------------------------------
        # Ayrıntılı sektör kaydı
        #
        # Burada ESKİ isimleri de tutuyoruz.
        # Böylece mevcut UI ve ilerideki kodlar kırılmaz.
        # ----------------------------------------------------

        rows.append(
            {
                "Sektör": sector,

                # Ana skor
                "Sektör Skoru": round(
                    sector_score,
                    1,
                ),

                # Eski / açıklayıcı isim
                "Hisse Gücü": round(
                    average_general_score,
                    1,
                ),

                # UI uyumluluğu
                "Ortalama Genel Skor": round(
                    average_general_score,
                    1,
                ),

                "Momentum": round(
                    momentum,
                    1,
                ),

                "Trend": round(
                    trend,
                    1,
                ),

                "Genişlik %": round(
                    breadth,
                    1,
                ),

                # UI uyumluluğu
                "AL Genişliği %": round(
                    breadth,
                    1,
                ),

                "Relatif Güç": round(
                    relative_strength,
                    1,
                ),

                "Sektör 1Y %": round(
                    sector_return,
                    1,
                ),

                "AL": int(
                    (
                        group["Karar"]
                        == "🟢 AL"
                    ).sum()
                ),

                "Güçlü AL": int(
                    (
                        group["Karar"]
                        == "🟢 GÜÇLÜ AL"
                    ).sum()
                ),

                "Toplam Hisse": int(
                    len(group)
                ),

                "Durum": sector_status(
                    sector_score
                ),
            }
        )

    if not rows:
        return pd.DataFrame(
            columns=[
                "Sektör",
                "Sektör Skoru",
                "Hisse Gücü",
                "Ortalama Genel Skor",
                "Momentum",
                "Trend",
                "Genişlik %",
                "AL Genişliği %",
                "Relatif Güç",
                "Sektör 1Y %",
                "AL",
                "Güçlü AL",
                "Toplam Hisse",
                "Durum",
            ]
        )

    result = pd.DataFrame(rows)

    return (
        result
        .sort_values(
            [
                "Sektör Skoru",
                "Toplam Hisse",
            ],
            ascending=[
                False,
                False,
            ],
        )
        .reset_index(drop=True)
    )

# ============================================================
# ADAY HAVUZU
# ============================================================

def build_candidates(stock_df, sector_df, sector_min, stock_min):
    if stock_df.empty or sector_df.empty:
        return pd.DataFrame()

    eligible_sectors = set(
        sector_df.loc[
            sector_df["Sektör Skoru"] >= sector_min,
            "Sektör",
        ]
    )

    candidates = stock_df[
        (stock_df["Sektör"].isin(eligible_sectors))
        & (stock_df["Genel Skor"] >= stock_min)
        & (stock_df["Karar"].isin(["🟢 AL", "🟢 GÜÇLÜ AL"]))
    ].copy()

    if candidates.empty:
        return candidates

    sector_lookup = dict(
        zip(
            sector_df["Sektör"],
            sector_df["Sektör Skoru"],
        )
    )

    candidates["Sektör Skoru"] = (
        candidates["Sektör"].map(sector_lookup).fillna(50.0)
    )

    # Portföy skoru:
    # Genel %65 + sektör %25 + momentum %10
    candidates["Portföy Skoru"] = (
        candidates["Genel Skor"] * 0.65
        + candidates["Sektör Skoru"] * 0.25
        + candidates["Momentum 60G"] * 0.10
    ).clip(0, 100).round(1)

    candidates["Aday Gücü"] = np.where(
        candidates["Karar"].eq("🟢 GÜÇLÜ AL"),
        "⭐⭐⭐⭐⭐",
        "⭐⭐⭐⭐",
    )

    candidates["Veri Güveni"] = np.where(
        candidates["Financial Veri"],
        "🟢 Teknik + KAP",
        "🟡 Teknik + nötr finansal",
    )

    return candidates.sort_values(
        ["Portföy Skoru", "Genel Skor", "Momentum 60G"],
        ascending=False,
    ).reset_index(drop=True)


# ============================================================
# KISITLI AĞIRLIK MOTORU
# ============================================================

def allocate_capped_weights(candidates, max_positions, stock_cap, sector_cap):
    """
    Gerçek kısıtlı ağırlık dağıtımı.

    Önce skor bazlı ağırlık oluşturur.
    Sonra:
      - tek hisse tavanını,
      - tek sektör tavanını
    uygular.
    Kalan ağırlığı, kapasitesi olan hisselere tekrar dağıtır.

    Böylece eski kodda görülen:
        cap -> normalize -> cap ihlali
    problemi oluşmaz.
    """
    if candidates.empty or max_positions <= 0:
        return candidates.copy()

    df = candidates.head(int(max_positions)).copy().reset_index(drop=True)

    stock_cap = max(0.0, min(100.0, safe_float(stock_cap, 25.0)))
    sector_cap = max(0.0, min(100.0, safe_float(sector_cap, 40.0)))

    if df.empty:
        return df

    scores = df["Portföy Skoru"].clip(lower=0.01).astype(float)
    raw = scores / scores.sum() * 100.0

    # Başlangıç
    weights = pd.Series(0.0, index=df.index)

    # Aktif sektörler ve hisse kapasiteleri
    active = set(df.index)

    # Adım adım dağıtım.
    # Her turda kalan ağırlığı skor oranına göre dağıt,
    # limitlere takılanları sabitle ve kalanları tekrar dağıt.
    for _ in range(50):
        if not active:
            break

        remaining = 100.0 - float(weights.sum())
        if remaining <= 1e-9:
            break

        active_idx = sorted(active)
        active_scores = scores.loc[active_idx]

        if active_scores.sum() <= 0:
            shares = pd.Series(
                1.0 / len(active_idx),
                index=active_idx,
            )
        else:
            shares = active_scores / active_scores.sum()

        proposed = shares * remaining
        capped_any = False

        # Önce hisse kapasitesi
        for idx in active_idx:
            stock_room = max(0.0, stock_cap - weights.loc[idx])
            if proposed.loc[idx] > stock_room + 1e-9:
                weights.loc[idx] += stock_room
                active.remove(idx)
                capped_any = True

        # Sektör kapasitesi:
        # mevcut + önerilenler üzerinden sektör toplamını sınırla.
        for sector in df.loc[active_idx, "Sektör"].unique():
            sector_idx = [
                i for i in active_idx
                if i in active and df.loc[i, "Sektör"] == sector
            ]
            if not sector_idx:
                continue

            current_sector = float(
                weights.loc[
                    df.index[df["Sektör"] == sector]
                ].sum()
            )
            room = max(0.0, sector_cap - current_sector)

            proposed_sector = float(proposed.loc[sector_idx].sum())

            if proposed_sector > room + 1e-9:
                # Oransal biçimde sektör içine dağıt.
                if proposed_sector <= 0:
                    continue

                for idx in sector_idx:
                    add = proposed.loc[idx] / proposed_sector * room
                    weights.loc[idx] += add

                # Sektör doldu; bu hisseleri aktiften çıkar.
                for idx in sector_idx:
                    active.remove(idx)

                capped_any = True

        if not capped_any:
            for idx in active_idx:
                if idx in active:
                    weights.loc[idx] += proposed.loc[idx]
            break

    # Yuvarlama sonrası küçük farkları güvenli biçimde dağıt.
    weights = weights.clip(lower=0.0)

    total = float(weights.sum())
    if total > 0 and abs(total - 100.0) > 1e-7:
        weights = weights / total * 100.0

    # Son doğrulama: floating point yüzünden cap aşımı oluşursa düzelt.
    weights = weights.clip(upper=stock_cap)

    # Sektör tavanı kesin kontrol.
    for sector in df["Sektör"].unique():
        idx = df.index[df["Sektör"] == sector]
        total_sector = float(weights.loc[idx].sum())
        if total_sector > sector_cap + 1e-7:
            weights.loc[idx] *= sector_cap / total_sector

    # Cap düzeltmesinden sonra toplam %100 olmayabilir.
    # Bu durumda kapasitesi olanlara tekrar dağıt.
    for _ in range(100):
        total = float(weights.sum())
        remainder = 100.0 - total

        if remainder <= 1e-8:
            break

        capacities = {}
        for idx in df.index:
            stock_room = max(0.0, stock_cap - weights.loc[idx])

            sector = df.loc[idx, "Sektör"]
            sector_idx = df.index[df["Sektör"] == sector]
            sector_room = max(
                0.0,
                sector_cap - float(weights.loc[sector_idx].sum()),
            )

            capacities[idx] = min(stock_room, sector_room)

        total_capacity = sum(capacities.values())
        if total_capacity <= 1e-8:
            break

        # Skor bazlı kapasite önceliği
        priority = scores * pd.Series(
            capacities,
            index=df.index,
        )
        if priority.sum() <= 0:
            priority = pd.Series(capacities, index=df.index)

        for idx in df.index:
            add = (
                remainder * priority.loc[idx] / priority.sum()
                if priority.sum() > 0
                else 0
            )
            weights.loc[idx] += min(
                add,
                capacities[idx],
            )

    # Nihai güvenlik kontrolü
    weights = weights.clip(0.0, stock_cap)

    for sector in df["Sektör"].unique():
        idx = df.index[df["Sektör"] == sector]
        total_sector = float(weights.loc[idx].sum())
        if total_sector > sector_cap + 1e-7:
            weights.loc[idx] *= sector_cap / total_sector

    df["Hedef Oran %"] = weights.round(2)

    # Portföyde sıfır ağırlıklı aday kalmasın.
    df = df[df["Hedef Oran %"] > 0].copy()

    return df.reset_index(drop=True)


# ============================================================
# MEVCUT / HEDEF KARŞILAŞTIRMA
# ============================================================

def compare_portfolio(target_df, current, capital):
    if target_df.empty:
        return target_df.copy()

    df = target_df.copy()
    capital = max(0.0, safe_float(capital))

    df["Mevcut Lot"] = 0.0
    df["Mevcut Değer"] = 0.0
    df["Mevcut Oran %"] = 0.0

    for idx, row in df.iterrows():
        symbol = row["Hisse"]
        qty = safe_float(current.get(symbol))
        price = safe_float(row["Fiyat"])
        value = qty * price

        df.at[idx, "Mevcut Lot"] = qty
        df.at[idx, "Mevcut Değer"] = value
        df.at[idx, "Mevcut Oran %"] = (
            value / capital * 100.0
            if capital > 0
            else 0.0
        )

    df["Oran Farkı %"] = (
        df["Hedef Oran %"] - df["Mevcut Oran %"]
    ).round(2)

    actions = []

    for _, row in df.iterrows():
        current_weight = safe_float(row["Mevcut Oran %"])
        target_weight = safe_float(row["Hedef Oran %"])
        diff = target_weight - current_weight

        if current_weight <= 0.001:
            action = "🟢 YENİ POZİSYON"
        elif diff >= 3:
            action = "🟢 AĞIRLIK ARTIR"
        elif diff <= -5:
            action = "🟠 AĞIRLIK AZALT"
        else:
            action = "🟡 KORU"

        actions.append(action)

    df["Aksiyon"] = actions

    df["Hedef Tutar"] = (
        df["Hedef Oran %"] / 100.0 * capital
    )
    df["Al/Sat Tutarı"] = (
        df["Hedef Tutar"] - df["Mevcut Değer"]
    )

    safe_price = df["Fiyat"].replace(0, np.nan)
    df["Hedef Lot"] = (
        df["Hedef Tutar"] / safe_price
    ).fillna(0.0)

    df["Hedef Lot"] = np.floor(df["Hedef Lot"]).astype(float)

    df["Lot Farkı"] = (
        df["Hedef Lot"] - df["Mevcut Lot"]
    ).round(0)

    return df


# ============================================================
# MEVCUT PORTFÖY RİSKİ
# ============================================================

def build_risk_table(stock_df, sector_df, current, sector_min, stock_min):
    if not current:
        return pd.DataFrame()

    sector_lookup = dict(
        zip(
            sector_df["Sektör"],
            sector_df["Sektör Skoru"],
        )
    ) if not sector_df.empty else {}

    rows = []

    for symbol, qty in current.items():
        match = stock_df[
            stock_df["Hisse"] == symbol
        ]

        if match.empty:
            rows.append({
                "Hisse": symbol,
                "Lot": qty,
                "Durum": "🟠 VERİ YOK",
                "Neden": "Son DB snapshotında analiz bulunamadı.",
            })
            continue

        row = match.iloc[0]
        sector_score = safe_float(
            sector_lookup.get(row["Sektör"], 50.0),
            50.0,
        )

        if row["Karar"] == "🔴 SAT":
            status = "🔴 ÇIKIŞ RİSKİ"
            reason = "Genel skor satış bölgesinde."

        elif row["Karar"] in ["🟡 TUT", "🟠 İZLE"]:
            status = "🟠 İZLE / AZALT"
            reason = "Hisse aday havuzunun altında."

        elif sector_score < sector_min:
            status = "🟠 SEKTÖR RİSKİ"
            reason = (
                f"Sektör skoru {sector_score:.1f}; "
                f"eşik {sector_min:.1f}."
            )

        elif row["Genel Skor"] < stock_min:
            status = "🟠 HİSSE SKORU ZAYIF"
            reason = (
                f"Genel skor {row['Genel Skor']:.1f}; "
                f"seçilen eşik {stock_min:.0f}."
            )

        else:
            status = "🟢 UYGUN"
            reason = "Mevcut kriterleri karşılıyor."

        rows.append({
            "Hisse": symbol,
            "Lot": qty,
            "Sektör": row["Sektör"],
            "Sektör Skoru": sector_score,
            "Genel Skor": row["Genel Skor"],
            "Karar": row["Karar"],
            "Durum": status,
            "Neden": reason,
        })

    return pd.DataFrame(rows)


# ============================================================
# VERİ DURUMU
# ============================================================

def format_timestamp(value):
    value = pd.to_datetime(value, errors="coerce")
    if pd.isna(value):
        return "Bilinmiyor"
    return value.strftime("%d.%m.%Y %H:%M:%S")


def age_minutes(value):
    value = pd.to_datetime(value, errors="coerce")
    if pd.isna(value):
        return None

    now = pd.Timestamp.now(tz=None)

    # timezone farklılığı varsa güvenli hale getir.
    try:
        if value.tzinfo is not None:
            value = value.tz_localize(None)
    except Exception:
        pass

    try:
        return max(
            0.0,
            (now - value).total_seconds() / 60.0,
        )
    except Exception:
        return None


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:
    st.header("⚙️ Dinamik Portföy")

    universe_name = st.selectbox(
        "Veri evreni",
        ["DB Snapshot", "BIST 500", "BIST 100", "BIST 50", "BIST 30"],
        index=0,
        help="DB Snapshot tüm technical_analysis snapshot'ını kullanır. "
             "BIST seçenekleri yalnızca DB içindeki hisseleri filtreler.",
    )

    sector_min = st.slider(
        "Minimum sektör skoru",
        40.0,
        80.0,
        DEFAULT_SECTOR_MIN,
        1.0,
    )

    stock_min = st.slider(
        "Minimum hisse Genel Skoru",
        60.0,
        90.0,
        DEFAULT_STOCK_MIN,
        1.0,
    )

    max_positions = st.slider(
        "Maksimum hedef hisse",
        3,
        15,
        DEFAULT_MAX_POSITIONS,
        1,
    )

    max_stock_weight = st.slider(
        "Tek hisse maksimum %",
        10.0,
        40.0,
        DEFAULT_STOCK_CAP,
        1.0,
    )

    max_sector_weight = st.slider(
        "Tek sektör maksimum %",
        20.0,
        60.0,
        DEFAULT_SECTOR_CAP,
        1.0,
    )

    capital = st.number_input(
        "Model portföy sermayesi (TL)",
        min_value=0.0,
        value=100000.0,
        step=5000.0,
    )

    ui_refresh = st.selectbox(
        "Arayüz yenileme",
        [0, 5, 10, 15, 30],
        index=0,
        format_func=lambda x:
            "Kapalı" if x == 0 else f"{x} dakika",
        help="Sadece ekranı yeniler. Yeni veri taraması yapmaz.",
    )

    refresh_button = st.button(
        "🔄 ŞİMDİ YENİLE",
        use_container_width=True,
    )

    st.divider()
    st.caption("Veri kaynağı: SQLite / borsa.db")
    st.caption("Dış kaynak taraması: KAPALI")
    st.caption("Emir gönderimi: KAPALI")


if refresh_button:
    st.cache_data.clear()
    st.rerun()

if ui_refresh > 0 and st_autorefresh is not None:
    st_autorefresh(
        interval=ui_refresh * 60 * 1000,
        key="dynamic_portfolio_ui_refresh",
    )


# ============================================================
# ANA VERİ
# ============================================================

payload = load_snapshot_data()

stocks = payload["stocks"].copy()
market_score = payload["market_score"]
market_reasons = payload["market_reasons"]
market_at = payload["market_at"]
market_valid = payload["market_valid"]
update_status = payload["status"]
load_error = payload["error"]

st.title("🏆 DİNAMİK AI PORTFÖY")
st.caption(
    "SQLite snapshot → sektör gücü → hisse skoru → "
    "hedef ağırlık → mevcut portföy → rebalance"
)

if load_error and stocks.empty:
    st.error(load_error)
    st.info(
        "Bu sayfa dış kaynağa gitmez. Önce veri güncelleme motorunun "
        "technical_analysis snapshot üretmesi gerekir."
    )
    st.stop()


# ============================================================
# VERİ DURUMU
# ============================================================

last_success = pd.to_datetime(
    update_status.get("last_success_at"),
    errors="coerce",
)

snapshot_time = (
    stocks["_snapshot_time"].iloc[0]
    if not stocks.empty and "_snapshot_time" in stocks.columns
    else None
)

if pd.isna(last_success):
    status_time_text = "Henüz başarılı veri güncellemesi yok"
    status_age_text = "Bilinmiyor"
else:
    status_time_text = format_timestamp(last_success)
    age = age_minutes(last_success)
    status_age_text = (
        f"{age:.0f} dk" if age is not None else "Bilinmiyor"
    )

source_text = "SQLite önbellek / snapshot"

st.info(
    f"🟢 Son başarılı veri: **{status_time_text}** | "
    f"Veri yaşı: **{status_age_text}** | "
    f"Kaynak: **{source_text}**"
)

if str(update_status.get("status", "")).upper() in {
    "ERROR", "FAILED"
}:
    st.warning(
        "Son veri güncellemesi başarısız. "
        "Mevcut geçerli DB snapshotı kullanılmaya devam ediyor."
    )


# ============================================================
# EVREN FİLTRESİ
# ============================================================

if universe_name == "DB Snapshot":
    universe_symbols = set(stocks["Hisse"].astype(str))
    universe_label = "DB Snapshot"
else:
    requested = try_load_universe(universe_name)

    if requested:
        universe_symbols = (
            set(stocks["Hisse"].astype(str))
            & requested
        )
        universe_label = (
            f"{universe_name} / DB'de bulunanlar"
        )
    else:
        # Liste modülü yoksa sayfa yine çalışır:
        universe_symbols = set(stocks["Hisse"].astype(str))
        universe_label = (
            f"{universe_name} / liste bulunamadı → DB Snapshot"
        )

stocks = stocks[
    stocks["Hisse"].isin(universe_symbols)
].copy()

if stocks.empty:
    st.error(
        "Seçilen evrende DB snapshotında geçerli hisse bulunamadı."
    )
    st.stop()


# ============================================================
# SEKTÖR / ADAY / HEDEF
# ============================================================

# Sektör skoru TÜM geçerli snapshot üzerinden hesaplanır.
# Önce hisse filtresi uygulamak sektörleri yapay biçimde güçlendiriyordu.
all_snapshot_count = len(stocks)

sector_df = calculate_sector_scores(stocks)

strong_sector_df = sector_df[
    sector_df["Sektör Skoru"] >= sector_min
].copy()

# Hisse minimumu yalnızca aday seçiminde kullanılır.
eligible_stock_df = stocks[
    stocks["Genel Skor"] >= stock_min
].copy()

candidate_df = build_candidates(
    stocks,
    sector_df,
    sector_min,
    stock_min,
)

target_df = allocate_capped_weights(
    candidate_df,
    max_positions,
    max_stock_weight,
    max_sector_weight,
)

current_portfolio = load_current_portfolio()

target_df = compare_portfolio(
    target_df,
    current_portfolio,
    capital,
)

if eligible_stock_df.empty:
    st.warning(
        f"Genel Skor ≥ {stock_min:.0f} olan hisse bulunamadı. "
        "Aday havuzu bu nedenle boş."
    )

# ============================================================
# ÜST ÖZET
# ============================================================

st.divider()
st.subheader("🧠 DİNAMİK PORTFÖY ÖZETİ")

c1, c2, c3, c4, c5, c6 = st.columns(6)

c1.metric(
    "DB Hisse",
    all_snapshot_count,
)

c2.metric(
    "Skor Uygun",
    len(eligible_stock_df),
)

c3.metric(
    "Güçlü Sektör",
    len(strong_sector_df),
)

c4.metric(
    "AL / GÜÇLÜ AL",
    len(candidate_df),
)

c5.metric(
    "Hedef Hisse",
    len(target_df),
)

c6.metric(
    "Piyasa",
    f"{market_score:.1f}",
)


# ============================================================
# SEKTÖR GÜÇ HARİTASI
# ============================================================

st.divider()
st.subheader("🏭 SEKTÖR GÜÇ HARİTASI")
st.caption(
    "Sektör skoru = %35 Hisse Gücü + %25 Momentum + "
    "%20 Trend + %10 Genişlik + %10 BIST relatif güç."
)

if sector_df.empty:
    st.info("Sektör verisi bulunamadı.")
else:
    sector_show = sector_df.copy()

    for col in [
        "Sektör Skoru",
        "Ortalama Genel Skor",
        "AL Genişliği %",
    ]:
        sector_show[col] = sector_show[col].round(1)

    st.dataframe(
        sector_show,
        use_container_width=True,
        hide_index=True,
    )

    st.bar_chart(
        sector_df.head(15).set_index("Sektör")["Sektör Skoru"],
        use_container_width=True,
    )


# ============================================================
# HEDEF PORTFÖY
# ============================================================

st.divider()
st.subheader("🏆 ÖNERİLEN DİNAMİK PORTFÖY")

if target_df.empty:
    st.warning(
        f"Sektör skoru ≥ {sector_min:.0f} ve "
        f"Genel Skor ≥ {stock_min:.0f} şartlarını sağlayan "
        "AL/GÜÇLÜ AL adayı yok."
    )
else:
    first = target_df.iloc[0]

    st.success(
        f"🏆 Ana aday: **{first['Hisse']}** — "
        f"{first['Karar']} — "
        f"Portföy Skoru **{first['Portföy Skoru']:.1f}**"
    )

    show = target_df.copy()

    for col in [
        "Hedef Oran %",
        "Mevcut Oran %",
        "Oran Farkı %",
        "Sektör Skoru",
        "Genel Skor",
        "Portföy Skoru",
        "Fiyat",
        "Mevcut Lot",
        "Hedef Lot",
        "Lot Farkı",
    ]:
        if col in show.columns:
            show[col] = show[col].round(2)

    for col in [
        "Hedef Tutar",
        "Mevcut Değer",
        "Al/Sat Tutarı",
    ]:
        if col in show.columns:
            show[col] = show[col].map(money)

    display_cols = [
        "Hisse",
        "Sektör",
        "Karar",
        "Portföy Skoru",
        "Sektör Skoru",
        "Genel Skor",
        "Fiyat",
        "Mevcut Lot",
        "Hedef Lot",
        "Lot Farkı",
        "Mevcut Oran %",
        "Hedef Oran %",
        "Oran Farkı %",
        "Aksiyon",
        "Hedef Tutar",
        "Al/Sat Tutarı",
    ]

    display_cols = [
        x for x in display_cols
        if x in show.columns
    ]

    st.dataframe(
        show[display_cols],
        use_container_width=True,
        hide_index=True,
    )

    # Ağırlık kontrolü
    total_target = float(
        target_df["Hedef Oran %"].sum()
    )

    max_stock_real = float(
        target_df["Hedef Oran %"].max()
    )

    sector_real = (
        target_df.groupby("Sektör")["Hedef Oran %"]
        .sum()
        if not target_df.empty
        else pd.Series(dtype=float)
    )

    max_sector_real = (
        float(sector_real.max())
        if not sector_real.empty
        else 0.0
    )

    cc1, cc2, cc3 = st.columns(3)
    cc1.metric(
        "Hedef toplam",
        f"{total_target:.2f}%",
    )
    cc2.metric(
        "En yüksek hisse",
        f"{max_stock_real:.2f}%",
    )
    cc3.metric(
        "En yüksek sektör",
        f"{max_sector_real:.2f}%",
    )

    # Beklenen kontrol
    if (
        abs(total_target - 100.0) <= 0.15
        and max_stock_real <= max_stock_weight + 0.15
        and max_sector_real <= max_sector_weight + 0.15
    ):
        st.success(
            "✅ Ağırlık motoru doğrulandı: "
            "toplam %100 ve hisse/sektör tavanları korunuyor."
        )
    else:
        st.warning(
            "⚠️ Ağırlıklar tavanlara göre sınırlı kaldı. "
            "Bu durum aşırı sıkı risk limitlerinde normaldir."
        )


# ============================================================
# SEKTÖR AĞIRLIKLARI
# ============================================================

if not target_df.empty:
    st.divider()
    st.subheader("⚖️ HEDEF SEKTÖR AĞIRLIKLARI")

    sector_weights = (
        target_df.groupby("Sektör")["Hedef Oran %"]
        .sum()
        .sort_values(ascending=False)
    )

    st.dataframe(
        sector_weights.reset_index(
            name="Hedef Ağırlık %"
        ).round(2),
        use_container_width=True,
        hide_index=True,
    )

    st.bar_chart(
        sector_weights,
        use_container_width=True,
    )


# ============================================================
# REBALANCE
# ============================================================

if not target_df.empty:
    st.divider()
    st.subheader("🔄 REBALANCE SİNYALLERİ")

    actions = target_df[
        target_df["Aksiyon"] != "🟡 KORU"
    ].copy()

    if actions.empty:
        st.success(
            "🟢 Mevcut portföy ile hedef portföy arasında "
            "önemli ağırlık farkı yok."
        )
    else:
        action_show = actions.copy()
        action_show["Al/Sat Tutarı"] = (
            action_show["Al/Sat Tutarı"].map(money)
        )

        st.dataframe(
            action_show[
                [
                    "Hisse",
                    "Sektör",
                    "Karar",
                    "Mevcut Oran %",
                    "Hedef Oran %",
                    "Oran Farkı %",
                    "Aksiyon",
                    "Al/Sat Tutarı",
                    "Lot Farkı",
                ]
            ],
            use_container_width=True,
            hide_index=True,
        )


# ============================================================
# ADAY HAVUZU
# ============================================================

st.divider()
st.subheader("🎯 GÜÇLÜ SEKTÖRLERDE AL / GÜÇLÜ AL HAVUZU")

if candidate_df.empty:
    st.warning("Uygun aday bulunamadı.")
else:
    candidate_show = candidate_df.copy()

    for col in [
        "Portföy Skoru",
        "Sektör Skoru",
        "Genel Skor",
        "Teknik",
        "Fundamental",
        "Momentum 60G",
        "Trend",
        "Piyasa",
        "RSI",
        "Hacim x",
        "1Y Getiri %",
    ]:
        if col in candidate_show.columns:
            candidate_show[col] = candidate_show[col].round(2)

    cols = [
        "Hisse",
        "Sektör",
        "Aday Gücü",
        "Karar",
        "Portföy Skoru",
        "Sektör Skoru",
        "Genel Skor",
        "Teknik",
        "Fundamental",
        "Momentum 60G",
        "Trend",
        "Piyasa",
        "RSI",
        "Hacim x",
        "1Y Getiri %",
        "Veri Güveni",
    ]

    cols = [x for x in cols if x in candidate_show.columns]

    st.dataframe(
        candidate_show[cols],
        use_container_width=True,
        hide_index=True,
    )


# ============================================================
# MEVCUT PORTFÖY RİSK KONTROLÜ
# ============================================================

st.divider()
st.subheader("🚨 MEVCUT PORTFÖY RİSK KONTROLÜ")

risk_df = build_risk_table(
    stocks,
    sector_df,
    current_portfolio,
    sector_min,
    stock_min,
)

if risk_df.empty:
    st.info(
        "portfolio tablosunda mevcut pozisyon bulunamadı."
    )
else:
    st.dataframe(
        risk_df,
        use_container_width=True,
        hide_index=True,
    )


# ============================================================
# PİYASA
# ============================================================

st.divider()
st.subheader("🌍 PİYASA DURUMU")

m1, m2 = st.columns(2)

m1.metric(
    "BIST Piyasa Skoru",
    f"{market_score:.1f}/100",
)

m2.metric(
    "Piyasa Snapshot",
    "Geçerli" if market_valid else "Nötr varsayım",
)

if market_at is not None:
    st.caption(
        f"Piyasa snapshot zamanı: {format_timestamp(market_at)}"
    )

if market_reasons:
    for reason in market_reasons:
        st.write(f"• {reason}")
else:
    st.caption(
        "Piyasa snapshot gerekçesi bulunamadı."
    )


# ============================================================
# VERİ KALİTESİ
# ============================================================

st.divider()
st.subheader("🛡️ VERİ KALİTESİ")

financial_coverage = (
    float(stocks["Financial Veri"].mean() * 100)
    if not stocks.empty
    else 0.0
)

q1, q2, q3, q4 = st.columns(4)

q1.metric(
    "Snapshot Hisse",
    len(stocks),
)

q2.metric(
    "Filtrelenen",
    len(eligible_stock_df),
)

q3.metric(
    "KAP Finansal Veri",
    f"{financial_coverage:.1f}%",
)

q4.metric(
    "Dış Kaynak Taraması",
    "KAPALI",
)


# ============================================================
# NASIL ÇALIŞIR?
# ============================================================

with st.expander("📖 Dinamik Portföy nasıl çalışıyor?"):
    st.markdown(
        f"""
### 1. Veri kaynağı
Sayfa dış kaynağa gidip hisse taramaz. `technical_analysis`
snapshotını SQLite'tan okur.

### 2. Genel skor
Tarama Merkezi ile uyumlu ağırlıklar:

- Teknik: **%50**
- KAP/Finansal: **%20**
- 60G Momentum: **%15**
- Piyasa: **%15**

### 3. Sektör gücü
Sektör skoru:

**%35 Hisse Gücü + %25 Momentum + %20 Trend + %10 Genişlik + %10 BIST relatif güç**

Sektör skoru, hisse minimum filtresinden **önce** tüm geçerli
snapshot üzerinden hesaplanır.

### 4. Aday seçimi
Sadece:

- Sektör skoru ≥ **{sector_min:.0f}**
- Genel skor ≥ **{stock_min:.0f}**
- Karar = **AL / GÜÇLÜ AL**

olan hisseler aday olur.

### 5. Portföy skoru
**Genel Skor %65 + Sektör %25 + 60G Momentum %10**

### 6. Risk kontrolü
Tek hisse maksimum **%{max_stock_weight:.0f}**,
tek sektör maksimum **%{max_sector_weight:.0f}**.

Ağırlık motoru tavanları uyguladıktan sonra kalan ağırlığı
kapasitesi olan hisselere tekrar dağıtır; böylece normalizasyon
sonrasında tavanların aşılması engellenir.

### 7. Mevcut portföy
`portfolio` tablosundaki gerçek lotlar hedef portföyle karşılaştırılır.

### 8. Önemli
Bu sayfa emir göndermez. Yalnızca hedef portföy,
risk ve rebalance önerisi üretir.

Arka plandaki veri güncelleme motoru ayrı çalışır; burada
**30 dakikalık yenileme yalnızca arayüzü yeniler.**
"""
    )

st.caption(
    "BIST AI PRO bir karar destek sistemidir; otomatik emir sistemi değildir."
)
