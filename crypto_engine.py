# ============================================================
# CRYPTO AI PRO
# crypto_engine.py
#
# TEK KRİPTO ANALİZ MOTORU
#
# VERİ KAYNAKLARI:
#   1. Binance TR
#   2. Binance Global Spot
#
# PARİTELER:
#   Binance TR  -> TRY
#   Binance     -> USDT
#
# GLOBAL USDT COINLER:
#   TRY karşılığı USDT/TRY kuru ile hesaplanır.
#
# TIMEFRAME:
#   15m
#
# ANALİZ:
#   EMA 9 / 20 / 50
#   RSI
#   VWAP
#   Volume Ratio
#   Momentum
#   Support / Resistance
#   Risk / Reward
#
# ÇIKTI:
#   Trade Score
#   A / B / C
#   Trade Decision
#
# ============================================================

import requests
import pandas as pd
import numpy as np

from datetime import datetime


# ============================================================
# AYARLAR
# ============================================================

# ------------------------------------------------------------
# BINANCE TR
# ------------------------------------------------------------

BINANCE_TR_BASE_URL = "https://www.binance.tr"

BINANCE_TR_API_URL = "https://api.binance.me"


# ------------------------------------------------------------
# BINANCE GLOBAL
# ------------------------------------------------------------

BINANCE_GLOBAL_API_URL = "https://api.binance.com"


# ------------------------------------------------------------
# GENEL
# ------------------------------------------------------------

INTERVAL = "15m"

KLINE_LIMIT = 200


# ============================================================
# LİKİDİTE
# ============================================================

MIN_VOLUME_TRY = 20_000_000


# ============================================================
# ANALİZ LİMİTİ
# ============================================================

MAX_ANALYSIS_COINS = 80


# ============================================================
# GLOBAL COINLERDE ÖNCELİK VERİLECEKLER
# ============================================================

PRIORITY_GLOBAL_COINS = {

    "TUT",

}


# ============================================================
# EXCLUDED COINS
# ============================================================

EXCLUDED_COINS = {

    "USDT",
    "USDC",
    "FDUSD",
    "TUSD",
    "DAI",
    "EUR",
    "TRY",

}


# ============================================================
# SESSION
# ============================================================

SESSION = requests.Session()

SESSION.headers.update({

    "User-Agent":
        "Mozilla/5.0 Crypto AI PRO",

    "Accept":
        "application/json",

})


# ============================================================
# SAFE FLOAT
# ============================================================

def safe_float(
    value,
    default=0.0
):

    try:

        value = float(value)

        if np.isnan(value) or np.isinf(value):

            return default

        return value

    except Exception:

        return default


# ============================================================
# SYMBOL NORMALIZE
# ============================================================

def normalize_symbol(
    symbol
):

    if symbol is None:

        return ""

    symbol = str(
        symbol
    ).upper().strip()

    symbol = symbol.replace(
        "/",
        ""
    )

    symbol = symbol.replace(
        "_",
        ""
    )

    symbol = symbol.replace(
        "-",
        ""
    )

    return symbol


# ============================================================
# BASE ASSET
# ============================================================

def get_base_asset(
    symbol
):

    symbol = normalize_symbol(
        symbol
    )

    if symbol.endswith("TRY"):

        return symbol[:-3]

    if symbol.endswith("USDT"):

        return symbol[:-4]

    return ""


# ============================================================
# USDT / TRY KURU
# ============================================================

def get_usdt_try_rate():

    """
    USDT/TRY kurunu Binance TR'den almaya çalışır.

    Öncelik:
        USDTTRY

    Bulunamazsa:
        47.0 gibi sabit değer KULLANILMAZ.
        0 döndürülür.
    """

    endpoints = [

        f"{BINANCE_TR_API_URL}/api/v3/ticker/24hr",

        f"{BINANCE_TR_API_URL}/api/v1/ticker/24hr",

        f"{BINANCE_TR_BASE_URL}/api/v3/ticker/24hr",

        f"{BINANCE_TR_BASE_URL}/api/v1/ticker/24hr",

    ]

    for url in endpoints:

        try:

            response = SESSION.get(
                url,
                timeout=15
            )

            if response.status_code != 200:

                continue

            payload = response.json()

            if isinstance(
                payload,
                dict
            ):

                data = payload.get(
                    "data",
                    payload
                )

            else:

                data = payload

            if isinstance(
                data,
                dict
            ):

                data = [data]

            if not isinstance(
                data,
                list
            ):

                continue

            for item in data:

                if not isinstance(
                    item,
                    dict
                ):

                    continue

                raw_symbol = (

                    item.get(
                        "symbol"
                    )

                    or item.get(
                        "s"
                    )

                    or ""

                )

                symbol = normalize_symbol(
                    raw_symbol
                )

                if symbol != "USDTTRY":

                    continue

                price = safe_float(

                    item.get(
                        "lastPrice",
                        item.get(
                            "last",
                            item.get(
                                "c",
                                0
                            )
                        )
                    )

                )

                if price > 0:

                    print(
                        f"USDT/TRY kuru: {price:.4f}"
                    )

                    return price

        except Exception as e:

            print(
                "USDT/TRY hata:",
                e
            )

            continue

    print(
        "USDT/TRY kuru alınamadı."
    )

    return 0.0


# ============================================================
# BINANCE TR - MARKET TICKER
# ============================================================

