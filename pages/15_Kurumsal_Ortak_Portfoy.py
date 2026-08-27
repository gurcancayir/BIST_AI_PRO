# ============================================================
# BIST AI PRO
# 15_Kurumsal_Ortak_Portfoy.py
#
# KURUMSAL ORTAK PORTFÖY V2
# ============================================================
#
# AMAÇ
# ------------------------------------------------------------
# Açık erişilebilen yatırım kuruluşlarının:
#
#   - Model portföylerini
#   - Aktif AL önerilerini
#   - Hedef fiyatlarını
#   - Getiri potansiyellerini
#   - Rapor / güncelleme tarihlerini
#
# toplamaya çalışır.
#
# Ardından kurumların ortak önerilerinden bağımsız bir:
#
#       KURUMSAL ORTAK PORTFÖY
#
# oluşturur.
#
# ÖNEMLİ
# ------------------------------------------------------------
# Bu modül:
#
#   ❌ BIST AI PRO skoruna puan EKLEMEZ
#   ❌ teknik skoru değiştirmez
#   ❌ temel skoru değiştirmez
#   ❌ Günlük Trade skorunu değiştirmez
#
# Tamamen bağımsız bir kurumsal konsensüs motorudur.
#
# ============================================================


from __future__ import annotations


# ============================================================
# IMPORTLAR
# ============================================================

import re
import unicodedata
from datetime import date, datetime
from io import StringIO
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import requests
import streamlit as st

from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


# ============================================================
# SAYFA AYARLARI
# ============================================================

st.set_page_config(
    page_title="BIST AI PRO - Kurumsal Ortak Portföy",
    page_icon="🏦",
    layout="wide",
)

st.title("🏦 Kurumsal Ortak Portföy")

st.caption(
    "Yatırım kuruluşlarının açık erişimli güncel önerilerini "
    "karşılaştırır ve ortak bir portföy oluşturur. "
    "BIST AI PRO'nun kendi skor sistemine müdahale etmez."
)


# ============================================================
# SABİTLER
# ============================================================

TIMEOUT = 25


SOURCE_URLS = {

    # --------------------------------------------------------
    # İŞ YATIRIM
    # --------------------------------------------------------
    "İş Yatırım": (
        "https://www.isyatirim.com.tr/"
        "tr-tr/analiz/hisse/Sayfalar/takip-listesi.aspx"
    ),

    # --------------------------------------------------------
    # GEDİK
    # --------------------------------------------------------
    "Gedik Yatırım": (
        "https://gedik.com/"
        "analiz/model-portfoy/hisse-model-portfoy"
    ),

    "Gedik Arşiv": (
        "https://gedik.com/"
        "yurt-ici-piyasa-bultenleri/model-portfoy"
    ),

    # --------------------------------------------------------
    # DENİZ
    # --------------------------------------------------------
    "Deniz Yatırım": (
        "https://www.denizyatirim.com/"
        "ModelPortfoyPerformans"
    ),

    "Deniz Arşiv": (
        "https://www.denizyatirim.com/"
        "ModelPortfoy"
    ),

    # --------------------------------------------------------
    # YATIRIM FİNANSMAN
    # --------------------------------------------------------
    "Yatırım Finansman": (
        "https://www.yf.com.tr/"
        "analizler/pay-piyasasi/model-portfoy"
    ),
}


STANDARD_COLUMNS = [
    "institution",
    "symbol",
    "recommendation",
    "target_price",
    "potential",
    "report_date",
    "source_type",
    "source_url",
]


# ============================================================
# SESSION
# ============================================================

def create_session() -> requests.Session:

    session = requests.Session()

    retry = Retry(
        total=3,
        connect=3,
        read=3,
        status=3,
        backoff_factor=0.8,
        status_forcelist=[
            429,
            500,
            502,
            503,
            504,
        ],
        allowed_methods=["GET"],
    )

    adapter = HTTPAdapter(
        max_retries=retry
    )

    session.mount(
        "https://",
        adapter,
    )

    session.mount(
        "http://",
        adapter,
    )

    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 "
                "(Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/131.0.0.0 "
                "Safari/537.36"
            ),

            "Accept": (
                "text/html,"
                "application/xhtml+xml,"
                "application/xml;q=0.9,"
                "image/avif,"
                "image/webp,"
                "*/*;q=0.8"
            ),

            "Accept-Language": (
                "tr-TR,tr;q=0.9,"
                "en-US;q=0.8,"
                "en;q=0.7"
            ),

            "Cache-Control": "no-cache",
            "Pragma": "no-cache",

            "Connection": "keep-alive",
        }
    )

    return session


# ============================================================
# HTTP
# ============================================================

def get_html(
    url: str,
) -> str:

    session = create_session()

    response = session.get(
        url,
        timeout=TIMEOUT,
        allow_redirects=True,
    )

    response.raise_for_status()

    if not response.encoding:

        response.encoding = (
            response.apparent_encoding
            or "utf-8"
        )

    return response.text


# ============================================================
# METİN NORMALİZASYONU
# ============================================================

def clean_text(
    value: Any,
) -> str:

    if value is None:
        return ""

    text = str(value)

    text = text.replace(
        "\xa0",
        " ",
    )

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip()


def ascii_text(
    value: Any,
) -> str:

    text = clean_text(
        value
    ).lower()

    replacements = {
        "ı": "i",
        "ş": "s",
        "ğ": "g",
        "ü": "u",
        "ö": "o",
        "ç": "c",
    }

    for old, new in replacements.items():

        text = text.replace(
            old,
            new,
        )

    text = unicodedata.normalize(
        "NFKD",
        text,
    )

    text = "".join(
        c
        for c in text
        if not unicodedata.combining(c)
    )

    return text


# ============================================================
# HİSSE KODU
# ============================================================

def normalize_symbol(
    value: Any,
) -> str:

    text = clean_text(
        value
    ).upper()

    text = (
        text
        .replace(".IS", "")
        .replace("BIST:", "")
        .replace("TL", "")
        .replace("₺", "")
        .strip()
    )

    # --------------------------------------------------------
    # Doğrudan ticker
    # --------------------------------------------------------

    match = re.search(
        r"\b[A-Z]{3,6}\b",
        text,
    )

    if match:

        symbol = (
            match.group(0)
            .upper()
            .strip()
        )

        return symbol

    return ""


# ============================================================
# SAYI PARSER
# ============================================================

