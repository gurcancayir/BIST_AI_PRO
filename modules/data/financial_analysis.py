import sqlite3
import numpy as np
import pandas as pd


# ============================================================
# BIST AI PRO
# FINANCIAL ANALYSIS ENGINE
# ============================================================
#
# Amaç:
#
# 1) KAP finansal raporlarından finansal sağlık hesaplamak
# 2) Finansal trendi hesaplamak
# 3) Çeyreklik / yıllık raporları doğru yorumlamak
# 4) Finansal Score üretmek
# 5) Financial Trend Score üretmek
# 6) Güçlü / zayıf noktaları belirlemek
#
# Veri kaynağı:
# financial_reports
#
# Şimdilik yalnızca:
# KAP / kullanıcı tarafından sisteme aktarılan finansal raporlar
#
# ============================================================


DB_PATH = "borsa.db"


# ============================================================
# GENEL YARDIMCILAR
# ============================================================

def safe_float(value, default=np.nan):

    try:

        if value is None:
            return default

        if pd.isna(value):
            return default

        return float(value)

    except Exception:

        return default


def clamp(
    value,
    low=0.0,
    high=100.0
):

    try:

        value = float(value)

    except Exception:

        return 50.0

    return max(
        low,
        min(high, value)
    )


def get_quarter(period):

    period = str(
        period
    ).upper()

    if "_1Q" in period or "_1C" in period:
        return 1

    if "_2Q" in period or "_2C" in period:
        return 2

    if "_3Q" in period or "_3C" in period:
        return 3

    if "_YILLIK" in period:
        return 4

    return None


# ============================================================
# RAPOR TİPİ
# ============================================================

def is_annual_period(period):

    return get_quarter(period) == 4


def is_quarter_period(period):

    quarter = get_quarter(period)

    return quarter in (
        1,
        2,
        3
    )


# ============================================================
# FİNANSAL SAĞLIK PUANLAMA
# ============================================================

def score_current_ratio(value):

    value = safe_float(value)

    if np.isnan(value):
        return None

    # Aşırı yüksek cari oranı da ayrıca değerlendirebiliriz.
    #
    # Finansal sağlık açısından:
    #
    # < 0.80      zayıf
    # 0.80-1.00   düşük
    # 1.00-1.20   kabul edilebilir
    # 1.20-1.50   iyi
    # 1.50-2.00   çok iyi
    # >=2.00      güçlü
    #
    # 80 gibi aşırı yüksek oranlar ayrıca sermaye
    # verimliliği açısından incelenebilir fakat sağlık
    # skorunda maksimum 100 kabul edilir.

    if value >= 2.00:
        return 100.0

    if value >= 1.50:
        return 85.0

    if value >= 1.20:
        return 75.0

    if value >= 1.00:
        return 60.0

    if value >= 0.80:
        return 40.0

    return 20.0


def score_debt_equity(value):

    value = safe_float(value)

    if np.isnan(value):
        return None

    if value <= 0.30:
        return 100.0

    if value <= 0.60:
        return 85.0

    if value <= 1.00:
        return 70.0

    if value <= 1.50:
        return 55.0

    if value <= 2.50:
        return 35.0

    return 15.0


def score_net_margin(value):

    value = safe_float(value)

    if np.isnan(value):
        return None

    if value >= 15:
        return 100.0

    if value >= 10:
        return 90.0

    if value >= 5:
        return 75.0

    if value >= 0:
        return 55.0

    if value >= -5:
        return 35.0

    return 15.0


def score_net_cash(
    net_cash,
    equity
):

    net_cash = safe_float(
        net_cash
    )

    equity = safe_float(
        equity
    )

    if (
        np.isnan(net_cash)
        or np.isnan(equity)
    ):
        return None

    if equity == 0:
        return None

    ratio = (
        net_cash
        /
        abs(equity)
    )

    if ratio >= 0.50:
        return 100.0

    if ratio >= 0.25:
        return 90.0

    if ratio >= 0:
        return 75.0

    if ratio >= -0.25:
        return 55.0

    if ratio >= -0.50:
        return 35.0

    return 15.0


