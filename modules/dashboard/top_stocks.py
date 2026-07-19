import streamlit as st


def show_top_stocks():

    st.markdown("### 🔥 AI Top Hisseler")


    stocks = [

        ("ASELS", "96", "🟢 Güçlü"),
        ("FROTO", "94", "🟢 Güçlü"),
        ("BIMAS", "92", "🟢 Pozitif"),
        ("MGROS", "90", "🟢 Pozitif"),
        ("THYAO", "88", "🟡 Takip"),
        ("TUPRS", "86", "🟡 Takip"),

    ]


    col1, col2 = st.columns(2)


    for i, stock in enumerate(stocks):

        with col1 if i % 2 == 0 else col2:

            st.metric(
                label=f"📈 {stock[0]}",
                value=f"AI {stock[1]}",
                delta=stock[2]
            )


    st.caption(
        "AI Top Hisseler; teknik görünüm, momentum ve piyasa koşullarına göre örneklenmiştir."
    )