import plotly.express as px
import yfinance as yf
import streamlit as st
import sqlite3
import pandas as pd
from datetime import date


st.set_page_config(
    page_title="Portföy Takip",
    page_icon="📊",
    layout="wide"
)


DB_PATH = "borsa.db"


def get_connection():
    return sqlite3.connect(DB_PATH)


# ===============================
# BAŞLIK
# ===============================

st.title("📊 Portföy Takip Merkezi")


# ===============================
# PORTFÖY EKLEME
# ===============================

st.subheader("➕ Yeni Hisse Ekle")


col1, col2, col3, col4 = st.columns(4)


with col1:
    symbol = st.text_input(
        "Hisse Kodu",
        placeholder="Örn: BIMAS"
    )


with col2:
    lot = st.number_input(
        "Lot",
        min_value=1,
        step=1
    )


with col3:
    cost = st.number_input(
        "Alış Maliyeti",
        min_value=0.0,
        step=0.01
    )


with col4:
    buy_date = st.date_input(
        "Alış Tarihi",
        value=date.today()
    )


if st.button("💾 Portföye Ekle"):

    if symbol:

        conn = get_connection()
        cursor = conn.cursor()


        cursor.execute(
            """
            SELECT lot, cost
            FROM portfolio
            WHERE symbol=?
            """,
            (symbol.upper(),)
        )


        mevcut = cursor.fetchone()


        if mevcut:

            eski_lot = mevcut[0]
            eski_cost = mevcut[1]


            toplam_lot = eski_lot + lot


            yeni_ortalama = (
                (eski_lot * eski_cost)
                +
                (lot * cost)
            ) / toplam_lot


            cursor.execute(
                """
                UPDATE portfolio
                SET lot=?,
                    cost=?,
                    buy_date=?
                WHERE symbol=?
                """,
                (
                    toplam_lot,
                    yeni_ortalama,
                    str(buy_date),
                    symbol.upper()
                )
            )


        else:

            cursor.execute(
                """
                INSERT INTO portfolio
                (
                symbol,
                lot,
                cost,
                buy_date
                )
                VALUES (?,?,?,?)
                """,
                (
                    symbol.upper(),
                    lot,
                    cost,
                    str(buy_date)
                )
            )

            cursor.execute(
            """
            INSERT INTO transactions
            (
            symbol,
            action,
            lot,
            price,
            date,
            cost
            )
            VALUES (?,?,?,?,?,?)
            """,
            (
                symbol.upper(),
                "ALIS",
                lot,
                cost,
                str(buy_date),
                cost
            )
        )
        conn.commit()
        conn.close()


        st.success(
            f"{symbol.upper()} portföye eklendi."
        )

        st.rerun()


    else:

        st.warning(
            "Hisse kodu giriniz."
        )



# ===============================
# PORTFÖY GÖSTERİM
# ===============================

st.divider()

st.subheader("📈 Güncel Portföy")


conn = get_connection()


df = pd.read_sql_query(
    """
    SELECT *
    FROM portfolio
    ORDER BY id DESC
    """,
    conn
)


conn.close()



if df.empty:

    st.info(
        "Henüz portföy kaydı bulunmuyor."
    )


else:


    fiyatlar = []


    for hisse in df["symbol"]:

        try:

            veri = yf.Ticker(
                hisse + ".IS"
            )


            fiyat = veri.history(
                period="1d"
            )["Close"].iloc[-1]


            fiyatlar.append(
                round(float(fiyat),2)
            )


        except:

            fiyatlar.append(0)



    df["guncel_fiyat"] = fiyatlar



    df["maliyet_tl"] = (
        df["lot"]
        *
        df["cost"]
    )


    df["guncel_deger"] = (
        df["lot"]
        *
        df["guncel_fiyat"]
    )


    df["kar_zarar"] = (
        df["guncel_deger"]
        -
        df["maliyet_tl"]
    )


    df["getiri_%"] = (
        df["kar_zarar"]
        /
        df["maliyet_tl"]
        *
        100
    ).round(2)



    gosterilecek = df[
        [
            "symbol",
            "lot",
            "cost",
            "guncel_fiyat",
            "maliyet_tl",
            "guncel_deger",
            "kar_zarar",
            "getiri_%"
        ]
    ]



    st.dataframe(
        gosterilecek.style.format(
            {
                "cost":"{:.2f}",
                "guncel_fiyat":"{:.2f}",
                "maliyet_tl":"{:,.2f}",
                "guncel_deger":"{:,.2f}",
                "kar_zarar":"{:,.2f}",
                "getiri_%":"{:.2f}%"
            }
        ),
        use_container_width=True
    )



    # ===============================
    # GRAFİK
    # ===============================

    st.subheader("📊 Portföy Dağılımı")


    fig = px.pie(
        df,
        values="guncel_deger",
        names="symbol",
        title="Hisse Ağırlıkları"
    )


    st.plotly_chart(
        fig,
        use_container_width=True
    )



    # ===============================
    # ÖZET
    # ===============================

    toplam_maliyet = df["maliyet_tl"].sum()

    toplam_deger = df["guncel_deger"].sum()

    toplam_kar = toplam_deger - toplam_maliyet



    st.divider()


    c1, c2, c3 = st.columns(3)


    c1.metric(
        "Toplam Maliyet",
        f"{toplam_maliyet:,.2f} TL"
    )


    c2.metric(
        "Güncel Değer",
        f"{toplam_deger:,.2f} TL"
    )


    c3.metric(
        "Toplam K/Z",
        f"{toplam_kar:,.2f} TL"
    )