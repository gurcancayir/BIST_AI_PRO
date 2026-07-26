import pandas as pd
import yfinance as yf
import streamlit as st
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
# MOMENTUM SKORU
# ----------------------------------------------------------

def calculate_momentum_score(data):

    try:

        price_now = data["Close"].iloc[-1]

        price_old = data["Close"].iloc[-20]


        change = (
            (price_now / price_old) - 1
        ) * 100


        if change >= 15:
            return 100

        elif change >= 8:
            return 85

        elif change >= 3:
            return 70

        elif change >= 0:
            return 55

        else:
            return 30


    except:

        return 50

# ----------------------------------------------------------
# AYARLAR
# ----------------------------------------------------------

HISTORY_PERIOD = "2y"
INTERVAL = "1d"


# ----------------------------------------------------------
# VERİ İNDİR
# ----------------------------------------------------------


@st.cache_data(ttl=1800)
def get_history(symbol):

    """
    Yahoo Finance'den hisse geçmiş verisini indirir.
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

        if df.empty:
            return None

        return df

    except Exception:

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

            "sector": info.get("sector", "-"),

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

def calculate_ai_score(df):

    score = 50

    rsi = get_rsi(df)

    macd, signal = get_macd(df)

    trend = get_trend(df)

    volume = get_volume(df)

    avg_volume = get_average_volume(df)

    momentum = get_momentum(df)

    volatility = get_volatility(df)

    price = get_last_price(df)

    ema20 = get_ema(df, 20)

    ema50 = get_ema(df, 50)

    upper, lower = get_bollinger(df)

    support = get_support(df)

    resistance = get_resistance(df)

  
    # RSI

    if rsi is not None:

        if 45 <= rsi <= 65:
            score += 10

        elif rsi < 30:
            score += 5

        elif rsi > 75:
            score -= 10

# MACD

    if macd is not None and signal is not None:

        if macd > signal:
            score += 15
        else:
            score -= 10

    # Trend
    # Hacim
    # ----------------------------------------------------------
    # TREND PUANI
    # ----------------------------------------------------------

    if trend == "Güçlü Yükseliş":
        score += 20

    elif trend == "Yükseliş":
        score += 10

    elif trend == "Düşüş":
        score -= 10

    elif trend == "Güçlü Düşüş":
        score -= 20


    # ----------------------------------------------------------
    # HACİM
    # ----------------------------------------------------------

    if avg_volume > 0:

        if volume > avg_volume:
            score += 5

        else:
            score -= 5


    # ----------------------------------------------------------
    # MOMENTUM
    # ----------------------------------------------------------

    if momentum is not None:

        if momentum > 0:
            score += 10

        else:
            score -= 10


    # ----------------------------------------------------------
    # VOLATİLİTE
    # ----------------------------------------------------------

    if volatility is not None:

        if volatility < 3:
            score += 5

        elif volatility > 6:
            score -= 5


    # ----------------------------------------------------------
    # EMA
    # ----------------------------------------------------------

    if ema20 is not None and ema50 is not None and price is not None:

        if price > ema20:
            score += 5

        if ema20 > ema50:
            score += 5


    # ----------------------------------------------------------
    # BOLLINGER
    # ----------------------------------------------------------

    if upper is not None and lower is not None and price is not None:

        if price <= lower:
            score += 10

        elif price >= upper:
            score -= 10

        # ----------------------------------------------------------
    # DESTEK / DİRENÇ
    # ----------------------------------------------------------

    if support is not None and resistance is not None:

        if price <= support * 1.03:
            score += 5

        elif price >= resistance * 0.97:
            score -= 5


    return max(0, min(score, 100))

    # Momentum
# ----------------------------------------------------------
# DESTEK / DİRENÇ
# ----------------------------------------------------------



# ----------------------------------------------------------
# KARAR
# ----------------------------------------------------------

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

    df = get_history(symbol)

    if df is None:

        return None

    info = get_company_info(symbol)

    score = calculate_ai_score(df)
    volume_score = calculate_volume_score(df)

    momentum_score = calculate_momentum_score(df)

    macd, signal = get_macd(df)

    upper, lower = get_bollinger(df)
    support = get_support(df)
    resistance = get_resistance(df)

    print("SUPPORT:", support)
    print("RESISTANCE:", resistance)

    analysis = {

        "symbol": symbol,

        "company": info["company"],

        "sector": info["sector"],

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