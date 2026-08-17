import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st

# ============================================================
# BIST AI PRO - BİLANÇOLAR MERKEZİ
# ============================================================
# Bu sayfa Python komut satırından çalıştırılmaz.
# Streamlit açıldığında pages klasöründeki menüden otomatik görünür.
# "📥 Bilançoları Aktar" butonu import_all_financial_reports()
# fonksiyonunu tetikler: PDF -> TXT -> SQLite.
# ============================================================

st.set_page_config(
    page_title="BIST AI PRO - Bilançolar",
    page_icon="📊",
    layout="wide",
)

BASE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = BASE_DIR / "borsa.db"
REPORTS_DIR = BASE_DIR / "data" / "financial_reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def load_statements():
    if not DB_PATH.exists():
        return pd.DataFrame()
    try:
        conn = get_connection()
        df = pd.read_sql_query(
            """
            SELECT
                id, symbol, period, period_end,
                net_profit, revenue, operating_profit,
                equity, total_assets, current_liabilities,
                long_term_financial_debt,
                short_term_financial_debt,
                operating_cash_flow,
                cash, inventory, current_assets
            FROM financial_statements
            ORDER BY period_end DESC, symbol ASC
            """,
            conn,
        )
        conn.close()

        # SQLite'dan gelen finansal kolonları kesin olarak numerik yap.
        # Eski/bozuk importlardan kalan string değerler .abs(), / vb.
        # işlemlerinde TypeError üretmesin.
        numeric_cols = [
            "net_profit", "revenue", "operating_profit", "equity",
            "total_assets", "current_liabilities",
            "long_term_financial_debt", "short_term_financial_debt",
            "operating_cash_flow", "cash", "inventory", "current_assets",
        ]

        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        if "period_end" in df.columns:
            df["period_end"] = pd.to_datetime(
                df["period_end"], errors="coerce"
            )

        return df
    except Exception:
        return pd.DataFrame()


def fmt_money(v):
    if pd.isna(v):
        return "-"
    v = float(v)
    if abs(v) >= 1_000_000_000:
        return f"{v / 1_000_000_000:.2f} Mr TL"
    if abs(v) >= 1_000_000:
        return f"{v / 1_000_000:.2f} Mn TL"
    return f"{v:,.0f} TL".replace(",", ".")


def pct(v):
    if v is None or pd.isna(v):
        return None
    return float(v) * 100



def safe_change_pct(current, previous):
    """Sayısal ve sıfır olmayan önceki değere göre değişim yüzdesi."""
    try:
        current = float(current)
        previous = float(previous)
    except (TypeError, ValueError):
        return None

    if previous == 0:
        return None

    return (current - previous) / abs(previous) * 100

def analyze_row(row, previous=None):
    comments = []
    score = 50

    profit = row.get("net_profit")
    revenue = row.get("revenue")
    op_profit = row.get("operating_profit")
    equity = row.get("equity")
    debt = (row.get("short_term_financial_debt") or 0) + (row.get("long_term_financial_debt") or 0)
    cash = row.get("cash")
    current_assets = row.get("current_assets")
    current_liabilities = row.get("current_liabilities")
    ocf = row.get("operating_cash_flow")

    if pd.notna(profit):
        if profit > 0:
            score += 10
            comments.append("Net dönem kârı pozitif; şirket kârlı çalışıyor.")
        else:
            score -= 15
            comments.append("Net dönem zararı var; kârlılık tarafında risk bulunuyor.")

    if previous is not None and pd.notna(profit) and pd.notna(previous.get("net_profit")):
        old = float(previous["net_profit"])
        if old != 0:
            change = (float(profit) - old) / abs(old) * 100
            if change >= 10:
                score += 10
                comments.append(f"Net kâr önceki döneme göre yaklaşık %{change:.1f} arttı.")
            elif change <= -10:
                score -= 10
                comments.append(f"Net kâr önceki döneme göre yaklaşık %{abs(change):.1f} geriledi.")
            else:
                comments.append(f"Net kâr değişimi sınırlı: %{change:.1f}.")

    if pd.notna(revenue) and float(revenue) > 0 and pd.notna(op_profit):
        margin = float(op_profit) / float(revenue) * 100
        if margin >= 15:
            score += 8
            comments.append(f"Esas faaliyet kârlılığı güçlü: yaklaşık %{margin:.1f}.")
        elif margin < 5:
            score -= 5
            comments.append(f"Esas faaliyet marjı düşük: yaklaşık %{margin:.1f}.")
        else:
            comments.append(f"Esas faaliyet marjı yaklaşık %{margin:.1f}.")

    if pd.notna(equity) and float(equity) > 0 and debt >= 0:
        leverage = debt / float(equity)
        if leverage < 0.5:
            score += 8
            comments.append("Finansal borç / özkaynak oranı düşük; bilanço daha rahat görünüyor.")
        elif leverage > 1.5:
            score -= 8
            comments.append("Finansal borç / özkaynak oranı yüksek; borçluluk takip edilmeli.")
        else:
            comments.append("Borçluluk seviyesi orta bölgede.")

    if pd.notna(current_assets) and pd.notna(current_liabilities) and float(current_liabilities) > 0:
        cr = float(current_assets) / float(current_liabilities)
        if cr >= 1.5:
            score += 7
            comments.append(f"Cari oran yaklaşık {cr:.2f}; kısa vadeli ödeme gücü olumlu.")
        elif cr < 1:
            score -= 7
            comments.append(f"Cari oran yaklaşık {cr:.2f}; kısa vadeli likidite baskısı var.")

    if pd.notna(ocf):
        if float(ocf) > 0:
            score += 7
            comments.append("Faaliyetlerden nakit akışı pozitif.")
        else:
            score -= 7
            comments.append("Faaliyetlerden nakit akışı negatif; nakit üretimi izlenmeli.")

    score = max(0, min(100, score))
    if score >= 75:
        verdict = "🟢 Güçlü"
    elif score >= 60:
        verdict = "🟡 Olumlu / İzle"
    elif score >= 45:
        verdict = "🟠 Temkinli"
    else:
        verdict = "🔴 Zayıf"

    return score, verdict, comments


