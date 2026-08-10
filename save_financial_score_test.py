from modules.data.financial_score import calculate_and_save_financial_score

stocks = ["FROTO", "THYAO", "TUPRS"]

for symbol in stocks:
    result = calculate_and_save_financial_score(
        symbol,
        "2026-06-30"
    )

    print()
    print("=" * 60)

    if result:
        print(symbol, "KAYDEDİLDİ")
        print("Dönem:", result["period"])
        print("Skor:", result["total_score"])
        print("Sinyal:", result["signal"])
    else:
        print(symbol, "HATA - sonuç oluşturulamadı")