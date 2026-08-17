import sqlite3
from pathlib import Path
from datetime import datetime

import pandas as pd


# ==========================================================
# BIST AI PRO - MERKEZİ SQLITE DATABASE
#
# AMAÇ
# ----------------------------------------------------------
# - Tüm uygulama modüllerinin aynı borsa.db dosyasını
#   kullanmasını sağlamak
# - Eski veritabanlarını SİLMEDEN yeni kolonları otomatik
#   olarak eklemek
# - Özellikle financial_scores.fiscal_year hatasını
#   güvenli şekilde çözmek
# ==========================================================


# ==========================================================
# VERİTABANI KONUMU
# ==========================================================

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "borsa.db"


# ==========================================================
# VERİTABANI BAĞLANTISI
# ==========================================================

def get_connection():
    conn = sqlite3.connect(
        DB_PATH,
        check_same_thread=False
    )

    conn.row_factory = sqlite3.Row

    return conn


# ==========================================================
# TABLO KOLONLARINI KONTROL
# ==========================================================

def _get_columns(cursor, table_name):
    """
    Verilen tablonun mevcut kolonlarını döndürür.

    ÖNEMLİ:
    Mevcut veritabanı silinmez.
    Sadece PRAGMA ile şema kontrol edilir.
    """
    cursor.execute(
        f"PRAGMA table_info({table_name})"
    )

    return {
        row["name"]
        for row in cursor.fetchall()
    }


# ==========================================================
# EKSİK KOLONU OTOMATİK EKLE
# ==========================================================

def _add_missing_columns(cursor, table_name, columns):
    """
    columns:
        {
            "column_name": "SQL TYPE DEFAULT ..."
        }

    Mevcut kolona dokunmaz.
    Eksik kolon varsa ALTER TABLE ile ekler.
    """

    existing_columns = _get_columns(
        cursor,
        table_name
    )

    for column_name, definition in columns.items():

        if column_name not in existing_columns:

            cursor.execute(
                f"""
                ALTER TABLE {table_name}
                ADD COLUMN {column_name} {definition}
                """
            )


# ==========================================================
# TABLOLARI OLUŞTUR + ŞEMA MIGRATION
# ==========================================================

