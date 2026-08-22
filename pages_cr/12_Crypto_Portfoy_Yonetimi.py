# ============================================================
# CRYPTO AI PRO
# 11_Crypto_Portfoy.py
#
# KRİPTO PORTFÖY YÖNETİM MERKEZİ
#
# AMAÇ
# ------------------------------------------------------------
# Kullanıcının elindeki coinleri takip eder.
#
# Her coin için:
#   - Mevcut fiyat
#   - Maliyet
#   - Adet
#   - Pozisyon değeri
#   - Kâr / Zarar
#   - Kâr / Zarar %
#   - 24s değişim
#   - Teknik güç
#   - Momentum
#   - Portföy ağırlığı
#   - Risk
#   - FINAL karar
#
# KARARLAR
# ------------------------------------------------------------
# 🟢 AL
# 🟢 TUT / GÜÇLÜ
# 🟡 TUT
# 🟡 AZALT
# 🔴 SAT
# ⚪ İZLE
#
# VERİ KAYNAĞI
# ------------------------------------------------------------
# crypto_engine.get_all_try_universe()
#
# ============================================================

import streamlit as st
import pandas as pd
import numpy as np
import importlib
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
# BAŞLIK
# ============================================================

st.title("💼 Kripto Portföy Yönetim PRO")

st.caption(
    "Portföyündeki coinleri maliyet, momentum, teknik güç, "
    "risk ve piyasa koşullarına göre değerlendiren karar motoru."
)


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

    if value >= 1_000_000_000:

        return f"₺{value / 1_000_000_000:.2f} Mr"

    if value >= 1_000_000:

        return f"₺{value / 1_000_000:.2f} Mn"

    if value >= 1_000:

        return f"₺{value / 1_000:.1f} Bin"

    return f"₺{value:,.0f}"


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


# ============================================================
# VERİ AL
# ============================================================

df_market, market_error = load_market()


if df_market.empty:

    st.error(
        "Kripto piyasa verisi alınamadı."
    )

    if market_error:

        st.caption(market_error)

    st.stop()


# ============================================================
# KOLON NORMALİZASYONU
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
# COIN ADI
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
# FİYAT
# ============================================================

if "price_try" not in df_market.columns:

    df_market["price_try"] = 0.0


df_market["price_try"] = pd.to_numeric(
    df_market["price_try"],
    errors="coerce"
).fillna(0)


# ============================================================
# 24S DEĞİŞİM
# ============================================================

if "change_24h" not in df_market.columns:

    df_market["change_24h"] = 0.0


df_market["change_24h"] = pd.to_numeric(
    df_market["change_24h"],
    errors="coerce"
).fillna(0)


# ============================================================
# 24S HACİM
# ============================================================

if "volume_try" not in df_market.columns:

    df_market["volume_try"] = 0.0


df_market["volume_try"] = pd.to_numeric(
    df_market["volume_try"],
    errors="coerce"
).fillna(0)


# ============================================================
# PORTFÖY STATE
# ============================================================

if "portfolio_rows" not in st.session_state:

    st.session_state.portfolio_rows = []


# ============================================================
# COİN EKLEME
# ============================================================

st.subheader(
    "➕ Portföye Coin Ekle"
)

st.caption(
    "Aynı anda birden fazla coin ekleyebilirsin. "
    "Her coin için adet ve ortalama maliyet gir."
)


coin_options = (
    df_market["base_asset"]
    .dropna()
    .unique()
    .tolist()
)

coin_options = sorted(
    coin_options
)


with st.form(
    "add_portfolio_coin",
    clear_on_submit=False
):

    c1, c2, c3 = st.columns(3)

    with c1:

        selected_coin = st.selectbox(
            "Coin",
            coin_options
        )

    with c2:

        quantity = st.number_input(
            "Adet",
            min_value=0.0,
            value=0.0,
            step=1.0
        )

    with c3:

        cost = st.number_input(
            "Ortalama Maliyet (₺)",
            min_value=0.0,
            value=0.0,
            step=0.0001,
            format="%.8f"
        )

    add_button = st.form_submit_button(
        "➕ Portföye Ekle",
        use_container_width=True
    )


