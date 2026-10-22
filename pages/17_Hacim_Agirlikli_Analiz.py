import pandas as pd
import streamlit as st
import yfinance as yf
from datetime import datetime
from zoneinfo import ZoneInfo

st.set_page_config(page_title="Hacim Ağırlıklı Analiz", page_icon="📊", layout="wide")
st.title("📊 Hacim Ağırlıklı Fiyat ve Hareketli Ortalama")
st.caption("Yahoo Finance 15 dakikalık mumları üzerinden VWAP / VWMA. Veri kapsamı ve gecikme sembole göre değişebilir; işlem kararı öncesi aracı kurum ekranıyla doğrulayın.")

DEFAULT_SYMBOLS = ["ENERY", "TUPRS", "FROTO"]
symbol_text = st.text_input("Hisse kodları (virgülle ayırın)", value=", ".join(DEFAULT_SYMBOLS))
symbols = list(dict.fromkeys(s.strip().upper().replace(".IS", "") for s in symbol_text.split(",") if s.strip()))
selected = st.selectbox("Detaylı inceleme yapılacak hisse", symbols or DEFAULT_SYMBOLS)

@st.cache_data(ttl=300, show_spinner=False)
def load_intraday(symbol):
    ticker = symbol if symbol.endswith(".IS") else f"{symbol}.IS"
    df = yf.Ticker(ticker).history(period="5d", interval="15m", auto_adjust=False, prepost=False, timeout=15)
    if df is None or df.empty:
        return pd.DataFrame(), f"{ticker}: Yahoo Finance 15 dakikalık veri döndürmedi."
    df = df.copy()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] for c in df.columns]
    required = {"High", "Low", "Close", "Volume"}
    if not required.issubset(df.columns):
        return pd.DataFrame(), f"Eksik kolonlar: {', '.join(sorted(required - set(df.columns)))}"
    df = df.dropna(subset=["High", "Low", "Close", "Volume"])
    df = df[df["Volume"] > 0].copy()
    if df.empty:
        return pd.DataFrame(), "Geçerli hacimli mum bulunamadı."
    idx = pd.to_datetime(df.index)
    if idx.tz is None:
        idx = idx.tz_localize("UTC")
    df.index = idx.tz_convert("Europe/Istanbul")
    df = df.sort_index()
    typical = (df["High"] + df["Low"] + df["Close"]) / 3.0
    session_key = pd.Series(df.index.strftime("%Y-%m-%d"), index=df.index)
    pv = typical * df["Volume"]
    df["VWAP"] = pv.groupby(session_key).cumsum() / df["Volume"].groupby(session_key).cumsum()
    df["VWMA20"] = (df["Close"] * df["Volume"]).rolling(20, min_periods=20).sum() / df["Volume"].rolling(20, min_periods=20).sum()
    df["VWMA50"] = (df["Close"] * df["Volume"]).rolling(50, min_periods=50).sum() / df["Volume"].rolling(50, min_periods=50).sum()
    df["Volume_MA20"] = df["Volume"].rolling(20, min_periods=5).mean()
    df["Volume_Ratio"] = df["Volume"] / df["Volume_MA20"]
    return df, ""

def money(x):
    return "—" if pd.isna(x) else f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

if not symbols:
    st.warning("En az bir hisse kodu girin.")
    st.stop()

rows = []
errors = {}
details = {}
with st.spinner("15 dakikalık fiyat ve hacim verileri alınıyor..."):
    for symbol in symbols:
        try:
            data, err = load_intraday(symbol)
            if err:
                errors[symbol] = err
                continue
            details[symbol] = data
            last = data.iloc[-1]
            price = float(last["Close"])
            vwap = float(last["VWAP"])
            vwma20 = last["VWMA20"]
            vwma50 = last["VWMA50"]
            vr = last["Volume_Ratio"]
            checks = [price > vwap]
            if pd.notna(vwma20):
                checks.append(price > vwma20)
            if pd.notna(vwma50):
                checks.append(price > vwma50)
            bullish = sum(checks)
            if bullish == len(checks) and pd.notna(vr) and vr >= 1.2:
                verdict = "Pozitif teyit"
            elif bullish == len(checks):
                verdict = "Olumlu, hacim teyidi zayıf"
            elif bullish == 0:
                verdict = "Zayıf görünüm"
            else:
                verdict = "Karışık / bekle"
            rows.append({
                "Hisse": symbol,
                "Son 15dk kapanış": price,
                "Gün içi VWAP": vwap,
                "VWMA 20 mum": vwma20,
                "VWMA 50 mum": vwma50,
                "Son hacim / 20 mum ort.": vr,
                "Son mum zamanı": data.index[-1].strftime("%d.%m.%Y %H:%M"),
                "Ön değerlendirme": verdict,
            })
        except Exception as exc:
            errors[symbol] = f"Veri alınamadı: {exc}"

