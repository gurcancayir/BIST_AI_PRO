from pathlib import Path


DOSYA = Path(
    r"data\financial_reports\2026\1C\ASTOR_2026_1C.txt"
)

ARAMALAR = [
    "Hasılat",
    "Satışların Maliyeti",
    "Esas Faaliyet Karı",
    "Esas Faaliyet Kârı",
    "Dönem Karı",
    "Dönem Kârı",
    "Net Dönem Karı",
    "Net Dönem Kârı",
    "Nakit ve Nakit Benzerleri",
    "Ticari Alacaklar",
    "Stoklar",
    "Dönen Varlıklar",
    "Kısa Vadeli Yükümlülükler",
    "Uzun Vadeli Yükümlülükler",
    "Toplam Varlıklar",
    "Toplam Özkaynaklar",
    "Finansal Borçlanmalar",
    "Finansal Borçlar",
    "Kısa Vadeli Borçlanmalar",
    "Uzun Vadeli Borçlanmalar",
    "Faaliyetlerden Elde Edilen Nakit Akışları",
]


text = DOSYA.read_text(encoding="utf-8")
satirlar = text.splitlines()


for arama in ARAMALAR:

    print()
    print("=" * 80)
    print("ARAMA:", arama)
    print("=" * 80)

    bulundu = False

    for i, satir in enumerate(satirlar):

        if arama.lower() in satir.lower():

            bulundu = True

            baslangic = max(0, i - 3)
            bitis = min(len(satirlar), i + 8)

            for j in range(baslangic, bitis):
                print(satirlar[j])

            print("-" * 80)

    if not bulundu:
        print("Bulunamadı.")