import streamlit as st


def show_market_summary():

    st.markdown("### 📊 Piyasa Özeti")


    markets = [

        ("📈 BIST100", "10.521", "+1.24%"),
        ("💵 USD/TL", "40.18", "+0.25%"),
        ("💶 EUR/TL", "47.04", "+0.15%"),
        ("🥇 Gram Altın", "4.365", "+0.82%"),
        ("🌕 Ons Altın", "3.335", "+0.52%"),
        ("🛢 Petrol", "69.80", "-0.42%"),

    ]


    cols = st.columns(6)


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