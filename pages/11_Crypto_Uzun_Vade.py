# ============================================================
# CRYPTO AI PRO
# 10_Crypto_Uzun_Vade.py
#
# UZUN VADE KRİPTO YATIRIM MERKEZİ
#
# VADE:
# 3 AY - 12 AY
#
# AMAÇ:
# ------------------------------------------------------------
# Güçlü uzun vadeli trendi olan,
# düzeltmelerde değerlendirilebilecek,
# risk/getiri oranı uygun coinleri bulmak.
#
# GÜNLÜK TRADE MANTIĞINDAN FARKI:
# ------------------------------------------------------------
# Günlük fiyat hareketleri ana kriter değildir.
#
# Odak:
#   - Uzun vadeli trend
#   - EMA 50 / 100 / 200
#   - Momentum
#   - RSI
#   - ATH mesafesi
#   - Düzeltme kalitesi
#   - Volatilite
#   - Risk / Ödül
#   - Kademeli giriş
#
# ============================================================

import streamlit as st
import pandas as pd
import numpy as np
import requests
import time
import importlib
from datetime import datetime

import crypto_engine


# ============================================================
# SAYFA AYARLARI
# ============================================================

st.set_page_config(
    page_title="Kripto Uzun Vade PRO",
    page_icon="🏆",
    layout="wide",
)


# ============================================================
# ENGINE
# ============================================================

crypto_engine = importlib.reload(
    crypto_engine
)


# ============================================================
# AYARLAR
# ============================================================

BINANCE_KLINE_URL = (
    "https://api.binance.com/api/v3/klines"
)

INTERVAL = "1d"

KLINE_LIMIT = 250

MIN_VOLUME = 100_000_000

MAX_COINS = 50


# ============================================================
# BAŞLIK
# ============================================================

st.title("🏆 Kripto Uzun Vade PRO")

st.caption(
    "CRYPTO AI PRO | 3–12 aylık yatırım perspektifi"
)

st.info(
    "Bu sayfa günlük trade aramaz. "
    "Uzun vadeli trendi güçlü, düzeltme sonrası "
    "kademeli yatırım yapılabilecek coinleri belirler."
)


# ============================================================
# YARDIMCI FONKSİYONLAR
# ============================================================

def safe_float(value, default=0.0):

    try:
        if value is None:
            return default

        return float(value)

    except Exception:
        return default


def clamp(value, low=0, high=100):

    return max(
        low,
        min(high, safe_float(value))
    )


def fmt_price(value):

    value = safe_float(value)

    if value >= 1000:
        return f"{value:,.2f}"

    if value >= 100:
        return f"{value:,.3f}"

    if value >= 1:
        return f"{value:,.4f}"

    if value >= 0.01:
        return f"{value:.5f}"

    return f"{value:.8f}"


def fmt_money(value):

    value = safe_float(value)

    if value >= 1_000_000_000:
        return f"₺{value / 1_000_000_000:.2f} Mr"

    if value >= 1_000_000:
        return f"₺{value / 1_000_000:.1f} Mn"

    if value >= 1_000:
        return f"₺{value / 1_000:.0f} Bin"

    return f"₺{value:,.0f}"


# ============================================================
# EMA
# ============================================================

def ema(series, period):

    return (
        pd.Series(series)
        .ewm(
            span=period,
            adjust=False
        )
        .mean()
    )


# ============================================================
# RSI
# ============================================================

def rsi(series, period=14):

    series = pd.Series(
        series
    ).astype(float)

    delta = series.diff()

    gain = delta.clip(
        lower=0
    )

    loss = -delta.clip(
        upper=0
    )

    avg_gain = gain.rolling(
        period
    ).mean()

    avg_loss = loss.rolling(
        period
    ).mean()

    rs = (
        avg_gain /
        avg_loss.replace(
            0,
            np.nan
        )
    )

    return (
        100 -
        (
            100 /
            (1 + rs)
        )
    )


# ============================================================
# ATR
# ============================================================

def atr(df, period=14):

    high = df["high"]

    low = df["low"]

    close = df["close"]

    previous = close.shift(1)

    tr = pd.concat(
        [
            high - low,
            (high - previous).abs(),
            (low - previous).abs()
        ],
        axis=1
    ).max(axis=1)

    return tr.rolling(
        period
    ).mean()


# ============================================================
# LONG TERM KLINE
# ============================================================

