# ============================================================
# BIST AI PRO
# 07_Bloomberg_Haberleri.py
#
# BLOOMBERG HT HABER MERKEZİ
#
# GÖRÜNÜMLER:
#   📰 Tüm Haberler
#   🏢 Şirket Haberleri
#   📈 Hisse Bazlı
#
# ÖZELLİKLER:
#   - Bloomberg HT haberlerini çeker
#   - SQLite'a kalıcı kaydeder
#   - Eski haberleri korur
#   - Duplicate haberleri engeller
#   - Şirket haberlerini otomatik ayırır
#   - BIST hisseleriyle ilişkilendirir
#   - Pozitif / Nötr / Negatif analiz yapar
#   - Tarih filtresi
#   - Özel tarih aralığı
#
# ÖNEMLİ:
#   Bu modül Dinamik Portföy skorlarını DEĞİŞTİRMEZ.
# ============================================================

import streamlit as st
import sqlite3
import requests
import re
import hashlib
import json

from datetime import datetime, timedelta, date
from urllib.parse import urljoin

import pandas as pd
from bs4 import BeautifulSoup


# ============================================================
# AYARLAR
# ============================================================

st.set_page_config(
    page_title="Bloomberg HT Haberleri",
    page_icon="📰",
    layout="wide",
)

BASE_URL = "https://www.bloomberght.com"
NEWS_URL = "https://www.bloomberght.com/tumhaberler"

DB_PATH = "borsa.db"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/151.0 Safari/537.36"
    ),
    "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
}

REQUEST_TIMEOUT = 15


# ============================================================
# BIST HİSSE / ŞİRKET EŞLEŞTİRME
# ============================================================

STOCK_MAP = {

    # --------------------------------------------------------
    # ENERJİ
    # --------------------------------------------------------

    "TUPRS": [
        "tüpraş",
        "tupras",
        "rafineri",
        "rafineri marjı",
        "motorin",
        "benzin",
    ],

    "PETKM": [
        "petkim",
        "petrokimya",
        "petrokimya tesisi",
        "nafta",
    ],

    "AKSEN": [
        "aksa enerji",
        "aksa enerji üretim",
        "elektrik üretimi",
        "enerji santrali",
    ],

    "AYGAZ": [
        "aygaz",
        "lpg",
        "likit petrol gazı",
    ],

    "ENJSA": [
        "enerjisa",
        "enerjisa enerji",
    ],

    "ODAS": [
        "odaş",
        "odas",
    ],

    # --------------------------------------------------------
    # SAVUNMA / TEKNOLOJİ
    # --------------------------------------------------------

    "ASELS": [
        "aselsan",
        "savunma sanayii",
        "savunma sanayi",
        "savunma ihracatı",
        "radar",
        "füze",
    ],

    "SDTTR": [
        "sdt uzay",
        "sdttr",
        "uzay teknolojileri",
    ],

    "FROTO": [
        "ford otosan",
        "ford",
        "otomotiv ihracatı",
    ],

    "TOASO": [
        "tofaş",
        "tofas",
    ],

    "OTKAR": [
        "otokar",
    ],

    "TTRAK": [
        "türk traktör",
        "turk traktör",
    ],

    "ARCLK": [
        "arçelik",
        "arcelik",
    ],

    # --------------------------------------------------------
    # PERAKENDE
    # --------------------------------------------------------

    "BIMAS": [
        "bim",
        "bim birleşik mağazalar",
        "bim mağaza",
    ],

    "MGROS": [
        "migros",
    ],

    "SOKM": [
        "şok market",
        "sok market",
    ],

    "ULKER": [
        "ülker",
        "ulker",
    ],

    # --------------------------------------------------------
    # HAVACILIK / ULAŞTIRMA
    # --------------------------------------------------------

    "THYAO": [
        "türk hava yolları",
        "thy",
        "turkish airlines",
    ],

    "PGSUS": [
        "pegasus",
    ],

    "TAVHL": [
        "tav havalimanları",
        "tav havalimanı",
    ],

    "RYSAS": [
        "reysaş",
        "reysas",
        "lojistik",
    ],

    # --------------------------------------------------------
    # BANKALAR
    # --------------------------------------------------------

    "AKBNK": [
        "akbank",
    ],

    "GARAN": [
        "garanti bbva",
        "garanti bankası",
    ],

    "YKBNK": [
        "yapı kredi",
        "yapı ve kredi bankası",
    ],

    "ISCTR": [
        "iş bankası",
        "türkiye iş bankası",
    ],

    "HALKB": [
        "halkbank",
        "halk bankası",
    ],

    "VAKBN": [
        "vakıfbank",
    ],

    # --------------------------------------------------------
    # HOLDİNG
    # --------------------------------------------------------

    "KCHOL": [
        "koç holding",
    ],

    "SAHOL": [
        "sabancı holding",
        "hacı ömer sabancı holding",
    ],

    "SISE": [
        "şişecam",
        "sisecam",
    ],

    # --------------------------------------------------------
    # İNŞAAT / SANAYİ
    # --------------------------------------------------------

    "TKFEN": [
        "tekfen",
        "tekfen holding",
    ],

    "ENKAI": [
        "enka",
        "enka inşaat",
    ],

    "CIMSA": [
        "çimsa",
        "cimsa",
    ],

    "OYAKC": [
        "oyak çimento",
        "oyakc",
    ],

    # --------------------------------------------------------
    # TELEKOM
    # --------------------------------------------------------

    "TCELL": [
        "turkcell",
    ],

    "TTKOM": [
        "türk telekom",
        "turk telekom",
    ],

    # --------------------------------------------------------
    # GIDA
    # --------------------------------------------------------

    "CCOLA": [
        "coca cola içecek",
        "coca-cola içecek",
        "coca cola",
    ],

    "AEFES": [
        "anadolu efes",
        "efes",
    ],

    # --------------------------------------------------------
    # TEKNOLOJİ
    # --------------------------------------------------------

    "LOGO": [
        "logo yazılım",
        "logo yazilim",
    ],

    "MIATK": [
        "mia teknoloji",
    ],

    "ATATP": [
        "atp yazılım",
        "atp teknoloji",
    ],

    "FORTE": [
        "forte teknoloji",
        "forte",
    ],
}


