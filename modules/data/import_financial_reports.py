# ============================================================
# BIST AI PRO
# KAP FİNANSAL RAPOR IMPORTER
#
# AKIŞ
# PDF / TXT
#    ↓
# METİN
#    ↓
# DÖNEM + HİSSE TESPİTİ
#    ↓
# KAP TABLO SATIRLARI
#    ↓
# FİNANSAL KALEMLER
#    ↓
# SQLite / financial_statements
#
# ÖNEMLİ TASARIM KARARLARI
# - Bu dosya proje kökünde de, modules/data altında da çalışabilir.
# - data/financial_reports alt klasörleri recursive taranır.
# - Aynı raporun PDF + TXT kopyası varsa TXT tercih edilir.
# - KAP tablolarındaki dipnot numarası (örn. "Hasılat 14 88.494.252")
#   finansal değer sanılmaz.
# - KAP "1.000 TL" birimi gerçek TL'ye çevrilir.
# - 2Ç gelir tablosunda 4 değer bulunursa ilk değer 6 aylık cari dönemdir.
#   3 aylık değerler yanlışlıkla alınmaz.
# - Bilanço satırlarında ilk değer cari dönem, ikinci değer önceki dönemdir.
# - Aynı symbol + period_end kaydı varsa UPDATE yapılır.
# - import_all_financial_reports() HER ZAMAN dict döndürür.
# ============================================================

import re
import sqlite3
from datetime import datetime
from pathlib import Path

from pypdf import PdfReader


# ============================================================
# PROJE YOLLARI
# ============================================================

CURRENT_FILE = Path(__file__).resolve()


def find_project_root():
    """
    borsa.db dosyasının bulunduğu proje kökünü bulur.

    Dosya:
        proje/import_financial_reports.py
    veya:
        proje/modules/data/import_financial_reports.py

    her iki yapıda da çalışır.
    """
    for parent in [CURRENT_FILE.parent, *CURRENT_FILE.parents]:
        if (parent / "borsa.db").exists():
            return parent

    # DB henüz yoksa en makul fallback:
    if CURRENT_FILE.parent.name.lower() == "data":
        return CURRENT_FILE.parents[2]
    if CURRENT_FILE.parent.name.lower() == "modules":
        return CURRENT_FILE.parent.parent
    return CURRENT_FILE.parent


BASE_DIR = find_project_root()

DB_PATH = BASE_DIR / "borsa.db"
REPORTS_DIR = BASE_DIR / "data" / "financial_reports"

SUPPORTED_EXTENSIONS = {".pdf", ".txt"}

PERIOD_MAP = {
    "1C": ("_1Q", "-03-31"),
    "1Q": ("_1Q", "-03-31"),
    "2C": ("_2Q", "-06-30"),
    "2Q": ("_2Q", "-06-30"),
    "3C": ("_3Q", "-09-30"),
    "3Q": ("_3Q", "-09-30"),
    "4C": ("_4Q", "-12-31"),
    "4Q": ("_4Q", "-12-31"),
    "YILLIK": ("_YILLIK", "-12-31"),
    "ANNUAL": ("_YILLIK", "-12-31"),
}


# ============================================================
# SQLITE
# ============================================================

REQUIRED_COLUMNS = {
    "symbol": "TEXT",
    "period": "TEXT",
    "period_end": "TEXT",
    "report_type": "TEXT",
    "currency": "TEXT",
    "revenue": "REAL",
    "net_profit": "REAL",
    "cash": "REAL",
    "trade_receivables": "REAL",
    "inventory": "REAL",
    "current_assets": "REAL",
    "current_liabilities": "REAL",
    "total_assets": "REAL",
    "equity": "REAL",
    "cost_of_sales": "REAL",
    "operating_profit": "REAL",
    "interest_expense": "REAL",
    "operating_cash_flow": "REAL",
    "short_term_financial_debt": "REAL",
    "current_portion_long_term_debt": "REAL",
    "long_term_financial_debt": "REAL",
    "source": "TEXT",
    "source_date": "TEXT",
    "updated_at": "TEXT",
}


