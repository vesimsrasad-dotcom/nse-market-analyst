"""
pages/5_ _Portfolio.py
Personal Portfolio tracker for NSE Market Analyst.
"""

import streamlit as st
from streamlit_autorefresh import st_autorefresh
from lib.refresh import market_status, timestamp_ist
import pandas as pd
from lib.config import DISCLAIMER, ANTHROPIC_API_KEY, normalise_symbol
from lib.market_data import enrich_portfolio
from lib.portfolio import (
    load_portfolio, save_portfolio, add_holding, remove_holding,
    portfolio_summary_text, concentration_warnings,
)
from lib.charts import portfolio_pie, portfolio_bar
from lib.claude_analyst import analyse_portfolio

_ms_status = market_status()
_count_port = st_autorefresh(interval=_ms_status["interval_ms"], key="port_autorefresh")
st.set_page_config(page_title="Portfolio | NSE Market Analyst",
                   page_icon="💼", layout="wide")

st.markdown("""
<style>
  html, body, [class*="css"] { font-size: 17px !important; }
  .summary-card { background:#1A1F2E; border-radius:10px; padding:16px 20px;
    border:1px solid rgba(255,255,255,0.06); text-align:center; }
  .green { color: #00C853; } .red { color: #FF1744; }
  .disclaimer { font-size:11px; color:#555; text-align:center;
    border-top:1px solid #222; padding-top:10px; margin-top:30px; }
</style>
""", unsafe_allow_html=True)

col_h1, col_h2 = st.columns([4,1])
with col_h1:
    st.markdown("💼 Portfolio Tracker")
    st.caption("Track your NSE holdings — educational P&L view only. Not financial advice.")
with col_h2:
    st.markdown(f"""
    <div style="text-align:right;padding-top:10px;">
      <span style="font-size:13px;color={_ms_status['color']};font-weight:700;">{_ms_status['label']}</span><br>
      <span style="font-size:11px;color:#555;">{timestamp_ist()}</span>
    </div>""", unsafe_allow_html=True)
    if st.button("🔄 Refresh", key="port_manual_refresh"):
        st.cache_data.clear()
        st.rerun()

# ── Load State ────────────────────────────────────────────────────────────────
if "holdings" not in st.session_state:
    st.session_state.holdings = load_portfolio()

holdings = st.session_state.holdings

# ── Add Holding Form ──────────────────────────────────────────────────────────
with st.expander("➕ Add / Update Holding", expanded=len(holdings) == 0):
    c1, c2, c3, c4, c5 = st.columns([2, 1.5, 1.5, 2, 2])
    with c1:
        new_ticker = st.text_input("NSE Symbol", placeholder="RELIANCE", key="port_ticker")
    with c2:
        new_qty    = st.number_input("Quantity", min_value=0.01, value=1.0, step=1.0, key="port_qty")
    with c3:
        new_cost   = st.number_input("Avg Cost (₹)", min_value=0.01, value=100.0, key="port_cost")
    with c4:
        new_sector = st.text_input("Sector (optional)", key="port_sector")
    with c5:
        new_notes  = st.text_input("Notes (optional)", key="port_notes")

    if st.button("Add to Portfolio", type="primary", key="port_add"):
        if new_ticker:
            norm_ticker = normalise_symbol(new_ticker)
            holdings = add_holding(
                holdings, norm_ticker, new_qty, new_cost,
                new_sector, new_notes,
            )
            st.session_state.holdings = holdings
            save_portfolio(holdings)
            st.success(f"Added {norm_ticker} to portfolio.")
            st.rerun()
        else:
            st.warning("Please enter a ticker symbol.")

# ── Portfolio Table ───────────────────────────────────────────────────────────
if not holdings:
    st.info("No holdings yet. Add your first stock above.")
    st.markdown(f'<div class="disclaimer">{DISCLAIMER}</div>', unsafe_allow_html=True)
    st.stop()

with st.spinner("Fetching current prices…"):
    df = enrich_portfolio(holdings)

