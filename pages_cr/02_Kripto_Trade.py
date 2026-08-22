# ============================================================
# CRYPTO AI PRO
# 02_Kripto_Trade.py
#
# PROFESYONEL KRİPTO TRADE MOTORU
#
# AMAÇ:
#   Güçlü coin bulmak yetmez.
#   Güçlü + likit + momentumlu + uygun fiyatta olan coinleri
#   ayırmak gerekir.
#
# KARARLAR:
#   🟢 AL
#   🟢 GERİ ÇEKİLMEDE AL
#   🔵 KIRILIM BEKLE
#   🟡 TEYİT BEKLE
#   🟠 İZLE
#   🔴 KOVALAMA
#
# VERİ:
#   Binance TR 24 saatlik piyasa verisi
#
# NOT:
#   Bu sayfa emir göndermez.
#   Sadece analiz ve trade planı üretir.
# ============================================================

import math
import requests
import pandas as pd
import numpy as np
import streamlit as st


# ============================================================
# SAYFA AYARLARI
# ============================================================

st.set_page_config(
    page_title="Kripto Trade",
    page_icon="⚡",
    layout="wide",
)


# ============================================================
# AYARLAR
# ============================================================

API_BASES = [
    "https://api.binance.me",
    "https://www.binance.tr",
]

TIMEOUT = 8

MIN_VOLUME_TRY = 50_000_000

# Sert yükseliş sonrası kovalama bölgeleri
CHASE_WARNING = 7.0
CHASE_DANGER = 12.0
CHASE_EXTREME = 18.0

# Risk / ödül
MIN_RR = 2.0

# ============================================================
# RENK / FORMAT YARDIMCILARI
# ============================================================


def safe_float(value, default=0.0):
    try:
        if value is None:
            return default

        if isinstance(value, str):
            value = value.replace(",", "").replace("%", "").strip()

        return float(value)

    except Exception:
        return default


def clamp(value, low=0.0, high=100.0):
    return max(low, min(high, value))


def fmt_price(price):
    price = safe_float(price)

    if price >= 1000:
        return f"{price:,.2f}"

    if price >= 100:
        return f"{price:,.3f}"

    if price >= 1:
        return f"{price:,.4f}"

    if price >= 0.01:
        return f"{price:,.5f}"

    if price >= 0.0001:
        return f"{price:,.8f}"

    return f"{price:,.10f}"


def fmt_try(value):
    value = safe_float(value)

    if value >= 1_000_000_000:
        return f"₺{value / 1_000_000_000:.2f} Mr"

    if value >= 1_000_000:
        return f"₺{value / 1_000_000:.1f} Mn"

    if value >= 1_000:
        return f"₺{value / 1_000:.1f} B"

    return f"₺{value:,.0f}"


def pct(value):
    return f"{safe_float(value):+.2f}%"


# ============================================================
# API
# ============================================================