def parse_number(
    value: Any,
) -> float:

    if value is None:
        return np.nan

    text = clean_text(
        value
    )

    if not text:
        return np.nan

    text = (
        text
        .replace("%", "")
        .replace("TL", "")
        .replace("₺", "")
        .replace("TRY", "")
        .replace(" ", "")
    )

    # --------------------------------------------------------
    # Türkçe:
    #
    # 1.234,56
    #
    # --------------------------------------------------------

    if "," in text:

        text = (
            text
            .replace(".", "")
            .replace(",", ".")
        )

    else:

        # 73.30 gibi değerleri bozma
        if text.count(".") > 1:

            text = text.replace(
                ".",
                "",
            )

    try:

        return float(
            text
        )

    except Exception:

        match = re.search(
            r"-?\d+(?:[.,]\d+)?",
            text,
        )

        if not match:
            return np.nan

        candidate = (
            match
            .group(0)
            .replace(",", ".")
        )

        try:
            return float(candidate)

        except Exception:
            return np.nan


# ============================================================
# TARİH PARSER
# ============================================================

TURKISH_MONTHS = {

    "ocak": 1,

    "subat": 2,
    "şubat": 2,

    "mart": 3,

    "nisan": 4,

    "mayis": 5,
    "mayıs": 5,

    "haziran": 6,

    "temmuz": 7,

    "agustos": 8,
    "ağustos": 8,

    "eylul": 9,
    "eylül": 9,

    "ekim": 10,

    "kasim": 11,
    "kasım": 11,

    "aralik": 12,
    "aralık": 12,
}


def parse_date(
    value: Any,
) -> Optional[date]:

    text = clean_text(
        value
    )

    if not text:
        return None

    # --------------------------------------------------------
    # DD.MM.YYYY
    # DD/MM/YYYY
    # DD-MM-YYYY
    # --------------------------------------------------------

    match = re.search(
        r"\b"
        r"(\d{1,2})"
        r"[./-]"
        r"(\d{1,2})"
        r"[./-]"
        r"(\d{4})"
        r"\b",
        text,
    )

    if match:

        try:

            return date(
                int(match.group(3)),
                int(match.group(2)),
                int(match.group(1)),
            )

        except Exception:
            pass

    # --------------------------------------------------------
    # 24 Ağustos 2026
    # --------------------------------------------------------

    lower = text.lower()

    for month_name, month_number in (
        TURKISH_MONTHS.items()
    ):

        pattern = (
            rf"\b"
            rf"(\d{{1,2}})"
            rf"\s+"
            rf"{re.escape(month_name)}"
            rf"\s+"
            rf"(\d{{4}})"
            rf"\b"
        )

        match = re.search(
            pattern,
            lower,
        )

        if match:

            try:

                return date(
                    int(match.group(2)),
                    month_number,
                    int(match.group(1)),
                )

            except Exception:
                pass

    return None


# ============================================================
# SAYFADAKİ EN YENİ TARİH
# ============================================================

def find_latest_date(
    text: str,
) -> Optional[date]:

    dates: List[date] = []

    # --------------------------------------------------------
    # Numeric
    # --------------------------------------------------------

    for value in re.findall(
        r"\b"
        r"\d{1,2}"
        r"[./-]"
        r"\d{1,2}"
        r"[./-]"
        r"\d{4}"
        r"\b",
        text,
    ):

        parsed = parse_date(
            value
        )

        if parsed:
            dates.append(parsed)

    # --------------------------------------------------------
    # Türkçe ay
    # --------------------------------------------------------

    month_regex = "|".join(
        re.escape(x)
        for x in TURKISH_MONTHS.keys()
    )

    pattern = (
        rf"\b"
        rf"\d{{1,2}}"
        rf"\s+"
        rf"(?:{month_regex})"
        rf"\s+"
        rf"\d{{4}}"
        rf"\b"
    )

    for value in re.findall(
        pattern,
        text,
        flags=re.I,
    ):

        parsed = parse_date(
            value
        )

        if parsed:
            dates.append(parsed)

    if not dates:
        return None

    today = date.today()

    # gelecekteki tarihleri rapor tarihi sayma
    dates = [
        d
        for d in dates
        if d <= today
    ]

    if not dates:
        return None

    return max(
        dates
    )


# ============================================================
# TARİH YAŞI
# ============================================================

def age_days(
    report_date: Optional[date],
) -> Optional[int]:

    if report_date is None:
        return None

    return (
        date.today()
        - report_date
    ).days


def report_is_fresh(
    report_date: Optional[date],
    max_age: int,
) -> bool:

    age = age_days(
        report_date
    )

    if age is None:
        return False

    return (
        0 <= age <= max_age
    )


# ============================================================
# DATAFRAME KOLONLARI
# ============================================================

def flatten_columns(
    df: pd.DataFrame,
) -> pd.DataFrame:

    df = df.copy()

    if isinstance(
        df.columns,
        pd.MultiIndex,
    ):

        columns = []

        for column in df.columns:

            parts = [
                clean_text(x)
                for x in column
                if clean_text(x).lower()
                != "nan"
            ]

            columns.append(
                " ".join(parts)
            )

        df.columns = columns

    else:

        df.columns = [
            clean_text(x)
            for x in df.columns
        ]

    return df


# ============================================================
# KOLON BUL
# ============================================================

def find_column(
    df: pd.DataFrame,
    include: List[str],
    exclude: Optional[List[str]] = None,
) -> Optional[str]:

    if exclude is None:
        exclude = []

    for column in df.columns:

        normalized = ascii_text(
            column
        )

        include_ok = all(
            ascii_text(term)
            in normalized
            for term in include
        )

        exclude_ok = not any(
            ascii_text(term)
            in normalized
            for term in exclude
        )

        if (
            include_ok
            and exclude_ok
        ):
            return column

    return None


# ============================================================
# BOŞ DF
# ============================================================

def empty_df() -> pd.DataFrame:

    return pd.DataFrame(
        columns=STANDARD_COLUMNS
    )


# ============================================================
# KAYNAK SONUÇ METASI
# ============================================================

def error_meta(
    institution: str,
    error: Exception,
    mode: str = "report",
) -> Dict[str, Any]:

    return {

        "institution": institution,

        "report_date": None,

        "mode": mode,

        "status": "error",

        "error": (
            f"{type(error).__name__}: "
            f"{error}"
        ),
    }


# ============================================================
# HTML TABLE OKUMA
# ============================================================

