import streamlit as st


def show_market_summary():

    st.subheader("📊 Piyasa Özeti")

    c1, c2, c3, c4, c5, c6 = st.columns(6)

    market_data = [
        ("BIST100", "10.521", "+1.24%"),
        ("USD", "40.18", "+0.25%"),
        ("EURO", "47.04", "+0.15%"),
        ("GRAM ALTIN", "4.365", "+0.82%"),
        ("ONS", "3335", "+0.52%"),
        ("PETROL", "69.80", "-0.42%"),
    ]

    columns = [c1, c2, c3, c4, c5, c6]

    for col, (title, value, delta) in zip(columns, market_data):
        col.metric(
            label=title,
            value=value,
            delta=delta
        )

    st.divider()