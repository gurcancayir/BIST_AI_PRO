from pathlib import Path
from pypdf import PdfReader

base = Path("data/financial_reports/2025")

files = [
    ("astor_2025_1C.pdf", "astor_2025_1C.txt"),
    ("astor_2025_2c.pdf", "astor_2025_2c.txt"),
    ("astor_2025_3c.pdf", "astor_2025_3c.txt"),
]

for pdf_name, txt_name in files:
    pdf_path = base / pdf_name
    txt_path = base / txt_name

    reader = PdfReader(str(pdf_path))
    pages = []

    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        pages.append(f"--- SAYFA {i + 1} ---\n{text}")

    txt_path.write_text(
        "\n\n".join(pages),
        encoding="utf-8"
    )

    print(f"OK - {pdf_name} -> {txt_name}")

print("TAMAMLANDI")
