import streamlit as st
from modules.data.yahoo_data import get_yahoo_price
from modules.data.alpha_data import get_alpha_price
from modules.data.validator import compare_sources


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


           
    st.divider()

    st.markdown("### 🔍 Canlı Veri Doğrulama")


symbol = st.selectbox(
    "Kontrol Edilecek Hisse",
    [
        "BIMAS",
        "TUPRS",
        "AKSEN",
        "MGROS",
        "THYAO"
    ]
)


yahoo_price = get_yahoo_price(symbol)

alpha_price = get_alpha_price(symbol)


result = compare_sources(
    symbol,
    yahoo_price,
    alpha_price
)


col_a, col_b, col_c = st.columns(3)


col_a.metric(
    "Yahoo Finance",
    str(result["Yahoo"])
)


col_b.metric(
    "Alpha Vantage",
    str(result["Alpha"])
)


col_c.metric(
    "Veri Güveni",
    f'{result["Güven"]}/100'
)


st.write(
    f"""
    Durum: {result["Durum"]}

    Fiyat farkı: %{result["Fark %"]}
    """
)   

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