@st.cache_data(ttl=30, show_spinner=False)
def get_market_data():

    errors = []

    # --------------------------------------------------------
    # Önce Binance tarzı 24hr ticker endpointleri denenir.
    # --------------------------------------------------------

    endpoints = [
        ("https://api.binance.me/api/v3/ticker/24hr", "standard"),
        ("https://www.binance.tr/api/v3/ticker/24hr", "standard"),
        ("https://www.binance.tr/open/v1/market/ticker", "tr"),
    ]

    for url, endpoint_type in endpoints:

        try:

            response = requests.get(
                url,
                timeout=TIMEOUT,
                headers={
                    "User-Agent": "Mozilla/5.0"
                },
            )

            if response.status_code != 200:
                errors.append(
                    f"{url} -> HTTP {response.status_code}"
                )
                continue

            data = response.json()

            # ------------------------------------------------
            # Standart Binance formatı
            # ------------------------------------------------

            if endpoint_type == "standard":

                if isinstance(data, list):

                    rows = []

                    for item in data:

                        symbol = str(
                            item.get("symbol", "")
                        ).upper()

                        # Sadece TRY pariteleri
                        if not symbol.endswith("TRY"):
                            continue

                        rows.append(
                            {
                                "symbol": symbol,
                                "coin": symbol.replace(
                                    "TRY", ""
                                ),
                                "price": safe_float(
                                    item.get("lastPrice")
                                ),
                                "change": safe_float(
                                    item.get(
                                        "priceChangePercent"
                                    )
                                ),
                                "high": safe_float(
                                    item.get("highPrice")
                                ),
                                "low": safe_float(
                                    item.get("lowPrice")
                                ),
                                "volume": safe_float(
                                    item.get("quoteVolume")
                                ),
                            }
                        )

                    if rows:
                        return pd.DataFrame(rows)

            # ------------------------------------------------
            # Binance TR farklı wrapper formatları
            # ------------------------------------------------

            if endpoint_type == "tr":

                payload = data.get("data", data)

                if isinstance(payload, dict):
                    payload = (
                        payload.get("list")
                        or payload.get("data")
                        or []
                    )

                if isinstance(payload, list):

                    rows = []

                    for item in payload:

                        symbol = str(
                            item.get("symbol", "")
                        ).upper()

                        if not symbol.endswith("TRY"):
                            continue

                        rows.append(
                            {
                                "symbol": symbol,
                                "coin": symbol.replace(
                                    "TRY", ""
                                ),
                                "price": safe_float(
                                    item.get("lastPrice")
                                    or item.get("price")
                                    or item.get("close")
                                ),
                                "change": safe_float(
                                    item.get(
                                        "priceChangePercent"
                                    )
                                    or item.get("changePercent")
                                ),
                                "high": safe_float(
                                    item.get("highPrice")
                                    or item.get("high")
                                ),
                                "low": safe_float(
                                    item.get("lowPrice")
                                    or item.get("low")
                                ),
                                "volume": safe_float(
                                    item.get("quoteVolume")
                                    or item.get("volume")
                                ),
                            }
                        )

                    if rows:
                        return pd.DataFrame(rows)

        except Exception as exc:

            errors.append(
                f"{url} -> {str(exc)}"
            )

    return pd.DataFrame()


# ============================================================
# FALLBACK:
# Kullanıcının mevcut piyasa tablosu
#
# API çalışmazsa sayfanın tamamen boş kalmasını engeller.
# ============================================================


def fallback_market_data():

    data = [

        ["XRPTRY", "XRP", 72.02, 10.68,
         2_604_256_286, 80.68, 63.83],

        ["ENATRY", "ENA", 7.24, 9.59,
         1_953_492_781, 7.88, 6.25],

        ["TRUMPTRY", "TRUMP", 128.60, 54.75,
         1_666_001_455, 175.90, 81.30],

        ["ETHTRY", "ETH", 115448.00, 0.74,
         1_270_552_115, 121142.00, 112673.00],

        ["PEPETRY", "PEPE", 0.00019456, 17.25,
         1_259_808_574, 0.00021642, 0.00016338],

        ["HEMITRY", "HEMI", 0.4563, -12.67,
         1_134_544_610, 0.7625, 0.4244],

        ["ACETRY", "ACE", 11.24, -0.80,
         941_361_462, 11.90, 9.10],

        ["BBTRY", "BB", 0.4779, -7.06,
         867_870_553, 0.6683, 0.4425],

        ["BTCTRY", "BTC", 3_680_454, -1.30,
         850_715_005, 3_748_292, 3_640_001],

        ["GALATRY", "GALA", 0.0926, 3.69,
         762_562_863, 0.1300, 0.0842],

        ["COTITRY", "COTI", 0.5582, 15.09,
         521_386_337, 0.7000, 0.4763],

        ["MUBARAKTRY", "MUBARAK", 1.25, 20.40,
         376_060_038, 1.41, 0.965],
    ]

    return pd.DataFrame(
        data,
        columns=[
            "symbol",
            "coin",
            "price",
            "change",
            "volume",
            "high",
            "low",
        ],
    )


# ============================================================
# MARKET DATA
# ============================================================


df = get_market_data()

using_fallback = False

if df.empty:

    df = fallback_market_data()
    using_fallback = True


# ============================================================
# TEMİZLE
# ============================================================

numeric_cols = [
    "price",
    "change",
    "volume",
    "high",
    "low",
]

for col in numeric_cols:

    df[col] = pd.to_numeric(
        df[col],
        errors="coerce"
    )

