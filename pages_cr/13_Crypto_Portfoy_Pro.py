# ============================================================
# CRYPTO AI PRO
# 13_Crypto_Portfoy_Pro.py
#
# PROFESYONEL KRİPTO PORTFÖY YÖNETİM MERKEZİ
# ============================================================

from __future__ import annotations

import importlib
import json
import os
from datetime import datetime
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd
import streamlit as st

import crypto_engine


# ============================================================
# SAYFA
# ============================================================

st.set_page_config(
    page_title="Crypto AI PRO - Portföy PRO",
    page_icon="💼",
    layout="wide",
)

try:
    crypto_engine = importlib.reload(crypto_engine)
except Exception:
    pass


# ============================================================
# AYARLAR
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

PORTFOLIO_FILE = os.path.join(
    BASE_DIR,
    "crypto_portfolio.json",
)

REALIZED_FILE = os.path.join(
    BASE_DIR,
    "crypto_portfolio_realized.json",
)

CACHE_TTL = 60


# ============================================================
# YARDIMCILAR
# ============================================================

def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default

        result = float(value)

        if not np.isfinite(result):
            return default

        return result

    except Exception:
        return default


def clamp(value: Any, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, safe_float(value)))


def fmt_price(value: Any) -> str:
    value = safe_float(value)

    if value >= 1000:
        return f"{value:,.2f}"
    if value >= 100:
        return f"{value:,.3f}"
    if value >= 1:
        return f"{value:,.4f}"
    if value >= 0.01:
        return f"{value:.5f}"
    if value >= 0.0001:
        return f"{value:.8f}"

    return f"{value:.10f}"


def fmt_money(value: Any) -> str:
    value = safe_float(value)
    sign = "-" if value < 0 else ""
    value = abs(value)

    if value >= 1_000_000_000:
        return f"{sign}₺{value / 1_000_000_000:.2f} Mr"
    if value >= 1_000_000:
        return f"{sign}₺{value / 1_000_000:.2f} Mn"
    if value >= 1_000:
        return f"{sign}₺{value / 1_000:.1f} Bin"

    return f"{sign}₺{value:,.0f}"


def normalize_symbol(value: Any) -> str:
    return (
        str(value or "")
        .upper()
        .strip()
        .replace("/", "")
        .replace("_", "")
        .replace("-", "")
    )


def first_existing(
    df: pd.DataFrame,
    names: List[str],
    default: Any = np.nan,
) -> pd.Series:
    for name in names:
        if name in df.columns:
            return df[name]

    return pd.Series(
        [default] * len(df),
        index=df.index,
    )


# ============================================================
# JSON
# ============================================================

def load_json(path: str) -> List[Dict[str, Any]]:
    if not os.path.exists(path):
        return []

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return data if isinstance(data, list) else []

    except Exception:
        return []


def save_json(path: str, rows: List[Dict[str, Any]]) -> bool:
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(
                rows,
                f,
                ensure_ascii=False,
                indent=2,
            )

        return True

    except Exception as exc:
        st.error(f"Kayıt hatası: {exc}")
        return False


def load_portfolio() -> List[Dict[str, Any]]:
    cleaned = []

    for item in load_json(PORTFOLIO_FILE):
        if not isinstance(item, dict):
            continue

        coin = str(item.get("coin", "")).upper().strip()
        qty = safe_float(item.get("quantity", 0))
        cost = safe_float(item.get("cost", 0))

        if coin and qty > 0 and cost > 0:
            cleaned.append(
                {
                    "coin": coin,
                    "quantity": qty,
                    "cost": cost,
                    "updated_at": item.get("updated_at", ""),
                }
            )

    return cleaned


# ============================================================
# PİYASA
# ============================================================

