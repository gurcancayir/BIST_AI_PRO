import pandas as pd


def calculate_data_confidence(
        yahoo_price,
        alpha_price
):


    # İki kaynak da veri vermiyorsa

    if yahoo_price is None and alpha_price is None:

        return {

            "confidence":0,
            "difference":None,
            "status":"❌ Veri Yok"

        }



    # Sadece Yahoo varsa

    if alpha_price is None:

        return {

            "confidence":70,
            "difference":None,
            "status":"🟡 Tek Kaynak"

        }



    # Sadece Alpha varsa

    if yahoo_price is None:

        return {

            "confidence":70,
            "difference":None,
            "status":"🟡 Tek Kaynak"

        }



    # Fiyat farkı hesaplama

    difference = abs(
        yahoo_price - alpha_price
    )


    average = (
        yahoo_price + alpha_price
    ) / 2



    difference_percent = (
        difference /
        average
        *
        100
    )



    # Güven puanı

    if difference_percent < 0.10:

        confidence = 99


    elif difference_percent < 0.50:

        confidence = 95


    elif difference_percent < 1:

        confidence = 90


    else:

        confidence = 75



    return {


        "confidence":confidence,


        "difference":
            round(
                difference_percent,
                2
            ),


        "status":

            "🟢 Uyumlu"
            if confidence >= 95
            else
            "🟡 Kontrol Gerekli"


    }



def compare_sources(symbol,
                    yahoo_price,
                    alpha_price):


    result = calculate_data_confidence(
        yahoo_price,
        alpha_price
    )


    return {


        "Hisse":symbol,

        "Yahoo":
            yahoo_price,

        "Alpha":
            alpha_price,

        "Fark %":
            result["difference"],

        "Güven":
            result["confidence"],

        "Durum":
            result["status"]

    }