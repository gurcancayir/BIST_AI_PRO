import re
import json
import requests

URL = "https://www.binance.tr/en/markets/trading-data"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/140.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
}

r = requests.get(
    URL,
    headers=HEADERS,
    timeout=30,
)

print("=" * 100)
print("BINANCE TR HTML VERİ ANALİZİ")
print("=" * 100)

print("HTTP:", r.status_code)
print("HTML:", len(r.text))

html = r.text


# ============================================================
# 1. BTC_TRY çevresini bul
# ============================================================

print()
print("=" * 100)
print("BTC_TRY ÇEVRESİ")
print("=" * 100)

positions = [
    m.start()
    for m in re.finditer("BTC_TRY", html)
]

print("BTC_TRY ADET:", len(positions))

for i, pos in enumerate(positions[:10], 1):

    start = max(0, pos - 1500)
    end = min(len(html), pos + 3000)

    print()
    print(f"--- BTC_TRY #{i} ---")
    print(html[start:end])


# ============================================================
# 2. TRY sembollerini bul
# ============================================================

print()
print("=" * 100)
print("TRY SEMBOLLERİ")
print("=" * 100)

symbols = sorted(
    set(
        re.findall(
            r'"([A-Z0-9]+_TRY)"',
            html,
        )
    )
)

print("TRY SYMBOL SAYISI:", len(symbols))

print()

for symbol in symbols[:100]:
    print(symbol)


# ============================================================
# 3. HTML içinde JSON scriptleri ara
# ============================================================

print()
print("=" * 100)
print("JSON SCRIPT BLOKLARI")
print("=" * 100)

patterns = [
    r'<script[^>]+type=["\']application/json["\'][^>]*>(.*?)</script>',
    r'<script[^>]+id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>',
]

for pattern in patterns:

    matches = re.findall(
        pattern,
        html,
        re.DOTALL | re.IGNORECASE,
    )

    print()
    print("PATTERN:", pattern)
    print("BLOK SAYISI:", len(matches))

    for i, block in enumerate(matches[:5], 1):

        print()
        print("BLOCK:", i)
        print("LENGTH:", len(block))

        if "BTC_TRY" in block:

            print("!!! BTC_TRY BU BLOKTA VAR !!!")

            pos = block.find("BTC_TRY")

            print(
                block[
                    max(0, pos - 2000):
                    pos + 5000
                ]
            )


# ============================================================
# 4. Next.js / SSR veri izleri
# ============================================================

print()
print("=" * 100)
print("SSR / NEXT VERİ İZLERİ")
print("=" * 100)

keywords = [
    "__NEXT_DATA__",
    "initialState",
    "initialData",
    "marketData",
    "marketList",
    "ticker",
    "tickers",
    "tradingData",
    "symbols",
    "markets",
]

for keyword in keywords:

    count = html.lower().count(keyword.lower())

    print(
        f"{keyword:20} -> {count}"
    )


# ============================================================
# 5. BTC_TRY'nin bulunduğu satırları göster
# ============================================================

print()
print("=" * 100)
print("BTC_TRY SATIRLARI")
print("=" * 100)

for line in html.splitlines():

    if "BTC_TRY" in line:

        print(line[:10000])


print()
print("=" * 100)
print("TEST BİTTİ")
print("=" * 100)