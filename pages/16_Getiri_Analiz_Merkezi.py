"""Getiri Analiz Merkezi — BIST AI PRO."""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import streamlit as st

st.set_page_config(
    page_title="BIST AI PRO - Getiri Analiz Merkezi",
    page_icon="📈",
    layout="wide",
)

PAGE_DIR = Path(__file__).resolve().parent
BASE_DIR = next(
    (parent for parent in (PAGE_DIR, *PAGE_DIR.parents) if (parent / "modules").is_dir()),
    PAGE_DIR.parent,
)
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

try:
    import pandas as pd

    from modules.performance.total_return_engine import (
        calculate_period_tables,
        download_adjusted_closes,
        download_return_benchmark,
        get_completed_calendar_years,
        load_benchmark_csv,
        load_universe,
        has_minimum_benchmark_history,
    )
except Exception as exc:
    st.title("📈 Getiri Analiz Merkezi")
    st.error(
        "Getiri analiz modülü yüklenemedi. Dosyaların yerleşimini ve bağımlılıkları kontrol et. "
        "Motor dosyası `modules/performance/total_return_engine.py` konumunda olmalı."
    )
    st.exception(exc)
    st.stop()

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
        - **Dönemler:** Son beş tamamlanmış takvim yılı; cari yılın kısmi getirisi kullanılmaz.
        - **Eksik veri:** Sıfır getiri kabul edilmez; veri yetersiz olarak işaretlenir.
        - **Karşılaştırma:** Her yılın son işlem günündeki temettü düzeltilmiş kapanışlar karşılaştırılır.
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
c2.metric("Karşılaştırma dönemi", "5 tamamlanmış takvim yılı")
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
    "Önce otomatik kaynak denenir. Yahoo Finance bu endekste çoğu zaman yalnızca "
    "son günü döndürdüğü için yeterli geçmiş yoksa Borsa İstanbul DataStore'dan "
    "BIST 100 RETURN (`XU100_CFNNTLTL`) tarihçesini indirip CSV veya Excel olarak yükle. "
    "Karşılaştırma son beş tamamlanmış takvim yılı için yapılır."
)
benchmark_file = st.file_uploader(
    "BIST 100 RETURN tarihsel veri (CSV veya Excel, gerekirse)",
    type=["csv", "xlsx", "xls"],
    key="benchmark_return_csv",
)

run = st.button("🔎 Beş Takvim Yılını Hesapla", type="primary", use_container_width=True)

