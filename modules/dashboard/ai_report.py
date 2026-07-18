import streamlit as st


def show_ai_report():

    sol, sag = st.columns(2)

    with sol:

        st.subheader("🌍 Makro Görünüm")

        st.write("FED Beklentisi : 🟢 Güvercin")
        st.write("TCMB : 🟡 Bekle-Gör")
        st.write("Enflasyon : 🔴 Yüksek")
        st.write("Jeopolitik Risk : 🟠 Orta")
        st.write("Altın Gücü : 🟢 Güçlü")
        st.write("Petrol : 🟡 Dengeli")

    with sag:

        st.subheader("🤖 AI Yorumu")

        st.success("""
• Endeks ana trendi pozitif.

• Savunma ve perakende güçlü.

• Enerji sektörü takip edilmeli.

• Risk seviyesi orta.

• Portföy çeşitlendirmesi önemli.
""")

    st.divider()