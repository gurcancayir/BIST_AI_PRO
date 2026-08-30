import sqlite3

import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf

from modules.data.yahoo_data import get_stock_analysis
from modules.data.fundamental import (
    get_fundamental_data,
    calculate_fundamental_score,
)
from modules.ai.market_ai import get_market_score


# ============================================================
# SAYFA AYARLARI
# ============================================================

st.set_page_config(
    page_title="Hisse Analiz Merkezi",
    page_icon="📈",
    layout="wide",
)

st.title("📈 HİSSE ANALİZ MERKEZİ")

st.caption(
    "PRO V2 • Şirket Kalitesi + KAP Bilanço Kalitesi + "
    "Vade Bazlı Teknik Zamanlama + Finansal Risk Kapıları"
)


# ============================================================
# YENİ KULLANICI REHBERİ
# ============================================================

with st.expander(
    "📘 Bu sayfa nasıl çalışıyor? — Yeni kullanıcı rehberi"
):

    st.markdown(
        """
# BIST AI PRO Hisse Analiz Merkezi

Bu ekran bir hissenin yalnızca fiyatına bakmaz.

Bir hisseyi farklı katmanlarda değerlendirir ve sonunda
**işlem kararı için bir karar destek sistemi** oluşturur.

---

## 1️⃣ Teknik Skor

Fiyatın ve grafik yapısının gücünü ölçer.

Dikkate alınan başlıca göstergeler:

- MA5 / MA20 / MA50 / MA100 / MA200
- EMA9 / EMA20
- RSI
- Momentum
- Hacim
- Kısa / orta / uzun vadeli trend
- Hareketli ortalama kesişimleri

**Amaç:**

> Hissenin fiyat yapısı güçlü mü, zayıf mı?

---

## 2️⃣ Fundamental Skor

Şirketin işletme ve değerleme kalitesini değerlendirir.

Örneğin:

- F/K
- PD/DD
- Kâr marjı
- Ciro büyümesi
- Kârlılık
- Temel şirket performansı

**Amaç:**

> Şirket ekonomik olarak kaliteli mi?

---

## 3️⃣ Financial Skor 🏦

Financial Skor şirketin mevcut finansal sağlığını gösterir.

### Financial Skor

Şirketin **mevcut finansal sağlığını** ölçer.

Örneğin:

- Borçluluk
- Likidite
- Özkaynak yapısı
- Nakit
- Finansal borç
- Bilanço gücü

### Basitçe:

> Financial Skor = Şirketin finansal sağlığı bugün nasıl?

Örneğin:

**Financial = 80**

şirketin mevcut finansal yapısının güçlü olduğunu gösterir.

---

## 4️⃣ Sektör Skoru 🏭

Hissenin bulunduğu sektörün genel gücünü değerlendirir.

İyi bir şirket bile zayıf bir sektörde baskı altında kalabilir.

---

## 4️⃣ Sektör Skoru 🏭

Hissenin bulunduğu sektörün genel gücünü değerlendirir.

İyi bir şirket bile zayıf bir sektörde baskı altında kalabilir.

---

## 5️⃣ Piyasa Skoru 🌍

Genel BIST ortamını değerlendirir.

Piyasa güçlü olduğunda pozitif teknik yapılar daha kolay devam edebilir.

Piyasa zayıf olduğunda ise iyi şirketlerde bile
yeni girişlerde daha temkinli olunur.

---

## 6️⃣ Alım / Satış Teyidi 🚦

En önemli ayrımlardan biridir.

### Yüksek Genel Skor ≠ otomatik AL

Örneğin:

**Genel Skor = 82**

olabilir.

Ancak:

**Alım Teyidi = YOK**

ise sistem:

> Yüksek kaliteli fakat giriş için uygun teyit oluşmadı.

diyebilir.

---

## ⚠️ Kısa vadede özel kontrol

Kısa vadeli işlemlerde ayrıca:

- RSI
- Dirence uzaklık
- Momentum
- EMA9 / EMA20
- Hacim

kontrol edilir.

Örneğin:

**Genel Skor = 80**

**Alım Teyidi = VAR**

ancak:

**RSI = 78**

ve fiyat direncin hemen altındaysa:

> Hisse güçlü ancak giriş kovalanmamalı.

şeklinde karar üretilebilir.

---

# 🎯 Sistemin temel sırası

**1. Şirket kaliteli mi?**

↓

**2. Finansal olarak sağlıklı mı?**

↓

**3. Finansal yapı iyileşiyor mu?**

↓

**4. Teknik trend yukarı mı?**

↓

**5. Sektör destekliyor mu?**

↓

**6. Piyasa destekliyor mu?**

↓

**7. Giriş için teknik teyit var mı?**

↓

**8. Fiyat aşırı yükselmiş veya dirence çok yakın mı?**

↓

## SON KARAR

BIST AI PRO bir **karar destek sistemidir**.

Tek başına yatırım danışmanlığı değildir.
"""
    )


# ============================================================
# YARDIMCI FONKSİYONLAR
# ============================================================

def safe_float(value, default=0.0):

    try:

        if value is None or pd.isna(value):
            return default

        return float(value)

    except Exception:

        return default


def clamp(
    value,
    low=0.0,
    high=100.0,
):

    try:
        value = float(value)
    except Exception:
        value = 50.0

    return max(
        low,
        min(high, value),
    )


def fmt_money(value):

    if value is None or pd.isna(value):
        return "-"

    return (
        f"{float(value):,.2f}"
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )


# ============================================================
# PORTFÖY KONTROLÜ
# ============================================================

def get_portfolio_position(symbol):

    try:

        conn = sqlite3.connect("borsa.db")

        tables = pd.read_sql_query(
            """
            SELECT name
            FROM sqlite_master
            WHERE type='table'
            """,
            conn,
        )

        if "portfolio" not in set(
            tables["name"].tolist()
        ):

            conn.close()

            return False, 0.0, 0.0

        cols = pd.read_sql_query(
            "PRAGMA table_info(portfolio)",
            conn,
        )["name"].tolist()

        symbol_col = next(
            (
                c
                for c in [
                    "symbol",
                    "ticker",
                    "stock",
                    "hisse",
                    "hisse_kodu",
                ]
                if c in cols
            ),
            None,
        )

        if symbol_col is None:

            conn.close()

            return False, 0.0, 0.0

        df = pd.read_sql_query(
            f"""
            SELECT *
            FROM portfolio
            WHERE UPPER({symbol_col}) = ?
            """,
            conn,
            params=(symbol.upper(),),
        )

        conn.close()

        if df.empty:

            return False, 0.0, 0.0

        shares = 0.0

        for col in [
            "quantity",
            "shares",
            "lot",
            "adet",
            "kalan_adet",
        ]:

            if col in df.columns:

                shares = safe_float(
                    df[col].sum(),
                    0,
                )

                break

        weight = 0.0

        for col in [
            "portfolio_weight",
            "weight",
            "portfoy_pct",
            "portfoy",
        ]:

            if col in df.columns:

                weight = safe_float(
                    df[col].iloc[-1],
                    0,
                )

                break

        return (
            True,
            shares,
            weight,
        )

    except Exception:

        return (
            False,
            0.0,
            0.0,
        )


# ============================================================
# FINANCIAL SKOR — KAP / financial_statements TABLOSUNDAN
# ============================================================
#
# Bu sayfada Financial Skor'u doğrudan SQLite içindeki
# financial_statements tablosundan hesaplıyoruz.
# Böylece calculate_financial_score(symbol) gibi farklı sürümlerde
# değişebilen fonksiyon imzalarına bağımlı kalmıyoruz.
#
# ÖNEMLİ AYRIM:
#   Financial Skor  = şirketin MEVCUT finansal sağlığı
#     = bu sağlığın ZAMAN İÇİNDEKİ yönü
#
# Veri yoksa 50 vermek artık "gerçek skor" gibi gösterilmiyor.
# financial_available=False tutuluyor ve ekranda açıkça VERİ YOK deniyor.
# ============================================================

def _score_current_ratio(value):
    value = safe_float(value, np.nan)
    if np.isnan(value):
        return None
    if value >= 2.0:
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


def _score_debt_equity(value):
    value = safe_float(value, np.nan)
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


def _score_net_margin(value):
    value = safe_float(value, np.nan)
    if np.isnan(value):
        return None
    # net_margin yüzde olarak hesaplanır.
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


def _score_cash_to_debt(net_cash, equity):
    net_cash = safe_float(net_cash, np.nan)
    equity = safe_float(equity, np.nan)
    if np.isnan(net_cash) or np.isnan(equity) or equity == 0:
        return None
    ratio = net_cash / abs(equity)
    if ratio >= 0.50:
        return 100.0
    if ratio >= 0.25:
        return 90.0
    if ratio >= 0.00:
        return 75.0
    if ratio >= -0.25:
        return 55.0
    if ratio >= -0.50:
        return 35.0
    return 15.0


def _score_operating_cash_flow(value, net_profit):
    ocf = safe_float(value, np.nan)
    profit = safe_float(net_profit, np.nan)
    if np.isnan(ocf):
        return None
    if ocf < 0:
        return 20.0
    if np.isnan(profit) or profit == 0:
        return 70.0 if ocf > 0 else 50.0
    ratio = ocf / abs(profit)
    if ratio >= 1.20:
        return 100.0
    if ratio >= 0.80:
        return 90.0
    if ratio >= 0.50:
        return 75.0
    if ratio > 0:
        return 60.0
    return 20.0


def _score_equity_ratio(value):
    value = safe_float(value, np.nan)
    if np.isnan(value):
        return None
    if value >= 0.60:
        return 100.0
    if value >= 0.45:
        return 90.0
    if value >= 0.30:
        return 75.0
    if value >= 0.20:
        return 55.0
    if value >= 0.10:
        return 35.0
    return 15.0


def _score_interest_coverage(value):
    value = safe_float(value, np.nan)
    if np.isnan(value):
        return None
    if value >= 6:
        return 100.0
    if value >= 4:
        return 90.0
    if value >= 2.5:
        return 75.0
    if value >= 1.5:
        return 55.0
    if value >= 1.0:
        return 35.0
    return 10.0


def _score_growth(value):
    value = safe_float(value, np.nan)
    if np.isnan(value):
        return None
    if value >= 25:
        return 100.0
    if value >= 15:
        return 90.0
    if value >= 5:
        return 75.0
    if value >= 0:
        return 60.0
    if value >= -10:
        return 40.0
    if value >= -25:
        return 25.0
    return 10.0


def _score_days(value, excellent, good, acceptable, weak):
    value = safe_float(value, np.nan)
    if np.isnan(value) or value < 0:
        return None
    if value <= excellent:
        return 100.0
    if value <= good:
        return 85.0
    if value <= acceptable:
        return 70.0
    if value <= weak:
        return 45.0
    return 20.0


