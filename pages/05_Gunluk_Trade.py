import re
import urllib.request
from html.parser import HTMLParser

import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf


# =========================================================
# SAYFA
# =========================================================

st.set_page_config(
    page_title="Günlük Trade",
    page_icon="⚡",
    layout="wide"
)

st.title("⚡ Günlük Trade Merkezi")

st.caption(
    "BIST500 → Likidite + 9 EMA + Pullback + 15 Dakika Trend + VWAP "
    "+ RSI + Hacim + Destek/Direnç + Risk/Ödül"
)


# =========================================================
# FİLTRE AYARLARI
# =========================================================

MIN_TRADE_SCORE = 62.0
MIN_RR = 1.20
STRONG_RR = 1.80
STOP_ATR_MULTIPLIER = 1.50
SUPPORT_BUFFER = 0.997
MIN_SETUP_SCORE = 62.0
MIN_TIMING_SCORE = 55.0
STRONG_SETUP_SCORE = 75.0
STRONG_TIMING_SCORE = 75.0

# Fiyatın 9 EMA'dan bu seviyeden fazla uzaklaşması "KOVALAMA YOK"
# olarak değerlendirilir. Günlük trade için kontrollü gevşetme: %6.
CHASE_DISTANCE_MAX = 6.0


# =========================================================
# BIST 500 EVRENİ
# =========================================================

BIST500_URL = (
    "https://finans.mynet.com/borsa/endeks/"
    "xu500-bist-500/endekshisseleri/"
)


class BISTSymbolParser(HTMLParser):
    """Mynet sayfasındaki hisse bağlantılarından sembolleri çıkarır.

    lxml/pandas.read_html kullanılmaz. Böylece Streamlit Cloud gibi
    ortamlarda ayrıca lxml kurmak gerekmez.
    """

    def __init__(self):
        super().__init__()
        self.in_anchor = False
        self.anchor_text = []
        self.symbols = []
        self.in_table = False

    def handle_starttag(self, tag, attrs):
        if tag.lower() == "table":
            self.in_table = True
        if tag.lower() == "a" and self.in_table:
            self.in_anchor = True
            self.anchor_text = []

    def handle_data(self, data):
        if self.in_anchor:
            self.anchor_text.append(data)

    def handle_endtag(self, tag):
        if tag.lower() == "a" and self.in_anchor:
            text = " ".join(self.anchor_text)
            text = re.sub(r"\s+", " ", text).strip().upper()
            match = re.match(r"^([A-Z0-9]{4,6})\s+", text)
            if match:
                symbol = match.group(1)
                if symbol not in self.symbols:
                    self.symbols.append(symbol)
            self.in_anchor = False
            self.anchor_text = []
        if tag.lower() == "table":
            self.in_table = False


@st.cache_data(ttl=21600, show_spinner=False)
def get_bist500_symbols():
    """Güncel BIST500 listesini lxml olmadan alır ve doğrular."""

    request = urllib.request.Request(
        BIST500_URL,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 Chrome/150.0 Safari/537.36"
            ),
            "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            html = response.read().decode("utf-8", errors="ignore")

        parser = BISTSymbolParser()
        parser.feed(html)

        symbols = []
        seen = set()
        for symbol in parser.symbols:
            symbol = symbol.strip().upper()
            if symbol not in seen:
                seen.add(symbol)
                symbols.append(symbol)

        # Güvenlik: eksik/bozuk listeyle asla tarama başlatma.
        if not (450 <= len(symbols) <= 550):
            raise RuntimeError(
                f"BIST500 listesi doğrulanamadı: {len(symbols)} sembol bulundu."
            )

        return symbols

    except Exception as e:
        raise RuntimeError(
            "Güncel BIST500 bileşen listesi alınamadı. "
            "Güvenli olmayan eski bir listeyle tarama yapılmadı. "
            f"Kaynak hatası: {e}"
        )


try:
    BIST500 = get_bist500_symbols()
    UNIVERSE_ERROR = None
except Exception as e:
    BIST500 = []
    UNIVERSE_ERROR = str(e)

DEFAULT_MIN_AVG_TRADE_VALUE = 20_000_000.0
DEFAULT_INTRADAY_LIMIT = 120

# =========================================================
# GÜVENLİ SAYI
# =========================================================

def safe_float(value, default=0.0):
    try:
        value = float(value)

        if np.isnan(value) or np.isinf(value):
            return default

        return value

    except Exception:
        return default


# =========================================================
# SEMBOL
# =========================================================

def normalize_symbol(symbol):

    symbol = str(symbol).strip().upper()

    if not symbol.endswith(".IS"):
        symbol += ".IS"

    return symbol


# =========================================================
# GÜNLÜK VERİ
# =========================================================

@st.cache_data(ttl=300)
def get_daily_data(symbol):

    try:

        symbol = normalize_symbol(symbol)

        df = yf.Ticker(symbol).history(
            period="1y",
            interval="1d",
            auto_adjust=True
        )

        if df is None or df.empty:
            return None

        required = [
            "Open",
            "High",
            "Low",
            "Close",
            "Volume"
        ]

        df = df.dropna(
            subset=required
        )

        if len(df) < 60:
            return None

        return df

    except Exception as e:

        print(
            f"[DAILY ERROR] {symbol}: {e}"
        )

        return None


# =========================================================
# 15 DK VERİ
# =========================================================

@st.cache_data(ttl=180)
def get_intraday_data(symbol):

    try:

        symbol = normalize_symbol(symbol)

        df = yf.Ticker(symbol).history(
            period="5d",
            interval="15m",
            auto_adjust=True
        )

        if df is None or df.empty:
            return None

        required = [
            "Open",
            "High",
            "Low",
            "Close",
            "Volume"
        ]

        df = df.dropna(
            subset=required
        )

        if len(df) < 30:
            return None

        return df

    except Exception as e:

        print(
            f"[INTRADAY ERROR] {symbol}: {e}"
        )

        return None


# =========================================================
# LİKİDİTE / GÜNLÜK ÖN FİLTRE
# =========================================================

