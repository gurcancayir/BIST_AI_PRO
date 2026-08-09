import sqlite3
from pathlib import Path
import re

DB = "borsa.db"
ROOT = Path("data/financial_reports")


def tr_number(value):
    if value is None:
        return None

    value = str(value).strip()
    value = value.replace(" ", "").replace("\n", "")

    if not value:
        return None

    negative = value.startswith("-")
    value = value.replace("-", "")

    # Türkçe binlik ayýrýcýlarýný kaldýr
    value = value.replace(".", "")

    # Ondalýk virgül varsa
    value = value.replace(",", ".")

    try:
        number = float(value)
        return -number if negative else number
    except:
        return None


def get_symbol(path):
    name = path.stem.upper()

    match = re.match(r"([A-Z0-9]+)_\d{4}", name)

    if match:
        return match.group(1)

    return None


def get_period(path):
    name = path.stem.upper()

    match = re.search(r"_(\d{4})_1C", name)

    if match:
        return int(match.group(1)), "2026_1Q"

    match = re.search(r"_(\d{4})_YILLIK", name)

    if match:
        return int(match.group(1)), "2025_YILLIK"

    return None, None


def parse_lines(text):
    rows = []

    for raw_line in text.splitlines():

        line = " ".join(raw_line.split())

        if not line:
            continue

        # En az iki sayý içeren satýrlarý yakala
        numbers = re.findall(
            r"-?\d[\d\.]*(?:,\d+)?",
            line
        )

        if len(numbers) < 2:
            continue

        # Son iki sayýyý cari / önceki dönem kabul et
        current = tr_number(numbers[-2])
        previous = tr_number(numbers[-1])

        if current is None:
            continue

        # Sayýlarý metinden çýkar
        item_name = line

        for n in numbers:
            item_name = item_name.replace(n, " ")

        item_name = re.sub(r"\s+", " ", item_name).strip()

        # Çok kýsa / anlamsýz satýrlarý alma
        if len(item_name) < 3:
            continue

        rows.append(
            (
                item_name,
                current,
                previous
            )
        )

    return rows


def main():

    if not ROOT.exists():
        print("HATA: financial_reports klasörü bulunamadý.")
        return

    files = list(ROOT.rglob("*.txt"))

    print(f"\nBulunan TXT sayýsý: {len(files)}")

    conn = sqlite3.connect(DB)
    cursor = conn.cursor()

    total = 0

    for path in files:

        symbol = get_symbol(path)
        fiscal_year, fiscal_period = get_period(path)

        if not symbol:
            print(f"ATLANDI - sembol bulunamadý: {path.name}")
            continue

        if not fiscal_year:
            print(f"ATLANDI - dönem bulunamadý: {path.name}")
            continue

        print(
            f"\nÝþleniyor: {symbol} | "
            f"{fiscal_year} | {fiscal_period}"
        )

        text = path.read_text(
            encoding="utf-8",
            errors="ignore"
        )

        rows = parse_lines(text)

        inserted = 0

        for item_name, value, previous_value in rows:

            change_amount = None
            change_percent = None

            if previous_value not in (None, 0):

                change_amount = value - previous_value

                change_percent = (
                    change_amount /
                    abs(previous_value)
                ) * 100

            cursor.execute(
                """
                INSERT INTO financial_statements
                (
                    symbol,
                    fiscal_year,
                    fiscal_period,
                    statement_date,
                    report_date,
                    source,
                    document_name,
                    currency,
                    statement_type,
                    item_code,
                    item_name,
                    value,
                    previous_value,
                    change_amount,
                    change_percent
                )
                VALUES
                (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?
                )

                ON CONFLICT
                (
                    symbol,
                    fiscal_year,
                    fiscal_period,
                    statement_type,
                    item_code
                )

                DO UPDATE SET

                    statement_date =
                        excluded.statement_date,

                    report_date =
                        excluded.report_date,

                    source =
                        excluded.source,

                    document_name =
                        excluded.document_name,

                    currency =
                        excluded.currency,

                    item_name =
                        excluded.item_name,

                    value =
                        excluded.value,

                    previous_value =
                        excluded.previous_value,

                    change_amount =
                        excluded.change_amount,

                    change_percent =
                        excluded.change_percent
                """,
                (
                    symbol,
                    fiscal_year,
                    fiscal_period,
                    None,
                    None,
                    "KAP",
                    path.name,
                    "TRY",
                    "FINANCIAL",
                    item_name,
                    item_name,
                    value,
                    previous_value,
                    change_amount,
                    change_percent
                )
            )

            inserted += 1
            total += 1

    conn.commit()
    conn.close()

    print("\n==============================")
    print("AKTARIM TAMAMLANDI")
    print("==============================")
    print(f"Toplam kayýt: {total}")


if __name__ == "__main__":
    main()
