import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf


# ============================================================
# SAYFA AYARLARI
# ============================================================

st.set_page_config(
    page_title="BIST AI PRO - Hisse Bazlı Karar Sistemi",
    page_icon="📊",
    layout="wide"
)


# ============================================================
# SİSTEM AYARLARI
# ============================================================

# Genel skor ağırlıkları
SHORT_WEIGHT = 0.20
MID_WEIGHT = 0.35
LONG_WEIGHT = 0.45

# Tek hisse için normal maksimum hedef ağırlık
MAX_TARGET_WEIGHT = 15.0

# Tek işlemde pozisyonun en fazla ne kadarı değişebilir?
MAX_INCREASE_PCT = 25.0
MAX_REDUCE_PCT = 25.0

# Çok güçlü teyitte biraz daha yüksek artırma
STRONG_INCREASE_PCT = 35.0

# %100 çıkış koruması
EMERGENCY_EXIT = True

# Veri güvenliği
MIN_PRICE_HISTORY = 200

# Piyasa cache
MARKET_CACHE_TTL = 1800

# Şirket verisi cache
INFO_CACHE_TTL = 21600


# ============================================================
# YARDIMCI FONKSİYONLAR
# ============================================================

def safe_float(value, default=np.nan):

    try:

        if value is None:
            return default

        if pd.isna(value):
            return default

        return float(value)

    except Exception:

        return default


def clamp(value, low=0, high=100):

    value = safe_float(value, low)

    return max(
        low,
        min(high, value)
    )


def parse_number(value):

    if pd.isna(value):
        return np.nan

    if isinstance(
        value,
        (int, float, np.number)
    ):
        return float(value)

    text = str(value).strip()

    text = text.replace(
        "%",
        ""
    )

    text = text.replace(
        " ",
        ""
    )

    # Türkçe sayı formatı
    if "," in text and "." in text:

        text = text.replace(
            ".",
            ""
        )

        text = text.replace(
            ",",
            "."
        )

    elif "," in text:

        text = text.replace(
            ",",
            "."
        )

    try:

        return float(text)

    except Exception:

        return np.nan


def normalize_weight(value):

    value = safe_float(
        value,
        0
    )

    if value <= 1:

        return value * 100

    return value


def safe_bool(value):

    try:

        if pd.isna(value):
            return False

        return bool(value)

    except Exception:

        return False


def fmt_pct(value):

    value = safe_float(
        value,
        0
    )

    return f"%{value:.1f}"


def fmt_money(value):

    value = safe_float(
        value,
        0
    )

    return f"{value:,.2f} TL"


# ============================================================
# YAHOO FİYAT VERİSİ
# ============================================================

@st.cache_data(
    ttl=900,
    show_spinner=False
)
def download_price_data(symbol):

    ticker = str(
        symbol
    ).upper().strip()

    if not ticker.endswith(".IS"):

        ticker += ".IS"

    try:

        df = yf.download(
            ticker,
            period="2y",
            interval="1d",
            auto_adjust=False,
            progress=False
        )

        if df is None or df.empty:

            return None

        # MultiIndex düzeltmesi
        if isinstance(
            df.columns,
            pd.MultiIndex
        ):

            df.columns = (
                df.columns
                .get_level_values(0)
            )

        required = [
            "Close",
            "Volume"
        ]

        for col in required:

            if col not in df.columns:

                return None

        df = df.copy()

        df["Close"] = pd.to_numeric(
            df["Close"],
            errors="coerce"
        )

        df["Volume"] = pd.to_numeric(
            df["Volume"],
            errors="coerce"
        )

        df = df.dropna(
            subset=[
                "Close"
            ]
        )

        if len(df) < 80:

            return None

        return df

    except Exception:

        return None


# ============================================================
# ŞİRKET BİLGİLERİ
# ============================================================

@st.cache_data(
    ttl=INFO_CACHE_TTL,
    show_spinner=False
)
def get_info(symbol):

    ticker = str(
        symbol
    ).upper().strip()

    if not ticker.endswith(".IS"):

        ticker += ".IS"

    try:

        info = yf.Ticker(
            ticker
        ).info

        if not isinstance(
            info,
            dict
        ):

            return {}

        return info

    except Exception:

        return {}


# ============================================================
# TEKNİK GÖSTERGELER
# ============================================================

def build_indicators(df):

    df = df.copy()

    close = df["Close"]

    volume = df["Volume"]

    # --------------------------------------------------------
    # HAREKETLİ ORTALAMALAR
    # --------------------------------------------------------

    df["MA5"] = (
        close
        .rolling(5)
        .mean()
    )

    df["MA20"] = (
        close
        .rolling(20)
        .mean()
    )

    df["MA50"] = (
        close
        .rolling(50)
        .mean()
    )

    df["MA100"] = (
        close
        .rolling(100)
        .mean()
    )

    df["MA200"] = (
        close
        .rolling(200)
        .mean()
    )

    # --------------------------------------------------------
    # EMA
    # --------------------------------------------------------

    df["EMA9"] = (
        close
        .ewm(
            span=9,
            adjust=False
        )
        .mean()
    )

    df["EMA20"] = (
        close
        .ewm(
            span=20,
            adjust=False
        )
        .mean()
    )

    # --------------------------------------------------------
    # RSI - Wilder yaklaşımı
    # --------------------------------------------------------

    delta = close.diff()

    gain = delta.clip(
        lower=0
    )

    loss = -delta.clip(
        upper=0
    )

    avg_gain = (
        gain
        .ewm(
            alpha=1 / 14,
            adjust=False,
            min_periods=14
        )
        .mean()
    )

    avg_loss = (
        loss
        .ewm(
            alpha=1 / 14,
            adjust=False,
            min_periods=14
        )
        .mean()
    )

    rs = (
        avg_gain /
        avg_loss.replace(
            0,
            np.nan
        )
    )

    df["RSI"] = (
        100 -
        (
            100 /
            (1 + rs)
        )
    )

    # --------------------------------------------------------
    # MOMENTUM
    # --------------------------------------------------------

    df["MOM5"] = (
        (
            close /
            close.shift(5)
        ) - 1
    ) * 100

    df["MOM20"] = (
        (
            close /
            close.shift(20)
        ) - 1
    ) * 100

    df["MOM60"] = (
        (
            close /
            close.shift(60)
        ) - 1
    ) * 100

    df["MOM120"] = (
        (
            close /
            close.shift(120)
        ) - 1
    ) * 100

    # --------------------------------------------------------
    # HACİM
    # --------------------------------------------------------

    df["VOL20"] = (
        volume
        .rolling(20)
        .mean()
    )

    df["VOLUME_RATIO"] = (
        volume /
        df["VOL20"].replace(
            0,
            np.nan
        )
    )

    # --------------------------------------------------------
    # 5 GÜNLÜK KESİŞİM
    # --------------------------------------------------------

    df["CROSS_UP_5"] = (

        (
            df["Close"] >
            df["MA5"]
        )

        &

        (
            df["Close"].shift(1)
            <=
            df["MA5"].shift(1)
        )

    )

    df["CROSS_DOWN_5"] = (

        (
            df["Close"] <
            df["MA5"]
        )

        &

        (
            df["Close"].shift(1)
            >=
            df["MA5"].shift(1)
        )

    )

    # --------------------------------------------------------
    # TREND YAPISI
    # --------------------------------------------------------

    df["TREND_SHORT"] = (
        (
            df["EMA9"] >
            df["EMA20"]
        )
    )

    df["TREND_MID"] = (
        (
            df["MA20"] >
            df["MA50"]
        )
    )

    df["TREND_LONG"] = (
        (
            df["MA50"] >
            df["MA100"]
        )
        &
        (
            df["MA100"] >
            df["MA200"]
        )
    )

    return df


# ============================================================
# TEKNİK SKOR MOTORU
# ============================================================

def technical_engine(df):

    last = df.iloc[-1]

    price = safe_float(
        last["Close"],
        0
    )

    previous = safe_float(
        df["Close"].iloc[-2],
        price
    )

    if previous > 0:

        daily_change = (
            (
                price /
                previous
            ) - 1
        ) * 100

    else:

        daily_change = 0

    ma5 = safe_float(
        last["MA5"]
    )

    ma20 = safe_float(
        last["MA20"]
    )

    ma50 = safe_float(
        last["MA50"]
    )

    ma100 = safe_float(
        last["MA100"]
    )

    ma200 = safe_float(
        last["MA200"]
    )

    ema9 = safe_float(
        last["EMA9"]
    )

    ema20 = safe_float(
        last["EMA20"]
    )

    rsi = safe_float(
        last["RSI"],
        50
    )

    mom5 = safe_float(
        last["MOM5"],
        0
    )

    mom20 = safe_float(
        last["MOM20"],
        0
    )

    mom60 = safe_float(
        last["MOM60"],
        0
    )

    mom120 = safe_float(
        last["MOM120"],
        0
    )

    volume_ratio = safe_float(
        last["VOLUME_RATIO"],
        1
    )

    cross_up = safe_bool(
        last["CROSS_UP_5"]
    )

    cross_down = safe_bool(
        last["CROSS_DOWN_5"]
    )

    # ========================================================
    # KISA VADE
    # ========================================================

    short = 0

    # Fiyat / MA5
    if (
        not np.isnan(ma5)
        and price > ma5
    ):

        short += 15

    # Fiyat / EMA9
    if (
        not np.isnan(ema9)
        and price > ema9
    ):

        short += 15

    # EMA9 / EMA20
    if (
        not np.isnan(ema9)
        and not np.isnan(ema20)
        and ema9 > ema20
    ):

        short += 20

    # 5 günlük momentum
    if mom5 > 0:

        short += 10

    # 20 günlük momentum
    if mom20 > 0:

        short += 10

    # RSI
    if 45 <= rsi <= 65:

        short += 15

    elif 65 < rsi <= 72:

        short += 10

    elif 40 <= rsi < 45:

        short += 5

    elif rsi > 80:

        short -= 5

    # Hacim
    if volume_ratio >= 1.50:

        short += 10

    elif volume_ratio >= 1.10:

        short += 5

    # 5 günlük yukarı kesişim
    if cross_up:

        short += 5

    short = clamp(
        short
    )

    # ========================================================
    # ORTA VADE
    # ========================================================

    mid = 0

    if (
        not np.isnan(ma20)
        and price > ma20
    ):

        mid += 15

    if (
        not np.isnan(ma50)
        and price > ma50
    ):

        mid += 15

    if (
        not np.isnan(ma20)
        and not np.isnan(ma50)
        and ma20 > ma50
    ):

        mid += 20

    if (
        not np.isnan(ema9)
        and not np.isnan(ema20)
        and ema9 > ema20
    ):

        mid += 10

    if mom20 > 0:

        mid += 10

    if mom60 > 0:

        mid += 15

    if (
        not np.isnan(ma100)
        and price > ma100
    ):

        mid += 10

    if volume_ratio >= 1:

        mid += 5

    mid = clamp(
        mid
    )

    # ========================================================
    # UZUN VADE TEKNİK
    # ========================================================

    long_technical = 0

    if (
        not np.isnan(ma50)
        and price > ma50
    ):

        long_technical += 15

    if (
        not np.isnan(ma100)
        and price > ma100
    ):

        long_technical += 15

    if (
        not np.isnan(ma50)
        and not np.isnan(ma100)
        and ma50 > ma100
    ):

        long_technical += 20

    if (
        not np.isnan(ma200)
        and price > ma200
    ):

        long_technical += 20

    if (
        not np.isnan(ma100)
        and not np.isnan(ma200)
        and ma100 > ma200
    ):

        long_technical += 10

    if mom60 > 0:

        long_technical += 10

    if mom120 > 0:

        long_technical += 10

    long_technical = clamp(
        long_technical
    )

    # ========================================================
    # TEKNİK ÇIKIŞ RİSKİ
    # ========================================================

    technical_breakdown = 0

    if (
        not np.isnan(ma20)
        and price < ma20
    ):

        technical_breakdown += 1

    if (
        not np.isnan(ma50)
        and price < ma50
    ):

        technical_breakdown += 1

    if (
        not np.isnan(ma200)
        and price < ma200
    ):

        technical_breakdown += 1

    if mom60 < 0:

        technical_breakdown += 1

    if mom120 < 0:

        technical_breakdown += 1

    return {

        "price": price,

        "daily_change":
            daily_change,

        "short":
            short,

        "mid":
            mid,

        "long_technical":
            long_technical,

        "rsi":
            rsi,

        "mom5":
            mom5,

        "mom20":
            mom20,

        "mom60":
            mom60,

        "mom120":
            mom120,

        "volume_ratio":
            volume_ratio,

        "cross_up":
            cross_up,

        "cross_down":
            cross_down,

        "price_above_ema9":
            price > ema9
            if not np.isnan(ema9)
            else False,

        "ema9_above_ema20":
            ema9 > ema20
            if (
                not np.isnan(ema9)
                and not np.isnan(ema20)
            )
            else False,

        "price_above_ma50":
            price > ma50
            if not np.isnan(ma50)
            else False,

        "price_above_ma200":
            price > ma200
            if not np.isnan(ma200)
            else False,

        "technical_breakdown":
            technical_breakdown

    }


