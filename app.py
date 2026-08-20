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
firsat_merkezi = st.Page(
    "pages/08_Hisse_Firsat_Merkezi.py",
    title="Fırsat Merkezi",
    icon="🎯",
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

bloomberg_haberleri = st.Page(
    "pages/07_Bloomberg_Haberleri.py",
    title="Bloomberg HT",
    icon="📰",
)

# ==================================================
# CRYPTO AI PRO SAYFALARI
# ==================================================

crypto_gunluk_trade = st.Page(
    "pages/08_Crypto_Gunluk_Trade.py",
    title="Günlük Trade",
    icon="⚡",
)

crypto_kisa_vade = st.Page(
    "pages/09_Crypto_Kisa_Vade.py",
    title="Kısa Vade",
    icon="📈",
)

crypto_orta_vade = st.Page(
    "pages/10_Crypto_Orta_Vade.py",
    title="Orta Vade",
    icon="📊",
)

crypto_uzun_vade = st.Page(
    "pages/11_Crypto_Uzun_Vade.py",
    title="Uzun Vade",
    icon="🏆",
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
        # --------------------------------------------------
        # BIST AI PRO
        # --------------------------------------------------
        "BIST AI PRO": [
            anasayfa,
            veri_guncelleme,
            portfoy,
            gunluk_trade,
            hisse_analiz,
            tarama,
            bilancolar,
            dinamik_portfoy,
            firsat_merkezi,
            altin_coin,
            bloomberg_haberleri,
            bist500_test,
        ],

        # --------------------------------------------------
        # CRYPTO AI PRO
        # --------------------------------------------------
        "🪙 CRYPTO AI PRO": [
            crypto_gunluk_trade,
            crypto_kisa_vade,
            crypto_orta_vade,
            crypto_uzun_vade,
        ],
    },
    position="sidebar",
)


# ==================================================
# SAYFAYI ÇALIŞTIR
# ==================================================

pg.run()