def _score_net_debt_ebitda(value):
    value = safe_float(value, np.nan)
    if np.isnan(value):
        return None
    if value <= 0:
        return 100.0
    if value <= 1:
        return 90.0
    if value <= 2:
        return 80.0
    if value <= 3:
        return 65.0
    if value <= 4:
        return 45.0
    if value <= 5:
        return 30.0
    return 10.0


FINANCIAL_WEIGHTS = {
    "Net Kâr Marjı": 0.12,
    "Net Borç / FAVÖK": 0.12,
    "Faaliyet Nakit Akışı": 0.15,
    "Cari Oran": 0.08,
    "Özkaynak / Varlık": 0.08,
    "Faiz Karşılama": 0.10,
    "Alacak Tahsil Süresi": 0.06,
    "Stok Devir Süresi": 0.06,
    "Net Nakit / Özkaynak": 0.08,
    "Ciro Büyümesi": 0.10,
    "Son Çeyrek İvmesi": 0.05,
}


def get_financial_health(symbol):
    """financial_statements tablosundaki en güncel KAP döneminden
    mevcut finansal sağlık skorunu üretir.

    Dönen yapı özellikle veri kalitesini de taşır. Böylece eksik KAP
    verisini 50 puanmış gibi göstermeyiz.
    """
    result = {
        "available": False,
        "score": None,
        "signal": "VERİ YOK",
        "latest": None,
        "valid_metrics": 0,
        "total_metrics": len(FINANCIAL_WEIGHTS),
        "metrics": {},
        "missing": [],
        "message": "financial_statements tablosunda kullanılabilir finansal veri bulunamadı.",
    }

    try:
        conn = sqlite3.connect("borsa.db")
        tables = pd.read_sql_query(
            "SELECT name FROM sqlite_master WHERE type='table'",
            conn,
        )["name"].tolist()

        if "financial_statements" not in tables:
            conn.close()
            result["message"] = "financial_statements tablosu bulunamadı."
            return result

        df = pd.read_sql_query(
            """
            SELECT *
            FROM financial_statements
            WHERE UPPER(symbol) = ?
            ORDER BY period_end DESC
            """,
            conn,
            params=(symbol.upper(),),
        )
        conn.close()

        if df.empty:
            result["message"] = f"{symbol} için financial_statements tablosunda kayıt yok."
            return result

        df["period_end"] = pd.to_datetime(df["period_end"], errors="coerce")
        df = df.dropna(subset=["period_end"])
        if "updated_at" in df.columns:
            df["updated_at"] = pd.to_datetime(df["updated_at"], errors="coerce")
            df = df.sort_values(["period_end", "updated_at"])
        else:
            df = df.sort_values("period_end")
        df = df.drop_duplicates(subset=["period_end"], keep="last")
        if df.empty:
            result["message"] = f"{symbol} için geçerli dönem tarihi bulunamadı."
            return result

        latest = df.iloc[-1].copy()
        previous_rows = df[df["period_end"] < latest["period_end"]]
        previous = previous_rows.iloc[-1].copy() if not previous_rows.empty else None
        latest_date = latest["period_end"]
        yoy_rows = df[
            (df["period_end"].dt.year == latest_date.year - 1)
            & (df["period_end"].dt.month == latest_date.month)
        ]
        previous_year = yoy_rows.iloc[-1].copy() if not yoy_rows.empty else None
        result["latest"] = latest

        def first_value(row, *columns):
            if row is None:
                return np.nan
            for col in columns:
                if col in row.index:
                    value = safe_float(row.get(col), np.nan)
                    if not np.isnan(value):
                        return value
            return np.nan

        def val(*columns):
            return first_value(latest, *columns)

        def prev(*columns):
            return first_value(previous, *columns)

        def yoy(*columns):
            return first_value(previous_year, *columns)

        current_assets = val("current_assets")
        current_liabilities = val("current_liabilities")
        total_assets = val("total_assets", "assets")
        equity = val("equity", "total_equity")
        net_profit = val("net_profit", "period_profit")
        revenue = val("revenue", "sales")
        cash = val("cash")
        ocf = val("operating_cash_flow", "cash_flow_from_operations")
        operating_profit = val("operating_profit", "ebit", "main_operating_profit")
        finance_expense = abs(val("finance_expense", "financial_expense"))
        ebitda = val("ebitda", "favok")
        depreciation = val("depreciation_amortization", "depreciation")
        receivables = val("trade_receivables", "receivables")
        inventory = val("inventories", "inventory", "stocks")
        cost_of_sales = abs(val("cost_of_sales", "cost_of_revenue"))

        debt_parts = []
        for col in [
            "short_term_financial_debt",
            "current_portion_long_term_debt",
            "long_term_financial_debt",
        ]:
            x = val(col)
            if not np.isnan(x):
                debt_parts.append(x)

        financial_debt = sum(debt_parts) if debt_parts else np.nan
        current_ratio = (
            current_assets / current_liabilities
            if not np.isnan(current_assets)
            and not np.isnan(current_liabilities)
            and current_liabilities != 0
            else np.nan
        )
        debt_equity = (
            financial_debt / equity
            if not np.isnan(financial_debt)
            and not np.isnan(equity)
            and equity != 0
            else np.nan
        )
        net_margin = (
            net_profit / revenue * 100
            if not np.isnan(net_profit)
            and not np.isnan(revenue)
            and revenue != 0
            else np.nan
        )
        net_cash = (
            cash - financial_debt
            if not np.isnan(cash) and not np.isnan(financial_debt)
            else np.nan
        )

        if np.isnan(ebitda) and not np.isnan(operating_profit) and not np.isnan(depreciation):
            ebitda = operating_profit + depreciation

        net_debt = -net_cash if not np.isnan(net_cash) else np.nan
        net_debt_ebitda = (
            net_debt / ebitda
            if not np.isnan(net_debt) and not np.isnan(ebitda) and ebitda > 0
            else np.nan
        )
        equity_ratio = (
            equity / total_assets
            if not np.isnan(equity) and not np.isnan(total_assets) and total_assets != 0
            else np.nan
        )
        interest_coverage = (
            operating_profit / finance_expense
            if not np.isnan(operating_profit) and not np.isnan(finance_expense) and finance_expense > 0
            else np.nan
        )

        revenue_growth = val("revenue_growth_yoy", "sales_growth_yoy")
        previous_revenue = yoy("revenue", "sales")
        if np.isnan(revenue_growth):
            revenue_growth = (
            (revenue / previous_revenue - 1) * 100
            if not np.isnan(revenue) and not np.isnan(previous_revenue) and previous_revenue > 0
            else np.nan
            )
        profit_growth = val(
            "quarterly_profit_growth",
            "net_profit_quarterly_growth",
            "quarter_momentum",
        )
        day_factor = {
            3: 90.0,
            6: 181.0,
            9: 273.0,
            12: 365.0,
        }.get(int(latest_date.month), 365.0)
        receivable_days = (
            receivables / revenue * day_factor
            if not np.isnan(receivables) and not np.isnan(revenue) and revenue > 0
            else np.nan
        )
        inventory_days = (
            inventory / cost_of_sales * day_factor
            if not np.isnan(inventory) and not np.isnan(cost_of_sales) and cost_of_sales > 0
            else np.nan
        )

        metrics = {
            "Net Kâr Marjı": _score_net_margin(net_margin),
            "Net Borç / FAVÖK": _score_net_debt_ebitda(net_debt_ebitda),
            "Faaliyet Nakit Akışı": _score_operating_cash_flow(ocf, net_profit),
            "Cari Oran": _score_current_ratio(current_ratio),
            "Özkaynak / Varlık": _score_equity_ratio(equity_ratio),
            "Faiz Karşılama": _score_interest_coverage(interest_coverage),
            "Alacak Tahsil Süresi": _score_days(receivable_days, 45, 75, 105, 150),
            "Stok Devir Süresi": _score_days(inventory_days, 45, 75, 120, 180),
            "Net Nakit / Özkaynak": _score_cash_to_debt(net_cash, equity),
            "Ciro Büyümesi": _score_growth(revenue_growth),
            "Son Çeyrek İvmesi": _score_growth(profit_growth),
        }

        result["raw"] = {
            "current_ratio": current_ratio,
            "debt_equity": debt_equity,
            "net_margin": net_margin,
            "net_cash": net_cash,
            "financial_debt": financial_debt,
            "equity": equity,
            "cash": cash,
            "net_profit": net_profit,
            "revenue": revenue,
            "operating_cash_flow": ocf,
            "total_assets": total_assets,
            "equity_ratio": equity_ratio,
            "operating_profit": operating_profit,
            "finance_expense": finance_expense,
            "interest_coverage": interest_coverage,
            "ebitda": ebitda,
            "net_debt_ebitda": net_debt_ebitda,
            "receivable_days": receivable_days,
            "inventory_days": inventory_days,
            "revenue_growth": revenue_growth,
            "profit_growth": profit_growth,
        }

        valid = {k: v for k, v in metrics.items() if v is not None and pd.notna(v)}
        result["metrics"] = valid
        result["valid_metrics"] = len(valid)

        result["missing"] = [k for k in metrics if k not in valid]

        # En az 4 bağımsız finansal göstergenin hesaplanabilmesi,
        # Financial Skor'u "gerçek skor" olarak göstermek için alt sınırdır.
        if len(valid) < 4:
            result["message"] = (
                f"{symbol} son KAP döneminde yalnızca {len(valid)}/{len(metrics)} "
                "Financial göstergesi hesaplanabildi; skor güvenilir kabul edilmedi."
            )
            return result

        used_weight = sum(FINANCIAL_WEIGHTS[k] for k in valid)
        score = (
            sum(valid[k] * FINANCIAL_WEIGHTS[k] for k in valid) / used_weight
            if used_weight > 0 else 50.0
        )
        result["score"] = round(clamp(score), 1)
        result["available"] = True

        if score >= 75:
            result["signal"] = "🟢 GÜÇLÜ"
        elif score >= 60:
            result["signal"] = "🟢 OLUMLU"
        elif score >= 45:
            result["signal"] = "🟡 ORTA"
        else:
            result["signal"] = "🔴 ZAYIF"

        period = str(latest.get("period", ""))
        date_text = pd.to_datetime(latest.get("period_end"), errors="coerce")
        if pd.notna(date_text):
            date_text = date_text.strftime("%d.%m.%Y")
        result["message"] = (
            f"Son finansal dönem: {period or '-'} / {date_text}. "
            f"{len(valid)}/{len(metrics)} Financial göstergesi kullanılabildi."
        )
        return result

    except Exception as exc:
        result["message"] = f"Financial Skor hesaplanırken hata oluştu: {exc}"
        return result


# ============================================================
# SEKTÖR MOTORU
# ============================================================

