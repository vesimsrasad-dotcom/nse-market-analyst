"""
lib/symbol_resolver.py
Resolves a stock name OR ticker to a canonical NSE ticker symbol.

Resolution order:
  1. If input already looks like a known NSE ticker → return as-is
  2. Query Yahoo Finance search API for the name
  3. Filter results to NSE exchange (.NS suffix)
  4. Return the best match ticker (stripped of .NS)

Usage:
    from lib.symbol_resolver import resolve_to_ticker
    ticker = resolve_to_ticker("Reliance Industries")  # → "RELIANCE"
    ticker = resolve_to_ticker("RELIANCE")             # → "RELIANCE"
    ticker = resolve_to_ticker("TCS")                  # → "TCS"
"""

import re
import time
import requests
import streamlit as st

YAHOO_SEARCH_URL = "https://query2.finance.yahoo.com/v1/finance/search"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; NSEMarketAnalyst/1.0)",
    "Accept": "application/json",
}

# Common short aliases that are already valid NSE tickers — skip API for these
_OBVIOUS_TICKER_RE = re.compile(r"^[A-Z0-9&\-]{2,20}$")


@st.cache_data(show_spinner=False, ttl=86400)   # cache for 24 h
def resolve_to_ticker(raw: str) -> tuple[str, str]:
    """
    Given a raw stock name or ticker string, return (nse_ticker, display_name).
    Returns (raw.upper(), raw) if resolution fails — so the page still works.

    Examples:
        "Reliance Industries"  → ("RELIANCE", "Reliance Industries Ltd")
        "RELIANCE"             → ("RELIANCE", "Reliance Industries Ltd")
        "Tata Consultancy"     → ("TCS",      "Tata Consultancy Services Ltd")
        "HDFC Bank"            → ("HDFCBANK", "HDFC Bank Ltd")
    """
    raw = raw.strip()
    if not raw:
        return raw, raw

    # Step 1 — strip common exchange prefixes the user might include
    cleaned = re.sub(r"^(NSE:|BSE:|NSE/|BSE/)", "", raw, flags=re.IGNORECASE).strip()

    # Step 2 — query Yahoo Finance search
    try:
        resp = requests.get(
            YAHOO_SEARCH_URL,
            params={"q": cleaned, "lang": "en-IN", "region": "IN",
                    "quotesCount": 10, "newsCount": 0},
            headers=HEADERS,
            timeout=5,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        # Network / parse failure — fall back to raw input as ticker
        return cleaned.upper(), cleaned

    quotes = data.get("quotes", [])

    # Step 3 — prefer NSE (.NS) results
    nse_quotes = [q for q in quotes if q.get("exchange") == "NSE"
                  or q.get("symbol", "").endswith(".NS")]

    candidates = nse_quotes if nse_quotes else quotes

    if not candidates:
        return cleaned.upper(), cleaned

    best        = candidates[0]
    raw_symbol  = best.get("symbol", cleaned).replace(".NS", "").replace(".BO", "")
    name        = best.get("longname") or best.get("shortname") or raw_symbol

    return raw_symbol.upper(), name


def resolve_ticker_column(series: "pd.Series") -> "pd.DataFrame":
    """
    Takes a pandas Series of raw ticker-or-name strings.
    Returns a DataFrame with columns: raw, ticker, name.
    Adds a small delay between API calls to avoid rate-limiting.
    """
    import pandas as pd
    results = []
    seen    = {}

    for raw in series:
        raw_str = str(raw).strip()
        if raw_str in seen:
            results.append(seen[raw_str])
            continue

        ticker, name = resolve_to_ticker(raw_str)
        row = {"raw": raw_str, "ticker": ticker, "name": name}
        seen[raw_str] = row
        results.append(row)
        time.sleep(0.15)   # polite delay

    return pd.DataFrame(results)
