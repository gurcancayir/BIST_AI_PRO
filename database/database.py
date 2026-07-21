import sqlite3


DB_NAME = "borsa.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    return conn


def create_tables():

    conn = get_connection()
    cursor = conn.cursor()


    # Hisse tablosu
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


    # Portföy tablosu
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


    # İşlem geçmişi
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


    conn.commit()
    conn.close()



def add_stock(symbol, company="", sector=""):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT OR IGNORE INTO stocks
    (symbol,company,sector)

    VALUES (?,?,?)

    """,
    (
        symbol,
        company,
        sector
    ))

    conn.commit()
    conn.close()



def add_portfolio(symbol, quantity, avg_cost, buy_date, note=""):

    conn=get_connection()
    cursor=conn.cursor()

    cursor.execute("""

    INSERT INTO portfolio
    (symbol,quantity,avg_cost,buy_date,note)

    VALUES (?,?,?,?,?)

    """,
    (
        symbol,
        quantity,
        avg_cost,
        buy_date,
        note
    ))

    conn.commit()
    conn.close()



def get_portfolio():

    conn=get_connection()

    df = __import__("pandas").read_sql_query(
        """
        SELECT * FROM portfolio
        """,
        conn
    )

    conn.close()

    return df
def update_portfolio_stock(symbol, quantity, avg_cost):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    UPDATE portfolio

    SET quantity = ?,
        avg_cost = ?

    WHERE symbol = ?

    """,
    (
        quantity,
        avg_cost,
        symbol
    ))

    conn.commit()
    conn.close()
def load_portfolio():

    conn = get_connection()

    df = __import__("pandas").read_sql_query(
        """
        SELECT *
        FROM portfolio
        """,
        conn
    )

    conn.close()

    return df