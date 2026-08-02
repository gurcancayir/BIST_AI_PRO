import streamlit as st
import pandas as pd

from modules.data.yahoo_data import get_stock_analysis
from modules.data.fundamental import (
    get_fundamental_data,
    calculate_fundamental_score
)
from modules.ai.market_ai import get_market_score


# ==========================================================
# SAYFA AYARLARI
# ==========================================================

st.set_page_config(
    page_title="AI Hisse Tarama",
    page_icon="🔎",
    layout="wide"
)

st.title("🔎 AI Hisse Tarama Merkezi")

st.write(
    "BIST hisselerini Teknik, Temel, Momentum ve Market "
    "Skorlarını birleştirerek Genel Yatırım Skoruna göre tarar."
)


# ==========================================================
# BIST 100 HAVUZU
# ==========================================================

BIST100 = [

    "AEFES",
    "AGHOL",
    "AKBNK",
    "AKCNS",
    "AKSA",
    "AKSEN",
    "ALARK",
    "ALBRK",
    "ALFAS",
    "ALTNY",

    "ARCLK",
    "ASELS",
    "ASGYO",
    "ASTOR",
    "AYDEM",
    "BIMAS",
    "BINBN",
    "BRSAN",
    "BRYAT",
    "BSOKE",

    "BTCIM",
    "CANTE",
    "CCOLA",
    "CIMSA",
    "CLEBI",
    "CWENE",
    "DOAS",
    "DOHOL",
    "DSTKF",
    "ECILC",

    "ECZYT",
    "EFORC",
    "EGEEN",
    "EKGYO",
    "ENERY",
    "ENJSA",
    "ENKAI",
    "EREGL",
    "EUPWR",
    "FENER",

    "FROTO",
    "GARAN",
    "GESAN",
    "GUBRF",
    "GWIND",
    "HALKB",
    "HEKTS",
    "ISCTR",
    "ISMEN",
    "KARSN",

    "KCAER",
    "KCHOL",
    "KONTR",
    "KONYA",
    "KORDS",
    "KOZAA",
    "KOZAL",
    "KRDMD",
    "KTLEV",
    "KUYAS",

    "MAVI",
    "MGROS",
    "MIATK",
    "MPARK",
    "ODAS",
    "ODINE",
    "OYAKC",
    "PASEU",
    "PETKM",
    "PGSUS",

    "REEDR",
    "SAHOL",
    "SASA",
    "SDTTR",
    "SISE",
    "SKBNK",
    "SMRTG",
    "SOKM",
    "TABGD",
    "TAVHL",

    "TCELL",
    "THYAO",
    "TKFEN",
    "TKNSA",
    "TMSN",
    "TOASO",
    "TSKB",
    "TTKOM",
    "TTRAK",
    "TUKAS",

    "TUPRS",
    "TURSG",
    "ULKER",
    "VAKBN",
    "VESBE",
    "VESTL",
    "YKBNK",
    "YEOTK",
    "ZOREN"

]


# ==========================================================
# RİSK DURUMU
# ==========================================================

def calculate_risk_status(daily_change, rsi, general_score):

    """
    Kısa vadeli risk değerlendirmesi.

    Günlük değişim ana kriterdir.
    RSI ve Genel Skor yardımcı kriter olarak kullanılır.
    """

    try:

        if daily_change is None:
            daily_change = 0

        if rsi is None:
            rsi = 50

        # ----------------------------------------------
        # YÜKSEK RİSK
        # ----------------------------------------------

        if daily_change <= -5:

            return "🔴 Yüksek Risk"

        if daily_change <= -3 and general_score < 75:

            return "🔴 Yüksek Risk"

        # ----------------------------------------------
        # DİKKAT
        # ----------------------------------------------

        if daily_change <= -3:

            return "🟡 Dikkat"

        if rsi >= 75:

            return "🟡 Dikkat"

        # ----------------------------------------------
        # NORMAL
        # ----------------------------------------------

        return "🟢 Normal"

    except Exception:

        return "🟡 Dikkat"


# ==========================================================
# ADAY TİPİ
# ==========================================================

