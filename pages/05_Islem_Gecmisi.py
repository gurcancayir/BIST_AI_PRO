import streamlit as st
import sqlite3
import pandas as pd


st.set_page_config(
    page_title="İşlem Geçmişi",
    page_icon="💰",
    layout="wide"
)


DB_PATH = "borsa.db"


def get_connection():
    return sqlite3.connect(DB_PATH)



st.title("💰 İşlem Geçmişi Merkezi")


# ==================================
# VERİ ÇEK
# ==================================

conn = get_connection()


df = pd.read_sql_query(
    """
    SELECT *
    FROM transactions
    ORDER BY id DESC
    """,
    conn
)


conn.close()



if df.empty:

    st.info(
        "Henüz işlem kaydı bulunmuyor."
    )

    st.stop()



# ==================================
# HESAPLAMALAR
# ==================================

df["tutar"] = (
    df["lot"]
    *
    df["price"]
)



# ==================================
# FİLTRE
# ==================================

st.subheader("🔎 Filtre")


secim = st.selectbox(
    "İşlem Türü",
    [
        "Tümü",
        "ALIS",
        "SATIS"
    ]
)


if secim != "Tümü":

    tablo = df[
        df["action"] == secim
    ]

else:

    tablo = df



# ==================================
# ÖZET
# ==================================

toplam_alis = df[
    df["action"]=="ALIS"
]["tutar"].sum()


toplam_satis = df[
    df["action"]=="SATIS"
]["tutar"].sum()


net_hareket = toplam_satis - toplam_alis



c1, c2, c3 = st.columns(3)


c1.metric(
    "📥 Toplam Alış",
    f"{toplam_alis:,.2f} TL"
)


c2.metric(
    "📤 Toplam Satış",
    f"{toplam_satis:,.2f} TL"
)


c3.metric(
    "💵 Net Nakit",
    f"{net_hareket:,.2f} TL"
)



st.divider()



# ==================================
# TABLO
# ==================================

st.subheader("📋 İşlem Listesi")


st.dataframe(
    tablo[
        [
            "date",
            "symbol",
            "action",
            "lot",
            "price",
            "tutar"
        ]
    ].style.format(
        {
            "price":"{:,.2f}",
            "tutar":"{:,.2f}"
        }
    ),
    use_container_width=True
)