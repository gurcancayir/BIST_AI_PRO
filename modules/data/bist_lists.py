# ============================================================
# BIST AI PRO
# modules/data/bist_lists.py
#
# MERKEZİ BIST LİSTELERİ
#
# BIST30 / BIST50 / BIST100 / BIST500
#
# ÖNEMLİ:
# ------------------------------------------------------------
# Midas sayfalarında pandas.read_html() KULLANILMIYOR.
#
# Doğrulanan gerçek HTML yapısı:
#
# <a class="title stock-code"
#    href="/canli-borsa/a1cap-hisse/">A1CAP</a>
#
# Bu nedenle doğrudan "stock-code" HTML bağlantılarından
# sembol çıkarıyoruz.
#
# BIST500:
# ------------------------------------------------------------
# 500 TEKİL HİSSE doğrulanmadan BIST500 kullanılamaz.
#
# BIST500 hiçbir zaman BIST100'e düşürülmez.
#
# ============================================================


from __future__ import annotations

import re
from typing import Dict, List, Optional

import requests


# ============================================================
# AYARLAR
# ============================================================

REQUEST_TIMEOUT = 30

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/151.0.0.0 Safari/537.36"
    ),
    "Accept-Language": (
        "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7"
    ),
}


# ============================================================
# MİDAS KAYNAKLARI
# ============================================================

MIDAS_URLS = {

    "BIST30": (
        "https://www.getmidas.com/"
        "canli-borsa/xu030-bist-30-hisseleri"
    ),

    "BIST50": (
        "https://www.getmidas.com/"
        "canli-borsa/xu050-bist-50-hisseleri"
    ),

    "BIST100": (
        "https://www.getmidas.com/"
        "canli-borsa/xu100-bist-100-hisseleri"
    ),

    "BIST500": (
        "https://www.getmidas.com/"
        "canli-borsa/bist-500-hisseleri"
    ),
}


# ============================================================
# BEKLENEN LİSTE SAYILARI
# ============================================================

EXPECTED_COUNTS = {

    "BIST30": 30,

    "BIST50": 50,

    "BIST100": 100,

    "BIST500": 500,
}


# ============================================================
# GEÇERSİZ SEMBOLLER
# ============================================================

INVALID_SYMBOLS = {

    "BIST",
    "XU030",
    "XU050",
    "XU100",
    "XU500",

    "INDEX",
    "HISSE",
    "SEMBOL",
    "SYMBOL",

    "KOD",
    "CODE",

    "FON",
    "NULL",
    "NAN",
}


# ============================================================
# SEKTÖR HARİTASI
#
# Mevcut sistemde kullanılan sektörler korunmuştur.
#
# ============================================================

