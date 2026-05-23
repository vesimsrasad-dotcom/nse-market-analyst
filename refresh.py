"""
lib/refresh.py
Market hours awareness and refresh utilities for NSE Market Analyst.
"""

from datetime import datetime
import pytz

IST = pytz.timezone("Asia/Kolkata")

# NSE trading hours
MARKET_OPEN_H,  MARKET_OPEN_M  = 9,  15
MARKET_CLOSE_H, MARKET_CLOSE_M = 15, 30

# Pre-open session
PRE_OPEN_H, PRE_OPEN_M = 9, 0


def now_ist() -> datetime:
    return datetime.now(IST)


def is_market_open() -> bool:
    now = now_ist()
    if now.weekday() >= 5:          # Sat=5, Sun=6
        return False
    market_open  = now.replace(hour=MARKET_OPEN_H,  minute=MARKET_OPEN_M,  second=0, microsecond=0)
    market_close = now.replace(hour=MARKET_CLOSE_H, minute=MARKET_CLOSE_M, second=0, microsecond=0)
    return market_open <= now <= market_close


def is_pre_open() -> bool:
    now = now_ist()
    if now.weekday() >= 5:
        return False
    pre_open     = now.replace(hour=PRE_OPEN_H,     minute=PRE_OPEN_M,     second=0, microsecond=0)
    market_open  = now.replace(hour=MARKET_OPEN_H,  minute=MARKET_OPEN_M,  second=0, microsecond=0)
    return pre_open <= now < market_open


def market_status() -> dict:
    """Return status dict with label, color, and refresh interval (ms)."""
    now = now_ist()
    if now.weekday() >= 5:
        return {"label": "🔴 Weekend — Market Closed", "color": "#FF1744",
                "interval_ms": 600_000, "badge": "CLOSED"}
    if is_market_open():
        return {"label": "🟢 NSE Market Open",        "color": "#00C853",
                "interval_ms": 30_000,  "badge": "LIVE"}
    if is_pre_open():
        return {"label": "🟡 Pre-Open Session",        "color": "#FFD600",
                "interval_ms": 15_000,  "badge": "PRE-OPEN"}

    close_time = now.replace(hour=MARKET_CLOSE_H, minute=MARKET_CLOSE_M)
    if now > close_time:
        return {"label": "🔴 Market Closed (After Hours)", "color": "#FF1744",
                "interval_ms": 300_000, "badge": "CLOSED"}

    return {"label": "🔴 Market Closed (Before Hours)", "color": "#FF1744",
            "interval_ms": 300_000, "badge": "CLOSED"}


def timestamp_ist() -> str:
    return now_ist().strftime("%d %b %Y, %H:%M:%S IST")


def refresh_interval_ms() -> int:
    return market_status()["interval_ms"]