SECTOR_MAP = {

    "EREGL": "Metal",
    "KCAER": "Metal",
    "ISDMR": "Metal",

    "BIMAS": "Perakende",
    "MGROS": "Perakende",

    "TUPRS": "Enerji",

    "AKSA": "Kimya",

    "CCOLA": "Gıda",

    "TKFEN": "Holding/İnşaat",

    "KCHOL": "Holding",

    "MOBTL": "Teknoloji",

    "OYAKC": "Çimento",
    "CIMSA": "Çimento",
    "AKCNS": "Çimento",
    "NUHCM": "Çimento",
    "LMKDC": "Çimento",
    "BUCIM": "Çimento",
    "BTCIM": "Çimento",
    "BSOKE": "Çimento",
    "GOLTS": "Çimento",
    "KONYA": "Çimento",
    "AFYON": "Çimento",
}


SECTOR_BASE = {

    "Metal": 55,
    "Perakende": 70,
    "Enerji": 65,
    "Kimya": 60,
    "Gıda": 70,
    "Holding/İnşaat": 60,
    "Holding": 70,
    "Teknoloji": 60,
    "Çimento": 60,
    "Diğer": 55,
}


def sector_engine(
    symbol,
    analysis,
):

    sector_name = SECTOR_MAP.get(
        symbol,
        str(
            analysis.get(
                "sector"
            )
            or
            "Diğer"
        ),
    )

    score = SECTOR_BASE.get(
        sector_name,
        55,
    )

    return (
        float(score),
        sector_name,
    )


def financial_risk_engine(financial_data):
    if not financial_data.get("available"):
        return {"level": "unknown", "flags": [], "block_new_position": False}

    raw = financial_data.get("raw", {})
    flags = []
    if safe_float(raw.get("current_ratio"), np.nan) < 1:
        flags.append("cari oran 1'in altında")
    if safe_float(raw.get("interest_coverage"), np.nan) < 1:
        flags.append("faiz karşılama 1'in altında")
    if safe_float(raw.get("net_debt_ebitda"), np.nan) > 4:
        flags.append("net borç/FAVÖK 4'ün üzerinde")
    if safe_float(raw.get("operating_cash_flow"), np.nan) < 0:
        flags.append("işletme nakit akışı negatif")
    if safe_float(raw.get("operating_profit"), np.nan) < 0:
        flags.append("esas faaliyet sonucu negatif")

    severe = len(flags) >= 2 or any("faiz karşılama" in x for x in flags)
    return {
        "level": "high" if severe else ("medium" if flags else "low"),
        "flags": flags,
        "block_new_position": severe,
    }


# ============================================================
# TEKNİK GÖSTERGELER
# ============================================================

def build_indicators(df):

    df = df.copy()

    close = pd.to_numeric(
        df["Close"],
        errors="coerce",
    )

    volume = pd.to_numeric(
        df["Volume"],
        errors="coerce",
    )

    df["MA5"] = (
        close.rolling(5).mean()
    )

    df["MA20"] = (
        close.rolling(20).mean()
    )

    df["MA50"] = (
        close.rolling(50).mean()
    )

    df["MA100"] = (
        close.rolling(100).mean()
    )

    df["MA200"] = (
        close.rolling(200).mean()
    )

    df["EMA9"] = close.ewm(
        span=9,
        adjust=False,
    ).mean()

    df["EMA20"] = close.ewm(
        span=20,
        adjust=False,
    ).mean()

    # --------------------------------------------------------
    # RSI
    # --------------------------------------------------------

    delta = close.diff()

    gain = delta.clip(
        lower=0
    )

    loss = -delta.clip(
        upper=0
    )

    avg_gain = gain.ewm(
        alpha=1 / 14,
        adjust=False,
        min_periods=14,
    ).mean()

    avg_loss = loss.ewm(
        alpha=1 / 14,
        adjust=False,
        min_periods=14,
    ).mean()

    rs = (
        avg_gain
        /
        avg_loss.replace(
            0,
            np.nan,
        )
    )

    df["RSI"] = (

        100

        -

        (
            100
            /
            (1 + rs)
        )
    )

    # --------------------------------------------------------
    # Momentum
    # --------------------------------------------------------

    df["MOM5"] = (
        close
        /
        close.shift(5)
        - 1
    ) * 100

    df["MOM20"] = (
        close
        /
        close.shift(20)
        - 1
    ) * 100

    df["MOM60"] = (
        close
        /
        close.shift(60)
        - 1
    ) * 100

    df["MOM120"] = (
        close
        /
        close.shift(120)
        - 1
    ) * 100

    # --------------------------------------------------------
    # Hacim
    # --------------------------------------------------------

    df["VOL20"] = (
        volume.rolling(20).mean()
    )

    df["VOLUME_RATIO"] = (

        volume

        /

        df["VOL20"].replace(
            0,
            np.nan,
        )
    )

    # --------------------------------------------------------
    # MA5 kesişimleri
    # --------------------------------------------------------

    df["CROSS_UP_5"] = (

        (close > df["MA5"])

        &

        (
            close.shift(1)
            <=
            df["MA5"].shift(1)
        )
    )

    df["CROSS_DOWN_5"] = (

        (close < df["MA5"])

        &

        (
            close.shift(1)
            >=
            df["MA5"].shift(1)
        )
    )

    return df


# ============================================================
# TEKNİK MOTOR
# ============================================================

def technical_engine(df):

    last = df.iloc[-1]

    price = safe_float(
        last["Close"],
        0,
    )

    previous = safe_float(
        df["Close"].iloc[-2],
        price,
    )

    daily_change = (

        (
            price
            /
            previous
        )
        - 1
    ) * 100 if previous > 0 else 0

    ma5 = safe_float(
        last["MA5"],
        np.nan,
    )

    ma20 = safe_float(
        last["MA20"],
        np.nan,
    )

    ma50 = safe_float(
        last["MA50"],
        np.nan,
    )

    ma100 = safe_float(
        last["MA100"],
        np.nan,
    )

    ma200 = safe_float(
        last["MA200"],
        np.nan,
    )

    ema9 = safe_float(
        last["EMA9"],
        np.nan,
    )

    ema20 = safe_float(
        last["EMA20"],
        np.nan,
    )

    rsi = safe_float(
        last["RSI"],
        50,
    )

    mom5 = safe_float(
        last["MOM5"],
        0,
    )

    mom20 = safe_float(
        last["MOM20"],
        0,
    )

    mom60 = safe_float(
        last["MOM60"],
        0,
    )

    mom120 = safe_float(
        last["MOM120"],
        0,
    )

    volume_ratio = safe_float(
        last["VOLUME_RATIO"],
        1,
    )

    cross_up = bool(
        last["CROSS_UP_5"]
    )

    cross_down = bool(
        last["CROSS_DOWN_5"]
    )

    # ========================================================
    # KISA VADE
    # ========================================================

    short = 0

    if not np.isnan(ma5) and price > ma5:
        short += 15

    if not np.isnan(ema9) and price > ema9:
        short += 15

    if (
        not np.isnan(ema9)
        and not np.isnan(ema20)
        and ema9 > ema20
    ):
        short += 20

    if mom5 > 0:
        short += 10

    if mom20 > 0:
        short += 10

    if 45 <= rsi <= 65:
        short += 15

    elif 65 < rsi <= 72:
        short += 10

    elif 40 <= rsi < 45:
        short += 5

    elif rsi > 80:
        short -= 5

    elif rsi > 75:
        # Yeni:
        # RSI aşırı ısınmışsa kısa vadeli skoru
        # bir miktar frenliyoruz.
        short -= 3

    if volume_ratio >= 1.50:
        short += 10

    elif volume_ratio >= 1.10:
        short += 5

    if cross_up:
        short += 5

    short = clamp(short)

    # ========================================================
    # ORTA VADE
    # ========================================================

    mid = 0

    if not np.isnan(ma20) and price > ma20:
        mid += 15

    if not np.isnan(ma50) and price > ma50:
        mid += 15

    if (
        not np.isnan(ma20)
        and not np.isnan(ma50)
        and ma20 > ma50
    ):
        mid += 20

    if (
        not np.isnan(ema9)
        and not np.isnan(ema20)
        and ema9 > ema20
    ):
        mid += 10

    if mom20 > 0:
        mid += 10

    if mom60 > 0:
        mid += 15

    if not np.isnan(ma100) and price > ma100:
        mid += 10

    if volume_ratio >= 1:
        mid += 5

    mid = clamp(mid)

    # ========================================================
    # UZUN VADE
    # ========================================================

    long_technical = 0

    if not np.isnan(ma50) and price > ma50:
        long_technical += 15

    if not np.isnan(ma100) and price > ma100:
        long_technical += 15

    if (
        not np.isnan(ma50)
        and not np.isnan(ma100)
        and ma50 > ma100
    ):
        long_technical += 20

    if not np.isnan(ma200) and price > ma200:
        long_technical += 20

    if (
        not np.isnan(ma100)
        and not np.isnan(ma200)
        and ma100 > ma200
    ):
        long_technical += 10

    if mom60 > 0:
        long_technical += 10

    if mom120 > 0:
        long_technical += 10

    long_technical = clamp(
        long_technical
    )

    # ========================================================
    # TEKNİK BOZULMA
    # ========================================================

    breakdown = 0

    if not np.isnan(ma20) and price < ma20:
        breakdown += 1

    if not np.isnan(ma50) and price < ma50:
        breakdown += 1

    if not np.isnan(ma200) and price < ma200:
        breakdown += 1

    if mom60 < 0:
        breakdown += 1

    if mom120 < 0:
        breakdown += 1

    return {

        "price": price,

        "daily_change": daily_change,

        "short": short,

        "mid": mid,

        "long_technical": long_technical,

        "rsi": rsi,

        "mom5": mom5,

        "mom20": mom20,

        "mom60": mom60,

        "mom120": mom120,

        "volume_ratio": volume_ratio,

        "cross_up": cross_up,

        "cross_down": cross_down,

        "price_above_ema9": (
            bool(price > ema9)
            if not np.isnan(ema9)
            else False
        ),

        "ema9_above_ema20": (
            bool(ema9 > ema20)
            if (
                not np.isnan(ema9)
                and not np.isnan(ema20)
            )
            else False
        ),

        "price_above_ma50": (
            bool(price > ma50)
            if not np.isnan(ma50)
            else False
        ),

        "ma5": ma5,
        "ma20": ma20,
        "ma50": ma50,
        "ma100": ma100,
        "ma200": ma200,

        "ema9": ema9,
        "ema20": ema20,

        "technical_breakdown": breakdown,
    }


# ============================================================
# GİRİŞ KALİTESİ
# ============================================================

