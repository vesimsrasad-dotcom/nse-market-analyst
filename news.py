"""
lib/news.py
News fetching and categorisation helpers for NSE Market Analyst.
"""

import yfinance as yf
import streamlit as st
from datetime import datetime


NEWS_CATEGORIES = [
    "Price-Sensitive",
    "Earnings",
    "Corporate Action",
    "Sector",
    "Macro",
    "Regulatory",
    "Rumour / Noise",
]

# Keywords for basic auto-categorisation
CATEGORY_KEYWORDS = {
    "Earnings":         ["profit", "revenue", "eps", "quarterly", "results", "q1", "q2", "q3", "q4",
                         "annual", "ebitda", "margin", "pat"],
    "Corporate Action": ["bonus", "split", "dividend", "buyback", "rights", "ofs", "qip", "merger",
                         "demerger", "delist", "allot", "preferential"],
    "Macro":            ["rbi", "repo rate", "inflation", "gdp", "cpi", "wpi", "rupee", "dollar",
                         "crude", "oil", "budget", "fiscal", "monsoon"],
    "Regulatory":       ["sebi", "cci", "nclt", "regulatory", "compliance", "penalty", "notice",
                         "order", "ban", "investigation", "probe"],
    "Price-Sensitive":  ["surges", "rallies", "plunges", "crashes", "hits 52-week",
                         "all-time high", "circuit", "block deal", "bulk deal"],
}


def categorise_headline(title: str) -> str:
    title_lower = title.lower()
    for cat, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in title_lower:
                return cat
    return "Sector"


@st.cache_data(ttl=300, show_spinner=False)
def get_market_news(max_items: int = 20) -> list[dict]:
    """Fetch general market news via Nifty 50 ticker."""
    try:
        news_raw = yf.Ticker("^NSEI").news or []
        items = []
        for n in news_raw[:max_items]:
            title = (n.get("content", {}).get("title") or n.get("title", "No title"))
            pub   = (n.get("content", {}).get("provider", {}).get("displayName") or
                     n.get("publisher", "Unknown"))
            link  = (n.get("content", {}).get("canonicalUrl", {}).get("url") or
                     n.get("link", "#"))
            ts    = (n.get("content", {}).get("pubDate") or
                     n.get("providerPublishTime", ""))
            items.append({
                "title":     title,
                "publisher": pub,
                "link":      link,
                "published": ts,
                "category":  categorise_headline(title),
            })
        return items
    except Exception:
        return []


def format_timestamp(ts) -> str:
    if not ts:
        return ""
    try:
        if isinstance(ts, (int, float)):
            return datetime.utcfromtimestamp(ts).strftime("%d %b %Y, %H:%M UTC")
        return str(ts)[:16]
    except Exception:
        return str(ts)


def news_card_html(item: dict) -> str:
    cat   = item.get("category", "General")
    title = item.get("title", "")
    pub   = item.get("publisher", "")
    link  = item.get("link", "#")
    ts    = format_timestamp(item.get("published", ""))

    cat_colors = {
        "Price-Sensitive": "#FF1744",
        "Earnings":        "#2979FF",
        "Corporate Action":"#FF6B00",
        "Macro":           "#FFD600",
        "Regulatory":      "#CE93D8",
        "Sector":          "#80DEEA",
        "Rumour / Noise":  "#888",
    }
    color = cat_colors.get(cat, "#888")

    return f"""
<div style="border-left:3px solid {color};padding:8px 14px;margin-bottom:10px;
            background:rgba(255,255,255,0.03);border-radius:4px;">
  <span style="font-size:11px;color:{color};font-weight:600;text-transform:uppercase;">{cat}</span>
  &nbsp;·&nbsp;
  <span style="font-size:11px;color:#888;">{pub}</span>
  &nbsp;·&nbsp;
  <span style="font-size:11px;color:#666;">{ts}</span>
  <br/>
  <a href="{link}" target="_blank"
     style="font-size:14px;color:#FAFAFA;text-decoration:none;line-height:1.5;">
    {title}
  </a>
</div>"""
