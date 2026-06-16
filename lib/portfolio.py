"""
pages/5_ _Portfolio.py
Single-file upload → Live Portfolio (left) + XIRR (right).
No second upload — df_tx feeds both panels directly.

File columns:
  Date | Ticker | Type | Quantity | Price | Avg Cost (₹) | Current Holdings | Notes (optional)
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh

from lib.config import DISCLAIMER, ANTHROPIC_API_KEY, normalise_symbol
from lib.market_data import get_quote
from lib.charts import portfolio_pie, portfolio_bar
from lib.claude_analyst import analyse_portfolio
from lib.refresh import market_status, timestamp_ist
from lib.auth import check_password, logout_button
from lib.xirr import xirr_summary, build_cashflows, xirr

st.set_page_config(page_title="Portfolio | NSE Market Analyst",
                   page_icon="💼", layout="wide")

if not check_password():
    st.stop()

_ms    = market_status()
_count = st_autorefresh(interval=_ms["interval_ms"], key="port_autorefresh")

st.markdown("""
<style>
  html, body, [class*="css"] { font-size: 17px !important; }
  .disclaimer { font-size:11px; color:#555; text-align:center;
    border-top:1px solid #222; padding-top:10px; margin-top:30px; }
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────
col_h1, col_h2 = st.columns([4, 1])
with col_h1:
    st.markdown("## 💼 Portfolio Tracker")
    st.caption("Upload one transaction file → live P&L on the left · XIRR on the right")
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

# ── Template + single file upload ────────────────────────────────────────────
with st.expander("📂 Upload Transaction File", expanded=True):
    st.markdown("""
    Upload **one CSV or Excel file** — it drives both the live portfolio and XIRR.
    Stock names are resolved automatically from NSE.

    | Column | Format | Example |
    |---|---|---|
    | **Date** | YYYY-MM-DD | 2023-01-15 |
    | **Ticker** | NSE symbol | RELIANCE |
    | **Type** | BUY / SELL / DIVIDEND | BUY |
    | **Quantity** | Shares transacted | 10 |
    | **Price** | Price per share (₹) | 2500 |
    | **Avg Cost (₹)** | Your blended avg cost for current holding | 2350 |
    | **Current Holdings** | Shares held today — fill for active rows only | 10 |
    | **Notes** | Optional | — |

    > 💡 Fill **Avg Cost (₹)** and **Current Holdings** on the latest active row per ticker.
    > Leave them blank on historical / fully-exited rows.
    """)

    template_df = pd.DataFrame([
        {"Date":"2023-01-15","Ticker":"RELIANCE","Type":"BUY",     "Quantity":10,"Price":2400,"Avg Cost (₹)":2400,"Current Holdings":10,"Notes":"Initial buy"},
        {"Date":"2023-06-10","Ticker":"RELIANCE","Type":"BUY",     "Quantity":5, "Price":2200,"Avg Cost (₹)":2333,"Current Holdings":15,"Notes":"Added more"},
        {"Date":"2023-03-01","Ticker":"TCS",     "Type":"BUY",     "Quantity":5, "Price":3800,"Avg Cost (₹)":3800,"Current Holdings":5, "Notes":""},
        {"Date":"2023-09-20","Ticker":"HDFCBANK","Type":"BUY",     "Quantity":20,"Price":1600,"Avg Cost (₹)":1600,"Current Holdings":20,"Notes":""},
        {"Date":"2024-01-05","Ticker":"HDFCBANK","Type":"SELL",    "Quantity":5, "Price":1750,"Avg Cost (₹)":"",  "Current Holdings":"","Notes":"Partial exit"},
        {"Date":"2024-02-10","Ticker":"RELIANCE","Type":"DIVIDEND","Quantity":"","Price":"",  "Avg Cost (₹)":"",  "Current Holdings":"","Notes":"Div ₹9/share"},
    ])
    st.dataframe(template_df, use_container_width=True, hide_index=True)
    st.download_button("⬇️ Download CSV Template",
                       data=template_df.to_csv(index=False).encode(),
                       file_name="portfolio_transactions_template.csv",
                       mime="text/csv", key="tmpl_dl")

    uploaded = st.file_uploader(
        "Upload your transaction file (CSV or Excel)",
        type=["csv", "xlsx", "xls"],
        key="main_upload"
    )

if not uploaded:
    st.info("⬆️ Upload your transaction file above to get started.")
    st.stop()

# ── Parse file (once, cached) ─────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def parse_file(file_bytes: bytes, file_name: str):
    import io
    buf = io.BytesIO(file_bytes)
    df  = pd.read_csv(buf) if file_name.lower().endswith(".csv") else pd.read_excel(buf)
    df.columns = [c.strip() for c in df.columns]

    # Flexible column name mapping
    col_map = {}
    for col in df.columns:
        cl = col.lower().replace(" ", "").replace("(₹)","").replace("(rs)","")
        if   cl in ["date","transactiondate","txdate"]:              col_map[col] = "Date"
        elif cl in ["ticker","symbol","nsesymbol","stock","scrip"]:  col_map[col] = "Ticker"
        elif cl in ["type","transactiontype","txtype","action"]:     col_map[col] = "Type"
        elif cl in ["quantity","qty","shares","units"]:              col_map[col] = "Quantity"
        elif cl in ["price","pricepershare","tradeprice"]:           col_map[col] = "Price"
        elif cl in ["avgcost","averagecost","avgprice","costprice"]: col_map[col] = "Avg Cost (₹)"
        elif cl in ["currentholdings","holdingqty","currentqty",
                    "holdings","heldqty"]:                           col_map[col] = "Current Holdings"
        elif cl in ["notes","note","remarks","comment"]:             col_map[col] = "Notes"
    df = df.rename(columns=col_map)

    required = ["Date", "Ticker", "Type"]
    missing  = [c for c in required if c not in df.columns]
    if missing:
        return None, f"Missing required columns: {missing}"

    # Types
    df["Date"]             = pd.to_datetime(df["Date"], errors="coerce")
    df["Quantity"]         = pd.to_numeric(df.get("Quantity",         pd.Series(dtype=float)), errors="coerce").fillna(0)
    df["Price"]            = pd.to_numeric(df.get("Price",            pd.Series(dtype=float)), errors="coerce").fillna(0)
    df["Avg Cost (₹)"]     = pd.to_numeric(df.get("Avg Cost (₹)",     pd.Series(dtype=float)), errors="coerce")
    df["Current Holdings"] = pd.to_numeric(df.get("Current Holdings", pd.Series(dtype=float)), errors="coerce")
    df["Notes"]            = df.get("Notes", pd.Series([""] * len(df))).fillna("")
    df["Ticker"]           = df["Ticker"].astype(str).str.strip().str.upper() \
                               .str.replace(r"^(NSE:|BSE:|NSE/|BSE/)", "", regex=True).str.strip()
    df["Type"]             = df["Type"].astype(str).str.strip().str.upper()
    df = df.sort_values("Date").reset_index(drop=True)
    return df, None

file_bytes = uploaded.read()
df_tx, parse_error = parse_file(file_bytes, uploaded.name)

if parse_error:
    st.error(parse_error)
    st.stop()

st.success(f"✅ Loaded {len(df_tx)} transactions · {df_tx['Ticker'].nunique()} stocks")
with st.expander("📄 View Parsed Transactions"):
    st.dataframe(df_tx, use_container_width=True, hide_index=True)

# ── Fetch live prices + names (once, cached 60 s) ────────────────────────────
all_tickers = tuple(sorted(df_tx["Ticker"].unique().tolist()))

@st.cache_data(show_spinner=False, ttl=60)
def fetch_quotes(tickers: tuple) -> dict:
    result = {}
    for tk in tickers:
        norm = normalise_symbol(tk)
        q    = get_quote(norm)
        result[tk] = {
            "price": q.get("price"),
            "name":  q.get("name") or q.get("companyName") or tk,
        }
    return result

with st.spinner("Fetching live prices & stock names from NSE…"):
    quotes = fetch_quotes(all_tickers)

# current_prices dict used by xirr_summary / build_cashflows
current_prices = {tk: v["price"] for tk, v in quotes.items() if v["price"]}

# ── Prepare df for xirr.py ────────────────────────────────────────────────────
# xirr_summary expects columns: Date (date), Ticker, Type, Quantity, Price
# Convert Date to date objects (xirr core needs date, not datetime)
df_for_xirr = df_tx.copy()
df_for_xirr["Date"] = df_for_xirr["Date"].dt.date

# ── Live portfolio from Current Holdings column ───────────────────────────────
active = (
    df_tx[df_tx["Current Holdings"].notna() & (df_tx["Current Holdings"] > 0)]
    .sort_values("Date")
    .groupby("Ticker")
    .last()
    .reset_index()
)

live_rows = []
for _, row in active.iterrows():
    tk       = row["Ticker"]
    cmp      = quotes.get(tk, {}).get("price") or 0
    name     = quotes.get(tk, {}).get("name", tk)
    qty      = row["Current Holdings"]
    avg      = row["Avg Cost (₹)"] if pd.notna(row.get("Avg Cost (₹)")) else 0
    invested = qty * avg
    value    = qty * cmp
    pnl      = value - invested
    pnl_pct  = (pnl / invested * 100) if invested else 0
    live_rows.append({
        "Name": name, "Ticker": tk, "Qty": qty,
        "Avg Cost": avg, "CMP": cmp,
        "Invested (₹)": invested, "Value (₹)": value,
        "P&L (₹)": pnl, "P&L (%)": pnl_pct,
    })

df_live = pd.DataFrame(live_rows) if live_rows else pd.DataFrame()

# ── Two-column layout ─────────────────────────────────────────────────────────
st.divider()
col_left, col_right = st.columns([1, 1], gap="large")

# ════════════════════════════════════════════════════════════════════════════
# LEFT — LIVE PORTFOLIO
# ════════════════════════════════════════════════════════════════════════════
with col_left:
    st.markdown("### 📊 Live Portfolio")

    if df_live.empty:
        st.warning("No active holdings found. Ensure 'Current Holdings' > 0 for your active rows.")
    else:
        total_invested = df_live["Invested (₹)"].sum()
        total_value    = df_live["Value (₹)"].sum()
        total_pnl      = total_value - total_invested
        total_pnl_pct  = (total_pnl / total_invested * 100) if total_invested else 0

        m1, m2 = st.columns(2)
        with m1: st.metric("Total Invested", f"₹{total_invested:,.0f}")
        with m2: st.metric("Current Value",  f"₹{total_value:,.0f}")
        m3, m4 = st.columns(2)
        with m3: st.metric("Unrealized P&L", f"₹{total_pnl:+,.0f}", delta=f"{total_pnl_pct:+.1f}%")
        with m4: st.metric("Holdings", len(df_live))

        st.divider()
        st.markdown("#### Holdings Detail")
        disp = df_live.copy()
        disp["P&L (₹)"]      = disp["P&L (₹)"].map(lambda x: f"₹{x:+,.0f}")
        disp["P&L (%)"]      = disp["P&L (%)"].map(lambda x: f"{x:+.1f}%")
        disp["CMP"]          = disp["CMP"].map(lambda x: f"₹{x:,.2f}")
        disp["Avg Cost"]     = disp["Avg Cost"].map(lambda x: f"₹{x:,.2f}")
        disp["Invested (₹)"] = disp["Invested (₹)"].map(lambda x: f"₹{x:,.0f}")
        disp["Value (₹)"]    = disp["Value (₹)"].map(lambda x: f"₹{x:,.0f}")
        st.dataframe(disp[["Name","Ticker","Qty","Avg Cost","CMP",
                            "Invested (₹)","Value (₹)","P&L (₹)","P&L (%)"]],
                     use_container_width=True, hide_index=True)

        st.divider()
        st.plotly_chart(portfolio_pie(df_live, "Value (₹)", "Name", "By Stock"),
                        use_container_width=True, config={"displayModeBar": False})
        st.plotly_chart(portfolio_bar(df_live),
                        use_container_width=True, config={"displayModeBar": False})

        if ANTHROPIC_API_KEY:
            st.divider()
            st.markdown("#### 🤖 AI Portfolio Analysis")
            if st.button("Generate Portfolio Analysis", type="primary", key="port_ai"):
                summary = df_live[["Name","Ticker","Qty","Avg Cost","CMP",
                                   "Invested (₹)","Value (₹)","P&L (%)"]].to_string(index=False)
                with st.spinner("Claude is reviewing your portfolio…"):
                    analysis = analyse_portfolio(summary)
                st.markdown(analysis)

# ════════════════════════════════════════════════════════════════════════════
# RIGHT — XIRR  (uses df_for_xirr — same data, no second upload)
# ════════════════════════════════════════════════════════════════════════════
with col_right:
    st.markdown("### 📈 XIRR Calculator")

    df_xirr = xirr_summary(df_for_xirr, current_prices)

    if df_xirr.empty:
        st.warning("Could not calculate XIRR. Ensure the file has valid BUY/SELL/DIVIDEND rows.")
    else:
        all_flows      = build_cashflows(df_for_xirr, current_prices).get("__portfolio__", [])
        portfolio_xirr = xirr(all_flows)
        port_xirr_pct  = f"{portfolio_xirr * 100:.2f}%" if portfolio_xirr else "N/A"

        total_inv  = df_xirr["Invested (₹)"].sum()
        total_cur  = df_xirr["Current Value (₹)"].sum()
        total_real = df_xirr["Realised (₹)"].sum()
        total_div  = df_xirr["Dividends (₹)"].sum()

        m1, m2 = st.columns(2)
        with m1: st.metric("Total Invested", f"₹{total_inv:,.0f}")
        with m2: st.metric("Current Value",  f"₹{total_cur:,.0f}")
        m3, m4 = st.columns(2)
        with m3: st.metric("Realised + Divs", f"₹{total_real + total_div:,.0f}")
        with m4:
            color = "#00C853" if portfolio_xirr and portfolio_xirr > 0 else "#FF1744"
            st.markdown(f"""
            <div style="background:#1A1F2E;border-radius:10px;padding:14px 16px;
                        border:1px solid rgba(255,255,255,0.06);text-align:center;">
              <div style="font-size:12px;color:#888;text-transform:uppercase;">Portfolio XIRR</div>
              <div style="font-size:28px;font-weight:700;color:{color};">{port_xirr_pct}</div>
              <div style="font-size:11px;color:#555;">Annualised return</div>
            </div>""", unsafe_allow_html=True)

        st.divider()
        st.markdown("#### Per-Stock XIRR Breakdown")

        def style_xirr(val):
            if val is None or (isinstance(val, float) and pd.isna(val)):
                return "color: #888"
            if val >= 15: return "color: #00C853; font-weight: bold"
            if val >= 0:  return "color: #FFD600; font-weight: bold"
            return "color: #FF1744; font-weight: bold"

        display_xirr = df_xirr.copy()
        for col in ["Invested (₹)", "Realised (₹)", "Dividends (₹)", "Current Value (₹)"]:
            if col in display_xirr.columns:
                display_xirr[col] = display_xirr[col].map(lambda x: f"₹{x:,.0f}")
        display_xirr.insert(1, "Name",
            display_xirr["Ticker"].map(lambda t: quotes.get(t, {}).get("name", t)))

        st.dataframe(
            display_xirr.style.applymap(style_xirr, subset=["XIRR (%)"]),
            use_container_width=True, hide_index=True
        )

        st.markdown("""
        > **XIRR guide:** 🟢 >15% Strong · 🟡 0–15% Moderate · 🔴 Negative — Loss
        >
        > *XIRR weights each transaction by its date for a true annualised return.*
        """)

        valid = df_xirr.dropna(subset=["XIRR (%)"])
        if not valid.empty:
            bar_labels = valid["Ticker"].map(lambda t: quotes.get(t, {}).get("name", t))
            bar_colors = ["#00C853" if x >= 0 else "#FF1744" for x in valid["XIRR (%)"]]
            fig = go.Figure(go.Bar(
                x=bar_labels, y=valid["XIRR (%)"],
                marker_color=bar_colors,
                text=[f"{v:+.1f}%" for v in valid["XIRR (%)"]],
                textposition="outside",
            ))
            fig.add_hline(y=0, line_color="#555", line_dash="dash")
            fig.update_layout(
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                height=360, title="XIRR by Stock (%)",
                yaxis_ticksuffix="%", xaxis_tickangle=-30,
                margin=dict(l=40, r=30, t=50, b=80),
            )
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    st.caption("⚠️ XIRR is for educational tracking only. Consult a SEBI-registered adviser for investment decisions.")

st.markdown(f'<div class="disclaimer">{DISCLAIMER}</div>', unsafe_allow_html=True)
