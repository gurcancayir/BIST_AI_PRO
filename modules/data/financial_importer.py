import re
import sqlite3
from pathlib import Path

from pypdf import PdfReader


# ==========================================================
# YOLLAR
# ==========================================================

BASE_DIR = Path(__file__).resolve().parents[2]

DB_PATH = BASE_DIR / "borsa.db"

REPORTS_DIR = (
    BASE_DIR
    / "data"
    / "financial_reports"
)


# ==========================================================
# SAYI OKUMA
# ==========================================================

def parse_number(value):

    if value is None:
        return None

    value = str(value).strip()

    if not value:
        return None

    negative = False

    if value.startswith("(") and value.endswith(")"):
        negative = True
        value = value[1:-1]

    value = value.replace(" ", "")
    value = value.replace("%", "")

    # Türkçe sayı formatı
    value = value.replace(".", "")
    value = value.replace(",", ".")

    try:

        number = float(value)

        if negative:
            number *= -1

        return number

    except (ValueError, TypeError):

        return None


# ==========================================================
# PDF OKUMA
# ==========================================================

def read_pdf(path):

    path = Path(path)

    reader = PdfReader(str(path))

    pages = []

    for page_number, page in enumerate(
        reader.pages,
        start=1
    ):

        try:

            text = page.extract_text()

            if text:
                pages.append(text)

        except Exception as error:

            print(
                f"PDF sayfası okunamadı "
                f"(sayfa {page_number}): {error}"
            )

    return "\n".join(pages)


# ==========================================================
# DOSYA OKUMA
# ==========================================================

def read_file(path):

    path = Path(path)

    if path.suffix.lower() == ".pdf":

        return read_pdf(path)

    raise ValueError(
        f"Desteklenmeyen dosya: {path}"
    )


# ==========================================================
# BİRİM TESPİTİ
# ==========================================================
def detect_unit_multiplier(text):
    """
    PDF finansal tablo birimini tespit eder.

    Dönen değer:
        (çarpan, birim)

    Örnek:
        1.000.000 TL  -> (1_000_000, "Milyon TL")
        1.000.000.000 TL -> (1_000_000_000, "Milyar TL")
    """

    sample = text[:100000].lower()

    # ------------------------------------------------------
    # AÇIK SAYISAL BİRİM FORMATLARI
    # ------------------------------------------------------

    if re.search(
        r"1[\s\.\,]*000[\s\.\,]*000[\s\.\,]*000\s*tl",
        sample,
        re.IGNORECASE
    ):
        return 1_000_000_000, "Milyar TL"

    if re.search(
        r"1[\s\.\,]*000[\s\.\,]*000\s*tl",
        sample,
        re.IGNORECASE
    ):
        return 1_000_000, "Milyon TL"

    if re.search(
        r"1[\s\.\,]*000\s*tl",
        sample,
        re.IGNORECASE
    ):
        return 1_000, "Bin TL"

    # ------------------------------------------------------
    # YAZIYLA BELİRTİLEN BİRİMLER
    # ------------------------------------------------------

    if re.search(
        r"milyar\s*tl",
        sample,
        re.IGNORECASE
    ):
        return 1_000_000_000, "Milyar TL"

    if re.search(
        r"milyon\s*tl",
        sample,
        re.IGNORECASE
    ):
        return 1_000_000, "Milyon TL"

    if re.search(
        r"bin\s*tl",
        sample,
        re.IGNORECASE
    ):
        return 1_000, "Bin TL"

    # ------------------------------------------------------
    # KAP'IN BAZI PDF'LERİNDEKİ ALTERNATİF İFADELER
    # ------------------------------------------------------

    if re.search(
        r"sunum\s*para\s*birimi.*milyar",
        sample,
        re.IGNORECASE
    ):
        return 1_000_000_000, "Milyar TL"

    if re.search(
        r"sunum\s*para\s*birimi.*milyon",
        sample,
        re.IGNORECASE
    ):
        return 1_000_000, "Milyon TL"

    if re.search(
        r"sunum\s*para\s*birimi.*bin",
        sample,
        re.IGNORECASE
    ):
        return 1_000, "Bin TL"

    # ------------------------------------------------------
    # VARSAYILAN
    # ------------------------------------------------------

    return 1, "TL"

    # Öncelikle açık finansal tablo birimlerini ara.
    unit_patterns = [

        (
            r"birim\s*[-:–—]?\s*milyar\s*tl",
            1_000_000_000,
            "Milyar TL"
        ),

        (
            r"birim\s*[-:–—]?\s*milyon\s*tl",
            1_000_000,
            "Milyon TL"
        ),

        (
            r"birim\s*[-:–—]?\s*bin\s*tl",
            1_000,
            "Bin TL"
        ),

        (
            r"birim\s*[-:–—]?\s*tl\b",
            1,
            "TL"
        ),
    ]

    # Önce tüm metnin ilk 100.000 karakterinde ara.
    sample = text[:100000].lower()

    for pattern, multiplier, unit in unit_patterns:

        if re.search(
            pattern,
            sample,
            re.IGNORECASE
        ):

            return multiplier, unit

    # Daha genel aramalar
    if re.search(
        r"milyar\s*tl",
        sample,
        re.IGNORECASE
    ):

        return 1_000_000_000, "Milyar TL"

    if re.search(
        r"milyon\s*tl",
        sample,
        re.IGNORECASE
    ):

        return 1_000_000, "Milyon TL"

    if re.search(
        r"\bbin\s*tl\b",
        sample,
        re.IGNORECASE
    ):

        return 1_000, "Bin TL"

    return 1, "TL"