def score_operating_cash_flow(
    ocf,
    net_profit
):

    ocf = safe_float(
        ocf
    )

    net_profit = safe_float(
        net_profit
    )

    if np.isnan(ocf):
        return None

    # Pozitif faaliyet nakit akışı
    # başlı başına olumlu.
    if ocf < 0:
        return 20.0

    if (
        np.isnan(net_profit)
        or net_profit == 0
    ):
        return 70.0

    ratio = (
        ocf
        /
        abs(net_profit)
    )

    if ratio >= 1.20:
        return 100.0

    if ratio >= 0.80:
        return 90.0

    if ratio >= 0.50:
        return 75.0

    if ratio > 0:
        return 60.0

    return 20.0


# ============================================================
# FİNANSAL RAPORLARI OKU
# ============================================================

def load_financial_reports(symbol):

    try:

        conn = sqlite3.connect(
            DB_PATH
        )

        df = pd.read_sql_query(
            """
            SELECT *
            FROM financial_reports
            WHERE UPPER(TRIM(symbol)) = ?
            ORDER BY period_end
            """,
            conn,
            params=(
                str(symbol)
                .upper()
                .strip(),
            ),
        )

        conn.close()

        if df.empty:
            return pd.DataFrame()

        df["period_end"] = pd.to_datetime(
            df["period_end"],
            errors="coerce",
        )

        df = df.dropna(
            subset=[
                "period_end"
            ]
        ).copy()

        if df.empty:
            return pd.DataFrame()

        return (
            df
            .sort_values(
                "period_end"
            )
            .reset_index(
                drop=True
            )
        )

    except Exception:

        return pd.DataFrame()


# ============================================================
# EN GÜNCEL RAPOR
# ============================================================

def get_latest_financial_report(symbol):

    df = load_financial_reports(
        symbol
    )

    if df.empty:
        return None

    financial_columns = [

        "revenue",
        "operating_profit",
        "net_profit",
        "cash",

        "current_assets",
        "current_liabilities",

        "equity",

        "operating_cash_flow",

        "short_term_financial_debt",
        "current_portion_long_term_debt",
        "long_term_financial_debt",
    ]

    available_columns = [
        c
        for c in financial_columns
        if c in df.columns
    ]

    if available_columns:

        df["_filled"] = (
            df[
                available_columns
            ]
            .notna()
            .sum(axis=1)
        )

        df = (
            df
            .sort_values(
                [
                    "period_end",
                    "_filled"
                ]
            )
            .drop_duplicates(
                subset=[
                    "period_end"
                ],
                keep="last",
            )
            .drop(
                columns=[
                    "_filled"
                ]
            )
        )

    return df.iloc[-1].copy()


# ============================================================
# FİNANSAL SAĞLIK
# ============================================================

