import streamlit as st

from modules.ai.market_ai import get_market_score


def get_allocation(score, risk):

    # Varsayılan
    allocation = {
        "Hisse": 45,
        "Fon": 20,
        "Altın": 15,
        "Döviz": 10,
        "Nakit": 10
    }

    # Risk profili etkisi
    if risk == "Korumacı":

        allocation = {
            "Hisse": 30,
            "Fon": 30,
            "Altın": 20,
            "Döviz": 10,
            "Nakit": 10
        }

    elif risk == "Agresif":

        allocation = {
            "Hisse": 70,
            "Fon": 15,
            "Altın": 5,
            "Döviz": 5,
            "Nakit": 5
        }

    # AI Market Score düzeltmesi

    if score >= 75:

        allocation["Hisse"] += 10
        allocation["Nakit"] -= 5
        allocation["Altın"] -= 5

    elif score < 35:

        allocation["Hisse"] -= 10
        allocation["Altın"] += 5
        allocation["Nakit"] += 5

    return allocation


def show_allocation_ai():

    st.subheader("💼 AI Yatırım Dağılımı")

    amount = st.number_input(
        "Yatırım Tutarı (TL)",
        min_value=1000,
        value=100000,
        step=1000
    )

    risk = st.radio(
        "Risk Profili",
        [
            "Korumacı",
            "Dengeli",
            "Agresif"
        ],
        horizontal=True
    )

    score, reasons = get_market_score()

    allocation = get_allocation(
        score,
        risk
    )

    st.markdown("---")

    st.write(f"### AI Market Score : {score}/100")

    st.markdown("### Önerilen Dağılım")

    toplam = 0

    for item, percent in allocation.items():

        tl = amount * percent / 100

        toplam += tl

        col1, col2, col3 = st.columns([2,1,1])

        col1.write(item)

        col2.write(f"%{percent}")

        col3.write(f"{tl:,.0f} TL")

    st.markdown("---")

    st.success(
        f"Toplam Yatırım : {toplam:,.0f} TL"
    )

    with st.expander("AI Bu Dağılımı Neden Önerdi?"):

        for r in reasons:

            st.write("•", r)