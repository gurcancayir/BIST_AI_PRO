# ============================================================
# BIST AI PRO
# 05_Gunluk_Trade.py
#
# GÜNLÜK TRADE MERKEZİ - PRO / HAVUZ MODELİ
#
# AMAÇ:
# BIST500
#   ↓
# Günlük veri + likidite
#   ↓
# Geniş trade havuzu
#   ↓
# Günlük setup skoru
#   ↓
# En güçlü adaylarda 15D teyit
#   ↓
# Trade skoru
#   ↓
# Karar
#   ↓
# 🟢 GÜÇLÜ TRADE
# 🟡 TRADE ADAYI
# 🔵 İZLE
#   ↓
# Trade Adayları için:
# 🟢 A SINIFI
# 🟡 B SINIFI
# 🔵 C SINIFI
#
# ÖNEMLİ TASARIM:
# 1) 500 hissenin her biri için ayrı ayrı 15D veri indirilmez.
# 2) Önce günlük veri ile geniş havuz oluşturulur.
# 3) Sadece en güçlü günlük adaylara 15D teyit uygulanır.
# 4) 15D veri alınamazsa hisse havuzdan silinmez.
# 5) Tek bir sert kriter hisseyi otomatik olarak çöpe atmaz.
# 6) Hangi aşamada kaç hissenin kaldığı açıkça gösterilir.
# 7) A/B/C sınıflandırması mevcut karar sistemini bozmaz.
# ============================================================

import sqlite3
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf


# ============================================================
# SAYFA
# ============================================================

st.set_page_config(
    page_title="BIST AI PRO - Günlük Trade Merkezi",
    page_icon="⚡",
    layout="wide",
)

st.title("⚡ Günlük Trade Merkezi PRO")

st.markdown(
    """
    **BIST500 → Günlük Setup → Trade Havuzu → 15D Teyit → Sıralama**

    Bu sürümün amacı önce **geniş ve ölçülebilir bir trade havuzu**
    oluşturmaktır. Ardından en güçlü adaylar 15 dakikalık veride teyit edilir.

    **Trade Adayları ayrıca A / B / C kalite sınıfına ayrılır.**
    """
)


# ============================================================
# AYARLAR
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "borsa.db"

DEFAULT_MIN_LIQUIDITY = 20_000_000
HISTORY_PERIOD = "3mo"

# Havuz
POOL_MIN_SCORE = 48

# Karar seviyeleri
STRONG_SCORE = 76
CANDIDATE_SCORE = 62
WATCH_SCORE = 52

# 15D sadece bu kadar günlük adayda çalıştırılır.
MAX_INTRADAY_CHECK = 120


# ============================================================
# TRADE A / B / C EŞİKLERİ
# ============================================================

# A SINIFI
# Çok güçlü trade adayı.
A_TRADE_SCORE = 78
A_TOMORROW_SCORE = 78
A_DAILY_SCORE = 68
A_TREND = 55
A_PULLBACK = 55
A_RR = 1.50
A_INTRADAY = 60

# B SINIFI
# Güçlü fakat A kadar teyitli olmayan aday.
B_TRADE_SCORE = 70
B_TOMORROW_SCORE = 70
B_DAILY_SCORE = 62
B_TREND = 45
B_PULLBACK = 40
B_RR = 1.20


# ============================================================
# DB
# ============================================================

@st.cache_data(ttl=60)
def get_db_stocks():

    if not DB_PATH.exists():
        return pd.DataFrame()

    try:

        with sqlite3.connect(DB_PATH) as conn:

            tables = pd.read_sql_query(
                """
                SELECT name
                FROM sqlite_master
                WHERE type='table'
                """,
                conn,
            )["name"].tolist()

            if "stocks" not in tables:
                return pd.DataFrame()

            return pd.read_sql_query(
                "SELECT * FROM stocks",
                conn,
            )

    except Exception:

        return pd.DataFrame()


# ============================================================
# TICKER
# ============================================================

def normalize_ticker(value):

    if value is None:
        return None

    ticker = str(value).upper().strip()

    ticker = ticker.replace(".IS", "")
    ticker = ticker.replace(" BIST", "")
    ticker = ticker.replace("$", "")
    ticker = ticker.replace(" ", "")

    if ticker.endswith("."):
        ticker = ticker[:-1]

    return ticker or None


def yahoo_symbol(ticker):

    ticker = normalize_ticker(ticker)

    return f"{ticker}.IS" if ticker else None


def get_universe():

    df = get_db_stocks()

    if df.empty:
        return []

    possible = [
        "symbol",
        "ticker",
        "code",
        "hisse",
        "hisse_kodu",
    ]

    column = next(
        (
            c
            for c in possible
            if c in df.columns
        ),
        None,
    )

    if column is None:
        return []

    tickers = []

    for value in df[column].dropna():

        ticker = normalize_ticker(value)

        if ticker and ticker not in tickers:
            tickers.append(ticker)

    return tickers


# ============================================================
# YARDIMCI
# ============================================================

def scalar(value, default=np.nan):
    """
    Pandas/yfinance değerini güvenli float'a çevir.
    """

    try:

        if isinstance(value, pd.Series):
            value = value.iloc[0]

        value = float(value)

        if np.isfinite(value):
            return value

    except Exception:
        pass

    return default


def clean_ohlcv(df):

    if df is None or df.empty:
        return None

    df = df.copy()

    if isinstance(df.columns, pd.MultiIndex):

        df.columns = df.columns.get_level_values(0)

    required = [
        "Open",
        "High",
        "Low",
        "Close",
        "Volume",
    ]

    if not all(
        c in df.columns
        for c in required
    ):
        return None

    for c in required:

        df[c] = pd.to_numeric(
            df[c],
            errors="coerce",
        )

    df = df.dropna(
        subset=["Close"]
    )

    if df.empty:
        return None

    return df


# ============================================================
# GÜNLÜK GÖSTERGELER
# ============================================================

