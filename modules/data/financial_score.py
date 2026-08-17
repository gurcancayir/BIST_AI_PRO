import math


# ============================================================
# BIST AI PRO
# KAP / FİNANSAL RAPOR TABANLI FİNANSAL SAĞLIK SKORU
# ============================================================


def safe_div(a, b):
    """
    Güvenli bölme.
    """
    try:
        if b in (None, 0):
            return None
        return a / b
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def clamp(value, minimum=0, maximum=100):
    """
    Skoru 0-100 arasında tutar.
    """
    if value is None:
        return 0

    return max(minimum, min(maximum, value))


# ============================================================
# 1. LİKİDİTE SKORU
# ============================================================

def calculate_liquidity_score(current_assets, current_liabilities):
    """
    Cari oran:
        Dönen Varlıklar / Kısa Vadeli Yükümlülükler

    Skorlama:
        >= 2.00  -> 100
        1.50     -> 85
        1.20     -> 70
        1.00     -> 50
        0.75     -> 25
        < 0.75   -> 0
    """

    ratio = safe_div(current_assets, current_liabilities)

    if ratio is None:
        return 0, None

    if ratio >= 2.00:
        score = 100
    elif ratio >= 1.50:
        score = 85
    elif ratio >= 1.20:
        score = 70
    elif ratio >= 1.00:
        score = 50
    elif ratio >= 0.75:
        score = 25
    else:
        score = 0

    return score, ratio


# ============================================================
# 2. BORÇLULUK SKORU
# ============================================================

def calculate_debt_score(
    short_term_debt,
    short_term_long_term_debt,
    long_term_debt,
    equity,
):
    """
    Finansal borç / özkaynak oranı.

    Düşük borç = yüksek skor.
    """

    total_debt = (
        (short_term_debt or 0)
        + (short_term_long_term_debt or 0)
        + (long_term_debt or 0)
    )

    debt_equity = safe_div(total_debt, equity)

    if debt_equity is None:
        return 0, None

    if debt_equity <= 0.20:
        score = 100
    elif debt_equity <= 0.35:
        score = 90
    elif debt_equity <= 0.50:
        score = 80
    elif debt_equity <= 0.75:
        score = 65
    elif debt_equity <= 1.00:
        score = 45
    elif debt_equity <= 1.50:
        score = 25
    else:
        score = 0

    return score, debt_equity


# ============================================================
# 3. NET NAKİT / BORÇ SKORU
# ============================================================

def calculate_net_cash_score(
    cash,
    current_financial_investments,
    noncurrent_financial_investments,
    total_debt,
):
    """
    Net nakit:

        Nakit + finansal yatırımlar - finansal borç

    Pozitif net nakit şirket lehine değerlendirilir.
    """

    liquid_financial_assets = (
        (cash or 0)
        + (current_financial_investments or 0)
        + (noncurrent_financial_investments or 0)
    )

    net_cash = liquid_financial_assets - (total_debt or 0)

    if total_debt in (None, 0):
        if net_cash > 0:
            return 100, net_cash
        return 50, net_cash

    net_cash_ratio = safe_div(net_cash, total_debt)

    if net_cash_ratio is None:
        return 0, net_cash

    if net_cash_ratio >= 1.00:
        score = 100
    elif net_cash_ratio >= 0.50:
        score = 90
    elif net_cash_ratio >= 0.20:
        score = 80
    elif net_cash_ratio >= 0:
        score = 70
    elif net_cash_ratio >= -0.25:
        score = 50
    elif net_cash_ratio >= -0.50:
        score = 30
    else:
        score = 10

    return score, net_cash


# ============================================================
# 4. ÖZKAYNAK GÜCÜ
# ============================================================

def calculate_equity_score(equity, total_assets):
    """
    Özkaynak / toplam varlık.
    """

    ratio = safe_div(equity, total_assets)

    if ratio is None:
        return 0, None

    if ratio >= 0.70:
        score = 100
    elif ratio >= 0.60:
        score = 90
    elif ratio >= 0.50:
        score = 80
    elif ratio >= 0.40:
        score = 65
    elif ratio >= 0.30:
        score = 45
    elif ratio >= 0.20:
        score = 25
    else:
        score = 0

    return score, ratio


# ============================================================
# 5. KÂRLILIK SKORU
# ============================================================