if rows:
    result = pd.DataFrame(rows)
    view = result.copy()
    for col in ["Son 15dk kapanış", "Gün içi VWAP", "VWMA 20 mum", "VWMA 50 mum"]:
        view[col] = view[col].map(money)
    view["Son hacim / 20 mum ort."] = view["Son hacim / 20 mum ort."].map(lambda x: "—" if pd.isna(x) else f"{x:.2f}x")
    st.subheader("Hisse karşılaştırması")
    st.dataframe(view, use_container_width=True, hide_index=True)
    st.caption("VWAP her işlem gününde yeniden başlatılır. VWMA 20/50, 15 dakikalık 20/50 mum üzerinden hesaplanır. 50 mum yaklaşık 12,5 saatlik işlem süresine karşılık gelir; birkaç işlem gününe yayılabilir.")
    st.subheader(f"{selected} — ayrıntılı yorum")
    if selected in details:
        data = details[selected]
        last = data.iloc[-1]
        price = float(last["Close"])
        vwap = float(last["VWAP"])
        vwma20, vwma50 = last["VWMA20"], last["VWMA50"]
        vr = last["Volume_Ratio"]
        st.metric("Son kapanış (15dk mum)", money(price), help="Son alınan mum kapanışı; canlı anlık fiyat olmayabilir.")
        c1,c2,c3 = st.columns(3)
        c1.metric("Gün içi VWAP", money(vwap), f"{(price/vwap-1)*100:+.2f}% fiyata göre")
        c2.metric("VWMA 20", money(vwma20), "Hesaplanamadı" if pd.isna(vwma20) else f"{(price/vwma20-1)*100:+.2f}% fiyata göre")
        c3.metric("VWMA 50", money(vwma50), "Yeterli mum yok" if pd.isna(vwma50) else f"{(price/vwma50-1)*100:+.2f}% fiyata göre")
        conditions = []
        conditions.append(("Fiyat VWAP üzerinde" if price > vwap else "Fiyat VWAP altında", price > vwap))
        if pd.notna(vwma20): conditions.append(("Fiyat VWMA20 üzerinde" if price > vwma20 else "Fiyat VWMA20 altında", price > vwma20))
        if pd.notna(vwma50): conditions.append(("Fiyat VWMA50 üzerinde" if price > vwma50 else "Fiyat VWMA50 altında", price > vwma50))
        if pd.notna(vr): conditions.append((f"Hacim / 20 mum ortalaması: {vr:.2f}x", vr >= 1.2))
        positives = sum(v for _,v in conditions)
        st.markdown("**Kontrol listesi**")
        for label, ok in conditions:
            st.write(("🟢 " if ok else "🔴 ") + label)
        if positives == len(conditions) and len(conditions) >= 3:
            st.success("Kısa vadeli görünüm olumlu: fiyat hacim ağırlıklı referansların üzerinde. Yine de direnç, genel piyasa ve zarar-kes seviyesi ayrıca kontrol edilmeli.")
        elif positives == 0:
            st.warning("Kısa vadeli görünüm zayıf: fiyat hacim ağırlıklı referansların altında ve/veya hacim teyidi yok. Yeni alımda acele etmeyin.")
        else:
            st.info("Sinyaller karışık. Tek başına VWAP/VWMA ile alım kararı vermeyin; kırılımın mum kapanışı ve hacimle teyidini bekleyin.")
        chart = data[["Close", "VWAP", "VWMA20", "VWMA50"]].rename(columns={"Close":"Fiyat", "VWMA20":"VWMA 20", "VWMA50":"VWMA 50"})
        st.line_chart(chart, use_container_width=True)
        st.caption(f"Son veri zamanı: {data.index[-1].strftime('%d.%m.%Y %H:%M')} (İstanbul). Kaynak verinin gerçek gecikmesi Yahoo tarafından garanti edilmez.")
else:
    st.warning("Hiçbir sembol için kullanılabilir 15 dakikalık veri alınamadı. BIST sembol kapsamı Yahoo'da sınırlı olabilir; alternatif veri sağlayıcı gerekebilir.")

if errors:
    with st.expander("Veri alınamayan hisseler / hata ayrıntısı"):
        for symbol, err in errors.items():
            st.write(f"**{symbol}:** {err}")

st.info("Bu ekran karar destek amaçlıdır. Yahoo Finance verisi gecikebilir, eksik olabilir veya sembole göre sunulmayabilir. Emir vermeden önce aracı kurum verisiyle doğrulayın.")
