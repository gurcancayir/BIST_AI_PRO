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

        st.info(
            "Canlı kaynak doğrulama aktif"
        )



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



    c1, c2, c3 = st.columns(3)


    c1.metric(
        "Yahoo Finance",
        str(result["Yahoo"])
    )


    c2.metric(
        "Alpha Vantage",
        str(result["Alpha"])
    )


    c3.metric(
        "Veri Güveni",
        f'{result["Güven"]}/100'
    )


    st.write(
        f"""
        Durum: {result["Durum"]}

        Fiyat farkı: %{result["Fark %"]}
        """
    )



    st.divider()


    st.markdown("### 🔄 Kaynak Durumu")


    data = [

        ["Yahoo Finance","🟢 Aktif"],

        ["Alpha Vantage","🟡 Test"],

        ["Twelve Data","🟡 Hazır"],

        ["Matriks API","⚪ Bağlanmadı"],

        ["Foreks API","⚪ Bağlanmadı"]

    ]


    st.table(data)