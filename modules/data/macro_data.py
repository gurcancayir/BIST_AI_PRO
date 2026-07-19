import yfinance as yf


def get_price(symbol):

    try:

        data = yf.Ticker(symbol).history(period="5d")

        last = round(data["Close"].dropna().iloc[-1], 2)

        prev = round(data["Close"].dropna().iloc[-2], 2)

        change = round(((last - prev) / prev) * 100, 2)

        return last, change

    except:

        return "-", "-"


def get_macro_data():

    bist, bist_change = get_price("XU100.IS")

    gold, gold_change = get_price("GC=F")

    usd, usd_change = get_price("USDTRY=X")

    eur, eur_change = get_price("EURTRY=X")

    brent, brent_change = get_price("BZ=F")

    silver, silver_change = get_price("SI=F")
    try:
        gram = round((gold * usd) / 31.1035, 2)
    except:
        gram = "-"        
    
    return {

        "gold": gold,
        "gold_change": gold_change,

        "usd": usd,
        "usd_change": usd_change,

        "brent": brent,
        "brent_change": brent_change,

        "silver": silver,
        "silver_change": silver_change,
        
        "eur": eur,
        
        "eur_change": eur_change,

        "gram": gram,
        "bist": bist,
        "bist_change": bist_change,

    }