def entry_quality_engine(
    technical,
    resistance,
    horizon,
):
    """
    Yüksek skor ile iyi giriş noktasını birbirinden ayırır.

    Örneğin:

    Genel Skor = 80
    Alım Teyidi = VAR
    RSI = 78
    Direnç = çok yakın

    ise sistem doğrudan AL demek yerine
    girişin kovalanmaması gerektiğini söyler.
    """

    price = safe_float(
        technical["price"],
        0,
    )

    rsi = safe_float(
        technical["rsi"],
        50,
    )

    resistance = safe_float(
        resistance,
        0,
    )

    resistance_distance = None

    if (
        price > 0
        and resistance > price
    ):

        resistance_distance = (

            (
                resistance
                -
                price
            )
            /
            price
        ) * 100

    overbought = (
        rsi >= 75
    )

    extreme_overbought = (
        rsi >= 80
    )

    near_resistance = (

        resistance_distance is not None

        and

        resistance_distance <= 2.0
    )

    very_near_resistance = (

        resistance_distance is not None

        and

        resistance_distance <= 1.0
    )

    # --------------------------------------------------------
    # Sadece kısa vadede giriş filtresi güçlü çalışır.
    # --------------------------------------------------------

    if horizon.startswith("⚡"):

        if (
            extreme_overbought
            and very_near_resistance
        ):

            return {
                "status": "🚨 AŞIRI ISINMIŞ",
                "penalty": 15,
                "overbought": True,
                "near_resistance": True,
                "resistance_distance":
                    resistance_distance,
                "message":
                    "RSI çok yüksek ve fiyat dirence çok yakın. "
                    "Güçlü trend olmasına rağmen giriş kovalanmamalı.",
            }

        if (
            overbought
            and near_resistance
        ):

            return {
                "status": "🟡 GİRİŞİ KOVALAMA",
                "penalty": 10,
                "overbought": True,
                "near_resistance": True,
                "resistance_distance":
                    resistance_distance,
                "message":
                    "Hisse güçlü ancak RSI yüksek ve fiyat dirence yakın. "
                    "Daha iyi giriş veya direnç kırılımı beklenmeli.",
            }

        if overbought:

            return {
                "status": "🟡 RSI YÜKSEK",
                "penalty": 5,
                "overbought": True,
                "near_resistance": False,
                "resistance_distance":
                    resistance_distance,
                "message":
                    "Momentum güçlü ancak RSI yükselmiş durumda. "
                    "Yeni girişte kademeli hareket tercih edilmeli.",
            }

        if near_resistance:

            return {
                "status": "🟡 DİRENÇ YAKIN",
                "penalty": 5,
                "overbought": False,
                "near_resistance": True,
                "resistance_distance":
                    resistance_distance,
                "message":
                    "Fiyat önemli dirence yakın. "
                    "Direnç kırılımı veya geri çekilme izlenmeli.",
            }

    return {
        "status": "🟢 GİRİŞ KOŞULLARI UYGUN",
        "penalty": 0,
        "overbought": overbought,
        "near_resistance": near_resistance,
        "resistance_distance":
            resistance_distance,
        "message":
            "Aşırı ısınma veya kritik direnç kaynaklı "
            "belirgin bir giriş problemi görülmüyor.",
    }


# ============================================================
# ALIM / SATIŞ TEYİDİ
# ============================================================

def confirmation_engine(
    technical,
    entry_quality,
):

    buy_checks = {

        "Fiyat EMA9 üzerinde":
            technical[
                "price_above_ema9"
            ],

        "EMA9 > EMA20":
            technical[
                "ema9_above_ema20"
            ],

        "5G yukarı kesişim":
            technical[
                "cross_up"
            ],

        "20G momentum pozitif":
            technical[
                "mom20"
            ] > 0,

        "60G momentum pozitif":
            technical[
                "mom60"
            ] > 0,

        "Hacim destekli":
            technical[
                "volume_ratio"
            ] >= 1.10,
    }

    sell_checks = {

        "Fiyat EMA9 altında":
            not technical[
                "price_above_ema9"
            ],

        "EMA9 < EMA20":
            not technical[
                "ema9_above_ema20"
            ],

        "5G aşağı kesişim":
            technical[
                "cross_down"
            ],

        "20G momentum negatif":
            technical[
                "mom20"
            ] < 0,

        "60G momentum negatif":
            technical[
                "mom60"
            ] < 0,

        "Fiyat MA50 altında":
            not technical[
                "price_above_ma50"
            ],
    }

    buy_count = sum(
        bool(v)
        for v in buy_checks.values()
    )

    sell_count = sum(
        bool(v)
        for v in sell_checks.values()
    )

    # --------------------------------------------------------
    # Ham teknik alım teyidi
    # --------------------------------------------------------

    raw_buy_confirmation = (

        buy_count >= 4

        and

        technical["short"] >= 60

        and

        technical["mid"] >= 55
    )

    # --------------------------------------------------------
    # Yeni giriş filtresi
    #
    # RSI yüksek + direnç yakınsa teyidi tamamen silmiyoruz.
    #
    # Çünkü trend hâlâ güçlü olabilir.
    #
    # Fakat "AL" yerine "GİRİŞİ KOVALAMA"
    # durumuna dönüştürüyoruz.
    # --------------------------------------------------------

    entry_blocked = (
        entry_quality["penalty"] >= 10
    )

    buy_confirmation = (

        raw_buy_confirmation

        and

        not entry_blocked
    )

    sell_confirmation = (

        sell_count >= 4

        and

        (
            technical["short"] < 50

            or

            technical["mid"] < 55
        )
    )

    decline_signal = (

        sell_count >= 3

        or

        technical[
            "technical_breakdown"
        ] >= 3

        or

        (
            technical["short"] < 40
            and
            technical["mid"] < 50
        )
    )

    return {

        "buy_count": buy_count,

        "sell_count": sell_count,

        "raw_buy_confirmation":
            raw_buy_confirmation,

        "buy_confirmation":
            buy_confirmation,

        "sell_confirmation":
            sell_confirmation,

        "decline_signal":
            decline_signal,

        "entry_blocked":
            entry_blocked,

        "buy_checks":
            buy_checks,

        "sell_checks":
            sell_checks,
    }


# ============================================================
# VADE SKORLARI
# ============================================================

SHORT_WEIGHT = 0.20
MID_WEIGHT = 0.35
LONG_WEIGHT = 0.45


def weighted_score(
    components,
):
    """
    Veri olmayan bileşenlerin sisteme sahte şekilde
    tam ağırlıkla girmesini önler.

    Örneğin Financial veri yoksa Financial = 50 kabul edilip
    sanki gerçek bir skor varmış gibi davranılmaz.
    Mevcut bileşenlerin ağırlıkları yeniden normalize edilir.
    """

    valid = []

    for value, weight, available in components:

        if available:

            valid.append(
                (
                    safe_float(
                        value,
                        50,
                    ),
                    weight,
                )
            )

    if not valid:

        return 50.0

    total_weight = sum(
        weight
        for _, weight in valid
    )

    if total_weight <= 0:

        return 50.0

    score = sum(
        value * weight
        for value, weight in valid
    ) / total_weight

    return clamp(score)


def calculate_horizon_scores(
    technical,
    technical_score,
    fundamental,
    financial,
    sector,
    market,
    horizon,
    fundamental_available=True,
    financial_available=True,
):

    # --------------------------------------------------------
    # KISA VADE
    # --------------------------------------------------------

    short = weighted_score(
        [

            (
                technical["short"],
                0.45,
                True,
            ),

            (
                technical_score,
                0.15,
                True,
            ),

            (
                technical["mid"],
                0.10,
                True,
            ),

            (
                market,
                0.10,
                True,
            ),

            (
                sector,
                0.05,
                True,
            ),

            (
                fundamental,
                0.05,
                fundamental_available,
            ),

            (
                financial,
                0.10,
                financial_available,
            ),
        ]
    )

    # --------------------------------------------------------
    # ORTA VADE
    # --------------------------------------------------------

    mid = weighted_score(
        [

            (
                technical["mid"],
                0.20,
                True,
            ),

            (
                technical_score,
                0.10,
                True,
            ),

            (
                fundamental,
                0.20,
                fundamental_available,
            ),

            (
                financial,
                0.30,
                financial_available,
            ),

            (
                sector,
                0.10,
                True,
            ),

            (
                market,
                0.10,
                True,
            ),
        ]
    )

    # --------------------------------------------------------
    # UZUN VADE
    # --------------------------------------------------------

    long = weighted_score(
        [

            (
                fundamental,
                0.25,
                fundamental_available,
            ),

            (
                financial,
                0.40,
                financial_available,
            ),

            (
                technical["long_technical"],
                0.20,
                True,
            ),

            (
                sector,
                0.10,
                True,
            ),

            (
                market,
                0.05,
                True,
            ),
        ]
    )

    # --------------------------------------------------------
    # GENEL SKOR
    # --------------------------------------------------------

    if str(horizon).startswith("⚡"):
        horizon_weights = (0.60, 0.25, 0.15)
    elif str(horizon).startswith("📅"):
        horizon_weights = (0.25, 0.50, 0.25)
    else:
        horizon_weights = (0.10, 0.25, 0.65)

    general = (
        short * horizon_weights[0]
        + mid * horizon_weights[1]
        + long * horizon_weights[2]
    )

    return {

        "short": round(
            clamp(short),
            1,
        ),

        "mid": round(
            clamp(mid),
            1,
        ),

        "long": round(
            clamp(long),
            1,
        ),

        "general": round(
            clamp(general),
            1,
        ),
    }


# ============================================================
# KALİTE MOTORU
# ============================================================

def quality_engine(
    long_score,
    fundamental,
    financial,
    completeness=100,
):

    data_completeness = safe_float(
        completeness,
        100,
    )

    # --------------------------------------------------------
    # Finansal veri eksikse A kalite verilmesini engelliyoruz.
    # --------------------------------------------------------

    if (
        long_score >= 75
        and fundamental >= 70
        and financial >= 65
        and data_completeness >= 80
    ):

        return (
            round(
                (
                    long_score
                    +
                    fundamental
                    +
                    financial
                ) / 3,
                1,
            ),
            "🟢 A - Güçlü",
        )

    if (
        long_score >= 65
        and fundamental >= 55
        and financial >= 55
        and data_completeness >= 60
    ):

        return (
            round(
                (
                    long_score
                    +
                    fundamental
                    +
                    financial
                ) / 3,
                1,
            ),
            "🟢 B - Olumlu",
        )

    if long_score >= 50:

        return (
            round(
                (
                    long_score
                    +
                    fundamental
                    +
                    financial
                ) / 3,
                1,
            ),
            "🟡 C - İzle",
        )

    return (
        round(
            (
                long_score
                +
                fundamental
                +
                financial
            ) / 3,
            1,
        ),
        "🔴 D - Zayıf",
    )

# ============================================================
# OTOMATİK EYLEM KARARI
# ============================================================