# ============================================================
# KATEGORİLER
# ============================================================

CATEGORY_KEYWORDS = {

    "Şirket": [
        "şirket",
        "bilanço",
        "net kâr",
        "net kar",
        "gelir",
        "ciro",
        "satış",
        "sipariş",
        "yatırım",
        "sermaye",
        "temettü",
        "bedelli",
        "bedelsiz",
        "ihale",
        "sözleşme",
        "anlaşma",
        "fabrika",
        "tesis",
        "üretim",
        "ihracat",
        "finansal sonuç",
        "mali sonuç",
        "kâr",
        "kar",
    ],

    "Enerji": [
        "petrol",
        "brent",
        "doğalgaz",
        "doğal gaz",
        "elektrik",
        "enerji",
        "rafineri",
        "lpg",
    ],

    "Faiz / TCMB": [
        "tcmb",
        "merkez bankası",
        "faiz",
        "politika faizi",
        "mevduat",
        "repo",
    ],

    "Döviz": [
        "dolar",
        "euro",
        "sterlin",
        "döviz",
        "kur",
        "tl",
        "türk lirası",
    ],

    "Borsa": [
        "borsa",
        "bist",
        "bist 100",
        "hisse",
        "endeks",
        "pay piyasası",
    ],

    "Enflasyon": [
        "enflasyon",
        "tüfe",
        "üfe",
        "fiyat artışı",
    ],

    "Jeopolitik": [
        "savaş",
        "gerilim",
        "iran",
        "israil",
        "abd",
        "rusya",
        "ukrayna",
        "hürmüz",
        "orta doğu",
    ],

    "Küresel Piyasalar": [
        "abd borsaları",
        "nasdaq",
        "s&p 500",
        "dow jones",
        "avrupa borsaları",
        "asya borsaları",
        "fed",
        "ecb",
    ],
}


# ============================================================
# SENTIMENT
# ============================================================

POSITIVE_WORDS = [
    "arttı",
    "artış",
    "yükseldi",
    "yükseliş",
    "rekor",
    "güçlü",
    "beklentiyi aştı",
    "beklentilerin üzerinde",
    "kâr arttı",
    "kar arttı",
    "büyüdü",
    "büyüme",
    "pozitif",
    "olumlu",
    "kazandı",
    "yeni sipariş",
    "yatırım",
    "anlaşma",
    "ihracat arttı",
    "ihracat rekoru",
]

