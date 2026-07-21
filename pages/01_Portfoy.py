import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px

from datetime import date

from database.database import (
    get_connection,
    update_portfolio_stock,
    load_portfolio
)

from modules.portfolio.stock_ai_signal import show_stock_ai_signal


# --------------------------------------------------
# PAGE
# --------------------------------------------------

st.set_page_config(
    page_title="BIST AI PRO - Portföy",
    page_icon="💼",
    layout="wide"
)

# --------------------------------------------------
# CSS
# --------------------------------------------------

st.markdown("""
<style>

.block-container{
    padding-top:1rem;
    padding-bottom:2rem;
}

.metric-container{
    background:#ffffff;
    border-radius:12px;
    padding:15px;
    border:1px solid #E5E7EB;
}

</style>
""", unsafe_allow_html=True)

# --------------------------------------------------
# HEADER
# --------------------------------------------------

st.title("💼 Portföy Yönetim Merkezi")

st.caption(
    "BIST AI PRO | Yapay Zeka Destekli Portföy Yönetimi"
)

st.divider()

# --------------------------------------------------
# KPI KARTLARI
# --------------------------------------------------

k1,k2,k3,k4 = st.columns(4)

with k1:
    st.metric("Portföy Değeri","--")

with k2:
    st.metric("Toplam K/Z","--")

with k3:
    st.metric("Getiri","--")

with k4:
    st.metric("Hisse Sayısı","--")

st.divider()

# --------------------------------------------------
# PORTFÖY EKLEME
# --------------------------------------------------

st.subheader("➕ Yeni Hisse Ekle")

c1,c2,c3,c4 = st.columns(4)

with c1:
    symbol = st.text_input("Hisse")

with c2:
    lot = st.number_input(
        "Lot",
        min_value=1,
        step=1
    )

with c3:
    cost = st.number_input(
        "Maliyet",
        min_value=0.0,
        step=0.01
    )

with c4:
    buy_date = st.date_input(
        "Alış Tarihi",
        value=date.today()
    )

if st.button("💾 Portföye Kaydet",use_container_width=True):

    if symbol:

        update_portfolio_stock(
            symbol,
            lot,
            cost,
            str(buy_date)
        )

        st.success(f"{symbol.upper()} portföye eklendi.")

        st.rerun()

    else:

        st.warning("Hisse kodu giriniz.")

st.divider()

# --------------------------------------------------
# BURADAN DEVAM EDECEĞİZ
# --------------------------------------------------
# --------------------------------------------------
# PORTFÖYÜ YÜKLE
# --------------------------------------------------

df = load_portfolio()

if df.empty:

    st.info("Henüz portföyde hisse bulunmuyor.")

    st.stop()


# --------------------------------------------------
# GÜNCEL FİYATLARI ÇEK
# --------------------------------------------------

prices = []

for symbol in df["symbol"]:

    try:

        ticker = yf.Ticker(symbol + ".IS")

        close = ticker.history(period="1d")["Close"].iloc[-1]

        prices.append(round(float(close), 2))

    except:

        prices.append(0.0)


df["Güncel Fiyat"] = prices


# --------------------------------------------------
# HESAPLAMALAR
# --------------------------------------------------

df["Maliyet Tutarı"] = df["lot"] * df["cost"]

df["Piyasa Değeri"] = df["lot"] * df["Güncel Fiyat"]

df["Kar/Zarar"] = (
    df["Piyasa Değeri"] -
    df["Maliyet Tutarı"]
)

df["Getiri %"] = (
    (
        df["Kar/Zarar"]
        /
        df["Maliyet Tutarı"]
    ) * 100
).round(2)


toplam_portfoy = df["Piyasa Değeri"].sum()

if toplam_portfoy > 0:

    df["Portföy %"] = (
        (
            df["Piyasa Değeri"]
            /
            toplam_portfoy
        ) * 100
    ).round(2)

else:

    df["Portföy %"] = 0


