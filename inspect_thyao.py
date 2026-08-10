from pathlib import Path

pdf_path = Path("data/financial_reports/2026/2C/thyao_2026_2c.pdf")

try:
    from pypdf import PdfReader
except ImportError:
    print("pypdf not found")
    raise SystemExit

reader = PdfReader(str(pdf_path))

print("PAGE COUNT:", len(reader.pages))
print("=" * 80)

keywords = [
    "ozkaynak",
    "hasilat",
    "net donem",
    "faaliyetlerden",
    "nakit"
]

for page_no, page in enumerate(reader.pages, 1):

    text = page.extract_text() or ""

    text_lower = text.lower()

    if any(keyword in text_lower for keyword in keywords):

        print("\n### PAGE", page_no, "###")
        print(text[:12000])

