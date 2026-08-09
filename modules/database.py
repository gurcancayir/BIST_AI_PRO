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
# VERİTABANINI OLUŞTUR
# ==========================================================

def init_database():

    conn = get_connection()

    cursor = conn.cursor()


    # ------------------------------------------------------
    # HİSSELER
    # ------------------------------------------------------

    cursor.execute("""
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
    """)


    # ------------------------------------------------------
    # İŞLEMLER
    # ------------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            symbol TEXT NOT NULL,

            transaction_date TEXT,

            transaction_type TEXT,

            quantity REAL DEFAULT 0,

            price REAL DEFAULT 0,

            total REAL DEFAULT 0,

            commission REAL DEFAULT 0,

            average_cost REAL DEFAULT 0,

            profit_loss REAL DEFAULT 0,

            net_profit_loss REAL DEFAULT 0,

            cumulative_profit_loss REAL DEFAULT 0,

            created_at TEXT DEFAULT CURRENT_TIMESTAMP

        )
    """)


    # ------------------------------------------------------
    # FİYATLAR
    # ------------------------------------------------------

    cursor.execute("""
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
    """)


    # ------------------------------------------------------
    # TEKNİK ANALİZ
    # ------------------------------------------------------

    cursor.execute("""
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
    """)


    # ------------------------------------------------------
    # TEMEL ANALİZ
    # ------------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS fundamentals (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            symbol TEXT NOT NULL,

            analysis_date TEXT,

            pe_ratio REAL,

            pb_ratio REAL,

            market_cap REAL,

            profit_margin REAL,

            revenue REAL,

            debt_equity REAL,

            dividend_yield REAL,

            created_at TEXT DEFAULT CURRENT_TIMESTAMP,

            UNIQUE(symbol, analysis_date)

        )
    """)


    # ======================================================
    # MERKEZİ BİLANÇO / FİNANSAL TABLOLAR
    # ======================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS financial_statements (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            symbol TEXT NOT NULL,

            fiscal_year INTEGER NOT NULL,

            fiscal_period TEXT NOT NULL,

            statement_date TEXT,

            report_date TEXT,

            source TEXT DEFAULT 'KAP',

            document_name TEXT,

            currency TEXT DEFAULT 'TRY',

            statement_type TEXT,

            item_code TEXT,

            item_name TEXT NOT NULL,

            value REAL,

            previous_value REAL,

            change_amount REAL,

            change_percent REAL,

            created_at TEXT DEFAULT CURRENT_TIMESTAMP,

            UNIQUE(
                symbol,
                fiscal_year,
                fiscal_period,
                statement_type,
                item_code
            )

        )
    """)


    # ======================================================
    # BİLANÇO SKORLARI
    # ======================================================

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


    # ======================================================
    # BİLANÇO İÇİN İNDEKSLER
    # ======================================================

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_financial_symbol_period

        ON financial_statements (
            symbol,
            fiscal_year,
            fiscal_period
        )
    """)


    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_financial_item

        ON financial_statements (
            symbol,
            item_code
        )
    """)


    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_financial_scores_symbol

        ON financial_scores (
            symbol,
            fiscal_year,
            fiscal_period
        )
    """)


    conn.commit()

    conn.close()


# ==========================================================
# VERİTABANINI BAŞLAT
# ==========================================================

init_database()


# ==========================================================
# HİSSE EKLE / GÜNCELLE
# ==========================================================

def save_stock(
    symbol,
    company=None,
    sector=None,
    industry=None,
    market_cap=None,
    currency="TRY"
):

    symbol = str(symbol).upper().strip()

    if not symbol.endswith(".IS"):
        symbol = symbol + ".IS"


    conn = get_connection()

    cursor = conn.cursor()


    cursor.execute("""
        INSERT INTO stocks (

            symbol,
            company,
            sector,
            industry,
            market_cap,
            currency,
            updated_at

        )

        VALUES (?, ?, ?, ?, ?, ?, ?)

        ON CONFLICT(symbol)

        DO UPDATE SET

            company = excluded.company,

            sector = excluded.sector,

            industry = excluded.industry,

            market_cap = excluded.market_cap,

            currency = excluded.currency,

            updated_at = excluded.updated_at
    """, (

        symbol,
        company,
        sector,
        industry,
        market_cap,
        currency,
        datetime.now().isoformat()

    ))


    conn.commit()

    conn.close()


