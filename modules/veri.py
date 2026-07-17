import yfinance as yf
import pandas as pd


# =====================================
# TEK HİSSE VERİSİ
# =====================================

def veri_getir(symbol, period="1y"):

    try:

        ticker = yf.Ticker(symbol + ".IS")

        df = ticker.history(period=period)

        if df.empty:
            return None

        return df

    except Exception:

        return None


# =====================================
# ÇOKLU HİSSE VERİSİ
# =====================================

def coklu_veri_getir(liste, period="1y"):

    veriler = {}

    for hisse in liste:

        df = veri_getir(hisse, period)

        if df is not None:

            veriler[hisse] = df

    return veriler