def calculate_liquidity_metrics(df):
    traded_value = df["Close"] * df["Volume"]
    avg_trade_value_20 = safe_float(traded_value.tail(20).mean())
    avg_volume_20 = safe_float(df["Volume"].tail(20).mean())
    current_volume = safe_float(df["Volume"].iloc[-1])
    volume_ratio_daily = current_volume / avg_volume_20 if avg_volume_20 > 0 else 0
    return avg_trade_value_20, volume_ratio_daily


def calculate_daily_general_score(df):
    price = safe_float(df["Close"].iloc[-1])
    ema20 = safe_float(calculate_ema(df["Close"], 20).iloc[-1])
    ema50 = safe_float(calculate_ema(df["Close"], 50).iloc[-1])
    ema200 = safe_float(calculate_ema(df["Close"], 200).iloc[-1])

    score = 0
    if price > ema20: score += 25
    if price > ema50: score += 25
    if price > ema200: score += 25
    if ema20 > ema50: score += 15
    if ema50 > ema200: score += 10
    return min(score, 100)


def download_daily_batch(symbols, chunk_size=50):
    """BIST500 günlük verisini toplu indirir; 500 ayrı HTTP isteği yerine parçalara böler."""
    result = {}
    normalized = [normalize_symbol(x) for x in symbols]

    for start in range(0, len(normalized), chunk_size):
        chunk = normalized[start:start + chunk_size]
        try:
            data = yf.download(
                tickers=chunk,
                period="1y",
                interval="1d",
                auto_adjust=True,
                group_by="ticker",
                threads=True,
                progress=False,
            )

            if data is None or data.empty:
                continue

            # Çoklu ticker indirmede MultiIndex; tek ticker için normal kolon yapısı olabilir.
            if isinstance(data.columns, pd.MultiIndex):
                level0 = set(data.columns.get_level_values(0))
                level1 = set(data.columns.get_level_values(1))
                ticker_first = all(t in level0 for t in chunk if t in level0)

                for ticker in chunk:
                    try:
                        if ticker_first and ticker in level0:
                            df = data[ticker].copy()
                        elif ticker in level1:
                            df = data.xs(ticker, axis=1, level=1).copy()
                        else:
                            continue
                    except Exception:
                        continue

                    required = ["Open", "High", "Low", "Close", "Volume"]
                    if all(col in df.columns for col in required):
                        df = df.dropna(subset=required)
                        if len(df) >= 60:
                            result[ticker] = df
            else:
                # Güvenlik: chunk tek sembol olursa normal DataFrame.
                if len(chunk) == 1:
                    df = data.copy()
                    required = ["Open", "High", "Low", "Close", "Volume"]
                    if all(col in df.columns for col in required):
                        df = df.dropna(subset=required)
                        if len(df) >= 60:
                            result[chunk[0]] = df
        except Exception as e:
            print(f"[BATCH DAILY ERROR] {start + 1}-{start + len(chunk)}: {e}")

    return result


def download_intraday_batch(symbols, chunk_size=20):
    """Sadece günlük ön filtreden geçen adayların 15 dk verisini toplu indirir."""
    result = {}
    normalized = [normalize_symbol(x) for x in symbols]

    for start in range(0, len(normalized), chunk_size):
        chunk = normalized[start:start + chunk_size]
        try:
            data = yf.download(
                tickers=chunk,
                period="5d",
                interval="15m",
                auto_adjust=True,
                group_by="ticker",
                threads=True,
                progress=False,
            )

            if data is None or data.empty:
                continue

            if isinstance(data.columns, pd.MultiIndex):
                level0 = set(data.columns.get_level_values(0))
                level1 = set(data.columns.get_level_values(1))
                ticker_first = any(t in level0 for t in chunk)

                for ticker in chunk:
                    try:
                        if ticker_first and ticker in level0:
                            df = data[ticker].copy()
                        elif ticker in level1:
                            df = data.xs(ticker, axis=1, level=1).copy()
                        else:
                            continue
                    except Exception:
                        continue

                    required = ["Open", "High", "Low", "Close", "Volume"]
                    if all(col in df.columns for col in required):
                        df = df.dropna(subset=required)
                        if len(df) >= 30:
                            result[ticker] = df
            elif len(chunk) == 1:
                df = data.copy()
                required = ["Open", "High", "Low", "Close", "Volume"]
                if all(col in df.columns for col in required):
                    df = df.dropna(subset=required)
                    if len(df) >= 30:
                        result[chunk[0]] = df

        except Exception as e:
            print(f"[BATCH INTRADAY ERROR] {start + 1}-{start + len(chunk)}: {e}")

    return result


def analyze_daily_candidate(symbol, daily, min_avg_trade_value):
    """BIST500'ü ucuz/güvenli günlük aşamada daraltır."""
    try:
        if daily is None or daily.empty:
            return None

        price = safe_float(daily["Close"].iloc[-1])
        ema9 = safe_float(calculate_ema(daily["Close"], 9).iloc[-1])
        pullback = analyze_daily_pullback(daily)
        general_score = calculate_daily_general_score(daily)
        avg_trade_value, daily_volume_ratio = calculate_liquidity_metrics(daily)

        if avg_trade_value < min_avg_trade_value: return None
        if price <= ema9: return None
        if pullback["skor"] < 40: return None
        if general_score < 35: return None
        if daily_volume_ratio < 0.50: return None

        distance = calculate_ema_distance(price, ema9)
        pre_score = (
            pullback["skor"] * 0.45
            + general_score * 0.30
            + min(daily_volume_ratio * 20, 20)
            + max(0, 10 - abs(distance) * 2)
        )

        return {
            "symbol": symbol,
            "avg_trade_value": avg_trade_value,
            "daily_volume_ratio": daily_volume_ratio,
            "pre_score": round(pre_score, 2),
        }
    except Exception as e:
        print(f"[DAILY PREFILTER ERROR] {symbol}: {e}")
        return None


# =========================================================
# EMA
# =========================================================

