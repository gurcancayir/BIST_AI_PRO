# Borsa Karar Destek Otomasyonu

Bu proje; borsa islemlerini kaydetmek, portfoy durumunu izlemek, kar/zarar hesaplamak ve basit karar destek uyarilari uretmek icin hazirlanmis ilk surum iskeletidir.

## Kurulum

Python kurulduktan sonra PowerShell'de bu klasore gel:

```powershell
cd C:\Users\gurca\Documents\Codex\2026-05-01\borsada-i-lemlerimi-tuttu-um-bir
```

Sanal ortam olustur:

```powershell
py -m venv .venv
```

Sanal ortami ac:

```powershell
.\.venv\Scripts\Activate.ps1
```

Gerekli paketleri kur:

```powershell
py -m pip install -r requirements.txt
```

Programi calistir:

```powershell
streamlit run app.py
```

## Ilk Surum Ozellikleri

- Alis, satis ve temettu islemi ekleme
- SQLite veritabani ile lokal kayit
- Portfoy ozeti
- Gerceklesen kar/zarar
- Acik pozisyon kar/zarar hesabi icin guncel fiyat girisi
- Strateji bazli performans raporu
- Basit karar destek uyarilari
- CSV ice aktarma

## CSV Kolonlari

CSV dosyan su kolonlari icerebilir:

```text
date,symbol,type,quantity,price,commission,tax,currency,strategy,reason,target_price,stop_loss,notes
```

Ornek `type` degerleri:

```text
buy
sell
dividend
fee
```