@st.cache_data(ttl=900)
def get_long_term_klines(symbol):

    try:

        response = requests.get(
            BINANCE_KLINE_URL,
            params={
                "symbol": symbol,
                "interval": INTERVAL,
                "limit": KLINE_LIMIT,
            },
            timeout=10
        )

        response.raise_for_status()

        data = response.json()

        if not data:
            return pd.DataFrame()

        rows = []

        for item in data:

            rows.append(
                {
                    "open": safe_float(item[1]),
                    "high": safe_float(item[2]),
                    "low": safe_float(item[3]),
                    "close": safe_float(item[4]),
                    "volume": safe_float(item[5]),
                }
            )

        df = pd.DataFrame(
            rows
        )

        if df.empty:
            return df

        df["ema50"] = ema(
            df["close"],
            50
        )

        df["ema100"] = ema(
            df["close"],
            100
        )

        df["ema200"] = ema(
            df["close"],
            200
        )

        df["rsi"] = rsi(
            df["close"],
            14
        )

        df["atr"] = atr(
            df
        )

        return df

    except Exception:

        return pd.DataFrame()


# ============================================================
# UZUN VADE ANALİZİ
# ============================================================

def analyze_long_term(row, klines):

    price = safe_float(
        row["price_try"]
    )

    change = safe_float(
        row["change_24h"]
    )

    volume = safe_float(
        row["volume_try"]
    )

    if klines.empty:

        return None

    last = klines.iloc[-1]

    ema50 = safe_float(
        last["ema50"],
        price
    )

    ema100 = safe_float(
        last["ema100"],
        price
    )

    ema200 = safe_float(
        last["ema200"],
        price
    )

    current_rsi = safe_float(
        last["rsi"],
        50
    )

    current_atr = safe_float(
        last["atr"],
        price * 0.05
    )

    # ========================================================
    # 1. TREND SKORU
    # ========================================================

    trend_score = 0

    if price > ema50:
        trend_score += 20

    if price > ema100:
        trend_score += 20

    if price > ema200:
        trend_score += 25

    if ema50 > ema100:
        trend_score += 15

    if ema100 > ema200:
        trend_score += 20

    trend_score = clamp(
        trend_score
    )

    # ========================================================
    # 2. RSI
    # ========================================================

    if 50 <= current_rsi <= 65:

        rsi_score = 95

    elif 65 < current_rsi <= 72:

        rsi_score = 85

    elif 45 <= current_rsi < 50:

        rsi_score = 70

    elif current_rsi > 72:

        rsi_score = 55

    elif current_rsi < 35:

        rsi_score = 40

    else:

        rsi_score = 60

    # ========================================================
    # 3. 200 EMA MESAFESİ
    # ========================================================

    if ema200 > 0:

        ema200_distance = (
            (price - ema200)
            / ema200
        ) * 100

    else:

        ema200_distance = 0

    # ========================================================
    # 4. ATH / 250 GÜNLÜK ZİRVE
    # ========================================================

    ath = safe_float(
        klines["high"].max(),
        price
    )

    if ath > 0:

        ath_distance = (
            (price - ath)
            / ath
        ) * 100

    else:

        ath_distance = 0

    ath_gap = abs(
        ath_distance
    )

    # ========================================================
    # 5. DÜZELTME KALİTESİ
    # ========================================================

    if ath_gap >= 50:

        correction_score = 70

    elif ath_gap >= 35:

        correction_score = 82

    elif ath_gap >= 20:

        correction_score = 90

    elif ath_gap >= 10:

        correction_score = 78

    else:

        correction_score = 55

    # ========================================================
    # 6. VOLATİLİTE
    # ========================================================

    if price > 0:

        volatility = (
            current_atr /
            price
        ) * 100

    else:

        volatility = 5

    if volatility <= 4:

        volatility_score = 90

    elif volatility <= 7:

        volatility_score = 80

    elif volatility <= 10:

        volatility_score = 65

    else:

        volatility_score = 45

    # ========================================================
    # 7. HACİM
    # ========================================================

    if volume >= 2_000_000_000:

        volume_score = 100

    elif volume >= 1_000_000_000:

        volume_score = 95

    elif volume >= 500_000_000:

        volume_score = 90

    elif volume >= 250_000_000:

        volume_score = 82

    elif volume >= 100_000_000:

        volume_score = 70

    else:

        volume_score = 50

    # ========================================================
    # 8. MOMENTUM
    # ========================================================

    if len(klines) >= 30:

        price_30d = safe_float(
            klines.iloc[-30]["close"],
            price
        )

        if price_30d > 0:

            momentum_30d = (
                (price - price_30d)
                / price_30d
            ) * 100

        else:

            momentum_30d = 0

    else:

        momentum_30d = 0

    if momentum_30d >= 30:

        momentum_score = 100

    elif momentum_30d >= 20:

        momentum_score = 90

    elif momentum_30d >= 10:

        momentum_score = 80

    elif momentum_30d >= 0:

        momentum_score = 65

    elif momentum_30d >= -10:

        momentum_score = 50

    else:

        momentum_score = 35

    # ========================================================
    # 9. UZUN VADE SKORU
    # ========================================================

    long_score = (

        trend_score * 0.35 +

        momentum_score * 0.15 +

        rsi_score * 0.10 +

        correction_score * 0.15 +

        volume_score * 0.10 +

        volatility_score * 0.05 +

        80 * 0.10
    )

    long_score = clamp(
        long_score
    )

    # ========================================================
    # 10. GİRİŞ SKORU
    # ========================================================

    entry_score = (

        correction_score * 0.40 +

        rsi_score * 0.20 +

        trend_score * 0.25 +

        volatility_score * 0.15
    )

    entry_score = clamp(
        entry_score
    )

    # ========================================================
    # DESTEK
    # ========================================================

    recent = klines.tail(
        60
    )

    support = safe_float(
        recent["low"].min(),
        price * 0.85
    )

    # EMA destekleri

    ema_support = min(
        ema50,
        ema100
    )

    # ========================================================
    # STOP
    # ========================================================

    structural_stop = support * 0.97

    atr_stop = (
        price -
        current_atr * 2
    )

    stop = min(
        structural_stop,
        atr_stop
    )

    # Aşırı uzak stop kontrolü

    if stop < price * 0.70:

        stop = price * 0.70

    if stop >= price:

        stop = price * 0.85

    risk = price - stop

    # ========================================================
    # HEDEFLER
    # ========================================================

    target1 = price + (
        risk * 2
    )

    target2 = price + (
        risk * 3
    )

    target3 = price + (
        risk * 5
    )

    # ========================================================
    # KADEMELİ GİRİŞ
    # ========================================================

    entry1 = price

    entry2 = min(
        ema50,
        price * 0.96
    )

    entry3 = min(
        ema100,
        price * 0.90
    )

    if entry2 >= price:

        entry2 = price * 0.96

    if entry3 >= entry2:

        entry3 = entry2 * 0.94

    # ========================================================
    # KARAR
    # ========================================================

    if (
        long_score >= 82
        and entry_score >= 75
        and trend_score >= 75
    ):

        decision = "🟢 UZUN VADE AL"

        reason = (
            "Uzun vadeli trend güçlü, "
            "teknik yapı olumlu ve "
            "kademeli giriş için uygun."
        )

    elif (
        long_score >= 75
        and trend_score >= 65
    ):

        decision = "🟢 KADEMELİ TOPLA"

        reason = (
            "Uzun vadeli yapı olumlu. "
            "Tek seferde giriş yerine "
            "kademeli alım daha uygun."
        )

    elif (
        long_score >= 68
        and trend_score >= 55
    ):

        decision = "🟡 İZLE / DÜZELTME BEKLE"

        reason = (
            "Uzun vadeli potansiyel var ancak "
            "daha avantajlı giriş beklenebilir."
        )

    elif trend_score >= 45:

        decision = "🟡 TEYİT BEKLE"

        reason = (
            "Uzun vadeli trend henüz yeterince "
            "güçlü değil."
        )

    else:

        decision = "🔴 UZUN VADE UYGUN DEĞİL"

        reason = (
            "Mevcut teknik yapı uzun vadeli "
            "pozisyon için yeterli değil."
        )

    return {

        "Coin": row["base_asset"],

        "Fiyat": price,

        "24s %": change,

        "Hacim": volume,

        "Uzun Vade": long_score,

        "Giriş Skoru": entry_score,

        "Trend": trend_score,

        "RSI": current_rsi,

        "30G Momentum": momentum_30d,

        "200 EMA Mesafe": ema200_distance,

        "ATH Mesafe": ath_distance,

        "Volatilite": volatility,

        "Destek": support,

        "EMA50": ema50,

        "EMA100": ema100,

        "EMA200": ema200,

        "Giriş 1": entry1,

        "Giriş 2": entry2,

        "Giriş 3": entry3,

        "Stop": stop,

        "Hedef 1": target1,

        "Hedef 2": target2,

        "Hedef 3": target3,

        "R/R": 2.0,

        "Karar": decision,

        "Açıklama": reason,
    }