def get_24h_ticker():

    """
    Binance TR market verilerini alır.

    TRY paritelerini döndürür.
    """

    endpoints = [

        f"{BINANCE_TR_API_URL}/api/v3/ticker/24hr",

        f"{BINANCE_TR_API_URL}/api/v1/ticker/24hr",

        f"{BINANCE_TR_BASE_URL}/api/v3/ticker/24hr",

        f"{BINANCE_TR_BASE_URL}/api/v1/ticker/24hr",

    ]

    for url in endpoints:

        try:

            response = SESSION.get(
                url,
                timeout=15
            )

            if response.status_code != 200:

                print(
                    f"TR Ticker HTTP "
                    f"{response.status_code}"
                )

                continue

            payload = response.json()

            if isinstance(
                payload,
                dict
            ):

                code = payload.get(
                    "code"
                )

                if code not in (
                    None,
                    0,
                    "0"
                ):

                    continue

                data = payload.get(
                    "data",
                    payload
                )

            else:

                data = payload

            if isinstance(
                data,
                dict
            ):

                data = [data]

            if not isinstance(
                data,
                list
            ):

                continue

            rows = []

            for item in data:

                if not isinstance(
                    item,
                    dict
                ):

                    continue

                raw_symbol = (

                    item.get(
                        "symbol"
                    )

                    or item.get(
                        "s"
                    )

                    or ""

                )

                symbol = normalize_symbol(
                    raw_symbol
                )

                if not symbol.endswith(
                    "TRY"
                ):

                    continue

                base_asset = get_base_asset(
                    symbol
                )

                if not base_asset:

                    continue

                if base_asset in EXCLUDED_COINS:

                    continue

                price = safe_float(

                    item.get(
                        "lastPrice",
                        item.get(
                            "last",
                            item.get(
                                "c",
                                0
                            )
                        )
                    )

                )

                change = safe_float(

                    item.get(
                        "priceChangePercent",
                        item.get(
                            "priceChangePercentage",
                            item.get(
                                "P",
                                0
                            )
                        )
                    )

                )

                volume_base = safe_float(

                    item.get(
                        "volume",
                        item.get(
                            "v",
                            0
                        )
                    )

                )

                quote_volume = safe_float(

                    item.get(
                        "quoteVolume",
                        item.get(
                            "q",
                            0
                        )
                    )

                )

                volume_try = quote_volume

                if volume_try <= 0:

                    volume_try = (
                        volume_base *
                        price
                    )

                high = safe_float(

                    item.get(
                        "highPrice",
                        item.get(
                            "h",
                            0
                        )
                    )

                )

                low = safe_float(

                    item.get(
                        "lowPrice",
                        item.get(
                            "l",
                            0
                        )
                    )

                )

                rows.append({

                    "symbol":
                        symbol,

                    "base_asset":
                        base_asset,

                    "price_try":
                        price,

                    "change_24h":
                        change,

                    "volume_try":
                        volume_try,

                    "high_24h":
                        high,

                    "low_24h":
                        low,

                    "source":
                        "BINANCE_TR",

                    "analysis_symbol":
                        symbol,

                    "quote_asset":
                        "TRY",

                })

            if rows:

                df = pd.DataFrame(
                    rows
                )

                df = (
                    df
                    .drop_duplicates(
                        subset=[
                            "base_asset"
                        ]
                    )
                    .reset_index(
                        drop=True
                    )
                )

                print(
                    "Binance TR ticker "
                    f"başarılı: {len(df)} coin"
                )

                return df

        except Exception as e:

            print(
                "TR ticker endpoint "
                f"hatası: {e}"
            )

            continue

    print(
        "Binance TR market verisi alınamadı."
    )

    return pd.DataFrame()


# ============================================================
# BINANCE GLOBAL - EXCHANGE INFO
# ============================================================

def get_global_spot_symbols():

    """
    Binance Global Spot'taki aktif USDT
    paritelerini bulur.
    """

    url = (
        f"{BINANCE_GLOBAL_API_URL}"
        "/api/v3/exchangeInfo"
    )

    try:

        response = SESSION.get(
            url,
            timeout=20
        )

        if response.status_code != 200:

            print(
                "Global exchangeInfo HTTP:",
                response.status_code
            )

            return []

        payload = response.json()

        symbols = payload.get(
            "symbols",
            []
        )

        result = []

        for item in symbols:

            if not isinstance(
                item,
                dict
            ):

                continue

            symbol = normalize_symbol(
                item.get(
                    "symbol"
                )
            )

            status = str(
                item.get(
                    "status",
                    ""
                )
            ).upper()

            quote_asset = str(
                item.get(
                    "quoteAsset",
                    ""
                )
            ).upper()

            base_asset = str(
                item.get(
                    "baseAsset",
                    ""
                )
            ).upper()

            if status != "TRADING":

                continue

            if quote_asset != "USDT":

                continue

            if not symbol.endswith(
                "USDT"
            ):

                continue

            if base_asset in EXCLUDED_COINS:

                continue

            result.append({

                "symbol":
                    symbol,

                "base_asset":
                    base_asset,

                "quote_asset":
                    "USDT",

            })

        print(
            "Binance Global aktif USDT "
            f"parite: {len(result)}"
        )

        return result

    except Exception as e:

        print(
            "Global exchangeInfo hata:",
            e
        )

        return []


# ============================================================
# BINANCE GLOBAL - 24H TICKER
# ============================================================

def get_global_24h_ticker():

    """
    Binance Global USDT ticker verilerini alır.
    """

    url = (
        f"{BINANCE_GLOBAL_API_URL}"
        "/api/v3/ticker/24hr"
    )

    try:

        response = SESSION.get(
            url,
            timeout=20
        )

        if response.status_code != 200:

            print(
                "Global ticker HTTP:",
                response.status_code
            )

            return pd.DataFrame()

        payload = response.json()

        if not isinstance(
            payload,
            list
        ):

            return pd.DataFrame()

        rows = []

        for item in payload:

            if not isinstance(
                item,
                dict
            ):

                continue

            symbol = normalize_symbol(
                item.get(
                    "symbol",
                    ""
                )
            )

            if not symbol.endswith(
                "USDT"
            ):

                continue

            base_asset = get_base_asset(
                symbol
            )

            if not base_asset:

                continue

            if base_asset in EXCLUDED_COINS:

                continue

            price_usdt = safe_float(

                item.get(
                    "lastPrice",
                    0
                )

            )

            if price_usdt <= 0:

                continue

            change = safe_float(

                item.get(
                    "priceChangePercent",
                    0
                )

            )

            volume_usdt = safe_float(

                item.get(
                    "quoteVolume",
                    0
                )

            )

            high_usdt = safe_float(

                item.get(
                    "highPrice",
                    0
                )

            )

            low_usdt = safe_float(

                item.get(
                    "lowPrice",
                    0
                )

            )

            rows.append({

                "symbol":
                    f"{base_asset}TRY",

                "analysis_symbol":
                    symbol,

                "base_asset":
                    base_asset,

                "price_usdt":
                    price_usdt,

                "change_24h":
                    change,

                "volume_usdt":
                    volume_usdt,

                "high_usdt":
                    high_usdt,

                "low_usdt":
                    low_usdt,

                "source":
                    "BINANCE_GLOBAL",

                "quote_asset":
                    "USDT",

            })

        if not rows:

            return pd.DataFrame()

        df = pd.DataFrame(
            rows
        )

        return df

    except Exception as e:

        print(
            "Global ticker hata:",
            e
        )

        return pd.DataFrame()


