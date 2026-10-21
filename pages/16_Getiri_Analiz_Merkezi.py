"""Getiri Analiz Merkezi — BIST AI PRO."""
from __future__ import annotations

import sqlite3
from datetime import timedelta
from pathlib import Path

import pandas as pd
import streamlit as st

from modules.performance.total_return_engine import (
    calculate_period_tables,
    download_adjusted_closes,
    download_return_benchmark,
    load_benchmark_csv,
    load_universe,
)

st.set_page_config(
    page_title="BIST AI PRO - Getiri Analiz Merkezi",
    page_icon="📈",
    layout="wide",
)

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "borsa.db"

st.title("📈 Getiri Analiz Merkezi")
st.caption(
    "BIST AI PRO evrenindeki hisselerin temettü ve bölünme düzeltilmiş "
    "toplam getirisini BIST 100 RETURN endeksiyle karşılaştırır."
)

st.info(
    "Bu modül mevcut teknik analizleri ve portföy karar motorunu değiştirmez. "
    "Sonuçlar geçmiş performans karşılaştırmasıdır; tek başına alım sinyali değildir."
)

with st.expander("Hesaplama yöntemi ve veri koşulları", expanded=False):
    st.markdown(
        """
        - **Hisse evreni:** `bist500_universe` tablosundaki aktif hisseler.
        - **Hisse getirisi:** Yahoo Finance `Adj Close` serisi (temettü/bölünme düzeltmeli).
        - **Benchmark:** BIST 100 RETURN (`XU100_CFNNTLTL`) — fiyat endeksine otomatik dönüş yapılmaz.
        - **Dönemler:** 1, 2, 3, 4 ve 5 yıl; aynı son ortak tamamlanmış veri günü esas alınır.
        - **Eksik veri:** Sıfır getiri kabul edilmez; veri yetersiz olarak işaretlenir.
        - **Yıllıklandırma:** Toplam getiri üzerinden bileşik yıllık getiri hesaplanır.
        """
    )

if not DB_PATH.exists():
    st.error(
        f"Veritabanı bulunamadı: {DB_PATH}. "
        "Bu sayfayı BIST AI PRO ana klasörüne ve mevcut borsa.db dosyanın yanına yerleştir."
    )
    st.stop()

conn = None
try:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    universe = load_universe(conn)
except Exception as exc:
    st.error(f"Hisse evreni okunamadı: {exc}")
    st.stop()
finally:
    if conn is not None:
        conn.close()

c1, c2, c3 = st.columns(3)
c1.metric("Aktif evren hissesi", f"{len(universe):,}")
c2.metric("Karşılaştırma dönemi", "1–5 yıl")
c3.metric("Getiri türü", "Temettü dâhil")

with st.expander("Evren denetimi", expanded=False):
    st.dataframe(
        universe[["symbol", "company", "sector"]].rename(
            columns={"symbol": "Hisse", "company": "Şirket", "sector": "Sektör"}
        ),
        use_container_width=True,
        hide_index=True,
    )

st.subheader("Veri kaynağı")
st.write(
    "Önce BIST 100 RETURN serisi otomatik olarak denenir. Otomatik kaynak "
    "çalışmazsa Borsa İstanbul'dan dışa aktardığın tarih ve endeks değeri "
    "sütunlarını içeren CSV dosyasını yükleyebilirsin."
)
benchmark_file = st.file_uploader(
    "BIST 100 RETURN tarihsel veri CSV (gerekirse)",
    type=["csv"],
    key="benchmark_return_csv",
)

run = st.button("🔎 Beş Dönemi Hesapla", type="primary", use_container_width=True)