df = df.dropna(
    subset=["price"]
)

df = df[
    df["price"] > 0
].copy()


# ============================================================
# MARKET ANALİZİ
# ============================================================


def analyze_coin(row):

    price = safe_float(row["price"])
    change = safe_float(row["change"])
    high = safe_float(row["high"])
    low = safe_float(row["low"])
    volume = safe_float(row["volume"])

    # --------------------------------------------------------
    # 1. 24S RANGE
    # --------------------------------------------------------

    if high > low > 0:

        range_pct = (
            (high - low) / low
        ) * 100

        position = (
            (price - low)
            / (high - low)
        ) * 100

    else:

        range_pct = 0
        position = 50

    position = clamp(position)

    # --------------------------------------------------------
    # 2. MOMENTUM SKORU
    # --------------------------------------------------------

    if change <= -10:
        momentum = 15

    elif change < 0:
        momentum = 35

    elif change < 3:
        momentum = 55

    elif change < 7:
        momentum = 70

    elif change < 12:
        momentum = 85

    elif change < 20:
        momentum = 78

    else:
        momentum = 65

    # --------------------------------------------------------
    # 3. RANGE POZİSYONU
    # --------------------------------------------------------

    # Fiyat 24s dibine yakınsa daha avantajlı
    # Zirveye yakınsa kovalamaya daha açık.

    if position < 25:
        location_score = 85

    elif position < 45:
        location_score = 92

    elif position < 65:
        location_score = 82

    elif position < 80:
        location_score = 68

    elif position < 90:
        location_score = 52

    else:
        location_score = 30

    # --------------------------------------------------------
    # 4. LİKİDİTE
    # --------------------------------------------------------

    if volume >= 2_000_000_000:
        liquidity_score = 100

    elif volume >= 1_000_000_000:
        liquidity_score = 92

    elif volume >= 500_000_000:
        liquidity_score = 82

    elif volume >= 100_000_000:
        liquidity_score = 70

    elif volume >= 50_000_000:
        liquidity_score = 58

    else:
        liquidity_score = 35

    # --------------------------------------------------------
    # 5. KOVALAMA SKORU
    # --------------------------------------------------------

    chase_score = 0

    # Günlük yükseliş
    if change >= 5:
        chase_score += 20

    if change >= 10:
        chase_score += 20

    if change >= 15:
        chase_score += 15

    if change >= 20:
        chase_score += 15

    # 24S zirvesine yakınlık
    if position >= 80:
        chase_score += 15

    if position >= 90:
        chase_score += 10

    if position >= 97:
        chase_score += 5

    chase_score = clamp(chase_score)

    # --------------------------------------------------------
    # 6. VOLATİLİTE
    # --------------------------------------------------------

    volatility_score = clamp(
        100 - min(range_pct * 4, 80)
    )

    # --------------------------------------------------------
    # 7. GÜÇ SKORU
    # --------------------------------------------------------

    strength = (
        momentum * 0.35
        + liquidity_score * 0.20
        + location_score * 0.25
        + volatility_score * 0.10
        + (100 - max(0, chase_score - 40))
        * 0.10
    )

    strength = clamp(strength)

    # --------------------------------------------------------
    # 8. GERİ ÇEKİLME BÖLGESİ
    # --------------------------------------------------------

    # 24S range üzerinden Fibonacci benzeri yaklaşım

    if high > low:

        pullback_382 = (
            high
            - (high - low) * 0.382
        )

        pullback_500 = (
            high
            - (high - low) * 0.500
        )

        pullback_618 = (
            high
            - (high - low) * 0.618
        )

    else:

        pullback_382 = price * 0.97
        pullback_500 = price * 0.95
        pullback_618 = price * 0.93

    # --------------------------------------------------------
    # 9. İDEAL GİRİŞ
    # --------------------------------------------------------

    if chase_score >= 75:

        ideal_low = pullback_618
        ideal_high = pullback_500

    elif chase_score >= 50:

        ideal_low = pullback_500
        ideal_high = pullback_382

    else:

        ideal_low = price * 0.985
        ideal_high = price * 1.005

    # Fiyatın altına doğru normalize
    ideal_low = min(
        ideal_low,
        price
    )

    ideal_high = min(
        max(ideal_high, ideal_low),
        price * 1.01
    )

    # --------------------------------------------------------
    # 10. STOP
    # --------------------------------------------------------

    # Range tabanına göre stop

    stop = pullback_618 * 0.985

    # Çok uzak stop oluşmasını engelle
    max_stop_distance = 0.15

    minimum_allowed_stop = (
        price * (1 - max_stop_distance)
    )

    stop = max(
        stop,
        minimum_allowed_stop
    )

    # --------------------------------------------------------
    # 11. HEDEFLER
    # --------------------------------------------------------

    risk = max(
        price - stop,
        price * 0.005
    )

    target1 = price + risk * 2.0
    target2 = price + risk * 3.0
    target3 = price + risk * 4.0

    rr1 = (
        (target1 - price)
        / risk
    )

    rr2 = (
        (target2 - price)
        / risk
    )

    # --------------------------------------------------------
    # 12. GİRİŞ SKORU
    # --------------------------------------------------------

    entry_score = (
        strength * 0.35
        + location_score * 0.25
        + liquidity_score * 0.10
        + (100 - chase_score) * 0.20
        + min(rr2 / 3.0 * 100, 100) * 0.10
    )

    entry_score = clamp(entry_score)

    # --------------------------------------------------------
    # 13. KARAR MOTORU
    # --------------------------------------------------------

    if volume < MIN_VOLUME_TRY:

        decision = "🔴 LİKİDİTE YETERSİZ"

    elif change >= 20 and chase_score >= 75:

        decision = "🔴 KOVALAMA"

    elif chase_score >= 75:

        decision = "🟡 GERİ ÇEKİLME BEKLE"

    elif entry_score >= 78 and strength >= 72:

        decision = "🟢 AL"

    elif entry_score >= 68 and strength >= 65:

        decision = "🟢 GERİ ÇEKİLMEDE AL"

    elif strength >= 70:

        decision = "🔵 KIRILIM BEKLE"

    elif strength >= 55:

        decision = "🟡 TEYİT BEKLE"

    else:

        decision = "🟠 İZLE"

    # --------------------------------------------------------
    # 14. SINIF
    # --------------------------------------------------------

    if strength >= 80:

        grade = "🟢 A SINIFI"

    elif strength >= 70:

        grade = "🟡 B SINIFI"

    elif strength >= 60:

        grade = "🟠 C SINIFI"

    else:

        grade = "🔴 ZAYIF"

    # --------------------------------------------------------
    # 15. GİRİŞ MESAJI
    # --------------------------------------------------------

    if decision == "🟢 AL":

        entry_message = (
            "Mevcut fiyat trade için uygun."
        )

    elif decision == "🟢 GERİ ÇEKİLMEDE AL":

        entry_message = (
            "Güçlü yapı var. "
            "Daha iyi risk/getiri için küçük geri çekilme beklenebilir."
        )

    elif decision == "🟡 GERİ ÇEKİLME BEKLE":

        entry_message = (
            "Momentum güçlü fakat fiyat fazla yükseldi. "
            "Mevcut seviyeden kovalamak riskli."
        )

    elif decision == "🔵 KIRILIM BEKLE":

        entry_message = (
            "Yapı güçlü. Yeni zirve/kırılım teyidi beklenmeli."
        )

    elif decision == "🟡 TEYİT BEKLE":

        entry_message = (
            "Trade için yeterli teyit henüz oluşmadı."
        )

    elif decision == "🔴 KOVALAMA":

        entry_message = (
            "Fiyat çok hızlı yükselmiş. "
            "Bu seviyeden pozisyon açmak riskli."
        )

    else:

        entry_message = (
            "Şimdilik izleme bölgesinde."
        )

    return {

        "strength": round(strength, 1),

        "entry_score": round(entry_score, 1),

        "chase_score": round(chase_score, 1),

        "position": round(position, 1),

        "range_pct": round(range_pct, 2),

        "momentum": round(momentum, 1),

        "liquidity_score": round(
            liquidity_score,
            1
        ),

        "grade": grade,

        "decision": decision,

        "entry_low": ideal_low,

        "entry_high": ideal_high,

        "stop": stop,

        "target1": target1,

        "target2": target2,

        "target3": target3,

        "rr": round(rr2, 2),

        "message": entry_message,
    }


