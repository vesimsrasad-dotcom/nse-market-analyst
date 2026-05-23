"""
lib/market_data.py
All market data fetching for NSE Market Analyst.
Uses yfinance as primary source for NSE/BSE data.
"""

import yfinance as yf
import pandas as pd
import numpy as np
import streamlit as st
from datetime import datetime, timedelta
from lib.config import (
    CACHE_TTL_QUOTES, CACHE_TTL_HISTORY, CACHE_TTL_FUNDAMENTALS,
    CHART_PERIODS, normalise_symbol
)


# ── Quote / Snapshot ──────────────────────────────────────────────────────────

@st.cache_data(ttl=CACHE_TTL_QUOTES, show_spinner=False)
def get_quote(ticker: str) -> dict:
    """Fetch live quote data for a single ticker."""
    try:
        t = yf.Ticker(ticker)

        # Try fast_info first
        price      = None
        prev_close = None
        volume     = None
        market_cap = None
        high52     = None
        low52      = None

        try:
            fi = t.fast_info
            price      = _safe_float(getattr(fi, "last_price", None))
            prev_close = _safe_float(getattr(fi, "previous_close", None))
            volume     = _safe_float(getattr(fi, "three_month_average_volume", None))
            market_cap = _safe_float(getattr(fi, "market_cap", None))
            high52     = _safe_float(getattr(fi, "year_high", None))
            low52      = _safe_float(getattr(fi, "year_low", None))
        except Exception:
            pass

        # Fallback to history
        if price is None or prev_close is None:
            try:
                hist = t.history(period="2d", interval="1d")
                if not hist.empty:
                    if price is None:
                        price = float(hist["Close"].iloc[-1])
                    if prev_close is None and len(hist) >= 2:
                        prev_close = float(hist["Close"].iloc[-2])
            except Exception:
                pass

        change = (price - prev_close) if (price is not None and prev_close) else 0.0
        pct    = (change / prev_close * 100) if prev_close else 0.0

        return {
            "ticker":     ticker,
            "price":      price,
            "prev_close": prev_close,
            "change":     change,
            "pct":        pct,
            "volume":     volume,
            "market_cap": market_cap,
            "52w_high":   high52,
            "52w_low":    low52,
        }
    except Exception as e:
        return {"ticker": ticker, "price": None, "pct": 0.0, "error": str(e)}


def _safe_float(val) -> float | None:
    """Convert a value to float, returning None on failure."""
    if val is None:
        return None
    try:
        f = float(val)
        return None if (f != f) else f  # NaN check
    except (TypeError, ValueError):
        return None


@st.cache_data(ttl=CACHE_TTL_QUOTES, show_spinner=False)
def get_multi_quotes(tickers: list[str]) -> dict[str, dict]:
    """Fetch quotes for multiple tickers at once."""
    results = {}
    for tk in tickers:
        results[tk] = get_quote(tk)
    return results


# ── Historical Price Data ─────────────────────────────────────────────────────

@st.cache_data(ttl=CACHE_TTL_HISTORY, show_spinner=False)
def get_history(ticker: str, period_key: str = "1M") -> pd.DataFrame:
    """Return OHLCV history for a ticker using CHART_PERIODS config."""
    cfg = CHART_PERIODS.get(period_key, CHART_PERIODS["1M"])
    try:
        t = yf.Ticker(ticker)
        df = t.history(period=cfg["period"], interval=cfg["interval"])
        if df.empty:
            return pd.DataFrame()
        df.index = pd.to_datetime(df.index)
        df.index = df.index.tz_localize(None) if df.index.tzinfo else df.index
        return df[["Open", "High", "Low", "Close", "Volume"]].copy()
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=CACHE_TTL_HISTORY, show_spinner=False)
def get_sparkline(ticker: str, points: int = 20) -> list[float]:
    """Return last N closing prices for a sparkline."""
    try:
        df = yf.Ticker(ticker).history(period="1mo", interval="1d")
        if df.empty:
            return []
        closes = df["Close"].dropna().tolist()
        return closes[-points:]
    except Exception:
        return []


# ── Fundamentals ──────────────────────────────────────────────────────────────

