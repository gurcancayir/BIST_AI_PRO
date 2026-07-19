import streamlit as st


def show_sector_strength():

    st.subheader("🏭 Sektör Güç Endeksi")

    sectors = [
        ("🛒 Perakende", 94),
        ("🛡️ Savunma", 91),
        ("🚗 Otomotiv", 88),
        ("🏦 Bankacılık", 76),
        ("⚡ Enerji", 71),
        ("🧪 Kimya", 67),
    ]

    for sector, score in sectors:

        col1, col2 = st.columns([2, 5])

        with col1:
            st.write(f"**{sector}**")

        with col2:
            st.progress(score / 100, text=f"{score}/100")

    st.divider()