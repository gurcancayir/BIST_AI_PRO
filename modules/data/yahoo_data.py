import pandas as pd
import yfinance as yf
import streamlit as st
SEKTOR_MAP = {

    "TUPRS.IS": "Enerji",
    "AKSEN.IS": "Enerji",
    "ENJSA.IS": "Enerji",
    "ODAS.IS": "Enerji",

    "ASELS.IS": "Savunma",
    "ASTOR.IS": "Enerji",
    "OTKAR.IS": "Savunma",
    "SDTTR.IS": "Savunma",
    "ALTNY.IS": "Savunma",

    "THYAO.IS": "Ulaştırma",
    "PGSUS.IS": "Ulaştırma",

    "BIMAS.IS": "Perakende",
    "MGROS.IS": "Perakende",
    "SOKM.IS": "Perakende",

    "FROTO.IS": "Otomotiv",
    "TOASO.IS": "Otomotiv",
    "DOAS.IS": "Otomotiv",
    
    "AKBNK.IS": "Banka",
    "GARAN.IS": "Banka",

    "SISE.IS": "Sanayi",
    "EREGL.IS": "Sanayi",
    "KCAER.IS": "Sanayi",

    "AGHOL.IS": "Holding",
    "KCHOL.IS": "Holding",
    "SAHOL.IS": "Holding",
    "DOHOL.IS": "Holding",
    "ALARK.IS": "Holding",

}
# ----------------------------------------------------------
# HACİM SKORU
# ----------------------------------------------------------

def calculate_volume_score(data):

    try:

        avg_volume = data["Volume"].rolling(20).mean().iloc[-1]

        current_volume = data["Volume"].iloc[-1]

        ratio = current_volume / avg_volume


        if ratio >= 2:
            return 100

        elif ratio >= 1.5:
            return 85

        elif ratio >= 1:
            return 70

        elif ratio >= 0.7:
            return 50

        else:
            return 30


    except:

        return 50

# ----------------------------------------------------------
# 60 GÜNLÜK MOMENTUM SKORU
# ----------------------------------------------------------

def calculate_momentum_60_score(data):

    try:

        price_now = data["Close"].iloc[-1]

        price_old = data["Close"].iloc[-60]


        change = (
            (price_now / price_old) - 1
        ) * 100


        if change >= 30:
            return 100

        elif change >= 15:
            return 85

        elif change >= 5:
            return 70

        elif change >= 0:
            return 55

        else:
            return 30


    except:

        return 50

# ----------------------------------------------------------
# MOMENTUM SKORU
# ----------------------------------------------------------
# ----------------------------------------------------------
# GELİŞTİRİLMİŞ MOMENTUM SKORU
# ----------------------------------------------------------

def calculate_momentum_score(data):

    try:
        if data is None:
            print("[MOMENTUM] data None")
            return 50

        if len(data) < 61:
            print(f"[MOMENTUM] Yetersiz veri: {len(data)}")
            return 50

        close = data["Close"]

        price_now = float(close.iloc[-1])
        price_20 = float(close.iloc[-21])
        price_60 = float(close.iloc[-61])

        change_20 = ((price_now / price_20) - 1) * 100
        change_60 = ((price_now / price_60) - 1) * 100

        # 20 günlük skor
        if change_20 >= 15:
            score_20 = 100
        elif change_20 >= 10:
            score_20 = 90
        elif change_20 >= 5:
            score_20 = 80
        elif change_20 >= 2:
            score_20 = 70
        elif change_20 >= 0:
            score_20 = 60
        elif change_20 >= -3:
            score_20 = 50
        elif change_20 >= -7:
            score_20 = 40
        else:
            score_20 = 25

        # 60 günlük skor
        if change_60 >= 30:
            score_60 = 100
        elif change_60 >= 20:
            score_60 = 90
        elif change_60 >= 10:
            score_60 = 80
        elif change_60 >= 5:
            score_60 = 70
        elif change_60 >= 0:
            score_60 = 60
        elif change_60 >= -5:
            score_60 = 50
        elif change_60 >= -10:
            score_60 = 40
        else:
            score_60 = 25

        momentum_score = (
            score_20 * 0.45
            +
            score_60 * 0.55
        )

        print(
            f"[MOMENTUM] "
            f"20G={change_20:.2f}% | "
            f"60G={change_60:.2f}% | "
            f"SKOR={momentum_score:.1f}"
        )

        return round(momentum_score, 1)

    except Exception as e:

        print(
            f"[MOMENTUM HATA] {type(e).__name__}: {e}"
        )

        return 50
    
        # --------------------------------------------------
        # 60 GÜNLÜK MOMENTUM
        # --------------------------------------------------

        if change_60 >= 30:
            score_60 = 100

        elif change_60 >= 20:
            score_60 = 90

        elif change_60 >= 10:
            score_60 = 80

        elif change_60 >= 5:
            score_60 = 70

        elif change_60 >= 0:
            score_60 = 60

        elif change_60 >= -5:
            score_60 = 50

        elif change_60 >= -10:
            score_60 = 40

        else:
            score_60 = 25


        # --------------------------------------------------
        # 20 GÜN + 60 GÜN BİRLİKTE
        # --------------------------------------------------

        momentum_score = (
            score_20 * 0.45
            +
            score_60 * 0.55
        )


        return round(
            momentum_score,
            1
        )


    except Exception:

        return 50


