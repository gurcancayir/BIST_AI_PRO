# ============================================================
# CRYPTO AI PRO
# 04_Crypto_Portfoy_PRO.py
#
# KALICI KRİPTO PORTFÖY YÖNETİM MERKEZİ
#
# ÖZELLİKLER
# ------------------------------------------------------------
# - Portföy kalıcı olarak JSON dosyasına kaydedilir
# - Sayfa yenilense de portföy silinmez
# - Birden fazla coin aynı anda eklenebilir
# - Adet + ortalama maliyet tutulur
# - Güncel piyasa verisi crypto_engine'den alınır
# - Kısa / Orta / Uzun vade ayrı değerlendirilir
# - Genel portföy kararı oluşturulur
#
# KARARLAR
# ------------------------------------------------------------
# 🟢 AL
# 🟢 GÜÇLÜ TUT
# 🟡 TUT
# 🟡 AZALT
# 🔴 SAT
# ⚪ BEKLE
#
# DOSYA
# ------------------------------------------------------------
# crypto_portfolio.json
#
# ============================================================

import streamlit as st
import pandas as pd
import numpy as np
import importlib
import json
import os
import crypto_engine


# ============================================================
# SAYFA AYARLARI
# ============================================================

st.set_page_config(
    page_title="Kripto Portföy PRO",
    page_icon="💼",
    layout="wide",
)


# ============================================================
# ENGINE YENİLE
# ============================================================

crypto_engine = importlib.reload(
    crypto_engine
)


# ============================================================
# AYARLAR
# ============================================================

PORTFOLIO_FILE = "crypto_portfolio.json"


# ============================================================
# YARDIMCI FONKSİYONLAR
# ============================================================

def safe_float(value, default=0.0):

    try:

        if value is None:
            return default

        value = float(value)

        if np.isnan(value):
            return default

        return value

    except Exception:

        return default


def clamp(value, low=0, high=100):

    return max(
        low,
        min(high, safe_float(value))
    )


def format_price(value):

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


def format_money(value):

    value = safe_float(value)

    if abs(value) >= 1_000_000_000:
        return f"₺{value / 1_000_000_000:.2f} Mr"

    if abs(value) >= 1_000_000:
        return f"₺{value / 1_000_000:.2f} Mn"

    if abs(value) >= 1_000:
        return f"₺{value / 1_000:.1f} Bin"

    return f"₺{value:,.0f}"


# ============================================================
# PORTFÖY DOSYASI
# ============================================================