SECTOR_MAP: Dict[str, List[str]] = {

    # --------------------------------------------------------
    # BANKA
    # --------------------------------------------------------

    "Banka": [
        "AKBNK",
        "ALBRK",
        "GARAN",
        "HALKB",
        "ICBCT",
        "ISCTR",
        "KLNMA",
        "QNBTR",
        "SKBNK",
        "TSKB",
        "VAKBN",
        "YKBNK",
    ],

    # --------------------------------------------------------
    # SİGORTA
    # --------------------------------------------------------

    "Sigorta": [
        "AGESA",
        "ANHYT",
        "AKGRT",
        "ANSGR",
        "TURSG",
    ],

    # --------------------------------------------------------
    # ENERJİ
    # --------------------------------------------------------

    "Enerji": [
        "AKFYE",
        "AKSEN",
        "ALFAS",
        "ASTOR",
        "AYDEM",
        "AYEN",
        "CWENE",
        "ENJSA",
        "ENERY",
        "EUPWR",
        "GESAN",
        "GWIND",
        "KONTR",
        "MAGEN",
        "NATEN",
        "ODAS",
        "SMRTG",
        "YEOTK",
        "ZOREN",
    ],

    # --------------------------------------------------------
    # PETROL
    # --------------------------------------------------------

    "Petrol": [
        "TUPRS",
        "PETKM",
        "AYGAZ",
    ],

    # --------------------------------------------------------
    # SAVUNMA
    # --------------------------------------------------------

    "Savunma": [
        "ASELS",
        "ALTNY",
        "SDTTR",
        "ONRYT",
    ],

    # --------------------------------------------------------
    # HAVACILIK
    # --------------------------------------------------------

    "Havacılık": [
        "THYAO",
        "PGSUS",
        "TAVHL",
        "CLEBI",
    ],

    # --------------------------------------------------------
    # OTOMOTİV
    # --------------------------------------------------------

    "Otomotiv": [
        "FROTO",
        "TOASO",
        "DOAS",
        "TTRAK",
        "KARSN",
        "ASUZU",
        "OTKAR",
    ],

    # --------------------------------------------------------
    # DEMİR ÇELİK
    # --------------------------------------------------------

    "Demir Çelik": [
        "EREGL",
        "KRDMD",
        "BRSAN",
        "ISDMR",
        "CEMTS",
    ],

    # --------------------------------------------------------
    # ÇİMENTO
    # --------------------------------------------------------

    "Çimento": [
        "AKCNS",
        "BTCIM",
        "BUCIM",
        "CIMSA",
        "OYAKC",
        "NUHCM",
        "KONYA",
        "AFYON",
    ],

    # --------------------------------------------------------
    # KİMYA
    # --------------------------------------------------------

    "Kimya": [
        "PETKM",
        "SASA",
        "ALKIM",
        "BRISA",
        "KMPUR",
        "GUBRF",
    ],

    # --------------------------------------------------------
    # GIDA
    # --------------------------------------------------------

    "Gıda": [
        "AEFES",
        "CCOLA",
        "ULKER",
        "TATGD",
        "TUKAS",
        "BANVT",
        "KERVT",
        "PNSUT",
        "SOKM",
    ],

    # --------------------------------------------------------
    # PERAKENDE
    # --------------------------------------------------------

    "Perakende": [
        "BIMAS",
        "MGROS",
        "SOKM",
        "BIZIM",
        "MAVI",
    ],

    # --------------------------------------------------------
    # HOLDİNG
    # --------------------------------------------------------

    "Holding": [
        "KCHOL",
        "SAHOL",
        "AGHOL",
        "ALARK",
        "DOHOL",
        "ENKAI",
        "TKFEN",
    ],

    # --------------------------------------------------------
    # TEKNOLOJİ
    # --------------------------------------------------------

    "Teknoloji": [
        "ARDYZ",
        "ASELS",
        "LOGO",
        "MIATK",
        "REEDR",
        "SDTTR",
        "SMART",
    ],

    # --------------------------------------------------------
    # TELEKOM
    # --------------------------------------------------------

    "Telekom": [
        "TCELL",
        "TTKOM",
    ],

    # --------------------------------------------------------
    # GAYRİMENKUL
    # --------------------------------------------------------

    "GMYO": [
        "AKFGY",
        "AVPGY",
        "EKGYO",
        "TRGYO",
        "ISGYO",
        "SISE",
    ],

    # --------------------------------------------------------
    # İNŞAAT
    # --------------------------------------------------------

    "İnşaat": [
        "ENKAI",
        "KUYAS",
        "GESAN",
        "KONTR",
    ],

    # --------------------------------------------------------
    # MADENCİLİK
    # --------------------------------------------------------

    "Madencilik": [
        "KOZAA",
        "KOZAL",
        "IPEKE",
        "CVKMD",
        "PRKME",
    ],

    # --------------------------------------------------------
    # CAM
    # --------------------------------------------------------

    "Cam": [
        "SISE",
    ],

    # --------------------------------------------------------
    # TURİZM
    # --------------------------------------------------------

    "Turizm": [
        "MAALT",
        "ULAS",
        "PKENT",
    ],

    # --------------------------------------------------------
    # MOBİLYA
    # --------------------------------------------------------

    "Mobilya": [
        "YATAS",
        "KLSYN",
    ],
}


# ============================================================
# SEKTÖR → HİSSE TERS HARİTA
# ============================================================

STOCK_TO_SECTOR: Dict[str, str] = {}

for sector_name, symbols in SECTOR_MAP.items():

    for symbol in symbols:

        STOCK_TO_SECTOR[
            str(symbol).upper().strip()
        ] = sector_name


# ============================================================
# SEMBOL NORMALİZASYONU
# ============================================================

def normalize_symbol(value) -> Optional[str]:
    """
    Hisse kodunu temizler.

    Örnek:

        A1CAP
        a1cap
        A1CAP.E
        A1CAP.IS
    """

    if value is None:
        return None

    try:

        text = str(value).strip().upper()

    except Exception:

        return None

    if not text:
        return None

    text = text.replace(
        "\xa0",
        " ",
    )

    text = text.strip()

    # Yahoo / Borsa formatları

    text = re.sub(
        r"\.(E|IS)$",
        "",
        text,
    )

    # Normal sembol

    if re.fullmatch(
        r"[A-Z0-9]{2,8}",
        text,
    ):

        return text

    # Metin içerisinde sembol

    match = re.search(
        r"\b([A-Z0-9]{2,8})\b",
        text,
    )

    if match:

        candidate = match.group(1)

        if not candidate.isdigit():

            return candidate

    return None