if add_button:

    if quantity <= 0:

        st.warning(
            "Adet 0'dan büyük olmalıdır."
        )

    elif cost <= 0:

        st.warning(
            "Maliyet 0'dan büyük olmalıdır."
        )

    else:

        # Aynı coin varsa güncelle
        existing = None

        for item in st.session_state.portfolio_rows:

            if item["coin"] == selected_coin:

                existing = item
                break

        if existing:

            old_qty = existing["quantity"]
            old_cost = existing["cost"]

            total_qty = old_qty + quantity

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

            st.success(
                f"{selected_coin} portföyde güncellendi."
            )

        else:

            st.session_state.portfolio_rows.append(
                {
                    "coin": selected_coin,
                    "quantity": quantity,
                    "cost": cost,
                }
            )

            st.success(
                f"{selected_coin} portföye eklendi."
            )


# ============================================================
# PORTFÖY BOŞSA
# ============================================================

if not st.session_state.portfolio_rows:

    st.info(
        "Henüz portföye coin eklenmedi."
    )

    st.stop()


# ============================================================
# PORTFÖY TABLOSU
# ============================================================

portfolio_df = pd.DataFrame(
    st.session_state.portfolio_rows
)


# ============================================================
# PORTFÖY PİYASA VERİSİYLE BİRLEŞTİR
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


portfolio_df["price_try"] = (
    pd.to_numeric(
        portfolio_df["price_try"],
        errors="coerce"
    )
    .fillna(0)
)


portfolio_df["change_24h"] = (
    pd.to_numeric(
        portfolio_df["change_24h"],
        errors="coerce"
    )
    .fillna(0)
)


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

    (
        portfolio_df["profit_loss"]
        /
        portfolio_df["cost_value"]
    ) * 100,

    0
)


# ============================================================
# TOPLAM PORTFÖY
# ============================================================

total_value = portfolio_df[
    "position_value"
].sum()


total_cost = portfolio_df[
    "cost_value"
].sum()


total_profit = (
    total_value
    -
    total_cost
)


total_profit_pct = (
    total_profit / total_cost * 100
    if total_cost > 0
    else 0
)


# ============================================================
# ÜST METRİKLER
# ============================================================

st.divider()

st.subheader(
    "📊 Portföy Özeti"
)


m1, m2, m3, m4 = st.columns(4)


with m1:

    st.metric(
        "Portföy Değeri",
        format_money(total_value)
    )


with m2:

    st.metric(
        "Toplam Maliyet",
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
        "Coin Sayısı",
        len(portfolio_df)
    )


# ============================================================
# TEKNİK PORTFÖY SKORU
# ============================================================

def calculate_portfolio_score(row):

    change = safe_float(
        row["change_24h"]
    )

    # Momentum
    if change >= 20:

        momentum = 100

    elif change >= 15:

        momentum = 95

    elif change >= 10:

        momentum = 88

    elif change >= 7:

        momentum = 82

    elif change >= 3:

        momentum = 72

    elif change >= 0:

        momentum = 62

    elif change >= -5:

        momentum = 48

    elif change >= -10:

        momentum = 35

    else:

        momentum = 20


    # Pozisyon performansı
    pnl = safe_float(
        row["profit_loss_pct"]
    )

    if pnl >= 30:

        performance = 100

    elif pnl >= 20:

        performance = 95

    elif pnl >= 10:

        performance = 85

    elif pnl >= 5:

        performance = 75

    elif pnl >= 0:

        performance = 65

    elif pnl >= -5:

        performance = 50

    elif pnl >= -10:

        performance = 35

    else:

        performance = 20


    # Likidite
    volume = safe_float(
        row["volume_try"]
    )

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

    else:

        liquidity = 50


    score = (
        momentum * 0.45
        +
        performance * 0.30
        +
        liquidity * 0.25
    )

    return clamp(score)


portfolio_df["Güç"] = (
    portfolio_df
    .apply(
        calculate_portfolio_score,
        axis=1
    )
)


# ============================================================
# PORTFÖY AĞIRLIĞI
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

    # Aşırı portföy ağırlığı
    if weight >= 40:

        risk += 35

    elif weight >= 30:

        risk += 25

    elif weight >= 20:

        risk += 15

    elif weight >= 10:

        risk += 5


    # Günlük sert hareket
    if abs(change) >= 20:

        risk += 25

    elif abs(change) >= 15:

        risk += 18

    elif abs(change) >= 10:

        risk += 10


    # Büyük zarar
    if pnl <= -20:

        risk += 35

    elif pnl <= -10:

        risk += 25

    elif pnl <= -5:

        risk += 15


    return clamp(risk)


