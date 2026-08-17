import re
import requests
import streamlit as st
import pandas as pd
import numpy as np

from modules.data.bist_lists import BIST30, BIST50, BIST100
from modules.data.yahoo_data import get_stock_analysis
from modules.data.fundamental import get_fundamental_data, calculate_fundamental_score
from modules.ai.market_ai import get_market_score

st.set_page_config(page_title='BIST AI PRO - Dinamik Portföy Test', page_icon='🧠', layout='wide')
st.title('🧠 BIST AI PRO — Dinamik Portföy Motoru')
st.caption('Midas hisse evreni → teknik + temel + momentum + trend + hacim → sektör gücü → dinamik model portföy')

MIDAS_URL='https://www.getmidas.com/canli-borsa/'
REQUEST_TIMEOUT=20
MIN_UNIVERSE=450
TECH_WEIGHT=0.50
FUND_WEIGHT=0.20
MOMENTUM_WEIGHT=0.15
MARKET_WEIGHT=0.15

SECTOR_OPTIONS=['Banka','Enerji','Savunma','Çimento','Ulaştırma','Perakende','Otomotiv','Holding','Sanayi','Teknoloji','Sağlık','Gıda/İçecek','Finans','Sigorta','GYO','Madencilik','Telekomünikasyon','İnşaat','Turizm','Kimya','Diğer']

MANUAL_SECTOR_MAP={
'AKBNK':'Banka','GARAN':'Banka','ISCTR':'Banka','YKBNK':'Banka','VAKBN':'Banka','HALKB':'Banka','SKBNK':'Banka','TSKB':'Banka','ALBRK':'Banka','KLNMA':'Banka','ICBCT':'Banka',
'AKSEN':'Enerji','AKFYE':'Enerji','ENJSA':'Enerji','GWIND':'Enerji','GESAN':'Enerji','EUPWR':'Enerji','ODAS':'Enerji','ZOREN':'Enerji','AYDEM':'Enerji','ALFAS':'Enerji','ASTOR':'Enerji','SMRTG':'Enerji','YEOTK':'Enerji','CWENE':'Enerji','KONTR':'Enerji','BIOEN':'Enerji','MAGEN':'Enerji','NATEN':'Enerji','ESEN':'Enerji','ENERY':'Enerji','MOGAN':'Enerji','TUPRS':'Enerji',
'ASELS':'Savunma','SDTTR':'Savunma','ALTNY':'Savunma','ONRYT':'Savunma',
'AKCNS':'Çimento','CIMSA':'Çimento','OYAKC':'Çimento','BUCIM':'Çimento','KONYA':'Çimento','NUHCM':'Çimento','BSOKE':'Çimento','GOLTS':'Çimento','KAPLM':'Çimento','BTCIM':'Çimento','BOBET':'Çimento',
'THYAO':'Ulaştırma','PGSUS':'Ulaştırma','TAVHL':'Ulaştırma','CLEBI':'Ulaştırma','RYSAS':'Ulaştırma',
'BIMAS':'Perakende','MGROS':'Perakende','SOKM':'Perakende','MAVI':'Perakende','TABGD':'Perakende','KOTON':'Perakende','BIGEN':'Perakende','BIZIM':'Perakende',
'FROTO':'Otomotiv','TOASO':'Otomotiv','DOAS':'Otomotiv','TTRAK':'Otomotiv','KARSN':'Otomotiv','OTKAR':'Otomotiv','AYGAZ':'Otomotiv','JANTS':'Otomotiv',
'KCHOL':'Holding','SAHOL':'Holding','DOHOL':'Holding','AGHOL':'Holding','ALARK':'Holding','GSDHO':'Holding','GLYHO':'Holding',
'SISE':'Sanayi','EREGL':'Sanayi','KRDMD':'Sanayi','KCAER':'Sanayi','AKSA':'Sanayi','ARCLK':'Sanayi','BRSAN':'Sanayi','VESBE':'Sanayi','VESTL':'Sanayi','KORDS':'Sanayi','CEMTS':'Sanayi','SARKY':'Sanayi','KRDMA':'Sanayi','KRDMB':'Sanayi',
'SASA':'Kimya','PETKM':'Kimya','HEKTS':'Kimya','ALKIM':'Kimya',
'ARDYZ':'Teknoloji','MIATK':'Teknoloji','INDES':'Teknoloji','LOGO':'Teknoloji','ODINE':'Teknoloji','REEDR':'Teknoloji','BINHO':'Teknoloji','KAREL':'Teknoloji','LINK':'Teknoloji','PENTA':'Teknoloji','FORTE':'Teknoloji','HTTBT':'Teknoloji','SMART':'Teknoloji','KRONT':'Teknoloji','VBTYZ':'Teknoloji','ARENA':'Teknoloji','ATATP':'Teknoloji','ESCOM':'Teknoloji',
'MPARK':'Sağlık','SELEC':'Sağlık','MEDTR':'Sağlık','ECILC':'Sağlık','LKMNH':'Sağlık','GENIL':'Sağlık','DEVA':'Sağlık','TRILC':'Sağlık','EGEPO':'Sağlık','ONCSM':'Sağlık',
'CCOLA':'Gıda/İçecek','AEFES':'Gıda/İçecek','ULKER':'Gıda/İçecek','TATGD':'Gıda/İçecek','TUKAS':'Gıda/İçecek','BANVT':'Gıda/İçecek','PNSUT':'Gıda/İçecek','PETUN':'Gıda/İçecek','KERVT':'Gıda/İçecek','SOKE':'Gıda/İçecek',
'ISMEN':'Finans','INFO':'Finans','GEDIK':'Finans','GLBMD':'Finans','ANSGR':'Sigorta','ANHYT':'Sigorta','TURSG':'Sigorta','AGESA':'Sigorta',
'EKGYO':'GYO','ISGYO':'GYO','TRGYO':'GYO','HLGYO':'GYO','SAFGY':'GYO','KLGYO':'GYO','ALGYO':'GYO','OZKGY':'GYO','PEKGY':'GYO','SRVGY':'GYO','RYGYO':'GYO',
'KOZAL':'Madencilik','KOZAA':'Madencilik','IPEKE':'Madencilik','CVKMD':'Madencilik','PRKME':'Madencilik',
'TCELL':'Telekomünikasyon','TTKOM':'Telekomünikasyon','ENKAI':'İnşaat','TURGG':'İnşaat','YYAPI':'İnşaat','SKYMD':'İnşaat',
'AVTUR':'Turizm','DOCO':'Turizm','MAALT':'Turizm','ULAS':'Turizm'
}