def calculate_ema(series, period):

    return series.ewm(
        span=period,
        adjust=False
    ).mean()


# =========================================================
# RSI
# =========================================================

def calculate_rsi(df, period=14):

    delta = df["Close"].diff()

    gain = delta.clip(
        lower=0
    )

    loss = -delta.clip(
        upper=0
    )

    avg_gain = gain.ewm(
        alpha=1 / period,
        adjust=False
    ).mean()

    avg_loss = loss.ewm(
        alpha=1 / period,
        adjust=False
    ).mean()

    if avg_loss.iloc[-1] == 0:
        return 100.0

    rs = (
        avg_gain /
        avg_loss
    )

    rsi = 100 - (
        100 /
        (1 + rs)
    )

    return safe_float(
        rsi.iloc[-1],
        50
    )


# =========================================================
# ATR
# =========================================================

def calculate_atr(df, period=14):

    high_low = (
        df["High"] -
        df["Low"]
    )

    high_close = (
        df["High"] -
        df["Close"].shift()
    ).abs()

    low_close = (
        df["Low"] -
        df["Close"].shift()
    ).abs()

    tr = pd.concat(
        [
            high_low,
            high_close,
            low_close
        ],
        axis=1
    ).max(axis=1)

    atr = tr.rolling(
        period
    ).mean()

    return safe_float(
        atr.iloc[-1],
        0
    )


# =========================================================
# VWAP
# =========================================================

def calculate_vwap(df):

    if df is None or df.empty:
        return 0

    data = df.copy()

    data["Date"] = data.index.date

    typical_price = (
        data["High"] +
        data["Low"] +
        data["Close"]
    ) / 3

    data["TPV"] = (
        typical_price *
        data["Volume"]
    )

    data["CumTPV"] = (
        data.groupby("Date")["TPV"]
        .cumsum()
    )

    data["CumVolume"] = (
        data.groupby("Date")["Volume"]
        .cumsum()
    )

    data["VWAP"] = (
        data["CumTPV"] /
        data["CumVolume"]
    )

    return safe_float(
        data["VWAP"].iloc[-1],
        0
    )


# =========================================================
# EMA UZAKLIK
# =========================================================

def calculate_ema_distance(
    price,
    ema9
):

    if ema9 <= 0:
        return 0

    return (
        (price / ema9) - 1
    ) * 100


# =========================================================
# PULLBACK
# =========================================================

def analyze_daily_pullback(df):

    data = df.copy()

    data["EMA9"] = calculate_ema(
        data["Close"],
        9
    )

    last = data.iloc[-1]
    previous = data.iloc[-2]

    price = safe_float(
        last["Close"]
    )

    ema9 = safe_float(
        last["EMA9"]
    )

    distance = calculate_ema_distance(
        price,
        ema9
    )

    recent = data.tail(5)

    distances = (
        (
            recent["Close"] /
            recent["EMA9"]
        ) - 1
    ) * 100

    min_distance = safe_float(
        distances.min()
    )

    above_ema = price > ema9

    if abs(distance) <= 1:
        proximity_score = 40

    elif abs(distance) <= 2:
        proximity_score = 30

    elif abs(distance) <= 3:
        proximity_score = 20

    elif abs(distance) <= 5:
        proximity_score = 5

    else:
        proximity_score = 0

    pullback_detected = (
        min_distance <= 1.5
        and
        price >= ema9
    )

    bullish_reaction = (
        price >
        safe_float(
            previous["Close"]
        )
        and
        price >= ema9
    )

    score = proximity_score

    if above_ema:
        score += 20

    if pullback_detected:
        score += 25

    if bullish_reaction:
        score += 20

    score = min(
        score,
        100
    )

    if (
        pullback_detected
        and
        bullish_reaction
    ):

        durum = "🟢 PULLBACK + TEPKİ"

    elif (
        above_ema
        and
        abs(distance) <= 2
    ):

        durum = "🟢 EMA YAKINI"

    elif (
        above_ema
        and
        distance > 3
    ):

        durum = "🟡 KOVALAMA RİSKİ"

    elif price < ema9:

        durum = "🟠 EMA ALTI"

    else:

        durum = "🟡 BEKLE"

    return {
        "durum": durum,
        "skor": score,
        "distance": distance
    }


# =========================================================
# 15 DK ANALİZ
# =========================================================

def analyze_intraday(df):

    if df is None or len(df) < 30:

        return {
            "trend": "VERİ YETERSİZ",
            "score": 0,
            "price": 0,
            "ema9": 0,
            "ema20": 0,
            "vwap": 0,
            "rsi": 50,
            "volume_ratio": 0
        }

    data = df.copy()

    data["EMA9"] = calculate_ema(
        data["Close"],
        9
    )

    data["EMA20"] = calculate_ema(
        data["Close"],
        20
    )

    price = safe_float(
        data["Close"].iloc[-1]
    )

    ema9 = safe_float(
        data["EMA9"].iloc[-1]
    )

    ema20 = safe_float(
        data["EMA20"].iloc[-1]
    )

    vwap = calculate_vwap(
        data
    )

    rsi = calculate_rsi(
        data
    )

    current_volume = safe_float(
        data["Volume"].iloc[-1]
    )

    avg_volume = safe_float(
        data["Volume"].tail(20).mean()
    )

    if avg_volume > 0:

        volume_ratio = (
            current_volume /
            avg_volume
        )

    else:

        volume_ratio = 0

    score = 0

    if price > ema9:
        score += 25

    if ema9 > ema20:
        score += 25

    if vwap > 0 and price > vwap:
        score += 25

    if volume_ratio >= 1.5:
        score += 15

    elif volume_ratio >= 1:
        score += 10

    elif volume_ratio >= 0.7:
        score += 5

    if 50 <= rsi <= 70:
        score += 10

    elif 45 <= rsi < 50:
        score += 5

    score = min(
        score,
        100
    )

    if score >= 75:
        trend = "🟢 POZİTİF"

    elif score >= 55:
        trend = "🟡 NÖTR / POZİTİF"

    elif score >= 40:
        trend = "🟠 ZAYIF"

    else:
        trend = "🔴 NEGATİF"

    return {
        "trend": trend,
        "score": score,
        "price": price,
        "ema9": ema9,
        "ema20": ema20,
        "vwap": vwap,
        "rsi": rsi,
        "volume_ratio": volume_ratio
    }


