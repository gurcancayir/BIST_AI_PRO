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

    excel = pd.ExcelFile(
        excel_file
    )

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
        # Hisseyi kaydet
        # ----------------------------------------------

        save_stock(
            symbol
        )

        # ----------------------------------------------
        # Sütun kontrolü
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
        # İşlemleri kaydet
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

                    toplam = (
                        adet * fiyat
                    )

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

        "fundamentals"

    ]


    result = {}


    for table in tables:


        cursor.execute(
            f"SELECT COUNT(*) FROM {table}"
        )


        result[table] = cursor.fetchone()[0]


    conn.close()


    return result