# ============================================================
# FUNDAMENTAL MOTOR
# ============================================================

def fundamental_engine(info):

    score = 50

    reasons = []

    available = 0

    # --------------------------------------------------------
    # ROE
    # --------------------------------------------------------

    roe = safe_float(
        info.get(
            "returnOnEquity"
        )
    )

    if not np.isnan(roe):

        available += 1

        if roe >= 0.20:

            score += 15

            reasons.append(
                "ROE güçlü"
            )

        elif roe >= 0.10:

            score += 8

        elif roe < 0:

            score -= 15

            reasons.append(
                "ROE negatif"
            )

    # --------------------------------------------------------
    # NET KÂR MARJI
    # --------------------------------------------------------

    margin = safe_float(
        info.get(
            "profitMargins"
        )
    )

    if not np.isnan(margin):

        available += 1

        if margin >= 0.15:

            score += 12

            reasons.append(
                "net kâr marjı güçlü"
            )

        elif margin >= 0.05:

            score += 5

        elif margin < 0:

            score -= 12

            reasons.append(
                "net kâr marjı negatif"
            )

    # --------------------------------------------------------
    # GELİR BÜYÜMESİ
    # --------------------------------------------------------

    revenue_growth = safe_float(
        info.get(
            "revenueGrowth"
        )
    )

    if not np.isnan(
        revenue_growth
    ):

        available += 1

        if revenue_growth >= 0.20:

            score += 10

            reasons.append(
                "gelir büyümesi güçlü"
            )

        elif revenue_growth >= 0.05:

            score += 5

        elif revenue_growth < 0:

            score -= 5

            reasons.append(
                "gelir büyümesi negatif"
            )

    # --------------------------------------------------------
    # KÂR BÜYÜMESİ
    # --------------------------------------------------------

    earnings_growth = safe_float(
        info.get(
            "earningsGrowth"
        )
    )

    if not np.isnan(
        earnings_growth
    ):

        available += 1

        if earnings_growth >= 0.20:

            score += 10

            reasons.append(
                "kâr büyümesi güçlü"
            )

        elif earnings_growth >= 0.05:

            score += 5

        elif earnings_growth < 0:

            score -= 10

            reasons.append(
                "kâr büyümesi negatif"
            )

    # --------------------------------------------------------
    # BORÇ
    # --------------------------------------------------------

    debt_equity = safe_float(
        info.get(
            "debtToEquity"
        )
    )

    if not np.isnan(
        debt_equity
    ):

        available += 1

        if debt_equity < 70:

            score += 10

        elif debt_equity < 120:

            score += 4

        elif debt_equity > 180:

            score -= 12

            reasons.append(
                "borçluluk yüksek"
            )

    # --------------------------------------------------------
    # TEMETTÜ
    # --------------------------------------------------------

    dividend = safe_float(
        info.get(
            "dividendYield"
        )
    )

    if not np.isnan(
        dividend
    ):

        available += 1

        if dividend >= 0.03:

            score += 5

            reasons.append(
                "temettü desteği var"
            )

    score = clamp(
        score
    )

    completeness = (
        available /
        6
    ) * 100

    return (
        score,
        reasons,
        completeness
    )


# ============================================================
# FİNANSAL MOTOR
# ============================================================

def financial_engine(info):

    score = 50

    reasons = []

    available = 0

    # --------------------------------------------------------
    # CURRENT RATIO
    # --------------------------------------------------------

    current_ratio = safe_float(
        info.get(
            "currentRatio"
        )
    )

    if not np.isnan(
        current_ratio
    ):

        available += 1

        if current_ratio >= 1.5:

            score += 15

            reasons.append(
                "likidite güçlü"
            )

        elif current_ratio >= 1:

            score += 5

        elif current_ratio < 1:

            score -= 15

            reasons.append(
                "likidite zayıf"
            )

    # --------------------------------------------------------
    # SERBEST NAKİT AKIŞI
    # --------------------------------------------------------

    fcf = safe_float(
        info.get(
            "freeCashflow"
        )
    )

    if not np.isnan(
        fcf
    ):

        available += 1

        if fcf > 0:

            score += 12

            reasons.append(
                "serbest nakit akışı pozitif"
            )

        elif fcf < 0:

            score -= 12

            reasons.append(
                "serbest nakit akışı negatif"
            )

    # --------------------------------------------------------
    # OPERASYONEL MARJ
    # --------------------------------------------------------

    operating_margin = safe_float(
        info.get(
            "operatingMargins"
        )
    )

    if not np.isnan(
        operating_margin
    ):

        available += 1

        if operating_margin >= 0.15:

            score += 12

            reasons.append(
                "operasyonel kârlılık güçlü"
            )

        elif operating_margin >= 0.05:

            score += 5

        elif operating_margin < 0:

            score -= 12

            reasons.append(
                "operasyonel kârlılık zayıf"
            )

    # --------------------------------------------------------
    # BRÜT MARJ
    # --------------------------------------------------------

    gross_margin = safe_float(
        info.get(
            "grossMargins"
        )
    )

    if not np.isnan(
        gross_margin
    ):

        available += 1

        if gross_margin >= 0.25:

            score += 8

        elif gross_margin < 0:

            score -= 8

    score = clamp(
        score
    )

    completeness = (
        available /
        4
    ) * 100

    return (
        score,
        reasons,
        completeness
    )


# ============================================================
# SEKTÖR
# ============================================================

SECTOR_MAP = {

    "EREGL": "Metal",
    "KCAER": "Metal",
    "ISDMR": "Metal",

    "BIMAS": "Perakende",
    "MGROS": "Perakende",

    "TUPRS": "Enerji",

    "AKSA": "Kimya",

    "CCOLA": "Gıda",

    "TKFEN": "Holding/İnşaat",

    "KCHOL": "Holding",

    "MOBTL": "Teknoloji"
}


SECTOR_BASE = {

    "Metal": 55,

    "Perakende": 70,

    "Enerji": 65,

    "Kimya": 60,

    "Gıda": 70,

    "Holding/İnşaat": 60,

    "Holding": 70,

    "Teknoloji": 60,

    "Diğer": 55
}


def sector_engine(symbol):

    sector_name = SECTOR_MAP.get(
        symbol,
        "Diğer"
    )

    score = SECTOR_BASE.get(
        sector_name,
        55
    )

    return (
        score,
        sector_name
    )


# ============================================================
# PİYASA MOTORU
# ============================================================

@st.cache_data(
    ttl=MARKET_CACHE_TTL,
    show_spinner=False
)
def market_engine():

    score = 50

    reasons = []

    try:

        bist = yf.download(
            "XU100.IS",
            period="1y",
            interval="1d",
            progress=False,
            auto_adjust=False
        )

        if (
            bist is None
            or bist.empty
        ):

            return (
                50,
                [
                    "Piyasa verisi alınamadı"
                ]
            )

        if isinstance(
            bist.columns,
            pd.MultiIndex
        ):

            bist.columns = (
                bist.columns
                .get_level_values(0)
            )

        close = bist["Close"]

        close = pd.to_numeric(
            close,
            errors="coerce"
        ).dropna()

        if len(close) >= 50:

            mom20 = (
                (
                    close.iloc[-1] /
                    close.iloc[-20]
                ) - 1
            ) * 100

            mom50 = (
                (
                    close.iloc[-1] /
                    close.iloc[-50]
                ) - 1
            ) * 100

            if mom20 > 0:

                score += 8

                reasons.append(
                    "BIST 20 günlük momentum pozitif"
                )

            else:

                score -= 8

                reasons.append(
                    "BIST 20 günlük momentum negatif"
                )

            if mom50 > 0:

                score += 8

                reasons.append(
                    "BIST 50 günlük momentum pozitif"
                )

            else:

                score -= 8

                reasons.append(
                    "BIST 50 günlük momentum negatif"
                )

        return (
            clamp(score),
            reasons
        )

    except Exception:

        return (
            50,
            [
                "Piyasa verisi sınırlı"
            ]
        )


# ============================================================
# ALIM / SATIŞ TEYİT MOTORU
# ============================================================
# ============================================================
# ALIM / SATIŞ TEYİT MOTORU
# ============================================================