# ============================================================
# ANALİZİ ÇALIŞTIR
# ============================================================

analysis_rows = []

for _, row in df.iterrows():

    result = analyze_coin(row)

    analysis_rows.append(
        {
            **row.to_dict(),
            **result,
        }
    )

analysis = pd.DataFrame(
    analysis_rows
)


# ============================================================
# SIRALAMA
# ============================================================

analysis = analysis.sort_values(
    [
        "entry_score",
        "strength",
    ],
    ascending=False
).reset_index(drop=True)


# ============================================================
# BAŞLIK
# ============================================================

st.title("⚡ Kripto Trade Merkezi")

st.caption(
    "Profesyonel momentum + giriş + risk/getiri + "
    "kovalama filtresi"
)


# ============================================================
# VERİ DURUMU
# ============================================================

if using_fallback:

    st.warning(
        "⚠️ Canlı piyasa API'sine şu anda ulaşılamadı. "
        "Analiz, son sağlanan piyasa tablosu üzerinden çalıştırılıyor."
    )

else:

    st.success(
        f"🟢 Canlı piyasa verisi alındı — "
        f"{len(analysis)} TRY paritesi analiz edildi."
    )


# ============================================================
# ÖZET METRİKLER
# ============================================================

trade_count = len(
    analysis[
        analysis["decision"].isin(
            [
                "🟢 AL",
                "🟢 GERİ ÇEKİLMEDE AL",
            ]
        )
    ]
)