@st.cache_data(ttl=CACHE_TTL_FUNDAMENTALS, show_spinner=False)
def get_fundamentals(ticker: str) -> dict:
    """Fetch full info dict from yfinance for fundamental analysis."""
    try:
        info = yf.Ticker(ticker).info
        return info
    except Exception as e:
        return {"error": str(e)}


@st.cache_data(ttl=CACHE_TTL_FUNDAMENTALS, show_spinner=False)
def get_financials(ticker: str) -> dict:
    """Fetch income statement, balance sheet, cash flow."""
    try:
        t = yf.Ticker(ticker)
        return {
            "income":     t.financials,
            "balance":    t.balance_sheet,
            "cashflow":   t.cashflow,
            "quarterly":  t.quarterly_financials,
        }
    except Exception as e:
        return {"error": str(e)}


# ── Technical Indicators ──────────────────────────────────────────────────────

def compute_technicals(df: pd.DataFrame) -> dict:
    """
    Compute common technical indicators on a price DataFrame.
    Returns dict with indicator values (scalar or series).
    """
    if df.empty or "Close" not in df.columns:
        return {}

    close = df["Close"]
    result = {}

    # Moving averages
    for ma in [20, 50, 100, 200]:
        if len(close) >= ma:
            result[f"ma{ma}"] = close.rolling(ma).mean().iloc[-1]

    # RSI (14-period)
    if len(close) >= 15:
        delta = close.diff()
        gain  = delta.clip(lower=0)
        loss  = -delta.clip(upper=0)
        avg_gain = gain.ewm(com=13, min_periods=14).mean()
        avg_loss = loss.ewm(com=13, min_periods=14).mean()
        rs  = avg_gain / avg_loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))
        result["rsi"] = rsi.iloc[-1]

    # MACD
    if len(close) >= 26:
        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        macd  = ema12 - ema26
        signal = macd.ewm(span=9, adjust=False).mean()
        result["macd"]        = macd.iloc[-1]
        result["macd_signal"] = signal.iloc[-1]
        result["macd_hist"]   = (macd - signal).iloc[-1]

    # Bollinger Bands (20-period)
    if len(close) >= 20:
        mid  = close.rolling(20).mean()
        std  = close.rolling(20).std()
        result["bb_upper"] = (mid + 2 * std).iloc[-1]
        result["bb_mid"]   = mid.iloc[-1]
        result["bb_lower"] = (mid - 2 * std).iloc[-1]

    # ATR (14-period)
    if "High" in df.columns and "Low" in df.columns and len(df) >= 15:
        high, low = df["High"], df["Low"]
        tr = pd.concat([
            high - low,
            (high - close.shift()).abs(),
            (low  - close.shift()).abs(),
        ], axis=1).max(axis=1)
        result["atr"] = tr.rolling(14).mean().iloc[-1]

    # Current price and price stats
    result["current"]  = close.iloc[-1]
    result["52w_high"] = close.max()
    result["52w_low"]  = close.min()
    result["pct_from_52w_high"] = (close.iloc[-1] / close.max() - 1) * 100
    result["pct_from_52w_low"]  = (close.iloc[-1] / close.min() - 1) * 100

    return result


def rsi_label(rsi: float) -> str:
    if rsi is None:
        return "Unavailable"
    if rsi >= 70:
        return "Overbought zone"
    if rsi >= 55:
        return "Firm momentum"
    if rsi >= 45:
        return "Neutral momentum"
    if rsi >= 30:
        return "Weak momentum"
    return "Oversold zone"


def trend_label(price: float, ma200: float | None) -> str:
    if ma200 is None:
        return "200-DMA unavailable"
    return "Above 200-DMA" if price > ma200 else "Below 200-DMA"


def pe_tier(pe: float | None) -> str:
    if pe is None:
        return "P/E unavailable"
    if pe < 0:
        return "Loss-making"
    if pe < 15:
        return "Lower valuation"
    if pe < 25:
        return "Fair valuation"
    if pe < 40:
        return "Higher valuation"
    return "Elevated valuation"


def roe_tier(roe: float | None) -> str:
    if roe is None:
        return "ROE unavailable"
    roe_pct = roe * 100 if abs(roe) < 5 else roe  # handle decimal vs percent
    if roe_pct >= 20:
        return "Strong profitability"
    if roe_pct >= 12:
        return "Moderate profitability"
    return "Weak profitability"