SECTOR_NORMALIZATION={'Banks':'Banka','Banking':'Banka','Financial Services':'Finans','Capital Markets':'Finans','Insurance':'Sigorta','Oil & Gas':'Enerji','Utilities':'Enerji','Renewable Energy':'Enerji','Aerospace & Defense':'Savunma','Airlines':'Ulaştırma','Transportation':'Ulaştırma','Railroads':'Ulaştırma','Marine Shipping':'Ulaştırma','Retail':'Perakende','Auto Manufacturers':'Otomotiv','Auto Parts':'Otomotiv','Conglomerates':'Holding','Industrial Products':'Sanayi','Machinery':'Sanayi','Steel':'Sanayi','Building Materials':'Çimento','Construction Materials':'Çimento','Electrical Equipment':'Sanayi','Manufacturing':'Sanayi','Chemicals':'Kimya','Engineering & Construction':'İnşaat','Construction':'İnşaat','Technology':'Teknoloji','Software':'Teknoloji','Information Technology':'Teknoloji','Semiconductors':'Teknoloji','Healthcare':'Sağlık','Medical Devices':'Sağlık','Biotechnology':'Sağlık','Drug Manufacturers':'Sağlık','Food & Beverage':'Gıda/İçecek','Beverages':'Gıda/İçecek','Packaged Foods':'Gıda/İçecek','Real Estate':'GYO','REIT':'GYO','Gold':'Madencilik','Silver':'Madencilik','Copper':'Madencilik','Mining':'Madencilik','Telecom':'Telekomünikasyon','Telecom Services':'Telekomünikasyon','Communication Services':'Telekomünikasyon','Travel Services':'Turizm','Lodging':'Turizm'}

