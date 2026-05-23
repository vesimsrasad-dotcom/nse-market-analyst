"""
app.py
NSE Market Analyst — Landing page with real-time Indian market snapshot.
Auto-refreshes every 30s during market hours, 5 min after hours.
"""

import streamlit as st
from streamlit_autorefresh import st_autorefresh
from lib.config import (
    APP_TITLE, APP_ICON, DISCLAIMER,
    INDICES, MARKET_PULSE_CARDS, SECTOR_INDICES, CHART_PERIODS,
)
from lib.market_data import get_multi_quotes, get_sparkline, get_history, get_sector_returns
from lib.charts import sparkline, sector_bar, price_chart
from lib.refresh import market_status, timestamp_ist, refresh_interval_ms

# ── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title=APP_TITLE,
    page_icon=APP_ICON,
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Auto-Refresh ──────────────────────────────────────────────────────────────
status  = market_status()
_count  = st_autorefresh(interval=status["interval_ms"], key="home_refresh")

# ── Global CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  html, body, [class*="css"] { font-size: 17px !important; }
  .metric-card {
    background: #1A1F2E; border-radius: 10px;
    padding: 14px 16px; margin-bottom: 4px;
    border: 1px solid rgba(255,255,255,0.06);
  }
  .metric-name  { font-size: 12px; color: #888; text-transform: uppercase; letter-spacing: 0.06em; }
  .metric-value { font-size: 22px; font-weight: 700; color: #FAFAFA; margin: 2px 0; }
  .metric-pct   { font-size: 14px; font-weight: 600; }
  .green { color: #00C853; } .red { color: #FF1744; }
  .status-badge {
    display: inline-block; padding: 4px 12px; border-radius: 20px;
    font-size: 12px; font-weight: 700; letter-spacing: 0.05em;
  }
  .disclaimer {
    font-size: 11px; color: #555; text-align: center;
    border-top: 1px solid #222; padding-top: 10px; margin-top: 30px;
  }
  div[data-testid="stSidebarContent"] { background: #0E1117; }
  .sidebar-brand { font-size: 20px; font-weight: 700; color: #FF6B00; }
</style>
""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="sidebar-brand">📊 NSE Market Analyst</div>', unsafe_allow_html=True)
    st.caption("Educational market research tool")
    st.divider()
    st.markdown("**Navigate**")
    st.page_link("pages/1_ _Market_Pulse.py",       label="📈 Market Pulse")
    st.page_link("pages/2_ _Stock_Analyzer.py",     label="🔍 Stock Analyzer")
    st.page_link("pages/3_ _Index_ETF_Analyzer.py", label="📦 Index / ETF Analyzer")
    st.page_link("pages/4_ _India_Macro.py",        label="🌏 India Macro")
    st.page_link("pages/5_ _Portfolio.py",          label="💼 Portfolio")
    st.page_link("pages/6_ _News.py",               label="📰 News")
    st.divider()

    # Refresh info in sidebar
    st.markdown("**Live Data**")
    st.markdown(f"""
    <div style="font-size:13px; color:{status['color']}; font-weight:600;">
      {status['label']}
    </div>
    <div style="font-size:11px; color:#555; margin-top:4px;">
      Refreshes every {status['interval_ms']//1000}s
    </div>
    """, unsafe_allow_html=True)
    st.caption(f"🕐 {timestamp_ist()}")
    if st.button("🔄 Force Refresh", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    st.divider()
    st.caption("Data: yfinance · AI: Claude API")

# ── Header ────────────────────────────────────────────────────────────────────
col_h1, col_h2 = st.columns([4, 1])
with col_h1:
    st.markdown("## 📊 NSE Market Analyst")
    st.markdown("*Indian equity market research dashboard — for educational use only*")
with col_h2:
    st.markdown(f"""
    <div style="text-align:right; padding-top:10px;">
      <span class="status-badge" style="background:rgba(0,200,83,0.12);color:{status['color']};">
        {status['badge']}
      </span><br>
      <span style="font-size:11px; color:#555;">{timestamp_ist()}</span>
    </div>
    """, unsafe_allow_html=True)

st.divider()

# ── Market Snapshot Cards ─────────────────────────────────────────────────────
pulse_tickers = [INDICES[name]["ticker"] for name in MARKET_PULSE_CARDS]
with st.spinner("Loading market data…"):
    quotes = get_multi_quotes(pulse_tickers)

cols = st.columns(4)
for i, name in enumerate(MARKET_PULSE_CARDS):
    tk    = INDICES[name]["ticker"]
    q     = quotes.get(tk, {})
    price = q.get("price")
    pct   = q.get("pct", 0)
    up    = pct >= 0
    emoji = INDICES[name]["emoji"]
    spark = get_sparkline(tk)

    with cols[i % 4]:
        price_str = f"{price:,.2f}" if price else "—"
        pct_str   = f"{'▲' if up else '▼'} {abs(pct):.2f}%"
        pct_class = "green" if up else "red"
        st.markdown(f"""
        <div class="metric-card">
          <div class="metric-name">{emoji} {name}</div>
          <div class="metric-value">{price_str}</div>
          <div class="metric-pct {pct_class}">{pct_str}</div>
        </div>
        """, unsafe_allow_html=True)
        if spark:
            fig = sparkline(spark, positive=up)
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

st.divider()

# ── Main Nifty Chart ──────────────────────────────────────────────────────────
col1, col2 = st.columns([3, 1])
with col1:
    st.markdown("### Nifty 50 — Price Chart")
with col2:
    period_key = st.selectbox("Period", list(CHART_PERIODS.keys()), index=2,
                              key="home_period", label_visibility="collapsed")

chart_type = st.radio("Chart type", ["Area", "Price", "Candlestick", "Performance"],
                      horizontal=True, key="home_chart_type")

nifty_df = get_history("^NSEI", period_key)
if not nifty_df.empty:
    fig = price_chart(nifty_df, "Nifty 50", chart_type)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
else:
    st.warning("Could not load Nifty 50 data.")

st.divider()

# ── Sector Performance ────────────────────────────────────────────────────────
st.markdown("### NSE Sector Performance")
sec_period = st.radio("Sector period", ["1M", "3M", "6M", "YTD", "1Y"],
                      horizontal=True, key="home_sector_period")
with st.spinner("Loading sector data…"):
    df_sec = get_sector_returns(SECTOR_INDICES, sec_period)

if not df_sec.empty:
    fig_sec = sector_bar(df_sec, sec_period)
    st.plotly_chart(fig_sec, use_container_width=True, config={"displayModeBar": False})
    st.dataframe(
        df_sec.style.format({"Return (%)": "{:+.2f}%"})
              .background_gradient(subset=["Return (%)"], cmap="RdYlGn", vmin=-10, vmax=10),
        use_container_width=True, hide_index=True,
    )
else:
    st.info("Sector data loading…")


# ── Live Countdown Timer ──────────────────────────────────────────────────────
interval_s = status["interval_ms"] // 1000
st.markdown(f"""
<div id="nse-countdown" style="text-align:center;font-size:12px;color:#444;margin:8px 0;">
  Next refresh in <span id="nse-timer" style="color:#FF6B00;font-weight:700;">{interval_s}</span>s
</div>
<script>
(function() {{
  var secs = {interval_s};
  var el = document.getElementById("nse-timer");
  if (!el) return;
  var t = setInterval(function() {{
    secs--;
    if (secs <= 0) {{ secs = {interval_s}; }}
    if (el) el.textContent = secs;
  }}, 1000);
}})();
</script>
""", unsafe_allow_html=True)

# ── Disclaimer ────────────────────────────────────────────────────────────────
st.markdown(f'<div class="disclaimer">{DISCLAIMER}</div>', unsafe_allow_html=True)
