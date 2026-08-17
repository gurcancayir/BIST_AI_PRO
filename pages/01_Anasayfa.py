import html
import json
import re
from email.utils import parsedate_to_datetime
import xml.etree.ElementTree as ET
import sqlite3
from pathlib import Path

import pandas as pd
import requests
import streamlit as st

# ==========================================================
# SAYFA AYARLARI
# ==========================================================

st.set_page_config(
    page_title="BIST AI PRO",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ==========================================================
# DATABASE
# ==========================================================

from database.database import create_tables

create_tables()


# ==========================================================
# MODÜLLER
# ==========================================================

from modules.dashboard.hero import show_hero
from modules.dashboard.market_summary import show_market_summary


# ==========================================================
# GENEL STİL
# ==========================================================

st.markdown(
    """
    <style>

    .block-container {
        padding-top: 1rem;
        padding-bottom: 2rem;
    }

    [data-testid="stMetricValue"] {
        font-size: 1.5rem;
    }

    .block-container h2,
    .block-container h3 {
        margin-top: 0.2rem;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# ==========================================================
# SIDEBAR
# ==========================================================

with st.sidebar:

   

   

    st.markdown("### 📌 GÜNLÜK KULLANIM SIRASI")

    st.markdown(
        """
        **1. 🏠 Anasayfa**  
        Piyasa uygun mu?

        **2. 🔎 Tarama**  
        Aday hisseleri bul.

        **3. 📊 Hisse Analiz**  
        Adayı doğrula.

        **4. ⚡ Günlük Trade**  
        Bugün işlem fırsatı var mı?

        **5. 🎯 Karar Destek**  
        Son kararı ver.

        **6. 💼 Portföy**  
        Mevcut pozisyonları yönet.
        """
    )

    st.divider()

    st.warning(
        "⚠️ Tek bir göstergeyle işlem yapılmaz. "
        "Karar teyit ile verilir."
    )

    st.divider()

    st.caption(
        "BIST AI PRO • Disiplinli Karar Sistemi"
    )


# ==========================================================
# BAŞLIK
# ==========================================================

st.title("🏠 BIST AI PRO")

st.subheader(
    "Piyasa Kontrol Merkezi"
)

st.caption(
    "Günün ilk kontrolü: Piyasa → Sektör → Önemli Haberler → Hisse"
)


# ==========================================================
# 1 — PİYASA GENEL DURUMU
# ==========================================================

st.divider()

st.header("🌍 1. Piyasa Durumu")

show_hero()

show_market_summary()

# ==========================================================
# 2 — SEKTÖR GÜCÜ
# ==========================================================

st.divider()

st.header("🔥 2. Sektör Güç Haritası")

st.caption(
    "Sektör skoru yalnızca tek bir göstergenin ortalaması değildir. "
    "Hisse gücü, momentum, trend, sektör iç genişliği ve BIST'e "
    "göre relatif performans birlikte değerlendirilir."
)

SECTOR_GROUPS = [
    ("🏢", "Holding", ["holding", "holdings", "investment holding", "conglomerate"]),
    ("🏦", "Bankacılık", ["banka", "bank", "bankacılık", "bankacilik", "banks"]),
    ("💳", "Finans", ["finans", "financial services", "fintech", "insurance", "sigorta", "leasing", "faktoring"]),
    ("🏭", "Sanayi", ["sanayi", "industrial", "industrials", "manufacturing", "imalat", "üretim", "uretim"]),
    ("🧪", "Kimya", ["kimya", "chemical", "chemicals"]),
    ("🧱", "Çimento", ["çimento", "cimento", "cement"]),
    ("🪟", "Cam", ["cam", "glass"]),
    ("🧵", "Tekstil", ["tekstil", "textile", "apparel"]),
    ("🚗", "Otomotiv", ["otomotiv", "automotive", "auto"]),
    ("🍽️", "Gıda", ["gıda", "gida", "food", "beverage", "consumer defensive"]),
    ("🛒", "Perakende", ["perakende", "retail"]),
    ("⚡", "Enerji", ["enerji", "energy"]),
    ("🔌", "Elektrik", ["elektrik", "utilities", "utility"]),
    ("🛢️", "Petrol & Rafineri", ["petrol", "oil", "refinery", "refining", "petrokimya"]),
    ("⛏️", "Madencilik", ["madencilik", "mining", "metals & mining"]),
    ("🌾", "Tarım", ["tarım", "tarim", "agriculture", "fertilizers", "gübre", "gubre"]),
    ("🏗️", "İnşaat", ["inşaat", "insaat", "construction"]),
    ("🏢", "GYO", ["gyo", "real estate", "reit"]),
    ("🛡️", "Savunma", ["savunma", "defence", "defense", "aerospace & defense"]),
    ("💻", "Teknoloji", ["teknoloji", "technology", "software"]),
    ("📡", "Telekom", ["telekom", "telecommunications", "communication services"]),
    ("✈️", "Ulaştırma", ["ulaştırma", "ulastirma", "transport", "airlines", "havacılık"]),
    ("📦", "Lojistik", ["lojistik", "logistics", "transportation"]),
    ("🏨", "Turizm", ["turizm", "tourism", "hotel", "hospitality"]),
    ("🩺", "Sağlık", ["sağlık", "saglik", "healthcare", "health"]),
    ("🛍️", "Tüketim", ["tüketim", "tuketim", "consumer"]),
]

def _find_database():
    """
    borsa.db için güvenli yol çözümleme.
    Anasayfa dış veri taraması yapmaz; yalnızca yerel SQLite DB'yi bulur.
    """
    candidates = [
        Path("borsa.db"),
        Path("data") / "borsa.db",
        Path("database") / "borsa.db",
        Path(__file__).resolve().parent / "borsa.db",
        Path(__file__).resolve().parent.parent / "borsa.db",
    ]

    for path in candidates:
        if path.exists():
            return path

    # Streamlit çalışma dizininden bağımsız olarak üst dizinlerde ara.
    current = Path(__file__).resolve().parent

    for parent in [current, *current.parents]:
        candidate = parent / "borsa.db"
        if candidate.exists():
            return candidate

    return None


# ==========================================================
# BIST SEKTÖR SINIFLANDIRMASI
# ==========================================================
# Ticker bazlı eşleştirme her zaman ham DB sektör bilgisinden
# önce gelir. Böylece DB'deki genel/yanlış sektör adı yüzünden
# CVKMD, TARKM, ENKAI, holdingler vb. yanlış kartta görünmez.
#
# Bu liste "anasayfa" gösterim sınıflandırmasıdır; veritabanındaki
# ham sektör alanını değiştirmez.
TICKER_SECTOR_OVERRIDES = {
    # -----------------------------
    # HOLDİNG
    # -----------------------------
    "KCHOL": "Holding",
    "SAHOL": "Holding",
    "DOHOL": "Holding",
    "AGHOL": "Holding",
    "ALARK": "Holding",
    "GLYHO": "Holding",
    "POLHO": "Holding",
    "GSDHO": "Holding",
    "IEYHO": "Holding",
    "TAVHL": "Ulaştırma",
    "RYSAS": "Lojistik",

    # -----------------------------
    # DEMİR-ÇELİK
    # -----------------------------
    "EREGL": "Sanayi",
    "KRDMD": "Sanayi",
    "BRSAN": "Sanayi",
    "KCAER": "Sanayi",
    "IZMDC": "Sanayi",
    "DOAS": "Otomotiv",

    # -----------------------------
    # MADENCİLİK
    # -----------------------------
    "CVKMD": "Madencilik",
    "KOZAL": "Madencilik",
    "KOZAA": "Madencilik",
    "IPEKE": "Madencilik",
    "TRMET": "Madencilik",

    # -----------------------------
    # TARIM
    # -----------------------------
    "TARKM": "Tarım",
    "GUBRF": "Tarım",

    # -----------------------------
    # İNŞAAT
    # -----------------------------
    "ENKAI": "İnşaat",
    "TKFEN": "İnşaat",

    # -----------------------------
    # TEKSTİL
    # -----------------------------
    "SOKM": "Perakende",
    "EBEBK": "Perakende",
    "MAVI": "Tekstil",
    "BLCYT": "Tekstil",
    "DERHL": "Tekstil",
    "DAGI": "Tekstil",
    "DESA": "Tekstil",
    "KORDS": "Tekstil",

    # -----------------------------
    # CAM
    # -----------------------------
    "SISE": "Cam",

    # -----------------------------
    # ÇİMENTO
    # -----------------------------
    "AKCNS": "Çimento",
    "CIMSA": "Çimento",
    "OYAKC": "Çimento",
    "BUCIM": "Çimento",
    "BSOKE": "Çimento",
    "CMBTN": "Çimento",
    "GOLTS": "Çimento",

    # -----------------------------
    # PETROL / RAFİNERİ
    # -----------------------------
    "TUPRS": "Petrol & Rafineri",
    "PETKM": "Petrol & Rafineri",

    # -----------------------------
    # ENERJİ / ELEKTRİK
    # -----------------------------
    "AKSEN": "Enerji",
    "AKFYE": "Enerji",
    "ENJSA": "Enerji",
    "GWIND": "Enerji",
    "GESAN": "Elektrik",
    "EUPWR": "Elektrik",
    "ASTOR": "Elektrik",

    # -----------------------------
    # SAVUNMA
    # -----------------------------
    "ASELS": "Savunma",
    "SDTTR": "Savunma",
    "ALTNY": "Savunma",
    "ONRYT": "Savunma",

    # -----------------------------
    # TEKNOLOJİ
    # -----------------------------
    "ATATP": "Teknoloji",
    "MIATK": "Teknoloji",
    "LOGO": "Teknoloji",
    "ARDYZ": "Teknoloji",
    "KFEIN": "Teknoloji",
    "INDES": "Teknoloji",
    "SMART": "Teknoloji",
    "HTTBT": "Teknoloji",

    # -----------------------------
    # OTOMOTİV
    # -----------------------------
    "FROTO": "Otomotiv",
    "TOASO": "Otomotiv",
    "TTRAK": "Otomotiv",
    "OTKAR": "Otomotiv",
    "DOAS": "Otomotiv",

    # -----------------------------
    # GIDA / İÇECEK
    # -----------------------------
    "BIMAS": "Perakende",
    "MGROS": "Perakende",
    "ULKER": "Gıda",
    "CCOLA": "Gıda",
    "AEFES": "Gıda",
    "TATGD": "Gıda",
    "PNSUT": "Gıda",
    "PETUN": "Gıda",

    # -----------------------------
    # ULAŞTIRMA
    # -----------------------------
    "THYAO": "Ulaştırma",
    "PGSUS": "Ulaştırma",
    "CLEBI": "Ulaştırma",
    "TAVHL": "Ulaştırma",

    # -----------------------------
    # SAĞLIK
    # -----------------------------
    "SELEC": "Sağlık",
    "MPARK": "Sağlık",
    "MEDTR": "Sağlık",
    "ECILC": "Sağlık",
    "DEVA": "Sağlık",

    # -----------------------------
    # GYO
    # -----------------------------
    "EKGYO": "GYO",
    "TRGYO": "GYO",
    "KLGYO": "GYO",
    "ISGYO": "GYO",
    "AKSGY": "GYO",
    "HLGYO": "GYO",
    "SAFGY": "GYO",
    "VKGYO": "GYO",
    "ALGYO": "GYO",
    "SRVGY": "GYO",
    "OZKGY": "GYO",
    "PEKGY": "GYO",
}

# Holding adı DB'de sektör olarak "ticaret", "sanayi" vb. gelirse
# isimden de yakalayabilmek için bilinen holding anahtarları.
HOLDING_TICKERS = {
    "KCHOL", "SAHOL", "DOHOL", "AGHOL", "ALARK", "GLYHO",
    "POLHO", "GSDHO", "IEYHO", "HDFGS",
}

def _sector_bucket(raw_sector, symbol=None):
    """Hisseyi anasayfa sektör kartlarından birine yerleştirir."""

    ticker = str(symbol or "").upper().strip()

    # 1) Kesin ticker eşleştirmesi.
    if ticker in TICKER_SECTOR_OVERRIDES:
        return TICKER_SECTOR_OVERRIDES[ticker]

    # 2) Holdingler her zaman Holding.
    if ticker in HOLDING_TICKERS:
        return "Holding"

    text = str(raw_sector or "").strip().lower()

    # 3) DB'deki doğrudan sektör adları.
    direct_map = {
        "holding": "Holding",
        "holding şirketi": "Holding",
        "holding şirketleri": "Holding",
        "holding/inşaat": "İnşaat",

        "inşaat": "İnşaat",
        "insaat": "İnşaat",
        "construction": "İnşaat",

        "madencilik": "Madencilik",
        "maden": "Madencilik",
        "mining": "Madencilik",
        "metals & mining": "Madencilik",

        "tarım": "Tarım",
        "tarim": "Tarım",
        "agriculture": "Tarım",
        "fertilizers": "Tarım",
        "gübre": "Tarım",
        "gubre": "Tarım",

        "demir çelik": "Sanayi",
        "demir-celik": "Sanayi",
        "demir çelik sanayi": "Sanayi",
        "çelik": "Sanayi",
        "celik": "Sanayi",
        "iron & steel": "Sanayi",
        "steel": "Sanayi",

        "çimento": "Çimento",
        "cimento": "Çimento",
        "cement": "Çimento",

        "enerji": "Enerji",
        "energy": "Enerji",

        "elektrik": "Elektrik",
        "utilities": "Elektrik",
        "utility": "Elektrik",

        "sağlık": "Sağlık",
        "saglik": "Sağlık",
        "healthcare": "Sağlık",
        "health": "Sağlık",

        "banka": "Bankacılık",
        "bank": "Bankacılık",
        "bankacılık": "Bankacılık",
        "bankacilik": "Bankacılık",

        "finans": "Finans",
        "financial services": "Finans",
        "fintech": "Finans",
        "insurance": "Finans",
        "sigorta": "Finans",
        "leasing": "Finans",
        "faktoring": "Finans",

        "teknoloji": "Teknoloji",
        "technology": "Teknoloji",
        "software": "Teknoloji",

        "otomotiv": "Otomotiv",
        "automotive": "Otomotiv",
        "auto": "Otomotiv",

        "gıda": "Gıda",
        "gida": "Gıda",
        "food": "Gıda",
        "beverage": "Gıda",
        "consumer defensive": "Gıda",

        "savunma": "Savunma",
        "defence": "Savunma",
        "defense": "Savunma",
        "aerospace & defense": "Savunma",

        "kimya": "Kimya",
        "chemical": "Kimya",
        "chemicals": "Kimya",

        "metal": "Demir-Çelik",
        "metals": "Demir-Çelik",

        "gyo": "GYO",
        "real estate": "GYO",
        "reit": "GYO",

        "petrokimya": "Petrol & Rafineri",
        "petrol": "Petrol & Rafineri",
        "oil": "Petrol & Rafineri",
        "refinery": "Petrol & Rafineri",
        "refining": "Petrol & Rafineri",

        "bankacılık": "Bankacılık",
        "sanayi": "Sanayi",
        "industrials": "Sanayi",
        "industrial": "Sanayi",
        "manufacturing": "Sanayi",
        "imalat": "Sanayi",
        "üretim": "Sanayi",
        "uretim": "Sanayi",

        "communication services": "Telekom",
        "telecommunications": "Telekom",
        "telekom": "Telekom",

        "perakende": "Perakende",
        "retail": "Perakende",

        "tekstil": "Tekstil",
        "textile": "Tekstil",
        "apparel": "Tekstil",

        "cam": "Cam",
        "glass": "Cam",

        # Eski "Ticaret" grubu kaldırıldı.
        # Ticaret bilgisi varsa şirketin gerçek faaliyet grubuna
        # veya en azından Tüketim/Perakende grubuna düşürülür.
        "ticaret": "Tüketim",
        "trade": "Tüketim",

        "ulaştırma": "Ulaştırma",
        "ulastirma": "Ulaştırma",
        "transport": "Ulaştırma",
        "airlines": "Ulaştırma",
        "havacılık": "Ulaştırma",

        "lojistik": "Lojistik",
        "logistics": "Lojistik",
        "transportation": "Lojistik",

        "turizm": "Turizm",
        "tourism": "Turizm",
        "hotel": "Turizm",
        "hospitality": "Turizm",

        "tüketim": "Tüketim",
        "tuketim": "Tüketim",
        "consumer": "Tüketim",
    }

    if text in direct_map:
        return direct_map[text]

    # 4) Tam eşleşme yoksa alias listesinde ara.
    for _, name, aliases in SECTOR_GROUPS:
        if text in aliases:
            return name

    # 5) Metin birden fazla kelime içeriyorsa anahtar kelime taraması.
    # Öncelik sırası özellikle holding / demir-çelik / tekstil /
    # madencilik / tarım gibi özel grupları korur.
    keyword_priority = [
        ("holding", "Holding"),
        ("demir çelik", "Sanayi"),
        ("demir-celik", "Sanayi"),
        ("iron & steel", "Sanayi"),
        ("steel", "Sanayi"),
        ("tekstil", "Tekstil"),
        ("textile", "Tekstil"),
        ("madencilik", "Madencilik"),
        ("mining", "Madencilik"),
        ("tarım", "Tarım"),
        ("tarim", "Tarım"),
        ("agriculture", "Tarım"),
        ("inşaat", "İnşaat"),
        ("insaat", "İnşaat"),
        ("construction", "İnşaat"),
        ("çimento", "Çimento"),
        ("cimento", "Çimento"),
        ("cement", "Çimento"),
        ("savunma", "Savunma"),
        ("defence", "Savunma"),
        ("defense", "Savunma"),
        ("otomotiv", "Otomotiv"),
        ("automotive", "Otomotiv"),
        ("sağlık", "Sağlık"),
        ("saglik", "Sağlık"),
        ("health", "Sağlık"),
        ("enerji", "Enerji"),
        ("energy", "Enerji"),
        ("petrol", "Petrol & Rafineri"),
        ("refinery", "Petrol & Rafineri"),
        ("gyo", "GYO"),
        ("real estate", "GYO"),
        ("teknoloji", "Teknoloji"),
        ("technology", "Teknoloji"),
        ("kimya", "Kimya"),
        ("chemical", "Kimya"),
        ("cam", "Cam"),
        ("glass", "Cam"),
        ("perakende", "Perakende"),
        ("retail", "Perakende"),
    ]

    for keyword, sector_name in keyword_priority:
        if keyword in text:
            return sector_name

    return "Diğer"


def _score_from_analysis(data):
    """Mevcut hisse analizinden 0-100 arası ana skor."""
    vals = []

    for key, weight in [
        ("Genel Skor", 0.60),
        ("Momentum 60G", 0.20),
        ("Trend", 0.20),
    ]:
        value = pd.to_numeric(
            data.get(key),
            errors="coerce",
        )

        if pd.notna(value):
            vals.append((float(value), weight))

    if not vals:
        return None

    total_weight = sum(w for _, w in vals)

    return sum(
        value * weight
        for value, weight in vals
    ) / total_weight


@st.cache_data(ttl=10 * 60, show_spinner=False)
def _load_sector_strength_v2():
    """
    Yeni sektör modeli.

    1) Hisse Gücü          %35
    2) Momentum             %25
    3) Trend                %20
    4) Sektör Genişliği     %10
    5) BIST relatif güç    %10

    Önemli:
    - Sadece SQLite snapshot kullanılır.
    - Yeni dış tarama yapılmaz.
    - Veri olmayan bileşenler ağırlıklarıyla birlikte normalize edilir.
    - Sektör skoru, o sektördeki hisselerin MEDYAN + ORTALAMA
      kombinasyonundan oluşturulur; birkaç uç değerin etkisi azaltılır.
    """
    db_path = _find_database()

    if db_path is None:
        return pd.DataFrame()

    try:
        with sqlite3.connect(
            str(db_path),
            timeout=5,
        ) as conn:

            raw = pd.read_sql_query(
                """
                SELECT
                    symbol,
                    analysis_json,
                    analysis_time
                FROM dynamic_portfolio_cache
                WHERE analysis_json IS NOT NULL
                """,
                conn,
            )

        if raw.empty:
            return pd.DataFrame()

        rows = []

        for _, record in raw.iterrows():
            try:
                data = json.loads(
                    record["analysis_json"]
                )
            except Exception:
                continue

            sector = _sector_bucket(
                data.get("Sektör")
                or data.get("Sektor")
                or data.get("sector"),
                record["symbol"],
            )

            if sector == "Diğer":
                continue

            general = pd.to_numeric(
                data.get("Genel Skor"),
                errors="coerce",
            )

            momentum = pd.to_numeric(
                data.get("Momentum 60G"),
                errors="coerce",
            )

            trend = pd.to_numeric(
                data.get("Trend"),
                errors="coerce",
            )

            price = pd.to_numeric(
                data.get("price"),
                errors="coerce",
            )

            rows.append(
                {
                    "symbol": str(record["symbol"]),
                    "sector": sector,
                    "general": general,
                    "momentum": momentum,
                    "trend": trend,
                    "price": price,
                }
            )

        df = pd.DataFrame(rows)

        if df.empty:
            return pd.DataFrame()

        # --------------------------------------------------
        # SEKTÖR İÇİ HİSSE GÜCÜ
        # --------------------------------------------------
        df["stock_strength"] = df.apply(
            lambda r: _score_from_analysis(
                {
                    "Genel Skor": r["general"],
                    "Momentum 60G": r["momentum"],
                    "Trend": r["trend"],
                }
            ),
            axis=1,
        )

        # --------------------------------------------------
        # SEKTÖR GENİŞLİĞİ
        #
        # Güçlü hisse oranı + pozitif momentum oranı.
        # Böylece yalnızca 1-2 güçlü hissenin sektörü
        # olduğundan güçlü göstermesi zorlaşır.
        # --------------------------------------------------
        grouped = []

        for sector, g in df.groupby("sector"):
            g = g.copy()

            valid_stock = g["stock_strength"].dropna()

            if valid_stock.empty:
                continue

            mean_stock = valid_stock.mean()
            median_stock = valid_stock.median()

            # Ortalama + medyan: uç değerlerin etkisini azaltır.
            stock_component = (
                mean_stock * 0.60
                + median_stock * 0.40
            )

            momentum_valid = g["momentum"].dropna()

            if momentum_valid.empty:
                momentum_component = None
            else:
                momentum_component = float(
                    momentum_valid.mean()
                )

            trend_valid = g["trend"].dropna()

            if trend_valid.empty:
                trend_component = None
            else:
                trend_component = float(
                    trend_valid.mean()
                )

            strong_ratio = float(
                (
                    valid_stock >= 60
                ).mean() * 100
            )

            positive_momentum_ratio = (
                float(
                    (
                        momentum_valid >= 50
                    ).mean() * 100
                )
                if not momentum_valid.empty
                else None
            )

            if positive_momentum_ratio is None:
                breadth = strong_ratio
            else:
                breadth = (
                    strong_ratio * 0.60
                    + positive_momentum_ratio * 0.40
                )

            grouped.append(
                {
                    "sector": sector,
                    "stock_component": stock_component,
                    "momentum_component": momentum_component,
                    "trend_component": trend_component,
                    "breadth": breadth,
                    "stock_count": int(
                        g["symbol"].nunique()
                    ),
                }
            )

        result = pd.DataFrame(grouped)

        if result.empty:
            return result

        # --------------------------------------------------
        # BIST RELATİF GÜÇ
        #
        # Burada fiyat serisi yoksa uydurma relatif getiri
        # üretmiyoruz. Bunun yerine mevcut hisse skorunun
        # BIST genel medyanına göre farkını normalize ediyoruz.
        #
        # Bu "relatif skor"dur; fiyat getirisi değildir.
        # --------------------------------------------------
        market_reference = float(
            df["stock_strength"]
            .dropna()
            .median()
        )

        result["relative_component"] = (
            50
            + (
                result["stock_component"]
                - market_reference
            )
            * 0.80
        ).clip(0, 100)

        # --------------------------------------------------
        # AĞIRLIKLI SEKTÖR SKORU
        # --------------------------------------------------
        weights = {
            "stock_component": 0.35,
            "momentum_component": 0.25,
            "trend_component": 0.20,
            "breadth": 0.10,
            "relative_component": 0.10,
        }

        components = []

        for column, weight in weights.items():
            if result[column].notna().any():
                components.append(
                    (column, weight)
                )

        total_weight = sum(
            weight
            for _, weight in components
        )

        result["strength"] = 0.0

        for column, weight in components:
            result["strength"] += (
                result[column]
                .fillna(result[column].median())
                * weight
                / total_weight
            )

        result["strength"] = (
            result["strength"]
            .clip(0, 100)
            .round(1)
        )

        result["market_reference"] = round(
            market_reference,
            1,
        )

        return result.sort_values(
            "strength",
            ascending=False,
        ).reset_index(drop=True)

    except Exception:
        return pd.DataFrame()


sector_strength_df = _load_sector_strength_v2()

sector_lookup = {}

if not sector_strength_df.empty:
    for _, row in sector_strength_df.iterrows():
        sector_lookup[
            str(row["sector"])
        ] = row.to_dict()


def _sector_state(score):
    if score >= 80:
        return "🟢 ÇOK GÜÇLÜ"
    if score >= 65:
        return "🟢 GÜÇLÜ"
    if score >= 50:
        return "🟡 NÖTR"
    if score >= 35:
        return "🟠 ZAYIF"

    return "🔴 ÇOK ZAYIF"


# ----------------------------------------------------------
# YATAY SEKTÖR KARTLARI
# ----------------------------------------------------------

for start_idx in range(
    0,
    len(SECTOR_GROUPS),
    5,
):
    row_sectors = SECTOR_GROUPS[
        start_idx:start_idx + 5
    ]

    cols = st.columns(
        len(row_sectors),
        gap="small",
    )

    for col, (
        icon,
        name,
        _aliases,
    ) in zip(
        cols,
        row_sectors,
    ):
        with col:
            data = sector_lookup.get(name)

            with st.container(border=True):
                st.markdown(
                    f"### {icon} {name}"
                )

                if data:
                    score = float(
                        data["strength"]
                    )

                    count = int(
                        data["stock_count"]
                    )

                    state = _sector_state(
                        score
                    )

                    st.metric(
                        "Sektör Gücü",
                        f"{score:.1f}/100",
                    )

                    st.caption(
                        f"{state} · {count} hisse"
                    )

                    breadth = float(
                        data["breadth"]
                    )

                    st.progress(
                        min(
                            max(
                                score / 100,
                                0.0,
                            ),
                            1.0,
                        )
                    )

                    st.caption(
                        f"Genişlik: %{breadth:.0f}"
                    )

                    relative = float(
                        data[
                            "relative_component"
                        ]
                    )

                    if relative >= 55:
                        relative_text = "BIST'e göre pozitif"
                    elif relative <= 45:
                        relative_text = "BIST'e göre negatif"
                    else:
                        relative_text = "BIST'e yakın"

                    st.caption(
                        relative_text
                    )

                else:
                    st.metric(
                        "Sektör Gücü",
                        "—",
                    )

                    st.caption(
                        "Snapshot verisi yok"
                    )

st.caption(
    "Model: %35 hisse gücü + %25 momentum + %20 trend + "
    "%10 sektör genişliği + %10 relatif güç. "
    "Sektör sınıflandırması ticker öncelikli çalışır; "
    "Holding ve özel sektör eşleştirmeleri ham DB sektör bilgisini ezer. "
    "Sektör skoru mevcut SQLite snapshotından hesaplanır; "
    "anasayfa yeni dış tarama başlatmaz."
)


# ==========================================================
# 3 — SON 24 SAATİN ÖNEMLİ HABERLERİ
# ==========================================================

# 3 — SON 24 SAATİN ÖNEMLİ HABERLERİ
# ==========================================================

# 3 — SON 24 SAATİN ÖNEMLİ HABERLERİ
# ==========================================================

# ==========================================================

NEWS_FEEDS = [
    {
        "category": "🇹🇷 Yurt İçi Ekonomi",
        "name": "TRT Haber Ekonomi",
        "url": "https://www.trthaber.com/ekonomi_articles.rss",
    },
    {
        "category": "🇹🇷 Yurt İçi Ekonomi",
        "name": "Anadolu Ajansı Ekonomi",
        "url": "https://www.aa.com.tr/tr/rss/default?cat=ekonomi",
    },
    {
        "category": "📈 BIST / Şirketler",
        "name": "Anadolu Ajansı Finans",
        "url": "https://www.aa.com.tr/tr/rss/default?cat=finans",
    },
    {
        "category": "🌍 Dünya / Makro",
        "name": "TRT Haber Dünya",
        "url": "https://www.trthaber.com/dunya_articles.rss",
    },
    {
        "category": "⚡ Enerji / Jeopolitik",
        "name": "TRT Haber Dünya",
        "url": "https://www.trthaber.com/dunya_articles.rss",
    },
]

NEWS_SOURCE_PRIORITY = {
    "Reuters": 10,
    "Reuters Türkiye": 10,
    "Bloomberg HT": 9,
    "Bloomberg": 9,
    "Anadolu Ajansı": 8,
    "AA": 8,
    "Dünya": 8,
    "CNBC-e": 7,
    "Investing.com": 6,
    "TRT Haber": 5,
}

IMPORTANT_TERMS = {
    "tcmb": 5,
    "faiz": 5,
    "enflasyon": 5,
    "fed": 5,
    "ecb": 4,
    "merkez bank": 5,
    "bist": 4,
    "borsa": 4,
    "kap": 4,
    "bilanço": 4,
    "bilanco": 4,
    "dolar": 3,
    "euro": 3,
    "kur": 3,
    "petrol": 4,
    "brent": 4,
    "altın": 3,
    "doğalgaz": 4,
    "enerji": 4,
    "rezerv": 4,
    "cari açık": 4,
    "büyüme": 4,
    "işsizlik": 3,
    "sanayi üretimi": 4,
    "vergi": 3,
    "jeopolitik": 4,
    "savaş": 4,
    "abd": 2,
    "çin": 2,
    "rusya": 2,
}


def _clean_news_text(value):
    value = html.unescape(str(value or ""))
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _parse_news_date(value):
    if not value:
        return pd.NaT
    try:
        dt = parsedate_to_datetime(value)
        if dt.tzinfo:
            return dt.astimezone().replace(tzinfo=None)
        return dt
    except Exception:
        return pd.to_datetime(value, errors="coerce")


@st.cache_data(ttl=10 * 60, show_spinner=False)
def _fetch_news_feed(feed_url):
    """
    Doğrudan RSS kaynaklarından haberleri alır.
    Bir kaynak erişilemezse hata yutulur; diğer kaynaklar
    çalışmaya devam eder.
    """
    try:
        response = requests.get(
            feed_url,
            timeout=10,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 "
                    "BIST-AI-PRO/1.0"
                )
            },
        )
        response.raise_for_status()

        root = ET.fromstring(response.content)
        rows = []

        for item in root.findall(".//item"):
            title = _clean_news_text(
                item.findtext("title")
            )
            link = (
                item.findtext("link")
                or ""
            ).strip()

            description = _clean_news_text(
                item.findtext("description")
            )

            pub_date = (
                item.findtext("pubDate")
                or item.findtext("date")
                or ""
            )

            if not title or not link:
                continue

            rows.append(
                {
                    "title": title,
                    "link": link,
                    "description": description,
                    "date": _parse_news_date(pub_date),
                }
            )

        return rows

    except Exception:
        return []


def _news_source(title):
    """
    Google News başlıkları çoğunlukla:
    'Haber başlığı - Kaynak'
    biçimindedir.
    """
    parts = [
        p.strip()
        for p in str(title).rsplit(" - ", 1)
    ]

    if len(parts) == 2 and len(parts[1]) <= 80:
        return parts[1]

    return "Haber Akışı"


def _importance(row):
    text = (
        f"{row['title']} "
        f"{row.get('description', '')}"
    ).lower()

    score = 0

    for term, weight in IMPORTANT_TERMS.items():
        if term in text:
            score += weight

    source = str(
        row.get("source", "")
    ).lower()

    for name, weight in NEWS_SOURCE_PRIORITY.items():
        if name.lower() in source:
            score += weight
            break

    # Güncellik: bugün/yeni haberleri belirgin biçimde öne al.
    dt = row.get("date")

    if pd.notna(dt):
        age_hours = max(
            0,
            (
                pd.Timestamp.now()
                - pd.Timestamp(dt)
            ).total_seconds()
            / 3600,
        )

        if age_hours <= 6:
            score += 8
        elif age_hours <= 24:
            score += 5
        elif age_hours <= 48:
            score += 2

    return score


@st.cache_data(ttl=10 * 60, show_spinner=False)
def get_daily_news():
    rows = []

    for feed in NEWS_FEEDS:
        for item in _fetch_news_feed(feed["url"]):
            item = dict(item)
            item["category"] = feed["category"]
            item["source"] = feed["name"]
            item["importance"] = _importance(item)
            rows.append(item)

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)

    # ======================================================
    # SADECE SON 24 SAAT
    # ======================================================
    # Haber eskiyse anasayfada gösterilmez.
    # Tarihi okunamayan haberler de güvenli tarafta kalmak
    # için dışarıda bırakılır.
    now = pd.Timestamp.now()

    # Tüm tarihleri timezone'suz yerel zamana normalize et.
    normalized_dates = pd.to_datetime(
        df["date"],
        errors="coerce",
        utc=True,
    ).dt.tz_convert(None)

    df["date"] = normalized_dates

    df = df[
        df["date"].notna()
        & (
            (now - df["date"])
            <= pd.Timedelta(hours=24)
        )
        & (
            (now - df["date"])
            >= pd.Timedelta(seconds=0)
        )
    ].copy()

    if df.empty:
        return pd.DataFrame()

    # Aynı haber farklı aramalarda geldiyse tekilleştir.
    df["title_key"] = (
        df["title"]
        .str.lower()
        .str.replace(
            r"[^a-z0-9çğıöşü\s]",
            "",
            regex=True,
        )
        .str.replace(
            r"\s+",
            " ",
            regex=True,
        )
        .str.strip()
    )

    df = (
        df.sort_values(
            ["importance", "date"],
            ascending=[False, False],
            na_position="last",
        )
        .drop_duplicates(
            "title_key",
            keep="first",
        )
        .reset_index(drop=True)
    )

    return df


def _show_news_card(row):
    title = html.escape(
        str(row["title"])
    )
    source = html.escape(
        str(row["source"])
    )
    category = html.escape(
        str(row["category"])
    )
    link = html.escape(
        str(row["link"])
    )

    summary = str(
        row.get("description") or ""
    )

    if len(summary) > 240:
        summary = summary[:237] + "..."

    summary = html.escape(summary)

    dt = row.get("date")

    if pd.notna(dt):
        date_text = pd.Timestamp(
            dt
        ).strftime(
            "%d.%m.%Y %H:%M"
        )
    else:
        date_text = "Saat bilgisi yok"

    st.markdown(
        f"""
        <div class="news-card">
            <div class="news-meta">
                {category} · {source} · {date_text}
            </div>
            <div class="news-title">
                <a href="{link}"
                   target="_blank"
                   rel="noopener noreferrer">
                    {title}
                </a>
            </div>
            {
                f'<div class="news-summary">{summary}</div>'
                if summary else ""
            }
        </div>
        """,
        unsafe_allow_html=True,
    )


st.divider()

st.header("📰 3. Son 24 Saatin Önemli Haberleri")

st.caption(
    "BIST ve yatırım kararlarını etkileyebilecek "
    "makro, yurt içi ekonomi, şirket, enerji ve "
    "jeopolitik gelişmeler önem sırasına göre seçilir."
)

# Haber kartlarının görünümü.
st.markdown(
    """
    <style>

    .news-card {
        border: 1px solid rgba(128,128,128,.22);
        border-radius: 12px;
        padding: 14px 16px;
        margin-bottom: 12px;
        min-height: 132px;
        background: rgba(128,128,128,.035);
    }

    .news-meta {
        font-size: .74rem;
        opacity: .65;
        margin-bottom: 7px;
    }

    .news-title {
        font-size: .98rem;
        font-weight: 650;
        line-height: 1.35;
    }

    .news-title a {
        color: inherit;
        text-decoration: none;
    }

    .news-title a:hover {
        text-decoration: underline;
    }

    .news-summary {
        font-size: .82rem;
        opacity: .76;
        line-height: 1.4;
        margin-top: 7px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

news_df = get_daily_news()

if news_df.empty:
    st.warning(
        "Son 24 saat içinde okunabilen haber bulunamadı. "
        "Haber kaynakları 10 dakikada bir yeniden kontrol edilir."
    )
else:
    # Her yenilemede güncel akış tekrar kontrol edilir.
    top_news = news_df.head(12)

    news_cols = st.columns(3)

    for i, (_, row) in enumerate(
        top_news.iterrows()
    ):
        with news_cols[i % 3]:
            _show_news_card(row)

    st.caption(
        f"Son 24 saat taraması: "
        f"{pd.Timestamp.now().strftime('%d.%m.%Y %H:%M')} "
        f"· {len(news_df)} haber değerlendirildi "
        f"· En önemli 12 haber gösteriliyor "
        f"· Kaynaklar: TRT Haber / Anadolu Ajansı."
    )

    if st.button(
        "🔄 Haberleri şimdi güncelle",
        key="update_home_news",
    ):
        _fetch_news_feed.clear()
        get_daily_news.clear()
        st.rerun()


# ==========================================================
# GÜNLÜK KARAR MANTIĞI
# ==========================================================

# ==========================================================

st.divider()

st.header("🧭 Bugünkü İşlem Disiplini")

col1, col2, col3, col4 = st.columns(4)


with col1:

    st.info(
        """
        **1️⃣ PİYASA**

        Piyasa riskliyse
        agresif işlem yok.
        """
    )


with col2:

    st.info(
        """
        **2️⃣ TARAMA**

        Güçlü adayları
        seç.
        """
    )


with col3:

    st.info(
        """
        **3️⃣ TEYİT**

        Teknik göstergeleri
        birlikte kontrol et.
        """
    )


with col4:

    st.info(
        """
        **4️⃣ KARAR**

        AL / ARTIR / TUT /
        AZALT / SAT
        """
    )


# ==========================================================
# SON KURAL
# ==========================================================

st.divider()

st.success(
    "🎯 Kural: Önce aday bulunur → sonra doğrulanır → "
    "teyit gelirse işlem yapılır."
)


# ==========================================================
# FOOTER
# ==========================================================

st.divider()

st.caption(
    "© 2026 BIST AI PRO | Disiplinli Yapay Zeka Destekli BIST Karar Sistemi"
)