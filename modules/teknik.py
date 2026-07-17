import pandas as pd
import numpy as np


# =====================================
# RSI
# =====================================

def hesapla_rsi(df, period=14):

    delta = df["Close"].diff()

    gain = delta.where(delta > 0, 0)

    loss = -delta.where(delta < 0, 0)

    avg_gain = gain.rolling(period).mean()

    avg_loss = loss.rolling(period).mean()

    rs = avg_gain / avg_loss

    rsi = 100 - (100 / (1 + rs))

    df["RSI"] = rsi

    return df


# =====================================
# HAREKETLİ ORTALAMALAR
# =====================================

def hesapla_ma(df):

    df["MA20"] = (
        df["Close"]
        .rolling(20)
        .mean()
    )

    df["MA50"] = (
        df["Close"]
        .rolling(50)
        .mean()
    )

    df["MA100"] = (
        df["Close"]
        .rolling(100)
        .mean()
    )

    df["MA200"] = (
        df["Close"]
        .rolling(200)
        .mean()
    )

    return df


# =====================================
# EMA
# =====================================

def hesapla_ema(df):

    df["EMA12"] = (
        df["Close"]
        .ewm(span=12, adjust=False)
        .mean()
    )

    df["EMA26"] = (
        df["Close"]
        .ewm(span=26, adjust=False)
        .mean()
    )

    df["EMA50"] = (
        df["Close"]
        .ewm(span=50, adjust=False)
        .mean()
    )

    return df


# =====================================
# MACD
# =====================================

def hesapla_macd(df):

    if "EMA12" not in df.columns:

        df = hesapla_ema(df)

    df["MACD"] = (
        df["EMA12"]
        -
        df["EMA26"]
    )

    df["MACD_SIGNAL"] = (
        df["MACD"]
        .ewm(span=9, adjust=False)
        .mean()
    )

    df["MACD_HIST"] = (
        df["MACD"]
        -
        df["MACD_SIGNAL"]
    )

    return df


# =====================================
# TÜM GÖSTERGELER
# =====================================

def temel_gostergeler(df):

    df = hesapla_rsi(df)

    df = hesapla_ma(df)

    df = hesapla_ema(df)

    df = hesapla_macd(df)

    return df
# =====================================
# DESTEK / DİRENÇ
# =====================================

def destek_direnc(df, pencere=20):

    son = df.tail(pencere)

    destek = round(
        son["Low"].min(),
        2
    )

    direnc = round(
        son["High"].max(),
        2
    )

    return destek, direnc


# =====================================
# HACİM ANALİZİ
# =====================================

def hacim_analizi(df):

    ortalama = df["Volume"].tail(20).mean()

    son_hacim = df["Volume"].iloc[-1]

    oran = son_hacim / ortalama

    if oran >= 1.50:

        yorum = "Çok Güçlü"

        puan = 20

    elif oran >= 1.20:

        yorum = "Güçlü"

        puan = 15

    elif oran >= 1.00:

        yorum = "Normal"

        puan = 10

    else:

        yorum = "Zayıf"

        puan = 5

    return yorum, puan


# =====================================
# TEKNİK PUAN
# =====================================

def teknik_puan(df):

    son = df.iloc[-1]

    puan = 0

    # Trend

    if son["Close"] > son["MA20"]:
        puan += 10

    if son["Close"] > son["MA50"]:
        puan += 15

    if son["Close"] > son["MA200"]:
        puan += 20

    # RSI

    if 45 <= son["RSI"] <= 65:
        puan += 15

    elif 30 <= son["RSI"] < 45:
        puan += 10

    elif 65 < son["RSI"] <= 75:
        puan += 8

    # MACD

    if son["MACD"] > son["MACD_SIGNAL"]:
        puan += 20

    # Hacim

    _, hacim_puan = hacim_analizi(df)

    puan += hacim_puan

    puan = min(puan, 100)

    return puan


# =====================================
# TREND
# =====================================

def trend_yorumu(puan):

    if puan >= 85:

        return "🟢 Çok Güçlü Yükseliş"

    elif puan >= 70:

        return "🟢 Güçlü Pozitif"

    elif puan >= 55:

        return "🟡 Pozitif"

    elif puan >= 40:

        return "🟠 Nötr"

    else:

        return "🔴 Negatif"
    # =====================================
# AI YORUMU
# =====================================

def ai_yorumu(df):

    son = df.iloc[-1]

    puan = teknik_puan(df)

    yorumlar = []

    if son["Close"] > son["MA200"]:
        yorumlar.append(
            "Uzun vadeli ana trend yukarı yönlü."
        )
    else:
        yorumlar.append(
            "Uzun vadeli trend zayıf görünüyor."
        )

    if son["Close"] > son["MA50"]:
        yorumlar.append(
            "Orta vadeli görünüm olumlu."
        )
    else:
        yorumlar.append(
            "Orta vadede dikkatli olunmalı."
        )

    if son["MACD"] > son["MACD_SIGNAL"]:
        yorumlar.append(
            "MACD alış yönünde sinyal üretiyor."
        )
    else:
        yorumlar.append(
            "MACD henüz güçlü bir alış sinyali vermiyor."
        )

    if son["RSI"] < 30:
        yorumlar.append(
            "RSI aşırı satım bölgesinde."
        )

    elif son["RSI"] > 70:
        yorumlar.append(
            "RSI aşırı alım bölgesinde."
        )

    else:
        yorumlar.append(
            "RSI dengeli bölgede."
        )

    if puan >= 85:
        karar = "🟢 GÜÇLÜ AL"

    elif puan >= 70:
        karar = "🟢 AL"

    elif puan >= 55:
        karar = "🟡 TUT"

    elif puan >= 40:
        karar = "🟠 İZLE"

    else:
        karar = "🔴 SAT"

    return yorumlar, karar


# =====================================
# GÜVEN SKORU
# =====================================

def guven_skoru(df):

    puan = teknik_puan(df)

    return min(
        95,
        puan + 5
    )


# =====================================
# ANA ANALİZ FONKSİYONU
# =====================================

def analiz_et(df):

    df = temel_gostergeler(df)

    destek, direnc = destek_direnc(df)

    puan = teknik_puan(df)

    trend = trend_yorumu(puan)

    hacim, _ = hacim_analizi(df)

    yorumlar, karar = ai_yorumu(df)

    sonuc = {
        "fiyat": round(df["Close"].iloc[-1], 2),
        "rsi": round(df["RSI"].iloc[-1], 2),
        "ma20": round(df["MA20"].iloc[-1], 2),
        "ma50": round(df["MA50"].iloc[-1], 2),
        "ma200": round(df["MA200"].iloc[-1], 2),
        "macd": round(df["MACD"].iloc[-1], 2),
        "macd_signal": round(df["MACD_SIGNAL"].iloc[-1], 2),
        "destek": destek,
        "direnc": direnc,
        "puan": puan,
        "trend": trend,
        "hacim": hacim,
        "guven": guven_skoru(df),
        "karar": karar,
        "yorumlar": yorumlar,
    }

    return sonuc