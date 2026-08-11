import streamlit as st
import yfinance as yf
import sqlite3
import pandas as pd

from modules.data.yahoo_data import get_stock_analysis

from modules.data.fundamental import (
    get_fundamental_data,
    calculate_fundamental_score
)

from modules.ai.market_ai import get_market_score

from modules.data.financial_score import (
    calculate_financial_score
)

# ============================================================
# SAYFA AYARLARI
# ============================================================

st.set_page_config(
    page_title="Hisse Analiz Merkezi",
    page_icon="📈",
    layout="wide"
)

st.title("📈 Hisse Analiz Merkezi")

# ============================================================
# VADE AĞIRLIKLARI
# ============================================================

VADELER = {

    "⚡ Kısa Vade — 1 Hafta": {
        "technical": 0.45,
        "fundamental": 0.10,
        "kap": 0.05,
        "momentum": 0.25,
        "market": 0.10,
        "financial_trend": 0.05,
    },

    "📅 Orta Vade — 1 Ay": {
        "technical": 0.40,
        "fundamental": 0.15,
        "kap": 0.10,
        "momentum": 0.20,
        "market": 0.10,
        "financial_trend": 0.05,
    },

    "📈 Orta/Uzun Vade — 6 Ay": {
        "technical": 0.30,
        "fundamental": 0.20,
        "kap": 0.20,
        "momentum": 0.15,
        "market": 0.05,
        "financial_trend": 0.10,
    },

    "🏦 Uzun Vade — 6 Ay–3 Yıl": {
        "technical": 0.20,
        "fundamental": 0.25,
        "kap": 0.30,
        "momentum": 0.10,
        "market": 0.05,
        "financial_trend": 0.10,
    },
}

# ============================================================
# YARDIMCI FONKSİYONLAR
# ============================================================

def safe_float(value, default=0):
    try:
        if value is None:
            return default

        if pd.isna(value):
            return default

        return float(value)

    except Exception:
        return default


def format_money(value):

    if value is None or pd.isna(value):
        return "-"

    value = float(value)

    return (
        f"{value:,.2f}"
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )


def get_quarter(period):

    period = str(period)

    if "_1Q" in period:
        return 1

    if "_2Q" in period:
        return 2

    if "_3Q" in period:
        return 3

    if "_YILLIK" in period:
        return 4

    return None


# ============================================================
# PORTFÖYDE Mİ?
# ============================================================

def is_in_portfolio(symbol):

    try:

        conn = sqlite3.connect("borsa.db")

        tables = pd.read_sql_query(
            """
            SELECT name
            FROM sqlite_master
            WHERE type='table'
            """,
            conn
        )

        table_names = set(
            tables["name"].tolist()
        )

        if "portfolio" not in table_names:
            conn.close()
            return False

        columns = pd.read_sql_query(
            "PRAGMA table_info(portfolio)",
            conn
        )

        column_names = columns["name"].tolist()

        possible_symbol_columns = [
            "symbol",
            "ticker",
            "stock",
            "hisse",
            "hisse_kodu"
        ]

        symbol_column = None

        for column in possible_symbol_columns:

            if column in column_names:
                symbol_column = column
                break

        if symbol_column is None:
            conn.close()
            return False

        query = f"""
            SELECT *
            FROM portfolio
            WHERE UPPER({symbol_column}) = ?
        """

        df = pd.read_sql_query(
            query,
            conn,
            params=(symbol.upper(),)
        )

        conn.close()

        return not df.empty

    except Exception:

        return False


# ============================================================
# FİNANSAL TREND VERİSİ
# ============================================================