# =========================================================
# DESTEK / DİRENÇ
# =========================================================

def calculate_levels(df):

    support = safe_float(
        df["Low"].tail(20).min()
    )

    resistance = safe_float(
        df["High"].tail(20).max()
    )

    return support, resistance


# =========================================================
# SKORLAR: SETUP + GİRİŞ ZAMANLAMASI
# =========================================================

def calculate_volume_score(volume_ratio):
    if volume_ratio >= 1.5:
        return 100.0
    if volume_ratio >= 1.0:
        return 70.0 + (volume_ratio - 1.0) * 60.0
    if volume_ratio >= 0.7:
        return 45.0 + (volume_ratio - 0.7) * 83.333
    return max(0.0, volume_ratio / 0.7 * 45.0)


def calculate_setup_score(
    general_score,
    pullback_score,
    intraday_score,
    volume_ratio
):
    """Hissenin teknik olarak ne kadar güçlü olduğunu ölçer."""
    volume_score = calculate_volume_score(volume_ratio)
    score = (
        general_score * 0.30
        + pullback_score * 0.30
        + intraday_score * 0.25
        + volume_score * 0.15
    )
    return round(min(max(score, 0), 100), 1)


def calculate_timing_score(
    price,
    ema9,
    vwap,
    rsi,
    intraday_score,
    volume_ratio
):
    """Şu anda giriş yapılmasının ne kadar uygun olduğunu ölçer."""
    distance = abs(calculate_ema_distance(price, ema9))

    if distance <= 1.0:
        ema_timing = 100.0
    elif distance <= 2.0:
        ema_timing = 90.0
    elif distance <= 3.0:
        ema_timing = 75.0
    elif distance <= 4.0:
        ema_timing = 65.0
    elif distance <= 6.0:
        ema_timing = 50.0
    else:
        ema_timing = 20.0

    vwap_score = 100.0 if (vwap > 0 and price > vwap) else 25.0

    if 50 <= rsi <= 68:
        rsi_score = 100.0
    elif 45 <= rsi < 50 or 68 < rsi <= 72:
        rsi_score = 75.0
    elif 40 <= rsi < 45 or 72 < rsi < 75:
        rsi_score = 45.0
    else:
        rsi_score = 15.0

    volume_timing = calculate_volume_score(volume_ratio)

    score = (
        ema_timing * 0.35
        + vwap_score * 0.25
        + rsi_score * 0.15
        + intraday_score * 0.15
        + volume_timing * 0.10
    )
    return round(min(max(score, 0), 100), 1)


def calculate_trade_score(setup_score, timing_score):
    """Tek bir nihai puan: teknik güç + giriş zamanlaması."""
    return round(
        min(max(setup_score * 0.60 + timing_score * 0.40, 0), 100),
        1
    )


# =========================================================
# KARAR
# =========================================================

def generate_trade_decision(
    setup_score,
    timing_score,
    trade_score,
    rr,
    price,
    ema9,
    vwap,
    rsi
):
    """
    Günlük trade için nihai karar.

    Öncelik sırası:
    1) Aşırı uzama / aşırı alım
    2) Teknik setup
    3) Giriş zamanlaması
    4) Risk/ödül
    5) EMA9 + VWAP teyidi
    """

    distance = calculate_ema_distance(price, ema9)

    # Fiyat 9 EMA'dan ciddi şekilde uzaklaştıysa yüksek skor bile
    # olsa pozisyon kovalanmaz.
    if distance > 4.0:
        return (
            "🟡 KOVALAMA YOK",
            "Setup güçlü olsa bile fiyat 9 EMA'dan fazla uzak; geri çekilme veya EMA9'a yaklaşım beklenmeli."
        )

    if rsi >= 75:
        return (
            "🟡 BEKLE",
            "RSI aşırı alım bölgesinde; giriş zamanlaması uygun değil."
        )

    # R/R 1.30'un altında hiçbir AL kararı verilmez.
    if rr < MIN_RR:
        return (
            "🔴 İŞLEM YOK",
            f"Risk/Ödül yetersiz (1:{rr:.2f}); minimum kabul edilebilir R/R 1:{MIN_RR:.2f}."
        )

    # Güçlü aday: bütün ana teyitler birlikte aranır.
    if (
        setup_score >= STRONG_SETUP_SCORE
        and timing_score >= STRONG_TIMING_SCORE
        and trade_score >= 75
        and rr >= STRONG_RR
        and price > ema9
        and vwap > 0
        and price > vwap
    ):
        return (
            "🟢 GÜÇLÜ AL ADAYI",
            "Setup güçlü, giriş zamanlaması uygun, fiyat EMA9/VWAP üzerinde ve R/R güçlü."
        )

    # Normal AL adayı: EMA9 ve VWAP üzerinde olma şartı korunur.
    if (
        setup_score >= MIN_SETUP_SCORE
        and timing_score >= MIN_TIMING_SCORE
        and trade_score >= MIN_TRADE_SCORE
        and rr >= MIN_RR
        and price > ema9
        and vwap > 0
        and price > vwap
    ):
        return (
            "🟢 AL ADAYI",
            "Setup, giriş zamanlaması, EMA9/VWAP teyidi ve R/R kabul edilebilir seviyede."
        )

    if setup_score >= 70 and timing_score < MIN_TIMING_SCORE:
        return (
            "🟡 İZLE / ZAMANLAMA BEKLE",
            "Hisse teknik olarak güçlü; ancak giriş zamanlaması henüz yeterli değil."
        )

    if trade_score >= 50:
        return (
            "🟡 İZLE",
            "Olumlu sinyaller var fakat işlem için yeterli avantaj oluşmadı."
        )

    return (
        "🔴 İŞLEM YOK",
        "Günlük trade için yeterli teknik avantaj bulunmuyor."
    )