def get_tables(
    html: str,
) -> List[pd.DataFrame]:

    try:

        tables = pd.read_html(
            StringIO(html)
        )

    except Exception:

        return []

    output = []

    for table in tables:

        try:

            table = flatten_columns(
                table
            )

            output.append(
                table
            )

        except Exception:
            continue

    return output


# ============================================================
# İŞ YATIRIM
# ============================================================

@st.cache_data(
    ttl=1800,
    show_spinner=False,
)
def fetch_is_yatirim() -> Tuple[
    pd.DataFrame,
    Dict[str, Any],
]:

    institution = "İş Yatırım"

    url = SOURCE_URLS[
        institution
    ]

    try:

        html = get_html(
            url
        )

        tables = get_tables(
            html
        )

        if not tables:

            raise ValueError(
                "Sayfada HTML tablo bulunamadı."
            )

        selected = None

        # ----------------------------------------------------
        # İdeal tabloyu bul
        # ----------------------------------------------------

        for table in tables:

            text = ascii_text(
                " ".join(
                    str(x)
                    for x in table.columns
                )
            )

            if (
                "kod" in text
                and "oneri" in text
                and "hedef" in text
            ):

                selected = table.copy()
                break

        if selected is None:

            raise ValueError(
                "Takip listesi tablosu bulunamadı."
            )

        symbol_col = find_column(
            selected,
            ["kod"],
        )

        recommendation_col = find_column(
            selected,
            ["öneri"],
            ["tarih"],
        )

        target_col = find_column(
            selected,
            ["hedef"],
        )

        potential_col = (
            find_column(
                selected,
                ["getiri"],
                ["tarih"],
            )
            or
            find_column(
                selected,
                ["potansiyel"],
            )
        )

        recommendation_date_col = (
            find_column(
                selected,
                ["öneri", "tarih"],
            )
        )

        if symbol_col is None:

            raise ValueError(
                "Hisse kodu kolonu bulunamadı."
            )

        if recommendation_col is None:

            raise ValueError(
                "Öneri kolonu bulunamadı."
            )

        rows = []

        for _, row in selected.iterrows():

            symbol = normalize_symbol(
                row.get(symbol_col)
            )

            recommendation = (
                clean_text(
                    row.get(
                        recommendation_col
                    )
                )
                .upper()
                .strip()
            )

            recommendation_ascii = (
                ascii_text(
                    recommendation
                )
                .upper()
            )

            # sadece AL önerileri
            if recommendation_ascii != "AL":
                continue

            if not re.fullmatch(
                r"[A-Z]{3,6}",
                symbol,
            ):
                continue

            target_price = (
                parse_number(
                    row.get(target_col)
                )
                if target_col
                else np.nan
            )

            potential = (
                parse_number(
                    row.get(potential_col)
                )
                if potential_col
                else np.nan
            )

            recommendation_date = None

            if recommendation_date_col:

                recommendation_date = (
                    parse_date(
                        row.get(
                            recommendation_date_col
                        )
                    )
                )

            rows.append(
                {
                    "institution":
                        institution,

                    "symbol":
                        symbol,

                    "recommendation":
                        "AL",

                    "target_price":
                        target_price,

                    "potential":
                        potential,

                    # ------------------------------------------------
                    # Bu aktif bir takip listesidir.
                    # Dolayısıyla sayfanın bugün aktif olması
                    # güncel kaynak kabul edilir.
                    # ------------------------------------------------
                    "report_date":
                        date.today(),

                    "source_type":
                        "Aktif AL listesi",

                    "source_url":
                        url,

                    "recommendation_date":
                        recommendation_date,
                }
            )

        df = pd.DataFrame(
            rows
        )

        if df.empty:

            raise ValueError(
                "Tablo bulundu fakat aktif AL hissesi "
                "ayrıştırılamadı."
            )

        return (
            df,
            {
                "institution":
                    institution,

                "report_date":
                    date.today(),

                "mode":
                    "live",

                "status":
                    "ok",

                "error":
                    "",
            },
        )

    except Exception as exc:

        return (
            empty_df(),
            error_meta(
                institution,
                exc,
                "live",
            ),
        )


# ============================================================
# GEDİK YATIRIM
# ============================================================

@st.cache_data(
    ttl=1800,
    show_spinner=False,
)
def fetch_gedik() -> Tuple[
    pd.DataFrame,
    Dict[str, Any],
]:

    institution = "Gedik Yatırım"

    url = SOURCE_URLS[
        institution
    ]

    archive_url = SOURCE_URLS[
        "Gedik Arşiv"
    ]

    try:

        # ----------------------------------------------------
        # Tarih
        # ----------------------------------------------------

        report_date = None

        try:

            archive_html = get_html(
                archive_url
            )

            archive_text = (
                BeautifulSoup(
                    archive_html,
                    "html.parser",
                )
                .get_text(
                    " ",
                    strip=True,
                )
            )

            report_date = find_latest_date(
                archive_text
            )

        except Exception:
            pass

        # ----------------------------------------------------
        # Portföy
        # ----------------------------------------------------

        html = get_html(
            url
        )

        page_text = (
            BeautifulSoup(
                html,
                "html.parser",
            )
            .get_text(
                " ",
                strip=True,
            )
        )

        if report_date is None:

            report_date = find_latest_date(
                page_text
            )

        tables = get_tables(
            html
        )

        selected = None

        for table in tables:

            text = ascii_text(
                " ".join(
                    str(x)
                    for x in table.columns
                )
            )

            if (
                "hisse" in text
                and (
                    "hedef" in text
                    or
                    "potansiyel" in text
                )
            ):

                selected = table.copy()
                break

        if selected is None:

            raise ValueError(
                "Model portföy tablosu bulunamadı."
            )

        symbol_col = (
            find_column(
                selected,
                ["hisse"],
            )
            or
            find_column(
                selected,
                ["kod"],
            )
        )

        target_col = (
            find_column(
                selected,
                ["hedef"],
            )
        )

        potential_col = (
            find_column(
                selected,
                ["potansiyel"],
            )
            or
            find_column(
                selected,
                ["getiri"],
            )
        )

        if symbol_col is None:

            raise ValueError(
                "Hisse kodu kolonu bulunamadı."
            )

        rows = []

        for _, row in selected.iterrows():

            symbol = normalize_symbol(
                row.get(
                    symbol_col
                )
            )

            if not re.fullmatch(
                r"[A-Z]{3,6}",
                symbol,
            ):
                continue

            rows.append(
                {
                    "institution":
                        institution,

                    "symbol":
                        symbol,

                    "recommendation":
                        "MODEL PORTFÖY",

                    "target_price":
                        (
                            parse_number(
                                row.get(
                                    target_col
                                )
                            )
                            if target_col
                            else np.nan
                        ),

                    "potential":
                        (
                            parse_number(
                                row.get(
                                    potential_col
                                )
                            )
                            if potential_col
                            else np.nan
                        ),

                    "report_date":
                        report_date,

                    "source_type":
                        "Model Portföy",

                    "source_url":
                        url,
                }
            )

        df = pd.DataFrame(
            rows
        )

        if df.empty:

            raise ValueError(
                "Model portföy hisseleri ayrıştırılamadı."
            )

        return (
            df,
            {
                "institution":
                    institution,

                "report_date":
                    report_date,

                "mode":
                    "report",

                "status":
                    "ok",

                "error":
                    "",
            },
        )

    except Exception as exc:

        return (
            empty_df(),
            error_meta(
                institution,
                exc,
            ),
        )