def get_momentum_details(data):

    try:

        if data is None or len(data) < 61:
            return {
                "momentum_20": None,
                "momentum_60": None
            }

        price_now = float(data["Close"].iloc[-1])

        price_20 = float(data["Close"].iloc[-21])
        price_60 = float(data["Close"].iloc[-61])

        momentum_20 = (
            (price_now / price_20) - 1
        ) * 100

        momentum_60 = (
            (price_now / price_60) - 1
        ) * 100

        return {
            "momentum_20": round(momentum_20, 2),
            "momentum_60": round(momentum_60, 2)
        }

    except Exception:

        return {
            "momentum_20": None,
            "momentum_60": None
        }
# ----------------------------------------------------------
# AYARLAR
# ----------------------------------------------------------

HISTORY_PERIOD = "2y"
INTERVAL = "1d"


# ----------------------------------------------------------
# VERİ İNDİR
# ----------------------------------------------------------

@st.cache_data(ttl=1800)

@st.cache_data(ttl=1800)
def get_history(symbol):

    """
    Yahoo Finance'den hisse geçmiş verisini indirir.
    Boş/NaN kapanış kayıtlarını temizler.
    """

    try:

        if not symbol.endswith(".IS"):
            symbol = symbol + ".IS"

        ticker = yf.Ticker(symbol)

        df = ticker.history(
            period=HISTORY_PERIOD,
            interval=INTERVAL,
            auto_adjust=True
        )

        if df is None or df.empty:
            return None

        # --------------------------------------------------
        # GEÇERSİZ / BOŞ KAYITLARI TEMİZLE
        # --------------------------------------------------

        required_columns = [
            "Open",
            "High",
            "Low",
            "Close",
            "Volume"
        ]

        existing_columns = [
            col for col in required_columns
            if col in df.columns
        ]

        if "Close" not in existing_columns:
            print(
                f"[YAHOO HATA] {symbol} -> Close kolonu yok"
            )
            return None

        df = df.dropna(
            subset=existing_columns
        )

        if df.empty:
            return None

        # Son fiyatın gerçekten geçerli olduğundan emin ol
        if pd.isna(df["Close"].iloc[-1]):
            print(
                f"[YAHOO HATA] {symbol} -> Son Close NaN"
            )
            return None

        print(
            f"[YAHOO OK] {symbol} -> "
            f"{len(df)} kayıt | "
            f"Son fiyat: {float(df['Close'].iloc[-1]):.2f}"
        )

        return df

    except Exception as e:

        print(
            f"[YAHOO HATA] {symbol}: "
            f"{type(e).__name__}: {e}"
        )

        return None
# ----------------------------------------------------------
# ŞİRKET BİLGİLERİ
# ----------------------------------------------------------

@st.cache_data(ttl=86400)
def get_company_info(symbol):

    try:

        if not symbol.endswith(".IS"):
            symbol = symbol + ".IS"

        ticker = yf.Ticker(symbol)

        info = ticker.info or {}

        return {

            "company": info.get("longName", "-"),

            "sector": info.get("sector",""),

            "industry": info.get("industry", "-"),

            "market_cap": info.get("marketCap", 0),

            "employees": info.get("fullTimeEmployees", "-"),

            "currency": info.get("currency", "TRY")

        }

    except Exception:

        return {

            "company": "-",

            "sector": "-",

            "industry": "-",

            "market_cap": 0,

            "employees": "-",

            "currency": "TRY"

        }


