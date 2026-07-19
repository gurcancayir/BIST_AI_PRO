import streamlit as st


def show_macro_view():

    st.markdown("### 🌍 Makro Görünüm")


    macro_data = [

        ("🇺🇸 FED Beklentisi", "🟢 Güvercin"),
        ("🇹🇷 TCMB Politikası", "🟡 Bekle-Gör"),
        ("📈 Enflasyon", "🔴 Yüksek"),
        ("🌍 Jeopolitik Risk", "🟠 Orta"),
        ("🥇 Altın Gücü", "🟢 Güçlü"),
        ("🛢 Petrol", "🟡 Dengeli"),

    ]


    col1, col2 = st.columns(2)


    for i, item in enumerate(macro_data):

        with col1 if i % 2 == 0 else col2:

            st.info(
                f"""
                **{item[0]}**

                {item[1]}
                """
            )


    st.caption(
        "Makro değerlendirme; faiz, enflasyon, emtia ve küresel risk faktörlerine göre oluşturulur."
    )