# ============================================================
# DENİZ YATIRIM
# ============================================================

@st.cache_data(
    ttl=1800,
    show_spinner=False,
)
def fetch_deniz() -> Tuple[
    pd.DataFrame,
    Dict[str, Any],
]:

    institution = "Deniz Yatırım"

    url = SOURCE_URLS[
        institution
    ]

    archive_url = SOURCE_URLS[
        "Deniz Arşiv"
    ]

    try:

        report_date = None

        # ----------------------------------------------------
        # Arşiv tarih kontrolü
        # ----------------------------------------------------

        try:

            archive_html = get_html(
                archive_url
            )

            archive_text = (
                BeautifulSoup(
                    archive_html,
                    "html.parser",
                )
                .get_text(
                    " ",
                    strip=True,
                )
            )

            report_date = find_latest_date(
                archive_text
            )

        except Exception:
            pass

        # ----------------------------------------------------
        # Portföy sayfası
        # ----------------------------------------------------

        html = get_html(
            url
        )

        page_text = (
            BeautifulSoup(
                html,
                "html.parser",
            )
            .get_text(
                " ",
                strip=True,
            )
        )

        if report_date is None:

            report_date = find_latest_date(
                page_text
            )

        tables = get_tables(
            html
        )

        selected = None

        for table in tables:

            text = ascii_text(
                " ".join(
                    str(x)
                    for x in table.columns
                )
            )

            if (
                "hisse" in text
                and (
                    "hedef" in text
                    or
                    "potansiyel" in text
                )
            ):

                selected = table.copy()
                break

        if selected is None:

            raise ValueError(
                "Model portföy tablosu bulunamadı."
            )

        symbol_col = (
            find_column(
                selected,
                ["hisse"],
            )
            or
            find_column(
                selected,
                ["kod"],
            )
        )

        target_col = (
            find_column(
                selected,
                ["hedef"],
            )
        )

        potential_col = (
            find_column(
                selected,
                ["potansiyel"],
            )
            or
            find_column(
                selected,
                ["getiri"],
            )
        )

        if symbol_col is None:

            raise ValueError(
                "Hisse kodu kolonu bulunamadı."
            )

        rows = []

        for _, row in selected.iterrows():

            symbol = normalize_symbol(
                row.get(
                    symbol_col
                )
            )

            if not re.fullmatch(
                r"[A-Z]{3,6}",
                symbol,
            ):
                continue

            rows.append(
                {
                    "institution":
                        institution,

                    "symbol":
                        symbol,

                    "recommendation":
                        "MODEL PORTFÖY",

                    "target_price":
                        (
                            parse_number(
                                row.get(
                                    target_col
                                )
                            )
                            if target_col
                            else np.nan
                        ),

                    "potential":
                        (
                            parse_number(
                                row.get(
                                    potential_col
                                )
                            )
                            if potential_col
                            else np.nan
                        ),

                    "report_date":
                        report_date,

                    "source_type":
                        "Model Portföy",

                    "source_url":
                        url,
                }
            )

        df = pd.DataFrame(
            rows
        )

        if df.empty:

            raise ValueError(
                "Model portföy hisseleri ayrıştırılamadı."
            )

        return (
            df,
            {
                "institution":
                    institution,

                "report_date":
                    report_date,

                "mode":
                    "report",

                "status":
                    "ok",

                "error":
                    "",
            },
        )

    except Exception as exc:

        return (
            empty_df(),
            error_meta(
                institution,
                exc,
            ),
        )


# ============================================================
# YATIRIM FİNANSMAN
# ============================================================

@st.cache_data(
    ttl=1800,
    show_spinner=False,
)
def fetch_yatirim_finansman() -> Tuple[
    pd.DataFrame,
    Dict[str, Any],
]:

    institution = "Yatırım Finansman"

    url = SOURCE_URLS[
        institution
    ]

    try:

        html = get_html(
            url
        )

        soup = BeautifulSoup(
            html,
            "html.parser",
        )

        page_text = soup.get_text(
            " ",
            strip=True,
        )

        report_date = find_latest_date(
            page_text
        )

        tables = get_tables(
            html
        )

        selected = None

        # ----------------------------------------------------
        # İlk olarak başlıklardan yakala
        # ----------------------------------------------------

        for table in tables:

            text = ascii_text(
                " ".join(
                    str(x)
                    for x in table.columns
                )
            )

            if (
                (
                    "hisse" in text
                    or
                    "kod" in text
                )
                and
                (
                    "hedef" in text
                    or
                    "potansiyel" in text
                    or
                    "getiri" in text
                )
            ):

                selected = table.copy()
                break

        # ----------------------------------------------------
        # Başlık iyi değilse içerikten ara
        # ----------------------------------------------------

        if selected is None:

            for table in tables:

                whole_text = ascii_text(
                    table.to_string()
                )

                if (
                    "hedef" in whole_text
                    and
                    len(table) >= 3
                ):

                    selected = table.copy()
                    break

        if selected is None:

            raise ValueError(
                "Model portföy tablosu bulunamadı."
            )

        symbol_col = (
            find_column(
                selected,
                ["hisse"],
            )
            or
            find_column(
                selected,
                ["kod"],
            )
        )

        target_col = (
            find_column(
                selected,
                ["hedef"],
            )
        )

        potential_col = (
            find_column(
                selected,
                ["potansiyel"],
            )
            or
            find_column(
                selected,
                ["getiri"],
            )
        )

        # ----------------------------------------------------
        # Kolon başlığı yakalanamadıysa
        # ilk kolonu hisse kabul et.
        # ----------------------------------------------------

        if (
            symbol_col is None
            and len(selected.columns) > 0
        ):

            symbol_col = (
                selected.columns[0]
            )

        rows = []

        for _, row in selected.iterrows():

            symbol = normalize_symbol(
                row.get(
                    symbol_col
                )
            )

            if not re.fullmatch(
                r"[A-Z]{3,6}",
                symbol,
            ):
                continue

            rows.append(
                {
                    "institution":
                        institution,

                    "symbol":
                        symbol,

                    "recommendation":
                        "MODEL PORTFÖY",

                    "target_price":
                        (
                            parse_number(
                                row.get(
                                    target_col
                                )
                            )
                            if target_col
                            else np.nan
                        ),

                    "potential":
                        (
                            parse_number(
                                row.get(
                                    potential_col
                                )
                            )
                            if potential_col
                            else np.nan
                        ),

                    "report_date":
                        report_date,

                    "source_type":
                        "Model Portföy",

                    "source_url":
                        url,
                }
            )

        df = pd.DataFrame(
            rows
        )

        if df.empty:

            raise ValueError(
                "Model portföy hisseleri ayrıştırılamadı."
            )

        return (
            df,
            {
                "institution":
                    institution,

                "report_date":
                    report_date,

                "mode":
                    "report",

                "status":
                    "ok",

                "error":
                    "",
            },
        )

    except Exception as exc:

        return (
            empty_df(),
            error_meta(
                institution,
                exc,
            ),
        )