def get_financial_health(symbol):

    result = {

        "available": False,

        "score": None,

        "signal": "VERİ YOK",

        "period": None,

        "period_end": None,

        "valid_metrics": 0,

        "metrics": {},

        "raw": {},

        "missing": [],

        "message": "",
    }

    latest = get_latest_financial_report(
        symbol
    )

    if latest is None:

        result["message"] = (
            f"{symbol} için financial_reports "
            "tablosunda kayıt bulunamadı."
        )

        return result

    def val(column):

        return safe_float(
            latest.get(
                column
            ),
            np.nan,
        )

    revenue = val(
        "revenue"
    )

    net_profit = val(
        "net_profit"
    )

    cash = val(
        "cash"
    )

    equity = val(
        "equity"
    )

    current_assets = val(
        "current_assets"
    )

    current_liabilities = val(
        "current_liabilities"
    )

    operating_cash_flow = val(
        "operating_cash_flow"
    )

    # ========================================================
    # FİNANSAL BORÇ
    # ========================================================

    debt_values = []

    for column in [

        "short_term_financial_debt",

        "current_portion_long_term_debt",

        "long_term_financial_debt",

    ]:

        value = val(
            column
        )

        if not np.isnan(value):

            debt_values.append(
                value
            )

    financial_debt = (
        sum(debt_values)
        if debt_values
        else np.nan
    )

    # ========================================================
    # ORANLAR
    # ========================================================

    current_ratio = (

        current_assets
        /
        current_liabilities

        if (

            not np.isnan(
                current_assets
            )

            and

            not np.isnan(
                current_liabilities
            )

            and

            current_liabilities != 0

        )

        else np.nan
    )

    debt_equity = (

        financial_debt
        /
        equity

        if (

            not np.isnan(
                financial_debt
            )

            and

            not np.isnan(
                equity
            )

            and

            equity != 0

        )

        else np.nan
    )

    net_margin = (

        net_profit
        /
        revenue
        *
        100

        if (

            not np.isnan(
                net_profit
            )

            and

            not np.isnan(
                revenue
            )

            and

            revenue != 0

        )

        else np.nan
    )

    net_cash = (

        cash
        -
        financial_debt

        if (

            not np.isnan(
                cash
            )

            and

            not np.isnan(
                financial_debt
            )

        )

        else np.nan
    )

    # ========================================================
    # GÖSTERGE SKORLARI
    # ========================================================

    metrics = {

        "Cari Oran":
            score_current_ratio(
                current_ratio
            ),

        "Borç / Özkaynak":
            score_debt_equity(
                debt_equity
            ),

        "Net Kâr Marjı":
            score_net_margin(
                net_margin
            ),

        "Net Nakit / Özkaynak":
            score_net_cash(
                net_cash,
                equity,
            ),

        "Faaliyet Nakit Akışı":
            score_operating_cash_flow(
                operating_cash_flow,
                net_profit,
            ),
    }

    valid_metrics = {

        key: value

        for key, value in metrics.items()

        if (
            value is not None
            and
            pd.notna(value)
        )
    }

    result["metrics"] = (
        valid_metrics
    )

    result["valid_metrics"] = (
        len(valid_metrics)
    )

    result["missing"] = [

        key

        for key in metrics

        if key not in valid_metrics
    ]

    # ========================================================
    # HAM VERİ
    # ========================================================

    result["raw"] = {

        "revenue":
            revenue,

        "net_profit":
            net_profit,

        "cash":
            cash,

        "equity":
            equity,

        "current_assets":
            current_assets,

        "current_liabilities":
            current_liabilities,

        "operating_cash_flow":
            operating_cash_flow,

        "financial_debt":
            financial_debt,

        "current_ratio":
            current_ratio,

        "debt_equity":
            debt_equity,

        "net_margin":
            net_margin,

        "net_cash":
            net_cash,
    }

    # ========================================================
    # VERİ YETERLİLİĞİ
    # ========================================================

    if len(valid_metrics) < 3:

        result["message"] = (

            f"{symbol} için yalnızca "

            f"{len(valid_metrics)}/5 "

            "finansal gösterge hesaplanabildi. "

            "Gerçek skor üretmek için veri yetersiz."
        )

        result["period"] = latest.get(
            "period"
        )

        result["period_end"] = latest.get(
            "period_end"
        )

        return result

    # ========================================================
    # FİNANSAL SKOR
    # ========================================================

    # Sağlık göstergelerinin ağırlıkları.
    #
    # Borç / Özkaynak:
    # şirketin finansal riskini doğrudan gösterir.
    #
    # Net Kâr Marjı:
    # kârlılık kalitesini gösterir.
    #
    # Faaliyet Nakit Akışı:
    # muhasebe kârının nakde dönüşümünü gösterir.
    #
    # Net Nakit:
    # bilanço dayanıklılığını gösterir.
    #
    # Cari Oran:
    # kısa vadeli ödeme gücünü gösterir.

    metric_weights = {

        "Borç / Özkaynak":
            0.25,

        "Net Kâr Marjı":
            0.25,

        "Faaliyet Nakit Akışı":
            0.20,

        "Net Nakit / Özkaynak":
            0.20,

        "Cari Oran":
            0.10,
    }

    weighted_sum = 0.0
    total_weight = 0.0

    for metric, value in valid_metrics.items():

        weight = metric_weights.get(
            metric,
            0.0
        )

        weighted_sum += (
            value * weight
        )

        total_weight += weight

    if total_weight <= 0:

        score = 50.0

    else:

        score = (
            weighted_sum
            /
            total_weight
        )

    score = clamp(
        score
    )

    result["score"] = round(
        score,
        1
    )

    result["available"] = True

    # ========================================================
    # FİNANSAL SİNYAL
    # ========================================================

    if score >= 75:

        result["signal"] = (
            "🟢 GÜÇLÜ"
        )

    elif score >= 60:

        result["signal"] = (
            "🟢 OLUMLU"
        )

    elif score >= 45:

        result["signal"] = (
            "🟡 ORTA"
        )

    else:

        result["signal"] = (
            "🔴 ZAYIF"
        )

    result["period"] = latest.get(
        "period"
    )

    result["period_end"] = latest.get(
        "period_end"
    )

    result["message"] = (

        f"Son dönem: "
        f"{result['period']} | "
        f"{len(valid_metrics)}/5 "
        "gösterge kullanılabilir."
    )

    return result


