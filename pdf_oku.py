from pypdf import PdfReader
from pathlib import Path


def pdf_to_txt(pdf_path, txt_path):
    pdf_path = Path(pdf_path)
    txt_path = Path(txt_path)

    reader = PdfReader(str(pdf_path))

    pages = []

    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""

        pages.append(
            f"--- SAYFA {i + 1} ---\n{text}"
        )

    txt_path.write_text(
        "\n\n".join(pages),
        encoding="utf-8"
    )

    print(
        f"OK - {len(reader.pages)} sayfa çıkarıldı: "
        f"{txt_path}"
    )


# --------------------------------------------------
# ASTOR 2026 1Ç
# --------------------------------------------------

pdf_to_txt(
    r"data\financial_reports\2026\1C\ASTOR_2026_1C.pdf",
    r"data\financial_reports\2026\1C\ASTOR_2026_1C.txt"
)


# --------------------------------------------------
# ASTOR 2025 YILLIK
# --------------------------------------------------

pdf_to_txt(
    r"data\financial_reports\2025\ASTOR_2025_YILLIK.pdf",
    r"data\financial_reports\2025\ASTOR_2025_YILLIK.txt"
)
# ASTOR 2025 1C
pdf_to_txt(
    r"data\financial_reports\2025\astor_2025_1C.pdf",
    r"data\financial_reports\2025\astor_2025_1C.txt"
)

# ASTOR 2025 2C
pdf_to_txt(
    r"data\financial_reports\2025\astor_2025_2c.pdf",
    r"data\financial_reports\2025\astor_2025_2c.txt"
)

# ASTOR 2025 3C
pdf_to_txt(
    r"data\financial_reports\2025\astor_2025_3c.pdf",
    r"data\financial_reports\2025\astor_2025_3c.txt"
)