# ==========================================================
# SAYISAL DEĞERLERİ BUL
# ==========================================================

def extract_numbers(text):

    return re.findall(
        r"-?\(?\d[\d.]*,\d+\)?|-?\(?\d[\d.]*\)?",
        text
    )


# ==========================================================
# GÜRÜLTÜ SAYISI KONTROLÜ
# ==========================================================

def is_noise_number(number):

    if number is None:
        return True

    # Çok küçük yardımcı değerler
    if abs(number) <= 100:
        return True

    # Tablo içinde yıl olarak geçen değerler
    # 2020 / 2021 / 2022 / 2023 / 2024 / 2025 / 2026
    if 1900 <= abs(number) <= 2100:
        return True

    return False


# ==========================================================
# ETİKETİN AYNI SATIRINDA DEĞER BUL
# ==========================================================

def find_line_value(
    text,
    labels,
    multiplier=1
):

    if isinstance(labels, str):

        labels = [labels]

    lines = text.splitlines()

    for i, line in enumerate(lines):

        clean = line.strip()

        if not clean:
            continue

        lower = clean.lower()

        matched_label = None

        for label in labels:

            if label.lower() in lower:

                matched_label = label
                break

        if matched_label is None:
            continue

        position = lower.find(
            matched_label.lower()
        )

        remainder = clean[
            position + len(matched_label):
        ]

        numbers = extract_numbers(
            remainder
        )

        # --------------------------------------------------
        # AYNI SATIR
        # --------------------------------------------------

        if numbers:

            for value in numbers:

                number = parse_number(value)

                if is_noise_number(number):
                    continue

                return number * multiplier

        # --------------------------------------------------
        # SONRAKİ SATIRLAR
        # --------------------------------------------------

        for next_line in lines[
            i + 1:i + 10
        ]:

            next_clean = next_line.strip()

            if not next_clean:
                continue

            numbers = extract_numbers(
                next_clean
            )

            for value in numbers:

                number = parse_number(value)

                if is_noise_number(number):
                    continue

                return number * multiplier

    return None


# ==========================================================
# GELİR / HASILAT
# ==========================================================

def find_revenue(
    text,
    multiplier
):

    return find_line_value(
        text,
        [
            "Hasılat",
            "Satış Gelirleri",
            "Satışlar"
        ],
        multiplier
    )


# ==========================================================
# NET KÂR
# ==========================================================

def find_net_profit(
    text,
    multiplier
):

    return find_line_value(
        text,
        [
            "Net Dönem Karı veya Zararı",
            "Net Dönem Kârı veya Zararı",
            "Sürdürülen Faaliyetler Dönem Karı (Zararı)",
            "Sürdürülen Faaliyetler Dönem Kârı (Zararı)"
        ],
        multiplier
    )


