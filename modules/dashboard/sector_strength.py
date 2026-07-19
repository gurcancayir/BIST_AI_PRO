import streamlit as st


def show_sector_strength():

    st.markdown("### 🏭 Sektör Gücü")


    sectors = [
        ("🛡️ Savunma", "96", "🟢 Güçlü"),
        ("🛒 Perakende", "92", "🟢 Güçlü"),
        ("🚗 Otomotiv", "88", "🟢 Pozitif"),
        ("⚡ Enerji", "82", "🟡 Takip"),
        ("🏦 Banka", "76", "🟡 Nötr"),
        ("🏗️ GYO", "64", "🟠 Zayıf"),
    ]


    col1, col2 = st.columns(2)


    for i, sector in enumerate(sectors):

        with col1 if i % 2 == 0 else col2:

            st.metric(
                label=sector[0],
                value=f"{sector[1]} / 100",
                delta=sector[2]
            )


    st.caption(
        "Sektör gücü; momentum, hacim, trend ve piyasa ilgisine göre değerlendirilir."
    )