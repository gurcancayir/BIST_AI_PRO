import streamlit as st
import sqlite3
from datetime import date


st.set_page_config(
    page_title="Alım Satım Merkezi",
    page_icon="💹",
    layout="wide"
)


DB_PATH = "borsa.db"


def get_connection():
    return sqlite3.connect(DB_PATH)



st.title("💹 Alım Satım Merkezi")


# ======================================
# İŞLEM SEÇİMİ
# ======================================

islem = st.radio(
    "İşlem Türü",
    [
        "ALIS",
        "SATIS"
    ]
)



# ======================================
# ALIŞ
# ======================================

if islem == "ALIS":

    st.subheader("📥 Yeni Alış")


    symbol = st.text_input(
        "Hisse Kodu"
    )


    lot = st.number_input(
        "Lot",
        min_value=1,
        step=1
    )


    fiyat = st.number_input(
        "Alış Fiyatı",
        min_value=0.0,
        step=0.01
    )


    tarih = st.date_input(
        "Tarih",
        value=date.today()
    )



    if st.button("Alışı Kaydet"):

        if symbol:


            conn = get_connection()
            cursor = conn.cursor()


            cursor.execute(
                """
                SELECT lot,cost
                FROM portfolio
                WHERE symbol=?
                """,
                (symbol.upper(),)
            )


            mevcut = cursor.fetchone()



            if mevcut:


                eski_lot = mevcut[0]
                eski_cost = mevcut[1]


                yeni_lot = eski_lot + lot


                yeni_cost = (
                    (eski_lot * eski_cost)
                    +
                    (lot * fiyat)
                ) / yeni_lot



                cursor.execute(
                    """
                    UPDATE portfolio
                    SET lot=?,
                    cost=?
                    WHERE symbol=?
                    """,
                    (
                        yeni_lot,
                        yeni_cost,
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
                        fiyat,
                        str(tarih)
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
                    fiyat,
                    str(tarih),
                    fiyat
                )
            )



            conn.commit()
            conn.close()


            st.success(
                "Alış kaydedildi."
            )



# ======================================
# SATIŞ
# ======================================

else:


    st.subheader("📤 Satış")


    conn = get_connection()


    hisseler = cursor = conn.cursor()

    cursor.execute(
        """
        SELECT symbol,lot,cost
        FROM portfolio
        """
    )


    liste = cursor.fetchall()


    conn.close()



    if liste:


        secim = st.selectbox(
            "Hisse",
            [
                x[0] for x in liste
            ]
        )


        bilgi = [
            x for x in liste
            if x[0] == secim
        ][0]



        mevcut_lot = bilgi[1]
        maliyet = bilgi[2]



        lot = st.number_input(
            "Satış Lot",
            min_value=1,
            max_value=int(mevcut_lot)
        )


        fiyat = st.number_input(
            "Satış Fiyatı",
            min_value=0.0,
            step=0.01
        )


        tarih = st.date_input(
            "Tarih",
            value=date.today()
        )



        if st.button("Satışı Kaydet"):


            kar = (
                fiyat - maliyet
            ) * lot



            conn = get_connection()
            cursor = conn.cursor()



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
                    secim,
                    "SATIS",
                    lot,
                    fiyat,
                    str(tarih),
                    maliyet
                )
            )



            kalan = mevcut_lot - lot



            if kalan == 0:

                cursor.execute(
                    """
                    DELETE FROM portfolio
                    WHERE symbol=?
                    """,
                    (secim,)
                )

            else:

                cursor.execute(
                    """
                    UPDATE portfolio
                    SET lot=?
                    WHERE symbol=?
                    """,
                    (
                        kalan,
                        secim
                    )
                )



            conn.commit()
            conn.close()



            st.success(
                f"Satış tamamlandı. Gerçekleşen K/Z: {kar:,.2f} TL"
            )