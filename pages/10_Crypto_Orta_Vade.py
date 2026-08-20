# ============================================================
# BIST AI PRO
# 10_Crypto_Orta_Vade.py
#
# CRYPTO ORTA VADE
# 4H + 1D TREND
# ============================================================

import streamlit as st

from crypto_engine import (
    get_medium_term_candidates,
    get_update_time,
)


# ============================================================
# SAYFA AYARLARI
# ============================================================

st.set_page_config(
    page_title="Crypto Orta Vade",
    page_icon="📊",
    layout="wide",
)


# ============================================================
# BAŞLIK
# ============================================================

st.title("📊 Crypto Orta Vade")

st.caption(
    "4 saat + günlük trend • Momentum • Hacim • RSI • BTC rejimi"
)

st.info(
    "Bu sayfa orta vadede teknik olarak öne çıkan "
    "5 kripto adayını gösterir. Skorlar yatırım tavsiyesi değildir."
)


# ============================================================
# YENİLE
# ============================================================

if st.button(
    "🔄 Crypto Verilerini Yenile",
    use_container_width=True,
):

    st.cache_data.clear()
    st.rerun()


# ============================================================
# VERİLERİ AL
# ============================================================

with st.spinner(
    "Orta vadeli crypto piyasası taranıyor..."
):

    df = get_medium_term_candidates(
        top_n=5
    )


# ============================================================
# VERİ YOK
# ============================================================

if df is None or df.empty:

    st.error(
        "Uygun orta vadeli crypto adayı bulunamadı."
    )

    st.info(
        "Crypto motorunun veri bağlantısını ve "
        "crypto_engine.py dosyasını kontrol et."
    )

    st.stop()


# ============================================================
# ÖZET
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
        "🕐 Güncelleme",
        get_update_time(),
    )


st.divider()


# ============================================================
# ADAYLAR
# ============================================================

st.subheader(
    "🏆 Orta Vadede En Güçlü 5 Coin"
)


for _, row in df.iterrows():

    score = float(row["score"])


    # --------------------------------------------------------
    # DURUM
    # --------------------------------------------------------

    if score >= 80:

        status = "🟢 GÜÇLÜ ADAY"

    elif score >= 70:

        status = "🟢 POZİTİF"

    elif score >= 60:

        status = "🟡 İZLE"

    else:

        status = "🔴 ZAYIF"


    # --------------------------------------------------------
    # HABER KARTI
    # --------------------------------------------------------

    with st.container(border=True):

        # ----------------------------------------------------
        # SIRALAMA
        # ----------------------------------------------------

        c1, c2, c3 = st.columns(
            [1, 5, 1.5]
        )

        with c1:

            st.markdown(
                f"## #{int(row['rank'])}"
            )

        with c2:

            st.markdown(
                f"## {row['symbol']}"
            )

            st.caption(
                f"{row['timeframe']} • {status}"
            )

        with c3:

            st.metric(
                "Crypto Score",
                f"{score:.1f}",
            )


        # ----------------------------------------------------
        # TEKNİK VERİLER
        # ----------------------------------------------------

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
        # İKİNCİ TEKNİK SATIR
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
        # AI YORUMU
        # ----------------------------------------------------

        if score >= 80:

            yorum = (
                f"**{row['symbol']}**, orta vadede güçlü "
                f"bir teknik yapı sergiliyor. Trend skoru "
                f"{row['trend']:.1f}, momentum "
                f"{row['momentum']:+.2f}% ve hacim oranı "
                f"{row['volume_ratio']:.2f}x seviyesinde. "
                "Ana trend korunuyorsa izleme listesinde "
                "öncelikli aday olarak değerlendirilebilir."
            )

        elif score >= 70:

            yorum = (
                f"**{row['symbol']}** orta vadede olumlu "
                "bir görünüme sahip. Trend ve momentum "
                "destekliyor ancak daha güçlü bir fiyat "
                "teyidi tercih edilebilir."
            )

        elif score >= 60:

            yorum = (
                f"**{row['symbol']}** orta vadeli izleme "
                "listesine alınabilir. Teknik görünüm "
                "karışık ancak tamamen negatif değil."
            )

        else:

            yorum = (
                f"**{row['symbol']}** mevcut teknik verilerle "
                "orta vadede güçlü aday seviyesinde değil."
            )


        st.markdown(
            f"🤖 **AI Yorumu:** {yorum}"
        )


# ============================================================
# ALT BİLGİ
# ============================================================

st.divider()

st.caption(
    "Veri kaynağı: Crypto piyasa verileri • "
    "Crypto AI Pro • Skorlar otomatik yatırım tavsiyesi değildir."
)