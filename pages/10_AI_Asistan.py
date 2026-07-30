import streamlit as st

from modules.ai.assistant_ai import (
    answer_question
)

st.set_page_config(

    page_title="AI Asistan",

    page_icon="🤖",

    layout="wide"

)

st.title("🤖 AI Asistan")

st.write(
    "BIST AI PRO'nun yapay zekâ destekli finans asistanı."
)

question = st.text_input(

    "Sorunuzu yazın"

)

if question:

    answer = answer_question(

        question

    )

    st.success(answer)