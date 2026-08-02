import sqlite3
import pandas as pd
import streamlit as st
from pathlib import Path
import yfinance as yf

from modules.data.yahoo_data import get_stock_analysis


# ==========================================================
# SAYFA AYARLARI
# ==========================================================

st.set_page_config(
    page_title="Portföy",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Portföy")


# ==========================================================
# VERİTABANI
# ==========================================================

DB_PATH = "borsa.db"


def get_connection():
    return sqlite3.connect(DB_PATH)


# ==========================================================
# İŞLEMLERİ OKU
# ==========================================================

def load_transactions():

    try:

        conn = get_connection()

        df = pd.read_sql_query(
            """
            SELECT *
            FROM transactions
            ORDER BY id ASC
            """,
            conn
        )

        conn.close()

        return df

    except Exception as e:

        st.error(f"İşlemler okunamadı: {e}")

        return pd.DataFrame()


# ==========================================================
# İŞLEM TÜRÜ NORMALİZASYONU
# ==========================================================

def normalize_transaction_type(value):

    if value is None:
        return ""

    text = str(value).strip().lower()

    text = text.replace("ı", "i")
    text = text.replace("ş", "s")
    text = text.replace("ğ", "g")
    text = text.replace("ü", "u")
    text = text.replace("ö", "o")
    text = text.replace("ç", "c")

    if text in [
        "alis",
        "al",
        "buy",
        "b",
        "alma"
    ]:
        return "ALIS"

    if text in [
        "satis",
        "sat",
        "sell",
        "s",
        "satma"
    ]:
        return "SATIS"

    return text.upper()



def calculate_positions(transactions):

    if transactions.empty:
        return pd.DataFrame()

    required_columns = [
        "symbol",
        "transaction_type",
        "quantity",
        "price"
    ]

    missing = [
        col
        for col in required_columns
        if col not in transactions.columns
    ]

    if missing:
        st.error(
            "transactions tablosunda eksik sütunlar: "
            + ", ".join(missing)
        )
        return pd.DataFrame()

    df = transactions.copy()

    # ---------------------------------------------
    # SAYISAL ALANLAR
    # ---------------------------------------------

    df["quantity"] = pd.to_numeric(
        df["quantity"],
        errors="coerce"
    ).fillna(0)

    df["price"] = pd.to_numeric(
        df["price"],
        errors="coerce"
    ).fillna(0)

    # ---------------------------------------------
    # SEMBOL
    # ---------------------------------------------

    df["symbol"] = (
        df["symbol"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    # ---------------------------------------------
    # İŞLEM TÜRÜ
    # ---------------------------------------------

    df["transaction_type_normalized"] = (
        df["transaction_type"]
        .apply(normalize_transaction_type)
    )

    positions = []

    # ---------------------------------------------
    # HER HİSSEYİ AYRI HESAPLA
    # ---------------------------------------------

    for symbol, group in df.groupby("symbol"):

        group = group.copy()

        # ÖNEMLİ:
        # TARİHE BAKMIYORUZ.
        # VERİTABANINDAKİ ID SIRASI ESAS.
        if "id" in group.columns:

            group = group.sort_values(
                by="id",
                ascending=True
            )

        total_buy_quantity = 0.0
        total_buy_cost = 0.0
        total_sell_quantity = 0.0

        # -----------------------------------------
        # İŞLEMLERİ TEK TEK UYGULA
        # -----------------------------------------

        for _, row in group.iterrows():

            transaction_type = (
                row["transaction_type_normalized"]
            )

            quantity = float(
                row["quantity"]
            )

            price = float(
                row["price"]
            )

            # ALIŞ
            if transaction_type == "ALIS":

                total_buy_quantity += quantity

                total_buy_cost += (
                    quantity * price
                )

            # SATIŞ
            elif transaction_type == "SATIS":

                total_sell_quantity += quantity

        # -----------------------------------------
        # NET ADET
        # -----------------------------------------

        remaining_quantity = (
            total_buy_quantity
            - total_sell_quantity
        )

        # Pozisyon kapandıysa gösterme
        if remaining_quantity <= 0:
            continue

        # -----------------------------------------
        # ORTALAMA MALİYET
        # -----------------------------------------

        if total_buy_quantity > 0:

            average_cost = (
                total_buy_cost
                / total_buy_quantity
            )

        else:

            average_cost = 0.0

        # -----------------------------------------
        # TOPLAM MALİYET
        # -----------------------------------------

        total_cost = (
            remaining_quantity
            * average_cost
        )

        positions.append(
            {
                "symbol": symbol,
                "quantity": remaining_quantity,
                "average_cost": average_cost,
                "total_cost": total_cost
            }
        )

    return pd.DataFrame(positions)

    df = transactions.copy()

    # ------------------------------------------------------
    # SAYISAL ALANLAR
    # ------------------------------------------------------

    df["quantity"] = pd.to_numeric(
        df["quantity"],
        errors="coerce"
    ).fillna(0)

    df["price"] = pd.to_numeric(
        df["price"],
        errors="coerce"
    ).fillna(0)

    # ------------------------------------------------------
    # İŞLEM TÜRÜ
    # ------------------------------------------------------

    df["transaction_type_normalized"] = (
        df["transaction_type"]
        .apply(normalize_transaction_type)
    )

    # ------------------------------------------------------
    # SEMBOL TEMİZLE
    # ------------------------------------------------------

    df["symbol"] = (
        df["symbol"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    # ------------------------------------------------------
    # POZİSYONLAR
    # ------------------------------------------------------

    positions = []

    for symbol, group in df.groupby("symbol"):

        group = group.copy()

        # --------------------------------------------------
        # KRİTİK:
        # İşlemleri tarih + id sırasına koy
        # --------------------------------------------------

        if "id" in group.columns:

            group = group.sort_values(
                by=["transaction_date", "id"]
            )

        else:

            group = group.sort_values(
                by=["transaction_date"]
            )

        total_buy_quantity = 0.0
        total_buy_cost = 0.0
        total_sell_quantity = 0.0

        # --------------------------------------------------
        # İŞLEMLERİ TEK TEK İŞLE
        # --------------------------------------------------

        for _, row in group.iterrows():

            transaction_type = (
                row["transaction_type_normalized"]
            )

            quantity = float(
                row["quantity"]
            )

            price = float(
                row["price"]
            )

            # ----------------------------------------------
            # ALIŞ
            # ----------------------------------------------

            if transaction_type == "ALIS":

                total_buy_quantity += quantity

                total_buy_cost += (
                    quantity * price
                )

            # ----------------------------------------------
            # SATIŞ
            # ----------------------------------------------

            elif transaction_type == "SATIS":

                total_sell_quantity += quantity

        # --------------------------------------------------
        # NET ADET
        # --------------------------------------------------

        remaining_quantity = (
            total_buy_quantity
            - total_sell_quantity
        )

        # Tamamen kapanmış pozisyon
        if remaining_quantity <= 0:
            continue

        # --------------------------------------------------
        # ORTALAMA MALİYET
        # --------------------------------------------------

        if total_buy_quantity > 0:

            average_cost = (
                total_buy_cost
                / total_buy_quantity
            )

        else:

            average_cost = 0.0

        # --------------------------------------------------
        # TOPLAM MALİYET
        # --------------------------------------------------

        total_cost = (
            remaining_quantity
            * average_cost
        )

        positions.append(
            {
                "symbol": symbol,
                "quantity": remaining_quantity,
                "average_cost": average_cost,
                "total_cost": total_cost
            }
        )

    return pd.DataFrame(positions)
    df = transactions.copy()

    df["quantity"] = pd.to_numeric(
        df["quantity"],
        errors="coerce"
    ).fillna(0)

    df["price"] = pd.to_numeric(
        df["price"],
        errors="coerce"
    ).fillna(0)

    df["transaction_type_normalized"] = (
        df["transaction_type"]
        .apply(normalize_transaction_type)
    )

    positions = []

    for symbol, group in df.groupby("symbol"):

        group = group.copy()

        group = group.sort_values(
            by="id"
        )

        total_buy_quantity = 0.0
        total_buy_cost = 0.0
        total_sell_quantity = 0.0

        for _, row in group.iterrows():

            transaction_type = (
                row["transaction_type_normalized"]
            )

            quantity = float(
                row["quantity"]
            )

            price = float(
                row["price"]
            )

            if transaction_type == "ALIS":

                total_buy_quantity += quantity

                total_buy_cost += (
                    quantity * price
                )

            elif transaction_type == "SATIS":

                total_sell_quantity += quantity

        remaining_quantity = (
            total_buy_quantity
            - total_sell_quantity
        )

        if remaining_quantity <= 0:
            continue

        average_cost = 0

        if total_buy_quantity > 0:

            average_cost = (
                total_buy_cost
                / total_buy_quantity
            )

        positions.append(
            {
                "symbol": symbol,
                "quantity": remaining_quantity,
                "average_cost": average_cost,
                "total_cost": (
                    remaining_quantity
                    * average_cost
                )
            }
        )

    return pd.DataFrame(positions)


# ==========================================================
# GÜNCEL FİYATLARI AL
# ==========================================================

def get_current_price(symbol):

    try:

        analysis = get_stock_analysis(
            symbol
        )

        if analysis is None:
            return None

        price = analysis.get(
            "price"
        )

        if price is None:
            return None

        return float(price)

    except Exception as e:

        print(
            f"Portföy fiyat hatası "
            f"{symbol}: {e}"
        )

        return None


# ==========================================================
# PORTFÖY TABLOSUNU OLUŞTUR
# ==========================================================

def build_portfolio():

    transactions = load_transactions()

    if transactions.empty:
        return pd.DataFrame()

    positions = calculate_positions(
        transactions
    )

    if positions.empty:
        return pd.DataFrame()

    portfolio = []

    for _, row in positions.iterrows():

        symbol = row["symbol"]

        quantity = float(
            row["quantity"]
        )

        average_cost = float(
            row["average_cost"]
        )

        total_cost = float(
            row["total_cost"]
        )

        current_price = get_current_price(
            symbol
        )

        if current_price is not None:

            market_value = (
                quantity
                * current_price
            )

            profit_loss = (
                market_value
                - total_cost
            )

            if total_cost != 0:

                profit_loss_pct = (
                    profit_loss
                    / total_cost
                ) * 100

            else:

                profit_loss_pct = 0

        else:

            market_value = None
            profit_loss = None
            profit_loss_pct = None

        portfolio.append(
            {
                "Hisse": symbol.replace(
                    ".IS",
                    ""
                ),
                "Adet": quantity,
                "Ortalama Maliyet": average_cost,
                "Güncel Fiyat": current_price,
                "Toplam Maliyet": total_cost,
                "Piyasa Değeri": market_value,
                "K/Z": profit_loss,
                "K/Z %": profit_loss_pct
            }
        )

    return pd.DataFrame(
        portfolio
    )


# ==========================================================
# ==========================================================
# VADeye GÖRE HİSSE DEĞERLENDİRMESİ
# ==========================================================
# 1 HAFTA  = kısa vade
# 1 AY      = orta vade
# 6 AY      = uzun vade
# ==========================================================


@st.cache_data(ttl=900)
def get_vade_data(symbol):

    try:

        ticker = symbol

        if not ticker.endswith(".IS"):
            ticker = ticker + ".IS"

        df = yf.download(
            ticker,
            period="1y",
            interval="1d",
            auto_adjust=True,
            progress=False
        )

        if df is None or df.empty:
            return None

        # yfinance bazı durumlarda MultiIndex döndürebiliyor
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

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
            subset=["Close"]
        )

        if len(df) < 30:
            return None

        # ==================================================
        # TEKNİK GÖSTERGELER
        # ==================================================

        df["EMA20"] = (
            df["Close"]
            .ewm(span=20, adjust=False)
            .mean()
        )

        df["EMA50"] = (
            df["Close"]
            .ewm(span=50, adjust=False)
            .mean()
        )

        df["EMA100"] = (
            df["Close"]
            .ewm(span=100, adjust=False)
            .mean()
        )

        # RSI
        delta = df["Close"].diff()

        gain = delta.clip(
            lower=0
        )

        loss = -delta.clip(
            upper=0
        )

        avg_gain = (
            gain
            .rolling(14)
            .mean()
        )

        avg_loss = (
            loss
            .rolling(14)
            .mean()
        )

        rs = (
            avg_gain
            / avg_loss.replace(0, pd.NA)
        )

        df["RSI"] = (
            100
            - (
                100
                / (1 + rs)
            )
        )

        # MACD
        ema12 = (
            df["Close"]
            .ewm(
                span=12,
                adjust=False
            )
            .mean()
        )

        ema26 = (
            df["Close"]
            .ewm(
                span=26,
                adjust=False
            )
            .mean()
        )

        df["MACD"] = (
            ema12 - ema26
        )

        df["MACD_SIGNAL"] = (
            df["MACD"]
            .ewm(
                span=9,
                adjust=False
            )
            .mean()
        )

        # Hacim ortalaması
        df["Volume20"] = (
            df["Volume"]
            .rolling(20)
            .mean()
        )

        latest = df.iloc[-1]

        current = float(
            latest["Close"]
        )

        rsi = float(
            latest["RSI"]
        ) if pd.notna(
            latest["RSI"]
        ) else 50

        macd = float(
            latest["MACD"]
        )

        macd_signal = float(
            latest["MACD_SIGNAL"]
        )

        ema20 = float(
            latest["EMA20"]
        )

        ema50 = float(
            latest["EMA50"]
        )

        ema100 = float(
            latest["EMA100"]
        )

        volume_ratio = 1.0

        if (
            pd.notna(latest["Volume"])
            and pd.notna(latest["Volume20"])
            and latest["Volume20"] != 0
        ):

            volume_ratio = (
                float(latest["Volume"])
                / float(latest["Volume20"])
            )

        # ==================================================
        # GETİRİLER
        # ==================================================

        def get_return(days):

            if len(df) <= days:
                return 0

            old_price = float(
                df["Close"].iloc[-days - 1]
            )

            if old_price == 0:
                return 0

            return (
                (current / old_price) - 1
            ) * 100

        return_5 = get_return(5)
        return_21 = get_return(21)
        return_63 = get_return(63)
        return_126 = get_return(126)

        # ==================================================
        # SKORLAMA FONKSİYONLARI
        # ==================================================

        def clamp(value):

            return max(
                0,
                min(
                    100,
                    value
                )
            )

        # RSI skoru
        def rsi_score():

            if 50 <= rsi <= 65:
                return 100

            if 45 <= rsi < 50:
                return 75

            if 65 < rsi <= 70:
                return 80

            if 35 <= rsi < 45:
                return 55

            if 70 < rsi <= 75:
                return 60

            if rsi < 35:
                return 40

            return 35

        rsi_s = rsi_score()

        # MACD skoru
        if macd > macd_signal and macd > 0:
            macd_s = 100

        elif macd > macd_signal:
            macd_s = 75

        elif macd < macd_signal and macd < 0:
            macd_s = 25

        else:
            macd_s = 50

        # Trend skorları
        ema20_s = (
            100 if current > ema20
            else 30
        )

        ema50_s = (
            100 if current > ema50
            else 30
        )

        ema100_s = (
            100 if current > ema100
            else 30
        )

        # Hacim
        if volume_ratio >= 1.50:
            volume_s = 100

        elif volume_ratio >= 1.20:
            volume_s = 85

        elif volume_ratio >= 1.00:
            volume_s = 70

        elif volume_ratio >= 0.80:
            volume_s = 50

        else:
            volume_s = 35

        # Momentum skorları
        def momentum_score(return_value):

            if return_value >= 15:
                return 100

            elif return_value >= 10:
                return 90

            elif return_value >= 5:
                return 80

            elif return_value >= 2:
                return 70

            elif return_value >= 0:
                return 60

            elif return_value >= -3:
                return 45

            elif return_value >= -7:
                return 30

            else:
                return 15

        momentum_5_s = momentum_score(
            return_5
        )

        momentum_21_s = momentum_score(
            return_21
        )

        momentum_63_s = momentum_score(
            return_63
        )

        momentum_126_s = momentum_score(
            return_126
        )

        # ==================================================
        # 1 HAFTA SKORU
        # ==================================================

        score_1w = (
            momentum_5_s * 0.35
            + rsi_s * 0.20
            + macd_s * 0.20
            + ema20_s * 0.15
            + volume_s * 0.10
        )

        score_1w = round(
            clamp(score_1w)
        )

        # ==================================================
        # 1 AY SKORU
        # ==================================================

        score_1m = (
            momentum_21_s * 0.30
            + ema20_s * 0.20
            + ema50_s * 0.20
            + macd_s * 0.15
            + rsi_s * 0.15
        )

        score_1m = round(
            clamp(score_1m)
        )

        # ==================================================
        # 6 AY SKORU
        # ==================================================

        score_6m = (
            momentum_126_s * 0.30
            + momentum_63_s * 0.15
            + ema50_s * 0.20
            + ema100_s * 0.20
            + rsi_s * 0.15
        )

        score_6m = round(
            clamp(score_6m)
        )

        return {
            "1 Hafta": score_1w,
            "1 Ay": score_1m,
            "6 Ay": score_6m,
            "5 Gün %": return_5,
            "1 Ay %": return_21,
            "3 Ay %": return_63,
            "6 Ay %": return_126
        }

    except Exception as e:

        print(
            f"Vade analiz hatası "
            f"{symbol}: {e}"
        )

        return None


# ==========================================================
# KARAR ÜRET
# ==========================================================

def vade_karari(score):

    if score is None:
        return "VERİ YOK"

    if score >= 80:
        return "🟢 GÜÇLÜ"

    elif score >= 70:
        return "🟢 POZİTİF"

    elif score >= 60:
        return "🟡 İZLE"

    elif score >= 45:
        return "🟠 ZAYIF"

    else:
        return "🔴 RİSKLİ"


# ==========================================================
# VERİLERİ HAZIRLA
# ==========================================================

portfolio = build_portfolio()


# ==========================================================
# AÇIK POZİSYON YOK
# ==========================================================

if portfolio.empty:

    st.warning(
        "Açık pozisyon bulunamadı."
    )

    st.stop()


# ==========================================================
# TOPLAM HESAPLAR
# ==========================================================

total_cost = (
    portfolio["Toplam Maliyet"]
    .sum()
)


market_values = portfolio[
    "Piyasa Değeri"
].dropna()


total_market_value = (
    market_values.sum()
)


total_profit_loss = (
    total_market_value
    - total_cost
)


if total_cost != 0:

    total_profit_loss_pct = (
        total_profit_loss
        / total_cost
    ) * 100

else:

    total_profit_loss_pct = 0


# ==========================================================
# PORTFÖY ÖZETİ
# ==========================================================

st.subheader(
    "📌 Portföy Özeti"
)

col1, col2, col3, col4 = st.columns(4)


with col1:

    st.metric(
        "Toplam Maliyet",
        f"{total_cost:,.2f} TL"
    )


with col2:

    st.metric(
        "Portföy Değeri",
        f"{total_market_value:,.2f} TL"
    )


with col3:

    st.metric(
        "Toplam K/Z",
        f"{total_profit_loss:,.2f} TL"
    )


with col4:

    st.metric(
        "Toplam K/Z %",
        f"%{total_profit_loss_pct:.2f}"
    )


st.divider()


# ==========================================================
# PORTFÖY TABLOSU
# ==========================================================

st.subheader(
    "📊 Açık Pozisyonlar"
)


display_df = portfolio.copy()


display_df["Adet"] = (
    display_df["Adet"]
    .round(2)
)


display_df["Ortalama Maliyet"] = (
    display_df["Ortalama Maliyet"]
    .round(2)
)


display_df["Güncel Fiyat"] = (
    display_df["Güncel Fiyat"]
    .round(2)
)


display_df["Toplam Maliyet"] = (
    display_df["Toplam Maliyet"]
    .round(2)
)


display_df["Piyasa Değeri"] = (
    display_df["Piyasa Değeri"]
    .round(2)
)


display_df["K/Z"] = (
    display_df["K/Z"]
    .round(2)
)


display_df["K/Z %"] = (
    display_df["K/Z %"]
    .round(2)
)


st.dataframe(
    display_df,
    width="stretch",
    hide_index=True
)


# ==========================================================
# ==========================================================
# VADE BAZLI PORTFÖY ANALİZİ
# ==========================================================
# ==========================================================

st.divider()

st.subheader(
    "🎯 Vade Bazlı Hisse Değerlendirmesi"
)

st.caption(
    "Kısa vade: 1 hafta  |  "
    "Orta vade: 1 ay  |  "
    "Uzun vade: 6 ay"
)


# ==========================================================
# VADE SEÇİMİ
# ==========================================================

vade = st.radio(
    "Değerlendirme vadesi",
    [
        "🟢 1 Hafta",
        "🔵 1 Ay",
        "🟣 6 Ay"
    ],
    horizontal=True
)


if "1 Hafta" in vade:
    selected_period = "1 Hafta"

elif "1 Ay" in vade:
    selected_period = "1 Ay"

else:
    selected_period = "6 Ay"


# ==========================================================
# VADE SKORLARINI HESAPLA
# ==========================================================

vade_results = []

for _, row in portfolio.iterrows():

    symbol = row["Hisse"]

    result = get_vade_data(
        symbol
    )

    if result is None:

        vade_results.append(
            {
                "Hisse": symbol,
                "1 Hafta": None,
                "1 Ay": None,
                "6 Ay": None,
                "Karar": "VERİ YOK"
            }
        )

    else:

        selected_score = result[
            selected_period
        ]

        vade_results.append(
            {
                "Hisse": symbol,
                "1 Hafta": result["1 Hafta"],
                "1 Ay": result["1 Ay"],
                "6 Ay": result["6 Ay"],
                "Karar": vade_karari(
                    selected_score
                )
            }
        )


vade_df = pd.DataFrame(
    vade_results
)


# ==========================================================
# SEÇİLEN VADE ÖZETİ
# ==========================================================

st.markdown(
    f"### {vade} Görünümü"
)


selected_scores = vade_df[
    selected_period
].dropna()


if not selected_scores.empty:

    average_score = (
        selected_scores.mean()
    )

    strong_count = (
        selected_scores >= 70
    ).sum()

    weak_count = (
        selected_scores < 50
    ).sum()

    c1, c2, c3 = st.columns(3)

    with c1:

        st.metric(
            "Portföy Vade Skoru",
            f"{average_score:.0f}/100"
        )

    with c2:

        st.metric(
            "Pozitif Hisseler",
            f"{strong_count} adet"
        )

    with c3:

        st.metric(
            "Zayıf Hisseler",
            f"{weak_count} adet"
        )


# ==========================================================
# VADE TABLOSU
# ==========================================================

display_vade = vade_df.copy()


for column in [
    "1 Hafta",
    "1 Ay",
    "6 Ay"
]:

    display_vade[column] = (
        display_vade[column]
        .apply(
            lambda x:
            f"{int(x)}/100"
            if pd.notna(x)
            else "-"
        )
    )


st.dataframe(
    display_vade,
    width="stretch",
    hide_index=True
)


# ==========================================================
# SEÇİLEN VADEYE GÖRE SIRALAMA
# ==========================================================

ranking_df = vade_df.copy()

ranking_df = ranking_df.dropna(
    subset=[selected_period]
)

ranking_df = ranking_df.sort_values(
    by=selected_period,
    ascending=False
)


st.markdown(
    f"### 🏆 {vade} En Güçlü Hisseler"
)


if not ranking_df.empty:

    ranking_display = ranking_df[
        [
            "Hisse",
            selected_period,
            "Karar"
        ]
    ].copy()

    ranking_display[selected_period] = (
        ranking_display[selected_period]
        .apply(
            lambda x:
            f"{int(x)}/100"
        )
    )

    st.dataframe(
        ranking_display,
        width="stretch",
        hide_index=True
    )


# ==========================================================
# PORTFÖY DAĞILIMI
# ==========================================================

st.divider()

st.subheader(
    "📈 Portföy Dağılımı"
)


distribution = portfolio[
    [
        "Hisse",
        "Piyasa Değeri"
    ]
].copy()


distribution = distribution.dropna(
    subset=["Piyasa Değeri"]
)


if not distribution.empty:

    distribution = distribution.set_index(
        "Hisse"
    )

    st.bar_chart(
        distribution[
            "Piyasa Değeri"
        ],
        width="stretch"
    )

transactions = load_transactions()

if not transactions.empty:

    transaction_display = transactions[
        pd.to_numeric(
            transactions["quantity"],
            errors="coerce"
        ).fillna(0) > 0
    ].copy()

    st.dataframe(
        transaction_display[
            [
                "id",
                "symbol",
                "transaction_date",
                "transaction_type",
                "quantity",
                "price"
            ]
        ],
        width="stretch",
        hide_index=True
    )

else:

    st.info("İşlem kaydı bulunamadı.")
st.divider()

st.subheader("🔎 İşlem Kontrolü")

transactions = load_transactions()

kontrol = (
    transactions
    .assign(
        quantity=pd.to_numeric(
            transactions["quantity"],
            errors="coerce"
        ).fillna(0)
    )
    .assign(
        is_buy=transactions["transaction_type"]
        .apply(normalize_transaction_type)
        .eq("ALIS")
    )
)

kontrol["Alış Adedi"] = kontrol["quantity"].where(
    kontrol["is_buy"], 0
)

kontrol["Satış Adedi"] = kontrol["quantity"].where(
    ~kontrol["is_buy"], 0
)

ozet = (
    kontrol
    .groupby("symbol")
    .agg(
        Alış=("Alış Adedi", "sum"),
        Satış=("Satış Adedi", "sum")
    )
    .reset_index()
)

ozet["Net Adet"] = (
    ozet["Alış"] - ozet["Satış"]
)

st.dataframe(
    ozet,
    width="stretch",
    hide_index=True
)
# ==========================================================
# ASTOR HAM İŞLEM KONTROLÜ
# ==========================================================

st.divider()

st.subheader("🔬 ASTOR Ham İşlem Kontrolü")

astor = transactions[
    transactions["symbol"]
    .astype(str)
    .str.strip()
    .str.upper()
    .str.replace(".IS", "", regex=False)
    .eq("ASTOR")
].copy()

astor["quantity"] = pd.to_numeric(
    astor["quantity"],
    errors="coerce"
).fillna(0)

astor["Tip_Normalize"] = (
    astor["transaction_type"]
    .apply(normalize_transaction_type)
)

st.dataframe(
    astor[
        [
            "id",
            "symbol",
            "transaction_date",
            "transaction_type",
            "Tip_Normalize",
            "quantity",
            "price"
        ]
    ],
    width="stretch",
    hide_index=True
)

astor_alis = astor.loc[
    astor["Tip_Normalize"] == "ALIS",
    "quantity"
].sum()

astor_satis = astor.loc[
    astor["Tip_Normalize"] == "SATIS",
    "quantity"
].sum()

astor_net = (
    astor_alis
    - astor_satis
)

st.write(
    f"🟢 ASTOR Toplam Alış: **{astor_alis:.0f} lot**"
)

st.write(
    f"🔴 ASTOR Toplam Satış: **{astor_satis:.0f} lot**"
)

st.write(
    f"🟡 ASTOR NET: **{astor_net:.0f} lot**"
)
# ==========================================================
# ASTOR KÜMÜLATİF ADET KONTROLÜ
# ==========================================================

st.divider()

st.subheader("🔍 ASTOR Kümülatif Adet Kontrolü")

astor_kontrol = astor.copy()

astor_kontrol["Net Etki"] = 0.0

astor_kontrol.loc[
    astor_kontrol["Tip_Normalize"] == "ALIS",
    "Net Etki"
] = astor_kontrol["quantity"]

astor_kontrol.loc[
    astor_kontrol["Tip_Normalize"] == "SATIS",
    "Net Etki"
] = -astor_kontrol["quantity"]

astor_kontrol["Kümülatif Adet"] = (
    astor_kontrol["Net Etki"].cumsum()
)

st.dataframe(
    astor_kontrol[
        [
            "id",
            "transaction_date",
            "transaction_type",
            "Tip_Normalize",
            "quantity",
            "price",
            "Net Etki",
            "Kümülatif Adet"
        ]
    ],
    width="stretch",
    hide_index=True
)

st.metric(
    "ASTOR Son Kümülatif Adet",
    f"{astor_kontrol['Kümülatif Adet'].iloc[-1]:.0f} lot"
)