def de_tier(de: float | None) -> str:
    if de is None:
        return "D/E unavailable"
    if de < 0.5:
        return "Low leverage"
    if de < 1.5:
        return "Moderate leverage"
    return "Elevated leverage"


def beta_label(beta: float | None) -> str:
    if beta is None:
        return "Beta unavailable"
    if beta < 0.7:
        return "Low volatility vs market"
    if beta < 1.2:
        return "In-line with market"
    return "Higher volatility vs market"


def week52_position(price: float, high52: float, low52: float) -> str:
    if not high52 or not low52:
        return "Unavailable"
    rng  = high52 - low52
    if rng == 0:
        return "Flat range"
    pos = (price - low52) / rng
    if pos >= 0.8:
        return "Near 52-week high"
    if pos >= 0.5:
        return "Upper half of 52-week range"
    if pos >= 0.2:
        return "Lower half of 52-week range"
    return "Near 52-week low"


# ── Sector Performance ────────────────────────────────────────────────────────

@st.cache_data(ttl=CACHE_TTL_HISTORY, show_spinner=False)
def get_sector_returns(sector_map: dict, period_key: str = "1M") -> pd.DataFrame:
    """Return % return for each sector index over the given period."""
    rows = []
    for name, ticker in sector_map.items():
        df = get_history(ticker, period_key)
        if df.empty:
            continue
        ret = (df["Close"].iloc[-1] / df["Close"].iloc[0] - 1) * 100
        rows.append({"Sector": name, "Return (%)": round(ret, 2)})
    return pd.DataFrame(rows).sort_values("Return (%)", ascending=False)


# ── Market Cap Formatting ─────────────────────────────────────────────────────

def format_market_cap(mc: float | None) -> str:
    if mc is None:
        return "N/A"
    cr = mc / 1e7  # Convert to Crore (1 Cr = 10M)
    if cr >= 1_00_000:
        return f"₹{cr/1_00_000:.2f} Lakh Cr"
    return f"₹{cr:,.0f} Cr"


def format_inr(val: float | None, decimals: int = 2) -> str:
    if val is None:
        return "N/A"
    return f"₹{val:,.{decimals}f}"


# ── News ──────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=300, show_spinner=False)
def get_stock_news(ticker: str, max_items: int = 10) -> list[dict]:
    """Fetch news for a ticker via yfinance."""
    try:
        news_raw = yf.Ticker(ticker).news or []
        items = []
        for n in news_raw[:max_items]:
            items.append({
                "title":     n.get("content", {}).get("title", n.get("title", "No title")),
                "publisher": n.get("content", {}).get("provider", {}).get("displayName",
                             n.get("publisher", "Unknown")),
                "link":      (n.get("content", {}).get("canonicalUrl", {}).get("url") or
                              n.get("link", "#")),
                "published": n.get("content", {}).get("pubDate", n.get("providerPublishTime", "")),
            })
        return items
    except Exception:
        return []


# ── Portfolio Helpers ─────────────────────────────────────────────────────────

def enrich_portfolio(holdings: list[dict]) -> pd.DataFrame:
    """
    Given a list of {ticker, qty, avg_cost, sector, notes},
    fetch current prices and compute P&L.
    """
    rows = []
    for h in holdings:
        ticker = normalise_symbol(h["ticker"])
        q      = get_quote(ticker)
        price  = q.get("price") or 0
        cost   = h.get("avg_cost", 0)
        qty    = h.get("qty", 0)

        invested = cost * qty
        current  = price * qty
        pnl      = current - invested
        pnl_pct  = (pnl / invested * 100) if invested else 0

        rows.append({
            "Ticker":       ticker,
            "Name":         h.get("name", ticker.replace(".NS", "")),
            "Qty":          qty,
            "Avg Cost":     cost,
            "CMP":          price,
            "Invested (₹)": invested,
            "Value (₹)":    current,
            "P&L (₹)":      pnl,
            "P&L (%)":      pnl_pct,
            "Sector":       h.get("sector", "Unknown"),
            "Notes":        h.get("notes", ""),
        })

    return pd.DataFrame(rows)