# ----------------------------------------------------------
# GÜNCEL FİYAT
# ----------------------------------------------------------

def get_last_price(df):

    if df is None:
        return None

    return round(float(df["Close"].iloc[-1]), 2)


# ----------------------------------------------------------
# GÜNLÜK DEĞİŞİM
# ----------------------------------------------------------

def get_daily_change(df):

    if df is None:
        return 0

    if len(df) < 2:
        return 0

    today = float(df["Close"].iloc[-1])

    yesterday = float(df["Close"].iloc[-2])

    change = ((today - yesterday) / yesterday) * 100

    return round(change, 2)


# ----------------------------------------------------------
# HACİM
# ----------------------------------------------------------

def get_volume(df):

    if df is None:
        return 0

    return int(df["Volume"].iloc[-1])


# ----------------------------------------------------------
# ORTALAMA HACİM (20 Gün)
# ----------------------------------------------------------

def get_average_volume(df):

    if df is None:
        return 0

    return int(df["Volume"].tail(20).mean())
# ----------------------------------------------------------
# EMA
# ----------------------------------------------------------

# ----------------------------------------------------------
# EMA
# ----------------------------------------------------------

def get_ema(df, period=20):

    if df is None:
        return None

    ema = df["Close"].ewm(
        span=period,
        adjust=False
    ).mean()

    return round(float(ema.iloc[-1]), 2)
# ----------------------------------------------------------
# SMA
# ----------------------------------------------------------

def get_sma(df, period=20):

    if df is None:
        return None

    sma = df["Close"].rolling(period).mean()

    return round(float(sma.iloc[-1]), 2)


# ----------------------------------------------------------
# RSI
# ----------------------------------------------------------


def get_rsi(df, period=14):

    if df is None:
        return None

    delta = df["Close"].diff()

    gain = delta.clip(lower=0)

    loss = -delta.clip(upper=0)


    avg_gain = gain.ewm(
        alpha=1/period,
        adjust=False
    ).mean()


    avg_loss = loss.ewm(
        alpha=1/period,
        adjust=False
    ).mean()


    if avg_loss.iloc[-1] == 0:
        return 100


    rs = avg_gain / avg_loss

    rsi = 100 - (100 / (1 + rs))


    return round(float(rsi.iloc[-1]), 2)
# ----------------------------------------------------------
# MACD
# ----------------------------------------------------------

def get_macd(df):

    if df is None:
        return None, None

    ema12 = df["Close"].ewm(
        span=12,
        adjust=False
    ).mean()

    ema26 = df["Close"].ewm(
        span=26,
        adjust=False
    ).mean()

    macd = ema12 - ema26

    signal = macd.ewm(
        span=9,
        adjust=False
    ).mean()

    return (

        round(float(macd.iloc[-1]), 2),

        round(float(signal.iloc[-1]), 2)

    )


# ----------------------------------------------------------
# BOLLINGER
# ----------------------------------------------------------

def get_bollinger(df, period=20):

    if df is None:
        return None, None

    sma = df["Close"].rolling(period).mean()

    std = df["Close"].rolling(period).std()

    upper = sma + (std * 2)

    lower = sma - (std * 2)

    return (

        round(float(upper.iloc[-1]), 2),

        round(float(lower.iloc[-1]), 2)

    )


# ----------------------------------------------------------
# ATR
# ----------------------------------------------------------

def get_atr(df, period=14):

    if df is None:
        return None

    high_low = df["High"] - df["Low"]

    high_close = (df["High"] - df["Close"].shift()).abs()

    low_close = (df["Low"] - df["Close"].shift()).abs()

    tr = pd.concat(

        [

            high_low,

            high_close,

            low_close

        ],

        axis=1

    ).max(axis=1)

    atr = tr.rolling(period).mean()

    return round(float(atr.iloc[-1]), 2)


# ----------------------------------------------------------
# MOMENTUM
# ----------------------------------------------------------

def get_momentum(df, period=10):

    if df is None:
        return None

    momentum = (

        df["Close"]

        -

        df["Close"].shift(period)

    )

    return round(float(momentum.iloc[-1]), 2)


# ----------------------------------------------------------
# VOLATILITY
# ----------------------------------------------------------

def get_volatility(df):

    if df is None:
        return None

    returns = df["Close"].pct_change()

    volatility = returns.std() * 100

    return round(float(volatility), 2)
