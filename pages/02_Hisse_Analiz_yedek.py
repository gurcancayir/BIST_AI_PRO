import streamlit as st
import yfinance as yf
import sqlite3
import pandas as pd

from modules.teknik import analiz_et
from modules.data.yahoo_data import get_stock_analysis

from modules.data.fundamental import (
    get_fundamental_data,
    calculate_fundamental_score
)

from modules.ai.market_ai import get_market_score

from modules.data.financial_score import (
    calculate_financial_score,
    get_financial_statement
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
# HİSSE SEÇİMİ
# ============================================================

symbol = st.text_input(
    "Hisse Kodu",
    placeholder="Örn: BIMAS"
)


if st.button("Analiz Et"):

    if not symbol:
        st.warning("Hisse kodu giriniz.")
        st.stop()

    symbol = symbol.upper().strip()

    # ========================================================
    # YAHOO VERİSİ
    # ========================================================

    try:

        ticker = yf.Ticker(symbol + ".IS")

        veri = ticker.history(
            period="1y"
        )

    except Exception as e:

        st.error(
            f"Yahoo Finance verisi alınamadı: {e}"
        )

        st.stop()

    if veri.empty:

        st.error(
            "Veri bulunamadı."
        )

        st.stop()

    # ========================================================
    # TEKNİK ANALİZ
    # ========================================================

    sonuc = get_stock_analysis(symbol)

    if sonuc is None:

        st.error(
            "Analiz verisi alınamadı."
        )

        st.stop()

    # ========================================================
    # TEMEL ANALİZ VERİLERİ
    # ========================================================

    fundamental = get_fundamental_data(
        symbol
    )

    fund_score = calculate_fundamental_score(
        fundamental
    )

    market_score, market_reasons = get_market_score()

    # ========================================================
    # KAP FİNANSAL ANALİZ
    # ========================================================

    kap_data = get_financial_statement(
        symbol
    )
    

    kap_financial = calculate_financial_score(
        symbol
    )
    print("DEBUG ASTOR SYMBOL:", symbol)
    print("DEBUG KAP FINANCIAL:", kap_financial)
    if kap_financial:

        kap_score = kap_financial["total_score"]

        kap_signal = kap_financial["signal"]

    else:

        kap_score = None

        kap_signal = "Veri Yok"

    # ========================================================
    # KAP FİNANSAL SKOR
    # ========================================================

    st.divider()

    st.subheader(
        "🧾 KAP Finansal Analiz"
    )

    if kap_score is not None:

        kc1, kc2 = st.columns(2)

        with kc1:

            st.metric(
                "🧾 KAP Finansal Skor",
                f"{kap_score:.1f}/100"
            )

        with kc2:

            st.metric(
                "📌 Finansal Durum",
                kap_signal
            )

    else:

        st.metric(
            "🧾 KAP Finansal Skor",
            "Veri Yok"
        )

    # ========================================================
    # KAP FİNANSAL VERİLER
    # ========================================================

    if kap_data:

        st.markdown(
            "### 💰 KAP Finansal Veriler"
        )

        col1, col2, col3 = st.columns(3)

        # ----------------------------------------------------
        # HASILAT
        # ----------------------------------------------------

        with col1:

            revenue = kap_data.get("revenue")
            st.write("DEBUG REVENUE:", revenue)
            if revenue is not None:

                st.metric(
                    "Hasılat",
                    f"{revenue / 1_000_000:.2f} Mlyr TL"
                )

            else:

                st.metric(
                    "Hasılat",
                    "Veri Yok"
                )

        # ----------------------------------------------------
        # NET KÂR
        # ----------------------------------------------------

        with col2:

            net_profit = kap_data.get("net_profit")

            if net_profit is not None:

                st.metric(
                    "Net Kâr",
                    f"{net_profit / 1_000_000:.2f} Mlyr TL"
                )

            else:

                st.metric(
                    "Net Kâr",
                    "Veri Yok"
                )

        # ----------------------------------------------------
        # NAKİT
        # ----------------------------------------------------

        with col3:

            cash = kap_data.get("cash")

            if cash is not None:

                st.metric(
                    "Nakit",
                    f"{cash / 1_000_000:.2f} Mlyr TL"
                )

            else:

                st.metric(
                    "Nakit",
                    "Veri Yok"
                )

        col4, col5 = st.columns(2)

        # ----------------------------------------------------
        # ÖZKAYNAK
        # ----------------------------------------------------

        with col4:

            equity = kap_data.get("equity")

            if equity is not None:

                st.metric(
                    "Özkaynak",
                    f"{equity / 1_000_000:.2f} Mlyr TL"
                )

            else:

                st.metric(
                    "Özkaynak",
                    "Veri Yok"
                )

        # ----------------------------------------------------
        # FAALİYET NAKİT AKIŞI
        # ----------------------------------------------------

        with col5:

            operating_cash_flow = kap_data.get("operating_cash_flow")

            if operating_cash_flow is not None:

                st.metric(
                    "Faaliyet Nakit Akışı",
                    f"{operating_cash_flow / 1_000_000:.2f} Mlyr TL"
                )

            else:

                st.metric(
                    "Faaliyet Nakit Akışı",
                    "Veri Yok"
                )

        st.caption(
            f"KAP Dönemi: {kap_data.get('period')} "
            f"({kap_data.get('period_end')})"
        )
        # ====================================================
        # KAP FİNANSAL SAĞLIK
        # ====================================================

        st.markdown(
            "### 🏦 KAP Finansal Sağlık"
        )

        cash = kap_data.get(
            "cash"
        )

        equity = kap_data.get(
            "equity"
        )

        short_debt = kap_data.get(
            "short_term_financial_debt"
        )

        current_long_debt = kap_data.get(
            "current_portion_long_term_debt"
        )

        long_debt = kap_data.get(
            "long_term_financial_debt"
        )

        net_profit = kap_data.get(
            "net_profit"
        )

        revenue = kap_data.get(
            "revenue"
        )

        operating_cash_flow = kap_data.get(
            "operating_cash_flow"
        )

        # ----------------------------------------------------
        # TOPLAM FİNANSAL BORÇ
        # ----------------------------------------------------

        debt_parts = [
            short_debt,
            current_long_debt,
            long_debt
        ]

        valid_debts = [
            x
            for x in debt_parts
            if x is not None
        ]

        if valid_debts:

            total_debt = sum(
                valid_debts
            )

        else:

            total_debt = None

        # ----------------------------------------------------
        # BORÇ / ÖZKAYNAK
        # ----------------------------------------------------

        if (
            total_debt is not None
            and equity
        ):

            debt_equity = (
                total_debt / equity
            )

        else:

            debt_equity = None

        # ----------------------------------------------------
        # NET NAKİT / BORÇ
        # ----------------------------------------------------

        if (
            cash is not None
            and total_debt is not None
        ):

            net_cash = (
                cash - total_debt
            )

        else:

            net_cash = None

        # ----------------------------------------------------
        # NET KÂR MARJI
        # ----------------------------------------------------

        if (
            net_profit is not None
            and revenue
        ):

            net_margin = (
                net_profit
                / revenue
                * 100
            )

        else:

            net_margin = None

        # ----------------------------------------------------
        # NAKİT / NET KÂR
        # ----------------------------------------------------

        if (
            operating_cash_flow is not None
            and net_profit
        ):

            cash_profit_ratio = (
                operating_cash_flow
                / net_profit
                * 100
            )

        else:

            cash_profit_ratio = None

        # ----------------------------------------------------
        # FİNANSAL BORÇ
        # ----------------------------------------------------

        c1, c2, c3 = st.columns(3)

        with c1:

            if total_debt is not None:

                st.metric(
                    "💳 Finansal Borç",
                    f"{total_debt / 1_000_000:.2f} Mlyr TL"
                )

            else:

                st.metric(
                    "💳 Finansal Borç",
                    "Veri Yok"
                )

        # ----------------------------------------------------
        # BORÇ / ÖZKAYNAK
        # ----------------------------------------------------

        with c2:

            if debt_equity is not None:

                st.metric(
                    "⚖️ Borç / Özkaynak",
                    f"{debt_equity:.2f}x"
                )

            else:

                st.metric(
                    "⚖️ Borç / Özkaynak",
                    "Veri Yok"
                )

        # ----------------------------------------------------
        # NET NAKİT
        # ----------------------------------------------------

        with c3:

            if net_cash is not None:

                if net_cash >= 0:

                    st.metric(
                        "💰 Net Nakit",
                        f"{net_cash / 1_000:.2f} Mlyr TL"
                    )

                else:

                    st.metric(
                        "💰 Net Borç",
                        f"{abs(net_cash) / 1_000:.2f} Mlyr TL"
                    )

            else:

                st.metric(
                    "💰 Net Nakit/Borç",
                    "Veri Yok"
                )

        # ----------------------------------------------------
        # KÂRLILIK
        # ----------------------------------------------------

        c4, c5 = st.columns(2)

        with c4:

            if net_margin is not None:

                st.metric(
                    "📈 Net Kâr Marjı",
                    f"%{net_margin:.2f}"
                )

            else:

                st.metric(
                    "📈 Net Kâr Marjı",
                    "Veri Yok"
                )

        with c5:

            if cash_profit_ratio is not None:

                st.metric(
                    "💵 Nakit / Net Kâr",
                    f"%{cash_profit_ratio:.1f}"
                )

            else:

                st.metric(
                    "💵 Nakit / Net Kâr",
                    "Veri Yok"
                )

        # ----------------------------------------------------
        # FİNANSAL SAĞLIK
        # ----------------------------------------------------

        if (
            debt_equity is not None
            and net_cash is not None
        ):

            if (
                net_cash > 0
                and debt_equity < 0.50
            ):

                financial_health = (
                    "🟢 Çok Güçlü"
                )

            elif (
                net_cash >= 0
                and debt_equity < 1.00
            ):

                financial_health = (
                    "🟢 Güçlü"
                )

            elif debt_equity < 2.00:

                financial_health = (
                    "🟡 Dengeli"
                )

            else:

                financial_health = (
                    "🔴 Borçluluk Yüksek"
                )

            st.info(
                f"**Finansal Sağlık:** {financial_health}"
            )

        st.caption(
            "Borç/Özkaynak ve net nakit değerleri "
            "KAP finansal tablolarından hesaplanır."
        )

    # ========================================================
    # KAP FİNANSAL TREND
    # ========================================================

    st.divider()

    st.markdown(
        "### 📊 KAP Finansal Trend"
    )

    try:

        trend_db = sqlite3.connect(
            "borsa.db"
        )

        trend_df = pd.read_sql_query(
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
            trend_db,
            params=(symbol,)
        )

        trend_db.close()

        if trend_df.empty:

            st.info(
                "KAP finansal trend verisi bulunamadı."
            )

        else:

            # =================================================
            # DÖNEM BİLGİLERİ
            # =================================================

            trend_df["period_end"] = pd.to_datetime(
                trend_df["period_end"]
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

            trend_df["year"] = (
                trend_df["period_end"].dt.year
            )

            trend_df["quarter"] = (
                trend_df["period"].apply(
                    get_quarter
                )
            )

            # =================================================
            # KÜMÜLATİF VERİLERİ ÇEYREKLİĞE ÇEVİR
            # =================================================

            flow_columns = [
                "revenue",
                "net_profit",
                "operating_cash_flow"
            ]

            quarterly_rows = []

            for _, row in trend_df.iterrows():

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

                        previous_quarter_number = (
                            quarter - 1
                        )

                        previous = trend_df[
                            (
                                trend_df["year"]
                                == year
                            )
                            &
                            (
                                trend_df["quarter"]
                                == previous_quarter_number
                            )
                        ]

                        if not previous.empty:

                            previous_value = (
                                previous.iloc[0][
                                    column
                                ]
                            )

                            if pd.notna(
                                previous_value
                            ):

                                current[column] = (
                                    value
                                    - previous_value
                                )

                            else:

                                current[column] = value

                        else:

                            current[column] = value

                quarterly_rows.append(
                    current
                )

            quarterly_df = pd.DataFrame(
                quarterly_rows
            )

            # =================================================
            # ÇEYREK İSİMLERİ
            # =================================================

            def quarter_name(row):

                year = int(
                    row["year"]
                )

                quarter = row["quarter"]

                if quarter == 1:
                    return f"{year} 1Ç"

                if quarter == 2:
                    return f"{year} 2Ç"

                if quarter == 3:
                    return f"{year} 3Ç"

                if quarter == 4:
                    return f"{year} Yıllık"

                return str(
                    row["period"]
                )

            quarterly_df[
                "display_period"
            ] = quarterly_df.apply(
                quarter_name,
                axis=1
            )

            # =================================================
            # FİNANSAL BORÇ
            # =================================================

            quarterly_df[
                "financial_debt"
            ] = (
                quarterly_df[
                    "short_term_financial_debt"
                ].fillna(0)

                +

                quarterly_df[
                    "current_portion_long_term_debt"
                ].fillna(0)

                +

                quarterly_df[
                    "long_term_financial_debt"
                ].fillna(0)
            )

            # =================================================
            # BORÇ / ÖZKAYNAK
            # =================================================

            quarterly_df[
                "debt_equity"
            ] = (
                quarterly_df[
                    "financial_debt"
                ]

                /

                quarterly_df[
                    "equity"
                ].replace(
                    0,
                    pd.NA
                )
            )

            # =================================================
            # NET NAKİT
            # =================================================

            quarterly_df[
                "net_cash"
            ] = (
                quarterly_df[
                    "cash"
                ]

                -

                quarterly_df[
                    "financial_debt"
                ]
            )

            # =================================================
            # NET KÂR MARJI
            # =================================================

            quarterly_df[
                "net_margin"
            ] = (
                quarterly_df[
                    "net_profit"
                ]

                /

                quarterly_df[
                    "revenue"
                ].replace(
                    0,
                    pd.NA
                )

                * 100
            )

            # =================================================
            # MİLYAR TL
            # =================================================

            billion_columns = [
                "revenue",
                "net_profit",
                "cash",
                "equity",
                "operating_cash_flow",
                "financial_debt",
                "net_cash"
            ]

            for column in billion_columns:

                quarterly_df[
                    column + "_b"
                ] = (
                    quarterly_df[column]
                    / 1_000_000
                )

            # =================================================
            # FİNANSAL TREND GRAFİĞİ
            # =================================================

            chart_df = quarterly_df[
                [
                    "display_period",
                    "revenue_b",
                    "net_profit_b",
                    "cash_b",
                    "equity_b"
                ]
            ].copy()

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
                "Hasılat ve Net Kâr gerçek çeyreklik "
                "değerlerdir. Nakit ve Özkaynak "
                "dönem sonu bakiyeleridir."
            )

            # =================================================
            # SON DÖNEM
            # =================================================

            latest = quarterly_df.iloc[-1]

            latest_year = int(
                latest["year"]
            )

            latest_quarter = latest[
                "quarter"
            ]

            # =================================================
            # ÖNCEKİ ÇEYREK
            # =================================================

            previous_quarter_df = quarterly_df[
                (
                    quarterly_df["year"]
                    == latest_year
                )
                &
                (
                    quarterly_df["quarter"]
                    == latest_quarter - 1
                )
            ]

            # =================================================
            # GEÇEN YIL AYNI ÇEYREK
            # =================================================

            previous_year_df = quarterly_df[
                (
                    quarterly_df["year"]
                    == latest_year - 1
                )
                &
                (
                    quarterly_df["quarter"]
                    == latest_quarter
                )
            ]

            previous_quarter = None

            if not previous_quarter_df.empty:

                previous_quarter = (
                    previous_quarter_df.iloc[-1]
                )

            previous_year = None

            if not previous_year_df.empty:

                previous_year = (
                    previous_year_df.iloc[-1]
                )

            # =================================================
            # TREND FONKSİYONU
            # =================================================

            def trend_direction(
                latest_value,
                compare_value,
                higher_is_better=True
            ):

                if (
                    latest_value is None
                    or compare_value is None
                ):

                    return None

                if (
                    pd.isna(latest_value)
                    or pd.isna(compare_value)
                ):

                    return None

                if compare_value == 0:

                    return None

                change = (
                    (
                        latest_value
                        - compare_value
                    )
                    /
                    abs(compare_value)
                    * 100
                )

                if higher_is_better:

                    if change > 5:
                        return 1

                    elif change < -5:
                        return -1

                    else:
                        return 0

                else:

                    if change < -5:
                        return 1

                    elif change > 5:
                        return -1

                    else:
                        return 0

            # =================================================
            # TREND GÖSTERGELERİ
            # =================================================

            trend_items = [

                (
                    "Hasılat",
                    "revenue",
                    True
                ),

                (
                    "Net Kâr",
                    "net_profit",
                    True
                ),

                (
                    "Net Kâr Marjı",
                    "net_margin",
                    True
                ),

                (
                    "Faaliyet Nakit Akışı",
                    "operating_cash_flow",
                    True
                ),

                (
                    "Nakit",
                    "cash",
                    True
                ),

                (
                    "Özkaynak",
                    "equity",
                    True
                ),

                (
                    "Finansal Borç",
                    "financial_debt",
                    False
                ),

                (
                    "Net Nakit",
                    "net_cash",
                    True
                ),

                (
                    "Borç / Özkaynak",
                    "debt_equity",
                    False
                )
            ]

            trend_results = []

            for (
                name,
                column,
                higher_is_better
            ) in trend_items:

                qoq = None
                yoy = None

                if previous_quarter is not None:

                    qoq = trend_direction(
                        latest[column],
                        previous_quarter[column],
                        higher_is_better
                    )

                if previous_year is not None:

                    yoy = trend_direction(
                        latest[column],
                        previous_year[column],
                        higher_is_better
                    )

                scores = []

                if qoq is not None:
                    scores.append(qoq)

                if yoy is not None:
                    scores.append(yoy)

                if scores:

                    average_direction = (
                        sum(scores)
                        / len(scores)
                    )

                    if average_direction > 0.25:

                        status = "Güçlü"

                    elif average_direction < -0.25:

                        status = "Zayıf"

                    else:

                        status = "Stabil"

                else:

                    average_direction = None

                    status = "Veri Yok"

                trend_results.append(
                    {
                        "name": name,
                        "column": column,
                        "direction": average_direction,
                        "status": status
                    }
                )

            # =================================================
            # TREND SKORU
            # =================================================

            valid_results = [
                x
                for x in trend_results
                if x["direction"] is not None
            ]

            if valid_results:

                positive = sum(
                    1
                    for x in valid_results
                    if x["direction"] > 0.25
                )

                neutral = sum(
                    1
                    for x in valid_results
                    if -0.25
                    <= x["direction"]
                    <= 0.25
                )

                negative = sum(
                    1
                    for x in valid_results
                    if x["direction"] < -0.25
                )

                total = len(
                    valid_results
                )

                trend_score = (
                    positive * 100
                    +
                    neutral * 60
                    +
                    negative * 20
                ) / total

            else:

                trend_score = None

            # =================================================
            # TREND SİNYALİ
            # =================================================

            if trend_score is None:

                trend_signal = "⚪ Veri Yok"

            elif trend_score >= 80:

                trend_signal = "🟢 Güçleniyor"

            elif trend_score >= 60:

                trend_signal = "🟡 Stabil / Pozitif"

            elif trend_score >= 40:

                trend_signal = "🟠 Zayıflıyor"

            else:

                trend_signal = "🔴 Bozuluyor"

            # =================================================
            # TREND ÖZETİ
            # =================================================

            st.markdown(
                "### 🧭 Finansal Trend Sinyali"
            )

            tc1, tc2, tc3 = st.columns(3)

            with tc1:

                if trend_score is not None:

                    st.metric(
                        "📊 Finansal Trend Skoru",
                        f"{trend_score:.0f}/100"
                    )

                else:

                    st.metric(
                        "📊 Finansal Trend Skoru",
                        "Veri Yok"
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
                        latest[
                            "display_period"
                        ]
                    )
                )

            # =================================================
            # GÜÇLÜ / ZAYIF NOKTALAR
            # =================================================

            strong_points = []
            weak_points = []

            for item in trend_results:

                if item["direction"] is None:
                    continue

                if item["direction"] > 0.25:

                    strong_points.append(
                        item["name"]
                    )

                elif item["direction"] < -0.25:

                    weak_points.append(
                        item["name"]
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

            if (
                not strong_points
                and not weak_points
            ):

                st.info(
                    "🟡 Finansal göstergelerde "
                    "belirgin bir yön değişimi "
                    "görülmüyor."
                )

            # =================================================
            # OTOMATİK FİNANSAL YORUM
            # =================================================

            commentary = []

            if (
                pd.notna(
                    latest["net_profit"]
                )
                and pd.notna(
                    latest["revenue"]
                )
                and pd.notna(
                    latest["net_margin"]
                )
            ):

                commentary.append(
                    f"Son çeyrekte net kâr marjı "
                    f"%{latest['net_margin']:.2f} seviyesinde."
                )

            if (
                pd.notna(
                    latest[
                        "operating_cash_flow"
                    ]
                )
                and pd.notna(
                    latest["net_profit"]
                )
                and latest["net_profit"] != 0
            ):

                cash_conversion = (
                    latest[
                        "operating_cash_flow"
                    ]
                    /
                    latest["net_profit"]
                    * 100
                )

                if cash_conversion > 100:

                    commentary.append(
                        "Faaliyet nakit akışı net kârın "
                        "üzerinde; kârın nakit üretimi güçlü."
                    )

                elif cash_conversion > 70:

                    commentary.append(
                        "Faaliyet nakit akışı net kârı "
                        "makul ölçüde destekliyor."
                    )

                else:

                    commentary.append(
                        "Faaliyet nakit akışı net kâra "
                        "göre zayıf seyrediyor."
                    )

            if (
                pd.notna(
                    latest["net_cash"]
                )
                and latest["net_cash"] > 0
            ):

                commentary.append(
                    "Şirket net nakit pozisyonunda."
                )

            elif (
                pd.notna(
                    latest["net_cash"]
                )
                and latest["net_cash"] < 0
            ):

                commentary.append(
                    "Şirket net borç pozisyonunda."
                )

            if (
                pd.notna(
                    latest["debt_equity"]
                )
                and latest["debt_equity"] < 0.50
            ):

                commentary.append(
                    "Borç/özkaynak oranı düşük ve "
                    "finansal kaldıraç kontrollü."
                )

            if commentary:

                st.info(
                    "📝 **Otomatik Finansal Trend Yorumu:**\n\n"
                    + " ".join(commentary)
                )

            # =================================================
            # SON DÖNEM FİNANSAL DURUM
            # =================================================

            st.markdown(
                "### 📌 Son Dönem Finansal Durum"
            )

            sc1, sc2, sc3, sc4 = st.columns(4)

            with sc1:

                st.metric(
                    "Hasılat",
                    f"{latest['revenue_b']:.2f} Mlyr TL"
                )

            with sc2:

                st.metric(
                    "Net Kâr",
                    f"{latest['net_profit_b']:.2f} Mlyr TL"
                )

            with sc3:

                st.metric(
                    "Faaliyet Nakit Akışı",
                    f"{latest['operating_cash_flow_b']:.2f} Mlyr TL"
                )

            with sc4:

                if latest["net_cash"] >= 0:

                    st.metric(
                        "Net Nakit",
                        f"{latest['net_cash_b']:.2f} Mlyr TL"
                    )

                else:

                    st.metric(
                        "Net Borç",
                        f"{abs(latest['net_cash_b']):.2f} Mlyr TL"
                    )

            # =================================================
            # OKUNABİLİR TREND TABLOSU
            # =================================================

            st.markdown(
                "### 📋 Finansal Trend Tablosu"
            )

            display_df = quarterly_df[
                [
                    "display_period",
                    "period_end",
                    "revenue_b",
                    "net_profit_b",
                    "cash_b",
                    "equity_b",
                    "operating_cash_flow_b",
                    "financial_debt_b",
                    "net_cash_b",
                    "debt_equity",
                    "net_margin"
                ]
            ].copy()

            # -------------------------------------------------
            # TARİH
            # -------------------------------------------------

            display_df["period_end"] = (
                pd.to_datetime(
                    display_df["period_end"]
                ).dt.strftime(
                    "%d.%m.%Y"
                )
            )

            # -------------------------------------------------
            # PARA FORMATLARI
            # -------------------------------------------------

            money_columns = [
                "revenue_b",
                "net_profit_b",
                "cash_b",
                "equity_b",
                "operating_cash_flow_b",
                "financial_debt_b",
                "net_cash_b"
            ]

            for column in money_columns:

                display_df[column] = (
                    display_df[column].apply(
                        lambda x:
                        (
                            f"{x:,.2f}"
                            .replace(",", "X")
                            .replace(".", ",")
                            .replace("X", ".")
                            if pd.notna(x)
                            else "-"
                        )
                    )
                )

            # -------------------------------------------------
            # BORÇ / ÖZKAYNAK
            # -------------------------------------------------

            display_df[
                "debt_equity"
            ] = (
                display_df[
                    "debt_equity"
                ].apply(
                    lambda x:
                    (
                        f"{x:.2f}x"
                        if pd.notna(x)
                        else "-"
                    )
                )
            )

            # -------------------------------------------------
            # NET KÂR MARJI
            # -------------------------------------------------

            display_df[
                "net_margin"
            ] = (
                display_df[
                    "net_margin"
                ].apply(
                    lambda x:
                    (
                        f"%{x:.2f}"
                        if pd.notna(x)
                        else "-"
                    )
                )
            )

            # -------------------------------------------------
            # SÜTUN İSİMLERİ
            # -------------------------------------------------

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

    except Exception as e:

        st.warning(
            f"KAP finansal trend yüklenemedi: {e}"
        )

    # ========================================================
    # TEMEL ANALİZ
    # ========================================================

    st.divider()

    st.subheader(
        "📊 Temel Analiz"
    )

    st.write(
        "🟢 Sektör:",
        fundamental.get("sector")
    )

    market_cap = fundamental.get(
        "market_cap"
    )

    if market_cap is not None:

        if market_cap >= 1_000_000:

            market_cap_text = (
                f"{market_cap / 1_000_000:.1f} Milyar TL"
            )

        elif market_cap >= 1_000_000:

            market_cap_text = (
                f"{market_cap / 1_000_000:.1f} Milyon TL"
            )

        else:

            market_cap_text = (
                f"{market_cap:,.0f} TL"
            )

    else:

        market_cap_text = "-"

    st.write(
        "💰 Piyasa Değeri:",
        market_cap_text
    )

    c1, c2 = st.columns(2)

    with c1:

        st.metric(
            "📌 F/K",
            f'{fundamental.get("pe_ratio", "-")}'
        )

    with c2:

        st.metric(
            "📌 PD/DD",
            f'{fundamental.get("pb_ratio", "-")}'
        )

    st.write(
        "📈 Kâr Marjı:",
        fundamental.get(
            "profit_margin"
        )
    )

    st.write(
        "📈 Ciro Büyümesi:",
        fundamental.get(
            "revenue_growth"
        )
    )

    st.write(
        "💳 Borç/Özsermaye:",
        fundamental.get(
            "debt_to_equity"
        )
    )

    # ========================================================
    # GÜNCEL DEĞER
    # ========================================================

    st.divider()

    st.metric(
        "💰 Güncel Değer",
        f'{sonuc["price"]:.2f} TL',
        f'{sonuc["change"]:.2f}%'
    )

    # ========================================================
    # GENEL YATIRIM SKORU
    # ========================================================

    genel_skor = (
        sonuc["score"] * 0.50
        +
        fund_score * 0.20
        +
        sonuc["momentum_60_score"] * 0.15
        +
        market_score * 0.15
    )

    st.divider()

    st.subheader(
        "🏆 Genel Yatırım Skoru"
    )

    c1, c2, c3, c4, c5 = st.columns(5)

    with c1:

        st.metric(
            "📈 Teknik Skor",
            f"{sonuc['score']}/100"
        )

    with c2:

        st.metric(
            "📊 Temel Skor",
            f"{fund_score}/100"
        )

    with c3:

        if kap_score is not None:

            st.metric(
                "🏦 KAP Finansal Skor",
                f"{kap_score:.1f}/100"
            )

        else:

            st.metric(
                "🏦 KAP Finansal Skor",
                "Veri Yok"
            )

    with c4:

        st.metric(
            "🏆 Genel Skor",
            f"{genel_skor:.0f}/100"
        )

    with c5:

        st.metric(
            "🚀 60G Momentum",
            f"{sonuc['momentum_60_score']}/100"
        )

    st.caption(
        f"🌍 Market Score: {market_score}/100"
    )

    # ========================================================
    # TEKNİK ANALİZ
    # ========================================================

    st.divider()

    st.subheader(
        f"📊 {symbol} Teknik Analizi"
    )

    c1, c2, c3, c4, c5 = st.columns(5)

    with c1:

        st.metric(
            "📍 Destek",
            f"{sonuc['support']:.2f} TL"
        )

    with c2:

        st.metric(
            "🚧 Direnç",
            f"{sonuc['resistance']:.2f} TL"
        )

    with c3:

        st.metric(
            "MACD",
            f"{sonuc['macd']:.2f}"
        )

    with c4:

        st.metric(
            "RSI",
            f"{sonuc['rsi']:.2f}"
        )

    with c5:

        st.metric(
            "📈 Teknik Skor",
            f"{sonuc['score']}/100"
        )

    st.divider()

    # ========================================================
    # TEKNİK ÖNERİ
    # ========================================================

    if "Güçlü Al" in sonuc["recommendation"]:

        st.success(
            sonuc["recommendation"]
        )

    elif "Al" in sonuc["recommendation"]:

        st.success(
            sonuc["recommendation"]
        )

    elif "Tut" in sonuc["recommendation"]:

        st.warning(
            sonuc["recommendation"]
        )

    else:

        st.error(
            sonuc["recommendation"]
        )

    st.info(
        f"Trend : {sonuc['trend']}"
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

    c1, c2, c3 = st.columns(3)

    with c1:

        st.metric(
            "EMA20",
            f"{sonuc['ema20']:.2f}"
        )

    with c2:

        st.metric(
            "EMA50",
            f"{sonuc['ema50']:.2f}"
        )

    with c3:

        st.metric(
            "EMA200",
            f"{sonuc['ema200']:.2f}"
        )

    # ========================================================
    # GENEL DEĞERLENDİRME
    # ========================================================

    st.divider()

    st.subheader(
        "📝 Genel Değerlendirme"
    )

    if sonuc["score"] >= 85:

        st.success(
            "Teknik göstergelerin büyük bölümü olumlu. "
            "Trend güçlü ve görünüm pozitif."
        )

    elif sonuc["score"] >= 70:

        st.info(
            "Teknik görünüm pozitif. "
            "Direnç seviyeleri takip edilmeli."
        )

    elif sonuc["score"] >= 55:

        st.warning(
            "Hisse nötr-pozitif görünümde. "
            "Yeni alım için teyit beklenebilir."
        )

    else:

        st.error(
            "Teknik görünüm zayıf. "
            "Risk yönetimi ön planda tutulmalı "
            "ve destek seviyeleri dikkatle takip edilmeli."
        )