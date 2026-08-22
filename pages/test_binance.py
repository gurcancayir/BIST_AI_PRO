import requests
import json

URL = "https://www.binance.tr/open/v1/common/symbols"

print("=" * 70)
print("BINANCE TR API TEST")
print("=" * 70)

try:

    response = requests.get(
        URL,
        timeout=20,
        headers={
            "User-Agent": "Mozilla/5.0"
        }
    )

    print()
    print("HTTP STATUS:", response.status_code)

    print()
    print("CONTENT TYPE:")
    print(response.headers.get("content-type"))

    print()
    print("RAW RESPONSE:")
    print(response.text[:2000])

    print()
    print("=" * 70)

    data = response.json()

    print("JSON OK")

    print()
    print("TOP LEVEL:")
    print(data.keys())

    print()
    print("CODE:")
    print(data.get("code"))

    print()
    print("MESSAGE:")
    print(data.get("msg"))

    payload = data.get("data")

    print()
    print("DATA TYPE:")
    print(type(payload))

    if isinstance(payload, dict):

        symbols = payload.get("list", [])

        print()
        print("SYMBOL SAYISI:")
        print(len(symbols))

        print()
        print("İLK 5 SYMBOL:")
        print(
            json.dumps(
                symbols[:5],
                indent=2,
                ensure_ascii=False
            )
        )

        try_symbols = [
            x
            for x in symbols
            if isinstance(x, dict)
            and str(
                x.get("quoteAsset", "")
            ).upper() == "TRY"
        ]

        print()
        print("=" * 70)
        print("TRY SYMBOL SAYISI:")
        print(len(try_symbols))

        print()
        print("İLK 20 TRY SYMBOL:")
        print(
            json.dumps(
                try_symbols[:20],
                indent=2,
                ensure_ascii=False
            )
        )

except Exception as e:

    print()
    print("=" * 70)
    print("HATA")
    print("=" * 70)

    print(
        type(e).__name__,
        str(e)
    )