def calculate_daily_indicators(df):

    df = clean_ohlcv(df)

    if df is None or len(df) < 30:
        return None

    df = df.copy()

    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    volume = df["Volume"]

    # EMA
    for span in [
        5,
        9,
        20,
        50,
    ]:

        df[f"EMA{span}"] = close.ewm(
            span=span,
            adjust=False,
        ).mean()

    # RSI - Wilder benzeri EMA yaklaşımı
    delta = close.diff()

    gain = delta.clip(
        lower=0
    )

    loss = -delta.clip(
        upper=0
    )

    avg_gain = gain.ewm(
        alpha=1 / 14,
        adjust=False,
        min_periods=14,
    ).mean()

    avg_loss = loss.ewm(
        alpha=1 / 14,
        adjust=False,
        min_periods=14,
    ).mean()

    rs = (
        avg_gain
        / avg_loss.replace(
            0,
            np.nan,
        )
    )

    df["RSI"] = (
        100
        - (
            100
            / (1 + rs)
        )
    )

    df["RSI"] = (
        df["RSI"]
        .fillna(50)
        .clip(0, 100)
    )

    # Hacim
    df["VOL20"] = volume.rolling(
        20,
        min_periods=10,
    ).mean()

    df["VolumeRatio"] = (
        volume
        / df["VOL20"].replace(
            0,
            np.nan,
        )
    ).replace(
        [np.inf, -np.inf],
        np.nan,
    ).fillna(1.0)

    # ATR
    prev_close = close.shift(1)

    tr = pd.concat(
        [
            high - low,
            (
                high
                - prev_close
            ).abs(),
            (
                low
                - prev_close
            ).abs(),
        ],
        axis=1,
    ).max(axis=1)

    df["ATR"] = tr.ewm(
        alpha=1 / 14,
        adjust=False,
        min_periods=14,
    ).mean()

    # Günlük VWAP yerine son 20 gün ağırlıklı referans.
    typical = (
        high
        + low
        + close
    ) / 3

    pv = (
        typical * volume
    ).rolling(
        20,
        min_periods=5,
    ).sum()

    vv = volume.rolling(
        20,
        min_periods=5,
    ).sum()

    df["VWAP20"] = (
        pv
        / vv.replace(
            0,
            np.nan,
        )
    )

    # Momentumlar
    df["Return_1D"] = (
        close.pct_change(1)
        * 100
    )

    df["Return_5D"] = (
        close.pct_change(5)
        * 100
    )

    df["Return_20D"] = (
        close.pct_change(20)
        * 100
    )

    df["ATR_Pct"] = (
        df["ATR"]
        / close.replace(
            0,
            np.nan,
        )
        * 100
    ).fillna(0)

    df["EMA9_Slope_5D"] = (
        df["EMA9"].pct_change(5)
        * 100
    )

    df["EMA20_Slope_5D"] = (
        df["EMA20"].pct_change(5)
        * 100
    )

    df["Prev20High"] = (
        high.shift(1)
        .rolling(
            20,
            min_periods=10,
        )
        .max()
    )

    df["BreakoutDistance"] = (
        (
            df["Prev20High"]
            - close
        )
        / close
        * 100
    ).replace(
        [np.inf, -np.inf],
        np.nan,
    ).fillna(99)

    return df


# ============================================================
# GÜNLÜK SETUP PUANLARI
# ============================================================

def trend_score(row):

    price = scalar(
        row["Close"]
    )

    ema9 = scalar(
        row["EMA9"]
    )

    ema20 = scalar(
        row["EMA20"]
    )

    ema50 = scalar(
        row["EMA50"]
    )

    score = 0

    if price > ema20:
        score += 30

    elif price >= ema20 * 0.985:
        score += 20

    elif price >= ema20 * 0.97:
        score += 10

    if ema9 > ema20:
        score += 25

    elif ema9 >= ema20 * 0.995:
        score += 15

    if ema20 > ema50:
        score += 25

    elif ema20 >= ema50 * 0.995:
        score += 15

    ret5 = scalar(
        row["Return_5D"],
        0,
    )

    if ret5 > 0:
        score += 10

    elif ret5 > -2:
        score += 5

    return min(
        score,
        100,
    )


def pullback_score(row):

    price = scalar(
        row["Close"]
    )

    ema9 = scalar(
        row["EMA9"]
    )

    ema20 = scalar(
        row["EMA20"]
    )

    if price <= 0:
        return 0

    distance9 = (
        abs(price - ema9)
        / price
        * 100
    )

    score = 0

    if price >= ema9:
        score += 30

    elif price >= ema9 * 0.985:
        score += 22

    elif price >= ema9 * 0.97:
        score += 14

    if distance9 <= 1:
        score += 25

    elif distance9 <= 2:
        score += 22

    elif distance9 <= 4:
        score += 16

    elif distance9 <= 6:
        score += 10

    else:
        score += 4

    if price > ema20:
        score += 25

    elif price >= ema20 * 0.985:
        score += 18

    elif price >= ema20 * 0.97:
        score += 10

    if ema9 > ema20:
        score += 20

    elif ema9 >= ema20 * 0.995:
        score += 12

    return min(
        score,
        100,
    )


def rsi_score(row):

    rsi = scalar(
        row["RSI"],
        50,
    )

    if 50 <= rsi <= 68:
        return 100

    if 45 <= rsi < 50:
        return 80

    if 68 < rsi <= 75:
        return 75

    if 40 <= rsi < 45:
        return 60

    if 75 < rsi <= 80:
        return 45

    return 30


def volume_score(row):

    vr = scalar(
        row["VolumeRatio"],
        1,
    )

    if vr >= 1.50:
        return 100

    if vr >= 1.20:
        return 90

    if vr >= 1.00:
        return 80

    if vr >= 0.80:
        return 65

    if vr >= 0.60:
        return 50

    return 35


def daily_vwap_score(row):

    price = scalar(
        row["Close"]
    )

    vwap = scalar(
        row["VWAP20"],
        price,
    )

    if price >= vwap:
        return 100

    if price >= vwap * 0.99:
        return 75

    if price >= vwap * 0.97:
        return 55

    return 35


# ============================================================
# YARIN TRADE SKORU
# ============================================================

def tomorrow_setup_score(
    row,
    rr,
):

    trend = trend_score(row)
    pull = pullback_score(row)
    rsi = rsi_score(row)
    vol = volume_score(row)
    vwap = daily_vwap_score(row)

    ret5 = scalar(
        row["Return_5D"],
        0,
    )

    atr_pct = scalar(
        row["ATR_Pct"],
        0,
    )

    slope9 = scalar(
        row["EMA9_Slope_5D"],
        0,
    )

    breakout_dist = scalar(
        row["BreakoutDistance"],
        99,
    )

    if 1 <= ret5 <= 8:
        momentum = 100

    elif (
        0 <= ret5 < 1
        or 8 < ret5 <= 12
    ):
        momentum = 80

    elif -2 <= ret5 < 0:
        momentum = 60

    elif ret5 > 12:
        momentum = 45

    else:
        momentum = 35

    if (
        slope9 > 1.0
        and scalar(row["EMA9"])
        > scalar(row["EMA20"])
    ):
        slope_score = 100

    elif slope9 > 0.3:
        slope_score = 80

    elif slope9 > -0.3:
        slope_score = 60

    else:
        slope_score = 35

    if breakout_dist >= 4:
        room_score = 100

    elif breakout_dist >= 2.5:
        room_score = 85

    elif breakout_dist >= 1.5:
        room_score = 70

    elif breakout_dist >= 0.75:
        room_score = 50

    else:
        room_score = 30

    if 1.5 <= atr_pct <= 5.0:
        volatility_score = 100

    elif (
        1.0 <= atr_pct < 1.5
        or 5.0 < atr_pct <= 7.0
    ):
        volatility_score = 80

    elif (
        0.7 <= atr_pct < 1.0
        or 7.0 < atr_pct <= 9.0
    ):
        volatility_score = 60

    else:
        volatility_score = 40

    rr_s = rr_score(rr)

    score = (
        trend * 0.22
        + pull * 0.20
        + momentum * 0.13
        + rsi * 0.08
        + vol * 0.08
        + vwap * 0.08
        + slope_score * 0.07
        + room_score * 0.06
        + volatility_score * 0.03
        + rr_s * 0.05
    )

    return round(
        min(
            max(score, 0),
            100,
        ),
        1,
    )


