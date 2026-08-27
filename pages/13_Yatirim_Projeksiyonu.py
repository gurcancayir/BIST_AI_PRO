from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import requests
import streamlit as st
import yfinance as yf


# ============================================================
# BIST AI PRO — YATIRIM PROJEKSIYONU
# Agresif profil | 00:00 sonrası kapanış değerlendirmesi
# Amaç: Ertesi işlem sabahı 09:00–10:00 için karar desteği
# ============================================================

st.set_page_config(
    page_title="BIST AI PRO - Yatırım Projeksiyonu",
    page_icon="🧭",
    layout="wide",
)

TZ = ZoneInfo("Europe/Istanbul")
TEFAS_URL = "https://www.tefas.gov.tr/api/DB/BindHistoryInfo"


@dataclass(frozen=True)
class Asset:
    code: str
    name: str
    group: str
    ticker: str


ASSETS = [
    Asset("BIST", "BIST 100", "Hisse", "XU100.IS"),
    Asset("BTC", "Bitcoin", "Kripto", "BTC-USD"),
    Asset("ETH", "Ethereum", "Kripto", "ETH-USD"),
    Asset("ALTIN", "Altın (Ons)", "Değerli Maden", "GC=F"),
    Asset("GUMUS", "Gümüş (Ons)", "Değerli Maden", "SI=F"),
    Asset("USD", "Dolar/TL", "Döviz", "USDTRY=X"),
    Asset("EUR", "Euro/TL", "Döviz", "EURTRY=X"),
    Asset("GBP", "Sterlin/TL", "Döviz", "GBPTRY=X"),
]

MACRO_TICKERS = {
    "BRENT": "BZ=F",
    "WTI": "CL=F",
    "VIX": "^VIX",
    "DXY": "DX-Y.NYB",
    "US10Y": "^TNX",
}

ACTION_COLORS = {
    "GÜÇLÜ AL": "#00b050",
    "AL": "#34a853",
    "ARTIR": "#45a049",
    "TUT": "#d4a017",
    "BEKLE": "#d4a017",
    "AZALT": "#f57c00",
    "SAT": "#d32f2f",
    "VERİ YOK": "#757575",
}


def _num(value: Any, default: float = np.nan) -> float:
    try:
        result = float(value)
        return result if math.isfinite(result) else default
    except (TypeError, ValueError):
        return default


def _safe_last(series: pd.Series, lag: int = 0) -> float:
    clean = pd.to_numeric(series, errors="coerce").dropna()
    if len(clean) <= lag:
        return np.nan
    return float(clean.iloc[-1 - lag])


@st.cache_data(ttl=1800, show_spinner=False)
def download_prices(tickers: tuple[str, ...]) -> dict[str, pd.DataFrame]:
    """Yahoo Finance üzerinden günlük OHLCV verisini indirir."""
    result: dict[str, pd.DataFrame] = {}
    for ticker in tickers:
        try:
            frame = yf.download(
                ticker,
                period="1y",
                interval="1d",
                auto_adjust=True,
                progress=False,
                threads=False,
                timeout=15,
            )
            if isinstance(frame.columns, pd.MultiIndex):
                frame.columns = frame.columns.get_level_values(0)
            frame = frame.dropna(how="all")
            if not frame.empty and "Close" in frame:
                result[ticker] = frame
        except Exception:
            continue
    return result


def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / period, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / period, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    return (100 - 100 / (1 + rs)).fillna(50)


def max_drawdown(close: pd.Series, window: int = 90) -> float:
    values = close.dropna().tail(window)
    if values.empty:
        return np.nan
    drawdown = values / values.cummax() - 1
    return float(drawdown.min() * 100)


