import yfinance as yf


def get_fundamental_data(symbol):

    try:

        if not symbol.endswith(".IS"):
            symbol = symbol + ".IS"

        ticker = yf.Ticker(symbol)

        info = ticker.info

        return {

            "company": info.get("longName"),

            "sector": info.get("sector"),

            "market_cap": info.get("marketCap"),

            "pe_ratio": info.get("trailingPE"),

            "pb_ratio": info.get("priceToBook"),

            "profit_margin": info.get("profitMargins"),

            "revenue_growth": info.get("revenueGrowth"),

            "roe": info.get("returnOnEquity"),

            "debt_to_equity": info.get("debtToEquity")

        }


    except Exception as e:

        print("Fundamental hata:", e)

        return {}



def calculate_fundamental_score(data):

    score = 50


    pe = data.get("pe_ratio")

    if pe:

        if 0 < pe < 15:
            score += 10

        elif pe > 40:
            score -= 10



    pb = data.get("pb_ratio")

    if pb:

        if 0 < pb < 2:
            score += 10

        elif pb > 5:
            score -= 10



    margin = data.get("profit_margin")

    if margin:

        if margin > 0.15:
            score += 10

        elif margin < 0:
            score -= 15



    growth = data.get("revenue_growth")

    if growth:

        if growth > 0.15:
            score += 10

        elif growth < 0:
            score -= 10



    roe = data.get("roe")

    if roe:

        if roe > 0.20:
            score += 10



    debt = data.get("debt_to_equity")

    if debt:

        if debt < 100:
            score += 5

        elif debt > 300:
            score -= 10



    return max(0, min(score, 100))