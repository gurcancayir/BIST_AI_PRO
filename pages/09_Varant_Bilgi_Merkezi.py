from __future__ import annotations

import io
import math
import re
from datetime import date, datetime

import numpy as np
import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="BIST AI PRO - Varant Merkezi", page_icon="🎓", layout="wide")

SOURCES = {
    "İş Varant": "https://isvarant.com/piyasa-analiz/varant-izleme-ekrani",
    "Ak Yatırım Günlük Bülten": "https://varant.akyatirim.com.tr/",
}
ALIASES = {
    "symbol": ["varant kodu", "varant", "kod", "sembol", "symbol"],
    "underlying": ["dayanak varlık", "dayanak varlik", "dayanak", "underlying"],
    "type": ["varant tipi", "tür", "tur", "tip", "type"],
    "issuer": ["ihraççı", "ihracci", "ihraç eden", "issuer"],
    "expiry": ["vade tarihi", "vade sonu", "vade", "expiry"],
    "strike": ["kullanım fiyatı", "kullanim fiyati", "kullanım", "strike"],
    "ratio": ["çarpan", "carpan", "dönüşüm oranı", "ratio"],
    "bid": ["alış fiyatı", "alis fiyati", "alış", "alis", "bid"],
    "ask": ["satış fiyatı", "satis fiyati", "satış", "satis", "ask"],
    "last": ["son fiyat", "kapanış", "son", "last"],
    "volume": ["işlem hacmi", "islem hacmi", "hacim", "volume"],
    "delta": ["delta (%)", "delta%", "delta"],
    "theta": ["teta (tl)", "theta (tl)", "teta", "theta"],
    "leverage": ["etkin kaldıraç", "etkin kaldirac", "effective leverage"],
    "sensitivity": ["duyarlılık", "duyarlilik", "sensitivity"],
    "risk": ["risk grubu", "risk group", "risk"],
}


def tr_money(value: float) -> str:
    if pd.isna(value):
        return "—"
    return f"{value:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


def clean(value: object) -> str:
    return re.sub(r"\s+", " ", str(value).strip().lower())


def find_col(columns, names):
    mapping = {clean(c): c for c in columns}
    for name in names:
        if clean(name) in mapping:
            return mapping[clean(name)]
    for key, original in mapping.items():
        if any(clean(name) in key for name in names):
            return original
    return None


def numeric(series: pd.Series) -> pd.Series:
    def parse(value):
        if value is None or (isinstance(value, float) and math.isnan(value)):
            return np.nan
        if isinstance(value, (int, float, np.number)):
            return float(value)
        text = str(value).strip().replace("%", "").replace("₺", "").replace("TL", "").replace(" ", "")
        if text in {"", "-", "—", "nan", "None"}:
            return np.nan
        if "," in text and "." in text:
            text = text.replace(".", "").replace(",", ".") if text.rfind(",") > text.rfind(".") else text.replace(",", "")
        elif "," in text:
            text = text.replace(".", "").replace(",", ".")
        try:
            return float(text)
        except ValueError:
            return np.nan
    return series.map(parse)


def warrant_type(value: object) -> str:
    text = clean(value)
    if "alım" in text or "alim" in text or text in {"a", "call", "c"}:
        return "ALIM"
    if "satım" in text or "satim" in text or text in {"s", "put", "p"}:
        return "SATIM"
    return str(value).strip().upper() if pd.notna(value) else ""


def normalize(raw: pd.DataFrame, issuer="") -> pd.DataFrame:
    raw = raw.copy().dropna(how="all")
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = [" ".join(str(x) for x in col if str(x) != "nan").strip() for col in raw.columns]
    out = pd.DataFrame(index=raw.index)
    for target, names in ALIASES.items():
        source = find_col(raw.columns, names)
        out[target] = raw[source] if source is not None else np.nan
    out["symbol"] = out["symbol"].astype(str).str.strip().str.upper()
    out["underlying"] = out["underlying"].astype(str).str.strip().str.upper()
    out["type"] = out["type"].map(warrant_type)
    out["issuer"] = out["issuer"].replace({np.nan: issuer, "nan": issuer}).fillna(issuer)
    for col in ["strike", "ratio", "bid", "ask", "last", "volume", "delta", "theta", "leverage", "sensitivity"]:
        out[col] = numeric(out[col])
    out["expiry"] = pd.to_datetime(out["expiry"], errors="coerce", dayfirst=True)
    out = out[out["symbol"].str.match(r"^[A-Z0-9.]{4,12}$", na=False)]
    return out.drop_duplicates("symbol").reset_index(drop=True)


