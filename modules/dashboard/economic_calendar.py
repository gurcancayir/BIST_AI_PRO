import streamlit as st


def show_economic_calendar():

    st.subheader("📅 Ekonomik Takvim")

    events = [
        {
            "time": "10:00",
            "country": "🇹🇷",
            "event": "TCMB Faiz Kararı",
            "impact": "🔴 Yüksek",
            "status": "Bekleniyor"
        },
        {
            "time": "15:30",
            "country": "🇺🇸",
            "event": "Tarım Dışı İstihdam",
            "impact": "🔴 Yüksek",
            "status": "Bekleniyor"
        },
        {
            "time": "16:45",
            "country": "🇺🇸",
            "event": "PMI Verisi",
            "impact": "🟠 Orta",
            "status": "Bekleniyor"
        },
        {
            "time": "20:00",
            "country": "🇺🇸",
            "event": "FED Toplantı Tutanakları",
            "impact": "🔴 Yüksek",
            "status": "Bekleniyor"
        },
    ]

    for event in events:
        with st.container(border=True):
            col1, col2 = st.columns([1, 5])

            with col1:
                st.markdown(f"### {event['time']}")
                st.caption(event["country"])

            with col2:
                st.write(f"**{event['event']}**")
                st.caption(
                    f"Etki: {event['impact']} | Durum: {event['status']}"
                )