pullback_count = len(
    analysis[
        analysis["decision"]
        == "🟡 GERİ ÇEKİLME BEKLE"
    ]
)

chase_count = len(
    analysis[
        analysis["decision"]
        == "🔴 KOVALAMA"
    ]
)

breakout_count = len(
    analysis[
        analysis["decision"]
        == "🔵 KIRILIM BEKLE"
    ]
)


c1, c2, c3, c4, c5 = st.columns(5)

c1.metric(
    "Analiz Edilen",
    len(analysis)
)

c2.metric(
    "Trade Adayı",
    trade_count
)

c3.metric(
    "Geri Çekilme",
    pullback_count
)

c4.metric(
    "Kırılım",
    breakout_count
)

c5.metric(
    "Kovalama",
    chase_count
)


# ============================================================
# PROFESYONEL TRADE LİSTESİ
# ============================================================

st.divider()

st.subheader(
    "🏆 En İyi Trade Fırsatları"
)


display_cols = [

    "coin",
    "price",
    "change",
    "volume",
    "strength",
    "entry_score",
    "chase_score",
    "grade",
    "decision",
]


display_df = analysis[
    display_cols
].copy()


display_df.columns = [

    "Coin",
    "Fiyat",
    "24S",
    "Hacim",
    "Güç",
    "Giriş",
    "Kovalama",
    "Sınıf",
    "Karar",
]


display_df["Fiyat"] = display_df[
    "Fiyat"
].apply(fmt_price)

display_df["24S"] = display_df[
    "24S"
].apply(pct)

display_df["Hacim"] = display_df[
    "Hacim"
].apply(fmt_try)


st.dataframe(
    display_df,
    use_container_width=True,
    hide_index=True,
)


# ============================================================
# SADECE TRADE ADAYLARI
# ============================================================

st.divider()

st.subheader(
    "🟢 Trade Adayları"
)


trade_df = analysis[
    analysis["decision"].isin(
        [
            "🟢 AL",
            "🟢 GERİ ÇEKİLMEDE AL",
        ]
    )
].copy()


if trade_df.empty:

    st.info(
        "Şu anda profesyonel kriterlerin tamamını "
        "karşılayan güçlü bir trade fırsatı bulunmuyor."
    )

