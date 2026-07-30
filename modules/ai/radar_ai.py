from modules.data.yahoo_data import get_stock_analysis


WATCHLIST = [

    "ASELS",
    "ASTOR",
    "TUPRS",
    "BIMAS",
    "MGROS",
    "THYAO",
    "AKSEN",
    "SISE",
    "EREGL",
    "FROTO",
    "TOASO",
    "KCHOL",
    "ENKAI",
    "ODAS",
    "PGSUS"

]


def calculate_radar_score(analysis):

    score = 0
    reasons = []


    trend = analysis.get("trend_strength", 50)

    score += trend * 0.30

    if trend >= 70:
        reasons.append("Güçlü trend")



    momentum = analysis.get(
        "momentum_score",
        50
    )

    score += momentum * 0.25

    if momentum >= 70:
        reasons.append("Momentum güçlü")



    volume = analysis.get(
        "volume_score",
        50
    )

    score += volume * 0.15

    if volume >= 70:
        reasons.append("Hacim güçlü")



    ai = analysis.get(
        "score",
        50
    )

    score += ai * 0.20

    if ai >= 80:
        reasons.append("AI puanı yüksek")



    rsi = analysis.get(
        "rsi",
        50
    )

    if rsi and 45 <= rsi <= 65:

        score += 10

        reasons.append(
            "RSI uygun"
        )


    return round(
        min(score,100),
        1
    ), reasons




def get_radar_picks():

    radar = []


    for symbol in WATCHLIST:


        print(
            "Taranıyor:",
            symbol
        )


        analysis = get_stock_analysis(
            symbol
        )


        if analysis is None:

            print(
                "VERİ YOK:",
                symbol
            )

            continue



        radar_score, reasons = calculate_radar_score(
            analysis
        )


        radar.append({

            "symbol": symbol,

            "price": analysis.get(
                "price",
                0
            ),

            "change": analysis.get(
                "change",
                0
            ),

            "sector": analysis.get(
                "sector",
                "-"
            ),

            "recommendation": analysis.get(
                "recommendation",
                "Tut"
            ),

            "score": analysis.get(
                "score",
                0
            ),

            "trend": analysis.get(
                "trend",
                "-"
            ),

            "trend_strength": analysis.get(
                "trend_strength",
                0
            ),

            "momentum_score": analysis.get(
                "momentum_score",
                0
            ),

            "volume_score": analysis.get(
                "volume_score",
                0
            ),

            "radar_score": radar_score,

            "reasons": reasons

        })


    radar.sort(
        key=lambda x:x["radar_score"],
        reverse=True
    )


    print(
        "TOPLAM RADAR:",
        len(radar)
    )


    return radar