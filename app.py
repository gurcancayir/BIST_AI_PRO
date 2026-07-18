import streamlit as st
from datetime import datetime
from database.database import create_tables


# Veritabanını hazırla
create_tables()


# --------------------------------------------------
# SAYFA AYARLARI
# --------------------------------------------------

st.set_page_config(
    page_title="BIST AI PRO",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)


# --------------------------------------------------
# CSS
# --------------------------------------------------

st.markdown("""
<style>

.main{
    background:#f5f7fb;
}

.block-container{
    padding-top:1rem;
}

.bigtitle{
    font-size:42px;
    font-weight:bold;
    color:#0E4D92;
}

.subtitle{
    color:gray;
    font-size:18px;
}

</style>
""", unsafe_allow_html=True)



# --------------------------------------------------
# SIDEBAR
# --------------------------------------------------

with st.sidebar:

    st.title("📈 BIST AI PRO")

    st.success(
        "Yapay Zeka Destekli BIST Analiz Platformu"
    )

    st.divider()

    st.header("Sayfalar")


    st.page_link(
        "app.py",
        label="🏠 Ana Sayfa"
    )


    # Şu an aktif olan tek modül
    st.page_link(
        "pages/01_portfoy.py",
        label="💼 Portföy Yönetimi"
    )


    st.divider()

    st.info("Versiyon 0.1")



# --------------------------------------------------
# ANA SAYFA
# --------------------------------------------------

st.markdown(
"""
<div class='bigtitle'>
📈 BIST AI PRO
</div>

<div class='subtitle'>
TradingView ve Matriks seviyesinde Yapay Zeka Destekli BIST Analiz Platformu
</div>

""",
unsafe_allow_html=True
)


st.write("")

st.caption(
    datetime.now().strftime("%d.%m.%Y %H:%M")
)


st.divider()



# --------------------------------------------------
# PİYASA ÖZETİ
# --------------------------------------------------

st.subheader("📊 Piyasa Özeti")


c1,c2,c3,c4,c5,c6 = st.columns(6)


c1.metric(
    "BIST100",
    "10.521",
    "+1.24%"
)

c2.metric(
    "USD",
    "40.18",
    "+0.25%"
)

c3.metric(
    "EURO",
    "47.04",
    "+0.15%"
)

c4.metric(
    "GRAM ALTIN",
    "4.365",
    "+0.82%"
)

c5.metric(
    "ONS",
    "3335",
    "+0.52%"
)

c6.metric(
    "PETROL",
    "69.80",
    "-0.42%"
)


st.divider()



# --------------------------------------------------
# MAKRO GÖRÜNÜM
# --------------------------------------------------

sol,sag = st.columns(2)


with sol:

    st.subheader("🌍 Makro Görünüm")

    st.write("FED Beklentisi : 🟢 Güvercin")
    st.write("TCMB : 🟡 Bekle-Gör")
    st.write("Enflasyon : 🔴 Yüksek")
    st.write("Jeopolitik Risk : 🟠 Orta")
    st.write("Altın Gücü : 🟢 Güçlü")
    st.write("Petrol : 🟡 Dengeli")



with sag:

    st.subheader("🤖 AI Yorumu")

    st.success(
"""
• Endeks ana trendi pozitif.

• Savunma ve perakende güçlü.

• Enerji sektörü takip edilmeli.

• Risk seviyesi orta.

• Portföy çeşitlendirmesi önemli.
"""
    )


st.divider()



# --------------------------------------------------
# TEKNİK DURUM
# --------------------------------------------------

st.subheader("📈 Endeks Teknik Durumu")


a,b,c,d,e = st.columns(5)


a.metric("Trend","Yukarı")
b.metric("RSI","61")
c.metric("MACD","AL")
d.metric("ADX","29")
e.metric("Puan","84/100")


st.progress(84)



st.divider()



# --------------------------------------------------
# İZLEME LİSTESİ
# --------------------------------------------------

st.subheader("👀 İzleme Listesi")


watchlist = [
    "ASELS",
    "THYAO",
    "BIMAS",
    "AKSEN",
    "FROTO",
    "CCOLA",
    "MGROS",
    "TUPRS",
    "ENKAI",
    "ASTOR"
]


cols = st.columns(5)


for i,hisse in enumerate(watchlist):

    cols[i%5].button(
        hisse,
        use_container_width=True
    )



st.divider()


st.caption(
"© 2026 BIST AI PRO"
)