# ============================================================
# SEMBOL GEÇERLİ Mİ?
# ============================================================

def is_valid_symbol(
    symbol: Optional[str],
) -> bool:

    if not symbol:

        return False

    symbol = (
        str(symbol)
        .upper()
        .strip()
    )

    if symbol in INVALID_SYMBOLS:

        return False

    if not re.fullmatch(
        r"[A-Z0-9]{2,8}",
        symbol,
    ):

        return False

    return True


# ============================================================
# MİDAS HTML AL
# ============================================================

def fetch_midas_html(
    pool: str,
) -> str:

    url = MIDAS_URLS.get(pool)

    if not url:

        return ""

    try:

        response = requests.get(
            url,
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT,
        )

        response.raise_for_status()

        html = response.text

        if not html:

            return ""

        print(
            f"[{pool}] Midas HTML alındı. "
            f"Uzunluk: {len(html):,}"
        )

        return html

    except Exception as exc:

        print(
            f"[{pool}] Midas HTML alınamadı: "
            f"{exc}"
        )

        return ""


# ============================================================
# MİDAS HTML'DEN HİSSE ÇIKAR
#
# GERÇEK MİDAS YAPISI:
#
# <a class="title stock-code"
#    href="/canli-borsa/a1cap-hisse/">A1CAP</a>
#
# Burada sadece stock-code sınıfına güveniyoruz.
#
# ============================================================

def extract_midas_symbols(
    html: str,
) -> List[str]:

    if not html:

        return []

    # --------------------------------------------------------
    # Öncelikli yöntem:
    #
    # class içinde stock-code bulunan <a> etiketleri
    # --------------------------------------------------------

    pattern = re.compile(
        r'<a\b'
        r'[^>]*'
        r'class\s*=\s*["\'][^"\']*\bstock-code\b[^"\']*["\']'
        r'[^>]*>'
        r'\s*'
        r'([A-Z0-9]{2,8})'
        r'\s*'
        r'</a>',
        re.IGNORECASE,
    )

    matches = pattern.findall(html)

    symbols: List[str] = []

    seen = set()

    for value in matches:

        symbol = normalize_symbol(value)

        if not is_valid_symbol(symbol):

            continue

        if symbol in seen:

            continue

        seen.add(symbol)

        symbols.append(symbol)

    return symbols


# ============================================================
# HAVUZ DOĞRULAMA
# ============================================================

def validate_pool(
    pool: str,
    symbols: List[str],
) -> bool:

    expected = EXPECTED_COUNTS.get(pool)

    if expected is None:

        return False

    if not symbols:

        return False

    unique_symbols = list(
        dict.fromkeys(
            symbols
        )
    )

    # Tam sayı

    if len(unique_symbols) != expected:

        return False

    # Gerçek tekillik

    if len(set(unique_symbols)) != expected:

        return False

    return True


# ============================================================
# MİDAS HAVUZU GETİR
#
# BIST30 / BIST50 / BIST100
# ============================================================

def fetch_midas_list(
    pool: str,
) -> List[str]:

    html = fetch_midas_html(
        pool
    )

    if not html:

        print(
            f"[{pool}] HTML bulunamadı."
        )

        return []

    symbols = extract_midas_symbols(
        html
    )

    print(
        f"[{pool}] Midas HTML'den "
        f"{len(symbols)} tekil sembol çıkarıldı."
    )

    if validate_pool(
        pool,
        symbols,
    ):

        print(
            f"[{pool}] "
            f"✅ {len(symbols)} hisse doğrulandı."
        )

        return symbols

    print(
        f"[{pool}] "
        f"❌ Liste doğrulanamadı."
        f" Beklenen: {EXPECTED_COUNTS.get(pool)},"
        f" Bulunan: {len(symbols)}"
    )

    return []


# ============================================================
# BIST500
#
# ÖZEL VE SIKI DOĞRULAMA
#
# ASLA BIST100 FALLBACK YOK.
# ============================================================

