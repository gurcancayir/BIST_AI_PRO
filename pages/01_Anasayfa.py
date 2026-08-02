import streamlit as st

# --------------------------------------------------
# PAGE SETTINGS
# --------------------------------------------------

st.set_page_config(
    page_title="BIST AI PRO",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)


# --------------------------------------------------
# DATABASE
# --------------------------------------------------

from database.database import create_tables

create_tables()


# --------------------------------------------------
# MODULES
# --------------------------------------------------

from modules.portfolio.portfolio import show_portfolio

from modules.dashboard.hero import show_hero
from modules.dashboard.market_summary import show_market_summary
from modules.dashboard.market_score import show_market_score
from modules.dashboard.macro_view import show_macro_view
from modules.dashboard.ai_report import show_ai_report
from modules.dashboard.sector_strength import show_sector_strength
from modules.dashboard.ai_top_stocks import show_ai_top_stocks

from modules.data.data_center import show_data_center


# ==================================================
# GLOBAL STYLE
# ==================================================

st.markdown(
    """
    <style>

    .block-container {
        padding-top: 1rem;
        padding-bottom: 2rem;
    }

    h3 {
        color: #0E4D92;
    }

    [data-testid="stMetricValue"] {
        font-size: 1.5rem;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# ==================================================
# SIDEBAR
# ==================================================

with st.sidebar:

    st.title("📈 BIST AI PRO")

    st.success(
        "Yapay Zeka Destekli BIST Analiz Platformu"
    )

    st.divider()

    st.page_link(
        "pages/01_Anasayfa.py",
        label="🏠 Ana Sayfa"
    )

    st.page_link(
        "pages/01_Portfoy.py",
        label="💼 Portföy"
    )

    st.divider()

    st.caption("BIST AI PRO • Dashboard V3")


# ==================================================
# HERO
# ==================================================

show_hero()


# ==================================================
# MARKET SUMMARY
# ==================================================

show_market_summary()


# ==================================================
# PORTFOLIO
# ==================================================

show_portfolio()


# ==================================================
# MARKET SCORE + MACRO
# ==================================================

col1, col2 = st.columns(2)

with col1:
    with st.container(border=True):
        show_market_score()

with col2:
    with st.container(border=True):
        show_macro_view()


# ==================================================
# AI REPORT + SECTOR STRENGTH
# ==================================================

col1, col2 = st.columns(2)

with col1:
    with st.container(border=True):
        show_ai_report()

with col2:
    with st.container(border=True):
        show_sector_strength()


# ==================================================
# AI TOP STOCKS
# ==================================================

with st.container(border=True):
    show_ai_top_stocks()


# ==================================================
# DATA CENTER
# ==================================================

with st.container(border=True):
    show_data_center()


# ==================================================
# FOOTER
# ==================================================

st.divider()

st.caption(
    "© 2026 BIST AI PRO | Yapay Zeka Destekli BIST Analiz Platformu"
)