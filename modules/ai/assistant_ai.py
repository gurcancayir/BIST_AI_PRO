import streamlit as st

from modules.ai.market_ai import (
    get_market_score,
    get_market_comment
)

from modules.ai.ai_picker import (
    get_top_ai_picks
)

from modules.ai.radar_ai import (
    get_radar_picks
)


def answer_question(question):

    question = question.lower()


    # ----------------------------------------------------
    # PORTFÖY
    # ----------------------------------------------------

    if "portföy" in question:

        return (
            "Portföy analizi yakında eklenecek."
        )


    # ----------------------------------------------------
    # PİYASA
    # ----------------------------------------------------

    elif "borsa" in question or "piyasa" in question:

        score, reasons = get_market_score()

        return f"""
Genel Piyasa Puanı

{score}/100

{get_market_comment(score)}

Öne çıkan nedenler

- """ + "\n- ".join(reasons)


    # ----------------------------------------------------
    # HİSSE
    # ----------------------------------------------------

    elif "hisse" in question:

        picks = get_top_ai_picks()

        cevap = "Bugün AI tarafından öne çıkarılan hisseler\n\n"

        for s in picks[:5]:

            cevap += f"""
{s["symbol"]}

AI Gücü

{s["recommendation_score"]}/100

"""

        return cevap


    # ----------------------------------------------------
    # RADAR
    # ----------------------------------------------------

    elif "radar" in question:

        radar = get_radar_picks()

        cevap = "Radar hisseleri\n\n"

        for r in radar:

            cevap += f"""
{r["symbol"]}

Radar Gücü

{r["radar_score"]}/100

"""

        return cevap


    return (
        "Soruyu anlayamadım."
    )