# ============================================================
# PİYASA VERİSİ
# ============================================================

try:

    raw_data = (
        crypto_engine
        .get_all_try_universe()
    )

except Exception as e:

    st.error(
        "Kripto piyasa verisi alınamadı."
    )

    st.exception(e)

    st.stop()


# ============================================================
# DATAFRAME
# ============================================================

if isinstance(
    raw_data,
    pd.DataFrame
):

    market = raw_data.copy()

elif isinstance(
    raw_data,
    list
):

    market = pd.DataFrame(
        raw_data
    )

else:

    st.error(
        "Kripto piyasa verisi uygun formatta değil."
    )

    st.stop()


if market.empty:

    st.warning(
        "TRY kripto evreni boş."
    )

    st.stop()


# ============================================================
# GEREKLİ KOLONLAR
# ============================================================

required = [

    "symbol",
    "base_asset",
    "price_try",
    "change_24h",
    "volume_try"
]


missing = [

    col
    for col in required
    if col not in market.columns
]


if missing:

    st.error(
        "Eksik piyasa kolonları: "
        + ", ".join(missing)
    )

    st.stop()


# ============================================================
# SAYISAL DÖNÜŞÜM
# ============================================================

for col in [
    "price_try",
    "change_24h",
    "volume_try"
]:

    market[col] = pd.to_numeric(
        market[col],
        errors="coerce"
    )


