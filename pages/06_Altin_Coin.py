# ============================================================
# BIST AI PRO
# ALTIN & GÜMÜŞ ANALİZ MERKEZİ
#
# Gerekli motorlar:
#   modules/metals/gold_analysis.py
#   modules/metals/silver_analysis.py
#
# Gram fiyat:
#   Ons × USD/TRY / 31.1034768
# ============================================================

from __future__ import annotations

from typing import Any, Callable, Dict

import pandas as pd
import streamlit as st

from modules.metals.gold_analysis import analyze_gold

try:
    from modules.forex.forex_analysis import DEFAULT_PAIRS, scan_forex

    FOREX_ENGINE_AVAILABLE = True
    FOREX_IMPORT_ERROR = ""
except Exception as exc:
    DEFAULT_PAIRS = ()
    scan_forex = None
    FOREX_ENGINE_AVAILABLE = False
    FOREX_IMPORT_ERROR = str(exc)

try:
    from modules.metals.silver_analysis import analyze_silver

    SILVER_ENGINE_AVAILABLE = True
    SILVER_IMPORT_ERROR = ""
except Exception as exc:
    analyze_silver = None
    SILVER_ENGINE_AVAILABLE = False
    SILVER_IMPORT_ERROR = str(exc)


# ============================================================
# SAYFA AYARLARI
# ============================================================

st.set_page_config(
    page_title="BIST AI PRO - Altın & Gümüş",
    page_icon="🥇",
    layout="wide",
)

st.title("🥇 BIST AI PRO | Altın, Gümüş & Döviz Merkezi")

st.caption(
    "Altın, gümüş ve çapraz kurlar: teknik analiz + çoklu zaman dilimi + "
    "trend + momentum + çift yönlü risk/getiri karar motoru"
)


# ============================================================
# YARDIMCI FONKSİYONLAR
# ============================================================

def get_value(
    result: Dict[str, Any],
    key: str,
    default: Any = None,
) -> Any:
    """Sonuç sözlüğünden güvenli değer alır."""

    value = result.get(key, default)

    if value is None:
        return default

    return value


def valid_number(value: Any) -> bool:
    """Değerin gösterilebilir sayısal değer olup olmadığını kontrol eder."""

    try:
        return value is not None and pd.notna(value)
    except Exception:
        return False


def format_number(
    value: Any,
    decimals: int = 2,
    suffix: str = "",
    signed: bool = False,
) -> str:
    """Sayısal değerleri güvenli biçimde formatlar."""

    if not valid_number(value):
        return "-"

    try:
        value = float(value)

        if signed:
            return f"{value:+,.{decimals}f}{suffix}"

        return f"{value:,.{decimals}f}{suffix}"

    except (TypeError, ValueError):
        return "-"


def format_price(value: Any, decimals: int = 2) -> str:
    return format_number(
        value=value,
        decimals=decimals,
    )


def render_decision(decision: str) -> None:
    """Karar sonucunu uygun Streamlit bileşeniyle gösterir."""

    decision = str(decision or "🟡 KARAR ÜRETİLEMEDİ")

    if decision.startswith("🟢"):
        st.success(decision)

    elif decision.startswith("🔴"):
        st.error(decision)

    else:
        st.warning(decision)


def normalize_analysis_response(
    analysis: Any,
) -> tuple[bool, Dict[str, Any], str]:
    """
    Analiz motorunun hem dataclass/nesne hem sözlük sonuçlarını destekler.
    """

    if analysis is None:
        return False, {}, "Analiz motoru boş sonuç döndürdü."

    # Nesne tipi sonuç
    if hasattr(analysis, "ok"):
        ok = bool(getattr(analysis, "ok", False))
        error = str(getattr(analysis, "error", "") or "")
        result = getattr(analysis, "result", {}) or {}

        if not isinstance(result, dict):
            return False, {}, "Analiz sonucu sözlük formatında değil."

        return ok, result, error

    # Sözlük tipi sonuç
    if isinstance(analysis, dict):
        if "ok" in analysis:
            ok = bool(analysis.get("ok", False))
            error = str(analysis.get("error", "") or "")
            result = analysis.get("result", {}) or {}

            if not isinstance(result, dict):
                return False, {}, "Analiz sonucu sözlük formatında değil."

            return ok, result, error

        return True, analysis, ""

    return False, {}, "Analiz motoru desteklenmeyen bir sonuç döndürdü."