def automatic_action_engine(
    scores,
    technical,
    confirmation,
    entry_quality,
    in_portfolio,
    resistance,
    financial_risk=None,
):
    """
    Nihai kullanıcı aksiyonunu belirler.

    Amaç:
    Yüksek skor ile hemen AL kararını birbirinden ayırmak.

    Sonuçlar:
        🟢 ŞİMDİ AL
        🟡 GİRİŞİ KOVALA
        🔵 KIRILIM BEKLE
        🟠 GERİ ÇEKİLME BEKLE
        🔴 SAT / ÇIKIŞI DEĞERLENDİR
        ⚪ BEKLE / TEYİT BEKLE
    """

    general = safe_float(
        scores.get("general"),
        0,
    )

    rsi = safe_float(
        technical.get("rsi"),
        50,
    )

    price = safe_float(
        technical.get("price"),
        0,
    )

    resistance = safe_float(
        resistance,
        0,
    )

    buy_confirmation = bool(
        confirmation.get(
            "buy_confirmation",
            False,
        )
    )

    sell_confirmation = bool(
        confirmation.get(
            "sell_confirmation",
            False,
        )
    )

    decline_signal = bool(
        confirmation.get(
            "decline_signal",
            False,
        )
    )

    raw_buy = bool(
        confirmation.get(
            "raw_buy_confirmation",
            False,
        )
    )

    entry_blocked = bool(
        confirmation.get(
            "entry_blocked",
            False,
        )
    )

    financial_risk = financial_risk or {}

    # --------------------------------------------------------
    # DİRENÇ MESAFESİ
    # --------------------------------------------------------

    resistance_distance = None

    if (
        price > 0
        and resistance > price
    ):
        resistance_distance = (
            (resistance - price)
            / price
        ) * 100

    near_resistance = (
        resistance_distance is not None
        and resistance_distance <= 2.0
    )

    very_near_resistance = (
        resistance_distance is not None
        and resistance_distance <= 1.0
    )

    # ========================================================
    # 1 — PORTFÖYDEKİ HİSSELER
    # ========================================================

    if in_portfolio:

        if sell_confirmation:
            return {
                "action": "🔴 SAT / ÇIKIŞI DEĞERLENDİR",
                "short_action": "SATIŞ TEYİDİ VAR",
                "message":
                    "Satış teyidi oluştu. "
                    "Pozisyon azaltma veya çıkış "
                    "değerlendirilmeli.",
                "status": "danger",
            }

        if decline_signal:
            return {
                "action": "🟠 DÜŞÜŞÜ İZLE",
                "short_action": "DÜŞÜŞ SİNYALİ",
                "message":
                    "Teknik yapıda zayıflama sinyali var. "
                    "Satış teyidi henüz oluşmadı; "
                    "pozisyon yakından izlenmeli.",
                "status": "warning",
            }

        return {
            "action": "🟢 TUT / POZİSYONU KORU",
            "short_action": "SATIŞ SİNYALİ YOK",
            "message":
                "Pozisyon için satış veya düşüş teyidi "
                "oluşmadı. Mevcut trend korunuyor.",
            "status": "success",
        }

    # ========================================================
    # 2 — PORTFÖYDE OLMAYAN HİSSE
    # ========================================================

    if decline_signal and not raw_buy:
        return {
            "action": "🔴 ALMA",
            "short_action": "DÜŞÜŞ SİNYALİ",
            "message":
                "Yeni pozisyon açılmamalı. "
                "Teknik yapının toparlanması beklenmeli.",
            "status": "danger",
        }

    if financial_risk.get("block_new_position"):
        flags = ", ".join(financial_risk.get("flags", [])[:3])
        return {
            "action": "🟠 FİNANSAL RİSK / BEKLE",
            "short_action": "BİLANÇO RİSK KAPISI",
            "message": f"Yeni giriş finansal risk kapısı nedeniyle bekletildi: {flags}.",
            "status": "warning",
        }

    # ========================================================
    # 3 — GERÇEK ALIM TEYİDİ
    # ========================================================

    if (
        buy_confirmation
        and general >= 75
        and not entry_blocked
    ):
        return {
            "action": "🟢 ŞİMDİ AL",
            "short_action": "ALIM TEYİDİ VAR",
            "message":
                "Genel skor güçlü, teknik alım teyidi "
                "oluştu ve giriş kalitesi uygun.",
            "status": "success",
        }

    # ========================================================
    # 4 — DİRENÇ KIRILIMI BEKLE
    # ========================================================

    if (
        raw_buy
        and entry_blocked
        and very_near_resistance
        and rsi >= 75
    ):
        resistance_text = (
            f"{resistance:.2f} TL"
            if resistance > 0
            else "direnç"
        )

        return {
            "action": "🔵 KIRILIM BEKLE",
            "short_action": "DİRENÇ ÇOK YAKIN",
            "message":
                f"Hisse güçlü ancak RSI yüksek ve "
                f"fiyat dirence çok yakın. "
                f"{resistance_text} üzerindeki hacimli "
                f"kırılım beklenmeli.",
            "status": "info",
        }

    # ========================================================
    # 5 — GERİ ÇEKİLME BEKLE
    # ========================================================

    if (
        raw_buy
        and entry_blocked
        and rsi >= 75
    ):
        return {
            "action": "🟠 GERİ ÇEKİLME BEKLE",
            "short_action": "FİYAT ISINMIŞ",
            "message":
                "Trend güçlü ancak RSI yüksek. "
                "Fiyatın soğuması ve daha iyi "
                "risk/getiri oluşması beklenmeli.",
            "status": "warning",
        }

    # ========================================================
    # 6 — GİRİŞİ KOVALA
    # ========================================================

    if (
        raw_buy
        and general >= 70
        and entry_blocked
    ):
        return {
            "action": "🟡 GİRİŞİ KOVALA",
            "short_action": "GÜÇLÜ AMA GİRİŞ UYGUN DEĞİL",
            "message":
                "Hisse güçlü ancak mevcut fiyatlama "
                "yeni giriş için ideal değil.",
            "status": "warning",
        }

    # ========================================================
    # 7 — NORMAL BEKLE
    # ========================================================

    return {
        "action": "⚪ BEKLE / TEYİT BEKLE",
        "short_action": "NET TEYİT YOK",
        "message":
            "Yeni pozisyon için yeterli teknik teyit "
            "henüz oluşmadı.",
        "status": "neutral",
    }
# ============================================================
# KARAR MOTORU
# ============================================================

def decision_engine(
    scores,
    quality,
    confirmation,
    in_portfolio,
    entry_quality,
    horizon,
    financial_risk=None,
):

    general = scores["general"]
    financial_risk = financial_risk or {}

    long_score = scores["long"]

    buy = confirmation[
        "buy_confirmation"
    ]

    raw_buy = confirmation[
        "raw_buy_confirmation"
    ]

    sell = confirmation[
        "sell_confirmation"
    ]

    decline = confirmation[
        "decline_signal"
    ]

    entry_blocked = (
        confirmation[
            "entry_blocked"
        ]
    )

    # ========================================================
    # PORTFÖYDE OLMAYAN HİSSE
    # ========================================================

    if not in_portfolio:

        if financial_risk.get("block_new_position"):
            return (
                "🟠 FİNANSAL RİSK / BEKLE",
                "Bilanço risk kapısı yeni pozisyonu engelliyor: "
                + ", ".join(financial_risk.get("flags", [])[:3])
                + ".",
            )

        # ----------------------------------------------------
        # Önce ciddi düşüş sinyali
        # ----------------------------------------------------

        if decline and not buy:

            return (
                "⛔ ALMA / DÜŞÜŞ SİNYALİ",

                "Hissede teknik düşüş sinyali var. "
                "Yeni pozisyon açılmıyor; "
                "teknik yapının toparlanması bekleniyor.",
            )

        # ----------------------------------------------------
        # Güçlü ama giriş kovalanmamalı
        # ----------------------------------------------------

        if (
            raw_buy
            and
            entry_blocked
        ):

            return (
                "🟡 GÜÇLÜ / GİRİŞİ KOVALAMA",

                entry_quality[
                    "message"
                ]
                +
                " Genel skor güçlü olsa da "
                "fiyatlama nedeniyle yeni giriş "
                "için daha iyi risk/getiri bekleniyor.",
            )

        # ----------------------------------------------------
        # Normal AL
        # ----------------------------------------------------

        if buy and general >= 75:

            return (
                "🟢 AL / KADEMELİ GİR",

                "Alım teyidi oluştu ve genel görünüm güçlü. "
                "Pozisyon kademeli şekilde değerlendirilebilir.",
            )

        if buy and general >= 60:

            return (
                "🟢 ALIM ADAYI",

                "Alım teyidi var ancak genel skor "
                "henüz güçlü AL bölgesinde değil.",
            )

        return (
            "🟡 İZLE / TEYİT BEKLE",

            "Alım teyidi oluşmadı. "
            "Yüksek skor olsa bile teyitsiz "
            "yeni pozisyon açılmıyor.",
        )

    # ========================================================
    # PORTFÖYDEKİ HİSSE
    # ========================================================

    if in_portfolio:

        # ----------------------------------------------------
        # Güçlü satış teyidi
        # ----------------------------------------------------

        if (
            sell
            and
            long_score < 45
        ):

            return (
                "🔴 SATIŞ TEYİDİ",

                "Satış teyidi oluştu ve "
                "uzun vadeli yapı da ciddi "
                "zayıflık gösteriyor.",
            )

        # ----------------------------------------------------
        # Düşüş sinyali var ama satış teyidi yok
        # ----------------------------------------------------

        if (
            decline
            and
            not sell
        ):

            if quality.startswith(
                "🟢 A"
            ):

                return (
                    "🟡 TUT / TEYİT BEKLE",

                    "A kalite yapı korunuyor. "
                    "Düşüş sinyali var ancak "
                    "satış teyidi henüz oluşmadı.",
                )

            return (
                "🟠 AZALT / TEYİT BEKLE",

                "Teknik yapı zayıflıyor. "
                "Satış teyidi oluşmadan "
                "kontrollü izleme tercih ediliyor.",
            )

        # ----------------------------------------------------
        # Portföydeki güçlü hisse
        # ----------------------------------------------------

        if (
            buy
            and
            general >= 75
        ):

            return (
                "🟢 TUT / GÜÇLÜ",

                "Pozisyonun teknik görünümü güçlü "
                "ve alım teyidi korunuyor.",
            )

        if general >= 55:

            return (
                "🟡 TUT",

                "Mevcut pozisyon korunabilir; "
                "yeni işlem için ek teyit bekleniyor.",
            )

    # ========================================================
    # GENEL ZAYIFLIK
    # ========================================================

    if general < 45:

        return (
            "🟠 İZLE / TEMKİNLİ",

            "Genel skor zayıf; "
            "net işlem üstünlüğü oluşmadı.",
        )

    return (
        "🟡 TUT / İZLE",

        "Göstergeler karışık ve "
        "net işlem üstünlüğü oluşmadı.",
    )


# ============================================================
# GÜVEN SKORU
# ============================================================