def normalize_symbol(x):
    return re.sub(r'[^A-Z0-9]','',str(x).upper().replace('.IS','').replace('$',''))

def safe_float(x,default=0):
    try:
        if x is None:return default
        if isinstance(x,str):x=x.replace('%','').replace(',','.').strip()
        v=float(x)
        return default if np.isnan(v) or np.isinf(v) else v
    except:return default

def clamp(x,lo=0,hi=100):return max(lo,min(safe_float(x,50),hi))

@st.cache_data(ttl=300,show_spinner=False)
def get_midas_html():
    r=requests.get(MIDAS_URL,headers={'User-Agent':'Mozilla/5.0 Chrome/151 Safari/537.36','Accept-Language':'tr-TR,tr;q=0.9,en;q=0.8'},timeout=REQUEST_TIMEOUT)
    r.raise_for_status();return r.text

def extract_midas_symbols(html):
    patterns=[r'<a[^>]+class=["\'][^"\']*stock-code[^"\']*["\'][^>]*>\s*([A-Z0-9]{2,12})\s*</a>',r'/canli-borsa/([a-z0-9]+)-hisse/']
    out=[]
    for p in patterns:
        for s in re.findall(p,html or '',re.I):
            s=normalize_symbol(s)
            if 2<=len(s)<=12:out.append(s)
        if len(set(out))>=MIN_UNIVERSE:break
    return list(dict.fromkeys(out))

def universe_coverage(u):
    s=set(u);lists=[BIST30,BIST50,BIST100]
    return [(sum(normalize_symbol(x) in s for x in z),len(z)) for z in lists]

def get_sector(symbol,analysis=None):
    symbol=normalize_symbol(symbol)
    if symbol in MANUAL_SECTOR_MAP:return MANUAL_SECTOR_MAP[symbol]
    try:
        from modules.data.bist_lists import SECTOR_MAP
        for name,items in SECTOR_MAP.items():
            if symbol in {normalize_symbol(x) for x in items} and name in SECTOR_OPTIONS:return name
    except Exception:pass
    if analysis:
        for key in ('sector','sector_name','sectorName','industry','industry_name'):
            v=str(analysis.get(key) or '').strip()
            if v in SECTOR_OPTIONS:return v
            if v in SECTOR_NORMALIZATION:return SECTOR_NORMALIZATION[v]
    return 'Diğer'

def stock_result(symbol,market):
    a=get_stock_analysis(symbol)
    if not a:return None
    technical=clamp(a.get('score',50));momentum=clamp(a.get('momentum_60_score',50));trend=clamp(a.get('trend_strength',50));volume=clamp(a.get('volume_score',50));rsi=safe_float(a.get('rsi',50),50);price=safe_float(a.get('price',0));change=safe_float(a.get('change',0))
    try:
        f=get_fundamental_data(symbol);fund=clamp(calculate_fundamental_score(f)) if f is not None else 50
    except Exception:fund=50
    general=clamp(technical*.50+fund*.20+momentum*.15+market*.15)
    decision='🟢 Güçlü Al' if general>=85 else '🟢 Al' if general>=75 else '🟡 Tut' if general>=60 else '🟠 Zayıf' if general>=45 else '🔴 Sat'
    decline_points=(2 if change<=-4 else 1 if change<=-2 else 0)+(2 if technical<45 else 1 if technical<55 else 0)+(2 if trend<40 else 1 if trend<50 else 0)+(1 if rsi<35 else 0)
    decline='🔴 Düşüş Sinyali' if decline_points>=4 else '🟡 Zayıflama' if decline_points>=2 else '🟢 Pozitif'
    risk_points=(3 if change<=-5 else 2 if change<=-3 else 1 if change<=-2 else 0)+(1 if rsi>=75 else 0)+(2 if technical<45 else 1 if technical<60 else 0)+(2 if trend<40 else 1 if trend<50 else 0)
    risk='🔴 Yüksek' if risk_points>=4 else '🟡 Dikkat' if risk_points>=2 else '🟢 Normal'
    return {'Hisse':symbol,'Sektör':get_sector(symbol,a),'Fiyat':price,'Günlük %':change,'Genel Skor':round(general,1),'Teknik':round(technical,1),'Temel':round(fund,1),'Momentum':round(momentum,1),'Trend':round(trend,1),'Hacim':round(volume,1),'RSI':round(rsi,1),'Market':round(market,1),'Karar':decision,'Düşüş':decline,'Risk':risk}

