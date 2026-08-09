# modules/analysis/balance_sheet.py

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional

import pandas as pd


# ============================================================
# DB
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]
DB_PATH = BASE_DIR / "borsa.db"


def get_connection() -> sqlite3.Connection:
    """Merkezi AI PRO veritabanına bağlanır."""
    return sqlite3.connect(DB_PATH)


# ============================================================
# YARDIMCI FONKSİYONLAR
# ============================================================

def safe_div(
    numerator: Optional[float],
    denominator: Optional[float]
) -> Optional[float]:
    """Sıfıra bölme ve eksik veri problemlerini önler."""

    if numerator is None or denominator is None:
        return None

    if pd.isna(numerator) or pd.isna(denominator):
        return None

    if denominator == 0:
        return None

    return numerator / denominator


def avg_balance(
    current: Optional[float],
    previous: Optional[float]
) -> Optional[float]:
    """
    Dönem başı ve dönem sonu bakiyesinin ortalamasını hesaplar.

    Önceki dönem yoksa sadece mevcut değeri kullanır.
    """

    if current is None or pd.isna(current):
        return None

    if previous is None or pd.isna(previous):
        return current

    return (current + previous) / 2


# ============================================================
# HAM VERİYİ OKU
# ============================================================

def get_financial_statement(
    symbol: str,
    period: str
) -> Optional[pd.Series]:
    """
    financial_statements tablosundan belirli şirket/dönem verisini getirir.
    """

    symbol = symbol.upper().replace(".IS", "")

    query = """
        SELECT *
        FROM financial_statements
        WHERE symbol = ?
          AND period = ?
        LIMIT 1
    """

    with get_connection() as conn:
        df = pd.read_sql_query(
            query,
            conn,
            params=(symbol, period)
        )

    if df.empty:
        return None

    return df.iloc[0]


def get_previous_statement(
    symbol: str,
    period_end: str
) -> Optional[pd.Series]:
    """
    Mevcut dönemin öncesindeki en yakın finansal tabloyu getirir.

    Özellikle:
    - alacak günleri
    - stok günleri

    hesaplarında kullanılacak.
    """

    symbol = symbol.upper().replace(".IS", "")

    query = """
        SELECT *
        FROM financial_statements
        WHERE symbol = ?
          AND period_end < ?
        ORDER BY period_end DESC
        LIMIT 1
    """

    with get_connection() as conn:
        df = pd.read_sql_query(
            query,
            conn,
            params=(symbol, period_end)
        )

    if df.empty:
        return None

    return df.iloc[0]


# ============================================================
# FİNANSAL KRİTERLER
# ============================================================

def calculate_net_margin(data: pd.Series) -> Optional[float]:
    """
    Net Kâr Marjı (%)

    Net Kâr / Hasılat × 100
    """

    result = safe_div(
        data["net_profit"],
        data["revenue"]
    )

    return result * 100 if result is not None else None


def calculate_net_debt(data: pd.Series) -> Optional[float]:
    """
    Net Borç

    Kısa vadeli finansal borç
    + Uzun vadeli borcun kısa vadeli kısmı
    + Uzun vadeli finansal borç
    - Nakit
    """

    debt_columns = [
        "short_term_financial_debt",
        "current_portion_long_term_debt",
        "long_term_financial_debt",
    ]

    values = []

    for column in debt_columns:
        value = data[column]

        if value is not None and not pd.isna(value):
            values.append(float(value))

    cash = data["cash"]

    if not values or cash is None or pd.isna(cash):
        return None

    return sum(values) - float(cash)


def calculate_net_debt_ebitda(
    data: pd.Series
) -> Optional[float]:
    """
    Net Borç / FAVÖK
    """

    net_debt = calculate_net_debt(data)

    if net_debt is None:
        return None

    return safe_div(
        net_debt,
        data["ebitda"]
    )


def calculate_cfo_margin(
    data: pd.Series
) -> Optional[float]:
    """
    Faaliyetlerden Nakit Akışı / Ciro (%)
    """

    result = safe_div(
        data["operating_cash_flow"],
        data["revenue"]
    )

    return result * 100 if result is not None else None


def calculate_current_ratio(
    data: pd.Series
) -> Optional[float]:
    """
    Cari Oran

    Dönen Varlıklar / Kısa Vadeli Yükümlülükler
    """

    return safe_div(
        data["current_assets"],
        data["current_liabilities"]
    )


def calculate_equity_asset_ratio(
    data: pd.Series
) -> Optional[float]:
    """
    Özkaynak / Toplam Varlık (%)
    """

    result = safe_div(
        data["equity"],
        data["total_assets"]
    )

    return result * 100 if result is not None else None


