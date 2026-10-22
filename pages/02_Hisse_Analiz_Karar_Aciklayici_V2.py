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


symbol_input = st.text_input("BIST hisse kodu", value="TUPRS", placeholder="Örn. TUPRS").strip().upper()
horizon = st.selectbox("Analiz vadesi", ["Kısa vade — 1 hafta", "Orta vade — 1–3 ay", "Uzun vade — 6 ay–3 yıl"], index=1)
run = st.button("🔍 GERÇEK VERİYLE ANALİZ ET", type="primary", use_container_width=True)

if not run:
    st.warning("Hisse kodunu kontrol edin ve analizi başlatın.")
    st.stop()
if not symbol_input or not symbol_input.replace(".", "").isalnum():
    st.error("Geçerli bir hisse kodu girin.")
    st.stop()

symbol = symbol_input
with st.spinner(f"{symbol} için fiyat, teknik ve temel veriler inceleniyor..."):
    try:
        prices = yf.Ticker(f"{symbol}.IS").history(period="2y", auto_adjust=False)
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

# A weighted diagnostic is only calculated when the relevant data exists.
parts = [(technical_score, 0.60)]
if np.isfinite(fundamental_score):
    parts.append((max(0, min(100, fundamental_score)), 0.25))
if np.isfinite(market_score):
    parts.append((max(0, min(100, market_score)), 0.15))
diagnostic_score = sum(v * w for v, w in parts) / sum(w for _, w in parts)
coverage = min(100, round((len(prices) / 200) * 25 + (25 if fundamental_available else 0) + (15 if np.isfinite(market_score) else 0) + 35))

if diagnostic_score > 80:
    diagnostic_decision = "AL ADAYI"
elif diagnostic_score > 75:
    diagnostic_decision = "İZLE / TEYİT"
else:
    diagnostic_decision = "TEYİT"
if coverage < 65 or len(prices) < 50:
    diagnostic_decision = "VERİ YETERSİZ — İZLE"

st.caption(f"Fiyat verisinin son tarihi: **{pd.Timestamp(latest_date).strftime('%d.%m.%Y')}** | Fiyat barı: **{len(prices)}** | Veri kapsamı tahmini: **%{coverage}**")
m1, m2, m3, m4 = st.columns(4)
m1.metric("Son kapanış", f"{latest_price:,.2f} TL")
m2.metric("Bu sayfanın teknik puanı", f"{technical_score:.0f}/100")
m3.metric("Bağımsız tanı puanı", f"{diagnostic_score:.1f}/100")
m4.metric("Bu sayfanın ön değerlendirmesi", diagnostic_decision)

st.divider()
st.subheader("1. Teknik görünüm")
cols = st.columns(5)
cols[0].metric("RSI(14)", fmt(rsi_now, 1))
cols[1].metric("20 günlük momentum", f"%{fmt(mom20, 1)}")
cols[2].metric("60 günlük momentum", f"%{fmt(mom60, 1)}")
cols[3].metric("Hacim / 20G ort.", f"{fmt(volume_ratio, 2)}x")
cols[4].metric("ATR(14)", fmt(atr))
ma_rows = []
for name, val in [("MA21", ma21), ("MA50", ma50), ("MA200", ma200)]:
    ma_rows.append({"Gösterge": name, "Seviye": round(val, 2) if np.isfinite(val) else None,
                    "Fiyata göre": ("ÜZERİNDE" if latest_price > val else "ALTINDA") if np.isfinite(val) else "Hesaplanamadı"})
st.dataframe(pd.DataFrame(ma_rows), use_container_width=True, hide_index=True)
st.line_chart(prices[["Close", "MA21", "MA50", "MA200"]].tail(180), use_container_width=True)

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
f1, f2, f3 = st.columns(3)
f1.metric("Temel analiz", f"{fundamental_score:.1f}/100" if np.isfinite(fundamental_score) else "VERİ YOK")
f2.metric("Piyasa skoru", f"{market_score:.1f}/100" if np.isfinite(market_score) else "VERİ YOK")
f3.metric("Veri kapsamı", f"%{coverage}")
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
