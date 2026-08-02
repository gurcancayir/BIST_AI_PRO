import streamlit as st
from datetime import datetime
from modules.ai.allocation_ai import show_allocation_ai

from modules.ai.market_ai import (
    get_market_score,
    get_macro_comment
)
from modules.dashboard.sector_strength import get_sector_scores
# Sayfa ayarları
st.set_page_config(
    page_title="BIST AI PRO",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)
# AI Market Score al
score, reasons = get_market_score()
st.write("DEBUG SCORE:", score)
st.write("DEBUG NEDENLER:", reasons)
# -----------------------------
# BAŞLIK
# -----------------------------
st.title("🤖 BIST AI PRO")
st.subheader("AI Sabah Brifingi")

bugun = datetime.now().strftime("%d.%m.%Y")

st.caption(f"📅 {bugun} | Yapay Zeka Destekli Piyasa Analizi")
# -----------------------------
# AI GÜVEN ENDEKSİ
# -----------------------------
st.divider()

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        label="🤖 AI Güven Endeksi",
        value=f"{score} / 100"
    )


with col2:

    if score >= 80:
        durum = "🟢 Güçlü Pozitif"

    elif score >= 60:
        durum = "🟡 Temkinli Pozitif"

    elif score >= 40:
        durum = "🟠 Nötr"

    else:
        durum = "🔴 Riskli"

    st.metric(
        label="📈 BIST Görünümü",
        value=durum
    )
   
with col3:
    st.metric(
        label="⚠️ Risk Seviyesi",
        value="Orta"
    )

with col4:
    st.metric(
        label="🎯 Günlük Strateji",
        value="Seçici Alım"
    )


# -----------------------------
# EKONOMİST ÖZETLERİ
# -----------------------------
st.divider()

st.header("👨‍🏫 Ekonomist Görüşleri")

col1, col2 = st.columns(2)

with col1:

    st.info(
        """
        **Mahfi Eğilmez**

        Enflasyon, faiz ve ekonomik dengeler
        piyasaların ana belirleyicisi olmaya devam ediyor.

        BIST Etkisi:
        🟡 Temkinli
        """
    )

    st.info(
        """
        **Hakan Kara**

        Para politikası ve TCMB beklentileri
        yakından takip edilmeli.

        BIST Etkisi:
        🟢 Pozitif
        """
    )


with col2:

    st.info(
        """
        **Atilla Yeşilada**

        Küresel riskler, dolar ve yabancı yatırımcı
        hareketleri önemli.

        BIST Etkisi:
        🟡 Dengeli
        """
    )

    st.info(
        """
        **Bora Özkent**

        Güçlü bilanço ve kaliteli şirketler
        ön plana çıkıyor.

        BIST Etkisi:
        🟢 Pozitif
        """
    )


# -----------------------------
# MAKRO GÖRÜNÜM
# -----------------------------

st.divider()

st.header("🌍 AI Makro Görünüm")


macro_comments = get_macro_comment()


for item in macro_comments:

    col1, col2, col3 = st.columns([2,2,3])

    with col1:
        st.write("**" + item[0] + "**")

    with col2:
        st.write(item[1])

    with col3:
        st.write(item[2])

# -----------------------------
# SEKTÖR GÜCÜ
# -----------------------------
st.divider()

st.header("🔥 Sektör Gücü")

sektorler = get_sector_scores()


for sektor, puan in sektorler.items():

    if puan >= 60:
        durum = "🟢"

    elif puan <= 40:
        durum = "🔴"

    else:
        durum = "🟡"


    st.write(
        f"**{durum} {sektor}**  {puan}/100"
    )

    st.progress(
        puan / 100
    )

# -----------------------------
# AI YORUMU
# -----------------------------
st.divider()
st.header("💼 AI Yatırım Dağılımı")

show_allocation_ai()



# -----------------------------
# ALT BİLGİ
# -----------------------------
st.divider()

st.caption(
    "BIST AI PRO v2.0 | AI Sabah Brifingi Modülü"
)