def technical_score(frame: pd.DataFrame) -> dict[str, float]:
    close = pd.to_numeric(frame["Close"], errors="coerce").dropna()
    if len(close) < 55:
        return {}

    last = _safe_last(close)
    sma20 = _safe_last(close.rolling(20).mean())
    sma50 = _safe_last(close.rolling(50).mean())
    sma200 = _safe_last(close.rolling(200, min_periods=120).mean())
    rsi14 = _safe_last(rsi(close))
    ret5 = (last / _safe_last(close, 5) - 1) * 100
    ret20 = (last / _safe_last(close, 20) - 1) * 100
    ret60 = (last / _safe_last(close, 60) - 1) * 100 if len(close) > 60 else np.nan
    vol20 = float(close.pct_change().tail(20).std() * np.sqrt(252) * 100)
    dd90 = max_drawdown(close, 90)

    trend = 0.0
    trend += 35 if last > sma20 else 5
    trend += 35 if sma20 > sma50 else 5
    trend += 20 if (np.isnan(sma200) or sma50 > sma200) else 5
    trend += 10 if last > _safe_last(close, 5) else 0

    momentum = 50.0
    momentum += np.clip(ret5 * 2.0, -15, 15)
    momentum += np.clip(ret20 * 0.8, -20, 20)
    if rsi14 > 78:
        momentum -= 18
    elif rsi14 > 70:
        momentum -= 8
    elif 52 <= rsi14 <= 68:
        momentum += 10
    elif rsi14 < 35:
        momentum -= 12

    risk = 100.0 - np.clip(vol20 * 1.10, 5, 55) - np.clip(abs(min(dd90, 0)) * 1.2, 0, 35)
    score = np.clip(0.48 * trend + 0.34 * momentum + 0.18 * risk, 0, 100)

    return {
        "price": last,
        "score": float(score),
        "trend": float(np.clip(trend, 0, 100)),
        "momentum": float(np.clip(momentum, 0, 100)),
        "risk": float(np.clip(risk, 0, 100)),
        "rsi": rsi14,
        "ret1": (_safe_last(close) / _safe_last(close, 1) - 1) * 100,
        "ret5": ret5,
        "ret20": ret20,
        "ret60": ret60,
        "vol20": vol20,
        "drawdown90": dd90,
        "date": pd.Timestamp(close.index[-1]).date(),
    }


def macro_regime(price_map: dict[str, pd.DataFrame]) -> tuple[float, list[str], pd.DataFrame]:
    rows: list[dict[str, Any]] = []
    comments: list[str] = []
    values: dict[str, dict[str, float]] = {}
    for name, ticker in MACRO_TICKERS.items():
        metric = technical_score(price_map.get(ticker, pd.DataFrame()))
        if metric:
            values[name] = metric
            rows.append({
                "Gösterge": name,
                "Son": metric["price"],
                "1G %": metric["ret1"],
                "20G %": metric["ret20"],
                "RSI": metric["rsi"],
                "Tarih": metric["date"],
            })

    regime = 50.0
    vix = values.get("VIX")
    dxy = values.get("DXY")
    us10y = values.get("US10Y")
    brent = values.get("BRENT")

    if vix:
        if vix["price"] >= 30:
            regime -= 22
            comments.append("VIX 30 üzerinde: riskli varlıklar için güçlü baskı.")
        elif vix["price"] >= 22:
            regime -= 12
            comments.append("VIX yüksek: pozisyon büyüklüğü sınırlanmalı.")
        elif vix["price"] < 17:
            regime += 10
            comments.append("VIX düşük: risk iştahı destekleyici.")
    if dxy:
        regime += -8 if dxy["ret20"] > 2 else (6 if dxy["ret20"] < -2 else 0)
    if us10y:
        regime += -7 if us10y["ret20"] > 5 else (4 if us10y["ret20"] < -5 else 0)
    if brent:
        if brent["ret20"] > 12:
            regime -= 8
            comments.append("Petrolde hızlı yükseliş: Türkiye varlıkları için enflasyon/cari denge riski.")
        elif brent["ret20"] < -10:
            regime += 5
            comments.append("Petrol geriliyor: Türkiye maliyet görünümüne destek.")

    regime = float(np.clip(regime, 0, 100))
    if not comments:
        comments.append("Küresel göstergelerde olağanüstü bir rejim sinyali yok.")
    return regime, comments, pd.DataFrame(rows)


def asset_adjustment(code: str, macro: dict[str, dict[str, float]]) -> tuple[float, str]:
    adj = 0.0
    reasons: list[str] = []
    vix = macro.get("VIX", {})
    dxy = macro.get("DXY", {})
    brent = macro.get("BRENT", {})
    us10y = macro.get("US10Y", {})

    if code in {"BIST", "BTC", "ETH"}:
        if _num(vix.get("price"), 20) >= 25:
            adj -= 10
            reasons.append("yüksek VIX")
        if _num(dxy.get("ret20"), 0) > 2:
            adj -= 5
            reasons.append("güçlü dolar")
    if code == "BIST" and _num(brent.get("ret20"), 0) > 10:
        adj -= 6
        reasons.append("petrol baskısı")
    if code in {"ALTIN", "GUMUS"}:
        if _num(dxy.get("ret20"), 0) < -2:
            adj += 6
            reasons.append("zayıf dolar")
        if _num(us10y.get("ret20"), 0) > 5:
            adj -= 5
            reasons.append("yükselen ABD faizi")
    if code in {"USD", "EUR", "GBP"} and _num(dxy.get("ret20"), 0) > 2:
        adj += 4
        reasons.append("küresel dolar gücü")
    return adj, ", ".join(reasons) if reasons else "teknik görünüm"