# ============================================================
# GLOBAL COINLERİ TRY'YE ÇEVİR
# ============================================================

def convert_global_to_try(
    df,
    usdt_try
):

    if df is None:

        return pd.DataFrame()

    if df.empty:

        return pd.DataFrame()

    if usdt_try <= 0:

        print(
            "Global coinler TRY'ye "
            "çevrilemedi: USDT/TRY yok."
        )

        return pd.DataFrame()

    result = df.copy()

    result["price_try"] = (

        pd.to_numeric(
            result["price_usdt"],
            errors="coerce"
        )
        .fillna(0)
        *
        usdt_try

    )

    result["volume_try"] = (

        pd.to_numeric(
            result["volume_usdt"],
            errors="coerce"
        )
        .fillna(0)
        *
        usdt_try

    )

    result["high_24h"] = (

        pd.to_numeric(
            result["high_usdt"],
            errors="coerce"
        )
        .fillna(0)
        *
        usdt_try

    )

    result["low_24h"] = (

        pd.to_numeric(
            result["low_usdt"],
            errors="coerce"
        )
        .fillna(0)
        *
        usdt_try

    )

    return result[[
        "symbol",
        "analysis_symbol",
        "base_asset",
        "price_try",
        "change_24h",
        "volume_try",
        "high_24h",
        "low_24h",
        "source",
        "quote_asset",
    ]].copy()


# ============================================================
# BİRLEŞİK KRİPTO EVRENİ
# ============================================================

def get_all_crypto_universe():

    """
    Binance TR + Binance Global birleşik evren.

    Öncelik:
        1. Binance TR TRY
        2. Global USDT

    Aynı coin her iki yerde varsa
    Binance TR tercih edilir.
    """

    print()
    print(
        "=========================================="
    )
    print(
        "CRYPTO AI PRO - BİRLEŞİK EVREN"
    )
    print(
        "=========================================="
    )

    # --------------------------------------------------------
    # TR
    # --------------------------------------------------------

    tr_df = get_24h_ticker()

    # --------------------------------------------------------
    # USDT/TRY
    # --------------------------------------------------------

    usdt_try = get_usdt_try_rate()

    # --------------------------------------------------------
    # GLOBAL
    # --------------------------------------------------------

    global_df = get_global_24h_ticker()

    global_try = convert_global_to_try(
        global_df,
        usdt_try
    )

    # --------------------------------------------------------
    # GLOBAL + TR
    # --------------------------------------------------------

    frames = []

    if not tr_df.empty:

        frames.append(
            tr_df
        )

    if not global_try.empty:

        frames.append(
            global_try
        )

    if not frames:

        print(
            "Birleşik evren boş."
        )

        return pd.DataFrame()

    combined = pd.concat(
        frames,
        ignore_index=True
    )

    # --------------------------------------------------------
    # TR ÖNCELİKLİ
    # --------------------------------------------------------

    combined["_source_priority"] = (
        combined["source"]
        .map({
            "BINANCE_TR": 0,
            "BINANCE_GLOBAL": 1,
        })
        .fillna(9)
    )

    combined = (

        combined
        .sort_values(
            [
                "base_asset",
                "_source_priority",
                "volume_try",
            ],
            ascending=[
                True,
                True,
                False,
            ]
        )

    )

    # Aynı coin varsa TR kalır.
    combined = (

        combined
        .drop_duplicates(
            subset=[
                "base_asset"
            ],
            keep="first"
        )

        .drop(
            columns=[
                "_source_priority"
            ],
            errors="ignore"
        )

        .sort_values(
            "volume_try",
            ascending=False
        )

        .reset_index(
            drop=True
        )

    )

    print(
        f"TR coin sayısı: "
        f"{len(tr_df)}"
    )

    print(
        f"Global coin sayısı: "
        f"{len(global_try)}"
    )

    print(
        f"Birleşik coin sayısı: "
        f"{len(combined)}"
    )

    # --------------------------------------------------------
    # TUT KONTROL
    # --------------------------------------------------------

    tut = combined[
        combined["base_asset"]
        == "TUT"
    ]

    if not tut.empty:

        print(
            "✅ TUT birleşik evrende bulundu."
        )

        print(
            tut[
                [
                    "base_asset",
                    "price_try",
                    "change_24h",
                    "volume_try",
                    "source",
                    "analysis_symbol",
                ]
            ]
            .to_string(
                index=False
            )
        )

    else:

        print(
            "⚠️ TUT birleşik evrende bulunamadı."
        )

    return combined


# ============================================================
# GERİYE DÖNÜK UYUMLULUK
# ============================================================

def get_all_try_universe():

    """
    Eski fonksiyon adı korunuyor.

    Artık:
        Binance TR TRY
        +
        Binance Global USDT -> TRY

    birleşik evren döndürür.
    """

    return get_all_crypto_universe()


# ============================================================
# TRADE UNIVERSE
# ============================================================

def get_trade_universe(
    min_volume=MIN_VOLUME_TRY
):

    df = get_all_crypto_universe()

    if df.empty:

        return pd.DataFrame()

    df["volume_try"] = pd.to_numeric(
        df["volume_try"],
        errors="coerce"
    ).fillna(0)

    # --------------------------------------------------------
    # HACİM FİLTRESİ
    # --------------------------------------------------------

    df = df[
        df["volume_try"]
        >= min_volume
    ].copy()

    # --------------------------------------------------------
    # SIRALA
    # --------------------------------------------------------

    df = (
        df
        .sort_values(
            "volume_try",
            ascending=False
        )
        .reset_index(
            drop=True
        )
    )

    print(
        f"Likidite filtresi sonrası: "
        f"{len(df)} coin"
    )

    # --------------------------------------------------------
    # TUT KONTROL
    # --------------------------------------------------------

    tut = df[
        df["base_asset"]
        == "TUT"
    ]

    if not tut.empty:

        print(
            "✅ TUT likidite filtresini geçti."
        )

    else:

        print(
            "ℹ️ TUT likidite filtresini "
            "geçemedi veya bulunamadı."
        )

    return df


# ============================================================
# KLINE - BINANCE TR
# ============================================================