NEGATIVE_WORDS = [
    "azaldı",
    "düştü",
    "düşüş",
    "geriledi",
    "zarar",
    "kayıp",
    "beklentinin altında",
    "beklentilerin altında",
    "olumsuz",
    "borç",
    "risk",
    "kriz",
    "savaş",
    "yaptırım",
    "iptal",
    "işten çıkarma",
]


# ============================================================
# DB
# ============================================================

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


def init_db():

    conn = get_connection()

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS bloomberg_news (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            news_hash TEXT UNIQUE,
            title TEXT NOT NULL,
            url TEXT,
            published_at TEXT,
            category TEXT,
            summary TEXT,
            related_stocks TEXT,
            impact TEXT,
            impact_score INTEGER,
            ai_comment TEXT,
            created_at TEXT
        )
        """
    )

    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_bloomberg_published
        ON bloomberg_news(published_at)
        """
    )

    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_bloomberg_category
        ON bloomberg_news(category)
        """
    )

    conn.commit()
    conn.close()


# ============================================================
# METİN TEMİZLE
# ============================================================

def clean_text(text):

    if text is None:
        return ""

    text = re.sub(r"\s+", " ", str(text))

    return text.strip()


# ============================================================
# HASH
# ============================================================

def make_hash(title, url):

    raw = f"{title}|{url}".lower().strip()

    return hashlib.sha256(
        raw.encode("utf-8")
    ).hexdigest()


# ============================================================
# KATEGORİ
# ============================================================

def detect_category(title, summary):

    text = f"{title} {summary}".lower()

    scores = {}

    for category, keywords in CATEGORY_KEYWORDS.items():

        score = 0

        for keyword in keywords:

            if keyword.lower() in text:
                score += 1

        scores[category] = score

    best_category = max(
        scores,
        key=scores.get
    )

    if scores[best_category] == 0:
        return "Genel"

    return best_category


# ============================================================
# HİSSE EŞLEŞTİRME
# ============================================================

def detect_stocks(title, summary):

    text = f"{title} {summary}".lower()

    matched = []

    for symbol, keywords in STOCK_MAP.items():

        for keyword in keywords:

            if keyword.lower() in text:

                matched.append(symbol)
                break

    return sorted(set(matched))


# ============================================================
# ŞİRKET HABERİ Mİ?
# ============================================================

def is_company_news(
    title,
    summary,
    stocks,
    category,
):

    text = f"{title} {summary}".lower()

    # Doğrudan hisse eşleşmesi varsa şirket haberidir.
    if stocks:
        return True

    # Şirket kategorisiyse şirket haberidir.
    if category == "Şirket":
        return True

    # Şirket haberlerinde sık kullanılan kelimeler
    company_words = [
        "bilanço",
        "net kâr",
        "net kar",
        "finansal sonuç",
        "mali sonuç",
        "şirket",
        "ortaklık",
        "sermaye artırımı",
        "sermaye artırımı",
        "temettü",
        "bedelli",
        "bedelsiz",
        "ihale",
        "sözleşme",
        "anlaşma",
        "sipariş",
        "yatırım kararı",
        "yatırım planı",
        "fabrika",
        "tesis",
        "üretim tesisi",
        "ihracat",
        "satın alma",
        "birleşme",
        "devralma",
        "genel kurul",
        "yönetim kurulu",
    ]

    for word in company_words:

        if word in text:
            return True

    return False


# ============================================================
# SENTIMENT
# ============================================================

def detect_sentiment(title, summary):

    text = f"{title} {summary}".lower()

    positive = 0
    negative = 0

    for word in POSITIVE_WORDS:

        if word.lower() in text:
            positive += 1

    for word in NEGATIVE_WORDS:

        if word.lower() in text:
            negative += 1

    score = positive - negative

    if score >= 2:

        return "🟢 POZİTİF", 2

    if score <= -2:

        return "🔴 NEGATİF", -2

    return "🟡 NÖTR", 0


# ============================================================
# AI YORUMU
# ============================================================

def make_comment(
    title,
    summary,
    stocks,
    category,
    impact_score,
):

    if stocks:

        stock_text = ", ".join(stocks)

        if impact_score > 0:

            return (
                f"{stock_text} açısından haber akışı olumlu "
                f"görünüyor. Haber şirket performansı veya "
                f"faaliyetleri açısından destekleyici nitelikte. "
                f"Tek başına alım sinyali olarak değerlendirilmemelidir."
            )

        if impact_score < 0:

            return (
                f"{stock_text} açısından haber akışı olumsuz "
                f"görünüyor. Gelişmenin kalıcı etkisi için şirket "
                f"verileri ve fiyat hareketi ayrıca izlenmelidir."
            )

        return (
            f"{stock_text} ile ilişkili şirket haberi. "
            f"Mevcut içerik belirgin bir pozitif veya negatif "
            f"yön göstermiyor."
        )

    if category == "Enerji":

        return (
            "Enerji piyasalarını ilgilendiren gelişme. "
            "Enerji üreticileri, rafineriler ve enerji maliyeti "
            "yüksek şirketlerde farklı yönlerde etkiler oluşabilir."
        )

    if category == "Faiz / TCMB":

        return (
            "Faiz ve para politikası kaynaklı gelişme. "
            "Bankalar, holdingler ve finansman maliyeti yüksek "
            "şirketler açısından takip edilmesi gerekir."
        )

    if category == "Döviz":

        return (
            "Döviz kuru açısından önemli gelişme. "
            "İhracatçı ve döviz geliri bulunan şirketlerle "
            "döviz borcu bulunan şirketler farklı etkilenebilir."
        )

    if category == "Jeopolitik":

        return (
            "Jeopolitik gelişme. Enerji, savunma, ulaştırma "
            "ve dış ticaret bağlantılı şirketlerde dolaylı "
            "etki oluşturabilir."
        )

    return (
        "Haber BIST şirketiyle doğrudan eşleştirilemedi. "
        "Sektörel ve piyasa etkisi ayrıca değerlendirilmelidir."
    )


# ============================================================
# GERÇEK HABER TARİHİNİ BUL
# ============================================================

def extract_article_date(url):

    try:

        response = requests.get(
            url,
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT,
        )

        response.raise_for_status()

        soup = BeautifulSoup(
            response.text,
            "html.parser",
        )

        # ----------------------------------------------------
        # 1. OpenGraph
        # ----------------------------------------------------

        meta = soup.find(
            "meta",
            attrs={
                "property": "article:published_time"
            }
        )

        if meta and meta.get("content"):

            value = meta.get("content").strip()

            parsed = pd.to_datetime(
                value,
                errors="coerce",
            )

            if not pd.isna(parsed):

                return parsed.strftime(
                    "%Y-%m-%d %H:%M:%S"
                )

        # ----------------------------------------------------
        # 2. datePublished
        # ----------------------------------------------------

        for script in soup.find_all(
            "script",
            type="application/ld+json",
        ):

            try:

                data = json.loads(
                    script.get_text(
                        strip=True
                    )
                )

                items = (
                    data
                    if isinstance(data, list)
                    else [data]
                )

                for item in items:

                    if not isinstance(item, dict):
                        continue

                    value = item.get(
                        "datePublished"
                    )

                    if value:

                        parsed = pd.to_datetime(
                            value,
                            errors="coerce",
                        )

                        if not pd.isna(parsed):

                            return parsed.strftime(
                                "%Y-%m-%d %H:%M:%S"
                            )

            except Exception:
                pass

        # ----------------------------------------------------
        # 3. time tag
        # ----------------------------------------------------

        time_tag = soup.find("time")

        if time_tag:

            value = (
                time_tag.get("datetime")
                or time_tag.get_text(
                    " ",
                    strip=True
                )
            )

            parsed = pd.to_datetime(
                value,
                errors="coerce",
                dayfirst=True,
            )

            if not pd.isna(parsed):

                return parsed.strftime(
                    "%Y-%m-%d %H:%M:%S"
                )

    except Exception:
        pass

    return None


# ============================================================
# BLOOMBERG HABERLERİNİ ÇEK
# ============================================================

def fetch_news():

    try:

        response = requests.get(
            NEWS_URL,
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT,
        )

        response.raise_for_status()

    except Exception as e:

        return [], f"Bloomberg HT bağlantı hatası: {e}"

    soup = BeautifulSoup(
        response.text,
        "html.parser",
    )

    articles = []

    bad_words = [
        "giriş yap",
        "üye ol",
        "canlı yayın",
        "programlar",
        "yayın akışı",
        "frekans",
        "hava durumu",
    ]

    for a in soup.find_all(
        "a",
        href=True,
    ):

        title = clean_text(
            a.get_text(
                " ",
                strip=True
            )
        )

        href = a.get("href")

        if not title or not href:
            continue

        url = urljoin(
            BASE_URL,
            href,
        )

        if "bloomberght.com" not in url:
            continue

        if len(title) < 25:
            continue

        if any(
            bad.lower() in title.lower()
            for bad in bad_words
        ):
            continue

        articles.append(
            {
                "title": title,
                "url": url,
            }
        )

    # --------------------------------------------------------
    # Duplicate temizliği
    # --------------------------------------------------------

    unique = {}

    for article in articles:

        key = (
            article["title"].lower().strip(),
            article["url"].lower().strip(),
        )

        unique[key] = article

    articles = list(
        unique.values()
    )

    # --------------------------------------------------------
    # GERÇEK YAYIN TARİHİ
    # --------------------------------------------------------

    enriched = []

    for article in articles:

        published_at = extract_article_date(
            article["url"]
        )

        enriched.append(
            {
                "title": article["title"],
                "url": article["url"],
                "published_at": published_at,
            }
        )

    return enriched, None


# ============================================================
# HABERLERİ DB'YE KAYDET
# ============================================================

def save_news(articles):

    conn = get_connection()

    inserted = 0

    now = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    for article in articles:

        title = article["title"]
        url = article["url"]

        published_at = (
            article.get("published_at")
            or now
        )

        summary = ""

        news_hash = make_hash(
            title,
            url,
        )

        category = detect_category(
            title,
            summary,
        )

        stocks = detect_stocks(
            title,
            summary,
        )

        company_news = is_company_news(
            title,
            summary,
            stocks,
            category,
        )

        # ----------------------------------------------------
        # Şirket haberi için kategori zorlaması
        # ----------------------------------------------------

        if company_news:
            category = "Şirket"

        impact, impact_score = detect_sentiment(
            title,
            summary,
        )

        comment = make_comment(
            title,
            summary,
            stocks,
            category,
            impact_score,
        )

        try:

            conn.execute(
                """
                INSERT INTO bloomberg_news (
                    news_hash,
                    title,
                    url,
                    published_at,
                    category,
                    summary,
                    related_stocks,
                    impact,
                    impact_score,
                    ai_comment,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    news_hash,
                    title,
                    url,
                    published_at,
                    category,
                    summary,
                    ",".join(stocks),
                    impact,
                    impact_score,
                    comment,
                    now,
                ),
            )

            inserted += 1

        except sqlite3.IntegrityError:

            pass

    conn.commit()
    conn.close()

    return inserted


