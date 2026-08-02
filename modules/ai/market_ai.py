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

    score = 0
    reasons = []

    # =================================================
    # 1 - BIST TEKNİK ANALİZ (30 PUAN)
    # =================================================

    try:

        df = get_history("XU100.IS")

        if df is not None and not df.empty:

            trend = get_trend(df)
            rsi = get_rsi(df)
            macd, signal = get_macd(df)

            # -------------------------
            # TREND - 15 PUAN
            # -------------------------

            if trend == "Güçlü Yükseliş":

                score += 15
                reasons.append("BIST güçlü yükseliş trendinde")

            elif trend == "Yükseliş":

                score += 10
                reasons.append("BIST yükseliş trendinde")

            elif trend == "Düşüş":

                score += 5
                reasons.append("BIST düşüş trendinde")

            elif trend == "Güçlü Düşüş":

                score += 0
                reasons.append("BIST güçlü düşüş trendinde")

            # -------------------------
            # RSI - 7 PUAN
            # -------------------------

            if rsi:

                if 45 <= rsi <= 65:

                    score += 7
                    reasons.append("RSI dengeli bölgede")

                elif 35 <= rsi < 45:

                    score += 5
                    reasons.append("RSI zayıf ama toparlanabilir")

                elif rsi < 30:

                    score += 4
                    reasons.append("RSI aşırı satım bölgesinde")

                elif 65 < rsi <= 75:

                    score += 4
                    reasons.append("RSI güçlü fakat dikkat edilmeli")

                elif rsi > 75:

                    score += 1
                    reasons.append("RSI aşırı alım bölgesinde")

            # -------------------------
            # MACD - 8 PUAN
            # -------------------------

            if macd is not None and signal is not None:

                if macd > signal:

                    score += 8
                    reasons.append("MACD pozitif")

                else:

                    score += 2
                    reasons.append("MACD zayıf")


    except Exception:

        reasons.append("BIST teknik veri alınamadı")


    # =================================================
    # 2 - MOMENTUM / HACİM / VOLATİLİTE (30 PUAN)
    # =================================================

    try:

        df = get_history("XU100.IS")

        if df is not None and not df.empty:

            momentum = safe_float(get_momentum(df))
            volume = safe_float(get_volume(df))
            avg_volume = safe_float(get_average_volume(df))
            volatility = safe_float(get_volatility(df))

            # -------------------------
            # MOMENTUM - 15 PUAN
            # -------------------------

            if momentum > 3:

                score += 15
                reasons.append("Piyasa momentumu güçlü")

            elif momentum > 0:

                score += 10
                reasons.append("Piyasa momentumu pozitif")

            elif momentum > -3:

                score += 5
                reasons.append("Momentum zayıf")

            else:

                score += 0
                reasons.append("Momentum negatif")

            # -------------------------
            # HACİM - 8 PUAN
            # -------------------------

            if avg_volume > 0:

                volume_ratio = volume / avg_volume

                if volume_ratio >= 1.20:

                    score += 8
                    reasons.append("Hacim güçlü şekilde destekliyor")

                elif volume_ratio >= 1.00:

                    score += 6
                    reasons.append("Hacim hareketi destekliyor")

                elif volume_ratio >= 0.80:

                    score += 3
                    reasons.append("Hacim desteği sınırlı")

                else:

                    score += 0
                    reasons.append("Hacim teyidi zayıf")

            # -------------------------
            # VOLATİLİTE - 7 PUAN
            # -------------------------

            if volatility:

                if volatility < 3:

                    score += 7
                    reasons.append("Volatilite düşük, risk kontrollü")

                elif volatility < 5:

                    score += 5
                    reasons.append("Volatilite normal")

                elif volatility < 7:

                    score += 3
                    reasons.append("Volatilite yüksek")

                else:

                    score += 1
                    reasons.append("Volatilite çok yüksek")


    except Exception:

        reasons.append("Momentum/hacim verisi alınamadı")


    # =================================================
    # 3 - MAKRO FAKTÖRLER (40 PUAN)
    # =================================================

    try:

        macro = get_macro_data()

        # -------------------------
        # USD/TRY - 10 PUAN
        # -------------------------

        usd = safe_float(
            macro.get("usd_change")
        )

        if usd < -0.5:

            score += 10
            reasons.append("Dolar geriliyor, BIST açısından olumlu")

        elif usd <= 0.2:

            score += 7
            reasons.append("Dolar hareketi sınırlı")

        elif usd <= 0.5:

            score += 4
            reasons.append("Dolar hafif yükseliyor")

        else:

            score += 0
            reasons.append("Dolar baskısı yüksek")

        # -------------------------
        # ALTIN - 5 PUAN
        # -------------------------

        gold = safe_float(
            macro.get("gold_change")
        )

        if gold < 0:

            score += 5
            reasons.append("Altın geriliyor, risk iştahı destekleniyor")

        elif gold <= 1:

            score += 3
            reasons.append("Altın yatay")

        else:

            score += 1
            reasons.append("Altın güçlü, güvenli liman talebi var")

        # -------------------------
        # BRENT - 5 PUAN
        # -------------------------

        brent = safe_float(
            macro.get("brent_change")
        )

        if brent < -1:

            score += 5
            reasons.append("Petrol geriliyor")

        elif brent <= 1:

            score += 3
            reasons.append("Petrol hareketi sınırlı")

        else:

            score += 1
            reasons.append("Petrol maliyet baskısı oluşturuyor")

        # -------------------------
        # BIST GÜNLÜK - 20 PUAN
        # -------------------------

        bist = safe_float(
            macro.get("bist_change")
        )

        if bist > 1:

            score += 20
            reasons.append("BIST günlük performansı güçlü")

        elif bist > 0:

            score += 14
            reasons.append("BIST günlük performansı pozitif")

        elif bist > -1:

            score += 7
            reasons.append("BIST günlük performansı yatay/zayıf")

        else:

            score += 0
            reasons.append("BIST günlük performansı negatif")


    except Exception:

        reasons.append("Makro veri alınamadı")


    # =================================================
    # SONUÇ - 100 PUANA NORMALİZE
    # =================================================

    score = max(
        0,
        min(
            int(score),
            100
        )
    )

    print("AI MARKET SCORE:", score)

    print("AI MARKET REASONS:")

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