portfolio_df["Risk"] = (
    portfolio_df
    .apply(
        calculate_risk,
        axis=1
    )
)


# ============================================================
# KARAR MOTORU
# ============================================================

def portfolio_decision(row):

    score = safe_float(
        row["Güç"]
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

    weight = safe_float(
        row["Ağırlık"]
    )


    # --------------------------------------------------------
    # AŞIRI RİSK
    # --------------------------------------------------------

    if risk >= 70:

        return (
            "🔴 AZALT",
            "Portföy veya fiyat riski yüksek."
        )


    # --------------------------------------------------------
    # ÇOK ZAYIF
    # --------------------------------------------------------

    if score < 35:

        return (
            "🔴 SAT",
            "Momentum ve pozisyon gücü zayıf."
        )


    # --------------------------------------------------------
    # ÇOK GÜÇLÜ
    # --------------------------------------------------------

    if (
        score >= 85
        and risk < 35
        and change < 15
    ):

        return (
            "🟢 AL",
            "Güçlü momentum ve kontrollü risk."
        )


    # --------------------------------------------------------
    # GÜÇLÜ
    # --------------------------------------------------------

    if score >= 75:

        return (
            "🟢 TUT / GÜÇLÜ",
            "Trend ve momentum güçlü."
        )


    # --------------------------------------------------------
    # YÜKSEK KÂR + ZAYIFLAMA
    # --------------------------------------------------------

    if (
        pnl >= 25
        and change < 0
    ):

        return (
            "🟡 AZALT",
            "Yüksek kâr mevcut ancak momentum zayıflıyor."
        )


    # --------------------------------------------------------
    # ZARARDA + ZAYIF
    # --------------------------------------------------------

    if (
        pnl <= -15
        and score < 55
    ):

        return (
            "🔴 SAT",
            "Pozisyon zararda ve toparlanma gücü düşük."
        )


    # --------------------------------------------------------
    # NORMAL
    # --------------------------------------------------------

    if score >= 55:

        return (
            "🟡 TUT",
            "Pozisyon izlenebilir seviyede."
        )


    return (
        "⚪ İZLE",
        "Yeni teyit beklenmeli."
    )


decisions = (
    portfolio_df
    .apply(
        portfolio_decision,
        axis=1
    )
)


portfolio_df["Karar"] = (
    decisions
    .apply(
        lambda x: x[0]
    )
)


portfolio_df["Yorum"] = (
    decisions
    .apply(
        lambda x: x[1]
    )
)


# ============================================================
# KARAR ÖZETİ
# ============================================================

st.divider()

st.subheader(
    "🎯 Portföy Karar Merkezi"
)


decision_counts = (
    portfolio_df["Karar"]
    .value_counts()
)


a1, a2, a3, a4, a5 = st.columns(5)


with a1:

    st.metric(
        "🟢 AL",
        int(
            decision_counts.get(
                "🟢 AL",
                0
            )
        )
    )


with a2:

    st.metric(
        "🟢 TUT",
        int(
            decision_counts.get(
                "🟢 TUT / GÜÇLÜ",
                0
            )
        )
    )


with a3:

    st.metric(
        "🟡 AZALT",
        int(
            decision_counts.get(
                "🟡 AZALT",
                0
            )
        )
    )


with a4:

    st.metric(
        "🔴 SAT",
        int(
            decision_counts.get(
                "🔴 SAT",
                0
            )
        )
    )


with a5:

    st.metric(
        "⚪ İZLE",
        int(
            decision_counts.get(
                "⚪ İZLE",
                0
            )
        )
    )


# ============================================================
# ÖNEMLİ UYARILAR
# ============================================================

reduce_df = portfolio_df[
    portfolio_df["Karar"].isin(
        [
            "🟡 AZALT",
            "🔴 SAT"
        ]
    )
]


if not reduce_df.empty:

    st.warning(
        f"{len(reduce_df)} pozisyonda "
        "azaltma veya satış yönünde risk sinyali bulunuyor."
    )


# ============================================================
# COİN KARTLARI
# ============================================================

st.divider()

st.subheader(
    "🪙 Portföy Pozisyonları"
)


for _, row in portfolio_df.iterrows():

    decision = row["Karar"]

    if decision.startswith("🟢"):

        box_type = "success"

    elif decision.startswith("🟡"):

        box_type = "warning"

    elif decision.startswith("🔴"):

        box_type = "error"

    else:

        box_type = "info"


    with st.container(
        border=True
    ):

        c1, c2, c3, c4, c5 = st.columns(5)


        with c1:

            st.markdown(
                f"### {row['coin']}"
            )

            st.markdown(
                f"**{decision}**"
            )


        with c2:

            st.metric(
                "Mevcut Fiyat",
                f"₺{format_price(row['price_try'])}"
            )

            st.metric(
                "Maliyet",
                f"₺{format_price(row['cost'])}"
            )


        with c3:

            st.metric(
                "Adet",
                f"{row['quantity']:,.4f}"
            )

            st.metric(
                "Pozisyon",
                format_money(
                    row["position_value"]
                )
            )


        with c4:

            st.metric(
                "Kâr / Zarar",
                format_money(
                    row["profit_loss"]
                ),
                f"{row['profit_loss_pct']:+.2f}%"
            )

            st.metric(
                "Ağırlık",
                f"{row['Ağırlık']:.1f}%"
            )


        with c5:

            st.metric(
                "Güç",
                f"{row['Güç']:.1f}"
            )

            st.metric(
                "Risk",
                f"{row['Risk']:.1f}"
            )


        if box_type == "success":

            st.success(
                row["Yorum"]
            )

        elif box_type == "warning":

            st.warning(
                row["Yorum"]
            )

        elif box_type == "error":

            st.error(
                row["Yorum"]
            )

        else:

            st.info(
                row["Yorum"]
            )


# ============================================================
# DETAYLI TABLO
# ============================================================

st.divider()

st.subheader(
    "📊 Detaylı Portföy Tablosu"
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
        "change_24h",
        "Karar",
    ]
].copy()