def create_tables():

    conn = get_connection()
    cursor = conn.cursor()

    try:

        # --------------------------------------------------
        # HİSSELER
        # --------------------------------------------------

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stocks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT UNIQUE,
                company TEXT,
                sector TEXT,
                price REAL,
                change_percent REAL,
                volume REAL,
                updated_at TEXT
            )
        """)

        # --------------------------------------------------
        # PORTFÖY
        # --------------------------------------------------

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS portfolio (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT,
                quantity INTEGER,
                avg_cost REAL,
                buy_date TEXT,
                note TEXT
            )
        """)

        # --------------------------------------------------
        # İŞLEM GEÇMİŞİ
        # --------------------------------------------------

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT,
                action TEXT,
                quantity INTEGER,
                price REAL,
                date TEXT
            )
        """)

        # --------------------------------------------------
        # BİLANÇO TABLOSU
        # --------------------------------------------------

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS financial_statements (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                symbol TEXT NOT NULL,

                period TEXT NOT NULL,

                period_end TEXT NOT NULL,

                report_type TEXT,

                currency TEXT DEFAULT 'TRY',

                revenue REAL,

                cost_of_sales REAL,

                operating_profit REAL,

                depreciation_amortization REAL,

                ebitda REAL,

                net_profit REAL,

                interest_expense REAL,

                cash REAL,

                short_term_financial_debt REAL,

                current_portion_long_term_debt REAL,

                long_term_financial_debt REAL,

                trade_receivables REAL,

                inventory REAL,

                current_assets REAL,

                current_liabilities REAL,

                total_assets REAL,

                equity REAL,

                operating_cash_flow REAL,

                source TEXT DEFAULT 'KAP',

                source_date TEXT,

                created_at TEXT DEFAULT CURRENT_TIMESTAMP,

                updated_at TEXT DEFAULT CURRENT_TIMESTAMP

            )
        """)

        # --------------------------------------------------
        # BİLANÇO SKORLARI
        # --------------------------------------------------

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS financial_scores (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                symbol TEXT NOT NULL,

                analysis_date TEXT,

                fiscal_year INTEGER,

                fiscal_period TEXT,

                revenue_score REAL DEFAULT 0,

                profit_score REAL DEFAULT 0,

                margin_score REAL DEFAULT 0,

                debt_score REAL DEFAULT 0,

                equity_score REAL DEFAULT 0,

                cash_flow_score REAL DEFAULT 0,

                growth_score REAL DEFAULT 0,

                total_score REAL DEFAULT 0,

                signal TEXT,

                created_at TEXT DEFAULT CURRENT_TIMESTAMP,

                UNIQUE(
                    symbol,
                    fiscal_year,
                    fiscal_period
                )

            )
        """)


        # --------------------------------------------------
        # DİNAMİK PORTFÖY ANALİZ CACHE
        # --------------------------------------------------
        # Dinamik Portföyün pahalı hisse analizlerini tekrar tekrar
        # çalıştırmak yerine son üretilen analizleri saklar.
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dynamic_portfolio_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                universe TEXT NOT NULL,
                market_score REAL DEFAULT 50,
                analysis_json TEXT NOT NULL,
                analysis_time TEXT NOT NULL,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(symbol, universe)
            )
        """)

        # ==================================================
        # ŞEMA MIGRATION
        #
        # BURASI ÖNEMLİ
        #
        # CREATE TABLE IF NOT EXISTS mevcut tabloyu
        # değiştirmez.
        #
        # Eski borsa.db'de fiscal_year yoksa burada
        # otomatik olarak eklenir.
        # ==================================================

        # --------------------------------------------------
        # financial_scores
        # --------------------------------------------------

        _add_missing_columns(
            cursor,
            "financial_scores",
            {
                "analysis_date": "TEXT",
                "fiscal_year": "INTEGER",
                "fiscal_period": "TEXT",
                "revenue_score": "REAL DEFAULT 0",
                "profit_score": "REAL DEFAULT 0",
                "margin_score": "REAL DEFAULT 0",
                "debt_score": "REAL DEFAULT 0",
                "equity_score": "REAL DEFAULT 0",
                "cash_flow_score": "REAL DEFAULT 0",
                "growth_score": "REAL DEFAULT 0",
                "total_score": "REAL DEFAULT 0",
                "signal": "TEXT",
                "created_at": "TEXT DEFAULT CURRENT_TIMESTAMP",
            }
        )

        # --------------------------------------------------
        # financial_statements
        #
        # Eski bilanço tablolarında bazı kolonlar eksikse
        # yine otomatik tamamlanır.
        # --------------------------------------------------

        _add_missing_columns(
            cursor,
            "financial_statements",
            {
                "report_type": "TEXT",
                "currency": "TEXT DEFAULT 'TRY'",
                "revenue": "REAL",
                "cost_of_sales": "REAL",
                "operating_profit": "REAL",
                "depreciation_amortization": "REAL",
                "ebitda": "REAL",
                "net_profit": "REAL",
                "interest_expense": "REAL",
                "cash": "REAL",
                "short_term_financial_debt": "REAL",
                "current_portion_long_term_debt": "REAL",
                "long_term_financial_debt": "REAL",
                "trade_receivables": "REAL",
                "inventory": "REAL",
                "current_assets": "REAL",
                "current_liabilities": "REAL",
                "total_assets": "REAL",
                "equity": "REAL",
                "operating_cash_flow": "REAL",
                "source": "TEXT DEFAULT 'KAP'",
                "source_date": "TEXT",
                "created_at": "TEXT DEFAULT CURRENT_TIMESTAMP",
                "updated_at": "TEXT DEFAULT CURRENT_TIMESTAMP",
            }
        )

        conn.commit()

    finally:
        conn.close()


# ==========================================================
# VERİTABANINI BAŞLAT
# ==========================================================

create_tables()


# ==========================================================
# HİSSE EKLE
# ==========================================================

def add_stock(symbol, company="", sector=""):

    conn = get_connection()

    try:

        cursor = conn.cursor()

        symbol = str(symbol).upper().strip()

        if symbol.endswith(".IS"):
            symbol = symbol[:-3]

        cursor.execute("""
            INSERT OR IGNORE INTO stocks
            (
                symbol,
                company,
                sector
            )
            VALUES (?, ?, ?)
        """, (
            symbol,
            company,
            sector
        ))

        conn.commit()

    finally:
        conn.close()


# ==========================================================
# PORTFÖYE HİSSE EKLE
# ==========================================================