def render_confirmation_table(
    checks: Dict[str, Any],
    positive_icon: str,
    negative_icon: str,
) -> pd.DataFrame:
    """Teyit kontrollerini tabloya dönüştürür."""

    if not isinstance(checks, dict) or not checks:
        return pd.DataFrame(
            [{"Kontrol": "Kontrol verisi bulunamadı", "Durum": "—"}]
        )

    return pd.DataFrame(
        [
            {
                "Kontrol": str(key),
                "Durum": positive_icon if bool(value) else negative_icon,
            }
            for key, value in checks.items()
        ]
    )


# ============================================================
# METAL ANALİZ EKRANI
# ============================================================

def render_metal_analysis(
    metal_name: str,
    metal_icon: str,
    analyzer: Callable[..., Any],
    period: str,
    gram_price_key: str,
    gram_title: str,
    spot_title: str,
    spot_currency: str = "USD",
) -> None:
    """
    Altın ve gümüş için ortak analiz ekranı.

    Her iki analiz motorunun da aynı sonuç şemasını döndürmesi beklenir.
    Yalnızca gram fiyat anahtarı farklı olabilir.
    """

    with st.spinner(
        f"{metal_name} ons ve USD/TRY verileri analiz ediliyor..."
    ):
        try:
            analysis = analyzer(
                period=period,
                interval="1d",
            )
        except Exception as exc:
            st.error(
                f"{metal_name} analiz motoru çalıştırılırken hata oluştu: {exc}"
            )
            return

    ok, result, error = normalize_analysis_response(analysis)

    if not ok:
        st.error(
            error
            or f"{metal_name} analizi gerçekleştirilemedi."
        )
        return

    r = result

    # Bazı motorlarda ortak isim gram_price olabilir.
    gram_price = get_value(
        r,
        gram_price_key,
        get_value(r, "gram_price"),
    )

    spot_price = get_value(
        r,
        "ons_price",
        get_value(r, "spot_price"),
    )

    usdtry = get_value(r, "usdtry")
    general_score = get_value(r, "general_score")
    gram_momentum_20 = get_value(r, "gram_momentum_20")

    # ========================================================
    # ANA ÖZET
    # ========================================================

    st.subheader(f"{metal_icon} {metal_name} Genel Görünüm")

    c1, c2, c3, c4, c5 = st.columns(5)

    c1.metric(
        gram_title,
        (
            f"{format_price(gram_price, 2)} TL"
            if valid_number(gram_price)
            else "-"
        ),
    )

    c2.metric(
        spot_title,
        (
            f"{format_price(spot_price, 2)} {spot_currency}"
            if valid_number(spot_price)
            else "-"
        ),
    )

    c3.metric(
        "USD/TRY",
        format_number(usdtry, decimals=4),
    )

    c4.metric(
        "Genel Skor",
        (
            f"{format_number(general_score, decimals=1)}/100"
            if valid_number(general_score)
            else "-"
        ),
    )

    c5.metric(
        f"20G {metal_name} Momentum",
        format_number(
            gram_momentum_20,
            decimals=2,
            suffix="%",
            signed=True,
        ),
    )

    st.divider()

    # ========================================================
    # KARAR
    # ========================================================

    st.subheader("🧠 SON KARAR")

    decision = str(
        get_value(
            r,
            "decision",
            "🟡 KARAR ÜRETİLEMEDİ",
        )
    )

    render_decision(decision)

    reason = get_value(
        r,
        "reason",
        "Karar gerekçesi bulunamadı.",
    )

    st.write(reason)

    # ========================================================
    # TEYİT
    # ========================================================

    st.subheader("🚦 İşlem Teyitleri")

    buy_confirmation = bool(
        get_value(r, "buy_confirmation", False)
    )

    sell_confirmation = bool(
        get_value(r, "sell_confirmation", False)
    )

    buy_count = get_value(r, "buy_count", 0)
    sell_count = get_value(r, "sell_count", 0)

    buy_checks = get_value(r, "buy_checks", {})
    sell_checks = get_value(r, "sell_checks", {})

    total_buy_checks = (
        len(buy_checks)
        if isinstance(buy_checks, dict) and buy_checks
        else 6
    )

    total_sell_checks = (
        len(sell_checks)
        if isinstance(sell_checks, dict) and sell_checks
        else 6
    )

    a, b, c = st.columns(3)

    a.metric(
        "Alım Teyidi",
        "🟢 VAR" if buy_confirmation else "🟡 YOK",
        f"{buy_count}/{total_buy_checks}",
    )

    b.metric(
        "Satış Teyidi",
        "🔴 VAR" if sell_confirmation else "🟢 YOK",
        f"{sell_count}/{total_sell_checks}",
    )

    c.metric(
        "RSI",
        format_number(
            get_value(r, "rsi"),
            decimals=1,
        ),
    )

    with st.expander("🔬 Teyit kontrollerini göster"):
        left, right = st.columns(2)

        buy_df = render_confirmation_table(
            checks=buy_checks,
            positive_icon="🟢",
            negative_icon="🔴",
        )

        sell_df = render_confirmation_table(
            checks=sell_checks,
            positive_icon="🔴",
            negative_icon="🟢",
        )

        with left:
            st.markdown("**Alım kontrolleri**")
            st.dataframe(
                buy_df,
                use_container_width=True,
                hide_index=True,
            )

        with right:
            st.markdown("**Satış kontrolleri**")
            st.dataframe(
                sell_df,
                use_container_width=True,
                hide_index=True,
            )

    # ========================================================
    # ANALİZ KATMANLARI
    # ========================================================

    st.subheader("📊 Analiz Katmanları")

    x1, x2, x3, x4 = st.columns(4)

    x1.metric(
        "Teknik",
        format_number(
            get_value(r, "technical_score"),
            decimals=1,
        ),
    )

    x2.metric(
        "Trend",
        format_number(
            get_value(r, "trend_score"),
            decimals=1,
        ),
    )

    x3.metric(
        "Momentum",
        format_number(
            get_value(r, "momentum_score"),
            decimals=1,
        ),
    )

    x4.metric(
        "Risk/Getiri",
        format_number(
            get_value(r, "risk_reward_score"),
            decimals=1,
        ),
    )

    # ========================================================
    # ONS + KUR KATKISI
    # ========================================================

    st.subheader(f"🌍 Gram {metal_name} Hareketinin Kaynağı")

    ons_contribution = get_value(
        r,
        "ons_contribution_20",
        get_value(r, "spot_contribution_20"),
    )

    fx_contribution = get_value(
        r,
        "fx_contribution_20",
    )

    o1, o2, o3 = st.columns(3)

    o1.metric(
        "Ons 20G Katkısı",
        format_number(
            ons_contribution,
            decimals=2,
            suffix="%",
            signed=True,
        ),
    )

    o2.metric(
        "USD/TRY 20G Katkısı",
        format_number(
            fx_contribution,
            decimals=2,
            suffix="%",
            signed=True,
        ),
    )

    o3.metric(
        f"Gram {metal_name} 20G",
        format_number(
            gram_momentum_20,
            decimals=2,
            suffix="%",
            signed=True,
        ),
    )

    st.info(
        f"Teorik gram {metal_name.lower()} fiyatı yaklaşık olarak "
        f"{metal_name} ons × USD/TRY / 31.1034768 formülüyle hesaplanır. "
        "Bu değer kuyumcu, banka veya serbest piyasa alış/satış fiyatının "
        "birebir karşılığı değildir. Analiz motorunun teorik gram TL "
        "referansıdır."
    )

    # ========================================================
    # TEKNİK GÖRÜNÜM
    # ========================================================

    st.subheader("📈 Teknik Görünüm")

    technical_rows = [
        ("EMA9", get_value(r, "ema9")),
        ("EMA20", get_value(r, "ema20")),
        ("EMA50", get_value(r, "ema50")),
        ("EMA100", get_value(r, "ema100")),
        ("EMA200", get_value(r, "ema200")),
        ("RSI", get_value(r, "rsi")),
        ("MACD", get_value(r, "macd")),
        ("20G Momentum", get_value(r, "momentum_20")),
        ("60G Momentum", get_value(r, "momentum_60")),
        ("ATR", get_value(r, "atr")),
        ("20G Volatilite", get_value(r, "volatility_20")),
    ]

    tech = pd.DataFrame(
        [
            {
                "Gösterge": indicator,
                "Değer": (
                    round(float(value), 4)
                    if valid_number(value)
                    else None
                ),
            }
            for indicator, value in technical_rows
        ]
    )

    st.dataframe(
        tech,
        use_container_width=True,
        hide_index=True,
    )

    # ========================================================
    # DESTEK / DİRENÇ
    # ========================================================

    st.subheader("🎯 Destek / Direnç")

    support = get_value(r, "support")
    resistance = get_value(r, "resistance")
    resistance_distance = get_value(
        r,
        "resistance_distance_pct",
    )
    risk_reward = get_value(r, "risk_reward")

    d1, d2, d3, d4 = st.columns(4)

    d1.metric(
        f"{metal_name} Ons Destek",
        (
            f"{format_price(support, 2)} {spot_currency}"
            if valid_number(support)
            else "-"
        ),
    )

    d2.metric(
        f"{metal_name} Ons Direnç",
        (
            f"{format_price(resistance, 2)} {spot_currency}"
            if valid_number(resistance)
            else "-"
        ),
    )

    d3.metric(
        "Dirence Uzaklık",
        format_number(
            resistance_distance,
            decimals=2,
            suffix="%",
            signed=True,
        ),
    )

    d4.metric(
        "Risk/Getiri",
        format_number(
            risk_reward,
            decimals=2,
        ),
    )

    support_touches = get_value(r, "support_touches", 0)
    resistance_touches = get_value(r, "resistance_touches", 0)

    st.caption(
        f"Destek bölgesi temas: {support_touches} | "
        f"Direnç bölgesi temas: {resistance_touches}"
    )

    # ========================================================
    # VERİ BİLGİSİ
    # ========================================================

    st.divider()

    data_source = get_value(r, "data_source", "Belirtilmedi")
    reference_source = get_value(
        r,
        "reference_source",
        "Belirtilmedi",
    )
    data_timestamp = get_value(
        r,
        "data_timestamp",
        "Belirtilmedi",
    )
    data_status = get_value(
        r,
        "data_status",
        "Bilinmiyor",
    )

    st.caption(
        f"Operasyonel kaynak: {data_source} | "
        f"Referans: {reference_source}"
    )

    st.caption(
        f"Veri zamanı: {data_timestamp} | "
        f"{data_status}"
    )


