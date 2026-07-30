from modules.data.yahoo_data import get_stock_analysis
from modules.data.yahoo_data import (
    get_stock_analysis,
    get_rsi
)


# İzlenecek hisseler
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

    # -----------------------------------
    # Trend Gücü (25)
    # -----------------------------------

    trend_strength = analysis["trend_strength"]

    score += trend_strength * 0.25

    if trend_strength >= 80:
        reasons.append("Trend çok güçlü")

    # -----------------------------------
    # Momentum (20)
    # -----------------------------------

    momentum = analysis["momentum_score"]

    score += momentum * 0.20

    if momentum >= 70:
        reasons.append("Momentum güçlü")

    # -----------------------------------
    # Hacim (15)
    # -----------------------------------

    volume = analysis["volume_score"]

    score += volume * 0.15

    if volume >= 70:
        reasons.append("Hacim artıyor")

    # -----------------------------------
    # AI Score (15)
    # -----------------------------------

    ai = analysis["score"]

    score += ai * 0.15

    if ai >= 80:
        reasons.append("AI puanı yüksek")

    # -----------------------------------
    # RSI (10)
    # -----------------------------------

    rsi = analysis["rsi"]

    if rsi is not None:

        if 45 <= rsi <= 65:

            score += 10

            reasons.append("RSI sağlıklı bölgede")

        elif rsi < 35:

            score += 8

            reasons.append("RSI toparlanıyor")

    # -----------------------------------
    # Destek Bölgesi (5)
    # -----------------------------------

    try:

        price = analysis["price"]
        support = analysis["support"]

        if support > 0:

            distance = abs(price - support) / support

            if distance <= 0.03:

                score += 5

                reasons.append("Destek bölgesinde")

    except:
        pass



    return round(min(score, 100), 1), reasons
def get_radar_picks():

    radar = []

    for symbol in WATCHLIST:

        try:

            analysis = get_stock_analysis(symbol)

            if analysis is None:
                continue

            radar_score, reasons = calculate_radar_score(
                analysis
            )

            radar.append({

                "symbol": symbol,

                "price": analysis["price"],

                "change": analysis["change"],

                "sector": analysis["sector"],

                "recommendation": analysis["recommendation"],

                "score": analysis["score"],

                "trend": analysis["trend"],

                "trend_strength": analysis["trend_strength"],

                "momentum_score": analysis["momentum_score"],

                "volume_score": analysis["volume_score"],

                "radar_score": radar_score,

                "reasons": reasons

            })

        except:

            pass


    radar.sort(

        key=lambda x: x["radar_score"],

        reverse=True

    )

    return radar