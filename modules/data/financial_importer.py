import re
import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]
DB_PATH = BASE_DIR / "borsa.db"


def parse_number(value):
    if value is None:
        return None

    value = str(value).strip()
    value = value.replace(".", "")
    value = value.replace(",", ".")

    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def read_text(path):
    return Path(path).read_text(
        encoding="utf-8",
        errors="replace"
    )


def find_exact_line_value(text, label):
    lines = text.splitlines()

    for i, line in enumerate(lines):
        clean = line.strip()

        if not clean.startswith(label):
            continue

        if label == "Uzun Vadeli Borçlanmalar":
            if clean.startswith("Uzun Vadeli Borçlanmaların "):
                continue

        remainder = clean[len(label):].strip()

        numbers = re.findall(
            r"-?\d[\d.]*,\d+|-?\d[\d.]*",
            remainder
        )

        if numbers:
            for value in numbers:
                number = parse_number(value)

                if number is None:
                    continue

                if abs(number) <= 100:
                    continue

                return number

        for next_line in lines[i + 1:i + 8]:
            next_clean = next_line.strip()

            if not next_clean:
                continue

            numbers = re.findall(
                r"-?\d[\d.]*,\d+|-?\d[\d.]*",
                next_clean
            )

            for value in numbers:
                number = parse_number(value)

                if number is None:
                    continue

                if abs(number) <= 100:
                    continue

                return number

    return None

def find_value(text, label):
    pattern = rf"{re.escape(label)}\s+((?:-?[\d.,]+\s+){{1,4}})"

    match = re.search(
        pattern,
        text,
        re.IGNORECASE
    )

    if not match:
        return None

    values = re.findall(
        r"-?[\d.,]+",
        match.group(1)
    )

    if not values:
        return None

    for value in values:
        number = parse_number(value)

        if number is None:
            continue

        if abs(number) <= 100:
            continue

        return number

    return None


def detect_period_from_filename(filename):
    name = Path(filename).stem.upper()

    match = re.search(
        r"(20\d{2})[_-](1C|2C|3C|4C|YILLIK)",
        name
    )

    if not match:
        raise ValueError(
            f"Dönem dosya adından bulunamadı: {filename}"
        )

    year = match.group(1)
    period_code = match.group(2)

    if period_code == "1C":
        return f"{year}_1Q", f"{year}-03-31"

    if period_code == "2C":
        return f"{year}_2Q", f"{year}-06-30"

    if period_code == "3C":
        return f"{year}_3Q", f"{year}-09-30"

    if period_code == "4C":
        return f"{year}_4Q", f"{year}-12-31"

    if period_code == "YILLIK":
        return f"{year}_YILLIK", f"{year}-12-31"

    raise ValueError(
        f"Tanımsız dönem kodu: {period_code}"
    )


def detect_symbol_from_filename(filename):
    name = Path(filename).stem.upper()

    match = re.match(
        r"([A-Z0-9]+)[_-]20\d{2}",
        name
    )

    if not match:
        raise ValueError(
            f"Hisse kodu dosya adından bulunamadı: {filename}"
        )

    return match.group(1)


def import_financial_file(txt_path):
    txt_path = Path(txt_path)

    if not txt_path.exists():
        print(f"DOSYA YOK: {txt_path}")
        return False

    text = read_text(txt_path)

    symbol = detect_symbol_from_filename(txt_path)
    period, period_end = detect_period_from_filename(txt_path)

    revenue = find_value(
        text,
        "Hasılat"
    )

    net_profit = find_value(
        text,
        "Net Dönem Karı veya Zararı"
    )

    if net_profit is None:
        net_profit = find_value(
            text,
            "Sürdürülen Faaliyetler Dönem Karı (Zararı)"
        )

    cash = find_exact_line_value(
        text,
        "Nakit ve Nakit Benzerleri"
    )

    equity = find_exact_line_value(
        text,
        "Ana Ortaklığa Ait Özkaynaklar"
    )

    operating_cash_flow = find_exact_line_value(
        text,
        "Faaliyetlerden Elde Edilen Nakit Akışları"
    )

    total_assets = find_exact_line_value(
        text,
        "TOPLAM VARLIKLAR"
    )

    short_term_financial_debt = find_exact_line_value(
        text,
        "Kısa Vadeli Borçlanmalar"
    )

    current_portion_long_term_debt = find_exact_line_value(
        text,
        "Uzun Vadeli Borçlanmaların Kısa Vadeli Kısımları"
    )

    long_term_financial_debt = find_exact_line_value(
        text,
        "Uzun Vadeli Borçlanmalar"
    )

    conn = sqlite3.connect(DB_PATH)

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
                updated_at = CURRENT_TIMESTAMP
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
            VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
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

    conn.commit()
    conn.close()

    print("=" * 55)
    print(f"OK - {txt_path.name} aktarıldı")
    print("=" * 55)
    print("Hisse:", symbol)
    print("Dönem:", period)
    print("Dönem sonu:", period_end)
    print("Hasılat:", revenue)
    print("Net kâr:", net_profit)
    print("Nakit:", cash)
    print("Toplam varlık:", total_assets)
    print("Özkaynak:", equity)
    print("Faaliyet nakit akışı:", operating_cash_flow)
    print("Kısa vadeli borç:", short_term_financial_debt)
    print("KV uzun vadeli borç:", current_portion_long_term_debt)
    print("Uzun vadeli borç:", long_term_financial_debt)
    print("=" * 55)

    return True


if __name__ == "__main__":

    import sys

    if len(sys.argv) < 2:

        print(
            "Kullanım: python financial_importer.py DOSYA.txt"
        )

    else:

        import_financial_file(
            sys.argv[1]
        )