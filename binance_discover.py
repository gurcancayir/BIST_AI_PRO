import re
import requests

URL = "https://www.binance.tr/en/markets/trading-data"

headers = {
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
    headers=headers,
    timeout=30,
)

print("=" * 80)
print("BINANCE TR WEB TEST")
print("=" * 80)

print("HTTP:", r.status_code)
print("CONTENT TYPE:", r.headers.get("content-type"))
print("HTML LENGTH:", len(r.text))

html = r.text

print()
print("BTC_TRY VAR MI:", "BTC_TRY" in html)
print("ETH_TRY VAR MI:", "ETH_TRY" in html)
print("USDT_TRY VAR MI:", "USDT_TRY" in html)

print()
print("=" * 80)
print("BINANCE URL'LERİ")
print("=" * 80)

patterns = [
    r'https?://[^"\']+',
    r'/api/[^"\']+',
    r'/bapi/[^"\']+',
    r'/api/[^"\']+',
    r'api[^"\']+ticker[^"\']+',
    r'api[^"\']+market[^"\']+',
    r'api[^"\']+exchange[^"\']+',
]

found = set()

for pattern in patterns:
    try:
        matches = re.findall(pattern, html, re.IGNORECASE)

        for item in matches:
            item = item.replace("\\u002F", "/")

            if (
                "api" in item.lower()
                or "bapi" in item.lower()
            ):
                found.add(item[:1000])

    except Exception:
        pass


for item in sorted(found):
    print(item)

print()
print("=" * 80)
print("SCRIPT DOSYALARI")
print("=" * 80)

scripts = re.findall(
    r'<script[^>]+src=["\']([^"\']+)["\']',
    html,
    re.IGNORECASE,
)

for script in scripts:
    print(script)

print()
print("=" * 80)
print("TEST BİTTİ")
print("=" * 80)