import streamlit as st
import pandas as pd
import importlib
import crypto_engine


# ============================================================
# SAYFA
# ============================================================

st.set_page_config(
    page_title="Kripto Piyasa",
    page_icon="₿",
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

st.title("₿ Kripto Piyasa Merkezi")

st.caption(
    "CRYPTO AI PRO | Binance TR Spot | TRY Bazlı Piyasa Analizi"
)

st.write(
    "Binance TR TRY spot piyasaları analiz ediliyor."
)


# ============================================================
# BINANCE TR VERİSİ
# ============================================================

try:

    raw_data = crypto_engine.get_all_try_universe()

except Exception as e:

    st.error(
        "Binance TR bağlantısında hata oluştu."
    )

    st.exception(e)

    st.stop()


# ============================================================
# VERİ TİPİNİ NORMALLEŞTİR
# ============================================================

if raw_data is None:

    st.error(
        "Binance TR veri döndürmedi."
    )

    st.stop()


# ------------------------------------------------------------
# DataFrame geldiyse
# ------------------------------------------------------------

if isinstance(raw_data, pd.DataFrame):

    df = raw_data.copy()


# ------------------------------------------------------------
# Liste geldiyse
# ------------------------------------------------------------

elif isinstance(raw_data, list):

    # Liste boş
    if len(raw_data) == 0:

        st.warning(
            "Binance TR'den TRY pariteleri alınamadı."
        )

        st.stop()

    # Liste dictionary ise
    if isinstance(raw_data[0], dict):

        df = pd.DataFrame(raw_data)

    # Liste string ise
    else:

        df = pd.DataFrame(
            {
                "symbol": raw_data
            }
        )


# ------------------------------------------------------------
# Beklenmeyen veri tipi
# ------------------------------------------------------------

else:

    st.error(
        f"Beklenmeyen veri tipi: {type(raw_data).__name__}"
    )

    st.stop()


# ============================================================
# DATAFRAME KONTROL
# ============================================================

if df.empty:

    st.warning(
        "Binance TR'den TRY pariteleri alınamadı."
    )

    st.stop()


# ============================================================
# KOLON NORMALİZASYONU
# ============================================================

if "symbol" not in df.columns:

    # Binance TR bazen sembol bilgisini farklı isimle döndürebilir

    possible_symbol_columns = [
        "symbol",
        "pair",
        "name",
        "code"
    ]

    found_symbol = None

    for col in possible_symbol_columns:

        if col in df.columns:

            found_symbol = col
            break

    if found_symbol:

        df["symbol"] = df[found_symbol].astype(str)

    else:

        st.error(
            "Binance TR verisinde parite bilgisi bulunamadı."
        )

        st.stop()


# ============================================================
# SYMBOL TEMİZLEME
# ============================================================

df["symbol"] = (
    df["symbol"]
    .astype(str)
    .str.upper()
    .str.strip()
)


# ============================================================
# BASE ASSET
# ============================================================

if "base_asset" not in df.columns:

    df["base_asset"] = (
        df["symbol"]
        .str.replace("_TRY", "", regex=False)
        .str.replace("TRY", "", regex=False)
    )


# ============================================================
# ÜST BİLGİ
# ============================================================

total = len(df)

priced = 0

if "price_try" in df.columns:

    priced = int(
        pd.to_numeric(
            df["price_try"],
            errors="coerce"
        )
        .fillna(0)
        .gt(0)
        .sum()
    )


c1, c2, c3, c4 = st.columns(4)


with c1:

    st.metric(
        "TRY Paritesi",
        total
    )


with c2:

    st.metric(
        "Fiyat Verisi",
        priced
    )


with c3:

    if "change_24h" in df.columns:

        avg_change = (
            pd.to_numeric(
                df["change_24h"],
                errors="coerce"
            )
            .dropna()
        )

        if not avg_change.empty:

            st.metric(
                "Ortalama 24s",
                f"{avg_change.mean():.2f}%"
            )

        else:

            st.metric(
                "Ortalama 24s",
                "-"
            )

    else:

        st.metric(
            "Ortalama 24s",
            "-"
        )


with c4:

    st.metric(
        "API",
        "OK"
    )


st.divider()


# ============================================================
# FİLTRE
# ============================================================

st.subheader(
    "🪙 Binance TR TRY Pariteleri"
)


search = st.text_input(
    "Coin ara",
    placeholder="BTC, ETH, SOL..."
)


view = df.copy()


if search:

    search = search.upper().strip()

    view = view[
        view["symbol"]
        .astype(str)
        .str.upper()
        .str.contains(
            search,
            na=False
        )
    ].copy()


# ============================================================
# KOLONLAR
# ============================================================

columns = [
    "symbol",
    "base_asset",
    "price_try",
    "change_24h",
    "volume_try",
    "high_24h",
    "low_24h",
]


available = [
    col
    for col in columns
    if col in view.columns
]


display = view[available].copy()


# ============================================================
# FORMAT - FİYAT
# ============================================================

if "price_try" in display.columns:

    numeric_price = pd.to_numeric(
        display["price_try"],
        errors="coerce"
    )

    display["price_try"] = numeric_price.map(
        lambda x:
        (
            f"{x:,.8f}"
            if pd.notna(x) and x < 1
            else f"{x:,.2f}"
            if pd.notna(x)
            else "-"
        )
    )


# ============================================================
# FORMAT - DEĞİŞİM
# ============================================================

if "change_24h" in display.columns:

    display["change_24h"] = (
        pd.to_numeric(
            display["change_24h"],
            errors="coerce"
        )
        .map(
            lambda x:
            f"{x:+.2f}%"
            if pd.notna(x)
            else "-"
        )
    )


# ============================================================
# FORMAT - HACİM
# ============================================================

if "volume_try" in display.columns:

    display["volume_try"] = (
        pd.to_numeric(
            display["volume_try"],
            errors="coerce"
        )
        .map(
            lambda x:
            f"₺{x:,.0f}"
            if pd.notna(x)
            else "-"
        )
    )


# ============================================================
# FORMAT - YÜKSEK
# ============================================================

if "high_24h" in display.columns:

    display["high_24h"] = (
        pd.to_numeric(
            display["high_24h"],
            errors="coerce"
        )
        .map(
            lambda x:
            (
                f"{x:,.8f}"
                if pd.notna(x) and x < 1
                else f"{x:,.2f}"
                if pd.notna(x)
                else "-"
            )
        )
    )


# ============================================================
# FORMAT - DÜŞÜK
# ============================================================

if "low_24h" in display.columns:

    display["low_24h"] = (
        pd.to_numeric(
            display["low_24h"],
            errors="coerce"
        )
        .map(
            lambda x:
            (
                f"{x:,.8f}"
                if pd.notna(x) and x < 1
                else f"{x:,.2f}"
                if pd.notna(x)
                else "-"
            )
        )
    )


# ============================================================
# İSİMLER
# ============================================================

rename = {

    "symbol": "Parite",

    "base_asset": "Coin",

    "price_try": "Fiyat ₺",

    "change_24h": "24s %",

    "volume_try": "24s TRY Hacim",

    "high_24h": "24s Yüksek",

    "low_24h": "24s Düşük",

}


display = display.rename(
    columns=rename
)


# ============================================================
# TABLO
# ============================================================

st.dataframe(
    display,
    use_container_width=True,
    hide_index=True,
    height=650,
)


# ============================================================
# ALT BİLGİ
# ============================================================

st.caption(
    f"{len(view)} parite gösteriliyor."
)