def confidence_engine(
    scores,
    data_completeness,
    fundamental_available=True,
    financial_available=True,
):

    values = [

        scores["short"],

        scores["mid"],

        scores["long"],
    ]

    spread = (

        max(values)

        -

        min(values)
    )

    confidence = 100

    confidence -= min(
        spread * 0.55,
        30,
    )

    data_quality = clamp(data_completeness)
    confidence -= (100 - data_quality) * 0.35

    if not fundamental_available:
        confidence -= 10

    # Finansal veri eksikliği güveni ayrıca düşürür.
    if not financial_available:

        confidence -= 10


    confidence = clamp(
        confidence
    )

    if confidence >= 75:

        label = "🟢 Yüksek"

    elif confidence >= 55:

        label = "🟡 Orta"

    else:

        label = "🟠 Düşük"

    return (
        round(
            confidence,
            1,
        ),
        label,
    )


# ============================================================
# GEREKÇE MOTORU
# ============================================================

def create_reason(
    symbol,
    scores,
    fundamental,
    financial,
    market,
    quality,
    confirmation,
    decision,
    entry_quality,
    financial_available,
):

    reasons = []

    if scores["short"] >= 70:

        reasons.append(
            "kısa vadeli momentum güçlü"
        )

    elif scores["short"] < 40:

        reasons.append(
            "kısa vadeli teknik görünüm zayıf"
        )

    if scores["mid"] >= 70:

        reasons.append(
            "orta vadeli trend güçlü"
        )

    elif scores["mid"] < 45:

        reasons.append(
            "orta vadeli görünüm zayıf"
        )

    if scores["long"] >= 70:

        reasons.append(
            "uzun vadeli yapı güçlü"
        )

    elif scores["long"] < 45:

        reasons.append(
            "uzun vadeli yapı zayıf"
        )

    if fundamental >= 70:

        reasons.append(
            "temel kalite güçlü"
        )

    elif fundamental < 45:

        reasons.append(
            "temel kalite zayıf"
        )

    if financial_available:

        if financial >= 70:

            reasons.append(
                "mevcut finansal yapı güçlü"
            )

        elif financial < 45:

            reasons.append(
                "mevcut finansal yapı zayıf"
            )

    else:

        reasons.append(
            "Financial Skor için yeterli veri bulunamadı"
        )


    if market >= 65:

        reasons.append(
            "piyasa koşulları destekleyici"
        )

    elif market < 45:

        reasons.append(
            "piyasa koşulları temkinli"
        )

    if entry_quality[
        "overbought"
    ]:

        reasons.append(
            "RSI yüksek"
        )

    if entry_quality[
        "near_resistance"
    ]:

        distance = entry_quality[
            "resistance_distance"
        ]

        if distance is not None:

            reasons.append(
                f"direnç yaklaşık %{distance:.1f} uzakta"
            )

        else:

            reasons.append(
                "direnç bölgesi yaklaşıyor"
            )

    if confirmation[
        "buy_confirmation"
    ]:

        reasons.append(
            f"alım teyidi var "
            f"({confirmation['buy_count']}/6)"
        )

    elif confirmation[
        "sell_confirmation"
    ]:

        reasons.append(
            f"satış teyidi var "
            f"({confirmation['sell_count']}/6)"
        )

    elif confirmation[
        "decline_signal"
    ]:

        reasons.append(
            "düşüş sinyali mevcut"
        )

    else:

        reasons.append(
            "işlem teyidi henüz oluşmadı"
        )

    return (
        f"{symbol}: {decision}. "
        f"Kalite {quality}. "
        +
        "; ".join(
            reasons[:10]
        )
        +
        "."
    )


# ============================================================
# GİRİŞ
# ============================================================

c1, c2 = st.columns(
    [1, 1]
)

with c1:

    symbol_input = st.text_input(
        "Hisse Kodu",
        placeholder="Örn: TUPRS",
    )

with c2:

    vade = st.selectbox(
        "Ana Karar Vadesi",
        [
            "⚡ Kısa Vade — 1 Hafta",
            "📅 Orta Vade — 1–3 Ay",
            "🏦 Uzun Vade — 6 Ay–3 Yıl",
        ],
    )

analiz_et = st.button(
    "🔍 ANALİZ ET",
    type="primary",
    use_container_width=True,
)

if not analiz_et:

    st.info(
        "Bir hisse kodu girip ANALİZ ET'e basın."
    )

    st.stop()

symbol = (
    symbol_input
    .upper()
    .strip()
)

if not symbol:

    st.warning(
        "Lütfen bir hisse kodu giriniz."
    )

    st.stop()


# ============================================================
# VERİLER
# ============================================================

with st.spinner(
    f"{symbol} analiz ediliyor..."
):

    try:

        ticker = yf.Ticker(
            symbol + ".IS"
        )

        veri = ticker.history(
            period="2y"
        )

    except Exception as exc:

        st.error(
            f"Yahoo Finance verisi alınamadı: {exc}"
        )

        st.stop()

if veri is None or veri.empty:

    st.error(
        "Hisse için fiyat verisi bulunamadı."
    )

    st.stop()


# ============================================================
# TEKNİK ANALİZ
# ============================================================

try:

    analysis = get_stock_analysis(
        symbol
    )

except Exception as exc:

    st.error(
        f"Teknik analiz alınamadı: {exc}"
    )

    st.stop()

if not analysis:

    st.error(
        "Teknik analiz sonucu alınamadı."
    )

    st.stop()


# ============================================================
# FUNDAMENTAL
# ============================================================

try:

    fundamental_data = (
        get_fundamental_data(symbol)
        or {}
    )

    fundamental_score = clamp(
        calculate_fundamental_score(
            fundamental_data
        ),
        0,
        100,
    )
    fundamental_available = bool(fundamental_data)

except Exception as exc:

    fundamental_data = {}

    fundamental_score = 50.0
    fundamental_available = False
    fundamental_error = str(exc)


# ============================================================
# FINANCIAL
# ============================================================

# Financial Skor artık doğrudan KAP -> SQLite -> financial_statements
# verisinden hesaplanır. calculate_financial_score(symbol) kullanılmaz;
# böylece modül imzası veya eski Yahoo verisi nedeniyle skorun VERİ YOK
# kalması engellenir.

financial_data = get_financial_health(symbol)

financial_available = bool(
    financial_data.get("available", False)
)

financial_score = (
    clamp(financial_data.get("score"))
    if financial_available
    else 50.0
)

financial_signal = financial_data.get(
    "signal",
    "VERİ YOK",
)

financial_valid_metrics = int(
    financial_data.get("valid_metrics", 0) or 0
)

financial_total_metrics = int(
    financial_data.get("total_metrics", len(FINANCIAL_WEIGHTS))
    or len(FINANCIAL_WEIGHTS)
)

financial_missing = financial_data.get(
    "missing",
    [],
)

financial_message = financial_data.get(
    "message",
    "Financial veri durumu alınamadı.",
)

financial_risk = financial_risk_engine(financial_data)


# ============================================================
# PİYASA
# ============================================================

try:

    market_score, market_reasons = (
        get_market_score()
    )

    market_score = clamp(
        market_score
    )

except Exception:

    market_score = 50.0

    market_reasons = []


# ============================================================
# TEKNİK
# ============================================================

indicator_df = build_indicators(
    veri
)

technical = technical_engine(
    indicator_df
)

technical_score = clamp(
    analysis.get(
        "score",
        50,
    )
)


# ============================================================
# SEKTÖR
# ============================================================

sector_score, sector_name = (
    sector_engine(
        symbol,
        analysis,
    )
)


# ============================================================
# DESTEK / DİRENÇ
# ============================================================

support = safe_float(
    analysis.get(
        "support"
    ),
    0,
)

resistance = safe_float(
    analysis.get(
        "resistance"
    ),
    0,
)


# ============================================================
# GİRİŞ KALİTESİ
# ============================================================

entry_quality = entry_quality_engine(
    technical,
    resistance,
    vade,
)


# ============================================================
# TEYİT
# ============================================================

confirmation = (
    confirmation_engine(
        technical,
        entry_quality,
    )
)


# ============================================================
# VADE SKORLARI
# ============================================================

scores = calculate_horizon_scores(
    technical,
    technical_score,
    fundamental_score,
    financial_score,
    sector_score,
    market_score,
    vade,
    fundamental_available=
        fundamental_available,
    financial_available=
        financial_available,
)


# ============================================================
# VERİ TAMAMLANMA ORANI
# ============================================================

# Financial göstergelerinin doluluk oranı veri kalitesine doğrudan yansıtılır.
price_completeness = min(len(indicator_df) / 200.0, 1.0) * 20.0
fundamental_completeness = 25.0 if fundamental_available else 0.0
financial_completeness = (
    financial_valid_metrics / max(financial_total_metrics, 1) * 40.0
)
market_completeness = 10.0 if market_reasons is not None else 0.0
sector_completeness = 5.0 if sector_name != "Diğer" else 2.0

data_completeness = clamp(
    price_completeness
    + fundamental_completeness
    + financial_completeness
    + market_completeness
    + sector_completeness
)


# ============================================================
# KALİTE
# ============================================================

quality_score, quality_label = (
    quality_engine(
        scores["long"],
        fundamental_score,
        financial_score,
        data_completeness,
    )
)


# ============================================================
# PORTFÖY
# ============================================================

in_portfolio, portfolio_shares, portfolio_weight = (
    get_portfolio_position(
        symbol
    )
)


# ============================================================
# KARAR
# ============================================================

decision, action_reason = (
    decision_engine(
        scores,
        quality_label,
        confirmation,
        in_portfolio,
        entry_quality,
        vade,
        financial_risk,
    )
)
# ============================================================
# OTOMATİK EYLEM KARARI
# ============================================================

automatic_action = automatic_action_engine(
    scores=scores,
    technical=technical,
    confirmation=confirmation,
    entry_quality=entry_quality,
    in_portfolio=in_portfolio,
    resistance=resistance,
    financial_risk=financial_risk,
)

# ============================================================
# GÜVEN
# ============================================================

confidence_score, confidence_label = (
    confidence_engine(
        scores,
        data_completeness,
        fundamental_available=fundamental_available,
        financial_available=financial_available,
    )
)


# ============================================================
# GEREKÇE
# ============================================================

reason = create_reason(
    symbol,
    scores,
    fundamental_score,
    financial_score,
    market_score,
    quality_label,
    confirmation,
    decision,
    entry_quality,
    financial_available,
)


# ============================================================
# TEMEL DEĞERLER
# ============================================================

price = technical[
    "price"
]

daily_change = technical[
    "daily_change"
]

rsi = technical[
    "rsi"
]

mom20 = technical[
    "mom20"
]

mom60 = technical[
    "mom60"
]


# ============================================================
# ANA SONUÇ
# ============================================================

st.divider()

st.subheader(
    f"🎯 {symbol} — {vade}"
)


if in_portfolio:

    st.success(
        f"📦 Portföyde mevcut — "
        f"{portfolio_shares:.0f} lot"
        +
        (
            f" | Ağırlık %{portfolio_weight:.2f}"
            if portfolio_weight
            else ""
        )
    )

