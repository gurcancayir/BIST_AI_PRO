import streamlit as st
import pandas as pd
import sqlite3
import yfinance as yf
from datetime import datetime

from modules.database import (
    import_transactions_from_excel,
    get_database_stats,
    get_transactions,
    get_stocks
)


st.set_page_config(
    page_title="Veritabanı",
    page_icon="🗄️",
    layout="wide"
)


st.title("🗄️ Veritabanı Yönetimi")

st.write(
    "Excel portföy işlemlerini SQLite veritabanına aktar."
)


# ==========================================================
# VERİTABANI DURUMU
# ==========================================================

st.subheader("📊 Veritabanı Durumu")

stats = get_database_stats()


col1, col2, col3, col4, col5 = st.columns(5)


with col1:
    st.metric(
        "Hisseler",
        stats["stocks"]
    )


with col2:
    st.metric(
        "İşlemler",
        stats["transactions"]
    )


with col3:
    st.metric(
        "Fiyat Kayıtları",
        stats["stock_prices"]
    )


with col4:
    st.metric(
        "Teknik Analiz",
        stats["technical_analysis"]
    )


with col5:
    st.metric(
        "Temel Analiz",
        stats["fundamentals"]
    )


st.divider()


# ==========================================================
# EXCEL YÜKLE
# ==========================================================

st.subheader("📥 Excel'den Veri Aktar")


uploaded_file = st.file_uploader(

    "Portföy Excel dosyanı seç",

    type=["xlsx", "xls"]

)


if uploaded_file is not None:

    st.success(
        "Excel dosyası seçildi."
    )


    try:

        excel = pd.ExcelFile(
            uploaded_file
        )


        st.write(
            "Bulunan sayfalar:"
        )


        st.write(
            excel.sheet_names
        )


        if st.button(
            "🚀 Excel'i Veritabanına Aktar",
            type="primary"
        ):


            with st.spinner(
                "Veriler aktarılıyor..."
            ):


                count = import_transactions_from_excel(
                    uploaded_file
                )


            st.success(

                f"{count} işlem veritabanına aktarıldı."

            )


            st.rerun()


    except Exception as e:

        st.error(
            f"Excel okunamadı: {e}"
        )


st.divider()


# ==========================================================
# HİSSELER
# ==========================================================

st.subheader("📋 Veritabanındaki Hisseler")


stocks = get_stocks()


if stocks.empty:

    st.info(
        "Henüz hisse kaydı bulunmuyor."
    )

else:

    st.dataframe(
        stocks,
        use_container_width=True,
        hide_index=True
    )


st.divider()


# ==========================================================
# İŞLEMLER
# ==========================================================

st.subheader("🧾 Veritabanındaki İşlemler")


transactions = get_transactions()

# ==========================================================
# ASTOR İŞLEM KONTROL
# ==========================================================

st.divider()

st.subheader("🔎 ASTOR İşlem Kontrolü")

conn = sqlite3.connect("borsa.db")

astor_check = pd.read_sql_query(
    """
    SELECT
        id,
        symbol,
        transaction_date,
        transaction_type,
        quantity,
        price,
        total
    FROM transactions
    WHERE symbol = 'ASTOR.IS'
    ORDER BY transaction_date, id
    """,
    conn
)

conn.close()


if astor_check.empty:

    st.error("ASTOR işlemi bulunamadı.")

else:

    # Sayısal alanları garantiye al
    astor_check["quantity"] = pd.to_numeric(
        astor_check["quantity"],
        errors="coerce"
    ).fillna(0)

    # İşlem türünü temizle
    astor_check["transaction_type"] = (
        astor_check["transaction_type"]
        .astype(str)
        .str.strip()
        .str.lower()
    )

    # ALIŞ
    alis_mask = astor_check[
        "transaction_type"
    ].isin([
        "alış",
        "alis",
        "al"
    ])

    # SATIŞ
    satis_mask = astor_check[
        "transaction_type"
    ].isin([
        "satış",
        "satis",
        "sat"
    ])

    toplam_alis = astor_check.loc[
        alis_mask,
        "quantity"
    ].sum()

    toplam_satis = astor_check.loc[
        satis_mask,
        "quantity"
    ].sum()

    net_adet = (
        toplam_alis
        - toplam_satis
    )

    # ======================================================
    # SONUÇLAR
    # ======================================================

    st.markdown("### 📊 ASTOR Net Adet Hesabı")

    st.write(
        f"**Toplam Alış:** {toplam_alis:.0f} lot"
    )

    st.write(
        f"**Toplam Satış:** {toplam_satis:.0f} lot"
    )

    st.write(
        f"**NET ADET:** {net_adet:.0f} lot"
    )

    st.write(
        f"**Toplam işlem:** {len(astor_check)} adet"
    )

    st.divider()

    # ======================================================
    # TÜM İŞLEMLER
    # ======================================================

    st.write("### 📋 ASTOR Tüm İşlem Geçmişi")

    st.dataframe(
        astor_check,
        use_container_width=True,
        hide_index=True
    )
if transactions.empty:

    st.info(
        "Henüz işlem kaydı bulunmuyor."
    )

else:

    st.dataframe(
        transactions,
        use_container_width=True,
        hide_index=True
    )

# ==========================================================
# STOCKS TABLOSUNU OTOMATİK TAMAMLAMA
# ==========================================================

