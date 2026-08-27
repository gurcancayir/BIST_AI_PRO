# ============================================================
# BIST AI PRO
# 09_Portfoy_PRO.py
#
# KALICI BIST PORTFÖY YÖNETİM MERKEZİ
#
# ÖZELLİKLER
# ------------------------------------------------------------
# - Portföy kalıcı olarak SQLite'a kaydedilir
# - Sayfa yenilenince portföy kaybolmaz
# - Aynı anda birden fazla hisse eklenebilir
# - Adet + ortalama maliyet tutulur
# - Güncel fiyat otomatik alınır
# - K/Z hesaplanır
# - Portföy ağırlığı hesaplanır
# - Teknik güç
# - Momentum
# - Risk
# - Kısa Vade kararı
# - Orta Vade kararı
# - Uzun Vade kararı
# - Final portföy kararı
#
# KARARLAR
# ------------------------------------------------------------
# 🟢 AL
# 🟢 GÜÇLÜ TUT
# 🟢 TUT
# 🟡 BEKLE
# 🟡 AZALT
# 🔴 SAT
#
# VERİ
# ------------------------------------------------------------
# Yahoo Finance / yfinance
#
# PORTFÖY VERİTABANI
# ------------------------------------------------------------
# borsa_portfoy_pro.db
#
# ============================================================


import streamlit as st
import pandas as pd
import numpy as np
import sqlite3
import yfinance as yf
import importlib
from datetime import datetime


# ============================================================
# SAYFA AYARLARI
# ============================================================

st.set_page_config(
    page_title="BIST Portföy PRO",
    page_icon="💼",
    layout="wide",
)


# ============================================================
# BAŞLIK
# ============================================================

st.title("💼 BIST AI PRO — Portföy Yönetim PRO")

st.caption(
    "Kalıcı portföy | Kısa Vade | Orta Vade | Uzun Vade | "
    "Risk | Teknik Güç | Otomatik Karar"
)


# ============================================================
# AYARLAR
# ============================================================

DB_FILE = "bist_portfoy_pro.db"


# ============================================================
# DATABASE
# ============================================================

def get_connection():

    conn = sqlite3.connect(
        DB_FILE,
        check_same_thread=False
    )

    return conn


def init_database():

    conn = get_connection()

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS portfolio (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT UNIQUE NOT NULL,
            quantity REAL NOT NULL,
            avg_cost REAL NOT NULL,
            created_at TEXT,
            updated_at TEXT
        )
        """
    )

    conn.commit()
    conn.close()


init_database()


# ============================================================
# DATABASE - PORTFÖYÜ OKU
# ============================================================

def load_portfolio():

    conn = get_connection()

    df = pd.read_sql_query(
        """
        SELECT
            id,
            symbol,
            quantity,
            avg_cost,
            created_at,
            updated_at
        FROM portfolio
        ORDER BY symbol
        """,
        conn
    )

    conn.close()

    return df


# ============================================================
# DATABASE - COİN/HİSSE EKLE
# ============================================================

def add_position(
    symbol,
    quantity,
    avg_cost
):

    symbol = (
        symbol
        .upper()
        .strip()
        .replace(".IS", "")
    )

    now = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    conn = get_connection()

    existing = conn.execute(
        """
        SELECT quantity, avg_cost
        FROM portfolio
        WHERE symbol = ?
        """,
        (symbol,)
    ).fetchone()

    if existing:

        old_qty = float(
            existing[0]
        )

        old_cost = float(
            existing[1]
        )

        new_qty = (
            old_qty
            +
            quantity
        )

        if new_qty > 0:

            weighted_cost = (
                old_qty * old_cost
                +
                quantity * avg_cost
            ) / new_qty

        else:

            weighted_cost = avg_cost

        conn.execute(
            """
            UPDATE portfolio
            SET
                quantity = ?,
                avg_cost = ?,
                updated_at = ?
            WHERE symbol = ?
            """,
            (
                new_qty,
                weighted_cost,
                now,
                symbol
            )
        )

    else:

        conn.execute(
            """
            INSERT INTO portfolio
            (
                symbol,
                quantity,
                avg_cost,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                symbol,
                quantity,
                avg_cost,
                now,
                now
            )
        )

    conn.commit()
    conn.close()


# ============================================================
# DATABASE - SİL
# ============================================================

def delete_position(symbol):

    conn = get_connection()

    conn.execute(
        """
        DELETE FROM portfolio
        WHERE symbol = ?
        """,
        (symbol,)
    )

    conn.commit()
    conn.close()


# ============================================================
# DATABASE - TÜMÜNÜ SİL
# ============================================================

def delete_all_positions():

    conn = get_connection()

    conn.execute(
        "DELETE FROM portfolio"
    )

    conn.commit()
    conn.close()


# ============================================================
# YARDIMCI FONKSİYONLAR
# ============================================================