def confirmation_engine(technical):

    """
    ALIM / SATIŞ / DÜŞÜŞ TEYİT SİSTEMİ

    ALIM TEYİDİ:
        6 teknik koşuldan en az 4'ü olumlu olmalı.
        Ayrıca kısa ve orta vade yeterli güçte olmalı.

    DÜŞÜŞ SİNYALİ:
        Erken uyarıdır.
        Satış emri değildir.

    SATIŞ TEYİDİ:
        6 teknik satış koşulundan en az 4'ü oluşmalı.
        Ayrıca kısa veya orta vadede bozulma bulunmalı.

    Tek bir gösterge tek başına AL / SAT üretmez.
    """

    # ========================================================
    # ALIM KONTROLLERİ
    # ========================================================

    buy_checks = {

        "Fiyat EMA9 üzerinde":
            technical["price_above_ema9"],

        "EMA9 > EMA20":
            technical["ema9_above_ema20"],

        "5G yukarı kesişim":
            technical["cross_up"],

        "20G momentum pozitif":
            technical["mom20"] > 0,

        "60G momentum pozitif":
            technical["mom60"] > 0,

        "Hacim destekli":
            technical["volume_ratio"] >= 1.10,
    }

    buy_count = sum(
        bool(value)
        for value in buy_checks.values()
    )

    # ========================================================
    # SATIŞ KONTROLLERİ
    # ========================================================

    sell_checks = {

        "Fiyat EMA9 altında":
            not technical["price_above_ema9"],

        "EMA9 < EMA20":
            not technical["ema9_above_ema20"],

        "5G aşağı kesişim":
            technical["cross_down"],

        "20G momentum negatif":
            technical["mom20"] < 0,

        "60G momentum negatif":
            technical["mom60"] < 0,

        "Fiyat MA50 altında":
            not technical["price_above_ma50"],
    }

    sell_count = sum(
        bool(value)
        for value in sell_checks.values()
    )

    # ========================================================
    # ALIM TEYİDİ
    # ========================================================

    buy_confirmation = (
        buy_count >= 4
        and technical["short"] >= 60
        and technical["mid"] >= 55
    )

    # ========================================================
    # SATIŞ TEYİDİ
    # ========================================================

    sell_confirmation = (
        sell_count >= 4
        and (
            technical["short"] < 50
            or technical["mid"] < 55
        )
    )

    # ========================================================
    # DÜŞÜŞ SİNYALİ
    # ========================================================

    decline_signal = (

        sell_count >= 3

        or technical["technical_breakdown"] >= 3

        or (
            technical["short"] < 40
            and technical["mid"] < 50
        )
    )

    # ========================================================
    # YAZILAR
    # ========================================================

    if buy_confirmation:

        buy_text = "🟢 ALIM TEYİDİ VAR"

    else:

        buy_text = "🟡 ALIM TEYİDİ YOK"

    # --------------------------------------------------------

    if sell_confirmation:

        sell_text = "🔴 SATIŞ TEYİDİ VAR"

    else:

        sell_text = "🟡 SATIŞ TEYİDİ YOK"

    # --------------------------------------------------------

    if decline_signal:

        decline_text = "🔴 DÜŞÜŞ SİNYALİ VAR"

    else:

        decline_text = "🟢 DÜŞÜŞ SİNYALİ YOK"

    # ========================================================
    # SONUÇ
    # ========================================================

    return {

        "buy_count":
            buy_count,

        "sell_count":
            sell_count,

        "buy_confirmation":
            buy_confirmation,

        "sell_confirmation":
            sell_confirmation,

        "decline_signal":
            decline_signal,

        "buy_text":
            buy_text,

        "sell_text":
            sell_text,

        "decline_text":
            decline_text,

        "buy_checks":
            buy_checks,

        "sell_checks":
            sell_checks,
    }
# ============================================================
# VADE SKORLARI

# ============================================================

def horizon_engine(
    technical,
    fundamental,
    financial,
    sector,
    market
):

    # ========================================================
    # KISA
    # ========================================================

    short = (

        technical["short"] * 0.65

        +

        technical["mid"] * 0.10

        +

        market * 0.10

        +

        sector * 0.05

        +

        fundamental * 0.05

        +

        financial * 0.05

    )

    # ========================================================
    # ORTA
    # ========================================================

    mid = (

        technical["mid"] * 0.35

        +

        fundamental * 0.20

        +

        financial * 0.20

        +

        sector * 0.10

        +

        market * 0.15

    )

    # ========================================================
    # UZUN
    # ========================================================

    long = (

        fundamental * 0.30

        +

        financial * 0.25

        +

        technical["long_technical"] * 0.20

        +

        sector * 0.15

        +

        market * 0.10

    )

    # ========================================================
    # GENEL
    # ========================================================

    general = (

        short * SHORT_WEIGHT

        +

        mid * MID_WEIGHT

        +

        long * LONG_WEIGHT

    )

    return {

        "short": round(
            clamp(short),
            1
        ),

        "mid": round(
            clamp(mid),
            1
        ),

        "long": round(
            clamp(long),
            1
        ),

        "general": round(
            clamp(general),
            1
        )

    }


# ============================================================
# KALİTE MOTORU
# ============================================================

def quality_engine(
    long_score,
    fundamental,
    financial,
    fundamental_completeness,
    financial_completeness
):

    data_completeness = (
        fundamental_completeness
        +
        financial_completeness
    ) / 2

    if (
        long_score >= 75
        and fundamental >= 70
        and financial >= 65
        and data_completeness >= 60
    ):

        return (
            "🟢 A - Güçlü",
            "Uzun vadeli yatırım kalitesi güçlü."
        )

    if (
        long_score >= 65
        and fundamental >= 55
        and financial >= 55
        and data_completeness >= 40
    ):

        return (
            "🟢 B - Olumlu",
            "Uzun vadeli yapı olumlu."
        )

    if long_score >= 50:

        return (
            "🟡 C - İzle",
            "Uzun vadede üstünlük sınırlı."
        )

    return (
        "🔴 D - Zayıf",
        "Uzun vadeli yapı zayıf."
    )


# ============================================================
# HEDEF AĞIRLIK MOTORU
# ============================================================

def target_weight_engine(
    scores,
    quality,
    fundamental,
    financial
):

    long = scores["long"]

    general = scores["general"]

    # --------------------------------------------------------
    # TEMEL HEDEF
    # --------------------------------------------------------

    if long >= 80:

        target = 14

    elif long >= 72:

        target = 12

    elif long >= 65:

        target = 10

    elif long >= 58:

        target = 8

    elif long >= 50:

        target = 6

    elif long >= 42:

        target = 4

    else:

        target = 2

    # --------------------------------------------------------
    # GENEL SKOR AYARI
    # --------------------------------------------------------

    if general >= 75:

        target += 1

    elif general < 50:

        target -= 1

    # --------------------------------------------------------
    # A KALİTE KORUMASI
    # --------------------------------------------------------

    if quality.startswith(
        "🟢 A"
    ):

        target = max(
            target,
            10
        )

    # --------------------------------------------------------
    # ZAYIF KALİTE
    # --------------------------------------------------------

    if quality.startswith(
        "🔴 D"
    ):

        target = min(
            target,
            4
        )

    # --------------------------------------------------------
    # TEMEL / FİNANSAL ÇOK ZAYIFSA
    # --------------------------------------------------------

    if (
        fundamental < 40
        and financial < 40
    ):

        target = min(
            target,
            3
        )

    return round(
        clamp(
            target,
            0,
            MAX_TARGET_WEIGHT
        ),
        1
    )


# ============================================================
# KARAR VADE MOTORU
# ============================================================

def determine_decision_horizon(
    scores,
    quality
):

    short = scores["short"]

    mid = scores["mid"]

    long = scores["long"]

    # Uzun vadeli kalite güçlü
    if (
        long >= 70
        and (
            short < 55
            or mid < 60
        )
    ):

        return (
            "🏦 Uzun Vade",
            "Uzun vadeli yapı güçlü; kısa vadeli dalgalanma ana kararı değiştirmiyor."
        )

    # Kısa vadeli güçlü teyit
    if (
        short >= 75
        and mid >= 65
    ):

        return (
            "⚡ Kısa Vade",
            "Kısa ve orta vadeli teknik momentum birlikte güçlü."
        )

    # Orta vadeli
    if (
        mid >= 65
        and long >= 55
    ):

        return (
            "📅 Orta Vade",
            "Orta vadeli trend ve temel yapı birlikte değerlendiriliyor."
        )

    if long >= 65:

        return (
            "🏦 Uzun Vade",
            "Kararın ana dayanağı uzun vadeli yatırım kalitesi."
        )

    return (
        "🔎 İzleme",
        "Vade yönünde yeterli üstünlük oluşmadı."
    )


# ============================================================
# İŞLEM MOTORU
# ============================================================
# ============================================================
# İŞLEM MOTORU — KARAR HİYERARŞİSİ
# ============================================================