# ============================================================
# FİNANSAL TREND VERİSİ
# ============================================================

def get_financial_trend(symbol):

    df = load_financial_reports(
        symbol
    )

    if df.empty:
        return None

    # ========================================================
    # NUMERİK ALANLAR
    # ========================================================

    numeric_columns = [

        "revenue",

        "operating_profit",

        "net_profit",

        "cash",

        "equity",

        "operating_cash_flow",

        "short_term_financial_debt",

        "current_portion_long_term_debt",

        "long_term_financial_debt",
    ]

    for column in numeric_columns:

        if column not in df.columns:

            df[column] = np.nan

        df[column] = pd.to_numeric(
            df[column],
            errors="coerce",
        )

    df["period"] = (
        df["period"]
        .astype(str)
    )

    df["year"] = (
        df["period_end"]
        .dt.year
    )

    df["quarter"] = (
        df["period"]
        .apply(
            get_quarter
        )
    )

    df = df[
        df["quarter"].notna()
    ].copy()

    if df.empty:
        return None

    # ========================================================
    # AYNI DÖNEM TEKRARLARINI TEMİZLE
    # ========================================================

    df["_filled"] = (

        df[
            numeric_columns
        ]
        .notna()
        .sum(axis=1)
    )

    df = (

        df
        .sort_values(
            [
                "period_end",
                "_filled"
            ]
        )

        .drop_duplicates(
            subset=[
                "period_end"
            ],
            keep="last",
        )

        .drop(
            columns=[
                "_filled"
            ]
        )

        .sort_values(
            "period_end"
        )

        .reset_index(
            drop=True
        )
    )

    # ========================================================
    # KAP KÜMÜLATİF VERİLERİ ÇEYREKSEL VERİYE ÇEVİR
    # ========================================================
    #
    # Önemli:
    #
    # 1Ç = doğrudan 1Ç
    #
    # 2Ç = 6 aylık - 1Ç
    #
    # 3Ç = 9 aylık - 6 aylık
    #
    # YILLIK = yıllık - 9 aylık
    #
    # Böylece:
    #
    # 2026 1Ç
    # 2026 2Ç
    # 2026 3Ç
    # 2026 4Ç
    #
    # şeklinde gerçek çeyreklik seri oluşturulur.
    #
    # ========================================================

    flow_columns = [

        "revenue",

        "net_profit",

        "operating_cash_flow",

    ]

    quarterly_rows = []

    for _, row in df.iterrows():

        current = row.copy()

        year = int(
            row["year"]
        )

        quarter = int(
            row["quarter"]
        )

        for column in flow_columns:

            value = row[column]

            if pd.isna(value):

                current[column] = np.nan

                continue

            # ------------------------------------------------
            # 1Ç
            # ------------------------------------------------

            if quarter == 1:

                current[column] = value

                continue

            # ------------------------------------------------
            # Önceki kümülatif dönem
            # ------------------------------------------------

            previous = df[
                (df["year"] == year)
                &
                (
                    df["quarter"]
                    == quarter - 1
                )
            ]

            if (
                not previous.empty
                and
                pd.notna(
                    previous.iloc[-1][
                        column
                    ]
                )
            ):

                previous_value = (
                    previous.iloc[-1][
                        column
                    ]
                )

                current[column] = (
                    value
                    -
                    previous_value
                )

            else:

                # Önceki dönem bulunamadıysa
                # değeri olduğu gibi bırak.
                current[column] = value

        quarterly_rows.append(
            current
        )

    qdf = pd.DataFrame(
        quarterly_rows
    )

    if qdf.empty:
        return None

    # ========================================================
    # DÖNEM ADI
    # ========================================================

    def period_name(row):

        year = int(
            row["year"]
        )

        quarter = int(
            row["quarter"]
        )

        if quarter == 1:
            return f"{year} 1Ç"

        if quarter == 2:
            return f"{year} 2Ç"

        if quarter == 3:
            return f"{year} 3Ç"

        return f"{year} 4Ç"

    qdf["display_period"] = (
        qdf.apply(
            period_name,
            axis=1,
        )
    )

    # ========================================================
    # FİNANSAL BORÇ
    # ========================================================

    debt_columns = [

        "short_term_financial_debt",

        "current_portion_long_term_debt",

        "long_term_financial_debt",

    ]

    def calculate_debt(row):

        values = [

            row[column]

            for column in debt_columns

            if pd.notna(
                row[column]
            )
        ]

        if not values:
            return np.nan

        return sum(values)

    qdf["financial_debt"] = (
        qdf.apply(
            calculate_debt,
            axis=1,
        )
    )

    # ========================================================
    # TÜRETİLMİŞ ORANLAR
    # ========================================================

    qdf["debt_equity"] = (

        qdf["financial_debt"]

        /

        qdf["equity"].replace(
            0,
            np.nan,
        )
    )

    qdf["net_cash"] = (

        qdf["cash"]

        -

        qdf["financial_debt"]
    )

    qdf["net_margin"] = (

        qdf["net_profit"]

        /

        qdf["revenue"].replace(
            0,
            np.nan,
        )

        *

        100
    )

    # ========================================================
    # CARİ ORAN
    # ========================================================

    if "current_assets" not in qdf.columns:
        qdf["current_assets"] = np.nan

    if "current_liabilities" not in qdf.columns:
        qdf["current_liabilities"] = np.nan

    qdf["current_ratio"] = (

        qdf["current_assets"]

        /

        qdf["current_liabilities"].replace(
            0,
            np.nan,
        )
    )

    # ========================================================
    # BOŞ DÖNEMLERİ TEMİZLE
    # ========================================================

    core_columns = [

        "revenue",

        "net_profit",

        "cash",

        "equity",

        "operating_cash_flow",
    ]

    qdf = qdf[
        qdf[
            core_columns
        ]
        .notna()
        .sum(axis=1)
        >= 2
    ].copy()

    if qdf.empty:
        return None

    return (

        qdf

        .sort_values(
            "period_end"
        )

        .reset_index(
            drop=True
        )
    )