# ============================================================
# DB'DEN HABERLER
# ============================================================

def load_news(
    view_mode="Tüm Haberler",
    start_date=None,
    end_date=None,
    category="Tümü",
    stock="Tümü",
):

    conn = get_connection()

    query = """
        SELECT
            id,
            title,
            url,
            published_at,
            category,
            summary,
            related_stocks,
            impact,
            impact_score,
            ai_comment
        FROM bloomberg_news
        WHERE 1=1
    """

    params = []

    # --------------------------------------------------------
    # TARİH
    # --------------------------------------------------------

    if start_date is not None:

        start_dt = datetime.combine(
            start_date,
            datetime.min.time(),
        ).strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        query += """
            AND published_at >= ?
        """

        params.append(start_dt)

    if end_date is not None:

        end_dt = datetime.combine(
            end_date,
            datetime.max.time(),
        ).strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        query += """
            AND published_at <= ?
        """

        params.append(end_dt)

    # --------------------------------------------------------
    # ŞİRKET HABERLERİ
    # --------------------------------------------------------

    if view_mode == "Şirket Haberleri":

        query += """
            AND (
                category = 'Şirket'
                OR related_stocks IS NOT NULL
                AND related_stocks != ''
            )
        """

    # --------------------------------------------------------
    # KATEGORİ
    # --------------------------------------------------------

    if category != "Tümü":

        query += """
            AND category = ?
        """

        params.append(category)

    # --------------------------------------------------------
    # HİSSE
    # --------------------------------------------------------

    if (
        view_mode == "Hisse Bazlı"
        and stock != "Tümü"
    ):

        query += """
            AND (
                related_stocks = ?
                OR related_stocks LIKE ?
                OR related_stocks LIKE ?
                OR related_stocks LIKE ?
            )
        """

        params.extend(
            [
                stock,
                f"{stock},%",
                f"%,{stock}",
                f"%,{stock},%",
            ]
        )

    # --------------------------------------------------------
    # SIRALAMA
    # --------------------------------------------------------

    query += """
        ORDER BY
            published_at DESC,
            id DESC
    """

    df = pd.read_sql_query(
        query,
        conn,
        params=params,
    )

    conn.close()

    return df