# ============================================================
# DÖVİZ / ÇAPRAZ KUR EKRANI
# ============================================================

@st.cache_data(ttl=900, show_spinner=False)
def load_forex_scan(period_value: str):
    """Tüm pariteleri 15 dakika önbellekte tutar."""
    if scan_forex is None:
        return []
    return scan_forex(DEFAULT_PAIRS, period=period_value)


def forex_price(value: Any, digits: int) -> str:
    return format_number(value, decimals=digits)


def render_forex_center(period_value: str) -> None:
    if not FOREX_ENGINE_AVAILABLE or scan_forex is None:
        st.error(
            "Döviz analiz motoru bulunamadı. "
            "`modules/forex/forex_analysis.py` dosyasını ekleyin."
        )
        if FOREX_IMPORT_ERROR:
            with st.expander("Teknik hata ayrıntısı"):
                st.code(FOREX_IMPORT_ERROR)
        return

    st.subheader("💱 Döviz ve Çapraz Kur Fırsat Taraması")
    st.caption(
        "Günlük %45 + 4 saatlik %35 + 1 saatlik %20. "
        "Sistem yalnızca yeterli yön üstünlüğü varsa AL veya SAT planı üretir."
    )

    left, right = st.columns([3, 1])
    with left:
        st.info(
            "AL: ilk para biriminin ikinci para birimine karşı güçlenmesi; "
            "SAT: ilk para biriminin ikinci para birimine karşı zayıflaması beklentisidir."
        )
    with right:
        if st.button("🔄 Döviz verilerini yenile", use_container_width=True):
            load_forex_scan.clear()

    with st.spinner("10 döviz paritesi, üç zaman diliminde analiz ediliyor..."):
        analyses = load_forex_scan(period_value)

    valid = [x.result for x in analyses if getattr(x, "ok", False)]
    errors = [getattr(x, "error", "Bilinmeyen hata") for x in analyses if not getattr(x, "ok", False)]

    if not valid:
        st.error("Döviz verileri alınamadı veya yeterli geçmiş bulunamadı.")
        if errors:
            with st.expander("Veri hataları"):
                for error in errors:
                    st.write(f"• {error}")
        return

    summary_rows = []
    for item in valid:
        digits = int(item.get("digits", 5))
        summary_rows.append(
            {
                "Parite": item.get("pair"),
                "Fiyat": forex_price(item.get("price"), digits),
                "1G %": round(float(item.get("change_1d", 0)), 2),
                "Genel": item.get("general_score"),
                "Günlük": item.get("daily_score"),
                "4 Saat": item.get("h4_score"),
                "1 Saat": item.get("h1_score"),
                "RSI": round(float(item.get("rsi", 0)), 1),
                "Karar": item.get("decision"),
            }
        )

    summary = pd.DataFrame(summary_rows).sort_values("Genel", ascending=False)
    st.dataframe(summary, use_container_width=True, hide_index=True)

    if errors:
        st.warning(f"{len(errors)} paritede veri sorunu oluştu; diğer sonuçlar gösteriliyor.")

    actionable = [x for x in valid if bool(x.get("tradeable"))]
    buy_list = [x["pair"] for x in actionable if x.get("direction") == "AL"]
    sell_list = [x["pair"] for x in actionable if x.get("direction") == "SAT"]

    a, b, c = st.columns(3)
    a.metric("🟢 Alım Adayı", len(buy_list))
    b.metric("🔴 Satış Adayı", len(sell_list))
    c.metric("🟡 İşlem Yok/Bekle", len(valid) - len(actionable))
    st.caption(
        f"AL adayları: {', '.join(buy_list) if buy_list else 'Yok'} | "
        f"SAT adayları: {', '.join(sell_list) if sell_list else 'Yok'}"
    )

    selected_pair = st.selectbox(
        "Ayrıntılı analiz edilecek parite",
        options=[x["pair"] for x in valid],
        key="forex_selected_pair",
    )
    r = next(x for x in valid if x["pair"] == selected_pair)
    digits = int(r.get("digits", 5))

    st.divider()
    st.subheader(f"🔬 {selected_pair} Ayrıntılı İşlem Planı")
    render_decision(str(r.get("decision", "🟡 KARAR YOK")))
    st.write(r.get("reason", "Karar gerekçesi bulunamadı."))

    p1, p2, p3, p4, p5 = st.columns(5)
    p1.metric("Güncel Fiyat", forex_price(r.get("price"), digits))
    p2.metric("Genel Skor", f"{format_number(r.get('general_score'), 1)}/100")
    p3.metric("Günlük Trend", format_number(r.get("daily_score"), 1))
    p4.metric("4 Saatlik Trend", format_number(r.get("h4_score"), 1))
    p5.metric("1 Saatlik Trend", format_number(r.get("h1_score"), 1))

    if bool(r.get("tradeable")):
        st.markdown("### 🎯 Uygulanabilir işlem seviyeleri")
        q1, q2, q3, q4, q5, q6 = st.columns(6)
        q1.metric("Yön", str(r.get("direction")))
        q2.metric("Giriş", forex_price(r.get("entry"), digits))
        q3.metric("Stop", forex_price(r.get("trade_stop"), digits))
        q4.metric("Hedef 1", forex_price(r.get("target1"), digits))
        q5.metric("Hedef 2", forex_price(r.get("target2"), digits))
        q6.metric("R/R (H2)", format_number(r.get("risk_reward_target2"), 2))

        capital = st.number_input(
            "Bu işlem için hesap sermayesi (TL)",
            min_value=0.0,
            value=100000.0,
            step=5000.0,
            key="forex_capital",
        )
        risk_pct = st.slider(
            "İşlem başına azami risk (%)",
            min_value=0.25,
            max_value=2.00,
            value=0.50,
            step=0.25,
            key="forex_risk_pct",
        )
        st.warning(
            f"Bu plan için azami kabul edilen zarar: "
            f"{capital * risk_pct / 100:,.2f} TL. Lot miktarı, aracı kurumun pip değerine "
            "göre stop çalıştığında bu tutarı aşmayacak şekilde belirlenmelidir."
        )
    else:
        st.warning(
            "Bu paritede uygulanabilir giriş seviyesi üretilmedi. "
            "Sinyal netleşmeden pozisyon açılması önerilmez."
        )

    st.markdown("### 📊 Teknik yapı")
    t1, t2, t3, t4 = st.columns(4)
    t1.metric("Teknik", format_number(r.get("technical_score"), 1))
    t2.metric("Momentum", format_number(r.get("momentum_score"), 1))
    t3.metric("RSI", format_number(r.get("rsi"), 1))
    t4.metric("20G Volatilite", format_number(r.get("volatility_20"), 2, "%"))

    s1, s2 = st.columns(2)
    s1.metric("Destek", forex_price(r.get("support"), digits))
    s2.metric("Direnç", forex_price(r.get("resistance"), digits))

    with st.expander("🚦 AL / SAT teyitlerini göster"):
        buy_df = render_confirmation_table(r.get("buy_checks", {}), "🟢", "⚪")
        sell_df = render_confirmation_table(r.get("sell_checks", {}), "🔴", "⚪")
        e1, e2 = st.columns(2)
        with e1:
            st.markdown("**AL teyitleri**")
            st.dataframe(buy_df, use_container_width=True, hide_index=True)
        with e2:
            st.markdown("**SAT teyitleri**")
            st.dataframe(sell_df, use_container_width=True, hide_index=True)

    st.caption(
        f"Kaynak: {r.get('data_source')} | Veri zamanı: {r.get('data_timestamp')} | "
        f"{r.get('data_status')}"
    )
    st.error(
        "Bu ekran yatırım danışmanlığı veya kesin kazanç vaadi değildir. "
        "Sinyaller gecikmeli tarihsel verilerden üretilir; gerçek emir fiyatı, spread, "
        "swap, kayma ve kaldıraç sonucu değiştirebilir."
    )


