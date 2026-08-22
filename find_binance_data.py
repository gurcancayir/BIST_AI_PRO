import json
import re
import requests

URL = "https://www.binance.tr/en/markets/overview"

headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/140.0 Safari/537.36"
    ),
    "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
}

print("=" * 80)
print("BINANCE TR DATA DISCOVERY")
print("=" * 80)

r = requests.get(
    URL,
    headers=headers,
    timeout=30,
)

print("HTTP:", r.status_code)
print("HTML:", len(r.text))

m = re.search(
    r'<script[^>]+id=["\']__APP_DATA["\'][^>]*>(.*?)</script>',
    r.text,
    re.I | re.S,
)

if not m:
    print("!!! __APP_DATA YOK !!!")
    raise SystemExit

data = json.loads(m.group(1))

print("__APP_DATA OK")
print("ROOT KEYS:")
print(list(data.keys()))


def walk(obj, path="ROOT"):

    if isinstance(obj, dict):

        # TRY sembollerini içeren listeleri bul
        for key, value in obj.items():

            if isinstance(value, list):

                try:
                    try_items = []

                    for item in value:

                        if not isinstance(item, dict):
                            continue

                        symbol = str(
                            item.get("symbol")
                            or ""
                        ).upper()

                        if (
                            symbol.endswith("_TRY")
                            or symbol.endswith("TRY")
                        ):
                            try_items.append(item)

                    if len(try_items) >= 2:

                        print()
                        print("=" * 80)
                        print("!!! TRY LIST FOUND !!!")
                        print("PATH:", path + "." + key)
                        print("COUNT:", len(try_items))
                        print("=" * 80)

                        for item in try_items[:5]:

                            print(
                                json.dumps(
                                    item,
                                    ensure_ascii=False,
                                    indent=2,
                                )
                            )

                except Exception:
                    pass

            walk(
                value,
                path + "." + str(key),
            )

    elif isinstance(obj, list):

        for i, value in enumerate(obj):
            walk(
                value,
                f"{path}[{i}]",
            )


walk(data)

print()
print("=" * 80)
print("TEST BİTTİ")
print("=" * 80)