import streamlit as st


def show_stock_ai_signal(df):

    st.divider()

    st.subheader("📈 Hisse AI Analizi")


    if df.empty:

        st.info(
            "Analiz için hisse bulunamadı."
        )

        return



    results = []


    for hisse in df["symbol"]:

        # Şimdilik örnek AI değerleri
        # Daha sonra RSI, MACD, hacim verileri bağlanacak

        if hisse in ["BIMAS", "ASELS", "FROTO"]:

            trend = "🟢 Yukarı"
            rsi = 62
            score = 88
            signal = "TUT"

        elif hisse in ["TUPRS", "MGROS"]:

            trend = "🟡 Yatay"
            rsi = 51
            score = 74
            signal = "İZLE"

        else:

            trend = "🟢 Pozitif"
            rsi = 58
            score = 80
            signal = "TUT"



        results.append(

            [
                hisse,
                trend,
                rsi,
                score,
                signal
            ]

        )



    tablo = st.dataframe(

        results,

        column_config={

            "0":"Hisse",
            "1":"Trend",
            "2":"RSI",
            "3":"AI Skor",
            "4":"Sinyal"

        },

        use_container_width=True

    )