# --------------------------------------------------
# KPI GÜNCELLE
# --------------------------------------------------

toplam_maliyet = df["Maliyet Tutarı"].sum()

toplam_deger = df["Piyasa Değeri"].sum()

toplam_kar = toplam_deger - toplam_maliyet

if toplam_maliyet > 0:

    toplam_getiri = (
        toplam_kar /
        toplam_maliyet
    ) * 100

else:

    toplam_getiri = 0


k1,k2,k3,k4 = st.columns(4)

with k1:
    st.metric(
        "💰 Portföy Değeri",
        f"{toplam_deger:,.2f} TL"
    )

with k2:
    st.metric(
        "📈 Toplam K/Z",
        f"{toplam_kar:,.2f} TL"
    )

with k3:
    st.metric(
        "📊 Getiri",
        f"%{toplam_getiri:.2f}"
    )

with k4:
    st.metric(
        "🏦 Hisse Sayısı",
        len(df)
    )


st.divider()


# --------------------------------------------------
# PORTFÖY TABLOSU
# --------------------------------------------------

st.subheader("📋 Güncel Portföy")

tablo = df[
    [
        "symbol",
        "lot",
        "cost",
        "Güncel Fiyat",
        "Maliyet Tutarı",
        "Piyasa Değeri",
        "Kar/Zarar",
        "Getiri %",
        "Portföy %"
    ]
]

tablo.columns = [
    "Hisse",
    "Lot",
    "Maliyet",
    "Fiyat",
    "Maliyet TL",
    "Piyasa Değeri",
    "K/Z",
    "Getiri %",
    "Portföy %"
]

st.dataframe(
    tablo.style.format(
        {
            "Maliyet":"{:.2f}",
            "Fiyat":"{:.2f}",
            "Maliyet TL":"{:,.2f}",
            "Piyasa Değeri":"{:,.2f}",
            "K/Z":"{:,.2f}",
            "Getiri %":"{:.2f}",
            "Portföy %":"{:.2f}"
        }
    ),
    use_container_width=True
)

st.divider()


# --------------------------------------------------
# BURADAN DEVAM EDECEĞİZ
# --------------------------------------------------
# --------------------------------------------------
# PORTFÖY DAĞILIMI
# --------------------------------------------------

st.subheader("📊 Portföy Dağılımı")

col1, col2 = st.columns(2)

with col1:

    fig = px.pie(
        df,
        values="Piyasa Değeri",
        names="symbol",
        hole=0.45,
        title="Portföy Dağılımı"
    )

    fig.update_traces(textposition="inside")

    st.plotly_chart(
        fig,
        use_container_width=True
    )


with col2:

    fig = px.bar(
        df,
        x="symbol",
        y="Piyasa Değeri",
        text="Piyasa Değeri",
        title="Hisse Büyüklükleri"
    )

    fig.update_traces(
        texttemplate="%{text:,.0f}",
        textposition="outside"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )


st.divider()


# --------------------------------------------------
# KAR / ZARAR GRAFİĞİ
# --------------------------------------------------

st.subheader("📈 Kar / Zarar Analizi")

fig = px.bar(

    df,

    x="symbol",

    y="Kar/Zarar",

    color="Kar/Zarar",

    text="Kar/Zarar"

)

fig.update_traces(

    texttemplate="%{text:,.0f}",

    textposition="outside"

)

st.plotly_chart(

    fig,

    use_container_width=True

)


st.divider()


# --------------------------------------------------
# AI PORTFÖY ANALİZİ
# --------------------------------------------------

st.subheader("🤖 AI Portföy Analizi")

show_stock_ai_signal(df)

st.divider()


# --------------------------------------------------
# PORTFÖY ÖZETİ
# --------------------------------------------------

if toplam_getiri >= 15:

    st.success("""
🟢 **Portföy Değerlendirmesi**

Portföy oldukça güçlü görünüyor.

• Kâr realizasyonu değerlendirilebilir.

• Yeni alımlar için düzeltmeler beklenebilir.
""")