def safe_float(
    value,
    default=0.0
):

    try:

        if value is None:
            return default

        value = float(value)

        if np.isnan(value):
            return default

        if np.isinf(value):
            return default

        return value

    except Exception:

        return default


def clamp(
    value,
    low=0,
    high=100
):

    return max(
        low,
        min(
            high,
            safe_float(value)
        )
    )


def format_price(value):

    value = safe_float(value)

    if value >= 1000:
        return f"{value:,.2f}"

    if value >= 100:
        return f"{value:,.3f}"

    if value >= 1:
        return f"{value:,.4f}"

    return f"{value:,.6f}"


def format_money(value):

    value = safe_float(value)

    if abs(value) >= 1_000_000:

        return (
            f"₺{value / 1_000_000:,.2f} Mn"
        )

    if abs(value) >= 1_000:

        return (
            f"₺{value / 1_000:,.1f} Bin"
        )

    return f"₺{value:,.0f}"


# ============================================================
# TEKNİK FONKSİYONLAR
# ============================================================

def calculate_rsi(series, period=14):

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
        avg_gain
        /
        avg_loss.replace(
            0,
            np.nan
        )
    )

    rsi = (
        100
        -
        (
            100
            /
            (1 + rs)
        )
    )

    return rsi


# ============================================================
# TEKNİK VERİ ÇEK
# ============================================================

@st.cache_data(ttl=300)
def get_stock_analysis(symbol):

    ticker = (
        symbol.upper().strip()
        + ".IS"
    )

    try:

        hist = yf.download(
            ticker,
            period="1y",
            interval="1d",
            auto_adjust=False,
            progress=False,
            threads=False
        )

    except Exception:

        return None


    if hist is None or hist.empty:

        return None


    # --------------------------------------------------------
    # MULTIINDEX DÜZELT
    # --------------------------------------------------------

    if isinstance(
        hist.columns,
        pd.MultiIndex
    ):

        try:

            hist.columns = (
                hist.columns
                .get_level_values(0)
            )

        except Exception:

            return None


    required = [
        "Close",
        "High",
        "Low",
        "Volume"
    ]

    for col in required:

        if col not in hist.columns:

            return None


    close = pd.to_numeric(
        hist["Close"],
        errors="coerce"
    )

    high = pd.to_numeric(
        hist["High"],
        errors="coerce"
    )

    low = pd.to_numeric(
        hist["Low"],
        errors="coerce"
    )

    volume = pd.to_numeric(
        hist["Volume"],
        errors="coerce"
    )


    data = pd.DataFrame(
        {
            "close": close,
            "high": high,
            "low": low,
            "volume": volume
        }
    ).dropna()


    if len(data) < 60:

        return None


    # ========================================================
    # EMA
    # ========================================================

    data["ema9"] = (
        data["close"]
        .ewm(
            span=9,
            adjust=False
        )
        .mean()
    )

    data["ema20"] = (
        data["close"]
        .ewm(
            span=20,
            adjust=False
        )
        .mean()
    )

    data["ema50"] = (
        data["close"]
        .ewm(
            span=50,
            adjust=False
        )
        .mean()
    )


    # ========================================================
    # RSI
    # ========================================================

    data["rsi"] = calculate_rsi(
        data["close"],
        14
    )


    # ========================================================
    # MOMENTUM
    # ========================================================

    momentum_5 = (
        (
            data["close"].iloc[-1]
            /
            data["close"].iloc[-6]
        )
        - 1
    ) * 100


    momentum_20 = (
        (
            data["close"].iloc[-1]
            /
            data["close"].iloc[-21]
        )
        - 1
    ) * 100


    momentum_60 = (
        (
            data["close"].iloc[-1]
            /
            data["close"].iloc[-61]
        )
        - 1
    ) * 100


    # ========================================================
    # HACİM
    # ========================================================

    volume_avg = (
        data["volume"]
        .rolling(20)
        .mean()
        .iloc[-1]
    )

    current_volume = (
        data["volume"].iloc[-1]
    )

    if volume_avg > 0:

        volume_ratio = (
            current_volume
            /
            volume_avg
        )

    else:

        volume_ratio = 1


    # ========================================================
    # TREND
    # ========================================================

    price = (
        data["close"].iloc[-1]
    )

    ema9 = (
        data["ema9"].iloc[-1]
    )

    ema20 = (
        data["ema20"].iloc[-1]
    )

    ema50 = (
        data["ema50"].iloc[-1]
    )

    rsi = safe_float(
        data["rsi"].iloc[-1],
        50
    )


    # ========================================================
    # TREND SKORU
    # ========================================================

    trend_score = 50


    if price > ema9:
        trend_score += 10
    else:
        trend_score -= 10


    if price > ema20:
        trend_score += 10
    else:
        trend_score -= 10


    if price > ema50:
        trend_score += 10
    else:
        trend_score -= 10


    if ema9 > ema20:
        trend_score += 5
    else:
        trend_score -= 5


    if ema20 > ema50:
        trend_score += 5
    else:
        trend_score -= 5


    trend_score = clamp(
        trend_score
    )


    # ========================================================
    # MOMENTUM SKORU
    # ========================================================

    momentum_score = 50


    if momentum_5 > 5:
        momentum_score += 15

    elif momentum_5 > 0:
        momentum_score += 8

    elif momentum_5 < -5:
        momentum_score -= 15

    elif momentum_5 < 0:
        momentum_score -= 8


    if momentum_20 > 10:
        momentum_score += 15

    elif momentum_20 > 0:
        momentum_score += 8

    elif momentum_20 < -10:
        momentum_score -= 15

    elif momentum_20 < 0:
        momentum_score -= 8


    momentum_score = clamp(
        momentum_score
    )


    # ========================================================
    # RSI SKORU
    # ========================================================

    if 50 <= rsi <= 65:

        rsi_score = 90

    elif 45 <= rsi < 50:

        rsi_score = 70

    elif 65 < rsi <= 70:

        rsi_score = 75

    elif 35 <= rsi < 45:

        rsi_score = 50

    elif rsi > 70:

        rsi_score = 55

    else:

        rsi_score = 30


    # ========================================================
    # HACİM SKORU
    # ========================================================

    if volume_ratio >= 2:

        volume_score = 100

    elif volume_ratio >= 1.5:

        volume_score = 90

    elif volume_ratio >= 1.2:

        volume_score = 80

    elif volume_ratio >= 0.8:

        volume_score = 65

    else:

        volume_score = 45


    # ========================================================
    # GENEL TEKNİK GÜÇ
    # ========================================================

    technical_score = (
        trend_score * 0.40
        +
        momentum_score * 0.30
        +
        rsi_score * 0.15
        +
        volume_score * 0.15
    )


    technical_score = clamp(
        technical_score
    )


    # ========================================================
    # VOLATİLİTE / RİSK
    # ========================================================

    returns = (
        data["close"]
        .pct_change()
        .dropna()
    )

    volatility = (
        returns
        .tail(30)
        .std()
        * 100
    )


    if volatility >= 6:

        risk_score = 85

    elif volatility >= 4:

        risk_score = 70

    elif volatility >= 3:

        risk_score = 55

    elif volatility >= 2:

        risk_score = 40

    else:

        risk_score = 25


    # ========================================================
    # SONUÇ
    # ========================================================

    return {
        "price": price,
        "ema9": ema9,
        "ema20": ema20,
        "ema50": ema50,
        "rsi": rsi,
        "momentum_5": momentum_5,
        "momentum_20": momentum_20,
        "momentum_60": momentum_60,
        "volume_ratio": volume_ratio,
        "trend_score": trend_score,
        "momentum_score": momentum_score,
        "technical_score": technical_score,
        "risk_score": risk_score,
        "volatility": volatility,
    }