else:

    st.info(
        "📭 Bu hisse portföyde görünmüyor."
    )
# ============================================================
# 🎯 OTOMATİK İŞLEM KARARI
# ============================================================

st.divider()

st.subheader("🎯 OTOMATİK İŞLEM KARARI")

action = automatic_action["action"]
short_action = automatic_action["short_action"]
message = automatic_action["message"]

if automatic_action["status"] == "success":
    st.success(
        f"### {action}\n\n"
        f"**{short_action}**\n\n"
        f"{message}"
    )

elif automatic_action["status"] == "danger":
    st.error(
        f"### {action}\n\n"
        f"**{short_action}**\n\n"
        f"{message}"
    )

elif automatic_action["status"] == "warning":
    st.warning(
        f"### {action}\n\n"
        f"**{short_action}**\n\n"
        f"{message}"
    )

elif automatic_action["status"] == "info":
    st.info(
        f"### {action}\n\n"
        f"**{short_action}**\n\n"
        f"{message}"
    )

else:
    st.info(
        f"### {action}\n\n"
        f"**{short_action}**\n\n"
        f"{message}"
    )

# ------------------------------------------------------------
# İşlem tetikleyicisi
# ------------------------------------------------------------

if (
    not in_portfolio
    and
    automatic_action["action"]
    == "🔵 KIRILIM BEKLE"
):

    st.caption(
        f"🎯 **Tetikleyici:** "
        f"{resistance:.2f} TL üzerindeki hacimli "
        f"direnç kırılımı sonrası yeniden ALIM TEYİDİ kontrol edilir."
    )

elif (
    not in_portfolio
    and
    automatic_action["action"]
    == "🟠 GERİ ÇEKİLME BEKLE"
):

    st.caption(
        "🎯 **Tetikleyici:** "
        "RSI'ın soğuması, fiyatın daha uygun bölgeye gelmesi "
        "ve yeniden yukarı dönüş teyidi."
    )

elif (
    not in_portfolio
    and
    automatic_action["action"]
    == "🟢 ŞİMDİ AL"
):

    st.caption(
        "🎯 **Tetikleyici:** "
        "Alım teyidi oluştu. Pozisyon büyüklüğü ve risk yönetimi "
        "ayrıca kontrol edilmelidir."
    )

c1, c2, c3, c4, c5 = st.columns(5)

c1.metric(
    "Genel Skor",
    f"{scores['general']:.1f}/100",
)

c2.metric(
    "Karar",
    decision,
)

c3.metric(
    "Fiyat",
    f"{price:.2f} TL",
    f"{daily_change:+.2f}%",
)

c4.metric(
    "Kalite",
    quality_label,
)

c5.metric(
    "Güven",
    f"{confidence_score:.1f}",
)


st.info(
    f"**Karar gerekçesi:** {reason}"
)


# ============================================================
# GİRİŞ KALİTESİ UYARISI
# ============================================================

if entry_quality[
    "penalty"
] >= 10:

    st.warning(
        f"⚠️ **Giriş Kalitesi Uyarısı:** "
        f"{entry_quality['message']}"
    )

elif entry_quality[
    "penalty"
] > 0:

    st.info(
        f"ℹ️ **Giriş Kalitesi:** "
        f"{entry_quality['message']}"
    )

else:

    st.success(
        f"🟢 **Giriş Kalitesi:** "
        f"{entry_quality['message']}"
    )


# ============================================================
# VADELER
# ============================================================

st.divider()

st.subheader(
    "📅 Vade Bazlı Görünüm"
)

st.caption(
    """
Vade skorları aynı hissenin farklı zaman ufuklarındaki
gücünü gösterir.

Kısa vadede teknik göstergeler,
uzun vadede ise temel ve finansal göstergeler
daha fazla ağırlık taşır.
"""
)

vc1, vc2, vc3 = st.columns(3)

vc1.metric(
    "⚡ Kısa — 1 Hafta",
    f"{scores['short']:.1f}",
)

vc2.metric(
    "📅 Orta — 1–3 Ay",
    f"{scores['mid']:.1f}",
)

vc3.metric(
    "🏦 Uzun — 6 Ay–3 Yıl",
    f"{scores['long']:.1f}",
)


# ============================================================
# TEYİT PANELİ
# ============================================================

st.divider()

st.subheader(
    "🚦 İşlem Teyitleri"
)

st.caption(
    """
Yüksek Genel Skor tek başına AL anlamına gelmez.

Yeni pozisyonlarda ALIM TEYİDİ,
portföydeki hisselerde ise DÜŞÜŞ SİNYALİ
ve SATIŞ TEYİDİ birlikte değerlendirilir.

Ayrıca kısa vadede RSI ve direnç mesafesi
giriş kalitesini etkiler.
"""
)

t1, t2, t3, t4 = st.columns(4)

t1.metric(
    "Alım Teyidi",
    (
        "🟢 VAR"
        if confirmation[
            "buy_confirmation"
        ]
        else
        "🟡 YOK"
    ),
)

t2.metric(
    "Satış Teyidi",
    (
        "🔴 VAR"
        if confirmation[
            "sell_confirmation"
        ]
        else
        "🟢 YOK"
    ),
)

t3.metric(
    "Düşüş Sinyali",
    (
        "🔴 VAR"
        if confirmation[
            "decline_signal"
        ]
        else
        "🟢 YOK"
    ),
)

t4.metric(
    "Alım Teyit Skoru",
    f"{confirmation['buy_count']}/6",
)


if (
    confirmation[
        "buy_confirmation"
    ]
):

    st.success(
        f"🟢 ALIM TEYİDİ VAR — "
        f"{confirmation['buy_count']}/6 "
        f"teknik kontrol olumlu."
    )

elif (
    confirmation[
        "raw_buy_confirmation"
    ]
    and
    confirmation[
        "entry_blocked"
    ]
):

    st.warning(
        f"🟡 TEKNİK ALIM YAPISI VAR "
        f"ancak giriş kalitesi uygun değil — "
        f"{entry_quality['message']}"
    )

elif (
    confirmation[
        "sell_confirmation"
    ]
):

    st.error(
        f"🔴 SATIŞ TEYİDİ VAR — "
        f"{confirmation['sell_count']}/6 "
        f"satış kontrolü oluştu."
    )

elif (
    confirmation[
        "decline_signal"
    ]
):

    st.warning(
        "🔴 DÜŞÜŞ SİNYALİ VAR — "
        "Yeni pozisyon için alım yapılmaz; "
        "mevcut pozisyon satış teyidi açısından izlenir."
    )

else:

    st.info(
        "🟡 Net işlem teyidi oluşmadı. Bekle / izle."
    )


with st.expander(
    "🔬 Teyit kontrollerini göster"
):

    st.markdown(
        "**Alım kontrolleri**"
    )

    for name, status in (
        confirmation[
            "buy_checks"
        ].items()
    ):

        st.write(
            (
                "🟢 "
                if status
                else
                "🔴 "
            )
            + name
        )

    st.markdown(
        "**Satış kontrolleri**"
    )

    for name, status in (
        confirmation[
            "sell_checks"
        ].items()
    ):

        st.write(
            (
                "🔴 "
                if status
                else
                "🟢 "
            )
            + name
        )


# ============================================================
# SKORLAR
# ============================================================

st.divider()

st.subheader(
    "📊 Analiz Katmanları"
)

st.caption(
    """
Bu bölüm hissenin hangi katmanda güçlü veya zayıf olduğunu
gösterir.

Financial Skor şirketin mevcut finansal sağlığını gösterir.
"""
)

c1, c2, c3, c4, c5 = st.columns(5)

c1.metric(
    "Teknik",
    f"{technical_score:.1f}",
)

c2.metric(
    "Fundamental",
    f"{fundamental_score:.1f}",
)

c3.metric(
    "Financial",
    (
        f"{financial_score:.1f}"
        if financial_available
        else
        "VERİ YOK"
    ),
)

c4.metric(
    "Piyasa",
    f"{market_score:.1f}",
)

c5.metric(
    "Kalite",
    f"{quality_score:.1f}",
)

st.caption(
    f"Sektör: **{sector_name}** | "
    f"Sektör Skoru: **{sector_score:.1f}/100**"
)


# ============================================================
# VERİ KALİTESİ
# ============================================================

if not financial_available:

    with st.expander(
        "⚠️ Veri Kalitesi Uyarısı"
    ):

        st.warning(
            f"""
**Financial Skor gerçek skor olarak üretilemedi.**

{financial_message}

Kullanılabilen Financial göstergesi: **{financial_valid_metrics}/{financial_total_metrics}**.

Eksik göstergeler: **{', '.join(financial_missing) if financial_missing else 'Yok'}**

Bu durumda `50` değeri yalnızca hesaplama güvenliği için kullanılan
yedek değerdir; **gerçek Financial Skor olarak kabul edilmez.**
"""
        )

elif financial_valid_metrics < financial_total_metrics:

    with st.expander(
        "ℹ️ Veri Kalitesi Bilgisi"
    ):
        st.info(
            f"Financial Skor üretildi ancak {financial_valid_metrics}/{financial_total_metrics} "
            f"gösterge kullanılabildi. Eksik: "
            f"{', '.join(financial_missing) if financial_missing else '-'}"
        )

if financial_risk.get("flags"):
    risk_text = "; ".join(financial_risk["flags"])
    if financial_risk.get("level") == "high":
        st.error(f"🚨 Finansal risk kapısı: {risk_text}")
    else:
        st.warning(f"⚠️ Finansal izleme notu: {risk_text}")


# ============================================================
# FINANCIAL AÇIKLAMASI
# ============================================================

with st.expander("🏦 Financial Skor nasıl okunur?"):
    st.info(
        """
### 🏦 Financial Skor

Şirketin **mevcut finansal sağlığını** gösterir.

🟢 **70–100:** Güçlü

🟡 **50–69:** Orta

🔴 **0–49:** Zayıf / riskli

Bu skor KAP'tan SQLite `financial_statements` tablosuna aktarılan
finansal verilerden hesaplanır. Eksik göstergeler sahte şekilde
50 kabul edilerek gerçek skor gibi gösterilmez.
"""
    )


# ============================================================
# TEKNİK DETAY
# ============================================================

st.divider()

st.subheader(
    "📈 Teknik Görünüm"
)

tc1, tc2, tc3, tc4, tc5 = st.columns(5)

tc1.metric(
    "RSI",
    f"{rsi:.1f}",
)

tc2.metric(
    "20G Momentum",
    f"{mom20:+.2f}%",
)

tc3.metric(
    "60G Momentum",
    f"{mom60:+.2f}%",
)

tc4.metric(
    "Hacim Oranı",
    f"{technical['volume_ratio']:.2f}x",
)

tc5.metric(
    "MA5",
    f"{technical['ma5']:.2f}",
)


