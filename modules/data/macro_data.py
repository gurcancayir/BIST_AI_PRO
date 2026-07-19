import yfinance as yf


def get_macro_data():

    try:
        gold = round(
            yf.Ticker("GC=F").history(period="5d")["Close"].iloc[-1],
            2
        )
    except:
        gold = "-"

    try:
        usdtry = round(
            yf.Ticker("USDTRY=X").history(period="5d")["Close"].iloc[-1],
            2
        )
    except:
        usdtry = "-"

    try:
        brent = round(
            yf.Ticker("BZ=F").history(period="5d")["Close"].iloc[-1],
            2
        )
    except:
        brent = "-"

    try:
        silver = round(
            yf.Ticker("SI=F").history(period="5d")["Close"].iloc[-1],
            2
        )
    except:
        silver = "-"

    return {

        "gold": gold,

        "usd": usdtry,

        "brent": brent,

        "silver": silver

    }