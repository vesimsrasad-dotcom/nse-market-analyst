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

    # ── Upload Excel / CSV ────────────────────────────────────────────────────
    with st.expander("📂 Upload Excel / CSV to load portfolio", expanded=len(holdings) == 0):
        st.markdown("""
        Upload an Excel or CSV file with your holdings. Required columns:

        | Column | Example |
        |---|---|
        | **NSE Symbol** | RELIANCE |
        | **Quantity** | 50 |
        | **Avg Cost (₹)** | 1350.00 |

        Optional columns: **Sector**, **Notes**
        """)

        # Template download as CSV (no extra dependencies needed)
        import io
        template_df = pd.DataFrame([
            {"NSE Symbol": "RELIANCE", "Quantity": 10, "Avg Cost (₹)": 2500.00, "Sector": "Energy",  "Notes": ""},
            {"NSE Symbol": "TCS",      "Quantity": 5,  "Avg Cost (₹)": 3800.00, "Sector": "IT",      "Notes": ""},
            {"NSE Symbol": "HDFCBANK", "Quantity": 20, "Avg Cost (₹)": 1600.00, "Sector": "Banking", "Notes": ""},
        ])
        csv_template = template_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇️ Download CSV Template",
            data=csv_template,
            file_name="portfolio_template.csv",
            mime="text/csv",
            key="port_template_dl"
        )
        st.caption("💡 You can also open this CSV in Excel, fill in your data, save as .xlsx or .csv and upload.")

        port_file = st.file_uploader(
            "Upload your portfolio file",
            type=["csv", "xlsx", "xls"],
            key="port_upload"
        )

        if port_file:
            try:
                fname = port_file.name.lower()
                if fname.endswith(".csv"):
                    df_upload = pd.read_csv(port_file)
                else:
                    df_upload = pd.read_excel(port_file)

                # Normalise column names — flexible matching
                df_upload.columns = [c.strip() for c in df_upload.columns]
                col_map = {}
                for col in df_upload.columns:
                    cl = col.lower().replace(" ", "").replace("(₹)","").replace("(rs)","")
                    if cl in ["nsesymbol","symbol","ticker","stock","scrip"]:
                        col_map[col] = "ticker"
                    elif cl in ["quantity","qty","shares","units"]:
                        col_map[col] = "qty"
                    elif cl in ["avgcost","averagecost","avgprice","buyprice","cost","price","purchaseprice"]:
                        col_map[col] = "avg_cost"
                    elif cl in ["sector","industry"]:
                        col_map[col] = "sector"
                    elif cl in ["notes","note","remarks","comment"]:
                        col_map[col] = "notes"

                df_upload = df_upload.rename(columns=col_map)

                missing = [c for c in ["ticker","qty","avg_cost"] if c not in df_upload.columns]
                if missing:
                    st.error(f"Could not find columns: {missing}. Please check your file matches the template.")
                else:
                    df_upload["qty"]      = pd.to_numeric(df_upload["qty"],      errors="coerce").fillna(0)
                    df_upload["avg_cost"] = pd.to_numeric(df_upload["avg_cost"], errors="coerce").fillna(0)
                    # Clean ticker — strip exchange prefixes like NSE: BSE: NSE/ etc.
                    df_upload["ticker"] = (
                        df_upload["ticker"]
                        .astype(str)
                        .str.strip()
                        .str.upper()
                        .str.replace(r"^(NSE:|BSE:|NSE/|BSE/|NSE\\|BSE\\)", "", regex=True)
                        .str.strip()
                    )
                    df_upload["sector"]   = df_upload.get("sector",   pd.Series([""] * len(df_upload))).fillna("")
                    df_upload["notes"]    = df_upload.get("notes",    pd.Series([""] * len(df_upload))).fillna("")

                    valid = df_upload[(df_upload["qty"] > 0) & (df_upload["avg_cost"] > 0)]
                    if valid.empty:
                        st.error("No valid rows found. Check quantity and cost columns have numbers.")
                    else:
                        st.success(f"✅ Found {len(valid)} holdings ready to import")
                        st.dataframe(valid[["ticker","qty","avg_cost","sector","notes"]], 
                                     use_container_width=True, hide_index=True)

                        if st.button("📥 Import to Portfolio", type="primary", key="port_import_btn"):
                            new_holdings = list(holdings)
                            for _, row in valid.iterrows():
                                norm = normalise_symbol(str(row["ticker"]))
                                new_holdings = add_holding(
                                    new_holdings, norm,
                                    float(row["qty"]), float(row["avg_cost"]),
                                    str(row.get("sector","")),
                                    str(row.get("notes",""))
                                )
                            st.session_state.holdings = new_holdings
                            save_portfolio(new_holdings)
                            st.success(f"✅ Imported {len(valid)} holdings successfully!")
                            st.rerun()
            except Exception as e:
                st.error(f"Could not read file: {e}")
                st.info("Make sure your file is a valid Excel (.xlsx) or CSV file.")

    # ── Manual Add ────────────────────────────────────────────────────────────
    with st.expander("➕ Add single holding manually"):
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