def action_engine(
    scores,
    fundamental,
    financial,
    current_weight,
    target_weight,
    quality,
    technical,
    confirmations,
    position_exists
):

    short = scores["short"]
    mid = scores["mid"]
    long = scores["long"]
    general = scores["general"]

    buy_confirmation = confirmations["buy_confirmation"]
    sell_confirmation = confirmations["sell_confirmation"]
    decline_signal = confirmations["decline_signal"]

    # ========================================================
    # 1. POZİSYON YOKSA
    # ========================================================

    if not position_exists:

        # Düşüş sinyali varsa kesinlikle ALMA
        if decline_signal:

            return (
                "⛔ ALMA / DÜŞÜŞ SİNYALİ",
                0.0,
                "Hissede düşüş sinyali var. "
                "Portföyde pozisyon bulunmadığı için yeni alım yapılmıyor. "
                "Önce düşüş sinyalinin ortadan kalkması bekleniyor."
            )

        # Alım teyidi yoksa ALMA
        if not buy_confirmation:

            return (
                "🟡 İZLE / TEYİT BEKLE",
                0.0,
                "Portföyde pozisyon bulunmuyor ve alım teyidi oluşmadı. "
                "Teyitsiz alım yapılmıyor."
            )

        # Alım teyidi var ama kısa/orta vade zayıf
        if short < 65 or mid < 60:

            return (
                "🟡 İZLE / GÜÇLENME BEKLE",
                0.0,
                "Alım teyidi oluşmuş olsa da kısa veya orta vadeli yapı "
                "yeterince güçlü değil. Pozisyon açmadan önce güçlenme bekleniyor."
            )

        # Gerçek başlangıç alımı
        return (
            "🟢 KADEMELİ ARTIR",
            20.0,
            "Portföyde pozisyon bulunmuyor. "
            "Alım teyidi mevcut ve kısa/orta vadeli yapı yeterince güçlü. "
            "Kontrollü başlangıç pozisyonu öneriliyor."
        )

    # ========================================================
    # 2. KRİTİK ÇIKIŞ
    # ========================================================

    severe_long_failure = long < 40
    severe_fundamental_failure = fundamental < 35
    severe_financial_failure = financial < 35
    severe_technical_failure = (
        technical["technical_breakdown"] >= 4
    )

    if (
        EMERGENCY_EXIT
        and position_exists
        and sell_confirmation
        and severe_long_failure
        and severe_fundamental_failure
        and severe_financial_failure
        and severe_technical_failure
    ):

        return (
            "🔴 ÇIKIŞ",
            -100.0,
            "Uzun vadeli, temel, finansal ve teknik yapı "
            "aynı anda ciddi biçimde bozulmuş ve satış teyidi oluşmuş. "
            "Pozisyon tamamen kapatılabilir."
        )

    # ========================================================
    # 3. A KALİTE ŞİRKET KORUMASI
    # ========================================================

    if quality.startswith("🟢 A"):

        # Düşüş sinyali var ama satış teyidi yok
        if decline_signal and not sell_confirmation:

            return (
                "🟡 TUT / TEYİT BEKLE",
                0.0,
                "A kalite şirket korunuyor. "
                "Düşüş sinyali mevcut ancak satış teyidi oluşmadı. "
                "Kısa vadeli zayıflık tek başına satış gerekçesi değildir."
            )

        # Satış teyidi varsa kaliteli şirkette önce azalt
        if sell_confirmation:

            if long >= 70 and fundamental >= 60 and financial >= 60:

                return (
                    "🟠 KADEMELİ AZALT",
                    -20.0,
                    "Satış teyidi oluştu ancak şirketin uzun vadeli, "
                    "temel ve finansal yapısı güçlü. "
                    "Tam çıkış yerine kontrollü pozisyon azaltımı öneriliyor."
                )

            return (
                "🔴 AZALT",
                -25.0,
                "Satış teyidi oluştu ve şirketin uzun vadeli yapısında "
                "zayıflama görülüyor. Pozisyon kontrollü azaltılmalı."
            )

        # Hedefin çok üzerindeyse portföy dengelemesi
        if current_weight > target_weight + 7:

            return (
                "🟡 TUT / KADEMELİ AZALT",
                -10.0,
                "Şirketin yatırım kalitesi güçlü. "
                "Portföy ağırlığı hedefin belirgin üzerinde. "
                "Yalnızca portföy dengelemesi amacıyla kademeli azaltım öneriliyor."
            )

        # Hedefin biraz üzerindeyse satış yapma
        if current_weight > target_weight + 3:

            return (
                "🟡 TUT",
                0.0,
                "Uzun vadeli kalite güçlü. "
                "Mevcut ağırlık biraz yüksek ancak satış teyidi olmadığı için "
                "sert satış yapılmıyor."
            )

        # Pozisyon hedefin altında + alım teyidi
        if (
            current_weight < target_weight - 3
            and short >= 65
            and mid >= 60
            and buy_confirmation
        ):

            return (
                "🟢 KADEMELİ ARTIR",
                20.0,
                "Uzun vadeli kalite güçlü, portföy ağırlığı düşük "
                "ve alım teyidi oluştuğu için kademeli artırma öneriliyor."
            )

        # Kısa vade zayıf
        if short < 45:

            return (
                "🟡 TUT / TEYİT BEKLE",
                0.0,
                "Uzun vadeli kalite güçlü ancak kısa vadeli momentum zayıf. "
                "Yeni alım veya satış için teyit bekleniyor."
            )

        # A kalite normal durum
        return (
            "🟢 TUT",
            0.0,
            "Uzun vadeli kalite güçlü ve mevcut pozisyon dengeli."
        )

    # ========================================================
    # 4. B / C KALİTE — SATIŞ TEYİDİ
    # ========================================================

    if sell_confirmation:

        # Uzun vade hâlâ güçlü ise kontrollü azalt
        if long >= 60 and fundamental >= 50 and financial >= 50:

            return (
                "🟠 KADEMELİ AZALT",
                -20.0,
                "Satış teyidi oluştu ancak uzun vadeli yapı tamamen bozulmuş değil. "
                "Kontrollü pozisyon azaltımı öneriliyor."
            )

        # Yapı zayıflıyorsa daha güçlü azalt
        return (
            "🔴 AZALT",
            -25.0,
            "Satış teyidi oluştu ve uzun vadeli, temel veya finansal yapı zayıflıyor. "
            "Pozisyon azaltılmalı."
        )

    # ========================================================
    # 5. DÜŞÜŞ SİNYALİ — SATIŞ TEYİDİ YOK
    # ========================================================

    if decline_signal:

        if long >= 60:

            return (
                "🟡 TUT / TEYİT BEKLE",
                0.0,
                "Düşüş sinyali mevcut ancak satış teyidi oluşmadı. "
                "Uzun vadeli yapı hâlâ güçlü olduğu için pozisyon korunuyor."
            )

        if long >= 50:

            return (
                "🟡 TUT / İZLE",
                0.0,
                "Düşüş sinyali mevcut ancak satış teyidi oluşmadı. "
                "Pozisyon korunuyor ve teknik yapının netleşmesi bekleniyor."
            )

        return (
            "🟠 AZALTMA İZLE",
            0.0,
            "Düşüş sinyali mevcut ve uzun vadeli yapı zayıflıyor. "
            "Ancak satış teyidi henüz oluşmadı."
        )

    # ========================================================
    # 6. ALIM TEYİDİ
    # ========================================================

    if buy_confirmation:

        # Hedef ağırlığın belirgin şekilde altında
        if current_weight < target_weight - 3:

            if (
                short >= 80
                and mid >= 70
                and general >= 70
            ):

                return (
                    "🟢 GÜÇLÜ ARTIR",
                    STRONG_INCREASE_PCT,
                    "Alım teyidi güçlü ve mevcut pozisyon hedef ağırlığın "
                    "belirgin şekilde altında. Güçlü pozisyon artırımı öneriliyor."
                )

            return (
                "🟢 KADEMELİ ARTIR",
                MAX_INCREASE_PCT,
                "Alım teyidi oluştu ve mevcut pozisyon hedef ağırlığın altında. "
                "Kontrollü pozisyon artırımı öneriliyor."
            )

        # Hedefe yakın
        if current_weight <= target_weight + 2:

            return (
                "🟢 TUT / HEDEFTE",
                0.0,
                "Alım teyidi mevcut ancak mevcut portföy ağırlığı "
                "hedef seviyeye yakın. İlave işlem gerekmiyor."
            )

        # Hedefin üzerinde
        return (
            "🟡 TUT",
            0.0,
            "Alım teyidi mevcut ancak mevcut pozisyon hedef ağırlığın üzerinde. "
            "Yeni alım yapılmıyor."
        )

    # ========================================================
    # 7. HİÇBİR TEYİT YOK
    # ========================================================

    return (
        "🟡 TUT",
        0.0,
        "Alım veya satış teyidi oluşmadı. Mevcut pozisyon korunuyor."
    )
    # ========================================================
    # B KALİTE
    # ========================================================

    if quality.startswith("🟢 B"):

        if position_exists and decline_signal and not sell_confirmation:

            return (
                "🟡 TUT / TEYİT BEKLE",
                0.0,
                "Düşüş sinyali var ancak satış teyidi yok. B kalite yapı nedeniyle erken satış yapılmıyor."
            )

        if (
            current_weight < target_weight - 2
            and short >= 72
            and mid >= 65
            and buy_confirmation
        ):

            return (
                "🟢 KADEMELİ ARTIR",
                20.0,
                "Temel kalite olumlu, kısa ve orta vadeli momentum güçlü ve alım teyidi oluştu."
            )

        if short < 45 and not sell_confirmation:

            return (
                "🟡 TUT / TEYİT BEKLE",
                0.0,
                "Uzun vadeli yapı olumlu ancak kısa vadeli teknik görünüm zayıf ve satış teyidi oluşmadı."
            )

        if position_exists and current_weight > target_weight + 5:

            if sell_confirmation:
                return (
                    "🟠 KADEMELİ AZALT",
                    -15.0,
                    "Şirket olumlu olsa da portföy ağırlığı hedefin üzerinde ve satış teyidi oluşmuş."
                )

            return (
                "🟡 TUT / DENGELEMEYİ BEKLE",
                0.0,
                "Portföy ağırlığı yüksek ancak satış teyidi yok; gereksiz satış yapılmıyor."
            )

        return (
            "🟢 TUT",
            0.0,
            "Uzun vadeli yapı olumlu ve mevcut pozisyon dengeli."
        )

    # ========================================================
    # C KALİTE
    # ========================================================

    if quality.startswith("🟡 C"):

        if position_exists and decline_signal and not sell_confirmation:

            return (
                "🟡 BEKLE / SATIŞ TEYİDİ BEKLE",
                0.0,
                "Düşüş sinyali oluştu ancak gerçek satış teyidi için çoklu teknik bozulma henüz yeterli değil."
            )

        if (
            short >= 75
            and mid >= 65
            and current_weight < target_weight
            and buy_confirmation
        ):

            return (
                "🟢 KADEMELİ ARTIR",
                10.0,
                "Uzun vadeli kalite henüz güçlü değil ancak kısa ve orta vadeli teknik yapı olumlu ve alım teyidi mevcut."
            )

        if short < 45:

            if position_exists and current_weight > target_weight + 5 and sell_confirmation:

                return (
                    "🟠 AZALT",
                    -15.0,
                    "Uzun vadeli üstünlük sınırlı, kısa vadeli yapı zayıf ve satış teyidi oluşmuş."
                )

            return (
                "🟡 BEKLE",
                0.0,
                "Göstergeler yeterince güçlü değil. Yeni alım için teyit, mevcut pozisyon için ise satış teyidi bekleniyor."
            )

        if position_exists and current_weight > target_weight + 5:

            if sell_confirmation:
                return (
                    "🟠 KADEMELİ AZALT",
                    -15.0,
                    "Uzun vadeli kalite orta seviyede, portföy ağırlığı hedefin üzerinde ve satış teyidi oluşmuş."
                )

            return (
                "🟡 TUT / İZLE",
                0.0,
                "Portföy ağırlığı yüksek ancak satış teyidi yok."
            )

        return (
            "🟡 TUT / İZLE",
            0.0,
            "Göstergeler karışık ve net işlem üstünlüğü oluşmadı."
        )

    # ========================================================
    # D KALİTE
    # ========================================================

    if (
        long < 45
        and mid < 45
        and short < 45
    ):

        if position_exists and sell_confirmation:

            return (
                "🟠 KADEMELİ AZALT",
                -25.0,
                "Kısa, orta ve uzun vadeli yapı zayıf ve satış teyidi oluşmuş. Otomatik %100 çıkış yerine pozisyon kademeli azaltılıyor."
            )

        if position_exists:

            return (
                "🟡 TUT / TEYİT BEKLE",
                0.0,
                "Kısa, orta ve uzun vadeli yapı zayıf ancak satış teyidi henüz oluşmadı."
            )

        return (
            "🔴 ALMA / İZLE",
            0.0,
            "Kısa, orta ve uzun vadeli görünüm yeterince güçlü değil."
        )

    if short < 40 and not sell_confirmation:

        return (
            "🟡 BEKLE",
            0.0,
            "Kısa vadeli teknik yapı zayıf ancak satış teyidi oluşmadı; yeni işlem için teyit bekleniyor."
        )

    if position_exists and sell_confirmation:

        return (
            "🟠 KADEMELİ AZALT",
            -15.0,
            "Çoklu teknik satış teyidi oluştu. Pozisyon kademeli azaltılıyor."
        )

    return (
        "🟡 TUT / İZLE",
        0.0,
        "Göstergeler karışık ve net işlem üstünlüğü oluşmadı."
    )