market = market[
    market["price_try"] > 0
].copy()


market = market[
    market["volume_try"] >= MIN_VOLUME
].copy()


market = market.sort_values(
    "volume_try",
    ascending=False
).head(
    MAX_COINS
)


# ============================================================
# ANALİZ
# ============================================================

results = []

progress = st.progress(
    0,
    text="Uzun vadeli coinler analiz ediliyor..."
)

total = len(market)

for i, (_, row) in enumerate(
    market.iterrows()
):

    klines = get_long_term_klines(
        row["symbol"]
    )

    result = analyze_long_term(
        row,
        klines
    )

    if result is not None:

        results.append(
            result
        )

    progress.progress(
        (i + 1) / max(total, 1),
        text=(
            f"{row['base_asset']} "
            "analiz ediliyor..."
        )
    )

    time.sleep(
        0.02
    )


progress.empty()


df = pd.DataFrame(
    results
)


if df.empty:

    st.warning(
        "Uzun vadeli analiz yapılabilecek "
        "yeterli coin bulunamadı."
    )

    st.stop()


df = df.sort_values(
    "Uzun Vade",
    ascending=False
).reset_index(
    drop=True
)


# ============================================================
# ÜST ÖZET
# ============================================================

st.divider()

c1, c2, c3, c4 = st.columns(4)


with c1:

    st.metric(
        "Analiz Edilen",
        len(df)
    )


with c2:

    st.metric(
        "Uzun Vade AL",
        len(
            df[
                df["Karar"]
                == "🟢 UZUN VADE AL"
            ]
        )
    )


with c3:

    st.metric(
        "Kademeli Topla",
        len(
            df[
                df["Karar"]
                == "🟢 KADEMELİ TOPLA"
            ]
        )
    )


with c4:

    st.metric(
        "Ortalama Skor",
        f"{df['Uzun Vade'].mean():.1f}"
    )


# ============================================================
# EN İYİ UZUN VADE ADAYLARI
# ============================================================

st.divider()

st.subheader(
    "🏆 En Güçlü Uzun Vade Adayları"
)


top = df[
    df["Karar"].isin(
        [
            "🟢 UZUN VADE AL",
            "🟢 KADEMELİ TOPLA"
        ]
    )
].head(5)


if top.empty:

    st.info(
        "Şu anda uzun vadeli kriterleri "
        "yeterince güçlü karşılayan coin yok."
    )

