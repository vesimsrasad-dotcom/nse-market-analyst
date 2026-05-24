"""
pages/5_ _Portfolio.py
Portfolio tracker with XIRR calculations via CSV/Excel upload.
"""

import streamlit as st
import pandas as pd
from streamlit_autorefresh import st_autorefresh
from lib.config import DISCLAIMER, ANTHROPIC_API_KEY, normalise_symbol
from lib.market_data import enrich_portfolio, get_quote
from lib.portfolio import (
    load_portfolio, save_portfolio, add_holding, remove_holding,
    portfolio_summary_text, concentration_warnings,
)
from lib.charts import portfolio_pie, portfolio_bar
from lib.claude_analyst import analyse_portfolio
from lib.refresh import market_status, timestamp_ist
from lib.auth import check_password, logout_button
from lib.xirr import (
    parse_transaction_file, xirr_summary, build_cashflows,
    xirr, xirr_pct, TEMPLATE_EXAMPLE, TEMPLATE_COLUMNS
)

st.set_page_config(page_title="Portfolio | NSE Market Analyst",
                   page_icon="💼", layout="wide")

if not check_password():
    st.stop()

_ms = market_status()
_count = st_autorefresh(interval=_ms["interval_ms"], key="port_autorefresh")

st.markdown("""
<style>
  html, body, [class*="css"] { font-size: 17px !important; }
  .summary-card { background:#1A1F2E; border-radius:10px; padding:16px 20px;
    border:1px solid rgba(255,255,255,0.06); text-align:center; }
  .green { color: #00C853; } .red { color: #FF1744; }
  .xirr-good  { color: #00C853; font-weight:700; }
  .xirr-ok    { color: #FFD600; font-weight:700; }
  .xirr-bad   { color: #FF1744; font-weight:700; }
  .disclaimer { font-size:11px; color:#555; text-align:center;
    border-top:1px solid #222; padding-top:10px; margin-top:30px; }
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────
col_h1, col_h2 = st.columns([4, 1])
with col_h1:
    st.markdown("## 💼 Portfolio Tracker")
    st.caption("Track your NSE holdings with live P&L and XIRR returns")
with col_h2:
    st.markdown(f"""
    <div style="text-align:right;padding-top:10px;">
      <span style="font-size:13px;color:{_ms['color']};font-weight:700;">{_ms['label']}</span><br>
      <span style="font-size:11px;color:#555;">{timestamp_ist()}</span>
    </div>""", unsafe_allow_html=True)
    if st.button("🔄 Refresh", key="port_refresh"):
        st.cache_data.clear()
        st.rerun()

logout_button()

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_live, tab_xirr = st.tabs(["📊 Live Portfolio", "📈 XIRR Calculator"])

# ════════════════════════════════════════════════════════════════════════════
# TAB 1 — LIVE PORTFOLIO
# ════════════════════════════════════════════════════════════════════════════
with tab_live:
    if "holdings" not in st.session_state:
        st.session_state.holdings = load_portfolio()
    holdings = st.session_state.holdings

    with st.expander("➕ Add / Update Holding", expanded=len(holdings) == 0):
        c1, c2, c3, c4, c5 = st.columns([2, 1.5, 1.5, 2, 2])
        with c1: new_ticker = st.text_input("NSE Symbol", placeholder="RELIANCE", key="port_ticker")
        with c2: new_qty    = st.number_input("Quantity", min_value=0.01, value=1.0, step=1.0, key="port_qty")
        with c3: new_cost   = st.number_input("Avg Cost (₹)", min_value=0.01, value=100.0, key="port_cost")
        with c4: new_sector = st.text_input("Sector (optional)", key="port_sector")
        with c5: new_notes  = st.text_input("Notes (optional)", key="port_notes")

        if st.button("Add to Portfolio", type="primary", key="port_add"):
            if new_ticker:
                norm = normalise_symbol(new_ticker)
                holdings = add_holding(holdings, norm, new_qty, new_cost, new_sector, new_notes)
                st.session_state.holdings = holdings
                save_portfolio(holdings)
                st.success(f"Added {norm}")
                st.rerun()
            else:
                st.warning("Please enter a ticker symbol.")

    if not holdings:
        st.info("No holdings yet. Add your first stock above.")
        st.stop()

    with st.spinner("Fetching live prices…"):
        df = enrich_portfolio(holdings)

    # Remove holding
    remove_col, _ = st.columns([2, 3])
    with remove_col:
        remove_ticker = st.selectbox("Remove holding",
            ["— select —"] + [h["ticker"] for h in holdings], key="port_remove")
        if remove_ticker != "— select —":
            if st.button("🗑️ Remove", key="port_remove_btn"):
                holdings = remove_holding(holdings, remove_ticker)
                st.session_state.holdings = holdings
                save_portfolio(holdings)
                st.rerun()

    # Summary metrics
    total_invested = df["Invested (₹)"].sum()
    total_value    = df["Value (₹)"].sum()
    total_pnl      = total_value - total_invested
    total_pnl_pct  = (total_pnl / total_invested * 100) if total_invested else 0

    st.divider()
    m1, m2, m3, m4 = st.columns(4)
    with m1: st.metric("Total Invested",  f"₹{total_invested:,.0f}")
    with m2: st.metric("Current Value",   f"₹{total_value:,.0f}")
    with m3: st.metric("Unrealized P&L",  f"₹{total_pnl:+,.0f}", delta=f"{total_pnl_pct:+.1f}%")
    with m4: st.metric("Holdings",        len(df))

    for w in concentration_warnings(df):
        st.warning(w)

    st.divider()
    st.markdown("### Holdings Detail")
    disp = df.copy()
    disp["P&L (₹)"]      = disp["P&L (₹)"].map(lambda x: f"₹{x:+,.0f}")
    disp["P&L (%)"]      = disp["P&L (%)"].map(lambda x: f"{x:+.1f}%")
    disp["CMP"]          = disp["CMP"].map(lambda x: f"₹{x:,.2f}")
    disp["Avg Cost"]     = disp["Avg Cost"].map(lambda x: f"₹{x:,.2f}")
    disp["Invested (₹)"] = disp["Invested (₹)"].map(lambda x: f"₹{x:,.0f}")
    disp["Value (₹)"]    = disp["Value (₹)"].map(lambda x: f"₹{x:,.0f}")
    st.dataframe(disp[[
        "Name","Ticker","Qty","Avg Cost","CMP",
        "Invested (₹)","Value (₹)","P&L (₹)","P&L (%)","Sector"
    ]], use_container_width=True, hide_index=True)

    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(portfolio_pie(df, "Value (₹)", "Name", "By Stock"),
                        use_container_width=True, config={"displayModeBar": False})
    with c2:
        sec_df = df.groupby("Sector")["Value (₹)"].sum().reset_index()
        sec_df.columns = ["Name", "Value (₹)"]
        st.plotly_chart(portfolio_pie(sec_df, title="By Sector"),
                        use_container_width=True, config={"displayModeBar": False})

    st.plotly_chart(portfolio_bar(df), use_container_width=True, config={"displayModeBar": False})

    st.divider()
    st.markdown("### 🤖 AI Portfolio Analysis")
    if not ANTHROPIC_API_KEY:
        st.warning("Add `ANTHROPIC_API_KEY` to enable AI analysis.")
    else:
        if st.button("Generate Portfolio Analysis", type="primary", key="port_ai"):
            with st.spinner("Claude is reviewing your portfolio…"):
                analysis = analyse_portfolio(portfolio_summary_text(df))
            st.markdown(analysis)

# ════════════════════════════════════════════════════════════════════════════
# TAB 2 — XIRR CALCULATOR
# ════════════════════════════════════════════════════════════════════════════
with tab_xirr:
    st.markdown("### 📈 XIRR Calculator")
    st.markdown("""
    Upload your **transaction history** (CSV or Excel) to calculate the true
    annualised return (XIRR) for each stock and your overall portfolio.
    """)

    # ── Template Download ────────────────────────────────────────────────────
    with st.expander("📋 Download Template / View Format", expanded=True):
        st.markdown("""
        Your file must have these columns:

        | Column | Format | Example |
        |---|---|---|
        | **Date** | YYYY-MM-DD | 2023-01-15 |
        | **Ticker** | NSE symbol | RELIANCE |
        | **Type** | BUY / SELL / DIVIDEND | BUY |
        | **Quantity** | Number of shares | 10 |
        | **Price** | Price per share in ₹ | 2500 |
        | **Notes** | Optional note | Initial buy |
        """)

        st.markdown("**Example data:**")
        st.dataframe(TEMPLATE_EXAMPLE, use_container_width=True, hide_index=True)

        # CSV download
        csv_bytes = TEMPLATE_EXAMPLE.to_csv(index=False).encode()
        st.download_button(
            "⬇️ Download CSV Template",
            data=csv_bytes,
            file_name="nse_transactions_template.csv",
            mime="text/csv",
            key="xirr_template_dl"
        )

    # ── File Upload ──────────────────────────────────────────────────────────
    st.divider()
    uploaded = st.file_uploader(
        "Upload your transaction file (CSV or Excel)",
        type=["csv", "xlsx", "xls"],
        key="xirr_upload"
    )

    if not uploaded:
        st.info("Upload your transaction file above to calculate XIRR.")
        st.stop()

    df_tx, errors = parse_transaction_file(uploaded)

    if errors:
        for e in errors:
            st.error(e)
        if df_tx.empty:
            st.stop()

    st.success(f"✅ Loaded {len(df_tx)} transactions for {df_tx['Ticker'].nunique()} stocks")

    # Show parsed transactions
    with st.expander("📄 View Parsed Transactions"):
        st.dataframe(df_tx, use_container_width=True, hide_index=True)

    # ── Fetch current prices ─────────────────────────────────────────────────
    tickers = df_tx["Ticker"].unique().tolist()
    st.info(f"Fetching live prices for: {', '.join(tickers)}…")

    current_prices = {}
    for tk in tickers:
        norm = normalise_symbol(tk)
        q = get_quote(norm)
        if q.get("price"):
            current_prices[norm] = q["price"]
            current_prices[tk]   = q["price"]

    # ── XIRR Summary ─────────────────────────────────────────────────────────
    st.divider()
    st.markdown("### XIRR Results")

    df_xirr = xirr_summary(df_tx, current_prices)

    if df_xirr.empty:
        st.warning("Could not calculate XIRR. Check your transaction data.")
    else:
        # Portfolio-level XIRR
        all_flows = build_cashflows(df_tx, current_prices).get("__portfolio__", [])
        portfolio_xirr = xirr(all_flows)
        portfolio_xirr_pct = f"{portfolio_xirr * 100:.2f}%" if portfolio_xirr else "N/A"

        # Summary cards
        c1, c2, c3, c4 = st.columns(4)
        total_inv  = df_xirr["Invested (₹)"].sum()
        total_cur  = df_xirr["Current Value (₹)"].sum()
        total_real = df_xirr["Realised (₹)"].sum()
        total_div  = df_xirr["Dividends (₹)"].sum()

        with c1: st.metric("Total Invested",    f"₹{total_inv:,.0f}")
        with c2: st.metric("Current Value",     f"₹{total_cur:,.0f}")
        with c3: st.metric("Realised + Divs",   f"₹{total_real + total_div:,.0f}")
        with c4:
            color = "#00C853" if portfolio_xirr and portfolio_xirr > 0 else "#FF1744"
            st.markdown(f"""
            <div style="background:#1A1F2E;border-radius:10px;padding:14px 16px;
                        border:1px solid rgba(255,255,255,0.06);text-align:center;">
              <div style="font-size:12px;color:#888;text-transform:uppercase;">Portfolio XIRR</div>
              <div style="font-size:28px;font-weight:700;color:{color};">{portfolio_xirr_pct}</div>
              <div style="font-size:11px;color:#555;">Annualised return</div>
            </div>""", unsafe_allow_html=True)

        st.divider()

        # Per-ticker table with colour coding
        st.markdown("#### Per-Stock XIRR Breakdown")

        def style_xirr(val):
            if val is None or (isinstance(val, float) and pd.isna(val)):
                return "color: #888"
            if val >= 15:
                return "color: #00C853; font-weight: bold"
            if val >= 0:
                return "color: #FFD600; font-weight: bold"
            return "color: #FF1744; font-weight: bold"

        display_xirr = df_xirr.copy()
        display_xirr["Invested (₹)"]     = display_xirr["Invested (₹)"].map(lambda x: f"₹{x:,.0f}")
        display_xirr["Realised (₹)"]     = display_xirr["Realised (₹)"].map(lambda x: f"₹{x:,.0f}")
        display_xirr["Dividends (₹)"]    = display_xirr["Dividends (₹)"].map(lambda x: f"₹{x:,.0f}")
        display_xirr["Current Value (₹)"]= display_xirr["Current Value (₹)"].map(lambda x: f"₹{x:,.0f}")

        st.dataframe(
            display_xirr.style.applymap(style_xirr, subset=["XIRR (%)"]),
            use_container_width=True, hide_index=True
        )

        st.markdown("""
        > **XIRR interpretation guide:**
        > - 🟢 **Above 15%** — Strong outperformance vs Nifty long-term average
        > - 🟡 **0–15%** — Moderate return
        > - 🔴 **Negative** — Loss-making position
        >
        > *XIRR accounts for the timing of each transaction, making it more accurate than simple return %.*
        """)

        # XIRR bar chart
        import plotly.graph_objects as go
        valid = df_xirr.dropna(subset=["XIRR (%)"])
        if not valid.empty:
            colors = ["#00C853" if x >= 0 else "#FF1744" for x in valid["XIRR (%)"]]
            fig = go.Figure(go.Bar(
                x=valid["Ticker"],
                y=valid["XIRR (%)"],
                marker_color=colors,
                text=[f"{v:+.1f}%" for v in valid["XIRR (%)"]],
                textposition="outside",
            ))
            fig.add_hline(y=0, line_color="#555", line_dash="dash")
            fig.update_layout(
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                height=340,
                title="XIRR by Stock (%)",
                yaxis_ticksuffix="%",
                margin=dict(l=40, r=30, t=50, b=40),
            )
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    st.caption("⚠️ XIRR is for educational tracking only. Consult a SEBI-registered adviser for investment decisions.")

st.markdown(f'<div class="disclaimer">{DISCLAIMER}</div>', unsafe_allow_html=True)
