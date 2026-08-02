import streamlit as st
import pandas as pd

from modules.data.yahoo_data import get_stock_analysis
from modules.data.fundamental import (
    get_fundamental_data,
    calculate_fundamental_score
)
from modules.ai.market_ai import get_market_score


# =========================================================
# SAYFA AYARLARI
# =========================================================

st.set_page_config(
    page_title="Karar Destek",
    page_icon="🧠",
    layout="wide"
)

st.title("🧠 Karar Destek Sistemi")

st.caption(
    "Teknik + Temel + Momentum + Trend + Piyasa verilerini "
    "birleştirerek yatırım karar desteği üretir."
)


# =========================================================
# GÜVENLİ SAYI
# =========================================================

def safe_float(value):

    try:
        return float(value)
    except:
        return 0.0


# =========================================================
# MARKET SCORE
# =========================================================

@st.cache_data(ttl=1800)
def get_market():

    try:
        score, reasons = get_market_score()
        return score, reasons

    except Exception as e:

        print("MARKET SCORE HATASI:", e)

        return 50, []


# =========================================================
# TEYİT KONTROLÜ
# =========================================================

def teyit_kontrolu(
    fiyat,
    destek,
    direnç,
    rsi,
    gunluk,
    teknik,
    momentum,
    trend
):

    kontroller = []

    # -----------------------------------------------------
    # 1. DESTEK
    # -----------------------------------------------------

    if destek > 0 and fiyat > 0:

        if fiyat >= destek:

            kontroller.append({
                "Teyit": "Destek üzerinde tutunma",
                "Durum": True,
                "Yorum": (
                    f"Fiyat {destek:.2f} TL desteğinin üzerinde."
                )
            })

        else:

            kontroller.append({
                "Teyit": "Destek üzerinde tutunma",
                "Durum": False,
                "Yorum": (
                    f"Fiyat {destek:.2f} TL desteğinin altında."
                )
            })

    else:

        kontroller.append({
            "Teyit": "Destek üzerinde tutunma",
            "Durum": True,
            "Yorum": "Destek verisi bulunamadı."
        })

    # -----------------------------------------------------
    # 2. RSI
    # -----------------------------------------------------

    if rsi <= 70:

        kontroller.append({
            "Teyit": "RSI uygun bölge",
            "Durum": True,
            "Yorum": (
                f"RSI {rsi:.1f}; aşırı alım bölgesinde değil."
            )
        })

    else:

        kontroller.append({
            "Teyit": "RSI uygun bölge",
            "Durum": False,
            "Yorum": (
                f"RSI {rsi:.1f}; aşırı alım riski yüksek."
            )
        })

    # -----------------------------------------------------
    # 3. GÜNLÜK HAREKET
    # -----------------------------------------------------

    if -3 <= gunluk <= 3:

        kontroller.append({
            "Teyit": "Günlük hareket normalleşmesi",
            "Durum": True,
            "Yorum": (
                f"Günlük hareket %{gunluk:.2f}; normal bölgede."
            )
        })

    else:

        kontroller.append({
            "Teyit": "Günlük hareket normalleşmesi",
            "Durum": False,
            "Yorum": (
                f"Günlük hareket %{gunluk:.2f}; "
                "hareket yüksek."
            )
        })

    # -----------------------------------------------------
    # 4. MOMENTUM
    # -----------------------------------------------------

    if momentum >= 60:

        kontroller.append({
            "Teyit": "Momentum korunuyor",
            "Durum": True,
            "Yorum": (
                f"60G momentum skoru {momentum:.1f}; güçlü."
            )
        })

    else:

        kontroller.append({
            "Teyit": "Momentum korunuyor",
            "Durum": False,
            "Yorum": (
                f"60G momentum skoru {momentum:.1f}; zayıf."
            )
        })

    # -----------------------------------------------------
    # 5. TREND
    # -----------------------------------------------------

    if trend >= 60:

        kontroller.append({
            "Teyit": "Trend korunuyor",
            "Durum": True,
            "Yorum": (
                f"Trend skoru {trend:.1f}; pozitif."
            )
        })

    else:

        kontroller.append({
            "Teyit": "Trend korunuyor",
            "Durum": False,
            "Yorum": (
                f"Trend skoru {trend:.1f}; zayıf."
            )
        })

    olumlu = sum(
        1
        for x in kontroller
        if x["Durum"]
    )

    toplam = len(kontroller)

    return kontroller, olumlu, toplam