# ----------------------------------------------------------
# DESTEK
# ----------------------------------------------------------

def get_support(df, period=20):

    if df is None:
        return None

    support = df["Low"].tail(period).min()

    return round(float(support), 2)



# ----------------------------------------------------------
# DİRENÇ
# ----------------------------------------------------------

def get_resistance(df, period=20):

    if df is None:
        return None

    resistance = df["High"].tail(period).max()

    return round(float(resistance), 2)
# ----------------------------------------------------------
# AI TREND GÜCÜ SKORU
# ----------------------------------------------------------

# ----------------------------------------------------------
# GELİŞMİŞ TREND GÜCÜ SKORU
# ----------------------------------------------------------

def calculate_trend_strength(df):

    try:

        if df is None or len(df) < 220:
            return 50

        close = df["Close"]

        price = float(close.iloc[-1])

        ema20_series = close.ewm(
            span=20,
            adjust=False
        ).mean()

        ema50_series = close.ewm(
            span=50,
            adjust=False
        ).mean()

        ema200_series = close.ewm(
            span=200,
            adjust=False
        ).mean()

        ema20 = float(ema20_series.iloc[-1])
        ema50 = float(ema50_series.iloc[-1])
        ema200 = float(ema200_series.iloc[-1])

        # --------------------------------------------------
        # 1. EMA SIRALAMASI - 25 PUAN
        # --------------------------------------------------

        if ema20 > ema50 > ema200:
            ema_order_score = 25

        elif ema20 > ema50:
            ema_order_score = 18

        elif ema20 > ema200:
            ema_order_score = 12

        elif ema50 > ema200:
            ema_order_score = 8

        elif ema20 < ema50 < ema200:
            ema_order_score = 0

        else:
            ema_order_score = 5


        # --------------------------------------------------
        # 2. FİYATIN EMA'LARA GÖRE KONUMU - 25 PUAN
        # --------------------------------------------------

        price_score = 0

        if price > ema20:
            price_score += 8

        if price > ema50:
            price_score += 8

        if price > ema200:
            price_score += 9


        # --------------------------------------------------
        # 3. EMA20 - EMA50 UZAKLIĞI - 15 PUAN
        # --------------------------------------------------

        spread_20_50 = (
            (ema20 / ema50) - 1
        ) * 100

        if spread_20_50 >= 8:
            spread_score = 15

        elif spread_20_50 >= 5:
            spread_score = 12

        elif spread_20_50 >= 3:
            spread_score = 9

        elif spread_20_50 >= 1:
            spread_score = 6

        elif spread_20_50 >= 0:
            spread_score = 3

        else:
            spread_score = 0


        # --------------------------------------------------
        # 4. EMA50 - EMA200 UZAKLIĞI - 15 PUAN
        # --------------------------------------------------

        spread_50_200 = (
            (ema50 / ema200) - 1
        ) * 100

        if spread_50_200 >= 15:
            long_trend_score = 15

        elif spread_50_200 >= 10:
            long_trend_score = 12

        elif spread_50_200 >= 5:
            long_trend_score = 9

        elif spread_50_200 >= 2:
            long_trend_score = 6

        elif spread_50_200 >= 0:
            long_trend_score = 3

        else:
            long_trend_score = 0


        # --------------------------------------------------
        # 5. EMA EĞİMİ - 20 PUAN
        # --------------------------------------------------

        lookback = 10

        ema20_old = float(
            ema20_series.iloc[-lookback]
        )

        ema50_old = float(
            ema50_series.iloc[-lookback]
        )

        ema20_slope = (
            (ema20 / ema20_old) - 1
        ) * 100

        ema50_slope = (
            (ema50 / ema50_old) - 1
        ) * 100


        slope_score = 0

        # EMA20 eğimi
        if ema20_slope >= 3:
            slope_score += 10

        elif ema20_slope >= 1:
            slope_score += 7

        elif ema20_slope >= 0:
            slope_score += 4


        # EMA50 eğimi
        if ema50_slope >= 2:
            slope_score += 10

        elif ema50_slope >= 0.5:
            slope_score += 7

        elif ema50_slope >= 0:
            slope_score += 4


        # --------------------------------------------------
        # TOPLAM
        # --------------------------------------------------

        score = (
            ema_order_score
            + price_score
            + spread_score
            + long_trend_score
            + slope_score
        )

        score = max(
            0,
            min(score, 100)
        )


        print(
            f"[TREND] "
            f"EMA20={ema20:.2f} "
            f"EMA50={ema50:.2f} "
            f"EMA200={ema200:.2f} "
            f"Trend={score}"
        )


        return round(
            score,
            1
        )


    except Exception as e:

        print(
            f"[TREND HATA] "
            f"{type(e).__name__}: {e}"
        )

        return 50
