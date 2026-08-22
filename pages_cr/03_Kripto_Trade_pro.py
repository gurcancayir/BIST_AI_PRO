# ============================================================
# CRYPTO AI PRO
# 03_Kripto_Trade_Pro.py
#
# PROFESYONEL KRİPTO TRADE MOTORU
#
# ANA MANTIK:
# Güçlü coin = otomatik AL değildir.
#
# Sistem iki ayrı soruya cevap verir:
#
# 1) COIN GÜÇLÜ MÜ?
# 2) ŞU ANDA GİRİŞ YAPMAK MANTIKLI MI?
#
# Kararlar:
# 🟢 BREAKOUT AL
# 🟢 GERİ ÇEKİLMEDE AL
# 🟡 TEYİT BEKLE
# 🟠 İZLE
# 🔴 KOVALAMA
#
# Veri kaynağı:
# BtcTurk Public Ticker API
# ============================================================

import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime

# ============================================================
# SAYFA AYARLARI
# ============================================================

st.set_page_config(
    page_title="Crypto AI Pro - Trade Pro",
    page_icon="🚀",
    layout="wide",
)

# ============================================================
# AYARLAR
# ============================================================

API_URL = "https://api.btcturk.com/api/v2/ticker"

REQUEST_TIMEOUT = 15

# Çok küçük hareketleri filtrele
MIN_PRICE = 0

# Trade için minimum hacim
MIN_VOLUME_TRY = 50_000_000

# Günlük aşırı yükseliş eşikleri
CHASE_WARNING = 10.0
CHASE_HIGH = 15.0
CHASE_EXTREME = 20.0

# ============================================================
# CSS
# ============================================================

