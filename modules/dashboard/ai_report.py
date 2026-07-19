import streamlit as st

from modules.ai.market_ai import get_market_score
from modules.data.macro_data import get_macro_data
from modules.dashboard.sector_strength import calculate_sector_strength


def show_ai_report():

    score, reasons = get_market_score()

    macro = get_macro_data()


    sektorler = {

        "Enerji": [
            "AKSEN.IS",
            "ENJSA.IS",
            "TUPRS.IS",
            "ODAS.IS",
            "AYDEM.IS"
        ],

        "Banka": [
            "AKBNK.IS",
            "GARAN.IS",
            "YKBNK.IS",
            "ISCTR.IS",
            "HALKB.IS"
        ],

        "Savunma": [
            "ASELS.IS",
            "OTKAR.IS",
            "ASTOR.IS",
            "SDTTR.IS",
            "KONTR.IS"
        ]

    }


    enerji = calculate_sector_strength(
        sektorler["Enerji"]
    )

    banka = calculate_sector_strength(
        sektorler["Banka"]
    )

    savunma = calculate_sector_strength(
        sektorler["Savunma"]
    )


    st.markdown("### 🤖 AI Piyasa Yorumu")


    if score >= 80:

        st.success(f"""
### 🟢 Güçlü Pozitif

AI Skoru: **{score}/100**

• BIST görünümü güçlü.

• USD/TL: %{macro["usd_change"]}

• Ons Altın: %{macro["gold_change"]}

• Brent: %{macro["brent_change"]}


### AI Strateji

Kademeli alımlar sürdürülebilir.

Mevcut pozisyonlar korunabilir.
""")


    elif score >= 60:

        st.info(f"""
### 🟡 Pozitif

AI Skoru: **{score}/100**

Makro görünüm dengeli.

USD ve emtia tarafı takip edilmeli.

Yeni alımlar seçici yapılabilir.
""")


    else:

        st.warning(f"""
### 🔴 Temkinli

AI Skoru: **{score}/100**

Risk göstergelerinde bozulma görülüyor.

Nakit oranı artırılması değerlendirilebilir.
""")


    st.markdown("### 📊 Sektör Durumu")


    st.write(
        f"""
⚡ Enerji: %{enerji}

🏦 Banka: %{banka}

🛡️ Savunma: %{savunma}
"""
    )


    st.markdown("### 📌 Skoru Etkileyen Faktörler")


    for reason in reasons:

        st.write(
            f"• {reason}"
        )