cc1, cc2, cc3, cc4, cc5 = st.columns(5)

cc1.metric(
    "EMA9",
    f"{technical['ema9']:.2f}",
)

cc2.metric(
    "EMA20",
    f"{technical['ema20']:.2f}",
)

cc3.metric(
    "MA50",
    f"{technical['ma50']:.2f}",
)

cc4.metric(
    "MA200",
    f"{technical['ma200']:.2f}",
)

cc5.metric(
    "MACD",
    f"{safe_float(analysis.get('macd')):.2f}",
)


if rsi >= 80:

    st.error(
        "🚨 RSI 80 üzerinde. Kısa vadede aşırı ısınma "
        "nedeniyle yeni girişte çok dikkatli olunmalı."
    )

elif rsi >= 75:

    st.warning(
        "⚠️ RSI 75 üzerinde. Momentum güçlü ancak "
        "kısa vadeli fiyatlama aşırı ısınmış olabilir."
    )

elif rsi >= 45:

    st.success(
        "🟢 RSI normal/pozitif bölgede."
    )

else:

    st.warning(
        "🟠 RSI zayıf bölgede."
    )


if technical["cross_up"]:

    st.success(
        "📈 Fiyat 5 günlük hareketli ortalamayı yukarı kesti."
    )

elif technical["cross_down"]:

    st.warning(
        "📉 Fiyat 5 günlük hareketli ortalamayı aşağı kesti."
    )

elif price > technical["ma5"]:

    st.info(
        "Fiyat MA5 üzerinde; yeni yukarı kesişim oluşmadı."
    )

else:

    st.warning(
        "Fiyat MA5 altında."
    )


# ============================================================
# DESTEK / DİRENÇ
# ============================================================

st.divider()

st.subheader(
    "🎯 Destek / Direnç"
)

st.caption(
    """
Destek ve direnç seviyeleri teknik işlem planında kullanılır.
Tek başına AL veya SAT kararı değildir.

Ancak fiyatın dirence çok yaklaşması kısa vadeli
yeni girişlerde risk/getiri oranını bozabilir.
"""
)

rc1, rc2, rc3, rc4 = st.columns(4)

rc1.metric(
    "Destek",
    f"{support:.2f} TL",
)

rc2.metric(
    "Direnç",
    f"{resistance:.2f} TL",
)

rc3.metric(
    "ATR",
    f"{safe_float(analysis.get('atr')):.2f}",
)

rc4.metric(
    "Volatilite",
    f"{safe_float(analysis.get('volatility')):.2f}",
)


if entry_quality[
    "resistance_distance"
] is not None:

    st.caption(
        f"Fiyatın dirence uzaklığı: "
        f"**%{entry_quality['resistance_distance']:.2f}**"
    )


# ============================================================
# TEMEL ANALİZ
# ============================================================

st.divider()

st.subheader(
    "📊 Temel Analiz"
)

st.caption(
    """
Temel analiz şirketin kârlılık, büyüme ve değerleme tarafını
inceler. Teknik göstergelerden farklı olarak şirketin
işletme performansına odaklanır.
"""
)

fc1, fc2, fc3, fc4, fc5 = st.columns(5)

fc1.metric(
    "F/K",
    str(
        fundamental_data.get(
            "pe_ratio",
            "-",
        )
    ),
)

fc2.metric(
    "PD/DD",
    str(
        fundamental_data.get(
            "pb_ratio",
            "-",
        )
    ),
)

margin = fundamental_data.get(
    "profit_margin"
)

fc3.metric(
    "Kâr Marjı",
    (
        f"%{safe_float(margin) * 100:.1f}"
        if margin is not None
        else "-"
    ),
)

revenue_growth = fundamental_data.get(
    "revenue_growth"
)

fc4.metric(
    "Ciro Büyümesi",
    (
        f"%{safe_float(revenue_growth) * 100:.1f}"
        if revenue_growth is not None
        else "-"
    ),
)

fc5.metric(
    "Temel Skor",
    f"{fundamental_score:.1f}/100",
)

st.write(
    f"**Sektör:** "
    f"{fundamental_data.get('sector', analysis.get('sector', '-'))}"
)


# ============================================================
# FINANCIAL
# ============================================================

st.divider()

st.subheader(
    "🏦 Finansal Değerlendirme"
)

st.caption(
    """
Financial Skor şirketin **mevcut finansal sağlığını** gösterir.
Skor KAP'tan SQLite `financial_statements` tablosuna aktarılan
veriler üzerinden hesaplanır.
"""
)

fc1, fc2 = st.columns(2)

fc1.metric(
    "Financial Skor",
    (
        f"{financial_score:.1f}/100"
        if financial_available
        else
        "VERİ YOK"
    ),
)

fc2.metric(
    "Financial Durum",
    str(
        financial_signal
    ),
)


st.caption(
    f"KAP Financial veri kapsamı: **{financial_valid_metrics}/{financial_total_metrics} gösterge** | "
    f"{financial_message}"
)


if financial_available and financial_data.get("raw"):

    raw = financial_data["raw"]

    with st.expander("🔎 Financial Skor hesaplama detayları"):

        dc1, dc2, dc3, dc4, dc5 = st.columns(5)

        dc1.metric(
            "Cari Oran",
            f"{safe_float(raw.get('current_ratio'), np.nan):.2f}"
            if pd.notna(raw.get("current_ratio")) else "-",
        )

        dc2.metric(
            "Borç/Özkaynak",
            f"{safe_float(raw.get('debt_equity'), np.nan):.2f}x"
            if pd.notna(raw.get("debt_equity")) else "-",
        )

        dc3.metric(
            "Net Kâr Marjı",
            f"%{safe_float(raw.get('net_margin'), np.nan):.2f}"
            if pd.notna(raw.get("net_margin")) else "-",
        )

        dc4.metric(
            "Net Nakit",
            f"{fmt_money(safe_float(raw.get('net_cash'), np.nan) / 1_000_000)} Mlyr TL"
            if pd.notna(raw.get("net_cash")) else "-",
        )

        dc5.metric(
            "Faaliyet Nakit",
            f"{fmt_money(safe_float(raw.get('operating_cash_flow'), np.nan) / 1_000_000)} Mlyr TL"
            if pd.notna(raw.get("operating_cash_flow")) else "-",
        )

        st.write(
            f"**Kullanılan dönem:** {financial_message}"
        )



# ============================================================
# FİYAT GRAFİĞİ
# ============================================================

st.divider()

st.subheader(
    "📈 Fiyat Grafiği"
)

grafik = veri[
    ["Close"]
].copy()

grafik["MA5"] = (
    veri["Close"]
    .rolling(5)
    .mean()
)

grafik["MA20"] = (
    veri["Close"]
    .rolling(20)
    .mean()
)

grafik["MA50"] = (
    veri["Close"]
    .rolling(50)
    .mean()
)

grafik["MA200"] = (
    veri["Close"]
    .rolling(200)
    .mean()
)

grafik.columns = [
    "Fiyat",
    "MA5",
    "MA20",
    "MA50",
    "MA200",
]

st.line_chart(
    grafik,
    use_container_width=True,
)


# ============================================================
# PİYASA
# ============================================================

st.divider()

st.subheader(
    "🌍 Piyasa Değerlendirmesi"
)

st.caption(
    """
Piyasa skoru hissenin kendisinden bağımsız olarak genel
BIST ortamının işlem kararını ne kadar desteklediğini gösterir.
"""
)

st.metric(
    "BIST Piyasa Skoru",
    f"{market_score:.1f}/100",
)

for item in market_reasons or []:

    st.write(
        f"• {item}"
    )


# ============================================================
# SON KARAR
# ============================================================

st.divider()

st.subheader(
    "🧠 SON KARAR"
)


if decision.startswith(
    "🟢"
):

    st.success(
        f"### {decision}\n\n"
        f"{action_reason}"
    )

elif decision.startswith(
    "🔴"
):

    st.error(
        f"### {decision}\n\n"
        f"{action_reason}"
    )

else:

    st.warning(
        f"### {decision}\n\n"
        f"{action_reason}"
    )


st.write(
    f"**Detaylı gerekçe:** {reason}"
)


# ============================================================
# SON OKUMA REHBERİ
# ============================================================

with st.expander(
    "📖 Sonuç ekranı nasıl okunmalı?"
):

    st.markdown(
        """
# Sonuç Okuma Sırası

## 🥇 1. Önce KARAR'a bak

Sistemin bütün katmanları birlikte değerlendirmesi
sonucunda oluşan işlem durumudur.

---

## 🥈 2. Sonra ALIM TEYİDİ'ne bak

Portföyde olmayan bir hisse için:

**Genel Skor yüksek + Alım Teyidi VAR**

önemli bir kombinasyondur.

Ancak kısa vadede bunun yanında:

- RSI
- Direnç mesafesi
- Momentum

da kontrol edilir.

---

## 🥉 3. Giriş kalitesine bak

Örneğin:

**Genel Skor 82**

**Alım Teyidi VAR**

ama:

**RSI 78**

**Dirence uzaklık %1**

ise:

> Hisse güçlüdür ancak fiyatı kovalamak doğru olmayabilir.

Sistem bu durumda doğrudan AL yerine:

> **GÜÇLÜ / GİRİŞİ KOVALAMA**

üretebilir.

---

## 📉 4. Portföydeysen SATIŞ TEYİDİ ve DÜŞÜŞ SİNYALİ'ne bak

### Düşüş Sinyali

> Yapı bozuluyor olabilir.

### Satış Teyidi

> Teknik bozulma işlem çıkışı için daha güçlü seviyeye geldi.

İkisini özellikle birbirinden ayırıyoruz.

---

## 🏦 5. Financial Skor'u oku

Financial Skor şirketin **mevcut finansal sağlığını** gösterir.

- **70–100:** Güçlü
- **50–69:** Orta
- **0–49:** Zayıf / riskli

Financial Skor'u teknik yapı, fundamental kalite, sektör ve piyasa ile birlikte değerlendir.

---

## 📈 6. Kısa / Orta / Uzun vadeyi karşılaştır

Örneğin:

**Kısa 82 / Orta 76 / Uzun 48**

Hisse kısa vadede güçlü olabilir ancak uzun vadeli
şirket yapısı henüz yeterince güçlü değildir.

---

## 🎯 7. Son olarak gerekçeyi oku

Sistem sadece:

> AL

veya

> SAT

dememeli.

Kararın nedenini de açıklamalıdır.

---

# ⚠️ ÖNEMLİ

BIST AI PRO bir **karar destek sistemidir**.

**Alım Teyidi = sınırsız alım**

anlamına gelmez.

**Satış Teyidi = koşulsuz tüm pozisyonu sat**

anlamına da gelmez.

Pozisyon büyüklüğü, portföy ağırlığı,
destek/direnç, risk/getiri ve piyasa koşulları
ayrıca değerlendirilmelidir.
"""
    )