# =========================================================
# TEYİT DURUMU
# =========================================================

def teyit_durumu_uret(
    kontroller,
    olumlu,
    toplam
):

    eksikler = [
        x
        for x in kontroller
        if not x["Durum"]
    ]

    # 5/5
    if olumlu == toplam:

        return (
            "🟢 TEYİT GELDİ",
            "Tüm teyit koşulları olumlu.",
            eksikler
        )

    # 4/5
    if olumlu == toplam - 1:

        return (
            "🟢 TEYİT ÇOK YAKIN",
            "Teyitlerin büyük bölümü olumlu. "
            "Son eksik koşulun düzelmesi bekleniyor.",
            eksikler
        )

    # 3/5
    if olumlu >= 3:

        return (
            "🟡 TEYİT BEKLE",
            "Olumlu sinyaller var ancak giriş teyidi "
            "henüz tam oluşmadı.",
            eksikler
        )

    # 2/5
    if olumlu >= 2:

        return (
            "🟠 İZLE",
            "Bazı olumlu sinyaller var ancak teyit "
            "yeterli değil.",
            eksikler
        )

    return (
        "🔴 TEYİT YOK",
        "Teyit koşullarının çoğu olumsuz.",
        eksikler
    )


# =========================================================
# TEK KARAR MOTORU
# =========================================================

def karar_motoru(
    genel_skor,
    teknik,
    temel,
    momentum,
    trend,
    market,
    rsi,
    gunluk,
    teyit_olumlu,
    teyit_toplam
):

    # -----------------------------------------------------
    # TEYİT ORANI
    # -----------------------------------------------------

    teyit_orani = (
        teyit_olumlu / teyit_toplam
        if teyit_toplam > 0
        else 0
    )

    # -----------------------------------------------------
    # 1. UZAK DUR
    # -----------------------------------------------------

    if genel_skor < 45:

        return (
            "🔴 UZAK DUR",
            "Zayıf",
            "Genel skor düşük. Güçlü giriş avantajı bulunmuyor."
        )

    if (
        teknik < 40
        and trend < 40
        and momentum < 40
    ):

        return (
            "🔴 UZAK DUR",
            "Zayıf",
            "Teknik, trend ve momentum birlikte zayıf."
        )

    # -----------------------------------------------------
    # 2. ÇOK SERT DÜŞÜŞ
    # -----------------------------------------------------

    if gunluk <= -6:

        return (
            "🟡 TEYİT BEKLE",
            "Yüksek",
            "Günlük düşüş çok sert. Fiyat hareketinin "
            "sakinleşmesi ve destek üzerinde tutunması beklenmeli."
        )

    # -----------------------------------------------------
    # 3. MARKET ÇOK ZAYIF
    # -----------------------------------------------------

    if market < 35:

        return (
            "🟡 TEYİT BEKLE",
            "Orta",
            "Piyasa koşulları zayıf. Hisse güçlü olsa bile "
            "piyasa teyidi beklenmeli."
        )

    # =====================================================
    # 4. AL
    # =====================================================

    if (
        genel_skor >= 80
        and teknik >= 75
        and momentum >= 70
        and trend >= 70
        and teyit_orani == 1
    ):

        return (
            "🟢 AL",
            "Yüksek",
            "Genel skor yüksek, teknik yapı güçlü ve "
            "tüm teyit koşulları olumlu."
        )

    # =====================================================
    # 5. AL ADAYI
    # =====================================================

    if (
        genel_skor >= 75
        and teknik >= 70
        and momentum >= 65
        and trend >= 65
        and teyit_orani >= 0.80
    ):

        return (
            "🟢 AL ADAYI",
            "Orta-Yüksek",
            "Hisse güçlü ve AL seviyesine yakın. "
            "Son teyidin tamamlanması bekleniyor."
        )

    # =====================================================
    # 6. TEYİT BEKLE
    # =====================================================

    if genel_skor >= 65:

        return (
            "🟡 TEYİT BEKLE",
            "Orta",
            "Hisse olumlu sinyaller veriyor ancak "
            "giriş için yeterli teyit henüz oluşmadı."
        )

    # =====================================================
    # 7. İZLE
    # =====================================================

    if genel_skor >= 55:

        return (
            "🟠 İZLE",
            "Orta",
            "Hisse takip edilebilir ancak mevcut "
            "seviyede güçlü giriş avantajı bulunmuyor."
        )

    # =====================================================
    # 8. UZAK DUR
    # =====================================================

    return (
        "🔴 UZAK DUR",
        "Zayıf",
        "Genel skor ve teknik göstergeler yeterince güçlü değil."
    )