# ============================================================
# TREND KARŞILAŞTIRMA YARDIMCISI
# ============================================================

def calculate_direction(
    latest_value,
    old_value,
    higher_is_better=True,
    neutral_threshold=5.0
):

    if (
        pd.isna(latest_value)
        or
        pd.isna(old_value)
    ):
        return None

    if old_value == 0:
        return None

    change = (

        (
            latest_value
            -
            old_value
        )

        /

        abs(old_value)

        *

        100
    )

    if higher_is_better:

        if change > neutral_threshold:
            return 1

        if change < -neutral_threshold:
            return -1

        return 0

    else:

        if change < -neutral_threshold:
            return 1

        if change > neutral_threshold:
            return -1

        return 0


# ============================================================
# TREND SKORU
# ============================================================

def calculate_financial_trend_score(
    qdf
):

    if (
        qdf is None
        or
        len(qdf) < 2
    ):

        return {

            "score": 50.0,

            "signal":
                "🟡 VERİ YETERSİZ",

            "strong_points": [],

            "weak_points": [],
        }

    qdf = (
        qdf
        .sort_values(
            "period_end"
        )
        .reset_index(
            drop=True
        )
    )

    latest = qdf.iloc[-1]

    latest_year = int(
        latest["year"]
    )

    latest_quarter = int(
        latest["quarter"]
    )

    # ========================================================
    # SON ÇEYREĞİN ÖNCEKİ ÇEYREĞİ
    # ========================================================
    #
    # Burada YILLIK kayıt referans alınmaz.
    #
    # Örneğin:
    #
    # 2026 1Ç -> 2025 4Ç
    #
    # Eğer 2025 4Ç mevcut değilse
    # yalnızca yıllık karşılaştırma yapılır.
    #
    # ========================================================

    sequential_candidates = qdf[
        (
            qdf["period_end"]
            <
            latest["period_end"]
        )
        &
        (
            qdf["quarter"] != 4
        )
    ]

    previous_quarter = None

    if latest_quarter > 1:

        candidates = qdf[
            (
                qdf["year"]
                == latest_year
            )
            &
            (
                qdf["quarter"]
                == latest_quarter - 1
            )
        ]

        if not candidates.empty:

            previous_quarter = (
                candidates.iloc[-1]
            )

    else:

        # 1Ç için önceki yılın 4Ç'si
        candidates = qdf[
            (
                qdf["year"]
                == latest_year - 1
            )
            &
            (
                qdf["quarter"]
                == 4
            )
        ]

        if not candidates.empty:

            previous_quarter = (
                candidates.iloc[-1]
            )

    # ========================================================
    # AYNI ÇEYREĞİN GEÇEN YILI
    # ========================================================

    previous_year_candidates = qdf[
        (
            qdf["year"]
            == latest_year - 1
        )
        &
        (
            qdf["quarter"]
            == latest_quarter
        )
    ]

    previous_year = None

    if not previous_year_candidates.empty:

        previous_year = (
            previous_year_candidates
            .iloc[-1]
        )

    # ========================================================
    # TREND GÖSTERGELERİ
    # ========================================================

    trend_items = [

        (
            "Hasılat",
            "revenue",
            True,
            0.20,
        ),

        (
            "Net Kâr",
            "net_profit",
            True,
            0.20,
        ),

        (
            "Net Kâr Marjı",
            "net_margin",
            True,
            0.15,
        ),

        (
            "Faaliyet Nakit Akışı",
            "operating_cash_flow",
            True,
            0.15,
        ),

        (
            "Nakit",
            "cash",
            True,
            0.05,
        ),

        (
            "Özkaynak",
            "equity",
            True,
            0.05,
        ),

        (
            "Finansal Borç",
            "financial_debt",
            False,
            0.10,
        ),

        (
            "Net Nakit",
            "net_cash",
            True,
            0.05,
        ),

        (
            "Borç / Özkaynak",
            "debt_equity",
            False,
            0.05,
        ),
    ]

    weighted_directions = []

    strong_points = []

    weak_points = []

    neutral_points = []

    # ========================================================
    # HER GÖSTERGEYİ DEĞERLENDİR
    # ========================================================

    for (
        name,
        column,
        higher_is_better,
        weight,
    ) in trend_items:

        item_directions = []

        # ----------------------------------------------------
        # Ardışık çeyrek
        # ----------------------------------------------------

        if previous_quarter is not None:

            direction = calculate_direction(

                latest[column],

                previous_quarter[column],

                higher_is_better,
            )

            if direction is not None:

                item_directions.append(
                    direction
                )

        # ----------------------------------------------------
        # Yıllık karşılaştırma
        # ----------------------------------------------------

        if previous_year is not None:

            direction = calculate_direction(

                latest[column],

                previous_year[column],

                higher_is_better,
            )

            if direction is not None:

                item_directions.append(
                    direction
                )

        # ----------------------------------------------------
        # Veri yoksa
        # ----------------------------------------------------

        if not item_directions:
            continue

        # ----------------------------------------------------
        # Gösterge yönü
        # ----------------------------------------------------

        direction = (

            sum(item_directions)

            /

            len(item_directions)
        )

        weighted_directions.append(
            (
                direction,
                weight
            )
        )

        # ----------------------------------------------------
        # Güçlü / zayıf noktalar
        # ----------------------------------------------------

        if direction > 0.50:

            strong_points.append(
                name
            )

        elif direction < -0.50:

            weak_points.append(
                name
            )

        else:

            neutral_points.append(
                name
            )

    # ========================================================
    # AĞIRLIKLI TREND
    # ========================================================

    if not weighted_directions:

        score = 50.0

    else:

        weighted_sum = sum(

            direction * weight

            for direction, weight
            in weighted_directions
        )

        total_weight = sum(

            weight

            for direction, weight
            in weighted_directions
        )

        if total_weight <= 0:

            score = 50.0

        else:

            average_direction = (

                weighted_sum
                /
                total_weight
            )

            score = (

                50
                +
                average_direction * 50
            )

    score = clamp(
        score
    )

    # ========================================================
    # TREND SİNYALİ
    # ========================================================

    if score >= 75:

        signal = (
            "🟢 ÇOK POZİTİF"
        )

    elif score >= 65:

        signal = (
            "🟢 POZİTİF"
        )

    elif score >= 55:

        signal = (
            "🟢 HAFİF POZİTİF"
        )

    elif score >= 45:

        signal = (
            "🟡 STABİL"
        )

    elif score >= 35:

        signal = (
            "🟠 BOZULUYOR"
        )

    else:

        signal = (
            "🔴 ZAYIFLIYOR"
        )

    return {

        "score":
            round(
                score,
                1
            ),

        "signal":
            signal,

        "strong_points":
            strong_points,

        "weak_points":
            weak_points,

        "neutral_points":
            neutral_points,

        "previous_quarter":
            (
                previous_quarter[
                    "display_period"
                ]
                if previous_quarter is not None
                else None
            ),

        "previous_year":
            (
                previous_year[
                    "display_period"
                ]
                if previous_year is not None
                else None
            ),
    }