# ==========================================================
# İŞLEM KAYDET
# ==========================================================

def save_transaction(
    symbol,
    transaction_date,
    transaction_type,
    quantity,
    price,
    total=None,
    commission=0,
    average_cost=0,
    profit_loss=0,
    net_profit_loss=0,
    cumulative_profit_loss=0
):

    symbol = str(symbol).upper().strip()

    if not symbol.endswith(".IS"):
        symbol = symbol + ".IS"


    if total is None:
        total = float(quantity) * float(price)


    conn = get_connection()

    cursor = conn.cursor()


    cursor.execute("""
        INSERT INTO transactions (

            symbol,

            transaction_date,

            transaction_type,

            quantity,

            price,

            total,

            commission,

            average_cost,

            profit_loss,

            net_profit_loss,

            cumulative_profit_loss

        )

        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)

    """, (

        symbol,

        str(transaction_date),

        str(transaction_type),

        float(quantity),

        float(price),

        float(total),

        float(commission),

        float(average_cost),

        float(profit_loss),

        float(net_profit_loss),

        float(cumulative_profit_loss)

    ))


    conn.commit()

    conn.close()


# ==========================================================
# EXCEL'DEN İŞLEM AKTAR
# ==========================================================

def import_transactions_from_excel(excel_file):

    excel = pd.ExcelFile(excel_file)

    imported = 0
    skipped = 0

    conn = get_connection()

    cursor = conn.cursor()


    for sheet in excel.sheet_names:

        df = pd.read_excel(
            excel_file,
            sheet_name=sheet
        )


        if df.empty:
            continue


        symbol = str(sheet).upper().strip()

        if symbol.endswith(".IS"):
            symbol = symbol[:-3]


        # ----------------------------------------------
        # HİSSEYİ KAYDET
        # ----------------------------------------------

        save_stock(symbol)


        # ----------------------------------------------
        # SÜTUN KONTROLÜ
        # ----------------------------------------------

        required_columns = [
            "Tarih",
            "İşlem",
            "Adet",
            "Fiyat"
        ]


        missing = [
            col
            for col in required_columns
            if col not in df.columns
        ]


        if missing:
            continue


        # ----------------------------------------------
        # İŞLEMLERİ KAYDET
        # ----------------------------------------------

        for _, row in df.iterrows():

            try:

                tarih = row.get(
                    "Tarih",
                    ""
                )

                islem = row.get(
                    "İşlem",
                    ""
                )

                adet = row.get(
                    "Adet",
                    0
                )

                fiyat = row.get(
                    "Fiyat",
                    0
                )

                toplam = row.get(
                    "Toplam",
                    None
                )

                komisyon = row.get(
                    "Komisyon",
                    0
                )

                ortalama = row.get(
                    "Ortalama Alış",
                    0
                )

                kz = row.get(
                    "K/Z",
                    0
                )

                net_kz = row.get(
                    "Net K/Z",
                    0
                )

                kumulatif_kz = row.get(
                    "Kümülatif K/Z",
                    0
                )


                # --------------------------------------
                # BOŞ SATIRLARI ATLA
                # --------------------------------------

                if pd.isna(islem):

                    skipped += 1

                    continue


                islem = str(islem).strip()


                if islem == "":

                    skipped += 1

                    continue


                # --------------------------------------
                # SAYISAL TEMİZLİK
                # --------------------------------------

                def clean_number(value):

                    if pd.isna(value):
                        return 0

                    try:
                        return float(value)

                    except Exception:
                        return 0


                adet = clean_number(adet)

                fiyat = clean_number(fiyat)

                komisyon = clean_number(komisyon)

                ortalama = clean_number(ortalama)

                kz = clean_number(kz)

                net_kz = clean_number(net_kz)

                kumulatif_kz = clean_number(
                    kumulatif_kz
                )


                # --------------------------------------
                # 0 ADET İŞLEMİ ATLA
                # --------------------------------------

                if adet <= 0:

                    skipped += 1

                    continue


                # --------------------------------------
                # TOPLAM
                # --------------------------------------

                if pd.isna(toplam):

                    toplam = adet * fiyat

                else:

                    toplam = clean_number(
                        toplam
                    )


                # --------------------------------------
                # TARİH
                # --------------------------------------

                if pd.isna(tarih):

                    skipped += 1

                    continue


                tarih = str(tarih)


                # --------------------------------------
                # MÜKERRER KAYIT KONTROLÜ
                # --------------------------------------

                cursor.execute(
                    """
                    SELECT id

                    FROM transactions

                    WHERE
                        symbol = ?
                        AND transaction_date = ?
                        AND transaction_type = ?
                        AND quantity = ?
                        AND price = ?

                    LIMIT 1
                    """,
                    (
                        symbol + ".IS",
                        tarih,
                        islem,
                        adet,
                        fiyat
                    )
                )


                existing = cursor.fetchone()


                if existing:

                    skipped += 1

                    continue


                # --------------------------------------
                # KAYDET
                # --------------------------------------

                save_transaction(

                    symbol=symbol,

                    transaction_date=tarih,

                    transaction_type=islem,

                    quantity=adet,

                    price=fiyat,

                    total=toplam,

                    commission=komisyon,

                    average_cost=ortalama,

                    profit_loss=kz,

                    net_profit_loss=net_kz,

                    cumulative_profit_loss=kumulatif_kz

                )


                imported += 1


            except Exception:

                skipped += 1

                continue


    conn.close()


    return imported