def calculate_profitability_score(
    revenue,
    gross_profit,
    operating_profit,
    net_profit,
    equity,
    total_assets,
):
    """
    Brüt marj + faaliyet marjı + net marj
    + ROE + ROA birlikte değerlendirilir.
    """

    gross_margin = safe_div(gross_profit, revenue)
    operating_margin = safe_div(operating_profit, revenue)
    net_margin = safe_div(net_profit, revenue)

    roe = safe_div(net_profit, equity)
    roa = safe_div(net_profit, total_assets)

    scores = []

    # Brüt kâr marjı
    if gross_margin is not None:
        if gross_margin >= 0.30:
            scores.append(100)
        elif gross_margin >= 0.20:
            scores.append(85)
        elif gross_margin >= 0.15:
            scores.append(70)
        elif gross_margin >= 0.10:
            scores.append(55)
        elif gross_margin > 0:
            scores.append(30)
        else:
            scores.append(0)

    # Esas faaliyet marjı
    if operating_margin is not None:
        if operating_margin >= 0.25:
            scores.append(100)
        elif operating_margin >= 0.15:
            scores.append(85)
        elif operating_margin >= 0.10:
            scores.append(70)
        elif operating_margin >= 0.05:
            scores.append(55)
        elif operating_margin > 0:
            scores.append(30)
        else:
            scores.append(0)

    # Net kâr marjı
    if net_margin is not None:
        if net_margin >= 0.20:
            scores.append(100)
        elif net_margin >= 0.15:
            scores.append(90)
        elif net_margin >= 0.10:
            scores.append(80)
        elif net_margin >= 0.05:
            scores.append(65)
        elif net_margin > 0:
            scores.append(40)
        else:
            scores.append(0)

    # ROE
    if roe is not None:
        if roe >= 0.30:
            scores.append(100)
        elif roe >= 0.20:
            scores.append(90)
        elif roe >= 0.15:
            scores.append(80)
        elif roe >= 0.10:
            scores.append(65)
        elif roe > 0:
            scores.append(40)
        else:
            scores.append(0)

    # ROA
    if roa is not None:
        if roa >= 0.15:
            scores.append(100)
        elif roa >= 0.10:
            scores.append(90)
        elif roa >= 0.07:
            scores.append(80)
        elif roa >= 0.04:
            scores.append(65)
        elif roa > 0:
            scores.append(40)
        else:
            scores.append(0)

    if not scores:
        return 0, {}

    score = sum(scores) / len(scores)

    return score, {
        "gross_margin": gross_margin,
        "operating_margin": operating_margin,
        "net_margin": net_margin,
        "roe": roe,
        "roa": roa,
    }


# ============================================================
# 6. NAKİT AKIŞI SKORU
# ============================================================

def calculate_cashflow_score(
    operating_cashflow,
    net_profit,
    capex,
):
    """
    Operasyonel nakit akışı ve serbest nakit akışı.

    CFO = işletme faaliyetlerinden nakit akışı

    FCF = CFO - Capex
    """

    operating_cashflow = operating_cashflow or 0
    net_profit = net_profit or 0
    capex = abs(capex or 0)

    free_cashflow = operating_cashflow - capex

    scores = []

    # CFO pozitif mi?
    if operating_cashflow > 0:
        scores.append(70)
    else:
        scores.append(10)

    # CFO / Net kâr
    cfo_profit_ratio = safe_div(
        operating_cashflow,
        net_profit
    )

    if cfo_profit_ratio is not None:

        if cfo_profit_ratio >= 1.00:
            scores.append(100)

        elif cfo_profit_ratio >= 0.75:
            scores.append(85)

        elif cfo_profit_ratio >= 0.50:
            scores.append(70)

        elif cfo_profit_ratio >= 0.25:
            scores.append(45)

        else:
            scores.append(20)

    # FCF
    if free_cashflow > 0:
        scores.append(100)
    else:
        scores.append(30)

    score = sum(scores) / len(scores)

    return score, {
        "operating_cashflow": operating_cashflow,
        "free_cashflow": free_cashflow,
        "cfo_profit_ratio": cfo_profit_ratio,
    }


# ============================================================
# 7. KÂR KALİTESİ
# ============================================================

def calculate_profit_quality_score(
    net_profit,
    operating_profit,
    operating_cashflow,
):
    """
    Net kârın operasyonel faaliyetlerle desteklenip
    desteklenmediğini ölçer.
    """

    scores = []

    # CFO / Net kâr
    cfo_profit_ratio = safe_div(
        operating_cashflow,
        net_profit
    )

    if cfo_profit_ratio is not None:

        if cfo_profit_ratio >= 1.00:
            scores.append(100)

        elif cfo_profit_ratio >= 0.75:
            scores.append(85)

        elif cfo_profit_ratio >= 0.50:
            scores.append(70)

        elif cfo_profit_ratio >= 0.25:
            scores.append(45)

        else:
            scores.append(20)

    # Faaliyet kârı pozitif mi?
    if operating_profit > 0:
        scores.append(100)
    else:
        scores.append(0)

    if not scores:
        return 0

    return sum(scores) / len(scores)