table = table.rename(
    columns={
        "coin": "Coin",
        "quantity": "Adet",
        "cost": "Maliyet",
        "price_try": "Fiyat",
        "position_value": "Pozisyon",
        "profit_loss": "K/Z",
        "profit_loss_pct": "K/Z %",
        "Ağırlık": "Ağırlık %",
        "Güç": "Güç",
        "Risk": "Risk",
        "change_24h": "24s %",
        "Karar": "Karar",
    }
)


st.dataframe(
    table,
    use_container_width=True,
    hide_index=True,
)


# ============================================================
# PORTFÖY RİSK ANALİZİ
# ============================================================

st.divider()

st.subheader(
    "⚠️ Portföy Risk Analizi"
)


risk_col1, risk_col2 = st.columns(2)


with risk_col1:

    highest_weight = (
        portfolio_df
        .sort_values(
            "Ağırlık",
            ascending=False
        )
        .iloc[0]
    )

    st.info(
        f"En yüksek ağırlık: "
        f"**{highest_weight['coin']} "
        f"(%{highest_weight['Ağırlık']:.1f})**"
    )


with risk_col2:

    highest_risk = (
        portfolio_df
        .sort_values(
            "Risk",
            ascending=False
        )
        .iloc[0]
    )

    st.warning(
        f"En yüksek risk: "
        f"**{highest_risk['coin']} "
        f"({highest_risk['Risk']:.1f}/100)**"
    )


# ============================================================
# PORTFÖY YAPISI
# ============================================================

st.divider()

st.subheader(
    "📐 Portföy Dağılımı"
)


allocation = portfolio_df[
    [
        "coin",
        "position_value"
    ]
].copy()


allocation = allocation.sort_values(
    "position_value",
    ascending=False
)


allocation["Ağırlık"] = (
    allocation["position_value"]
    /
    total_value
    *
    100
    if total_value > 0
    else 0
)


st.dataframe(
    allocation.rename(
        columns={
            "coin": "Coin",
            "position_value": "Değer",
            "Ağırlık": "Ağırlık %"
        }
    ),
    use_container_width=True,
    hide_index=True,
)


# ============================================================
# COİN DETAYI
# ============================================================

st.divider()

st.subheader(
    "🔎 Coin Detaylı Karar"
)


