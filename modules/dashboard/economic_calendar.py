import streamlit as st


def show_economic_calendar():

    st.subheader("📅 Ekonomik Takvim")

    events = [
        ("21 Tem", "🇹🇷 TCMB Faiz Kararı", "🔴 Yüksek"),
        ("23 Tem", "🇺🇸 FED Toplantısı", "🔴 Çok Yüksek"),
        ("24 Tem", "🇹🇷 TÜFE Verisi", "🟠 Orta"),
        ("25 Tem", "🇺🇸 Tarım Dışı İstihdam", "🔴 Çok Yüksek"),
        ("28 Tem", "🇪🇺 ECB Faiz Kararı", "🟠 Orta"),
    ]

    for date, event, impact in events:

        col1, col2, col3 = st.columns([1, 5, 2])

        col1.write(f"**{date}**")
        col2.write(event)
        col3.write(impact)

    st.divider()