# ============================================================
# DESTEK / DİRENÇ
# ============================================================

def support_resistance(df):

    recent = df.tail(30)

    support = scalar(
        recent["Low"].min()
    )

    resistance = scalar(
        recent["High"].max()
    )

    return support, resistance


# ============================================================
# RİSK / ÖDÜL
# ============================================================

def risk_reward(
    price,
    support,
    resistance,
    atr,
):

    if price <= 0:
        return 0, 0, 0, 0

    if (
        not np.isfinite(atr)
        or atr <= 0
    ):
        atr = price * 0.02

    # --------------------------------------------------------
    # STOP
    # --------------------------------------------------------

    atr_stop = (
        price
        - (1.20 * atr)
    )

    if (
        np.isfinite(support)
        and 0 < support < price
    ):

        support_stop = (
            support * 0.995
        )

    else:

        support_stop = np.nan

    if np.isfinite(
        support_stop
    ):

        support_distance = (
            price
            - support_stop
        )

        atr_distance = (
            price
            - atr_stop
        )

        if (
            support_distance
            > atr_distance * 1.50
        ):

            stop = atr_stop

        else:

            stop = support_stop

    else:

        stop = atr_stop

    if (
        stop <= 0
        or stop >= price
    ):

        stop = price * 0.97

    risk = price - stop

    # --------------------------------------------------------
    # HEDEF
    # --------------------------------------------------------

    atr_target = (
        price
        + (2.50 * atr)
    )

    if (
        np.isfinite(resistance)
        and resistance > price
    ):

        resistance_target = resistance

    else:

        resistance_target = np.nan

    if np.isfinite(
        resistance_target
    ):

        resistance_reward = (
            resistance_target
            - price
        )

        atr_reward = (
            atr_target
            - price
        )

        if (
            resistance_reward
            < atr_reward * 0.75
        ):

            target = atr_target

        else:

            target = resistance_target

    else:

        target = atr_target

    if target <= price:

        target = (
            price
            + (2.0 * atr)
        )

    reward = max(
        target - price,
        0,
    )

    rr = (
        reward / risk
        if risk > 0
        else 0
    )

    return (
        stop,
        target,
        risk,
        rr,
    )


def rr_score(rr):

    if rr >= 2.5:
        return 100

    if rr >= 2.0:
        return 90

    if rr >= 1.5:
        return 80

    if rr >= 1.2:
        return 70

    if rr >= 1.0:
        return 55

    if rr >= 0.8:
        return 40

    return 25


# ============================================================
# 15 DAKİKA
# ============================================================

@st.cache_data(
    ttl=300,
    show_spinner=False,
)
def calculate_intraday(ticker):

    try:

        symbol = yahoo_symbol(
            ticker
        )

        data = yf.download(
            symbol,
            period="5d",
            interval="15m",
            progress=False,
            auto_adjust=False,
            threads=False,
        )

        data = clean_ohlcv(
            data
        )

        if (
            data is None
            or len(data) < 25
        ):
            return None

        close = data["Close"]

        data["EMA9"] = close.ewm(
            span=9,
            adjust=False,
        ).mean()

        data["EMA20"] = close.ewm(
            span=20,
            adjust=False,
        ).mean()

        typical = (
            data["High"]
            + data["Low"]
            + data["Close"]
        ) / 3

        volume = data["Volume"]

        data["VWAP"] = (
            (typical * volume).cumsum()
            / volume.cumsum().replace(
                0,
                np.nan,
            )
        )

        data["VOL20"] = volume.rolling(
            20,
            min_periods=5,
        ).mean()

        data["VolumeRatio"] = (
            volume
            / data["VOL20"].replace(
                0,
                np.nan,
            )
        ).replace(
            [np.inf, -np.inf],
            np.nan,
        ).fillna(1)

        last = data.iloc[-1]
        prev = data.iloc[-2]

        score = 0

        # EMA trend
        if last["EMA9"] > last["EMA20"]:
            score += 30

        elif (
            last["EMA9"]
            >= last["EMA20"] * 0.998
        ):
            score += 20

        # Fiyat EMA9
        if last["Close"] > last["EMA9"]:
            score += 25

        elif (
            last["Close"]
            >= last["EMA9"] * 0.995
        ):
            score += 15

        # VWAP
        if last["Close"] > last["VWAP"]:
            score += 25

        elif (
            last["Close"]
            >= last["VWAP"] * 0.995
        ):
            score += 15

        # Son mum
        if last["Close"] > prev["Close"]:
            score += 10

        elif (
            last["Close"]
            >= prev["Close"] * 0.997
        ):
            score += 5

        # Intraday hacim
        if (
            last["VolumeRatio"]
            >= 1.20
        ):
            score += 10

        elif (
            last["VolumeRatio"]
            >= 0.90
        ):
            score += 5

        return {
            "score": min(
                score,
                100,
            ),

            "price": scalar(
                last["Close"]
            ),

            "ema9": scalar(
                last["EMA9"]
            ),

            "ema20": scalar(
                last["EMA20"]
            ),

            "vwap": scalar(
                last["VWAP"]
            ),

            "volume_ratio": scalar(
                last["VolumeRatio"],
                1,
            ),
        }

    except Exception:

        return None


# ============================================================
# GÜNLÜK ANALİZ
# ============================================================