def sector_score(g):
    return round(clamp(g['Teknik'].mean()*.25+g['Temel'].mean()*.15+g['Momentum'].mean()*.20+g['Trend'].mean()*.15+g['Hacim'].mean()*.10+g['Genel Skor'].mean()*.15),1)

def portfolio_size(m):
    return 5 if m>=85 else 6 if m>=80 else 7 if m>=75 else 8 if m>=70 else 9 if m>=65 else 10 if m>=60 else 11 if m>=55 else 12 if m>=50 else 14

def sector_count(m):return 3 if m>=80 else 4 if m>=70 else 5 if m>=60 else 6 if m>=50 else 7

def build_portfolio(stocks,sectors,market):
    if stocks.empty or sectors.empty:return pd.DataFrame()
    n=portfolio_size(market);sn=sector_count(market);ss=dict(zip(sectors.Sektör,sectors['Sektör Skoru']))
    w=stocks.copy();w['Sektör Skoru']=w.Sektör.map(ss).fillna(50);w['Aday Skoru']=(w['Genel Skor']*.70+w['Sektör Skoru']*.20+w['Momentum']*.05+w['Trend']*.05);w['Portföy Skoru']=w['Aday Skoru']
    w.loc[w.Düşüş=='🔴 Düşüş Sinyali','Portföy Skoru']-=15;w.loc[w.Risk=='🔴 Yüksek','Portföy Skoru']-=8
    allowed=set(sectors.head(sn).Sektör);c=w[w.Sektör.isin(allowed)].sort_values('Portföy Skoru',ascending=False)
    selected=[];used=set()
    for _,r in c.iterrows():
        if r.Sektör not in used:selected.append(r);used.add(r.Sektör)
        if len(selected)>=min(sn,n):break
    for _,r in c.iterrows():
        if len(selected)>=n:break
        if r.Hisse not in {x.Hisse for x in selected}:selected.append(r)
    if not selected:return pd.DataFrame()
    p=pd.DataFrame(selected);p['Ham Ağırlık']=(p['Portföy Skoru']*.65+p['Sektör Skoru']*.35).clip(lower=1);p['Ağırlık %']=p['Ham Ağırlık']/p['Ham Ağırlık'].sum()*100;p['Ağırlık %']=p['Ağırlık %'].clip(upper=25);p['Ağırlık %']=p['Ağırlık %']/p['Ağırlık %'].sum()*100;p=p.sort_values('Ağırlık %',ascending=False).reset_index(drop=True);p.insert(0,'Sıra',range(1,len(p)+1));return p

try:html=get_midas_html()
except Exception as e:st.error(f'Midas HTML alınamadı: {e}');st.stop()
symbols=extract_midas_symbols(html)
if len(symbols)<MIN_UNIVERSE:st.error(f'BIST evreni doğrulanamadı. Bulunan: **{len(symbols)}**');st.stop()
st.success(f'✅ Midas evreni doğrulandı — **{len(symbols)} tekil hisse** bulundu.')
coverage=universe_coverage(symbols);c1,c2,c3=st.columns(3)
for c,(found,total),name in zip((c1,c2,c3),coverage,('BIST30','BIST50','BIST100')):c.metric(name,f'{found}/{total}')
try:market,reasons=get_market_score();market=clamp(market)
except Exception:market=50;reasons=[]
st.metric('Market Score',f'{market:.0f}/100');st.metric('Hedef Hisse Sayısı',portfolio_size(market))
if reasons:
    with st.expander('🌍 Market Score gerekçeleri'):
        for x in reasons:st.write(f'• {x}')