# ============================================================
# SAĞLIK GÜÇLÜ / ZAYIF NOKTALARI
# ============================================================

def get_health_points(
    health
):

    strong = []

    weak = []

    if not health:
        return strong, weak

    metrics = health.get(
        "metrics",
        {}
    )

    raw = health.get(
        "raw",
        {}
    )

    # ========================================================
    # BORÇ / ÖZKAYNAK
    # ========================================================

    debt_equity = raw.get(
        "debt_equity"
    )

    if (
        debt_equity is not None
        and
        not pd.isna(
            debt_equity
        )
    ):

        if debt_equity <= 0.30:

            strong.append(
                "Düşük Borçluluk"
            )

        elif debt_equity > 1.50:

            weak.append(
                "Yüksek Borçluluk"
            )

    # ========================================================
    # NET MARJ
    # ========================================================

    net_margin = raw.get(
        "net_margin"
    )

    if (
        net_margin is not None
        and
        not pd.isna(
            net_margin
        )
    ):

        if net_margin >= 10:

            strong.append(
                "Güçlü Net Kâr Marjı"
            )

        elif net_margin < 0:

            weak.append(
                "Negatif Net Kâr"
            )

    # ========================================================
    # NET NAKİT
    # ========================================================

    net_cash = raw.get(
        "net_cash"
    )

    if (
        net_cash is not None
        and
        not pd.isna(
            net_cash
        )
    ):

        if net_cash > 0:

            strong.append(
                "Pozitif Net Nakit"
            )

        else:

            weak.append(
                "Negatif Net Nakit"
            )

    # ========================================================
    # FAALİYET NAKİT AKIŞI
    # ========================================================

    ocf = raw.get(
        "operating_cash_flow"
    )

    if (
        ocf is not None
        and
        not pd.isna(
            ocf
        )
    ):

        if ocf > 0:

            strong.append(
                "Pozitif Faaliyet Nakit Akışı"
            )

        else:

            weak.append(
                "Negatif Faaliyet Nakit Akışı"
            )

    # ========================================================
    # CARİ ORAN
    # ========================================================

    current_ratio = raw.get(
        "current_ratio"
    )

    if (
        current_ratio is not None
        and
        not pd.isna(
            current_ratio
        )
    ):

        if current_ratio >= 1.50:

            strong.append(
                "Güçlü Likidite"
            )

        elif current_ratio < 1:

            weak.append(
                "Zayıf Likidite"
            )

    return strong, weak


