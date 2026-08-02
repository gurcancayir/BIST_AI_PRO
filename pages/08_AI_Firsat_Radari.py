import streamlit as st

from modules.ai.radar_ai import get_radar_picks


# ==========================================================
# SAYFA AYARLARI
# ==========================================================

st.set_page_config(

    page_title="AI Fırsat Radarı",

    page_icon="🚀",

    layout="wide"

)


st.title("🚀 AI Fırsat Radarı")

st.write(
    "Trend + momentum + hacim + AI skoru + risk analizi ile "
    "potansiyeli yüksek hisseler"
)


# ==========================================================
# VERİLER
# ==========================================================

radar = get_radar_picks()


# ==========================================================
# FİLTRELER
# ==========================================================

col1, col2, col3, col4 = st.columns(4)


with col1:

    min_score = st.slider(

        "Minimum Fırsat Skoru",

        0,

        100,

        60

    )


with col2:

    recommendation = st.selectbox(

        "AI Kararı",

        [

            "Tümü",

            "🟢 Güçlü Al",

            "🟢 Al",

            "🟡 Tut",

            "🔴 Sat"

        ]

    )


with col3:

    sector = st.selectbox(

        "Sektör",

        [

            "Tümü",

            "Enerji",

            "Savunma",

            "Perakende",

            "Otomotiv",

            "Sanayi",

            "Banka",

            "Ulaştırma",

            "Holding",

            "Çimento",

            "Teknoloji",

            "Diğer"

        ]

    )


with col4:

    max_risk = st.slider(

        "Maksimum Risk",

        0,

        30,

        15

    )


# ==========================================================
# FİLTRELEME
# ==========================================================

filtered = []


for stock in radar:

    # Minimum fırsat skoru
    if (
        stock["risk_adjusted_score"]
        < min_score
    ):

        continue


    # Maksimum risk
    if (
        stock["risk_score"]
        > max_risk
    ):

        continue


    # AI kararı
    if recommendation != "Tümü":

        if (
            stock["recommendation"]
            != recommendation
        ):

            continue


    # Sektör
    if sector != "Tümü":

        if (
            stock["sector"]
            != sector
        ):

            continue


    filtered.append(stock)


# ==========================================================
# SONUÇ
# ==========================================================

st.subheader(
    f"🎯 {len(filtered)} fırsat bulundu"
)


if len(filtered) == 0:

    st.warning(
        "Filtrelere uygun hisse bulunamadı."
    )


else:

    for i, stock in enumerate(
        filtered,
        start=1
    ):

        opportunity = stock[
            "risk_adjusted_score"
        ]

        risk = stock[
            "risk_score"
        ]

        radar_score = stock[
            "radar_score"
        ]


        # --------------------------------------------------
        # SKOR RENKLERİ
        # --------------------------------------------------

        if opportunity >= 85:

            score_icon = "🟢"

        elif opportunity >= 70:

            score_icon = "🟡"

        else:

            score_icon = "🟠"


        if risk <= 5:

            risk_icon = "🟢"

        elif risk <= 12:

            risk_icon = "🟡"

        else:

            risk_icon = "🔴"


        # --------------------------------------------------
        # KART
        # --------------------------------------------------

        with st.container():

            st.markdown(
                f"## {i}. {stock['symbol']}"
            )


            col1, col2, col3 = st.columns(
                [3, 2, 2]
            )


            # ==============================================
            # SOL
            # ==============================================

            with col1:

                st.write(
                    f"**Sektör:** "
                    f"{stock['sector']}"
                )

                st.write(
                    f"💰 **Fiyat:** "
                    f"{stock['price']} TL"
                )

                st.write(
                    f"📈 **Günlük:** "
                    f"%{stock['change']}"
                )

                st.write(
                    f"📊 **Trend:** "
                    f"{stock['trend']}"
                )

                st.write(
                    f"🧠 **AI Kararı:** "
                    f"{stock['recommendation']}"
                )


            # ==============================================
            # ORTA
            # ==============================================

            with col2:

                st.metric(

                    "🎯 Fırsat Skoru",

                    f"{score_icon} "
                    f"{opportunity}/100"

                )

                st.metric(

                    "🚀 Ham Radar",

                    f"{radar_score}/100"

                )

                st.metric(

                    "⚠️ Risk",

                    f"{risk_icon} "
                    f"{risk}/30"

                )


            # ==============================================
            # SAĞ
            # ==============================================

            with col3:

                st.metric(

                    "AI Score",

                    f"{stock['score']}/100"

                )

                st.metric(

                    "Trend Gücü",

                    f"{stock['trend_strength']}/100"

                )

                st.metric(

                    "Momentum",

                    f"{stock['momentum_score']}/100"

                )


            # ------------------------------------------------
            # TEKNİK BİLGİLER
            # ------------------------------------------------

            st.write(

                f"**Hacim:** "
                f"{stock['volume_score']}/100   |   "

                f"**RSI:** "
                f"{stock['rsi']}   |   "

                f"**Destek:** "
                f"{stock['support']}   |   "

                f"**Direnç:** "
                f"{stock['resistance']}"

            )


            # ------------------------------------------------
            # RADAR NEDENLERİ
            # ------------------------------------------------

            st.write(
                "**🔎 Radar Analizi**"
            )


            if stock["reasons"]:

                for reason in stock[
                    "reasons"
                ]:

                    st.write(
                        f"• {reason}"
                    )

            else:

                st.write(
                    "Yeterli açıklama verisi yok."
                )


            st.divider()