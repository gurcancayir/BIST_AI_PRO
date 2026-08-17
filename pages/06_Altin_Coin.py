import streamlit as st
import pandas as pd

from modules.metals.gold_analysis import analyze_gold


st.set_page_config(
    page_title="BIST AI PRO - Altın & Coin",
    page_icon="🥇",
    layout="wide",
)

st.title("🥇 BIST AI PRO | Altın & Coin Merkezi")
st.caption(
    "Gram altın: teknik + trend + momentum + ons/kur katkısı + risk/getiri karar motoru"
)

period = st.selectbox(
    "Analiz geçmişi",
    ["1y", "2y", "5y"],
    index=1,
)

with st.spinner("Ons altın ve USD/TRY verileri analiz ediliyor..."):
    analysis = analyze_gold(period=period, interval="1d")

if not analysis.ok:
    st.error(analysis.error)
    st.stop()

r = analysis.result

# ============================================================
# ANA ÖZET
# ============================================================

c1, c2, c3, c4, c5 = st.columns(5)

c1.metric("🥇 Gram Altın", f"{r['gram_price']:,.2f} TL")
c2.metric("Ons Altın", f"{r['ons_price']:,.2f}")
c3.metric("USD/TRY", f"{r['usdtry']:,.4f}")
c4.metric("Genel Skor", f"{r['general_score']:.1f}/100")
c5.metric(
    "20G Gram Momentum",
    f"{r['gram_momentum_20']:+.2f}%" if pd.notna(r["gram_momentum_20"]) else "-"
)

st.divider()

# ============================================================
# KARAR
# ============================================================

st.subheader("🧠 SON KARAR")

decision = r["decision"]

if decision.startswith("🟢"):
    st.success(decision)
elif decision.startswith("🔴"):
    st.error(decision)
else:
    st.warning(decision)

st.write(r["reason"])

# ============================================================
# TEYİT
# ============================================================

st.subheader("🚦 İşlem Teyitleri")

a, b, c = st.columns(3)

a.metric(
    "Alım Teyidi",
    "🟢 VAR" if r["buy_confirmation"] else "🟡 YOK",
    f"{r['buy_count']}/6",
)

b.metric(
    "Satış Teyidi",
    "🔴 VAR" if r["sell_confirmation"] else "🟢 YOK",
    f"{r['sell_count']}/6",
)

c.metric("RSI", f"{r['rsi']:.1f}")

with st.expander("🔬 Teyit kontrollerini göster"):
    left, right = st.columns(2)

    buy_df = pd.DataFrame([
        {"Kontrol": k, "Durum": "🟢" if v else "🔴"}
        for k, v in r["buy_checks"].items()
    ])

    sell_df = pd.DataFrame([
        {"Kontrol": k, "Durum": "🔴" if v else "🟢"}
        for k, v in r["sell_checks"].items()
    ])

    with left:
        st.markdown("**Alım kontrolleri**")
        st.dataframe(buy_df, use_container_width=True, hide_index=True)

    with right:
        st.markdown("**Satış kontrolleri**")
        st.dataframe(sell_df, use_container_width=True, hide_index=True)

# ============================================================
# KATMANLAR
# ============================================================

st.subheader("📊 Analiz Katmanları")

x1, x2, x3, x4 = st.columns(4)
x1.metric("Teknik", f"{r['technical_score']:.1f}")
x2.metric("Trend", f"{r['trend_score']:.1f}")
x3.metric("Momentum", f"{r['momentum_score']:.1f}")
x4.metric("Risk/Getiri", f"{r['risk_reward_score']:.1f}")

# ============================================================
# ONS + KUR KATKISI
# ============================================================

st.subheader("🌍 Gram Altın Hareketinin Kaynağı")

o1, o2, o3 = st.columns(3)

o1.metric(
    "Ons 20G Katkısı",
    f"{r['ons_contribution_20']:+.2f}%"
    if pd.notna(r["ons_contribution_20"]) else "-"
)

o2.metric(
    "USD/TRY 20G Katkısı",
    f"{r['fx_contribution_20']:+.2f}%"
    if pd.notna(r["fx_contribution_20"]) else "-"
)

o3.metric(
    "Gram Altın 20G",
    f"{r['gram_momentum_20']:+.2f}%"
    if pd.notna(r["gram_momentum_20"]) else "-"
)

st.info(
    "Gram altın yaklaşık olarak Ons × USD/TRY / 31.1034768 formülüyle "
    "hesaplanır. Bu değer piyasa kuyumcu/spot satış fiyatının birebir yerine "
    "geçmez; analiz motorunun teorik gram TL referansıdır."
)

# ============================================================
# TEKNİK
# ============================================================

st.subheader("📈 Teknik Görünüm")

tech = pd.DataFrame({
    "Gösterge": [
        "EMA9", "EMA20", "EMA50", "EMA100", "EMA200",
        "RSI", "MACD", "20G Momentum", "60G Momentum",
        "ATR", "20G Volatilite"
    ],
    "Değer": [
        r["ema9"], r["ema20"], r["ema50"], r["ema100"], r["ema200"],
        r["rsi"], r["macd"], r["momentum_20"], r["momentum_60"],
        r["atr"], r["volatility_20"]
    ]
})

st.dataframe(tech, use_container_width=True, hide_index=True)

# ============================================================
# DESTEK / DİRENÇ
# ============================================================

st.subheader("🎯 Destek / Direnç")

d1, d2, d3, d4 = st.columns(4)

d1.metric("Ons Destek", f"{r['support']:,.2f}")
d2.metric("Ons Direnç", f"{r['resistance']:,.2f}")
d3.metric("Dirence Uzaklık", f"{r['resistance_distance_pct']:+.2f}%")
d4.metric(
    "Risk/Getiri",
    f"{r['risk_reward']:.2f}" if pd.notna(r["risk_reward"]) else "-"
)

st.caption(
    f"Destek bölgesi temas: {r['support_touches']} | "
    f"Direnç bölgesi temas: {r['resistance_touches']}"
)

# ============================================================
# AÇIKLAMA
# ============================================================

with st.expander("📖 Karar sistemi nasıl çalışıyor?"):
    st.markdown(
        """
### Genel Skor

**%30 Trend + %25 Momentum + %25 Teknik + %20 Risk/Getiri**

### Çok önemli

**Genel skor tek başına AL değildir.**

Sistem ayrıca:

- Alım teyidini,
- Satış teyidini,
- RSI'ı,
- Dirence uzaklığı,
- Risk/getiri oranını

kontrol eder.

### Gram altın

Gram altın tarafında iki ana değişken ayrıştırılır:

**Ons altın:** küresel altın hareketi

**USD/TRY:** TL bazındaki kur etkisi

Bu nedenle sistem yalnızca "altın yükseldi" demez;
yükselişin ons ve kur tarafındaki katkısını da gösterir.

### Veri güvenliği

Eksik veri olduğunda sistem karar üretmez.
Sabit 50 puan veya tahmini fiyat kullanmaz.
"""
    )

st.divider()

st.caption(
    f"Operasyonel kaynak: {r['data_source']} | "
    f"Referans: {r['reference_source']}"
)
st.caption(
    f"Veri zamanı: {r['data_timestamp']} | {r['data_status']}"
)
