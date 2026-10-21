"""BIST AI PRO için temettü düzeltilmiş toplam getiri karşılaştırma motoru.

Bu modül mevcut teknik analiz tablolarını değiştirmez. Hisse verisi için Yahoo
Finance Adj Close (temettü ve bölünme düzeltmeli) kullanır. Benchmark olarak
yalnızca BIST 100 RETURN serisini kabul eder; fiyat endeksine sessizce düşmez.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from io import BytesIO
import sqlite3
from typing import Dict, Iterable, Optional

import numpy as np
import pandas as pd
import yfinance as yf

from modules.data.bist_lists import STOCK_TO_SECTOR

PERIODS = (1, 2, 3, 4, 5)
BENCHMARK_TICKERS = ("XU100_CFNNTLTL.IS", "XU100_CFNNTLTL")


def normalize_symbol(value: object) -> str:
    symbol = str(value or "").strip().upper()
    return symbol[:-3] if symbol.endswith(".IS") else symbol


def load_universe(conn: sqlite3.Connection) -> pd.DataFrame:
    """Evrenin tek doğruluk kaynağı olan bist500_universe tablosunu okur."""
    exists = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='bist500_universe'"
    ).fetchone()
    if not exists:
        raise RuntimeError("bist500_universe tablosu bulunamadı; evren güvenle belirlenemiyor.")

    columns = {row[1] for row in conn.execute("PRAGMA table_info(bist500_universe)")}
    required = {"symbol"}
    if not required.issubset(columns):
        raise RuntimeError("bist500_universe tablosunda symbol alanı bulunamadı.")

    select_fields = ["symbol"]
    for optional in ("company", "sector", "active"):
        if optional in columns:
            select_fields.append(optional)

    sql = "SELECT " + ", ".join(select_fields) + " FROM bist500_universe"
    if "active" in columns:
        sql += " WHERE active = 1 OR active IS NULL"
    universe = pd.read_sql_query(sql, conn)

    if universe.empty:
        raise RuntimeError("bist500_universe tablosunda aktif hisse bulunamadı.")

    for col in ("company", "sector"):
        if col not in universe.columns:
            universe[col] = ""
    universe["symbol"] = universe["symbol"].map(normalize_symbol)
    universe = universe[universe["symbol"].ne("")].drop_duplicates("symbol")
    universe["company"] = universe["company"].fillna("").astype(str).str.strip()
    universe["sector"] = universe["sector"].fillna("").astype(str).str.strip()

    # Merkezi sektör haritası yalnızca DB'de sektör bilgisi boş olan satırları tamamlar.
    # Mevcut ve kullanıcı tarafından tanımlanmış sektör değerleri ezilmez.
    blank_sector = universe["sector"].eq("") | universe["sector"].str.lower().isin(
        {"nan", "none", "null", "bilinmiyor"}
    )
    universe.loc[blank_sector, "sector"] = universe.loc[blank_sector, "symbol"].map(
        STOCK_TO_SECTOR
    ).fillna("")

    # Merkezi BIST sektör haritasındaki semboller de analiz evrenine eklenir.
    # Veritabanında bulunan satırlar önceliklidir; var olan şirket/sektör bilgileri
    # ve aktiflik durumu değiştirilmez. Yeni satırlar yalnızca sektör haritasında
    # tanımlı semboller içindir; indirilemeyen geçmişler denetim tablosunda görünür.
    mapped_symbols = pd.DataFrame({
        "symbol": list(STOCK_TO_SECTOR.keys()),
        "company": "",
        "sector": [STOCK_TO_SECTOR[s] for s in STOCK_TO_SECTOR],
    })
    universe = pd.concat([universe, mapped_symbols], ignore_index=True)
    universe = universe.drop_duplicates("symbol", keep="first")

    return universe.reset_index(drop=True)


def _ticker_for_symbol(symbol: str) -> str:
    symbol = str(symbol).strip().upper()
    return symbol if "." in symbol else f"{symbol}.IS"


def _extract_adjusted_close(frame: pd.DataFrame, ticker: str) -> Optional[pd.Series]:
    if frame is None or frame.empty:
        return None
    try:
        if isinstance(frame.columns, pd.MultiIndex):
            # yfinance may return (ticker, field) or (field, ticker).
            for level in (0, 1):
                values = frame.columns.get_level_values(level)
                if ticker in values:
                    sub = frame.xs(ticker, axis=1, level=level)
                    if "Adj Close" in sub.columns:
                        return sub["Adj Close"].dropna().astype(float)
                    return None
            return None
        if "Adj Close" in frame.columns:
            return frame["Adj Close"].dropna().astype(float)
    except Exception:
        return None
    return None


def download_adjusted_closes(
    symbols: Iterable[str],
    start_date: date,
    end_date: date,
    batch_size: int = 35,
) -> tuple[Dict[str, pd.Series], list[str]]:
    """Hisse bazında temettü/bölünme düzeltilmiş kapanış serilerini indirir."""
    clean_symbols = list(dict.fromkeys(normalize_symbol(s) for s in symbols if normalize_symbol(s)))
    result: Dict[str, pd.Series] = {}
    failed: list[str] = []
    tickers = {_ticker_for_symbol(s): s for s in clean_symbols}

    ticker_list = list(tickers)
    start = (pd.Timestamp(start_date) - pd.Timedelta(days=15)).date().isoformat()
    end = (pd.Timestamp(end_date) + pd.Timedelta(days=1)).date().isoformat()

    for offset in range(0, len(ticker_list), batch_size):
        batch = ticker_list[offset:offset + batch_size]
        try:
            data = yf.download(
                tickers=batch,
                start=start,
                end=end,
                auto_adjust=False,
                actions=True,
                group_by="ticker",
                threads=True,
                progress=False,
                timeout=30,
            )
        except Exception:
            data = pd.DataFrame()

        for ticker in batch:
            symbol = tickers[ticker]
            series = _extract_adjusted_close(data, ticker)
            if series is None or series.empty:
                failed.append(symbol)
                continue
            series.index = pd.to_datetime(series.index).tz_localize(None)
            series = series[~series.index.duplicated(keep="last")].sort_index()
            result[symbol] = series

    return result, failed


def download_return_benchmark() -> tuple[Optional[pd.Series], Optional[str]]:
    """BIST 100 RETURN endeksini dener; XU100 fiyat endeksine fallback yapmaz.

    Bazı Yahoo sembollerinde 5y isteği kısmi geçmiş döndürebildiğinden önce
    max geçmiş denenir. Kullanılabilir veri aralığı hesaplama ekranında ayrıca
    denetlenir; kısa seri 5 yıllık karşılaştırma varmış gibi kabul edilmez.
    """
    for ticker in BENCHMARK_TICKERS:
        for period in ("max", "5y"):
            try:
                frame = yf.download(
                    ticker, period=period, auto_adjust=False,
                    progress=False, threads=False, timeout=30
                )
                if frame is None or frame.empty:
                    continue
                series = _extract_adjusted_close(frame, ticker)
                if series is None:
                    # Index feed may expose only Close; source remains the RETURN index.
                    if isinstance(frame.columns, pd.MultiIndex):
                        for level in (0, 1):
                            if "Close" in frame.columns.get_level_values(level):
                                close = frame.xs("Close", axis=1, level=level)
                                if isinstance(close, pd.DataFrame):
                                    if ticker in close.columns:
                                        close = close[ticker]
                                    elif close.shape[1] == 1:
                                        close = close.iloc[:, 0]
                                if isinstance(close, pd.Series):
                                    series = close.dropna().astype(float)
                                    break
                    elif "Close" in frame.columns:
                        series = frame["Close"].dropna().astype(float)
                if series is not None and not series.empty:
                    series = series.dropna().astype(float)
                    series.index = pd.to_datetime(series.index).tz_localize(None)
                    series = series[~series.index.duplicated(keep="last")].sort_index()
                    if not series.empty:
                        return series, ticker
            except Exception:
                continue
    return None, None


def _parse_numeric(values: pd.Series) -> pd.Series:
    def parse_one(value):
        if pd.isna(value):
            return np.nan
        if isinstance(value, (int, float, np.number)):
            return float(value)
        text = str(value).strip().replace(" ", "")
        if not text:
            return np.nan
        if "," in text:
            text = text.replace(".", "").replace(",", ".")
        try:
            return float(text)
        except ValueError:
            return np.nan
    return values.map(parse_one)


def load_benchmark_csv(uploaded_file) -> pd.Series:
    """BIST resmi dışa aktarımı veya Date/Value başlıklı CSV dosyasını okur."""
    raw_bytes = uploaded_file.getvalue()
    if not raw_bytes:
        raise ValueError("Benchmark dosyası boş.")

    try:
        frame = pd.read_csv(BytesIO(raw_bytes), sep=None, engine="python")
        lowered = {str(c).strip().lower(): c for c in frame.columns}
        date_col = next((lowered[k] for k in lowered if k in {
            "date", "tarih", "datetime", "price_date", "işlem tarihi"
        }), None)
        value_col = next((lowered[k] for k in lowered if k in {
            "value", "close", "kapanis", "kapanış", "deger", "değer", "index", "endeks değeri"
        }), None)
        if date_col is None or value_col is None:
            raise ValueError("Başlıklı kolonlar tanınamadı.")
        dates = pd.to_datetime(frame[date_col], dayfirst=True, errors="coerce")
        values = _parse_numeric(frame[value_col])
    except Exception:
        frame = pd.read_csv(BytesIO(raw_bytes), sep=None, engine="python", header=None)
        if frame.shape[1] < 2:
            raise ValueError("CSV en az tarih ve endeks değeri sütunu içermeli.")
        dates = pd.to_datetime(frame.iloc[:, 0], dayfirst=True, errors="coerce")
        values = _parse_numeric(frame.iloc[:, -1])

    series = pd.Series(values.to_numpy(), index=pd.DatetimeIndex(dates))
    series = series[series.index.notna() & series.notna() & (series > 0)]
    series.index = series.index.tz_localize(None)
    series = series[~series.index.duplicated(keep="last")].sort_index()
    if series.empty:
        raise ValueError("CSV içinden geçerli tarih/endeks değeri okunamadı.")
    return series


def _latest_on_or_before(series: pd.Series, target: pd.Timestamp, max_days: int = 8):
    eligible = series.loc[series.index <= target].dropna()
    if eligible.empty:
        return None
    idx = eligible.index[-1]
    if (target - idx).days > max_days:
        return None
    return idx, float(eligible.iloc[-1])


def _total_return(series: pd.Series, start_target: pd.Timestamp, end_target: pd.Timestamp):
    start_point = _latest_on_or_before(series, start_target)
    end_point = _latest_on_or_before(series, end_target)
    if start_point is None or end_point is None:
        return None, None, None
    start_date, start_value = start_point
    end_date, end_value = end_point
    if start_value <= 0 or end_value <= 0 or end_date <= start_date:
        return None, start_date, end_date
    return (end_value / start_value - 1.0) * 100.0, start_date, end_date


def calculate_period_tables(
    universe: pd.DataFrame,
    stock_series: Dict[str, pd.Series],
    benchmark_series: pd.Series,
) -> tuple[dict[int, pd.DataFrame], pd.DataFrame, pd.DataFrame]:
    """Beş dönem için endeksi geçenleri ve ortak liderleri üretir."""
    if benchmark_series is None or benchmark_series.empty:
        raise RuntimeError("BIST 100 RETURN endeks serisi boş.")
    benchmark_series = benchmark_series.dropna().sort_index()
    as_of = pd.Timestamp(benchmark_series.index[-1]).normalize()
    benchmark_first_date = pd.Timestamp(benchmark_series.index[0]).normalize()
    tables: dict[int, pd.DataFrame] = {}
    full_rows = []

    meta = universe.set_index("symbol", drop=False)
    for years in PERIODS:
        start_target = as_of - pd.DateOffset(years=years)
        benchmark_return, benchmark_start, benchmark_end = _total_return(
            benchmark_series, start_target, as_of
        )
        rows = []
        for symbol, series in stock_series.items():
            if symbol not in meta.index:
                continue
            stock_return, stock_start, stock_end = _total_return(series, start_target, as_of)
            item = meta.loc[symbol]
            if isinstance(item, pd.DataFrame):
                item = item.iloc[0]
            valid = stock_return is not None and benchmark_return is not None
            row = {
                "Dönem": f"{years} yıl",
                "Hisse": symbol,
                "Şirket": item.get("company", ""),
                "Sektör": item.get("sector", ""),
                "Hisse Toplam Getiri (%)": round(stock_return, 2) if valid else np.nan,
                "BIST 100 Toplam Getiri (%)": round(benchmark_return, 2) if benchmark_return is not None else np.nan,
                "Endeks Başlangıç": benchmark_start.strftime("%Y-%m-%d") if benchmark_start is not None else "",
                "Endeks Bitiş": benchmark_end.strftime("%Y-%m-%d") if benchmark_end is not None else "",
                "Endeks Geçmişi İlk Tarih": benchmark_first_date.strftime("%Y-%m-%d"),
                "Endeks Farkı (yp)": round(stock_return - benchmark_return, 2) if valid else np.nan,
                "Yıllıklandırılmış Getiri (%)": round(((1 + stock_return / 100) ** (1 / years) - 1) * 100, 2)
                    if valid and stock_return > -100 else (-100.0 if valid else np.nan),
                "Hisse Başlangıç": stock_start.strftime("%Y-%m-%d") if stock_start is not None else "",
                "Hisse Bitiş": stock_end.strftime("%Y-%m-%d") if stock_end is not None else "",
                "Veri Durumu": "Uygun" if valid else "Yetersiz geçmiş/veri",
                "Endeksi Geçti": bool(valid and stock_return > benchmark_return),
            }
            full_rows.append(row)
            if valid and stock_return > benchmark_return:
                rows.append(row)

        period_df = pd.DataFrame(rows)
        if not period_df.empty:
            period_df = period_df.sort_values(
                ["Endeks Farkı (yp)", "Hisse Toplam Getiri (%)"], ascending=False
            ).reset_index(drop=True)
            period_df.insert(0, "Sıra", range(1, len(period_df) + 1))
        tables[years] = period_df

    all_df = pd.DataFrame(full_rows)
    if all_df.empty:
        return tables, all_df, pd.DataFrame()

    valid_df = all_df[all_df["Veri Durumu"].eq("Uygun")]
    leaders = (
        valid_df.groupby(["Hisse", "Şirket", "Sektör"], dropna=False)["Endeksi Geçti"]
        .agg(["sum", "count"])
        .reset_index()
        .rename(columns={"sum": "Lider Olunan Dönem", "count": "Geçerli Dönem"})
    )
    leaders["Liderlik Oranı (%)"] = (
        leaders["Lider Olunan Dönem"] / leaders["Geçerli Dönem"] * 100
    ).round(1)
    wide = all_df.pivot_table(
        index="Hisse", columns="Dönem", values="Endeksi Geçti", aggfunc="first"
    )
    for years in PERIODS:
        col = f"{years} yıl"
        if col not in wide.columns:
            wide[col] = False
    wide["Liderlik Sayısı (5 dönem)"] = wide[[f"{y} yıl" for y in PERIODS]].fillna(False).sum(axis=1)
    wide = wide.reset_index()
    leaders = leaders.merge(wide, on="Hisse", how="left")
    leaders = leaders.sort_values(
        ["Liderlik Sayısı (5 dönem)", "Liderlik Oranı (%)"], ascending=False
    ).reset_index(drop=True)
    leaders.insert(0, "Sıra", range(1, len(leaders) + 1))
    return tables, all_df, leaders
