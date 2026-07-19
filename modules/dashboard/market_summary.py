import streamlit as st
from modules.data.macro_data import get_macro_data


def show_market_summary():

    st.markdown("### 📊 Piyasa Özeti")
    macro = get_macro_data()

    markets = [

    ("💵 USD/TL", macro["usd"], ""),
    ("🌕 Ons Altın", macro["gold"], ""),
    ("🥈 Gümüş", macro["silver"], ""),
    ("🛢 Brent", macro["brent"], ""),

]


    cols = st.columns(len(markets))


    for i, item in enumerate(markets):

        with cols[i]:

            st.metric(
                label=item[0],
                value=item[1],
                delta=item[2]
            )


    st.caption(
        "Piyasa özeti; endeks, döviz, emtia ve küresel piyasa göstergelerini içerir."
    )