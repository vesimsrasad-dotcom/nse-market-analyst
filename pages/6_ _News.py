"""
pages/6_ _News.py
News & Corporate Actions page.
"""

import streamlit as st
from streamlit_autorefresh import st_autorefresh
from lib.refresh import market_status, timestamp_ist
from lib.config import DISCLAIMER, ANTHROPIC_API_KEY, normalise_symbol, POPULAR_STOCKS
from lib.market_data import get_stock_news
from lib.news import get_market_news, news_card_html, NEWS_CATEGORIES, categorise_headline
from lib.claude_analyst import analyse_news, explain_corporate_action

_ms_status = market_status()
_count_news = st_autorefresh(interval=_ms_status["interval_ms"], key="news_autorefresh")
st.set_page_config(page_title="News | NSE Market Analyst",
                   page_icon="📰", layout="wide")

st.markdown("""
<style>
  html, body, [class*="css"] { font-size: 17px !important; }
  .disclaimer { font-size:11px; color:#555; text-align:center;
    border-top:1px solid #222; padding-top:10px; margin-top:30px; }
</style>
""", unsafe_allow_html=True)

col_h1, col_h2 = st.columns([4,1])
with col_h1:
    st.markdown("📰 News & Corporate Actions")
    st.caption("Market news, stock-specific updates, and corporate action explainer")
with col_h2:
    st.markdown(f"""
    <div style="text-align:right;padding-top:10px;">
      <span style="font-size:13px;color={_ms_status['color']};font-weight:700;">{_ms_status['label']}</span><br>
      <span style="font-size:11px;color:#555;">{timestamp_ist()}</span>
    </div>""", unsafe_allow_html=True)
    if st.button("🔄 Refresh", key="news6_manual_refresh"):
        st.cache_data.clear()
        st.rerun()

tab_market, tab_stock, tab_corp = st.tabs([
    "🌐 Market News", "🔍 Stock News", "📋 Corporate Action Explainer"
])

# ── Market News ───────────────────────────────────────────────────────────────
with tab_market:
    cat_filter = st.multiselect(
        "Filter by category", NEWS_CATEGORIES,
        default=NEWS_CATEGORIES, key="news_cat_filter",
    )
    with st.spinner("Loading market news…"):
        news_items = get_market_news(max_items=25)

    if not news_items:
        st.warning("Could not fetch news. yfinance news availability varies.")
    else:
        for item in news_items:
            if item.get("category") in cat_filter:
                st.markdown(news_card_html(item), unsafe_allow_html=True)

# ── Stock News ────────────────────────────────────────────────────────────────
with tab_stock:
    c1, c2 = st.columns([3, 1])
    with c1:
        raw_ticker = st.text_input("Stock symbol", value="RELIANCE",
                                   placeholder="e.g. TCS, INFY", key="news_ticker")
    with c2:
        st.markdown("<br>", unsafe_allow_html=True)
        pop = st.selectbox("Popular", ["—"] + POPULAR_STOCKS, key="news_pop",
                            label_visibility="collapsed")
        if pop != "—":
            raw_ticker = pop

    ticker  = normalise_symbol(raw_ticker)
    company = ticker.replace(".NS", "").replace(".BO", "")

    with st.spinner(f"Fetching news for {ticker}…"):
        stock_news = get_stock_news(ticker, max_items=15)

    if not stock_news:
        st.info(f"No recent news found for {ticker} via yfinance.")
    else:
        for item in stock_news:
            item["category"] = categorise_headline(item.get("title", ""))
            st.markdown(news_card_html(item), unsafe_allow_html=True)

    st.divider()
    st.markdown("#### 🤖 AI News Analysis")
    if not ANTHROPIC_API_KEY:
        st.warning("Add `ANTHROPIC_API_KEY` to enable AI news analysis.")
    elif stock_news:
        if st.button("Analyse News", type="primary", key="news_ai_btn"):
            with st.spinner("Claude is analysing the news…"):
                analysis = analyse_news(ticker, company, stock_news)
            st.markdown(analysis)
    else:
        st.info("No news items to analyse.")

# ── Corporate Action Explainer ────────────────────────────────────────────────
with tab_corp:
    st.markdown("### Corporate Action Explainer")
    st.caption("Understand what a corporate action means for your holding (educational only)")

    CORP_ACTIONS = [
        "Bonus Issue", "Stock Split", "Dividend", "Buyback",
        "Rights Issue", "OFS (Offer for Sale)", "QIP",
        "Preferential Allotment", "Merger", "Demerger", "Delisting",
    ]

    c1, c2 = st.columns([2, 2])
    with c1:
        action_type = st.selectbox("Select corporate action", CORP_ACTIONS, key="corp_action")
    with c2:
        corp_company = st.text_input("Company name (optional)", key="corp_company",
                                      placeholder="e.g. Reliance Industries")

    details = st.text_area(
        "Action details (optional)",
        placeholder="e.g. 1:1 bonus issue, record date 15 June 2025",
        key="corp_details",
    )

    if st.button("Explain this Action", type="primary", key="corp_explain_btn"):
        if not ANTHROPIC_API_KEY:
            st.warning("Add `ANTHROPIC_API_KEY` to enable explanations.")
        else:
            with st.spinner("Claude is explaining the corporate action…"):
                explanation = explain_corporate_action(
                    action_type,
                    corp_company or "the company",
                    details or "No specific details provided.",
                )
            st.markdown(explanation)

    # Quick reference table
    st.divider()
    st.markdown("#### Quick Reference: Corporate Actions")
    ref_data = {
        "Action":      ["Bonus", "Split", "Dividend", "Buyback", "Rights Issue"],
        "Shares":      ["Increase", "Increase", "No change", "Decrease", "Increase"],
        "Price":       ["Adjusts down", "Adjusts down", "Adjusts on ex-date", "May rise", "Below market"],
        "Market Cap":  ["No change", "No change", "Slight decrease", "Decreases", "Increases"],
        "Cash to Investor": ["No", "No", "Yes", "For participants", "Requires payment"],
    }
    import pandas as pd
    st.dataframe(pd.DataFrame(ref_data), use_container_width=True, hide_index=True)
    st.caption("Educational reference only. Tax treatment and specifics vary.")

st.markdown(f'<div class="disclaimer">{DISCLAIMER}</div>', unsafe_allow_html=True)
