"""
lib/macro_india.py
India macro data helpers for NSE Market Analyst.
Uses World Bank, RBI public data, or manual fallback.
"""

import requests
import streamlit as st
import pandas as pd

# World Bank indicator codes for India (country code: IND)
WB_BASE = "https://api.worldbank.org/v2/country/IND/indicator"
WB_PARAMS = {"format": "json", "mrv": 10, "per_page": 10}

INDICATORS = {
    "GDP Growth (%)":        "NY.GDP.MKTP.KD.ZG",
    "CPI Inflation (%)":     "FP.CPI.TOTL.ZG",
    "Forex Reserves (USD B)":"FI.RES.TOTL.CD",
    "Current Account (% GDP)":"BN.CAB.XOKA.GD.ZS",
}

# Hardcoded recent values as fallback when APIs are unavailable
FALLBACK_MACRO = {
    "RBI Repo Rate (%)":        6.5,
    "CPI Inflation (%)":        4.83,
    "WPI Inflation (%)":        1.04,
    "GDP Growth FY25E (%)":     6.4,
    "10Y Gsec Yield (%)":       6.87,
    "USD/INR":                  None,  # fetched live via yfinance
    "Crude Brent (USD/bbl)":    None,  # fetched live
    "Forex Reserves (USD B)":   654.0,
    "GST Collections (₹ Cr)":   187000,
    "Fiscal Deficit (% GDP)":   5.1,
}


@st.cache_data(ttl=86400, show_spinner=False)
def fetch_world_bank(indicator_code: str, label: str) -> dict:
    """Fetch a World Bank indicator time series for India."""
    try:
        url = f"{WB_BASE}/{indicator_code}"
        r = requests.get(url, params=WB_PARAMS, timeout=8)
        if r.status_code != 200:
            return {}
        data = r.json()
        if len(data) < 2 or not data[1]:
            return {}
        records = [
            {"year": int(item["date"]), "value": item["value"]}
            for item in data[1]
            if item.get("value") is not None
        ]
        records.sort(key=lambda x: x["year"])
        return {"label": label, "records": records}
    except Exception:
        return {}


def get_india_macro_dict() -> dict:
    """
    Return best-effort India macro dict.
    Tries World Bank for some indicators; falls back to hardcoded.
    """
    result = dict(FALLBACK_MACRO)
    # Try live GDP and CPI from World Bank
    for label, code in [("GDP Growth (%)", "NY.GDP.MKTP.KD.ZG"),
                         ("CPI Inflation (%)", "FP.CPI.TOTL.ZG")]:
        wb = fetch_world_bank(code, label)
        if wb and wb.get("records"):
            result[label] = wb["records"][-1]["value"]
    return result


def get_gsec_yield() -> float | None:
    """Attempt to get 10Y India Gsec yield via yfinance (^IRX proxy or manual)."""
    try:
        import yfinance as yf
        t = yf.Ticker("^IRX")  # 3-month US T-bill (proxy, not Indian Gsec)
        return None  # Not a reliable source; return None and show fallback
    except Exception:
        return None


def macro_summary_text(macro: dict) -> str:
    lines = []
    for k, v in macro.items():
        if v is None:
            lines.append(f"{k}: Fetching live...")
        elif isinstance(v, float):
            lines.append(f"{k}: {v}")
        else:
            lines.append(f"{k}: {v}")
    return "\n".join(lines)