# ============================================================
# 🎯 PORTFÖY AKSİYON ÖZETİ
# ============================================================

def portfolio_action_summary(
    decision,
    confirmations,
    quality,
    general_score,
    short_score,
    mid_score,
    long_score,
):

    buy_confirmation = confirmations.get(
        "buy_confirmation",
        False
    )

    sell_confirmation = confirmations.get(
        "sell_confirmation",
        False
    )

    decline_signal = confirmations.get(
        "decline_signal",
        False
    )

    # SATIŞ TEYİDİ
    if sell_confirmation:

        if (
            quality.startswith("🟢 A")
            and long_score >= 70
        ):
            return (
                "🟠 KADEMELİ AZALT",
                "Satış teyidi oluştu ancak şirketin "
                "uzun vadeli yapısı güçlü. "
                "Kontrollü azaltma değerlendirilmeli."
            )

        return (
            "🔴 SAT / ÇIKIŞI DEĞERLENDİR",
            "Satış teyidi oluştu. "
            "Pozisyon azaltılmalı veya çıkış değerlendirilmeli."
        )

    # DÜŞÜŞ VAR — SATIŞ TEYİDİ YOK
    if decline_signal:

        if (
            long_score >= 70
            and quality.startswith("🟢 A")
        ):
            return (
                "🟡 TUT / TEYİT BEKLE",
                "Düşüş sinyali var ancak satış teyidi yok. "
                "Uzun vadeli yapı güçlü olduğu için pozisyon korunuyor."
            )

        return (
            "🟡 DİKKAT / İZLE",
            "Düşüş sinyali oluştu. "
            "Satış teyidi beklenmeli."
        )

    # GÜÇLÜ POZİSYON
    if (
        general_score >= 75
        and short_score >= 65
        and mid_score >= 60
    ):
        return (
            "🟢 TUT / POZİSYONU KORU",
            "Genel skor ve kısa/orta vadeli yapı güçlü. "
            "Satış veya düşüş teyidi bulunmuyor."
        )

    # ALIM TEYİDİ
    if buy_confirmation:
        return (
            "🟢 KADEMELİ ARTIR",
            "Alım teyidi mevcut. "
            "Pozisyon kontrollü şekilde artırılabilir."
        )

    return (
        "⚪ TUT / İZLE",
        "Satış teyidi yok. "
        "Yeni işlem için ek teyit bekleniyor."
    )



# ============================================================
# GERÇEK İŞLEM HESAPLAMA
# ============================================================

def calculate_trade(
    decision,
    trade_pct,
    shares,
    price,
    current_weight,
    target_weight,
    portfolio_total_value
):

    shares = max(
        0,
        safe_float(
            shares,
            0
        )
    )

    price = max(
        0,
        safe_float(
            price,
            0
        )
    )

    current_weight = max(
        0,
        safe_float(
            current_weight,
            0
        )
    )

    target_weight = max(
        0,
        safe_float(
            target_weight,
            0
        )
    )

    # ========================================================
    # ÇIKIŞ
    # ========================================================

    if trade_pct <= -100:

        signed_lots = -int(
            round(shares)
        )

        actual_trade_pct = -100.0

    # ========================================================
    # SATIŞ
    # ========================================================

    elif trade_pct < 0:

        requested = abs(
            trade_pct
        )

        requested = min(
            requested,
            MAX_REDUCE_PCT
        )

        lots = int(
            round(
                shares *
                requested /
                100
            )
        )

        signed_lots = -min(
            lots,
            int(round(shares))
        )

        if shares > 0:

            actual_trade_pct = (
                signed_lots /
                shares
            ) * 100

        else:

            actual_trade_pct = 0

    # ========================================================
    # ALIŞ
    # ========================================================

    elif trade_pct > 0:

        requested = min(
            trade_pct,
            STRONG_INCREASE_PCT
        )

        lots = int(
            round(
                shares *
                requested /
                100
            )
        )

        # Pozisyon yoksa hedef ağırlığa göre başlangıç pozisyonu
        if shares <= 0 and price > 0:

            target_value = (
                portfolio_total_value
                *
                target_weight
                /
                100
            )

            lots = int(
                target_value /
                price
            )

        signed_lots = max(
            0,
            lots
        )

        if shares > 0:

            actual_trade_pct = (
                signed_lots /
                shares
            ) * 100

        else:

            actual_trade_pct = (
                100.0
                if signed_lots > 0
                else 0
            )

    else:

        signed_lots = 0

        actual_trade_pct = 0.0

    # ========================================================
    # SONRAKİ LOT
    # ========================================================

    next_lots = max(
        0,
        shares + signed_lots
    )

    # ========================================================
    # İŞLEM TUTARI
    # ========================================================

    transaction_value = (
        signed_lots *
        price
    )

    # ========================================================
    # SONRAKİ PORTFÖY AĞIRLIĞI
    # ========================================================

    if portfolio_total_value > 0:

        next_position_value = (
            next_lots *
            price
        )

        next_weight = (
            next_position_value /
            portfolio_total_value
        ) * 100

    else:

        next_weight = 0

    return {

        "signed_lots":
            int(signed_lots),
        "lot_reason":
            (
                f"Satış: %{abs(actual_trade_pct):.1f} oranında azaltma"
                if signed_lots < 0
                else
                f"Alış: %{actual_trade_pct:.1f} oranında artırma"
                if signed_lots > 0
                else
                "İşlem önerilmiyor"
            ),
                "actual_trade_pct":
                    round(
                        actual_trade_pct,
                        1
                    ),

        "transaction_value":
            transaction_value,

        "next_lots":
            next_lots,

        "next_weight":
            next_weight

    }


# ============================================================
# GÜVEN SKORU
# ============================================================

def confidence_engine(
    scores,
    fundamental_completeness,
    financial_completeness
):

    values = [
        scores["short"],
        scores["mid"],
        scores["long"]
    ]

    spread = (
        max(values)
        -
        min(values)
    )

    data_quality = (
        fundamental_completeness
        +
        financial_completeness
    ) / 2

    confidence = 100

    confidence -= min(
        spread * 0.55,
        30
    )

    confidence -= (
        100 -
        data_quality
    ) * 0.18

    confidence = clamp(
        confidence
    )

    if confidence >= 75:

        label = "🟢 Yüksek"

    elif confidence >= 55:

        label = "🟡 Orta"

    else:

        label = "🟠 Düşük"

    return (
        round(
            confidence,
            1
        ),
        label
    )


# ============================================================
# DETAYLI GEREKÇE
# ============================================================

def create_reason(
    scores,
    technical,
    fundamental,
    financial,
    sector,
    sector_name,
    market,
    current_weight,
    target_weight,
    decision_horizon,
    action_reason
):

    reasons = []

    # --------------------------------------------------------
    # KISA
    # --------------------------------------------------------

    if scores["short"] >= 70:

        reasons.append(
            "kısa vadeli momentum güçlü"
        )

    elif scores["short"] < 40:

        reasons.append(
            "kısa vadeli teknik görünüm zayıf"
        )

    else:

        reasons.append(
            "kısa vadeli görünüm nötr"
        )

    # --------------------------------------------------------
    # ORTA
    # --------------------------------------------------------

    if scores["mid"] >= 70:

        reasons.append(
            "orta vadeli trend güçlü"
        )

    elif scores["mid"] < 45:

        reasons.append(
            "orta vadeli trend zayıf"
        )

    # --------------------------------------------------------
    # UZUN
    # --------------------------------------------------------

    if scores["long"] >= 70:

        reasons.append(
            "uzun vadeli yapı güçlü"
        )

    elif scores["long"] < 45:

        reasons.append(
            "uzun vadeli yapı zayıf"
        )

    # --------------------------------------------------------
    # FUNDAMENTAL
    # --------------------------------------------------------

    if fundamental >= 70:

        reasons.append(
            "temel kalite güçlü"
        )

    elif fundamental < 45:

        reasons.append(
            "temel kalite zayıf"
        )

    # --------------------------------------------------------
    # FINANCIAL
    # --------------------------------------------------------

    if financial >= 70:

        reasons.append(
            "finansal yapı güçlü"
        )

    elif financial < 45:

        reasons.append(
            "finansal yapı zayıf"
        )

    # --------------------------------------------------------
    # EMA
    # --------------------------------------------------------

    if (
        technical["price_above_ema9"]
        and
        technical["ema9_above_ema20"]
    ):

        reasons.append(
            "EMA9/EMA20 trendi destekliyor"
        )

    elif not technical[
        "price_above_ema9"
    ]:

        reasons.append(
            "fiyat EMA9 altında"
        )

    # --------------------------------------------------------
    # 5 GÜNLÜK KESİŞİM
    # --------------------------------------------------------

    if technical["cross_up"]:

        reasons.append(
            "5 günlük ortalama yukarı kesildi"
        )

    elif technical["cross_down"]:

        reasons.append(
            "5 günlük ortalama aşağı kesildi"
        )

    # --------------------------------------------------------
    # SEKTÖR
    # --------------------------------------------------------

    if sector >= 70:

        reasons.append(
            f"{sector_name} sektörü destekleyici"
        )

    elif sector < 50:

        reasons.append(
            f"{sector_name} sektörü zayıf"
        )

    # --------------------------------------------------------
    # PİYASA
    # --------------------------------------------------------

    if market >= 65:

        reasons.append(
            "piyasa koşulları destekleyici"
        )

    elif market < 45:

        reasons.append(
            "piyasa koşulları temkinli"
        )

    # --------------------------------------------------------
    # AĞIRLIK
    # --------------------------------------------------------

    if current_weight > target_weight + 3:

        reasons.append(
            f"mevcut ağırlık %{current_weight:.1f} hedefin üzerinde"
        )

    elif current_weight < target_weight - 3:

        reasons.append(
            f"mevcut ağırlık %{current_weight:.1f} hedefin altında"
        )

    # En fazla 8 gerekçe
    reason_text = "; ".join(
        reasons[:8]
    )

    return (
        f"{action_reason} "
        f"Kararın ana vadesi: {decision_horizon}. "
        f"{reason_text}."
    )


# ============================================================
# BAŞLIK
# ============================================================

st.title(
    "📊 HİSSE BAZLI KARAR SİSTEMİ"
)

st.caption(
    "Kısa Vade + Orta Vade + Uzun Vade + "
    "Temel + Finansal + Teknik + Sektör + Piyasa + "
    "Portföy Ağırlığı"
)


# ============================================================
# EXCEL
# ============================================================

uploaded_file = st.file_uploader(
    "📁 Portföy Excel dosyasını yükleyin",
    type=[
        "xlsx",
        "xls"
    ]
)


if uploaded_file is None:

    st.info(
        "Karar sistemini çalıştırmak için "
        "portföy Excel dosyanızı yükleyin."
    )

    st.stop()


try:

    portfolio = pd.read_excel(
        uploaded_file
    )