# =========================================================
# ADAY TÜRÜ
# =========================================================

def aday_turu(
    genel_skor,
    teknik,
    temel,
    momentum,
    trend
):

    if (
        genel_skor >= 75
        and teknik >= 75
        and momentum >= 70
        and trend >= 70
    ):

        return "🚀 Güçlü Aday"

    elif genel_skor >= 70:

        return "📊 Genel Aday"

    elif (
        teknik >= 70
        and momentum >= 60
    ):

        return "📈 Teknik Aday"

    elif temel >= 70:

        return "💰 Temel Aday"

    else:

        return "⚠️ Zayıf"


# =========================================================
# RİSK
# =========================================================

def risk_hesapla(
    genel_skor,
    rsi,
    gunluk,
    volatility
):

    risk = 0

    if genel_skor < 50:
        risk += 3

    elif genel_skor < 60:
        risk += 2

    elif genel_skor < 70:
        risk += 1

    if rsi > 75:
        risk += 2

    elif rsi > 70:
        risk += 1

    if gunluk <= -5:
        risk += 2

    elif gunluk <= -3:
        risk += 1

    if volatility >= 6:
        risk += 2

    elif volatility >= 4:
        risk += 1

    if risk >= 5:
        return "🔴 Yüksek"

    elif risk >= 3:
        return "🟡 Orta"

    else:
        return "🟢 Düşük"


# =========================================================
# GENEL SKOR
# =========================================================

def hesapla_genel_skor(
    teknik,
    temel,
    momentum_60,
    trend,
    market,
    w_teknik,
    w_temel,
    w_momentum,
    w_trend,
    w_market
):

    skor = (

        teknik * w_teknik

        +

        temel * w_temel

        +

        momentum_60 * w_momentum

        +

        trend * w_trend

        +

        market * w_market

    )

    return round(
        min(max(skor, 0), 100),
        1
    )


# =========================================================
# HİSSE ANALİZİ
# =========================================================