def get_klines_tr(
    symbol,
    interval=INTERVAL,
    limit=KLINE_LIMIT
):

    symbol = normalize_symbol(
        symbol
    )

    if not symbol.endswith(
        "TRY"
    ):

        return pd.DataFrame()

    endpoints = [

        f"{BINANCE_TR_API_URL}/api/v3/klines",

        f"{BINANCE_TR_API_URL}/api/v1/klines",

        f"{BINANCE_TR_BASE_URL}/api/v3/klines",

        f"{BINANCE_TR_BASE_URL}/api/v1/klines",

    ]

    params = {

        "symbol":
            symbol,

        "interval":
            interval,

        "limit":
            limit,

    }

    for url in endpoints:

        try:

            response = SESSION.get(
                url,
                params=params,
                timeout=15
            )

            if response.status_code != 200:

                continue

            payload = response.json()

            if isinstance(
                payload,
                dict
            ):

                code = payload.get(
                    "code"
                )

                if code not in (
                    None,
                    0,
                    "0"
                ):

                    continue

                data = payload.get(
                    "data",
                    []
                )

            else:

                data = payload

            if not isinstance(
                data,
                list
            ):

                continue

            if not data:

                continue

            rows = []

            for item in data:

                if not isinstance(
                    item,
                    (list, tuple)
                ):

                    continue

                if len(item) < 6:

                    continue

                rows.append(
                    item
                )

            if not rows:

                continue

            columns = [

                "open_time",
                "open",
                "high",
                "low",
                "close",
                "volume",
                "close_time",
                "quote_volume",
                "trades",
                "taker_buy_base",
                "taker_buy_quote",
                "ignore"

            ]

            max_cols = min(
                len(rows[0]),
                len(columns)
            )

            rows = [

                list(
                    row[:max_cols]
                )

                for row in rows

            ]

            df = pd.DataFrame(

                rows,

                columns=
                    columns[:max_cols]

            )

            required = [

                "open_time",
                "open",
                "high",
                "low",
                "close",
                "volume",

            ]

            if not all(
                col in df.columns
                for col in required
            ):

                continue

            numeric_cols = [

                "open",
                "high",
                "low",
                "close",
                "volume",
                "quote_volume",
                "trades",
                "taker_buy_base",
                "taker_buy_quote",

            ]

            for col in numeric_cols:

                if col in df.columns:

                    df[col] = pd.to_numeric(
                        df[col],
                        errors="coerce"
                    )

            df["open_time"] = pd.to_datetime(

                pd.to_numeric(
                    df["open_time"],
                    errors="coerce"
                ),

                unit="ms"

            )

            if "close_time" in df.columns:

                df["close_time"] = pd.to_datetime(

                    pd.to_numeric(
                        df["close_time"],
                        errors="coerce"
                    ),

                    unit="ms"

                )

            df = df.dropna(

                subset=[
                    "open",
                    "high",
                    "low",
                    "close",
                    "volume"
                ]

            )

            df = (

                df
                .sort_values(
                    "open_time"
                )
                .drop_duplicates(
                    subset=[
                        "open_time"
                    ]
                )
                .reset_index(
                    drop=True
                )

            )

            if len(df) < 10:

                continue

            return df

        except Exception as e:

            print(
                f"{symbol} TR kline hata: "
                f"{e}"
            )

            continue

    return pd.DataFrame()


# ============================================================
# KLINE - BINANCE GLOBAL
# ============================================================

def get_klines_global(
    symbol,
    interval=INTERVAL,
    limit=KLINE_LIMIT
):

    symbol = normalize_symbol(
        symbol
    )

    if not symbol.endswith(
        "USDT"
    ):

        return pd.DataFrame()

    url = (
        f"{BINANCE_GLOBAL_API_URL}"
        "/api/v3/klines"
    )

    params = {

        "symbol":
            symbol,

        "interval":
            interval,

        "limit":
            limit,

    }

    try:

        response = SESSION.get(
            url,
            params=params,
            timeout=20
        )

        if response.status_code != 200:

            print(
                f"{symbol} Global HTTP "
                f"{response.status_code}"
            )

            return pd.DataFrame()

        data = response.json()

        if not isinstance(
            data,
            list
        ):

            return pd.DataFrame()

        rows = []

        for item in data:

            if not isinstance(
                item,
                (list, tuple)
            ):

                continue

            if len(item) < 6:

                continue

            rows.append(
                item
            )

        if not rows:

            return pd.DataFrame()

        columns = [

            "open_time",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "close_time",
            "quote_volume",
            "trades",
            "taker_buy_base",
            "taker_buy_quote",
            "ignore"

        ]

        max_cols = min(
            len(rows[0]),
            len(columns)
        )

        rows = [

            list(
                row[:max_cols]
            )

            for row in rows

        ]

        df = pd.DataFrame(

            rows,

            columns=
                columns[:max_cols]

        )

        numeric_cols = [

            "open",
            "high",
            "low",
            "close",
            "volume",
            "quote_volume",
            "trades",
            "taker_buy_base",
            "taker_buy_quote",

        ]

        for col in numeric_cols:

            if col in df.columns:

                df[col] = pd.to_numeric(
                    df[col],
                    errors="coerce"
                )

        df["open_time"] = pd.to_datetime(

            pd.to_numeric(
                df["open_time"],
                errors="coerce"
            ),

            unit="ms"

        )

        if "close_time" in df.columns:

            df["close_time"] = pd.to_datetime(

                pd.to_numeric(
                    df["close_time"],
                    errors="coerce"
                ),

                unit="ms"

            )

        df = df.dropna(

            subset=[
                "open",
                "high",
                "low",
                "close",
                "volume"
            ]

        )

        df = (

            df
            .sort_values(
                "open_time"
            )
            .drop_duplicates(
                subset=[
                    "open_time"
                ]
            )
            .reset_index(
                drop=True
            )

        )

        if len(df) < 10:

            return pd.DataFrame()

        return df

    except Exception as e:

        print(
            f"{symbol} Global kline hata: "
            f"{e}"
        )

        return pd.DataFrame()


# ============================================================
# GENEL KLINE
# ============================================================