# ==========================================================
# NAKİT
# ==========================================================

def find_cash(
    text,
    multiplier
):

    return find_line_value(
        text,
        [
            "Nakit ve Nakit Benzerleri"
        ],
        multiplier
    )


# ==========================================================
# ÖZKAYNAK
# ==========================================================
def find_equity(text, multiplier):
    """
    Özkaynak değerini bulur.

    Öncelik:
    1. Ana Ortaklığa Ait Özkaynaklar
    2. Ana Ortaklığa Ait Özkaynak
    3. Toplam Özkaynaklar
    4. Özkaynaklar

    Çok küçük değerleri filtreler.
    """

    labels = [
        "Ana Ortaklığa Ait Özkaynaklar",
        "Ana Ortaklığa Ait Özkaynak",
        "Toplam Özkaynaklar",
        "Özkaynaklar",
    ]

    lines = text.splitlines()

    for label in labels:

        label_lower = label.lower()

        for i, line in enumerate(lines):

            clean = line.strip()

            if not clean:
                continue

            lower = clean.lower()

            if label_lower not in lower:
                continue

            # Etiketten sonraki bölüm
            position = lower.find(label_lower)

            remainder = clean[
                position + len(label):
            ].strip()

            # Önce aynı satırdaki sayıları kontrol et
            numbers = extract_numbers(remainder)

            valid_numbers = []

            for value in numbers:

                number = parse_number(value)

                if number is None:
                    continue

                if abs(number) <= 10000:
                    continue

                valid_numbers.append(number)

            if valid_numbers:

                # Etiketten hemen sonraki ilk geçerli değer
                return valid_numbers[0] * multiplier

            # Etiket ayrı satırdaysa sonraki satırlara bak
            for next_line in lines[i + 1:i + 8]:

                next_clean = next_line.strip()

                if not next_clean:
                    continue

                numbers = extract_numbers(
                    next_clean
                )

                valid_numbers = []

                for value in numbers:

                    number = parse_number(value)

                    if number is None:
                        continue

                    if abs(number) <= 10000:
                        continue

                    valid_numbers.append(number)

                if valid_numbers:

                    return valid_numbers[0] * multiplier

    return None
# ==========================================================
# FAALİYET NAKİT AKIŞI
# ==========================================================

def find_operating_cash_flow(
    text,
    multiplier
):

    return find_line_value(
        text,
        [
            "Faaliyetlerden Elde Edilen Nakit Akışları",
            "Faaliyetlerden Sağlanan Nakit Akışları",
            "İşletme Faaliyetlerinden Nakit Akışları"
        ],
        multiplier
    )


# ==========================================================
# TOPLAM VARLIK
# ==========================================================

def find_total_assets(
    text,
    multiplier
):

    return find_line_value(
        text,
        [
            "TOPLAM VARLIKLAR",
            "Toplam Varlıklar"
        ],
        multiplier
    )


# ==========================================================
# KISA VADELİ BORÇ
# ==========================================================

def find_short_debt(
    text,
    multiplier
):

    return find_line_value(
        text,
        [
            "Kısa Vadeli Borçlanmalar"
        ],
        multiplier
    )


# ==========================================================
# KV UZUN VADELİ BORÇ
# ==========================================================

def find_current_long_debt(
    text,
    multiplier
):

    return find_line_value(
        text,
        [
            "Uzun Vadeli Borçlanmaların Kısa Vadeli Kısımları"
        ],
        multiplier
    )


# ==========================================================
# UZUN VADELİ BORÇ
# ==========================================================

def find_long_debt(
    text,
    multiplier
):

    lines = text.splitlines()

    for i, line in enumerate(lines):

        clean = line.strip()

        if not clean.startswith(
            "Uzun Vadeli Borçlanmalar"
        ):

            continue

        # Kısa vadeli kısmı alma
        if clean.startswith(
            "Uzun Vadeli Borçlanmaların "
        ):

            continue

        remainder = clean[
            len("Uzun Vadeli Borçlanmalar"):
        ].strip()

        numbers = extract_numbers(
            remainder
        )

        for value in numbers:

            number = parse_number(value)

            if is_noise_number(number):
                continue

            return number * multiplier

        for next_line in lines[
            i + 1:i + 10
        ]:

            numbers = extract_numbers(
                next_line
            )

            for value in numbers:

                number = parse_number(value)

                if is_noise_number(number):
                    continue

                return number * multiplier

    return None


