from modules.data.macro_data import get_macro_data

from modules.data.yahoo_data import (
    get_history,
    get_rsi,
    get_macd,
    get_trend,
    get_momentum,
    get_average_volume,
    get_volume,
    get_volatility,
    get_ema
)



def safe_float(value):

    try:
        return float(value)

    except:
        return 0



def get_market_score():

    score = 60
    reasons = []


    # =================================================
    # 1 - BIST TEKNİK ANALİZ (25 PUAN)
    # =================================================

    try:

        df = get_history("XU100.IS")


        if df is not None:


            trend = get_trend(df)

            rsi = get_rsi(df)

            macd, signal = get_macd(df)


            ema20 = get_ema(df,20)

            ema50 = get_ema(df,50)

            price = df["Close"].iloc[-1]


            # Trend

            if trend == "Güçlü Yükseliş":

                score += 20

                reasons.append(
                    "BIST güçlü yükseliş trendinde"
                )


            elif trend == "Yükseliş":

                score += 12

                reasons.append(
                    "BIST yükseliş trendinde"
                )


            elif trend == "Düşüş":

                score -= 10

                reasons.append(
                    "BIST düşüş trendinde"
                )


            elif trend == "Güçlü Düşüş":

                score -= 20

                reasons.append(
                    "BIST güçlü düşüş trendinde"
                )


            # RSI

            if rsi:

                if 45 <= rsi <= 65:

                    score += 5

                    reasons.append(
                        "RSI dengeli bölgede"
                    )


                elif rsi > 75:

                    score -= 5

                    reasons.append(
                        "RSI aşırı alım bölgesinde"
                    )


                elif rsi < 30:

                    score += 3

                    reasons.append(
                        "RSI aşırı satım bölgesinde"
                    )


            # MACD

            if macd and signal:

                if macd > signal:

                    score += 5

                    reasons.append(
                        "MACD pozitif"
                    )

                else:

                    score -= 5

                    reasons.append(
                        "MACD zayıf"
                    )



    except Exception as e:

        reasons.append(
            "BIST teknik veri alınamadı"
        )



    # =================================================
    # 2 - MOMENTUM VE HACİM (25 PUAN)
    # =================================================

    try:

        df = get_history("XU100.IS")


        momentum = get_momentum(df)

        volume = get_volume(df)

        avg_volume = get_average_volume(df)



        if momentum > 0:

            score += 10

            reasons.append(
                "Piyasa momentumu pozitif"
            )

        else:

            score -= 5

            reasons.append(
                "Momentum zayıf"
            )



        if volume > avg_volume:

            score += 8

            reasons.append(
                "Hacim destekli hareket"
            )

        else:

            score -= 5

            reasons.append(
                "Hacim teyidi zayıf"
            )



        volatility = get_volatility(df)


        if volatility:

            if volatility < 3:

                score += 5

                reasons.append(
                    "Volatilite düşük, risk kontrollü"
                )

            elif volatility > 6:

                score -= 0

                reasons.append(
                    "Volatilite yüksek"
                )


    except:

        pass



    # =================================================
    # 3 - MAKRO FAKTÖRLER (25 PUAN)
    # =================================================


    macro = get_macro_data()



    # USD

    usd = safe_float(
        macro.get("usd_change")
    )


    if usd > 0.5:

        score -= 5

        reasons.append(
            "Dolar baskısı devam ediyor"
        )


    elif usd < -0.2:

        score += 8

        reasons.append(
            "Dolar olumlu etkiliyor"
        )



    # Altın

    gold = safe_float(
        macro.get("gold_change")
    )


    if gold > 1:

        score -= 1

        reasons.append(
            "Altın güçlü, güvenli liman talebi var"
        )



    # Petrol


    brent = safe_float(
        macro.get("brent_change")
    )


    if brent > 1:

        score -= 3

        reasons.append(
            "Petrol maliyet baskısı oluşturuyor"
        )


    elif brent < -1:

        score += 3

        reasons.append(
            "Petrol geriliyor"
        )



    # =================================================
    # SON NORMALİZASYON
    # =================================================


    score = max(
        0,
        min(
            int(score),
            100
        )
    )
    print("AI SCORE:", score)
    print("AI REASONS:")

    for r in reasons:
        print("-", r)

    return score, reasons




# =====================================================
# AI YORUM
# =====================================================

def get_market_comment(score):

    if score >= 75:
        return "🟢 Güçlü pozitif piyasa görünümü"

    elif score >= 55:
        return "🟡 Temkinli pozitif görünüm"

    elif score >= 35:
        return "🟠 Nötr / temkinli piyasa"

    elif score >= 20:
        return "🔴 Zayıf piyasa görünümü"

    else:
        return "🚨 Kritik risk seviyesi"
        
def get_macro_comment():

    macro = get_macro_data()

    yorumlar = []
    # BIST100

    bist = safe_float(
        macro.get("bist_change")
    )

    if bist > 0:

        yorumlar.append(
            ("BIST100",
             f"+{bist}%",
             "🟢 Günlük görünüm pozitif")
        )

    elif bist < 0:

        yorumlar.append(
            ("BIST100",
             f"{bist}%",
             "🔴 Günlük baskı var")
        )

    else:

        yorumlar.append(
            ("BIST100",
             "Yatay",
             "🟡 Kararsız")
        )


    # Gram Altın

    gram = macro.get("gram")

    if gram:

        yorumlar.append(
            ("Gram Altın",
             f"{gram} TL",
             "🟡 Güçlü")
        )

    usd = safe_float(macro.get("usd_change"))

    if usd > 0:
        yorumlar.append(
            ("Dolar", "Yükseliş", "🔴 BIST için negatif")
        )
    else:
        yorumlar.append(
            ("Dolar", "Sakin", "🟢 BIST için pozitif")
        )


    gold = safe_float(macro.get("gold_change"))

    if gold > 0:
        yorumlar.append(
            ("Altın", "Güçlü", "🟡 Güvenli Liman Talebi Var")
        )


    brent = safe_float(macro.get("brent_change"))

    if brent > 1:
        yorumlar.append(
            ("Petrol", "Yükseliyor", "🔴 Maliyet baskısı")
        )


    return yorumlar