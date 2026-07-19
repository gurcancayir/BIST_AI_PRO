import streamlit as st
from modules.data.macro_data import get_price


def calculate_sector_strength(stocks):

    degisimler = []

    for stock in stocks:

        fiyat, degisim = get_price(stock)

        if degisim != "-":

            degisimler.append(degisim)


    if len(degisimler) == 0:
        return "-"

    return round(
        sum(degisimler) / len(degisimler),
        2
    )



def show_sector_strength():

    st.markdown("### 💪 Sektör Gücü")


    sektorler = {

        "🛒 Perakende": [
            "BIMAS.IS",
            "MGROS.IS",
            "SOKM.IS",
            "BIZIM.IS",
            "ULKER.IS"
        ],


        "🛡️ Savunma": [
            "ASELS.IS",
            "OTKAR.IS",
            "ASTOR.IS",
            "SDTTR.IS",
            "KONTR.IS"
        ],


        "🚗 Otomotiv": [
            "FROTO.IS",
            "TOASO.IS",
            "DOAS.IS",
            "KARSN.IS",
            "TTRAK.IS"
        ],


        "⚡ Enerji": [
            "AKSEN.IS",
            "ENJSA.IS",
            "TUPRS.IS",
            "ODAS.IS",
            "AYDEM.IS"
        ],


        "🏭 Sanayi": [
            "SISE.IS",
            "EREGL.IS",
            "KRDMD.IS",
            "HEKTS.IS",
            "KCHOL.IS"
        ],


        "🏦 Banka": [
            "AKBNK.IS",
            "GARAN.IS",
            "YKBNK.IS",
            "ISCTR.IS",
            "HALKB.IS"
        ],


        "✈️ Ulaştırma": [
            "THYAO.IS",
            "PGSUS.IS",
            "TAVHL.IS",
            "CLEBI.IS",
            "GSDHO.IS"
        ]

    }



    for sektor, hisseler in sektorler.items():

        guc = calculate_sector_strength(hisseler)


        if guc == "-":

            durum = "⚪"

        elif guc > 1:

            durum = "🟢"

        elif guc < -1:

            durum = "🔴"

        else:

            durum = "🟡"



        st.metric(
            sektor,
            f"{durum} %{guc}"
        )