# ============================================================
# İSTATİSTİK
# ============================================================

def get_stats():

    conn = get_connection()

    total = conn.execute(
        "SELECT COUNT(*) FROM bloomberg_news"
    ).fetchone()[0]

    positive = conn.execute(
        """
        SELECT COUNT(*)
        FROM bloomberg_news
        WHERE impact_score > 0
        """
    ).fetchone()[0]

    neutral = conn.execute(
        """
        SELECT COUNT(*)
        FROM bloomberg_news
        WHERE impact_score = 0
        """
    ).fetchone()[0]

    negative = conn.execute(
        """
        SELECT COUNT(*)
        FROM bloomberg_news
        WHERE impact_score < 0
        """
    ).fetchone()[0]

    company = conn.execute(
        """
        SELECT COUNT(*)
        FROM bloomberg_news
        WHERE category = 'Şirket'
           OR (
               related_stocks IS NOT NULL
               AND related_stocks != ''
           )
        """
    ).fetchone()[0]

    conn.close()

    return (
        total,
        positive,
        neutral,
        negative,
        company,
    )


# ============================================================
# DB
# ============================================================

init_db()


# ============================================================
# BAŞLIK
# ============================================================

st.title(
    "📰 Bloomberg HT Haber Merkezi"
)

st.caption(
    "Bloomberg HT • Şirket Haberleri • Hisse Haberleri • Haber Arşivi"
)

