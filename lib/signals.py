"""
lib/signals.py
Technical strength scoring for NSE Market Analyst.
Returns neutral educational labels — no buy/sell language.
"""

import numpy as np
from lib.market_data import compute_technicals


def technical_score(df) -> tuple[float, dict]:
    """
    Compute a 0-100 technical strength score.
    Returns (score, components_dict).
    """
    tech = compute_technicals(df)
    if not tech:
        return 50.0, {}

    score = 0
    max_points = 0
    components = {}

    price = tech.get("current", 0)

    # Trend vs 200 DMA (25 pts)
    ma200 = tech.get("ma200")
    if ma200 and price:
        max_points += 25
        if price > ma200:
            pts = 25
        elif price > ma200 * 0.95:
            pts = 12
        else:
            pts = 0
        score += pts
        components["200-DMA Trend"] = {"points": pts, "max": 25,
                                        "label": "Above 200-DMA" if pts == 25
                                        else ("Near 200-DMA" if pts == 12 else "Below 200-DMA")}

    # Trend vs 50 DMA (15 pts)
    ma50 = tech.get("ma50")
    if ma50 and price:
        max_points += 15
        pts = 15 if price > ma50 else 0
        score += pts
        components["50-DMA Trend"] = {"points": pts, "max": 15,
                                       "label": "Above 50-DMA" if pts == 15 else "Below 50-DMA"}

    # RSI (20 pts)
    rsi = tech.get("rsi")
    if rsi is not None:
        max_points += 20
        if 50 <= rsi < 70:
            pts = 20
            lbl = "Firm momentum"
        elif 40 <= rsi < 50:
            pts = 10
            lbl = "Neutral momentum"
        elif rsi >= 70:
            pts = 12
            lbl = "Overbought zone"
        else:
            pts = 0
            lbl = "Weak momentum"
        score += pts
        components["RSI"] = {"points": pts, "max": 20, "label": lbl, "value": round(rsi, 1)}

    # MACD (20 pts)
    macd = tech.get("macd")
    macd_sig = tech.get("macd_signal")
    if macd is not None and macd_sig is not None:
        max_points += 20
        if macd > 0 and macd > macd_sig:
            pts = 20
            lbl = "Bullish MACD"
        elif macd > 0 or macd > macd_sig:
            pts = 10
            lbl = "Mixed MACD"
        else:
            pts = 0
            lbl = "Bearish MACD"
        score += pts
        components["MACD"] = {"points": pts, "max": 20, "label": lbl}

    # 52-week position (20 pts)
    high52 = tech.get("52w_high")
    low52  = tech.get("52w_low")
    if high52 and low52 and price:
        max_points += 20
        rng = high52 - low52
        pos = (price - low52) / rng if rng else 0.5
        if pos >= 0.7:
            pts = 20
            lbl = "Near 52-week high"
        elif pos >= 0.5:
            pts = 15
            lbl = "Upper half of range"
        elif pos >= 0.3:
            pts = 8
            lbl = "Lower half of range"
        else:
            pts = 2
            lbl = "Near 52-week low"
        score += pts
        components["52-Week Position"] = {"points": pts, "max": 20, "label": lbl}

    normalised = (score / max_points * 100) if max_points else 50
    return round(normalised, 1), components


def fundamental_score(info: dict) -> tuple[float, dict]:
    """
    Compute a 0-100 fundamental quality score.
    Returns (score, components_dict).
    """
    score = 0
    max_points = 0
    components = {}

    # ROE (25 pts)
    roe_raw = info.get("returnOnEquity")
    if roe_raw is not None:
        roe = roe_raw * 100 if abs(roe_raw) < 5 else roe_raw
        max_points += 25
        if roe >= 20:
            pts = 25; lbl = "Strong profitability"
        elif roe >= 12:
            pts = 15; lbl = "Moderate profitability"
        elif roe >= 5:
            pts = 5;  lbl = "Low profitability"
        else:
            pts = 0;  lbl = "Weak profitability"
        score += pts
        components["ROE"] = {"points": pts, "max": 25,
                              "label": lbl, "value": f"{roe:.1f}%"}

    # Debt/Equity (20 pts)
    de = info.get("debtToEquity")
    if de is not None:
        max_points += 20
        de_adj = de / 100 if de > 10 else de  # yfinance sometimes returns in %
        if de_adj < 0.3:
            pts = 20; lbl = "Low leverage"
        elif de_adj < 0.7:
            pts = 15; lbl = "Moderate leverage"
        elif de_adj < 1.5:
            pts = 8;  lbl = "Elevated leverage"
        else:
            pts = 2;  lbl = "High leverage"
        score += pts
        components["D/E Ratio"] = {"points": pts, "max": 20,
                                    "label": lbl, "value": f"{de_adj:.2f}x"}

    # Earnings Growth (20 pts)
    eg = info.get("earningsGrowth")
    if eg is not None:
        eg_pct = eg * 100 if abs(eg) < 5 else eg
        max_points += 20
        if eg_pct >= 20:
            pts = 20; lbl = "Strong earnings growth"
        elif eg_pct >= 10:
            pts = 14; lbl = "Moderate earnings growth"
        elif eg_pct >= 0:
            pts = 6;  lbl = "Marginal earnings growth"
        else:
            pts = 0;  lbl = "Declining earnings"
        score += pts
        components["Earnings Growth"] = {"points": pts, "max": 20,
                                          "label": lbl, "value": f"{eg_pct:.1f}%"}

    # Net Margin (15 pts)
    nm = info.get("profitMargins")
    if nm is not None:
        nm_pct = nm * 100 if abs(nm) < 5 else nm
        max_points += 15
        if nm_pct >= 15:
            pts = 15; lbl = "High net margin"
        elif nm_pct >= 8:
            pts = 10; lbl = "Moderate net margin"
        elif nm_pct >= 0:
            pts = 5;  lbl = "Thin net margin"
        else:
            pts = 0;  lbl = "Loss-making"
        score += pts
        components["Net Margin"] = {"points": pts, "max": 15,
                                     "label": lbl, "value": f"{nm_pct:.1f}%"}

    # Promoter Holding (20 pts) — higher promoter holding generally seen as confidence signal in India
    promoter = info.get("heldPercentInsiders")
    if promoter is not None:
        ph_pct = promoter * 100 if promoter < 1 else promoter
        max_points += 20
        if ph_pct >= 50:
            pts = 20; lbl = "High promoter holding"
        elif ph_pct >= 35:
            pts = 13; lbl = "Moderate promoter holding"
        elif ph_pct >= 20:
            pts = 6;  lbl = "Lower promoter holding"
        else:
            pts = 2;  lbl = "Low promoter holding"
        score += pts
        components["Promoter Holding"] = {"points": pts, "max": 20,
                                           "label": lbl, "value": f"{ph_pct:.1f}%"}

    normalised = (score / max_points * 100) if max_points else 50
    return round(normalised, 1), components