def get_klines(
    symbol,
    interval=INTERVAL,
    limit=KLINE_LIMIT,
    source=None
):

    """
    Hem Binance TR hem Binance Global destekler.

    TUTTRY gibi sentetik TRY sembolü gelirse
    globalde TUTUSDT aranır.
    """

    symbol = normalize_symbol(
        symbol
    )

    # --------------------------------------------------------
    # SOURCE BELİRTİLMİŞSE
    # --------------------------------------------------------

    if source == "BINANCE_TR":

        return get_klines_tr(
            symbol,
            interval,
            limit
        )

    if source == "BINANCE_GLOBAL":

        base = get_base_asset(
            symbol
        )

        if not base:

            return pd.DataFrame()

        global_symbol = (
            f"{base}USDT"
        )

        return get_klines_global(
            global_symbol,
            interval,
            limit
        )

    # --------------------------------------------------------
    # NORMAL TRY
    # --------------------------------------------------------

    if symbol.endswith(
        "TRY"
    ):

        df = get_klines_tr(
            symbol,
            interval,
            limit
        )

        if not df.empty:

            return df

        # TR'de yoksa Global dene

        base = get_base_asset(
            symbol
        )

        if base:

            return get_klines_global(

                f"{base}USDT",

                interval,

                limit

            )

    # --------------------------------------------------------
    # USDT
    # --------------------------------------------------------

    if symbol.endswith(
        "USDT"
    ):

        return get_klines_global(
            symbol,
            interval,
            limit
        )

    return pd.DataFrame()


# ============================================================
# EMA
# ============================================================

def calculate_ema(
    df,
    period
):

    return (

        df["close"]
        .ewm(
            span=period,
            adjust=False
        )
        .mean()

    )


# ============================================================
# RSI
# ============================================================

def calculate_rsi(
    df,
    period=14
):

    delta = df["close"].diff()

    gain = delta.clip(
        lower=0
    )

    loss = -delta.clip(
        upper=0
    )

    avg_gain = gain.ewm(

        alpha=1 / period,

        adjust=False

    ).mean()

    avg_loss = loss.ewm(

        alpha=1 / period,

        adjust=False

    ).mean()

    rs = (

        avg_gain /

        avg_loss.replace(
            0,
            np.nan
        )

    )

    rsi = (

        100 -

        (
            100 /
            (1 + rs)
        )

    )

    return (

        rsi
        .replace(
            [
                np.inf,
                -np.inf
            ],
            np.nan
        )
        .fillna(50)

    )


# ============================================================
# VWAP
# ============================================================

def calculate_vwap(
    df
):

    typical_price = (

        df["high"] +
        df["low"] +
        df["close"]

    ) / 3

    cumulative_volume = (

        df["volume"]
        .cumsum()

    )

    cumulative_pv = (

        typical_price *
        df["volume"]

    ).cumsum()

    return (

        cumulative_pv /

        cumulative_volume.replace(
            0,
            np.nan
        )

    )


# ============================================================
# VOLUME RATIO
# ============================================================

def calculate_volume_ratio(
    df,
    period=20
):

    avg_volume = (

        df["volume"]
        .rolling(
            period
        )
        .mean()

    )

    return (

        df["volume"] /

        avg_volume.replace(
            0,
            np.nan
        )

    )


# ============================================================
# SUPPORT / RESISTANCE
# ============================================================

def calculate_support_resistance(
    df,
    lookback=50
):

    recent = df.tail(
        lookback
    )

    if recent.empty:

        return 0.0, 0.0

    support = safe_float(
        recent["low"].min()
    )

    resistance = safe_float(
        recent["high"].max()
    )

    return support, resistance


# ============================================================
# MOMENTUM
# ============================================================

def calculate_momentum(
    df,
    period=20
):

    if len(df) < period:

        return 0.0

    current = safe_float(
        df["close"].iloc[-1]
    )

    previous = safe_float(
        df["close"].iloc[-period]
    )

    if previous <= 0:

        return 0.0

    return (

        (
            current /
            previous
        ) - 1

    ) * 100


# ============================================================
# TREND SCORE
# ============================================================

def calculate_trend_score(
    price,
    ema9,
    ema20,
    ema50
):

    score = 0

    if price > ema9:

        score += 20

    if ema9 > ema20:

        score += 25

    if ema20 > ema50:

        score += 25

    if price > ema50:

        score += 30

    return min(
        score,
        100
    )


# ============================================================
# RSI SCORE
# ============================================================

def calculate_rsi_score(
    rsi
):

    rsi = safe_float(
        rsi,
        50
    )

    if 50 <= rsi <= 65:

        return 100

    if 45 <= rsi < 50:

        return 75

    if 65 < rsi <= 70:

        return 70

    if 40 <= rsi < 45:

        return 55

    if 70 < rsi <= 75:

        return 40

    if rsi > 75:

        return 15

    return 30


# ============================================================
# VOLUME SCORE
# ============================================================

def calculate_volume_score(
    volume_ratio
):

    volume_ratio = safe_float(
        volume_ratio
    )

    if volume_ratio >= 2.0:

        return 100

    if volume_ratio >= 1.5:

        return 90

    if volume_ratio >= 1.2:

        return 75

    if volume_ratio >= 1.0:

        return 60

    if volume_ratio >= 0.8:

        return 40

    return 20


# ============================================================
# VWAP SCORE
# ============================================================

def calculate_vwap_score(
    price,
    vwap
):

    price = safe_float(
        price
    )

    vwap = safe_float(
        vwap
    )

    if vwap <= 0:

        return 50

    if price > vwap * 1.02:

        return 90

    if price > vwap:

        return 80

    if price >= vwap * 0.98:

        return 50

    return 20


# ============================================================
# RISK / REWARD
# ============================================================

def calculate_rr(
    price,
    support,
    resistance
):

    price = safe_float(
        price
    )

    support = safe_float(
        support
    )

    resistance = safe_float(
        resistance
    )

    if price <= 0:

        return 0.0

    if support <= 0:

        return 0.0

    if resistance <= 0:

        return 0.0

    if price <= support:

        return 0.0

    risk = price - support

    reward = resistance - price

    if risk <= 0:

        return 0.0

    if reward <= 0:

        return 0.0

    return reward / risk


# ============================================================
# MOMENTUM SCORE
# ============================================================

def calculate_momentum_score(
    momentum
):

    momentum = safe_float(
        momentum
    )

    if momentum >= 10:

        return 100

    if momentum >= 5:

        return 90

    if momentum >= 2:

        return 75

    if momentum >= 0:

        return 60

    if momentum >= -3:

        return 40

    return 20


# ============================================================
# R/R SCORE
# ============================================================