# ============================================================
# VADE KARAR MOTORU
# ============================================================

def get_short_term_decision(
    technical,
    pnl
):

    if technical is None:

        return (
            "⚪ BEKLE",
            "Yeterli teknik veri alınamadı."
        )


    score = technical[
        "technical_score"
    ]

    momentum = technical[
        "momentum_score"
    ]

    trend = technical[
        "trend_score"
    ]

    risk = technical[
        "risk_score"
    ]


    if (
        score >= 78
        and momentum >= 70
        and trend >= 65
        and risk < 75
    ):

        return (
            "🟢 AL",
            "Kısa vadede teknik yapı ve momentum güçlü."
        )


    if (
        score >= 65
        and trend >= 55
    ):

        return (
            "🟢 TUT",
            "Kısa vadeli yapı pozitif ancak yeni alımda teyit tercih edilmeli."
        )


    if (
        score < 40
        or trend < 35
    ):

        return (
            "🔴 SAT",
            "Kısa vadeli teknik yapı zayıf."
        )


    if (
        score < 50
        or momentum < 40
    ):

        return (
            "🟡 AZALT",
            "Kısa vadeli momentum zayıflıyor."
        )


    return (
        "🟡 BEKLE",
        "Kısa vadede net yön teyidi beklenmeli."
    )


# ============================================================
# ORTA VADE KARAR
# ============================================================

