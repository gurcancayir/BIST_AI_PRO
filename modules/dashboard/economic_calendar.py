import streamlit as st


def show_economic_calendar():

    st.markdown("### 📅 Ekonomik Takvim")


    events = [

        ("10:00", "🇹🇷 TCMB Faiz Kararı", "🔴 Yüksek Etki"),
        ("15:30", "🇺🇸 Tarım Dışı İstihdam", "🔴 Yüksek Etki"),
        ("16:45", "🇺🇸 PMI Verisi", "🟠 Orta Etki"),
        ("20:00", "🇺🇸 FED Toplantı Tutanakları", "🔴 Yüksek Etki"),

    ]


    for time, event, impact in events:

        with st.container(border=True):

            col1, col2 = st.columns([1, 4])


            with col1:

                st.markdown(
                    f"### {time}"
                )


            with col2:

                st.write(
                    f"**{event}**"
                )

                st.caption(
                    impact
                )


    st.caption(
        "Ekonomik takvim; piyasa hareketlerini etkileyebilecek önemli veri ve kararları gösterir."
    )