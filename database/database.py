import sqlite3


DB_NAME = "borsa.db"


def get_connection():
    return sqlite3.connect(DB_NAME)


def create_tables():

    conn = get_connection()
    cursor = conn.cursor()


    # Hisse fiyatları
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS stock_prices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT NOT NULL,
        price REAL,
        volume INTEGER,
        date TEXT
    )
    """)


    # Portföy
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS portfolio (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT NOT NULL,
        lot INTEGER,
        cost REAL,
        buy_date TEXT
    )
    """)


    # Alım satım geçmişi
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT,
        action TEXT,
        lot INTEGER,
        price REAL,
        date TEXT
    )
    """)


    # Teknik analiz sonuçları
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS technical_analysis (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT,
        rsi REAL,
        macd REAL,
        trend TEXT,
        support REAL,
        resistance REAL,
        date TEXT
    )
    """)


    # Temel analiz
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS fundamentals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT,
        fk REAL,
        pd_dd REAL,
        dividend REAL,
        profit_growth REAL,
        date TEXT
    )
    """)


    conn.commit()
    conn.close()