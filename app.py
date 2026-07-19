import streamlit as st
from database.database import create_tables

from modules.dashboard.hero import show_hero
from modules.dashboard.market_summary import show_market_summary
from modules.dashboard.market_score import show_market_score
from modules.dashboard.score_breakdown import show_score_breakdown
from modules.dashboard.macro_view import show_macro_view
from modules.dashboard.ai_report import show_ai_report
from modules.dashboard.sector_strength import show_sector_strength
from modules.dashboard.economic_calendar import show_economic_calendar
from modules.dashboard.top_stocks import show_top_stocks


# --------------------------------------------------
# DATABASE
# --------------------------------------------------

create_tables()


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
# GLOBAL STYLE
# --------------------------------------------------

st.markdown("""

<style>

.block-container {

    padding-top: 1rem;
    padding-bottom: 2rem;

}


.dashboard-box {

    background:white;
    border-radius:12px;
    padding:15px;
    border:1px solid #e5e7eb;

}


h3 {

    color:#0E4D92;

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


    st.page_link(
        "app.py",
        label="🏠 Dashboard"
    )


    st.page_link(
        "pages/01_Portfoy.py",
        label="💼 Portföy"
    )


    st.divider()

    st.caption(
        "Versiyon 0.2 Dashboard V2"
    )



# --------------------------------------------------
# HEADER
# --------------------------------------------------

show_hero()



# --------------------------------------------------
# MARKET SUMMARY
# --------------------------------------------------

show_market_summary()



st.divider()



# --------------------------------------------------
# ROW 1
# --------------------------------------------------

col1, col2 = st.columns(2)


with col1:

    with st.container(border=True):

        show_market_score()



with col2:

    with st.container(border=True):

        show_macro_view()
# --------------------------------------------------
# ROW 2
# --------------------------------------------------

col1, col2 = st.columns(2)


with col1:

    with st.container(border=True):

        show_ai_report()



with col2:

    with st.container(border=True):

        show_score_breakdown()



st.divider()



# --------------------------------------------------
# ROW 3
# --------------------------------------------------

col1, col2 = st.columns(2)


with col1:

    with st.container(border=True):

        show_sector_strength()



with col2:

    with st.container(border=True):

        show_economic_calendar()



st.divider()



# --------------------------------------------------
# ROW 4
# --------------------------------------------------

with st.container(border=True):

    show_top_stocks()



st.divider()



# --------------------------------------------------
# FOOTER
# --------------------------------------------------

st.caption(
    "© 2026 BIST AI PRO | Yapay Zeka Destekli BIST Analiz Platformu"
)