# ============================================================
# TEK FONKSİYONLA TÜM ANALİZ
# ============================================================

def analyze_financials(symbol):

    symbol = (
        str(symbol)
        .upper()
        .strip()
    )

    # ========================================================
    # FİNANSAL SAĞLIK
    # ========================================================

    health = get_financial_health(
        symbol
    )

    # ========================================================
    # FİNANSAL TREND
    # ========================================================

    trend_df = get_financial_trend(
        symbol
    )

    if trend_df is not None:

        trend = (
            calculate_financial_trend_score(
                trend_df
            )
        )

    else:

        trend = {

            "score":
                50.0,

            "signal":
                "🟡 VERİ YETERSİZ",

            "strong_points": [],

            "weak_points": [],

            "neutral_points": [],

            "previous_quarter":
                None,

            "previous_year":
                None,
        }

    # ========================================================
    # SAĞLIK NOKTALARI
    # ========================================================

    health_strong, health_weak = (
        get_health_points(
            health
        )
    )

    # ========================================================
    # TREND NOKTALARI
    # ========================================================

    trend_strong = trend.get(
        "strong_points",
        []
    )

    trend_weak = trend.get(
        "weak_points",
        []
    )

    # ========================================================
    # BİRLEŞTİR
    # ========================================================

    strong_points = []

    weak_points = []

    for item in (
        health_strong
        +
        trend_strong
    ):

        if item not in strong_points:

            strong_points.append(
                item
            )

    for item in (
        health_weak
        +
        trend_weak
    ):

        if item not in weak_points:

            weak_points.append(
                item
            )

    # ========================================================
    # ÇAKIŞAN GÜÇLÜ / ZAYIF NOKTALARI TEMİZLE
    # ========================================================

    weak_points = [

        item

        for item in weak_points

        if item not in strong_points
    ]

    # ========================================================
    # FİNANSAL TREND VERİ YETERLİLİĞİ
    # ========================================================

    if trend_df is None:

        trend_available = False

    else:

        trend_available = (
            len(trend_df) >= 2
        )

    # ========================================================
    # SONUÇ
    # ========================================================

    return {

        "symbol":
            symbol,

        "financial_score":
            health.get(
                "score"
            ),

        "financial_signal":
            health.get(
                "signal"
            ),

        "financial_available":
            health.get(
                "available",
                False
            ),

        "financial_trend_score":
            trend.get(
                "score",
                50.0
            ),

        "financial_trend_signal":
            trend.get(
                "signal",
                "🟡 VERİ YETERSİZ"
            ),

        "financial_trend_available":
            trend_available,

        "strong_points":
            strong_points,

        "weak_points":
            weak_points,

        "health":
            health,

        "trend":
            trend_df,

        "trend_detail":
            trend,
    }