elif toplam_getiri >= 0:

    st.info("""
🟡 **Portföy Değerlendirmesi**

Portföy pozitif bölgede.

• Mevcut strateji korunabilir.

• Risk dengesi takip edilmeli.
""")

else:

    st.warning("""
🔴 **Portföy Değerlendirmesi**

Portföy şu an zarar bölgesinde.

• Destek seviyeleri takip edilmeli.

• Pozisyon büyüklükleri gözden geçirilmeli.

• Yeni alımlar kademeli yapılmalı.
""")

st.divider()


# --------------------------------------------------
# PORTFÖY İSTATİSTİKLERİ
# --------------------------------------------------

st.subheader("📌 Portföy İstatistikleri")

sol, sag = st.columns(2)

with sol:

    st.write(f"Toplam Hisse : **{len(df)}**")

    st.write(f"Toplam Portföy : **{toplam_deger:,.2f} TL**")

    st.write(f"Toplam Maliyet : **{toplam_maliyet:,.2f} TL**")


with sag:

    en_buyuk = df.loc[df["Piyasa Değeri"].idxmax()]

    st.write(f"En Büyük Pozisyon : **{en_buyuk['symbol']}**")

    st.write(f"Ağırlık : **%{en_buyuk['Portföy %']:.2f}**")

    st.write(f"Getiri : **%{toplam_getiri:.2f}**")


st.divider()


# --------------------------------------------------
# BURADAN DEVAM EDECEĞİZ (V4)
# --------------------------------------------------
# --------------------------------------------------
# HİSSE SİLME
# --------------------------------------------------

st.subheader("🗑️ Portföy Yönetimi")

col1, col2 = st.columns([3, 1])

with col1:

    sil_symbol = st.selectbox(
        "Silinecek Hisse",
        df["symbol"].tolist()
    )

with col2:

    st.write("")

    if st.button(
        "🗑️ Sil",
        use_container_width=True
    ):

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "DELETE FROM portfolio WHERE symbol=?",
            (sil_symbol,)
        )

        conn.commit()
        conn.close()

        st.success(f"{sil_symbol} silindi.")
        st.rerun()


st.divider()


# --------------------------------------------------
# PORTFÖYÜ DIŞA AKTAR
# --------------------------------------------------

st.subheader("💾 Portföyü Dışa Aktar")

csv = tablo.to_csv(index=False).encode("utf-8-sig")

st.download_button(
    "📥 Excel (CSV) Olarak İndir",
    csv,
    "BIST_AI_PRO_Portfoy.csv",
    "text/csv",
    use_container_width=True
)

st.divider()


# --------------------------------------------------
# PORTFÖY KALİTE PUANI
# --------------------------------------------------

st.subheader("🏆 AI Portföy Skoru")

puan = 100

if len(df) < 5:
    puan -= 10

if en_buyuk["Portföy %"] > 40:
    puan -= 15

if toplam_getiri < 0:
    puan -= 10

if puan >= 90:

    st.success(f"AI Portföy Skoru : {puan}/100")

elif puan >= 75:

    st.info(f"AI Portföy Skoru : {puan}/100")

else:

    st.warning(f"AI Portföy Skoru : {puan}/100")


st.progress(puan / 100)


st.divider()


# --------------------------------------------------
# RİSK ANALİZİ
# --------------------------------------------------

st.subheader("⚠️ Risk Analizi")

if en_buyuk["Portföy %"] > 45:

    st.error(
        "Portföy tek hisseye fazla yoğunlaşmış."
    )

elif en_buyuk["Portföy %"] > 30:

    st.warning(
        "Portföyde yoğunlaşma riski bulunuyor."
    )

else:

    st.success(
        "Portföy dağılımı dengeli."
    )


st.divider()


# --------------------------------------------------
# SON GÜNCELLEME
# --------------------------------------------------

st.caption(
    f"Son Güncelleme : {date.today().strftime('%d.%m.%Y')}"
)