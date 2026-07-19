import yfinance as yf


def get_yahoo_price(symbol):

    try:

        ticker = yf.Ticker(
            symbol + ".IS"
        )


        data = ticker.history(
            period="1d"
        )


        if data.empty:

            return None


        price = data["Close"].iloc[-1]


        return round(
            float(price),
            2
        )


    except Exception:

        return None



def get_yahoo_info(symbol):

    try:

        ticker = yf.Ticker(
            symbol + ".IS"
        )


        info = ticker.info


        return {

            "symbol": symbol,

            "company":
                info.get(
                    "longName",
                    "-"
                ),

            "sector":
                info.get(
                    "sector",
                    "-"
                ),

            "market_cap":
                info.get(
                    "marketCap",
                    0
                )

        }


    except Exception:


        return {

            "symbol": symbol,

            "company":"-",

            "sector":"-",

            "market_cap":0

        }