else:

    for _, row in trade_df.head(8).iterrows():

        with st.container(border=True):

            st.markdown(
                f"### 🟢 {row['coin']}"
            )

            a, b, c, d = st.columns(4)

            a.metric(
                "Fiyat",
                fmt_price(row["price"])
            )

            b.metric(
                "Güç",
                f"{row['strength']:.1f}"
            )

            c.metric(
                "Giriş",
                f"{row['entry_score']:.1f}"
            )

            d.metric(
                "24S",
                pct(row["change"])
            )

            st.markdown(
                f"""
**Giriş Bölgesi:**  
`{fmt_price(row['entry_low'])}`
 – `{fmt_price(row['entry_high'])}`

**Stop:** `{fmt_price(row['stop'])}`

**Hedef 1:** `{fmt_price(row['target1'])}`

**Hedef 2:** `{fmt_price(row['target2'])}`

**Hedef 3:** `{fmt_price(row['target3'])}`

**Risk / Ödül:** `1 : {row['rr']:.2f}`

**Karar:** {row['decision']}

**Neden:** {row['message']}
"""
            )


# ============================================================
# GERİ ÇEKİLME BEKLENENLER
# ============================================================

st.divider()

st.subheader(
    "🟡 Güçlü Ama Geri Çekilme Beklenmeli"
)


pullback_df = analysis[
    analysis["decision"]
    == "🟡 GERİ ÇEKİLME BEKLE"
].copy()


if pullback_df.empty:

    st.info(
        "Şu anda belirgin geri çekilme beklenen güçlü coin yok."
    )

else:

    for _, row in pullback_df.head(8).iterrows():

        with st.container(border=True):

            st.markdown(
                f"### 🟡 {row['coin']}"
            )

            st.write(
                f"**Mevcut fiyat:** "
                f"{fmt_price(row['price'])}"
            )

            st.write(
                f"**24S:** {pct(row['change'])}"
            )

            st.write(
                f"**Güç Skoru:** "
                f"{row['strength']:.1f}"
            )

            st.write(
                f"**Kovalama Skoru:** "
                f"{row['chase_score']:.1f}"
            )

            st.write(
                f"**Beklenen giriş:** "
                f"{fmt_price(row['entry_low'])}"
                f" – "
                f"{fmt_price(row['entry_high'])}"
            )

            st.info(
                row["message"]
            )


# ============================================================
# KOVALAMA RİSKİ
# ============================================================

st.divider()

st.subheader(
    "🔴 Kovalama Riski Yüksek"
)


chase_df = analysis[
    analysis["decision"]
    == "🔴 KOVALAMA"
].copy()


if chase_df.empty:

    st.success(
        "🔴 Aşırı kovalama bölgesinde coin bulunmuyor."
    )

else:

    chase_df = chase_df.sort_values(
        "chase_score",
        ascending=False
    )

    st.dataframe(
        chase_df[
            [
                "coin",
                "price",
                "change",
                "position",
                "chase_score",
                "strength",
            ]
        ].rename(
            columns={
                "coin": "Coin",
                "price": "Fiyat",
                "change": "24S",
                "position": "24S Zirve Konumu",
                "chase_score": "Kovalama",
                "strength": "Güç",
            }
        ),
        use_container_width=True,
        hide_index=True,
    )


# ============================================================
# KIRILIM BEKLENENLER
# ============================================================

st.divider()

st.subheader(
    "🔵 Kırılım Beklenen Coinler"
)


breakout_df = analysis[
    analysis["decision"]
    == "🔵 KIRILIM BEKLE"
].copy()


if breakout_df.empty:

    st.info(
        "Şu anda belirgin kırılım beklenen coin yok."
    )

else:

    st.dataframe(
        breakout_df[
            [
                "coin",
                "price",
                "change",
                "strength",
                "entry_score",
                "position",
            ]
        ].rename(
            columns={
                "coin": "Coin",
                "price": "Fiyat",
                "change": "24S",
                "strength": "Güç",
                "entry_score": "Giriş",
                "position": "24S Zirve Konumu",
            }
        ),
        use_container_width=True,
        hide_index=True,
    )


# ============================================================
# DETAYLI ANALİZ
# ============================================================

st.divider()

st.subheader(
    "🔎 Coin Detay Analizi"
)


coin_list = analysis[
    "coin"
].tolist()