if st.button('🚀 TÜM EVRENİ TARA',type='primary',use_container_width=True):
    results=[];bar=st.progress(0);status=st.empty()
    for i,s in enumerate(symbols):
        status.write(f'🔎 **{s}** ({i+1}/{len(symbols)})')
        try:
            r=stock_result(s,market)
            if r:results.append(r)
        except Exception as e:print(f'[TARAMA HATASI] {s}: {e}')
        bar.progress((i+1)/len(symbols))
    bar.empty();status.empty()
    df=pd.DataFrame(results)
    if df.empty:st.error('Hiçbir hisse analiz edilemedi.');st.stop()
    rows=[]
    for sec,g in df.groupby('Sektör'):
        sc=sector_score(g);leader=g.sort_values('Genel Skor',ascending=False).iloc[0]
        rows.append({'Sektör':sec,'Hisse Sayısı':len(g),'Sektör Skoru':sc,'Durum':'🟢 Çok Güçlü' if sc>=80 else '🟢 Güçlü' if sc>=70 else '🟡 Pozitif' if sc>=60 else '🟠 Nötr' if sc>=50 else '🔴 Zayıf','Ort. Genel':round(g['Genel Skor'].mean(),1),'Ort. Teknik':round(g['Teknik'].mean(),1),'Ort. Temel':round(g['Temel'].mean(),1),'Ort. Momentum':round(g['Momentum'].mean(),1),'Ort. Trend':round(g['Trend'].mean(),1),'Güçlü Hisse':int((g['Genel Skor']>=65).sum()),'Sektör Lideri':leader.Hisse,'Lider Skoru':leader['Genel Skor']})
    sdf=pd.DataFrame(rows).sort_values('Sektör Skoru',ascending=False).reset_index(drop=True)
    st.subheader('📊 Günün Sektör Güç Haritası');st.dataframe(sdf,use_container_width=True,hide_index=True)
    st.subheader('🔥 Günün En Güçlü Sektörleri');st.dataframe(sdf.head(sector_count(market)),use_container_width=True,hide_index=True)
    strong=set(sdf.head(sector_count(market)).Sektör);st.subheader('9️⃣ Güçlü Sektörlerdeki Güçlü Hisseler');st.dataframe(df[df.Sektör.isin(strong)].sort_values(['Genel Skor','Momentum'],ascending=False).head(50),use_container_width=True,hide_index=True)
    p=build_portfolio(df,sdf,market);st.subheader('🔟 MODEL PORTFÖYÜ')
    if p.empty:st.warning('Model portföy oluşturulamadı.')
    else:
        st.success(f'🧠 Dinamik Model Portföy: **{len(p)} hisse** | Market Score: **{market:.1f}**')
        st.dataframe(p[['Sıra','Hisse','Sektör','Sektör Skoru','Genel Skor','Portföy Skoru','Ağırlık %','Karar','Risk','Düşüş']],use_container_width=True,hide_index=True)
        st.subheader('📌 Model Portföy Sektör Ağırlıkları');st.dataframe(p.groupby('Sektör')['Ağırlık %'].sum().sort_values(ascending=False).reset_index(),use_container_width=True,hide_index=True)
    st.subheader('⭐ Günün En Güçlü 15 Hissesi');st.dataframe(df.sort_values('Genel Skor',ascending=False).head(15),use_container_width=True,hide_index=True)
    st.subheader('🔴 Düşüş Sinyalleri');st.dataframe(df[df.Düşüş=='🔴 Düşüş Sinyali'].sort_values('Genel Skor',ascending=False).head(30),use_container_width=True,hide_index=True)
    st.download_button('📥 Tüm Sonuçları CSV indir',df.to_csv(index=False).encode('utf-8-sig'),'bist_ai_pro_dinamik_tarama.csv','text/csv',use_container_width=True)
    if not p.empty:st.download_button('📥 Model Portföyünü CSV indir',p.to_csv(index=False).encode('utf-8-sig'),'bist_ai_pro_model_portfoy.csv','text/csv',use_container_width=True)