st.info(
    "ℹ️ Bloomberg haber analizleri Dinamik Portföy "
    "skorunu ve hisse seçim motorunu değiştirmez."
)


# ============================================================
# GÜNCELLEME
# ============================================================

col1, col2 = st.columns(
    [1, 5]
)

with col1:

    if st.button(
        "🔄 Haberleri Güncelle",
        use_container_width=True,
    ):

        with st.spinner(
            "Bloomberg HT haberleri ve yayın tarihleri alınıyor..."
        ):

            articles, error = fetch_news()

            if error:

                st.error(error)

            else:

                inserted = save_news(
                    articles
                )

                st.success(
                    f"{len(articles)} haber tarandı. "
                    f"{inserted} yeni haber arşive eklendi."
                )

                st.rerun()


# ============================================================
# İSTATİSTİKLER
# ============================================================

(
    total,
    positive,
    neutral,
    negative,
    company,
) = get_stats()


c1, c2, c3, c4, c5 = st.columns(5)

with c1:
    st.metric(
        "📰 Toplam",
        total,
    )

with c2:
    st.metric(
        "🏢 Şirket",
        company,
    )

with c3:
    st.metric(
        "🟢 Pozitif",
        positive,
    )

with c4:
    st.metric(
        "🟡 Nötr",
        neutral,
    )

with c5:
    st.metric(
        "🔴 Negatif",
        negative,
    )


st.divider()


# ============================================================
# GÖRÜNÜM
# ============================================================

st.subheader(
    "🔎 Haber Görünümü"
)

view_mode = st.radio(
    "Görünüm",
    [
        "Tüm Haberler",
        "Şirket Haberleri",
        "Hisse Bazlı",
    ],
    horizontal=True,
)


# ============================================================
# TARİH FİLTRESİ
# ============================================================

st.subheader(
    "📅 Tarih Filtresi"
)

date_mode = st.radio(
    "Tarih seçimi",
    [
        "Son 24 Saat",
        "Son 3 Gün",
        "Son 7 Gün",
        "Son 30 Gün",
        "Özel Tarih Aralığı",
    ],
    horizontal=True,
)


today = date.today()

if date_mode == "Son 24 Saat":

    start_date = today - timedelta(days=1)
    end_date = today

elif date_mode == "Son 3 Gün":

    start_date = today - timedelta(days=3)
    end_date = today

elif date_mode == "Son 7 Gün":

    start_date = today - timedelta(days=7)
    end_date = today

elif date_mode == "Son 30 Gün":

    start_date = today - timedelta(days=30)
    end_date = today

else:

    d1, d2 = st.columns(2)

    with d1:

        start_date = st.date_input(
            "Başlangıç tarihi",
            value=today - timedelta(days=7),
        )

    with d2:

        end_date = st.date_input(
            "Bitiş tarihi",
            value=today,
        )

    if start_date > end_date:

        st.error(
            "Başlangıç tarihi bitiş tarihinden büyük olamaz."
        )

        st.stop()