if run:
    benchmark = None
    benchmark_source = None
    benchmark_error = None

    if benchmark_file is not None:
        try:
            benchmark = load_benchmark_csv(benchmark_file)
            benchmark_source = f"Yüklenen CSV: {benchmark_file.name}"
        except Exception as exc:
            benchmark_error = f"CSV okunamadı: {exc}"

    if benchmark is None:
        with st.spinner("BIST 100 RETURN tarihçesi kontrol ediliyor..."):
            benchmark, benchmark_source = download_return_benchmark()

    if benchmark is None or benchmark.empty:
        st.error(
            "BIST 100 RETURN tarihçesi doğrulanamadı. Fiyat endeksiyle "
            "otomatik karşılaştırma yapılmadı; sonuçların yanıltıcı olmaması için "
            "hesaplama durduruldu."
        )
        if benchmark_error:
            st.warning(benchmark_error)
        st.markdown(
            "Borsa İstanbul'un **BIST 100 RETURN** endeksinin tarihsel verisini "
            "CSV olarak dışa aktararak yukarıdaki alana yükle. CSV'de tarih ve "
            "endeks değeri sütunları bulunmalı."
        )
        st.link_button(
            "Borsa İstanbul — BIST 100 RETURN",
            "https://www.borsaistanbul.com/en/index/xu100cfnntltl",
        )
    else:
        benchmark = benchmark.dropna().sort_index()
        as_of = pd.Timestamp(benchmark.index[-1]).normalize()
        start_date = (as_of - pd.DateOffset(years=5) - pd.Timedelta(days=15)).date()
        end_date = as_of.date()

        st.write(f"**Benchmark:** {benchmark_source}")
        st.write(f"**Son benchmark tarihi:** {as_of:%Y-%m-%d}")
        st.write(f"**Hisse fiyat aralığı:** {start_date:%Y-%m-%d} – {end_date:%Y-%m-%d}")

        symbols = universe["symbol"].tolist()
        with st.spinner(
            f"{len(symbols)} hisse için temettü/bölünme düzeltilmiş fiyatlar indiriliyor. "
            "Bu işlem veri sağlayıcı hızına bağlı olarak birkaç dakika sürebilir..."
        ):
            stock_series, failed_symbols = download_adjusted_closes(
                symbols, start_date, end_date
            )

        if not stock_series:
            st.error(
                "Hiçbir hisse için düzeltilmiş fiyat serisi alınamadı. "
                "İnternet bağlantısını ve veri sağlayıcı erişimini kontrol et."
            )
        else:
            with st.spinner("Beş dönem ve ortak liderler hesaplanıyor..."):
                tables, all_rows, leaders = calculate_period_tables(
                    universe, stock_series, benchmark
                )

            st.session_state["return_analysis_result"] = {
                "tables": tables,
                "all_rows": all_rows,
                "leaders": leaders,
                "benchmark_source": benchmark_source,
                "as_of": str(as_of.date()),
                "universe_count": len(universe),
                "downloaded_count": len(stock_series),
                "failed_symbols": failed_symbols,
            }

            st.success(
                f"Hesaplama tamamlandı: evrende {len(universe)} hisse, "
                f"düzeltilmiş fiyatı alınabilen {len(stock_series)} hisse."
            )

            if failed_symbols:
                with st.expander(f"Fiyat verisi alınamayan hisseler ({len(failed_symbols)})"):
                    st.write(", ".join(sorted(failed_symbols)))

result = st.session_state.get("return_analysis_result")

if result:
    st.divider()
    st.subheader("Sonuç özeti")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Evren", f"{result['universe_count']:,}")
    m2.metric("Fiyatı alınan", f"{result['downloaded_count']:,}")
    m3.metric("Son veri tarihi", result["as_of"])
    common_count = int(
        (result["leaders"].get("Liderlik Sayısı (5 dönem)", pd.Series(dtype=float)) == 5).sum()
    )
    m4.metric("5/5 sürekli lider", f"{common_count:,}")

    tab_names = ["1 yıl", "2 yıl", "3 yıl", "4 yıl", "5 yıl", "Ortak Liderler", "Veri Denetimi"]
    tabs = st.tabs(tab_names)

    for idx, years in enumerate((1, 2, 3, 4, 5)):
        with tabs[idx]:
            df = result["tables"].get(years, pd.DataFrame())
            st.caption(
                f"{years} yıllık toplam getiride BIST 100 RETURN endeksini aşan hisseler. "
                "Sıralama, endekse göre fark (yüzde puan) esas alınarak yapılır."
            )
            if df.empty:
                st.warning("Bu dönemde doğrulanmış veriye göre endeksi geçen hisse bulunamadı.")
            else:
                st.dataframe(df, use_container_width=True, hide_index=True)
                st.download_button(
                    f"{years} yıllık tabloyu CSV indir",
                    data=df.to_csv(index=False).encode("utf-8-sig"),
                    file_name=f"bist_ai_pro_endeks_ustu_{years}yil.csv",
                    mime="text/csv",
                    key=f"download_{years}y",
                )

    with tabs[5]:
        leaders = result["leaders"]
        if leaders.empty:
            st.warning("Ortak lider tablosu oluşturmak için yeterli karşılaştırma verisi yok.")
        else:
            show_cols = [
                c for c in [
                    "Sıra", "Hisse", "Şirket", "Sektör", "Lider Olunan Dönem",
                    "Geçerli Dönem", "Liderlik Oranı (%)", "Liderlik Sayısı (5 dönem)",
                    "1 yıl", "2 yıl", "3 yıl", "4 yıl", "5 yıl"
                ] if c in leaders.columns
            ]
            st.dataframe(leaders[show_cols], use_container_width=True, hide_index=True)
            st.download_button(
                "Ortak liderleri CSV indir",
                data=leaders.to_csv(index=False).encode("utf-8-sig"),
                file_name="bist_ai_pro_ortak_liderler.csv",
                mime="text/csv",
                key="download_leaders",
            )

    with tabs[6]:
        all_rows = result["all_rows"]
        if all_rows.empty:
            st.warning("Veri denetim tablosu boş.")
        else:
            st.write("Bu tablo, endeksi geçenler dışındaki hisseleri de gösterir; eksik geçmiş sıfır getiri sayılmaz.")
            st.dataframe(all_rows, use_container_width=True, hide_index=True)
            st.download_button(
                "Tüm karşılaştırma verisini CSV indir",
                data=all_rows.to_csv(index=False).encode("utf-8-sig"),
                file_name="bist_ai_pro_tum_getiri_karsilastirmasi.csv",
                mime="text/csv",
                key="download_all",
            )

    st.caption(
        f"Benchmark kaynağı: {result['benchmark_source']}. "
        "Geçmiş getiri gelecekteki getiriyi garanti etmez; bu ekran tek başına alım/satım sinyali değildir."
    )
