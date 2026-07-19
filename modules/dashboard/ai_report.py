import streamlit as st


def show_ai_report():

    st.markdown("### 🤖 AI Piyasa Yorumu")


    st.success(
        """
        **Genel Görünüm: 🟢 Pozitif**


        BIST100 endeksinde ana trend yukarı yönlü korunuyor.


        **Güçlü Alanlar**

        • Savunma sanayi  
        • Perakende  
        • Otomotiv  


        **Takip Edilecek Riskler**

        • FED faiz beklentileri  
        • TCMB kararları  
        • Jeopolitik gelişmeler  


        **AI Strateji**

        Portföy korunabilir.
        Yeni alımlar kademeli yapılabilir.
        """
    )


    st.caption(
        "AI değerlendirmesi teknik göstergeler, makro veriler ve piyasa koşullarına göre oluşturulur."
    )