def calculate_rr_score(
    rr
):

    rr = safe_float(
        rr
    )

    if rr >= 3:

        return 100

    if rr >= 2:

        return 90

    if rr >= 1.5:

        return 75

    if rr >= 1:

        return 55

    return 20


# ============================================================
# TRADE SCORE
# ============================================================

def calculate_trade_score(
    trend_score,
    rsi_score,
    volume_score,
    vwap_score,
    momentum,
    rr
):

    momentum_score = (
        calculate_momentum_score(
            momentum
        )
    )

    rr_score = (
        calculate_rr_score(
            rr
        )
    )

    score = (

        trend_score * 0.30

        + rsi_score * 0.15

        + volume_score * 0.15

        + vwap_score * 0.15

        + momentum_score * 0.10

        + rr_score * 0.15

    )

    return round(

        min(
            max(
                score,
                0
            ),
            100
        ),

        2

    )


# ============================================================
# CLASSIFICATION
# ============================================================

def classify_trade(
    score
):

    score = safe_float(
        score
    )

    if score >= 80:

        return "🟢 A"

    if score >= 65:

        return "🟡 B"

    if score >= 50:

        return "🟠 C"

    return "🔴 ZAYIF"


# ============================================================
# TRADE DECISION
# ============================================================

def trade_decision(
    score,
    trend_score,
    rsi,
    price,
    vwap,
    rr,
    volume_ratio
):

    score = safe_float(
        score
    )

    trend_score = safe_float(
        trend_score
    )

    rsi = safe_float(
        rsi
    )

    price = safe_float(
        price
    )

    vwap = safe_float(
        vwap
    )

    rr = safe_float(
        rr
    )

    volume_ratio = safe_float(
        volume_ratio
    )

    if (

        score >= 80

        and trend_score >= 70

        and 50 <= rsi <= 70

        and price > vwap

        and rr >= 1.5

        and volume_ratio >= 1.2

    ):

        return "🟢 GÜÇLÜ TRADE"

    if (

        score >= 65

        and trend_score >= 60

        and price > vwap

        and rr >= 1

    ):

        return "🟡 TRADE ADAYI"

    if score >= 50:

        return "🟠 İZLE"

    return "🔴 UYGUN DEĞİL"


# ============================================================
# TEK COIN ANALİZ
# ============================================================

def analyze_coin(
    symbol,
    market_data=None
):

    """
    Tek coin analiz eder.

    Hem Binance TR hem Global desteklenir.
    """

    symbol = normalize_symbol(
        symbol
    )

    # --------------------------------------------------------
    # MARKET DATA BUL
    # --------------------------------------------------------

    market = {}

    if market_data is not None:

        if isinstance(
            market_data,
            pd.DataFrame
        ):

            if "base_asset" in market_data.columns:

                base_for_search = (
                    get_base_asset(symbol)
                )

                match = market_data[

                    market_data[
                        "base_asset"
                    ]
                    .astype(str)
                    .str.upper()
                    == base_for_search

                ]

                if not match.empty:

                    market = (
                        match
                        .iloc[0]
                        .to_dict()
                    )

            elif "symbol" in market_data.columns:

                match = market_data[

                    market_data[
                        "symbol"
                    ]
                    .astype(str)
                    .map(
                        normalize_symbol
                    )
                    == symbol

                ]

                if not match.empty:

                    market = (
                        match
                        .iloc[0]
                        .to_dict()
                    )

        elif isinstance(
            market_data,
            dict
        ):

            market = market_data

    # --------------------------------------------------------
    # BASE
    # --------------------------------------------------------

    base_asset = (

        market.get(
            "base_asset"
        )

        or get_base_asset(
            symbol
        )

    )

    base_asset = str(
        base_asset
    ).upper()

    if not base_asset:

        return None

    if base_asset in EXCLUDED_COINS:

        return None

    # --------------------------------------------------------
    # MARKET SOURCE
    # --------------------------------------------------------

    source = market.get(
        "source",
        None
    )

    # --------------------------------------------------------
    # HACİM
    # --------------------------------------------------------

    volume_try = safe_float(
        market.get(
            "volume_try",
            0
        )
    )

    if (

        volume_try > 0

        and volume_try < MIN_VOLUME_TRY

    ):

        return None

    # --------------------------------------------------------
    # KLINE
    # --------------------------------------------------------

    if source == "BINANCE_GLOBAL":

        analysis_symbol = market.get(
            "analysis_symbol"
        )

        if not analysis_symbol:

            analysis_symbol = (
                f"{base_asset}USDT"
            )

        df = get_klines_global(
            analysis_symbol
        )

    else:

        analysis_symbol = market.get(
            "analysis_symbol"
        )

        if not analysis_symbol:

            analysis_symbol = (
                f"{base_asset}TRY"
            )

        df = get_klines(
            analysis_symbol,
            source=source
        )

    if df.empty:

        return None

    if len(df) < 60:

        return None

    # --------------------------------------------------------
    # INDICATORS
    # --------------------------------------------------------

    df["ema9"] = calculate_ema(
        df,
        9
    )

    df["ema20"] = calculate_ema(
        df,
        20
    )

    df["ema50"] = calculate_ema(
        df,
        50
    )

    df["rsi"] = calculate_rsi(
        df
    )

    df["vwap"] = calculate_vwap(
        df
    )

    df["volume_ratio"] = (
        calculate_volume_ratio(
            df
        )
    )

    # --------------------------------------------------------
    # CURRENT
    # --------------------------------------------------------

    row = df.iloc[-1]

    price_market = safe_float(
        row["close"]
    )

    ema9 = safe_float(
        row["ema9"]
    )

    ema20 = safe_float(
        row["ema20"]
    )

    ema50 = safe_float(
        row["ema50"]
    )

    rsi = safe_float(
        row["rsi"],
        50
    )

    vwap_market = safe_float(
        row["vwap"]
    )

    volume_ratio = safe_float(
        row["volume_ratio"],
        0
    )

    # --------------------------------------------------------
    # TRY DÖNÜŞÜMÜ
    # --------------------------------------------------------

    if source == "BINANCE_GLOBAL":

        usdt_try = get_usdt_try_rate()

        if usdt_try <= 0:

            return None

        price = (
            price_market *
            usdt_try
        )

        vwap = (
            vwap_market *
            usdt_try
        )

    else:

        price = price_market

        vwap = vwap_market

    # --------------------------------------------------------
    # MOMENTUM
    # --------------------------------------------------------

    momentum = calculate_momentum(
        df
    )

    # --------------------------------------------------------
    # SUPPORT / RESISTANCE
    # --------------------------------------------------------

    support_market, resistance_market = (

        calculate_support_resistance(
            df,
            lookback=50
        )

    )

    if source == "BINANCE_GLOBAL":

        support = (
            support_market *
            usdt_try
        )

        resistance = (
            resistance_market *
            usdt_try
        )

    else:

        support = support_market

        resistance = resistance_market

    # --------------------------------------------------------
    # R/R
    # --------------------------------------------------------

    rr = calculate_rr(
        price,
        support,
        resistance
    )

    # --------------------------------------------------------
    # SCORES
    # --------------------------------------------------------

    trend_score = (
        calculate_trend_score(
            price_market,
            ema9,
            ema20,
            ema50
        )
    )

    rsi_score = (
        calculate_rsi_score(
            rsi
        )
    )

    volume_score = (
        calculate_volume_score(
            volume_ratio
        )
    )

    vwap_score = (
        calculate_vwap_score(
            price_market,
            vwap_market
        )
    )

    trade_score = (
        calculate_trade_score(
            trend_score,
            rsi_score,
            volume_score,
            vwap_score,
            momentum,
            rr
        )
    )

    classification = classify_trade(
        trade_score
    )

    decision = trade_decision(
        trade_score,
        trend_score,
        rsi,
        price,
        vwap,
        rr,
        volume_ratio
    )

    # --------------------------------------------------------
    # 15M CHANGE
    # --------------------------------------------------------

    change_15m = 0.0

    if len(df) >= 2:

        previous = safe_float(
            df["close"].iloc[-2]
        )

        if previous > 0:

            change_15m = (

                (
                    price_market /
                    previous
                ) - 1

            ) * 100

    # --------------------------------------------------------
    # RESULT
    # --------------------------------------------------------

    return {

        "symbol":
            base_asset,

        "pair":
            market.get(
                "symbol",
                f"{base_asset}TRY"
            ),

        "analysis_symbol":
            analysis_symbol,

        "source":
            source,

        "price":
            round(
                price,
                8
            ),

        "change_15m":
            round(
                change_15m,
                2
            ),

        "change_24h":
            round(
                safe_float(
                    market.get(
                        "change_24h",
                        0
                    )
                ),
                2
            ),

        "volume_try":
            round(
                volume_try,
                2
            ),

        "momentum":
            round(
                momentum,
                2
            ),

        "ema9":
            round(
                ema9,
                8
            ),

        "ema20":
            round(
                ema20,
                8
            ),

        "ema50":
            round(
                ema50,
                8
            ),

        "rsi":
            round(
                rsi,
                2
            ),

        "vwap":
            round(
                vwap,
                8
            ),

        "volume_ratio":
            round(
                volume_ratio,
                2
            ),

        "support":
            round(
                support,
                8
            ),

        "resistance":
            round(
                resistance,
                8
            ),

        "rr":
            round(
                rr,
                2
            ),

        "trend_score":
            round(
                trend_score,
                2
            ),

        "rsi_score":
            round(
                rsi_score,
                2
            ),

        "volume_score":
            round(
                volume_score,
                2
            ),

        "vwap_score":
            round(
                vwap_score,
                2
            ),

        "trade_score":
            trade_score,

        "class":
            classification,

        "decision":
            decision,

        "analysis_time":
            datetime.now(),

    }