def get_medium_term_decision(
    technical,
    pnl
):

    if technical is None:

        return (
            "⚪ BEKLE",
            "Yeterli teknik veri alınamadı."
        )


    score = technical[
        "technical_score"
    ]

    momentum = technical[
        "momentum_score"
    ]

    trend = technical[
        "trend_score"
    ]

    momentum_60 = technical[
        "momentum_60"
    ]


    if (
        score >= 75
        and trend >= 65
        and momentum_60 > 5
    ):

        return (
            "🟢 GÜÇLÜ TUT",
            "Orta vadeli trend ve momentum olumlu."
        )


    if (
        score >= 60
        and trend >= 50
    ):

        return (
            "🟢 TUT",
            "Orta vadeli yapı korunabilir."
        )


    if (
        score < 40
        and trend < 40
        and momentum_60 < -5
    ):

        return (
            "🔴 SAT",
            "Orta vadeli trend zayıf."
        )


    if (
        score < 50
        or momentum_60 < -8
    ):

        return (
            "🟡 AZALT",
            "Orta vadeli momentumda bozulma var."
        )


    return (
        "🟡 BEKLE",
        "Orta vadede yeni teyit beklenmeli."
    )


# ============================================================
# UZUN VADE KARAR
# ============================================================

def get_long_term_decision(
    technical,
    pnl
):

    if technical is None:

        return (
            "⚪ BEKLE",
            "Yeterli teknik veri alınamadı."
        )


    trend = technical[
        "trend_score"
    ]

    momentum_60 = technical[
        "momentum_60"
    ]

    score = technical[
        "technical_score"
    ]

    risk = technical[
        "risk_score"
    ]


    if (
        trend >= 70
        and momentum_60 >= 10
        and score >= 70
    ):

        return (
            "🟢 GÜÇLÜ TUT",
            "Uzun vadeli trend yapısı güçlü."
        )


    if (
        trend >= 55
        and momentum_60 >= 0
        and score >= 55
    ):

        return (
            "🟢 TUT",
            "Uzun vadeli yapı pozitif/korunabilir."
        )


    if (
        trend < 35
        and momentum_60 < -10
    ):

        return (
            "🔴 SAT",
            "Uzun vadeli trend belirgin şekilde zayıf."
        )


    if (
        trend < 45
        or momentum_60 < -5
    ):

        return (
            "🟡 AZALT",
            "Uzun vadeli görünüm zayıflıyor."
        )


    return (
        "🟡 BEKLE",
        "Uzun vadeli yön için yeni teyit gerekli."
    )


# ============================================================
# FİNAL KARAR
# ============================================================

def final_decision(
    short_decision,
    medium_decision,
    long_decision,
    risk,
    pnl
):

    decisions = [
        short_decision,
        medium_decision,
        long_decision
    ]


    # SAT sayısı
    sat_count = sum(
        1
        for x in decisions
        if "SAT" in x
    )


    # AZALT sayısı
    azalt_count = sum(
        1
        for x in decisions
        if "AZALT" in x
    )


    # GÜÇLÜ TUT
    strong_count = sum(
        1
        for x in decisions
        if "GÜÇLÜ TUT" in x
    )


    # AL
    al_count = sum(
        1
        for x in decisions
        if "AL" in x
    )


    if sat_count >= 2:

        return (
            "🔴 SAT",
            "Birden fazla vadede satış yönlü sinyal oluştu."
        )


    if (
        azalt_count >= 2
        or risk >= 75
    ):

        return (
            "🟡 AZALT",
            "Portföy veya teknik risk yükselmiş durumda."
        )


    if al_count >= 2:

        return (
            "🟢 AL",
            "Birden fazla vadede pozitif sinyal bulunuyor."
        )


    if strong_count >= 2:

        return (
            "🟢 GÜÇLÜ TUT",
            "Portföyde korunabilecek güçlü pozisyon."
        )


    positive_count = sum(
        1
        for x in decisions
        if x.startswith("🟢")
    )


    if positive_count >= 2:

        return (
            "🟢 TUT",
            "Genel görünüm pozitif."
        )


    return (
        "🟡 BEKLE",
        "Vadeler arasında net bir üstünlük bulunmuyor."
    )


# ============================================================
# PORTFÖYÜ OLUŞTUR
# ============================================================

