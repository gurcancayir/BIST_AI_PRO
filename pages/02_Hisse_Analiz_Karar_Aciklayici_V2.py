import sqlite3
import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf

from modules.data.yahoo_data import get_stock_analysis
from modules.data.fundamental import get_fundamental_data, calculate_fundamental_score
from modules.ai.market_ai import get_market_score


st.set_page_config(page_title="Hisse Analizi — Karar Açıklayıcı V3", page_icon="🧭", layout="wide")
st.title("🧭 Hisse Analizi — Karar Açıklayıcı V3")
st.caption("Gerçek fiyat verisi + teknik göstergeler + temel veri + karar tutarlılığı kontrolü")

st.info(
    "Bu ekran gerçek verilerle bağımsız bir analiz ve karar açıklama katmanı üretir. "
    "Ana Hisse Analiz Merkezi'nin karar motorunu değiştirmez; iki ekranın skorları farklıysa "
    "bunu açıkça belirtir. Veriler gecikmeli olabilir."
)


def num(value, default=np.nan):
    try:
        if value is None or pd.isna(value):
            return default
        return float(value)
    except Exception:
        return default


def fmt(value, digits=2):
    value = num(value)
    return "—" if not np.isfinite(value) else f"{value:.{digits}f}"


def rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    loss = -delta.clip(upper=0).ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    out = 100 - (100 / (1 + rs))
    return out.fillna(50)