# ============================================================
# TÜM COINLERİ SIRALA
# ============================================================

def rank_coins(
    symbols=None,
    min_volume=MIN_VOLUME_TRY
):

    """
    Binance TR + Binance Global
    birleşik evreni tarar.
    """

    market_df = get_trade_universe(
        min_volume=min_volume
    )

    if market_df.empty:

        print(
            "Trade universe boş."
        )

        return pd.DataFrame()

    # --------------------------------------------------------
    # SYMBOL LIST
    # --------------------------------------------------------

    if symbols is None:

        market_symbols = (

            market_df[
                "base_asset"
            ]
            .dropna()
            .astype(str)
            .str.upper()
            .drop_duplicates()
            .tolist()

        )

    else:

        market_symbols = [

            str(s)
            .upper()
            .strip()

            for s in symbols

            if str(s).strip()

        ]

        # Base asset veya parite kabul et

        normalized = []

        for s in market_symbols:

            if s.endswith("TRY"):

                normalized.append(
                    s[:-3]
                )

            elif s.endswith("USDT"):

                normalized.append(
                    s[:-4]
                )

            else:

                normalized.append(
                    s
                )

        market_symbols = list(
            dict.fromkeys(
                normalized
            )
        )

    # --------------------------------------------------------
    # MAX ANALYSIS
    # --------------------------------------------------------

    # Önce priority coinler
    priority = [

        coin

        for coin
        in PRIORITY_GLOBAL_COINS

        if coin in market_symbols

    ]

    normal = [

        coin

        for coin in market_symbols

        if coin not in priority

    ]

    normal = normal[
        :MAX_ANALYSIS_COINS
    ]

    symbols = priority + normal

    # --------------------------------------------------------
    # ANALİZ
    # --------------------------------------------------------

    results = []

    total = len(
        symbols
    )

    print()
    print(
        "=========================================="
    )
    print(
        "CRYPTO AI PRO TARAMA"
    )
    print(
        f"Analiz edilecek coin: {total}"
    )
    print(
        "=========================================="
    )

    for i, base in enumerate(
        symbols,
        start=1
    ):

        print(
            f"[{i}/{total}] {base}"
        )

        # ----------------------------------------------------
        # Market satırı
        # ----------------------------------------------------

        match = market_df[

            market_df[
                "base_asset"
            ]
            .astype(str)
            .str.upper()
            == base

        ]

        if match.empty:

            continue

        market_row = (
            match
            .iloc[0]
            .to_dict()
        )

        try:

            result = analyze_coin(
                market_row.get(
                    "symbol",
                    f"{base}TRY"
                ),
                market_data=market_df
            )

            if result is not None:

                results.append(
                    result
                )

        except Exception as e:

            print(
                f"{base} analiz hatası: "
                f"{e}"
            )

            continue

    # --------------------------------------------------------
    # SONUÇ
    # --------------------------------------------------------

    if not results:

        print(
            "Hiçbir coin analiz edilemedi."
        )

        return pd.DataFrame()

    result_df = pd.DataFrame(
        results
    )

    result_df = (

        result_df

        .sort_values(
            [
                "trade_score",
                "volume_try"
            ],

            ascending=[
                False,
                False
            ]

        )

        .reset_index(
            drop=True
        )

    )

    print()
    print(
        "=========================================="
    )
    print(
        "CRYPTO AI TARAMA TAMAMLANDI"
    )
    print(
        f"{len(result_df)} coin analiz edildi"
    )
    print(
        "=========================================="
    )

    # --------------------------------------------------------
    # TUT SONUÇ
    # --------------------------------------------------------

    tut_result = result_df[
        result_df["symbol"]
        == "TUT"
    ]

    if not tut_result.empty:

        print()
        print(
            "=========================================="
        )
        print(
            "✅ TUT ANALİZ SONUCU"
        )
        print(
            "=========================================="
        )

        print(
            tut_result[
                [
                    "symbol",
                    "price",
                    "change_24h",
                    "rsi",
                    "volume_ratio",
                    "rr",
                    "trend_score",
                    "trade_score",
                    "class",
                    "decision",
                    "source",
                ]
            ]
            .to_string(
                index=False
            )
        )

    return result_df