# ----------------------------------------------------------
# TREND
# ----------------------------------------------------------
# ----------------------------------------------------------
# 52 HAFTA GETİRİ
# ----------------------------------------------------------

def get_year_return(df):

    if df is None:
        return None

    # Yaklaşık 1 yıl işlem günü
    if len(df) < 250:
        return None

    first_price = df["Close"].iloc[-250]

    last_price = df["Close"].iloc[-1]

    year_return = (
        (last_price - first_price)
        /
        first_price
        *
        100
    )

    return round(float(year_return), 2)
# ----------------------------------------------------------
# DESTEK - DİRENÇ
# ----------------------------------------------------------


def get_trend(df):

    if df is None:
        return "Bilinmiyor"


    ema20 = get_ema(df,20)
    ema50 = get_ema(df,50)
    ema200 = get_ema(df,200)


    if ema20 is None or ema50 is None or ema200 is None:
        return "Yetersiz Veri"


    if ema20 > ema50 > ema200:
        return "Güçlü Yükseliş"

    elif ema20 > ema50:
        return "Yükseliş"

    elif ema20 < ema50 < ema200:
        return "Güçlü Düşüş"

    elif ema20 < ema50:
        return "Düşüş"

    return "Yatay"

# ----------------------------------------------------------
# AI SCORE
# ----------------------------------------------------------
# ----------------------------------------------------------
# GELİŞMİŞ AI SKORU
# ----------------------------------------------------------

def calculate_ai_score(df):

    try:

        if df is None or len(df) < 220:
            return 50

        # ==================================================
        # TEMEL VERİLER
        # ==================================================

        rsi = get_rsi(df)

        macd, signal = get_macd(df)

        trend_strength = calculate_trend_strength(df)

        momentum_score = calculate_momentum_score(df)

        volume_score = calculate_volume_score(df)

        price = get_last_price(df)

        ema20 = get_ema(df, 20)

        ema50 = get_ema(df, 50)

        ema200 = get_ema(df, 200)

        volatility = get_volatility(df)

        daily_change = get_daily_change(df)


        # ==================================================
        # 1 — TREND %25
        # ==================================================

        trend_component = trend_strength * 0.25


        # ==================================================
        # 2 — MOMENTUM %20
        # ==================================================

        momentum_component = momentum_score * 0.20


        # ==================================================
        # 3 — HACİM %15
        # ==================================================

        volume_component = volume_score * 0.15


        # ==================================================
        # 4 — RSI %15
        # ==================================================

        if rsi is None:

            rsi_score = 50

        elif 45 <= rsi <= 65:

            rsi_score = 100

        elif 40 <= rsi < 45:

            rsi_score = 80

        elif 65 < rsi <= 70:

            rsi_score = 80

        elif 35 <= rsi < 40:

            rsi_score = 60

        elif 70 < rsi <= 75:

            rsi_score = 60

        elif rsi < 30:

            rsi_score = 40

        else:

            rsi_score = 30


        rsi_component = rsi_score * 0.15


        # ==================================================
        # 5 — MACD %10
        # ==================================================

        if macd is None or signal is None:

            macd_score = 50

        elif macd > signal:

            macd_score = 100

        else:

            macd_score = 30


        macd_component = macd_score * 0.10


        # ==================================================
        # 6 — EMA KONUMU %10
        # ==================================================

        ema_score = 0

        if price is not None and ema20 is not None:

            if price > ema20:
                ema_score += 35

        if price is not None and ema50 is not None:

            if price > ema50:
                ema_score += 35

        if price is not None and ema200 is not None:

            if price > ema200:
                ema_score += 30


        ema_component = ema_score * 0.10


        # ==================================================
        # 7 — GÜNLÜK FİYAT RİSKİ %5
        # ==================================================

        if daily_change is None:

            daily_score = 50

        elif daily_change >= 3:

            daily_score = 100

        elif daily_change >= 1:

            daily_score = 90

        elif daily_change >= 0:

            daily_score = 75

        elif daily_change >= -2:

            daily_score = 60

        elif daily_change >= -4:

            daily_score = 40

        elif daily_change >= -6:

            daily_score = 25

        else:

            daily_score = 10


        daily_component = daily_score * 0.05


        # ==================================================
        # TOPLAM AI SKORU
        # ==================================================

        score = (

            trend_component

            + momentum_component

            + volume_component

            + rsi_component

            + macd_component

            + ema_component

            + daily_component

        )


        score = max(
            0,
            min(score, 100)
        )


        return round(
            score,
            1
        )


    except Exception as e:

        print(
            f"[AI SCORE HATA] "
            f"{type(e).__name__}: {e}"
        )

        return 50
    