# ============================================================
# ORTAK AYARLAR
# ============================================================

settings_left, settings_right = st.columns([1, 3])

with settings_left:
    period = st.selectbox(
        "Analiz geçmişi",
        options=["1y", "2y", "5y"],
        index=1,
        key="metal_analysis_period",
    )

with settings_right:
    st.info(
        "Altın ve gümüş günlük metal motorlarıyla; dövizler ise günlük + "
        "4 saatlik + 1 saatlik çoklu zaman dilimi motoruyla değerlendirilir."
    )


# ============================================================
# ALTIN VE GÜMÜŞ SEKMELERİ
# ============================================================

gold_tab, silver_tab, forex_tab, comparison_tab = st.tabs(
    [
        "🥇 Altın Analizi",
        "🥈 Gümüş Analizi",
        "💱 Döviz & Çapraz Kur",
        "⚖️ Sistem Açıklaması",
    ]
)


# ============================================================
# ALTIN
# ============================================================

with gold_tab:
    render_metal_analysis(
        metal_name="Altın",
        metal_icon="🥇",
        analyzer=analyze_gold,
        period=period,
        gram_price_key="gram_price",
        gram_title="🥇 Gram Altın",
        spot_title="Ons Altın",
        spot_currency="USD",
    )


# ============================================================
# GÜMÜŞ
# ============================================================

