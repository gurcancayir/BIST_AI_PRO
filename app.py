import streamlit as st


# ==================================================
# SAYFALAR
# ==================================================

anasayfa = st.Page(
    "pages/01_Anasayfa.py",
    title="Anasayfa",
    icon="🏠",
)

portfoy = st.Page(
    "pages/01_Portfoy.py",
    title="Portföy",
    icon="💼",
)

gunluk_trade = st.Page(
    "pages/01_Gunluk_Trade.py",
    title="Günlük Trade",
    icon="⚡",
)

hisse_analiz = st.Page(
    "pages/02_Hisse_Analiz.py",
    title="Hisse Analiz",
    icon="📈",
)

tarama = st.Page(
    "pages/03_Tarama.py",
    title="Tarama",
    icon="🔍",
)

veri_guncelleme = st.Page(
    "pages/00_Veri_Guncelleme.py",
    title="Veri Güncelleme",
    icon="🔄",
)

dinamik_portfoy = st.Page(
    "pages/01_Dinamik_Portfoy.py",
    title="Dinamik Portföy",
    icon="📊",
)

bilancolar = st.Page(
    "pages/05_Bilancolar.py",
    title="Bilançolar",
    icon="📑",
)

altin_coin = st.Page(
    "pages/06_Altin_Coin.py",
    title="Altın & Coin",
    icon="🪙",
)

bist500_test = st.Page(
    "pages/99_BIST500_Test.py",
    title="Deneme",
    icon="🧪",
)


# ==================================================
# SOL MENÜ
# ==================================================

pg = st.navigation(
    {
        "BIST AI PRO": [
            anasayfa,
            veri_guncelleme,
            portfoy,
            gunluk_trade,
            hisse_analiz,
            tarama,
            bilancolar,
            dinamik_portfoy,
            altin_coin,
            bist500_test,
        ]
    },
    position="sidebar",
)


# ==================================================
# SAYFAYI ÇALIŞTIR
# ==================================================

pg.run()