# ==========================================================
# BİLANÇO KAYDET
# ==========================================================

def save_financial_statement(
    symbol,
    fiscal_year,
    fiscal_period,
    statement_type,
    item_name,
    value,
    statement_date=None,
    report_date=None,
    source="KAP",
    document_name=None,
    currency="TRY",
    item_code=None,
    previous_value=None
):

    symbol = str(symbol).upper().strip()


    if not symbol.endswith(".IS"):

        symbol = symbol + ".IS"


    # ------------------------------------------------------
    # DEĞİŞİM HESABI
    # ------------------------------------------------------

    change_amount = None
    change_percent = None


    if (
        value is not None
        and previous_value is not None
    ):

        try:

            change_amount = (
                float(value)
                -
                float(previous_value)
            )


            if float(previous_value) != 0:

                change_percent = (
                    (
                        float(value)
                        -
                        float(previous_value)
                    )
                    /
                    abs(float(previous_value))
                ) * 100

        except Exception:

            change_amount = None
            change_percent = None


    conn = get_connection()

    cursor = conn.cursor()


    cursor.execute("""
        INSERT INTO financial_statements (

            symbol,

            fiscal_year,

            fiscal_period,

            statement_date,

            report_date,

            source,

            document_name,

            currency,

            statement_type,

            item_code,

            item_name,

            value,

            previous_value,

            change_amount,

            change_percent

        )

        VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
        )

        ON CONFLICT(
            symbol,
            fiscal_year,
            fiscal_period,
            statement_type,
            item_code
        )

        DO UPDATE SET

            statement_date = excluded.statement_date,

            report_date = excluded.report_date,

            source = excluded.source,

            document_name = excluded.document_name,

            currency = excluded.currency,

            item_name = excluded.item_name,

            value = excluded.value,

            previous_value = excluded.previous_value,

            change_amount = excluded.change_amount,

            change_percent = excluded.change_percent

    """, (

        symbol,

        int(fiscal_year),

        str(fiscal_period),

        statement_date,

        report_date,

        source,

        document_name,

        currency,

        statement_type,

        item_code,

        item_name,

        value,

        previous_value,

        change_amount,

        change_percent

    ))


    conn.commit()

    conn.close()