selected_coin = st.selectbox(
    "Detayını görmek istediğin coin",
    portfolio_df["coin"].tolist()
)


selected = portfolio_df[
    portfolio_df["coin"]
    ==
    selected_coin
].iloc[0]


st.markdown(
    f"## {selected_coin}"
)


if selected["Karar"].startswith("🟢"):

    st.success(
        selected["Karar"]
    )

elif selected["Karar"].startswith("🟡"):

    st.warning(
        selected["Karar"]
    )

elif selected["Karar"].startswith("🔴"):

    st.error(
        selected["Karar"]
    )

else:

    st.info(
        selected["Karar"]
    )


d1, d2, d3, d4, d5 = st.columns(5)


with d1:

    st.metric(
        "Güç",
        f"{selected['Güç']:.1f}"
    )


with d2:

    st.metric(
        "Risk",
        f"{selected['Risk']:.1f}"
    )


with d3:

    st.metric(
        "K/Z",
        f"{selected['profit_loss_pct']:+.2f}%"
    )


with d4:

    st.metric(
        "24s",
        f"{selected['change_24h']:+.2f}%"
    )


with d5:

    st.metric(
        "Portföy Ağırlığı",
        f"{selected['Ağırlık']:.1f}%"
    )


st.markdown(
    "### 💡 Karar"
)

st.info(
    selected["Yorum"]
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
    key="delete_coin"
)


if st.button(
    "🗑️ Seçili Coini Portföyden Çıkar",
    use_container_width=True
):

    st.session_state.portfolio_rows = [
        item
        for item in st.session_state.portfolio_rows
        if item["coin"] != delete_coin
    ]

    st.success(
        f"{delete_coin} portföyden çıkarıldı."
    )

    st.rerun()


# ============================================================
# TÜM PORTFÖYÜ TEMİZLE
# ============================================================

if st.button(
    "⚠️ Tüm Portföyü Temizle",
    use_container_width=True
):

    st.session_state.portfolio_rows = []

    st.rerun()


# ============================================================
# KARAR MOTORU AÇIKLAMASI
# ============================================================

st.divider()

with st.expander(
    "🧠 Portföy Karar Motoru Nasıl Çalışıyor?"
):

    st.markdown(
        """
### 🟢 AL

Coin güçlüdür ve portföydeki mevcut risk
kontrollü seviyededir.

Yeni alım için aday olabilir.

---

### 🟢 TUT / GÜÇLÜ

Pozisyon güçlüdür.

Mevcut pozisyon korunabilir.

---

### 🟡 TUT

Coin tamamen zayıf değildir ancak
yeni agresif alım için yeterli avantaj yoktur.

---

### 🟡 AZALT

İki temel durumda oluşabilir:

- Portföy ağırlığı fazla
- Kâr yüksek ancak momentum zayıflıyor

Amaç pozisyonun tamamını satmak değil,
riski azaltmaktır.

---

### 🔴 SAT

Coinin teknik/momentum yapısı ciddi şekilde
zayıflamışsa veya zarar ile birlikte güç de
düşmüşse satış yönünde sinyal oluşur.

---

### ⚪ İZLE

Coin için henüz net bir karar oluşmamıştır.

Yeni teyit beklenir.

---

## Önemli

Bu sayfa:

**"Coin yükselir mi?"**

sorusundan çok:

**"Elimdeki coin için şu anda ne yapmalıyım?"**

sorusuna cevap vermek üzere tasarlanmıştır.

Karar motorunda:

- Momentum
- 24 saatlik fiyat hareketi
- Pozisyon kâr/zararı
- Portföy ağırlığı
- Likidite
- Risk

birlikte değerlendirilir.

Bu nedenle başka bir sayfada
**AL** çıkan coin burada otomatik olarak
AL olmak zorunda değildir.

Portföy yönetimi ile yeni trade seçimi
farklı problemlerdir.
"""
    )


# ============================================================
# SON UYARI
# ============================================================

st.divider()

st.caption(
    "⚠️ Bu sayfa yatırım tavsiyesi değildir. "
    "Kararlar teknik ve portföy verilerine dayalı otomatik "
    "karar desteğidir. Gerçek işlem öncesinde piyasa koşulları, "
    "spread, likidite ve emir gerçekleşmesi ayrıca kontrol edilmelidir."
)