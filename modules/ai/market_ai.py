from modules.data.macro_data import get_macro_data


def get_market_score():

    macro = get_macro_data()

    score = 50
    reasons = []

    # USD/TL
    try:
        if macro["usd_change"] > 0:
            score -= 10
            reasons.append("USD yükseliyor")
        else:
            score += 10
            reasons.append("USD geriliyor")
    except:
        pass

    # Ons Altın
    try:
        if macro["gold_change"] > 0:
            score -= 8
            reasons.append("Altın yükseliyor")
        else:
            score += 8
            reasons.append("Altın geriliyor")
    except:
        pass

    # Brent Petrol
    try:
        if macro["brent_change"] > 0:
            score -= 6
            reasons.append("Petrol yükseliyor")
        else:
            score += 6
            reasons.append("Petrol geriliyor")
    except:
        pass

    score = max(0, min(score, 100))

    return score, reasons