def get_recommendation(score):

    if score >= 90:
        return "🟢 Güçlü Al"

    elif score >= 75:
        return "🟢 Al"

    elif score >= 60:
        return "🟡 Tut"

    elif score >= 40:
        return "🟠 Zayıf"

    return "🔴 Sat"


# ----------------------------------------------------------
# ANA ANALİZ FONKSİYONU
# ----------------------------------------------------------

def get_stock_analysis(symbol):

    if not symbol.endswith(".IS"):
        symbol = symbol + ".IS"


    df = get_history(symbol)

    if df is None:

        print(
        "VERİ ALINAMADI:",
        symbol
    )
        return None

    info = get_company_info(symbol)

    score = calculate_ai_score(df)
    volume_score = calculate_volume_score(df)

    momentum_score = calculate_momentum_score(df)

    momentum_60_score = calculate_momentum_60_score(df)
    
    momentum_details = get_momentum_details(df)

    trend_strength = calculate_trend_strength(df)

    macd, signal = get_macd(df)

    upper, lower = get_bollinger(df)
    support = get_support(df)
    resistance = get_resistance(df)

    print("SUPPORT:", support)
    print("RESISTANCE:", resistance)

    analysis = {

        "symbol": symbol,

        "company": info["company"],

        "sector": SEKTOR_MAP.get(
            symbol.upper(),
            info.get("sector", "")
        ),

        "market_cap": info["market_cap"],

        "price": get_last_price(df),

        "change": get_daily_change(df),

        "volume": get_volume(df),

        "avg_volume": get_average_volume(df),

        "ema20": get_ema(df,20),

        "ema50": get_ema(df,50),

        "ema200": get_ema(df,200),

        "rsi": get_rsi(df),

        "macd": macd,

        "signal": signal,

        "bollinger_upper": upper,

        "bollinger_lower": lower,

        "support": support,

        "resistance": resistance,

        "atr": get_atr(df),

        "momentum": get_momentum(df),

        "volatility": get_volatility(df),

        "year_return": get_year_return(df),

        "trend": get_trend(df),

        "score": score,

        "volume_score": volume_score,

                "momentum_score": momentum_score,

        "momentum_60_score": momentum_60_score,

        "momentum_20": momentum_details["momentum_20"],

        "momentum_60": momentum_details["momentum_60"],

        "trend_strength": trend_strength,

        "recommendation": get_recommendation(score)

    }

    return analysis

def get_yahoo_price(symbol):

    analysis = get_stock_analysis(symbol)

    if analysis is None:
        return None

    return analysis["price"]


def get_yahoo_info(symbol):

    analysis = get_stock_analysis(symbol)

    if analysis is None:
        return {
            "symbol": symbol,
            "company": "-",
            "sector": "-",
            "market_cap": 0
        }

    return {
        "symbol": symbol,
        "company": analysis["company"],
        "sector": analysis["sector"],
        "market_cap": analysis["market_cap"]
    }
# ----------------------------------------------------------
# TEMEL ANALİZ VERİLERİ
# ----------------------------------------------------------

def get_fundamental_data(symbol):

    try:

        if not symbol.endswith(".IS"):
            symbol = symbol + ".IS"

        ticker = yf.Ticker(symbol)

        info = ticker.info

        return {

            "pe_ratio": info.get("trailingPE"),
            "pb_ratio": info.get("priceToBook"),
            "market_cap": info.get("marketCap"),
            "profit_margin": info.get("profitMargins"),
            "revenue": info.get("totalRevenue"),
            "debt_equity": info.get("debtToEquity"),
            "dividend_yield": info.get("dividendYield")

        }

    except Exception:

        return None