else:

    for _, row in top.iterrows():

        with st.container(
            border=True
        ):

            c1, c2, c3, c4 = st.columns(4)

            with c1:

                st.markdown(
                    f"### 🏆 {row['Coin']}"
                )

                st.metric(
                    "Uzun Vade Skoru",
                    f"{row['Uzun Vade']:.1f}"
                )

                st.success(
                    row["Karar"]
                )

            with c2:

                st.metric(
                    "Trend",
                    f"{row['Trend']:.1f}"
                )

                st.metric(
                    "Giriş",
                    f"{row['Giriş Skoru']:.1f}"
                )

            with c3:

                st.metric(
                    "30G Momentum",
                    f"{row['30G Momentum']:+.1f}%"
                )

                st.metric(
                    "RSI",
                    f"{row['RSI']:.1f}"
                )

            with c4:

                st.metric(
                    "ATH Mesafe",
                    f"{row['ATH Mesafe']:.1f}%"
                )

                st.metric(
                    "200 EMA",
                    f"{row['200 EMA Mesafe']:+.1f}%"
                )

            st.write(
                f"**Fiyat:** "
                f"{fmt_price(row['Fiyat'])}"
            )

            st.write(
                f"**1. Giriş:** "
                f"{fmt_price(row['Giriş 1'])}"
                f"  |  "
                f"**2. Giriş:** "
                f"{fmt_price(row['Giriş 2'])}"
                f"  |  "
                f"**3. Giriş:** "
                f"{fmt_price(row['Giriş 3'])}"
            )

            st.write(
                f"**Stop:** "
                f"{fmt_price(row['Stop'])}"
                f"  |  "
                f"**Hedef 1:** "
                f"{fmt_price(row['Hedef 1'])}"
                f"  |  "
                f"**Hedef 2:** "
                f"{fmt_price(row['Hedef 2'])}"
                f"  |  "
                f"**Hedef 3:** "
                f"{fmt_price(row['Hedef 3'])}"
            )

            st.caption(
                row["Açıklama"]
            )


# ============================================================
# KADEMELİ ALIM
# ============================================================

st.divider()

st.subheader(
    "📥 Kademeli Alım Bölgeleri"
)

st.caption(
    "Uzun vadede tek fiyat yerine üç aşamalı "
    "pozisyon oluşturma mantığı kullanılır."
)


accumulation = df[
    df["Karar"].isin(
        [
            "🟢 UZUN VADE AL",
            "🟢 KADEMELİ TOPLA"
        ]
    )
].copy()


if not accumulation.empty:

    display = accumulation[
        [
            "Coin",
            "Fiyat",
            "Uzun Vade",
            "Giriş Skoru",
            "Giriş 1",
            "Giriş 2",
            "Giriş 3",
            "Stop",
            "Hedef 1",
            "Hedef 2",
            "Hedef 3",
            "Karar"
        ]
    ].copy()

    st.dataframe(
        display,
        use_container_width=True,
        hide_index=True
    )

else:

    st.info(
        "Şu anda kademeli alım için "
        "uygun coin bulunamadı."
    )


# ============================================================
# İZLEME LİSTESİ
# ============================================================

st.divider()

st.subheader(
    "👀 Uzun Vade İzleme Listesi"
)


watch = df[
    df["Karar"].isin(
        [
            "🟡 İZLE / DÜZELTME BEKLE",
            "🟡 TEYİT BEKLE"
        ]
    )
].copy()


if not watch.empty:

    st.dataframe(
        watch[
            [
                "Coin",
                "Fiyat",
                "Uzun Vade",
                "Trend",
                "Giriş Skoru",
                "30G Momentum",
                "RSI",
                "ATH Mesafe",
                "Karar"
            ]
        ],
        use_container_width=True,
        hide_index=True
    )

else:

    st.success(
        "İzleme listesine alınacak coin bulunamadı."
    )


# ============================================================
# TÜM COİNLER
# ============================================================

st.divider()

st.subheader(
    "📊 Tüm Uzun Vade Analizi"
)

st.dataframe(
    df[
        [
            "Coin",
            "Fiyat",
            "24s %",
            "Uzun Vade",
            "Giriş Skoru",
            "Trend",
            "RSI",
            "30G Momentum",
            "ATH Mesafe",
            "200 EMA Mesafe",
            "Volatilite",
            "Karar"
        ]
    ],
    use_container_width=True,
    hide_index=True
)


# ============================================================
# COİN DETAY
# ============================================================

st.divider()

st.subheader(
    "🔎 Uzun Vade Coin Analizi"
)


selected_coin = st.selectbox(
    "Coin seç",
    df["Coin"].tolist()
)


selected = df[
    df["Coin"]
    == selected_coin
].iloc[0]


if "🟢" in selected["Karar"]:

    st.success(
        selected["Karar"]
    )

elif "🟡" in selected["Karar"]:

    st.warning(
        selected["Karar"]
    )

else:

    st.error(
        selected["Karar"]
    )


