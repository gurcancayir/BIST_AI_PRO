import streamlit as st
from modules.data.macro_data import get_price


# ----------------------------------------------------------
# SEKTÖR ORTALAMA DEĞİŞİM HESAPLAMA
# ----------------------------------------------------------

def calculate_sector_strength(stocks):

    degisimler = []

    for stock in stocks:

        try:

            fiyat, degisim = get_price(stock)

            if degisim != "-":

                degisimler.append(float(degisim))

        except Exception:

            continue


    if len(degisimler) == 0:

        return None


    return round(
        sum(degisimler) / len(degisimler),
        2
    )


# ----------------------------------------------------------
# SEKTÖR SKORLARI
# ----------------------------------------------------------

def get_sector_scores():

    sektorler = {


        "Perakende": [

            "BIMAS.IS",
            "MGROS.IS",
            "SOKM.IS",
            "BIZIM.IS",
            "ULKER.IS"

        ],


        "Savunma": [

            "ASELS.IS",
            "OTKAR.IS",
            "ASTOR.IS",
            "SDTTR.IS",
            "KONTR.IS"

        ],


        "Otomotiv": [

            "FROTO.IS",
            "TOASO.IS",
            "DOAS.IS",
            "KARSN.IS",
            "TTRAK.IS"

        ],


        "Enerji": [

            "AKSEN.IS",
            "ENJSA.IS",
            "TUPRS.IS",
            "ODAS.IS",
            "AYDEM.IS"

        ],


        "Sanayi": [

            "SISE.IS",
            "EREGL.IS",
            "KRDMD.IS",
            "HEKTS.IS",
            "KCHOL.IS"

        ],


        "Banka": [

            "AKBNK.IS",
            "GARAN.IS",
            "YKBNK.IS",
            "ISCTR.IS",
            "HALKB.IS"

        ],


        "Ulaştırma": [

            "THYAO.IS",
            "PGSUS.IS",
            "TAVHL.IS",
            "CLEBI.IS",
            "GSDHO.IS"

        ]

    }


    sonuc = {}


    for sektor, hisseler in sektorler.items():


        guc = calculate_sector_strength(hisseler)


        if guc is None:

            skor = 50


        else:

            # Ortalama günlük değişimi skora çevir
            # %1 değişim = 60 puan
            # %-1 değişim = 40 puan

            skor = 50 + (guc * 10)

            skor = max(
                0,
                min(
                    100,
                    skor
                )
            )


        sonuc[sektor] = round(
            skor,
            1
        )


    return sonuc



# ----------------------------------------------------------
# STREAMLIT GÖRÜNÜMÜ
# ----------------------------------------------------------

def show_sector_strength():

    st.markdown(
        "### 💪 Sektör Gücü"
    )


    skorlar = get_sector_scores()


    for sektor, skor in skorlar.items():


        if skor >= 60:

            durum = "🟢"


        elif skor <= 40:

            durum = "🔴"


        else:

            durum = "🟡"



        st.metric(

            sektor,

            f"{durum} {skor}/100"

        )