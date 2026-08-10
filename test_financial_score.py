from modules.data.financial_score import calculate_financial_score

stocks = ["FROTO", "THYAO", "TUPRS"]

for symbol in stocks:
    print()
    print("=" * 60)
    print(symbol, "2026_2Q")
    print("=" * 60)

    result = calculate_financial_score(
        symbol,
        "2026-06-30"
    )

    if result is None:
        print("SONUÇ YOK")
        continue

    for key, value in result.items():
        print(f"{key}: {value}")