def get_financial_trend(symbol):

    try:

        conn = sqlite3.connect("borsa.db")

        df = pd.read_sql_query(
            """
            SELECT
                period,
                period_end,
                revenue,
                net_profit,
                cash,
                equity,
                operating_cash_flow,
                short_term_financial_debt,
                current_portion_long_term_debt,
                long_term_financial_debt
            FROM financial_statements
            WHERE symbol = ?
            ORDER BY period_end
            """,
            conn,
            params=(symbol,)
        )

        conn.close()

        if df.empty:
            return None

        df["period_end"] = pd.to_datetime(
            df["period_end"],
            errors="coerce"
        )

        df = df.dropna(
            subset=["period_end"]
        )

        df["year"] = df["period_end"].dt.year

        df["quarter"] = df["period"].apply(
            get_quarter
        )

        df = df[
            df["quarter"].notna()
        ].copy()

        if df.empty:
            return None

        flow_columns = [
            "revenue",
            "net_profit",
            "operating_cash_flow"
        ]

        quarterly_rows = []

        for _, row in df.iterrows():

            current = row.copy()

            year = row["year"]
            quarter = row["quarter"]

            for column in flow_columns:

                value = row[column]

                if pd.isna(value):
                    current[column] = None
                    continue

                if quarter == 1:

                    current[column] = value

                else:

                    previous = df[
                        (df["year"] == year)
                        &
                        (
                            df["quarter"]
                            == quarter - 1
                        )
                    ]

                    if not previous.empty:

                        previous_value = (
                            previous.iloc[-1][column]
                        )

                        if pd.notna(previous_value):

                            current[column] = (
                                value - previous_value
                            )

                        else:

                            current[column] = value

                    else:

                        current[column] = value

            quarterly_rows.append(current)

        qdf = pd.DataFrame(
            quarterly_rows
        )

        def period_name(row):

            year = int(row["year"])
            quarter = row["quarter"]

            if quarter == 1:
                return f"{year} 1Ç"

            if quarter == 2:
                return f"{year} 2Ç"

            if quarter == 3:
                return f"{year} 3Ç"

            if quarter == 4:
                return f"{year} Yıllık"

            return str(row["period"])

        qdf["display_period"] = qdf.apply(
            period_name,
            axis=1
        )

        qdf["financial_debt"] = (
            qdf["short_term_financial_debt"].fillna(0)
            +
            qdf["current_portion_long_term_debt"].fillna(0)
            +
            qdf["long_term_financial_debt"].fillna(0)
        )

        qdf["debt_equity"] = (
            qdf["financial_debt"]
            /
            qdf["equity"].replace(0, pd.NA)
        )

        qdf["net_cash"] = (
            qdf["cash"]
            -
            qdf["financial_debt"]
        )

        qdf["net_margin"] = (
            qdf["net_profit"]
            /
            qdf["revenue"].replace(0, pd.NA)
            * 100
        )

        return qdf

    except Exception:

        return None


# ============================================================
# FİNANSAL TREND SKORU
# ============================================================

def calculate_trend_score(qdf):

    if qdf is None or len(qdf) < 2:
        return None, [], [], []

    latest = qdf.iloc[-1]

    previous = qdf.iloc[-2]

    previous_year_df = qdf[
        (
            qdf["year"]
            == latest["year"] - 1
        )
        &
        (
            qdf["quarter"]
            == latest["quarter"]
        )
    ]

    previous_year = None

    if not previous_year_df.empty:

        previous_year = previous_year_df.iloc[-1]

    trend_items = [

        ("Hasılat", "revenue", True),
        ("Net Kâr", "net_profit", True),
        ("Net Kâr Marjı", "net_margin", True),
        ("Faaliyet Nakit Akışı", "operating_cash_flow", True),
        ("Nakit", "cash", True),
        ("Özkaynak", "equity", True),
        ("Finansal Borç", "financial_debt", False),
        ("Net Nakit", "net_cash", True),
        ("Borç / Özkaynak", "debt_equity", False)
    ]

    results = []

    for name, column, higher_is_better in trend_items:

        values = []

        latest_value = latest[column]
        previous_value = previous[column]

        if (
            pd.notna(latest_value)
            and pd.notna(previous_value)
            and previous_value != 0
        ):

            change = (
                (latest_value - previous_value)
                /
                abs(previous_value)
                * 100
            )

            if higher_is_better:

                if change > 5:
                    values.append(1)

                elif change < -5:
                    values.append(-1)

                else:
                    values.append(0)

            else:

                if change < -5:
                    values.append(1)

                elif change > 5:
                    values.append(-1)

                else:
                    values.append(0)

        if previous_year is not None:

            old_value = previous_year[column]

            if (
                pd.notna(latest_value)
                and pd.notna(old_value)
                and old_value != 0
            ):

                change = (
                    (latest_value - old_value)
                    /
                    abs(old_value)
                    * 100
                )

                if higher_is_better:

                    if change > 5:
                        values.append(1)

                    elif change < -5:
                        values.append(-1)

                    else:
                        values.append(0)

                else:

                    if change < -5:
                        values.append(1)

                    elif change > 5:
                        values.append(-1)

                    else:
                        values.append(0)

        if values:

            direction = sum(values) / len(values)

            if direction > 0.25:
                status = "Güçlü"

            elif direction < -0.25:
                status = "Zayıf"

            else:
                status = "Stabil"

        else:

            direction = None
            status = "Veri Yok"

        results.append(
            {
                "name": name,
                "direction": direction,
                "status": status
            }
        )

    valid = [
        x
        for x in results
        if x["direction"] is not None
    ]

    if not valid:
        return None, results, [], []

    positive = sum(
        1
        for x in valid
        if x["direction"] > 0.25
    )

    neutral = sum(
        1
        for x in valid
        if -0.25 <= x["direction"] <= 0.25
    )

    negative = sum(
        1
        for x in valid
        if x["direction"] < -0.25
    )

    total = len(valid)

    score = (
        positive * 100
        +
        neutral * 60
        +
        negative * 20
    ) / total

    strong = [
        x["name"]
        for x in valid
        if x["direction"] > 0.25
    ]

    weak = [
        x["name"]
        for x in valid
        if x["direction"] < -0.25
    ]

    return score, results, strong, weak


