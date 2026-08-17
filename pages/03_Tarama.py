import streamlit as st
import pandas as pd
import numpy as np

from modules.data.bist_lists import (
    BIST30,
    BIST50,
    BIST100,
    BIST500,
    SECTOR_MAP as CENTRAL_SECTOR_MAP,
)

from modules.data.yahoo_data import get_stock_analysis

from modules.data.fundamental import (
    get_fundamental_data,
    calculate_fundamental_score,
)

from modules.ai.market_ai import get_market_score


# ==========================================================
# SAYFA AYARLARI
# ==========================================================

st.set_page_config(
    page_title="AI Hisse Tarama",
    page_icon="🔎",
    layout="wide",
)

st.title("🔎 AI Hisse Tarama Merkezi")

st.caption(
    "Teknik + Temel + Momentum + Trend + Hacim + Market "
    "verilerini birleştirerek BIST hisselerinde fırsat ve risk taraması yapar."
)


# ==========================================================
# SKOR AĞIRLIKLARI
# ==========================================================
#
# Genel Skor:
#
# %50 Teknik
# %20 Temel
# %15 60G Momentum
# %15 Market
#
# Finansal Trend BU SAYFADA YOKTUR.
# ==========================================================

GENERAL_TECHNICAL_WEIGHT = 0.50
GENERAL_FUNDAMENTAL_WEIGHT = 0.20
GENERAL_MOMENTUM_WEIGHT = 0.15
GENERAL_MARKET_WEIGHT = 0.15


# ==========================================================
# SEKTÖR SEÇENEKLERİ
# ==========================================================

sector_options = [
    "Tüm Sektörler",

    "Banka",
    "Enerji",
    "Savunma",
    "Çimento",
    "İnşaat",
    "GYO",

    "Ulaştırma",
    "Otomotiv",
    "Perakende",
    "Gıda/İçecek",

    "Holding",
    "Sanayi",
    "Kimya",
    "Madencilik",

    "Teknoloji",
    "Sağlık",
    "Telekomünikasyon",

    "Finans",
    "Sigorta",
    "Turizm",

    "Diğer",
]


# ==========================================================
# YAHOO / SEKTÖR NORMALİZASYONU
# ==========================================================

SECTOR_NORMALIZATION = {

    # ------------------------------------------------------
    # BANKA
    # ------------------------------------------------------

    "Banks": "Banka",
    "Banking": "Banka",
    "Banks—Diversified": "Banka",
    "Banks—Regional": "Banka",
    "Diversified Banks": "Banka",
    "Regional Banks": "Banka",

    # ------------------------------------------------------
    # FİNANS
    # ------------------------------------------------------

    "Financial Services": "Finans",
    "Capital Markets": "Finans",
    "Investment Banking": "Finans",
    "Asset Management": "Finans",
    "Financial": "Finans",

    # ------------------------------------------------------
    # SİGORTA
    # ------------------------------------------------------

    "Insurance": "Sigorta",
    "Insurance—Life": "Sigorta",
    "Insurance—Diversified": "Sigorta",
    "Insurance—Property & Casualty": "Sigorta",
    "Insurance Brokers": "Sigorta",

    # ------------------------------------------------------
    # ENERJİ
    # ------------------------------------------------------

    "Oil & Gas": "Enerji",
    "Oil & Gas Integrated": "Enerji",
    "Oil & Gas E&P": "Enerji",
    "Oil & Gas Refining & Marketing": "Enerji",
    "Oil & Gas Midstream": "Enerji",
    "Utilities": "Enerji",
    "Renewable Energy": "Enerji",
    "Energy": "Enerji",
    "Oil Gas": "Enerji",

    # ------------------------------------------------------
    # SAVUNMA
    # ------------------------------------------------------

    "Aerospace & Defense": "Savunma",
    "Defense": "Savunma",
    "Aerospace": "Savunma",

    # ------------------------------------------------------
    # ULAŞTIRMA
    # ------------------------------------------------------

    "Airlines": "Ulaştırma",
    "Transportation": "Ulaştırma",
    "Railroads": "Ulaştırma",
    "Marine Shipping": "Ulaştırma",
    "Integrated Freight & Logistics": "Ulaştırma",
    "Trucking": "Ulaştırma",
    "Airports & Air Services": "Ulaştırma",

    # ------------------------------------------------------
    # PERAKENDE
    # ------------------------------------------------------

    "Retail": "Perakende",
    "Discount Stores": "Perakende",
    "Grocery Stores": "Perakende",
    "Specialty Retail": "Perakende",
    "Retail—Cyclical": "Perakende",
    "Retail—Defensive": "Perakende",

    # ------------------------------------------------------
    # OTOMOTİV
    # ------------------------------------------------------

    "Auto Manufacturers": "Otomotiv",
    "Auto Parts": "Otomotiv",
    "Auto & Truck Dealerships": "Otomotiv",
    "Automobiles": "Otomotiv",
    "Automotive": "Otomotiv",

    # ------------------------------------------------------
    # HOLDİNG
    # ------------------------------------------------------

    "Conglomerates": "Holding",
    "Diversified Holdings": "Holding",
    "Holding": "Holding",

    # ------------------------------------------------------
    # SANAYİ
    # ------------------------------------------------------

    "Industrial Products": "Sanayi",
    "Machinery": "Sanayi",
    "Steel": "Sanayi",
    "Building Materials": "Sanayi",
    "Construction Materials": "Sanayi",
    "Electrical Equipment": "Sanayi",
    "Manufacturing": "Sanayi",
    "Industrial": "Sanayi",
    "Industrial Products & Services": "Sanayi",

    # ------------------------------------------------------
    # ÇİMENTO
    # ------------------------------------------------------

    "Cement": "Çimento",
    "Cement Products": "Çimento",
    "Cement & Aggregates": "Çimento",
    "Construction Materials—Cement": "Çimento",

    # ------------------------------------------------------
    # İNŞAAT
    # ------------------------------------------------------

    "Engineering & Construction": "İnşaat",
    "Construction": "İnşaat",
    "Engineering": "İnşaat",
    "Construction Services": "İnşaat",

    # ------------------------------------------------------
    # KİMYA
    # ------------------------------------------------------

    "Chemicals": "Kimya",
    "Specialty Chemicals": "Kimya",
    "Basic Materials": "Kimya",

    # ------------------------------------------------------
    # TEKNOLOJİ
    # ------------------------------------------------------

    "Technology": "Teknoloji",
    "Software": "Teknoloji",
    "Information Technology": "Teknoloji",
    "Semiconductors": "Teknoloji",
    "Electronic Components": "Teknoloji",
    "Computer Hardware": "Teknoloji",
    "Information Technology Services": "Teknoloji",
    "Consumer Electronics": "Teknoloji",

    # ------------------------------------------------------
    # SAĞLIK
    # ------------------------------------------------------

    "Healthcare": "Sağlık",
    "Medical Care": "Sağlık",
    "Medical Devices": "Sağlık",
    "Biotechnology": "Sağlık",
    "Drug Manufacturers": "Sağlık",
    "Diagnostics & Research": "Sağlık",
    "Healthcare Plans": "Sağlık",
    "Medical Distribution": "Sağlık",

    # ------------------------------------------------------
    # GIDA / İÇECEK
    # ------------------------------------------------------

    "Food & Beverage": "Gıda/İçecek",
    "Beverages": "Gıda/İçecek",
    "Packaged Foods": "Gıda/İçecek",
    "Food Products": "Gıda/İçecek",
    "Food": "Gıda/İçecek",
    "Beverage": "Gıda/İçecek",

    # ------------------------------------------------------
    # GYO
    # ------------------------------------------------------

    "Real Estate": "GYO",
    "REIT": "GYO",
    "Real Estate Development": "GYO",
    "Real Estate Services": "GYO",

    # ------------------------------------------------------
    # MADENCİLİK
    # ------------------------------------------------------

    "Gold": "Madencilik",
    "Silver": "Madencilik",
    "Copper": "Madencilik",
    "Other Precious Metals & Mining": "Madencilik",
    "Mining": "Madencilik",
    "Metals & Mining": "Madencilik",

    # ------------------------------------------------------
    # TELEKOM
    # ------------------------------------------------------

    "Telecom": "Telekomünikasyon",
    "Telecom Services": "Telekomünikasyon",
    "Communication Services": "Telekomünikasyon",
    "Wireless Communications": "Telekomünikasyon",

    # ------------------------------------------------------
    # TURİZM
    # ------------------------------------------------------

    "Travel Services": "Turizm",
    "Lodging": "Turizm",
    "Resorts & Casinos": "Turizm",
    "Travel": "Turizm",
    "Hotels": "Turizm",
}