# ============================================================
# TÜM KAYNAKLARI ÇALIŞTIR
# ============================================================

def load_sources():

    source_functions = [

        fetch_is_yatirim,

        fetch_gedik,

        fetch_deniz,

        fetch_yatirim_finansman,
    ]

    results = []

    for func in source_functions:

        try:

            df, meta = func()

        except Exception as exc:

            df = empty_df()

            meta = {
                "institution":
                    func.__name__,

                "report_date":
                    None,

                "mode":
                    "unknown",

                "status":
                    "error",

                "error":
                    str(exc),
            }

        results.append(
            (
                df,
                meta,
            )
        )

    return results


# ============================================================
# PORTFÖY AĞIRLIK HESABI
# ============================================================

def calculate_portfolio_weights(
    df: pd.DataFrame,
    max_weight: float = 20.0,
) -> pd.DataFrame:

    result = df.copy()

    if result.empty:
        return result

    # ========================================================
    # BURASI BIST AI PRO SKORU DEĞİLDİR.
    #
    # Sadece portföy oranı hesabıdır.
    #
    # Ana belirleyici:
    #
    #       kurum sayısı
    #
    # İkincil:
    #
    #       ortalama potansiyel
    #
    # ========================================================

    result[
        "potential_weight_value"
    ] = (
        pd.to_numeric(
            result[
                "avg_potential"
            ],
            errors="coerce",
        )
        .fillna(0)
        .clip(
            lower=0,
            upper=100,
        )
    )

    # --------------------------------------------------------
    # Kurum ortaklığı ana ağırlık
    # --------------------------------------------------------

    result[
        "institution_factor"
    ] = result[
        "institution_count"
    ].astype(float)

    # --------------------------------------------------------
    # Hedef potansiyeli sadece hafif etki ediyor
    #
    # %0  → x1.00
    # %20 → x1.10
    # %50 → x1.25
    # %100→ x1.50
    # --------------------------------------------------------

    result[
        "potential_factor"
    ] = (
        1
        +
        result[
            "potential_weight_value"
        ]
        / 200
    )

    result[
        "allocation_factor"
    ] = (
        result[
            "institution_factor"
        ]
        *
        result[
            "potential_factor"
        ]
    )

    factor_sum = (
        result[
            "allocation_factor"
        ]
        .sum()
    )

    if factor_sum <= 0:

        result[
            "weight"
        ] = (
            100
            /
            len(result)
        )

    else:

        result[
            "weight"
        ] = (
            result[
                "allocation_factor"
            ]
            /
            factor_sum
            *
            100
        )

    # ========================================================
    # TEK HİSSE TAVANI
    # ========================================================

    max_weight = float(
        max_weight
    )

    # birkaç iterasyonda fazlayı dağıt
    for _ in range(50):

        over_mask = (
            result[
                "weight"
            ]
            >
            max_weight
            + 0.0001
        )

        if not over_mask.any():
            break

        excess = (
            result.loc[
                over_mask,
                "weight",
            ]
            -
            max_weight
        ).sum()

        result.loc[
            over_mask,
            "weight",
        ] = max_weight

        under_mask = (
            result[
                "weight"
            ]
            <
            max_weight
            - 0.0001
        )

        if not under_mask.any():
            break

        under_factor_sum = (
            result.loc[
                under_mask,
                "allocation_factor",
            ]
            .sum()
        )

        if under_factor_sum <= 0:
            break

        result.loc[
            under_mask,
            "weight",
        ] += (
            result.loc[
                under_mask,
                "allocation_factor",
            ]
            /
            under_factor_sum
            *
            excess
        )

    # --------------------------------------------------------
    # Son normalize
    # --------------------------------------------------------

    total = (
        result[
            "weight"
        ]
        .sum()
    )

    if total > 0:

        result[
            "weight"
        ] = (
            result[
                "weight"
            ]
            /
            total
            *
            100
        )

    result[
        "weight"
    ] = (
        result[
            "weight"
        ]
        .round(2)
    )

    return result


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.header(
    "⚙️ Portföy Ayarları"
)


max_report_age = st.sidebar.slider(
    "Maksimum rapor yaşı",
    min_value=1,
    max_value=60,
    value=14,
    step=1,
    help=(
        "Bu süreden daha eski tarihli "
        "model portföyler ortak hesaba alınmaz."
    ),
)


min_institution_count = (
    st.sidebar.slider(
        "Minimum ortak kurum",
        min_value=1,
        max_value=4,
        value=2,
        step=1,
    )
)


min_avg_potential = (
    st.sidebar.slider(
        "Minimum ortalama hedef potansiyeli %",
        min_value=0,
        max_value=100,
        value=0,
        step=5,
    )
)


max_stock_weight = (
    st.sidebar.slider(
        "Tek hisse maksimum ağırlık %",
        min_value=10,
        max_value=40,
        value=20,
        step=5,
    )
)