def analyze_daily(
    ticker,
    daily_df,
    min_liquidity,
):

    try:

        df = calculate_daily_indicators(
            daily_df
        )

        if df is None:
            return None, "veri_yetersiz"

        row = df.iloc[-1]

        price = scalar(
            row["Close"]
        )

        if (
            not np.isfinite(price)
            or price <= 0
        ):

            return None, "fiyat"

        avg_volume = scalar(
            row["VOL20"],
            0,
        )

        liquidity = (
            price
            * avg_volume
        )

        if liquidity < min_liquidity:
            return None, "likidite"

        t_score = trend_score(
            row
        )

        p_score = pullback_score(
            row
        )

        rsi_s = rsi_score(
            row
        )

        vol_s = volume_score(
            row
        )

        vwap_s = daily_vwap_score(
            row
        )

        support, resistance = (
            support_resistance(df)
        )

        atr = scalar(
            row["ATR"],
            price * 0.02,
        )

        stop, target, risk, rr = (
            risk_reward(
                price,
                support,
                resistance,
                atr,
            )
        )

        rr_s = rr_score(
            rr
        )

        # Günlük skor
        daily_score = (
            t_score * 0.30
            + p_score * 0.25
            + rsi_s * 0.10
            + vol_s * 0.10
            + vwap_s * 0.10
            + rr_s * 0.15
        )

        yarin_skor = (
            tomorrow_setup_score(
                row,
                rr,
            )
        )

        result = {

            "Hisse": ticker,

            "Fiyat": price,

            "9 EMA": round(
                scalar(
                    row["EMA9"],
                    price,
                ),
                2,
            ),

            "EMA20": round(
                scalar(
                    row["EMA20"],
                    price,
                ),
                2,
            ),

            "EMA50": round(
                scalar(
                    row["EMA50"],
                    price,
                ),
                2,
            ),

            "Likidite": liquidity,

            "Yarın Skoru": yarin_skor,

            "ATR %": round(
                scalar(
                    row["ATR_Pct"],
                    0,
                ),
                2,
            ),

            "5G Getiri %": round(
                scalar(
                    row["Return_5D"],
                    0,
                ),
                2,
            ),

            "20G Getiri %": round(
                scalar(
                    row["Return_20D"],
                    0,
                ),
                2,
            ),

            "EMA9 Eğim %": round(
                scalar(
                    row["EMA9_Slope_5D"],
                    0,
                ),
                2,
            ),

            "Dirence Mesafe %": round(
                scalar(
                    row["BreakoutDistance"],
                    99,
                ),
                2,
            ),

            "Günlük Skor": round(
                daily_score,
                1,
            ),

            "Trend": round(
                t_score,
                1,
            ),

            "Pullback": round(
                p_score,
                1,
            ),

            "RSI Skor": round(
                rsi_s,
                1,
            ),

            "Hacim Skor": round(
                vol_s,
                1,
            ),

            "VWAP Skor": round(
                vwap_s,
                1,
            ),

            "RSI": round(
                scalar(
                    row["RSI"],
                    50,
                ),
                1,
            ),

            "Hacim Oranı": round(
                scalar(
                    row["VolumeRatio"],
                    1,
                ),
                2,
            ),

            "Destek": support,

            "Direnç": resistance,

            "Stop": stop,

            "Hedef": target,

            "R/R": round(
                rr,
                2,
            ),

            "15D Trend": 50.0,

            "15D VWAP": "BEKLENİYOR",

            "15D Skor": 50.0,

            "Trade Skoru": round(
                daily_score,
                1,
            ),

            "Trade Sınıfı": "—",

            "Karar": "🔵 YARIN İZLE",
        }

        return result, "ok"

    except Exception:

        return None, "hata"


# ============================================================
# TRADE A / B / C SINIFLANDIRMASI
# ============================================================

def classify_trade_candidate(
    result
):
    """
    Mevcut karar sistemini değiştirmez.

    Sadece:
        🟡 YARIN TRADE ADAYI

    olan hisseleri kalite seviyesine ayırır.

    🟢 A = Çok güçlü aday
    🟡 B = Güçlü aday
    🔵 C = İzlenmesi gereken aday
    """

    trade_score = float(
        result.get(
            "Trade Skoru",
            0,
        )
    )

    tomorrow_score = float(
        result.get(
            "Yarın Skoru",
            0,
        )
    )

    daily_score = float(
        result.get(
            "Günlük Skor",
            0,
        )
    )

    trend = float(
        result.get(
            "Trend",
            0,
        )
    )

    pullback = float(
        result.get(
            "Pullback",
            0,
        )
    )

    rr = float(
        result.get(
            "R/R",
            0,
        )
    )

    intra_score = float(
        result.get(
            "15D Skor",
            50,
        )
    )

    intra_vwap = str(
        result.get(
            "15D VWAP",
            "VERİ YOK",
        )
    )

    karar = str(
        result.get(
            "Karar",
            "",
        )
    )

    # --------------------------------------------------------
    # SADECE TRADE ADAYLARI
    # --------------------------------------------------------

    if karar != "🟡 YARIN TRADE ADAYI":
        return "—"

    # --------------------------------------------------------
    # A SINIFI
    # --------------------------------------------------------

    if (
        trade_score >= A_TRADE_SCORE
        and tomorrow_score >= A_TOMORROW_SCORE
        and daily_score >= A_DAILY_SCORE
        and trend >= A_TREND
        and pullback >= A_PULLBACK
        and rr >= A_RR
        and intra_score >= A_INTRADAY
        and intra_vwap == "ÜSTÜNDE"
    ):

        return "🟢 A"

    # --------------------------------------------------------
    # B SINIFI
    # --------------------------------------------------------

    if (
        trade_score >= B_TRADE_SCORE
        and tomorrow_score >= B_TOMORROW_SCORE
        and daily_score >= B_DAILY_SCORE
        and trend >= B_TREND
        and pullback >= B_PULLBACK
        and rr >= B_RR
    ):

        return "🟡 B"

    # --------------------------------------------------------
    # C SINIFI
    # --------------------------------------------------------

    return "🔵 C"


# ============================================================
# 15D TEYİDİNİ SONRADAN UYGULA
# ============================================================