# =========================================================
# STOP / HEDEF
# =========================================================

def calculate_trade_levels(
    price,
    support,
    resistance,
    atr
):
    """Günlük trade için daha gerçekçi stop/hedef ve R/R hesaplar.

    Stop: yakın yapısal destek ile ATR stopunun daha sıkı olanı.
    Hedef: önce 20G direnç; R/R yetersizse 40G direnç kullanılması için
    çağıran fonksiyonda alternatif direnç ayrıca hesaplanabilir.
    """
    if price <= 0:
        return {
            "stop": 0.0, "target": 0.0, "risk_pct": 0.0,
            "reward_pct": 0.0, "rr": 0.0
        }

    # 1.2 ATR stop: günlük trade'de 20 günlük dip kadar geniş risk
    # oluşmasını önlemek için kullanılır.
    atr_stop = price - (atr * 1.20) if atr > 0 else price * 0.97

    # Yapısal destek stopu. Destek fiyatın altındaysa %0.3 tampon bırakılır.
    structure_stop = support * 0.997 if 0 < support < price else 0

    if structure_stop > 0:
        # Stop'u aşırı geniş bırakmamak için ATR stopu ile destek stopu
        # arasındaki daha sıkı seviyeyi kullanıyoruz.
        stop = max(structure_stop, atr_stop)
    else:
        stop = atr_stop

    # Stop fiyatın üstüne çıkarsa güvenli fallback.
    if stop >= price:
        stop = price - (atr * 1.20 if atr > 0 else price * 0.03)

    if stop <= 0 or stop >= price:
        stop = price * 0.97

    risk = price - stop

    # İlk hedef 2R. Direnç daha yakınsa direnç hedef olarak kullanılır.
    target_2r = price + (risk * 2.0)
    target = target_2r

    if resistance > price:
        target = min(resistance, target_2r)

    risk_pct = (risk / price) * 100
    reward_pct = max(0.0, (target - price) / price * 100)
    rr = (target - price) / risk if risk > 0 else 0

    return {
        "stop": round(stop, 2),
        "target": round(target, 2),
        "risk_pct": round(risk_pct, 2),
        "reward_pct": round(reward_pct, 2),
        "rr": round(max(rr, 0), 2)
    }


# =========================================================
# NEDEN ELENDİ?
# =========================================================

def get_filter_reasons(row):

    reasons = []

    if row["Setup Skor"] < MIN_SETUP_SCORE:
        reasons.append(
            f"❌ Setup Skoru {MIN_SETUP_SCORE:.0f} altında ({row['Setup Skor']:.1f})"
        )

    if row["Giriş Zamanlama"] < MIN_TIMING_SCORE:
        reasons.append(
            f"🟠 Giriş zamanlaması zayıf ({row['Giriş Zamanlama']:.1f})"
        )

    if row["Trade Skor"] < MIN_TRADE_SCORE:
        reasons.append(
            f"❌ Trade Skoru {MIN_TRADE_SCORE:.0f} altında ({row['Trade Skor']:.1f})"
        )

    if row["EMA Uzaklık %"] > CHASE_DISTANCE_MAX:
        reasons.append(
            f"🟡 Fiyat 9 EMA'dan fazla uzak (%{row['EMA Uzaklık %']:.2f})"
        )

    if row["Fiyat"] < row["9 EMA"]:
        reasons.append("❌ Fiyat 9 EMA altında")

    if row["VWAP"] > 0 and row["Fiyat"] < row["VWAP"]:
        reasons.append("❌ Fiyat VWAP altında")

    if row["Hacim x"] < 0.70:
        reasons.append(f"🟠 Hacim zayıf ({row['Hacim x']:.2f}x)")

    if row["R/R"] < MIN_RR:
        reasons.append(f"🔴 Risk/Ödül düşük (1:{row['R/R']:.2f})")

    if not reasons:
        reasons.append("⚪ İşlem filtresine girmedi.")

    return " | ".join(reasons)


# =========================================================
# HİSSE ANALİZİ
# =========================================================

