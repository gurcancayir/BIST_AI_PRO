import streamlit as st
import pandas as pd
from database.database import get_connection
from .portfolio import show_portfolio

def show_portfolio():

    st.divider()

    st.subheader("💼 Portföy Takibi")


    conn = get_connection()

    try:

        df = pd.read_sql(
            """
            SELECT 
                symbol,
                quantity,
                avg_cost,
                current_price
            FROM portfolio
            """,
            conn
        )


    except Exception as e:

        st.error(f"Portföy verisi okunamadı: {e}")
        return


    finally:

        conn.close()



    if df.empty:

        st.info(
            "Henüz portföy kaydı bulunmuyor."
        )

        return



    # TL hesaplamaları

    df["market_value"] = (
        df["quantity"] *
        df["current_price"]
    )


    df["cost_value"] = (
        df["quantity"] *
        df["avg_cost"]
    )


    df["profit_loss"] = (
        df["market_value"]
        -
        df["cost_value"]
    )


    df["profit_percent"] = (
        (
            df["current_price"]
            -
            df["avg_cost"]
        )
        /
        df["avg_cost"]
        *
        100
    )



    # Özet kartları

    total_value = df["market_value"].sum()

    total_cost = df["cost_value"].sum()

    total_profit = (
        total_value -
        total_cost
    )


    col1, col2, col3 = st.columns(3)


    with col1:

        st.metric(
            "Portföy Değeri",
            f"{total_value:,.2f} TL"
        )


    with col2:

        st.metric(
            "Maliyet",
            f"{total_cost:,.2f} TL"
        )


    with col3:

        st.metric(
            "Kar / Zarar",
            f"{total_profit:,.2f} TL"
        )



    st.divider()



    # Tablo

    display_df = df.copy()


    display_df.columns = [
        "Hisse",
        "Lot",
        "Ortalama Maliyet",
        "Güncel Fiyat",
        "Piyasa Değeri",
        "Maliyet",
        "Kar/Zarar",
        "Kar %",
    ]



    st.dataframe(
        display_df.style.format(
            {
                "Ortalama Maliyet": "{:.2f}",
                "Güncel Fiyat": "{:.2f}",
                "Piyasa Değeri": "{:,.2f}",
                "Maliyet": "{:,.2f}",
                "Kar/Zarar": "{:,.2f}",
                "Kar %": "{:.2f}"
            }
        ),
        use_container_width=True
    )



    # Grafik

    st.subheader("📊 Hisse Dağılımı")


    chart_df = df[
        [
            "symbol",
            "market_value"
        ]
    ]


    st.bar_chart(
        chart_df.set_index("symbol")
    )