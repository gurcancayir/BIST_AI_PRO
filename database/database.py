import sqlite3
from pathlib import Path
from datetime import datetime

import pandas as pd


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
# TABLOLARI OLUŞTUR
# ==========================================================

def create_tables():

    conn = get_connection()
    cursor = conn.cursor()

    # ------------------------------------------------------
    # HİSSELER
    # ------------------------------------------------------

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

    # ------------------------------------------------------
    # PORTFÖY
    # ------------------------------------------------------

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

    # ------------------------------------------------------
    # İŞLEM GEÇMİŞİ
    # ------------------------------------------------------

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

    # ------------------------------------------------------
    # BİLANÇO TABLOSU
    # ------------------------------------------------------
    #
    # Mevcut financial_statements tablosu korunur.
    # CREATE TABLE IF NOT EXISTS mevcut tabloyu değiştirmez.
    #

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

    # ------------------------------------------------------
    # BİLANÇO SKORLARI
    # ------------------------------------------------------

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

    conn.commit()
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
    cursor = conn.cursor()

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
    cursor = conn.cursor()

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
        quantity,
        avg_cost,
        buy_date,
        note
    ))

    conn.commit()
    conn.close()


# ==========================================================
# PORTFÖYÜ GETİR
# ==========================================================

def get_portfolio():

    conn = get_connection()

    df = pd.read_sql_query(
        """
        SELECT *
        FROM portfolio
        """,
        conn
    )

    conn.close()

    return df


# ==========================================================
# PORTFÖY HİSSESİNİ GÜNCELLE
# ==========================================================

def update_portfolio_stock(
    symbol,
    quantity,
    avg_cost
):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE portfolio

        SET
            quantity = ?,
            avg_cost = ?

        WHERE symbol = ?
    """, (
        quantity,
        avg_cost,
        symbol
    ))

    conn.commit()
    conn.close()


# ==========================================================
# PORTFÖYÜ YÜKLE
# ==========================================================

def load_portfolio():

    conn = get_connection()

    df = pd.read_sql_query(
        """
        SELECT *
        FROM portfolio
        """,
        conn
    )

    conn.close()

    return df


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
    cursor = conn.cursor()

    # ------------------------------------------------------
    # Aynı dönem varsa güncelle
    # ------------------------------------------------------

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
    conn.close()


# ==========================================================
# BİLANÇO VERİLERİNİ GETİR
# ==========================================================

def get_financial_statements(
    symbol=None,
    period=None
):

    conn = get_connection()

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

    df = pd.read_sql_query(
        query,
        conn,
        params=params
    )

    conn.close()

    return df


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

    if analysis_date is None:
        analysis_date = datetime.now().isoformat()

    conn = get_connection()
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
        int(fiscal_year),
        str(fiscal_period)
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
            int(fiscal_year),
            str(fiscal_period),
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
    conn.close()


# ==========================================================
# BİLANÇO SKORLARINI GETİR
# ==========================================================

def get_financial_scores(symbol=None):

    conn = get_connection()

    if symbol:

        symbol = str(symbol).upper().strip()

        if symbol.endswith(".IS"):
            symbol = symbol[:-3]

        df = pd.read_sql_query(
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

    else:

        df = pd.read_sql_query(
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

    conn.close()

    return df


# ==========================================================
# VERİTABANI DURUMU
# ==========================================================

def get_database_stats():

    conn = get_connection()
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

    conn.close()

    return result