def analyze_stock(symbol, daily=None, intraday=None):

    try:
        if daily is None:
            daily = get_daily_data(symbol)

        if intraday is None:
            intraday = get_intraday_data(symbol)

        if daily is None or daily.empty:
            return None

        price = safe_float(daily["Close"].iloc[-1])
        ema9 = safe_float(calculate_ema(daily["Close"], 9).iloc[-1])
        ema20 = safe_float(calculate_ema(daily["Close"], 20).iloc[-1])
        ema50 = safe_float(calculate_ema(daily["Close"], 50).iloc[-1])
        ema200 = safe_float(calculate_ema(daily["Close"], 200).iloc[-1])
        rsi = calculate_rsi(daily)
        atr = calculate_atr(daily)
        support, resistance = calculate_levels(daily)

        pullback = analyze_daily_pullback(daily)
        intraday_data = analyze_intraday(intraday)

        vwap = safe_float(intraday_data["vwap"])
        volume_ratio = safe_float(intraday_data["volume_ratio"])
        pullback_score = safe_float(pullback["skor"])
        intraday_score = safe_float(intraday_data["score"])

        general_score = 0
        if price > ema20: general_score += 25
        if price > ema50: general_score += 25
        if price > ema200: general_score += 25
        if ema20 > ema50: general_score += 15
        if ema50 > ema200: general_score += 10
        general_score = min(general_score, 100)

        setup_score = calculate_setup_score(
            general_score, pullback_score, intraday_score, volume_ratio
        )

        timing_score = calculate_timing_score(
            price, ema9, vwap, rsi, intraday_score, volume_ratio
        )

        trade_score = calculate_trade_score(
            setup_score, timing_score
        )

        levels = calculate_trade_levels(
            price, support, resistance, atr
        )

        # 20 günlük direnç çok yakınsa işlemi gereksiz yere elememek için
        # 40 günlük ikinci direnç kontrol edilir. Bu, hedefi keyfi şekilde
        # yükseltmez; yalnızca daha uzak gerçek bir teknik direnç varsa kullanır.
        if levels["rr"] < MIN_RR:
            resistance_40 = safe_float(daily["High"].tail(40).max())
            if resistance_40 > resistance:
                alt_levels = calculate_trade_levels(
                    price, support, resistance_40, atr
                )
                if alt_levels["rr"] > levels["rr"]:
                    levels = alt_levels

        decision, reason = generate_trade_decision(
            setup_score,
            timing_score,
            trade_score,
            levels["rr"],
            price,
            ema9,
            vwap,
            rsi
        )

        return {
            "Hisse": symbol.replace(".IS", ""),
            "Fiyat": round(price, 2),
            "9 EMA": round(ema9, 2),
            "EMA Uzaklık %": round(calculate_ema_distance(price, ema9), 2),
            "Pullback": pullback["durum"],
            "Pullback Skor": round(pullback_score, 1),
            "15D Trend": intraday_data["trend"],
            "15D Skor": round(intraday_score, 1),
            "VWAP": round(vwap, 2),
            "RSI": round(rsi, 1),
            "Hacim x": round(volume_ratio, 2),
            "Destek": round(support, 2),
            "Direnç": round(resistance, 2),
            "ATR": round(atr, 2),
            "Genel Skor": round(general_score, 1),
            "Setup Skor": setup_score,
            "Giriş Zamanlama": timing_score,
            "Trade Skor": trade_score,
            "Karar": decision,
            "Stop": levels["stop"],
            "Hedef": levels["target"],
            "Risk %": levels["risk_pct"],
            "Getiri %": levels["reward_pct"],
            "R/R": levels["rr"],
            "Stop Kaynağı": levels.get("stop_source", ""),
            "Hedef Kaynağı": levels.get("target_source", ""),
            "Açıklama": reason
        }

    except Exception as e:
        print(f"[ANALYSIS ERROR] {symbol}: {e}")
        return None


# =========================================================
# SIDEBAR
# =========================================================

with st.sidebar:

    st.header("📊 BIST500 Tarama")

    if UNIVERSE_ERROR:
        st.error(UNIVERSE_ERROR)
        st.stop()

    st.write(f"**Hisse sayısı:** {len(BIST500)}")

    st.info(
        "Güncel BIST500 evreni taranır. Önce günlük teknik + likidite filtresi, "
        "sonra sınırlı sayıda aday için 15 dk teyidi uygulanır."
    )

    st.divider()

    st.header("💰 Trade Sermayesi")
    sermaye = st.number_input(
        "Günlük trade sermayesi",
        min_value=1000.0,
        max_value=1000000.0,
        value=15000.0,
        step=1000.0
    )

    st.divider()
    st.header("🎯 Aktif Filtreler")

    min_avg_trade_value = st.number_input(
        "Minimum 20G ort. işlem hacmi (TL)",
        min_value=1_000_000.0,
        max_value=500_000_000.0,
        value=DEFAULT_MIN_AVG_TRADE_VALUE,
        step=5_000_000.0
    )

    intraday_limit = st.slider(
        "15 dk teyidine girecek aday sayısı",
        min_value=40,
        max_value=200,
        value=DEFAULT_INTRADAY_LIMIT,
        step=10
    )

    st.metric("Minimum Setup Skoru", f"{MIN_SETUP_SCORE:.0f}")
    st.metric("Minimum Giriş Zamanlaması", f"{MIN_TIMING_SCORE:.0f}")
    st.metric("Minimum Trade Skoru", f"{MIN_TRADE_SCORE:.0f}")
    st.metric("Minimum Risk/Ödül", f"1:{MIN_RR:.1f}")
    st.metric("Maks. EMA Uzaklığı", f"%{CHASE_DISTANCE_MAX:.0f}")

    st.divider()
    analiz_butonu = st.button(
        "⚡ BIST500'Ü TARA",
        type="primary",
        use_container_width=True
    )

# =========================================================
# BAŞLANGIÇ
# =========================================================

if not analiz_butonu:
    st.info(
        "👈 BIST500 hisselerini taramak için "
        "**⚡ BIST500'Ü TARA** butonuna basın."
    )
    st.stop()

# =========================================================
# TARAMA - 2 AŞAMALI
# =========================================================

sonuclar = []
daily_candidates = []

progress = st.progress(0)
status = st.empty()
toplam = len(BIST500)

# AŞAMA 1: 500 hissenin günlük verisini toplu al, sonra ön filtrele.
status.write("📥 BIST500 günlük verileri toplu indiriliyor...")
daily_cache = download_daily_batch(BIST500, chunk_size=50)

for i, symbol in enumerate(BIST500):
    status.write(f"🔎 Günlük ön tarama: {symbol} ({i + 1}/{toplam})")
    candidate = analyze_daily_candidate(
        symbol,
        daily_cache.get(normalize_symbol(symbol)),
        min_avg_trade_value
    )
    if candidate is not None:
        daily_candidates.append(candidate)
    progress.progress((i + 1) / toplam)

progress.empty()

daily_candidates.sort(key=lambda x: x["pre_score"], reverse=True)
selected_candidates = daily_candidates[:intraday_limit]

# AŞAMA 2: Sadece güçlü günlük adaylarda 15 dk teyidi.
selected_symbols = [x["symbol"] for x in selected_candidates]

progress = st.progress(0)
status = st.empty()
status.write(
    f"⚡ {len(selected_candidates)} aday için 15 dk verileri toplu indiriliyor..."
)
intraday_cache = download_intraday_batch(selected_symbols, chunk_size=20)

for i, candidate in enumerate(selected_candidates):
    symbol = candidate["symbol"]
    status.write(
        f"⚡ 15 dk teyit: {symbol} ({i + 1}/{max(len(selected_candidates), 1)})"
    )

    result = analyze_stock(
        symbol,
        daily_cache.get(normalize_symbol(symbol)),
        intraday_cache.get(normalize_symbol(symbol))
    )

    if result is not None:
        result["Ort. 20G İşlem Hacmi TL"] = round(candidate["avg_trade_value"], 0)
        result["Günlük Hacim x"] = round(candidate["daily_volume_ratio"], 2)
        result["Ön Tarama Skoru"] = candidate["pre_score"]
        sonuclar.append(result)

    progress.progress((i + 1) / max(len(selected_candidates), 1))