# ==========================================================
# SEKTÖR ALIASLARI
# ==========================================================

SECTOR_ALIASES = {

    "cement": "Çimento",
    "çimento": "Çimento",

    "construction": "İnşaat",
    "inşaat": "İnşaat",

    "bank": "Banka",
    "banking": "Banka",
    "banka": "Banka",

    "energy": "Enerji",
    "enerji": "Enerji",

    "defense": "Savunma",
    "defence": "Savunma",
    "savunma": "Savunma",

    "reit": "GYO",
    "real estate": "GYO",
    "gyo": "GYO",

    "transportation": "Ulaştırma",
    "transport": "Ulaştırma",
    "ulaştırma": "Ulaştırma",

    "automotive": "Otomotiv",
    "automotive manufacturers": "Otomotiv",
    "otomotiv": "Otomotiv",

    "retail": "Perakende",
    "perakende": "Perakende",

    "food": "Gıda/İçecek",
    "food & beverage": "Gıda/İçecek",
    "gıda": "Gıda/İçecek",
    "gıda/içecek": "Gıda/İçecek",

    "holding": "Holding",
    "holdings": "Holding",

    "industrial": "Sanayi",
    "sanayi": "Sanayi",

    "chemicals": "Kimya",
    "chemical": "Kimya",
    "kimya": "Kimya",

    "mining": "Madencilik",
    "madencilik": "Madencilik",

    "technology": "Teknoloji",
    "technology services": "Teknoloji",
    "teknoloji": "Teknoloji",

    "healthcare": "Sağlık",
    "health": "Sağlık",
    "sağlık": "Sağlık",

    "telecom": "Telekomünikasyon",
    "telecommunications": "Telekomünikasyon",
    "telekomünikasyon": "Telekomünikasyon",

    "financial services": "Finans",
    "finance": "Finans",
    "finans": "Finans",

    "insurance": "Sigorta",
    "sigorta": "Sigorta",

    "tourism": "Turizm",
    "tourism & travel": "Turizm",
    "turizm": "Turizm",
}


# ==========================================================
# YARDIMCI FONKSİYONLAR
# ==========================================================

def normalize_symbol(symbol):
    """
    Hisse sembolünü standart hale getirir.
    Örnek:
        ASELS.IS -> ASELS
        asels -> ASELS
    """

    symbol = str(symbol).upper().strip()

    if symbol.endswith(".IS"):
        symbol = symbol[:-3]

    return symbol


def safe_float(value, default=0):
    """
    Güvenli float dönüşümü.
    None / NaN / inf / hatalı string durumlarında
    default döndürür.
    """

    try:

        if value is None:
            return default

        if isinstance(value, str):

            value = (
                value
                .replace("%", "")
                .replace("₺", "")
                .replace("TL", "")
                .replace(",", ".")
                .strip()
            )

        value = float(value)

        if np.isnan(value) or np.isinf(value):
            return default

        return value

    except Exception:

        return default


def clamp_score(value, default=50):
    """
    Skoru 0-100 arasında tutar.
    """

    value = safe_float(
        value,
        default,
    )

    return max(
        0,
        min(
            value,
            100,
        ),
    )


def clean_text(value, default="-"):
    """
    Metin değerlerini güvenli hale getirir.
    """

    if value is None:
        return default

    try:

        if pd.isna(value):
            return default

    except Exception:
        pass

    text = str(value).strip()

    if not text:
        return default

    return text


# ==========================================================
# MERKEZİ SEKTÖR HARİTASI
# ==========================================================

SEKTOR_MAP = {}

try:

    for sector_name, symbols in CENTRAL_SECTOR_MAP.items():

        if not symbols:
            continue

        # Merkezi sektör adı da normalize edilir.
        raw_sector = clean_text(
            sector_name,
            "Diğer",
        )

        sector_key = raw_sector.lower().strip()

        normalized_sector = (
            SECTOR_ALIASES.get(
                sector_key,
                raw_sector,
            )
        )

        if normalized_sector not in sector_options:

            # Merkezi haritada farklı Türkçe isim varsa
            # mümkün olduğunca standartlaştır.
            if "çimento" in sector_key:
                normalized_sector = "Çimento"

            elif "inşaat" in sector_key:
                normalized_sector = "İnşaat"

            elif "construction" in sector_key:
                normalized_sector = "İnşaat"

            elif "cement" in sector_key:
                normalized_sector = "Çimento"

            elif "bank" in sector_key:
                normalized_sector = "Banka"

            elif "enerji" in sector_key or "energy" in sector_key:
                normalized_sector = "Enerji"

            elif "savunma" in sector_key or "defense" in sector_key:
                normalized_sector = "Savunma"

            else:
                normalized_sector = "Diğer"

        for symbol in symbols:

            normalized_symbol = normalize_symbol(
                symbol
            )

            if normalized_symbol:

                SEKTOR_MAP[
                    normalized_symbol
                ] = normalized_sector

except Exception as e:

    print(
        f"[SEKTÖR HARİTASI HATASI] {e}"
    )

    SEKTOR_MAP = {}


# ==========================================================
# SEKTÖR BUL
# ==========================================================