st.markdown(
    """
    <style>

    .trade-card {
        padding: 18px;
        border-radius: 14px;
        border: 1px solid rgba(128,128,128,.25);
        margin-bottom: 14px;
    }

    .big-price {
        font-size: 26px;
        font-weight: 700;
    }

    .score {
        font-size: 32px;
        font-weight: 800;
    }

    .small-label {
        font-size: 13px;
        opacity: .7;
    }

    .decision {
        font-size: 20px;
        font-weight: 800;
        margin-top: 8px;
    }

    </style>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# BAŞLIK
# ============================================================

st.title("🚀 Crypto AI PRO — Trade Merkezi")

st.caption(
    "Profesyonel giriş analizi • Momentum + Trend + Hacim + Giriş Kalitesi + Kovalama Filtresi"
)

# ============================================================
# API VERİSİ
# ============================================================


@st.cache_data(ttl=60)
def get_market_data():

    try:

        response = requests.get(
            API_URL,
            timeout=REQUEST_TIMEOUT,
            headers={
                "User-Agent": "Mozilla/5.0",
                "Accept": "application/json",
            },
        )

        response.raise_for_status()

        data = response.json()

        if not data.get("success"):
            return pd.DataFrame()

        rows = data.get("data", [])

        if not rows:
            return pd.DataFrame()

        df = pd.DataFrame(rows)

        return df

    except Exception as e:

        st.error(f"Kripto piyasa verisi alınamadı: {e}")

        return pd.DataFrame()


# ============================================================
# VERİYİ HAZIRLA
# ============================================================


def prepare_data(df):

    if df.empty:
        return df

    numeric_columns = [
        "last",
        "high",
        "low",
        "bid",
        "ask",
        "open",
        "volume",
        "daily",
        "dailyPercent",
        "average",
    ]

    for col in numeric_columns:

        if col in df.columns:
            df[col] = pd.to_numeric(
                df[col],
                errors="coerce",
            )

    # Sadece TRY
    if "pair" in df.columns:

        df = df[
            df["pair"].astype(str).str.endswith("TRY")
        ].copy()

    # Geçerli fiyat
    df = df[
        (df["last"] > MIN_PRICE)
        & (df["high"] > 0)
        & (df["low"] > 0)
    ].copy()

    # TRY hacim
    #
    # BtcTurk ticker volume alanı coin miktarıdır.
    # TRY hacmini yaklaşık hesaplıyoruz:
    #
    # volume_coin * last_price
    #
    df["volume_try"] = (
        df["volume"] * df["last"]
    )

    # Günlük hareket
    df["daily_pct"] = df["dailyPercent"]

    # Gün içi konum
    #
    # 0  = günün dibinde
    # 100 = günün tepesinde
    #
    range_value = df["high"] - df["low"]

    df["day_position"] = np.where(
        range_value > 0,
        ((df["last"] - df["low"]) / range_value) * 100,
        50,
    )

    # Gün içi hareket genişliği
    df["range_pct"] = np.where(
        df["low"] > 0,
        ((df["high"] - df["low"]) / df["low"]) * 100,
        0,
    )

    return df


# ============================================================
# PUANLAMA MOTORU
# ============================================================


def clamp(value, low=0, high=100):

    return max(low, min(high, float(value)))


# ------------------------------------------------------------
# MOMENTUM
# ------------------------------------------------------------


def momentum_score(row):

    daily = abs(float(row["daily_pct"]))

    if daily >= 20:
        return 100

    if daily >= 15:
        return 92

    if daily >= 10:
        return 85

    if daily >= 7:
        return 78

    if daily >= 5:
        return 70

    if daily >= 3:
        return 62

    if daily >= 1:
        return 52

    return 40


# ------------------------------------------------------------
# TREND
# ------------------------------------------------------------


def trend_score(row):

    daily = float(row["daily_pct"])
    pos = float(row["day_position"])

    score = 50

    if daily > 0:
        score += min(daily * 2.5, 25)

    if pos >= 80:
        score += 20

    elif pos >= 65:
        score += 15

    elif pos >= 50:
        score += 8

    elif pos < 30:
        score -= 10

    return clamp(score)


# ------------------------------------------------------------
# HACİM
# ------------------------------------------------------------


def volume_score(row):

    volume = float(row["volume_try"])

    if volume >= 2_000_000_000:
        return 100

    if volume >= 1_000_000_000:
        return 95

    if volume >= 500_000_000:
        return 88

    if volume >= 250_000_000:
        return 82

    if volume >= 100_000_000:
        return 75

    if volume >= 50_000_000:
        return 65

    if volume >= 20_000_000:
        return 50

    return 30


# ------------------------------------------------------------
# GÜÇ SKORU
# ------------------------------------------------------------


def calculate_strength(row):

    momentum = momentum_score(row)

    trend = trend_score(row)

    volume = volume_score(row)

    position = float(row["day_position"])

    daily = float(row["daily_pct"])

    strength = (
        momentum * 0.35
        + trend * 0.35
        + volume * 0.20
        + position * 0.10
    )

    # Pozitif hareket bonusu
    if daily > 5:
        strength += 3

    # Negatif hareket cezası
    if daily < 0:
        strength -= 8

    return clamp(strength)


# ============================================================
# KOVALAMA SKORU
# ============================================================


def calculate_chase_score(row):

    daily = float(row["daily_pct"])
    position = float(row["day_position"])
    range_pct = float(row["range_pct"])

    score = 0

    # Günlük yükseliş
    if daily >= CHASE_EXTREME:
        score += 60

    elif daily >= CHASE_HIGH:
        score += 45

    elif daily >= CHASE_WARNING:
        score += 30

    elif daily >= 7:
        score += 18

    elif daily >= 5:
        score += 10

    # Günün tepesine yakınlık
    if position >= 95:
        score += 30

    elif position >= 90:
        score += 25

    elif position >= 80:
        score += 15

    # Çok geniş günlük range
    if range_pct >= 20:
        score += 15

    elif range_pct >= 15:
        score += 10

    elif range_pct >= 10:
        score += 5

    return clamp(score)


# ============================================================
# GİRİŞ KALİTESİ
# ============================================================


def calculate_entry_quality(row):

    daily = float(row["daily_pct"])
    position = float(row["day_position"])
    chase = float(row["chase_score"])

    quality = 100

    # --------------------------------------------------------
    # Günlük yükseliş cezası
    # --------------------------------------------------------

    if daily >= 20:
        quality -= 45

    elif daily >= 15:
        quality -= 30

    elif daily >= 10:
        quality -= 20

    elif daily >= 7:
        quality -= 10

    elif daily >= 5:
        quality -= 5

    # --------------------------------------------------------
    # Günün tepesinden giriş cezası
    # --------------------------------------------------------

    if position >= 95:
        quality -= 25

    elif position >= 90:
        quality -= 18

    elif position >= 80:
        quality -= 10

    elif position <= 40:
        quality += 5

    # --------------------------------------------------------
    # Kovalama cezası
    # --------------------------------------------------------

    quality -= chase * 0.25

    return clamp(quality)


# ============================================================
# İDEAL GİRİŞ
# ============================================================


def calculate_entry_zone(row):

    price = float(row["last"])
    low = float(row["low"])
    high = float(row["high"])

    daily = float(row["daily_pct"])
    position = float(row["day_position"])

    # Günlük range
    day_range = high - low

    # --------------------------------------------------------
    # Çok yükselmişse daha derin geri çekilme bekle
    # --------------------------------------------------------

    if daily >= 20:

        entry_low = price * 0.94
        entry_high = price * 0.97

    elif daily >= 15:

        entry_low = price * 0.95
        entry_high = price * 0.975

    elif daily >= 10:

        entry_low = price * 0.96
        entry_high = price * 0.98

    elif daily >= 7:

        entry_low = price * 0.975
        entry_high = price * 0.99

    else:

        entry_low = price * 0.985
        entry_high = price * 1.005

    # --------------------------------------------------------
    # Gün içi pozisyonuna göre düzeltme
    # --------------------------------------------------------

    if position >= 90:

        entry_low = min(
            entry_low,
            price - day_range * 0.30,
        )

        entry_high = min(
            entry_high,
            price - day_range * 0.10,
        )

    # Mantıksal düzeltme
    if entry_low >= entry_high:

        entry_low = price * 0.97
        entry_high = price * 0.99

    return entry_low, entry_high


# ============================================================
# STOP
# ============================================================


def calculate_stop(row, entry_low):

    low = float(row["low"])
    price = float(row["last"])

    # Günlük low altına kontrollü buffer
    stop = low * 0.97

    # Aşırı uzak stop oluşmasını engelle
    max_stop = entry_low * 0.90

    stop = max(stop, max_stop)

    # Fiyatın altında olmalı
    stop = min(stop, price * 0.97)

    return stop


# ============================================================
# HEDEFLER
# ============================================================


def calculate_targets(entry, stop):

    risk = entry - stop

    if risk <= 0:

        return (
            entry * 1.05,
            entry * 1.08,
        )

    target1 = entry + risk * 2

    target2 = entry + risk * 3

    return target1, target2


# ============================================================
# KARAR MOTORU
# ============================================================


def determine_decision(row):

    strength = float(row["strength_score"])
    entry_quality = float(row["entry_quality"])
    chase = float(row["chase_score"])
    daily = float(row["daily_pct"])
    position = float(row["day_position"])

    # --------------------------------------------------------
    # KOVALAMA
    # --------------------------------------------------------

    if chase >= 75:

        return "🔴 KOVALAMA"

    # --------------------------------------------------------
    # GÜÇLÜ AMA GERİ ÇEKİLME
    # --------------------------------------------------------

    if (
        strength >= 75
        and entry_quality < 55
    ):

        return "🟢 GERİ ÇEKİLMEDE AL"

    # --------------------------------------------------------
    # BREAKOUT AL
    # --------------------------------------------------------

    if (
        strength >= 78
        and entry_quality >= 70
        and chase < 45
    ):

        return "🟢 BREAKOUT AL"

    # --------------------------------------------------------
    # TEYİT
    # --------------------------------------------------------

    if (
        strength >= 68
        and entry_quality >= 55
    ):

        return "🟡 TEYİT BEKLE"

    # --------------------------------------------------------
    # İZLE
    # --------------------------------------------------------

    if strength >= 55:

        return "🟠 İZLE"

    return "🔴 ZAYIF"


# ============================================================
# ANA ANALİZ
# ============================================================


def analyze_row(row):

    strength = calculate_strength(row)

    row["strength_score"] = strength

    row["chase_score"] = calculate_chase_score(row)

    row["entry_quality"] = calculate_entry_quality(row)

    entry_low, entry_high = calculate_entry_zone(row)

    row["entry_low"] = entry_low
    row["entry_high"] = entry_high

    row["stop"] = calculate_stop(
        row,
        entry_low,
    )

    target1, target2 = calculate_targets(
        (entry_low + entry_high) / 2,
        row["stop"],
    )

    row["target1"] = target1
    row["target2"] = target2

    entry_mid = (
        entry_low + entry_high
    ) / 2

    risk = entry_mid - row["stop"]

    reward = target1 - entry_mid

    if risk > 0:

        row["rr"] = reward / risk

    else:

        row["rr"] = 0

    row["decision"] = determine_decision(row)

    return row


# ============================================================
# VERİYİ AL
# ============================================================

raw_df = get_market_data()

df = prepare_data(raw_df)

if df.empty:

    st.error("⚠️ Kripto piyasa verisi alınamadı.")

    st.info(
        "BtcTurk API bağlantısını veya internet erişimini kontrol edin."
    )

    st.stop()


# ============================================================
# ANALİZ
# ============================================================

analysis_rows = []

for _, row in df.iterrows():

    try:

        analyzed = analyze_row(row.copy())

        analysis_rows.append(analyzed)

    except Exception:

        continue


df = pd.DataFrame(analysis_rows)

# ============================================================
# FİLTRE
# ============================================================

df = df[
    df["volume_try"] >= MIN_VOLUME_TRY
].copy()

# ============================================================
# SIRALAMA
# ============================================================

df = df.sort_values(
    [
        "strength_score",
        "entry_quality",
    ],
    ascending=False,
).reset_index(drop=True)


# ============================================================
# ÜST BİLGİ
# ============================================================

col1, col2, col3, col4 = st.columns(4)

with col1:

    st.metric(
        "Analiz Edilen Coin",
        len(df),
    )

with col2:

    trade_count = len(
        df[
            df["decision"].isin(
                [
                    "🟢 BREAKOUT AL",
                    "🟢 GERİ ÇEKİLMEDE AL",
                ]
            )
        ]
    )

    st.metric(
        "Trade Adayı",
        trade_count,
    )

with col3:

    chase_count = len(
        df[
            df["decision"] == "🔴 KOVALAMA"
        ]
    )

    st.metric(
        "Kovalama Riski",
        chase_count,
    )

with col4:

    now = datetime.now().strftime(
        "%d.%m.%Y %H:%M"
    )

    st.metric(
        "Son Güncelleme",
        now,
    )


# ============================================================
# PROFESYONEL TRADE TABLOSU
# ============================================================

st.subheader("🎯 Profesyonel Trade Sıralaması")

display_df = df.copy()

display_df["Coin"] = (
    display_df["numeratorSymbol"]
)

display_df["Fiyat"] = (
    display_df["last"]
)

display_df["Günlük"] = (
    display_df["daily_pct"]
)

display_df["Güç"] = (
    display_df["strength_score"]
)

display_df["Giriş Kalitesi"] = (
    display_df["entry_quality"]
)

display_df["Kovalama"] = (
    display_df["chase_score"]
)

display_df["Giriş"] = (
    display_df["entry_low"]
)

display_df["Giriş Üst"] = (
    display_df["entry_high"]
)

display_df["Stop"] = (
    display_df["stop"]
)

display_df["Hedef 1"] = (
    display_df["target1"]
)

display_df["Hedef 2"] = (
    display_df["target2"]
)

display_df["R/R"] = (
    display_df["rr"]
)

display_df["Karar"] = (
    display_df["decision"]
)

table = display_df[
    [
        "Coin",
        "Fiyat",
        "Günlük",
        "Güç",
        "Giriş Kalitesi",
        "Kovalama",
        "Giriş",
        "Giriş Üst",
        "Stop",
        "Hedef 1",
        "Hedef 2",
        "R/R",
        "Karar",
    ]
].copy()

st.dataframe(
    table,
    use_container_width=True,
    hide_index=True,
    column_config={

        "Fiyat": st.column_config.NumberColumn(
            "Fiyat",
            format="%.6f",
        ),

        "Günlük": st.column_config.NumberColumn(
            "Günlük",
            format="%.2f%%",
        ),

        "Güç": st.column_config.NumberColumn(
            "Güç",
            format="%.1f",
        ),

        "Giriş Kalitesi": st.column_config.NumberColumn(
            "Giriş Kalitesi",
            format="%.1f",
        ),

        "Kovalama": st.column_config.NumberColumn(
            "Kovalama",
            format="%.1f",
        ),

        "Giriş": st.column_config.NumberColumn(
            "Giriş",
            format="%.6f",
        ),

        "Giriş Üst": st.column_config.NumberColumn(
            "Giriş Üst",
            format="%.6f",
        ),

        "Stop": st.column_config.NumberColumn(
            "Stop",
            format="%.6f",
        ),

        "Hedef 1": st.column_config.NumberColumn(
            "Hedef 1",
            format="%.6f",
        ),

        "Hedef 2": st.column_config.NumberColumn(
            "Hedef 2",
            format="%.6f",
        ),

        "R/R": st.column_config.NumberColumn(
            "R/R",
            format="1 : %.2f",
        ),
    },
)


# ============================================================
# GİRİŞ KALİTESİ AÇIKLAMASI
# ============================================================

st.divider()

st.subheader("🧠 Giriş Kalitesi Neyi Söylüyor?")

st.markdown(
    """
### 🟢 80–100 → Çok iyi giriş bölgesi

Coin güçlü ve mevcut fiyat henüz aşırı uzamamış.

### 🟢 70–79 → İyi giriş

Trade yapılabilir ancak ideal giriş bölgesi tercih edilir.

### 🟡 55–69 → Teyit gerekli

Coin güçlü olabilir fakat mevcut fiyat avantajlı değil.

### 🟠 40–54 → Riskli

Geri çekilme beklemek daha mantıklı.

### 🔴 0–39 → Kovalama riski

Coin çok yükselmiş veya günün tepesine fazla yaklaşmış.
"""
)


# ============================================================
# TRADE ADAYLARI
# ============================================================

st.divider()

st.subheader("🟢 Gerçek Trade Adayları")

trade_df = df[
    df["decision"].isin(
        [
            "🟢 BREAKOUT AL",
            "🟢 GERİ ÇEKİLMEDE AL",
        ]
    )
].copy()

if trade_df.empty:

    st.info(
        "Şu anda profesyonel filtrelerden geçen net bir trade adayı yok."
    )

else:

    for _, row in trade_df.head(10).iterrows():

        coin = row["numeratorSymbol"]

        st.markdown(
            f"### {row['decision']} — {coin}"
        )

        c1, c2, c3, c4 = st.columns(4)

        with c1:

            st.metric(
                "Fiyat",
                f"{row['last']:.6f}",
            )

        with c2:

            st.metric(
                "Güç",
                f"{row['strength_score']:.1f}",
            )

        with c3:

            st.metric(
                "Giriş Kalitesi",
                f"{row['entry_quality']:.1f}",
            )

        with c4:

            st.metric(
                "Kovalama",
                f"{row['chase_score']:.1f}",
            )

        st.write(
            f"**Günlük:** {row['daily_pct']:+.2f}%"
        )

        st.write(
            f"**Giriş:** "
            f"{row['entry_low']:.6f} – "
            f"{row['entry_high']:.6f}"
        )

        st.write(
            f"**Stop:** {row['stop']:.6f}"
        )

        st.write(
            f"**Hedef 1:** {row['target1']:.6f}"
        )

        st.write(
            f"**Hedef 2:** {row['target2']:.6f}"
        )

        st.write(
            f"**Risk / Ödül:** "
            f"1 : {row['rr']:.2f}"
        )

        # ----------------------------------------------------
        # PROFESYONEL YORUM
        # ----------------------------------------------------

        daily = row["daily_pct"]
        quality = row["entry_quality"]
        chase = row["chase_score"]
        position = row["day_position"]

        if (
            daily >= 15
            or chase >= 60
        ):

            st.warning(
                "⚠️ Güçlü momentum var ancak fiyat uzamış. "
                "Mevcut fiyattan kovalamak yerine geri çekilme "
                "giriş bölgesi tercih edilmeli."
            )

        elif (
            quality >= 75
            and chase < 40
        ):

            st.success(
                "✅ Güçlü setup ve kabul edilebilir giriş kalitesi. "
                "Mevcut fiyat giriş açısından daha dengeli."
            )

        else:

            st.info(
                "ℹ️ Trade adayı ancak giriş için fiyat teyidi "
                "veya daha iyi bir geri çekilme tercih edilebilir."
            )

        st.divider()


# ============================================================
# KOVALAMA LİSTESİ
# ============================================================

st.subheader("🔴 Kovalama Riski Yüksek Coinler")

chase_df = df[
    df["decision"] == "🔴 KOVALAMA"
].copy()

if chase_df.empty:

    st.success(
        "Şu anda yüksek kovalama riski tespit edilmedi."
    )

else:

    chase_table = chase_df[
        [
            "numeratorSymbol",
            "last",
            "daily_pct",
            "strength_score",
            "entry_quality",
            "chase_score",
            "day_position",
        ]
    ].copy()

    chase_table.columns = [
        "Coin",
        "Fiyat",
        "Günlük",
        "Güç",
        "Giriş Kalitesi",
        "Kovalama",
        "Gün İçi Konum",
    ]

    st.dataframe(
        chase_table,
        use_container_width=True,
        hide_index=True,
    )


# ============================================================
# GÜÇLÜ AMA GERİ ÇEKİLME BEKLENMELİ
# ============================================================

st.subheader(
    "🟡 Güçlü Ama Geri Çekilme Beklenmeli"
)

pullback_df = df[
    df["decision"] == "🟢 GERİ ÇEKİLMEDE AL"
].copy()

if pullback_df.empty:

    st.info(
        "Şu anda bu kategoride coin bulunmuyor."
    )

else:

    pull_table = pullback_df[
        [
            "numeratorSymbol",
            "last",
            "daily_pct",
            "strength_score",
            "entry_quality",
            "entry_low",
            "entry_high",
            "stop",
            "target1",
            "target2",
        ]
    ].copy()

    pull_table.columns = [
        "Coin",
        "Fiyat",
        "Günlük",
        "Güç",
        "Giriş Kalitesi",
        "İdeal Giriş Alt",
        "İdeal Giriş Üst",
        "Stop",
        "Hedef 1",
        "Hedef 2",
    ]

    st.dataframe(
        pull_table,
        use_container_width=True,
        hide_index=True,
    )


# ============================================================
# HAM VERİ
# ============================================================

with st.expander("📊 Ham Piyasa Verisi"):

    raw_display = df[
        [
            "pair",
            "last",
            "open",
            "high",
            "low",
            "volume_try",
            "daily_pct",
            "day_position",
            "range_pct",
        ]
    ].copy()

    raw_display.columns = [
        "Pair",
        "Fiyat",
        "Açılış",
        "Yüksek",
        "Düşük",
        "TRY Hacim",
        "Günlük %",
        "Gün İçi Konum",
        "Range %",
    ]

    st.dataframe(
        raw_display,
        use_container_width=True,
        hide_index=True,
    )


# ============================================================
# SON NOT
# ============================================================

st.info(
    """
⚠️ Bu sistem finansal tavsiye değildir.

**Önemli ayrım:**

Güç Skoru yüksek olması yalnızca coin'in güçlü olduğunu gösterir.

**Giriş Kalitesi** ise mevcut fiyatın trade için ne kadar uygun
olduğunu ayrıca değerlendirir.

Bu nedenle +15% / +20% yükselmiş bir coin güçlü olsa bile
sistem otomatik olarak mevcut fiyattan AL demek yerine
**GERİ ÇEKİLMEDE AL** veya **KOVALAMA** kararı verebilir.
"""
)