show_single_institution = (
    st.sidebar.checkbox(
        "Tek kurum önerilerini de göster",
        value=True,
    )
)


# ============================================================
# CACHE TEMİZLE
# ============================================================

if st.sidebar.button(
    "🔄 Kurumsal Verileri Yenile",
    use_container_width=True,
):

    st.cache_data.clear()

    st.rerun()


st.sidebar.caption(
    "Kaynaklar 30 dakika önbellekte tutulur."
)


# ============================================================
# VERİ ÇEK
# ============================================================

with st.spinner(
    "Yatırım kuruluşlarının güncel verileri kontrol ediliyor..."
):

    source_results = load_sources()


# ============================================================
# KAYNAK DURUM
# ============================================================

st.subheader(
    "📡 Kaynak Durumu"
)


status_rows = []

accepted_frames = []


for df, meta in source_results:

    institution = meta.get(
        "institution",
        "?"
    )

    report_date = meta.get(
        "report_date"
    )

    mode = meta.get(
        "mode",
        "report"
    )

    error = meta.get(
        "error",
        ""
    )

    row_count = len(
        df
    )

    age = age_days(
        report_date
    )

    accepted = False

    # --------------------------------------------------------
    # HATA
    # --------------------------------------------------------

    if error:

        status = (
            "🔴 VERİ ALINAMADI"
        )

    # --------------------------------------------------------
    # CANLI AKTİF LİSTE
    # --------------------------------------------------------

    elif mode == "live":

        if row_count > 0:

            accepted = True

            status = (
                "🟢 CANLI"
            )

        else:

            status = (
                "🔴 BOŞ"
            )

    # --------------------------------------------------------
    # TARİHLİ RAPOR
    # --------------------------------------------------------

    else:

        if (
            row_count > 0
            and
            report_is_fresh(
                report_date,
                max_report_age,
            )
        ):

            accepted = True

            status = (
                "🟢 GÜNCEL"
            )

        elif row_count > 0:

            status = (
                "🟠 TARİH ESKİ / BELİRSİZ"
            )

        else:

            status = (
                "🔴 BOŞ"
            )

    # --------------------------------------------------------
    # Kabul edilen dataframe
    # --------------------------------------------------------

    if (
        accepted
        and
        not df.empty
    ):

        temp = df.copy()

        temp[
            "institution"
        ] = institution

        accepted_frames.append(
            temp
        )

    status_rows.append(
        {
            "Kurum":
                institution,

            "Rapor Tarihi":
                (
                    report_date.strftime(
                        "%d.%m.%Y"
                    )
                    if isinstance(
                        report_date,
                        date,
                    )
                    else "-"
                ),

            "Yaş":
                (
                    age
                    if age is not None
                    else "-"
                ),

            "Hisse":
                row_count,

            "Durum":
                status,

            "Hata":
                error,
        }
    )


status_df = pd.DataFrame(
    status_rows
)


st.dataframe(
    status_df,
    use_container_width=True,
    hide_index=True,
)


# ============================================================
# KAYNAK TEST KARTLARI
# ============================================================

st.subheader(
    "🧪 Bağlantı Testi"
)


for _, row in status_df.iterrows():

    institution = row[
        "Kurum"
    ]

    durum = row[
        "Durum"
    ]

    count = row[
        "Hisse"
    ]

    hata = row[
        "Hata"
    ]

    if (
        "🟢" in durum
    ):

        st.success(
            f"✅ {institution}: "
            f"{count} hisse başarıyla alındı."
        )

    elif hata:

        st.error(
            f"❌ {institution}: {hata}"
        )

    else:

        st.warning(
            f"⚠️ {institution}: {durum}"
        )


# ============================================================
# HİÇ KAYNAK YOKSA
# ============================================================

if not accepted_frames:

    st.error(
        "Şu anda güncel ve başarıyla ayrıştırılmış "
        "hiçbir kurumsal portföy kaynağı bulunamadı."
    )

    st.info(
        """
Bu ekranın üstündeki **Bağlantı Testi** bölümünde
hangi kurumun neden veri vermediği görülebilir.

Örneğin:

- HTTP 403 → site otomatik erişimi engelliyor
- tablo bulunamadı → sayfa yapısı değişmiş
- tarih eski → rapor güncellik filtresine takılmış
- aktif AL bulunamadı → parser ile site yapısı uyuşmuyor

Bir kurumun hata vermesi diğer kurumların çalışmasını engellemez.
"""
    )

    st.stop()


# ============================================================
# TÜM KURUM VERİSİ
# ============================================================

all_df = pd.concat(
    accepted_frames,
    ignore_index=True,
)


# ============================================================
# VERİ TEMİZLEME
# ============================================================

all_df[
    "symbol"
] = (
    all_df[
        "symbol"
    ]
    .astype(str)
    .str.upper()
    .str.strip()
)


all_df = all_df[
    all_df[
        "symbol"
    ].str.match(
        r"^[A-Z]{3,6}$"
    )
].copy()


all_df[
    "potential"
] = pd.to_numeric(
    all_df[
        "potential"
    ],
    errors="coerce",
)


all_df[
    "target_price"
] = pd.to_numeric(
    all_df[
        "target_price"
    ],
    errors="coerce",
)


# Aynı kurum-hisse bir kez
all_df = (
    all_df
    .drop_duplicates(
        subset=[
            "institution",
            "symbol",
        ],
        keep="first",
    )
    .reset_index(
        drop=True
    )
)


# ============================================================
# AKTİF KURUM SAYISI
# ============================================================

active_institution_count = (
    all_df[
        "institution"
    ]
    .nunique()
)


# ============================================================
# KONSENSÜS
# ============================================================

def join_institutions(
    series: pd.Series,
) -> str:

    values = sorted(
        set(
            clean_text(x)
            for x in series
            if clean_text(x)
        )
    )

    return ", ".join(
        values
    )


consensus = (
    all_df
    .groupby(
        "symbol",
        as_index=False,
    )
    .agg(

        institution_count=(
            "institution",
            "nunique",
        ),

        institutions=(
            "institution",
            join_institutions,
        ),

        avg_potential=(
            "potential",
            "mean",
        ),

        min_potential=(
            "potential",
            "min",
        ),

        max_potential=(
            "potential",
            "max",
        ),

        avg_target=(
            "target_price",
            "mean",
        ),
    )
)


