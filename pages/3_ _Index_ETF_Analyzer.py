"""
pages/3_ _Index_ETF_Analyzer.py
Indian Index / ETF Analyzer.
"""

import streamlit as st
from lib.auth import check_password, logout_button
from streamlit_autorefresh import st_autorefresh
from lib.refresh import market_status, timestamp_ist
from lib.config import DISCLAIMER, CHART_PERIODS, INDIA_ETFS, INDICES, ANTHROPIC_API_KEY
from lib.market_data import get_fundamentals, get_history, get_quote, format_market_cap
from lib.charts import price_chart, add_ma_overlays
from lib.claude_analyst import analyse_etf

if not check_password(): st.stop()
_ms_status = market_status()
_count_etf = st_autorefresh(interval=_ms_status["interval_ms"], key="etf_autorefresh")
st.set_page_config(page_title="Index / ETF Analyzer | NSE Market Analyst",
                   page_icon="📦", layout="wide")

st.markdown("""
<style>
  html, body, [class*="css"] { font-size: 17px !important; }
  .etf-card { background:#1A1F2E; border-radius:10px; padding:16px 20px;
              border:1px solid rgba(255,255,255,0.06); margin-bottom:12px; }
  .disclaimer { font-size:11px; color:#555; text-align:center;
    border-top:1px solid #222; padding-top:10px; margin-top:30px; }
</style>
""", unsafe_allow_html=True)

st.markdown("## 📦 Index / ETF Analyzer")
st.caption("Indian ETFs and index instruments — educational overview")

# ── Selection ─────────────────────────────────────────────────────────────────
mode = st.radio("Analyse", ["Indian ETF", "NSE Index"], horizontal=True, key="etf_mode")

if mode == "Indian ETF":
    etf_name = st.selectbox("Select ETF", list(INDIA_ETFS.keys()), key="etf_select")
    ticker   = INDIA_ETFS[etf_name]["ticker"]
    tracking = INDIA_ETFS[etf_name]["index"]
else:
    idx_name = st.selectbox("Select Index", list(INDICES.keys()), key="idx_select")
    ticker   = INDICES[idx_name]["ticker"]
    tracking = idx_name
    etf_name = idx_name

period_key = st.radio("History period", list(CHART_PERIODS.keys()),
                      horizontal=True, index=5, key="etf_period")

# ── Load Data ─────────────────────────────────────────────────────────────────
with st.spinner(f"Loading {ticker}…"):
    quote = get_quote(ticker)
    info  = get_fundamentals(ticker)
    df    = get_history(ticker, period_key)

price = quote.get("price")
pct   = quote.get("pct", 0)
mc    = info.get("marketCap") or quote.get("market_cap")
up    = pct >= 0

# ── ETF Header ────────────────────────────────────────────────────────────────
c1, c2 = st.columns([3, 1])
with c1:
    st.markdown(f"### {etf_name}")
    st.caption(f"Ticker: `{ticker}` · Tracking: **{tracking}**")
with c2:
    if price:
        st.metric(
            label="Price / NAV",
            value=f"₹{price:,.2f}",
            delta=f"{pct:+.2f}%",
        )

# ── Key Stats ─────────────────────────────────────────────────────────────────
stat_cols = st.columns(5)
stats = {
    "Market Cap / AUM": format_market_cap(mc),
    "Expense Ratio":    f"{info.get('annualReportExpenseRatio', 0)*100:.2f}%" if info.get("annualReportExpenseRatio") else "N/A",
    "52W High":         f"₹{info.get('fiftyTwoWeekHigh', 0):,.2f}" if info.get("fiftyTwoWeekHigh") else "N/A",
    "52W Low":          f"₹{info.get('fiftyTwoWeekLow', 0):,.2f}"  if info.get("fiftyTwoWeekLow")  else "N/A",
    "Volume":           f"{quote.get('volume', 0):,}"               if quote.get("volume") else "N/A",
}
for col, (k, v) in zip(stat_cols, stats.items()):
    with col:
        st.metric(k, v)

# ── Returns Table ─────────────────────────────────────────────────────────────
st.markdown("#### Period Returns")
returns_data = []
for pk in ["1M", "3M", "6M", "YTD", "1Y", "3Y", "5Y"]:
    df_p = get_history(ticker, pk)
    if df_p.empty:
        continue
    ret = (df_p["Close"].iloc[-1] / df_p["Close"].iloc[0] - 1) * 100
    returns_data.append({"Period": pk, "Return (%)": round(ret, 2)})

if returns_data:
    import pandas as pd
    df_ret = pd.DataFrame(returns_data)
    ret_cols = st.columns(len(df_ret))
    for col, (_, row) in zip(ret_cols, df_ret.iterrows()):
        with col:
            color = "#00C853" if row["Return (%)"] >= 0 else "#FF1744"
            st.markdown(f"""
            <div style="text-align:center;background:#1A1F2E;border-radius:8px;padding:10px;">
              <div style="font-size:12px;color:#888;">{row['Period']}</div>
              <div style="font-size:18px;font-weight:700;color:{color};">
                {row['Return (%)']:+.1f}%
              </div>
            </div>""", unsafe_allow_html=True)

st.divider()

# ── Price Chart ───────────────────────────────────────────────────────────────
chart_type = st.radio("Chart type", ["Area", "Price", "Candlestick", "Performance"],
                      horizontal=True, key="etf_chart_type")
show_ma = st.multiselect("Moving averages", [20, 50, 100, 200],
                          default=[50, 200], key="etf_ma")

if not df.empty:
    fig = price_chart(df, etf_name, chart_type)
    if show_ma and chart_type != "Candlestick":
        fig = add_ma_overlays(fig, df, show_ma)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
else:
    st.warning("No price data available.")

# ── Holdings ──────────────────────────────────────────────────────────────────
with st.expander("📋 Top Holdings (if available)"):
    holdings = info.get("holdings")
    if holdings:
        import pandas as pd
        df_h = pd.DataFrame(holdings)
        st.dataframe(df_h, use_container_width=True, hide_index=True)
    else:
        st.info("Top holdings data not available from yfinance for this ETF. "
                "Check the fund house website for latest holdings.")

# ── Notes ─────────────────────────────────────────────────────────────────────
st.markdown("""
> **Tracking Error Note:** ETF tracking error data is not available via yfinance.
> For precise tracking error metrics, refer to the fund's fact sheet on the AMC website.
""")

# ── AI Analysis ───────────────────────────────────────────────────────────────
with st.expander("🤖 AI Analysis"):
    if not ANTHROPIC_API_KEY:
        st.warning("Add `ANTHROPIC_API_KEY` to your `.env` file to enable AI analysis.")
    else:
        if st.button("Generate AI Analysis", type="primary", key="etf_ai_btn"):
            hist_summary = ""
            if returns_data:
                hist_summary = ", ".join([f"{r['Period']}: {r['Return (%)']:+.1f}%" for r in returns_data])
            with st.spinner("Claude is analysing…"):
                analysis = analyse_etf(etf_name, ticker, info, hist_summary)
            st.markdown(analysis)

st.markdown(f'<div class="disclaimer">{DISCLAIMER}</div>', unsafe_allow_html=True)