@st.cache_data(ttl=300, show_spinner=False)
def fetch_ak_bulletin():
    """Ak Yatırım ana sayfasından en yeni günlük bülteni bulup PDF'yi ayrıştırır."""
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError("PDF okuyucu eksik. requirements.txt dosyasına pypdf ekleyin.") from exc

    headers = {"User-Agent": "Mozilla/5.0 Chrome/126 Safari/537.36", "Accept-Language": "tr-TR,tr;q=0.9"}
    home = requests.get(SOURCES["Ak Yatırım Günlük Bülten"], headers=headers, timeout=20)
    home.raise_for_status()
    links = re.findall(r'["\']([^"\']*varant-gunluk-bulten-[^"\']+\.pdf)["\']', home.text, flags=re.I)
    if not links:
        raise ValueError("Ana sayfada günlük varant bülteni bağlantısı bulunamadı.")
    links = list(dict.fromkeys(links))
    pdf_url = requests.compat.urljoin(home.url, links[0])
    match = re.search(r"(\d{8})\.pdf", pdf_url)
    bulletin_date = match.group(1) if match else ""

    pdf = requests.get(pdf_url, headers=headers, timeout=60)
    pdf.raise_for_status()
    reader = PdfReader(io.BytesIO(pdf.content))
    rows = []
    for page in reader.pages:
        text = page.extract_text() or ""
        for line in text.splitlines():
            parts = line.replace("(a. v.)", "(a.v.)").split()
            if len(parts) < 15 or not re.fullmatch(r"[A-Z0-9]{5,8}", parts[0]):
                continue
            if parts[1] not in {"A", "S"}:
                continue
            try:
                expiry_index = next(i for i in range(2, min(7, len(parts))) if re.fullmatch(r"\d{2}\.\d{2}\.\d{4}", parts[i]))
            except StopIteration:
                continue
            underlying = " ".join(parts[2:expiry_index])
            values = parts[expiry_index + 1:]
            if len(values) < 12:
                continue
            rows.append({
                "symbol": parts[0], "type": "ALIM" if parts[1] == "A" else "SATIM",
                "underlying": underlying, "expiry": parts[expiry_index],
                "strike": values[0], "ratio": values[1], "underlying_price": values[2],
                "bid": values[3], "ask": values[4], "change": values[5],
                "leverage": values[6], "delta": values[7], "sensitivity": values[8],
                "theta": values[9], "theta_pct": values[10], "breakeven": values[11],
                "issuer": "Ak Yatırım", "last": np.nan, "volume": np.nan, "risk": np.nan,
            })
    if not rows:
        raise ValueError("Günlük bülten indirildi fakat varant satırları ayrıştırılamadı.")
    frame = pd.DataFrame(rows).drop_duplicates("symbol")
    for col in ["strike", "ratio", "underlying_price", "bid", "ask", "change", "leverage",
                "delta", "sensitivity", "theta", "theta_pct", "breakeven", "last", "volume"]:
        frame[col] = numeric(frame[col])
    frame["expiry"] = pd.to_datetime(frame["expiry"], dayfirst=True, errors="coerce")
    if frame["delta"].abs().median(skipna=True) <= 1.05:
        frame["delta"] = frame["delta"] * 100
    label_date = datetime.strptime(bulletin_date, "%d%m%Y").strftime("%d.%m.%Y") if bulletin_date else "güncel"
    return frame.reset_index(drop=True), f"Ak Yatırım Günlük Bülten • {label_date}"


@st.cache_data(ttl=300, show_spinner=False)
def fetch_source(name: str):
    if name == "Ak Yatırım Günlük Bülten":
        return fetch_ak_bulletin()
    response = requests.get(
        SOURCES[name], timeout=20,
        headers={"User-Agent": "Mozilla/5.0 Chrome/126 Safari/537.36", "Accept-Language": "tr-TR,tr;q=0.9"},
    )
    response.raise_for_status()
    tables = pd.read_html(io.StringIO(response.text), decimal=",", thousands=".")
    frames = []
    for table in tables:
        frame = normalize(table, name)
        if len(frame) >= 2:
            frames.append(frame)
    if not frames:
        raise ValueError("Kullanılabilir tablo bulunamadı; kaynak veriyi JavaScript ile yüklüyor olabilir.")
    return pd.concat(frames, ignore_index=True).drop_duplicates("symbol"), f"{name} • {datetime.now():%d.%m.%Y %H:%M}"