# ============================================================
# ORAN / KONSENSÜS
# ============================================================

consensus[
    "institution_ratio"
] = (
    consensus[
        "institution_count"
    ]
    /
    active_institution_count
    *
    100
)


def consensus_label(
    row: pd.Series,
) -> str:

    count = int(
        row[
            "institution_count"
        ]
    )

    ratio = float(
        row[
            "institution_ratio"
        ]
    )

    if (
        count >= 3
        and
        ratio >= 75
    ):

        return (
            "🟢 ÇOK GÜÇLÜ"
        )

    if (
        count >= 3
        or
        ratio >= 50
    ):

        return (
            "🟢 GÜÇLÜ"
        )

    if count >= 2:

        return (
            "🟡 ORTAK"
        )

    return (
        "⚪ TEK KURUM"
    )


consensus[
    "consensus"
] = consensus.apply(
    consensus_label,
    axis=1,
)


consensus[
    "avg_potential"
] = (
    consensus[
        "avg_potential"
    ]
    .round(2)
)


consensus[
    "min_potential"
] = (
    consensus[
        "min_potential"
    ]
    .round(2)
)


consensus[
    "max_potential"
] = (
    consensus[
        "max_potential"
    ]
    .round(2)
)


consensus[
    "avg_target"
] = (
    consensus[
        "avg_target"
    ]
    .round(2)
)


consensus[
    "institution_ratio"
] = (
    consensus[
        "institution_ratio"
    ]
    .round(1)
)


# ============================================================
# SIRALA
# ============================================================

consensus = (
    consensus
    .sort_values(
        by=[
            "institution_count",
            "avg_potential",
        ],
        ascending=[
            False,
            False,
        ],
        na_position="last",
    )
    .reset_index(
        drop=True
    )
)


# ============================================================
# ANA METRİKLER
# ============================================================

m1, m2, m3, m4 = st.columns(
    4
)


m1.metric(
    "Aktif Kurum",
    active_institution_count,
)


m2.metric(
    "Kurumsal Hisse",
    all_df[
        "symbol"
    ].nunique(),
)


common_count = int(
    (
        consensus[
            "institution_count"
        ]
        >= 2
    ).sum()
)


m3.metric(
    "Ortak Hisse",
    common_count,
)


max_consensus = (
    int(
        consensus[
            "institution_count"
        ].max()
    )
    if not consensus.empty
    else 0
)


m4.metric(
    "En Yüksek Ortaklık",
    (
        f"{max_consensus}/"
        f"{active_institution_count}"
    ),
)


# ============================================================
# KURUMSAL KONSENSÜS TABLOSU
# ============================================================

st.divider()

st.subheader(
    "🏦 Tüm Kurumsal Konsensüs"
)


consensus_display = (
    consensus.copy()
)


consensus_display = (
    consensus_display.rename(
        columns={

            "symbol":
                "Hisse",

            "institution_count":
                "Kurum",

            "institution_ratio":
                "Kurum Oranı %",

            "consensus":
                "Konsensüs",

            "avg_potential":
                "Ort. Potansiyel %",

            "min_potential":
                "Min Potansiyel %",

            "max_potential":
                "Max Potansiyel %",

            "avg_target":
                "Ort. Hedef",

            "institutions":
                "Öneren Kurumlar",
        }
    )
)


columns_to_show = [

    "Hisse",

    "Kurum",

    "Kurum Oranı %",

    "Konsensüs",

    "Ort. Potansiyel %",

    "Ort. Hedef",

    "Öneren Kurumlar",
]


if not show_single_institution:

    consensus_display = (
        consensus_display[
            consensus_display[
                "Kurum"
            ]
            >= 2
        ]
    )


st.dataframe(
    consensus_display[
        columns_to_show
    ],
    use_container_width=True,
    hide_index=True,
)


# ============================================================
# PORTFÖY FİLTRESİ
# ============================================================

portfolio = (
    consensus[
        consensus[
            "institution_count"
        ]
        >= min_institution_count
    ]
    .copy()
)


# ------------------------------------------------------------
# Potansiyel filtresi
#
# NaN potansiyel varsa ve minimum 0 ise
# hisseyi dışlamıyoruz.
# ------------------------------------------------------------

if min_avg_potential > 0:

    portfolio = portfolio[
        (
            portfolio[
                "avg_potential"
            ]
            .fillna(
                -999
            )
            >=
            min_avg_potential
        )
    ].copy()


# ============================================================
# AĞIRLIK
# ============================================================

portfolio = calculate_portfolio_weights(
    portfolio,
    max_weight=max_stock_weight,
)


portfolio = (
    portfolio
    .sort_values(
        by=[
            "institution_count",
            "weight",
            "avg_potential",
        ],
        ascending=[
            False,
            False,
            False,
        ],
        na_position="last",
    )
    .reset_index(
        drop=True
    )
)


# ============================================================
# ORTAK PORTFÖY
# ============================================================

st.divider()

st.subheader(
    "💼 Kurumsal Ortak Portföy"
)


if portfolio.empty:

    st.warning(
        "Seçilen kriterlerle ortak portföy oluşmadı. "
        "Sidebar'daki minimum kurum sayısını veya "
        "minimum potansiyeli düşürebilirsin."
    )

else:

    portfolio_display = (
        portfolio.copy()
    )


    portfolio_display = (
        portfolio_display.rename(
            columns={

                "symbol":
                    "Hisse",

                "weight":
                    "Portföy Oranı %",

                "institution_count":
                    "Kurum",

                "institution_ratio":
                    "Kurum Oranı %",

                "consensus":
                    "Konsensüs",

                "avg_potential":
                    "Ort. Potansiyel %",

                "avg_target":
                    "Ort. Hedef",

                "institutions":
                    "Öneren Kurumlar",
            }
        )
    )


    st.dataframe(
        portfolio_display[
            [
                "Hisse",
                "Portföy Oranı %",
                "Kurum",
                "Kurum Oranı %",
                "Konsensüs",
                "Ort. Potansiyel %",
                "Ort. Hedef",
                "Öneren Kurumlar",
            ]
        ],
        use_container_width=True,
        hide_index=True,
    )


    # ========================================================
    # PORTFÖY GRAFİĞİ
    # ========================================================

    chart_df = (
        portfolio[
            [
                "symbol",
                "weight",
            ]
        ]
        .set_index(
            "symbol"
        )
    )


    st.bar_chart(
        chart_df
    )


    # ========================================================
    # PORTFÖY ORAN TOPLAMI
    # ========================================================

    total_weight = (
        portfolio[
            "weight"
        ]
        .sum()
    )


    st.caption(
        f"Toplam portföy ağırlığı: "
        f"%{total_weight:.2f}"
    )