# ============================================================
# 8. ANA FİNANSAL SAĞLIK SKORU
# ============================================================

def calculate_financial_score(data):
    """
    Ana finansal sağlık skoru.

    Ağırlıklar:

        Likidite       %15
        Borçluluk      %20
        Kârlılık       %20
        Özkaynak       %15
        Nakit akışı    %20
        Kâr kalitesi   %10
    """

    current_assets = data.get("current_assets", 0)
    current_liabilities = data.get("current_liabilities", 0)

    short_term_debt = data.get("short_term_debt", 0)
    short_term_long_term_debt = data.get(
        "short_term_long_term_debt",
        0
    )
    long_term_debt = data.get("long_term_debt", 0)

    equity = data.get("equity", 0)
    total_assets = data.get("total_assets", 0)

    cash = data.get("cash", 0)

    current_financial_investments = data.get(
        "current_financial_investments",
        0
    )

    noncurrent_financial_investments = data.get(
        "noncurrent_financial_investments",
        0
    )

    revenue = data.get("revenue", 0)
    gross_profit = data.get("gross_profit", 0)
    operating_profit = data.get("operating_profit", 0)
    net_profit = data.get("net_profit", 0)

    operating_cashflow = data.get(
        "operating_cashflow",
        0
    )

    capex = data.get("capex", 0)

    # --------------------------------------------------------
    # ALT SKORLAR
    # --------------------------------------------------------

    liquidity_score, current_ratio = calculate_liquidity_score(
        current_assets,
        current_liabilities
    )

    debt_score, debt_equity = calculate_debt_score(
        short_term_debt,
        short_term_long_term_debt,
        long_term_debt,
        equity
    )

    total_debt = (
        (short_term_debt or 0)
        + (short_term_long_term_debt or 0)
        + (long_term_debt or 0)
    )

    net_cash_score, net_cash = calculate_net_cash_score(
        cash,
        current_financial_investments,
        noncurrent_financial_investments,
        total_debt
    )

    # Borç skoru ile net nakit skorunun ortalaması
    debt_health_score = (
        debt_score * 0.60
        + net_cash_score * 0.40
    )

    equity_score, equity_ratio = calculate_equity_score(
        equity,
        total_assets
    )

    profitability_score, profitability = (
        calculate_profitability_score(
            revenue,
            gross_profit,
            operating_profit,
            net_profit,
            equity,
            total_assets
        )
    )

    cashflow_score, cashflow = calculate_cashflow_score(
        operating_cashflow,
        net_profit,
        capex
    )

    profit_quality_score = calculate_profit_quality_score(
        net_profit,
        operating_profit,
        operating_cashflow
    )

    # --------------------------------------------------------
    # ANA SKOR
    # --------------------------------------------------------

    financial_score = (
        liquidity_score * 0.15
        + debt_health_score * 0.20
        + profitability_score * 0.20
        + equity_score * 0.15
        + cashflow_score * 0.20
        + profit_quality_score * 0.10
    )

    financial_score = round(
        clamp(financial_score),
        2
    )

    # --------------------------------------------------------
    # DURUM
    # --------------------------------------------------------

    if financial_score >= 80:
        status = "🟢 ÇOK GÜÇLÜ"

    elif financial_score >= 70:
        status = "🟢 GÜÇLÜ"

    elif financial_score >= 60:
        status = "🟡 SAĞLIKLI"

    elif financial_score >= 50:
        status = "🟠 ORTA"

    elif financial_score >= 40:
        status = "🟠 ZAYIF"

    else:
        status = "🔴 RİSKLİ"

    return {
        "financial_score": financial_score,
        "status": status,

        # Alt skorlar
        "liquidity_score": round(liquidity_score, 2),
        "debt_score": round(debt_health_score, 2),
        "profitability_score": round(profitability_score, 2),
        "equity_score": round(equity_score, 2),
        "cashflow_score": round(cashflow_score, 2),
        "profit_quality_score": round(
            profit_quality_score,
            2
        ),

        # Oranlar
        "current_ratio": current_ratio,
        "debt_equity": debt_equity,
        "equity_ratio": equity_ratio,
        "net_cash": net_cash,

        # Kârlılık
        "gross_margin": profitability.get(
            "gross_margin"
        ),
        "operating_margin": profitability.get(
            "operating_margin"
        ),
        "net_margin": profitability.get(
            "net_margin"
        ),
        "roe": profitability.get("roe"),
        "roa": profitability.get("roa"),

        # Nakit
        "operating_cashflow": cashflow.get(
            "operating_cashflow"
        ),
        "free_cashflow": cashflow.get(
            "free_cashflow"
        ),
        "cfo_profit_ratio": cashflow.get(
            "cfo_profit_ratio"
        ),

        # Borç
        "total_debt": total_debt,
    }