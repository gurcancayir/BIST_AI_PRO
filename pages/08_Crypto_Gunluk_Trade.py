# ============================================================
# BIST AI PRO
# 08_Crypto_Gunluk_Trade.py
#
# CRYPTO GÜNLÜK TRADE
# 15m + 1h
# ============================================================

import streamlit as st
import pandas as pd

from crypto_engine import (
    get_daily_candidates,
    get_update_time,
)


# ============================================================
# SAYFA AYARLARI
# ============================================================

st.set_page_config(
    page_title="Crypto Günlük Trade",
    page_icon="⚡",
    layout="wide",
)


# ============================================================
# BAŞLIK
# ============================================================

st.title("⚡ Crypto Günlük Trade")

st.caption(
    "15 dakika + 1 saatlik teknik yapı • "
    "Momentum • Hacim • Trend • BTC rejimi"
)

st.info(
    "Bu sayfa yatırım tavsiyesi üretmez. "
    "Gün içi işlem için teknik olarak öne çıkan "
    "5 kripto adayı sıralar."
)


# ============================================================
# GÜNCELLE
# ============================================================

if st.button(
    "🔄 Crypto Verilerini Yenile",
    use_container_width=True,
):

    st.cache_data.clear()

    st.rerun()


# ============================================================
# VERİ
# ============================================================

with st.spinner(
    "Crypto piyasası taranıyor..."
):

    df = get_daily_candidates(
        top_n=5
    )


# ============================================================
# DURUM
# ============================================================

if df.empty:

    st.error(
        "Crypto verisi alınamadı veya uygun aday bulunamadı."
    )

    st.stop()


# ============================================================
# ÜST BİLGİ
# ============================================================

c1, c2, c3 = st.columns(3)

with c1:

    st.metric(
        "🎯 Aday Sayısı",
        len(df),
    )

with c2:

    st.metric(
        "🥇 En Yüksek Skor",
        f"{df['score'].max():.1f}",
    )

with c3:

    st.metric(
        "🕐 Son Güncelleme",
        get_update_time(),
    )


st.divider()


# ============================================================
# ADAYLAR
# ============================================================

st.subheader(
    "🏆 Günlük Trade İçin En Güçlü 5 Aday"
)


for _, row in df.iterrows():

    score = float(
        row["score"]
    )

    if score >= 80:
        status = "🟢 GÜÇLÜ TRADE ADAYI"

    elif score >= 70:
        status = "🟢 TRADE ADAYI"

    elif score >= 60:
        status = "🟡 İZLE"

    else:
        status = "🔴 ZAYIF"


    with st.container(
        border=True
    ):

        # ----------------------------------------------------
        # BAŞLIK
        # ----------------------------------------------------

        col1, col2, col3 = st.columns(
            [1.2, 5, 1.5]
        )

        with col1:

            st.markdown(
                f"## #{int(row['rank'])}"
            )

        with col2:

            st.markdown(
                f"## {row['symbol']}"
            )

            st.caption(
                f"{row['timeframe']} • {status}"
            )

        with col3:

            st.metric(
                "Crypto Score",
                f"{score:.1f}",
            )


        # ----------------------------------------------------
        # FİYAT
        # ----------------------------------------------------

        st.markdown("### 📊 Teknik Görünüm")

        c1, c2, c3, c4, c5 = st.columns(5)

        with c1:

            st.metric(
                "Fiyat",
                f"{row['price']:,.6f}",
            )

        with c2:

            st.metric(
                "24s Değişim",
                f"{row['change_24h']:+.2f}%",
            )

        with c3:

            st.metric(
                "Trend",
                f"{row['trend']:.1f}",
            )

        with c4:

            st.metric(
                "Momentum",
                f"{row['momentum']:+.2f}%",
            )

        with c5:

            st.metric(
                "RSI",
                f"{row['rsi']:.1f}",
            )


        # ----------------------------------------------------
        # HACİM / RİSK
        # ----------------------------------------------------

        c1, c2, c3, c4 = st.columns(4)

        with c1:

            st.metric(
                "Hacim Oranı",
                f"{row['volume_ratio']:.2f}x",
            )

        with c2:

            st.metric(
                "ATR",
                f"{row['atr_pct']:.2f}%",
            )

        with c3:

            st.metric(
                "BTC Skoru",
                f"{row['btc_score']:.1f}",
            )

        with c4:

            st.metric(
                "BTC Rejimi",
                row["btc_label"],
            )


        # ----------------------------------------------------
        # AI YORUM
        # ----------------------------------------------------

        if score >= 80:

            yorum = (
                f"**{row['symbol']}**, günlük trade açısından "
                f"güçlü teknik yapı gösteriyor. Trend skoru "
                f"{row['trend']:.1f}, momentumu "
                f"{row['momentum']:+.2f}%. "
                f"Hacim oranı {row['volume_ratio']:.2f}x. "
                "Pozisyon alınmadan önce kısa zaman diliminde "
                "fiyat teyidi ve risk/ödül kontrolü yapılmalı."
            )

        elif score >= 70:

            yorum = (
                f"**{row['symbol']}** günlük trade için "
                "izlenmeye değer bir aday. Teknik yapı olumlu "
                "olmakla birlikte giriş için ek teyit beklemek "
                "daha sağlıklı olabilir."
            )

        elif score >= 60:

            yorum = (
                f"**{row['symbol']}** teknik olarak izleme "
                "listesinde tutulabilir ancak mevcut skor "
                "güçlü trade sinyali seviyesinde değil."
            )

        else:

            yorum = (
                f"**{row['symbol']}** mevcut teknik verilerle "
                "güçlü günlük trade adayı görünümünde değil."
            )


        st.markdown(
            f"🤖 **AI Yorumu:** {yorum}"
        )


# ============================================================
# ALT NOT
# ============================================================

st.divider()

st.caption(
    "Veri kaynağı: Binance Public Market Data • "
    "Motor: Crypto AI Pro • "
    "Skorlar otomatik yatırım tavsiyesi değildir."
)