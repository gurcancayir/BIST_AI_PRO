import streamlit as st
from database.database import create_tables

from modules.dashboard.hero import show_hero
from modules.dashboard.market_summary import show_market_summary
from modules.dashboard.market_score import show_market_score
from modules.dashboard.sector_strength import show_sector_strength
from modules.dashboard.economic_calendar import show_economic_calendar
from modules.dashboard.ai_report import show_ai_report


# --------------------------------------------------
# VERİTABANI
# --------------------------------------------------

create_tables()


# --------------------------------------------------
# SAYFA
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

.block-container{
    padding-top:1rem;
    padding-bottom:1rem;
}

div[data-testid="stMetric"]{
    border:1px solid #E5E7EB;
    border-radius:12px;
    padding:12px;
    background:white;
}

</style>
""", unsafe_allow_html=True)


# --------------------------------------------------
# SIDEBAR
# --------------------------------------------------

with st.sidebar:

    st.title("📈 BIST AI PRO")

    st.success("Yapay Zeka Destekli BIST Analiz Platformu")

    st.divider()

    st.subheader("Menü")

    st.page_link(
        "app.py",
        label="🏠 Dashboard"
    )

    st.page_link(
        "pages/01_Portfoy.py",
        label="💼 Portföy"
    )

    st.divider()

    st.caption("Sürüm 0.2")


# --------------------------------------------------
# DASHBOARD
# --------------------------------------------------

show_hero()

show_market_summary()


left, right = st.columns(2)

with left:
    show_market_score()

with right:
    show_ai_report()


left, right = st.columns(2)

with left:
    show_sector_strength()

with right:
    show_economic_calendar()


st.divider()

st.caption("© 2026 BIST AI PRO")