# ==========================================================
# DOSYA ADINDAN DÖNEM
# ==========================================================

def detect_period_from_filename(
    filename
):

    name = Path(filename).stem.upper()

    match = re.search(
        r"(20\d{2})[_-](1C|2C|3C|4C|YILLIK)",
        name
    )

    if not match:

        raise ValueError(
            f"Dönem dosya adından bulunamadı: "
            f"{filename}"
        )

    year = match.group(1)

    period_code = match.group(2)

    if period_code == "1C":

        return (
            f"{year}_1Q",
            f"{year}-03-31"
        )

    if period_code == "2C":

        return (
            f"{year}_2Q",
            f"{year}-06-30"
        )

    if period_code == "3C":

        return (
            f"{year}_3Q",
            f"{year}-09-30"
        )

    if period_code == "4C":

        return (
            f"{year}_4Q",
            f"{year}-12-31"
        )

    if period_code == "YILLIK":

        return (
            f"{year}_YILLIK",
            f"{year}-12-31"
        )

    raise ValueError(
        f"Tanımsız dönem kodu: "
        f"{period_code}"
    )


# ==========================================================
# HİSSE KODU
# ==========================================================

def detect_symbol_from_filename(
    filename
):

    name = Path(filename).stem.upper()

    match = re.match(
        r"([A-Z0-9]+)[_-]20\d{2}",
        name
    )

    if not match:

        raise ValueError(
            f"Hisse kodu dosya adından "
            f"bulunamadı: {filename}"
        )

    return match.group(1)


# ==========================================================
# FİNANSAL DOSYA AKTAR
# ==========================================================

