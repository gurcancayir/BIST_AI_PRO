import streamlit as st


def show_data_center():

    st.subheader("⚙️ Veri Merkezi")


    col1, col2 = st.columns(2)



    with col1:

        st.markdown("### 📡 Hisse Veri Kaynağı")


        source = st.selectbox(

            "Aktif Kaynak Seç",

            [

                "Yahoo Finance",

                "Alpha Vantage",

                "Twelve Data",

                "Matriks API",

                "Foreks API"

            ]

        )


        st.success(
            f"Aktif Kaynak: {source}"
        )



    with col2:

        st.markdown("### 🛡 Veri Güven Kontrolü")


        confidence = 96


        st.metric(

            "Veri Güven Skoru",

            f"{confidence}/100",

            "+2"

        )


        st.progress(
            confidence / 100
        )



    st.divider()



    st.markdown("### 🔄 Kaynak Durumu")


    data = [

        ["Yahoo Finance","🟢 Aktif"],

        ["Alpha Vantage","🟡 Hazır"],

        ["Twelve Data","🟡 Hazır"],

        ["Matriks API","⚪ Bağlanmadı"],

        ["Foreks API","⚪ Bağlanmadı"]

    ]


    st.table(data)



    st.info(
        """
        AI analizleri için veri doğrulama sistemi hazırlanıyor.

        Birden fazla kaynaktan gelen veriler karşılaştırılarak
        güven skoru oluşturulacaktır.
        """
    )