def load_file(uploaded) -> pd.DataFrame:
    if uploaded.name.lower().endswith(".csv"):
        content = uploaded.getvalue()
        for encoding in ("utf-8-sig", "utf-8", "cp1254", "latin1"):
            for separator in (";", ",", "\t"):
                try:
                    raw = pd.read_csv(io.BytesIO(content), encoding=encoding, sep=separator)
                    if raw.shape[1] > 1:
                        return normalize(raw, "Dosya")
                except Exception:
                    pass
        raise ValueError("CSV biçimi okunamadı.")
    return normalize(pd.read_excel(uploaded), "Dosya")


def range_score(series, low, ideal_low, ideal_high, high):
    x = pd.to_numeric(series, errors="coerce")
    score = pd.Series(0.0, index=x.index)
    score = score.mask(x.between(ideal_low, ideal_high), 100)
    score = score.mask(x.between(low, ideal_low, inclusive="left"), (x-low)/(ideal_low-low)*100)
    score = score.mask(x.between(ideal_high, high, inclusive="right"), (high-x)/(high-ideal_high)*100)
    return score.fillna(0).clip(0, 100)


def score_data(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["days"] = (out["expiry"] - pd.Timestamp(date.today())).dt.days
    out["mid"] = np.where((out["bid"] > 0) & (out["ask"] > 0), (out["bid"] + out["ask"])/2, out["last"])
    out["spread"] = np.where(out["mid"] > 0, (out["ask"]-out["bid"])/out["mid"]*100, np.nan)
    delta = range_score(out["delta"].abs(), 15, 35, 70, 95)
    maturity = range_score(out["days"], 7, 30, 120, 240)
    leverage = range_score(out["leverage"].abs(), 1, 3, 8, 15)
    spread = (100 - out["spread"].fillna(15).clip(0, 20)*5).clip(0, 100)
    quote = ((out["bid"] > 0) & (out["ask"] > 0)).astype(float)*100
    volume = out["volume"].fillna(0).rank(pct=True)*100
    out["score"] = (delta*.25 + maturity*.25 + leverage*.15 + spread*.20 + quote*.10 + volume*.05).round(1)
    missing = out[["expiry", "bid", "ask"]].isna().any(axis=1)
    out.loc[missing, "score"] = (out.loc[missing, "score"]*.75).round(1)
    out["decision"] = np.select(
        [(out["score"] >= 75) & (out["days"] >= 21), out["score"] >= 60, out["score"] >= 45],
        ["🟢 UYGUN ADAY", "🟡 İNCELENEBİLİR", "🟠 YÜKSEK RİSK"], default="🔴 ELE",
    )
    out.loc[out["days"].between(0, 7), "decision"] = "🔴 ÇOK KISA VADE"
    out.loc[out["days"] < 0, "decision"] = "⚫ VADESİ GEÇMİŞ"
    out.loc[(out["bid"].fillna(0) <= 0) | (out["ask"].fillna(0) <= 0), "decision"] = "🔴 KOTASYON YOK"
    return out.sort_values(["score", "volume"], ascending=False)


def show_table(df):
    names = {"symbol":"Varant", "underlying":"Dayanak", "type":"Tür", "issuer":"İhraççı",
             "expiry":"Vade", "days":"Kalan Gün", "strike":"Kullanım", "bid":"Alış", "ask":"Satış",
             "last":"Son", "spread":"Spread %", "volume":"Hacim", "delta":"Delta", "theta":"Teta",
             "leverage":"Etkin Kaldıraç", "sensitivity":"Duyarlılık", "score":"AI Skor", "decision":"Karar"}
    shown = df[list(names)].rename(columns=names).copy()
    shown["Vade"] = pd.to_datetime(shown["Vade"], errors="coerce").dt.strftime("%d.%m.%Y")
    st.dataframe(shown, use_container_width=True, hide_index=True, column_config={
        "AI Skor": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.1f"),
        "Spread %": st.column_config.NumberColumn(format="%.2f"),
        "Alış": st.column_config.NumberColumn(format="%.3f"),
        "Satış": st.column_config.NumberColumn(format="%.3f"),
    })


def trade_decision(row: pd.Series, direction: str) -> tuple[str, list[str]]:
    """Yeni pozisyon için açıklanabilir karar üretir."""
    reasons = []
    expected_type = "ALIM" if direction == "YÜKSELİŞ" else "SATIM" if direction == "DÜŞÜŞ" else ""
    quote_ok = pd.notna(row["bid"]) and pd.notna(row["ask"]) and row["bid"] > 0 and row["ask"] > 0
    direction_ok = bool(expected_type) and row["type"] == expected_type
    days = row["days"] if pd.notna(row["days"]) else -1
    spread = row["spread"] if pd.notna(row["spread"]) else 99

    reasons.append(f"Dayanak beklentisi {direction}; uygun ürün türü {expected_type or 'belirsiz'}.")
    reasons.append(f"Varant türü {row['type'] or 'bilinmiyor'}, AI uygunluk skoru {row['score']:.1f}/100.")
    reasons.append(f"Vadeye {int(days)} gün kaldı." if days >= 0 else "Vade bilgisi eksik veya geçmiş.")
    reasons.append(f"Alış-satış makası %{spread:.2f}." if spread < 99 else "Spread hesaplanamadı.")

    if not expected_type:
        return "⚪ YÖN BELİRLE", reasons + ["Dayanak yönü netleşmeden varant işlemi önerilmez."]
    if not direction_ok:
        return "🔴 ALMA / YÖN UYUMSUZ", reasons + ["Varant türü seçilen dayanak beklentisiyle ters yönde."]
    if not quote_ok:
        return "🔴 ALMA / KOTASYON YOK", reasons + ["Piyasa yapıcı alış-satış kotasyonu bulunmuyor."]
    if days < 8:
        return "🔴 ALMA / ÇOK KISA VADE", reasons + ["Çok kısa vadede teta ve fiyat hassasiyeti aşırı yükselebilir."]
    if spread > 10:
        return "🔴 ALMA / MAKAS YÜKSEK", reasons + ["Yüksek spread pozisyona başlarken önemli dezavantaj yaratıyor."]
    if row["score"] >= 75 and days >= 21 and spread <= 8:
        return "🟢 AL ADAYI", reasons + ["Yön, vade, kotasyon ve risk puanı birlikte uygun görünüyor."]
    if row["score"] >= 60:
        return "🟡 TEYİT BEKLE", reasons + ["Ürün incelenebilir; dayanakta teknik teyit olmadan giriş yapılmamalı."]
    return "🟠 İZLE / ALMA", reasons + ["Mevcut risk-getiri koşulları yeni pozisyon için yeterli değil."]


def position_decision(row: pd.Series, direction: str, cost: float, stop_pct: float, target_pct: float):
    """Mevcut pozisyon için TUT/AZALT/SAT kararı üretir."""
    current = row["bid"] if pd.notna(row["bid"]) and row["bid"] > 0 else row["last"]
    if pd.isna(current) or current <= 0:
        return "⚪ FİYAT YOK", np.nan, "Güncel çıkış fiyatı olmadığı için pozisyon değerlendirilemedi."
    pnl_pct = (current / cost - 1) * 100 if cost > 0 else np.nan
    expected_type = "ALIM" if direction == "YÜKSELİŞ" else "SATIM" if direction == "DÜŞÜŞ" else ""
    direction_ok = bool(expected_type) and row["type"] == expected_type
    days = row["days"] if pd.notna(row["days"]) else -1

    if pd.notna(pnl_pct) and pnl_pct <= -abs(stop_pct):
        return "🔴 SAT / ZARAR KES", pnl_pct, "Belirlenen maksimum zarar sınırı aşıldı."
    if days <= 7:
        return "🔴 SAT / VADE RİSKİ", pnl_pct, "Vadeye çok az kaldığı için zaman değeri ve oynaklık riski çok yüksek."
    if not direction_ok:
        return "🔴 SAT / YÖN BOZULDU", pnl_pct, "Dayanak beklentisi mevcut varant türüyle artık uyumlu değil."
    if pd.notna(pnl_pct) and pnl_pct >= abs(target_pct):
        return "🟡 KÂR AL / AZALT", pnl_pct, "Belirlenen kâr hedefi görüldü; en azından kısmi realizasyon değerlendirilebilir."
    if row["score"] < 45:
        return "🟠 AZALT", pnl_pct, "Varantın uygunluk skoru zayıfladı."
    if row["score"] >= 65 and direction_ok:
        return "🟢 TUT", pnl_pct, "Yön uyumu ve ürün koşulları korunuyor."
    return "🟡 YAKIN İZLE", pnl_pct, "Kesin çıkış sinyali yok; koşullar güçlü TUT için yeterli değil."


st.title("🎓 BIST AI PRO Varant Merkezi")
st.caption("Öğren • Hesapla • Veriyi getir • Filtrele • Riski puanla")
st.error("Varantta yönü doğru tahmin etmek yeterli değildir. Yatırılan tutarın tamamı kaybedilebilir.")

learn, calculator, market, shortlist, checklist = st.tabs(
    ["📘 Varantı Öğren", "🧮 Hesaplama", "📡 Piyasa Verileri", "⭐ Aday Seçimi", "✅ Kontrol Listesi"]
)

with learn:
    st.subheader("Varant nedir?")
    st.markdown("""
Varant; dayanak varlığın fiyatına bağlı, **vadeli ve kaldıraçlı** bir sermaye piyasası aracıdır.
Dayanak şirkete ortaklık ve temettü hakkı vermez.

- **Alım varantı:** Yükseliş beklentisiyle incelenir.
- **Satım varantı:** Düşüş beklentisiyle incelenir.
- **Maksimum kayıp:** Ödenen tutarın tamamıdır.
- **Vade:** Ürünün geçerli olduğu son tarihtir.
""")
    c1, c2 = st.columns(2)
    c1.success("### ↗️ ALIM\nDayanak yükselirse değer kazanabilir.")
    c2.warning("### ↘️ SATIM\nDayanak düşerse değer kazanabilir.")
    concepts = {
        "Kullanım fiyatı": "Vade sonu değer hesabındaki referans fiyat.",
        "Çarpan": "Dayanaktaki farkın varanta aktarılma oranı.",
        "Delta": "Dayanak hareketine yaklaşık fiyat duyarlılığı.",
        "Teta": "Zaman geçişinin varant değerine olası günlük etkisi.",
        "Etkin kaldıraç": "Dayanaktaki yüzdesel hareketin varanta yaklaşık etkisi.",
        "Spread": "En iyi alış ile satış kotasyonu arasındaki fark.",
    }
    for title, text in concepts.items():
        with st.expander(title): st.write(text)
    st.info("Koddan tahmin yürütmeyin; dayanak, tür, vade, kullanım fiyatı, çarpan ve ihraççıyı doğrulayın.")

with calculator:
    st.subheader("Vade sonu değer senaryosu")
    kind = st.radio("Tür", ["ALIM", "SATIM"], horizontal=True)
    a, b, c, d = st.columns(4)
    spot = a.number_input("Dayanak uzlaşı fiyatı", 0.0, value=100.0, step=1.0)
    strike = b.number_input("Kullanım fiyatı", 0.0, value=90.0, step=1.0)
    ratio = c.number_input("Çarpan", 0.0001, value=0.10, step=0.01, format="%.4f")
    qty = d.number_input("Varant adedi", 1, value=1000, step=100)
    unit = max(spot-strike, 0)*ratio if kind == "ALIM" else max(strike-spot, 0)*ratio
    m1, m2 = st.columns(2)
    m1.metric("1 varant brüt değeri", f"{tr_money(unit)} TL")
    m2.metric("Toplam brüt değer", f"{tr_money(unit*qty)} TL")
    st.error("Bu senaryoda varant değersizdir.") if unit == 0 else st.success("Pozitif vade sonu değeri bulunuyor.")
    st.caption("Basitleştirilmiş eğitim hesabıdır; izahname ve ihraççı hükümleri esas alınır.")
    st.divider()
    p1, p2, p3, p4 = st.columns(4)
    buy = p1.number_input("Alış fiyatı", 0.01, value=0.50, step=0.01)
    sell = p2.number_input("Satış fiyatı", 0.0, value=0.65, step=0.01)
    units = p3.number_input("Adet", 1, value=1000, step=100, key="units")
    costs = p4.number_input("Masraf", 0.0, value=0.0, step=1.0)
    pnl = (sell-buy)*units-costs
    st.metric("Net sonuç", f"{tr_money(pnl)} TL", delta=f"%{pnl/(buy*units)*100:.2f}")

with market:
    st.subheader("Aktif varant verisini yükle")
    st.caption("Otomatik kaynağı deneyin. Kaynak dış erişimi kapatırsa CSV/XLSX yükleyin.")
    source = st.selectbox("Veri kaynağı", ["Ak Yatırım Günlük Bülten", "İş Varant", "CSV / Excel yükle"])
    uploaded = st.file_uploader("Varant listesi", type=["csv", "xlsx", "xls"]) if source == "CSV / Excel yükle" else None
    c1, c2 = st.columns(2)
    if c1.button("📡 Verileri getir", type="primary", use_container_width=True):
        try:
            with st.spinner("Veriler alınıyor..."):
                if source == "CSV / Excel yükle":
                    if uploaded is None: raise ValueError("Önce dosya seçin.")
                    frame, label = load_file(uploaded), f"{uploaded.name} • {datetime.now():%d.%m.%Y %H:%M}"
                else:
                    frame, label = fetch_source(source)
                if frame.empty: raise ValueError("Geçerli varant satırı bulunamadı.")
                st.session_state.warrant_data, st.session_state.warrant_source = frame, label
            st.success(f"{len(frame)} varant yüklendi.")
        except Exception as exc:
            st.error(f"Veri alınamadı: {exc}")
            st.info("Listeyi aracı kurum ekranından CSV/Excel olarak dışa aktarıp yükleyebilirsiniz.")
    if c2.button("🧹 Veriyi temizle", use_container_width=True):
        st.session_state.pop("warrant_data", None); st.session_state.pop("warrant_source", None); st.rerun()
    data = st.session_state.get("warrant_data")
    if isinstance(data, pd.DataFrame) and not data.empty:
        scored = score_data(data)
        st.caption(f"Kaynak: {st.session_state.get('warrant_source', '—')} • Skor yatırım tavsiyesi değildir.")
        a, b, c, d = st.columns(4)
        a.metric("Toplam", len(scored)); b.metric("Dayanak", scored["underlying"].replace("NAN", np.nan).nunique())
        c.metric("Kotasyonlu", int(((scored["bid"]>0)&(scored["ask"]>0)).sum()))
        d.metric("Uygun aday", int(scored["decision"].eq("🟢 UYGUN ADAY").sum()))
        show_table(scored)
        st.download_button("⬇️ Listeyi indir", scored.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig"),
                           f"varant_listesi_{date.today():%Y%m%d}.csv", "text/csv")
    else:
        st.info("Henüz veri yüklenmedi.")

with shortlist:
    data = st.session_state.get("warrant_data")
    if not isinstance(data, pd.DataFrame) or data.empty:
        st.info("Önce Piyasa Verileri sekmesinden listeyi yükleyin.")
    else:
        scored = score_data(data)
        underlyings = sorted(x for x in scored["underlying"].dropna().unique() if x not in {"", "NAN"})
        a, b, c, d = st.columns(4)
        underlying = a.selectbox("Dayanak", ["TÜMÜ"]+underlyings)
        direction = b.selectbox("Beklenti", ["YÜKSELİŞ", "DÜŞÜŞ", "HER İKİSİ"])
        min_days = c.number_input("Minimum kalan gün", 0, value=21)
        max_spread = d.number_input("Maksimum spread %", 0.0, value=10.0, step=0.5)
        result = scored.copy()
        if underlying != "TÜMÜ": result = result[result["underlying"] == underlying]
        if direction == "YÜKSELİŞ": result = result[result["type"] == "ALIM"]
        elif direction == "DÜŞÜŞ": result = result[result["type"] == "SATIM"]
        result = result[(result["days"].fillna(-1) >= min_days) & (result["spread"].isna() | (result["spread"] <= max_spread))]
        st.write(f"Filtre sonucu: **{len(result)} varant**")
        if result.empty:
            st.warning("Koşullara uyan varant yok.")
        else:
            show_table(result.head(50))
            st.subheader("İlk 3 aday")
            for _, row in result.head(3).iterrows():
                with st.expander(f"{row['symbol']} • {row['underlying']} • Skor {row['score']:.1f}", expanded=True):
                    x1, x2, x3, x4 = st.columns(4)
                    x1.metric("Tür", row["type"] or "—")
                    x2.metric("Kalan gün", int(row["days"]) if pd.notna(row["days"]) else "—")
                    x3.metric("Etkin kaldıraç", f"{row['leverage']:.2f}" if pd.notna(row["leverage"]) else "—")
                    x4.metric("Spread", f"%{row['spread']:.2f}" if pd.notna(row["spread"]) else "—")
                    st.write(row["decision"])
                    if pd.isna(row["delta"]) or pd.isna(row["leverage"]):
                        st.warning("Eksik risk parametrelerini ihraççı ekranından doğrulayın.")

            st.divider()
            st.subheader("🤖 Seçili varant yorumu ve işlem kararı")
            symbols = result["symbol"].tolist()
            selected_symbol = st.selectbox("Yorumlanacak varant", symbols, key="comment_symbol")
            selected = result[result["symbol"] == selected_symbol].iloc[0]
            decision, reasons = trade_decision(selected, direction)
            st.markdown(f"## {decision}")
            st.write(
                f"**{selected_symbol}**, {selected['underlying']} dayanağına bağlı "
                f"**{selected['type']}** varantıdır. Puanı **{selected['score']:.1f}/100** ve "
                f"mevcut sınıflandırması **{selected['decision']}**."
            )
            for reason in reasons:
                st.write(f"- {reason}")
            st.warning("AL ADAYI sonucu doğrudan piyasa emri anlamına gelmez; dayanak varlıkta teknik yön teyidi gerekir.")

            st.subheader("💼 Elimde varsa: TUT / AZALT / SAT")
            have_position = st.checkbox("Bu varant portföyümde var", key="have_warrant")
            if have_position:
                p1, p2, p3, p4 = st.columns(4)
                position_cost = p1.number_input("Maliyet (TL)", min_value=0.01, value=0.50, step=0.01)
                position_qty = p2.number_input("Adet", min_value=1, value=1000, step=100, key="position_qty")
                stop_pct = p3.number_input("Zarar-kes %", min_value=1.0, value=20.0, step=1.0)
                target_pct = p4.number_input("Kâr-al %", min_value=1.0, value=30.0, step=1.0)
                pos_decision, pos_pnl_pct, pos_comment = position_decision(
                    selected, direction, position_cost, stop_pct, target_pct
                )
                exit_price = selected["bid"] if pd.notna(selected["bid"]) else selected["last"]
                pos_pnl = (exit_price-position_cost)*position_qty if pd.notna(exit_price) else np.nan
                q1, q2, q3 = st.columns(3)
                q1.metric("Pozisyon kararı", pos_decision)
                q2.metric("Tahmini K/Z %", f"%{pos_pnl_pct:.2f}" if pd.notna(pos_pnl_pct) else "—")
                q3.metric("Tahmini K/Z", f"{tr_money(pos_pnl)} TL" if pd.notna(pos_pnl) else "—")
                st.info(pos_comment)
                st.caption("Hesapta satış için piyasa yapıcı alış fiyatı kullanılır; komisyon ve diğer masraflar dahil değildir.")

with checklist:
    checks = ["Dayanak ve türü doğruladım.", "Vade ve kullanım fiyatını kontrol ettim.",
              "Çarpan, delta, teta ve kaldıracı inceledim.", "Piyasa yapıcı kotasyonlarını gördüm.",
              "Spread ve hacmi kontrol ettim.", "Zarar kes ve maksimum tutarı belirledim.",
              "Yatırdığım tutarın tamamını kaybedebileceğimi kabul ediyorum."]
    completed = sum(st.checkbox(text, key=f"wcheck_{i}") for i, text in enumerate(checks))
    st.progress(completed/len(checks)); st.write(f"Tamamlanan: **{completed}/{len(checks)}**")
    st.success("Kontrol tamamlandı; bu kazanç garantisi değildir.") if completed == len(checks) else st.warning("Eksik kontroller varken işlem kararı vermeyin.")

st.divider()
st.caption("BIST AI PRO Varant Merkezi V2 • İşlem öncesinde aracı kurumun güncel kotasyonu ve ihraççı bilgileri esas alınmalıdır.")