def get_sector(symbol, analysis=None):

    symbol = normalize_symbol(symbol)

    # ------------------------------------------------------
    # 1. MERKEZİ SEKTÖR HARİTASI
    # ------------------------------------------------------

    if symbol in SEKTOR_MAP:

        sector = clean_text(
            SEKTOR_MAP[symbol],
            "Diğer",
        )

        if sector in sector_options:

            return sector

    # ------------------------------------------------------
    # 2. ANALİZ VERİSİ
    # ------------------------------------------------------

    if isinstance(analysis, dict):

        possible_keys = [
            "sector",
            "sector_name",
            "sectorName",
            "industry",
            "industry_name",
        ]

        for key in possible_keys:

            sector = analysis.get(key)

            if sector is None:
                continue

            sector = clean_text(
                sector,
                "",
            )

            if not sector:
                continue

            # Zaten Türkçe standart sektör ise
            if sector in sector_options:

                return sector

            # Alias
            sector_lower = sector.lower().strip()

            if sector_lower in SECTOR_ALIASES:

                return SECTOR_ALIASES[
                    sector_lower
                ]

            # Yahoo normalizasyonu
            if sector in SECTOR_NORMALIZATION:

                return SECTOR_NORMALIZATION[
                    sector
                ]

            # Büyük/küçük harf toleransı
            for (
                source_sector,
                target_sector,
            ) in SECTOR_NORMALIZATION.items():

                if (
                    source_sector.lower().strip()
                    == sector_lower
                ):

                    return target_sector

    # ------------------------------------------------------
    # 3. SON ÇARE
    # ------------------------------------------------------

    return "Diğer"


# ==========================================================
# TEMEL VERİ DURUMU
# ==========================================================

def calculate_fundamental_result(symbol):
    """
    Temel veri ve temel skorunu güvenli biçimde hesaplar.

    Dönen yapı:
        score
        status
        available
        error
    """

    result = {
        "score": 50.0,
        "status": "Temel Veri Yok",
        "available": False,
        "error": None,
    }

    try:

        fundamental = get_fundamental_data(
            symbol
        )

    except Exception as e:

        result["error"] = (
            f"{type(e).__name__}: {e}"
        )

        return result

    if fundamental is None:

        return result

    # Boş DataFrame / boş dict kontrolü
    try:

        if hasattr(
            fundamental,
            "empty",
        ):

            if fundamental.empty:
                return result

        elif isinstance(
            fundamental,
            dict,
        ):

            if not fundamental:
                return result

    except Exception:
        pass

    try:

        fund_score = calculate_fundamental_score(
            fundamental
        )

        fund_score = clamp_score(
            fund_score,
            50,
        )

        result["score"] = fund_score
        result["available"] = True
        result["status"] = "Temel Veri Mevcut"

        return result

    except Exception as e:

        result["error"] = (
            f"{type(e).__name__}: {e}"
        )

        return result


# ==========================================================
# RİSK SİSTEMİ
# ==========================================================

def calculate_risk_status(
    daily_change,
    rsi,
    technical_score,
    trend_strength,
):

    daily_change = safe_float(
        daily_change,
        0,
    )

    rsi = safe_float(
        rsi,
        50,
    )

    technical_score = clamp_score(
        technical_score,
        50,
    )

    trend_strength = clamp_score(
        trend_strength,
        50,
    )

    risk_points = 0

    # ------------------------------------------------------
    # Günlük düşüş
    # ------------------------------------------------------

    if daily_change <= -5:

        risk_points += 3

    elif daily_change <= -3:

        risk_points += 2

    elif daily_change <= -2:

        risk_points += 1

    # ------------------------------------------------------
    # Aşırı alım
    # ------------------------------------------------------

    if rsi >= 80:

        risk_points += 2

    elif rsi >= 75:

        risk_points += 1

    # ------------------------------------------------------
    # Teknik
    # ------------------------------------------------------

    if technical_score < 40:

        risk_points += 3

    elif technical_score < 45:

        risk_points += 2

    elif technical_score < 60:

        risk_points += 1

    # ------------------------------------------------------
    # Trend
    # ------------------------------------------------------

    if trend_strength < 35:

        risk_points += 3

    elif trend_strength < 40:

        risk_points += 2

    elif trend_strength < 50:

        risk_points += 1

    # ------------------------------------------------------
    # Sonuç
    # ------------------------------------------------------

    if risk_points >= 5:

        return "🔴 Yüksek Risk"

    if risk_points >= 2:

        return "🟡 Dikkat"

    return "🟢 Normal"


# ==========================================================
# DÜŞÜŞ SİNYALİ
# ==========================================================

def calculate_decline_signal(
    analysis,
    daily_change,
    technical_score,
    trend_strength,
    rsi,
):

    decline_points = 0
    reasons = []

    daily_change = safe_float(
        daily_change,
        0,
    )

    technical_score = clamp_score(
        technical_score,
        50,
    )

    trend_strength = clamp_score(
        trend_strength,
        50,
    )

    rsi = safe_float(
        rsi,
        50,
    )

    # ------------------------------------------------------
    # Günlük düşüş
    # ------------------------------------------------------

    if daily_change <= -5:

        decline_points += 3

        reasons.append(
            "Günlük sert düşüş"
        )

    elif daily_change <= -4:

        decline_points += 2

        reasons.append(
            "Günlük belirgin düşüş"
        )

    elif daily_change <= -2:

        decline_points += 1

        reasons.append(
            "Günlük zayıflama"
        )

    # ------------------------------------------------------
    # Teknik
    # ------------------------------------------------------

    if technical_score < 40:

        decline_points += 3

        reasons.append(
            "Teknik yapı ciddi şekilde zayıf"
        )

    elif technical_score < 45:

        decline_points += 2

        reasons.append(
            "Teknik yapı zayıf"
        )

    elif technical_score < 55:

        decline_points += 1

        reasons.append(
            "Teknik yapı zayıflıyor"
        )

    # ------------------------------------------------------
    # Trend
    # ------------------------------------------------------

    if trend_strength < 35:

        decline_points += 3

        reasons.append(
            "Trend ciddi şekilde zayıf"
        )

    elif trend_strength < 40:

        decline_points += 2

        reasons.append(
            "Trend zayıf"
        )

    elif trend_strength < 50:

        decline_points += 1

        reasons.append(
            "Trend zayıflıyor"
        )

    # ------------------------------------------------------
    # RSI
    # ------------------------------------------------------

    if rsi < 30:

        decline_points += 2

        reasons.append(
            "RSI aşırı zayıf"
        )

    elif rsi < 35:

        decline_points += 1

        reasons.append(
            "RSI zayıf"
        )

    # ------------------------------------------------------
    # Harici sinyal
    # ------------------------------------------------------

    possible_signal_keys = [
        "decline_signal",
        "sell_signal",
        "dusus_sinyali",
        "düşüş_sinyali",
    ]

    external_signal = None

    if isinstance(analysis, dict):

        for key in possible_signal_keys:

            value = analysis.get(key)

            if value is not None:

                value_text = clean_text(
                    value,
                    "",
                )

                if value_text:

                    external_signal = value_text

                    break

    if external_signal:

        lower_signal = (
            external_signal
            .lower()
            .strip()
        )

        if (
            "düşüş" in lower_signal
            or "dus" in lower_signal
            or "sat" in lower_signal
            or "sell" in lower_signal
        ):

            decline_points += 2

            reasons.append(
                "Teknik sistem düşüş sinyali verdi"
            )

    # ------------------------------------------------------
    # Sonuç
    # ------------------------------------------------------

    if decline_points >= 5:

        return (
            "🔴 Düşüş Sinyali",
            " | ".join(reasons),
        )

    if decline_points >= 2:

        return (
            "🟡 Zayıflama",
            " | ".join(reasons),
        )

    return (
        "🟢 Pozitif",
        "Belirgin düşüş teyidi yok",
    )


