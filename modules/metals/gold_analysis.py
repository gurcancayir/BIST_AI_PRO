"""
============================================================
BIST AI PRO - ALTIN ANALİZ MOTORU V3
============================================================

Amaç
-----
Gram altın için:

1. Teknik yapı
2. Trend
3. Momentum
4. Ons altın katkısı
5. USD/TRY katkısı
6. Destek / direnç bölgeleri
7. İşlem stopu
8. Hedef 1 / Hedef 2
9. Risk / Getiri
10. Alım / satış teyitleri
11. Otomatik karar

üretmek.

ÖNEMLİ TASARIM KARARI
---------------------
Ana destek ile işlem stopu aynı şey değildir.

ANA DESTEK:
    Piyasanın önemli teknik destek bölgesi.

İŞLEM STOPU:
    Mevcut giriş fiyatından yapılacak işlem için
    teknik yapıyı bozan daha yakın risk seviyesi.

HEDEF 1:
    İlk anlamlı direnç.

HEDEF 2:
    Bir sonraki anlamlı direnç.

Risk/Getiri:
    Hedef - Giriş
    ----------------
    Giriş - Stop

üzerinden hesaplanır.

Genel skor tek başına AL değildir.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd
import yfinance as yf


# ============================================================
# VERİ KAYNAKLARI
# ============================================================

GOLD_SYMBOL = "GC=F"
USDTRY_SYMBOL = "USDTRY=X"

DEFAULT_PERIOD = "2y"
DEFAULT_INTERVAL = "1d"

MIN_ROWS = 220

TROY_OUNCE_GRAM = 31.1034768


# ============================================================
# GENEL SKOR AĞIRLIKLARI
# ============================================================

W_TREND = 0.30
W_MOMENTUM = 0.25
W_TECHNICAL = 0.25
W_RISK = 0.20


# ============================================================
# ATR / STOP PARAMETRELERİ
# ============================================================

ATR_STOP_MULTIPLIER = 0.75

MIN_STOP_DISTANCE_PCT = 0.75
MAX_STOP_DISTANCE_PCT = 6.00

TARGET_1_MIN_DISTANCE_PCT = 0.50


# ============================================================
# SONUÇ SINIFI
# ============================================================

@dataclass
class GoldAnalysisResult:

    ok: bool

    error: Optional[str]

    data: pd.DataFrame

    result: Dict[str, Any]


# ============================================================
# YARDIMCI VERİ FONKSİYONLARI
# ============================================================

def _flat(df: pd.DataFrame) -> pd.DataFrame:

    if isinstance(df.columns, pd.MultiIndex):

        df.columns = [
            c[0] if isinstance(c, tuple) else c
            for c in df.columns
        ]

    return df


def _clean(df: pd.DataFrame) -> pd.DataFrame:

    if df is None or df.empty:
        return pd.DataFrame()

    df = _flat(df.copy())

    required = [
        "Open",
        "High",
        "Low",
        "Close",
    ]

    if any(c not in df.columns for c in required):
        return pd.DataFrame()

    for c in [
        "Open",
        "High",
        "Low",
        "Close",
        "Volume",
    ]:

        if c in df.columns:

            df[c] = pd.to_numeric(
                df[c],
                errors="coerce",
            )

    if "Volume" not in df.columns:

        df["Volume"] = 0.0

    df = df.dropna(
        subset=required
    )

    df = df[
        ~df.index.duplicated(
            keep="last"
        )
    ]

    df = df.sort_index()

    return df


def fetch(
    symbol: str,
    period: str = DEFAULT_PERIOD,
    interval: str = DEFAULT_INTERVAL,
) -> pd.DataFrame:

    try:

        ticker = yf.Ticker(symbol)

        df = ticker.history(
            period=period,
            interval=interval,
            auto_adjust=False,
            actions=False,
        )

        return _clean(df)

    except Exception:

        return pd.DataFrame()


# ============================================================
# TEKNİK GÖSTERGELER
# ============================================================

def _ema(
    series: pd.Series,
    period: int,
) -> pd.Series:

    return series.ewm(
        span=period,
        adjust=False,
    ).mean()


def _rsi(
    close: pd.Series,
    period: int = 14,
) -> pd.Series:

    delta = close.diff()

    gain = delta.clip(
        lower=0
    )

    loss = -delta.clip(
        upper=0
    )

    avg_gain = gain.ewm(
        alpha=1 / period,
        min_periods=period,
        adjust=False,
    ).mean()

    avg_loss = loss.ewm(
        alpha=1 / period,
        min_periods=period,
        adjust=False,
    ).mean()

    rs = (
        avg_gain /
        avg_loss.replace(
            0,
            np.nan,
        )
    )

    rsi = (
        100 -
        100 / (1 + rs)
    )

    return rsi.replace(
        [np.inf, -np.inf],
        np.nan,
    )


def _atr(
    df: pd.DataFrame,
    period: int = 14,
) -> pd.Series:

    previous_close = (
        df["Close"].shift(1)
    )

    tr = pd.concat(
        [
            df["High"] - df["Low"],

            (
                df["High"] -
                previous_close
            ).abs(),

            (
                df["Low"] -
                previous_close
            ).abs(),
        ],
        axis=1,
    ).max(axis=1)

    return tr.ewm(
        alpha=1 / period,
        min_periods=period,
        adjust=False,
    ).mean()


def add_indicators(
    df: pd.DataFrame,
) -> pd.DataFrame:

    df = df.copy()

    close = df["Close"]

    # --------------------------------------------------------
    # EMA
    # --------------------------------------------------------

    for period in [
        9,
        20,
        50,
        100,
        200,
    ]:

        df[
            f"EMA{period}"
        ] = _ema(
            close,
            period,
        )

    # --------------------------------------------------------
    # RSI
    # --------------------------------------------------------

    df["RSI"] = _rsi(
        close
    )

    # --------------------------------------------------------
    # ATR
    # --------------------------------------------------------

    df["ATR"] = _atr(
        df
    )

    # --------------------------------------------------------
    # MACD
    # --------------------------------------------------------

    ema12 = _ema(
        close,
        12,
    )

    ema26 = _ema(
        close,
        26,
    )

    df["MACD"] = (
        ema12 -
        ema26
    )

    df["MACD_SIGNAL"] = _ema(
        df["MACD"],
        9,
    )

    df["MACD_HIST"] = (
        df["MACD"] -
        df["MACD_SIGNAL"]
    )

    # --------------------------------------------------------
    # MOMENTUM
    # --------------------------------------------------------

    df["MOMENTUM_20"] = (
        close.pct_change(20)
        * 100
    )

    df["MOMENTUM_60"] = (
        close.pct_change(60)
        * 100
    )

    # --------------------------------------------------------
    # HACİM
    # --------------------------------------------------------

    volume_mean = (
        df["Volume"]
        .rolling(
            20,
            min_periods=5,
        )
        .mean()
    )

    df["VOLUME_RATIO"] = np.where(
        volume_mean > 0,
        df["Volume"] /
        volume_mean,
        np.nan,
    )

    # --------------------------------------------------------
    # VOLATİLİTE
    # --------------------------------------------------------

    daily_return = (
        close.pct_change()
    )

    df["VOLATILITY_20"] = (
        daily_return
        .rolling(
            20,
            min_periods=10,
        )
        .std()
        * np.sqrt(252)
        * 100
    )

    return df


# ============================================================
# SWING NOKTALARI
# ============================================================

def _pivot_levels(
    df: pd.DataFrame,
    window: int = 3,
):

    highs = df["High"].values
    lows = df["Low"].values

    high_levels = []
    low_levels = []

    if len(df) < (
        window * 2 + 1
    ):

        return (
            low_levels,
            high_levels,
        )

    for i in range(
        window,
        len(df) - window,
    ):

        high_value = highs[i]

        low_value = lows[i]

        high_window = highs[
            i - window :
            i + window + 1
        ]

        low_window = lows[
            i - window :
            i + window + 1
        ]

        if (
            np.isfinite(
                high_value
            )
            and
            high_value ==
            np.max(
                high_window
            )
        ):

            high_levels.append(
                float(high_value)
            )

        if (
            np.isfinite(
                low_value
            )
            and
            low_value ==
            np.min(
                low_window
            )
        ):

            low_levels.append(
                float(low_value)
            )

    return (
        low_levels,
        high_levels,
    )


# ============================================================
# TEKNİK SEVİYE KÜMELENDİRME
# ============================================================

def _cluster(
    levels,
    tolerance_pct: float = 0.0075,
):

    levels = sorted(
        float(x)
        for x in levels
        if np.isfinite(x)
        and x > 0
    )

    if not levels:
        return []

    clusters = [
        [levels[0]]
    ]

    for level in levels[1:]:

        center = float(
            np.median(
                clusters[-1]
            )
        )

        distance = (
            abs(level - center)
            / center
        )

        if (
            distance <=
            tolerance_pct
        ):

            clusters[-1].append(
                level
            )

        else:

            clusters.append(
                [level]
            )

    output = []

    for cluster in clusters:

        output.append(
            {
                "level": float(
                    np.median(
                        cluster
                    )
                ),

                "touches": len(
                    cluster
                ),

                "low": float(
                    min(cluster)
                ),

                "high": float(
                    max(cluster)
                ),
            }
        )

    return output


# ============================================================
# DESTEK / DİRENÇ BÖLGELERİ
# ============================================================

def calculate_sr(
    df: pd.DataFrame,
    current: float,
):

    support_levels = []

    resistance_levels = []

    # --------------------------------------------------------
    # Farklı zaman pencereleri
    # --------------------------------------------------------

    windows = [
        (60, 3),
        (120, 4),
        (220, 5),
    ]

    for lookback, pivot_window in windows:

        part = df.tail(
            lookback
        )

        lows, highs = (
            _pivot_levels(
                part,
                pivot_window,
            )
        )

        support_levels.extend(
            lows
        )

        resistance_levels.extend(
            highs
        )

    support_clusters = _cluster(
        support_levels
    )

    resistance_clusters = _cluster(
        resistance_levels
    )

    # --------------------------------------------------------
    # Fiyat altındaki destekler
    # --------------------------------------------------------

    supports = [
        x
        for x in support_clusters
        if x["level"] < current
    ]

    # --------------------------------------------------------
    # Fiyat üzerindeki dirençler
    # --------------------------------------------------------

    resistances = [
        x
        for x in resistance_clusters
        if x["level"] > current
    ]

    # --------------------------------------------------------
    # DESTEK SEÇİMİ
    #
    # En yakın destek her zaman en iyi destek değildir.
    #
    # Temas sayısı + yakınlık birlikte değerlendirilir.
    # --------------------------------------------------------

    def support_rank(level):

        distance = (
            current -
            level["level"]
        ) / current

        return (
            level["touches"] * 2
            -
            distance * 100
        )

    if supports:

        supports = sorted(
            supports,
            key=support_rank,
            reverse=True,
        )

        support = supports[0]

    else:

        support = {
            "level": float(
                df["Low"]
                .tail(60)
                .min()
            ),
            "touches": 1,
        }

    # --------------------------------------------------------
    # DİRENÇLERİ FİYAT MESAFESİNE GÖRE SIRALA
    # --------------------------------------------------------

    resistances = sorted(
        resistances,
        key=lambda x:
        x["level"],
    )

    # --------------------------------------------------------
    # Çok yakın ve anlamsız tek pivotları filtrele
    # --------------------------------------------------------

    meaningful_resistances = []

    for level in resistances:

        distance_pct = (
            level["level"] -
            current
        ) / current * 100

        # Çok yakın seviye:
        # ancak birden fazla temas varsa önem ver.
        if (
            distance_pct <
            TARGET_1_MIN_DISTANCE_PCT
            and
            level["touches"] < 2
        ):
            continue

        meaningful_resistances.append(
            level
        )

    if not meaningful_resistances:

        meaningful_resistances = (
            resistances
        )

    # --------------------------------------------------------
    # HEDEF 1
    # --------------------------------------------------------

    if meaningful_resistances:

        target1 = (
            meaningful_resistances[0]
        )

    else:

        target1 = {
            "level": float(
                df["High"]
                .tail(60)
                .max()
            ),
            "touches": 1,
        }

    # --------------------------------------------------------
    # HEDEF 2
    #
    # Hedef 1'in belirgin şekilde üzerindeki
    # ikinci teknik bölge.
    # --------------------------------------------------------

    target2 = None

    for candidate in meaningful_resistances[1:]:

        if (
            candidate["level"] >
            target1["level"]
        ):

            target2 = candidate
            break

    if target2 is None:

        # İkinci anlamlı seviye yoksa
        # 120/220 günlük yüksek bölgeyi kullan.
        extended_high = float(
            df["High"]
            .tail(220)
            .max()
        )

        if (
            extended_high >
            target1["level"] * 1.005
        ):

            target2 = {
                "level":
                    extended_high,
                "touches": 1,
            }

        else:

            target2 = {
                "level":
                    target1["level"],
                "touches":
                    target1["touches"],
            }

    # --------------------------------------------------------
    # ANA DİRENÇ
    #
    # Uzun vadeli en önemli bölge.
    # --------------------------------------------------------

    major_resistance = max(
        meaningful_resistances,
        key=lambda x: (
            x["touches"],
            x["level"],
        ),
    ) if meaningful_resistances else target2

    return (
        support,
        target1,
        target2,
        major_resistance,
    )


# ============================================================
# TREND SKORU
# ============================================================

def score_trend(
    row: pd.Series,
) -> float:

    score = 50.0

    if row["Close"] > row["EMA9"]:
        score += 10
    else:
        score -= 10

    if row["EMA9"] > row["EMA20"]:
        score += 10
    else:
        score -= 10

    if row["EMA20"] > row["EMA50"]:
        score += 10
    else:
        score -= 10

    if row["EMA50"] > row["EMA100"]:
        score += 10
    else:
        score -= 10

    if row["EMA100"] > row["EMA200"]:
        score += 10
    else:
        score -= 10

    return float(
        np.clip(
            score,
            0,
            100,
        )
    )


# ============================================================
# MOMENTUM SKORU
# ============================================================

def score_momentum(
    row: pd.Series,
) -> float:

    score = 50.0

    if row["MOMENTUM_20"] > 0:
        score += 15
    else:
        score -= 15

    if row["MOMENTUM_60"] > 0:
        score += 15
    else:
        score -= 15

    if (
        row["MACD"] >
        row["MACD_SIGNAL"]
    ):
        score += 10
    else:
        score -= 10

    return float(
        np.clip(
            score,
            0,
            100,
        )
    )


# ============================================================
# TEKNİK SKOR
# ============================================================

def score_technical(
    row: pd.Series,
) -> float:

    score = 50.0

    rsi = float(
        row["RSI"]
    )

    # --------------------------------------------------------
    # RSI
    # --------------------------------------------------------

    if 50 <= rsi <= 70:

        score += 20

    elif (
        45 <= rsi < 50
        or
        70 < rsi <= 75
    ):

        score += 5

    elif rsi < 35:

        score -= 10

    elif rsi > 75:

        score -= 15

    # --------------------------------------------------------
    # MACD
    # --------------------------------------------------------

    if (
        row["MACD"] >
        row["MACD_SIGNAL"]
    ):

        score += 15

    else:

        score -= 15

    # --------------------------------------------------------
    # EMA20
    # --------------------------------------------------------

    if (
        row["Close"] >
        row["EMA20"]
    ):

        score += 10

    else:

        score -= 10

    # --------------------------------------------------------
    # HACİM
    # --------------------------------------------------------

    if (
        pd.notna(
            row["VOLUME_RATIO"]
        )
        and
        row["VOLUME_RATIO"] >= 1
    ):

        score += 5

    return float(
        np.clip(
            score,
            0,
            100,
        )
    )


# ============================================================
# İŞLEM STOPU
# ============================================================

def calculate_trade_stop(
    current: float,
    row: pd.Series,
    support: float,
) -> float:

    atr = float(
        row["ATR"]
    )

    ema20 = float(
        row["EMA20"]
    )

    ema50 = float(
        row["EMA50"]
    )

    # --------------------------------------------------------
    # Aday stop seviyeleri
    # --------------------------------------------------------

    candidates = []

    # EMA20 altı
    if ema20 < current:

        candidates.append(
            ema20
        )

    # EMA50 altı
    if ema50 < current:

        candidates.append(
            ema50
        )

    # Ana destek
    if support < current:

        candidates.append(
            support
        )

    # --------------------------------------------------------
    # Önce mevcut fiyatın altında kalan
    # teknik seviyeler arasından en yakın mantıklı
    # seviyeyi bul.
    # --------------------------------------------------------

    if candidates:

        nearest_technical = max(
            candidates
        )

    else:

        nearest_technical = (
            current -
            atr * ATR_STOP_MULTIPLIER
        )

    # ATR tamponu
    atr_stop = (
        current -
        atr * ATR_STOP_MULTIPLIER
    )

    # Stopun mevcut fiyata çok yakın olmasını engelle
    minimum_distance = (
        current *
        MIN_STOP_DISTANCE_PCT /
        100
    )

    maximum_distance = (
        current *
        MAX_STOP_DISTANCE_PCT /
        100
    )

    technical_distance = (
        current -
        nearest_technical
    )

    if technical_distance < minimum_distance:

        stop = (
            current -
            minimum_distance
        )

    elif technical_distance > maximum_distance:

        stop = (
            current -
            maximum_distance
        )

    else:

        # Teknik seviye + ATR tamponu
        stop = min(
            nearest_technical,
            atr_stop,
        )

    # Güvenlik
    stop = max(
        0.01,
        min(
            stop,
            current * 0.995,
        ),
    )

    return float(
        stop
    )


# ============================================================
# RİSK / GETİRİ
# ============================================================

def calculate_risk_reward(
    current: float,
    stop: float,
    target1: float,
    target2: float,
):

    risk = max(
        current -
        stop,
        0.01,
    )

    reward1 = max(
        target1 -
        current,
        0,
    )

    reward2 = max(
        target2 -
        current,
        0,
    )

    rr1 = (
        reward1 /
        risk
    )

    rr2 = (
        reward2 /
        risk
    )

    # Hedef 1 ağırlıklı,
    # Hedef 2 destekleyici.
    blended_rr = (
        rr1 * 0.65 +
        rr2 * 0.35
    )

    # --------------------------------------------------------
    # R/R SKORU
    # --------------------------------------------------------

    if blended_rr >= 3.0:

        score = 95

    elif blended_rr >= 2.0:

        score = 85

    elif blended_rr >= 1.5:

        score = 75

    elif blended_rr >= 1.0:

        score = 60

    elif blended_rr >= 0.75:

        score = 45

    else:

        score = 25

    return (
        float(score),
        float(rr1),
        float(rr2),
        float(blended_rr),
        float(risk),
        float(reward1),
        float(reward2),
    )


# ============================================================
# ALIM / SATIŞ TEYİTLERİ
# ============================================================

def confirmations(
    row: pd.Series,
):

    buy_checks = {

        "Fiyat EMA9 üzerinde":
            row["Close"] >
            row["EMA9"],

        "EMA9 > EMA20":
            row["EMA9"] >
            row["EMA20"],

        "20G momentum pozitif":
            row["MOMENTUM_20"] >
            0,

        "60G momentum pozitif":
            row["MOMENTUM_60"] >
            0,

        "MACD pozitif":
            row["MACD"] >
            row["MACD_SIGNAL"],

        "RSI aşırı değil":
            row["RSI"] <
            75,
    }

    sell_checks = {

        "Fiyat EMA9 altında":
            row["Close"] <
            row["EMA9"],

        "EMA9 < EMA20":
            row["EMA9"] <
            row["EMA20"],

        "20G momentum negatif":
            row["MOMENTUM_20"] <
            0,

        "60G momentum negatif":
            row["MOMENTUM_60"] <
            0,

        "MACD negatif":
            row["MACD"] <
            row["MACD_SIGNAL"],

        "Fiyat EMA50 altında":
            row["Close"] <
            row["EMA50"],
    }

    return {

        "buy_checks":
            buy_checks,

        "sell_checks":
            sell_checks,

        "buy_count":
            sum(
                buy_checks.values()
            ),

        "sell_count":
            sum(
                sell_checks.values()
            ),
    }


# ============================================================
# ONS + USD/TRY KATKISI
# ============================================================

def _contribution(
    ons_now,
    ons_previous,
    fx_now,
    fx_previous,
):

    if (
        not ons_previous
        or
        not fx_previous
    ):

        return (
            np.nan,
            np.nan,
            np.nan,
        )

    ons_change = (
        (
            ons_now /
            ons_previous
        ) - 1
    ) * 100

    fx_change = (
        (
            fx_now /
            fx_previous
        ) - 1
    ) * 100

    gram_change = (
        (
            (
                ons_now *
                fx_now
            )
            /
            (
                ons_previous *
                fx_previous
            )
        ) - 1
    ) * 100

    return (
        float(ons_change),
        float(fx_change),
        float(gram_change),
    )


# ============================================================
# OTOMATİK KARAR
# ============================================================

def decide(
    score: float,
    buy_count: int,
    sell_count: int,
    rsi: float,
    resistance_distance: float,
    rr1: float,
    blended_rr: float,
):

    # --------------------------------------------------------
    # 1. GÜÇLÜ SATIŞ
    # --------------------------------------------------------

    if (
        sell_count >= 5
        and
        score < 45
    ):

        return (
            "🔴 SAT / AZALT",
            "Trend, momentum ve satış teyitleri belirgin şekilde bozulmuş.",
        )

    # --------------------------------------------------------
    # 2. GÜÇLÜ AL
    #
    # Burada artık sadece genel skor yeterli değil.
    # --------------------------------------------------------

    if (
        score >= 80
        and
        buy_count >= 5
        and
        rsi < 75
        and
        blended_rr >= 1.50
        and
        (
            pd.isna(
                resistance_distance
            )
            or
            resistance_distance >= 2.0
        )
    ):

        return (
            "🟢 GÜÇLÜ AL",
            "Trend, momentum, teknik yapı ve işlem risk/getiri yapısı birlikte güçlü.",
        )

    # --------------------------------------------------------
    # 3. GÜÇLÜ AMA GİRİŞİ KOVALA
    # --------------------------------------------------------

    if (
        score >= 75
        and
        buy_count >= 5
    ):

        return (
            "🟡 GÜÇLÜ / GİRİŞİ KOVALA",
            "Ana yapı güçlü ancak mevcut fiyatlama nedeniyle ideal giriş bölgesi henüz oluşmamış.",
        )

    # --------------------------------------------------------
    # 4. KADEMELİ AL
    # --------------------------------------------------------

    if (
        score >= 65
        and
        buy_count >= 4
        and
        blended_rr >= 1.0
    ):

        return (
            "🟢 KADEMELİ AL",
            "Ana yapı pozitif ve işlem riski kabul edilebilir seviyede.",
        )

    # --------------------------------------------------------
    # 5. KADEMELİ AZALT
    # --------------------------------------------------------

    if (
        sell_count >= 4
        and
        score < 60
    ):

        return (
            "🟠 KADEMELİ AZALT",
            "Teknik yapı zayıflıyor ve satış teyitleri artıyor.",
        )

    # --------------------------------------------------------
    # 6. BEKLE
    # --------------------------------------------------------

    return (
        "🟡 BEKLE / TEYİT BEKLE",
        "Mevcut yapı net bir alım veya satış avantajı oluşturmuyor.",
    )


# ============================================================
# ANA ANALİZ
# ============================================================

def analyze_gold(
    period: str = DEFAULT_PERIOD,
    interval: str = DEFAULT_INTERVAL,
) -> GoldAnalysisResult:

    # ========================================================
    # VERİLER
    # ========================================================

    ons = fetch(
        GOLD_SYMBOL,
        period,
        interval,
    )

    usdtry = fetch(
        USDTRY_SYMBOL,
        period,
        interval,
    )

    if ons.empty:

        return GoldAnalysisResult(
            False,
            "Ons altın verisi alınamadı.",
            pd.DataFrame(),
            {},
        )

    if usdtry.empty:

        return GoldAnalysisResult(
            False,
            "USD/TRY verisi alınamadı. Gram altın kararı güvenli şekilde üretilemez.",
            pd.DataFrame(),
            {},
        )

    if (
        len(ons) < MIN_ROWS
        or
        len(usdtry) < MIN_ROWS
    ):

        return GoldAnalysisResult(
            False,
            (
                "Yetersiz veri. "
                f"Ons={len(ons)}, "
                f"USD/TRY={len(usdtry)}, "
                f"minimum={MIN_ROWS}."
            ),
            pd.DataFrame(),
            {},
        )

    # ========================================================
    # TEKNİK HESAPLAMA
    # ========================================================

    ons = add_indicators(
        ons
    )

    usdtry = add_indicators(
        usdtry
    )

    row = ons.iloc[-1]

    fx_row = usdtry.iloc[-1]

    # ========================================================
    # ANA FİYATLAR
    # ========================================================

    ons_price = float(
        row["Close"]
    )

    usdtry_price = float(
        fx_row["Close"]
    )

    gram_price = (
        ons_price *
        usdtry_price /
        TROY_OUNCE_GRAM
    )

    # ========================================================
    # DESTEK / DİRENÇ
    # ========================================================

    (
        support,
        target1,
        target2,
        major_resistance,
    ) = calculate_sr(
        ons,
        ons_price,
    )

    support_price = float(
        support["level"]
    )

    target1_price = float(
        target1["level"]
    )

    target2_price = float(
        target2["level"]
    )

    major_resistance_price = float(
        major_resistance["level"]
    )

    # ========================================================
    # SKORLAR
    # ========================================================

    technical_score = (
        score_technical(
            row
        )
    )

    trend_score = (
        score_trend(
            row
        )
    )

    momentum_score = (
        score_momentum(
            row
        )
    )

    # ========================================================
    # İŞLEM STOPU
    # ========================================================

    trade_stop = calculate_trade_stop(
        current=ons_price,
        row=row,
        support=support_price,
    )

    # ========================================================
    # RİSK / GETİRİ
    # ========================================================

    (
        risk_score,
        rr1,
        rr2,
        blended_rr,
        risk_distance,
        reward1,
        reward2,
    ) = calculate_risk_reward(
        current=ons_price,
        stop=trade_stop,
        target1=target1_price,
        target2=target2_price,
    )

    # ========================================================
    # GENEL SKOR
    # ========================================================

    general_score = (
        trend_score *
        W_TREND

        +

        momentum_score *
        W_MOMENTUM

        +

        technical_score *
        W_TECHNICAL

        +

        risk_score *
        W_RISK
    )

    # ========================================================
    # DİRENCE UZAKLIK
    # ========================================================

    if major_resistance_price > ons_price:

        resistance_distance = (
            (
                major_resistance_price -
                ons_price
            )
            /
            ons_price
        ) * 100

    else:

        resistance_distance = np.nan

    # ========================================================
    # TEYİTLER
    # ========================================================

    confirmation = confirmations(
        row
    )

    buy_count = (
        confirmation["buy_count"]
    )

    sell_count = (
        confirmation["sell_count"]
    )

    # ========================================================
    # KARAR
    # ========================================================

    decision, reason = decide(
        score=general_score,
        buy_count=buy_count,
        sell_count=sell_count,
        rsi=float(row["RSI"]),
        resistance_distance=resistance_distance,
        rr1=rr1,
        blended_rr=blended_rr,
    )

    # ========================================================
    # ONS / USDTRY KATKISI
    # ========================================================

    if (
        len(ons) >= 21
        and
        len(usdtry) >= 21
    ):

        ons_previous = float(
            ons["Close"].iloc[-21]
        )

        fx_previous = float(
            usdtry["Close"].iloc[-21]
        )

        (
            ons_contribution,
            fx_contribution,
            gram_momentum_20,
        ) = _contribution(
            ons_price,
            ons_previous,
            usdtry_price,
            fx_previous,
        )

    else:

        (
            ons_contribution,
            fx_contribution,
            gram_momentum_20,
        ) = (
            np.nan,
            np.nan,
            np.nan,
        )

    # ========================================================
    # GRAM FİYATINI AYRI SERİ OLARAK HESAPLAMA
    # ========================================================

    aligned = pd.DataFrame(
        {
            "ons": ons["Close"],
            "usdtry": usdtry["Close"],
        }
    ).dropna()

    aligned["gram"] = (
        aligned["ons"] *
        aligned["usdtry"] /
        TROY_OUNCE_GRAM
    )

    if len(aligned) >= 21:

        gram_momentum_20_check = (
            aligned["gram"]
            .pct_change(20)
            .iloc[-1]
            * 100
        )

    else:

        gram_momentum_20_check = np.nan

    # ========================================================
    # SONUÇ
    # ========================================================

    result = {

        # ----------------------------------------------------
        # ANA
        # ----------------------------------------------------

        "asset":
            "GRAM ALTIN",

        "gram_price":
            gram_price,

        "ons_price":
            ons_price,

        "usdtry":
            usdtry_price,

        # ----------------------------------------------------
        # SKORLAR
        # ----------------------------------------------------

        "general_score":
            round(
                general_score,
                1,
            ),

        "technical_score":
            round(
                technical_score,
                1,
            ),

        "trend_score":
            round(
                trend_score,
                1,
            ),

        "momentum_score":
            round(
                momentum_score,
                1,
            ),

        "risk_reward_score":
            round(
                risk_score,
                1,
            ),

        # ----------------------------------------------------
        # TEKNİK
        # ----------------------------------------------------

        "rsi":
            float(row["RSI"]),

        "ema9":
            float(row["EMA9"]),

        "ema20":
            float(row["EMA20"]),

        "ema50":
            float(row["EMA50"]),

        "ema100":
            float(row["EMA100"]),

        "ema200":
            float(row["EMA200"]),

        "macd":
            float(row["MACD"]),

        "macd_signal":
            float(row["MACD_SIGNAL"]),

        "momentum_20":
            float(row["MOMENTUM_20"]),

        "momentum_60":
            float(row["MOMENTUM_60"]),

        "volume_ratio":
            (
                float(row["VOLUME_RATIO"])
                if pd.notna(
                    row["VOLUME_RATIO"]
                )
                else np.nan
            ),

        "atr":
            float(row["ATR"]),

        "volatility_20":
            float(row["VOLATILITY_20"]),

        # ----------------------------------------------------
        # DESTEK
        # ----------------------------------------------------

        "support":
            support_price,

        "support_touches":
            int(
                support["touches"]
            ),

        # ----------------------------------------------------
        # HEDEFLER
        # ----------------------------------------------------

        "target1":
            target1_price,

        "target1_touches":
            int(
                target1["touches"]
            ),

        "target2":
            target2_price,

        "target2_touches":
            int(
                target2["touches"]
            ),

        # ----------------------------------------------------
        # ANA DİRENÇ
        # ----------------------------------------------------

        "major_resistance":
            major_resistance_price,

        "major_resistance_touches":
            int(
                major_resistance[
                    "touches"
                ]
            ),

        # Eski sayfa ile uyumluluk
        "resistance":
            major_resistance_price,

        "resistance_touches":
            int(
                major_resistance[
                    "touches"
                ]
            ),

        "resistance_distance_pct":
            float(
                resistance_distance
            )
            if pd.notna(
                resistance_distance
            )
            else np.nan,

        # ----------------------------------------------------
        # İŞLEM PLANI
        # ----------------------------------------------------

        "trade_stop":
            trade_stop,

        "risk_distance":
            risk_distance,

        "reward_to_target1":
            reward1,

        "reward_to_target2":
            reward2,

        "risk_reward_target1":
            rr1,

        "risk_reward_target2":
            rr2,

        "risk_reward":
            blended_rr,

        # Eski sayfa uyumluluğu
        "upside_to_resistance":
            max(
                major_resistance_price -
                ons_price,
                0,
            ),

        "stop_distance":
            risk_distance,

        # ----------------------------------------------------
        # ONS / KUR
        # ----------------------------------------------------

        "ons_contribution_20":
            ons_contribution,

        "fx_contribution_20":
            fx_contribution,

        "gram_momentum_20":
            gram_momentum_20,

        "gram_momentum_20_check":
            gram_momentum_20_check,

        # ----------------------------------------------------
        # TEYİTLER
        # ----------------------------------------------------

        "buy_checks":
            confirmation[
                "buy_checks"
            ],

        "sell_checks":
            confirmation[
                "sell_checks"
            ],

        "buy_count":
            buy_count,

        "sell_count":
            sell_count,

        "buy_confirmation":
            buy_count >= 5,

        "sell_confirmation":
            sell_count >= 5,

        # ----------------------------------------------------
        # KARAR
        # ----------------------------------------------------

        "decision":
            decision,

        "reason":
            reason,

        # ----------------------------------------------------
        # VERİ
        # ----------------------------------------------------

        "data_source":
            "Yahoo Finance: GC=F + USDTRY=X",

        "reference_source":
            "Borsa İstanbul KMTP / BIST-KYD",

        "data_timestamp":
            str(
                ons.index[-1]
            ),

        "data_status":
            (
                "Historical OHLC; "
                "real-time garanti edilmez."
            ),
    }

    return GoldAnalysisResult(
        True,
        None,
        aligned,
        result,
    )