def build_portfolio_analysis(
    portfolio
):

    rows = []


    for _, position in portfolio.iterrows():

        symbol = position[
            "symbol"
        ]

        quantity = safe_float(
            position["quantity"]
        )

        avg_cost = safe_float(
            position["avg_cost"]
        )


        technical = get_stock_analysis(
            symbol
        )


        if technical is None:

            rows.append(
                {
                    "symbol": symbol,
                    "quantity": quantity,
                    "avg_cost": avg_cost,
                    "price": 0,
                    "position_value": 0,
                    "cost_value": quantity * avg_cost,
                    "pnl": -quantity * avg_cost,
                    "pnl_pct": 0,
                    "technical_score": 0,
                    "trend_score": 0,
                    "momentum_score": 0,
                    "risk": 100,
                    "short": "⚪ BEKLE",
                    "medium": "⚪ BEKLE",
                    "long": "⚪ BEKLE",
                    "final": "⚪ BEKLE",
                    "comment": "Veri alınamadı."
                }
            )

            continue


        price = safe_float(
            technical["price"]
        )


        position_value = (
            quantity
            *
            price
        )


        cost_value = (
            quantity
            *
            avg_cost
        )


        pnl = (
            position_value
            -
            cost_value
        )


        pnl_pct = (
            pnl
            /
            cost_value
            *
            100
            if cost_value > 0
            else 0
        )


        short, short_comment = (
            get_short_term_decision(
                technical,
                pnl_pct
            )
        )


        medium, medium_comment = (
            get_medium_term_decision(
                technical,
                pnl_pct
            )
        )


        long, long_comment = (
            get_long_term_decision(
                technical,
                pnl_pct
            )
        )


        final, final_comment = (
            final_decision(
                short,
                medium,
                long,
                technical["risk_score"],
                pnl_pct
            )
        )


        rows.append(
            {
                "symbol": symbol,
                "quantity": quantity,
                "avg_cost": avg_cost,
                "price": price,
                "position_value": position_value,
                "cost_value": cost_value,
                "pnl": pnl,
                "pnl_pct": pnl_pct,
                "technical_score": technical[
                    "technical_score"
                ],
                "trend_score": technical[
                    "trend_score"
                ],
                "momentum_score": technical[
                    "momentum_score"
                ],
                "risk": technical[
                    "risk_score"
                ],
                "rsi": technical[
                    "rsi"
                ],
                "momentum_5": technical[
                    "momentum_5"
                ],
                "momentum_20": technical[
                    "momentum_20"
                ],
                "momentum_60": technical[
                    "momentum_60"
                ],
                "volume_ratio": technical[
                    "volume_ratio"
                ],
                "short": short,
                "medium": medium,
                "long": long,
                "final": final,
                "comment": final_comment
            }
        )


    result = pd.DataFrame(
        rows
    )


    if not result.empty:

        total_value = result[
            "position_value"
        ].sum()


        if total_value > 0:

            result["weight"] = (
                result["position_value"]
                /
                total_value
                *
                100
            )

        else:

            result["weight"] = 0


    return result


# ============================================================
# PORTFÖY VERİSİ
# ============================================================

portfolio = load_portfolio()


# ============================================================
# PORTFÖYE HİSSE EKLE
# ============================================================

st.divider()

st.subheader(
    "➕ Portföye Hisse Ekle"
)

st.caption(
    "Bir hisseyi mevcut portföyde varsa yeni adet ve maliyetle "
    "ekleyebilirsin. Sistem ağırlıklı ortalama maliyeti otomatik hesaplar."
)


with st.form(
    "add_stock_form",
    clear_on_submit=False
):

    c1, c2, c3 = st.columns(3)


    with c1:

        symbol_input = st.text_input(
            "Hisse Kodları",
            placeholder="Örn: THYAO, TUPRS, BIMAS"
        )


    with c2:

        quantity_input = st.number_input(
            "Adet",
            min_value=0.0,
            value=0.0,
            step=1.0
        )


    with c3:

        cost_input = st.number_input(
            "Ortalama Maliyet",
            min_value=0.0,
            value=0.0,
            step=0.01
        )


    submit = st.form_submit_button(
        "💾 Portföye Kaydet",
        use_container_width=True
    )


# ============================================================
# KAYDET
# ============================================================

if submit:

    symbols = (
        symbol_input
        .upper()
        .replace(" ", "")
        .split(",")
    )


    symbols = [
        x.strip()
        for x in symbols
        if x.strip()
    ]


    if not symbols:

        st.warning(
            "En az bir hisse kodu gir."
        )


    elif quantity_input <= 0:

        st.warning(
            "Adet 0'dan büyük olmalıdır."
        )


    elif cost_input <= 0:

        st.warning(
            "Maliyet 0'dan büyük olmalıdır."
        )


    else:

        for symbol in symbols:

            add_position(
                symbol,
                quantity_input,
                cost_input
            )


        st.success(
            f"{len(symbols)} hisse portföye kaydedildi."
        )


        st.rerun()


# ============================================================
# PORTFÖY BOŞSA
# ============================================================

# ============================================================
# PORTFÖYDEN HİSSE ÇIKAR / ADET AZALT
#
# Bu bölüm analizden ÖNCE yer alır. Böylece Yahoo Finance verisi
# alınamasa veya analiz üretilemese bile portföy düzenlenebilir.
# ============================================================

st.divider()
st.subheader("🗑️ Portföyden Hisse Çıkar / Adet Azalt")