# ==========================================================
# ADAY TİPİ
# ==========================================================

def determine_candidate_type(
    technical_score,
    fundamental_score,
    momentum_score,
    trend_strength,
    volume_score,
    general_score,
):

    technical_score = clamp_score(
        technical_score,
        50,
    )

    fundamental_score = clamp_score(
        fundamental_score,
        50,
    )

    momentum_score = clamp_score(
        momentum_score,
        50,
    )

    trend_strength = clamp_score(
        trend_strength,
        50,
    )

    volume_score = clamp_score(
        volume_score,
        50,
    )

    general_score = clamp_score(
        general_score,
        50,
    )

    # ------------------------------------------------------
    # Dengeli güçlü
    # ------------------------------------------------------

    if (
        general_score >= 75
        and technical_score >= 70
        and fundamental_score >= 65
        and momentum_score >= 65
        and trend_strength >= 60
    ):

        return "🏆 Dengeli Güçlü"

    # ------------------------------------------------------
    # Momentum
    # ------------------------------------------------------

    if (
        momentum_score >= 85
        and trend_strength >= 70
    ):

        return "🚀 Momentum"

    # ------------------------------------------------------
    # Teknik
    # ------------------------------------------------------

    if technical_score >= 82:

        return "📈 Teknik"

    # ------------------------------------------------------
    # Temel
    # ------------------------------------------------------

    if (
        fundamental_score >= 80
        and technical_score >= 60
    ):

        return "💎 Temel"

    # ------------------------------------------------------
    # Hacim
    # ------------------------------------------------------

    if volume_score >= 85:

        return "🔥 Hacim"

    # ------------------------------------------------------
    # Genel
    # ------------------------------------------------------

    if general_score >= 70:

        return "📊 Genel Aday"

    return "👀 İzleme"


# ==========================================================
# KARAR
# ==========================================================

def get_decision(
    general_score,
    decline_signal,
    risk_status,
):

    general_score = clamp_score(
        general_score,
        0,
    )

    # ======================================================
    # 1. DÜŞÜŞ SİNYALİ EN YÜKSEK ÖNCELİK
    # ======================================================

    if decline_signal == "🔴 Düşüş Sinyali":

        return "🔴 Düşüş Sinyali"

    # ======================================================
    # 2. YÜKSEK RİSK
    # ======================================================

    if (
        risk_status == "🔴 Yüksek Risk"
        and general_score < 80
    ):

        return "🟠 Temkinli"

    # ======================================================
    # 3. GENEL SKOR
    # ======================================================

    if general_score >= 85:

        return "🟢 Güçlü Al"

    if general_score >= 75:

        return "🟢 Al"

    if general_score >= 60:

        return "🟡 Tut"

    if general_score >= 45:

        return "🟠 Zayıf"

    return "🔴 Sat"


# ==========================================================
# SEKTÖR SKORU
# ==========================================================

def calculate_sector_score(group):

    if group is None or group.empty:

        return 0.0

    columns = [
        "Teknik",
        "Temel",
        "60G Momentum",
        "Trend Gücü",
        "Hacim Skoru",
    ]

    values = {}

    for column in columns:

        if column not in group.columns:

            values[column] = 50.0

            continue

        series = pd.to_numeric(
            group[column],
            errors="coerce",
        )

        if series.dropna().empty:

            values[column] = 50.0

        else:

            values[column] = clamp_score(
                series.mean(),
                50,
            )

    score = (

        values["Teknik"] * 0.30

        + values["Temel"] * 0.20

        + values["60G Momentum"] * 0.20

        + values["Trend Gücü"] * 0.15

        + values["Hacim Skoru"] * 0.15

    )

    return round(
        clamp_score(
            score,
            0,
        ),
        1,
    )


# ==========================================================
# SEKTÖR DURUMU
# ==========================================================

def sector_status(
    score,
    stock_count=0,
):

    score = clamp_score(
        score,
        0,
    )

    # ------------------------------------------------------
    # Çok az hisse varsa aşırı kesin ifade kullanma.
    # ------------------------------------------------------

    if stock_count < 2:

        if score >= 70:

            return "🟡 Güçlü*"

        if score >= 50:

            return "🟠 Nötr*"

        return "🔴 Zayıf*"

    # ------------------------------------------------------
    # Normal sınıflandırma
    # ------------------------------------------------------

    if score >= 80:

        return "🟢 Çok Güçlü"

    if score >= 70:

        return "🟢 Güçlü"

    if score >= 60:

        return "🟡 Pozitif"

    if score >= 50:

        return "🟠 Nötr"

    return "🔴 Zayıf"


# ==========================================================
# HİSSE HAVUZLARI
# ==========================================================

pool_map = {

    "BIST 30": BIST30,
    "BIST 50": BIST50,
    "BIST 100": BIST100,
    "BIST 500": BIST500,

}


# ==========================================================
# TARAMA AYARLARI
# ==========================================================

st.subheader(
    "⚙️ Tarama Ayarları"
)

col1, col2, col3, col4 = st.columns(4)


with col1:

    pool_name = st.selectbox(
        "Hisse Havuzu",
        list(pool_map.keys()),
    )


with col2:

    min_score = st.slider(
        "Minimum Genel Skor",
        0,
        100,
        60,
    )


with col3:

    min_momentum = st.slider(
        "Minimum 60G Momentum",
        0,
        100,
        50,
    )


with col4:

    min_trend = st.slider(
        "Minimum Trend Gücü",
        0,
        100,
        50,
    )


# ==========================================================
# SEKTÖR FİLTRESİ
# ==========================================================

selected_sector = st.selectbox(
    "🏭 Sektör Filtresi",
    sector_options,
)


# ==========================================================
# KARAR FİLTRESİ
# ==========================================================

decision_filter = st.multiselect(

    "🎯 Karar Filtresi",

    [
        "🟢 Güçlü Al",
        "🟢 Al",
        "🟡 Tut",
        "🟠 Temkinli",
        "🟠 Zayıf",
        "🔴 Düşüş Sinyali",
        "🔴 Sat",
    ],

    default=[],
)


# ==========================================================
# HAVUZU HAZIRLA
# ==========================================================

selected_pool = [

    normalize_symbol(symbol)

    for symbol in pool_map[pool_name]

    if normalize_symbol(symbol)

]


selected_pool = list(
    dict.fromkeys(
        selected_pool
    )
)


# ==========================================================
# BIST500 KESİN DOĞRULAMA
# ==========================================================

if pool_name == "BIST 500":

    bist500_count = len(
        selected_pool
    )

    bist500_unique = len(
        set(selected_pool)
    )

    if (
        bist500_count != 500
        or bist500_unique != 500
        or not BIST500
    ):

        st.error(
            "🚨 BIST500 TARAMASI KAPALI\n\n"
            f"Bulunan hisse: {bist500_count}\n"
            f"Tekil hisse: {bist500_unique}\n\n"
            "BIST500 tam olarak 500 tekil hisse "
            "olarak doğrulanmadan tarama başlatılamaz."
        )

        st.stop()

    else:

        st.success(
            "✅ BIST500 DOĞRULANDI — "
            "500 tekil hisse taramaya hazır."
        )