# ============================================================
# TRADE ADAYLARI
# ============================================================

def get_trade_candidates(
    symbols=None
):

    df = rank_coins(
        symbols
    )

    if df.empty:

        return df

    candidates = df[
        df["trade_score"] >= 65
    ].copy()

    return (

        candidates
        .reset_index(
            drop=True
        )

    )


# ============================================================
# A SINIFI
# ============================================================

def get_a_trades(
    symbols=None
):

    df = rank_coins(
        symbols
    )

    if df.empty:

        return df

    result = df[

        (
            df["trade_score"]
            >= 80
        )

        &

        (
            df["decision"]
            ==
            "🟢 GÜÇLÜ TRADE"
        )

    ].copy()

    return (

        result
        .reset_index(
            drop=True
        )

    )


# ============================================================
# TOP N
# ============================================================

def get_top_trades(
    symbols=None,
    n=10
):

    df = rank_coins(
        symbols
    )

    if df.empty:

        return df

    return (

        df
        .head(n)
        .reset_index(
            drop=True
        )

    )


# ============================================================
# STRONG TRADES
# ============================================================

def get_strong_trades(
    symbols=None
):

    df = rank_coins(
        symbols
    )

    if df.empty:

        return df

    result = df[

        df["decision"]
        ==
        "🟢 GÜÇLÜ TRADE"

    ].copy()

    return (

        result
        .reset_index(
            drop=True
        )

    )


# ============================================================
# MARKET SUMMARY
# ============================================================

def get_market_summary():

    df = get_trade_universe()

    if df.empty:

        return {

            "total_pairs":
                0,

            "liquid_pairs":
                0,

            "total_volume_try":
                0,

            "top_coin":
                None,

        }

    total_volume = safe_float(

        df[
            "volume_try"
        ].sum()

    )

    top_coin = None

    if not df.empty:

        top_coin = (

            df.iloc[0]
            ["base_asset"]

        )

    return {

        "total_pairs":
            len(df),

        "liquid_pairs":
            len(df),

        "total_volume_try":
            total_volume,

        "top_coin":
            top_coin,

    }


# ============================================================
# TUT KONTROL
# ============================================================

def check_tut():

    """
    TUT coinini özel olarak kontrol eder.

    Sonuç:
        True / False
    """

    df = get_all_crypto_universe()

    if df.empty:

        return False

    tut = df[
        df["base_asset"]
        == "TUT"
    ]

    if tut.empty:

        print(
            "❌ TUT bulunamadı."
        )

        return False

    print()
    print(
        "=========================================="
    )
    print(
        "✅ TUT BULUNDU"
    )
    print(
        "=========================================="
    )

    print(

        tut[
            [
                "base_asset",
                "symbol",
                "analysis_symbol",
                "price_try",
                "change_24h",
                "volume_try",
                "source",
            ]
        ]
        .to_string(
            index=False
        )

    )

    return True


# ============================================================
# CONNECTION TEST
# ============================================================

def test_binance_tr():

    print()
    print(
        "=========================================="
    )
    print(
        "BINANCE TR / GLOBAL BAĞLANTI TESTİ"
    )
    print(
        "=========================================="
    )

    df = get_all_crypto_universe()

    if df.empty:

        print(
            "❌ Veri alınamadı."
        )

        return False

    print()
    print(
        f"✅ Birleşik coin sayısı: "
        f"{len(df)}"
    )

    print()

    print(
        df[
            [
                "base_asset",
                "price_try",
                "change_24h",
                "volume_try",
                "source",
            ]
        ]
        .head(15)
        .to_string(
            index=False
        )
    )

    print()

    check_tut()

    print()
    print(
        "✅ Bağlantı sistemi çalışıyor."
    )

    return True


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    print()

    print(
        "=========================================="
    )

    print(
        "       CRYPTO AI PRO ENGINE TEST"
    )

    print(
        "=========================================="
    )

    print()

    # --------------------------------------------------------
    # 1. BAĞLANTI
    # --------------------------------------------------------

    if not test_binance_tr():

        print(
            "API testi başarısız."
        )

        raise SystemExit

    # --------------------------------------------------------
    # 2. TRADE UNIVERSE
    # --------------------------------------------------------

    market = get_trade_universe()

    print()

    print(
        f"Likidite evreni: "
        f"{len(market)}"
    )

    # --------------------------------------------------------
    # 3. TUT
    # --------------------------------------------------------

    print()

    check_tut()

    # --------------------------------------------------------
    # 4. TOP TRADES
    # --------------------------------------------------------

    print()

    top = get_top_trades(
        n=10
    )

    if top.empty:

        print(
            "Trade adayı bulunamadı."
        )

    else:

        print()
        print(
            "=========================================="
        )
        print(
            "TOP 10 CRYPTO TRADE"
        )
        print(
            "=========================================="
        )
        print()

        print(

            top[
                [
                    "symbol",
                    "price",
                    "change_24h",
                    "rsi",
                    "volume_ratio",
                    "rr",
                    "trend_score",
                    "trade_score",
                    "class",
                    "decision",
                    "source",
                ]
            ]
            .to_string(
                index=False
            )

        )