def action_from_score(score: float, held: bool, stale: bool) -> str:
    if stale or np.isnan(score):
        return "VERİ YOK"
    if score >= 82:
        return "ARTIR" if held else "GÜÇLÜ AL"
    if score >= 70:
        return "ARTIR" if held else "AL"
    if score >= 55:
        return "TUT" if held else "BEKLE"
    if score >= 42:
        return "AZALT" if held else "BEKLE"
    return "SAT" if held else "BEKLE"


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_tefas_history(days: int = 120, fund_codes: tuple[str, ...] = ()) -> pd.DataFrame:
    """TEFAS geçmişini indirir; portföy fonlarını ayrıca kodla sorgular."""
    end = date.today()
    start = end - timedelta(days=days)
    chunks: list[pd.DataFrame] = []
    cursor = start
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": "https://www.tefas.gov.tr/TarihselVeriler.aspx",
    })
    # Boş kod genel evreni; ayrıca her portföy kodu doğrudan sorgulanır.
    query_codes = ("",) + tuple(sorted({str(code).strip().upper() for code in fund_codes if str(code).strip()}))
    for fund_code in query_codes:
        cursor = start
        while cursor <= end:
            chunk_end = min(cursor + timedelta(days=29), end)
            payload = {
                "fontip": "YAT",
                "bastarih": cursor.strftime("%d.%m.%Y"),
                "bittarih": chunk_end.strftime("%d.%m.%Y"),
                "fonkod": fund_code,
            }
            response = session.post(TEFAS_URL, data=payload, timeout=30)
            response.raise_for_status()
            data = response.json().get("data", [])
            if data:
                chunks.append(pd.DataFrame(data))
            cursor = chunk_end + timedelta(days=1)
    if not chunks:
        return pd.DataFrame()
    frame = pd.concat(chunks, ignore_index=True)
    frame.columns = [str(c).strip().upper() for c in frame.columns]
    return frame.drop_duplicates()


def prepare_tefas(raw: pd.DataFrame) -> pd.DataFrame:
    if raw.empty:
        return pd.DataFrame()
    code_col = next((c for c in ["FONKODU", "FONKOD", "FON_KODU"] if c in raw), None)
    date_col = next((c for c in ["TARIH", "TARİH"] if c in raw), None)
    price_col = next((c for c in ["FIYAT", "FİYAT"] if c in raw), None)
    name_col = next((c for c in ["FONUNVAN", "FONUNVANI", "FONADI"] if c in raw), None)
    if not code_col or not date_col or not price_col:
        return pd.DataFrame()
    out = pd.DataFrame({
        "code": raw[code_col].astype(str).str.strip().str.upper(),
        "date": pd.to_datetime(raw[date_col], errors="coerce", dayfirst=True),
        "price": pd.to_numeric(raw[price_col], errors="coerce"),
        "name": raw[name_col].astype(str).str.strip() if name_col else raw[code_col].astype(str),
    }).dropna(subset=["code", "date", "price"])
    return out.sort_values(["code", "date"]).drop_duplicates(["code", "date"], keep="last")


