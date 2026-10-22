import sqlite3
import time
from pathlib import Path

import pandas as pd
import streamlit as st
import yfinance as yf

st.set_page_config(page_title="Hacim Ağırlıklı Analiz", page_icon="📊", layout="wide")
st.title("📊 Hacim Ağırlıklı Fiyat ve Hareketli Ortalama")
st.caption(
    "BIST AI PRO veritabanındaki aktif hisse evrenini otomatik okur. "
    "Yahoo Finance 15 dakikalık veriler grup hâlinde alınır; veri kapsamı ve gecikmesi değişebilir."
)

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "borsa.db"
BATCH_SIZE = 15
BATCH_PAUSE_SECONDS = 1.0


def normalize_symbol(value):
    symbol = str(value or "").strip().upper()
    if symbol.endswith(".IS"):
        symbol = symbol[:-3]
    return symbol


@st.cache_data(ttl=300, show_spinner=False)
def load_universe(db_path, db_mtime):
    """Read the actual BIST universe, not the synchronized stocks table."""
    path = Path(db_path)
    if not path.exists():
        return [], f"Veritabanı bulunamadı: {path}"
    try:
        with sqlite3.connect(str(path), timeout=15) as conn:
            tables = {
                row[0] for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
            if "bist500_universe" in tables:
                columns = {
                    row[1] for row in conn.execute(
                        "PRAGMA table_info(bist500_universe)"
                    ).fetchall()
                }
                if "symbol" not in columns:
                    return [], "bist500_universe tablosunda symbol kolonu yok."
                where = "WHERE symbol IS NOT NULL AND TRIM(symbol) <> ''"
                if "active" in columns:
                    where += " AND COALESCE(active, 1) = 1"
                query = f"SELECT DISTINCT symbol FROM bist500_universe {where} ORDER BY symbol"
                rows = conn.execute(query).fetchall()
                symbols = sorted({normalize_symbol(r[0]) for r in rows if normalize_symbol(r[0])})
                if symbols:
                    return symbols, ""
                return [], "bist500_universe tablosunda aktif hisse bulunamadı."
            return [], "Veritabanında bist500_universe tablosu bulunamadı."
    except Exception as exc:
        return [], f"Hisse evreni okunamadı: {exc}"


@st.cache_data(ttl=300, show_spinner=False)
def download_batch(symbols_tuple):
    """Download a small group in one request rather than issuing one request per stock."""
    symbols = list(symbols_tuple)
    tickers = [f"{symbol}.IS" for symbol in symbols]
    data = yf.download(
        tickers=tickers,
        period="5d",
        interval="15m",
        group_by="ticker",
        auto_adjust=False,
        prepost=False,
        threads=False,
        progress=False,
        timeout=25,
    )
    return data


def extract_symbol_frame(batch_data, symbol):
    if batch_data is None or batch_data.empty:
        return pd.DataFrame()
    ticker = f"{symbol}.IS"
    if isinstance(batch_data.columns, pd.MultiIndex):
        level0 = list(batch_data.columns.get_level_values(0).unique())
        level1 = list(batch_data.columns.get_level_values(1).unique())
        if ticker in level0:
            df = batch_data[ticker].copy()
        elif symbol in level0:
            df = batch_data[symbol].copy()
        elif ticker in level1:
            df = batch_data.xs(ticker, axis=1, level=1).copy()
        elif symbol in level1:
            df = batch_data.xs(symbol, axis=1, level=1).copy()
        else:
            return pd.DataFrame()
    else:
        # yfinance may return flat columns when the batch contains one ticker.
        df = batch_data.copy()
    df.columns = [str(c[0] if isinstance(c, tuple) else c) for c in df.columns]
    needed = {"High", "Low", "Close", "Volume"}
    if not needed.issubset(df.columns):
        return pd.DataFrame()
    df = df.dropna(subset=["High", "Low", "Close", "Volume"])
    df = df[df["Volume"] > 0].copy()
    if df.empty:
        return df
    idx = pd.to_datetime(df.index)
    if idx.tz is None:
        idx = idx.tz_localize("UTC")
    df.index = idx.tz_convert("Europe/Istanbul")
    df = df.sort_index()
    typical = (df["High"] + df["Low"] + df["Close"]) / 3.0
    session_key = pd.Series(df.index.strftime("%Y-%m-%d"), index=df.index)
    pv = typical * df["Volume"]
    df["VWAP"] = pv.groupby(session_key).cumsum() / df["Volume"].groupby(session_key).cumsum()
    vol_price = df["Close"] * df["Volume"]
    df["VWMA20"] = vol_price.rolling(20, min_periods=20).sum() / df["Volume"].rolling(20, min_periods=20).sum()
    df["VWMA50"] = vol_price.rolling(50, min_periods=50).sum() / df["Volume"].rolling(50, min_periods=50).sum()
    df["Volume_MA20"] = df["Volume"].rolling(20, min_periods=5).mean()
    df["Volume_Ratio"] = df["Volume"] / df["Volume_MA20"]
    return df


def money(value):
    if pd.isna(value):
        return "—"
    return f"{float(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def assess(symbol, data):
    last = data.iloc[-1]
    price = float(last["Close"])
    vwap = float(last["VWAP"])
    vwma20 = last["VWMA20"]
    vwma50 = last["VWMA50"]
    ratio = last["Volume_Ratio"]
    checks = [price > vwap]
    if pd.notna(vwma20):
        checks.append(price > float(vwma20))
    if pd.notna(vwma50):
        checks.append(price > float(vwma50))
    positive = sum(checks)
    if positive == len(checks) and pd.notna(ratio) and ratio >= 1.2:
        verdict, score = "Pozitif teyit", 85 + min(15, max(0, (float(ratio) - 1.2) * 10))
    elif positive == len(checks):
        verdict, score = "Olumlu; hacim teyidi zayıf", 65 + 20 * positive / max(1, len(checks))
    elif positive == 0:
        verdict, score = "Zayıf görünüm", 20
    else:
        verdict, score = "Karışık / bekle", 35 + 25 * positive / max(1, len(checks))
    return {
        "Hisse": symbol,
        "Skor": round(float(score), 1),
        "Son 15dk kapanış": price,
        "Gün içi VWAP": vwap,
        "VWMA 20 mum": vwma20,
        "VWMA 50 mum": vwma50,
        "Son hacim / 20 mum ort.": ratio,
        "Son mum zamanı": data.index[-1].strftime("%d.%m.%Y %H:%M"),
        "Ön değerlendirme": verdict,
    }


try:
    db_mtime = Path(DB_PATH).stat().st_mtime if Path(DB_PATH).exists() else 0
except Exception:
    db_mtime = 0
universe, universe_error = load_universe(str(DB_PATH), db_mtime)

if universe_error:
    st.error(universe_error)
    st.info("Tam evren taraması için uygulamanın kök dizininde borsa.db ve bist500_universe tablosu bulunmalıdır.")
    st.stop()

st.success(f"Veritabanındaki aktif evren: {len(universe)} hisse")
with st.expander("Tarama ayarları", expanded=True):
    mode = st.radio(
        "Tarama kapsamı",
        ["Tüm evren", "Sadece seçtiğim hisseler"],
        horizontal=True,
        help="Tüm evren seçildiğinde bist500_universe tablosundaki aktif hisseler taranır.",
    )
    selected_symbols = st.multiselect(
        "İsteğe bağlı hisse seçimi",
        options=universe,
        default=[],
        disabled=(mode == "Tüm evren"),
    )
    batch_size = st.slider("Grup büyüklüğü", min_value=5, max_value=25, value=BATCH_SIZE, step=5)
    pause_seconds = st.slider("Gruplar arası bekleme (saniye)", min_value=0.5, max_value=3.0, value=1.0, step=0.5)
    start_scan = st.button("🔎 Taramayı başlat / yenile", type="primary")

symbols = universe if mode == "Tüm evren" else (selected_symbols or [])
if not symbols:
    st.warning("Tarama için en az bir hisse seçin.")
    st.stop()

if "vwap_scan_results" not in st.session_state:
    st.session_state["vwap_scan_results"] = []
    st.session_state["vwap_scan_errors"] = {}
    st.session_state["vwap_scan_details"] = {}

if start_scan or not st.session_state["vwap_scan_results"]:
    rows, errors, details = [], {}, {}
    groups = [symbols[i:i + batch_size] for i in range(0, len(symbols), batch_size)]
    progress = st.progress(0, text="Tarama hazırlanıyor…")
    status = st.empty()
    for index, group in enumerate(groups):
        status.write(f"Grup {index + 1}/{len(groups)}: {len(group)} hisse alınıyor…")
        try:
            batch_data = download_batch(tuple(group))
            for symbol in group:
                try:
                    frame = extract_symbol_frame(batch_data, symbol)
                    if frame.empty:
                        errors[symbol] = "Yahoo Finance bu hisse için kullanılabilir 15 dakikalık veri döndürmedi."
                        continue
                    details[symbol] = frame
                    rows.append(assess(symbol, frame))
                except Exception as exc:
                    errors[symbol] = f"Analiz hatası: {exc}"
        except Exception as exc:
            for symbol in group:
                errors[symbol] = f"Grup veri isteği başarısız: {exc}"
        progress.progress((index + 1) / max(1, len(groups)), text=f"{min((index + 1) * batch_size, len(symbols))}/{len(symbols)} hisse işlendi")
        if index < len(groups) - 1:
            time.sleep(pause_seconds)
    progress.empty()
    status.empty()
    st.session_state["vwap_scan_results"] = rows
    st.session_state["vwap_scan_errors"] = errors
    st.session_state["vwap_scan_details"] = details

rows = st.session_state["vwap_scan_results"]
errors = st.session_state["vwap_scan_errors"]
details = st.session_state["vwap_scan_details"]

if rows:
    result = pd.DataFrame(rows).sort_values(["Skor", "Son hacim / 20 mum ort."], ascending=[False, False], na_position="last")
    c1, c2, c3 = st.columns(3)
    c1.metric("Evren", len(symbols))
    c2.metric("Analiz edilen", len(result))
    c3.metric("Veri alınamayan", len(errors))
    st.subheader("Tüm hisselerin VWAP/VWMA tarama sıralaması")
    view = result.copy()
    for col in ["Son 15dk kapanış", "Gün içi VWAP", "VWMA 20 mum", "VWMA 50 mum"]:
        view[col] = view[col].map(money)
    view["Son hacim / 20 mum ort."] = view["Son hacim / 20 mum ort."].map(
        lambda x: "—" if pd.isna(x) else f"{x:.2f}x"
    )
    st.dataframe(view, use_container_width=True, hide_index=True)
    st.download_button(
        "⬇️ Tarama sonuçlarını CSV indir",
        data=result.to_csv(index=False).encode("utf-8-sig"),
        file_name="bist_ai_pro_vwap_vwma_taramasi.csv",
        mime="text/csv",
    )
    detail_symbol = st.selectbox("Ayrıntılı inceleme", result["Hisse"].tolist())
    data = details.get(detail_symbol)
    if data is not None and not data.empty:
        last = data.iloc[-1]
        price = float(last["Close"])
        vwap = float(last["VWAP"])
        vwma20, vwma50 = last["VWMA20"], last["VWMA50"]
        ratio = last["Volume_Ratio"]
        st.subheader(f"{detail_symbol} — ayrıntılı yorum")
        st.metric("Son 15dk kapanış", money(price), help="Son alınan mum kapanışı; canlı anlık fiyat olmayabilir.")
        c1, c2, c3 = st.columns(3)
        c1.metric("Gün içi VWAP", money(vwap), f"{(price / vwap - 1) * 100:+.2f}% fiyata göre" if vwap else None)
        c2.metric("VWMA 20", money(vwma20), "Yeterli mum yok" if pd.isna(vwma20) else f"{(price / vwma20 - 1) * 100:+.2f}% fiyata göre")
        c3.metric("VWMA 50", money(vwma50), "Yeterli mum yok" if pd.isna(vwma50) else f"{(price / vwma50 - 1) * 100:+.2f}% fiyata göre")
        checks = [
            ("Fiyat VWAP üzerinde", price > vwap),
            ("Fiyat VWMA20 üzerinde", pd.notna(vwma20) and price > vwma20),
            ("Fiyat VWMA50 üzerinde", pd.notna(vwma50) and price > vwma50),
            (f"Hacim / 20 mum ortalaması: {ratio:.2f}x" if pd.notna(ratio) else "Hacim oranı hesaplanamadı", pd.notna(ratio) and ratio >= 1.2),
        ]
        for label, ok in checks:
            st.write(("🟢 " if ok else "🔴 ") + label)
        if all(ok for _, ok in checks):
            st.success("Kısa vadeli görünüm olumlu: fiyat hacim ağırlıklı referansların üzerinde ve hacim teyidi mevcut.")
        elif not any(ok for _, ok in checks):
            st.warning("Kısa vadeli görünüm zayıf. Tek başına VWAP/VWMA ile alım kararı vermeyin.")
        else:
            st.info("Sinyaller karışık. Kırılımı mum kapanışı ve hacimle teyit edin.")
        chart = data[["Close", "VWAP", "VWMA20", "VWMA50"]].rename(
            columns={"Close": "Fiyat", "VWMA20": "VWMA 20", "VWMA50": "VWMA 50"}
        )
        st.line_chart(chart, use_container_width=True)
        st.caption(f"Son veri zamanı: {data.index[-1].strftime('%d.%m.%Y %H:%M')} (İstanbul).")
else:
    st.warning("Hiçbir hisse için kullanılabilir 15 dakikalık veri alınamadı. Yahoo Finance bazı BIST sembollerini desteklemeyebilir.")

if errors:
    with st.expander(f"Veri alınamayan hisseler / hata ayrıntısı ({len(errors)})"):
        st.dataframe(pd.DataFrame([{"Hisse": s, "Hata": e} for s, e in errors.items()]), use_container_width=True, hide_index=True)

st.info(
    "Bu ekran karar destek amaçlıdır. Yahoo Finance verisi gecikebilir, eksik olabilir veya sembole göre sunulmayabilir. "
    "Taramada veri alınamayan hisseler ayrıca listelenir; sonuçları emir vermeden önce aracı kurum verisiyle doğrulayın."
)
