import streamlit as st
from modules.data.macro_data import get_macro_data


def show_market_summary():

    st.markdown("### 📊 Piyasa Özeti")
    macro = get_macro_data()
   
    markets = [

    ("💵 USD/TL", macro["usd"], f'{macro["usd_change"]}%'),

    ("💶 EUR/TL", macro["eur"], f'{macro["eur_change"]}%'),

    ("🥇 Gram Altın", macro["gram"], ""),

    ("🌕 Ons Altın", macro["gold"], f'{macro["gold_change"]}%'),

    ("🥈 Gümüş", macro["silver"], f'{macro["silver_change"]}%'),

    ("🛢 Brent", macro["brent"], f'{macro["brent_change"]}%'),
    
    ("📈 BIST100", macro["bist"], f'{macro["bist_change"]}%'),

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