# ============================================================
# MA5 KISA VADE MOMENTUM
# ============================================================

def calculate_ma5_signal(veri):

    try:

        if veri is None or len(veri) < 6:
            return 50, False, 0, 0

        close = veri["Close"].copy()

        ma5 = close.rolling(5).mean()

        current_price = safe_float(
            close.iloc[-1],
            0
        )

        current_ma5 = safe_float(
            ma5.iloc[-1],
            0
        )

        previous_price = safe_float(
            close.iloc[-2],
            0
        )

        previous_ma5 = safe_float(
            ma5.iloc[-2],
            0
        )

        if current_ma5 == 0:
            return 50, False, current_price, current_ma5

        cross_up = (
            previous_price <= previous_ma5
            and
            current_price > current_ma5
        )

        if cross_up:

            score = 100

        elif current_price > current_ma5:

            score = 70

        else:

            score = 30

        return (
            score,
            cross_up,
            current_price,
            current_ma5
        )

    except Exception:

        return 50, False, 0, 0


# ============================================================
# TEKNİK TREND
# ============================================================

def get_technical_trend_signal(sonuc):

    trend = str(
        sonuc.get(
            "trend",
            ""
        )
    ).upper()

    positive_words = [
        "YÜKSELİŞ",
        "YUKSELIS",
        "POZİTİF",
        "POZITIF",
        "BULLISH",
        "UPTREND",
        "YUKARI"
    ]

    negative_words = [
        "DÜŞÜŞ",
        "DUSUS",
        "NEGATİF",
        "NEGATIF",
        "BEARISH",
        "DOWNTREND",
        "AŞAĞI",
        "ASAGI"
    ]

    if any(
        word in trend
        for word in positive_words
    ):
        return "🟢 POZİTİF"

    if any(
        word in trend
        for word in negative_words
    ):
        return "🔴 NEGATİF"

    return "🟡 NÖTR"


# ============================================================
# DETAYLI KARAR YORUMU
# ============================================================

def create_decision_comment(
    symbol,
    genel_skor,
    genel_karar,
    technical_score,
    fundamental_score,
    kap_score,
    momentum_score,
    market_score,
    financial_trend_score,
    ma5_cross_up,
    sonuc,
    vade,
    portfolio_status
):

    comments = []

    if genel_skor >= 85:

        comments.append(
            "Genel skor çok güçlü seviyede."
        )

    elif genel_skor >= 70:

        comments.append(
            "Genel skor olumlu ve pozitif bölgede."
        )

    elif genel_skor >= 55:

        comments.append(
            "Genel skor nötr-pozitif bölgede."
        )

    elif genel_skor >= 40:

        comments.append(
            "Genel skor zayıf ve temkinli yaklaşım gerektiriyor."
        )

    else:

        comments.append(
            "Genel skor riskli bölgede."
        )

    if technical_score >= 80:

        comments.append(
            "Teknik görünüm güçlü."
        )

    elif technical_score >= 65:

        comments.append(
            "Teknik görünüm olumlu ancak tam güçte değil."
        )

    elif technical_score >= 50:

        comments.append(
            "Teknik görünüm kararsız/nötr."
        )

    else:

        comments.append(
            "Teknik görünüm zayıf."
        )

    if momentum_score >= 80:

        comments.append(
            "60 günlük momentum güçlü."
        )

    elif momentum_score >= 60:

        comments.append(
            "60 günlük momentum pozitif ancak sınırlı."
        )

    elif momentum_score < 40:

        comments.append(
            "60 günlük momentum zayıf."
        )

    if ma5_cross_up:

        comments.append(
            "Fiyat 5 günlük hareketli ortalamayı yukarı kesti; kısa vadeli momentum için pozitif teyit oluştu."
        )

    if fundamental_score >= 80:

        comments.append(
            "Temel göstergeler güçlü."
        )

    elif fundamental_score >= 60:

        comments.append(
            "Temel görünüm kabul edilebilir."
        )

    elif fundamental_score < 50:

        comments.append(
            "Temel göstergeler zayıf."
        )

    if kap_score >= 80:

        comments.append(
            "KAP finansal skor güçlü; şirketin finansal yapısı destekleyici."
        )

    elif kap_score >= 60:

        comments.append(
            "KAP finansal skor dengeli."
        )

    elif kap_score < 50:

        comments.append(
            "KAP finansal skor zayıf ve finansal taraf takip edilmeli."
        )

    if financial_trend_score >= 80:

        comments.append(
            "Finansal trend güçlü ve şirket finansallarında belirgin iyileşme görülüyor."
        )

    elif financial_trend_score >= 60:

        comments.append(
            "Finansal trend stabil/pozitif."
        )

    elif financial_trend_score < 40:

        comments.append(
            "Finansal trend zayıflıyor; bilanço tarafında dikkat gerekiyor."
        )

    if market_score >= 70:

        comments.append(
            "Piyasa koşulları hisseyi destekliyor."
        )

    elif market_score < 45:

        comments.append(
            "Genel piyasa koşulları baskı oluşturuyor."
        )

    if genel_karar == "🟠 İZLE":

        if technical_score < 60:

            comments.append(
                "İZLE kararının ana nedeni teknik görünümün henüz yeterince güçlenmemiş olması."
            )

        elif momentum_score < 60:

            comments.append(
                "İZLE kararının ana nedeni momentumun henüz yeterli teyidi vermemesi."
            )

        elif fundamental_score < 60:

            comments.append(
                "İZLE kararında temel göstergelerin henüz yeterli destek vermemesi etkili."
            )

        elif kap_score < 60:

            comments.append(
                "İZLE kararında finansal skorun henüz güçlü seviyeye ulaşmaması etkili."
            )

        else:

            comments.append(
                "Hisse tamamen negatif değil; ancak AL/TUT seviyesine geçmek için ek teyit gerekiyor."
            )

    if portfolio_status:

        if genel_karar == "🔴 SAT":

            comments.append(
                "Hisse portföyde mevcut. Mevcut pozisyon için azaltma/çıkış yönünde risk değerlendirmesi yapılmalı."
            )

        elif genel_karar == "🟠 İZLE":

            comments.append(
                "Hisse portföyde mevcut. Yeni alım yerine mevcut pozisyon izlenmeli ve teknik teyit beklenmeli."
            )

        elif genel_karar == "🟡 TUT":

            comments.append(
                "Hisse portföyde mevcut. Mevcut pozisyon korunabilir; önemli destekler takip edilmeli."
            )

        elif genel_karar == "🟢 AL":

            comments.append(
                "Hisse portföyde mevcut. Görünüm olumlu; pozisyon güçlendirme kararı risk yönetimiyle değerlendirilir."
            )

        elif genel_karar == "🟢 GÜÇLÜ AL":

            comments.append(
                "Hisse portföyde mevcut ve görünüm güçlü. Pozisyon korunabilir; ek alım için fiyat/direnç teyidi izlenebilir."
            )

    else:

        if genel_karar == "🟠 İZLE":

            comments.append(
                "Hisse portföyde değil. Mevcut seviyeden agresif alım yerine teyit beklemek daha uygun."
            )

        elif genel_karar == "🔴 SAT":

            comments.append(
                "Hisse portföyde değil. Mevcut görünüm yeni pozisyon açmak için uygun değil."
            )

    return " ".join(comments)