# ==========================================================
# SEKTÖR ÖN FİLTRESİ
# ==========================================================

if selected_sector != "Tüm Sektörler":

    sector_symbols = []

    # ------------------------------------------------------
    # Merkezi haritadaki seçilen sektörü kullan
    # ------------------------------------------------------

    for symbol, sector_name in SEKTOR_MAP.items():

        if sector_name == selected_sector:

            sector_symbols.append(
                normalize_symbol(symbol)
            )

    sector_symbols = list(
        dict.fromkeys(
            sector_symbols
        )
    )

    selected_pool = [

        symbol

        for symbol in selected_pool

        if symbol in sector_symbols

    ]


# ==========================================================
# SEKTÖR VERİ KONTROLÜ
# ==========================================================

with st.expander(
    "🔎 Sektör / Havuz Veri Kontrolü"
):

    st.write(
        f"Merkezi sektör sayısı: "
        f"**{len(CENTRAL_SECTOR_MAP)}**"
    )

    st.write(
        f"Merkezi sektör haritasındaki hisse sayısı: "
        f"**{len(SEKTOR_MAP)}**"
    )

    st.write(
        f"Seçilen havuz: "
        f"**{pool_name}**"
    )

    st.write(
        f"Seçilen sektör: "
        f"**{selected_sector}**"
    )

    st.write(
        f"Tarama havuzundaki hisse: "
        f"**{len(selected_pool)}**"
    )


# ==========================================================
# TARAMA HAVUZU BİLGİSİ
# ==========================================================

if selected_sector == "Tüm Sektörler":

    st.info(
        f"📊 **{pool_name}** havuzu seçildi — "
        f"**{len(selected_pool)} hisse** taranacak."
    )

else:

    st.info(
        f"🏭 **{selected_sector}** sektörü seçildi — "
        f"**{len(selected_pool)} hisse** taranacak."
    )


# ==========================================================
# SEKTÖR SEÇİMİ SONRASI HİSSE KALMADIYSA
# ==========================================================

if (
    selected_sector != "Tüm Sektörler"
    and len(selected_pool) == 0
):

    st.warning(
        f"⚠️ **{selected_sector}** sektöründe "
        f"**{pool_name}** havuzuna ait hisse bulunamadı."
    )

    st.stop()


# ==========================================================
# SONUÇ SAYISI
# ==========================================================

max_results = st.selectbox(

    "Gösterilecek maksimum hisse",

    [10, 20, 30, 50, 100],

    index=1,

)


# ==========================================================
# TARAMA
# ==========================================================