@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def load_market() -> Tuple[pd.DataFrame, str]:
    try:
        raw = crypto_engine.get_all_try_universe()

    except Exception as exc:
        return pd.DataFrame(), str(exc)

    if raw is None:
        return pd.DataFrame(), "Engine veri döndürmedi."

    if isinstance(raw, pd.DataFrame):
        df = raw.copy()

    elif isinstance(raw, list):
        if not raw:
            return pd.DataFrame(), "Piyasa evreni boş."

        df = (
            pd.DataFrame(raw)
            if isinstance(raw[0], dict)
            else pd.DataFrame({"symbol": raw})
        )

    else:
        return pd.DataFrame(), f"Beklenmeyen veri tipi: {type(raw).__name__}"

    if df.empty:
        return pd.DataFrame(), "Piyasa verisi boş."

    out = pd.DataFrame(index=df.index)

    out["symbol"] = (
        first_existing(
            df,
            ["symbol", "pair", "code", "name"],
            "",
        )
        .astype(str)
        .map(normalize_symbol)
    )

    out["base_asset"] = (
        first_existing(
            df,
            ["base_asset", "coin", "base", "asset"],
            "",
        )
        .astype(str)
        .str.upper()
        .str.strip()
    )

    missing = out["base_asset"].isin(["", "NAN", "NONE"])

    out.loc[missing, "base_asset"] = (
        out.loc[missing, "symbol"]
        .str.replace("TRY", "", regex=False)
        .str.replace("USDT", "", regex=False)
    )

    out["price_try"] = pd.to_numeric(
        first_existing(
            df,
            ["price_try", "price", "last_price", "lastPrice", "close"],
            0,
        ),
        errors="coerce",
    ).fillna(0)

    out["change_24h"] = pd.to_numeric(
        first_existing(
            df,
            ["change_24h", "change", "priceChangePercent"],
            0,
        ),
        errors="coerce",
    ).fillna(0)

    out["volume_try"] = pd.to_numeric(
        first_existing(
            df,
            ["volume_try", "volume", "quoteVolume", "quote_volume"],
            0,
        ),
        errors="coerce",
    ).fillna(0)

    out["source"] = (
        first_existing(df, ["source"], "")
        .astype(str)
        .str.upper()
        .str.strip()
    )

    out["analysis_symbol"] = (
        first_existing(df, ["analysis_symbol"], "")
        .astype(str)
        .map(normalize_symbol)
    )

    miss_analysis = out["analysis_symbol"].isin(["", "NAN", "NONE"])
    out.loc[miss_analysis, "analysis_symbol"] = out.loc[miss_analysis, "symbol"]

    out = (
        out[
            ~out["base_asset"].isin(["", "NAN", "NONE"])
        ]
        .drop_duplicates(
            subset=["base_asset"],
            keep="first",
        )
        .reset_index(drop=True)
    )

    return out, ""


# ============================================================
# TEKNİK ANALİZ
# ============================================================

@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def analyze_coin_cached(
    coin: str,
    symbol: str,
) -> Dict[str, Any]:
    market_df, _ = load_market()

    try:
        result = crypto_engine.analyze_coin(
            symbol,
            market_data=market_df,
        )

        if isinstance(result, dict):
            return result

    except Exception:
        pass

    return {
        "symbol": coin,
        "price": 0.0,
        "change_24h": 0.0,
        "volume_try": 0.0,
        "momentum": 0.0,
        "ema9": 0.0,
        "ema20": 0.0,
        "ema50": 0.0,
        "rsi": 50.0,
        "vwap": 0.0,
        "volume_ratio": 1.0,
        "support": 0.0,
        "resistance": 0.0,
        "rr": 0.0,
        "trend_score": 50.0,
        "trade_score": 50.0,
        "decision": "⚪ VERİ YETERSİZ",
    }


def liquidity_score(volume: Any) -> float:
    volume = safe_float(volume)

    if volume >= 2_000_000_000:
        return 100
    if volume >= 1_000_000_000:
        return 95
    if volume >= 500_000_000:
        return 90
    if volume >= 250_000_000:
        return 84
    if volume >= 100_000_000:
        return 76
    if volume >= 50_000_000:
        return 68
    if volume >= 20_000_000:
        return 58
    if volume >= 5_000_000:
        return 45

    return 30


def momentum_score(change: Any) -> float:
    change = safe_float(change)

    if change >= 15:
        return 90
    if change >= 10:
        return 86
    if change >= 6:
        return 80
    if change >= 3:
        return 74
    if change >= 0:
        return 64
    if change >= -3:
        return 54
    if change >= -7:
        return 42
    if change >= -12:
        return 28

    return 15


def rsi_score(rsi: Any) -> float:
    rsi = safe_float(rsi, 50)

    if 50 <= rsi <= 65:
        return 95
    if 45 <= rsi < 50:
        return 78
    if 65 < rsi <= 70:
        return 78
    if 40 <= rsi < 45:
        return 60
    if 70 < rsi <= 75:
        return 55

    return 35


def volume_score(ratio: Any) -> float:
    ratio = safe_float(ratio, 1)

    if ratio >= 2:
        return 100
    if ratio >= 1.5:
        return 90
    if ratio >= 1.2:
        return 78
    if ratio >= 1:
        return 65
    if ratio >= 0.75:
        return 52

    return 35


def vwap_score(price: Any, vwap: Any) -> float:
    price = safe_float(price)
    vwap = safe_float(vwap)

    if price <= 0 or vwap <= 0:
        return 50

    ratio = price / vwap

    if 1.00 <= ratio <= 1.03:
        return 92
    if 0.985 <= ratio < 1.00:
        return 72
    if 1.03 < ratio <= 1.06:
        return 68
    if ratio > 1.06:
        return 45

    return 38


