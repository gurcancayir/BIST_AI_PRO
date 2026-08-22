import requests
import json
import re

BASE = "https://www.binance.tr"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/140.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://www.binance.tr/tr/markets/trading-data",
    "Origin": "https://www.binance.tr",
}

session = requests.Session()
session.headers.update(HEADERS)


def test(url):
    print("=" * 100)
    print("URL:")
    print(url)
    print("=" * 100)

    try:
        r = session.get(url, timeout=20)

        print("HTTP:", r.status_code)
        print("CONTENT TYPE:", r.headers.get("content-type"))
        print("TEXT LENGTH:", len(r.text))
        print()
        print(r.text[:2000])

        try:
            data = r.json()

            print()
            print("JSON TYPE:", type(data))

            if isinstance(data, dict):
                print("KEYS:", list(data.keys()))

                print()
                print("JSON ÖZET:")
                print(json.dumps(data, indent=2, ensure_ascii=False)[:5000])

            elif isinstance(data, list):
                print("LIST LENGTH:", len(data))

                if data:
                    print()
                    print("FIRST ITEM:")
                    print(
                        json.dumps(
                            data[0],
                            indent=2,
                            ensure_ascii=False,
                        )
                    )

        except Exception as exc:
            print()
            print("JSON DEĞİL:", exc)

    except Exception as exc:
        print("REQUEST ERROR:", type(exc).__name__, exc)


# ============================================================
# BİLİNEN SAYFALAR
# ============================================================

urls = [

    # Ana piyasa sayfası
    f"{BASE}/tr/markets/trading-data",

    # İngilizce piyasa sayfası
    f"{BASE}/en/markets/trading-data",

    # Tek coin sayfası
    f"{BASE}/tr/trade/BTC_TRY",

    # API3 örneği
    f"{BASE}/tr/trade/API3_TRY",

    # Eski endpointler
    f"{BASE}/api/v3/exchangeInfo",
    f"{BASE}/api/v3/ticker/24hr",

    # Eski BAPI
    (
        f"{BASE}/bapi/asset/v2/public/"
        "asset-service/product/get-exchange-info"
    ),

    (
        f"{BASE}/bapi/asset/v2/public/"
        "asset-service/product/get-24hr-ticker"
    ),
]


for url in urls:
    test(url)
    print()
    print()


print("=" * 100)
print("TEST BİTTİ")
print("=" * 100)