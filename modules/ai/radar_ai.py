from modules.data.yahoo_data import get_stock_analysis


# ==========================================================
# FIRSAT RADARI İZLEME HAVUZU
# ==========================================================

WATCHLIST = [

    "AEFES",
    "AGHOL",
    "AKSA",
    "AKSEN",
    "AKCNS",
    "ASELS",
    "ASTOR",
    "BIMAS",
    "BINBN",
    "CCOLA",
    "CVKMD",
    "EREGL",
    "FROTO",
    "GESAN",
    "KARCL",
    "KCHOL",
    "KCAER",
    "KRDMD",
    "MASFN",
    "MGROS",
    "ODAS",
    "ODINE",
    "OYAKC",
    "PASEU",
    "PGSUS",
    "SISE",
    "SOKM",
    "THYAO",
    "TKFEN",
    "TOASO",
    "TUPRS",
    "YEOTK"

]


# ==========================================================
# RİSK SKORU
# ==========================================================

def calculate_risk_score(analysis):

    risk = 0
    reasons = []

    try:

        price = analysis.get("price")
        change = analysis.get("change")
        rsi = analysis.get("rsi")
        support = analysis.get("support")
        resistance = analysis.get("resistance")

        # --------------------------------------------------
        # 1. GÜNLÜK SERT DÜŞÜŞ
        # --------------------------------------------------

        if change is not None:

            change = float(change)

            if change <= -7:

                risk += 12
                reasons.append(
                    f"Günlük sert düşüş (%{change:.2f})"
                )

            elif change <= -5:

                risk += 8
                reasons.append(
                    f"Günlük güçlü satış (%{change:.2f})"
                )

            elif change <= -3:

                risk += 4
                reasons.append(
                    f"Günlük satış baskısı (%{change:.2f})"
                )


        # --------------------------------------------------
        # 2. RSI AŞIRI ALIM
        # --------------------------------------------------

        if rsi is not None:

            rsi = float(rsi)

            if rsi >= 80:

                risk += 12
                reasons.append(
                    f"RSI aşırı alım bölgesinde ({rsi:.1f})"
                )

            elif rsi >= 75:

                risk += 8
                reasons.append(
                    f"RSI yüksek ({rsi:.1f})"
                )

            elif rsi >= 70:

                risk += 5
                reasons.append(
                    f"RSI aşırı alım bölgesine yakın ({rsi:.1f})"
                )


        # --------------------------------------------------
        # 3. DİRENCE UZAKLIK
        # --------------------------------------------------

        if (
            price is not None
            and resistance is not None
            and float(resistance) > 0
        ):

            price = float(price)
            resistance = float(resistance)

            distance_to_resistance = (
                (resistance - price)
                / resistance
            ) * 100

            # Fiyat direnci geçmişse risk üretme
            if distance_to_resistance >= 0:

                if distance_to_resistance <= 1:

                    risk += 10
                    reasons.append(
                        "Dirence çok yakın"
                    )

                elif distance_to_resistance <= 3:

                    risk += 7
                    reasons.append(
                        "Dirence yakın"
                    )

                elif distance_to_resistance <= 5:

                    risk += 3
                    reasons.append(
                        "Direnç bölgesine yaklaşıyor"
                    )


        # --------------------------------------------------
        # 4. DESTEĞE YAKINLIK
        # --------------------------------------------------

        if (
            price is not None
            and support is not None
            and float(support) > 0
        ):

            price = float(price)
            support = float(support)

            distance_to_support = (
                (price - support)
                / support
            ) * 100

            if 0 <= distance_to_support <= 3:

                risk -= 5
                reasons.append(
                    "Desteğe yakın"
                )

            elif 3 < distance_to_support <= 5:

                risk -= 2
                reasons.append(
                    "Destek bölgesine yakın"
                )


        # --------------------------------------------------
        # SINIRLAR
        # --------------------------------------------------

        risk = max(
            0,
            min(risk, 30)
        )

        return round(risk, 1), reasons

    except Exception as e:

        print(
            f"[RADAR RISK HATA] "
            f"{type(e).__name__}: {e}"
        )

        return 0, []
# ==========================================================
# FIRSAT SKORUNA GÖRE KARAR
# ==========================================================

def get_radar_recommendation(score):

    score = float(score)

    if score >= 85:
        return "🟢 Güçlü Fırsat"

    elif score >= 75:
        return "🟢 Fırsat"

    elif score >= 65:
        return "🟡 İzle"

    elif score >= 55:
        return "🟠 Riskli"

    else:
        return "🔴 Uzak Dur"

# ==========================================================
# FIRSAT RADARI SKORU
# ==========================================================