def load_portfolio():

    if not os.path.exists(PORTFOLIO_FILE):

        return []

    try:

        with open(
            PORTFOLIO_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            data = json.load(f)

        if isinstance(data, list):

            return data

        return []

    except Exception:

        return []


def save_portfolio(rows):

    try:

        with open(
            PORTFOLIO_FILE,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                rows,
                f,
                ensure_ascii=False,
                indent=4
            )

        return True

    except Exception as e:

        st.error(
            f"Portföy kaydedilemedi: {e}"
        )

        return False


# ============================================================
# PORTFÖYÜ YÜKLE
# ============================================================

portfolio_rows = load_portfolio()


# ============================================================
# BAŞLIK
# ============================================================

st.title(
    "💼 Kripto Portföy Yönetim PRO"
)

st.caption(
    "Kalıcı portföy + kısa vade + orta vade + uzun vade "
    "karar merkezi"
)

st.info(
    "Portföy artık Streamlit oturumuna değil, "
    "`crypto_portfolio.json` dosyasına kaydedilir. "
    "Bu nedenle sayfa yenilendiğinde portföy korunur."
)


# ============================================================
# PİYASA VERİSİ
# ============================================================

@st.cache_data(ttl=60)
def load_market():

    try:

        raw = crypto_engine.get_all_try_universe()

    except Exception as e:

        return pd.DataFrame(), str(e)

    if raw is None:

        return pd.DataFrame(), "Veri alınamadı."

    if isinstance(raw, pd.DataFrame):

        df = raw.copy()

    elif isinstance(raw, list):

        if not raw:

            return pd.DataFrame(), "TRY evreni boş."

        if isinstance(raw[0], dict):

            df = pd.DataFrame(raw)

        else:

            df = pd.DataFrame(
                {
                    "symbol": raw
                }
            )

    else:

        return (
            pd.DataFrame(),
            f"Beklenmeyen veri tipi: {type(raw).__name__}"
        )

    if df.empty:

        return pd.DataFrame(), "Piyasa verisi boş."

    return df, ""


df_market, market_error = load_market()


if df_market.empty:

    st.error(
        "Kripto piyasa verisi alınamadı."
    )

    if market_error:

        st.caption(
            market_error
        )

    st.stop()


# ============================================================
# SYMBOL
# ============================================================

if "symbol" not in df_market.columns:

    possible = [
        "symbol",
        "pair",
        "name",
        "code"
    ]

    found = None

    for col in possible:

        if col in df_market.columns:

            found = col
            break

    if found:

        df_market["symbol"] = (
            df_market[found]
            .astype(str)
            .str.upper()
            .str.strip()
        )

    else:

        st.error(
            "Piyasa verisinde sembol bulunamadı."
        )

        st.stop()


df_market["symbol"] = (
    df_market["symbol"]
    .astype(str)
    .str.upper()
    .str.strip()
)


# ============================================================
# BASE ASSET
# ============================================================

if "base_asset" not in df_market.columns:

    df_market["base_asset"] = (
        df_market["symbol"]
        .str.replace("_TRY", "", regex=False)
        .str.replace("TRY", "", regex=False)
    )


df_market["base_asset"] = (
    df_market["base_asset"]
    .astype(str)
    .str.upper()
    .str.strip()
)


# ============================================================
# ZORUNLU KOLONLAR
# ============================================================

for col in [
    "price_try",
    "change_24h",
    "volume_try"
]:

    if col not in df_market.columns:

        df_market[col] = 0.0

    df_market[col] = pd.to_numeric(
        df_market[col],
        errors="coerce"
    ).fillna(0)


# ============================================================
# ÜST PİYASA BİLGİSİ
# ============================================================

market_change = (
    df_market["change_24h"]
    .replace(
        [np.inf, -np.inf],
        np.nan
    )
    .dropna()
)


if not market_change.empty:

    market_avg_change = (
        market_change.mean()
    )

else:

    market_avg_change = 0


m1, m2, m3, m4 = st.columns(4)


with m1:

    st.metric(
        "TRY Evreni",
        len(df_market)
    )


with m2:

    st.metric(
        "Portföy Coin",
        len(portfolio_rows)
    )


with m3:

    st.metric(
        "Piyasa 24s",
        f"{market_avg_change:+.2f}%"
    )


with m4:

    st.metric(
        "Veri",
        "CANLI"
    )


# ============================================================
# COİN LİSTESİ
# ============================================================

coin_options = sorted(
    df_market["base_asset"]
    .dropna()
    .unique()
    .tolist()
)


# ============================================================
# PORTFÖYE BİRDEN FAZLA COİN EKLE
# ============================================================

st.divider()

st.subheader(
    "➕ Portföye Coin Ekle"
)

st.caption(
    "Aynı anda birden fazla coin girebilirsin. "
    "Her satır bir pozisyondur."
)


if "new_portfolio_df" not in st.session_state:

    st.session_state.new_portfolio_df = pd.DataFrame(
        [
            {
                "Coin": "",
                "Adet": 0.0,
                "Maliyet": 0.0
            }
        ]
    )


edited = st.data_editor(
    st.session_state.new_portfolio_df,
    num_rows="dynamic",
    use_container_width=True,
    hide_index=True,
    column_config={

        "Coin": st.column_config.SelectboxColumn(
            "Coin",
            options=coin_options,
            required=False
        ),

        "Adet": st.column_config.NumberColumn(
            "Adet",
            min_value=0.0,
            step=1.0
        ),

        "Maliyet": st.column_config.NumberColumn(
            "Ortalama Maliyet ₺",
            min_value=0.0,
            step=0.0001,
            format="%.8f"
        ),
    },
    key="portfolio_editor"
)


c_add, c_clear = st.columns(2)


with c_add:

    if st.button(
        "💾 Portföye Kaydet / Güncelle",
        use_container_width=True
    ):

        changed = False

        for _, row in edited.iterrows():

            coin = str(
                row.get("Coin", "")
            ).upper().strip()

            quantity = safe_float(
                row.get("Adet", 0)
            )

            cost = safe_float(
                row.get("Maliyet", 0)
            )

            if not coin:
                continue

            if quantity <= 0:
                continue

            if cost <= 0:
                continue

            existing = None

            for item in portfolio_rows:

                if item["coin"] == coin:

                    existing = item
                    break

            if existing:

                old_qty = safe_float(
                    existing["quantity"]
                )

                old_cost = safe_float(
                    existing["cost"]
                )

                total_qty = (
                    old_qty
                    +
                    quantity
                )

                if total_qty > 0:

                    weighted_cost = (
                        old_qty * old_cost
                        +
                        quantity * cost
                    ) / total_qty

                else:

                    weighted_cost = cost

                existing["quantity"] = total_qty
                existing["cost"] = weighted_cost

            else:

                portfolio_rows.append(
                    {
                        "coin": coin,
                        "quantity": quantity,
                        "cost": cost
                    }
                )

            changed = True

        if changed:

            if save_portfolio(
                portfolio_rows
            ):

                st.success(
                    "Portföy başarıyla kaydedildi."
                )

                st.session_state.new_portfolio_df = pd.DataFrame(
                    [
                        {
                            "Coin": "",
                            "Adet": 0.0,
                            "Maliyet": 0.0
                        }
                    ]
                )

                st.rerun()

        else:

            st.warning(
                "Kaydedilecek geçerli bir coin bulunamadı."
            )


with c_clear:

    if st.button(
        "🧹 Giriş Alanını Temizle",
        use_container_width=True
    ):

        st.session_state.new_portfolio_df = pd.DataFrame(
            [
                {
                    "Coin": "",
                    "Adet": 0.0,
                    "Maliyet": 0.0
                }
            ]
        )

        st.rerun()


# ============================================================
# PORTFÖY BOŞSA
# ============================================================

if not portfolio_rows:

    st.info(
        "Portföy henüz boş. Yukarıdaki alandan coin ekleyebilirsin."
    )

    st.stop()


# ============================================================
# PORTFÖY DATAFRAME
# ============================================================

portfolio_df = pd.DataFrame(
    portfolio_rows
)


# ============================================================
# PİYASA VERİSİYLE BİRLEŞTİR
# ============================================================

portfolio_df = portfolio_df.merge(
    df_market[
        [
            "base_asset",
            "price_try",
            "change_24h",
            "volume_try"
        ]
    ],
    left_on="coin",
    right_on="base_asset",
    how="left"
)


portfolio_df["price_try"] = pd.to_numeric(
    portfolio_df["price_try"],
    errors="coerce"
).fillna(0)


portfolio_df["change_24h"] = pd.to_numeric(
    portfolio_df["change_24h"],
    errors="coerce"
).fillna(0)


portfolio_df["volume_try"] = pd.to_numeric(
    portfolio_df["volume_try"],
    errors="coerce"
).fillna(0)


# ============================================================
# POZİSYON HESAPLARI
# ============================================================

portfolio_df["position_value"] = (
    portfolio_df["quantity"]
    *
    portfolio_df["price_try"]
)


portfolio_df["cost_value"] = (
    portfolio_df["quantity"]
    *
    portfolio_df["cost"]
)


portfolio_df["profit_loss"] = (
    portfolio_df["position_value"]
    -
    portfolio_df["cost_value"]
)


portfolio_df["profit_loss_pct"] = np.where(
    portfolio_df["cost_value"] > 0,

    portfolio_df["profit_loss"]
    /
    portfolio_df["cost_value"]
    *
    100,

    0
)


# ============================================================
# TOPLAM PORTFÖY
# ============================================================

total_value = (
    portfolio_df["position_value"]
    .sum()
)


total_cost = (
    portfolio_df["cost_value"]
    .sum()
)


total_profit = (
    total_value
    -
    total_cost
)


total_profit_pct = (
    total_profit
    /
    total_cost
    *
    100
    if total_cost > 0
    else 0
)


# ============================================================
# AĞIRLIK
# ============================================================

if total_value > 0:

    portfolio_df["Ağırlık"] = (
        portfolio_df["position_value"]
        /
        total_value
        *
        100
    )

else:

    portfolio_df["Ağırlık"] = 0


# ============================================================
# TEKNİK GÜÇ
# ============================================================

def calculate_strength(row):

    change = safe_float(
        row["change_24h"]
    )

    pnl = safe_float(
        row["profit_loss_pct"]
    )

    volume = safe_float(
        row["volume_try"]
    )


    # --------------------------------------------------------
    # MOMENTUM
    # --------------------------------------------------------

    if change >= 15:
        momentum = 100

    elif change >= 10:
        momentum = 92

    elif change >= 7:
        momentum = 85

    elif change >= 4:
        momentum = 78

    elif change >= 1:
        momentum = 68

    elif change >= 0:
        momentum = 60

    elif change >= -3:
        momentum = 50

    elif change >= -7:
        momentum = 40

    elif change >= -12:
        momentum = 28

    else:
        momentum = 15


    # --------------------------------------------------------
    # POZİSYON PERFORMANSI
    # --------------------------------------------------------

    if pnl >= 30:
        performance = 100

    elif pnl >= 20:
        performance = 95

    elif pnl >= 10:
        performance = 88

    elif pnl >= 5:
        performance = 78

    elif pnl >= 0:
        performance = 65

    elif pnl >= -5:
        performance = 52

    elif pnl >= -10:
        performance = 40

    elif pnl >= -20:
        performance = 28

    else:
        performance = 15


    # --------------------------------------------------------
    # LİKİDİTE
    # --------------------------------------------------------

    if volume >= 2_000_000_000:
        liquidity = 100

    elif volume >= 1_000_000_000:
        liquidity = 95

    elif volume >= 500_000_000:
        liquidity = 90

    elif volume >= 250_000_000:
        liquidity = 80

    elif volume >= 100_000_000:
        liquidity = 70

    elif volume >= 50_000_000:
        liquidity = 60

    else:
        liquidity = 45


    score = (
        momentum * 0.45
        +
        performance * 0.30
        +
        liquidity * 0.25
    )

    return clamp(score)


portfolio_df["Güç"] = (
    portfolio_df.apply(
        calculate_strength,
        axis=1
    )
)


# ============================================================
# RİSK
# ============================================================

def calculate_risk(row):

    weight = safe_float(
        row["Ağırlık"]
    )

    pnl = safe_float(
        row["profit_loss_pct"]
    )

    change = safe_float(
        row["change_24h"]
    )

    risk = 0


    # Portföy ağırlığı

    if weight >= 50:
        risk += 40

    elif weight >= 35:
        risk += 30

    elif weight >= 25:
        risk += 20

    elif weight >= 15:
        risk += 10


    # Volatilite

    if abs(change) >= 20:
        risk += 30

    elif abs(change) >= 15:
        risk += 22

    elif abs(change) >= 10:
        risk += 14

    elif abs(change) >= 7:
        risk += 7


    # Zarar

    if pnl <= -25:
        risk += 30

    elif pnl <= -15:
        risk += 25

    elif pnl <= -10:
        risk += 18

    elif pnl <= -5:
        risk += 10


    return clamp(risk)


portfolio_df["Risk"] = (
    portfolio_df.apply(
        calculate_risk,
        axis=1
    )
)


# ============================================================
# VADE SKORLARI
# ============================================================

def short_score(row):

    strength = safe_float(
        row["Güç"]
    )

    change = safe_float(
        row["change_24h"]
    )

    risk = safe_float(
        row["Risk"]
    )

    score = (
        strength * 0.55
        +
        clamp(
            50 + change * 3,
            0,
            100
        ) * 0.30
        +
        (100 - risk) * 0.15
    )

    return clamp(score)


def medium_score(row):

    strength = safe_float(
        row["Güç"]
    )

    pnl = safe_float(
        row["profit_loss_pct"]
    )

    risk = safe_float(
        row["Risk"]
    )

    score = (
        strength * 0.55
        +
        clamp(
            60 + pnl,
            0,
            100
        ) * 0.25
        +
        (100 - risk) * 0.20
    )

    return clamp(score)


def long_score(row):

    strength = safe_float(
        row["Güç"]
    )

    pnl = safe_float(
        row["profit_loss_pct"]
    )

    weight = safe_float(
        row["Ağırlık"]
    )

    risk = safe_float(
        row["Risk"]
    )


    concentration_penalty = 0

    if weight > 30:

        concentration_penalty = (
            weight - 30
        )


    score = (
        strength * 0.45
        +
        clamp(
            60 + pnl * 0.5,
            0,
            100
        ) * 0.30
        +
        (100 - risk) * 0.25
        -
        concentration_penalty * 0.25
    )

    return clamp(score)


portfolio_df["Kısa Skor"] = (
    portfolio_df.apply(
        short_score,
        axis=1
    )
)


portfolio_df["Orta Skor"] = (
    portfolio_df.apply(
        medium_score,
        axis=1
    )
)


portfolio_df["Uzun Skor"] = (
    portfolio_df.apply(
        long_score,
        axis=1
    )
)


# ============================================================
# KARAR FONKSİYONU
# ============================================================

def decision_from_score(
    score,
    risk,
    pnl,
    change
):

    score = safe_float(score)
    risk = safe_float(risk)
    pnl = safe_float(pnl)
    change = safe_float(change)


    # Çok yüksek risk

    if risk >= 80:

        return "🔴 SAT"


    # Çok zayıf

    if score < 30:

        return "🔴 SAT"


    # Riskli zayıflama

    if (
        score < 45
        and change < -5
    ):

        return "🟡 AZALT"


    # Çok güçlü

    if (
        score >= 85
        and risk < 40
    ):

        return "🟢 AL"


    # Güçlü

    if (
        score >= 75
        and risk < 55
    ):

        return "🟢 GÜÇLÜ TUT"


    # Kâr yüksek + momentum bozuluyor

    if (
        pnl >= 25
        and change < 0
    ):

        return "🟡 AZALT"


    # Normal

    if score >= 55:

        return "🟡 TUT"


    return "⚪ BEKLE"


# ============================================================
# VADE KARARLARI
# ============================================================

portfolio_df["Kısa Karar"] = portfolio_df.apply(
    lambda row: decision_from_score(
        row["Kısa Skor"],
        row["Risk"],
        row["profit_loss_pct"],
        row["change_24h"]
    ),
    axis=1
)


portfolio_df["Orta Karar"] = portfolio_df.apply(
    lambda row: decision_from_score(
        row["Orta Skor"],
        row["Risk"],
        row["profit_loss_pct"],
        row["change_24h"]
    ),
    axis=1
)


portfolio_df["Uzun Karar"] = portfolio_df.apply(
    lambda row: decision_from_score(
        row["Uzun Skor"],
        row["Risk"],
        row["profit_loss_pct"],
        row["change_24h"]
    ),
    axis=1
)


# ============================================================
# GENEL KARAR
# ============================================================

def general_decision(row):

    scores = [
        safe_float(row["Kısa Skor"]),
        safe_float(row["Orta Skor"]),
        safe_float(row["Uzun Skor"])
    ]

    avg_score = np.mean(
        scores
    )

    risk = safe_float(
        row["Risk"]
    )

    pnl = safe_float(
        row["profit_loss_pct"]
    )

    change = safe_float(
        row["change_24h"]
    )


    if risk >= 80:

        return "🔴 SAT"


    if avg_score < 35:

        return "🔴 SAT"


    if (
        avg_score < 50
        and change < -5
    ):

        return "🟡 AZALT"


    if (
        avg_score >= 85
        and risk < 40
    ):

        return "🟢 AL"


    if (
        avg_score >= 75
        and risk < 55
    ):

        return "🟢 GÜÇLÜ TUT"


    if (
        pnl >= 25
        and change < 0
    ):

        return "🟡 AZALT"


    if avg_score >= 55:

        return "🟡 TUT"


    return "⚪ BEKLE"


portfolio_df["Genel Karar"] = (
    portfolio_df.apply(
        general_decision,
        axis=1
    )
)


# ============================================================
# GENEL YORUM
# ============================================================

def create_comment(row):

    short = row["Kısa Karar"]
    medium = row["Orta Karar"]
    long = row["Uzun Karar"]

    risk = safe_float(
        row["Risk"]
    )

    pnl = safe_float(
        row["profit_loss_pct"]
    )

    change = safe_float(
        row["change_24h"]
    )


    return (
        f"Kısa vade: {short} | "
        f"Orta vade: {medium} | "
        f"Uzun vade: {long}. "
        f"Pozisyon K/Z %{pnl:+.1f}, "
        f"24s %{change:+.1f}, "
        f"risk {risk:.0f}/100."
    )


portfolio_df["Yorum"] = (
    portfolio_df.apply(
        create_comment,
        axis=1
    )
)


# ============================================================
# PORTFÖY ÖZETİ
# ============================================================

st.divider()

st.subheader(
    "📊 Portföy Özeti"
)


m1, m2, m3, m4, m5 = st.columns(5)


with m1:

    st.metric(
        "Portföy Değeri",
        format_money(total_value)
    )


with m2:

    st.metric(
        "Maliyet",
        format_money(total_cost)
    )


with m3:

    st.metric(
        "Kâr / Zarar",
        format_money(total_profit),
        f"{total_profit_pct:+.2f}%"
    )


with m4:

    st.metric(
        "Coin",
        len(portfolio_df)
    )


with m5:

    avg_strength = (
        portfolio_df["Güç"].mean()
    )

    st.metric(
        "Ort. Güç",
        f"{avg_strength:.1f}/100"
    )


# ============================================================
# VADE KARAR ÖZETİ
# ============================================================

st.divider()

st.subheader(
    "🎯 Vade Bazlı Portföy Kararları"
)


v1, v2, v3 = st.columns(3)


with v1:

    st.markdown(
        "### ⚡ Kısa Vade"
    )

    short_avg = (
        portfolio_df["Kısa Skor"]
        .mean()
    )

    st.metric(
        "Kısa Vade Skoru",
        f"{short_avg:.1f}/100"
    )

    if short_avg >= 75:

        st.success(
            "Kısa vadede portföy güçlü."
        )

    elif short_avg >= 55:

        st.warning(
            "Kısa vadede seçici olmak gerekiyor."
        )

    else:

        st.error(
            "Kısa vadede risk yüksek."
        )


with v2:

    st.markdown(
        "### 📊 Orta Vade"
    )

    medium_avg = (
        portfolio_df["Orta Skor"]
        .mean()
    )

    st.metric(
        "Orta Vade Skoru",
        f"{medium_avg:.1f}/100"
    )

    if medium_avg >= 75:

        st.success(
            "Orta vadede yapı güçlü."
        )

    elif medium_avg >= 55:

        st.warning(
            "Orta vadede bekle-gör yaklaşımı uygun."
        )

    else:

        st.error(
            "Orta vadede zayıflık mevcut."
        )


with v3:

    st.markdown(
        "### 🏆 Uzun Vade"
    )

    long_avg = (
        portfolio_df["Uzun Skor"]
        .mean()
    )

    st.metric(
        "Uzun Vade Skoru",
        f"{long_avg:.1f}/100"
    )

    if long_avg >= 75:

        st.success(
            "Uzun vadede portföy yapısı güçlü."
        )

    elif long_avg >= 55:

        st.warning(
            "Uzun vadede seçici olmak gerekiyor."
        )

    else:

        st.error(
            "Uzun vadede risk/zayıflık mevcut."
        )


# ============================================================
# ANA PORTFÖY TABLOSU
# ============================================================

st.divider()

st.subheader(
    "💼 Portföy Karar Tablosu"
)


table = portfolio_df[
    [
        "coin",
        "quantity",
        "cost",
        "price_try",
        "position_value",
        "profit_loss",
        "profit_loss_pct",
        "Ağırlık",
        "Güç",
        "Risk",
        "Kısa Karar",
        "Orta Karar",
        "Uzun Karar",
        "Genel Karar"
    ]
].copy()


table = table.rename(
    columns={
        "coin": "Coin",
        "quantity": "Adet",
        "cost": "Maliyet ₺",
        "price_try": "Fiyat ₺",
        "position_value": "Pozisyon ₺",
        "profit_loss": "K/Z ₺",
        "profit_loss_pct": "K/Z %",
        "Ağırlık": "Ağırlık %",
        "Güç": "Güç",
        "Risk": "Risk",
        "Kısa Karar": "⚡ Kısa Vade",
        "Orta Karar": "📊 Orta Vade",
        "Uzun Karar": "🏆 Uzun Vade",
        "Genel Karar": "🎯 Genel Karar"
    }
)


st.dataframe(
    table,
    use_container_width=True,
    hide_index=True,
)


# ============================================================
# COİN KARTLARI
# ============================================================

st.divider()

st.subheader(
    "🪙 Coin Bazlı Karar Merkezi"
)


for _, row in portfolio_df.iterrows():

    with st.container(
        border=True
    ):

        c1, c2, c3, c4 = st.columns(4)


        # ----------------------------------------------------
        # COIN
        # ----------------------------------------------------

        with c1:

            st.markdown(
                f"## {row['coin']}"
            )

            st.metric(
                "Genel Karar",
                row["Genel Karar"]
            )

            st.caption(
                row["Yorum"]
            )


        # ----------------------------------------------------
        # POZİSYON
        # ----------------------------------------------------

        with c2:

            st.metric(
                "Fiyat",
                f"₺{format_price(row['price_try'])}"
            )

            st.metric(
                "K/Z",
                format_money(
                    row["profit_loss"]
                ),
                f"{row['profit_loss_pct']:+.2f}%"
            )

            st.metric(
                "Ağırlık",
                f"%{row['Ağırlık']:.1f}"
            )


        # ----------------------------------------------------
        # KISA / ORTA
        # ----------------------------------------------------

        with c3:

            st.markdown(
                "### ⚡ Kısa / 📊 Orta"
            )

            st.write(
                f"**Kısa:** "
                f"{row['Kısa Karar']}"
            )

            st.write(
                f"Skor: "
                f"**{row['Kısa Skor']:.1f}/100**"
            )

            st.write(
                f"**Orta:** "
                f"{row['Orta Karar']}"
            )

            st.write(
                f"Skor: "
                f"**{row['Orta Skor']:.1f}/100**"
            )


        # ----------------------------------------------------
        # UZUN / RİSK
        # ----------------------------------------------------

        with c4:

            st.markdown(
                "### 🏆 Uzun Vade"
            )

            st.write(
                f"**{row['Uzun Karar']}**"
            )

            st.write(
                f"Skor: "
                f"**{row['Uzun Skor']:.1f}/100**"
            )

            st.metric(
                "Güç",
                f"{row['Güç']:.1f}"
            )

            st.metric(
                "Risk",
                f"{row['Risk']:.1f}/100"
            )


# ============================================================
# EN RİSKLİ POZİSYONLAR
# ============================================================

st.divider()

st.subheader(
    "⚠️ Portföy Risk Merkezi"
)


risk_df = portfolio_df.sort_values(
    "Risk",
    ascending=False
)


r1, r2, r3 = st.columns(3)


with r1:

    highest_risk = risk_df.iloc[0]

    st.metric(
        "En Yüksek Risk",
        highest_risk["coin"],
        f"{highest_risk['Risk']:.1f}/100"
    )


with r2:

    highest_weight = (
        portfolio_df
        .sort_values(
            "Ağırlık",
            ascending=False
        )
        .iloc[0]
    )

    st.metric(
        "En Yüksek Ağırlık",
        highest_weight["coin"],
        f"%{highest_weight['Ağırlık']:.1f}"
    )


with r3:

    best_coin = (
        portfolio_df
        .sort_values(
            "Güç",
            ascending=False
        )
        .iloc[0]
    )

    st.metric(
        "En Güçlü Coin",
        best_coin["coin"],
        f"{best_coin['Güç']:.1f}/100"
    )


# ============================================================
# PORTFÖYDEN COİN SİL
# ============================================================

st.divider()

st.subheader(
    "🗑️ Portföy Yönetimi"
)


delete_coin = st.selectbox(
    "Portföyden çıkarılacak coin",
    portfolio_df["coin"].tolist(),
    key="portfolio_delete_coin"
)


if st.button(
    "🗑️ Seçili Coini Sil",
    use_container_width=True
):

    portfolio_rows = [
        item
        for item in portfolio_rows
        if item["coin"] != delete_coin
    ]

    save_portfolio(
        portfolio_rows
    )

    st.success(
        f"{delete_coin} portföyden silindi."
    )

    st.rerun()


# ============================================================
# TÜM PORTFÖYÜ SİL
# ============================================================

if st.button(
    "⚠️ TÜM PORTFÖYÜ SİL",
    use_container_width=True
):

    save_portfolio(
        []
    )

    st.success(
        "Portföy tamamen temizlendi."
    )

    st.rerun()


# ============================================================
# KARAR MOTORU
# ============================================================

st.divider()

with st.expander(
    "🧠 Karar Motoru"
):

    st.markdown(
        """
### ⚡ Kısa Vade

Kısa vadede ağırlık:

- 24 saatlik momentum
- Teknik güç
- Günlük risk
- Likidite

üzerindedir.

### 📊 Orta Vade

Orta vadede:

- Teknik güç
- Pozisyon performansı
- Risk
- Momentum

birlikte değerlendirilir.

### 🏆 Uzun Vade

Uzun vadede:

- Genel güç
- K/Z yapısı
- Risk
- Portföy ağırlığı

daha fazla önem kazanır.

### Kararlar

**🟢 AL**

Güçlü yapı + kontrollü risk.

**🟢 GÜÇLÜ TUT**

Mevcut pozisyon güçlü. Korunabilir.

**🟡 TUT**

Pozisyon izlenebilir ancak agresif hareket için
yeterli avantaj yok.

**🟡 AZALT**

Risk veya zayıflama nedeniyle pozisyon küçültme
düşünülebilir.

**🔴 SAT**

Güç ciddi şekilde zayıflamış veya risk çok yüksek.

**⚪ BEKLE**

Net yön oluşmamış. Yeni teyit beklenmeli.
"""
    )


# ============================================================
# SON UYARI
# ============================================================

st.divider()

st.caption(
    "⚠️ Bu sayfa yatırım tavsiyesi değildir. "
    "Kararlar otomatik teknik karar desteğidir. "
    "Gerçek işlem öncesinde likidite, spread, volatilite "
    "ve piyasa koşulları ayrıca değerlendirilmelidir."
)