# ============================================================
# EN GÜÇLÜ ORTAK ADAYLAR
# ============================================================

st.divider()

st.subheader(
    "⭐ En Güçlü Kurumsal Ortaklıklar"
)


top_common = (
    consensus[
        consensus[
            "institution_count"
        ]
        >= 2
    ]
    .head(10)
    .copy()
)


if top_common.empty:

    st.info(
        "Şu anda en az iki kurumun ortak önerdiği "
        "bir hisse ayrıştırılamadı."
    )

else:

    for _, row in top_common.iterrows():

        symbol = row[
            "symbol"
        ]

        count = int(
            row[
                "institution_count"
            ]
        )

        institutions = row[
            "institutions"
        ]

        potential = row[
            "avg_potential"
        ]

        label = row[
            "consensus"
        ]

        if pd.notna(
            potential
        ):

            potential_text = (
                f"%{potential:.1f}"
            )

        else:

            potential_text = "-"

        st.write(
            f"**{symbol}** — "
            f"{count}/{active_institution_count} kurum • "
            f"{label} • "
            f"Ort. potansiyel {potential_text} • "
            f"{institutions}"
        )


# ============================================================
# KURUM DETAYLARI
# ============================================================

st.divider()

st.subheader(
    "🔎 Kurum Bazında Portföyler"
)


for institution in sorted(
    all_df[
        "institution"
    ].unique()
):

    institution_df = (
        all_df[
            all_df[
                "institution"
            ]
            ==
            institution
        ]
        .copy()
    )


    with st.expander(
        f"🏛️ {institution} "
        f"({len(institution_df)} hisse)"
    ):

        institution_display = (
            institution_df.copy()
        )


        institution_display[
            "report_date"
        ] = (
            institution_display[
                "report_date"
            ]
            .apply(
                lambda x:
                (
                    x.strftime(
                        "%d.%m.%Y"
                    )
                    if isinstance(
                        x,
                        date,
                    )
                    else "-"
                )
            )
        )


        institution_display = (
            institution_display.rename(
                columns={

                    "symbol":
                        "Hisse",

                    "recommendation":
                        "Öneri",

                    "target_price":
                        "Hedef Fiyat",

                    "potential":
                        "Potansiyel %",

                    "report_date":
                        "Kaynak Tarihi",

                    "source_type":
                        "Kaynak Türü",
                }
            )
        )


        st.dataframe(
            institution_display[
                [
                    "Hisse",
                    "Öneri",
                    "Hedef Fiyat",
                    "Potansiyel %",
                    "Kaynak Tarihi",
                    "Kaynak Türü",
                ]
            ],
            use_container_width=True,
            hide_index=True,
        )


# ============================================================
# HİSSE DETAY / KURUM KARŞILAŞTIRMASI
# ============================================================

st.divider()

st.subheader(
    "🔬 Hisse Bazında Kurum Karşılaştırması"
)


symbols = sorted(
    all_df[
        "symbol"
    ].unique()
)


selected_symbol = st.selectbox(
    "Hisse seç",
    symbols,
)


detail = (
    all_df[
        all_df[
            "symbol"
        ]
        ==
        selected_symbol
    ]
    .copy()
)


if not detail.empty:

    detail_display = (
        detail[
            [
                "institution",
                "recommendation",
                "target_price",
                "potential",
                "report_date",
                "source_type",
            ]
        ]
        .copy()
    )


    detail_display[
        "report_date"
    ] = (
        detail_display[
            "report_date"
        ]
        .apply(
            lambda x:
            (
                x.strftime(
                    "%d.%m.%Y"
                )
                if isinstance(
                    x,
                    date,
                )
                else "-"
            )
        )
    )


    detail_display = (
        detail_display.rename(
            columns={

                "institution":
                    "Kurum",

                "recommendation":
                    "Öneri",

                "target_price":
                    "Hedef",

                "potential":
                    "Potansiyel %",

                "report_date":
                    "Tarih",

                "source_type":
                    "Kaynak",
            }
        )
    )


    st.dataframe(
        detail_display,
        use_container_width=True,
        hide_index=True,
    )


# ============================================================
# HAM VERİ
# ============================================================

with st.expander(
    "🧪 Ham Kurumsal Veri"
):

    st.dataframe(
        all_df,
        use_container_width=True,
        hide_index=True,
    )


# ============================================================
# HAM KONSENSÜS
# ============================================================

with st.expander(
    "🧮 Konsensüs Hesaplama Verisi"
):

    st.dataframe(
        consensus,
        use_container_width=True,
        hide_index=True,
    )


# ============================================================
# AÇIKLAMA
# ============================================================

st.divider()


st.info(
    """
### 🏦 Kurumsal Ortak Portföy nasıl çalışır?

Bu sistem **BIST AI PRO'nun puanlama motorundan tamamen bağımsızdır.**

Bir hisseye:

- teknik puan eklemez,
- temel puan eklemez,
- momentum puanı eklemez,
- Günlük Trade puanı eklemez.

Portföy oluştururken temel olarak **aynı hisseyi kaç yatırım kuruluşunun
önerdiğine** bakılır.

İkinci aşamada kurumların açıkladığı **ortalama hedef fiyat potansiyeli**
portföy oranını sınırlı ölçüde etkiler.

Örneğin:

**4 kurum THYAO öneriyor**  
**2 kurum ASELS öneriyor**

ise diğer şartlar yakın olduğunda THYAO daha yüksek portföy ağırlığı alır.

### Güncellik

Tarihli model portföylerinde eski raporlar otomatik dışarıda bırakılır.

Aktif ve sürekli güncellenen öneri listelerinde ise sayfanın hâlen aktif
öneri göstermesi esas alınır.

Bir yatırım kuruluşunun sitesi veri vermediğinde diğer kurumların
hesaplaması devam eder.
"""
)


st.warning(
    "⚠️ Kurumların internet sayfası yapısı zaman içinde değişebilir. "
    "Bu nedenle Kaynak Durumu bölümündeki kırmızı satırlar kontrol edilmelidir."
)


st.caption(
    "BIST AI PRO • Kurumsal Ortak Portföy V2 • "
    "Yatırım danışmanlığı kapsamında değildir."
)