except Exception as e:

    st.error(
        f"Excel okunamadı: {e}"
    )

    st.stop()


portfolio.columns = (
    portfolio.columns
    .astype(str)
    .str.strip()
)


# ============================================================
# GEREKLİ SÜTUNLAR
# ============================================================

required_columns = [

    "Hisse",
    "Kalan Adet",
    "Ortalama Maliyet",
    "Güncel Fiyat",
    "Maliyet Toplamı",
    "Piyasa Değeri",
    "Gerç. K/Z",
    "Getiri %",
    "Portföy %"

]


missing = [

    col

    for col in required_columns

    if col not in portfolio.columns

]


if missing:

    st.error(
        "Excel'de eksik sütunlar: "
        +
        ", ".join(missing)
    )

    st.stop()


# ============================================================
# SAYISAL ALANLAR
# ============================================================

numeric_columns = [

    "Kalan Adet",
    "Ortalama Maliyet",
    "Güncel Fiyat",
    "Maliyet Toplamı",
    "Piyasa Değeri",
    "Gerç. K/Z",
    "Getiri %",
    "Portföy %"

]


for column in numeric_columns:

    portfolio[column] = (
        portfolio[column]
        .apply(parse_number)
    )


portfolio["Portföy %"] = (
    portfolio["Portföy %"]
    .apply(
        normalize_weight
    )
)


# ============================================================
# PORTFÖY TOPLAMI
# ============================================================

portfolio_total_value = (
    portfolio[
        "Piyasa Değeri"
    ]
    .fillna(0)
    .sum()
)


if portfolio_total_value <= 0:

    st.error(
        "Portföy piyasa değeri hesaplanamadı."
    )

    st.stop()


# ============================================================
# ÜST ÖZET
# ============================================================

c1, c2, c3, c4 = st.columns(4)

c1.metric(
    "Portföy Değeri",
    fmt_money(
        portfolio_total_value
    )
)

c2.metric(
    "Hisse Sayısı",
    len(portfolio)
)

c3.metric(
    "En Büyük Pozisyon",
    f"%{portfolio['Portföy %'].max():.1f}"
)

c4.metric(
    "Sistem",
    "Aktif"
)


# ============================================================
# PİYASA
# ============================================================

with st.spinner(
    "🌍 Piyasa koşulları hesaplanıyor..."
):

    market_score, market_reasons = (
        market_engine()
    )


st.info(
    f"🌍 **BIST Piyasa Skoru: "
    f"{market_score:.1f}/100** — "
    +
    (
        " | ".join(
            market_reasons
        )
        if market_reasons
        else
        "Piyasa verisi nötr."
    )
)


# ============================================================
# ANALİZ
# ============================================================

results = []

progress = st.progress(
    0
)

total = len(
    portfolio
)


for index, (_, row) in enumerate(
    portfolio.iterrows()
):

    symbol = (
        str(
            row["Hisse"]
        )
        .upper()
        .strip()
    )

    shares = safe_float(
        row["Kalan Adet"],
        0
    )

    excel_price = safe_float(
        row["Güncel Fiyat"],
        0
    )

    current_weight = safe_float(
        row["Portföy %"],
        0
    )

    # --------------------------------------------------------
    # FİYAT
    # --------------------------------------------------------

    price_data = (
        download_price_data(
            symbol
        )
    )

    if price_data is None:

        results.append({

            "Hisse":
                symbol,

            "Fiyat":
                excel_price,

            "Günlük %":
                np.nan,

            "Mevcut %":
                current_weight,

            "Kısa Vade":
                np.nan,

            "Orta Vade":
                np.nan,

            "Uzun Vade":
                np.nan,

            "Genel Skor":
                np.nan,

            "Kalite":
                "⚠️ Veri Yok",

            "Hedef %":
                np.nan,

            "İşlem %":
                0,

            "İşlem Lot":
                "0 lot",

            "İşlem Tutarı":
                0,

            "Sonraki Lot":
                shares,

            "Sonraki %":
                current_weight,

            "Alım Teyidi":
                "⚪ Veri Yok",

            "Satış Teyidi":
                "⚪ Veri Yok",

            "Düşüş Sinyali":
                "⚪ Veri Yok",

            "Teyit Skoru":
                "-",

            "Karar":
                "⛔ KARAR YOK",

            "Karar Vadesi":
                "Veri yok",

            "Güven":
                "🔴 Veri Yok",

            "Güven Skoru":
                0,

            "RSI":
                np.nan,

            "Momentum 20G":
                np.nan,

            "Momentum 60G":
                np.nan,

            "Hacim Oranı":
                np.nan,

            "Fundamental":
                np.nan,

            "Financial":
                np.nan,

            "Sektör":
                np.nan,

            "Piyasa":
                market_score,

            "Gerekçe":
                "Teknik veri alınamadı. "
                "Otomatik işlem önerilmedi."

        })

        progress.progress(
            int(
                (
                    (index + 1)
                    /
                    total
                )
                * 100
            )
        )

        continue

    # --------------------------------------------------------
    # TEKNİK
    # --------------------------------------------------------

    technical_df = (
        build_indicators(
            price_data
        )
    )

    technical = (
        technical_engine(
            technical_df
        )
    )

    # --------------------------------------------------------
    # ALIM / SATIŞ TEYİDİ
    # --------------------------------------------------------

    confirmations = confirmation_engine(
        technical
    )

    price = technical[
        "price"
    ]

    daily_change = technical[
        "daily_change"
    ]

    # --------------------------------------------------------
    # ŞİRKET BİLGİSİ
    # --------------------------------------------------------

    info = get_info(
        symbol
    )

    # --------------------------------------------------------
    # FUNDAMENTAL
    # --------------------------------------------------------

    (
        fundamental,
        fundamental_reasons,
        fundamental_completeness

    ) = fundamental_engine(
        info
    )

    # --------------------------------------------------------
    # FINANCIAL
    # --------------------------------------------------------

    (
        financial,
        financial_reasons,
        financial_completeness

    ) = financial_engine(
        info
    )

    # --------------------------------------------------------
    # SEKTÖR
    # --------------------------------------------------------

    (
        sector,
        sector_name

    ) = sector_engine(
        symbol
    )

    # --------------------------------------------------------
    # VADE
    # --------------------------------------------------------

    scores = horizon_engine(

        technical,

        fundamental,

        financial,

        sector,

        market_score

    )

    # --------------------------------------------------------
    # KALİTE
    # --------------------------------------------------------

    (
        quality,
        quality_reason

    ) = quality_engine(

        scores["long"],

        fundamental,

        financial,

        fundamental_completeness,

        financial_completeness

    )

    # --------------------------------------------------------
    # HEDEF AĞIRLIK
    # --------------------------------------------------------

    target_weight = (
        target_weight_engine(

            scores,

            quality,

            fundamental,

            financial

        )
    )

    # --------------------------------------------------------
    # KARAR VADESİ
    # --------------------------------------------------------

    (
        decision_horizon,
        horizon_reason

    ) = determine_decision_horizon(

        scores,

        quality

    )

    # --------------------------------------------------------
    # KARAR
    # --------------------------------------------------------

    (
        decision,
        trade_pct,
        action_reason

    ) = action_engine(

        scores,

        fundamental,

        financial,

        current_weight,

        target_weight,

        quality,

        technical,

        confirmations,

        shares > 0

    )

    # --------------------------------------------------------
    # İŞLEM
    # --------------------------------------------------------

    trade = calculate_trade(

        decision,

        trade_pct,

        shares,

        price,

        current_weight,

        target_weight,

        portfolio_total_value

    )

    signed_lots = trade[
        "signed_lots"
    ]

    actual_trade_pct = trade[
        "actual_trade_pct"
    ]

    transaction_value = trade[
        "transaction_value"
    ]

    next_lots = trade[
        "next_lots"
    ]

    next_weight = trade[
        "next_weight"
    ]
    lot_reason = trade[
    "lot_reason"
    ]
    # --------------------------------------------------------
    # İŞLEM YAZISI
    # --------------------------------------------------------

    if signed_lots > 0:

        trade_lot_text = (
            f"+{signed_lots} lot"
        )

    elif signed_lots < 0:

        trade_lot_text = (
            f"{signed_lots} lot"
        )

    else:

        trade_lot_text = (
            "0 lot"
        )

    # --------------------------------------------------------
    # GÜVEN
    # --------------------------------------------------------

    (
        confidence_score,
        confidence_label

    ) = confidence_engine(

        scores,

        fundamental_completeness,

        financial_completeness

    )

    # --------------------------------------------------------
    # GEREKÇE
    # --------------------------------------------------------

    reason = create_reason(

        scores,

        technical,

        fundamental,

        financial,

        sector,

        sector_name,

        market_score,

        current_weight,

        target_weight,

        decision_horizon,

        action_reason

    )

    # --------------------------------------------------------
    # SONUÇ
    # --------------------------------------------------------

    results.append({

        "Hisse":
            symbol,

        "Fiyat":
            price,

        "Günlük %":
            daily_change,

        "Mevcut %":
            current_weight,

        "Kısa Vade":
            scores["short"],

        "Orta Vade":
            scores["mid"],

        "Uzun Vade":
            scores["long"],

        "Genel Skor":
            scores["general"],

        "Kalite":
            quality,

        "Hedef %":
            target_weight,

        "İşlem %":
            actual_trade_pct,

        "İşlem Lot":
            trade_lot_text,

        "Lot Kararı / Nedeni":
            trade["lot_reason"],

        "Lot Kararı / Nedeni":
            lot_reason,

        "İşlem Tutarı":
            transaction_value,

        "Sonraki Lot":
            next_lots,

        "Sonraki %":
            next_weight,

        "Alım Teyidi":
            confirmations["buy_text"],

        "Satış Teyidi":
            confirmations["sell_text"],

        "Düşüş Sinyali":
            confirmations["decline_text"],

        "Teyit Skoru":
            f"A{confirmations['buy_count']}/6 - S{confirmations['sell_count']}/6",

        "Karar":
            decision,

        "Karar Vadesi":
            decision_horizon,

        "Güven":
            confidence_label,

        "Güven Skoru":
            confidence_score,

        "RSI":
            technical["rsi"],

        "Momentum 20G":
            technical["mom20"],

        "Momentum 60G":
            technical["mom60"],

        "Hacim Oranı":
            technical["volume_ratio"],

        "Fundamental":
            fundamental,

        "Financial":
            financial,

        "Sektör":
            sector,

        "Piyasa":
            market_score,

        "Gerekçe":
            reason

    })

    progress.progress(
        int(
            (
                (index + 1)
                /
                total
            )
            * 100
        )
    )


progress.empty()


# ============================================================
# SONUÇ DATAFRAME
# ============================================================

result_df = pd.DataFrame(
    results
)
# ============================================================
# PORTFÖY İŞLEM ÖZETİ
# ============================================================

st.divider()

st.subheader(
    "💼 PORTFÖY İŞLEM ÖZETİ"
)

