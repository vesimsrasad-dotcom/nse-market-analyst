"""
pages/1_ _Market_Pulse.py
Market Pulse — full index / commodity dashboard.
"""

import streamlit as st
from streamlit_autorefresh import st_autorefresh
from lib.refresh import market_status, timestamp_ist
from lib.config import (
    DISCLAIMER, INDICES, MARKET_PULSE_CARDS, SECTOR_INDICES, CHART_PERIODS,
)
from lib.market_data import get_multi_quotes, get_sparkline, get_history, get_sector_returns
from lib.charts import sparkline, price_chart, add_ma_overlays, sector_bar

st.set_page_config(page_title="Market Pulse | NSE Market Analyst",
                   page_icon="📈", layout="wide")

status = market_status()
_count = st_autorefresh(interval=status["interval_ms"], key="mp_autorefresh")

st.markdown("""
<style>
  html, body, [class*="css"] { font-size: 17px !important; }
  .metric-card {
    background: #1A1F2E; border-radius: 10px;
    padding: 12px 14px; margin-bottom: 6px;
    border: 1px solid rgba(255,255,255,0.06);
  }
  .metric-name  { font-size: 11px; color: #888; text-transform: uppercase; }
  .metric-value { font-size: 20px; font-weight: 700; color: #FAFAFA; margin: 2px 0; }
  .green { color: #00C853; } .red { color: #FF1744; }
  .disclaimer { font-size: 11px; color: #555; text-align: center;
    border-top: 1px solid #222; padding-top: 10px; margin-top: 30px; }
</style>
""", unsafe_allow_html=True)

st.markdown("## 📈 Market Pulse")
st.caption("Live snapshot of Indian indices, commodities, and currency")

# ── Fetch all quotes ──────────────────────────────────────────────────────────
pulse_tickers = [INDICES[n]["ticker"] for n in MARKET_PULSE_CARDS]
with st.spinner("Fetching market data…"):
    quotes = get_multi_quotes(pulse_tickers)

# ── Index Cards ───────────────────────────────────────────────────────────────
st.divider()
cols = st.columns(4)
for i, name in enumerate(MARKET_PULSE_CARDS):
    tk = INDICES[name]["ticker"]
    q  = quotes.get(tk, {})
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
        </div>""", unsafe_allow_html=True)
        if spark:
            fig = sparkline(spark, positive=up)
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

st.divider()

# ── Main Chart ────────────────────────────────────────────────────────────────
st.markdown("### Index Chart")
c1, c2, c3 = st.columns([2, 2, 1])
with c1:
    index_choice = st.selectbox("Select Index",
                                list(INDICES.keys()), index=0, key="mp_index")
with c2:
    chart_type = st.radio("View", ["Area", "Price", "Candlestick", "Performance"],
                          horizontal=True, key="mp_chart_type")
with c3:
    period_key = st.selectbox("Period", list(CHART_PERIODS.keys()),
                              index=2, key="mp_period")

show_ma = st.multiselect("Moving averages overlay", [20, 50, 100, 200],
                          default=[], key="mp_ma")

ticker   = INDICES[index_choice]["ticker"]
df_chart = get_history(ticker, period_key)

if not df_chart.empty:
    fig = price_chart(df_chart, index_choice, chart_type)
    if show_ma and chart_type != "Candlestick":
        fig = add_ma_overlays(fig, df_chart, show_ma)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
else:
    st.warning(f"No data available for {index_choice}.")

st.divider()

# ── Sector Performance ────────────────────────────────────────────────────────
st.markdown("### NSE Sector Returns")
c1, c2 = st.columns([4, 1])
with c2:
    sec_period = st.radio("", ["1M", "3M", "6M", "1Y"], key="mp_sec_period",
                           label_visibility="collapsed")
with st.spinner("Loading sector data…"):
    df_sec = get_sector_returns(SECTOR_INDICES, sec_period)

if not df_sec.empty:
    fig_sec = sector_bar(df_sec, sec_period)
    st.plotly_chart(fig_sec, use_container_width=True, config={"displayModeBar": False})

st.divider()

# ── Relative Performance ──────────────────────────────────────────────────────
st.markdown("### Relative Performance")
rel_period = st.radio("Period", ["1M", "3M", "6M", "YTD", "1Y"],
                      horizontal=True, key="mp_rel_period")
selected = st.multiselect(
    "Compare indices",
    list(INDICES.keys()),
    default=["Nifty 50", "Bank Nifty", "Nifty IT", "Nifty Pharma"],
    key="mp_rel_select",
)

if selected:
    import plotly.graph_objects as go
    fig_rel = go.Figure()
    COLORS = ["#2979FF", "#FF6B00", "#00C853", "#FFD600", "#CE93D8",
              "#80DEEA", "#FF8A65", "#A5D6A7"]
    for idx, name in enumerate(selected):
        tk  = INDICES[name]["ticker"]
        df_ = get_history(tk, rel_period)
        if df_.empty:
            continue
        perf = (df_["Close"] / df_["Close"].iloc[0] - 1) * 100
        fig_rel.add_trace(go.Scatter(
            x=df_.index, y=perf,
            mode="lines",
            name=name,
            line=dict(color=COLORS[idx % len(COLORS)], width=2),
        ))
    fig_rel.add_hline(y=0, line_color="#555", line_dash="dash")
    fig_rel.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=380,
        yaxis_ticksuffix="%",
        margin=dict(l=50, r=30, t=30, b=40),
        legend=dict(bgcolor="rgba(0,0,0,0)"),
    )
    st.plotly_chart(fig_rel, use_container_width=True, config={"displayModeBar": False})

# ── Disclaimer ────────────────────────────────────────────────────────────────

# ── Countdown Timer ───────────────────────────────────────────────────────────
_iv_s = status["interval_ms"] // 1000
st.markdown(f"""
<div style="text-align:center;font-size:12px;color:#444;margin:8px 0;">
  Next auto-refresh in <span id="mp-timer" style="color:#FF6B00;font-weight:700;">{_iv_s}</span>s
</div>
<script>
(function(){{
  var s={_iv_s},el=document.getElementById("mp-timer");
  if(!el)return;
  setInterval(function(){{s--;if(s<=0)s={_iv_s};if(el)el.textContent=s;}},1000);
}})();
</script>
""", unsafe_allow_html=True)

st.markdown(f'<div class="disclaimer">{DISCLAIMER}</div>', unsafe_allow_html=True)
