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
portfoy_yonetim = st.Page(
    "pages/09_Portfoy_Pro.py",
    title="Portföy Yönetim PRO",
    icon="💼",
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
bist500_test = st.Page(
    "pages/99_BIST500_Test.py",
    title="Deneme",
    icon="🧪",
)
# ==================================================
# CRYPTO AI PRO SAYFALARI
# ==================================================
crypto_piyasa = st.Page(
    "pages_cr/01_Kripto_Piyasa.py",
    title="Kripto Piyasa",
    icon="🌐",
)
crypto_trade = st.Page(
    "pages_cr/02_Kripto_Trade.py",
    title="Kripto Trade",
    icon="⚡",
)
crypto_trade_pro = st.Page(
    "pages_cr/03_Kripto_Trade_Pro.py",
    title="Kripto Trade Pro",
    icon="🚀",
)
crypto_gunluk_trade = st.Page(
    "pages_cr/08_Crypto_Gunluk_Trade.py",
    title="Günlük Trade",
    icon="⚡",
)

crypto_kisa_vade = st.Page(
    "pages_cr/09_Crypto_Kisa_Vade.py",
    title="Kısa Vade",
    icon="📈",
)

crypto_orta_vade = st.Page(
    "pages_cr/10_Crypto_Orta_Vade.py",
    title="Orta Vade",
    icon="📊",
)

crypto_uzun_vade = st.Page(
    "pages_cr/11_Crypto_Uzun_Vade.py",
    title="Uzun Vade",
    icon="🏆",
)
crypto_portfoy = st.Page(
    "pages_cr/12_Crypto_Portfoy_Yonetimi.py",
    title="Kripto Portföy",
    icon="💼",
)
crypto_portfoy_pro = st.Page(
    "pages_cr/13_Crypto_Portfoy_Pro.py",
    title="Portföy PRO",
    icon="💼",
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
            portfoy_yonetim,
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
            crypto_piyasa,
            crypto_trade,
            crypto_trade_pro,
            crypto_gunluk_trade,
            crypto_kisa_vade,
            crypto_orta_vade,
            crypto_uzun_vade,
            crypto_portfoy,
            crypto_portfoy_pro,
        ],
    },
    position="sidebar",
)


# ==================================================
# SAYFAYI ÇALIŞTIR
# ==================================================

pg.run()