def fetch_bist500() -> List[str]:

    print()
    print("=" * 60)
    print(
        "[BIST500] Midas BIST500 listesi alınıyor..."
    )
    print("=" * 60)

    html = fetch_midas_html(
        "BIST500"
    )

    if not html:

        print(
            "[KRİTİK] BIST500 HTML alınamadı."
        )

        return []

    # --------------------------------------------------------
    # Doğrudan stock-code çıkar
    # --------------------------------------------------------

    symbols = extract_midas_symbols(
        html
    )

    print(
        f"[BIST500] HTML'den çıkarılan "
        f"tekil sembol: {len(symbols)}"
    )

    # --------------------------------------------------------
    # 500 TEKİL DOĞRULAMA
    # --------------------------------------------------------

    if validate_pool(
        "BIST500",
        symbols,
    ):

        print()
        print(
            "[BIST500] "
            "✅ 500 TEKİL HİSSE DOĞRULANDI."
        )

        print(
            "[BIST500] "
            "✅ Tarama Merkezi kullanabilir."
        )

        print("=" * 60)

        return symbols

    # --------------------------------------------------------
    # BAŞARISIZ
    # --------------------------------------------------------

    print()
    print(
        "[KRİTİK] BIST500 doğrulanamadı."
    )

    print(
        f"[KRİTİK] Bulunan: {len(symbols)}"
    )

    print(
        "[KRİTİK] BIST500 = []"
    )

    print(
        "[KRİTİK] BIST100, BIST500 "
        "olarak KULLANILMAYACAK."
    )

    print("=" * 60)

    return []


# ============================================================
# LİSTELERİ OLUŞTUR
#
# Modül import edildiğinde bir kez çalışır.
# ============================================================

BIST30 = fetch_midas_list(
    "BIST30"
)

BIST50 = fetch_midas_list(
    "BIST50"
)

BIST100 = fetch_midas_list(
    "BIST100"
)

BIST500 = fetch_bist500()


# ============================================================
# SEKTÖR GETİR
# ============================================================

def get_stock_sector(
    symbol: str,
) -> str:

    if not symbol:

        return "Diğer"

    symbol = (
        str(symbol)
        .upper()
        .strip()
    )

    return STOCK_TO_SECTOR.get(
        symbol,
        "Diğer",
    )


# ============================================================
# HİSSE HANGİ HAVUZLARDA?
# ============================================================

def get_stock_pools(
    symbol: str,
) -> List[str]:

    if not symbol:

        return []

    symbol = (
        str(symbol)
        .upper()
        .strip()
    )

    pools = []

    if symbol in BIST30:

        pools.append(
            "BIST30"
        )

    if symbol in BIST50:

        pools.append(
            "BIST50"
        )

    if symbol in BIST100:

        pools.append(
            "BIST100"
        )

    if symbol in BIST500:

        pools.append(
            "BIST500"
        )

    return pools


# ============================================================
# HAVUZ LİSTESİ GETİR
# ============================================================

def get_bist_list(
    pool: str,
) -> List[str]:

    if not pool:

        return []

    pool = (
        str(pool)
        .upper()
        .strip()
    )

    if pool == "BIST30":

        return BIST30.copy()

    if pool == "BIST50":

        return BIST50.copy()

    if pool == "BIST100":

        return BIST100.copy()

    if pool == "BIST500":

        return BIST500.copy()

    # --------------------------------------------------------
    # BIST TÜM
    #
    # BIST500 geçerliyse BIST500 temel alınır.
    #
    # BIST500 geçersizse BIST100 ile devam eder.
    #
    # Bu BIST500 FALLBACK değildir.
    # Sadece "BIST TÜM" havuzunun davranışıdır.
    # --------------------------------------------------------

    if pool in {
        "BIST TUM",
        "BISTTUM",
        "XUTUM",
    }:

        return sorted(
            set(BIST500)
            | set(BIST100)
        )

    return []


# ============================================================
# BIST500 GEÇERLİ Mİ?
# ============================================================

def can_scan_bist500() -> bool:

    return (
        len(BIST500) == 500
        and len(set(BIST500)) == 500
    )


# ============================================================
# BIST500 ZORUNLU KONTROL
# ============================================================

def require_bist500() -> List[str]:

    if not can_scan_bist500():

        raise RuntimeError(
            "GERÇEK BIST500 LİSTESİ "
            "DOĞRULANAMADI. "
            "Tarama işlemi durduruldu. "
            f"Mevcut hisse sayısı: "
            f"{len(BIST500)}"
        )

    return BIST500.copy()


# ============================================================
# HAVUZ DURUMU
# ============================================================