def calculate_interest_coverage(
    data: pd.Series
) -> Optional[float]:
    """
    Faiz Karşılama Oranı

    Esas Faaliyet Kârı / Faiz Gideri
    """

    return safe_div(
        data["operating_profit"],
        data["interest_expense"]
    )


def calculate_receivable_days(
    data: pd.Series,
    previous: Optional[pd.Series]
) -> Optional[float]:
    """
    Alacak Tahsil Süresi

    Ortalama Ticari Alacak / Hasılat × Dönem Gün Sayısı
    """

    avg_receivables = avg_balance(
        data["trade_receivables"],
        previous["trade_receivables"]
        if previous is not None
        else None
    )

    ratio = safe_div(
        avg_receivables,
        data["revenue"]
    )

    if ratio is None:
        return None

    return ratio * 90


def calculate_inventory_days(
    data: pd.Series,
    previous: Optional[pd.Series]
) -> Optional[float]:
    """
    Stok Süresi

    Ortalama Stok / Satışların Maliyeti × Dönem Gün Sayısı
    """

    avg_inventory = avg_balance(
        data["inventory"],
        previous["inventory"]
        if previous is not None
        else None
    )

    ratio = safe_div(
        avg_inventory,
        data["cost_of_sales"]
    )

    if ratio is None:
        return None

    return ratio * 90


def calculate_net_debt_equity(
    data: pd.Series
) -> Optional[float]:
    """
    Net Borç / Özkaynak (%)
    """

    net_debt = calculate_net_debt(data)

    result = safe_div(
        net_debt,
        data["equity"]
    )

    return result * 100 if result is not None else None


def calculate_revenue_growth(
    data: pd.Series,
    previous: Optional[pd.Series]
) -> Optional[float]:
    """
    Ciro büyümesi (%)

    (Cari dönem ciro / Önceki karşılaştırılabilir dönem ciro - 1) × 100
    """

    if previous is None:
        return None

    previous_revenue = previous["revenue"]

    result = safe_div(
        data["revenue"],
        previous_revenue
    )

    if result is None:
        return None

    return (result - 1) * 100


# ============================================================
# 10 KRİTERİ TEK SEFERDE HESAPLA
# ============================================================

def calculate_balance_metrics(
    symbol: str,
    period: str
) -> Optional[dict]:
    """
    Bir şirket ve dönem için bütün finansal kriterleri hesaplar.

    Bu fonksiyon henüz puanlama yapmaz.
    Sadece finansal oranları üretir.
    """

    data = get_financial_statement(
        symbol,
        period
    )

    if data is None:
        return None

    previous = get_previous_statement(
        symbol,
        data["period_end"]
    )

    metrics = {
        "symbol": symbol.upper().replace(".IS", ""),
        "period": period,
        "period_end": data["period_end"],

        # 1
        "net_margin": calculate_net_margin(data),

        # 2
        "net_debt_ebitda": calculate_net_debt_ebitda(data),

        # 3
        "cfo_margin": calculate_cfo_margin(data),

        # 4
        "current_ratio": calculate_current_ratio(data),

        # 5
        "equity_asset_ratio": calculate_equity_asset_ratio(data),

        # 6
        "interest_coverage": calculate_interest_coverage(data),

        # 7
        "receivable_days": calculate_receivable_days(
            data,
            previous
        ),

        # 8
        "inventory_days": calculate_inventory_days(
            data,
            previous
        ),

        # 9
        "net_debt_equity": calculate_net_debt_equity(data),

        # 10
        "revenue_growth": calculate_revenue_growth(
            data,
            previous
        ),

        # Kontrol
        "data_quality": calculate_data_quality(data),
    }

    return metrics


# ============================================================
# VERİ KALİTESİ
# ============================================================

def calculate_data_quality(
    data: pd.Series
) -> float:
    """
    10 kriter için gerekli temel alanların ne kadarının dolu
    olduğunu gösterir.

    Eksik veriyi 0 kabul etmiyoruz.
    """

    required = [
        "revenue",
        "net_profit",
        "ebitda",
        "cash",
        "current_assets",
        "current_liabilities",
        "total_assets",
        "equity",
        "trade_receivables",
        "inventory",
        "operating_cash_flow",
    ]

    available = 0

    for column in required:
        value = data[column]

        if value is not None and not pd.isna(value):
            available += 1

    return round(
        available / len(required) * 100,
        2
    )


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    for symbol in ["ASTOR", "TUPRS"]:

        result = calculate_balance_metrics(
            symbol,
            "2026/03"
        )

        print("\n" + "=" * 60)
        print(f"{symbol} - 2026/03")
        print("=" * 60)

        if result is None:
            print("Veri bulunamadı.")
            continue

        for key, value in result.items():
            print(
                f"{key:25}: {value}"
            )