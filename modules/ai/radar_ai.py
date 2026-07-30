from modules.data.yahoo_data import get_stock_analysis

import traceback
# ==========================================
# TARAMA LİSTESİ
# ==========================================

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


# ==========================================
# RADAR SKORU
# ==========================================

def calculate_radar_score(analysis):


    score = 0

    reasons = []


    # -------------------------
    # Trend
    # -------------------------

    trend_strength = analysis.get(
        "trend_strength",
        50
    )


    score += trend_strength * 0.25


    if trend_strength >= 80:

        reasons.append(
            "Güçlü trend"
        )


    # -------------------------
    # Momentum
    # -------------------------

    momentum = analysis.get(
        "momentum_score",
        50
    )


    score += momentum * 0.20


    if momentum >= 70:

        reasons.append(
            "Momentum güçlü"
        )



    # -------------------------
    # Hacim
    # -------------------------

    volume = analysis.get(
        "volume_score",
        50
    )


    score += volume * 0.15


    if volume >= 70:

        reasons.append(
            "Hacim destekliyor"
        )



    # -------------------------
    # AI Score
    # -------------------------

    ai_score = analysis.get(
        "score",
        50
    )


    score += ai_score * 0.15


    if ai_score >= 80:

        reasons.append(
            "AI puanı yüksek"
        )



    # -------------------------
    # RSI
    # -------------------------

    rsi = analysis.get(
        "rsi",
        None
    )


    if rsi:


        if 45 <= rsi <= 65:

            score += 10

            reasons.append(
                "RSI sağlıklı"
            )


        elif rsi < 35:

            score += 8

            reasons.append(
                "RSI toparlanma bölgesinde"
            )



    # -------------------------
    # Destek yakınlığı
    # -------------------------

    try:


        price = analysis["price"]

        support = analysis["support"]


        if support:


            uzaklik = abs(
                price - support
            ) / support



            if uzaklik <= 0.03:

                score += 5

                reasons.append(
                    "Destek bölgesinde"
                )


    except:

        pass



    return round(
        min(score,100),
        1
    ), reasons





# ==========================================
# RADAR ANA FONKSİYON
# ==========================================

def get_radar_picks():


    radar = []



    for symbol in WATCHLIST:


        try:


            analysis = get_stock_analysis(
                symbol
            )


            if analysis is None:

                continue



            radar_score, reasons = calculate_radar_score(
                analysis
            )



            radar.append(


                {


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


                }

            )



        except Exception as e:


            print(
                "RADAR HATA:",
                symbol,
                str(e)
            )


            print(
                traceback.format_exc()
            )



    radar.sort(

        key=lambda x: x["radar_score"],

        reverse=True

    )


    return radar