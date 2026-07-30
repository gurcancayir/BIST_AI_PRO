import streamlit as st

from modules.ai.radar_ai import get_radar_picks

st.set_page_config(
    page_title="AI Fırsat Radarı",
    page_icon="🚀",
    layout="wide"
)

st.title("🚀 AI Fırsat Radarı")

st.write(
    "Yapay zekâ tarafından potansiyeli yüksek bulunan hisseler"
)

# ==========================================
# FİLTRELER
# ==========================================

col1, col2, col3 = st.columns(3)

with col1:

    min_score = st.slider(

        "Minimum Radar Skoru",

        0,

        100,

        70

    )

with col2:

    recommendation = st.selectbox(

        "AI Kararı",

        [

            "Tümü",

            "🟢 Güçlü Al",

            "🟡 Al",

            "⚪ Tut",

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

            "Ulaştırma"

        ]

    )

radar = get_radar_picks()
# ==========================================
# FİLTRELEME
# ==========================================

filtered = []

for stock in radar:

    # Minimum skor
    if stock["radar_score"] < min_score:
        continue

    # AI Kararı
    if recommendation != "Tümü":

        if stock["recommendation"] != recommendation:
            continue

    # Sektör
    if sector != "Tümü":

        if stock["sector"] != sector:
            continue

    filtered.append(stock)

radar = filtered

if len(radar) == 0:

    st.warning("Uygun hisse bulunamadı.")

else:

    for i, stock in enumerate(radar, start=1):

        score = stock["radar_score"]

        if score >= 80:
            color = "🟢"

        elif score >= 60:
            color = "🟡"

        else:
            color = "🔴"

        with st.container():

            col1, col2 = st.columns([3,1])

            with col1:

                st.subheader(
                    f"{i}. {stock['symbol']}"
                )

                st.write(
                    f"**Sektör:** {stock['sector']}"
                )

                st.write(
                    f"**AI Kararı:** {stock['recommendation']}"
                )
                st.write(
                    f"💰 **Fiyat:** {stock['price']} TL"
                )

                st.write(
                    f"📈 **Günlük:** %{stock['change']}"
                )

                st.write(
                    f"📊 **Trend:** {stock['trend']}"
                )

                st.write(
                    f"⚡ **Momentum:** {stock['momentum_score']}/100"
                )

                st.write(
                    f"📦 **Hacim:** {stock['volume_score']}/100"
                )
                st.write("**Radar Nedenleri**")

                if stock["reasons"]:

                    for r in stock["reasons"]:

                        st.write(f"✔ {r}")

                else:

                    st.write("Yeterli veri yok")

            with col2:

                st.metric(
                    "🚀 Radar",
                    f"{score}/100"
                )

                st.metric(
                    "🧠 AI Score",
                    f"{stock['score']}/100"
                )

                st.metric(
                    "📈 Trend Gücü",
                    f"{stock['trend_strength']}/100"
                )
        st.divider()