st.title("📊 BIST AI PRO — Bilançolar Merkezi")
st.caption("KAP finansal raporları → PDF/TXT → SQLite → bilanço özeti ve yorum")

# ------------------------------------------------------------
# AKTARIM ALANI
# ------------------------------------------------------------
with st.container(border=True):
    st.subheader("📥 Bilançoları Aktar")
    st.write(
        "PDF/TXT dosyalarını aşağıdaki klasöre koyduysan, butona basman yeterli. "
        "Aktarım otomatik olarak PDF → TXT → veritabanı şeklinde yapılır."
    )

    uploaded = st.file_uploader(
        "İstersen KAP bilanço PDF'sini buradan yükle",
        type=["pdf", "txt"],
        accept_multiple_files=True,
    )

    c1, c2 = st.columns([1, 3])
    with c1:
        transfer = st.button("📥 Bilançoları Aktar", type="primary", use_container_width=True)
    with c2:
        st.caption(f"Rapor klasörü: {REPORTS_DIR}")

    if uploaded:
        for file in uploaded:
            target = REPORTS_DIR / Path(file.name).name
            target.write_bytes(file.getbuffer())
        st.success(f"{len(uploaded)} dosya rapor klasörüne alındı.")

    if transfer:
        try:
            # Importer'ın olası konumlarını destekle.
            import sys
            for p in [BASE_DIR, BASE_DIR / "modules", BASE_DIR / "modules" / "data"]:
                if str(p) not in sys.path:
                    sys.path.insert(0, str(p))

            importer = None
            for module_name in [
                "import_financial_reports",
                "modules.data.import_financial_reports",
                "modules.import_financial_reports",
            ]:
                try:
                    importer = __import__(module_name, fromlist=["import_all_financial_reports"])
                    break
                except ImportError:
                    continue

            if importer is None:
                st.error("KAP importer modülü bulunamadı. import_financial_reports.py dosyasının proje içinde olması gerekiyor.")
            else:
                with st.spinner("Bilançolar aktarılıyor... PDF → TXT → SQLite"):
                    result = importer.import_all_financial_reports()
                if result.get("success"):
                    st.success("✅ Bilanço aktarımı tamamlandı.")
                else:
                    st.warning("⚠️ Aktarım tamamlandı ancak bazı dosyalarda hata oluştu.")
                st.json(result)
                st.rerun()
        except Exception as e:
            st.error(f"Aktarım sırasında hata oluştu: {type(e).__name__}: {e}")

# ------------------------------------------------------------
# BİLANÇO LİSTESİ
# ------------------------------------------------------------
df = load_statements()

if df.empty:
    st.info("Henüz financial_statements tablosunda bilanço kaydı yok. Yukarıdaki 📥 Bilançoları Aktar butonunu kullan.")
    st.stop()

# Önceki dönemle değişimleri hesapla
for col in ["net_profit", "revenue", "operating_profit", "equity", "total_assets"]:
    df[col] = pd.to_numeric(df[col], errors="coerce")
    df[f"prev_{col}"] = df.groupby("symbol")[col].shift(-1)
    denominator = df[f"prev_{col}"].abs().replace(0, pd.NA)
    df[f"change_{col}"] = (
        (df[col] - df[f"prev_{col}"]) / denominator * 100
    )