# ============================================================
# EK FİLTRELER
# ============================================================

col1, col2 = st.columns(2)

with col1:

    categories = [
        "Tümü",
        "Şirket",
        "Enerji",
        "Faiz / TCMB",
        "Döviz",
        "Borsa",
        "Enflasyon",
        "Jeopolitik",
        "Küresel Piyasalar",
        "Genel",
    ]

    category = st.selectbox(
        "📂 Kategori",
        categories,
    )


with col2:

    stock_options = [
        "Tümü"
    ] + sorted(
        STOCK_MAP.keys()
    )

    if view_mode == "Hisse Bazlı":

        stock = st.selectbox(
            "📈 Hisse",
            stock_options,
        )

    else:

        stock = "Tümü"

        st.caption(
            "💡 Şirket Haberleri görünümünde "
            "hisse seçmek zorunda değilsiniz."
        )


# ============================================================
# HABERLERİ GETİR
# ============================================================

df = load_news(
    view_mode=view_mode,
    start_date=start_date,
    end_date=end_date,
    category=category,
    stock=stock,
)


# ============================================================
# SONUÇ BAŞLIĞI
# ============================================================

if view_mode == "Şirket Haberleri":

    st.subheader(
        f"🏢 Şirket Haberleri — {len(df)} haber"
    )

elif view_mode == "Hisse Bazlı":

    st.subheader(
        f"📈 {stock} Haberleri — {len(df)} haber"
    )

else:

    st.subheader(
        f"📰 Tüm Haberler — {len(df)} haber"
    )


st.caption(
    f"📅 {start_date.strftime('%d.%m.%Y')} "
    f"→ {end_date.strftime('%d.%m.%Y')}"
)


# ============================================================
# HABERLER
# ============================================================

if df.empty:

    st.warning(
        "Bu tarih ve filtrelerde haber bulunamadı."
    )

    st.info(
        "Yeni haberleri almak için "
        "**🔄 Haberleri Güncelle** butonunu kullan."
    )

else:

    # --------------------------------------------------------
    # GÜN GÜN GRUPLAMA
    # --------------------------------------------------------

    df["date_only"] = pd.to_datetime(
        df["published_at"],
        errors="coerce",
    ).dt.date

    current_date = None

    for _, row in df.iterrows():

        row_date = row["date_only"]

        if row_date != current_date:

            current_date = row_date

            if pd.isna(row_date):

                date_text = "Tarihi Belirlenemeyen Haberler"

            else:

                date_text = row_date.strftime(
                    "%d.%m.%Y"
                )

            st.markdown(
                f"## 📅 {date_text}"
            )

        title = row["title"]
        url = row["url"]
        published = row["published_at"]
        category_value = row["category"]
        related = row["related_stocks"]
        impact = row["impact"]
        comment = row["ai_comment"]

        with st.container(
            border=True
        ):

            st.markdown(
                f"### {title}"
            )

            c1, c2, c3 = st.columns(
                [1.4, 1.4, 1]
            )

            with c1:

                st.caption(
                    f"🕐 {published}"
                )

            with c2:

                st.caption(
                    f"📂 {category_value}"
                )

            with c3:

                st.caption(
                    f"📊 {impact}"
                )

            if related:

                stocks_display = " • ".join(
                    [
                        f"`{x}`"
                        for x in related.split(",")
                        if x
                    ]
                )

                st.markdown(
                    f"**📈 İlgili BIST hisseleri:** "
                    f"{stocks_display}"
                )

            elif category_value == "Şirket":

                st.markdown(
                    "**🏢 Şirket haberi**"
                )

            else:

                st.caption(
                    "📌 Doğrudan BIST hissesi eşleştirilemedi."
                )

            st.markdown(
                f"🤖 **AI Yorumu:** {comment}"
            )

            st.markdown(
                f"🔗 [Bloomberg HT haberini aç]({url})"
            )


# ============================================================
# ARŞİV BİLGİSİ
# ============================================================

st.divider()

st.caption(
    "💾 Haberler SQLite veritabanında saklanır. "
    "Eski haberler silinmez ve aynı haber ikinci kez kaydedilmez."
)

st.caption(
    "⚠️ Haber etkisi bilgilendirme amaçlıdır; "
    "Dinamik Portföy skoruna dahil edilmez."
)