def calculate_radar_score(analysis):

    score = 0
    reasons = []

    try:

        # --------------------------------------------------
        # TREND %25
        # --------------------------------------------------

        trend_strength = float(
            analysis.get(
                "trend_strength",
                50
            )
        )

        score += trend_strength * 0.25

        if trend_strength >= 80:

            reasons.append(
                "Trend güçlü"
            )


        # --------------------------------------------------
        # MOMENTUM %20
        # --------------------------------------------------

        momentum = float(
            analysis.get(
                "momentum_score",
                50
            )
        )

        score += momentum * 0.20

        if momentum >= 80:

            reasons.append(
                "Momentum çok güçlü"
            )

        elif momentum >= 70:

            reasons.append(
                "Momentum güçlü"
            )


        # --------------------------------------------------
        # HACİM %15
        # --------------------------------------------------

        volume = float(
            analysis.get(
                "volume_score",
                50
            )
        )

        score += volume * 0.15

        if volume >= 80:

            reasons.append(
                "Hacim güçlü"
            )


        # --------------------------------------------------
        # AI SCORE %20
        # --------------------------------------------------

        ai = float(
            analysis.get(
                "score",
                50
            )
        )

        score += ai * 0.20

        if ai >= 85:

            reasons.append(
                "AI skoru çok güçlü"
            )

        elif ai >= 75:

            reasons.append(
                "AI skoru güçlü"
            )


        # --------------------------------------------------
        # RSI %10
        # --------------------------------------------------

        rsi = analysis.get("rsi")

        if rsi is not None:

            rsi = float(rsi)

            # En sağlıklı bölge
            if 45 <= rsi <= 65:

                score += 10

                reasons.append(
                    "RSI sağlıklı bölgede"
                )

            # Hafif momentum
            elif 40 <= rsi < 45:

                score += 7

            elif 65 < rsi <= 70:

                score += 7

            # Çok düşük RSI
            elif rsi < 35:

                score += 5

                reasons.append(
                    "RSI düşük, toparlanma potansiyeli var"
                )


        # --------------------------------------------------
        # DESTEK BÖLGESİ %10
        # --------------------------------------------------

        price = analysis.get("price")
        support = analysis.get("support")

        if (
            price is not None
            and support is not None
            and float(support) > 0
        ):

            price = float(price)
            support = float(support)

            distance = (
                abs(price - support)
                / support
            )

            if distance <= 0.03:

                score += 10

                reasons.append(
                    "Destek bölgesinde"
                )

            elif distance <= 0.05:

                score += 5

                reasons.append(
                    "Desteğe yakın"
                )


        # --------------------------------------------------
        # HAM RADAR SKORU
        # --------------------------------------------------

        score = max(
            0,
            min(score, 100)
        )

        # --------------------------------------------------
        # RİSK
        # --------------------------------------------------

        risk_score, risk_reasons = calculate_risk_score(
            analysis
        )

        # --------------------------------------------------
        # RİSK CEZASI
        # --------------------------------------------------

        risk_adjusted_score = score - risk_score

        risk_adjusted_score = max(
            0,
            min(risk_adjusted_score, 100)
        )

        # Risk nedenlerini ayrı ekle
        for reason in risk_reasons:

            reasons.append(
                f"⚠️ {reason}"
            )


        return (
            round(score, 1),
            round(risk_score, 1),
            round(risk_adjusted_score, 1),
            reasons
        )


    except Exception as e:

        print(
            f"[RADAR SCORE HATA] "
            f"{type(e).__name__}: {e}"
        )

        return 50, 0, 50, []


# ==========================================================
# RADAR VERİLERİNİ GETİR
# ==========================================================

def get_radar_picks():

    radar = []

    for symbol in WATCHLIST:

        try:

            analysis = get_stock_analysis(symbol)

            if analysis is None:

                print(
                    f"[RADAR] {symbol} -> veri yok"
                )

                continue


            # ------------------------------------------------
            # SKORLAR
            # ------------------------------------------------

            (
                radar_score,
                risk_score,
                risk_adjusted_score,
                reasons

            ) = calculate_radar_score(
                analysis
            )
            radar_recommendation = get_radar_recommendation(
                risk_adjusted_score
            )


            # ------------------------------------------------
            # VERİ
            # ------------------------------------------------

            stock = {

                "symbol":
                    symbol,

                "price":
                    analysis.get(
                        "price"
                    ),

                "change":
                    analysis.get(
                        "change"
                    ),

                "sector":
                    analysis.get(
                        "sector",
                        "Diğer"
                    ),

                "recommendation":
                    radar_recommendation,
                    
                "score":
                    analysis.get(
                        "score",
                        50
                    ),

                "trend":
                    analysis.get(
                        "trend",
                        "Nötr"
                    ),

                "trend_strength":
                    analysis.get(
                        "trend_strength",
                        50
                    ),

                "momentum_score":
                    analysis.get(
                        "momentum_score",
                        50
                    ),

                "volume_score":
                    analysis.get(
                        "volume_score",
                        50
                    ),

                "rsi":
                    analysis.get(
                        "rsi"
                    ),

                "support":
                    analysis.get(
                        "support"
                    ),

                "resistance":
                    analysis.get(
                        "resistance"
                    ),

                "radar_score":
                    radar_score,

                "risk_score":
                    risk_score,

                "risk_adjusted_score":
                    risk_adjusted_score,

                "reasons":
                    reasons

            }


            radar.append(stock)


        except Exception as e:

            print(
                f"[RADAR HATA] "
                f"{symbol}: "
                f"{type(e).__name__}: {e}"
            )

            continue


    # ======================================================
    # RİSK AYARLI SKORA GÖRE SIRALA
    # ======================================================

    radar.sort(

        key=lambda x:
            x["risk_adjusted_score"],

        reverse=True

    )


    return radar