# ------------------------------------------------------------
# İŞLEM VERİLERİNİ GÜVENLİ HALE GETİR
# ------------------------------------------------------------

if not result_df.empty:

    result_df["İşlem %"] = pd.to_numeric(
        result_df["İşlem %"],
        errors="coerce"
    ).fillna(0)

    result_df["İşlem Tutarı"] = pd.to_numeric(
        result_df["İşlem Tutarı"],
        errors="coerce"
    ).fillna(0)

else:

    result_df["İşlem %"] = 0.0
    result_df["İşlem Tutarı"] = 0.0


# ------------------------------------------------------------
# ALIM / SATIM AYRIMI
# ------------------------------------------------------------

buy_df = result_df[
    result_df["İşlem %"] > 0
].copy()

sell_df = result_df[
    result_df["İşlem %"] < 0
].copy()

hold_df = result_df[
    result_df["İşlem %"] == 0
].copy()


# ------------------------------------------------------------
# ADET
# ------------------------------------------------------------

buy_count = len(
    buy_df
)

sell_count = len(
    sell_df
)

hold_count = len(
    hold_df
)


# ------------------------------------------------------------
# TOPLAM ALIM
# ------------------------------------------------------------

total_buy_value = (
    buy_df["İşlem Tutarı"]
    .clip(lower=0)
    .sum()
)


# ------------------------------------------------------------
# TOPLAM SATIŞ
# ------------------------------------------------------------

total_sell_value = (
    sell_df["İşlem Tutarı"]
    .abs()
    .sum()
)


# ------------------------------------------------------------
# NET NAKİT AKIŞI
#
# Satış = + nakit
# Alış  = - nakit
#
# Örneğin:
# 50.000 TL satış
# 30.000 TL alış
# = +20.000 TL net nakit
# ------------------------------------------------------------

net_cash_flow = (
    total_sell_value
    -
    total_buy_value
)


# ------------------------------------------------------------
# TOPLAM İŞLEM HACMİ
# ------------------------------------------------------------

total_transaction_volume = (
    total_buy_value
    +
    total_sell_value
)


# ------------------------------------------------------------
# PORTFÖYDE GERÇEK İŞLEM VAR MI?
# ------------------------------------------------------------

has_real_trade = (
    total_transaction_volume > 0
)


# ============================================================
# ÜST ÖZET
# ============================================================

c1, c2, c3, c4 = st.columns(4)


c1.metric(
    "🟢 Toplam Alım",
    fmt_money(
        total_buy_value
    )
)


c2.metric(
    "🔴 Toplam Satış",
    fmt_money(
        total_sell_value
    )
)


c3.metric(
    "💰 Net Nakit",
    fmt_money(
        net_cash_flow
    )
)


c4.metric(
    "🔄 İşlem Hacmi",
    fmt_money(
        total_transaction_volume
    )
)


# ============================================================
# HİSSE SAYISI ÖZETİ
# ============================================================

c1, c2, c3 = st.columns(3)


c1.metric(
    "🟢 Artırılacak",
    f"{buy_count} hisse"
)


c2.metric(
    "🔴 Azaltılacak",
    f"{sell_count} hisse"
)


c3.metric(
    "🟡 Tutulacak",
    f"{hold_count} hisse"
)


# ============================================================
# NET NAKİT DURUMU
# ============================================================

if not has_real_trade:

    st.success(
        "🟢 Portföyde şu anda uygulanabilir "
        "gerçek bir işlem bulunmuyor. "
        "Mevcut pozisyonlar korunuyor."
    )

elif net_cash_flow > 0:

    st.info(
        f"💰 İşlemler uygulandığında yaklaşık "
        f"{fmt_money(net_cash_flow)} "
        f"net nakit oluşması bekleniyor."
    )

elif net_cash_flow < 0:

    required_cash = abs(
        net_cash_flow
    )

    st.warning(
        f"💸 İşlemler uygulandığında yaklaşık "
        f"{fmt_money(required_cash)} "
        f"net nakit kullanılması gerekiyor."
    )

else:

    st.info(
        "⚖️ Alım ve satış işlemleri yaklaşık "
        "olarak birbirini dengeliyor."
    )


# ============================================================
# İŞLEM ÖZET TABLOSU
# ============================================================

if has_real_trade:

    summary_rows = []

    # --------------------------------------------------------
    # ALIMLAR
    # --------------------------------------------------------

    for _, row in buy_df.iterrows():

        summary_rows.append({

            "Hisse":
                row["Hisse"],

            "İşlem":
                "🟢 ALIM",

            "Mevcut %":
                row["Mevcut %"],

            "Hedef %":
                row["Hedef %"],

            "İşlem %":
                row["İşlem %"],

            "İşlem Lot":
                row["İşlem Lot"],

            "İşlem Tutarı":
                abs(
                    row["İşlem Tutarı"]
                ),

            "Sonraki %":
                row["Sonraki %"],

            "Karar":
                row["Karar"]

        })


    # --------------------------------------------------------
    # SATIŞLAR
    # --------------------------------------------------------

    for _, row in sell_df.iterrows():

        summary_rows.append({

            "Hisse":
                row["Hisse"],

            "İşlem":
                "🔴 SATIŞ",

            "Mevcut %":
                row["Mevcut %"],

            "Hedef %":
                row["Hedef %"],

            "İşlem %":
                row["İşlem %"],

            "İşlem Lot":
                row["İşlem Lot"],

            "İşlem Tutarı":
                abs(
                    row["İşlem Tutarı"]
                ),

            "Sonraki %":
                row["Sonraki %"],

            "Karar":
                row["Karar"]

        })


    summary_df = pd.DataFrame(
        summary_rows
    )


    # --------------------------------------------------------
    # ÖNCE SATIŞLAR, SONRA ALIMLAR
    # --------------------------------------------------------

    summary_df["_order"] = (
        summary_df["İşlem"]
        .map({
            "🔴 SATIŞ": 0,
            "🟢 ALIM": 1
        })
        .fillna(9)
    )

    summary_df = (
        summary_df
        .sort_values(
            [
                "_order",
                "İşlem Tutarı"
            ],
            ascending=[
                True,
                False
            ]
        )
        .drop(
            columns="_order"
        )
    )


    # --------------------------------------------------------
    # GÖSTER
    # --------------------------------------------------------

    st.dataframe(

        summary_df.style.format(

            {

                "Mevcut %":
                    "{:.2f}",

                "Hedef %":
                    "{:.1f}",

                "İşlem %":
                    "{:+.1f}",

                "İşlem Tutarı":
                    "{:,.2f}",

                "Sonraki %":
                    "{:.2f}"

            },

            na_rep="-"

        ),

        use_container_width=True,

        hide_index=True

    )

# ============================================================
# ANA TABLO
# ============================================================

st.divider()

st.subheader(
    "📊 HİSSE BAZLI KARAR TABLOSU"
)


main_columns = [

    "Hisse",
    "Fiyat",
    "Günlük %",
    "Mevcut %",
    "Kısa Vade",
    "Orta Vade",
    "Uzun Vade",
    "Genel Skor",
    "Kalite",
    "Hedef %",
    "İşlem %",
    "İşlem Lot",
    "Lot Kararı / Nedeni",
    "İşlem Tutarı",
    "Sonraki Lot",
    "Sonraki %",
    "Alım Teyidi",
    "Satış Teyidi",
    "Düşüş Sinyali",
    "Teyit Skoru",
    "Karar",
    "Karar Vadesi",
    "Güven"

]


display_df = result_df[
    main_columns
].copy()


format_dict = {

    "Fiyat":
        "{:.2f}",

    "Günlük %":
        "{:+.2f}",

    "Mevcut %":
        "{:.2f}",

    "Kısa Vade":
        "{:.1f}",

    "Orta Vade":
        "{:.1f}",

    "Uzun Vade":
        "{:.1f}",

    "Genel Skor":
        "{:.1f}",

    "Hedef %":
        "{:.1f}",

    "İşlem %":
        "{:+.1f}",

    "İşlem Tutarı":
        "{:,.2f}",

    "Sonraki Lot":
        "{:.0f}",

    "Sonraki %":
        "{:.2f}"

}


st.dataframe(

    display_df.style.format(
        format_dict,
        na_rep="-"
    ),

    use_container_width=True,

    hide_index=True,

    height=600

)


# ============================================================
# UYGULANABİLİR İŞLEMLER
# ============================================================

st.divider()

st.subheader(
    "💰 UYGULANABİLİR İŞLEMLER"
)


trade_df = result_df[
    result_df[
        "İşlem %"
    ].abs() > 0
].copy()


if trade_df.empty:

    st.success(
        "Şu anda sistem gerçek bir işlem gerektirmiyor."
    )

else:

    st.dataframe(

        trade_df[

            [

                "Hisse",
                "Fiyat",
                "Mevcut %",
                "Hedef %",
                "İşlem %",
                "İşlem Lot",
                "Lot Kararı / Nedeni",
                "İşlem Tutarı",
                "Sonraki Lot",
                "Sonraki %",
                "Alım Teyidi",
                "Satış Teyidi",
                "Düşüş Sinyali",
                "Teyit Skoru",
                "Karar",
                "Karar Vadesi",
                "Güven"

            ]

        ].style.format(

            {

                "Fiyat":
                    "{:.2f}",

                "Mevcut %":
                    "{:.2f}",

                "Hedef %":
                    "{:.1f}",

                "İşlem %":
                    "{:+.1f}",

                "İşlem Tutarı":
                    "{:,.2f}",

                "Sonraki Lot":
                    "{:.0f}",

                "Sonraki %":
                    "{:.2f}"

            },

            na_rep="-"

        ),

        use_container_width=True,

        hide_index=True

    )


# ============================================================
# KARAR GEREKÇELERİ
# ============================================================

st.divider()

st.subheader(
    "🔎 KARAR GEREKÇELERİ"
)