def add_portfolio(
    symbol,
    quantity,
    avg_cost,
    buy_date,
    note=""
):

    conn = get_connection()

    try:

        cursor = conn.cursor()

        symbol = str(symbol).upper().strip()

        if symbol.endswith(".IS"):
            symbol = symbol[:-3]

        cursor.execute("""
            INSERT INTO portfolio
            (
                symbol,
                quantity,
                avg_cost,
                buy_date,
                note
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            symbol,
            int(quantity),
            float(avg_cost),
            buy_date,
            note
        ))

        conn.commit()

    finally:
        conn.close()


# ==========================================================
# PORTFÖYÜ GETİR
# ==========================================================

def get_portfolio():

    conn = get_connection()

    try:

        return pd.read_sql_query(
            """
            SELECT *
            FROM portfolio
            """,
            conn
        )

    finally:
        conn.close()


# ==========================================================
# PORTFÖY HİSSESİNİ GÜNCELLE
# ==========================================================

def update_portfolio_stock(
    symbol,
    quantity,
    avg_cost
):

    conn = get_connection()

    try:

        cursor = conn.cursor()

        symbol = str(symbol).upper().strip()

        if symbol.endswith(".IS"):
            symbol = symbol[:-3]

        cursor.execute("""
            UPDATE portfolio

            SET
                quantity = ?,
                avg_cost = ?

            WHERE symbol = ?
        """, (
            int(quantity),
            float(avg_cost),
            symbol
        ))

        conn.commit()

    finally:
        conn.close()


# ==========================================================
# PORTFÖYÜ YÜKLE
# ==========================================================

def load_portfolio():

    return get_portfolio()


# ==========================================================
# BİLANÇO KAYDET
# ==========================================================

def save_financial_statement(
    symbol,
    period,
    period_end,
    report_type="",
    currency="TRY",
    revenue=None,
    cost_of_sales=None,
    operating_profit=None,
    depreciation_amortization=None,
    ebitda=None,
    net_profit=None,
    interest_expense=None,
    cash=None,
    short_term_financial_debt=None,
    current_portion_long_term_debt=None,
    long_term_financial_debt=None,
    trade_receivables=None,
    inventory=None,
    current_assets=None,
    current_liabilities=None,
    total_assets=None,
    equity=None,
    operating_cash_flow=None,
    source="KAP",
    source_date=None
):

    symbol = str(symbol).upper().strip()

    if symbol.endswith(".IS"):
        symbol = symbol[:-3]

    conn = get_connection()

    try:

        cursor = conn.cursor()

        # --------------------------------------------------
        # Aynı dönem varsa güncelle
        # --------------------------------------------------

        cursor.execute("""
            SELECT id
            FROM financial_statements
            WHERE symbol = ?
              AND period = ?
              AND period_end = ?
            LIMIT 1
        """, (
            symbol,
            str(period),
            str(period_end)
        ))

        existing = cursor.fetchone()

        if existing:

            cursor.execute("""
                UPDATE financial_statements

                SET
                    report_type = ?,
                    currency = ?,
                    revenue = ?,
                    cost_of_sales = ?,
                    operating_profit = ?,
                    depreciation_amortization = ?,
                    ebitda = ?,
                    net_profit = ?,
                    interest_expense = ?,
                    cash = ?,
                    short_term_financial_debt = ?,
                    current_portion_long_term_debt = ?,
                    long_term_financial_debt = ?,
                    trade_receivables = ?,
                    inventory = ?,
                    current_assets = ?,
                    current_liabilities = ?,
                    total_assets = ?,
                    equity = ?,
                    operating_cash_flow = ?,
                    source = ?,
                    source_date = ?,
                    updated_at = CURRENT_TIMESTAMP

                WHERE id = ?
            """, (
                report_type,
                currency,
                revenue,
                cost_of_sales,
                operating_profit,
                depreciation_amortization,
                ebitda,
                net_profit,
                interest_expense,
                cash,
                short_term_financial_debt,
                current_portion_long_term_debt,
                long_term_financial_debt,
                trade_receivables,
                inventory,
                current_assets,
                current_liabilities,
                total_assets,
                equity,
                operating_cash_flow,
                source,
                source_date,
                existing["id"]
            ))

        else:

            cursor.execute("""
                INSERT INTO financial_statements
                (
                    symbol,
                    period,
                    period_end,
                    report_type,
                    currency,
                    revenue,
                    cost_of_sales,
                    operating_profit,
                    depreciation_amortization,
                    ebitda,
                    net_profit,
                    interest_expense,
                    cash,
                    short_term_financial_debt,
                    current_portion_long_term_debt,
                    long_term_financial_debt,
                    trade_receivables,
                    inventory,
                    current_assets,
                    current_liabilities,
                    total_assets,
                    equity,
                    operating_cash_flow,
                    source,
                    source_date,
                    updated_at
                )
                VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?
                )
            """, (
                symbol,
                str(period),
                str(period_end),
                report_type,
                currency,
                revenue,
                cost_of_sales,
                operating_profit,
                depreciation_amortization,
                ebitda,
                net_profit,
                interest_expense,
                cash,
                short_term_financial_debt,
                current_portion_long_term_debt,
                long_term_financial_debt,
                trade_receivables,
                inventory,
                current_assets,
                current_liabilities,
                total_assets,
                equity,
                operating_cash_flow,
                source,
                source_date,
                datetime.now().isoformat()
            ))

        conn.commit()

    finally:
        conn.close()


# ==========================================================
# BİLANÇO VERİLERİNİ GETİR
# ==========================================================

def get_financial_statements(
    symbol=None,
    period=None
):

    conn = get_connection()

    try:

        query = """
            SELECT *
            FROM financial_statements
            WHERE 1 = 1
        """

        params = []

        if symbol:

            symbol = str(symbol).upper().strip()

            if symbol.endswith(".IS"):
                symbol = symbol[:-3]

            query += " AND symbol = ?"

            params.append(symbol)

        if period:

            query += " AND period = ?"

            params.append(str(period))

        query += """
            ORDER BY
                symbol,
                period_end DESC
        """

        return pd.read_sql_query(
            query,
            conn,
            params=params
        )

    finally:
        conn.close()


# ==========================================================
# HİSSE BİLANÇOSUNU GETİR
# ==========================================================

def get_stock_financials(
    symbol,
    period=None
):

    return get_financial_statements(
        symbol=symbol,
        period=period
    )


# ==========================================================
# BİLANÇO SKORU KAYDET
# ==========================================================

def save_financial_score(
    symbol,
    fiscal_year,
    fiscal_period,
    revenue_score=0,
    profit_score=0,
    margin_score=0,
    debt_score=0,
    equity_score=0,
    cash_flow_score=0,
    growth_score=0,
    total_score=0,
    signal=None,
    analysis_date=None
):

    symbol = str(symbol).upper().strip()

    if symbol.endswith(".IS"):
        symbol = symbol[:-3]

    # ------------------------------------------------------
    # fiscal_year güvenli hale getir
    # ------------------------------------------------------

    try:
        fiscal_year = int(fiscal_year)
    except (TypeError, ValueError):

        raise ValueError(
            f"Geçersiz fiscal_year: {fiscal_year!r}"
        )

    fiscal_period = str(
        fiscal_period
    ).strip()

    if not fiscal_period:

        raise ValueError(
            "fiscal_period boş olamaz."
        )

    if analysis_date is None:
        analysis_date = datetime.now().isoformat()

    conn = get_connection()

    try:

        cursor = conn.cursor()

        cursor.execute("""
            SELECT id
            FROM financial_scores
            WHERE symbol = ?
              AND fiscal_year = ?
              AND fiscal_period = ?
            LIMIT 1
        """, (
            symbol,
            fiscal_year,
            fiscal_period
        ))

        existing = cursor.fetchone()

        if existing:

            cursor.execute("""
                UPDATE financial_scores

                SET
                    analysis_date = ?,
                    revenue_score = ?,
                    profit_score = ?,
                    margin_score = ?,
                    debt_score = ?,
                    equity_score = ?,
                    cash_flow_score = ?,
                    growth_score = ?,
                    total_score = ?,
                    signal = ?

                WHERE id = ?
            """, (
                analysis_date,
                float(revenue_score),
                float(profit_score),
                float(margin_score),
                float(debt_score),
                float(equity_score),
                float(cash_flow_score),
                float(growth_score),
                float(total_score),
                signal,
                existing["id"]
            ))

        else:

            cursor.execute("""
                INSERT INTO financial_scores
                (
                    symbol,
                    analysis_date,
                    fiscal_year,
                    fiscal_period,
                    revenue_score,
                    profit_score,
                    margin_score,
                    debt_score,
                    equity_score,
                    cash_flow_score,
                    growth_score,
                    total_score,
                    signal
                )
                VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
            """, (
                symbol,
                analysis_date,
                fiscal_year,
                fiscal_period,
                float(revenue_score),
                float(profit_score),
                float(margin_score),
                float(debt_score),
                float(equity_score),
                float(cash_flow_score),
                float(growth_score),
                float(total_score),
                signal
            ))

        conn.commit()

    finally:
        conn.close()


# ==========================================================
# BİLANÇO SKORLARINI GETİR
# ==========================================================

def get_financial_scores(symbol=None):

    conn = get_connection()

    try:

        if symbol:

            symbol = str(symbol).upper().strip()

            if symbol.endswith(".IS"):
                symbol = symbol[:-3]

            return pd.read_sql_query(
                """
                SELECT *
                FROM financial_scores
                WHERE symbol = ?
                ORDER BY
                    fiscal_year DESC,
                    fiscal_period DESC
                """,
                conn,
                params=(symbol,)
            )

        return pd.read_sql_query(
            """
            SELECT *
            FROM financial_scores
            ORDER BY
                fiscal_year DESC,
                fiscal_period DESC,
                symbol
            """,
            conn
        )

    finally:
        conn.close()




# ==========================================================
# DİNAMİK PORTFÖY CACHE
# ==========================================================

def save_dynamic_portfolio_cache(
    symbol,
    universe,
    analysis,
    market_score=50.0,
    analysis_time=None
):
    """Dinamik Portföy hisse analizini SQLite cache'e kaydeder."""
    import json

    symbol = str(symbol).upper().strip()
    if symbol.endswith(".IS"):
        symbol = symbol[:-3]

    universe = str(universe).strip()
    if not symbol or not universe or not isinstance(analysis, dict):
        return False

    if analysis_time is None:
        analysis_time = datetime.now().isoformat()

    conn = get_connection()

    try:
        conn.execute(
            """
            INSERT INTO dynamic_portfolio_cache (
                symbol,
                universe,
                market_score,
                analysis_json,
                analysis_time,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(symbol, universe)
            DO UPDATE SET
                market_score = excluded.market_score,
                analysis_json = excluded.analysis_json,
                analysis_time = excluded.analysis_time,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                symbol,
                universe,
                float(market_score),
                json.dumps(
                    analysis,
                    ensure_ascii=False,
                    default=str
                ),
                str(analysis_time)
            )
        )
        conn.commit()
        return True
    except Exception as error:
        conn.rollback()
        print(
            f"❌ DİNAMİK PORTFÖY CACHE KAYIT HATASI: "
            f"{type(error).__name__}: {error}"
        )
        return False
    finally:
        conn.close()


def get_dynamic_portfolio_cache(
    symbol,
    universe,
    max_age_minutes=30
):
    """30 dakikadan eski değilse cache'deki hisse analizini döndürür."""
    import json

    symbol = str(symbol).upper().strip()
    if symbol.endswith(".IS"):
        symbol = symbol[:-3]

    universe = str(universe).strip()

    conn = get_connection()

    try:
        row = conn.execute(
            """
            SELECT
                analysis_json,
                analysis_time,
                market_score,
                updated_at
            FROM dynamic_portfolio_cache
            WHERE symbol = ?
              AND universe = ?
            LIMIT 1
            """,
            (symbol, universe)
        ).fetchone()

        if row is None:
            return None

        try:
            cached_time = datetime.fromisoformat(
                str(row["analysis_time"])
            )
        except (TypeError, ValueError):
            return None

        age_seconds = (
            datetime.now() - cached_time
        ).total_seconds()

        if age_seconds < 0:
            # Sistem saati değişmişse cache'i güvenilir kabul etme.
            return None

        if age_seconds > max_age_minutes * 60:
            return None

        data = json.loads(row["analysis_json"])

        if not isinstance(data, dict):
            return None

        data["_cache_time"] = row["analysis_time"]
        data["_cache_age_minutes"] = round(
            age_seconds / 60,
            1
        )
        data["_cache_market_score"] = float(
            row["market_score"] or 50
        )

        return data

    except Exception as error:
        print(
            f"⚠️ DİNAMİK PORTFÖY CACHE OKUMA HATASI: "
            f"{type(error).__name__}: {error}"
        )
        return None
    finally:
        conn.close()


def get_dynamic_portfolio_cache_stats(universe=None):
    """Dinamik Portföy cache durumunu özetler."""
    conn = get_connection()

    try:
        if universe:
            row = conn.execute(
                """
                SELECT
                    COUNT(*) AS total,
                    MAX(updated_at) AS last_update
                FROM dynamic_portfolio_cache
                WHERE universe = ?
                """,
                (str(universe),)
            ).fetchone()
        else:
            row = conn.execute(
                """
                SELECT
                    COUNT(*) AS total,
                    MAX(updated_at) AS last_update
                FROM dynamic_portfolio_cache
                """
            ).fetchone()

        return {
            "total": int(row["total"] or 0),
            "last_update": row["last_update"]
        }

    finally:
        conn.close()

# ==========================================================
# VERİTABANI DURUMU
# ==========================================================

def get_database_stats():

    conn = get_connection()

    try:

        cursor = conn.cursor()

        tables = [
            "stocks",
            "portfolio",
            "transactions",
            "financial_statements",
            "financial_scores"
        ]

        result = {}

        for table in tables:

            try:

                cursor.execute(
                    f"SELECT COUNT(*) FROM {table}"
                )

                result[table] = cursor.fetchone()[0]

            except sqlite3.OperationalError:

                result[table] = 0

        return result

    finally:
        conn.close()