if st.button(

    f"🔎 {pool_name}'i Tara",

    width="stretch",

    type="primary",

):

    all_results = []

    progress = st.progress(0)

    status = st.empty()

    total = len(selected_pool)

    # ------------------------------------------------------
    # Atlanan hisseler
    # ------------------------------------------------------

    skipped_analysis = []
    skipped_fundamental = []
    skipped_errors = []

    # ======================================================
    # HAVUZ BOŞSA
    # ======================================================

    if total == 0:

        st.warning(
            "Tarama yapılacak hisse bulunamadı."
        )

        st.stop()

    # ======================================================
    # MARKET SCORE
    # ======================================================

    try:

        market_result = get_market_score()

        if isinstance(
            market_result,
            tuple,
        ):

            if len(market_result) >= 2:

                market_score = market_result[0]
                market_reasons = market_result[1]

            elif len(market_result) == 1:

                market_score = market_result[0]
                market_reasons = []

            else:

                market_score = 50
                market_reasons = []

        else:

            market_score = market_result
            market_reasons = []

        market_score = clamp_score(
            market_score,
            50,
        )

    except Exception as e:

        st.error(
            f"Market Score alınamadı: {e}"
        )

        st.stop()


    st.info(
        f"🌍 Güncel Market Score: "
        f"**{market_score:.0f}/100**"
    )


    if market_reasons:

        with st.expander(
            "🌍 Market Score Gerekçeleri"
        ):

            if isinstance(
                market_reasons,
                (list, tuple),
            ):

                for reason in market_reasons:

                    st.write(
                        f"• {reason}"
                    )

            else:

                st.write(
                    market_reasons
                )


    # ======================================================
    # HİSSELER
    # ======================================================

    for i, symbol in enumerate(
        selected_pool
    ):

        status.write(
            f"Tarama yapılıyor: "
            f"**{symbol}** "
            f"({i + 1}/{total})"
        )

        try:

            # ==================================================
            # TEKNİK ANALİZ
            # ==================================================

            try:

                analysis = get_stock_analysis(
                    symbol
                )

            except Exception as e:

                skipped_analysis.append(
                    (
                        symbol,
                        f"{type(e).__name__}: {e}",
                    )
                )

                continue


            if analysis is None:

                skipped_analysis.append(
                    (
                        symbol,
                        "Teknik analiz verisi None döndü",
                    )
                )

                continue


            if not isinstance(
                analysis,
                dict,
            ):

                skipped_analysis.append(
                    (
                        symbol,
                        "Teknik analiz sonucu dict değil",
                    )
                )

                continue


            # ==================================================
            # TEKNİK DEĞERLER
            # ==================================================

            technical_score = clamp_score(
                analysis.get(
                    "score",
                    50,
                ),
                50,
            )


            momentum_60_score = clamp_score(
                analysis.get(
                    "momentum_60_score",
                    50,
                ),
                50,
            )


            trend_strength = clamp_score(
                analysis.get(
                    "trend_strength",
                    50,
                ),
                50,
            )


            volume_score = clamp_score(
                analysis.get(
                    "volume_score",
                    50,
                ),
                50,
            )


            daily_change = safe_float(
                analysis.get(
                    "change",
                    0,
                ),
                0,
            )


            rsi = safe_float(
                analysis.get(
                    "rsi",
                    50,
                ),
                50,
            )


            price = safe_float(
                analysis.get(
                    "price",
                    0,
                ),
                0,
            )


            # ==================================================
            # SEKTÖR
            # ==================================================

            sector = get_sector(
                symbol,
                analysis,
            )


            # ==================================================
            # TEMEL
            # ==================================================

            fundamental_result = (
                calculate_fundamental_result(
                    symbol
                )
            )

            fund_score = clamp_score(
                fundamental_result["score"],
                50,
            )

            fundamental_available = (
                fundamental_result["available"]
            )

            fundamental_status = (
                fundamental_result["status"]
            )

            fundamental_error = (
                fundamental_result["error"]
            )

            if not fundamental_available:

                skipped_fundamental.append(
                    (
                        symbol,
                        fundamental_error
                        or "Temel veri bulunamadı",
                    )
                )


            # ==================================================
            # GENEL SKOR
            # ==================================================
            #
            # %50 Teknik
            # %20 Temel
            # %15 Momentum
            # %15 Market
            #
            # Finansal trend burada kullanılmıyor.
            # ==================================================

            general_score = (

                technical_score
                * GENERAL_TECHNICAL_WEIGHT

                + fund_score
                * GENERAL_FUNDAMENTAL_WEIGHT

                + momentum_60_score
                * GENERAL_MOMENTUM_WEIGHT

                + market_score
                * GENERAL_MARKET_WEIGHT

            )


            general_score = clamp_score(
                general_score,
                50,
            )


            # ==================================================
            # RİSK
            # ==================================================

            risk_status = calculate_risk_status(

                daily_change,

                rsi,

                technical_score,

                trend_strength,

            )


            # ==================================================
            # DÜŞÜŞ
            # ==================================================

            decline_signal, decline_reason = (

                calculate_decline_signal(

                    analysis,

                    daily_change,

                    technical_score,

                    trend_strength,

                    rsi,

                )

            )


            # ==================================================
            # ADAY TİPİ
            # ==================================================

            candidate_type = (

                determine_candidate_type(

                    technical_score,

                    fund_score,

                    momentum_60_score,

                    trend_strength,

                    volume_score,

                    general_score,

                )

            )


            # ==================================================
            # KARAR
            # ==================================================

            decision = get_decision(

                general_score,

                decline_signal,

                risk_status,

            )


            # ==================================================
            # SONUÇ
            # ==================================================

            all_results.append({

                "Hisse": symbol,

                "Sektör": sector,

                "Fiyat": price,

                "Günlük %": daily_change,

                "Genel Skor": round(
                    general_score,
                    1,
                ),

                "Teknik": round(
                    technical_score,
                    1,
                ),

                "Temel": round(
                    fund_score,
                    1,
                ),

                "Temel Veri": (
                    "✅ Mevcut"
                    if fundamental_available
                    else "⚠️ Yok"
                ),

                "60G Momentum": round(
                    momentum_60_score,
                    1,
                ),

                "Market": round(
                    market_score,
                    1,
                ),

                "Trend Gücü": round(
                    trend_strength,
                    1,
                ),

                "Hacim Skoru": round(
                    volume_score,
                    1,
                ),

                "RSI": round(
                    rsi,
                    1,
                ),

                "Trend": clean_text(
                    analysis.get(
                        "trend",
                        "-",
                    )
                ),

                "Risk": risk_status,

                "Düşüş Sinyali": decline_signal,

                "Düşüş Nedeni": decline_reason,

                "Aday Tipi": candidate_type,

                "Karar": decision,

                "Destek": analysis.get(
                    "support"
                ),

                "Direnç": analysis.get(
                    "resistance"
                ),

            })


        except Exception as e:

            skipped_errors.append(
                (
                    symbol,
                    f"{type(e).__name__}: {e}",
                )
            )

            print(
                f"[TARAMA HATASI] "
                f"{symbol}: "
                f"{type(e).__name__}: {e}"
            )


        finally:

            progress.progress(
                min(
                    (i + 1) / total,
                    1.0,
                )
            )


    status.empty()

    progress.empty()


    # ======================================================
    # TARAMA SONUÇ BİLGİSİ
    # ======================================================

    scanned_count = len(all_results)

    skipped_count = (
        len(skipped_analysis)
        + len(skipped_errors)
    )


    # ======================================================
    # SONUÇ YOK
    # ======================================================

    if not all_results:

        st.warning(
            "Tarama sonucunda geçerli veri alınamadı."
        )

        with st.expander(
            "🔎 Atlanan hisseleri göster"
        ):

            for symbol, reason in (
                skipped_analysis
            ):

                st.write(
                    f"**{symbol}** — {reason}"
                )

            for symbol, reason in (
                skipped_errors
            ):

                st.write(
                    f"**{symbol}** — {reason}"
                )

        st.stop()


    # ======================================================
    # DATAFRAME
    # ======================================================

    all_df = pd.DataFrame(
        all_results
    )


    # ======================================================
    # SAYISAL KOLONLARI GARANTİLE
    # ======================================================

    numeric_columns = [

        "Fiyat",
        "Günlük %",
        "Genel Skor",
        "Teknik",
        "Temel",
        "60G Momentum",
        "Market",
        "Trend Gücü",
        "Hacim Skoru",
        "RSI",

    ]


    for column in numeric_columns:

        if column in all_df.columns:

            all_df[column] = pd.to_numeric(
                all_df[column],
                errors="coerce",
            )


    # ======================================================
    # SEKTÖR ANALİZİ
    # ======================================================

    sector_rows = []


    for sector_name, group in (
        all_df.groupby(
            "Sektör",
            dropna=False,
        )
    ):

        sector_name = clean_text(
            sector_name,
            "Diğer",
        )

        sector_score = calculate_sector_score(
            group
        )


        # --------------------------------------------------
        # Sektör lideri
        # --------------------------------------------------

        strongest_stock = (

            group

            .sort_values(
                [
                    "Genel Skor",
                    "Teknik",
                    "60G Momentum",
                ],
                ascending=False,
            )

            .iloc[0]

        )


        positive_count = len(

            group[
                group["Genel Skor"] >= 70
            ]

        )


        decline_count = len(

            group[
                group["Düşüş Sinyali"]
                == "🔴 Düşüş Sinyali"
            ]

        )


        sector_rows.append({

            "Sektör": sector_name,

            "Hisse Sayısı": len(
                group
            ),

            "Sektör Skoru": sector_score,

            "Durum": sector_status(
                sector_score,
                len(group),
            ),

            "Ort. Genel": round(
                group["Genel Skor"].mean(),
                1,
            ),

            "Ort. Teknik": round(
                group["Teknik"].mean(),
                1,
            ),

            "Ort. Temel": round(
                group["Temel"].mean(),
                1,
            ),

            "Ort. Momentum": round(
                group["60G Momentum"].mean(),
                1,
            ),

            "Ort. Trend": round(
                group["Trend Gücü"].mean(),
                1,
            ),

            "Ort. Hacim": round(
                group["Hacim Skoru"].mean(),
                1,
            ),

            "Güçlü Hisse": positive_count,

            "Düşüş Sinyali": decline_count,

            "Sektör Lideri": (
                strongest_stock["Hisse"]
            ),

            "Lider Skoru": (
                strongest_stock["Genel Skor"]
            ),

        })


    sector_df = pd.DataFrame(
        sector_rows
    )


    if not sector_df.empty:

        sector_df = sector_df.sort_values(
            [
                "Sektör Skoru",
                "Ort. Genel",
            ],
            ascending=False,
        ).reset_index(
            drop=True
        )


    # ======================================================
    # HİSSE FİLTRELERİ
    # ======================================================

    df = all_df.copy()


    # ------------------------------------------------------
    # Sektör
    # ------------------------------------------------------

    if selected_sector != "Tüm Sektörler":

        df = df[
            df["Sektör"]
            == selected_sector
        ]


    # ------------------------------------------------------
    # Genel skor
    # ------------------------------------------------------

    df = df[
        df["Genel Skor"]
        >= min_score
    ]


    # ------------------------------------------------------
    # Momentum
    # ------------------------------------------------------

    df = df[
        df["60G Momentum"]
        >= min_momentum
    ]


    # ------------------------------------------------------
    # Trend
    # ------------------------------------------------------

    df = df[
        df["Trend Gücü"]
        >= min_trend
    ]


    # ------------------------------------------------------
    # Karar
    # ------------------------------------------------------

    if decision_filter:

        df = df[
            df["Karar"].isin(
                decision_filter
            )
        ]


    # ------------------------------------------------------
    # Sıralama
    # ------------------------------------------------------

    df = df.sort_values(

        [
            "Genel Skor",
            "Teknik",
            "60G Momentum",
            "Trend Gücü",
        ],

        ascending=False,

    )


    display_df = df.head(
        max_results
    ).copy()


    # ======================================================
    # ÜST ÖZET
    # ======================================================

    st.success(

        f"✅ Tarama tamamlandı — "
        f"**{len(all_df)}** hisse analiz edildi."

    )


    c1, c2, c3, c4, c5 = st.columns(5)


    with c1:

        st.metric(
            "Analiz Edilen",
            len(all_df),
        )


    with c2:

        st.metric(
            "Filtre Sonucu",
            len(df),
        )


    with c3:

        st.metric(
            "En Yüksek Skor",
            f"{all_df['Genel Skor'].max():.1f}",
        )


    with c4:

        if not sector_df.empty:

            st.metric(
                "En Güçlü Sektör",
                sector_df.iloc[0]["Sektör"],
            )

        else:

            st.metric(
                "En Güçlü Sektör",
                "-",
            )


    with c5:

        st.metric(
            "Market Score",
            f"{market_score:.0f}",
        )


    # ======================================================
    # VERİ KALİTESİ
    # ======================================================

    st.subheader(
        "🧪 Tarama Veri Kalitesi"
    )


    fundamental_missing_count = len(
        skipped_fundamental
    )

    total_pool_count = len(
        selected_pool
    )


    q1, q2, q3 = st.columns(3)


    with q1:

        st.metric(
            "Geçerli Teknik Analiz",
            len(all_df),
        )


    with q2:

        st.metric(
            "Temel Verisi Eksik",
            fundamental_missing_count,
        )


    with q3:

        st.metric(
            "Teknik Veri Nedeniyle Atlanan",
            skipped_count,
        )


    if fundamental_missing_count > 0:

        st.warning(
            f"⚠️ {fundamental_missing_count} hissede "
            "temel veri alınamadı. Bu hisselerde Temel "
            "puanı nötr 50 olarak hesaplandı ve sonuçlarda "
            "'⚠️ Yok' olarak işaretlendi."
        )


    if skipped_analysis or skipped_errors:

        with st.expander(
            "🔎 Teknik analiz nedeniyle atlanan hisseler"
        ):

            for symbol, reason in (
                skipped_analysis
            ):

                st.write(
                    f"**{symbol}** — {reason}"
                )

            for symbol, reason in (
                skipped_errors
            ):

                st.write(
                    f"**{symbol}** — {reason}"
                )


    # ======================================================
    # SEKTÖR GÜÇ HARİTASI
    # ======================================================

    st.subheader(
        "🏭 Sektör Güç Haritası"
    )

    st.caption(
        "Sektör skoru Market Score'dan bağımsızdır. "
        "Teknik + temel + momentum + trend + hacim "
        "gücünü karşılaştırır. Az hisseli sektörlerde "
        "durum daha temkinli gösterilir."
    )


    if not sector_df.empty:

        sector_display = sector_df[

            [
                "Sektör",
                "Hisse Sayısı",
                "Sektör Skoru",
                "Durum",
                "Ort. Genel",
                "Ort. Teknik",
                "Ort. Temel",
                "Ort. Momentum",
                "Ort. Trend",
                "Ort. Hacim",
                "Güçlü Hisse",
                "Düşüş Sinyali",
                "Sektör Lideri",
                "Lider Skoru",
            ]

        ]


        st.dataframe(

            sector_display,

            width="stretch",

            hide_index=True,

            column_config={

                "Sektör Skoru":
                    st.column_config.NumberColumn(
                        "🏆 Sektör Skoru",
                        format="%.1f",
                    ),

                "Ort. Genel":
                    st.column_config.NumberColumn(
                        "📊 Ort. Genel",
                        format="%.1f",
                    ),

                "Ort. Teknik":
                    st.column_config.NumberColumn(
                        "📈 Ort. Teknik",
                        format="%.1f",
                    ),

                "Ort. Temel":
                    st.column_config.NumberColumn(
                        "💎 Ort. Temel",
                        format="%.1f",
                    ),

                "Ort. Momentum":
                    st.column_config.NumberColumn(
                        "🚀 Ort. Momentum",
                        format="%.1f",
                    ),

                "Ort. Trend":
                    st.column_config.NumberColumn(
                        "📈 Ort. Trend",
                        format="%.1f",
                    ),

                "Ort. Hacim":
                    st.column_config.NumberColumn(
                        "📊 Ort. Hacim",
                        format="%.1f",
                    ),

                "Lider Skoru":
                    st.column_config.NumberColumn(
                        "Lider Skoru",
                        format="%.1f",
                    ),

            },

        )


    # ======================================================
    # EN GÜÇLÜ SEKTÖR
    # ======================================================

    if not sector_df.empty:

        strongest = sector_df.iloc[0]


        st.success(

            f"🏆 **En Güçlü Sektör: "
            f"{strongest['Sektör']}** | "
            f"Sektör Skoru: "
            f"**{strongest['Sektör Skoru']:.1f}** | "
            f"Lider: "
            f"**{strongest['Sektör Lideri']}**"

        )


        weak_sectors = sector_df[
            sector_df["Sektör Skoru"] < 50
        ]


        if not weak_sectors.empty:

            st.warning(

                "⚠️ Zayıf sektörler: "
                + ", ".join(
                    weak_sectors[
                        "Sektör"
                    ].tolist()
                )

            )


    # ======================================================
    # FİLTRE SONUÇLARI
    # ======================================================

    st.subheader(

        f"🏆 {pool_name} — "
        f"AI PRO Fırsat Listesi"

    )


    if display_df.empty:

        st.warning(
            "Seçilen kriterlere uygun hisse bulunamadı."
        )

    else:

        st.dataframe(

            display_df,

            width="stretch",

            hide_index=True,

            column_config={

                "Fiyat":
                    st.column_config.NumberColumn(
                        "Fiyat",
                        format="%.2f TL",
                    ),

                "Günlük %":
                    st.column_config.NumberColumn(
                        "Günlük %",
                        format="%.2f",
                    ),

                "Genel Skor":
                    st.column_config.NumberColumn(
                        "🏆 Genel",
                        format="%.1f",
                    ),

                "Teknik":
                    st.column_config.NumberColumn(
                        "📈 Teknik",
                        format="%.1f",
                    ),

                "Temel":
                    st.column_config.NumberColumn(
                        "💎 Temel",
                        format="%.1f",
                    ),

                "60G Momentum":
                    st.column_config.NumberColumn(
                        "🚀 Momentum",
                        format="%.1f",
                    ),

                "Market":
                    st.column_config.NumberColumn(
                        "🌍 Market",
                        format="%.1f",
                    ),

                "Trend Gücü":
                    st.column_config.NumberColumn(
                        "📈 Trend",
                        format="%.1f",
                    ),

                "Hacim Skoru":
                    st.column_config.NumberColumn(
                        "📊 Hacim",
                        format="%.1f",
                    ),

                "RSI":
                    st.column_config.NumberColumn(
                        "RSI",
                        format="%.1f",
                    ),

                "Destek":
                    st.column_config.NumberColumn(
                        "Destek",
                        format="%.2f",
                    ),

                "Direnç":
                    st.column_config.NumberColumn(
                        "Direnç",
                        format="%.2f",
                    ),

            },

        )


    # ======================================================
    # EN GÜÇLÜ 10
    # ======================================================

    if not display_df.empty:

        st.subheader(
            "⭐ En Güçlü Hisseler"
        )


        top10 = display_df.head(10)


        for rank, (_, row) in enumerate(

            top10.iterrows(),

            start=1,

        ):

            score = safe_float(
                row["Genel Skor"],
                0,
            )


            if score >= 85:

                emoji = "🟢"

            elif score >= 75:

                emoji = "🟢"

            elif score >= 60:

                emoji = "🟡"

            else:

                emoji = "🔴"


            st.write(

                f"**{rank}.** {emoji} "
                f"**{row['Hisse']}** — "
                f"{row['Sektör']} | "
                f"Genel: **{score:.0f}** | "
                f"Teknik: **{row['Teknik']:.0f}** | "
                f"Temel: **{row['Temel']:.0f}** | "
                f"60G: **{row['60G Momentum']:.0f}** | "
                f"Trend: **{row['Trend Gücü']:.0f}** | "
                f"{row['Düşüş Sinyali']} | "
                f"Karar: **{row['Karar']}**"

            )


    # ======================================================
    # DÜŞÜŞ SİNYALLERİ
    # ======================================================

    decline_df = all_df[

        all_df["Düşüş Sinyali"]
        == "🔴 Düşüş Sinyali"

    ].sort_values(

        [
            "Genel Skor",
            "Teknik",
        ],

        ascending=False,

    )


    if not decline_df.empty:

        st.subheader(
            "🔴 Düşüş Sinyali Veren Hisseler"
        )


        st.caption(

            "Genel skoru yüksek olsa bile teknik "
            "yapısı bozulan hisseler ayrıca gösterilir. "
            "Bu sinyal genel skorun üzerine çıkar."

        )


        st.dataframe(

            decline_df[

                [
                    "Hisse",
                    "Sektör",
                    "Genel Skor",
                    "Teknik",
                    "60G Momentum",
                    "Trend Gücü",
                    "RSI",
                    "Günlük %",
                    "Düşüş Nedeni",
                    "Risk",
                    "Karar",
                ]

            ].head(20),

            width="stretch",

            hide_index=True,

        )


    # ======================================================
    # ADAY DAĞILIMI
    # ======================================================

    if not display_df.empty:

        st.subheader(
            "🎯 Aday Dağılımı"
        )


        candidate_counts = (

            display_df[
                "Aday Tipi"
            ]

            .value_counts()

        )


        cols = st.columns(

            min(

                max(
                    len(candidate_counts),
                    1,
                ),

                4,

            )

        )


        for i, (
            candidate,
            count,
        ) in enumerate(

            candidate_counts.items()

        ):

            with cols[
                i % len(cols)
            ]:

                st.metric(
                    candidate,
                    count,
                )


    # ======================================================
    # KARAR DAĞILIMI
    # ======================================================

    if not all_df.empty:

        st.subheader(
            "🎯 Karar Dağılımı"
        )


        decision_counts = (
            all_df["Karar"]
            .value_counts()
        )


        decision_cols = st.columns(
            min(
                max(
                    len(decision_counts),
                    1,
                ),
                4,
            )
        )


        for i, (
            decision_name,
            count,
        ) in enumerate(
            decision_counts.items()
        ):

            with decision_cols[
                i % len(decision_cols)
            ]:

                st.metric(
                    decision_name,
                    count,
                )