def hisse_analiz_et(
    symbol,
    market_score,
    w_teknik,
    w_temel,
    w_momentum,
    w_trend,
    w_market
):

    try:

        analysis = get_stock_analysis(
            symbol
        )

        if analysis is None:
            return None

        # -------------------------------------------------
        # TEMEL
        # -------------------------------------------------

        fundamental = get_fundamental_data(
            symbol
        )

        if fundamental is None:

            fundamental_score = 50

        else:

            fundamental_score = (
                calculate_fundamental_score(
                    fundamental
                )
            )

        # -------------------------------------------------
        # VERİLER
        # -------------------------------------------------

        fiyat = safe_float(
            analysis.get("price")
        )

        teknik = safe_float(
            analysis.get("score")
        )

        momentum_60 = safe_float(
            analysis.get("momentum_60_score")
        )

        trend = safe_float(
            analysis.get("trend_strength")
        )

        rsi = safe_float(
            analysis.get("rsi")
        )

        gunluk = safe_float(
            analysis.get("change")
        )

        volatility = safe_float(
            analysis.get("volatility")
        )

        destek = safe_float(
            analysis.get("support", 0)
        )

        direnç = safe_float(
            analysis.get("resistance", 0)
        )

        # -------------------------------------------------
        # GENEL SKOR
        # -------------------------------------------------

        genel_skor = hesapla_genel_skor(

            teknik,
            fundamental_score,
            momentum_60,
            trend,
            market_score,

            w_teknik,
            w_temel,
            w_momentum,
            w_trend,
            w_market

        )

        # =================================================
        # TEK TEYİT HESABI
        # =================================================

        kontroller, teyit_olumlu, teyit_toplam = (
            teyit_kontrolu(

                fiyat,
                destek,
                direnç,
                rsi,
                gunluk,
                teknik,
                momentum_60,
                trend

            )
        )

        (
            teyit_durumu,
            teyit_aciklama,
            teyit_eksikleri
        ) = teyit_durumu_uret(

            kontroller,
            teyit_olumlu,
            teyit_toplam

        )

        # =================================================
        # TEK KARAR HESABI
        # =================================================

        (
            karar,
            guven,
            neden
        ) = karar_motoru(

            genel_skor,

            teknik,

            fundamental_score,

            momentum_60,

            trend,

            market_score,

            rsi,

            gunluk,

            teyit_olumlu,

            teyit_toplam

        )

        # -------------------------------------------------
        # ADAY
        # -------------------------------------------------

        aday = aday_turu(

            genel_skor,
            teknik,
            fundamental_score,
            momentum_60,
            trend

        )

        # -------------------------------------------------
        # RİSK
        # -------------------------------------------------

        risk = risk_hesapla(

            genel_skor,
            rsi,
            gunluk,
            volatility

        )

        # =================================================
        # TEK SONUÇ SÖZLÜĞÜ
        # =================================================

        return {

            "Hisse": symbol,

            "Fiyat": fiyat,

            "Genel Skor": genel_skor,

            "Teknik": round(
                teknik,
                1
            ),

            "Temel": round(
                fundamental_score,
                1
            ),

            "60G Momentum": round(
                momentum_60,
                1
            ),

            "Trend": round(
                trend,
                1
            ),

            "Market": round(
                market_score,
                1
            ),

            "RSI": round(
                rsi,
                2
            ),

            "Günlük %": round(
                gunluk,
                2
            ),

            "Volatilite": round(
                volatility,
                2
            ),

            "Risk": risk,

            "Karar": karar,

            "Güven": guven,

            "Aday": aday,

            "Neden": neden,

            "Destek": destek,

            "Direnç": direnç,

            # TEK TEYİT SONUCU
            "Teyit": teyit_durumu,

            "Teyit Açıklaması": teyit_aciklama,

            "Teyit Olumlu": teyit_olumlu,

            "Teyit Toplam": teyit_toplam,

            "Teyit Kontrolleri": kontroller,

            "Teyit Eksikleri": teyit_eksikleri

        }

    except Exception as e:

        print(
            f"{symbol} ANALİZ HATASI:",
            e
        )

        return None


# =========================================================
# SOL PANEL
# =========================================================

with st.sidebar:

    st.header("📋 Hisse Seçimi")

    st.caption(
        "İstediğiniz BIST hisselerini yazabilirsiniz."
    )

    hisse_metni = st.text_area(

        "Hisseler:",

        value=(
            "ODINE, GESAN, TUPRS, SELEC, AGHOL, "
            "BIMAS, ASTOR, GENIL, CVKMD, TCELL"
        ),

        height=150,

        placeholder=(
            "Örnek:\n"
            "THYAO, ASELS, TUPRS, BIMAS\n"
            "KCHOL\n"
            "FROTO"
        )

    )

    # -----------------------------------------------------
    # HİSSELERİ TEMİZLE
    # -----------------------------------------------------

    temiz_metin = (

        hisse_metni
        .replace(",", " ")
        .replace(";", " ")
        .replace("\n", " ")
        .replace("\t", " ")

    )

    secilen_hisseler = []

    for hisse in temiz_metin.split():

        hisse = hisse.strip().upper()

        if hisse.endswith(".IS"):

            hisse = hisse[:-3]

        if (
            hisse
            and hisse not in secilen_hisseler
        ):

            secilen_hisseler.append(
                hisse
            )

    st.write(
        f"**{len(secilen_hisseler)} hisse seçildi**"
    )

    if secilen_hisseler:

        st.success(
            " • ".join(
                secilen_hisseler
            )
        )

    else:

        st.warning(
            "Henüz hisse girilmedi."
        )

    st.divider()

    # =====================================================
    # AĞIRLIKLAR
    # =====================================================

    st.header("⚙️ Analiz Ağırlıkları")

    teknik_yuzde = st.slider(
        "📈 Teknik",
        0,
        100,
        35,
        5
    )

    temel_yuzde = st.slider(
        "📊 Temel",
        0,
        100,
        20,
        5
    )

    momentum_yuzde = st.slider(
        "🚀 60G Momentum",
        0,
        100,
        15,
        5
    )

    trend_yuzde = st.slider(
        "📈 Trend",
        0,
        100,
        15,
        5
    )

    market_yuzde = st.slider(
        "🌍 Market",
        0,
        100,
        15,
        5
    )

    toplam_agirlik = (

        teknik_yuzde
        +
        temel_yuzde
        +
        momentum_yuzde
        +
        trend_yuzde
        +
        market_yuzde

    )

    st.write(
        f"**Toplam Ağırlık: %{toplam_agirlik}**"
    )

    if toplam_agirlik == 100:

        st.success(
            "✅ Ağırlıklar %100"
        )

        agirliklar_gecerli = True

    else:

        st.error(
            "❌ Toplam %100 olmalı"
        )

        agirliklar_gecerli = False

    st.divider()

    # =====================================================
    # SIRALAMA
    # =====================================================

    st.header("📊 Sıralama")

    siralama = st.selectbox(

        "Sıralama ölçütü",

        [
            "Genel Skor",
            "Teknik",
            "Temel",
            "60G Momentum",
            "Trend",
            "RSI"
        ]

    )

    sadece_70 = st.checkbox(

        "Sadece 70+ Skorları Göster",

        value=False

    )

    st.divider()

    analiz_butonu = st.button(

        "🚀 Analizi Çalıştır",

        type="primary",

        use_container_width=True

    )