if not portfolio.empty:

    position_map = {
        str(row["symbol"]): safe_float(row["quantity"])
        for _, row in portfolio.iterrows()
    }

    remove_symbol = st.selectbox(
        "İşlem yapılacak hisse",
        options=list(position_map.keys()),
        key="portfolio_remove_symbol"
    )

    current_quantity = position_map[remove_symbol]

    st.caption(
        f"{remove_symbol} mevcut adet: {current_quantity:g}"
    )

    remove_mode = st.radio(
        "İşlem türü",
        options=["Adet azalt", "Hisseyi tamamen çıkar"],
        horizontal=True,
        key="portfolio_remove_mode"
    )

    if remove_mode == "Adet azalt":

        reduce_quantity = st.number_input(
            "Çıkarılacak adet",
            min_value=0.0,
            max_value=float(current_quantity),
            value=0.0,
            step=1.0,
            key="portfolio_reduce_quantity"
        )

        if st.button(
            "➖ Seçili Adedi Portföyden Çıkar",
            use_container_width=True,
            key="portfolio_reduce_button"
        ):

            if reduce_quantity <= 0:
                st.warning("Çıkarılacak adet 0'dan büyük olmalıdır.")

            elif reduce_quantity >= current_quantity:
                delete_position(remove_symbol)
                st.success(f"{remove_symbol} portföyden tamamen çıkarıldı.")
                st.rerun()

            else:
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                remaining_quantity = current_quantity - reduce_quantity

                conn = get_connection()
                conn.execute(
                    """
                    UPDATE portfolio
                    SET quantity = ?, updated_at = ?
                    WHERE symbol = ?
                    """,
                    (remaining_quantity, now, remove_symbol)
                )
                conn.commit()
                conn.close()

                st.success(
                    f"{remove_symbol}: {reduce_quantity:g} adet çıkarıldı. "
                    f"Kalan adet: {remaining_quantity:g}"
                )
                st.rerun()

    else:

        confirm_remove = st.checkbox(
            f"{remove_symbol} hissesini tamamen çıkarmayı onaylıyorum",
            key="portfolio_remove_confirm"
        )

        if st.button(
            "🗑️ Hisseyi Portföyden Tamamen Çıkar",
            type="primary",
            use_container_width=True,
            disabled=not confirm_remove,
            key="portfolio_remove_button"
        ):
            delete_position(remove_symbol)
            st.success(f"{remove_symbol} portföyden tamamen çıkarıldı.")
            st.rerun()

else:
    st.info("Portföy boş olduğu için çıkarılacak hisse bulunmuyor.")

if portfolio.empty:

    st.info(
        "Portföy henüz boş. Yukarıdan hisselerini ekleyebilirsin."
    )

    st.stop()


# ============================================================
# ANALİZ
# ============================================================

with st.spinner(
    "Portföy analiz ediliyor..."
):

    analysis = build_portfolio_analysis(
        portfolio
    )


if analysis.empty:

    st.warning(
        "Portföy analiz edilemedi."
    )

    st.stop()


# ============================================================
# TOPLAM HESAPLAR
# ============================================================

total_value = analysis[
    "position_value"
].sum()


total_cost = analysis[
    "cost_value"
].sum()


total_pnl = (
    total_value
    -
    total_cost
)


total_pnl_pct = (
    total_pnl
    /
    total_cost
    *
    100
    if total_cost > 0
    else 0
)


# ============================================================
# ÖZET
# ============================================================

st.divider()

st.subheader(
    "📊 Portföy Özeti"
)


m1, m2, m3, m4, m5 = st.columns(5)


with m1:

    st.metric(
        "Portföy Değeri",
        format_money(
            total_value
        )
    )


with m2:

    st.metric(
        "Toplam Maliyet",
        format_money(
            total_cost
        )
    )


with m3:

    st.metric(
        "Toplam K/Z",
        format_money(
            total_pnl
        ),
        f"{total_pnl_pct:+.2f}%"
    )


with m4:

    st.metric(
        "Hisse Sayısı",
        len(analysis)
    )


with m5:

    avg_score = analysis[
        "technical_score"
    ].mean()

    st.metric(
        "Ortalama Güç",
        f"{avg_score:.1f}/100"
    )


# ============================================================
# KARAR SAYILARI
# ============================================================

st.divider()

st.subheader(
    "🎯 Portföy Karar Merkezi"
)


final_counts = (
    analysis["final"]
    .value_counts()
)


a1, a2, a3, a4, a5, a6 = st.columns(6)


with a1:

    st.metric(
        "🟢 AL",
        int(
            final_counts.get(
                "🟢 AL",
                0
            )
        )
    )


with a2:

    st.metric(
        "🟢 GÜÇLÜ TUT",
        int(
            final_counts.get(
                "🟢 GÜÇLÜ TUT",
                0
            )
        )
    )


with a3:

    st.metric(
        "🟢 TUT",
        int(
            final_counts.get(
                "🟢 TUT",
                0
            )
        )
    )


with a4:

    st.metric(
        "🟡 BEKLE",
        int(
            final_counts.get(
                "🟡 BEKLE",
                0
            )
        )
    )


with a5:

    st.metric(
        "🟡 AZALT",
        int(
            final_counts.get(
                "🟡 AZALT",
                0
            )
        )
    )


