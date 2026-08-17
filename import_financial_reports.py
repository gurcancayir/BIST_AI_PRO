import re
import sqlite3
from datetime import datetime
from pathlib import Path


# ==========================================================
# AYARLAR
# ==========================================================

BASE_DIR = Path(__file__).resolve().parent

DB_PATH = BASE_DIR / "borsa.db"

ROOT = (
    BASE_DIR
    / "data"
    / "financial_reports"
)


# ==========================================================
# TÜRKÇE METİN NORMALİZASYONU
# ==========================================================

def normalize_text(text):

    if text is None:
        return ""

    text = str(text).upper()

    replacements = {
        "Ã‡": "C",
        "Äž": "G",
        "Ä°": "I",
        "Ã–": "O",
        "Åž": "S",
        "Ãœ": "U",
        "Ã‚": "A",
        "Ä±": "I",
        "ÄŸ": "G",
        "Ã§": "C",
        "Ã¶": "O",
        "ÅŸ": "S",
        "Ã¼": "U",
        "â‚¬": "EUR",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    replacements_tr = {
        "Ç": "C",
        "Ğ": "G",
        "İ": "I",
        "Ö": "O",
        "Ş": "S",
        "Ü": "U",
        "Â": "A",
        "ı": "I",
        "ğ": "G",
        "ç": "C",
        "ö": "O",
        "ş": "S",
        "ü": "U",
    }

    for old, new in replacements_tr.items():
        text = text.replace(old, new)

    text = re.sub(r"\s+", " ", text)

    return text.strip()


# ==========================================================
# TÜRKÇE SAYIYI FLOAT'A ÇEVİR
# ==========================================================

def tr_number(value):

    if value is None:
        return None

    value = str(value).strip()

    if not value:
        return None

    value = value.replace(" ", "")
    value = value.replace("\xa0", "")

    negative = False

    if value.startswith("(") and value.endswith(")"):
        negative = True
        value = value[1:-1]

    if value.startswith("-"):
        negative = True
        value = value[1:]

    # Türkçe sayı formatı:
    # 1.234.567,89
    value = value.replace(".", "")
    value = value.replace(",", ".")

    try:

        number = float(value)

        if negative:
            number = -number

        return number

    except (ValueError, TypeError):

        return None


# ==========================================================
# SAYI SATIRI
# ==========================================================

def is_number_line(line):

    line = str(line).strip()

    if not line:
        return False

    return bool(
        re.fullmatch(
            r"-?\(?\d[\d\.,]*\)?",
            line
        )
    )


# ==========================================================
# OLASI DİPNOT NUMARASI
# ==========================================================

def is_probable_note_number(value):

    if value is None:
        return False

    try:

        if value != int(value):
            return False

        value = int(value)

    except Exception:

        return False

    return 0 < value <= 99


# ==========================================================
# FİNANSAL SAYI SATIRI
# ==========================================================

def is_financial_number_line(line):

    if not is_number_line(line):
        return False

    value = tr_number(line)

    if value is None:
        return False

    if value == 0:
        return True

    if is_probable_note_number(value):
        return False

    return True


# ==========================================================
# SEMBOL BUL
# ==========================================================

def get_symbol(path):

    name = Path(path).stem.upper()

    match = re.match(
        r"([A-Z0-9]+)_\d{4}",
        name
    )

    if match:
        return match.group(1)

    return None


# ==========================================================
# DÖNEM BUL
# ==========================================================

def get_period(path):

    name = Path(path).stem.upper()

    # ------------------------------------------------------
    # 1. Çeyrek
    # ------------------------------------------------------

    match = re.search(
        r"_(\d{4})_1C",
        name
    )

    if match:

        year = int(match.group(1))

        return (
            f"{year}_1Q",
            f"{year}-03-31"
        )

    # ------------------------------------------------------
    # 2. Çeyrek
    # ------------------------------------------------------

    match = re.search(
        r"_(\d{4})_2C",
        name
    )

    if match:

        year = int(match.group(1))

        return (
            f"{year}_2Q",
            f"{year}-06-30"
        )

    # ------------------------------------------------------
    # 3. Çeyrek
    # ------------------------------------------------------

    match = re.search(
        r"_(\d{4})_3C",
        name
    )

    if match:

        year = int(match.group(1))

        return (
            f"{year}_3Q",
            f"{year}-09-30"
        )

    # ------------------------------------------------------
    # Yıllık
    # ------------------------------------------------------

    match = re.search(
        r"_(\d{4})_YILLIK",
        name
    )

    if match:

        year = int(match.group(1))

        return (
            f"{year}_YILLIK",
            f"{year}-12-31"
        )

    return None, None


# ==========================================================
# SATIR TEMİZLE
# ==========================================================

def clean_line(line):

    if line is None:
        return ""

    return " ".join(
        str(line).split()
    ).strip()


# ==========================================================
# FİNANSAL KALEM LİSTESİ
# ==========================================================

FIELD_PATTERNS = {

    # ------------------------------------------------------
    # GELİR TABLOSU
    # ------------------------------------------------------

    "revenue": [

        "HASILAT",

        "SATIŞ GELİRLERİ",
        "SATIS GELIRLERI",

        "SATIŞ GELİRLERİ (HASILAT)",
        "SATIS GELIRLERI (HASILAT)",

        "HASILAT GELİRLERİ",
        "HASILAT GELIRLERI",
    ],

    "cost_of_sales": [

        "SATIŞLARIN MALİYETİ",
        "SATISLARIN MALIYETI",

        "SATILAN MALIN MALİYETİ",
        "SATILAN MALIN MALIYETI",
    ],

    "operating_profit": [

        "ESAS FAALİYET KARI (ZARARI)",
        "ESAS FAALİYET KÂRI (ZARARI)",

        "ESAS FAALIYET KARI (ZARARI)",
        "ESAS FAALIYET KÂRI (ZARARI)",

        "ESAS FAALİYET KARI",
        "ESAS FAALİYET KÂRI",

        "ESAS FAALIYET KARI",
        "ESAS FAALIYET KÂRI",

        "FAALİYET KARI",
        "FAALIYET KARI",
    ],

    "net_profit": [

        "DÖNEM KARI (ZARARI)",
        "DÖNEM KÂRI (ZARARI)",

        "DÖNEM KARI",
        "DÖNEM KÂRI",

        "NET DÖNEM KARI",
        "NET DÖNEM KÂRI",

        "ANA ORTAKLIK PAYLARI",
    ],

    # ------------------------------------------------------
    # EBITDA
    # ------------------------------------------------------

    "ebitda": [

        "FAVÖK",

        "FAVOK",

        "EBITDA",

        "FAIZ AMORTISMAN VE VERGI ONCESI KAR",

        "FAİZ AMORTİSMAN VE VERGİ ÖNCESİ KAR",

        "FAİZ AMORTİSMAN VE VERGİ ÖNCESİ KARI",

        "FAIZ AMORTISMAN VE VERGI ONCESI KARI",
    ],

    # ------------------------------------------------------
    # AMORTİSMAN
    # ------------------------------------------------------

    "depreciation_amortization": [

        "AMORTİSMAN GİDERLERİ",

        "AMORTISMAN GIDERLERI",

        "İTFA PAYLARI",

        "ITFA PAYLARI",

        "AMORTİSMAN VE İTFA PAYLARI",

        "AMORTISMAN VE ITFA PAYLARI",

        "AMORTİSMAN GİDERİ",

        "AMORTISMAN GIDERI",
    ],

    # ------------------------------------------------------
    # FAİZ GİDERİ
    # ------------------------------------------------------

    "interest_expense": [

        "FAİZ GİDERLERİ",

        "FAIZ GIDERLERI",

        "FİNANSMAN GİDERLERİ",

        "FINANSMAN GIDERLERI",

        "FİNANSMAN GİDERLERİ (GELİRLERİ)",

        "FINANSMAN GIDERLERI (GELIRLERI)",

        "FİNANSMAN GİDERLERİ - NET",

        "FINANSMAN GIDERLERI - NET",
    ],

    # ------------------------------------------------------
    # BİLANÇO
    # ------------------------------------------------------

    "cash": [

        "NAKİT VE NAKİT BENZERLERİ",

        "NAKIT VE NAKIT BENZERLERI",
    ],

    "current_portion_long_term_debt": [

        "UZUN VADELİ BORÇLANMALARIN KISA VADELİ KISIMLARI",

        "UZUN VADELI BORCLANMALARIN KISA VADELI KISIMLARI",

        "UZUN VADELİ BORÇLANMALARIN KISA VADELİ KISMI",

        "UZUN VADELI BORCLANMALARIN KISA VADELI KISMI",
    ],

    "short_term_financial_debt": [

        "KISA VADELİ BORÇLANMALAR",

        "KISA VADELI BORCLANMALAR",

        "KISA VADELİ FİNANSAL BORÇLAR",

        "KISA VADELI FINANSAL BORCLAR",
    ],

    "long_term_financial_debt": [

        "UZUN VADELİ BORÇLANMALAR",

        "UZUN VADELI BORCLANMALAR",

        "UZUN VADELİ FİNANSAL BORÇLAR",

        "UZUN VADELI FINANSAL BORCLAR",
    ],

    "trade_receivables": [

        "TİCARİ ALACAKLAR",

        "TICARI ALACAKLAR",
    ],

    "inventory": [

        "STOKLAR",
    ],

    "current_assets": [

        "TOPLAM DÖNEN VARLIKLAR",

        "TOPLAM DONEN VARLIKLAR",
    ],

    "current_liabilities": [

        "TOPLAM KISA VADELİ YÜKÜMLÜLÜKLER",

        "TOPLAM KISA VADELI YUKUMLULUKLER",

        "KISA VADELİ YÜKÜMLÜLÜKLER",

        "KISA VADELI YUKUMLULUKLER",
    ],

    "total_assets": [

        "TOPLAM VARLIKLAR",
    ],

    "equity": [

        "TOPLAM ÖZKAYNAKLAR",

        "TOPLAM OZKAYNAKLAR",

        "ÖZKAYNAKLAR",

        "OZKAYNAKLAR",
    ],

    # ------------------------------------------------------
    # NAKİT AKIŞ
    # ------------------------------------------------------

    "operating_cash_flow": [

        "İŞLETME FAALİYETLERİNDEN NAKİT AKIŞLARI",

        "ISLETME FAALIYETLERINDEN NAKIT AKISLARI",

        "FAALİYETLERDEN NAKİT AKIŞLARI",

        "FAALIYETLERDEN NAKIT AKISLARI",

        "İŞLETME FAALİYETLERİNDEN SAĞLANAN NAKİT",

        "ISLETME FAALIYETLERINDEN SAGLANAN NAKIT",
    ],
}


# ==========================================================
# ALAN BUL
# ==========================================================

def match_field(item_name):

    normalized = normalize_text(item_name)

    if not normalized:
        return None

    ordered_fields = sorted(
        FIELD_PATTERNS.items(),
        key=lambda x: max(
            len(normalize_text(p))
            for p in x[1]
        ),
        reverse=True
    )

    for field, patterns in ordered_fields:

        for pattern in patterns:

            normalized_pattern = normalize_text(
                pattern
            )

            if normalized == normalized_pattern:
                return field

            if normalized.startswith(
                normalized_pattern + " "
            ):
                return field

            if normalized_pattern in normalized:
                return field

    return None


# ==========================================================
# SATIR İÇİNDEKİ SAYILARI BUL
# ==========================================================

def extract_numbers_from_line(line):

    line = clean_line(line)

    if not line:
        return []

    pattern = (
        r"(?<![A-ZÇĞİÖŞÜ])"
        r"-?"
        r"\(?"
        r"\d"
        r"[\d\.,]*"
        r"\)?"
    )

    matches = re.findall(
        pattern,
        line,
        flags=re.IGNORECASE
    )

    values = []

    for match in matches:

        value = tr_number(match)

        if value is not None:
            values.append(value)

    return values


# ==========================================================
# AYNI SATIRDAKİ FİNANSAL DEĞERLERİ BUL
# ==========================================================

def extract_inline_values(line, field):

    normalized = normalize_text(line)

    patterns = FIELD_PATTERNS.get(
        field,
        []
    )

    patterns = sorted(
        patterns,
        key=lambda p: len(
            normalize_text(p)
        ),
        reverse=True
    )

    matched_pattern = None

    for pattern in patterns:

        p = normalize_text(pattern)

        if normalized == p:

            matched_pattern = p
            break

        if normalized.startswith(
            p + " "
        ):

            matched_pattern = p
            break

        if p in normalized:

            matched_pattern = p
            break

    if not matched_pattern:

        return None, None

    pos = normalized.find(
        matched_pattern
    )

    remainder = normalized[
        pos + len(matched_pattern):
    ]

    numbers = extract_numbers_from_line(
        remainder
    )

    if len(numbers) < 2:
        return None, None

    # Finansal tablolarda genellikle:
    #
    # Cari dönem | Önceki dönem
    #
    # olduğu için son iki değeri alıyoruz.

    current = numbers[-2]
    previous = numbers[-1]

    return current, previous


# ==========================================================
# SONRAKİ SAYI SATIRLARINI BUL
# ==========================================================

def collect_following_numbers(
    lines,
    start_index,
    max_count=8
):

    numbers = []

    i = start_index + 1

    while (
        i < len(lines)
        and len(numbers) < max_count
    ):

        line = clean_line(
            lines[i]
        )

        if not line:

            i += 1
            continue

        # Yeni finansal kaleme geldiysek dur.
        if match_field(line):

            break

        if not is_number_line(line):

            break

        number = tr_number(line)

        if number is not None:

            numbers.append(number)

        i += 1

    return numbers


# ==========================================================
# CARİ / ÖNCEKİ DÖNEM
# ==========================================================

def find_current_previous(numbers):

    if len(numbers) < 2:
        return None, None

    return (
        numbers[-2],
        numbers[-1]
    )


# ==========================================================
# RAPOR PARSER
# ==========================================================

def parse_report(text):

    result = {}

    # ------------------------------------------------------
    # Satırları hazırla
    # ------------------------------------------------------

    lines = [
        clean_line(line)
        for line in text.splitlines()
    ]

    # ------------------------------------------------------
    # Her satırı dolaş
    # ------------------------------------------------------

    for i, line in enumerate(lines):

        if not line:
            continue

        field = match_field(line)

        if not field:
            continue

        # Aynı alanı ikinci kez alma.
        if field in result:
            continue

        # ==================================================
        # YÖNTEM 1
        # AYNI SATIRDA DEĞERLER
        # ==================================================

        current, previous = extract_inline_values(
            line,
            field
        )

        if current is not None:

            result[field] = {
                "current": current,
                "previous": previous,
                "item_name": line,
            }

            continue

        # ==================================================
        # YÖNTEM 2
        # DEĞERLER SONRAKİ SATIRLARDA
        # ==================================================

        numbers = collect_following_numbers(
            lines,
            i,
            max_count=8
        )

        if len(numbers) < 2:
            continue

        current, previous = find_current_previous(
            numbers
        )

        if current is None:
            continue

        result[field] = {
            "current": current,
            "previous": previous,
            "item_name": line,
        }

    return result


# ==========================================================
# FINANCIAL_REPORTS TABLOSUNU OLUŞTUR
# ==========================================================

def ensure_financial_reports_table(conn):

    conn.execute("""
        CREATE TABLE IF NOT EXISTS financial_reports (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            symbol TEXT NOT NULL,

            period TEXT NOT NULL,

            period_end TEXT NOT NULL,

            report_type TEXT,

            currency TEXT DEFAULT 'TRY',

            revenue REAL,

            cost_of_sales REAL,

            operating_profit REAL,

            depreciation_amortization REAL,

            ebitda REAL,

            net_profit REAL,

            interest_expense REAL,

            cash REAL,

            short_term_financial_debt REAL,

            current_portion_long_term_debt REAL,

            long_term_financial_debt REAL,

            trade_receivables REAL,

            inventory REAL,

            current_assets REAL,

            current_liabilities REAL,

            total_assets REAL,

            equity REAL,

            operating_cash_flow REAL,

            source TEXT DEFAULT 'KAP',

            source_date TEXT,

            created_at TEXT DEFAULT CURRENT_TIMESTAMP,

            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS
        ux_financial_reports_symbol_period

        ON financial_reports(
            symbol,
            period
        )
    """)

    conn.commit()


# ==========================================================
# VERİTABANINA KAYDET
# ==========================================================

def save_report(
    conn,
    symbol,
    period,
    period_end,
    data,
    document_name
):

    ensure_financial_reports_table(conn)

    # ------------------------------------------------------
    # Alanlar
    # ------------------------------------------------------

    columns = [

        "revenue",

        "cost_of_sales",

        "operating_profit",

        "depreciation_amortization",

        "ebitda",

        "net_profit",

        "interest_expense",

        "cash",

        "short_term_financial_debt",

        "current_portion_long_term_debt",

        "long_term_financial_debt",

        "trade_receivables",

        "inventory",

        "current_assets",

        "current_liabilities",

        "total_assets",

        "equity",

        "operating_cash_flow",
    ]

    values = {
        column: None
        for column in columns
    }

    # ------------------------------------------------------
    # Parser sonuçlarını aktar
    # ------------------------------------------------------

    for field, info in data.items():

        if field in values:

            values[field] = info.get(
                "current"
            )

    now = datetime.now().isoformat()

    # ======================================================
    # YENİ SİSTEM
    #
    # financial_reports
    # ======================================================

    conn.execute(
        """
        INSERT INTO financial_reports
        (
            symbol,
            period,
            period_end,
            report_type,
            currency,

            revenue,
            cost_of_sales,
            operating_profit,

            depreciation_amortization,

            ebitda,

            net_profit,

            interest_expense,

            cash,

            short_term_financial_debt,

            current_portion_long_term_debt,

            long_term_financial_debt,

            trade_receivables,

            inventory,

            current_assets,

            current_liabilities,

            total_assets,

            equity,

            operating_cash_flow,

            source,

            source_date,

            updated_at
        )

        VALUES
        (
            ?, ?, ?, ?, ?,

            ?, ?, ?,

            ?,

            ?,

            ?,

            ?,

            ?,

            ?,

            ?,

            ?,

            ?,

            ?,

            ?,

            ?,

            ?,

            ?,

            ?,

            ?,

            ?,

            ?
        )

        ON CONFLICT(symbol, period)
        DO UPDATE SET

            period_end =
                excluded.period_end,

            report_type =
                excluded.report_type,

            currency =
                excluded.currency,

            revenue =
                excluded.revenue,

            cost_of_sales =
                excluded.cost_of_sales,

            operating_profit =
                excluded.operating_profit,

            depreciation_amortization =
                excluded.depreciation_amortization,

            ebitda =
                excluded.ebitda,

            net_profit =
                excluded.net_profit,

            interest_expense =
                excluded.interest_expense,

            cash =
                excluded.cash,

            short_term_financial_debt =
                excluded.short_term_financial_debt,

            current_portion_long_term_debt =
                excluded.current_portion_long_term_debt,

            long_term_financial_debt =
                excluded.long_term_financial_debt,

            trade_receivables =
                excluded.trade_receivables,

            inventory =
                excluded.inventory,

            current_assets =
                excluded.current_assets,

            current_liabilities =
                excluded.current_liabilities,

            total_assets =
                excluded.total_assets,

            equity =
                excluded.equity,

            operating_cash_flow =
                excluded.operating_cash_flow,

            source =
                excluded.source,

            source_date =
                excluded.source_date,

            updated_at =
                excluded.updated_at
        """,

        (

            symbol,

            period,

            period_end,

            "Konsolide",

            "TRY",

            values["revenue"],

            values["cost_of_sales"],

            values["operating_profit"],

            values["depreciation_amortization"],

            values["ebitda"],

            values["net_profit"],

            values["interest_expense"],

            values["cash"],

            values["short_term_financial_debt"],

            values["current_portion_long_term_debt"],

            values["long_term_financial_debt"],

            values["trade_receivables"],

            values["inventory"],

            values["current_assets"],

            values["current_liabilities"],

            values["total_assets"],

            values["equity"],

            values["operating_cash_flow"],

            "KAP",

            now,

            now,
        )
    )

    # ======================================================
    # ESKİ SİSTEM
    #
    # financial_statements
    #
    # Mevcut uygulamayı bozmamak için korunuyor.
    # ======================================================

    conn.execute(
        """
        INSERT INTO financial_statements
        (
            symbol,
            period,
            period_end,
            report_type,
            currency,

            revenue,
            cost_of_sales,
            operating_profit,
            net_profit,

            cash,

            short_term_financial_debt,

            current_portion_long_term_debt,

            long_term_financial_debt,

            trade_receivables,

            inventory,

            current_assets,

            current_liabilities,

            total_assets,

            equity,

            operating_cash_flow,

            source,

            source_date,

            updated_at
        )

        VALUES
        (
            ?, ?, ?, ?, ?,

            ?, ?, ?, ?,

            ?,

            ?,

            ?,

            ?,

            ?,

            ?,

            ?,

            ?,

            ?,

            ?,

            ?,

            ?,

            ?,

            ?
        )

        ON CONFLICT(symbol, period)
        DO UPDATE SET

            period_end =
                excluded.period_end,

            report_type =
                excluded.report_type,

            currency =
                excluded.currency,

            revenue =
                excluded.revenue,

            cost_of_sales =
                excluded.cost_of_sales,

            operating_profit =
                excluded.operating_profit,

            net_profit =
                excluded.net_profit,

            cash =
                excluded.cash,

            short_term_financial_debt =
                excluded.short_term_financial_debt,

            current_portion_long_term_debt =
                excluded.current_portion_long_term_debt,

            long_term_financial_debt =
                excluded.long_term_financial_debt,

            trade_receivables =
                excluded.trade_receivables,

            inventory =
                excluded.inventory,

            current_assets =
                excluded.current_assets,

            current_liabilities =
                excluded.current_liabilities,

            total_assets =
                excluded.total_assets,

            equity =
                excluded.equity,

            operating_cash_flow =
                excluded.operating_cash_flow,

            source =
                excluded.source,

            source_date =
                excluded.source_date,

            updated_at =
                excluded.updated_at
        """,

        (

            symbol,

            period,

            period_end,

            "Konsolide",

            "TRY",

            values["revenue"],

            values["cost_of_sales"],

            values["operating_profit"],

            values["net_profit"],

            values["cash"],

            values["short_term_financial_debt"],

            values["current_portion_long_term_debt"],

            values["long_term_financial_debt"],

            values["trade_receivables"],

            values["inventory"],

            values["current_assets"],

            values["current_liabilities"],

            values["total_assets"],

            values["equity"],

            values["operating_cash_flow"],

            "KAP",

            now,

            now,
        )
    )


# ==========================================================
# RAPORU TEK DOSYA OLARAK İŞLE
# ==========================================================

def import_financial_file(
    file_path,
    db_path=DB_PATH
):

    path = Path(file_path)

    print()
    print("=" * 70)
    print(
        f"RAPOR İŞLENİYOR: {path.name}"
    )
    print("=" * 70)

    if not path.exists():

        print(
            f"HATA: Dosya bulunamadı: {path}"
        )

        return False

    # ------------------------------------------------------
    # Sembol
    # ------------------------------------------------------

    symbol = get_symbol(path)

    if not symbol:

        print(
            "HATA: Sembol bulunamadı."
        )

        return False

    # ------------------------------------------------------
    # Dönem
    # ------------------------------------------------------

    period, period_end = get_period(
        path
    )

    if not period:

        print(
            "HATA: Dönem bulunamadı."
        )

        return False

    # ------------------------------------------------------
    # TXT oku
    # ------------------------------------------------------

    try:

        text = path.read_text(
            encoding="utf-8",
            errors="ignore"
        )

    except Exception as e:

        print(
            f"OKUMA HATASI: {e}"
        )

        return False

    # ------------------------------------------------------
    # Parser
    # ------------------------------------------------------

    data = parse_report(
        text
    )

    if not data:

        print(
            "UYARI: Finansal kalem bulunamadı."
        )

        return False

    # ------------------------------------------------------
    # DB
    # ------------------------------------------------------

    conn = sqlite3.connect(
        db_path
    )

    try:

        save_report(
            conn,
            symbol,
            period,
            period_end,
            data,
            path.name
        )

        conn.commit()

    except Exception as e:

        conn.rollback()

        print(
            f"VERİTABANI HATASI: {e}"
        )

        conn.close()

        return False

    conn.close()

    # ------------------------------------------------------
    # Sonuç
    # ------------------------------------------------------

    print()

    print(
        f"Sembol       : {symbol}"
    )

    print(
        f"Dönem        : {period}"
    )

    print(
        f"Tarih        : {period_end}"
    )

    print(
        f"Bulunan kalem: {len(data)}"
    )

    print()

    for field, info in data.items():

        current = info.get(
            "current"
        )

        previous = info.get(
            "previous"
        )

        if current is None:
            continue

        if previous is None:

            print(
                f"{field:<40}"
                f"{current:>18,.2f}"
                f" | "
                f"{'N/A':>18}"
            )

        else:

            print(
                f"{field:<40}"
                f"{current:>18,.2f}"
                f" | "
                f"{previous:>18,.2f}"
            )

    print()

    print(
        "OK - Rapor veritabanına kaydedildi."
    )

    return True


# ==========================================================
# TÜM TXT DOSYALARINI OTOMATİK İŞLE
# ==========================================================

def import_all_financial_reports():

    print()
    print("=" * 70)
    print("BIST AI PRO - KAP FİNANSAL RAPOR AKTARIMI")
    print("=" * 70)

    print()

    print(
        f"DB      : {DB_PATH}"
    )

    print(
        f"RAPORLAR: {ROOT}"
    )

    # ------------------------------------------------------
    # Klasör kontrol
    # ------------------------------------------------------

    if not ROOT.exists():

        print()

        print(
            "HATA: financial_reports klasörü bulunamadı."
        )

        return

    # ------------------------------------------------------
    # TXT dosyaları
    # ------------------------------------------------------

    files = sorted(
        ROOT.rglob("*.txt")
    )

    print()

    print(
        f"Bulunan TXT sayısı: {len(files)}"
    )

    if not files:

        print()

        print(
            "Aktarılacak TXT bulunamadı."
        )

        return

    # ------------------------------------------------------
    # DB
    # ------------------------------------------------------

    conn = sqlite3.connect(
        DB_PATH
    )

    # Yeni tabloyu garanti altına al.
    ensure_financial_reports_table(
        conn
    )

    total = 0
    success = 0
    failed = 0

    try:

        for path in files:

            print()

            print("-" * 70)

            print(
                f"İşleniyor: {path.name}"
            )

            # --------------------------------------------------
            # Sembol
            # --------------------------------------------------

            symbol = get_symbol(
                path
            )

            if not symbol:

                print(
                    "ATLANDI: sembol bulunamadı"
                )

                failed += 1

                continue

            # --------------------------------------------------
            # Dönem
            # --------------------------------------------------

            period, period_end = get_period(
                path
            )

            if not period:

                print(
                    "ATLANDI: dönem bulunamadı"
                )

                failed += 1

                continue

            # --------------------------------------------------
            # TXT
            # --------------------------------------------------

            try:

                text = path.read_text(
                    encoding="utf-8",
                    errors="ignore"
                )

            except Exception as e:

                print(
                    f"OKUMA HATASI: {e}"
                )

                failed += 1

                continue

            # --------------------------------------------------
            # PARSER
            # --------------------------------------------------

            data = parse_report(
                text
            )

            if not data:

                print(
                    "UYARI: finansal kalem bulunamadı"
                )

                failed += 1

                continue

            # --------------------------------------------------
            # DB
            # --------------------------------------------------

            try:

                save_report(
                    conn,
                    symbol,
                    period,
                    period_end,
                    data,
                    path.name
                )

                print()

                print(
                    f"Sembol       : {symbol}"
                )

                print(
                    f"Dönem        : {period}"
                )

                print(
                    f"Tarih        : {period_end}"
                )

                print(
                    f"Bulunan kalem: {len(data)}"
                )

                print()

                for field, info in data.items():

                    current = info.get(
                        "current"
                    )

                    if current is None:
                        continue

                    print(
                        f"{field:<40}"
                        f"{current:>18,.2f}"
                    )

                total += 1
                success += 1

            except Exception as e:

                print(
                    f"DB HATASI: {e}"
                )

                failed += 1

        # ------------------------------------------------------
        # Commit
        # ------------------------------------------------------

        conn.commit()

    except Exception as e:

        print(
            f"GENEL HATA: {e}"
        )

        conn.rollback()

    finally:

        conn.close()

    # ======================================================
    # SONUÇ
    # ======================================================

    print()

    print("=" * 70)

    print(
        "AKTARIM TAMAMLANDI"
    )

    print("=" * 70)

    print(
        f"İşlenen rapor : {total}"
    )

    print(
        f"Başarılı      : {success}"
    )

    print(
        f"Başarısız     : {failed}"
    )

    print(
        f"Toplam TXT    : {len(files)}"
    )

    print("=" * 70)


# ==========================================================
# GERİYE DÖNÜK UYUMLULUK
# ==========================================================

def main():

    import_all_financial_reports()


# ==========================================================
# ÇALIŞTIR
# ==========================================================

if __name__ == "__main__":

    main()