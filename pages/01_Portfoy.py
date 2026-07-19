import streamlit as st
import sqlite3
import pandas as pd
import yfinance as yf
import plotly.express as px
from datetime import date
from modules.portfolio.stock_ai_signal import show_stock_ai_signal


st.set_page_config(
    page_title="BIST AI PRO - Portföy",
    page_icon="💼",
    layout="wide"
)


DB_PATH = "borsa.db"


def get_connection():

    return sqlite3.connect(DB_PATH)



# --------------------------------------------------
# CSS
# --------------------------------------------------

st.markdown(
"""
<style>

.block-container{
    padding-top:2rem;
}


.portfolio-card{

    background:white;
    padding:18px;
    border-radius:12px;
    border:1px solid #e5e7eb;

}


</style>
""",
unsafe_allow_html=True
)



# --------------------------------------------------
# BAŞLIK
# --------------------------------------------------

st.title("💼 Portföy Yönetim Merkezi")

st.caption(
    "BIST AI PRO - Akıllı Portföy Takip ve Performans Analizi"
)



st.divider()



# --------------------------------------------------
# PORTFÖY EKLEME
# --------------------------------------------------

st.subheader("➕ Yeni Hisse Ekle")


col1,col2,col3,col4 = st.columns(4)



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



        conn.commit()

        conn.close()


        st.success(
            f"{symbol.upper()} eklendi"
        )

        st.rerun()



    else:

        st.warning(
            "Hisse kodu giriniz."
        )
# --------------------------------------------------
# PORTFÖY GÖSTERİM
# --------------------------------------------------

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



    df["Güncel Fiyat"] = fiyatlar



    df["Maliyet"] = (
        df["lot"] *
        df["cost"]
    )


    df["Güncel Değer"] = (
        df["lot"] *
        df["Güncel Fiyat"]
    )


    df["Kar/Zarar"] = (
        df["Güncel Değer"]
        -
        df["Maliyet"]
    )


    df["Getiri %"] = (
        df["Kar/Zarar"]
        /
        df["Maliyet"]
        *
        100
    ).round(2)



    tablo = df[
        [
            "symbol",
            "lot",
            "cost",
            "Güncel Fiyat",
            "Maliyet",
            "Güncel Değer",
            "Kar/Zarar",
            "Getiri %"
        ]
    ]



    tablo.columns = [

        "Hisse",
        "Lot",
        "Maliyet",
        "Fiyat",
        "Maliyet TL",
        "Değer TL",
        "K/Z",
        "Getiri %"

    ]



    st.dataframe(

        tablo.style.format(

            {

            "Maliyet":"{:.2f}",
            "Fiyat":"{:.2f}",
            "Maliyet TL":"{:,.2f}",
            "Değer TL":"{:,.2f}",
            "K/Z":"{:,.2f}",
            "Getiri %":"{:.2f}"

            }

        ),

        use_container_width=True

    )



    st.divider()



    # --------------------------------------------------
    # ÖZET KARTLARI
    # --------------------------------------------------


    toplam_maliyet = df["Maliyet"].sum()

    toplam_deger = df["Güncel Değer"].sum()

    toplam_kar = (
        toplam_deger -
        toplam_maliyet
    )


    getiri = (
        toplam_kar /
        toplam_maliyet *
        100
    )



    c1,c2,c3,c4 = st.columns(4)



    c1.metric(
        "💰 Toplam Maliyet",
        f"{toplam_maliyet:,.0f} TL"
    )


    c2.metric(
        "📈 Güncel Değer",
        f"{toplam_deger:,.0f} TL"
    )


    c3.metric(
        "🟢 Toplam K/Z",
        f"{toplam_kar:,.0f} TL"
    )


    c4.metric(
        "📊 Getiri",
        f"%{getiri:.2f}"
    )



    st.divider()



    # --------------------------------------------------
    # PORTFÖY DAĞILIMI
    # --------------------------------------------------


    st.subheader("📊 Portföy Dağılımı")


    fig = px.pie(

        df,

        values="Güncel Değer",

        names="symbol",

        hole=0.45,

        title="Hisse Ağırlıkları"

    )


    st.plotly_chart(

        fig,

        use_container_width=True

    )



    st.divider()



    # --------------------------------------------------
    # AI YORUM
    # --------------------------------------------------

    show_stock_ai_signal(df)
    
    st.subheader("🤖 AI Portföy Yorumu")


    if getiri > 10:

        st.success(
            """
            🟢 Portföy performansı güçlü.

            Kâr alan hisselerde kademeli koruma
            stratejisi değerlendirilebilir.
            """
        )


    elif getiri > 0:

        st.info(
            """
            🟡 Portföy pozitif bölgede.

            Sektör dağılımı ve risk dengesi takip edilmeli.
            """
        )


    else:

        st.warning(
            """
            🔴 Portföy negatif bölgede.

            Destek seviyeleri ve pozisyon ağırlıkları
            yeniden değerlendirilmeli.
            """
        )