with a6:

    st.metric(
        "🔴 SAT",
        int(
            final_counts.get(
                "🔴 SAT",
                0
            )
        )
    )


# ============================================================
# VADE TABLOSU
# ============================================================

st.divider()

st.subheader(
    "📅 Vade Bazlı Portföy Görünümü"
)


horizon_table = analysis[
    [
        "symbol",
        "short",
        "medium",
        "long",
        "final"
    ]
].copy()


horizon_table = horizon_table.rename(
    columns={
        "symbol": "Hisse",
        "short": "Kısa Vade",
        "medium": "Orta Vade",
        "long": "Uzun Vade",
        "final": "Final Karar"
    }
)


st.dataframe(
    horizon_table,
    use_container_width=True,
    hide_index=True
)


# ============================================================
# POZİSYON KARTLARI
# ============================================================

st.divider()

st.subheader(
    "📌 Portföy Pozisyonları"
)


for _, row in analysis.iterrows():

    final = row["final"]


    with st.container(
        border=True
    ):

        c1, c2, c3, c4, c5, c6 = st.columns(6)


        with c1:

            st.markdown(
                f"### {row['symbol']}"
            )

            if final.startswith("🟢"):

                st.success(
                    final
                )

            elif final.startswith("🟡"):

                st.warning(
                    final
                )

            elif final.startswith("🔴"):

                st.error(
                    final
                )

            else:

                st.info(
                    final
                )


        with c2:

            st.metric(
                "Fiyat",
                f"₺{format_price(row['price'])}"
            )

            st.metric(
                "Maliyet",
                f"₺{format_price(row['avg_cost'])}"
            )


        with c3:

            st.metric(
                "Adet",
                f"{row['quantity']:,.0f}"
            )

            st.metric(
                "Pozisyon",
                format_money(
                    row["position_value"]
                )
            )


        with c4:

            st.metric(
                "K/Z",
                format_money(
                    row["pnl"]
                ),
                f"{row['pnl_pct']:+.2f}%"
            )

            st.metric(
                "Ağırlık",
                f"%{row['weight']:.1f}"
            )


        with c5:

            st.metric(
                "Teknik Güç",
                f"{row['technical_score']:.1f}"
            )

            st.metric(
                "Risk",
                f"{row['risk']:.1f}"
            )


        with c6:

            st.metric(
                "RSI",
                f"{row['rsi']:.1f}"
            )

            st.metric(
                "60G Momentum",
                f"{row['momentum_60']:+.1f}%"
            )


        st.markdown(
            f"""
**Kısa Vade:** {row['short']}

**Orta Vade:** {row['medium']}

**Uzun Vade:** {row['long']}

**💡 Yorum:** {row['comment']}
"""
        )


# ============================================================
# DETAYLI TABLO
# ============================================================

st.divider()

st.subheader(
    "📋 Detaylı Portföy Tablosu"
)


table = analysis[
    [
        "symbol",
        "quantity",
        "avg_cost",
        "price",
        "position_value",
        "pnl",
        "pnl_pct",
        "weight",
        "technical_score",
        "trend_score",
        "momentum_score",
        "risk",
        "short",
        "medium",
        "long",
        "final"
    ]
].copy()


table = table.rename(
    columns={
        "symbol": "Hisse",
        "quantity": "Adet",
        "avg_cost": "Maliyet",
        "price": "Fiyat",
        "position_value": "Pozisyon",
        "pnl": "K/Z",
        "pnl_pct": "K/Z %",
        "weight": "Ağırlık %",
        "technical_score": "Teknik Güç",
        "trend_score": "Trend",
        "momentum_score": "Momentum",
        "risk": "Risk",
        "short": "Kısa Vade",
        "medium": "Orta Vade",
        "long": "Uzun Vade",
        "final": "Final"
    }
)


st.dataframe(
    table,
    use_container_width=True,
    hide_index=True
)


# ============================================================
# PORTFÖY RİSKİ
# ============================================================

st.divider()

st.subheader(
    "⚠️ Portföy Risk Analizi"
)


risk1, risk2, risk3 = st.columns(3)


highest_weight = (
    analysis
    .sort_values(
        "weight",
        ascending=False
    )
    .iloc[0]
)


highest_risk = (
    analysis
    .sort_values(
        "risk",
        ascending=False
    )
    .iloc[0]
)


weakest = (
    analysis
    .sort_values(
        "technical_score",
        ascending=True
    )
    .iloc[0]
)


with risk1:

    st.info(
        f"**En yüksek ağırlık**\n\n"
        f"{highest_weight['symbol']} "
        f"— %{highest_weight['weight']:.1f}"
    )


with risk2:

    st.warning(
        f"**En yüksek risk**\n\n"
        f"{highest_risk['symbol']} "
        f"— {highest_risk['risk']:.1f}/100"
    )