progress.empty()
status.empty()

# =========================================================
# SONUÇ KONTROLÜ
# =========================================================

if not sonuclar:

    st.error(
        "BIST500 taramasında kullanılabilir aday bulunamadı. Likidite filtresini ve ön filtreleri kontrol edin."
    )

    st.stop()


all_df = pd.DataFrame(
    sonuclar
)


# =========================================================
# ELENEN HİSSELER
# =========================================================

gecenler = all_df[
    (all_df["Trade Skor"] >= MIN_TRADE_SCORE)
    & (all_df["Setup Skor"] >= MIN_SETUP_SCORE)
    & (all_df["Giriş Zamanlama"] >= MIN_TIMING_SCORE)
    & (all_df["R/R"] >= MIN_RR)
    & (
        all_df["Karar"].isin(
            ["🟢 GÜÇLÜ AL ADAYI", "🟢 AL ADAYI"]
        )
    )
].copy()


gecmeyenler = all_df[
    ~all_df["Hisse"].isin(
        gecenler["Hisse"]
    )
].copy()


gecenler = gecenler.sort_values(
    "Trade Skor",
    ascending=False
)

gecmeyenler = gecmeyenler.sort_values(
    "Trade Skor",
    ascending=False
)


# =========================================================
# ÖZET
# =========================================================

st.divider()

c1, c2, c3, c4 = st.columns(4)

with c1:
    st.metric("💰 Sermaye", f"{sermaye:,.0f} TL")
with c2:
    st.metric("📊 BIST500 Günlük Tarama", len(BIST500))
with c3:
    st.metric("⚡ 15D Teyit", len(selected_candidates))
with c4:
    best_score = gecenler["Trade Skor"].max() if not gecenler.empty else 0
    st.metric("🏆 En Yüksek Skor", f"{best_score:.1f}")

st.caption(
    f"Günlük ön filtreden {len(daily_candidates)} hisse geçti; "
    f"en güçlü {len(selected_candidates)} aday 15 dk teyidine alındı. "
    f"Minimum 20G ort. işlem hacmi: {min_avg_trade_value:,.0f} TL."
)

# =========================================================
# GEÇENLER
# =========================================================

st.divider()

st.subheader(
    "🟢 Filtreden Geçen Günlük Trade Adayları"
)

if gecenler.empty:

    st.warning(
        "BIST500 içinde mevcut filtrelerden geçen "
        "trade adayı bulunamadı."
    )

else:

    display_columns = [
        "Hisse",
        "Fiyat",
        "9 EMA",
        "EMA Uzaklık %",
        "Pullback",
        "15D Trend",
        "VWAP",
        "RSI",
        "Hacim x",
        "Ort. 20G İşlem Hacmi TL",
        "Setup Skor",
        "Giriş Zamanlama",
        "Trade Skor",
        "Karar",
        "Stop",
        "Hedef",
        "R/R",
        "Risk %"
    ]

    st.dataframe(
        gecenler[display_columns],
        use_container_width=True,
        hide_index=True
    )


# =========================================================
# ELENENLER
# =========================================================

st.divider()

st.subheader(
    "🔎 Filtreden Geçemeyen Hisseler"
)

st.caption(
    "Filtreler otomatik olarak gevşetilmez. "
    "Aşağıda her hissenin neden elendiği gösterilir."
)

if gecmeyenler.empty:

    st.success(
        "Filtre dışı kalan hisse yok."
    )

else:

    for _, row in gecmeyenler.iterrows():

        reasons = get_filter_reasons(
            row
        )

        st.markdown(
            f"""
### 🔴 {row['Hisse']} — Trade Skor: {row['Trade Skor']:.1f} — {row['Karar']}

{reasons}
"""
        )


# =========================================================
# EN İYİ SETUPLAR
# =========================================================

st.divider()

st.subheader(
    "🏆 Günün En Güçlü Günlük Trade Adayları"
)

if gecenler.empty:

    st.warning(
        "Güçlü trade adayı bulunamadı."
    )

else:

    for _, row in gecenler.head(3).iterrows():

        if row["Karar"] == "🟢 GÜÇLÜ AL ADAYI":

            st.success(
                f"""
### {row['Hisse']} — 🟢 GÜÇLÜ AL ADAYI

**Setup Skor:** {row['Setup Skor']:.1f}  
**Giriş Zamanlama:** {row['Giriş Zamanlama']:.1f}  
**Trade Skor:** {row['Trade Skor']:.1f}

Fiyat: **{row['Fiyat']:.2f} TL**

9 EMA: **{row['9 EMA']:.2f} TL**

EMA uzaklığı: **%{row['EMA Uzaklık %']:.2f}**

Pullback: **{row['Pullback']}**

15 dk trend: **{row['15D Trend']}**

VWAP: **{row['VWAP']:.2f} TL**

RSI: **{row['RSI']:.1f}**

Hacim: **{row['Hacim x']:.2f}x**

🛑 Stop: **{row['Stop']:.2f} TL**

🎯 Hedef: **{row['Hedef']:.2f} TL**

Risk: **%{row['Risk %']:.2f}**

Potansiyel: **%{row['Getiri %']:.2f}**

Risk/Ödül: **1:{row['R/R']:.2f}**
"""
            )

        else:

            st.info(
                f"""
### {row['Hisse']} — {row['Karar']}

**Setup Skor:** {row['Setup Skor']:.1f}  
**Giriş Zamanlama:** {row['Giriş Zamanlama']:.1f}  
**Trade Skor:** {row['Trade Skor']:.1f}

9 EMA uzaklığı: **%{row['EMA Uzaklık %']:.2f}**

RSI: **{row['RSI']:.1f}**

Risk/Ödül: **1:{row['R/R']:.2f}**

{row['Açıklama']}
"""
            )