def apply_intraday(result):

    ticker = result["Hisse"]

    intra = calculate_intraday(
        ticker
    )

    if intra is None:

        intra_score = 50.0
        intra_vwap = "VERİ YOK"

    else:

        intra_score = float(
            intra["score"]
        )

        intra_vwap = (
            "ÜSTÜNDE"
            if intra["price"]
            >= intra["vwap"]
            else "ALTINDA"
        )

    daily_score = float(
        result["Günlük Skor"]
    )

    tomorrow_score = float(
        result["Yarın Skoru"]
    )

    # Yarın için ana ağırlık günlük setup;
    # 15D son seans teyidi.

    trade_score = (
        tomorrow_score * 0.80
        + intra_score * 0.20
    )

    if intra_score >= 80:
        trade_score += 2

    if float(
        result["R/R"]
    ) >= 2:

        trade_score += 2

    trade_score = min(
        trade_score,
        100,
    )

    result["15D Trend"] = round(
        intra_score,
        1,
    )

    result["15D VWAP"] = (
        intra_vwap
    )

    result["15D Skor"] = round(
        intra_score,
        1,
    )

    result["Trade Skoru"] = round(
        trade_score,
        1,
    )

    price = float(
        result["Fiyat"]
    )

    rr = float(
        result["R/R"]
    )

    trend = float(
        result["Trend"]
    )

    pullback = float(
        result["Pullback"]
    )

    rsi = float(
        result["RSI"]
    )

    ema9 = float(
        result.get(
            "9 EMA",
            price,
        )
    )

    distance = (
        abs(
            (
                price
                / ema9
                - 1
            )
            * 100
        )
        if ema9 > 0
        else 99
    )

    # --------------------------------------------------------
    # MEVCUT KARAR SİSTEMİ
    # --------------------------------------------------------

    if distance > 6:

        decision = (
            "🟠 YARIN İÇİN BEKLE"
        )

        reason = (
            f"Fiyat 9 EMA'dan "
            f"%{distance:.1f} uzak; "
            "açılışta kovalanmamalı."
        )

    elif rsi >= 78:

        decision = (
            "🟠 YARIN İÇİN BEKLE"
        )

        reason = (
            "RSI aşırı alım bölgesinde; "
            "açılışta kovalanmamalı."
        )

    elif (
        tomorrow_score >= 80
        and daily_score >= 70
        and trend >= 55
        and pullback >= 55
        and rr >= 1.50
    ):

        decision = (
            "🟢 YARIN GÜÇLÜ ADAY"
        )

        reason = (
            "Günlük trend + pullback "
            "+ momentum + R/R güçlü."
        )

    elif (
        tomorrow_score >= 70
        and daily_score >= 62
        and trend >= 45
        and pullback >= 40
        and rr >= 1.20
    ):

        decision = (
            "🟡 YARIN TRADE ADAYI"
        )

        reason = (
            "Günlük setup yeterli; "
            "açılışta fiyat, VWAP ve "
            "15D teyidi kontrol edilmeli."
        )

    elif tomorrow_score >= 58:

        decision = (
            "🔵 YARIN İZLE"
        )

        reason = (
            "Olumlu yapı var ancak "
            "güçlü trade avantajı henüz "
            "tamamlanmadı."
        )

    else:

        decision = (
            "⚪ HAVUZ DIŞI"
        )

        reason = (
            "Yarın için yeterli teknik "
            "avantaj bulunmuyor."
        )

    result["Karar"] = decision
    result["Açıklama"] = reason

    # A/B/C ilk hesaplama
    # Burada yalnızca mevcut karar
    # TRADE ADAYI ise sınıflandırılır.

    result["Trade Sınıfı"] = (
        classify_trade_candidate(
            result
        )
    )

    return result


# ============================================================
# BATCH DAILY DOWNLOAD
# ============================================================

@st.cache_data(
    ttl=300,
    show_spinner=False,
)
def download_daily_batch(tickers):

    symbols = [
        yahoo_symbol(t)
        for t in tickers
        if yahoo_symbol(t)
    ]

    if not symbols:
        return {}

    try:

        data = yf.download(
            symbols,
            period=HISTORY_PERIOD,
            interval="1d",
            progress=False,
            auto_adjust=False,
            threads=True,
            group_by="ticker",
        )

        if (
            data is None
            or data.empty
        ):
            return {}

        result = {}

        if isinstance(
            data.columns,
            pd.MultiIndex,
        ):

            level0 = list(
                data.columns
                .get_level_values(0)
            )

            level1 = list(
                data.columns
                .get_level_values(1)
            )

            if any(
                x in [
                    "Open",
                    "High",
                    "Low",
                    "Close",
                    "Volume",
                ]
                for x in level1
            ):

                for symbol in symbols:

                    if (
                        symbol
                        not in data.columns
                        .get_level_values(0)
                    ):
                        continue

                    part = data[
                        symbol
                    ].copy()

                    if not part.empty:
                        result[
                            symbol
                        ] = part

            else:

                for symbol in symbols:

                    if (
                        symbol
                        not in data.columns
                        .get_level_values(1)
                    ):
                        continue

                    part = data.xs(
                        symbol,
                        axis=1,
                        level=1,
                    ).copy()

                    if not part.empty:
                        result[
                            symbol
                        ] = part

        else:

            if len(symbols) == 1:
                result[
                    symbols[0]
                ] = data

        return result

    except Exception:

        return {}


# ============================================================
# ANA ARAYÜZ
# ============================================================

universe = get_universe()

if not universe:

    st.error(
        """
        ❌ `stocks` tablosunda hisse evreni bulunamadı.

        Önce **Veri Güncelleme** sayfasından BIST500 evrenini
        SQLite veritabanına yükleyin.
        """
    )

    st.stop()


# ============================================================
# AYARLAR
# ============================================================

with st.expander(
    "⚙️ Trade Tarama Ayarları",
    expanded=False,
):

    col1, col2, col3 = st.columns(3)

    with col1:

        min_liquidity = st.number_input(
            "Minimum 20G Ortalama İşlem Hacmi (TL)",
            min_value=1_000_000,
            max_value=500_000_000,
            value=DEFAULT_MIN_LIQUIDITY,
            step=5_000_000,
        )

    with col2:

        pool_min_score = st.slider(
            "Havuz Minimum Skoru",
            35,
            70,
            POOL_MIN_SCORE,
        )

    with col3:

        max_results = st.slider(
            "Gösterilecek Hisse",
            5,
            50,
            20,
        )

    st.info(
        """
        **Önemli:** Bu sürümde önce geniş havuz oluşturulur.
        15 dakikalık teyit yalnızca en güçlü günlük adaylarda aranır.
        15D veri alınamaması hisseyi otomatik olarak elemez.

        **A/B/C sınıfları yalnızca mevcut Trade Adayları
        üzerinde uygulanır.**
        """
    )


# ============================================================
# ÜST METRİK
# ============================================================

c1, c2, c3, c4 = st.columns(4)

c1.metric(
    "BIST500 Evreni",
    len(universe),
)

c2.metric(
    "Min. Likidite",
    f"{min_liquidity / 1_000_000:.0f} Mn TL",
)

c3.metric(
    "Havuz Eşiği",
    pool_min_score,
)

c4.metric(
    "15D Teyit Limiti",
    MAX_INTRADAY_CHECK,
)


# ============================================================
# TARAMA
# ============================================================

st.markdown("---")