def determine_candidate_type(
    technical_score,
    fundamental_score,
    momentum_score,
    general_score,
    daily_change
):

    """
    Hissenin hangi özelliğiyle öne çıktığını belirler.
    """

    try:

        # --------------------------------------------------
        # TEKNİK ÇOK GÜÇLÜ AMA FİYAT RİSKİ YÜKSEK
        # --------------------------------------------------

        if (
            technical_score >= 85
            and daily_change <= -5
        ):

            return "⚠️ Teknik Güçlü / Riskli"


        # --------------------------------------------------
        # MOMENTUM ADAYI
        # --------------------------------------------------

        if (
            momentum_score >= 85
            and technical_score >= 70
        ):

            return "🚀 Momentum"


        # --------------------------------------------------
        # TEMEL ADAYI
        # --------------------------------------------------

        if (
            fundamental_score >= 80
            and technical_score >= 60
        ):

            return "💎 Temel"


        # --------------------------------------------------
        # DENGELİ ADAY
        # --------------------------------------------------

        if (
            technical_score >= 70
            and fundamental_score >= 65
            and momentum_score >= 65
            and general_score >= 70
        ):

            return "🏆 Dengeli"


        # --------------------------------------------------
        # TEKNİK AĞIRLIKLI
        # --------------------------------------------------

        if technical_score >= 80:

            return "📈 Teknik"


        # --------------------------------------------------
        # MOMENTUM AĞIRLIKLI
        # --------------------------------------------------

        if momentum_score >= 80:

            return "🚀 Momentum"


        # --------------------------------------------------
        # TEMEL AĞIRLIKLI
        # --------------------------------------------------

        if fundamental_score >= 75:

            return "💎 Temel"


        # --------------------------------------------------
        # GENEL
        # --------------------------------------------------

        return "📊 Genel Aday"

    except Exception:

        return "📊 Genel Aday"


# ==========================================================
# FİLTRELER
# ==========================================================

st.subheader("⚙️ Tarama Ayarları")

col1, col2, col3 = st.columns(3)

with col1:

    min_score = st.slider(
        "Minimum Genel Skor",
        min_value=0,
        max_value=100,
        value=60
    )

with col2:

    min_momentum = st.slider(
        "Minimum 60G Momentum",
        min_value=0,
        max_value=100,
        value=50
    )

with col3:

    min_trend = st.slider(
        "Minimum Trend Gücü",
        min_value=0,
        max_value=100,
        value=50
    )


# ==========================================================
# SONUÇ SAYISI
# ==========================================================

max_results = st.selectbox(
    "Gösterilecek maksimum hisse",
    [10, 20, 30, 50, 100],
    index=1
)


# ==========================================================
# TARAMA BUTONU
# ==========================================================