def get_connection():
    conn = sqlite3.connect(
        DB_PATH,
        timeout=30,
        check_same_thread=False,
    )
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def ensure_database_schema():
    conn = get_connection()

    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS financial_statements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                period TEXT,
                period_end TEXT,
                report_type TEXT,
                currency TEXT,
                revenue REAL,
                net_profit REAL,
                cash REAL,
                trade_receivables REAL,
                inventory REAL,
                current_assets REAL,
                current_liabilities REAL,
                total_assets REAL,
                equity REAL,
                cost_of_sales REAL,
                operating_profit REAL,
                interest_expense REAL,
                operating_cash_flow REAL,
                short_term_financial_debt REAL,
                current_portion_long_term_debt REAL,
                long_term_financial_debt REAL,
                source TEXT,
                source_date TEXT,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        existing = {
            row[1]
            for row in conn.execute(
                "PRAGMA table_info(financial_statements)"
            ).fetchall()
        }

        for name, column_type in REQUIRED_COLUMNS.items():
            if name not in existing:
                conn.execute(
                    f"ALTER TABLE financial_statements "
                    f"ADD COLUMN {name} {column_type}"
                )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_financial_statements_symbol_period
            ON financial_statements(symbol, period_end)
            """
        )

        conn.commit()

    finally:
        conn.close()


# ============================================================
# METİN / SAYI NORMALİZASYONU
# ============================================================

def normalize_text(text):
    if text is None:
        return ""

    text = str(text)
    text = text.replace("\ufeff", "")
    text = text.replace("\u00a0", " ")
    text = text.replace("\r\n", "\n")
    text = text.replace("\r", "\n")
    text = text.replace("−", "-")
    text = text.replace("–", "-")
    text = text.replace("—", "-")

    # PDF'den gelen çoklu boşlukları tek boşluğa indir.
    text = re.sub(r"[ \t]+", " ", text)

    return text


def parse_number(value):
    """
    Türkçe/KAP sayılarını float'a çevirir.

    88.494.252       -> 88494252
    14.449.834       -> 14449834
    -60.397.561      -> -60397561
    (1.234.567)      -> -1234567
    1.234.567,89     -> 1234567.89
    """
    if value is None:
        return None

    value = str(value).strip()

    if not value:
        return None

    value = (
        value
        .replace("\u00a0", "")
        .replace(" ", "")
        .replace("%", "")
    )

    negative = value.startswith("(") and value.endswith(")")

    if negative:
        value = value[1:-1]

    if value.startswith("-"):
        value = value[1:]
        negative = not negative

    if "," in value:
        # Türkçe ondalık gösterim.
        value = value.replace(".", "").replace(",", ".")
    else:
        # 88.494.252 gibi binlik ayrımları.
        if value.count(".") > 1:
            value = value.replace(".", "")
        elif re.fullmatch(r"\d{1,3}\.\d{3}", value):
            value = value.replace(".", "")

    try:
        number = float(value)
    except (TypeError, ValueError):
        return None

    return -number if negative else number


NUMBER_RE = re.compile(
    r"""
    [-−]?
    \(?
    (?:
        \d{1,3}(?:[\.\s]\d{3})+(?:,\d+)?
        |
        \d+(?:,\d+)?
    )
    \)?
    """,
    re.VERBOSE,
)


def extract_raw_numbers(text):
    return NUMBER_RE.findall(text or "")


def extract_numbers(text):
    result = []

    for raw in extract_raw_numbers(text):
        value = parse_number(raw)

        if value is not None:
            result.append(value)

    return result


def is_small_integer(value):
    if value is None:
        return False

    return float(value).is_integer() and 0 <= value <= 99


def remove_note_number(values):
    """
    KAP satırlarında finansal kalemden hemen sonra dipnot numarası
    bulunabilir:

        Hasılat 14 88.494.252 70.956.004 ...

    Buradaki 14 finansal değer değildir.

    Eğer ilk sayı küçük bir tam sayı ve ikinci sayı finansal büyüklük
    görünümündeyse ilk sayı atılır.
    """
    if len(values) < 2:
        return values

    first = values[0]
    second = values[1]

    if is_small_integer(first) and abs(second) >= 1000:
        return values[1:]

    return values


def first_financial_value(values):
    values = remove_note_number(values)

    if not values:
        return None

    return values[0]


# ============================================================
# BİRİM TESPİTİ
# ============================================================

def detect_unit_multiplier(text):
    """
    KAP raporlarında tutarların hangi birimde sunulduğunu bulur.

    Dönen:
        multiplier, unit

    Örnek:
        1.000 TL -> 1000, "1.000 TL"
        1.000.000 TL -> 1000000, "1.000.000 TL"
    """
    sample = normalize_text(text[:250_000]).lower()

    patterns = [
        (
            r"sunum\s+para\s+birimi.{0,120}"
            r"1\s*[\.,]?\s*000\s*[\.,]?\s*tl",
            1_000,
            "1.000 TL",
        ),
        (
            r"sunum\s+para\s+birimi.{0,120}"
            r"bin\s*tl",
            1_000,
            "1.000 TL",
        ),
        (
            r"sunum\s+para\s+birimi.{0,120}"
            r"1\s*[\.,]?\s*000\s*[\.,]?\s*000\s*tl",
            1_000_000,
            "1.000.000 TL",
        ),
        (
            r"sunum\s+para\s+birimi.{0,120}"
            r"milyon\s*tl",
            1_000_000,
            "Milyon TL",
        ),
        (
            r"sunum\s+para\s+birimi.{0,120}"
            r"milyar\s*tl",
            1_000_000_000,
            "Milyar TL",
        ),
    ]

    # Milyon/Milyar ifadelerini önce kontrol et.
    for pattern, multiplier, unit in patterns[2:]:
        if re.search(pattern, sample, re.IGNORECASE):
            return multiplier, unit

    # Bin TL / 1.000 TL.
    for pattern, multiplier, unit in patterns[:2]:
        if re.search(pattern, sample, re.IGNORECASE):
            return multiplier, unit

    # Genel fallback.
    if re.search(r"\bmilyar\s*tl\b", sample):
        return 1_000_000_000, "Milyar TL"

    if re.search(r"\bmilyon\s*tl\b", sample):
        return 1_000_000, "Milyon TL"

    if re.search(r"\bbin\s*tl\b", sample):
        return 1_000, "1.000 TL"

    return 1, "TL"


# ============================================================
# DOSYA OKUMA
# ============================================================

def read_txt(path):
    path = Path(path)

    last_error = None

    for encoding in (
        "utf-8",
        "utf-8-sig",
        "cp1254",
        "iso-8859-9",
        "latin-1",
    ):
        try:
            text = path.read_text(encoding=encoding)

            if text.strip():
                return text

        except Exception as error:
            last_error = error

    raise ValueError(f"TXT okunamadı: {last_error}")


def read_pdf(path):
    path = Path(path)

    reader = PdfReader(str(path))
    pages = []

    for page_number, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""

            if text.strip():
                pages.append(text)

        except Exception as error:
            print(
                f"⚠️ PDF sayfası okunamadı "
                f"(sayfa {page_number}): {error}"
            )

    return "\n".join(pages)


def read_file(path):
    suffix = Path(path).suffix.lower()

    if suffix == ".txt":
        return read_txt(path)

    if suffix == ".pdf":
        return read_pdf(path)

    raise ValueError(f"Desteklenmeyen dosya türü: {suffix}")


# ============================================================
# HİSSE / DÖNEM
# ============================================================

def detect_symbol_from_filename(filename):
    name = Path(filename).stem.upper().strip()

    patterns = [
        r"^([A-Z0-9]{2,10})[_-]20\d{2}[_-]",
        r"^([A-Z0-9]{2,10})20\d{2}[_-]",
    ]

    for pattern in patterns:
        match = re.match(pattern, name)

        if match:
            return match.group(1)

    # Altı çizili / tireli olmayan isimler için fallback.
    match = re.search(r"^([A-Z]{3,6})(?=[_-]?20\d{2})", name)

    if match:
        return match.group(1)

    raise ValueError(
        f"Hisse kodu dosya adından bulunamadı: {filename}"
    )


def detect_period_from_filename(filename):
    name = Path(filename).stem.upper()

    match = re.search(
        r"(20\d{2})[_-]"
        r"(1C|2C|3C|4C|1Q|2Q|3Q|4Q|YILLIK|ANNUAL)"
        r"\b",
        name,
    )

    if match:
        year = match.group(1)
        code = match.group(2)

        suffix, date_suffix = PERIOD_MAP[code]

        return (
            f"{year}{suffix}",
            f"{year}{date_suffix}",
        )

    # Dosya adı farklıysa üst klasörleri de kontrol et.
    parts = [part.upper() for part in Path(filename).parts]

    for part in reversed(parts):
        match = re.search(
            r"(20\d{2})[_-]"
            r"(1C|2C|3C|4C|1Q|2Q|3Q|4Q|YILLIK|ANNUAL)"
            r"\b",
            part,
        )

        if match:
            year = match.group(1)
            code = match.group(2)
            suffix, date_suffix = PERIOD_MAP[code]

            return (
                f"{year}{suffix}",
                f"{year}{date_suffix}",
            )

        # Örn. klasör: 2026 / 2C
        if re.fullmatch(r"20\d{2}", part):
            year = part

            continue

    # 2026/2C klasör yapısı.
    parts = [part.upper() for part in Path(filename).parts]

    for index, part in enumerate(parts):
        if not re.fullmatch(r"20\d{2}", part):
            continue

        year = part

        if index + 1 < len(parts):
            code = parts[index + 1]

            if code in PERIOD_MAP:
                suffix, date_suffix = PERIOD_MAP[code]

                return (
                    f"{year}{suffix}",
                    f"{year}{date_suffix}",
                )

    raise ValueError(
        f"Dönem dosya adından/klasöründen bulunamadı: {filename}"
    )


# ============================================================
# SATIR BULMA
# ============================================================

def clean_lines(text):
    text = normalize_text(text)

    return [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]


def label_matches(line, labels):
    upper_line = normalize_text(line).upper()

    for label in labels:
        label_upper = normalize_text(label).upper()

        if label_upper in upper_line:
            return True

    return False


def values_after_label(line, labels):
    """
    Etiketten sonra gelen sayıları döndürür.

    Örnek:
        Hasılat 14 88.494.252 70.956.004 51.782.243 39.038.714

    sonuç:
        [88494252, 70956004, 51782243, 39038714]
    """
    upper_line = normalize_text(line).upper()

    selected_label = None

    for label in labels:
        label_upper = normalize_text(label).upper()

        if label_upper in upper_line:
            selected_label = label_upper
            break

    if selected_label is None:
        return []

    position = upper_line.find(selected_label)

    remainder = line[position + len(selected_label):]

    values = extract_numbers(remainder)

    return remove_note_number(values)


def find_exact_row_value(text, labels):
    """
    Finansal tablodaki aynı satırdan ilk cari dönem değerini alır.

    KRİTİK:
    lookahead ile rastgele sonraki satırdan değer alınmaz.
    Bu, eski importer'ın yanlış veri üretmesinin ana nedenlerinden biriydi.
    """
    lines = clean_lines(text)

    for line in lines:
        if not label_matches(line, labels):
            continue

        values = values_after_label(line, labels)

        if values:
            return values[0]

    return None


def find_line_values(text, labels):
    """
    Aynı satırdaki bütün finansal dönem değerlerini döndürür.
    """
    lines = clean_lines(text)

    for line in lines:
        if not label_matches(line, labels):
            continue

        values = values_after_label(line, labels)

        if values:
            return values

    return []


def find_first_matching_line(text, labels):
    lines = clean_lines(text)

    for line in lines:
        if label_matches(line, labels):
            return line

    return None


# ============================================================
# FİNANSAL KALEMLER
# ============================================================

def find_revenue(text):
    return find_exact_row_value(
        text,
        [
            "HASILAT",
            "SATIŞ GELİRLERİ",
            "SATIŞLAR",
            "SATIŞ HASILATI",
        ],
    )


def find_net_profit(text):
    """
    Net kâr satırını bulur.

    Öncelik:
      1) Net Dönem Kârı/Zararı
      2) Sürdürülen Faaliyetler Dönem Kârı/Zararı
      3) Dönem Kârı/Zararı

    Vergi yükümlülüğü gibi alt satırlara düşmemesi için
    'startswith' yaklaşımı kullanılır.
    """
    lines = clean_lines(text)

    targets = [
        "NET DÖNEM KARI VEYA ZARARI",
        "NET DÖNEM KÂRI VEYA ZARARI",
        "NET DÖNEM KARI",
        "NET DÖNEM KÂRI",
        "SÜRDÜRÜLEN FAALİYETLER DÖNEM KARI (ZARARI)",
        "SÜRDÜRÜLEN FAALİYETLER DÖNEM KÂRI (ZARARI)",
        "SÜRDÜRÜLEN FAALİYETLER DÖNEM KARI",
        "SÜRDÜRÜLEN FAALİYETLER DÖNEM KÂRI",
        "DÖNEM KARI (ZARARI)",
        "DÖNEM KÂRI (ZARARI)",
    ]

    for target in targets:
        target = target.upper()

        for line in lines:
            upper = line.upper().strip()

            if not upper.startswith(target):
                continue

            values = values_after_label(line, [target])

            if values:
                return values[0]

    return None


def find_cash(text):
    return find_exact_row_value(
        text,
        [
            "NAKİT VE NAKİT BENZERLERİ",
        ],
    )


def find_trade_receivables(text):
    return find_exact_row_value(
        text,
        [
            "TİCARİ ALACAKLAR",
        ],
    )


def find_inventory(text):
    return find_exact_row_value(
        text,
        [
            "STOKLAR",
        ],
    )


def find_current_assets(text):
    lines = clean_lines(text)

    targets = [
        "TOPLAM DÖNEN VARLIKLAR",
        "DÖNEN VARLIKLAR",
    ]

    for target in targets:
        target = target.upper()

        for line in lines:
            upper = line.upper().strip()
            if not upper.startswith(target):
                continue

            values = values_after_label(line, [target])
            if values:
                return values[0]

    return None


def find_current_liabilities(text):
    lines = clean_lines(text)

    targets = [
        "TOPLAM KISA VADELİ YÜKÜMLÜLÜKLER",
        "KISA VADELİ YÜKÜMLÜLÜKLER",
    ]

    for target in targets:
        target = target.upper()

        for line in lines:
            upper = line.upper().strip()
            if not upper.startswith(target):
                continue

            values = values_after_label(line, [target])
            if values:
                return values[0]

    return None


def find_total_assets(text):
    lines = clean_lines(text)

    targets = [
        "TOPLAM VARLIKLAR",
        "TOPLAM VARLIKLAR TOPLAMI",
    ]

    for target in targets:
        target = target.upper()

        for line in lines:
            upper = line.upper().strip()

            if not upper.startswith(target):
                continue

            values = values_after_label(line, [target])

            if values:
                return values[0]

    return None


def find_equity(text):
    """
    Özkaynak için yalnızca gerçek toplam/ana ortaklık satırlarını
    kabul eder. Genel 'Özkaynak' substring araması yapılmaz.

    Bu özellikle THYAO gibi raporlarda:
        Özkaynak Yöntemiyle Değerlenen Yatırımlar
    satırının yanlışlıkla özkaynak kabul edilmesini engeller.
    """
    lines = clean_lines(text)

    preferred = [
        "TOPLAM ÖZKAYNAKLAR",
        "ANA ORTAKLIĞA AİT ÖZKAYNAKLAR",
        "ANA ORTAKLIĞA AİT ÖZKAYNAK",
    ]

    for target in preferred:
        target = target.upper()

        for line in lines:
            upper = line.upper().strip()

            if not upper.startswith(target):
                continue

            values = values_after_label(line, [target])

            if values:
                return values[0]

    return None


def find_cost_of_sales(text):
    return find_exact_row_value(
        text,
        [
            "SATIŞLARIN MALİYETİ",
        ],
    )


def find_operating_profit(text):
    return find_exact_row_value(
        text,
        [
            "ESAS FAALİYET KARI (ZARARI)",
            "ESAS FAALİYET KÂRI (ZARARI)",
            "ESAS FAALİYET KARI",
            "ESAS FAALİYET KÂRI",
            "FAALİYET KARI (ZARARI)",
            "FAALİYET KÂRI (ZARARI)",
        ],
    )


def find_interest_expense(text):
    return find_exact_row_value(
        text,
        [
            "FİNANSMAN GİDERLERİ",
            "FİNANSMAN GİDERİ",
        ],
    )


def find_operating_cash_flow(text):
    """
    Toplam işletme faaliyetlerinden nakit akışını alır.

    ÖNEMLİ:
    "Faaliyetlerden Elde Edilen Nakit Akışları" ara toplamı ile
    "İŞLETME FAALİYETLERİNDEN NAKİT AKIŞLARI" toplamını karıştırmaz.
    """
    value = find_exact_row_value(
        text,
        [
            "İŞLETME FAALİYETLERİNDEN NAKİT AKIŞLARI",
        ],
    )

    if value is not None:
        return value

    return find_exact_row_value(
        text,
        [
            "İŞLETME FAALİYETLERİNDEN SAĞLANAN NAKİT AKIŞLARI",
        ],
    )


def find_short_debt(text):
    return find_exact_row_value(
        text,
        [
            "KISA VADELİ BORÇLANMALAR",
            "KISA VADELİ FİNANSAL BORÇLAR",
        ],
    )


def find_current_long_debt(text):
    return find_exact_row_value(
        text,
        [
            "UZUN VADELİ BORÇLANMALARIN KISA VADELİ KISIMLARI",
            "UZUN VADELİ BORÇLANMALARIN KISA VADELİ KISMI",
        ],
    )


def find_long_debt(text):
    lines = clean_lines(text)

    for line in lines:
        upper = line.upper().strip()

        # Kısa vadeli kısım satırını kesinlikle alma.
        if "KISA VADELİ" in upper:
            continue

        if not upper.startswith("UZUN VADELİ BORÇLANMALAR"):
            continue

        values = values_after_label(
            line,
            [
                "UZUN VADELİ BORÇLANMALAR",
            ],
        )

        if values:
            return values[0]

    return None


# ============================================================
# BİLANÇO / TABLO DOĞRULAMA
# ============================================================

def extract_financial_values(text):
    return {
        "revenue": find_revenue(text),
        "net_profit": find_net_profit(text),
        "cash": find_cash(text),
        "trade_receivables": find_trade_receivables(text),
        "inventory": find_inventory(text),
        "current_assets": find_current_assets(text),
        "current_liabilities": find_current_liabilities(text),
        "total_assets": find_total_assets(text),
        "equity": find_equity(text),
        "cost_of_sales": find_cost_of_sales(text),
        "operating_profit": find_operating_profit(text),
        "interest_expense": find_interest_expense(text),
        "operating_cash_flow": find_operating_cash_flow(text),
        "short_term_financial_debt": find_short_debt(text),
        "current_portion_long_term_debt": find_current_long_debt(text),
        "long_term_financial_debt": find_long_debt(text),
    }


def validate_financial_values(values):
    """
    Parser'ın yanlış veri üretmesini engelleyen hafif doğrulama.

    KAP şirketleri arasında tablo başlıkları farklılaşabildiği için
    bütün temel kalemlerin bulunmasını şart koşmuyoruz.
    Ancak tamamen boş/bozuk raporu da kabul etmiyoruz.
    """
    groups = [
        ("revenue", "net_profit"),
        ("current_assets", "current_liabilities"),
        ("total_assets", "equity"),
    ]

    found_group = any(
        any(values.get(key) is not None for key in group)
        for group in groups
    )

    if not found_group:
        return False, "Finansal tablo kalemleri bulunamadı."

    total_assets = values.get("total_assets")
    equity = values.get("equity")

    if total_assets is not None and total_assets <= 0:
        return False, "Toplam varlıklar pozitif olmalı."

    # Negatif özkaynak mümkündür; yalnızca aşırı açık parser
    # bozulmasını kontrol ediyoruz.
    if (
        equity is not None
        and total_assets is not None
        and abs(equity) > abs(total_assets) * 20
    ):
        return False, "Özkaynak / toplam varlık oranı anormal."

    return True, ""


def import_financial_file(file_path):
    file_path = Path(file_path)

    result = {
        "success": False,
        "file": file_path.name,
        "symbol": None,
        "period": None,
        "period_end": None,
        "action": None,
        "values": {},
        "error": None,
    }

    if not file_path.exists():
        result["error"] = f"Dosya bulunamadı: {file_path}"
        print(f"❌ {result['error']}")
        return result

    if file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        result["error"] = (
            f"Desteklenmeyen dosya türü: {file_path.suffix}"
        )
        print(f"❌ {result['error']}")
        return result

    print("\n" + "=" * 80)
    print(f"İŞLENİYOR: {file_path}")
    print("=" * 80)

    try:
        text = read_file(file_path)

        if not text.strip():
            raise ValueError("Dosyadan metin çıkarılamadı.")

        symbol = detect_symbol_from_filename(file_path)
        period, period_end = detect_period_from_filename(file_path)

        multiplier, unit = detect_unit_multiplier(text)

        raw_values = extract_financial_values(text)

        # KAP raporundaki tutarlar birim bazında verilir.
        # DB'ye gerçek TL kaydet.
        values = {}

        for key, value in raw_values.items():
            if value is None:
                values[key] = None
            else:
                values[key] = value * multiplier

        valid, reason = validate_financial_values(values)

        if not valid:
            raise ValueError(reason)

        result.update(
            {
                "symbol": symbol,
                "period": period,
                "period_end": period_end,
                "values": values,
                "unit": unit,
                "multiplier": multiplier,
            }
        )

        print(f"Hisse      : {symbol}")
        print(f"Dönem      : {period}")
        print(f"Dönem Sonu : {period_end}")
        print(f"Kaynak birim: {unit}")
        print(f"TL çarpanı : {multiplier:,}")
        print(
            f"Bulunan finansal kalem: "
            f"{sum(v is not None for v in values.values())}"
            f"/{len(values)}"
        )

        ensure_database_schema()

        conn = get_connection()

        try:
            existing = conn.execute(
                """
                SELECT id
                FROM financial_statements
                WHERE UPPER(TRIM(symbol)) = ?
                  AND period_end = ?
                LIMIT 1
                """,
                (
                    symbol.upper().strip(),
                    period_end,
                ),
            ).fetchone()

            source_date = datetime.fromtimestamp(
                file_path.stat().st_mtime
            ).strftime("%Y-%m-%d")

            params = (
                period,
                "Konsolide",
                "TRY",
                values["revenue"],
                values["net_profit"],
                values["cash"],
                values["trade_receivables"],
                values["inventory"],
                values["current_assets"],
                values["current_liabilities"],
                values["total_assets"],
                values["equity"],
                values["cost_of_sales"],
                values["operating_profit"],
                values["interest_expense"],
                values["operating_cash_flow"],
                values["short_term_financial_debt"],
                values["current_portion_long_term_debt"],
                values["long_term_financial_debt"],
                "KAP",
                source_date,
            )

            if existing:
                conn.execute(
                    """
                    UPDATE financial_statements
                    SET
                        period = ?,
                        report_type = ?,
                        currency = ?,
                        revenue = ?,
                        net_profit = ?,
                        cash = ?,
                        trade_receivables = ?,
                        inventory = ?,
                        current_assets = ?,
                        current_liabilities = ?,
                        total_assets = ?,
                        equity = ?,
                        cost_of_sales = ?,
                        operating_profit = ?,
                        interest_expense = ?,
                        operating_cash_flow = ?,
                        short_term_financial_debt = ?,
                        current_portion_long_term_debt = ?,
                        long_term_financial_debt = ?,
                        source = ?,
                        source_date = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    params + (existing[0],),
                )

                action = "GÜNCELLENDİ"

            else:
                conn.execute(
                    """
                    INSERT INTO financial_statements (
                        symbol,
                        period,
                        period_end,
                        report_type,
                        currency,
                        revenue,
                        net_profit,
                        cash,
                        trade_receivables,
                        inventory,
                        current_assets,
                        current_liabilities,
                        total_assets,
                        equity,
                        cost_of_sales,
                        operating_profit,
                        interest_expense,
                        operating_cash_flow,
                        short_term_financial_debt,
                        current_portion_long_term_debt,
                        long_term_financial_debt,
                        source,
                        source_date,
                        updated_at
                    )
                    VALUES (
                        ?, ?, ?,
                        ?, ?,
                        ?, ?,
                        ?, ?, ?,
                        ?, ?,
                        ?, ?,
                        ?, ?, ?,
                        ?,
                        ?, ?, ?,
                        ?, ?,
                        CURRENT_TIMESTAMP
                    )
                    """,
                    (
                        symbol,
                        period,
                        period_end,
                    ) + params[:-1],
                )

                action = "EKLENDİ"

            conn.commit()

        except Exception:
            conn.rollback()
            raise

        finally:
            conn.close()

        result["success"] = True
        result["action"] = action

        print(f"✅ {action}: {symbol} / {period}")

        for key, value in values.items():
            print(f"   {key:<35}: {value}")

        print("=" * 80)

        return result

    except Exception as error:
        result["error"] = (
            f"{type(error).__name__}: {error}"
        )

        print(f"❌ HATA: {result['error']}")
        print("=" * 80)

        return result