def chase_score(
    change: float,
    rsi: float,
    price: float,
    ema20: float,
    vwap: float,
) -> float:
    score = 0.0

    if change >= 7:
        score += 18
    if change >= 12:
        score += 20
    if change >= 18:
        score += 22
    if rsi >= 72:
        score += 15
    if rsi >= 78:
        score += 10

    if price > 0 and ema20 > 0 and price > ema20 * 1.06:
        score += 10

    if price > 0 and vwap > 0 and price > vwap * 1.05:
        score += 10

    return clamp(score)


def risk_score(
    weight: float,
    pnl_pct: float,
    trend: float,
    liquidity: float,
    chase: float,
) -> float:
    risk = 0.0

    if weight >= 45:
        risk += 38
    elif weight >= 35:
        risk += 30
    elif weight >= 25:
        risk += 22
    elif weight >= 18:
        risk += 14

    if pnl_pct <= -30:
        risk += 30
    elif pnl_pct <= -20:
        risk += 25
    elif pnl_pct <= -12:
        risk += 18
    elif pnl_pct <= -7:
        risk += 10

    if trend < 30:
        risk += 22
    elif trend < 45:
        risk += 14
    elif trend < 55:
        risk += 7

    if liquidity < 40:
        risk += 15
    elif liquidity < 55:
        risk += 8

    risk += chase * 0.10

    return clamp(risk)


def hold_decision(
    score: float,
    risk: float,
    trend: float,
) -> str:
    if risk >= 82 or (score < 35 and trend < 35):
        return "🔴 SAT"

    if risk >= 68 or (score < 48 and trend < 45):
        return "🟠 AZALT"

    if score >= 82 and risk < 45 and trend >= 65:
        return "🟢 GÜÇLÜ TUT"

    if score >= 70 and risk < 60 and trend >= 55:
        return "🟢 TUT"

    if score >= 55:
        return "🟡 TUT / TEYİT"

    return "⚪ BEKLE"


def add_decision(
    trade: float,
    trend: float,
    rr: float,
    chase: float,
    liquidity: float,
    rsi: float,
) -> str:
    if liquidity < 45:
        return "🔴 YENİ ALIM YOK / LİKİDİTE"

    if chase >= 75:
        return "🔴 YENİ ALIM YOK / KOVALAMA"

    if trade >= 80 and trend >= 70 and rr >= 1.5 and 48 <= rsi <= 70:
        return "🟢 EKLE"

    if trade >= 65 and trend >= 58 and rr >= 1.2 and chase < 65:
        return "🟢 GERİ ÇEKİLMEDE EKLE"

    if trend >= 55 and trade >= 55:
        return "🟡 TEYİT BEKLE"

    return "⚪ EKLEME YOK"


def final_decision(
    hold: str,
    add: str,
) -> str:
    if hold == "🔴 SAT":
        return "🔴 SAT"

    if hold == "🟠 AZALT":
        return "🟠 AZALT"

    if "KOVALAMA" in add:
        return "🟡 TUT / YENİ ALIM YOK"

    if hold == "🟢 GÜÇLÜ TUT" and add == "🟢 EKLE":
        return "🟢 TUT / EKLE"

    if (
        hold in ["🟢 GÜÇLÜ TUT", "🟢 TUT", "🟡 TUT / TEYİT"]
        and add == "🟢 GERİ ÇEKİLMEDE EKLE"
    ):
        return "🟢 TUT / GERİ ÇEKİLMEDE EKLE"

    if hold in ["🟢 GÜÇLÜ TUT", "🟢 TUT"]:
        return "🟢 TUT"

    return hold


# ============================================================
# UI BAŞLIK
# ============================================================

st.title("💼 Crypto AI PRO — Profesyonel Portföy Merkezi")

st.caption(
    "Pozisyon ekle/azalt • ağırlıklı maliyet • gerçekleşen K/Z • "
    "canlı değer • teknik güç • risk • TUT/EKLE/AZALT/SAT"
)


# ============================================================
# VERİ
# ============================================================

df_market, market_error = load_market()

if df_market.empty:
    st.error("❌ Kripto piyasa verisi alınamadı.")

    if market_error:
        st.caption(market_error)

    st.stop()

portfolio_rows = load_portfolio()
realized_rows = load_json(REALIZED_FILE)

st.success(
    f"🟢 Piyasa hazır — {len(df_market)} coin | "
    f"{datetime.now().strftime('%d.%m.%Y %H:%M:%S')}"
)


# ============================================================
# POZİSYON YÖNETİMİ
# ============================================================

st.divider()
st.subheader("🛠️ Pozisyon Yönetim Merkezi")

tab_add, tab_reduce, tab_delete, tab_hist = st.tabs(
    [
        "➕ Ekle / Artır",
        "➖ Azalt / Sat",
        "🗑️ Sil",
        "📜 Gerçekleşen K/Z",
    ]
)