# ============================================================
# HİSSE + VADE SEÇİMİ
# ============================================================

col1, col2 = st.columns([1, 1])

with col1:

    symbol_input = st.text_input(
        "Hisse Kodu",
        placeholder="Örn: ASTOR"
    )

with col2:

    vade = st.selectbox(
        "Analiz Vadesi",
        list(VADELER.keys())
    )


# ============================================================
# ANALİZ BUTONU
# ============================================================

analiz_et_buton = st.button(
    "🔍 ANALİZ ET",
    type="primary",
    use_container_width=True
)


# ============================================================
# ANALİZ
# ============================================================

if analiz_et_buton:

    if not symbol_input.strip():

        st.warning(
            "Lütfen bir hisse kodu giriniz."
        )

        st.stop()

    symbol = (
        symbol_input
        .upper()
        .strip()
    )

    weights = VADELER[vade]

    portfolio_status = is_in_portfolio(
        symbol
    )

    # --------------------------------------------------------
    # YAHOO
    # --------------------------------------------------------

    try:

        ticker = yf.Ticker(
            symbol + ".IS"
        )

        veri = ticker.history(
            period="2y"
        )

    except Exception as e:

        st.error(
            f"Yahoo Finance verisi alınamadı: {e}"
        )

        st.stop()

    if veri.empty:

        st.error(
            "Hisse için veri bulunamadı."
        )

        st.stop()

    # --------------------------------------------------------
    # MA5
    # --------------------------------------------------------

    (
        ma5_score,
        ma5_cross_up,
        current_price,
        ma5_current
    ) = calculate_ma5_signal(veri)

    # --------------------------------------------------------
    # TEKNİK
    # --------------------------------------------------------

    try:

        sonuc = get_stock_analysis(
            symbol
        )

    except Exception as e:

        st.error(
            f"Teknik analiz alınamadı: {e}"
        )

        st.stop()

    if sonuc is None:

        st.error(
            "Teknik analiz sonucu alınamadı."
        )

        st.stop()

    # --------------------------------------------------------
    # TEMEL
    # --------------------------------------------------------

    try:

        fundamental = get_fundamental_data(
            symbol
        )

        fund_score = calculate_fundamental_score(
            fundamental
        )

    except Exception:

        fundamental = {}
        fund_score = 50

    # --------------------------------------------------------
    # MARKET
    # --------------------------------------------------------

    try:

        market_score, market_reasons = (
            get_market_score()
        )

    except Exception:

        market_score = 50
        market_reasons = []

    # --------------------------------------------------------
    # KAP
    # --------------------------------------------------------

    try:

        kap_financial = calculate_financial_score(
            symbol
        )

    except Exception:

        kap_financial = None

    if kap_financial:

        kap_score = safe_float(
            kap_financial.get(
                "total_score"
            ),
            50
        )

        kap_signal = kap_financial.get(
            "signal",
            "NÖTR"
        )

    else:

        kap_score = 50
        kap_signal = "Veri Yok"

    # --------------------------------------------------------
    # FİNANSAL TREND
    # --------------------------------------------------------

    trend_df = get_financial_trend(
        symbol
    )

    if trend_df is not None:

        (
            financial_trend_score,
            trend_results,
            strong_points,
            weak_points
        ) = calculate_trend_score(
            trend_df
        )

    else:

        financial_trend_score = 50
        trend_results = []
        strong_points = []
        weak_points = []

    financial_trend_score = safe_float(
        financial_trend_score,
        50
    )

    # --------------------------------------------------------
    # SKORLAR
    # --------------------------------------------------------

    technical_score = safe_float(
        sonuc.get("score"),
        50
    )

    momentum_60_score = safe_float(
        sonuc.get(
            "momentum_60_score"
        ),
        50
    )

    fundamental_score = safe_float(
        fund_score,
        50
    )

    market_score = safe_float(
        market_score,
        50
    )

    # --------------------------------------------------------
    # KISA VADE MOMENTUM
    # --------------------------------------------------------

    short_momentum_score = (
        momentum_60_score * 0.70
        +
        ma5_score * 0.30
    )

    if vade == "⚡ Kısa Vade — 1 Hafta":

        momentum_used = short_momentum_score

    else:

        momentum_used = momentum_60_score

    # --------------------------------------------------------
    # GENEL SKOR
    # --------------------------------------------------------

    genel_skor = (

        technical_score
        * weights["technical"]

        +

        fundamental_score
        * weights["fundamental"]

        +

        kap_score
        * weights["kap"]

        +

        momentum_used
        * weights["momentum"]

        +

        market_score
        * weights["market"]

        +

        financial_trend_score
        * weights["financial_trend"]

    )

    genel_skor = round(
        genel_skor,
        1
    )

    # --------------------------------------------------------
    # GENEL KARAR
    # --------------------------------------------------------

    if genel_skor >= 85:

        genel_karar = "🟢 GÜÇLÜ AL"

    elif genel_skor >= 70:

        genel_karar = "🟢 AL"

    elif genel_skor >= 55:

        genel_karar = "🟡 TUT"

    elif genel_skor >= 40:

        genel_karar = "🟠 İZLE"

    else:

        genel_karar = "🔴 SAT"

    # --------------------------------------------------------
    # TEKNİK TREND
    # --------------------------------------------------------

    technical_trend_signal = (
        get_technical_trend_signal(
            sonuc
        )
    )

    # --------------------------------------------------------
    # RİSK
    # --------------------------------------------------------

    if genel_skor >= 80:

        risk_level = "🟢 Düşük"

    elif genel_skor >= 65:

        risk_level = "🟡 Orta"

    elif genel_skor >= 50:

        risk_level = "🟠 Orta-Yüksek"

    else:

        risk_level = "🔴 Yüksek"

    # ========================================================
    # BAŞLIK
    # ========================================================

    st.divider()

    st.subheader(
        f"🎯 {symbol} — {vade}"
    )

    if portfolio_status:

        st.success(
            "📦 **Bu hisse portföyünüzde mevcut.**"
        )

    else:

        st.info(
            "📭 Bu hisse şu anda portföyde görünmüyor."
        )

    # ========================================================
    # ANA SONUÇ
    # ========================================================

    c1, c2, c3 = st.columns(3)

    with c1:

        st.metric(
            "🏆 Genel Yatırım Skoru",
            f"{genel_skor:.0f}/100"
        )

    with c2:

        st.metric(
            "📌 Genel Karar",
            genel_karar
        )

    with c3:

        price = sonuc.get("price")
        change = sonuc.get("change", 0)

        if price is not None:

            st.metric(
                "💰 Güncel Fiyat",
                f"{price:.2f} TL",
                f"{change:.2f}%"
            )

    # ========================================================
    # VADE BAZLI DURUM
    # ========================================================

    st.divider()

    st.subheader(
        "🎯 Vade Bazlı Durum"
    )

    vc1, vc2, vc3 = st.columns(3)

    with vc1:

        st.metric(
            "📈 Teknik Trend",
            technical_trend_signal
        )

    with vc2:

        st.metric(
            "🏦 Finansal Trend",
            f"{financial_trend_score:.0f}/100"
        )

    with vc3:

        st.metric(
            "⚠️ Risk Seviyesi",
            risk_level
        )

    # ========================================================
    # DETAYLI KARAR
    # ========================================================

    karar_yorumu = create_decision_comment(
        symbol,
        genel_skor,
        genel_karar,
        technical_score,
        fundamental_score,
        kap_score,
        momentum_used,
        market_score,
        financial_trend_score,
        ma5_cross_up,
        sonuc,
        vade,
        portfolio_status
    )

    st.markdown(
        "### 🧠 Karar Yorumu"
    )

    if genel_karar in [
        "🟢 GÜÇLÜ AL",
        "🟢 AL"
    ]:

        st.success(
            karar_yorumu
        )

    elif genel_karar == "🟡 TUT":

        st.info(
            karar_yorumu
        )

    elif genel_karar == "🟠 İZLE":

        st.warning(
            karar_yorumu
        )

    else:

        st.error(
            karar_yorumu
        )

    # ========================================================
    # SKOR DAĞILIMI
    # ========================================================

    st.divider()

    st.subheader(
        "📊 Skor Dağılımı"
    )

    c1, c2, c3, c4, c5, c6 = st.columns(6)

    with c1:

        st.metric(
            "📈 Teknik",
            f"{technical_score:.0f}/100"
        )

    with c2:

        st.metric(
            "📊 Temel",
            f"{fundamental_score:.0f}/100"
        )

    with c3:

        st.metric(
            "🏦 KAP Finansal",
            f"{kap_score:.0f}/100"
        )

    with c4:

        st.metric(
            "🚀 Momentum",
            f"{momentum_used:.0f}/100"
        )

    with c5:

        st.metric(
            "🌍 Market",
            f"{market_score:.0f}/100"
        )

    with c6:

        st.metric(
            "📊 Finansal Trend",
            f"{financial_trend_score:.0f}/100"
        )

    # ========================================================
    # VADE AĞIRLIKLARI
    # ========================================================

    with st.expander(
        "⚙️ Bu vadede kullanılan ağırlıkları göster"
    ):

        st.write(
            f"📈 Teknik: **%{weights['technical'] * 100:.0f}**"
        )

        st.write(
            f"📊 Temel: **%{weights['fundamental'] * 100:.0f}**"
        )

        st.write(
            f"🏦 KAP Finansal: **%{weights['kap'] * 100:.0f}**"
        )

        st.write(
            f"🚀 Momentum: **%{weights['momentum'] * 100:.0f}**"
        )

        st.write(
            f"🌍 Market: **%{weights['market'] * 100:.0f}**"
        )

        st.write(
            f"📊 Finansal Trend: **%{weights['financial_trend'] * 100:.0f}**"
        )

    # ========================================================
    # KAP SKORU
    # ========================================================

    st.divider()

    st.subheader(
        "🏦 KAP Finansal Değerlendirme"
    )

    kc1, kc2 = st.columns(2)

    with kc1:

        st.metric(
            "KAP Finansal Skor",
            f"{kap_score:.1f}/100"
        )

    with kc2:

        st.metric(
            "Finansal Durum",
            kap_signal
        )

    st.caption(
        "KAP finansal skor genel yatırım skoruna dahil edilir. "
        "Bilanço kalemleri bu bölümde gösterilmez."
    )

    # ========================================================
    # TEMEL ANALİZ
    # ========================================================

    st.divider()

    st.subheader(
        "📊 Temel Analiz"
    )

    fc1, fc2, fc3, fc4 = st.columns(4)

    with fc1:

        st.metric(
            "📌 F/K",
            str(
                fundamental.get(
                    "pe_ratio",
                    "-"
                )
            )
        )

    with fc2:

        st.metric(
            "📌 PD/DD",
            str(
                fundamental.get(
                    "pb_ratio",
                    "-"
                )
            )
        )

    with fc3:

        margin = fundamental.get(
            "profit_margin"
        )

        if margin is not None:

            st.metric(
                "📈 Kâr Marjı",
                f"%{margin * 100:.1f}"
            )

        else:

            st.metric(
                "📈 Kâr Marjı",
                "-"
            )

    with fc4:

        growth = fundamental.get(
            "revenue_growth"
        )

        if growth is not None:

            st.metric(
                "📈 Ciro Büyümesi",
                f"%{growth * 100:.1f}"
            )

        else:

            st.metric(
                "📈 Ciro Büyümesi",
                "-"
            )

    st.write(
        "🏭 **Sektör:**",
        fundamental.get(
            "sector",
            "-"
        )
    )

    # ========================================================
    # TEKNİK ANALİZ
    # ========================================================

    st.divider()

    st.subheader(
        f"📈 {symbol} Teknik Analizi"
    )

    tc1, tc2, tc3, tc4, tc5 = st.columns(5)

    with tc1:

        st.metric(
            "📍 Destek",
            f"{safe_float(sonuc.get('support')):.2f} TL"
        )

    with tc2:

        st.metric(
            "🚧 Direnç",
            f"{safe_float(sonuc.get('resistance')):.2f} TL"
        )

    with tc3:

        st.metric(
            "MACD",
            f"{safe_float(sonuc.get('macd')):.2f}"
        )

    with tc4:

        st.metric(
            "RSI",
            f"{safe_float(sonuc.get('rsi')):.2f}"
        )

    with tc5:

        st.metric(
            "📊 Teknik Skor",
            f"{technical_score:.0f}/100"
        )

    recommendation = sonuc.get(
        "recommendation",
        "-"
    )

    if "Güçlü Al" in recommendation:

        st.success(
            recommendation
        )

    elif "Al" in recommendation:

        st.success(
            recommendation
        )

    elif "Tut" in recommendation:

        st.warning(
            recommendation
        )

    else:

        st.error(
            recommendation
        )

    st.info(
        f"Trend: {sonuc.get('trend', '-')}"
    )

    # ========================================================
    # FİNANSAL TREND
    # ========================================================

    st.divider()

    st.subheader(
        "📊 Finansal Trend"
    )

    if trend_df is None:

        st.info(
            "Finansal trend verisi bulunamadı."
        )

    else:

        latest = trend_df.iloc[-1]

        if financial_trend_score >= 80:

            trend_signal = "🟢 Güçleniyor"

        elif financial_trend_score >= 60:

            trend_signal = "🟡 Stabil / Pozitif"

        elif financial_trend_score >= 40:

            trend_signal = "🟠 Zayıflıyor"

        else:

            trend_signal = "🔴 Bozuluyor"

        tc1, tc2, tc3 = st.columns(3)

        with tc1:

            st.metric(
                "📊 Finansal Trend Skoru",
                f"{financial_trend_score:.0f}/100"
            )

        with tc2:

            st.metric(
                "📈 Trend",
                trend_signal
            )

        with tc3:

            st.metric(
                "📅 Son Dönem",
                str(
                    latest["display_period"]
                )
            )

        if strong_points:

            st.success(
                "🟢 **Güçlü Noktalar:** "
                + ", ".join(
                    strong_points
                )
            )

        if weak_points:

            st.warning(
                "🟠 **Dikkat Edilecek Noktalar:** "
                + ", ".join(
                    weak_points
                )
            )

        st.markdown(
            "### 📈 Finansal Trend Grafiği"
        )

        chart_df = trend_df[
            [
                "display_period",
                "revenue",
                "net_profit",
                "cash",
                "equity"
            ]
        ].copy()

        chart_df["revenue"] = (
            chart_df["revenue"]
            / 1_000_000
        )

        chart_df["net_profit"] = (
            chart_df["net_profit"]
            / 1_000_000
        )

        chart_df["cash"] = (
            chart_df["cash"]
            / 1_000_000
        )

        chart_df["equity"] = (
            chart_df["equity"]
            / 1_000_000
        )

        chart_df = chart_df.set_index(
            "display_period"
        )

        chart_df.columns = [
            "Hasılat",
            "Net Kâr",
            "Nakit",
            "Özkaynak"
        ]

        st.line_chart(
            chart_df,
            use_container_width=True
        )

        st.caption(
            "Hasılat ve Net Kâr çeyreklik akış; "
            "Nakit ve Özkaynak dönem sonu bakiyesidir."
        )

        st.markdown(
            "### 📌 Son Dönem Finansal Durum"
        )

        sc1, sc2, sc3, sc4 = st.columns(4)

        with sc1:

            st.metric(
                "Hasılat",
                f"{safe_float(latest['revenue']) / 1_000_000:.2f} Mlyr TL"
            )

        with sc2:

            st.metric(
                "Net Kâr",
                f"{safe_float(latest['net_profit']) / 1_000_000:.2f} Mlyr TL"
            )

        with sc3:

            st.metric(
                "Faaliyet Nakit Akışı",
                f"{safe_float(latest['operating_cash_flow']) / 1_000_000:.2f} Mlyr TL"
            )

        with sc4:

            net_cash = safe_float(
                latest["net_cash"]
            )

            if net_cash >= 0:

                st.metric(
                    "Net Nakit",
                    f"{net_cash / 1_000_000:.2f} Mlyr TL"
                )

            else:

                st.metric(
                    "Net Borç",
                    f"{abs(net_cash) / 1_000_000:.2f} Mlyr TL"
                )

        st.markdown(
            "### 📋 Finansal Trend Tablosu"
        )

        display_df = trend_df[
            [
                "display_period",
                "period_end",
                "revenue",
                "net_profit",
                "cash",
                "equity",
                "operating_cash_flow",
                "financial_debt",
                "net_cash",
                "debt_equity",
                "net_margin"
            ]
        ].copy()

        display_df["period_end"] = (
            pd.to_datetime(
                display_df["period_end"]
            ).dt.strftime(
                "%d.%m.%Y"
            )
        )

        money_columns = [
            "revenue",
            "net_profit",
            "cash",
            "equity",
            "operating_cash_flow",
            "financial_debt",
            "net_cash"
        ]

        for column in money_columns:

            display_df[column] = (
                display_df[column]
                .apply(
                    lambda x:
                    (
                        format_money(
                            x / 1_000_000
                        )
                        if pd.notna(x)
                        else "-"
                    )
                )
            )

        display_df["debt_equity"] = (
            display_df["debt_equity"]
            .apply(
                lambda x:
                (
                    f"{x:.2f}x"
                    if pd.notna(x)
                    else "-"
                )
            )
        )

        display_df["net_margin"] = (
            display_df["net_margin"]
            .apply(
                lambda x:
                (
                    f"%{x:.2f}"
                    if pd.notna(x)
                    else "-"
                )
            )
        )

        display_df.columns = [

            "Dönem",
            "Tarih",
            "Hasılat\n(Mlyr TL)",
            "Net Kâr\n(Mlyr TL)",
            "Nakit\n(Mlyr TL)",
            "Özkaynak\n(Mlyr TL)",
            "Faaliyet Nakit\n(Mlyr TL)",
            "Finansal Borç\n(Mlyr TL)",
            "Net Nakit/Borç\n(Mlyr TL)",
            "Borç/Özkaynak",
            "Net Kâr\nMarjı"
        ]

        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True
        )

    # ========================================================
    # FİYAT GRAFİĞİ
    # ========================================================

    st.divider()

    st.subheader(
        "📈 Fiyat Grafiği"
    )

    grafik = veri[
        ["Close"]
    ].copy()

    grafik["MA5"] = (
        veri["Close"]
        .rolling(5)
        .mean()
    )

    grafik["MA20"] = (
        veri["Close"]
        .rolling(20)
        .mean()
    )

    grafik["MA50"] = (
        veri["Close"]
        .rolling(50)
        .mean()
    )

    grafik["MA200"] = (
        veri["Close"]
        .rolling(200)
        .mean()
    )

    st.line_chart(
        grafik,
        use_container_width=True
    )

    # ========================================================
    # TEKNİK GÖSTERGELER
    # ========================================================

    st.divider()

    st.subheader(
        "📊 Teknik Göstergeler"
    )

    ec1, ec2, ec3, ec4, ec5 = st.columns(5)

    with ec1:

        st.metric(
            "MA5",
            f"{ma5_current:.2f}"
        )

    with ec2:

        if ma5_cross_up:

            ma5_status = "🟢 Yukarı Kesişim"

        elif current_price > ma5_current:

            ma5_status = "🟢 Üzerinde"

        else:

            ma5_status = "🔴 Altında"

        st.metric(
            "MA5 Durumu",
            ma5_status
        )

    with ec3:

        st.metric(
            "EMA20",
            f"{safe_float(sonuc.get('ema20')):.2f}"
        )

    with ec4:

        st.metric(
            "EMA50",
            f"{safe_float(sonuc.get('ema50')):.2f}"
        )

    with ec5:

        st.metric(
            "EMA200",
            f"{safe_float(sonuc.get('ema200')):.2f}"
        )

    if ma5_cross_up:

        st.success(
            "📈 **Kısa vadeli momentum teyidi:** "
            "Fiyat 5 günlük hareketli ortalamayı yukarı kesti."
        )

    elif current_price > ma5_current:

        st.info(
            "Fiyat 5 günlük hareketli ortalamanın üzerinde; "
            "ancak yeni yukarı kesişim oluşmadı."
        )

    else:

        st.warning(
            "Fiyat 5 günlük hareketli ortalamanın altında."
        )

    # ========================================================
    # MARKET DEĞERLENDİRMESİ
    # ========================================================

    if market_reasons:

        st.divider()

        st.subheader(
            "🌍 Piyasa Değerlendirmesi"
        )

        for reason in market_reasons:

            st.write(
                f"• {reason}"
            )

    # ========================================================
    # FİNAL DEĞERLENDİRME
    # ========================================================

    st.divider()

    st.subheader(
        "📝 Genel Değerlendirme"
    )

    if genel_skor >= 85:

        st.success(
            f"{symbol} için **{vade}** perspektifinde "
            f"çok güçlü görünüm var. "
            f"Genel yatırım skoru: **{genel_skor:.0f}/100**."
        )

    elif genel_skor >= 70:

        st.success(
            f"{symbol} için **{vade}** perspektifinde "
            f"olumlu görünüm var. "
            f"Genel yatırım skoru: **{genel_skor:.0f}/100**."
        )

    elif genel_skor >= 55:

        st.warning(
            f"{symbol} için **{vade}** perspektifinde "
            f"nötr-pozitif görünüm var. "
            f"Genel yatırım skoru: **{genel_skor:.0f}/100**."
        )

    elif genel_skor >= 40:

        st.warning(
            f"{symbol} için **{vade}** perspektifinde "
            f"temkinli olunmalı. "
            f"Genel yatırım skoru: **{genel_skor:.0f}/100**."
        )

    else:

        st.error(
            f"{symbol} için **{vade}** perspektifinde "
            f"riskli görünüm var. "
            f"Genel yatırım skoru: **{genel_skor:.0f}/100**."
        )