if st.button(
    "⚡ BIST500 GÜNLÜK TRADE TARAMASINI BAŞLAT",
    type="primary",
    use_container_width=True,
):

    # --------------------------------------------------------
    # 1) BATCH DAILY
    # --------------------------------------------------------

    st.info(
        f"📥 BIST500 günlük verisi toplu olarak indiriliyor... "
        f"({len(universe)} hisse)"
    )

    daily_map = download_daily_batch(
        tuple(universe)
    )

    if not daily_map:

        st.error(
            """
            ❌ Günlük Yahoo verisi alınamadı.

            İnternet / Yahoo Finance erişimini veya sembolleri kontrol edin.
            """
        )

        st.stop()

    results = []

    stats = {

        "universe": len(universe),

        "daily_data": 0,

        "liquidity": 0,

        "daily_pool": 0,

        "intraday_checked": 0,

        "intraday_available": 0,

        "strong": 0,

        "candidate": 0,

        "watch": 0,

        "score_62": 0,

        "score_60": 0,

        "score_76": 0,

        "trend_45": 0,

        "pullback_40": 0,

        "rr_090": 0,

        "final_candidate": 0,

        "final_strong": 0,

        # A / B / C
        "trade_a": 0,
        "trade_b": 0,
        "trade_c": 0,
    }

    progress = st.progress(
        0
    )

    status = st.empty()

    # --------------------------------------------------------
    # 2) DAILY POOL
    # --------------------------------------------------------

    for i, ticker in enumerate(
        universe
    ):

        symbol = yahoo_symbol(
            ticker
        )

        daily_df = daily_map.get(
            symbol
        )

        if daily_df is None:
            continue

        stats[
            "daily_data"
        ] += 1

        result, reason = analyze_daily(
            ticker,
            daily_df,
            min_liquidity,
        )

        if result is None:
            continue

        stats[
            "liquidity"
        ] += 1

        if (
            result["Günlük Skor"]
            >= pool_min_score
        ):

            results.append(
                result
            )

            stats[
                "daily_pool"
            ] += 1

        progress.progress(
            int(
                (
                    i + 1
                )
                / max(
                    len(universe),
                    1,
                )
                * 70
            )
        )

    status.text(
        f"📊 Günlük havuz oluşturuldu: "
        f"{len(results)} hisse"
    )

    if not results:

        progress.empty()
        status.empty()

        st.error(
            """
            ❌ Günlük havuz bile oluşturulamadı.

            Bu durumda sorun trade kriterleri değil;
            günlük veri / `stocks` evreni / Yahoo sembolleridir.
            """
        )

        st.stop()

    # --------------------------------------------------------
    # 3) GÜNLÜK SKORA GÖRE SIRALA
    # --------------------------------------------------------

    pool_df = pd.DataFrame(
        results
    ).sort_values(
        "Günlük Skor",
        ascending=False,
    ).reset_index(
        drop=True
    )

    # --------------------------------------------------------
    # 4) SADECE EN İYİ ADAYLARA 15D
    # --------------------------------------------------------

    intraday_n = min(
        MAX_INTRADAY_CHECK,
        len(pool_df),
    )

    checked_indices = (
        pool_df.head(
            intraday_n
        ).index
    )

    for count, idx in enumerate(
        checked_indices,
        start=1,
    ):

        ticker = pool_df.at[
            idx,
            "Hisse",
        ]

        status.text(
            f"⚡ 15D teyit: {ticker} "
            f"({count}/{intraday_n})"
        )

        updated = apply_intraday(
            pool_df.loc[
                idx
            ].to_dict()
        )

        pool_df.loc[
            idx,
            :
        ] = pd.Series(
            updated
        )

        if (
            updated["15D Skor"]
            != 50.0
        ):

            stats[
                "intraday_available"
            ] += 1

        stats[
            "intraday_checked"
        ] += 1

        progress.progress(
            70
            + int(
                count
                / max(
                    intraday_n,
                    1,
                )
                * 30
            )
        )

    progress.empty()
    status.empty()

    # --------------------------------------------------------
    # 5) 15D ALMAYANLAR DA KALSIN
    # --------------------------------------------------------

    pool_df = pool_df.sort_values(
        "Trade Skoru",
        ascending=False,
    ).reset_index(
        drop=True
    )

    # --------------------------------------------------------
    # 6) A / B / C SINIFLANDIRMASI
    # --------------------------------------------------------

    pool_df[
        "Trade Sınıfı"
    ] = pool_df.apply(
        lambda row:
            classify_trade_candidate(
                row.to_dict()
            ),
        axis=1,
    )

    # --------------------------------------------------------
    # A / B / C İSTATİSTİKLERİ
    # --------------------------------------------------------

    stats[
        "trade_a"
    ] = int(
        (
            pool_df[
                "Trade Sınıfı"
            ]
            == "🟢 A"
        ).sum()
    )

    stats[
        "trade_b"
    ] = int(
        (
            pool_df[
                "Trade Sınıfı"
            ]
            == "🟡 B"
        ).sum()
    )

    stats[
        "trade_c"
    ] = int(
        (
            pool_df[
                "Trade Sınıfı"
            ]
            == "🔵 C"
        ).sum()
    )

    # ========================================================
    # KARAR İSTATİSTİKLERİ
    # ========================================================

    stats[
        "strong"
    ] = int(
        (
            pool_df["Karar"]
            == "🟢 YARIN GÜÇLÜ ADAY"
        ).sum()
    )

    stats[
        "candidate"
    ] = int(
        (
            pool_df["Karar"]
            == "🟡 YARIN TRADE ADAYI"
        ).sum()
    )

    stats[
        "watch"
    ] = int(
        (
            pool_df["Karar"]
            == "🔵 YARIN İZLE"
        ).sum()
    )

    # ========================================================
    # DETAYLI TRADE ADAYI TEŞHİSİ
    # ========================================================

    stats[
        "score_62"
    ] = int(
        (
            pool_df["Yarın Skoru"]
            >= 62
        ).sum()
    )

    stats[
        "score_60"
    ] = int(
        (
            pool_df["Trade Skoru"]
            >= 60
        ).sum()
    )

    stats[
        "score_76"
    ] = int(
        (
            pool_df["Yarın Skoru"]
            >= 76
        ).sum()
    )

    stats[
        "trend_45"
    ] = int(
        (
            pool_df["Trend"]
            >= 45
        ).sum()
    )

    stats[
        "pullback_40"
    ] = int(
        (
            pool_df["Pullback"]
            >= 40
        ).sum()
    )

    stats[
        "rr_090"
    ] = int(
        (
            pool_df["R/R"]
            >= 0.90
        ).sum()
    )

    stats[
        "final_candidate"
    ] = int(
        (
            (
                pool_df[
                    "Yarın Skoru"
                ]
                >= 62
            )
            &
            (
                pool_df[
                    "Trend"
                ]
                >= 35
            )
            &
            (
                pool_df[
                    "Pullback"
                ]
                >= 30
            )
        ).sum()
    )

    stats[
        "final_strong"
    ] = int(
        (
            (
                pool_df[
                    "Yarın Skoru"
                ]
                >= 76
            )
            &
            (
                pool_df[
                    "Trend"
                ]
                >= 55
            )
            &
            (
                pool_df[
                    "Pullback"
                ]
                >= 45
            )
            &
            (
                pool_df[
                    "R/R"
                ]
                >= 0.90
            )
        ).sum()
    )

    # ========================================================
    # TEŞHİS
    # ========================================================

    st.markdown("---")

    st.subheader(
        "🔬 Tarama Teşhisi"
    )

    q1, q2, q3, q4, q5, q6, q7, q8 = (
        st.columns(8)
    )

    q1.metric(
        "BIST500",
        stats["universe"],
    )

    q2.metric(
        "Günlük Veri",
        stats["daily_data"],
    )

    q3.metric(
        "Likidite",
        stats["liquidity"],
    )

    q4.metric(
        "Trade Havuzu",
        stats["daily_pool"],
    )

    q5.metric(
        "15D Kontrol",
        stats["intraday_checked"],
    )

    q6.metric(
        "🟢 A Sınıfı",
        stats["trade_a"],
    )

    q7.metric(
        "🟡 B Sınıfı",
        stats["trade_b"],
    )

    q8.metric(
        "🔵 C Sınıfı",
        stats["trade_c"],
    )

    st.caption(
        f"""
        Günlük havuz: **{stats['daily_pool']}** |
        Gerçek 15D veri: **{stats['intraday_available']}** |
        🟢 Güçlü: **{stats['strong']}** |
        🟡 Trade Adayı: **{stats['candidate']}** |
        🔵 İzle: **{stats['watch']}** |
        🟢 A: **{stats['trade_a']}** |
        🟡 B: **{stats['trade_b']}** |
        🔵 C: **{stats['trade_c']}**
        """
    )

    # ========================================================
    # TRADE ADAYI NEDEN OLUŞTU / OLUŞMADI?
    # ========================================================

    st.markdown(
        "### 🔎 Trade Adayı Teşhis Paneli"
    )

    diagnosis = pd.DataFrame({

        "Aşama": [

            "Günlük Trade Havuzu",

            "Yarın Skoru ≥ 62",

            "Trend ≥ 45",

            "Pullback ≥ 40",

            "R/R ≥ 0.90",

            "Nihai Trade Adayı",

            "Yarın Skoru ≥ 76",

            "Nihai GÜNLÜK AL",

            "🟢 A Sınıfı",

            "🟡 B Sınıfı",

            "🔵 C Sınıfı",
        ],

        "Hisse Sayısı": [

            stats[
                "daily_pool"
            ],

            stats[
                "score_62"
            ],

            stats[
                "trend_45"
            ],

            stats[
                "pullback_40"
            ],

            stats[
                "rr_090"
            ],

            stats[
                "final_candidate"
            ],

            stats[
                "score_76"
            ],

            stats[
                "final_strong"
            ],

            stats[
                "trade_a"
            ],

            stats[
                "trade_b"
            ],

            stats[
                "trade_c"
            ],
        ],
    })

    st.dataframe(
        diagnosis,
        use_container_width=True,
        hide_index=True,
    )

    if (
        stats["final_candidate"]
        == 0
    ):

        st.warning(
            "⚠️ Trade Adayı oluşmadı. "
            "Yukarıdaki teşhis panelinde "
            "hangi aşamada adayların "
            "elendiğini görebilirsiniz."
        )

    elif (
        stats["final_candidate"]
        < 3
    ):

        st.info(
            f"ℹ️ Şu anda "
            f"{stats['final_candidate']} "
            "Trade Adayı var. "
            "Bunlar 15D teyit ve trade "
            "skoru açısından ayrıca "
            "değerlendirilmelidir."
        )

    else:

        st.success(
            f"🟡 "
            f"{stats['final_candidate']} "
            "adet Trade Adayı bulundu."
        )

    # ========================================================
    # HAVUZ
    # ========================================================

    st.markdown("---")

    st.subheader(
        "🏊 Günlük Trade Havuzu"
    )

    st.dataframe(
        pool_df.head(
            max_results
        )[

            [
                "Hisse",
                "Fiyat",
                "Yarın Skoru",
                "Trade Skoru",
                "Günlük Skor",
                "Trend",
                "Pullback",
                "15D Trend",
                "RSI",
                "Hacim Oranı",
                "R/R",
                "Trade Sınıfı",
                "Karar",
            ]
        ],

        use_container_width=True,

        hide_index=True,
    )

    # ========================================================
    # GÜÇLÜ TRADE
    # ========================================================

    st.markdown("---")

    st.subheader(
        "🟢 Günlük Trade Fırsatları"
    )

    buy_df = pool_df[
        pool_df["Karar"]
        == "🟢 YARIN GÜÇLÜ ADAY"
    ].copy()

    if buy_df.empty:

        st.info(
            "Bugün güçlü AL seviyesi oluşmadı. "
            "Aşağıdaki Trade Adayları "
            "havuzundan teyit beklenebilir."
        )

    else:

        st.dataframe(
            buy_df.head(
                max_results
            )[

                [
                    "Hisse",
                    "Fiyat",
                    "Yarın Skoru",
                    "Trade Skoru",
                    "Trend",
                    "Pullback",
                    "15D Trend",
                    "15D VWAP",
                    "RSI",
                    "Hacim Oranı",
                    "Stop",
                    "Hedef",
                    "R/R",
                    "Karar",
                ]
            ],

            use_container_width=True,

            hide_index=True,
        )

    # ========================================================
    # TRADE ADAYLARI
    # ========================================================

    st.markdown("---")

    st.subheader(
        "🟡 Trade Adayları"
    )

    candidate_df = pool_df[
        pool_df["Karar"]
        == "🟡 YARIN TRADE ADAYI"
    ].copy()

    if candidate_df.empty:

        st.info(
            "Trade Adayı oluşmadı."
        )

    else:

        st.dataframe(
            candidate_df.head(
                max_results
            )[

                [
                    "Hisse",
                    "Fiyat",
                    "Trade Sınıfı",
                    "Trade Skoru",
                    "Yarın Skoru",
                    "Günlük Skor",
                    "Trend",
                    "Pullback",
                    "15D Trend",
                    "15D VWAP",
                    "RSI",
                    "Hacim Oranı",
                    "R/R",
                    "Karar",
                ]
            ],

            use_container_width=True,

            hide_index=True,
        )

    # ========================================================
    # A / B / C TRADE SINIFLARI
    # ========================================================

    st.markdown("---")

    st.subheader(
        "🏅 Trade A / B / C Sınıfları"
    )

    a_df = pool_df[
        pool_df[
            "Trade Sınıfı"
        ]
        == "🟢 A"
    ].copy()

    b_df = pool_df[
        pool_df[
            "Trade Sınıfı"
        ]
        == "🟡 B"
    ].copy()

    c_df = pool_df[
        pool_df[
            "Trade Sınıfı"
        ]
        == "🔵 C"
    ].copy()

    ta, tb, tc = st.tabs(
        [
            "🟢 A SINIFI",
            "🟡 B SINIFI",
            "🔵 C SINIFI",
        ]
    )

    # --------------------------------------------------------
    # A SINIFI
    # --------------------------------------------------------

    with ta:

        st.caption(
            """
            **A Sınıfı:** Trade Adayları içerisindeki
            en güçlü teknik yapı. Yüksek trade skoru,
            güçlü günlük setup, yeterli R/R ve 15D teyit
            aranır.
            """
        )

        if a_df.empty:

            st.info(
                "Bugün A sınıfı Trade Adayı oluşmadı."
            )

        else:

            st.dataframe(
                a_df[
                    [
                        "Hisse",
                        "Fiyat",
                        "Trade Skoru",
                        "Yarın Skoru",
                        "Günlük Skor",
                        "Trend",
                        "Pullback",
                        "15D Trend",
                        "15D VWAP",
                        "RSI",
                        "Hacim Oranı",
                        "R/R",
                        "Stop",
                        "Hedef",
                    ]
                ],

                use_container_width=True,

                hide_index=True,
            )

    # --------------------------------------------------------
    # B SINIFI
    # --------------------------------------------------------

    with tb:

        st.caption(
            """
            **B Sınıfı:** Güçlü Trade Adayı.
            Teknik yapı olumlu ancak A sınıfındaki
            tüm teyitler henüz tamamlanmamış olabilir.
            """
        )

        if b_df.empty:

            st.info(
                "Bugün B sınıfı Trade Adayı oluşmadı."
            )

        else:

            st.dataframe(
                b_df[
                    [
                        "Hisse",
                        "Fiyat",
                        "Trade Skoru",
                        "Yarın Skoru",
                        "Günlük Skor",
                        "Trend",
                        "Pullback",
                        "15D Trend",
                        "15D VWAP",
                        "RSI",
                        "Hacim Oranı",
                        "R/R",
                    ]
                ],

                use_container_width=True,

                hide_index=True,
            )

    # --------------------------------------------------------
    # C SINIFI
    # --------------------------------------------------------

    with tc:

        st.caption(
            """
            **C Sınıfı:** Trade Adayı havuzunda bulunan
            ancak A/B seviyesinde yeterli teyide ulaşmamış
            hisseler. İzlenir, doğrudan öncelikli trade
            olarak değerlendirilmez.
            """
        )

        if c_df.empty:

            st.info(
                "Bugün C sınıfı Trade Adayı oluşmadı."
            )

        else:

            st.dataframe(
                c_df[
                    [
                        "Hisse",
                        "Fiyat",
                        "Trade Skoru",
                        "Yarın Skoru",
                        "Günlük Skor",
                        "Trend",
                        "Pullback",
                        "15D Trend",
                        "15D VWAP",
                        "RSI",
                        "Hacim Oranı",
                        "R/R",
                    ]
                ],

                use_container_width=True,

                hide_index=True,
            )

    # ========================================================
    # EN İYİ 10
    # ========================================================

    st.markdown("---")

    st.subheader(
        "🏆 En Güçlü 10 Setup"
    )

    st.dataframe(
        pool_df.head(10)[

            [
                "Hisse",
                "Fiyat",
                "Trade Skoru",
                "Yarın Skoru",
                "Trend",
                "Pullback",
                "15D Trend",
                "RSI",
                "Hacim Oranı",
                "R/R",
                "Trade Sınıfı",
                "Karar",
            ]
        ],

        use_container_width=True,

        hide_index=True,
    )

    # ========================================================
    # DETAY
    # ========================================================

    st.markdown("---")

    st.subheader(
        "🔍 Trade Detayı"
    )

    selected = st.selectbox(
        "Hisse seç",
        pool_df[
            "Hisse"
        ].tolist(),
    )

    selected_row = pool_df[
        pool_df["Hisse"]
        == selected
    ].iloc[0]

    d1, d2, d3, d4, d5 = (
        st.columns(5)
    )

    d1.metric(
        "Trade Skoru",
        f"{selected_row['Trade Skoru']:.1f}",
    )

    d2.metric(
        "Günlük Setup",
        f"{selected_row['Günlük Skor']:.1f}",
    )

    d3.metric(
        "15D",
        f"{selected_row['15D Trend']:.1f}",
    )

    d4.metric(
        "R/R",
        f"{selected_row['R/R']:.2f}",
    )

    d5.metric(
        "Sınıf",
        selected_row[
            "Trade Sınıfı"
        ],
    )

    st.markdown(
        "### 📌 Trade Planı"
    )

    p1, p2, p3, p4 = (
        st.columns(4)
    )

    p1.metric(
        "Giriş",
        f"{selected_row['Fiyat']:.2f} TL",
    )

    p2.metric(
        "Stop",
        f"{selected_row['Stop']:.2f} TL",
    )

    p3.metric(
        "Hedef",
        f"{selected_row['Hedef']:.2f} TL",
    )

    p4.metric(
        "R/R",
        f"{selected_row['R/R']:.2f}",
    )

    # ========================================================
    # KONTROL LİSTESİ
    # ========================================================

    st.markdown(
        "### ✅ Trade Kontrol Listesi"
    )

    price = float(
        selected_row["Fiyat"]
    )

    support = float(
        selected_row["Destek"]
    )

    resistance = float(
        selected_row["Direnç"]
    )

    checklist = {

        "Likidite yeterli": (
            selected_row[
                "Likidite"
            ]
            >= min_liquidity
        ),

        "Günlük trend kabul edilebilir": (
            selected_row[
                "Trend"
            ]
            >= 45
        ),

        "Pullback kabul edilebilir": (
            selected_row[
                "Pullback"
            ]
            >= 40
        ),

        "RSI aşırı zayıf değil": (
            selected_row[
                "RSI"
            ]
            >= 40
        ),

        "Hacim kabul edilebilir": (
            selected_row[
                "Hacim Oranı"
            ]
            >= 0.70
        ),

        "R/R kabul edilebilir": (
            selected_row[
                "R/R"
            ]
            >= 1.20
        ),

        "Direnç yukarıda": (
            resistance > price
        ),

        "Destek fiyatın altında": (
            support < price
        ),
    }

    for name, passed in (
        checklist.items()
    ):

        if passed:

            st.success(
                f"🟢 {name}"
            )

        else:

            st.warning(
                f"🟠 {name}"
            )

    # ========================================================
    # CSV
    # ========================================================

    csv = pool_df.to_csv(
        index=False,
        encoding="utf-8-sig",
    )

    st.download_button(
        "📥 Trade Havuzunu CSV Olarak İndir",
        data=csv,
        file_name=(
            f"gunluk_trade_havuzu_"
            f"{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
        ),
        mime="text/csv",
        use_container_width=True,
    )


# ============================================================
# ALT
# ============================================================

st.markdown("---")

st.caption(
    """
    ⚠️ Bu modül yatırım tavsiyesi değildir.

    Günlük trade skoru; günlük trend, pullback, momentum,
    hacim, VWAP, 15 dakikalık teyit ve risk/ödül bileşenlerinden
    oluşan bir sıralama sistemidir.

    A/B/C sınıfları ise yalnızca mevcut Trade Adaylarının
    teknik kalite seviyesini birbirinden ayırmak için kullanılır.
    """
)