# ==========================================================
# BİLANÇO VERİLERİNİ GETİR
# ==========================================================

def get_financial_statements(
    symbol=None,
    fiscal_year=None,
    fiscal_period=None
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

        if not symbol.endswith(".IS"):

            symbol = symbol + ".IS"

        query += " AND symbol = ?"

        params.append(symbol)


    if fiscal_year is not None:

        query += " AND fiscal_year = ?"

        params.append(int(fiscal_year))


    if fiscal_period is not None:

        query += " AND fiscal_period = ?"

        params.append(str(fiscal_period))


    query += """
        ORDER BY
            symbol,
            statement_type,
            item_name
    """


    df = pd.read_sql_query(
        query,
        conn,
        params=params
    )


    conn.close()


    return df


# ==========================================================
# BELİRLİ HİSSEDEN BİLANÇO GETİR
# ==========================================================

def get_stock_financials(
    symbol,
    fiscal_year=None,
    fiscal_period=None
):

    return get_financial_statements(
        symbol=symbol,
        fiscal_year=fiscal_year,
        fiscal_period=fiscal_period
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


    if not symbol.endswith(".IS"):

        symbol = symbol + ".IS"


    if analysis_date is None:

        analysis_date = datetime.now().isoformat()


    conn = get_connection()

    cursor = conn.cursor()


    cursor.execute("""
        INSERT INTO financial_scores (

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

        ON CONFLICT(
            symbol,
            fiscal_year,
            fiscal_period
        )

        DO UPDATE SET

            analysis_date = excluded.analysis_date,

            revenue_score = excluded.revenue_score,

            profit_score = excluded.profit_score,

            margin_score = excluded.margin_score,

            debt_score = excluded.debt_score,

            equity_score = excluded.equity_score,

            cash_flow_score = excluded.cash_flow_score,

            growth_score = excluded.growth_score,

            total_score = excluded.total_score,

            signal = excluded.signal

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

def get_financial_scores(
    symbol=None
):

    conn = get_connection()


    if symbol:

        symbol = str(symbol).upper().strip()

        if not symbol.endswith(".IS"):

            symbol = symbol + ".IS"


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
# TÜM İŞLEMLERİ GETİR
# ==========================================================

def get_transactions():

    conn = get_connection()


    df = pd.read_sql_query(
        """
        SELECT *

        FROM transactions

        ORDER BY
            transaction_date ASC,
            id ASC
        """,

        conn
    )


    conn.close()


    return df


# ==========================================================
# HİSSELERİ GETİR
# ==========================================================

def get_stocks():

    conn = get_connection()


    df = pd.read_sql_query(
        """
        SELECT *

        FROM stocks

        ORDER BY symbol
        """,

        conn
    )


    conn.close()


    return df


# ==========================================================
# HİSSE İŞLEMLERİNİ GETİR
# ==========================================================

def get_stock_transactions(symbol):

    symbol = str(symbol).upper().strip()


    if not symbol.endswith(".IS"):

        symbol = symbol + ".IS"


    conn = get_connection()


    df = pd.read_sql_query(
        """
        SELECT *

        FROM transactions

        WHERE symbol = ?

        ORDER BY
            transaction_date ASC,
            id ASC
        """,

        conn,

        params=(symbol,)

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

        "transactions",

        "stock_prices",

        "technical_analysis",

        "fundamentals",

        "financial_statements",

        "financial_scores"

    ]


    result = {}


    for table in tables:

        cursor.execute(
            f"SELECT COUNT(*) FROM {table}"
        )


        result[table] = cursor.fetchone()[0]


    conn.close()


    return result