with risk3:

    st.error(
        f"**En zayıf teknik yapı**\n\n"
        f"{weakest['symbol']} "
        f"— {weakest['technical_score']:.1f}/100"
    )


# ============================================================
# COİN / HİSSE DETAYI
# ============================================================

st.divider()

st.subheader(
    "🔎 Hisse Detaylı Karar"
)


selected_symbol = st.selectbox(
    "Detayını görmek istediğin hisse",
    analysis["symbol"].tolist()
)


selected = analysis[
    analysis["symbol"]
    ==
    selected_symbol
].iloc[0]


st.markdown(
    f"## {selected_symbol}"
)


if selected["final"].startswith("🟢"):

    st.success(
        selected["final"]
    )

elif selected["final"].startswith("🟡"):

    st.warning(
        selected["final"]
    )

elif selected["final"].startswith("🔴"):

    st.error(
        selected["final"]
    )

else:

    st.info(
        selected["final"]
    )


d1, d2, d3, d4, d5, d6 = st.columns(6)


with d1:

    st.metric(
        "Teknik Güç",
        f"{selected['technical_score']:.1f}"
    )


with d2:

    st.metric(
        "Trend",
        f"{selected['trend_score']:.1f}"
    )


with d3:

    st.metric(
        "Momentum",
        f"{selected['momentum_score']:.1f}"
    )


with d4:

    st.metric(
        "Risk",
        f"{selected['risk']:.1f}"
    )


with d5:

    st.metric(
        "RSI",
        f"{selected['rsi']:.1f}"
    )


with d6:

    st.metric(
        "60G Momentum",
        f"{selected['momentum_60']:+.2f}%"
    )


st.markdown("### 📅 Vade Kararları")


v1, v2, v3 = st.columns(3)


with v1:

    st.info(
        f"**Kısa Vade**\n\n"
        f"{selected['short']}"
    )


with v2:

    st.info(
        f"**Orta Vade**\n\n"
        f"{selected['medium']}"
    )


with v3:

    st.info(
        f"**Uzun Vade**\n\n"
        f"{selected['long']}"
    )


st.markdown(
    "### 💡 Final Yorum"
)


st.success(
    selected["comment"]
)


# ============================================================
# TÜM PORTFÖYÜ TEMİZLE
# ============================================================

if st.button(
    "⚠️ Tüm Portföyü Temizle",
    use_container_width=True
):

    delete_all_positions()

    st.success(
        "Portföy tamamen temizlendi."
    )

    st.rerun()


# ============================================================
# KARAR MOTORU
# ============================================================

st.divider()

with st.expander(
    "🧠 Portföy PRO Karar Motoru"
):

    st.markdown(
        """
### 🟢 AL

Kısa, orta veya uzun vadede güçlü teknik
yapı ve momentum desteği bulunuyorsa oluşur.

---

### 🟢 GÜÇLÜ TUT

Mevcut pozisyonun korunması için güçlü
teknik yapı bulunmaktadır.

---

### 🟢 TUT

Hisse pozitif görünümünü koruyor ancak
agresif yeni alım için ekstra teyit tercih edilir.

---

### 🟡 BEKLE

Vadeler arasında net bir üstünlük yoktur.
Yeni yön teyidi beklenir.

---

### 🟡 AZALT

Teknik yapı zayıflıyor veya portföy riski
yükseliyor.

Pozisyonun tamamını kapatmak yerine risk
azaltılması düşünülebilir.

---

### 🔴 SAT

Birden fazla vadede belirgin zayıflık
oluşmuştur.

---

## Vade Mantığı

**Kısa Vade**

- EMA 9
- EMA 20
- RSI
- kısa momentum
- hacim

**Orta Vade**

- EMA 20
- EMA 50
- 20 günlük momentum
- trend

**Uzun Vade**

- EMA 50
- 60 günlük momentum
- ana trend
- teknik güç

Bunlar birlikte değerlendirilerek
portföy kararı oluşturulur.

---

## Önemli

Bu sayfanın amacı:

**"Hangi hisseyi alayım?"**

sorusundan ziyade:

**"Elimdeki hisseyi kısa, orta ve uzun vadede
ne yapmalıyım?"**

sorusuna cevap vermektir.

Yeni hisse seçimi ile mevcut portföy yönetimi
aynı problem değildir.
"""
    )


# ============================================================
# SON DURUM
# ============================================================

st.divider()

st.caption(
    f"Portföy verileri kalıcı olarak SQLite'a kaydedilir. "
    f"Son analiz: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')} | "
    f"BIST AI PRO Portföy Yönetim PRO"
)

st.caption(
    "⚠️ Bu sayfa yatırım tavsiyesi değildir. "
    "Teknik karar desteği sağlar. Gerçek işlem öncesinde "
    "piyasa koşulları, likidite, haber akışı ve emir gerçekleşmesi "
    "ayrıca kontrol edilmelidir."
)
