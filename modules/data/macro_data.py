import yfinance as yf


# =========================================================
# GÜVENLİ SAYI DÖNÜŞÜMÜ
# =========================================================

def safe_float(value):

    try:
        return float(value)

    except:
        return None


# =========================================================
# FİYAT + GÜNLÜK DEĞİŞİM
# =========================================================

def get_price(symbol):

    try:

        data = yf.Ticker(symbol).history(
            period="5d",
            auto_adjust=False
        )

        if data is None or data.empty:
            return None, None

        close = data["Close"].dropna()

        if len(close) < 2:
            return None, None

        last = float(close.iloc[-1])
        prev = float(close.iloc[-2])

        if prev == 0:
            return None, None

        change = ((last - prev) / prev) * 100

        return round(last, 2), round(change, 2)

    except Exception as e:

        print(f"{symbol} veri hatası: {e}")

        return None, None


# =========================================================
# MAKRO VERİLER
# =========================================================

def get_macro_data():

    # -----------------------------------------------------
    # BIST
    # -----------------------------------------------------

    bist, bist_change = get_price("XU100.IS")


    # -----------------------------------------------------
    # ALTIN
    # -----------------------------------------------------

    gold, gold_change = get_price("GC=F")


    # -----------------------------------------------------
    # USD / TRY
    # -----------------------------------------------------

    usd, usd_change = get_price("USDTRY=X")


    # -----------------------------------------------------
    # EUR / TRY
    # -----------------------------------------------------

    eur, eur_change = get_price("EURTRY=X")


    # -----------------------------------------------------
    # BRENT
    # -----------------------------------------------------

    brent, brent_change = get_price("BZ=F")


    # -----------------------------------------------------
    # GÜMÜŞ
    # -----------------------------------------------------

    silver, silver_change = get_price("SI=F")


    # -----------------------------------------------------
    # GRAM ALTIN HESABI
    # -----------------------------------------------------

    gram = None

    if gold is not None and usd is not None:

        try:

            gram = round(
                (gold * usd) / 31.1035,
                2
            )

        except:

            gram = None


    # -----------------------------------------------------
    # SONUÇ
    # -----------------------------------------------------

    return {

        "bist": bist,
        "bist_change": bist_change,

        "gold": gold,
        "gold_change": gold_change,

        "usd": usd,
        "usd_change": usd_change,

        "eur": eur,
        "eur_change": eur_change,

        "brent": brent,
        "brent_change": brent_change,

        "silver": silver,
        "silver_change": silver_change,

        "gram": gram,

        # -------------------------------------------------
        # ŞİMDİLİK VERİ KAYNAĞI BAĞLANMADI
        # -------------------------------------------------

        "fed": None,
        "inflation": None,
        "tcmb": None,
        "geopolitical": None,

    }