if coin_list:

    selected_coin = st.selectbox(
        "Coin seç",
        coin_list
    )

    row = analysis[
        analysis["coin"]
        == selected_coin
    ].iloc[0]

    st.markdown(
        f"## {row['coin']}"
    )

    x1, x2, x3, x4 = st.columns(4)

    x1.metric(
        "Fiyat",
        fmt_price(row["price"])
    )

    x2.metric(
        "24S",
        pct(row["change"])
    )

    x3.metric(
        "Güç Skoru",
        f"{row['strength']:.1f}"
    )

    x4.metric(
        "Giriş Skoru",
        f"{row['entry_score']:.1f}"
    )

    st.markdown("---")

    d1, d2 = st.columns(2)

    with d1:

        st.markdown(
            "### 📊 Yapı"
        )

        st.write(
            f"**24S Yüksek:** "
            f"{fmt_price(row['high'])}"
        )

        st.write(
            f"**24S Düşük:** "
            f"{fmt_price(row['low'])}"
        )

        st.write(
            f"**24S Range:** "
            f"{row['range_pct']:.2f}%"
        )

        st.write(
            f"**Zirveye Konum:** "
            f"{row['position']:.1f}%"
        )

        st.write(
            f"**Hacim:** "
            f"{fmt_try(row['volume'])}"
        )

        st.write(
            f"**Likidite Skoru:** "
            f"{row['liquidity_score']:.1f}"
        )

    with d2:

        st.markdown(
            "### 🎯 Trade Planı"
        )

        st.write(
            f"**Karar:** "
            f"{row['decision']}"
        )

        st.write(
            f"**Sınıf:** "
            f"{row['grade']}"
        )

        st.write(
            f"**Giriş:** "
            f"{fmt_price(row['entry_low'])}"
            f" – "
            f"{fmt_price(row['entry_high'])}"
        )

        st.write(
            f"**Stop:** "
            f"{fmt_price(row['stop'])}"
        )

        st.write(
            f"**Hedef 1:** "
            f"{fmt_price(row['target1'])}"
        )

        st.write(
            f"**Hedef 2:** "
            f"{fmt_price(row['target2'])}"
        )

        st.write(
            f"**Hedef 3:** "
            f"{fmt_price(row['target3'])}"
        )

        st.write(
            f"**Risk / Ödül:** "
            f"1 : {row['rr']:.2f}"
        )

    st.info(
        row["message"]
    )


# ============================================================
# HAM VERİ
# ============================================================

with st.expander(
    "📊 Ham Piyasa Verisi"
):

    raw = analysis[
        [
            "symbol",
            "coin",
            "price",
            "change",
            "volume",
            "high",
            "low",
        ]
    ].copy()

    st.dataframe(
        raw,
        use_container_width=True,
        hide_index=True,
    )


# ============================================================
# SİSTEM MANTIĞI
# ============================================================

with st.expander(
    "🧠 Trade Motoru Nasıl Çalışıyor?"
):

    st.markdown(
        """
### 1. Güç Skoru

Coinin:

- momentumunu
- likiditesini
- 24 saatlik fiyat konumunu
- volatilitesini
- kovalama riskini

birlikte değerlendirir.

### 2. Giriş Skoru

Güçlü olmak tek başına AL anlamına gelmez.

Giriş skoru ayrıca:

- mevcut fiyatın konumu
- geri çekilme potansiyeli
- likidite
- kovalama riski
- risk/ödül

üzerinden hesaplanır.

### 3. Kovalama Filtresi

Coin çok hızlı yükselmişse sistem otomatik olarak AL demek yerine:

**GERİ ÇEKİLME BEKLE**

veya

**KOVALAMA**

kararı üretir.

### 4. Risk / Ödül

Trade planında hedefler stop mesafesine göre hesaplanır.

Sistem mümkün olduğunca:

**1 : 2**

ve üzerindeki fırsatları önceliklendirir.

### 5. Nihai Karar

Sistem yalnızca:

> "Bu coin güçlü mü?"

diye sormaz.

Asıl soru:

> **"Bu coin şu anda alınabilecek kadar güçlü ve fiyatı risk/getiri açısından uygun mu?"**

olur.
"""
    )


# ============================================================
# UYARI
# ============================================================

st.caption(
    "⚠️ Bu sayfa otomatik emir göndermez. "
    "Skorlar ve seviyeler teknik analiz amaçlıdır; "
    "yatırım tavsiyesi değildir."
)