import streamlit as st

st.set_page_config(page_title="Hisse Karar Açıklayıcı V2", page_icon="🧭", layout="wide")
st.title("🧭 Hisse Analizi — Karar Açıklayıcı V2")
st.caption("Genel karar, vade puanı ve işlem teyidini birbirinden ayırır; mevcut karar eşiklerini değiştirmez.")

st.info("Bu sayfa mevcut Hisse Analiz motorunun yerine geçmez. Skorların nasıl okunacağını açıklayan yardımcı ekrandır.")

st.subheader("Skorları gir / sonuç ekranındaki değerleri karşılaştır")
c1, c2, c3 = st.columns(3)
with c1:
    general = st.number_input("Genel Skor (0–100)", min_value=0.0, max_value=100.0, value=65.0, step=0.1)
with c2:
    vade = st.number_input("Seçili Vade Puanı (0–100)", min_value=0.0, max_value=100.0, value=88.1, step=0.1)
with c3:
    confidence = st.number_input("Güven (0–100)", min_value=0.0, max_value=100.0, value=66.0, step=0.1)

c4, c5, c6 = st.columns(3)
with c4:
    coverage = st.slider("Veri Kapsamı (%)", min_value=0, max_value=100, value=75)
with c5:
    quality = st.selectbox("Kalite", ["A", "B", "C", "D", "Veri yok"], index=2)
with c6:
    buy_count = st.selectbox("Alım Teyit Skoru", ["0/6", "1/6", "2/6", "3/6", "4/6", "5/6", "6/6"], index=5)

buy_confirmation = st.radio("Alım Teyidi", ["VAR", "YOK"], horizontal=True, index=0)
sell_confirmation = st.radio("Satış Teyidi", ["VAR", "YOK"], horizontal=True, index=1)
decline_signal = st.radio("Düşüş Sinyali", ["VAR", "YOK"], horizontal=True, index=1)

if general > 80:
    decision = "🟢 AL"
    threshold = "Genel skor 80'in üzerinde."
elif general > 75:
    decision = "🟡 AL ADAYI"
    threshold = "Genel skor 75'in üzerinde ancak 80'i aşmıyor."
else:
    decision = "🟡 TEYİT"
    threshold = "Genel skor 75'in üzerinde değil; genel AL eşiği karşılanmadı."

st.divider()
st.subheader("Sonuçların ayrı ayrı yorumu")
m1, m2, m3 = st.columns(3)
m1.metric("Genel Karar", decision)
m2.metric("Seçili Vade Puanı", f"{vade:.1f}/100")
m3.metric("Güven", f"{confidence:.1f}/100")

st.markdown(f"**Genel karar gerekçesi:** {threshold}")
if buy_confirmation == "VAR":
    st.success(f"**Teknik/işlem teyidi: VAR ({buy_count}).** Bu teyit genel skor eşiğini otomatik olarak geçersiz kılmaz.")
else:
    st.warning(f"**Teknik/işlem teyidi: YOK ({buy_count}).** Genel skor ayrıca değerlendirilir.")

if vade >= 80 and general <= 75:
    st.warning("**Fark açıklaması:** Seçili vade puanı yüksek, ancak genel skor AL ADAYI eşiğini karşılamıyor. Bu iki puan farklı göstergeleri veya ağırlıkları temsil ediyor olabilir. Genel skor formülü ve eksik veri etkisi kaynak koddan ayrıca doğrulanmalıdır.")
elif vade < 80 and general > 75:
    st.info("Genel skor eşiği karşılanıyor; seçili vade puanı daha düşük. İşlem ufku ve risk planı ayrıca incelenmeli.")
else:
    st.info("Vade puanı ve genel skor birlikte okunmalı; aynı ölçüm oldukları varsayılmamalıdır.")

if coverage < 100:
    st.warning(f"Veri kapsamı %{coverage}. Eksik kapsamın skora nasıl etki ettiği doğrulanmadan bu değerin doğrudan puan kesintisi olduğu varsayılmamalıdır.")
if quality in ["C", "D", "Veri yok"]:
    st.warning(f"Kalite sınıfı {quality}. Karar güvenilirliği için eksik veya düşük kaliteli veri alanlarını inceleyin.")

st.markdown("### İşlem teyitleri")
st.write(f"- Alım teyidi: **{buy_confirmation}**")
st.write(f"- Satış teyidi: **{sell_confirmation}**")
st.write(f"- Düşüş sinyali: **{decline_signal}**")

if sell_confirmation == "VAR":
    st.error("Satış teyidi var. Portföydeki pozisyon için stop, destek ve pozisyon büyüklüğüyle birlikte değerlendirin.")
elif decline_signal == "VAR":
    st.warning("Düşüş sinyali var; tek başına kesin satış emri değildir.")
elif buy_confirmation == "VAR":
    st.success("Alım teyidi olumlu, ancak genel karar TEYİT ise bu ekran otomatik AL önermez. Giriş fiyatı, stop ve risk/getiri ayrıca kontrol edilmelidir.")
else:
    st.info("Net alım teyidi yok; yeni pozisyon öncesi bekle/izle yaklaşımı değerlendirilebilir.")

st.caption("Not: Bu yardımcı ekran yatırım tavsiyesi değildir ve ana analiz motorunun hesaplamalarını değiştirmez. Skorların gerçek formülünü değiştirmek için ana dosyadaki skor üretim fonksiyonları ayrıca düzenlenip test edilmelidir.")
