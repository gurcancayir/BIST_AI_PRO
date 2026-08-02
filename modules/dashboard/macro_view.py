import streamlit as st

from modules.data.macro_data import get_macro_data


# =========================================================
# YARDIMCI FONKSİYONLAR
# =========================================================

def market_status(change, positive_text, negative_text):

    if change is None:
        return "⚪ Veri Yok"

    if change > 0.5:
        return f"🟢 {positive_text}"

    elif change < -0.5:
        return f"🔴 {negative_text}"

    else:
        return "🟡 Dengeli"


def gold_status(change):

    if change is None:
        return "⚪ Veri Yok"

    if change > 1:
        return "🟢 Güçlü"

    elif change < -1:
        return "🔴 Zayıf"

    else:
        return "🟡 Dengeli"


def oil_status(change):

    if change is None:
        return "⚪ Veri Yok"

    if change > 1:
        return "🔴 Yükseliyor"

    elif change < -1:
        return "🟢 Geriliyor"

    else:
        return "🟡 Dengeli"


def data_status(value):

    if value is None:
        return "⚪ Veri Yok"

    return str(value)


# =========================================================
# MAKRO GÖRÜNÜM
# =========================================================

def show_macro_view():

    st.markdown("### 🌍 Makro Görünüm")

    macro = get_macro_data()


    # =====================================================
    # VERİLER
    # =====================================================

    bist_change = macro.get("bist_change")

    usd_change = macro.get("usd_change")

    gold_change = macro.get("gold_change")

    brent_change = macro.get("brent_change")


    # =====================================================
    # MAKRO DURUMLAR
    # =====================================================

    # FED
    fed_value = macro.get("fed")

    if fed_value is None:
        fed_status = "⚪ Veri Yok"
    else:
        fed_status = fed_value


    # TCMB
    tcmb_value = macro.get("tcmb")

    if tcmb_value is None:
        tcmb_status = "⚪ Veri Yok"
    else:
        tcmb_status = tcmb_value


    # ENFLASYON
    inflation_value = macro.get("inflation")

    if inflation_value is None:
        inflation_status = "⚪ Veri Yok"
    else:
        inflation_status = inflation_value


    # JEOPOLİTİK
    geopolitical_value = macro.get("geopolitical")

    if geopolitical_value is None:
        geopolitical_status = "⚪ Veri Yok"
    else:
        geopolitical_status = geopolitical_value


    # ALTIN
    gold_status_value = gold_status(
        gold_change
    )


    # PETROL
    oil_status_value = oil_status(
        brent_change
    )


    # =====================================================
    # PANEL
    # =====================================================

    col1, col2 = st.columns(2)


    # -----------------------------------------------------
    # SOL KOLON
    # -----------------------------------------------------

    with col1:

        st.info(
            f"""
            **🇺🇸 FED Beklentisi**

            {fed_status}
            """
        )

        st.info(
            f"""
            **🇹🇷 TCMB Politikası**

            {tcmb_status}
            """
        )

        st.info(
            f"""
            **📈 Enflasyon**

            {inflation_status}
            """
        )


    # -----------------------------------------------------
    # SAĞ KOLON
    # -----------------------------------------------------

    with col2:

        st.info(
            f"""
            **🌍 Jeopolitik Risk**

            {geopolitical_status}
            """
        )

        st.info(
            f"""
            **🥇 Altın Gücü**

            {gold_status_value}
            """
        )

        st.info(
            f"""
            **🛢 Petrol**

            {oil_status_value}
            """
        )


    # =====================================================
    # GERÇEK PİYASA VERİLERİ
    # =====================================================

    st.markdown("#### 📊 Piyasa Göstergeleri")

    c1, c2, c3, c4 = st.columns(4)


    # BIST
    with c1:

        bist = macro.get("bist")

        if bist is not None:

            st.metric(
                "BIST 100",
                f"{bist:,.2f}",
                f"{bist_change:+.2f}%"
                if bist_change is not None
                else None
            )

        else:

            st.metric(
                "BIST 100",
                "Veri Yok"
            )


    # USD
    with c2:

        usd = macro.get("usd")

        if usd is not None:

            st.metric(
                "USD/TRY",
                f"{usd:,.2f}",
                f"{usd_change:+.2f}%"
                if usd_change is not None
                else None
            )

        else:

            st.metric(
                "USD/TRY",
                "Veri Yok"
            )


    # Gram Altın
    with c3:

        gram = macro.get("gram")

        if gram is not None:

            st.metric(
                "Gram Altın",
                f"{gram:,.2f} TL",
                f"{gold_change:+.2f}%"
                if gold_change is not None
                else None
            )

        else:

            st.metric(
                "Gram Altın",
                "Veri Yok"
            )


    # Brent
    with c4:

        brent = macro.get("brent")

        if brent is not None:

            st.metric(
                "Brent",
                f"${brent:,.2f}",
                f"{brent_change:+.2f}%"
                if brent_change is not None
                else None
            )

        else:

            st.metric(
                "Brent",
                "Veri Yok"
            )


    # =====================================================
    # ALT BİLGİ
    # =====================================================

    st.caption(
        "Piyasa fiyatları Yahoo Finance verilerinden alınır. "
        "FED, TCMB, enflasyon ve jeopolitik göstergeleri için "
        "ayrı resmi veri kaynakları henüz bağlanmamıştır."
    )