with tab_add:
    coins = sorted(
        df_market["base_asset"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    add_coin = st.selectbox(
        "Coin",
        coins,
        key="cpp_add_coin",
    )

    price_match = df_market[
        df_market["base_asset"] == add_coin
    ]

    current_price = (
        safe_float(
            price_match.iloc[0]["price_try"]
        )
        if not price_match.empty
        else 0.0
    )

    existing = next(
        (
            x
            for x in portfolio_rows
            if x["coin"] == add_coin
        ),
        None,
    )

    if existing:
        st.info(
            f"Mevcut: {existing['quantity']:,.8f} {add_coin} | "
            f"Ort. maliyet ₺{fmt_price(existing['cost'])}"
        )

    a1, a2, a3 = st.columns(3)

    with a1:
        add_qty = st.number_input(
            "Alınacak Adet",
            min_value=0.0,
            value=0.0,
            step=0.00000001,
            format="%.8f",
            key="cpp_add_qty",
        )

    with a2:
        st.metric(
            "Güncel Fiyat",
            f"₺{fmt_price(current_price)}",
        )

    with a3:
        add_cost = st.number_input(
            "Alış Maliyeti ₺",
            min_value=0.0,
            value=float(current_price),
            step=0.00000001,
            format="%.8f",
            key="cpp_add_cost",
        )

    if add_qty > 0 and add_cost > 0:
        st.info(
            f"İşlem tutarı: **{fmt_money(add_qty * add_cost)}**"
        )

    if st.button(
        "💾 POZİSYONU KAYDET",
        type="primary",
        use_container_width=True,
        key="cpp_save_add",
    ):
        if add_qty <= 0 or add_cost <= 0:
            st.warning("Adet ve maliyet 0'dan büyük olmalı.")

        else:
            now = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
            found = False

            for item in portfolio_rows:
                if item["coin"] == add_coin:
                    old_qty = safe_float(item["quantity"])
                    old_cost = safe_float(item["cost"])

                    total_qty = old_qty + add_qty

                    weighted_cost = (
                        old_qty * old_cost
                        + add_qty * add_cost
                    ) / total_qty

                    item["quantity"] = total_qty
                    item["cost"] = weighted_cost
                    item["updated_at"] = now

                    found = True
                    break

            if not found:
                portfolio_rows.append(
                    {
                        "coin": add_coin,
                        "quantity": add_qty,
                        "cost": add_cost,
                        "updated_at": now,
                    }
                )

            if save_json(PORTFOLIO_FILE, portfolio_rows):
                st.success(f"✅ {add_coin} kaydedildi.")
                st.rerun()


with tab_reduce:
    if not portfolio_rows:
        st.info("Portföy boş.")

    else:
        reduce_coin = st.selectbox(
            "Coin",
            [x["coin"] for x in portfolio_rows],
            key="cpp_reduce_coin",
        )

        item = next(
            x
            for x in portfolio_rows
            if x["coin"] == reduce_coin
        )

        qty_now = safe_float(item["quantity"])
        cost_now = safe_float(item["cost"])

        market_match = df_market[
            df_market["base_asset"] == reduce_coin
        ]

        price_now = (
            safe_float(
                market_match.iloc[0]["price_try"]
            )
            if not market_match.empty
            else 0.0
        )

        r1, r2, r3 = st.columns(3)

        r1.metric("Mevcut Adet", f"{qty_now:,.8f}")
        r2.metric("Ort. Maliyet", f"₺{fmt_price(cost_now)}")
        r3.metric("Güncel Fiyat", f"₺{fmt_price(price_now)}")

        reduce_qty = st.number_input(
            "Satılacak Adet",
            min_value=0.0,
            max_value=float(qty_now),
            value=0.0,
            step=0.00000001,
            format="%.8f",
            key="cpp_reduce_qty",
        )

        sale_price = st.number_input(
            "Satış Fiyatı ₺",
            min_value=0.0,
            value=float(price_now),
            step=0.00000001,
            format="%.8f",
            key="cpp_sale_price",
        )

        if reduce_qty > 0 and sale_price > 0:
            realized = reduce_qty * (sale_price - cost_now)

            realized_pct = (
                (sale_price - cost_now) / cost_now * 100
                if cost_now > 0
                else 0
            )

            st.info(
                f"Gerçekleşecek K/Z: "
                f"**{fmt_money(realized)} ({realized_pct:+.2f}%)**"
            )

        if st.button(
            "➖ SATIŞI / AZALTMAYI KAYDET",
            type="primary",
            use_container_width=True,
            key="cpp_save_reduce",
        ):
            if reduce_qty <= 0 or sale_price <= 0:
                st.warning("Geçerli adet ve satış fiyatı gir.")

            else:
                new_qty = qty_now - reduce_qty

                realized_rows.append(
                    {
                        "date": datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
                        "coin": reduce_coin,
                        "quantity": reduce_qty,
                        "cost": cost_now,
                        "sale_price": sale_price,
                        "realized_pnl": reduce_qty * (sale_price - cost_now),
                        "realized_pct": (
                            (sale_price - cost_now) / cost_now * 100
                            if cost_now > 0
                            else 0
                        ),
                    }
                )

                if new_qty <= 1e-12:
                    portfolio_rows = [
                        x
                        for x in portfolio_rows
                        if x["coin"] != reduce_coin
                    ]

                else:
                    for x in portfolio_rows:
                        if x["coin"] == reduce_coin:
                            x["quantity"] = round(new_qty, 8)
                            x["updated_at"] = datetime.now().strftime(
                                "%d.%m.%Y %H:%M:%S"
                            )
                            break

                ok1 = save_json(PORTFOLIO_FILE, portfolio_rows)
                ok2 = save_json(REALIZED_FILE, realized_rows)

                if ok1 and ok2:
                    st.success("✅ Satış / azaltma kaydedildi.")
                    st.rerun()


with tab_delete:
    if not portfolio_rows:
        st.info("Portföy boş.")

    else:
        delete_coin = st.selectbox(
            "Silinecek Coin",
            [x["coin"] for x in portfolio_rows],
            key="cpp_delete_coin",
        )

        confirm = st.checkbox(
            f"{delete_coin} pozisyonunu tamamen silmeyi onaylıyorum.",
            key="cpp_delete_confirm",
        )

        if st.button(
            "🗑️ TAMAMEN SİL",
            use_container_width=True,
            key="cpp_delete_btn",
        ):
            if not confirm:
                st.warning("Silme işlemini onayla.")

            else:
                portfolio_rows = [
                    x
                    for x in portfolio_rows
                    if x["coin"] != delete_coin
                ]

                if save_json(PORTFOLIO_FILE, portfolio_rows):
                    st.success(f"✅ {delete_coin} silindi.")
                    st.rerun()


with tab_hist:
    if not realized_rows:
        st.info("Henüz gerçekleşen satış yok.")

    else:
        hist = pd.DataFrame(realized_rows)

        st.dataframe(
            hist,
            use_container_width=True,
            hide_index=True,
        )

        if "realized_pnl" in hist.columns:
            realized_total = (
                pd.to_numeric(
                    hist["realized_pnl"],
                    errors="coerce",
                )
                .fillna(0)
                .sum()
            )

            st.metric(
                "Toplam Gerçekleşen K/Z",
                fmt_money(realized_total),
            )


# ============================================================
# PORTFÖY BOŞSA
# ============================================================

portfolio_rows = load_portfolio()

if not portfolio_rows:
    st.divider()
    st.success("💼 Portföy şu anda boş.")
    st.info("Yukarıdaki **Ekle / Artır** sekmesinden coin ekleyebilirsin.")
    st.stop()


# ============================================================
# BİRLEŞTİR
# ============================================================

portfolio_df = pd.DataFrame(portfolio_rows)

portfolio_df = portfolio_df.merge(
    df_market[
        [
            "base_asset",
            "symbol",
            "price_try",
            "change_24h",
            "volume_try",
            "source",
        ]
    ],
    left_on="coin",
    right_on="base_asset",
    how="left",
)

for col in [
    "quantity",
    "cost",
    "price_try",
    "change_24h",
    "volume_try",
]:
    portfolio_df[col] = pd.to_numeric(
        portfolio_df[col],
        errors="coerce",
    ).fillna(0)


# ============================================================
# TEKNİK ANALİZ
# ============================================================

rows = []

progress = st.progress(
    0,
    text="Portföy analiz ediliyor...",
)

total = len(portfolio_df)

for i, (_, row) in enumerate(
    portfolio_df.iterrows(),
    start=1,
):
    coin = str(row["coin"])
    symbol = normalize_symbol(
        row.get(
            "symbol",
            f"{coin}TRY",
        )
    )

    technical = analyze_coin_cached(
        coin,
        symbol,
    )

    rows.append(
        {
            **row.to_dict(),
            "tech_price": safe_float(technical.get("price", 0)),
            "ema9": safe_float(technical.get("ema9", 0)),
            "ema20": safe_float(technical.get("ema20", 0)),
            "ema50": safe_float(technical.get("ema50", 0)),
            "rsi": safe_float(technical.get("rsi", 50), 50),
            "vwap": safe_float(technical.get("vwap", 0)),
            "volume_ratio": safe_float(
                technical.get("volume_ratio", 1),
                1,
            ),
            "support": safe_float(technical.get("support", 0)),
            "resistance": safe_float(technical.get("resistance", 0)),
            "rr": safe_float(technical.get("rr", 0)),
            "trend_score": safe_float(
                technical.get("trend_score", 50),
                50,
            ),
            "trade_score": safe_float(
                technical.get("trade_score", 50),
                50,
            ),
            "trade_engine_decision": str(
                technical.get("decision", "⚪ VERİ YETERSİZ")
            ),
        }
    )

    progress.progress(
        i / max(total, 1),
        text=f"{coin} analiz ediliyor ({i}/{total})",
    )

progress.empty()

portfolio_df = pd.DataFrame(rows)

portfolio_df["current_price"] = np.where(
    portfolio_df["price_try"] > 0,
    portfolio_df["price_try"],
    portfolio_df["tech_price"],
)

portfolio_df["position_value"] = (
    portfolio_df["quantity"]
    * portfolio_df["current_price"]
)

portfolio_df["cost_value"] = (
    portfolio_df["quantity"]
    * portfolio_df["cost"]
)

portfolio_df["profit_loss"] = (
    portfolio_df["position_value"]
    - portfolio_df["cost_value"]
)

portfolio_df["profit_loss_pct"] = np.where(
    portfolio_df["cost_value"] > 0,
    portfolio_df["profit_loss"]
    / portfolio_df["cost_value"]
    * 100,
    0,
)

total_value = safe_float(
    portfolio_df["position_value"].sum()
)

total_cost = safe_float(
    portfolio_df["cost_value"].sum()
)

total_profit = total_value - total_cost

total_profit_pct = (
    total_profit / total_cost * 100
    if total_cost > 0
    else 0
)

portfolio_df["weight"] = np.where(
    total_value > 0,
    portfolio_df["position_value"]
    / total_value
    * 100,
    0,
)


# ============================================================
# SKORLAR
# ============================================================

portfolio_df["Likidite"] = portfolio_df["volume_try"].apply(
    liquidity_score
)

portfolio_df["Momentum"] = portfolio_df["change_24h"].apply(
    momentum_score
)

portfolio_df["RSI Skor"] = portfolio_df["rsi"].apply(
    rsi_score
)

portfolio_df["Hacim Skor"] = portfolio_df["volume_ratio"].apply(
    volume_score
)

portfolio_df["VWAP Skor"] = portfolio_df.apply(
    lambda r: vwap_score(
        r["current_price"],
        r["vwap"],
    ),
    axis=1,
)

portfolio_df["Chase"] = portfolio_df.apply(
    lambda r: chase_score(
        safe_float(r["change_24h"]),
        safe_float(r["rsi"], 50),
        safe_float(r["current_price"]),
        safe_float(r["ema20"]),
        safe_float(r["vwap"]),
    ),
    axis=1,
)

portfolio_df["Teknik Güç"] = (
    portfolio_df["trend_score"] * 0.35
    + portfolio_df["Momentum"] * 0.18
    + portfolio_df["RSI Skor"] * 0.12
    + portfolio_df["Hacim Skor"] * 0.12
    + portfolio_df["VWAP Skor"] * 0.10
    + portfolio_df["Likidite"] * 0.13
).clip(0, 100)

portfolio_df["Risk"] = portfolio_df.apply(
    lambda r: risk_score(
        safe_float(r["weight"]),
        safe_float(r["profit_loss_pct"]),
        safe_float(r["trend_score"], 50),
        safe_float(r["Likidite"]),
        safe_float(r["Chase"]),
    ),
    axis=1,
)

portfolio_df["Kısa Skor"] = (
    portfolio_df["trade_score"] * 0.30
    + portfolio_df["trend_score"] * 0.25
    + portfolio_df["Momentum"] * 0.15
    + portfolio_df["RSI Skor"] * 0.10
    + portfolio_df["Hacim Skor"] * 0.10
    + (100 - portfolio_df["Chase"]) * 0.10
).clip(0, 100)

portfolio_df["Orta Skor"] = (
    portfolio_df["Teknik Güç"] * 0.35
    + portfolio_df["trend_score"] * 0.30
    + portfolio_df["Likidite"] * 0.10
    + portfolio_df["RSI Skor"] * 0.10
    + (100 - portfolio_df["Risk"]) * 0.15
).clip(0, 100)

portfolio_df["Uzun Skor"] = (
    portfolio_df["Teknik Güç"] * 0.35
    + portfolio_df["trend_score"] * 0.25
    + portfolio_df["Likidite"] * 0.15
    + (100 - portfolio_df["Risk"]) * 0.25
).clip(0, 100)

portfolio_df["Genel Skor"] = (
    portfolio_df["Kısa Skor"] * 0.30
    + portfolio_df["Orta Skor"] * 0.35
    + portfolio_df["Uzun Skor"] * 0.35
).clip(0, 100)

portfolio_df["Pozisyon Kararı"] = portfolio_df.apply(
    lambda r: hold_decision(
        safe_float(r["Genel Skor"]),
        safe_float(r["Risk"]),
        safe_float(r["trend_score"], 50),
    ),
    axis=1,
)

portfolio_df["Ekleme Kararı"] = portfolio_df.apply(
    lambda r: add_decision(
        safe_float(r["trade_score"]),
        safe_float(r["trend_score"]),
        safe_float(r["rr"]),
        safe_float(r["Chase"]),
        safe_float(r["Likidite"]),
        safe_float(r["rsi"], 50),
    ),
    axis=1,
)

portfolio_df["FINAL Karar"] = portfolio_df.apply(
    lambda r: final_decision(
        str(r["Pozisyon Kararı"]),
        str(r["Ekleme Kararı"]),
    ),
    axis=1,
)


# ============================================================
# GENEL ÖZET
# ============================================================

portfolio_score = safe_float(
    portfolio_df["Genel Skor"].mean()
)

portfolio_risk = safe_float(
    portfolio_df["Risk"].mean()
)

portfolio_strength = safe_float(
    portfolio_df["Teknik Güç"].mean()
)

realized_total = 0.0

if realized_rows:
    hist = pd.DataFrame(realized_rows)

    if "realized_pnl" in hist.columns:
        realized_total = safe_float(
            pd.to_numeric(
                hist["realized_pnl"],
                errors="coerce",
            )
            .fillna(0)
            .sum()
        )

if portfolio_risk >= 75 or portfolio_score < 40:
    portfolio_final = "🔴 RİSK AZALT"
elif portfolio_score >= 80 and portfolio_risk < 45:
    portfolio_final = "🟢 GÜÇLÜ PORTFÖY"
elif portfolio_score >= 65:
    portfolio_final = "🟢 POZİSYONLAR KORUNABİLİR"
elif portfolio_score >= 52:
    portfolio_final = "🟡 SEÇİCİ / TUT"
else:
    portfolio_final = "🟠 ZAYIF / AZALT"


# ============================================================
# GENEL DURUM
# ============================================================

st.divider()
st.subheader("📊 Portföy Genel Durumu")

m1, m2, m3, m4, m5, m6, m7 = st.columns(7)

m1.metric("Portföy Değeri", fmt_money(total_value))
m2.metric("Toplam Maliyet", fmt_money(total_cost))
m3.metric(
    "Açık K/Z",
    fmt_money(total_profit),
    f"{total_profit_pct:+.2f}%",
)
m4.metric("Gerçekleşen K/Z", fmt_money(realized_total))
m5.metric("Genel Skor", f"{portfolio_score:.1f}/100")
m6.metric("Teknik Güç", f"{portfolio_strength:.1f}/100")
m7.metric("Risk", f"{portfolio_risk:.1f}/100")

st.success(
    f"🎯 Portföy Genel Kararı: **{portfolio_final}**"
)


# ============================================================
# ANA TABLO
# ============================================================

st.divider()
st.subheader("💼 Portföy PRO Karar Tablosu")

table = portfolio_df[
    [
        "coin",
        "quantity",
        "cost",
        "current_price",
        "position_value",
        "profit_loss",
        "profit_loss_pct",
        "weight",
        "Teknik Güç",
        "Risk",
        "Kısa Skor",
        "Orta Skor",
        "Uzun Skor",
        "Genel Skor",
        "trade_score",
        "rr",
        "Chase",
        "Pozisyon Kararı",
        "Ekleme Kararı",
        "FINAL Karar",
    ]
].copy()

table.columns = [
    "Coin",
    "Adet",
    "Maliyet ₺",
    "Fiyat ₺",
    "Pozisyon ₺",
    "K/Z ₺",
    "K/Z %",
    "Ağırlık %",
    "Güç",
    "Risk",
    "⚡ Kısa",
    "📊 Orta",
    "🏆 Uzun",
    "🎯 Genel",
    "Trade",
    "R/R",
    "Chase",
    "Pozisyon Kararı",
    "Ekleme Kararı",
    "🎯 FINAL",
]

st.dataframe(
    table,
    use_container_width=True,
    hide_index=True,
    height=650,
)


# ============================================================
# PORTFÖY DAĞILIMI
# ============================================================

st.divider()
st.subheader("🥧 Portföy Dağılımı")

allocation = portfolio_df[
    [
        "coin",
        "position_value",
        "weight",
    ]
].copy()

allocation.columns = [
    "Coin",
    "Değer ₺",
    "Ağırlık %",
]

a1, a2 = st.columns(2)

with a1:
    st.dataframe(
        allocation,
        use_container_width=True,
        hide_index=True,
    )

with a2:
    st.bar_chart(
        allocation.set_index("Coin")["Değer ₺"]
    )

max_weight = safe_float(
    portfolio_df["weight"].max()
)

if max_weight >= 45:
    st.error(
        f"🔴 Konsantrasyon riski yüksek. "
        f"En büyük pozisyon %{max_weight:.1f}."
    )
elif max_weight >= 30:
    st.warning(
        f"🟡 Belirgin konsantrasyon var. "
        f"En büyük pozisyon %{max_weight:.1f}."
    )
else:
    st.success(
        f"🟢 Konsantrasyon kontrol altında. "
        f"En büyük pozisyon %{max_weight:.1f}."
    )


# ============================================================
# COIN BAZLI KARAR
# ============================================================

st.divider()
st.subheader("🪙 Coin Bazlı Profesyonel Karar Merkezi")

for _, row in (
    portfolio_df
    .sort_values(
        "Genel Skor",
        ascending=False,
    )
    .iterrows()
):
    with st.container(border=True):
        st.markdown(
            f"## 🪙 {row['coin']} — {row['FINAL Karar']}"
        )

        c1, c2, c3, c4, c5 = st.columns(5)

        c1.metric(
            "Fiyat",
            f"₺{fmt_price(row['current_price'])}",
        )
        c2.metric(
            "K/Z",
            fmt_money(row["profit_loss"]),
            f"{row['profit_loss_pct']:+.2f}%",
        )
        c3.metric(
            "Genel Skor",
            f"{row['Genel Skor']:.1f}/100",
        )
        c4.metric(
            "Risk",
            f"{row['Risk']:.1f}/100",
        )
        c5.metric(
            "Ağırlık",
            f"%{row['weight']:.1f}",
        )

        d1, d2, d3, d4 = st.columns(4)

        with d1:
            st.markdown("#### 📊 Teknik")
            st.write(f"**Trend:** {row['trend_score']:.1f}")
            st.write(f"**RSI:** {row['rsi']:.1f}")
            st.write(f"**EMA9:** ₺{fmt_price(row['ema9'])}")
            st.write(f"**EMA20:** ₺{fmt_price(row['ema20'])}")
            st.write(f"**EMA50:** ₺{fmt_price(row['ema50'])}")

        with d2:
            st.markdown("#### ⚡ Trade")
            st.write(f"**Trade Skoru:** {row['trade_score']:.1f}")
            st.write(f"**R/R:** 1 : {row['rr']:.2f}")
            st.write(f"**Hacim:** {row['volume_ratio']:.2f}x")
            st.write(f"**Chase:** {row['Chase']:.1f}")
            st.write(f"**Motor:** {row['trade_engine_decision']}")

        with d3:
            st.markdown("#### 🎯 Seviyeler")
            st.write(f"**Destek:** ₺{fmt_price(row['support'])}")
            st.write(f"**Direnç:** ₺{fmt_price(row['resistance'])}")
            st.write(f"**VWAP:** ₺{fmt_price(row['vwap'])}")
            st.write(f"**24s:** {row['change_24h']:+.2f}%")

        with d4:
            st.markdown("#### 🧠 Kararlar")
            st.write(f"**Pozisyon:** {row['Pozisyon Kararı']}")
            st.write(f"**Yeni Ekleme:** {row['Ekleme Kararı']}")
            st.write(f"**FINAL:** **{row['FINAL Karar']}**")
            st.write(
                f"**Kısa / Orta / Uzun:** "
                f"{row['Kısa Skor']:.0f} / "
                f"{row['Orta Skor']:.0f} / "
                f"{row['Uzun Skor']:.0f}"
            )


# ============================================================
# AÇIKLAMA
# ============================================================

with st.expander(
    "🧠 Karar Motoru Nasıl Çalışıyor?"
):
    st.markdown(
        """
**Pozisyon Kararı**, elindeki coinin tutulup tutulmaması için çalışır.

**Ekleme Kararı**, mevcut coine bugün yeni para eklemenin uygun olup olmadığını ayrıca değerlendirir.

Bu nedenle güçlü bir coin için bile fiyat çok yükselmişse sistem:

**🟡 TUT / YENİ ALIM YOK**

diyebilir.

Zayıflayan pozisyonlarda:

**🟠 AZALT**

ve ciddi teknik bozulmada:

**🔴 SAT**

kararı üretilebilir.

Portföy ağırlığı da risk hesabına dahildir. Tek coinin ağırlığı aşırı yükselirse risk skoru artar.
        """
    )


st.caption(
    "⚠️ Bu sayfa otomatik emir göndermez. "
    "Kararlar teknik karar desteğidir; yatırım tavsiyesi değildir."
)