# ======================================================
# SEKTÖR LİDERLERİ
# ======================================================

    st.subheader(
        "🔍 Sektör Liderleri"
    )

    if not sector_df.empty:

        for _, sector_row in sector_df.iterrows():

            sector_name = str(
                sector_row["Sektör"]
            )

            sector_score = safe_float(
                sector_row["Sektör Skoru"],
                0,
            )

            stock_count = int(
                safe_float(
                    sector_row["Hisse Sayısı"],
                    0,
                )
            )

            leader = str(
                sector_row["Sektör Lideri"]
            )

            # --------------------------------------------------
            # SEKTÖR DURUMU
            # Fonksiyon sonucunu önce değişkene alıyoruz.
            # Böylece f-string parantez/tırnak problemi olmaz.
            # --------------------------------------------------

            sector_status_text = sector_status(
                sector_score,
                stock_count,
            )

            # --------------------------------------------------
            # SEKTÖR HİSSELERİ
            # --------------------------------------------------

            sector_stocks = (
                all_df[
                    all_df["Sektör"] == sector_name
                ]
                .sort_values(
                    [
                        "Genel Skor",
                        "Teknik",
                        "60G Momentum",
                    ],
                    ascending=False,
                )
                .head(5)
            )

            # --------------------------------------------------
            # EXPANDER
            # --------------------------------------------------

            expander_title = (
                f"🏭 {sector_name} "
                f"— {sector_status_text} "
                f"— Skor: {sector_score:.1f}"
            )

            with st.expander(
                expander_title
            ):

                st.write(
                    f"⭐ **Sektör Lideri:** "
                    f"{leader}"
                )

                st.write(
                    f"📊 **Hisse Sayısı:** "
                    f"{stock_count}"
                )

                st.dataframe(
                    sector_stocks[
                        [
                            "Hisse",
                            "Genel Skor",
                            "Teknik",
                            "Temel",
                            "Temel Veri",
                            "60G Momentum",
                            "Trend Gücü",
                            "Hacim Skoru",
                            "Düşüş Sinyali",
                            "Risk",
                            "Karar",
                        ]
                    ],
                    width="stretch",
                    hide_index=True,
                )


    # ======================================================
    # CSV
    # ======================================================

    csv = (
        all_df
        .to_csv(index=False)
        .encode("utf-8-sig")
    )

    st.download_button(
        "📥 Tüm Tarama Sonuçlarını CSV olarak indir",
        data=csv,
        file_name="bist_ai_pro_tarama_sonuclari.csv",
        mime="text/csv",
        width="stretch",
    )
    # ======================================================
    # CSV
    # ======================================================

    csv = (

        all_df

        .to_csv(
            index=False
        )

        .encode(
            "utf-8-sig"
        )

    )


    st.download_button(

        "📥 Tüm Tarama Sonuçlarını CSV olarak indir",

        data=csv,

        file_name=(
            "bist_ai_pro_tarama_sonuclari.csv"
        ),

        mime="text/csv",

        width="stretch",

    )