# =========================================================
# KONTROLLER
# =========================================================

if not secilen_hisseler:

    st.info(
        "👈 Sol taraftan analiz etmek istediğiniz hisseleri girin."
    )

    st.stop()


if not agirliklar_gecerli:

    st.error(
        "Analiz ağırlıklarının toplamı %100 olmalıdır."
    )

    st.stop()


# =========================================================
# ANALİZ
# =========================================================

if analiz_butonu:

    market_score, market_reasons = get_market()

    w_teknik = teknik_yuzde / 100
    w_temel = temel_yuzde / 100
    w_momentum = momentum_yuzde / 100
    w_trend = trend_yuzde / 100
    w_market = market_yuzde / 100

    sonuclar = []

    progress = st.progress(0)

    status = st.empty()

    toplam = len(
        secilen_hisseler
    )

    for i, symbol in enumerate(
        secilen_hisseler
    ):

        status.write(
            f"🔎 {symbol} analiz ediliyor..."
        )

        sonuc = hisse_analiz_et(

            symbol,

            market_score,

            w_teknik,

            w_temel,

            w_momentum,

            w_trend,

            w_market

        )

        if sonuc is not None:

            sonuclar.append(
                sonuc
            )

        progress.progress(
            (i + 1) / toplam
        )

    progress.empty()

    status.empty()

    if not sonuclar:

        st.error(
            "Hiçbir hissenin verisi alınamadı."
        )

        st.stop()

    df = pd.DataFrame(
        sonuclar
    )

else:

    st.info(
        "👈 Hisseleri seçin ve "
        "**🚀 Analizi Çalıştır** butonuna basın."
    )

    st.stop()


# =========================================================
# FİLTRE
# =========================================================

if sadece_70:

    df = df[
        df["Genel Skor"] >= 70
    ]


# =========================================================
# SIRALAMA
# =========================================================

if siralama in df.columns:

    df = df.sort_values(
        siralama,
        ascending=False
    )


# =========================================================
# ÜST KARTLAR
# =========================================================

col1, col2, col3, col4 = st.columns(4)

with col1:

    st.metric(
        "🌍 Market Skoru",
        f"{market_score}/100"
    )

with col2:

    if market_score >= 75:

        market_status = "🟢 Güçlü Pozitif"

    elif market_score >= 55:

        market_status = "🟡 Temkinli Pozitif"

    elif market_score >= 35:

        market_status = "🟠 Nötr"

    else:

        market_status = "🔴 Zayıf"

    st.metric(
        "📊 Piyasa Durumu",
        market_status
    )