if st.button(
    "🔎 BIST 100'ü Tara",
    width="stretch"
):

    results = []

    progress = st.progress(0)

    status = st.empty()

    total = len(BIST100)


    # ======================================================
    # MARKET SCORE
    # ======================================================

    try:

        market_score, market_reasons = get_market_score()

    except Exception as e:

        st.error(
            f"Market Score alınamadı: {e}"
        )

        st.stop()


    # ======================================================
    # MARKET SCORE GÖSTER
    # ======================================================

    st.info(
        f"🌍 Güncel Market Score: "
        f"**{market_score:.0f}/100**"
    )


    # ======================================================
    # HİSSELERİ TARA
    # ======================================================

    for i, symbol in enumerate(BIST100):

        status.write(
            f"Tarama yapılıyor: **{symbol}** "
            f"({i + 1}/{total})"
        )

        try:

            # ==================================================
            # TEKNİK ANALİZ
            # ==================================================

            analysis = get_stock_analysis(symbol)

            if analysis is None:

                progress.progress(
                    (i + 1) / total
                )

                continue


            technical_score = analysis.get(
                "score",
                0
            )


            momentum_60_score = analysis.get(
                "momentum_60_score",
                50
            )


            trend_strength = analysis.get(
                "trend_strength",
                50
            )


            daily_change = analysis.get(
                "change",
                0
            )


            rsi = analysis.get(
                "rsi",
                50
            )


            # ==================================================
            # TEMEL ANALİZ
            # ==================================================

            fundamental = get_fundamental_data(symbol)

            if fundamental is None:

                fund_score = 50

            else:

                fund_score = calculate_fundamental_score(
                    fundamental
                )


            # ==================================================
            # GENEL SKOR
            #
            # Teknik       %50
            # Temel        %20
            # 60G Momentum %15
            # Market       %15
            # ==================================================

            general_score = (

                technical_score * 0.50

                +

                fund_score * 0.20

                +

                momentum_60_score * 0.15

                +

                market_score * 0.15

            )


            general_score = max(
                0,
                min(
                    general_score,
                    100
                )
            )


            # ==================================================
            # RİSK
            # ==================================================

            risk_status = calculate_risk_status(
                daily_change,
                rsi,
                general_score
            )


            # ==================================================
            # ADAY TİPİ
            # ==================================================

            candidate_type = determine_candidate_type(
                technical_score,
                fund_score,
                momentum_60_score,
                general_score,
                daily_change
            )


            # ==================================================
            # FİLTRELER
            # ==================================================

            if general_score < min_score:

                progress.progress(
                    (i + 1) / total
                )

                continue


            if momentum_60_score < min_momentum:

                progress.progress(
                    (i + 1) / total
                )

                continue


            if trend_strength < min_trend:

                progress.progress(
                    (i + 1) / total
                )

                continue


            # ==================================================
            # KARAR
            # ==================================================

            if general_score >= 85:

                decision = "🟢 Güçlü Al"

            elif general_score >= 75:

                decision = "🟢 Al"

            elif general_score >= 60:

                decision = "🟡 Tut"

            elif general_score >= 40:

                decision = "🟠 Zayıf"

            else:

                decision = "🔴 Sat"


            # ==================================================
            # SONUÇ
            # ==================================================

            results.append({

                "Hisse": symbol,

                "Fiyat": analysis.get(
                    "price"
                ),

                "Günlük %": daily_change,

                "Genel Skor": round(
                    general_score,
                    1
                ),

                "Teknik": round(
                    technical_score,
                    1
                ),

                "Temel": round(
                    fund_score,
                    1
                ),

                "60G Momentum": round(
                    momentum_60_score,
                    1
                ),

                "Market": round(
                    market_score,
                    1
                ),

                "Trend Gücü": round(
                    trend_strength,
                    1
                ),

                "Hacim": analysis.get(
                    "volume_score"
                ),

                "RSI": rsi,

                "Trend": analysis.get(
                    "trend"
                ),

                "Risk": risk_status,

                "Aday Tipi": candidate_type,

                "Karar": decision,

                "Destek": analysis.get(
                    "support"
                ),

                "Direnç": analysis.get(
                    "resistance"
                )

            })


        except Exception as e:

            print(
                f"[TARAMA HATASI] "
                f"{symbol}: {e}"
            )


        progress.progress(
            (i + 1) / total
        )


    status.empty()

    progress.empty()


    # ======================================================
    # SONUÇLAR
    # ======================================================

    if not results:

        st.warning(
            "Seçilen kriterlere uygun hisse bulunamadı."
        )

    else:

        df = pd.DataFrame(results)


        # ==================================================
        # GENEL SKORA GÖRE SIRALA
        # ==================================================

        df = df.sort_values(
            "Genel Skor",
            ascending=False
        )


        df = df.head(
            max_results
        )


        # ==================================================
        # ÖZET
        # ==================================================

        st.success(
            f"{len(df)} hisse bulundu."
        )


        col1, col2, col3, col4 = st.columns(4)


        with col1:

            st.metric(
                "Bulunan Hisse",
                len(df)
            )


        with col2:

            st.metric(
                "En Yüksek Genel Skor",
                f"{df['Genel Skor'].max():.0f}"
            )


        with col3:

            st.metric(
                "Ortalama Genel Skor",
                f"{df['Genel Skor'].mean():.1f}"
            )


        with col4:

            st.metric(
                "Market Score",
                f"{market_score:.0f}"
            )


        # ==================================================
        # SONUÇ TABLOSU
        # ==================================================

        st.subheader(
            "🏆 BIST AI PRO Tarama Sonuçları"
        )


        st.dataframe(

            df,

            width="stretch",

            hide_index=True,

            column_config={

                "Fiyat": st.column_config.NumberColumn(
                    "Fiyat",
                    format="%.2f TL"
                ),

                "Günlük %": st.column_config.NumberColumn(
                    "Günlük %",
                    format="%.2f"
                ),

                "Genel Skor": st.column_config.NumberColumn(
                    "🏆 Genel Skor",
                    format="%.1f"
                ),

                "Teknik": st.column_config.NumberColumn(
                    "📈 Teknik",
                    format="%.1f"
                ),

                "Temel": st.column_config.NumberColumn(
                    "📊 Temel",
                    format="%.1f"
                ),

                "60G Momentum": st.column_config.NumberColumn(
                    "🚀 60G Momentum",
                    format="%.1f"
                ),

                "Market": st.column_config.NumberColumn(
                    "🌍 Market",
                    format="%.1f"
                ),

                "Trend Gücü": st.column_config.NumberColumn(
                    "📈 Trend",
                    format="%.1f"
                ),

                "Hacim": st.column_config.NumberColumn(
                    "Hacim",
                    format="%.0f"
                ),

                "RSI": st.column_config.NumberColumn(
                    "RSI",
                    format="%.2f"
                ),

                "Destek": st.column_config.NumberColumn(
                    "Destek",
                    format="%.2f"
                ),

                "Direnç": st.column_config.NumberColumn(
                    "Direnç",
                    format="%.2f"
                )

            }

        )


        # ==================================================
        # EN GÜÇLÜ 10
        # ==================================================

        st.subheader(
            "⭐ En Güçlü Hisseler"
        )


        top10 = df.head(10)


        for rank, (_, row) in enumerate(
            top10.iterrows(),
            start=1
        ):

            score = row["Genel Skor"]


            if score >= 85:

                emoji = "🟢"

            elif score >= 75:

                emoji = "🟢"

            elif score >= 60:

                emoji = "🟡"

            else:

                emoji = "🔴"


            st.write(

                f"**{rank}.** {emoji} "
                f"**{row['Hisse']}** — "
                f"Genel: **{score:.0f}** | "
                f"Teknik: **{row['Teknik']:.0f}** | "
                f"Temel: **{row['Temel']:.0f}** | "
                f"60G: **{row['60G Momentum']:.0f}** | "
                f"Market: **{row['Market']:.0f}** | "
                f"Risk: **{row['Risk']}** | "
                f"Tip: **{row['Aday Tipi']}** | "
                f"Karar: **{row['Karar']}**"

            )


        # ==================================================
        # RİSKLİ HİSSELER
        # ==================================================

        risky_df = df[
            df["Risk"].str.contains(
                "Yüksek Risk"
            )
        ]


        if not risky_df.empty:

            st.subheader(
                "⚠️ Yüksek Riskli Adaylar"
            )

            for _, row in risky_df.iterrows():

                st.warning(

                    f"**{row['Hisse']}** — "
                    f"Genel Skor: **{row['Genel Skor']:.0f}** | "
                    f"Günlük: **{row['Günlük %']:.2f}%** | "
                    f"Teknik: **{row['Teknik']:.0f}** | "
                    f"Momentum: **{row['60G Momentum']:.0f}**"
                )


        # ==================================================
        # ADAY TİPLERİ ÖZETİ
        # ==================================================

        st.subheader(
            "🎯 Aday Dağılımı"
        )


        candidate_counts = (
            df["Aday Tipi"]
            .value_counts()
        )


        cols = st.columns(
            min(
                len(candidate_counts),
                4
            )
        )


        for i, (candidate, count) in enumerate(
            candidate_counts.items()
        ):

            with cols[
                i % len(cols)
            ]:

                st.metric(
                    candidate,
                    count
                )


        # ==================================================
        # CSV
        # ==================================================

        csv = df.to_csv(
            index=False
        ).encode(
            "utf-8-sig"
        )


        st.download_button(

            "📥 Sonuçları Excel/CSV için indir",

            data=csv,

            file_name="bist_ai_genel_tarama.csv",

            mime="text/csv",

            width="stretch"

        )