def calculate_atr(df, period=14):
    high = df["High"]
    low = df["Low"]
    close = df["Close"]
    prev_close = close.shift(1)
    tr = pd.concat([(high - low), (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(axis=1)
    return tr.rolling(period).mean()


@st.cache_data(ttl=900, show_spinner=False)
def load_price_history(ticker, period="5y"):
    return yf.Ticker(ticker).history(period=period, auto_adjust=False)


def safe_float(value, default=np.nan):
    return num(value, default)


def clamp(value, low=0.0, high=100.0):
    try:
        value = float(value)
    except Exception:
        value = 50.0
    return max(low, min(high, value))


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

symbol_input = st.text_input("BIST hisse kodu", value=st.session_state.get("karar_aciklayici_symbol", "TUPRS"), placeholder="Örn. TUPRS").strip().upper()
horizon = st.selectbox("Analiz vadesi", ["Kısa vade — 1 hafta", "Orta vade — 1–3 ay", "Uzun vade — 6 ay–3 yıl"], index=1)
run = st.button("🔍 GERÇEK VERİYLE ANALİZ ET", type="primary", use_container_width=True)

# Streamlit her widget değişiminde scripti yeniden çalıştırır. Analiz çalıştırıldıktan
# sonra seçilen grafik dönemi değişse bile analiz sembolünü session_state'te koru.
if run:
    if not symbol_input or not symbol_input.replace(".", "").isalnum():
        st.error("Geçerli bir hisse kodu girin.")
        st.stop()
    st.session_state["karar_aciklayici_symbol"] = symbol_input

symbol = st.session_state.get("karar_aciklayici_symbol")
if not symbol:
    st.warning("Hisse kodunu girin ve analizi başlatın.")
    st.stop()
with st.spinner(f"{symbol} için fiyat, teknik ve temel veriler inceleniyor..."):
    try:
        prices = load_price_history(f"{symbol}.IS", period="5y")
    except Exception as exc:
        st.error(f"Fiyat verisi alınamadı: {exc}")
        st.stop()

if prices is None or prices.empty or "Close" not in prices:
    st.error(f"{symbol} için Yahoo Finance fiyat verisi bulunamadı. Hisse kodunu veya veri kaynağını kontrol edin.")
    st.stop()

prices = prices.dropna(subset=["Close"]).copy()
close = prices["Close"].astype(float)
latest_price = float(close.iloc[-1])
latest_date = prices.index[-1]
if len(prices) < 30:
    st.warning(f"Yalnızca {len(prices)} fiyat barı var. Uzun vade ve hareketli ortalama yorumlarının güveni düşüktür.")

prices["MA21"] = close.rolling(21).mean()
prices["MA50"] = close.rolling(50).mean()
prices["MA90"] = close.rolling(90).mean()
prices["MA120"] = close.rolling(120).mean()
prices["MA200"] = close.rolling(200).mean()
prices["RSI14"] = rsi(close)
prices["EMA12"] = close.ewm(span=12, adjust=False).mean()
prices["EMA26"] = close.ewm(span=26, adjust=False).mean()
prices["MACD"] = prices["EMA12"] - prices["EMA26"]
prices["MACD_signal"] = prices["MACD"].ewm(span=9, adjust=False).mean()
prices["ATR14"] = calculate_atr(prices)
prices["MOM20"] = close.pct_change(20) * 100
prices["MOM60"] = close.pct_change(60) * 100
if "Volume" in prices:
    prices["VOL20"] = prices["Volume"].rolling(20).mean()
    vol20 = num(prices["VOL20"].iloc[-1])
    volume_ratio = num(prices["Volume"].iloc[-1]) / vol20 if np.isfinite(vol20) and vol20 > 0 else np.nan
else:
    volume_ratio = np.nan

last = prices.iloc[-1]
ma21, ma50, ma200 = num(last["MA21"]), num(last["MA50"]), num(last["MA200"])
rsi_now, macd_now, macd_sig = num(last["RSI14"], 50), num(last["MACD"]), num(last["MACD_signal"])
mom20, mom60, atr = num(last["MOM20"]), num(last["MOM60"]), num(last["ATR14"])
support = num(prices["Low"].tail(20).min())
resistance = num(prices["High"].tail(20).max()) if "High" in prices else num(close.tail(20).max())

try:
    technical_data = get_stock_analysis(symbol) or {}
except Exception as exc:
    technical_data = {}
    st.warning(f"Mevcut teknik analiz modülü cevap vermedi; fiyat göstergeleriyle devam ediliyor. Ayrıntı: {exc}")

try:
    fundamental_data = get_fundamental_data(symbol) or {}
    fundamental_available = bool(fundamental_data)
    fundamental_score = num(calculate_fundamental_score(fundamental_data), np.nan) if fundamental_available else np.nan
except Exception as exc:
    fundamental_data, fundamental_available, fundamental_score = {}, False, np.nan
    st.warning(f"Temel analiz verisi alınamadı: {exc}")

try:
    market_result = get_market_score()
    market_score = num(market_result[0] if isinstance(market_result, (tuple, list)) else market_result)
    market_reasons = market_result[1] if isinstance(market_result, (tuple, list)) and len(market_result) > 1 else []
except Exception:
    market_score, market_reasons = np.nan, []

# Rule-based technical diagnostic score. This is explicitly labelled as this page's diagnostic,
# not as the production engine's General Score.
tech_points = []
tech_points.append(20 if np.isfinite(ma21) and latest_price > ma21 else 0)
tech_points.append(20 if np.isfinite(ma50) and latest_price > ma50 else 0)
tech_points.append(15 if np.isfinite(ma200) and latest_price > ma200 else 0)
tech_points.append(15 if np.isfinite(mom20) and mom20 > 0 else 0)
tech_points.append(10 if np.isfinite(mom60) and mom60 > 0 else 0)
tech_points.append(10 if np.isfinite(macd_now) and np.isfinite(macd_sig) and macd_now > macd_sig else 0)
tech_points.append(10 if np.isfinite(volume_ratio) and volume_ratio >= 1.0 else 0)
technical_score = float(sum(tech_points))

# Finansal puanı aynı uygulamadaki KAP financial_statements tablosundan al.
financial_data = get_financial_health(symbol)
financial_score = num(financial_data.get("score")) if financial_data.get("available") else np.nan
financial_message = financial_data.get("message", "Finansal veri durumu alınamadı.")
financial_metrics_count = int(financial_data.get("valid_metrics", 0) or 0)

# Bu sayfanın tanı puanı: yalnızca mevcut olan puanlar ağırlıklı ortalamaya girer.
parts = [(technical_score, 0.50)]
if np.isfinite(fundamental_score):
    parts.append((max(0, min(100, fundamental_score)), 0.25))
if np.isfinite(financial_score):
    parts.append((max(0, min(100, financial_score)), 0.15))
if np.isfinite(market_score):
    parts.append((max(0, min(100, market_score)), 0.10))
diagnostic_score = sum(v * w for v, w in parts) / sum(w for _, w in parts)
coverage = min(100, round((len(prices) / 200) * 25 + (25 if fundamental_available else 0) + (15 if np.isfinite(market_score) else 0) + (20 if np.isfinite(financial_score) else 0) + 15))

if diagnostic_score > 80:
    diagnostic_decision = "AL ADAYI"
elif diagnostic_score > 75:
    diagnostic_decision = "İZLE / TEYİT"
else:
    diagnostic_decision = "TEYİT"
if coverage < 65 or len(prices) < 50:
    diagnostic_decision = "VERİ YETERSİZ — İZLE"

st.caption(f"Fiyat verisinin son tarihi: **{pd.Timestamp(latest_date).strftime('%d.%m.%Y')}** | Fiyat barı: **{len(prices)}** | Veri kapsamı tahmini: **%{coverage}**")
m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Teknik puan", f"{technical_score:.0f}/100")
m2.metric("Temel puan", f"{fundamental_score:.1f}/100" if np.isfinite(fundamental_score) else "VERİ YOK")
m3.metric("Finansal puan", f"{financial_score:.1f}/100" if np.isfinite(financial_score) else "VERİ YOK")
m4.metric("Piyasa puanı", f"{market_score:.1f}/100" if np.isfinite(market_score) else "VERİ YOK")
m5.metric("Genel tanı puanı", f"{diagnostic_score:.1f}/100")
st.caption(f"Financial Skor ana Hisse Analiz Merkezi ile aynı KAP finansal göstergeleri ve ağırlıklarını kullanır. {financial_message}")
st.write(f"**Son kapanış:** {latest_price:,.2f} TL  |  **Ön değerlendirme:** {diagnostic_decision}")

st.divider()
st.subheader("1. Teknik görünüm")
cols = st.columns(5)
cols[0].metric("RSI(14)", fmt(rsi_now, 1))
cols[1].metric("20 günlük momentum", f"%{fmt(mom20, 1)}")
cols[2].metric("60 günlük momentum", f"%{fmt(mom60, 1)}")
cols[3].metric("Hacim / 20G ort.", f"{fmt(volume_ratio, 2)}x")
cols[4].metric("ATR(14)", fmt(atr))
ma_rows = []
for name, val in [
    ("MA21", num(last["MA21"])),
    ("MA50", num(last["MA50"])),
    ("MA90", num(last["MA90"])),
    ("MA120", num(last["MA120"])),
    ("MA200", num(last["MA200"])),
]:
    ma_rows.append({
        "Gösterge": name,
        "Seviye (TL)": round(val, 2) if np.isfinite(val) else None,
        "Fiyata göre": ("ÜZERİNDE" if latest_price > val else "ALTINDA") if np.isfinite(val) else "Hesaplanamadı"
    })
st.dataframe(pd.DataFrame(ma_rows), use_container_width=True, hide_index=True)
# Dönem seçimi ve 1–5 yıllık performans karşılaştırması
st.subheader("Fiyat grafiği — 1 ile 5 yıl")
period_options = {"1 yıl": 252, "2 yıl": 504, "3 yıl": 756, "4 yıl": 1008, "5 yıl": 1260}
# Form içindeki seçimler kullanıcı "Grafiği uygula" demeden betiği yeniden çalıştırmaz.
with st.form("karar_aciklayici_grafik_donemi_form", clear_on_submit=False):
    st.radio(
        "Grafik dönemi",
        list(period_options.keys()),
        index=0,
        horizontal=True,
        key="karar_aciklayici_grafik_donemi_secimi"
    )
    st.form_submit_button("Grafiği uygula")
period_label = st.session_state.get("karar_aciklayici_grafik_donemi_secimi", "1 yıl")
bars = period_options.get(period_label, 252)
chart_prices = prices.tail(min(bars, len(prices))).copy()
chart_cols = [c for c in ["Close", "MA21", "MA50", "MA90", "MA120", "MA200"] if c in chart_prices.columns]
st.line_chart(chart_prices[chart_cols], use_container_width=True)
if len(chart_prices) < bars:
    st.caption(f"Seçilen {period_label} için tam veri yok; grafik mevcut {len(chart_prices)} seansı gösteriyor.")

# Çeyreklik net kâr grafiği: mevcut KAP finansal tablosunu esnek alan eşlemesiyle okur.
st.subheader("Çeyreklik net kâr — finansal raporlar")
try:
    with sqlite3.connect("borsa.db") as conn:
        table_names = pd.read_sql_query(
            "SELECT name FROM sqlite_master WHERE type='table'", conn
        )["name"].tolist()
        if "financial_statements" in table_names:
            financial_rows = pd.read_sql_query(
                "SELECT * FROM financial_statements WHERE UPPER(symbol)=? ORDER BY period_end",
                conn, params=(symbol.upper(),)
            )
        else:
            financial_rows = pd.DataFrame()
except Exception as exc:
    financial_rows = pd.DataFrame()
    st.warning(f"Finansal raporlar okunamadı: {exc}")

if financial_rows.empty:
    st.warning(
        f"{symbol} için borsa.db içindeki financial_statements tablosunda kayıt bulunamadı. "
        "Uygulamanın kullandığı veritabanı yolunu ve KAP veri güncellemesini kontrol edin."
    )
else:
    date_col = next((x for x in ["period_end", "report_date", "period", "fiscal_date", "date"] if x in financial_rows.columns), None)
    profit_col = next((x for x in [
        "net_profit", "period_profit", "net_income", "net_profit_loss",
        "profit_loss_for_period", "profit_for_period", "net_income_loss",
        "consolidated_net_profit", "profit"
    ] if x in financial_rows.columns), None)
    if date_col is None:
        st.warning("Finansal rapor tablosunda dönem tarihi alanı bulunamadı. Bulunan sütunlar: " + ", ".join(map(str, financial_rows.columns)))
    elif profit_col is None:
        st.warning("Net kâr sütunu bulunamadı. Bulunan sütunlar: " + ", ".join(map(str, financial_rows.columns)))
    else:
        financial_rows[date_col] = pd.to_datetime(financial_rows[date_col], errors="coerce")
        financial_rows[profit_col] = pd.to_numeric(financial_rows[profit_col], errors="coerce")
        financial_rows = financial_rows.dropna(subset=[date_col, profit_col]).sort_values(date_col)
        if "updated_at" in financial_rows.columns:
            financial_rows = financial_rows.sort_values([date_col, "updated_at"])
        financial_rows = financial_rows.drop_duplicates(subset=[date_col], keep="last")
        financial_rows["year"] = financial_rows[date_col].dt.year
        financial_rows["month"] = financial_rows[date_col].dt.month
        financial_rows["quarter"] = ((financial_rows["month"] - 1) // 3) + 1
        if financial_rows.empty:
            st.info("Geçerli tarih ve net kâr verisi bulunamadı.")
        else:
            # Bazı kaynaklar net kârı çeyreklik, bazıları yılbaşından birikimli verir.
            # Çeyreklik fark yalnızca önceki rapor dönemi varsa hesaplanır.
            quarterly_rows = []
            for year, group in financial_rows.groupby("year"):
                group = group.sort_values(date_col)
                previous_cumulative = None
                for _, row in group.iterrows():
                    month = int(row["month"])
                    if month not in (3, 6, 9, 12):
                        continue
                    reported_profit = num(row[profit_col])
                    quarter_profit = np.nan
                    method = "Birikimli rapor"
                    if month == 3:
                        quarter_profit = reported_profit
                        method = "1. çeyrek / 3 aylık rapor"
                    elif previous_cumulative is not None:
                        quarter_profit = reported_profit - previous_cumulative
                        method = "Birikimli kârdan fark"
                    quarterly_rows.append({
                        "Dönem": f"{int(year)} Ç{int(row['quarter'])}",
                        "Dönem sonu": row[date_col].strftime("%d.%m.%Y"),
                        "Çeyreklik net kâr": quarter_profit,
                        "Rapordaki net kâr": reported_profit,
                        "Hesaplama": method,
                        "_sort": row[date_col]
                    })
                    previous_cumulative = reported_profit

            quarterly_df = pd.DataFrame(quarterly_rows)
            if quarterly_df.empty:
                st.info("Finansal raporlarda Mart, Haziran, Eylül veya Aralık dönem sonları bulunamadı.")
            else:
                quarterly_df = quarterly_df.sort_values("_sort").tail(20)
                chart_series = quarterly_df.set_index("Dönem")["Çeyreklik net kâr"].dropna()
                if not chart_series.empty:
                    st.bar_chart(chart_series, use_container_width=True)
                    st.caption("Grafik, raporlar birikimli ise önceki rapordan fark alınarak hesaplanan çeyreklik net kârı gösterir.")
                else:
                    st.warning(
                        "Rapor tarihleri bulundu ancak çeyreklik kâr hesaplamak için önceki dönem karşılaştırması yetersiz. "
                        "Aşağıda raporlanan net kârları ayrıca gösteriyorum; bunlar çeyreklik kâr olarak yorumlanmamalıdır."
                    )
                    fallback = quarterly_df.set_index("Dönem")["Rapordaki net kâr"]
                    st.bar_chart(fallback, use_container_width=True)
                display_df = quarterly_df.drop(columns=["_sort"]).copy()
                for col in ["Çeyreklik net kâr", "Rapordaki net kâr"]:
                    display_df[col] = pd.to_numeric(display_df[col], errors="coerce").round(2)
                st.dataframe(display_df, use_container_width=True, hide_index=True)
                st.caption(
                    "Değerler financial_statements tablosundaki kaynak para birimi/birimindedir. "
                    "Kaynak verinin dönemlik mi birikimli mi olduğu her şirket için ayrıca doğrulanmalıdır; "
                    "bu yüzden raporlanan değer ve hesaplama yöntemi tabloda birlikte gösterilir."
                )

performance_rows = []
for label, count in period_options.items():
    window = prices.tail(min(count, len(prices)))
    start_price = num(window["Close"].iloc[0]) if not window.empty else np.nan
    end_price = num(window["Close"].iloc[-1]) if not window.empty else np.nan
    change_pct = (end_price / start_price - 1) * 100 if np.isfinite(start_price) and start_price > 0 and np.isfinite(end_price) else np.nan
    performance_rows.append({
        "Dönem": label,
        "Başlangıç fiyatı (TL)": round(start_price, 2) if np.isfinite(start_price) else None,
        "Son fiyat (TL)": round(end_price, 2) if np.isfinite(end_price) else None,
        "Fiyat değişimi (%)": round(change_pct, 2) if np.isfinite(change_pct) else None,
        "Veri": f"{len(window)} seans" if len(window) < count else "Tam dönem"
    })
st.markdown("#### 1–5 yıllık fiyat getirisi")
st.dataframe(pd.DataFrame(performance_rows), use_container_width=True, hide_index=True)
st.caption("Getiri, seçilen dönem içindeki ilk ve son kapanış fiyatlarından hesaplanır; temettüler ve sermaye artırımları dahil toplam getiri değildir.")

# Her takvim yılı için fiyat değişimi yüzdesi
st.markdown("#### Yıllık artış / azalış (%)")
annual = prices[["Close"]].dropna().copy()
annual.index = pd.to_datetime(annual.index)
annual = annual.sort_index()
annual["Yıl"] = annual.index.year
year_end = annual.groupby("Yıl")["Close"].agg(["first", "last"])
annual_rows = []
for year, row in year_end.iterrows():
    prev = annual.loc[annual["Yıl"] == year - 1, "Close"]
    if len(prev) and np.isfinite(row["last"]) and np.isfinite(prev.iloc[-1]) and prev.iloc[-1] > 0:
        pct = (row["last"] / prev.iloc[-1] - 1) * 100
        basis = "Önceki yıl sonu kapanışına göre"
    else:
        pct = (row["last"] / row["first"] - 1) * 100 if row["first"] > 0 else np.nan
        basis = "İlk mevcut kapanıştan yıl sonuna (kısmi yıl)"
    annual_rows.append({
        "Yıl": int(year),
        "Yıllık fiyat değişimi (%)": round(float(pct), 2) if np.isfinite(pct) else None,
        "Hesaplama": basis
    })
annual_df = pd.DataFrame(annual_rows)
if not annual_df.empty:
    st.bar_chart(annual_df.set_index("Yıl")[["Yıllık fiyat değişimi (%)"]], use_container_width=True)
    st.dataframe(annual_df, use_container_width=True, hide_index=True)
st.caption("Bu oran fiyat değişimidir; temettüler ve sermaye artırımları dahil toplam getiri değildir.")

technical_notes = []
if np.isfinite(ma21):
    technical_notes.append("Fiyat MA21 üzerinde" if latest_price > ma21 else "Fiyat MA21 altında")
if np.isfinite(ma50):
    technical_notes.append("Fiyat MA50 üzerinde" if latest_price > ma50 else "Fiyat MA50 altında")
if np.isfinite(ma200):
    technical_notes.append("Fiyat MA200 üzerinde" if latest_price > ma200 else "Fiyat MA200 altında")
if rsi_now >= 75:
    technical_notes.append("RSI yüksek; kısa vadede aşırı ısınma riski")
elif rsi_now <= 30:
    technical_notes.append("RSI düşük; zayıflık veya tepki ihtimali, tek başına alım sinyali değil")
elif rsi_now >= 50:
    technical_notes.append("RSI momentum tarafı pozitif")
else:
    technical_notes.append("RSI momentum tarafı zayıf")
if np.isfinite(macd_now) and np.isfinite(macd_sig):
    technical_notes.append("MACD sinyal çizgisinin üzerinde" if macd_now > macd_sig else "MACD sinyal çizgisinin altında")
for note in technical_notes:
    st.write(f"- {note}")

st.divider()
st.subheader("2. Destek, direnç ve örnek risk planı")
distance_res = ((resistance / latest_price) - 1) * 100 if latest_price > 0 and np.isfinite(resistance) else np.nan
st.write(f"- Yakın dönem destek tahmini (20 seans dip bölgesi): **{fmt(support)} TL**")
st.write(f"- Yakın dönem direnç tahmini (20 seans tepe bölgesi): **{fmt(resistance)} TL**")
st.write(f"- Dirence kalan mesafe: **%{fmt(distance_res, 2)}**" if np.isfinite(distance_res) else "- Direnç mesafesi hesaplanamadı.")
if np.isfinite(atr) and atr > 0:
    stop = max(0, latest_price - 1.5 * atr)
    risk = latest_price - stop
    target1 = latest_price + risk * 1.5
    target2 = latest_price + risk * 2.5
    plan = pd.DataFrame([
        {"Seviye": "Örnek referans fiyatı", "Fiyat (TL)": round(latest_price, 2)},
        {"Seviye": "Örnek stop (1.5 ATR)", "Fiyat (TL)": round(stop, 2)},
        {"Seviye": "Hedef 1 (1.5R)", "Fiyat (TL)": round(target1, 2)},
        {"Seviye": "Hedef 2 (2.5R)", "Fiyat (TL)": round(target2, 2)},
    ])
    st.dataframe(plan, use_container_width=True, hide_index=True)
    st.caption("Bu seviyeler mekanik örneklerdir; destek/direnç, işlem maliyeti ve portföy riskiyle doğrulanmadan emir seviyesi sayılmaz.")
else:
    st.warning("ATR verisi oluşmadığı için örnek stop/hedef hesaplanamadı.")

st.divider()
st.subheader("3. Temel ve piyasa katmanı")
f1, f2, f3, f4 = st.columns(4)
f1.metric("Temel analiz", f"{fundamental_score:.1f}/100" if np.isfinite(fundamental_score) else "VERİ YOK")
f2.metric("Finansal analiz", f"{financial_score:.1f}/100" if np.isfinite(financial_score) else "VERİ YOK")
f3.metric("Piyasa skoru", f"{market_score:.1f}/100" if np.isfinite(market_score) else "VERİ YOK")
f4.metric("Veri kapsamı", f"%{coverage}")
st.caption(financial_message)
if fundamental_data:
    display_fields = {
        "F/K": ["pe_ratio", "trailing_pe"],
        "PD/DD": ["pb_ratio", "price_to_book"],
        "Kâr marjı": ["profit_margin"],
        "Ciro büyümesi": ["revenue_growth"],
        "Sektör": ["sector"],
    }
    rows = []
    for label, keys in display_fields.items():
        val = next((fundamental_data[k] for k in keys if k in fundamental_data and fundamental_data[k] is not None), None)
        rows.append({"Gösterge": label, "Değer": str(val) if val is not None else "Veri yok"})
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
if market_reasons:
    for reason in market_reasons:
        st.write(f"- {reason}")

st.divider()
st.subheader("4. Karar tutarlılığı ve açıklama")
st.markdown(
    f"**Bu sayfanın bağımsız ön değerlendirmesi: {diagnostic_decision}.** "
    f"Tanı puanı {diagnostic_score:.1f}/100; teknik puan {technical_score:.0f}/100."
)
if np.isfinite(fundamental_score) and fundamental_score < 40:
    st.warning("Temel analiz puanı zayıf. Teknik görünüm olumlu olsa bile şirket kalitesi ayrıca incelenmeli.")
if np.isfinite(market_score) and market_score < 40:
    st.warning("Piyasa skoru zayıf. Genel piyasa koşulları yeni giriş riskini artırabilir.")
if rsi_now >= 75:
    st.warning("Momentum güçlü olsa da RSI yüksek; fiyatı kovalamak yerine geri çekilme/teyit beklemek değerlendirilebilir.")
if np.isfinite(distance_res) and distance_res <= 2:
    st.warning("Fiyat yakın dönem direncine %2 veya daha yakın. Olası getiri alanı sınırlı olabilir.")
if latest_price < ma21 if np.isfinite(ma21) else False:
    st.warning("Fiyat MA21 altında. Kısa vadeli trend teyidi zayıf.")
if not fundamental_available:
    st.warning("Temel veri bulunamadı; bu analizde şirket kalitesi katmanı eksik.")
if coverage < 70:
    st.warning("Veri kapsamı sınırlı. Bu sayfanın puanını tek başına işlem kararı için kullanmayın.")

st.markdown("### Kararların neden farklı görünebileceği")
st.write(
    "Ana Hisse Analiz Merkezi; kendi teknik, temel, finansal, sektör, piyasa, kalite ve teyit "
    "fonksiyonlarını kullanır. Bu yardımcı sayfa ise erişilebilir güncel fiyat göstergelerinden "
    "bağımsız bir tanı puanı hesaplar. Bu yüzden puanlar birebir aynı olmak zorunda değildir. "
    "Ana karar eşiği ve ana motor bu sayfa tarafından değiştirilmez."
)
st.caption("Karar destek aracıdır; yatırım tavsiyesi veya kesin getiri garantisi değildir. Yahoo Finance verisi ve temel veri kaynağının güncelliği değişebilir.")