def score_funds(tefas: pd.DataFrame, held_funds: set[str]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    if tefas.empty:
        return pd.DataFrame()
    for code, group in tefas.groupby("code", sort=False):
        group = group.sort_values("date")
        prices = group.set_index("date")["price"].dropna()
        if len(prices) < 45 or prices.iloc[-1] <= 0:
            continue
        ret5 = (prices.iloc[-1] / prices.iloc[-6] - 1) * 100 if len(prices) >= 6 else np.nan
        ret20 = (prices.iloc[-1] / prices.iloc[-21] - 1) * 100 if len(prices) >= 21 else np.nan
        ret60 = (prices.iloc[-1] / prices.iloc[-61] - 1) * 100 if len(prices) >= 61 else np.nan
        vol = prices.pct_change().tail(40).std() * np.sqrt(252) * 100
        dd = max_drawdown(prices, 60)
        positive_ratio = float((prices.pct_change().tail(20) > 0).mean() * 100)
        score = 50 + np.clip(ret5 * 2, -12, 12) + np.clip(ret20 * 1.1, -18, 22)
        score += np.clip((ret60 if not np.isnan(ret60) else 0) * 0.35, -10, 14)
        score += np.clip((positive_ratio - 50) * 0.25, -8, 8)
        score -= np.clip(vol * 0.25, 0, 12) + np.clip(abs(min(dd, 0)) * 0.4, 0, 12)
        score = float(np.clip(score, 0, 100))
        held = code in held_funds
        rows.append({
            "Fon": code,
            "Fon Adı": str(group["name"].iloc[-1]),
            "Fiyat": prices.iloc[-1],
            "5G %": ret5,
            "20G %": ret20,
            "60G %": ret60,
            "Volatilite %": vol,
            "Düşüş %": dd,
            "Skor": score,
            "Karar": action_from_score(score, held, False),
            "Tarih": prices.index[-1].date(),
            "Portföyde": "Evet" if held else "Hayır",
        })
    return pd.DataFrame(rows)


def fmt_pct(value: Any) -> str:
    value = _num(value)
    return "—" if np.isnan(value) else f"%{value:+.2f}"


def decision_card(row: dict[str, Any]) -> None:
    action = row["Karar"]
    color = ACTION_COLORS.get(action, "#757575")
    st.markdown(
        f"""
        <div style="border-left:6px solid {color};padding:12px 14px;margin:5px 0;
                    border-radius:8px;background:rgba(128,128,128,.08)">
          <div style="font-size:1.05rem;font-weight:700">{row['Kod']} · {row['Varlık']}</div>
          <div style="font-size:1.35rem;font-weight:800;color:{color}">{action}</div>
          <div>Skor: <b>{row['Skor']:.1f}</b> · 1G {fmt_pct(row['1G %'])} · 20G {fmt_pct(row['20G %'])}</div>
          <div style="opacity:.8;margin-top:4px">{row['Açıklama']}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ----------------------------- UI -----------------------------
st.title("🧭 Yatırım Projeksiyonu")
st.caption("Gece kapanışlarını birlikte değerlendirir; ertesi sabah 09:00–10:00 karar penceresi için agresif profil üretir.")

with st.sidebar:
    st.header("Portföy ve ayarlar")
    held_assets = set(st.multiselect(
        "Portföyümde bulunan araçlar",
        options=[a.code for a in ASSETS],
        default=[],
        format_func=lambda x: next(a.name for a in ASSETS if a.code == x),
    ))
    held_fund_text = st.text_area(
        "Portföydeki fon kodları",
        placeholder="IJC, PHE, ...",
        help="Kodları virgül veya boşlukla ayırın. Karar AL yerine ARTIR, zayıfsa AZALT/SAT olabilir.",
    )
    held_funds = {x.strip().upper() for x in held_fund_text.replace(",", " ").split() if x.strip()}
    top_fund_count = st.slider("Gösterilecek en iyi fon", 5, 30, 10)
    include_fx = st.toggle("Döviz kararlarını göster", value=True)
    force_refresh = st.button("🔄 Verileri yenile", use_container_width=True)
    if force_refresh:
        st.cache_data.clear()

all_tickers = tuple([a.ticker for a in ASSETS] + list(MACRO_TICKERS.values()))
with st.spinner("Gece kapanışları ve TEFAS verileri değerlendiriliyor..."):
    prices = download_prices(all_tickers)
    tefas_error = ""
    try:
        tefas = prepare_tefas(fetch_tefas_history(120, tuple(sorted(held_funds))))
    except Exception as exc:
        tefas = pd.DataFrame()
        tefas_error = str(exc)

macro_score, macro_comments, macro_table = macro_regime(prices)
macro_metrics = {
    name: technical_score(prices[ticker])
    for name, ticker in MACRO_TICKERS.items()
    if ticker in prices and technical_score(prices[ticker])
}

now = datetime.now(TZ)
rows: list[dict[str, Any]] = []
for asset in ASSETS:
    if asset.group == "Döviz" and not include_fx:
        continue
    metric = technical_score(prices.get(asset.ticker, pd.DataFrame()))
    if not metric:
        rows.append({"Kod": asset.code, "Varlık": asset.name, "Grup": asset.group,
                     "Skor": np.nan, "Karar": "VERİ YOK", "1G %": np.nan,
                     "5G %": np.nan, "20G %": np.nan, "RSI": np.nan,
                     "Tarih": None, "Açıklama": "Yeterli fiyat geçmişi alınamadı."})
        continue
    adj, macro_reason = asset_adjustment(asset.code, macro_metrics)
    final_score = float(np.clip(metric["score"] + adj, 0, 100))
    age = (now.date() - metric["date"]).days
    allowed_age = 3 if asset.group != "Kripto" else 1
    stale = age > allowed_age
    action = action_from_score(final_score, asset.code in held_assets, stale)
    explanation = (
        f"Trend {metric['trend']:.0f}, momentum {metric['momentum']:.0f}, "
        f"risk kalitesi {metric['risk']:.0f}; makro etki: {macro_reason}."
    )
    if stale:
        explanation = f"Veri {age} günlük; işlem kararı askıya alındı. " + explanation
    rows.append({
        "Kod": asset.code, "Varlık": asset.name, "Grup": asset.group,
        "Fiyat": metric["price"], "Skor": final_score, "Karar": action,
        "1G %": metric["ret1"], "5G %": metric["ret5"], "20G %": metric["ret20"],
        "RSI": metric["rsi"], "Volatilite %": metric["vol20"],
        "Tarih": metric["date"], "Açıklama": explanation,
    })

decision_df = pd.DataFrame(rows).sort_values("Skor", ascending=False, na_position="last")

fresh_dates = [x for x in decision_df.get("Tarih", []) if isinstance(x, date)]
latest_market_date = max(fresh_dates) if fresh_dates else None
freshness_text = latest_market_date.strftime("%d.%m.%Y") if latest_market_date else "Veri yok"

c1, c2, c3, c4 = st.columns(4)
c1.metric("Risk rejimi", f"{macro_score:.0f}/100", "Risk-on" if macro_score >= 58 else "Temkinli")
c2.metric("Piyasa veri tarihi", freshness_text)
c3.metric("Güçlü/Al sinyali", int(decision_df["Karar"].isin(["GÜÇLÜ AL", "AL", "ARTIR"]).sum()))
c4.metric("Profil", "AGRESİF")

if now.time() < time(0, 15):
    st.info("Yeni gün kapanışları henüz tamamlanıyor olabilir. Nihai projeksiyonu 00:15 sonrasında yenileyin.")
if decision_df["Karar"].eq("VERİ YOK").any():
    st.warning("Bazı araçlarda veri eksik/eski. Bu araçlar için sistem işlem kararı üretmedi.")

st.subheader("Sabah karar özeti")
card_columns = st.columns(2)
for index, row in enumerate(decision_df.to_dict("records")):
    with card_columns[index % 2]:
        decision_card(row)

st.subheader("Varlıklar arası karşılaştırma")
display_cols = ["Kod", "Varlık", "Grup", "Fiyat", "Skor", "Karar", "1G %", "5G %", "20G %", "RSI", "Tarih"]
st.dataframe(
    decision_df[display_cols].style.format({
        "Fiyat": "{:,.4f}", "Skor": "{:.1f}", "1G %": "{:+.2f}",
        "5G %": "{:+.2f}", "20G %": "{:+.2f}", "RSI": "{:.1f}",
    }),
    use_container_width=True,
    hide_index=True,
)

st.subheader("TEFAS otomatik fon seçimi")
fund_scores = score_funds(tefas, held_funds)
if fund_scores.empty:
    st.warning("TEFAS verisi alınamadı veya yeterli tarih oluşmadı." + (f" Ayrıntı: {tefas_error}" if tefas_error else ""))
    if held_funds:
        st.error("Değerlendirilemeyen portföy fonları: " + ", ".join(sorted(held_funds)))
else:
    owned = fund_scores[fund_scores["Portföyde"].eq("Evet")].sort_values("Skor", ascending=False)
    candidates = fund_scores[~fund_scores["Portföyde"].eq("Evet")].sort_values("Skor", ascending=False).head(top_fund_count)

    st.markdown("#### 💼 Girdiğim fonların değerlendirmesi")
    scored_held_codes = set(owned["Fon"].astype(str)) if not owned.empty else set()
    missing_held = sorted(held_funds - scored_held_codes)
    if not held_funds:
        st.info("Sol menüdeki ‘Portföydeki fon kodları’ alanına IJC, PHE gibi fon kodlarını yazın.")
    elif owned.empty:
        st.warning("Girdiğiniz fonlar için yeterli TEFAS fiyat geçmişi bulunamadı.")
    else:
        st.dataframe(
            owned.style.format({
                "Fiyat": "{:,.6f}", "5G %": "{:+.2f}", "20G %": "{:+.2f}",
                "60G %": "{:+.2f}", "Volatilite %": "{:.2f}", "Düşüş %": "{:.2f}", "Skor": "{:.1f}",
            }),
            use_container_width=True,
            hide_index=True,
        )
    if missing_held:
        st.error(
            "Değerlendirilemeyen fon kodları: " + ", ".join(missing_held)
            + ". Kod hatalı olabilir, fon TEFAS YAT kategorisinde olmayabilir veya 45 işlem günlük geçmişi bulunmayabilir."
        )

    st.markdown("#### ⭐ TEFAS'tan otomatik seçilen yeni fon adayları")
    st.caption("Portföy fonlarından ayrı olarak, 5/20/60 günlük getiri, pozitif gün oranı, volatilite ve maksimum düşüşle sıralanır.")
    selected = candidates.drop_duplicates("Fon")
    st.dataframe(
        selected.style.format({
            "Fiyat": "{:,.6f}", "5G %": "{:+.2f}", "20G %": "{:+.2f}",
            "60G %": "{:+.2f}", "Volatilite %": "{:.2f}", "Düşüş %": "{:.2f}", "Skor": "{:.1f}",
        }),
        use_container_width=True,
        hide_index=True,
    )

st.subheader("Piyasayı etkileyen göstergeler")
for comment in macro_comments:
    st.write("•", comment)
if not macro_table.empty:
    st.dataframe(
        macro_table.style.format({"Son": "{:,.3f}", "1G %": "{:+.2f}", "20G %": "{:+.2f}", "RSI": "{:.1f}"}),
        use_container_width=True,
        hide_index=True,
    )

with st.expander("Karar verme kriterleri ve puanlama", expanded=True):
    st.markdown(
        """
**Varlık skoru (0–100)**

- Trend `%48`: fiyatın 20 günlük ortalama üzerinde olması, 20 günlük ortalamanın 50 günlüğü aşması ve ana trend.
- Momentum `%34`: 5 ve 20 günlük getiri ile RSI dengesi. RSI 70–78 arası aşırı ısınma, 78 üzeri güçlü kovalama cezası alır.
- Risk kalitesi `%18`: 20 günlük yıllıklandırılmış oynaklık ve son 90 günün maksimum düşüşü.
- Makro düzeltme: VIX, dolar endeksi, ABD 10 yıllık faiz ve Brent petrol; ilgili varlığa göre puanı artırır veya azaltır.

**Agresif profil karar eşikleri**

- `82–100`: Portföyde değilse **GÜÇLÜ AL**, portföydeyse **ARTIR**.
- `70–81.9`: Portföyde değilse **AL**, portföydeyse **ARTIR**.
- `55–69.9`: Portföydeyse **TUT**, değilse **BEKLE**.
- `42–54.9`: Portföydeyse **AZALT**, değilse **BEKLE**.
- `0–41.9`: Portföydeyse **SAT**, değilse **BEKLE**.

**TEFAS fon puanı**

- 5/20/60 günlük getiriyi, son 20 gündeki pozitif gün oranını, volatiliteyi ve maksimum düşüşü birlikte değerlendirir.
- Yeni fon adayları en yüksek skordan seçilir; portföyde yazdığınız fonlar zayıf olsa bile tabloda kalır ve **AZALT/SAT** kararı alabilir.

**Güvenlik kuralları**

- Eski veya yetersiz veri varsa sistem **VERİ YOK** yazar; otomatik olarak AL üretmez.
- Kararlar kapanış verisine dayanır. Sabah açılışında sert fiyat boşluğu oluşursa ilk 15–30 dakika teyit beklenmelidir.
- Aynı yönde çok korelasyonlu varlıkları birlikte artırmak toplam riski büyütür. Tek sinyal için portföyün tamamı kullanılmamalıdır.
        """
    )

st.info(
    "Bu ekran bir karar destek modelidir; kişisel yatırım danışmanlığı değildir. "
    "Gerçek işlemden önce güncel fiyat, makas, vergi/stopaj, fon valörü ve kişisel risk sınırı kontrol edilmelidir."
)