# ============================================================
# DOSYA BULMA
# ============================================================

def find_report_files():
    """
    data/financial_reports altındaki tüm PDF/TXT dosyalarını recursive bulur.

    Aynı raporun:
        asels_2026_2c.pdf
        asels_2026_2c.txt

    ikisi de varsa yalnızca TXT seçilir.
    """
    if not REPORTS_DIR.exists():
        return []

    candidates = [
        path
        for path in REPORTS_DIR.rglob("*")
        if path.is_file()
        and path.suffix.lower() in SUPPORTED_EXTENSIONS
    ]

    grouped = {}

    for path in candidates:
        key = str(path.with_suffix("")).lower()
        grouped.setdefault(key, []).append(path)

    selected = []

    for paths in grouped.values():
        txt_files = [
            path
            for path in paths
            if path.suffix.lower() == ".txt"
        ]

        if txt_files:
            selected.append(sorted(txt_files)[0])
        else:
            selected.append(sorted(paths)[0])

    return sorted(
        selected,
        key=lambda path: str(path).lower(),
    )


# ============================================================
# TÜM RAPORLARI AKTAR
# ============================================================

def import_all_financial_reports():
    """
    Tüm KAP raporlarını aktarır.

    HER ZAMAN dict döndürür.
    """
    result = {
        "success": False,
        "partial_success": False,
        "total": 0,
        "processed": 0,
        "failed": 0,
        "errors": [],
        "files": [],
        "reports_dir": str(REPORTS_DIR),
        "db_path": str(DB_PATH),
    }

    print("\n" + "=" * 80)
    print("BIST AI PRO — KAP FİNANSAL RAPOR IMPORTER")
    print("=" * 80)
    print(f"Proje      : {BASE_DIR}")
    print(f"Veritabanı : {DB_PATH}")
    print(f"Rapor yolu : {REPORTS_DIR}")
    print("=" * 80)

    try:
        ensure_database_schema()
    except Exception as error:
        result["errors"].append(
            f"Veritabanı hazırlanamadı: "
            f"{type(error).__name__}: {error}"
        )
        return result

    if not REPORTS_DIR.exists():
        result["errors"].append(
            f"Rapor klasörü bulunamadı: {REPORTS_DIR}"
        )
        return result

    report_files = find_report_files()
    result["total"] = len(report_files)

    if not report_files:
        result["errors"].append(
            f"Rapor bulunamadı: {REPORTS_DIR}"
        )
        return result

    print(f"Bulunan rapor sayısı: {len(report_files)}")

    for report_file in report_files:
        file_result = import_financial_file(report_file)

        result["files"].append(file_result)

        if file_result.get("success"):
            result["processed"] += 1
        else:
            result["failed"] += 1

            result["errors"].append(
                f"{report_file.name}: "
                f"{file_result.get('error', 'Bilinmeyen hata')}"
            )

    result["success"] = (
        result["processed"] > 0
        and result["failed"] == 0
    )

    result["partial_success"] = (
        result["processed"] > 0
        and result["failed"] > 0
    )

    print("\n" + "=" * 80)
    print("AKTARIM TAMAMLANDI")
    print(f"Toplam   : {result['total']}")
    print(f"Başarılı : {result['processed']}")
    print(f"Hatalı   : {result['failed']}")
    print("=" * 80)

    return result


# ============================================================
# TEK RAPOR TESTİ
# ============================================================

def test_report(file_path):
    """
    Veritabanına yazmadan parser testi yapmak için yardımcı fonksiyon.
    """
    file_path = Path(file_path)

    text = read_file(file_path)

    symbol = detect_symbol_from_filename(file_path)
    period, period_end = detect_period_from_filename(file_path)

    multiplier, unit = detect_unit_multiplier(text)

    raw_values = extract_financial_values(text)

    values = {
        key: (
            None
            if value is None
            else value * multiplier
        )
        for key, value in raw_values.items()
    }

    return {
        "symbol": symbol,
        "period": period,
        "period_end": period_end,
        "unit": unit,
        "multiplier": multiplier,
        "values": values,
    }


# ============================================================
# KOMUT SATIRI
# ============================================================

if __name__ == "__main__":
    result = import_all_financial_reports()

    print("\nSONUÇ:")
    print(result)