with silver_tab:
    if not SILVER_ENGINE_AVAILABLE or analyze_silver is None:
        st.error(
            "Gümüş analiz motoru bulunamadı. "
            "`modules/metals/silver_analysis.py` dosyası ve "
            "`analyze_silver()` fonksiyonu eklenmelidir."
        )

        if SILVER_IMPORT_ERROR:
            with st.expander("Teknik hata ayrıntısı"):
                st.code(SILVER_IMPORT_ERROR)

    else:
        render_metal_analysis(
            metal_name="Gümüş",
            metal_icon="🥈",
            analyzer=analyze_silver,
            period=period,
            gram_price_key="gram_silver_price",
            gram_title="🥈 Gram Gümüş",
            spot_title="Ons Gümüş",
            spot_currency="USD",
        )


# ============================================================
# DÖVİZ VE ÇAPRAZ KURLAR
# ============================================================

with forex_tab:
    render_forex_center(period)


# ============================================================
# SİSTEM AÇIKLAMASI
# ============================================================

with comparison_tab:
    st.subheader("📖 Karar sistemi nasıl çalışıyor?")

    st.markdown(
        """
### Genel skor

**%30 Trend + %25 Momentum + %25 Teknik + %20 Risk/Getiri**

### Genel skor tek başına AL sinyali değildir

Sistem ayrıca aşağıdaki koşulları kontrol eder:

- Alım teyidi
- Satış teyidi
- RSI seviyesi
- Dirence olan uzaklık
- Risk/getiri oranı
- Kısa ve uzun dönem hareketli ortalamalar
- Momentum ve oynaklık
- Destek ve direnç bölgeleri

### Gram altın ve gram gümüş

Her iki metalin teorik gram/TL değeri iki ana etkene ayrılır:

1. **Ons fiyatı:** Küresel metal fiyatı
2. **USD/TRY:** Türk lirasındaki kur etkisi

Yaklaşık hesaplama:

**Gram fiyat = Ons fiyatı × USD/TRY / 31.1034768**

Bu nedenle sistem yalnızca metal fiyatının yükseldiğini veya düştüğünü
söylemez. Hareketin ons fiyatından mı, döviz kurundan mı kaynaklandığını
da ayrı ayrı gösterir.

### Altın ve gümüş arasındaki fark

| Özellik | Altın | Gümüş |
|---|---|---|
| Temel kullanım | Güvenli liman, rezerv | Sanayi ve yatırım |
| Oynaklık | Görece düşük | Daha yüksek |
| Ekonomik hassasiyet | Faiz, dolar, jeopolitik risk | Sanayi talebi, büyüme, dolar |
| Risk seviyesi | Orta | Orta-yüksek |
| Hareket karakteri | Daha dengeli | Daha sert yükseliş/düşüş |

### Döviz ve çapraz kur sistemi

- **EUR/GBP = 0.85500**, 1 avronun 0.855 sterlin olduğunu gösterir.
- Paritede **AL**, soldaki para biriminin sağdakine karşı güçlenmesi beklentisidir.
- Paritede **SAT**, soldaki para biriminin sağdakine karşı zayıflaması beklentisidir.
- Döviz kararları günlük, 4 saatlik ve 1 saatlik trendlerin birleşiminden oluşur.
- Güçlü yapı olsa bile fiyat aşırı uzamışsa sistem AL/SAT yerine geri çekilme veya tepki bekler.
- AL işleminde stop girişin altında; SAT işleminde stop girişin üstünde hesaplanır.

### Veri güvenliği

Eksik veri olduğunda sistem karar üretmemelidir.

Sistem:

- Eksik veriye otomatik 50 puan vermez.
- Tahmini piyasa fiyatını gerçek veri gibi kullanmaz.
- Altın ve gümüş kararlarını birbirinden bağımsız hesaplar.
- Her metal için ayrı destek, direnç ve işlem teyidi üretir.
"""
    )
