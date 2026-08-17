from pypdf import PdfReader
from pathlib import Path


# ==========================================================
# FİNANSAL RAPORLAR KLASÖRÜ
# ==========================================================

ROOT = Path("data/financial_reports")


# ==========================================================
# PDF → TXT
# ==========================================================

def pdf_to_txt(pdf_path):

    pdf_path = Path(pdf_path)

    txt_path = pdf_path.with_suffix(".txt")

    print()
    print("-" * 70)
    print(f"PDF okunuyor: {pdf_path}")

    try:

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
            f"OK: {pdf_path.name}"
        )

        print(
            f"TXT: {txt_path.name}"
        )

        print(
            f"Sayfa: {len(reader.pages)}"
        )

        return True

    except Exception as error:

        print(
            f"HATA: {pdf_path.name}"
        )

        print(error)

        return False


# ==========================================================
# TÜM PDF'LERİ OTOMATİK BUL
# ==========================================================

def convert_all_pdfs():

    print()
    print("=" * 70)
    print("FİNANSAL RAPOR PDF → TXT OTOMATİK TARAMA")
    print("=" * 70)

    print()
    print(f"Klasör: {ROOT.resolve()}")

    if not ROOT.exists():

        print()
        print("HATA: financial_reports klasörü bulunamadı.")
        return

    pdf_files = sorted(
        ROOT.rglob("*.pdf")
    )

    print()
    print(
        f"Bulunan PDF sayısı: {len(pdf_files)}"
    )

    if not pdf_files:

        print(
            "PDF bulunamadı."
        )

        return

    created = 0
    updated = 0
    skipped = 0
    failed = 0

    for pdf in pdf_files:

        txt = pdf.with_suffix(".txt")

        # --------------------------------------------------
        # TXT YOK
        # --------------------------------------------------

        if not txt.exists():

            print()
            print(
                f"YENİ TXT OLUŞTURULUYOR: "
                f"{pdf.name}"
            )

            if pdf_to_txt(pdf):

                created += 1

            else:

                failed += 1

            continue

        # --------------------------------------------------
        # PDF TXT'DEN YENİ
        # --------------------------------------------------

        if pdf.stat().st_mtime > txt.stat().st_mtime:

            print()
            print(
                f"PDF GÜNCEL → TXT YENİLENİYOR: "
                f"{pdf.name}"
            )

            if pdf_to_txt(pdf):

                updated += 1

            else:

                failed += 1

            continue

        # --------------------------------------------------
        # TXT ZATEN GÜNCEL
        # --------------------------------------------------

        print(
            f"GEÇİLDİ: {pdf.name}"
        )

        skipped += 1

    # ======================================================
    # SONUÇ
    # ======================================================

    print()
    print("=" * 70)
    print("PDF → TXT TARAMASI TAMAMLANDI")
    print("=" * 70)

    print(
        f"Yeni TXT      : {created}"
    )

    print(
        f"Güncellenen   : {updated}"
    )

    print(
        f"Zaten güncel  : {skipped}"
    )

    print(
        f"Hatalı        : {failed}"
    )

    print("=" * 70)


# ==========================================================
# ÇALIŞTIR
# ==========================================================

if __name__ == "__main__":

    convert_all_pdfs()