c1, c2, c3, c4, c5 = st.columns(5)


with c1:

    st.metric(
        "Uzun Vade",
        f"{selected['Uzun Vade']:.1f}"
    )


with c2:

    st.metric(
        "Trend",
        f"{selected['Trend']:.1f}"
    )


with c3:

    st.metric(
        "Giriş",
        f"{selected['Giriş Skoru']:.1f}"
    )


with c4:

    st.metric(
        "30G Momentum",
        f"{selected['30G Momentum']:+.1f}%"
    )


with c5:

    st.metric(
        "RSI",
        f"{selected['RSI']:.1f}"
    )


st.markdown(
    "### 🎯 Uzun Vadeli İşlem Planı"
)


p1, p2, p3, p4 = st.columns(4)


with p1:

    st.metric(
        "Mevcut Fiyat",
        fmt_price(
            selected["Fiyat"]
        )
    )


with p2:

    st.metric(
        "Giriş 1",
        fmt_price(
            selected["Giriş 1"]
        )
    )


with p3:

    st.metric(
        "Giriş 2",
        fmt_price(
            selected["Giriş 2"]
        )
    )


with p4:

    st.metric(
        "Giriş 3",
        fmt_price(
            selected["Giriş 3"]
        )
    )


st.write(
    f"**Stop:** "
    f"{fmt_price(selected['Stop'])}"
)


st.write(
    f"**Hedef 1:** "
    f"{fmt_price(selected['Hedef 1'])}"
)


st.write(
    f"**Hedef 2:** "
    f"{fmt_price(selected['Hedef 2'])}"
)


st.write(
    f"**Hedef 3:** "
    f"{fmt_price(selected['Hedef 3'])}"
)


# ============================================================
# TEKNİK YAPI
# ============================================================

st.markdown(
    "### 📐 Uzun Vadeli Teknik Yapı"
)


t1, t2, t3, t4 = st.columns(4)


with t1:

    st.metric(
        "EMA 50",
        fmt_price(
            selected["EMA50"]
        )
    )


with t2:

    st.metric(
        "EMA 100",
        fmt_price(
            selected["EMA100"]
        )
    )


with t3:

    st.metric(
        "EMA 200",
        fmt_price(
            selected["EMA200"]
        )
    )


with t4:

    st.metric(
        "ATH Mesafesi",
        f"{selected['ATH Mesafe']:.1f}%"
    )


st.info(
    selected["Açıklama"]
)


# ============================================================
# SİSTEM MANTIĞI
# ============================================================

with st.expander(
    "🧠 Uzun Vade Karar Motoru Nasıl Çalışıyor?"
):

    st.markdown(
        """
### 1. Uzun Vade Skoru

Ana kriterler:

- EMA 50
- EMA 100
- EMA 200
- Uzun vadeli trend
- 30 günlük momentum
- RSI
- Hacim
- Volatilite
- ATH mesafesi

---

### 2. Giriş Skoru

Coin güçlü olsa bile doğrudan almak yerine:

**Şu anda fiyat avantajlı mı?**

sorusuna bakılır.

---

### 3. Kademeli Alım

Uzun vadede tek fiyattan bütün sermayeyi kullanmak yerine:

**Giriş 1 → %30**

**Giriş 2 → %30**

**Giriş 3 → %40**

gibi kademeli pozisyon oluşturulabilir.

---

### 4. Düzeltme

Bir coin ATH'den uzak olabilir.

Bu her zaman kötü değildir.

Eğer uzun vadeli trend korunuyorsa:

**düzeltme = daha iyi maliyet fırsatı**

olabilir.

---

### 5. Önemli Fark

Günlük Trade:

**"Bugün alınabilir mi?"**

Kısa Vade:

**"Önümüzdeki birkaç gün içinde fırsat var mı?"**

Orta Vade:

**"Önümüzdeki haftalar/aylarda trend devam eder mi?"**

Uzun Vade:

**"3–12 aylık perspektifte sermaye ayırmaya değer mi?"**

sorusunu cevaplar.
"""
    )


# ============================================================
# ALT UYARI
# ============================================================

st.divider()

st.caption(
    "⚠️ Bu sayfa yatırım kararını otomatik olarak vermez. "
    "Teknik karar desteği sağlar. Uzun vadeli kripto yatırımlarında "
    "yüksek volatilite ve sermaye kaybı riski bulunduğundan "
    "pozisyon büyüklüğü ve kademeli giriş ayrıca değerlendirilmelidir."
)