def get_pool_status() -> dict:

    return {

        "BIST30": {
            "count": len(BIST30),
            "valid": validate_pool(
                "BIST30",
                BIST30,
            ),
        },

        "BIST50": {
            "count": len(BIST50),
            "valid": validate_pool(
                "BIST50",
                BIST50,
            ),
        },

        "BIST100": {
            "count": len(BIST100),
            "valid": validate_pool(
                "BIST100",
                BIST100,
            ),
        },

        "BIST500": {
            "count": len(BIST500),
            "valid": validate_pool(
                "BIST500",
                BIST500,
            ),
        },
    }


# ============================================================
# MERKEZİ LİSTE KONTROLÜ
# ============================================================

def validate_bist_lists():

    print()
    print("=" * 70)
    print(
        "BIST AI PRO - MERKEZİ LİSTE KONTROLÜ"
    )
    print("=" * 70)

    print(
        f"BIST30  : {len(BIST30):>4}"
    )

    print(
        f"BIST50  : {len(BIST50):>4}"
    )

    print(
        f"BIST100 : {len(BIST100):>4}"
    )

    print(
        f"BIST500 : {len(BIST500):>4}"
    )

    print(
        f"Sektör  : {len(STOCK_TO_SECTOR):>4}"
    )

    print()

    # --------------------------------------------------------
    # BIST30
    # --------------------------------------------------------

    if validate_pool(
        "BIST30",
        BIST30,
    ):

        print(
            "✅ BIST30: 30 tekil hisse"
        )

    else:

        print(
            f"❌ BIST30: "
            f"{len(BIST30)}"
        )

    # --------------------------------------------------------
    # BIST50
    # --------------------------------------------------------

    if validate_pool(
        "BIST50",
        BIST50,
    ):

        print(
            "✅ BIST50: 50 tekil hisse"
        )

    else:

        print(
            f"❌ BIST50: "
            f"{len(BIST50)}"
        )

    # --------------------------------------------------------
    # BIST100
    # --------------------------------------------------------

    if validate_pool(
        "BIST100",
        BIST100,
    ):

        print(
            "✅ BIST100: 100 tekil hisse"
        )

    else:

        print(
            f"❌ BIST100: "
            f"{len(BIST100)}"
        )

    # --------------------------------------------------------
    # BIST500
    # --------------------------------------------------------

    if can_scan_bist500():

        print(
            "✅ BIST500: "
            "500 tekil hisse"
        )

        print(
            "✅ BIST500 TARAMA AÇIK"
        )

    else:

        print(
            f"❌ BIST500: "
            f"{len(BIST500)}"
        )

        print(
            "❌ BIST500 TARAMA KAPALI"
        )

    print("=" * 70)


# ============================================================
# MODÜL YÜKLENDİĞİNDE KONTROL
# ============================================================

validate_bist_lists()


# ============================================================
# TEST YARDIMCISI
# ============================================================

def print_bist_test():

    print()
    print("=" * 70)
    print(
        "BIST AI PRO - BIST LİSTE TESTİ"
    )
    print("=" * 70)

    print()

    print(
        "BIST30  :",
        len(BIST30),
    )

    print(
        "BIST50  :",
        len(BIST50),
    )

    print(
        "BIST100 :",
        len(BIST100),
    )

    print(
        "BIST500 :",
        len(BIST500),
    )

    print()

    print(
        "BIST500 tekil:",
        len(set(BIST500)),
    )

    print(
        "BIST500 geçerli:",
        can_scan_bist500(),
    )

    print()

    if BIST500:

        print(
            "BIST500 İLK 20:"
        )

        print(
            BIST500[:20]
        )

        print()

        print(
            "BIST500 SON 20:"
        )

        print(
            BIST500[-20:]
        )

    print()

    print(
        "ÖRNEK HAVUZ TESTİ:"
    )

    for symbol in [
        "A1CAP",
        "AEFES",
        "ASELS",
        "ASTOR",
        "BIMAS",
        "THYAO",
        "TUPRS",
        "YKBNK",
        "ZOREN",
    ]:

        print(
            f"{symbol:6} -> "
            f"{get_stock_pools(symbol)}"
        )

    print()

    print(
        "ÖRNEK SEKTÖR TESTİ:"
    )

    for symbol in [
        "ASELS",
        "TUPRS",
        "AKSEN",
        "BIMAS",
        "CIMSA",
        "ENKAI",
    ]:

        print(
            f"{symbol:6} -> "
            f"{get_stock_sector(symbol)}"
        )

    print()
    print("=" * 70)


# ============================================================
# SON
# ============================================================