# =========================================================
# SERMAYE DAĞILIMI
# =========================================================

st.divider()

st.subheader(
    "💰 Sermaye Dağılımı"
)

eligible = gecenler[
    gecenler["Karar"].isin(
        [
            "🟢 GÜÇLÜ AL ADAYI",
            "🟢 AL ADAYI"
        ]
    )
].copy()

eligible = eligible[
    eligible["R/R"] >= MIN_RR
].copy()


if eligible.empty:

    st.warning(
        "Sermaye dağıtılabilecek uygun trade adayı yok."
    )

else:

    eligible = eligible.head(3).copy()

    eligible["Ağırlık"] = (
        eligible["Trade Skor"] /
        eligible["Trade Skor"].sum()
    )

    eligible["Tahsis"] = (
        sermaye *
        eligible["Ağırlık"]
    )

    eligible["Tahsis"] = (
        eligible["Tahsis"] /
        100
    ).round() * 100

    fark = (
        sermaye -
        eligible["Tahsis"].sum()
    )

    if len(eligible) > 0:

        first_index = eligible.index[0]

        eligible.loc[
            first_index,
            "Tahsis"
        ] += fark

    allocation_columns = [
        "Hisse",
        "Setup Skor",
        "Giriş Zamanlama",
        "Trade Skor",
        "Karar",
        "Fiyat",
        "Tahsis",
        "Stop",
        "Hedef",
        "Risk %",
        "Getiri %",
        "R/R"
    ]

    st.dataframe(
        eligible[
            allocation_columns
        ],
        use_container_width=True,
        hide_index=True
    )

    st.success(
        f"💰 Toplam tahsis: "
        f"**{eligible['Tahsis'].sum():,.0f} TL**"
    )


# =========================================================
# DETAYLI ANALİZ
# =========================================================

st.divider()

st.subheader(
    "🔎 Detaylı Günlük Trade Analizi"
)

st.caption(
    "Setup Skoru = teknik güç; Giriş Zamanlama = şu an giriş uygunluğu; "
    "Trade Skoru = %60 Setup + %40 Zamanlama. "
    "KOVALAMA YOK hisseleri yüksek skorlu olsalar bile işlem adayına alınmaz."
)

detail_df = pd.concat(
    [
        gecenler,
        gecmeyenler
    ]
).sort_values(
    "Trade Skor",
    ascending=False
)


for _, row in detail_df.iterrows():

    with st.expander(
        f"{row['Hisse']} | "
        f"{row['Karar']} | "
        f"Setup: {row['Setup Skor']:.1f} | "
        f"Zamanlama: {row['Giriş Zamanlama']:.1f} | "
        f"Trade: {row['Trade Skor']:.1f}"
    ):

        c1, c2, c3, c4 = st.columns(4)

        with c1:
            st.metric("Setup Skoru", f"{row['Setup Skor']:.1f}")

        with c2:
            st.metric("Giriş Zamanlama", f"{row['Giriş Zamanlama']:.1f}")

        with c3:
            st.metric("Trade Skoru", f"{row['Trade Skor']:.1f}")

        with c4:
            st.metric("R/R", f"1:{row['R/R']:.2f}")

        c1, c2, c3, c4 = st.columns(4)

        with c1:

            st.metric(
                "Fiyat",
                f"{row['Fiyat']:.2f} TL"
            )

        with c2:

            st.metric(
                "9 EMA",
                f"{row['9 EMA']:.2f}"
            )

        with c3:

            st.metric(
                "EMA Uzaklığı",
                f"%{row['EMA Uzaklık %']:.2f}"
            )

        with c4:

            st.metric(
                "Trade Skor",
                f"{row['Trade Skor']:.1f}"
            )

        c1, c2, c3, c4 = st.columns(4)

        with c1:

            st.metric(
                "Pullback",
                f"{row['Pullback Skor']:.1f}"
            )

        with c2:

            st.metric(
                "15 dk",
                f"{row['15D Skor']:.1f}"
            )

        with c3:

            st.metric(
                "VWAP",
                f"{row['VWAP']:.2f}"
            )

        with c4:

            st.metric(
                "RSI",
                f"{row['RSI']:.1f}"
            )

        st.divider()

        c1, c2, c3, c4 = st.columns(4)

        with c1:

            st.metric(
                "Hacim",
                f"{row['Hacim x']:.2f}x"
            )

        with c2:

            st.metric(
                "Genel Skor",
                f"{row['Genel Skor']:.1f}"
            )

        with c3:

            st.metric(
                "Risk/Ödül",
                f"1:{row['R/R']:.2f}"
            )

        with c4:

            st.metric(
                "Risk",
                f"%{row['Risk %']:.2f}"
            )

        st.divider()

        st.write(
            f"**Pullback:** {row['Pullback']}"
        )

        st.write(
            f"**15 dk Trend:** {row['15D Trend']}"
        )

        st.write(
            f"**Destek:** {row['Destek']:.2f} TL"
        )

        st.write(
            f"**Direnç:** {row['Direnç']:.2f} TL"
        )

        st.write(
            f"**ATR:** {row['ATR']:.2f}"
        )

        st.write(
            f"**🛑 Stop:** {row['Stop']:.2f} TL"
        )

        st.write(
            f"**🎯 Hedef:** {row['Hedef']:.2f} TL"
        )

        st.write(
            f"**Potansiyel:** %{row['Getiri %']:.2f}"
        )

        if row["Hisse"] in set(
            gecmeyenler["Hisse"]
        ):

            st.warning(
                get_filter_reasons(row)
            )

        else:

            st.success(
                row["Açıklama"]
            )


# =========================================================
# SON UYARI
# =========================================================

st.divider()

st.caption(
    "⚠️ Bu sayfa teknik karar desteği üretir. "
    "İşlem öncesinde fiyat, hacim, VWAP ve 15 dk trend "
    "tekrar kontrol edilmelidir."
)