SEKTOR_MAP = {

    "TUPRS.IS": "Enerji",
    "AKSEN.IS": "Enerji",
    "ENJSA.IS": "Enerji",
    "ODAS.IS": "Enerji",
    "YEOTK.IS": "Enerji",

    "ASELS.IS": "Savunma",
    "ASTOR.IS": "Savunma",
    "OTKAR.IS": "Savunma",
    "SDTTR.IS": "Savunma",
    "ALTNY.IS": "Savunma",

    "THYAO.IS": "Ulaştırma",
    "PGSUS.IS": "Ulaştırma",

    "BIMAS.IS": "Perakende",
    "MGROS.IS": "Perakende",
    "SOKM.IS": "Perakende",

    "FROTO.IS": "Otomotiv",
    "TOASO.IS": "Otomotiv",

    "AKBNK.IS": "Banka",
    "GARAN.IS": "Banka",

    "SISE.IS": "Sanayi",
    "EREGL.IS": "Sanayi",
    "KCHOL.IS": "Holding",

    "OYAKC.IS": "İnşaat",
    "CVKMD.IS": "Madencilik",
    "KARCL.IS": "Sanayi",
    "MASFN.IS": "Sanayi",
    "METEN.IS": "Sanayi",

}


def update_stocks_from_transactions():

    DB_PATH = "borsa.db"

    conn = sqlite3.connect(DB_PATH)

    cursor = conn.cursor()

    # ------------------------------------------------------
    # TRANSACTIONS TABLOSUNDAN TÜM HİSSELER
    # ------------------------------------------------------

    cursor.execute(
        """
        SELECT DISTINCT symbol
        FROM transactions
        WHERE symbol IS NOT NULL
        AND TRIM(symbol) <> ''
        """
    )

    symbols = [
        row[0]
        for row in cursor.fetchall()
    ]

    if not symbols:

        conn.close()

        return 0, 0, []


    added = 0
    updated = 0
    errors = []


    # ------------------------------------------------------
    # HER HİSSE
    # ------------------------------------------------------

    for symbol in symbols:

        try:

            symbol = str(symbol).strip().upper()

            if not symbol.endswith(".IS"):

                symbol = symbol + ".IS"


            print(
                f"[STOCK UPDATE] {symbol}"
            )


            ticker = yf.Ticker(symbol)

            # --------------------------------------------------
            # YAHOO BİLGİLERİ
            # --------------------------------------------------

            try:

                info = ticker.info or {}

            except Exception:

                info = {}


            company = info.get(
                "longName"
            )

            if not company:

                company = info.get(
                    "shortName"
                )

            if not company:

                company = symbol.replace(
                    ".IS",
                    ""
                )


            yahoo_sector = info.get(
                "sector"
            )


            yahoo_industry = info.get(
                "industry"
            )


            market_cap = info.get(
                "marketCap"
            )

            if market_cap is None:

                market_cap = 0


            currency = info.get(
                "currency"
            )

            if not currency:

                currency = "TRY"


            # --------------------------------------------------
            # SEKTÖR
            # Önce bizim özel haritamız
            # --------------------------------------------------

            sector = SEKTOR_MAP.get(
                symbol,
                yahoo_sector or ""
            )


            if not sector:

                sector = "-"


            if not yahoo_industry:

                yahoo_industry = "-"


            now = datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )


            # --------------------------------------------------
            # HİSSE VAR MI?
            # --------------------------------------------------

            cursor.execute(
                """
                SELECT id
                FROM stocks
                WHERE symbol = ?
                """,
                (symbol,)
            )

            existing = cursor.fetchone()


            # --------------------------------------------------
            # VARSA GÜNCELLE
            # --------------------------------------------------

            if existing:

                cursor.execute(
                    """
                    UPDATE stocks

                    SET
                        company = ?,
                        sector = ?,
                        industry = ?,
                        market_cap = ?,
                        currency = ?,
                        updated_at = ?

                    WHERE symbol = ?
                    """,
                    (
                        company,
                        sector,
                        yahoo_industry,
                        market_cap,
                        currency,
                        now,
                        symbol
                    )
                )

                updated += 1


            # --------------------------------------------------
            # YOKSA EKLE
            # --------------------------------------------------

            else:

                cursor.execute(
                    """
                    INSERT INTO stocks
                    (
                        symbol,
                        company,
                        sector,
                        industry,
                        market_cap,
                        currency,
                        created_at,
                        updated_at
                    )

                    VALUES
                    (
                        ?, ?, ?, ?, ?, ?, ?, ?
                    )
                    """,
                    (
                        symbol,
                        company,
                        sector,
                        yahoo_industry,
                        market_cap,
                        currency,
                        now,
                        now
                    )
                )

                added += 1


            conn.commit()


        except Exception as e:

            errors.append(
                f"{symbol}: {str(e)}"
            )

            print(
                f"[STOCK ERROR] {symbol}: {e}"
            )


    conn.close()

    return added, updated, errors


# ==========================================================
# STREAMLIT BUTONU
# ==========================================================

st.divider()

st.subheader(
    "🔄 Hisse Bilgilerini Güncelle"
)

st.write(
    "Transactions tablosundaki hisseler "
    "stocks tablosuna aktarılır ve Yahoo Finance "
    "üzerinden şirket bilgileri güncellenir."
)


if st.button(
    "🚀 Hisse Bilgilerini Güncelle",
    width="stretch"
):

    with st.spinner(
        "Hisse bilgileri güncelleniyor..."
    ):

        added, updated, errors = (
            update_stocks_from_transactions()
        )


    st.success(
        f"Tamamlandı. "
        f"Yeni eklenen: {added} | "
        f"Güncellenen: {updated}"
    )


    if errors:

        st.warning(
            f"{len(errors)} hissede bilgi alınamadı."
        )

        for error in errors:

            st.write(
                f"⚠️ {error}"
            )

    else:

        st.success(
            "Tüm hisseler başarıyla işlendi."
        )

    st.rerun()