if run:
    # A failed new run must not leave a previous successful result on screen.
    st.session_state.pop("return_analysis_result", None)
    benchmark = None
    benchmark_source = None
    benchmark_error = None

    if benchmark_file is not None:
        try:
            benchmark = load_benchmark_csv(benchmark_file)
            if has_minimum_benchmark_history(benchmark, years=5):
                benchmark_source = f"Yüklenen dosya: {benchmark_file.name}"
            else:
                benchmark = None
                benchmark_error = (
                    "Benchmark dosyasında son beş tamamlanmış takvim yılını kapsayan "
                    "yeterli geçmiş bulunamadı. Tarih/değer sütunlarını ve aralığı kontrol et."
                )
        except Exception as exc:
            benchmark_error = f"Benchmark dosyası okunamadı: {exc}"

    if benchmark is None:
        with st.spinner("BIST 100 RETURN tarihçesi kontrol ediliyor..."):
            benchmark, benchmark_source = download_return_benchmark()

    if benchmark is None or benchmark.empty:
        st.error(
            "BIST 100 RETURN için son beş tamamlanmış takvim yılını kapsayan tarihçe bulunamadı. "
            "Yahoo Finance'ten gelen veri beş yıllık hesaplamaya yetmiyor; tek günlük benchmark "
            "ile yıllık getiri karşılaştırılamaz ve hesaplama durduruldu."
        )
        if benchmark_error:
            st.warning(benchmark_error)
        st.markdown(
            "Borsa İstanbul **DataStore**'dan **BIST 100 RETURN** (`XU100_CFNNTLTL`) "
            "tarihçesini indir. Dosyada tarih, endeks kodu ve kapanış/değer sütunları "
            "bulunmalı; gerekli yıl sonu referansları "
            f"{get_completed_calendar_years()[0] - 1}-12-31 – "
            f"{get_completed_calendar_years()[-1]}-12-31 aralığını kapsamalı. "
            "DataStore'dan indirilen CSV/Excel dosyasını doğrudan yükle."
        )
        st.link_button(
            "Borsa İstanbul DataStore — tarihsel veriler",
            "https://datastore.borsaistanbul.com/",
        )
    else:
        benchmark = benchmark.dropna().sort_index()
        as_of = pd.Timestamp(benchmark.index[-1]).normalize()
        analysis_years = get_completed_calendar_years()
        first_anchor = pd.Timestamp(analysis_years[0] - 1, 12, 31)
        last_anchor = pd.Timestamp(analysis_years[-1], 12, 31)
        start_date = (first_anchor - pd.Timedelta(days=15)).date()
        end_date = last_anchor.date()

        st.write(f"**Benchmark:** {benchmark_source}")
        st.write(f"**Son benchmark tarihi:** {as_of:%Y-%m-%d}")
        st.write(f"**Karşılaştırma yılları:** {analysis_years[0]}–{analysis_years[-1]}")
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
            if failed_symbols:
                st.caption(
                    f"İndirilemeyen semboller ({len(failed_symbols)}): "
                    + ", ".join(sorted(failed_symbols)[:40])
                    + (" …" if len(failed_symbols) > 40 else "")
                )
        else:
            with st.spinner("Yıllık getiriler ve ortak liderler hesaplanıyor..."):
                tables, all_rows, leaders = calculate_period_tables(
                    universe, stock_series, benchmark
                )

            st.session_state["return_analysis_result"] = {
                "tables": tables,
                "all_rows": all_rows,
                "leaders": leaders,
                "benchmark_source": benchmark_source,
                "benchmark_first_date": str(pd.Timestamp(benchmark.index[0]).date()),
                "benchmark_last_date": str(pd.Timestamp(benchmark.index[-1]).date()),
                "as_of": str(as_of.date()),
                "analysis_years": analysis_years,
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
        (result["leaders"].get("Endeksi Geçtiği Yıl Sayısı (5 yıl)", pd.Series(dtype=float)) == 5).sum()
    )
    m4.metric("5 yılın tümünde endeksi geçen", f"{common_count:,}")

    analysis_years = result.get("analysis_years", [])
    tab_names = [str(year) for year in analysis_years] + ["Ortak Liderler", "Veri Denetimi"]
    tabs = st.tabs(tab_names)

    for idx, year in enumerate(analysis_years):
        with tabs[idx]:
            df = result["tables"].get(year, pd.DataFrame())
            st.caption(
                f"{year} takvim yılında geçerli verisi bulunan tüm hisseler. "
                "Sıralama BIST 100 RETURN'e göre yıllık getiri farkına göredir; "
                "'Endeksi Geçti' sütunu sonucu gösterir."
            )
            if df.empty:
                audit = result.get("all_rows", pd.DataFrame())
                period_label = str(year)
                period_audit = (
                    audit[audit["Dönem"].eq(period_label)]
                    if not audit.empty and "Dönem" in audit.columns
                    else pd.DataFrame()
                )
                valid_audit = (
                    period_audit[period_audit["Veri Durumu"].eq("Uygun")]
                    if not period_audit.empty and "Veri Durumu" in period_audit.columns
                    else pd.DataFrame()
                )
                if period_audit.empty or valid_audit.empty:
                    st.warning(
                        f"{year} takvim yılı için doğrulanmış karşılaştırma verisi yok. "
                        "Bu, hisselerin endeksi geçemediği anlamına gelmez; yıl sonu benchmark "
                        "veya hisse fiyat geçmişi eksik olabilir."
                    )
                    if not period_audit.empty and "Veri Durumu" in period_audit.columns:
                        st.caption(
                            f"Denetlenen kayıt: {len(period_audit)} | "
                            f"Geçerli karşılaştırma: {len(valid_audit)} | "
                            f"Verisi yetersiz: {len(period_audit) - len(valid_audit)}"
                        )
                else:
                    st.info(
                        f"{year} yılında geçerli karşılaştırması olan "
                        f"{len(valid_audit)} hisse bulundu; tabloya tümü eklenmeliydi."
                    )
                    st.caption(
                        "Ayrıntılı getiriler ve veri durumları için 'Veri Denetimi' sekmesini aç."
                    )
            else:
                st.dataframe(df, use_container_width=True, hide_index=True)
                st.download_button(
                    f"{year} yılı tablosunu CSV indir",
                    data=df.to_csv(index=False).encode("utf-8-sig"),
                    file_name=f"bist_ai_pro_endeks_ustu_{year}.csv",
                    mime="text/csv",
                    key=f"download_{year}",
                )

    with tabs[len(analysis_years)]:
        leaders = result["leaders"]
        if leaders.empty:
            st.warning("Ortak lider tablosu oluşturmak için yeterli karşılaştırma verisi yok.")
        else:
            show_cols = [
                c for c in [
                    "Sıra", "Hisse", "Şirket", "Sektör", "Lider Olunan Yıl",
                    "Geçerli Yıl", "Yıllık Liderlik Oranı (%)", "Endeksi Geçtiği Yıl Sayısı (5 yıl)",
                    *[str(year) for year in analysis_years]
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

    with tabs[len(analysis_years) + 1]:
        all_rows = result["all_rows"]
        if all_rows.empty:
            st.warning("Veri denetim tablosu boş.")
        else:
            st.write("Bu tablo, endeksi geçemeyen hisseleri de gösterir; eksik geçmiş sıfır getiri sayılmaz.")
            st.dataframe(all_rows, use_container_width=True, hide_index=True)
            st.download_button(
                "Tüm karşılaştırma verisini CSV indir",
                data=all_rows.to_csv(index=False).encode("utf-8-sig"),
                file_name="bist_ai_pro_tum_getiri_karsilastirmasi.csv",
                mime="text/csv",
                key="download_all",
            )

    st.caption(
        f"Benchmark kaynağı: {result['benchmark_source']} | "
        f"Endeks tarihçesi: {result.get('benchmark_first_date', 'bilinmiyor')} – "
        f"{result.get('benchmark_last_date', result['as_of'])}. "
        "Geçmiş getiri gelecekteki getiriyi garanti etmez; bu ekran tek başına alım/satım sinyali değildir."
    )