# Remove holding
remove_col, _ = st.columns([1, 3])
with remove_col:
    remove_ticker = st.selectbox("Remove holding", ["— select —"] + [h["ticker"] for h in holdings],
                                  key="port_remove")
    if remove_ticker != "— select —":
        if st.button("🗑️ Remove", key="port_remove_btn"):
            holdings = remove_holding(holdings, remove_ticker)
            st.session_state.holdings = holdings
            save_portfolio(holdings)
            st.rerun()

# ── Summary Metrics ───────────────────────────────────────────────────────────
total_invested = df["Invested (₹)"].sum()
total_value    = df["Value (₹)"].sum()
total_pnl      = total_value - total_invested
total_pnl_pct  = (total_pnl / total_invested * 100) if total_invested else 0
up_overall     = total_pnl >= 0

st.divider()
m1, m2, m3, m4 = st.columns(4)
with m1:
    st.metric("Total Invested", f"₹{total_invested:,.0f}")
with m2:
    st.metric("Current Value", f"₹{total_value:,.0f}")
with m3:
    color = "normal" if up_overall else "inverse"
    st.metric("Unrealized P&L (₹)", f"₹{total_pnl:+,.0f}", delta=f"{total_pnl_pct:+.1f}%")
with m4:
    st.metric("Holdings", len(df))

# ── Warnings ──────────────────────────────────────────────────────────────────
warnings = concentration_warnings(df)
for w in warnings:
    st.warning(w)

st.divider()

# ── Holdings Table ────────────────────────────────────────────────────────────
st.markdown("### Holdings Detail")
display_df = df.copy()
display_df["P&L (₹)"]  = display_df["P&L (₹)"].map(lambda x: f"₹{x:+,.0f}")
display_df["P&L (%)"]  = display_df["P&L (%)"].map(lambda x: f"{x:+.1f}%")
display_df["CMP"]       = display_df["CMP"].map(lambda x: f"₹{x:,.2f}")
display_df["Avg Cost"]  = display_df["Avg Cost"].map(lambda x: f"₹{x:,.2f}")
display_df["Invested (₹)"] = display_df["Invested (₹)"].map(lambda x: f"₹{x:,.0f}")
display_df["Value (₹)"] = display_df["Value (₹)"].map(lambda x: f"₹{x:,.0f}")

st.dataframe(display_df[[
    "Name", "Ticker", "Qty", "Avg Cost", "CMP",
    "Invested (₹)", "Value (₹)", "P&L (₹)", "P&L (%)", "Sector"
]], use_container_width=True, hide_index=True)

# ── Charts ────────────────────────────────────────────────────────────────────
st.divider()
c1, c2 = st.columns(2)
with c1:
    fig_alloc = portfolio_pie(df, value_col="Value (₹)", label_col="Name",
                               title="Allocation by Stock")
    st.plotly_chart(fig_alloc, use_container_width=True, config={"displayModeBar": False})
with c2:
    sector_df = df.groupby("Sector")["Value (₹)"].sum().reset_index()
    sector_df.columns = ["Name", "Value (₹)"]
    fig_sec = portfolio_pie(sector_df, title="Allocation by Sector")
    st.plotly_chart(fig_sec, use_container_width=True, config={"displayModeBar": False})

fig_pnl = portfolio_bar(df)
st.plotly_chart(fig_pnl, use_container_width=True, config={"displayModeBar": False})

# ── AI Portfolio Analysis ─────────────────────────────────────────────────────
st.divider()
st.markdown("### 🤖 AI Portfolio Analysis")
if not ANTHROPIC_API_KEY:
    st.warning("Add `ANTHROPIC_API_KEY` to enable AI analysis.")
else:
    if st.button("Generate Portfolio Analysis", type="primary", key="port_ai_btn"):
        with st.spinner("Claude is reviewing your portfolio…"):
            summary = portfolio_summary_text(df)
            analysis = analyse_portfolio(summary)
        st.markdown(analysis)
    else:
        st.info("Click the button above for an educational AI-powered portfolio review.")

st.caption("⚠️ This is educational analysis only. Not financial advice or personalised recommendations.")

# ── Disclaimer ────────────────────────────────────────────────────────────────
st.markdown(f'<div class="disclaimer">{DISCLAIMER}</div>', unsafe_allow_html=True)
