"""
lib/config.py
Central configuration for NSE Market Analyst.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── API Keys ─────────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# ── App Meta ──────────────────────────────────────────────────────────────────
APP_TITLE = "NSE Market Analyst"
APP_ICON = "📊"
APP_VERSION = "1.0.0"

DISCLAIMER = (
    "This dashboard is for educational and informational purposes only. "
    "It is not financial advice, not a recommendation to buy or sell any security, "
    "and is not personalized to your financial situation. "
    "Please consult a SEBI-registered investment adviser before making investment decisions."
)

# ── Cache TTLs (seconds) ──────────────────────────────────────────────────────
CACHE_TTL_QUOTES = 60
CACHE_TTL_HISTORY = 300
CACHE_TTL_FUNDAMENTALS = 86400  # 1 day

# ── Indian Market Indices ─────────────────────────────────────────────────────
INDICES = {
    "Nifty 50":      {"ticker": "^NSEI",      "emoji": "🔵"},
    "Bank Nifty":    {"ticker": "^NSEBANK",   "emoji": "🏦"},
    "Sensex":        {"ticker": "^BSESN",     "emoji": "🔴"},
    "Nifty IT":      {"ticker": "^CNXIT",     "emoji": "💻"},
    "Nifty Pharma":  {"ticker": "^CNXPHARMA", "emoji": "💊"},
    "Nifty Auto":    {"ticker": "^CNXAUTO",   "emoji": "🚗"},
    "Nifty Metal":   {"ticker": "^CNXMETAL",  "emoji": "⚙️"},
    "Nifty FMCG":    {"ticker": "^CNXFMCG",  "emoji": "🛒"},
    "Nifty Realty":  {"ticker": "^CNXREALTY", "emoji": "🏢"},
    "Nifty Energy":  {"ticker": "^CNXENERGY", "emoji": "⚡"},
    "Nifty Next 50":    {"ticker": "^NSMIDCP",      "emoji": "📊"},
    "Nifty Smallcap":  {"ticker": "^CNXSMALLCAP",     "emoji": "🔹"},
    "Bitcoin":       {"ticker": "BTC-USD",      "emoji": "₿"},
    "India VIX":     {"ticker": "^INDIAVIX",  "emoji": "📉"},
    "USD/INR":       {"ticker": "INR=X",      "emoji": "💱"},
    "Gold":          {"ticker": "GC=F",       "emoji": "🥇"},
    "Crude Oil":     {"ticker": "CL=F",       "emoji": "🛢️"},
}

# Cards shown on market pulse page (subset of INDICES)
MARKET_PULSE_CARDS = [
    "Nifty 50", "Bank Nifty", "Sensex", "Nifty IT",
    "Nifty Pharma", "Nifty Auto", "Nifty Metal", "Nifty FMCG",
    "India VIX", "USD/INR", "Gold", "Crude Oil",
    "Nifty Next 50", "Nifty Smallcap", "Bitcoin",
]

# Sector indices for sector performance chart
SECTOR_INDICES = {
    "IT":      "^CNXIT",
    "Bank":    "^NSEBANK",
    "Pharma":  "^CNXPHARMA",
    "Auto":    "^CNXAUTO",
    "Metal":   "^CNXMETAL",
    "FMCG":    "^CNXFMCG",
    "Realty":  "^CNXREALTY",
    "Energy":  "^CNXENERGY",
}

# ── Symbol Normaliser ─────────────────────────────────────────────────────────
SYMBOL_OVERRIDES = {
    # Common aliases
    "NIFTY":       "^NSEI",
    "SENSEX":      "^BSESN",
    "BANKNIFTY":   "^NSEBANK",
    "NIFTYIT":     "^CNXIT",
}

def normalise_symbol(raw: str) -> str:
    """
    Convert user-entered symbol to yfinance-compatible ticker.
    RELIANCE -> RELIANCE.NS
    RELIANCE.NS -> RELIANCE.NS  (passthrough)
    RELIANCE.BO -> RELIANCE.BO  (passthrough)
    """
    raw = raw.strip().upper()
    if raw in SYMBOL_OVERRIDES:
        return SYMBOL_OVERRIDES[raw]
    if raw.startswith("^") or "=X" in raw or "=F" in raw:
        return raw
    if raw.endswith(".NS") or raw.endswith(".BO"):
        return raw
    return raw + ".NS"

# ── Popular NSE Stocks ────────────────────────────────────────────────────────
POPULAR_STOCKS = [
    "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK",
    "HINDUNILVR", "ITC", "SBIN", "BAJFINANCE", "BHARTIARTL",
    "KOTAKBANK", "LT", "HCLTECH", "ASIANPAINT", "AXISBANK",
    "MARUTI", "SUNPHARMA", "TITAN", "WIPRO", "ULTRACEMCO",
]

# ── Indian ETFs ───────────────────────────────────────────────────────────────
INDIA_ETFS = {
    "NiftyBeES":       {"ticker": "NIFTYBEES.NS", "index": "Nifty 50"},
    "BankBeES":        {"ticker": "BANKBEES.NS",  "index": "Bank Nifty"},
    "JuniorBeES":      {"ticker": "JUNIORBEES.NS","index": "Nifty Next 50"},
    "Bharat 22 ETF":   {"ticker": "BHARATIETF.NS","index": "Bharat 22"},
    "CPSE ETF":        {"ticker": "CPSEETF.NS",   "index": "CPSE Index"},
    "GoldBeES":        {"ticker": "GOLDBEES.NS",  "index": "Domestic Gold"},
    "ITBEES":          {"ticker": "ITBEES.NS",    "index": "Nifty IT"},
    "PSU Bank BeES":   {"ticker": "PSUBNKBEES.NS","index": "Nifty PSU Bank"},
}

# ── Chart Periods ─────────────────────────────────────────────────────────────
CHART_PERIODS = {
    "1D":  {"period": "1d",  "interval": "5m"},
    "5D":  {"period": "5d",  "interval": "30m"},
    "1M":  {"period": "1mo", "interval": "1d"},
    "3M":  {"period": "3mo", "interval": "1d"},
    "6M":  {"period": "6mo", "interval": "1d"},
    "YTD": {"period": "ytd", "interval": "1d"},
    "1Y":  {"period": "1y",  "interval": "1wk"},
    "3Y":  {"period": "3y",  "interval": "1wk"},
    "5Y":  {"period": "5y",  "interval": "1mo"},
    "Max": {"period": "max", "interval": "1mo"},
}

# ── Colour Palette ────────────────────────────────────────────────────────────
COLOR_GREEN  = "#00C853"
COLOR_RED    = "#FF1744"
COLOR_ORANGE = "#FF6B00"
COLOR_BLUE   = "#2979FF"
COLOR_GOLD   = "#FFD600"
COLOR_BG     = "#0E1117"
COLOR_CARD   = "#1A1F2E"

# ── Claude Model ─────────────────────────────────────────────────────────────
CLAUDE_MODEL = "claude-sonnet-4-20250514"
CLAUDE_MAX_TOKENS = 1800

# ── Private Access ────────────────────────────────────────────────────────────
# Set DASHBOARD_PASSWORD in your .env or Streamlit Secrets to enable password protection
# Leave empty string "" to disable password protection
DASHBOARD_PASSWORD = os.getenv("DASHBOARD_PASSWORD", "")