for _, row in result_df.iterrows():

    symbol = row[
        "Hisse"
    ]

    decision = row[
        "Karar"
    ]

    with st.expander(

        f"{symbol} — "
        f"{decision} — "
        f"{row['Karar Vadesi']}"

    ):

        c1, c2, c3, c4, c5 = st.columns(5)

        c1.metric(
            "Fiyat",
            f"{row['Fiyat']:.2f}"
        )

        c2.metric(
            "Kısa Vade",
            f"{row['Kısa Vade']:.1f}"
        )

        c3.metric(
            "Orta Vade",
            f"{row['Orta Vade']:.1f}"
        )

        c4.metric(
            "Uzun Vade",
            f"{row['Uzun Vade']:.1f}"
        )

        c5.metric(
            "Genel",
            f"{row['Genel Skor']:.1f}"
        )

        st.markdown(
            "### 🛡️ İŞLEM TEYİDİ"
        )

        tc1, tc2, tc3, tc4 = st.columns(4)

        tc1.metric(
            "Alım Teyidi",
            row["Alım Teyidi"]
        )

        tc2.metric(
            "Satış Teyidi",
            row["Satış Teyidi"]
        )

        tc3.metric(
            "Düşüş Sinyali",
            row["Düşüş Sinyali"]
        )

        tc4.metric(
            "Teyit",
            row["Teyit Skoru"]
        )

        st.markdown(
            f"### 🎯 {decision}"
        )

        st.write(
            f"**Karar vadesi:** "
            f"{row['Karar Vadesi']}"
        )

        st.write(
            f"**Gerekçe:** "
            f"{row['Gerekçe']}"
        )

        # ----------------------------------------------------
        # İŞLEM
        # ----------------------------------------------------

        st.markdown(
            "### 💰 İşlem Planı"
        )

        c1, c2, c3, c4 = st.columns(4)

        c1.metric(
            "Mevcut Ağırlık",
            f"%{row['Mevcut %']:.2f}"
        )

        c2.metric(
            "Hedef Ağırlık",
            f"%{row['Hedef %']:.1f}"
        )

        c3.metric(
            "Önerilen İşlem",
            f"%{row['İşlem %']:+.1f}"
        )

        c4.metric(
            "İşlem Lot",
            row["İşlem Lot"]
        )

        st.write(
            f"**İşlem fiyatı:** "
            f"{row['Fiyat']:.2f} TL"
        )

        st.write(
            f"**İşlem tutarı:** "
            f"{row['İşlem Tutarı']:,.2f} TL"
        )

        st.write(
            f"**İşlem sonrası lot:** "
            f"{row['Sonraki Lot']:.0f}"
        )

        st.write(
            f"**İşlem sonrası ağırlık:** "
            f"%{row['Sonraki %']:.2f}"
        )

        # ----------------------------------------------------
        # ALT KATMAN
        # ----------------------------------------------------

        st.markdown(
            "### 🔬 Analizin Alt Katmanları"
        )

        c1, c2, c3, c4, c5 = st.columns(5)

        c1.metric(
            "Fundamental",
            f"{row['Fundamental']:.1f}"
        )

        c2.metric(
            "Financial",
            f"{row['Financial']:.1f}"
        )

        c3.metric(
            "Sektör",
            f"{row['Sektör']:.1f}"
        )

        c4.metric(
            "Piyasa",
            f"{row['Piyasa']:.1f}"
        )

        c5.metric(
            "Güven",
            f"{row['Güven Skoru']:.1f}"
        )

        c1, c2, c3 = st.columns(3)

        c1.metric(
            "RSI",
            f"{row['RSI']:.1f}"
        )

        c2.metric(
            "20G Momentum",
            f"{row['Momentum 20G']:+.1f}%"
        )

        c3.metric(
            "60G Momentum",
            f"{row['Momentum 60G']:+.1f}%"
        )

        st.write(
            f"**Hacim oranı:** "
            f"{row['Hacim Oranı']:.2f}x"
        )


# ============================================================
# VADE TABLOLARI
# ============================================================

st.divider()

st.subheader(
    "📅 VADE BAZLI GÖRÜNÜM"
)


tab1, tab2, tab3 = st.tabs(

    [

        "⚡ Kısa Vade — 1 Hafta",

        "📅 Orta Vade — 1–3 Ay",

        "🏦 Uzun Vade — 6 Ay–3 Yıl"

    ]

)


# ============================================================
# KISA
# ============================================================

with tab1:

    st.dataframe(

        result_df[

            [

                "Hisse",
                "Fiyat",
                "Kısa Vade",
                "RSI",
                "Momentum 20G",
                "Hacim Oranı",
                "Alım Teyidi",
                "Satış Teyidi",
                "Düşüş Sinyali",
                "Karar",
                "Karar Vadesi"

            ]

        ].sort_values(

            "Kısa Vade",

            ascending=False

        ),

        use_container_width=True,

        hide_index=True

    )


# ============================================================
# ORTA
# ============================================================

with tab2:

    st.dataframe(

        result_df[

            [

                "Hisse",
                "Fiyat",
                "Orta Vade",
                "Momentum 60G",
                "Fundamental",
                "Financial",
                "Karar",
                "Karar Vadesi"

            ]

        ].sort_values(

            "Orta Vade",

            ascending=False

        ),

        use_container_width=True,

        hide_index=True

    )


# ============================================================
# UZUN
# ============================================================

with tab3:

    st.dataframe(

        result_df[

            [

                "Hisse",
                "Fiyat",
                "Uzun Vade",
                "Fundamental",
                "Financial",
                "Sektör",
                "Kalite",
                "Karar",
                "Karar Vadesi"

            ]

        ].sort_values(

            "Uzun Vade",

            ascending=False

        ),

        use_container_width=True,

        hide_index=True

    )


# ============================================================
# PORTFÖY YOĞUNLUK KONTROLÜ
# ============================================================

st.divider()

st.subheader(
    "⚠️ PORTFÖY YOĞUNLUK KONTROLÜ"
)


if not result_df.empty:

    max_index = (
        result_df[
            "Mevcut %"
        ].idxmax()
    )

    max_stock = (
        result_df.loc[
            max_index,
            "Hisse"
        ]
    )

    max_weight = (
        result_df.loc[
            max_index,
            "Mevcut %"
        ]
    )

    if max_weight >= 25:

        st.error(
            f"🔴 {max_stock} portföyün "
            f"%{max_weight:.1f}'ini oluşturuyor. "
            f"Tek hisse yoğunluğu çok yüksek."
        )

    elif max_weight >= 20:

        st.warning(
            f"⚠️ {max_stock} portföyün "
            f"%{max_weight:.1f}'ini oluşturuyor. "
            f"Tek hisse yoğunluğu yüksek."
        )

    elif max_weight >= 15:

        st.info(
            f"ℹ️ En yüksek pozisyon "
            f"{max_stock}: "
            f"%{max_weight:.1f}"
        )

    else:

        st.success(
            "✅ Tek hisse yoğunluğu kontrol altında."
        )


# ============================================================
# KARAR DAĞILIMI
# ============================================================

st.divider()

st.subheader(
    "📌 KARAR DAĞILIMI"
)


decision_counts = (
    result_df[
        "Karar"
    ]
    .value_counts()
)


st.dataframe(
    decision_counts
    .rename(
        "Adet"
    )
    .to_frame(),
    use_container_width=True
)


# ============================================================
# CSV
# ============================================================

st.divider()

csv_data = (
    result_df
    .to_csv(
        index=False
    )
    .encode(
        "utf-8-sig"
    )
)


st.download_button(

    "⬇️ Karar Raporunu CSV Olarak İndir",

    data=csv_data,

    file_name=(
        "BIST_AI_PRO_Hisse_Bazli_Karar.csv"
    ),

    mime="text/csv"

)


# ============================================================
# TEYİT MANTIĞI NOTU
# ============================================================

with st.expander(
    "🛡️ Alım / Satış teyidi nasıl çalışıyor?"
):

    st.markdown(
        """
### 🟢 Alım Teyidi

Alım teyidi 6 teknik koşul üzerinden hesaplanır. En az 4 koşul
sağlanmalı ve kısa/orta vade skorları da yeterli seviyede olmalıdır.

### 🔴 Düşüş Sinyali

Düşüş sinyali satış teyidinden daha erken çalışan bir uyarıdır.
En az 3 teknik bozulma veya teknik breakdown skoru 3 ve üzeri olduğunda
sistem uyarı verir. Bu durum **tek başına satış emri değildir**.

### 🔴 Satış Teyidi

6 teknik satış koşulundan en az 4'ünün aynı anda oluşması ve kısa/orta
vade yapısının da zayıflaması gerekir. Satış işlemleri esas olarak bu
teyide bağlanmıştır.

### ⛔ Portföyde olmayan hisse

Düşüş sinyali bulunan ve portföyde olmayan hisse için sistem yeni alım
yaptırmaz. Önce düşüş sinyalinin ortadan kalkması ve alım teyidinin\noluşması beklenir.

### 🟢 A kalite şirket

A kalite bir şirkette kısa vadeli düşüş tek başına satış gerekçesi
değildir. Satış teyidi oluşmadıkça sistem öncelikle **TUT / TEYİT BEKLE**
uygulamasını kullanır.

### %100 ÇIKIŞ

%100 çıkış için uzun vadeli, temel, finansal ve teknik yapının ciddi
biçimde bozulmasına ek olarak satış teyidi de zorunludur.
"""
    )


# ============================================================
# SİSTEM MANTIĞI
# ============================================================

with st.expander(
    "ℹ️ Karar sisteminin çalışma mantığı"
):

    st.markdown(
        """
## ⚡ Kısa Vade — 1 Hafta

Kullanılan ana kriterler:

- EMA9
- EMA20
- MA5
- RSI
- 5G momentum
- 20G momentum
- Hacim oranı
- 5 günlük yukarı/aşağı kesişim

**Amaç:** Alım/satım zamanlamasını belirlemek.

Kısa vade güçlü olduğunda bu tek başına
uzun vadeli bir şirketi satma gerekçesi değildir.

---

## 📅 Orta Vade — 1–3 Ay

Kullanılan kriterler:

- MA20
- MA50
- MA100
- EMA trendi
- 20G momentum
- 60G momentum
- Fundamental
- Financial
- Sektör
- Piyasa

**Amaç:** Pozisyonun korunması veya kademeli değiştirilmesi.

---

## 🏦 Uzun Vade — 6 Ay–3 Yıl

Kullanılan kriterler:

- Fundamental
- Financial
- MA50
- MA100
- MA200
- 60G momentum
- 120G momentum
- Sektör
- Piyasa

**Amaç:** Şirketin yatırım kalitesini belirlemek.

---

## 🛡️ Kaliteli Şirket Koruması

A kalite şirketlerde:

- kısa vadeli düşüş = otomatik satış değildir
- RSI zayıflığı = otomatik satış değildir
- tek bir teknik sinyal = çıkış değildir

Uzun vadeli yapı güçlü kaldığı sürece
sistem önce **TUT / TEYİT BEKLE** yaklaşımını kullanır.

---

## 🔴 %100 ÇIKIŞ

%100 çıkış yalnızca:

- uzun vadeli yapı ciddi bozulmuş
- temel yapı ciddi bozulmuş
- finansal yapı ciddi bozulmuş
- teknik yapı da ciddi bozulmuş

olduğunda devreye girer.

Yani yalnızca fiyat düştü diye
sistem bir hisseyi %100 satmaz.

---

## 💰 İşlem %

İşlem % artık hedef ağırlık ile doğrudan
karıştırılmamaktadır.

Örneğin:

600 EREGL

ve sistem:

**%10 azalt**

derse:

600 × %10 =

**60 lot satış**

önerilir.

---

## 📌 Önemli

**Hedef %**, hissenin portföyde bulunmasını
istediğimiz yaklaşık uzun vadeli ağırlıktır.

**İşlem %**, şu anda yapılması önerilen
işlemdir.

İkisi aynı şey değildir.

Bu ayrım özellikle kaliteli şirketlerde
gereksiz büyük satışları önlemek için
bilinçli olarak yapılmıştır.
"""
    )