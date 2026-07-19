import streamlit as st

from modules.data.macro_data import get_price


def calculate_ai_score(change):

    score = 50


    # Momentum
    if change >= 3:
        score += 30

    elif change >= 1:
        score += 15

    elif change <= -3:
        score -= 30

    elif change <= -1:
        score -= 15


    return max(0, min(score, 100))



def show_ai_top_stocks():

    st.markdown("### 🏆 AI Top Hisseler")


    hisseler = {

        "AKSEN": "AKSEN.IS",
        "BIMAS": "BIMAS.IS",
        "MGROS": "MGROS.IS",
        "TUPRS": "TUPRS.IS",
        "THYAO": "THYAO.IS",
        "ASTOR": "ASTOR.IS",
        "ENKAI": "ENKAI.IS",
        "CCOLA": "CCOLA.IS",
        "KCHOL": "KCHOL.IS",
        "FROTO": "FROTO.IS"

    }


    sonuc = []


    for isim, sembol in hisseler.items():

        fiyat, degisim = get_price(sembol)


        try:

            score = calculate_ai_score(
                float(degisim)
            )


            sonuc.append({

                "Hisse": isim,

                "Fiyat": fiyat,

                "Değişim": degisim,

                "Score": score

            })


        except:

            pass



    sonuc = sorted(
        sonuc,
        key=lambda x:x["Score"],
        reverse=True
    )



    col1,col2,col3,col4,col5 = st.columns(5)


    kolonlar = [
        col1,
        col2,
        col3,
        col4,
        col5
    ]


    for kolon, hisse in zip(kolonlar, sonuc[:5]):

        with kolon:

            if hisse["Score"] >= 80:

                durum="🟢"

            elif hisse["Score"] >=60:

                durum="🟡"

            else:

                durum="🔴"



            st.metric(

                f'{durum} {hisse["Hisse"]}',

                f'{hisse["Score"]}/100',

                f'%{hisse["Değişim"]}'

            )