def import_financial_file(
    file_path
):

    file_path = Path(file_path)

    if not file_path.exists():

        print(
            f"❌ DOSYA YOK: {file_path}"
        )

        return False

    print()
    print("=" * 70)

    print(
        f"İŞLENİYOR: {file_path.name}"
    )

    print("=" * 70)

    # ------------------------------------------------------
    # PDF OKU
    # ------------------------------------------------------

    try:

        text = read_file(
            file_path
        )

    except Exception as error:

        print(
            f"❌ PDF okunamadı: {error}"
        )

        return False

    if not text.strip():

        print(
            "❌ PDF'den metin çıkarılamadı."
        )

        return False

    # ------------------------------------------------------
    # HİSSE
    # ------------------------------------------------------

    symbol = detect_symbol_from_filename(
        file_path
    )

    # ------------------------------------------------------
    # DÖNEM
    # ------------------------------------------------------

    period, period_end = (
        detect_period_from_filename(
            file_path
        )
    )

    # ------------------------------------------------------
    # BİRİM
    # ------------------------------------------------------

    multiplier, unit = (
        detect_unit_multiplier(
            text
        )
    )

    print(
        f"Birim: {unit}"
    )

    print(
        f"Çarpan: {multiplier:,}"
    )

    # ------------------------------------------------------
    # FİNANSAL VERİLER
    # ------------------------------------------------------

    revenue = find_revenue(
        text,
        multiplier
    )

    net_profit = find_net_profit(
        text,
        multiplier
    )

    cash = find_cash(
        text,
        multiplier
    )

    equity = find_equity(
        text,
        multiplier
    )

    operating_cash_flow = (
        find_operating_cash_flow(
            text,
            multiplier
        )
    )

    total_assets = find_total_assets(
        text,
        multiplier
    )

    short_term_financial_debt = (
        find_short_debt(
            text,
            multiplier
        )
    )

    current_portion_long_term_debt = (
        find_current_long_debt(
            text,
            multiplier
        )
    )

    long_term_financial_debt = (
        find_long_debt(
            text,
            multiplier
        )
    )

    # ------------------------------------------------------
    # VERİTABANI
    # ------------------------------------------------------

    conn = sqlite3.connect(
        DB_PATH
    )

    existing = conn.execute(
        """
        SELECT id
        FROM financial_statements
        WHERE symbol = ?
          AND period_end = ?
        LIMIT 1
        """,
        (
            symbol,
            period_end
        )
    ).fetchone()

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
                total_assets = ?,
                equity = ?,
                operating_cash_flow = ?,
                short_term_financial_debt = ?,
                current_portion_long_term_debt = ?,
                long_term_financial_debt = ?,
                source = ?,
                source_date = ?,
                updated_at =
                    CURRENT_TIMESTAMP

            WHERE id = ?
            """,
            (
                period,
                "Konsolide",
                "TRY",
                revenue,
                net_profit,
                cash,
                total_assets,
                equity,
                operating_cash_flow,
                short_term_financial_debt,
                current_portion_long_term_debt,
                long_term_financial_debt,
                "KAP",
                period_end,
                existing[0]
            )
        )

        action = "GÜNCELLENDİ"

    else:

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
                net_profit,
                cash,
                total_assets,
                equity,
                operating_cash_flow,
                short_term_financial_debt,
                current_portion_long_term_debt,
                long_term_financial_debt,
                source,
                source_date,
                updated_at
            )

            VALUES
            (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?,
                CURRENT_TIMESTAMP
            )
            """,
            (
                symbol,
                period,
                period_end,
                "Konsolide",
                "TRY",
                revenue,
                net_profit,
                cash,
                total_assets,
                equity,
                operating_cash_flow,
                short_term_financial_debt,
                current_portion_long_term_debt,
                long_term_financial_debt,
                "KAP",
                period_end
            )
        )

        action = "EKLENDİ"

    conn.commit()

    conn.close()

    # ------------------------------------------------------
    # SONUÇ
    # ------------------------------------------------------

    print()

    print(
        f"✅ {action}"
    )

    print(
        "Hisse:",
        symbol
    )

    print(
        "Dönem:",
        period
    )

    print(
        "Dönem sonu:",
        period_end
    )

    print(
        "Birim:",
        unit
    )

    print(
        "Hasılat:",
        revenue
    )

    print(
        "Net kâr:",
        net_profit
    )

    print(
        "Nakit:",
        cash
    )

    print(
        "Toplam varlık:",
        total_assets
    )

    print(
        "Özkaynak:",
        equity
    )

    print(
        "Faaliyet nakit akışı:",
        operating_cash_flow
    )

    print(
        "Kısa vadeli borç:",
        short_term_financial_debt
    )

    print(
        "KV uzun vadeli borç:",
        current_portion_long_term_debt
    )

    print(
        "Uzun vadeli borç:",
        long_term_financial_debt
    )

    print("=" * 70)

    return True


# ==========================================================
# TÜM PDF'LERİ TARA
# ==========================================================

def import_all_financial_reports():

    print()
    print("=" * 70)

    print(
        "KAP FİNANSAL RAPORLARI "
        "OTOMATİK TARAMA"
    )

    print("=" * 70)

    if not REPORTS_DIR.exists():

        print(
            f"❌ Klasör bulunamadı: "
            f"{REPORTS_DIR}"
        )

        return

    pdf_files = sorted(
        REPORTS_DIR.rglob("*.pdf")
    )

    if not pdf_files:

        print(
            "❌ Hiç PDF bulunamadı."
        )

        return

    print(
        f"Bulunan PDF sayısı: "
        f"{len(pdf_files)}"
    )

    success = 0

    failed = 0

    for pdf_file in pdf_files:

        try:

            result = import_financial_file(
                pdf_file
            )

            if result:

                success += 1

            else:

                failed += 1

        except Exception as error:

            failed += 1

            print()

            print(
                f"❌ HATA: "
                f"{pdf_file.name}"
            )

            print(
                error
            )

    print()
    print("=" * 70)

    print(
        "OTOMATİK AKTARIM TAMAMLANDI"
    )

    print("=" * 70)

    print(
        "Başarılı:",
        success
    )

    print(
        "Hatalı:",
        failed
    )

    print("=" * 70)


# ==========================================================
# PROGRAM
# ==========================================================

if __name__ == "__main__":

    import_all_financial_reports()