# ------------------------------------------------------------
# FİLTRELER
# ------------------------------------------------------------
left, right = st.columns([1, 3])
with left:
    symbols = ["Tümü"] + sorted(df["symbol"].dropna().unique().tolist())
    selected = st.selectbox("Hisse", symbols)
with right:
    periods = ["Tümü"] + sorted(df["period"].dropna().unique().tolist(), reverse=True)
    selected_period = st.selectbox("Dönem", periods)

view = df.copy()
if selected != "Tümü":
    view = view[view["symbol"] == selected]
if selected_period != "Tümü":
    view = view[view["period"] == selected_period]

st.subheader("📋 Bilançolar")

summary_rows = []
for _, row in view.iterrows():
    previous = df[(df.symbol == row.symbol) & (df.period_end < row.period_end)].sort_values("period_end", ascending=False)
    prev = previous.iloc[0] if not previous.empty else None
    score, verdict, comments = analyze_row(row, prev)
    profit_change = row.get("change_net_profit")
    revenue_change = row.get("change_revenue")
    summary_rows.append({
        "Hisse": row.symbol,
        "Dönem": row.period,
        "Net Kâr": fmt_money(row.net_profit),
        "Kâr Değişim": f"%{profit_change:.1f}" if pd.notna(profit_change) else "-",
        "Hasılat": fmt_money(row.revenue),
        "Hasılat Değişim": f"%{revenue_change:.1f}" if pd.notna(revenue_change) else "-",
        "Özkaynak": fmt_money(row.equity),
        "Faaliyet Nakit": fmt_money(row.operating_cash_flow),
        "Bilanço Skoru": score,
        "Genel Görünüm": verdict,
    })

if summary_rows:
    st.dataframe(pd.DataFrame(summary_rows), use_container_width=True, hide_index=True)
else:
    st.info("Seçilen filtrelerde bilanço bulunamadı.")

# ------------------------------------------------------------
# DETAY + YORUM
# ------------------------------------------------------------
st.subheader("🔎 Bilanço Detayı ve Yorum")

if not view.empty:
    options = [f"{r.symbol} — {r.period} — {r.period_end}" for _, r in view.iterrows()]
    chosen = st.selectbox("Detayını görmek istediğin bilanço", options)
    idx = options.index(chosen)
    row = view.iloc[idx]

    previous = df[(df.symbol == row.symbol) & (df.period_end < row.period_end)].sort_values("period_end", ascending=False)
    prev = previous.iloc[0] if not previous.empty else None
    score, verdict, comments = analyze_row(row, prev)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Bilanço Skoru", f"{score}/100")
    m2.metric("Net Kâr", fmt_money(row.net_profit))
    m3.metric("Hasılat", fmt_money(row.revenue))
    m4.metric("Faaliyet Nakit", fmt_money(row.operating_cash_flow))

    st.markdown(f"### {verdict}")

    if prev is not None:
        pc = row.net_profit - prev.net_profit if pd.notna(row.net_profit) and pd.notna(prev.net_profit) else None
        rc = row.revenue - prev.revenue if pd.notna(row.revenue) and pd.notna(prev.revenue) else None
        cols = st.columns(2)
        with cols[0]:
            if pc is not None:
                st.metric("Net Kâr Değişimi", fmt_money(pc), ("-" if safe_change_pct(row.net_profit, prev.net_profit) is None else f"%{safe_change_pct(row.net_profit, prev.net_profit):.1f}"))
        with cols[1]:
            if rc is not None:
                st.metric("Hasılat Değişimi", fmt_money(rc), ("-" if safe_change_pct(row.revenue, prev.revenue) is None else f"%{safe_change_pct(row.revenue, prev.revenue):.1f}"))

    st.markdown("#### 💬 Otomatik Bilanço Yorumu")
    for comment in comments:
        st.write("• " + comment)

    debt = (row.short_term_financial_debt or 0) + (row.long_term_financial_debt or 0)
    ratios = {
        "Cari Oran": (row.current_assets / row.current_liabilities) if pd.notna(row.current_assets) and pd.notna(row.current_liabilities) and row.current_liabilities else None,
        "Borç / Özkaynak": (debt / row.equity) if pd.notna(row.equity) and row.equity else None,
        "Net Kâr Marjı": (row.net_profit / row.revenue * 100) if pd.notna(row.net_profit) and pd.notna(row.revenue) and row.revenue else None,
        "Faaliyet Kâr Marjı": (row.operating_profit / row.revenue * 100) if pd.notna(row.operating_profit) and pd.notna(row.revenue) and row.revenue else None,
    }

    st.markdown("#### 📐 Temel Oranlar")
    ratio_cols = st.columns(4)
    for col, (name, value) in zip(ratio_cols, ratios.items()):
        col.metric(name, "-" if value is None else (f"{value:.2f}" if name in ["Cari Oran", "Borç / Özkaynak"] else f"%{value:.1f}"))
