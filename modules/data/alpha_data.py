import requests
import streamlit as st


def get_alpha_price(symbol):

    try:

        api_key = st.secrets["ALPHAVANTAGE_KEY"]


        url = (
    "https://www.alphavantage.co/query"
    "?function=GLOBAL_QUOTE"
    f"&symbol={symbol}"
    f"&apikey={api_key}"
)


        response = requests.get(url)

        data = response.json()
        print(data)

        price = data["Global Quote"]["05. price"]


        return round(
            float(price),
            2
        )


    except Exception:

        return None