with col3:

    olumlu = len(
        df[
            df["Genel Skor"] >= 70
        ]
    )

    zayif = len(
        df[
            df["Genel Skor"] < 60
        ]
    )

    st.metric(
        "📈 Sinyal Durumu",
        f"{olumlu} Olumlu / {zayif} Zayıf"
    )

with col4:

    st.metric(
        "📋 Analiz Edilen",
        len(df)
    )


# =========================================================
# ANA TABLO
# =========================================================

st.divider()

st.subheader(
    "📊 Hisselerin Karşılaştırılması"
)

display_columns = [

    "Hisse",
    "Fiyat",
    "Genel Skor",
    "Teknik",
    "Temel",
    "60G Momentum",
    "Trend",
    "Market",
    "RSI",
    "Günlük %",
    "Teyit",
    "Risk",
    "Karar",
    "Aday"

]

st.dataframe(

    df[display_columns],

    use_container_width=True,

    hide_index=True,

    column_config={

        "Hisse": st.column_config.TextColumn(
            "🏷️ Hisse"
        ),

        "Fiyat": st.column_config.NumberColumn(
            "💰 Fiyat",
            format="%.2f TL"
        ),

        "Genel Skor": st.column_config.NumberColumn(
            "🏆 Genel Skor",
            format="%.1f"
        ),

        "Teknik": st.column_config.NumberColumn(
            "📈 Teknik",
            format="%.1f"
        ),

        "Temel": st.column_config.NumberColumn(
            "📊 Temel",
            format="%.1f"
        ),

        "60G Momentum": st.column_config.NumberColumn(
            "🚀 60G Momentum",
            format="%.1f"
        ),

        "Trend": st.column_config.NumberColumn(
            "📈 Trend",
            format="%.1f"
        ),

        "Market": st.column_config.NumberColumn(
            "🌍 Market",
            format="%.1f"
        ),

        "RSI": st.column_config.NumberColumn(
            "RSI",
            format="%.2f"
        ),

        "Günlük %": st.column_config.NumberColumn(
            "Günlük %",
            format="%.2f"
        ),

        "Teyit": st.column_config.TextColumn(
            "🔎 Teyit"
        ),

        "Risk": st.column_config.TextColumn(
            "⚠️ Risk"
        ),

        "Karar": st.column_config.TextColumn(
            "🎯 Karar"
        ),

        "Aday": st.column_config.TextColumn(
            "⭐ Aday"
        )

    }

)


# =========================================================
# DETAYLI KARAR DESTEK
# =========================================================

st.divider()

st.subheader(
    "🎯 Detaylı Karar Destek"
)

for row in df.to_dict(
    "records"
):

    with st.expander(

        f"{row['Hisse']} | "
        f"{row['Karar']} | "
        f"Genel Skor: {row['Genel Skor']}"

    ):

        # -------------------------------------------------
        # ÜST METRİKLER
        # -------------------------------------------------

        c1, c2, c3, c4 = st.columns(4)

        with c1:

            st.metric(
                "🏆 Genel Skor",
                row["Genel Skor"]
            )

        with c2:

            st.metric(
                "📈 Teknik",
                row["Teknik"]
            )

        with c3:

            st.metric(
                "📊 Temel",
                row["Temel"]
            )

        with c4:

            st.metric(
                "🚀 60G Momentum",
                row["60G Momentum"]
            )

        c1, c2, c3, c4 = st.columns(4)

        with c1:

            st.metric(
                "📈 Trend",
                row["Trend"]
            )

        with c2:

            st.metric(
                "🌍 Market",
                row["Market"]
            )

        with c3:

            st.metric(
                "RSI",
                row["RSI"]
            )

        with c4:

            st.metric(
                "Günlük %",
                row["Günlük %"]
            )

        # -------------------------------------------------
        # KARAR
        # -------------------------------------------------

        st.divider()

        st.markdown(
            f"### {row['Karar']}"
        )

        st.write(
            f"**Güven:** {row['Güven']}"
        )

        st.write(
            f"**Risk:** {row['Risk']}"
        )

        st.write(
            f"**Aday Tipi:** {row['Aday']}"
        )

        st.info(
            row["Neden"]
        )

        # -------------------------------------------------
        # TEYİT
        # -------------------------------------------------

        st.divider()

        st.markdown(
            "### 🔎 Teyit Durumu"
        )

        # AYNI TEYİT DEĞERİ
        st.write(
            f"**{row['Teyit']}**"
        )

        st.write(
            f"**Olumlu koşullar:** "
            f"{row['Teyit Olumlu']} / "
            f"{row['Teyit Toplam']}"
        )

        st.write(
            row["Teyit Açıklaması"]
        )

        # -------------------------------------------------
        # TEYİT KONTROLLERİ
        # -------------------------------------------------

        for kontrol in row[
            "Teyit Kontrolleri"
        ]:

            if kontrol["Durum"]:

                st.success(
                    f"🟢 {kontrol['Teyit']} — "
                    f"{kontrol['Yorum']}"
                )

            else:

                st.error(
                    f"🔴 {kontrol['Teyit']} — "
                    f"{kontrol['Yorum']}"
                )

        # -------------------------------------------------
        # EKSİK TEYİT
        # -------------------------------------------------

        if row["Teyit Eksikleri"]:

            st.warning(
                "### ⏳ Beklenen Teyit"
            )

            for eksik in row[
                "Teyit Eksikleri"
            ]:

                st.write(
                    f"🔴 **{eksik['Teyit']}**"
                )

                st.caption(
                    eksik["Yorum"]
                )

        else:

            st.success(
                "✅ Tüm teyit koşulları olumlu."
            )

        # -------------------------------------------------
        # FİYAT SEVİYELERİ
        # -------------------------------------------------

        st.divider()

        c1, c2 = st.columns(2)

        with c1:

            st.metric(
                "📍 Destek",
                f"{row['Destek']:.2f} TL"
            )

        with c2:

            st.metric(
                "🎯 Direnç",
                f"{row['Direnç']:.2f} TL"
            )

        # =================================================
        # KULLANICIYA NET AÇIKLAMA
        # =================================================

        st.divider()

        karar = row["Karar"]

        if karar == "🟢 AL":

            st.success(

                "📌 **Sistem Yorumu**\n\n"
                "Genel skor, teknik yapı ve teyit koşulları "
                "birlikte olumlu. Sistem AL sinyali üretiyor."

            )

        elif karar == "🟢 AL ADAYI":

            st.info(

                "📌 **Sistem Yorumu**\n\n"
                "Hisse güçlü bir AL adayı. Ancak AL sinyaline "
                "geçmeden önce eksik teyitlerin tamamlanması "
                "bekleniyor."

            )

        elif karar == "🟡 TEYİT BEKLE":

            st.warning(

                "📌 **Sistem Yorumu**\n\n"
                "Hisse olumlu görünüyor ancak giriş için "
                "teyit koşullarından biri veya birkaçı henüz "
                "tamamlanmadı."

            )

        elif karar == "🟠 İZLE":

            st.info(

                "📌 **Sistem Yorumu**\n\n"
                "Hisse takip edilebilir ancak şu anda "
                "yeterince güçlü bir giriş sinyali bulunmuyor."

            )

        else:

            st.error(

                "📌 **Sistem Yorumu**\n\n"
                "Mevcut teknik koşullar güçlü bir giriş "
                "avantajı göstermiyor."

            )


# =========================================================
# MARKET YORUMU
# =========================================================

st.divider()

st.subheader(
    "🌍 Piyasa Teyitleri"
)

if market_reasons:

    for reason in market_reasons:

        st.write(
            f"• {reason}"
        )

else:

    st.write(
        "Piyasa gerekçesi alınamadı."
    )


# =========================================================
# ÖNE ÇIKAN HİSSELER
# =========================================================

st.divider()

st.subheader(
    "🏆 Öne Çıkan Hisseler"
)

adaylar = (

    df[
        df["Genel Skor"] >= 70
    ]

    .sort_values(
        "Genel Skor",
        ascending=False
    )

)

if not adaylar.empty:

    st.dataframe(

        adaylar[
            [
                "Hisse",
                "Genel Skor",
                "Teknik",
                "Temel",
                "60G Momentum",
                "Trend",
                "Market",
                "Teyit",
                "Risk",
                "Karar",
                "Aday"
            ]
        ],

        use_container_width=True,

        hide_index=True

    )

else:

    st.warning(
        "Şu anda 70 üzeri güçlü aday bulunmuyor."
    )