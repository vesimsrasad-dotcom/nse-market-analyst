"""
pages/2_ _Stock_Analyzer.py
Stock Analyzer — deep-dive on any NSE / BSE stock.
"""

import streamlit as st
from streamlit_autorefresh import st_autorefresh
from lib.refresh import market_status, timestamp_ist
import pandas as pd
from lib.config import (
    DISCLAIMER, CHART_PERIODS, POPULAR_STOCKS,
    normalise_symbol, COLOR_GREEN, COLOR_RED, COLOR_ORANGE,
    ANTHROPIC_API_KEY,
)
from lib.market_data import (
    get_fundamentals, get_financials, get_history, get_quote,
    compute_technicals, format_market_cap, format_inr,
    rsi_label, trend_label, pe_tier, roe_tier, de_tier, beta_label, week52_position,
)
from lib.charts import (
    price_chart, add_ma_overlays, rsi_chart, macd_chart,
    gauge_chart, revenue_chart, margin_chart,
)
from lib.signals import technical_score, fundamental_score
from lib.claude_analyst import analyse_stock

_ms_status = market_status()
_count_sa = st_autorefresh(interval=_ms_status["interval_ms"], key="sa_autorefresh")
st.set_page_config(page_title="Stock Analyzer | NSE Market Analyst",
                   page_icon="🔍", layout="wide")

st.markdown("""
<style>
  html, body, [class*="css"] { font-size: 17px !important; }
  .header-card {
    background: #1A1F2E; border-radius: 12px;
    padding: 20px 24px; margin-bottom: 16px;
    border: 1px solid rgba(255,255,255,0.06);
  }
  .tag {
    display: inline-block; padding: 3px 10px; border-radius: 20px;
    font-size: 12px; font-weight: 600; margin: 2px;
    background: rgba(255,107,0,0.2); color: #FF6B00;
  }
  .at-a-glance-row {
    display: flex; align-items: center; justify-content: space-between;
    padding: 6px 0; border-bottom: 1px solid rgba(255,255,255,0.04);
  }
  .aag-label { color: #888; font-size: 13px; }
  .aag-value { font-size: 13px; font-weight: 600; }
  .green { color: #00C853; } .red { color: #FF1744; }
  .neutral { color: #FFD600; }
  .disclaimer { font-size: 11px; color: #555; text-align: center;
    border-top: 1px solid #222; padding-top: 10px; margin-top: 30px; }
</style>
""", unsafe_allow_html=True)

col_h1, col_h2 = st.columns([4,1])
with col_h1:
    st.markdown("## 🔍 Stock Analyzer")
    st.caption("Educational research tool — not investment advice")
with col_h2:
    st.markdown(f"""
    <div style="text-align:right;padding-top:10px;">
      <span style="font-size:13px;color:{_ms_status['color']};font-weight:700;">{_ms_status['label']}</span><br>
      <span style="font-size:11px;color:#555;">{timestamp_ist()}</span>
    </div>""", unsafe_allow_html=True)
    if st.button("🔄 Refresh", key="sa_manual_refresh"):
        st.cache_data.clear()
        st.rerun()

# ── Search Bar ────────────────────────────────────────────────────────────────
c1, c2 = st.columns([3, 1])
with c1:
    raw_input = st.text_input(
        "Enter NSE symbol",
        value="RELIANCE",
        placeholder="e.g. TCS, HDFCBANK, INFY",
        help="Enter the NSE symbol without .NS — it will be added automatically.",
    )
with c2:
    st.markdown("<br>", unsafe_allow_html=True)
    popular = st.selectbox("Popular stocks", ["— pick one —"] + POPULAR_STOCKS,
                           key="popular_select", label_visibility="collapsed")
    if popular != "— pick one —":
        raw_input = popular

ticker = normalise_symbol(raw_input)

# ── Load Data ─────────────────────────────────────────────────────────────────
with st.spinner(f"Loading data for {ticker}…"):
    info       = get_fundamentals(ticker)
    financials = get_financials(ticker)
    quote      = get_quote(ticker)

if "error" in info and not info.get("longName"):
    st.error(f"Could not load data for **{ticker}**. Check the symbol and try again.")
    st.stop()

name     = info.get("longName") or info.get("shortName") or ticker
sector   = info.get("sector",   "Unknown")
industry = info.get("industry", "Unknown")
cmp      = quote.get("price") or info.get("currentPrice") or info.get("regularMarketPrice")
pct      = quote.get("pct", 0)
mc       = info.get("marketCap") or quote.get("market_cap")
pe       = info.get("trailingPE")
beta     = info.get("beta")
h52      = info.get("fiftyTwoWeekHigh") or quote.get("52w_high")
l52      = info.get("fiftyTwoWeekLow")  or quote.get("52w_low")

# ── Header ────────────────────────────────────────────────────────────────────
up = pct >= 0
st.markdown(f"""
<div class="header-card">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;">
    <div>
      <div style="font-size:24px;font-weight:700;">{name}</div>
      <div style="color:#888;font-size:14px;margin:4px 0;">
        {ticker} &nbsp;·&nbsp;
        <span class="tag">{sector}</span>
        <span class="tag">{industry}</span>
      </div>
    </div>
    <div style="text-align:right;">
      <div style="font-size:28px;font-weight:700;">₹{cmp:,.2f}</div>
      <div style="font-size:16px;color:{'#00C853' if up else '#FF1744'};">
        {'▲' if up else '▼'} {abs(pct):.2f}% today
      </div>
    </div>
  </div>
  <div style="display:flex;gap:24px;margin-top:12px;flex-wrap:wrap;">
    <div><span style="color:#888;font-size:12px;">Market Cap</span><br>
         <b>{format_market_cap(mc)}</b></div>
    <div><span style="color:#888;font-size:12px;">Trailing P/E</span><br>
         <b>{f"{pe:.1f}x" if pe else "N/A"}</b></div>
    <div><span style="color:#888;font-size:12px;">Beta</span><br>
         <b>{f"{beta:.2f}" if beta else "N/A"}</b></div>
    <div><span style="color:#888;font-size:12px;">52W High</span><br>
         <b>{format_inr(h52)}</b></div>
    <div><span style="color:#888;font-size:12px;">52W Low</span><br>
         <b>{format_inr(l52)}</b></div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Snapshot / Gauges ─────────────────────────────────────────────────────────
period_key = st.radio("History period", list(CHART_PERIODS.keys()),
                      horizontal=True, index=5, key="sa_period")
df_hist = get_history(ticker, period_key)
tech    = compute_technicals(df_hist) if not df_hist.empty else {}

t_score, t_comp = technical_score(df_hist)
f_score, f_comp = fundamental_score(info)

tab_snap, tab_chart, tab_tech, tab_fund, tab_ai = st.tabs([
    "📋 Snapshot", "📊 Charts", "📐 Technical", "💰 Fundamental", "🤖 AI Analysis"
])

# ─ Snapshot Tab ───────────────────────────────────────────────────────────────
with tab_snap:
    c1, c2, c3 = st.columns(3)

    with c1:
        st.markdown("#### At a Glance")
        roe_raw = info.get("returnOnEquity")
        roe_pct = roe_raw * 100 if roe_raw and abs(roe_raw) < 5 else roe_raw
        de_raw  = info.get("debtToEquity")
        promoter_raw = info.get("heldPercentInsiders")
        promoter_pct = (promoter_raw * 100 if promoter_raw and promoter_raw < 1
                        else promoter_raw)

        glance_items = [
            ("Trend",        trend_label(cmp, tech.get("ma200")) if cmp else "N/A"),
            ("Momentum",     rsi_label(tech.get("rsi"))),
            ("52-Week Pos.", week52_position(cmp, h52, l52) if cmp else "N/A"),
            ("Valuation",    pe_tier(pe)),
            ("Profitability",roe_tier(roe_pct)),
            ("Leverage",     de_tier(de_raw)),
            ("Volatility",   beta_label(beta)),
            ("Promoter Hldg",f"{promoter_pct:.1f}%" if promoter_pct else "N/A"),
        ]
        for label, value in glance_items:
            color_cls = ""
            if any(k in value for k in ["Strong", "Low", "Above", "Firm", "Near 52-week high"]):
                color_cls = "green"
            elif any(k in value for k in ["Weak", "Elevated", "Below", "Declining", "Loss"]):
                color_cls = "red"
            else:
                color_cls = "neutral"
            st.markdown(f"""
            <div class="at-a-glance-row">
              <span class="aag-label">{label}</span>
              <span class="aag-value {color_cls}">{value}</span>
            </div>""", unsafe_allow_html=True)

    with c2:
        st.markdown("#### Technical Strength")
        fig_tg = gauge_chart(t_score, "Technical Score", threshold=50)
        st.plotly_chart(fig_tg, use_container_width=True, config={"displayModeBar": False})

        for comp_name, comp_data in t_comp.items():
            pts = comp_data["points"]
            mx  = comp_data["max"]
            lbl = comp_data.get("label", "")
            val = comp_data.get("value", "")
            bar_pct = int(pts / mx * 100)
            bar_color = "#00C853" if bar_pct > 60 else ("#FFD600" if bar_pct > 30 else "#FF1744")
            st.markdown(f"""
            <div style="margin:4px 0;">
              <div style="display:flex;justify-content:space-between;font-size:12px;color:#888;">
                <span>{comp_name}</span>
                <span style="color:#FAFAFA;">{lbl}{' · ' + val if val else ''}</span>
              </div>
              <div style="background:#222;border-radius:4px;height:6px;margin-top:3px;">
                <div style="background:{bar_color};width:{bar_pct}%;height:6px;border-radius:4px;"></div>
              </div>
            </div>""", unsafe_allow_html=True)

    with c3:
        st.markdown("#### Fundamental Quality")
        fig_fg = gauge_chart(f_score, "Fundamental Score", threshold=50)
        st.plotly_chart(fig_fg, use_container_width=True, config={"displayModeBar": False})

        for comp_name, comp_data in f_comp.items():
            pts = comp_data["points"]
            mx  = comp_data["max"]
            lbl = comp_data.get("label", "")
            val = comp_data.get("value", "")
            bar_pct = int(pts / mx * 100)
            bar_color = "#00C853" if bar_pct > 60 else ("#FFD600" if bar_pct > 30 else "#FF1744")
            st.markdown(f"""
            <div style="margin:4px 0;">
              <div style="display:flex;justify-content:space-between;font-size:12px;color:#888;">
                <span>{comp_name}</span>
                <span style="color:#FAFAFA;">{lbl}{' · ' + val if val else ''}</span>
              </div>
              <div style="background:#222;border-radius:4px;height:6px;margin-top:3px;">
                <div style="background:{bar_color};width:{bar_pct}%;height:6px;border-radius:4px;"></div>
              </div>
            </div>""", unsafe_allow_html=True)

    # Key fundamentals table
    st.divider()
    st.markdown("#### Key Fundamentals")
    rev_growth   = info.get("revenueGrowth")
    earn_growth  = info.get("earningsGrowth")
    gross_margin = info.get("grossMargins")
    net_margin   = info.get("profitMargins")
    roe_raw2     = info.get("returnOnEquity")
    roce         = info.get("returnOnAssets")  # proxy
    div_yield    = info.get("dividendYield")
    curr_ratio   = info.get("currentRatio")
    quick_ratio  = info.get("quickRatio")
    pb           = info.get("priceToBook")
    ps           = info.get("priceToSalesTrailing12Months")
    ev_ebitda    = info.get("enterpriseToEbitda")
    float_shares = info.get("floatShares")

    def pct_fmt(v):
        if v is None: return "N/A"
        return f"{v*100:.1f}%" if abs(v) < 5 else f"{v:.1f}%"

    def x_fmt(v):
        return f"{v:.2f}x" if v else "N/A"

    fundam_data = {
        "Revenue Growth (YoY)": pct_fmt(rev_growth),
        "Earnings Growth (YoY)": pct_fmt(earn_growth),
        "Gross Margin": pct_fmt(gross_margin),
        "Net Margin": pct_fmt(net_margin),
        "ROE": pct_fmt(roe_raw2),
        "P/E (Trailing)": x_fmt(pe),
        "P/B": x_fmt(pb),
        "P/S": x_fmt(ps),
        "EV/EBITDA": x_fmt(ev_ebitda),
        "Dividend Yield": pct_fmt(div_yield),
        "Current Ratio": x_fmt(curr_ratio),
        "Quick Ratio": x_fmt(quick_ratio),
    }

    fund_cols = st.columns(4)
    for idx, (k, v) in enumerate(fundam_data.items()):
        with fund_cols[idx % 4]:
            st.metric(label=k, value=v)

# ─ Charts Tab ─────────────────────────────────────────────────────────────────
with tab_chart:
    chart_type = st.radio("Chart type", ["Area", "Price", "Candlestick", "Performance"],
                          horizontal=True, key="sa_chart_type")
    show_ma = st.multiselect("Moving average overlays", [20, 50, 100, 200],
                              default=[50, 200], key="sa_ma")

    if not df_hist.empty:
        fig_price = price_chart(df_hist, ticker, chart_type)
        if show_ma and chart_type != "Candlestick":
            fig_price = add_ma_overlays(fig_price, df_hist, show_ma)
        st.plotly_chart(fig_price, use_container_width=True, config={"displayModeBar": False})
    else:
        st.warning("Insufficient price history for the selected period.")

# ─ Technical Tab ──────────────────────────────────────────────────────────────
with tab_tech:
    if df_hist.empty:
        st.warning("No data for technical analysis.")
    else:
        st.markdown("#### RSI (14)")
        st.plotly_chart(rsi_chart(df_hist), use_container_width=True,
                        config={"displayModeBar": False})

        st.markdown("#### MACD (12, 26, 9)")
        st.plotly_chart(macd_chart(df_hist), use_container_width=True,
                        config={"displayModeBar": False})

        st.markdown("#### Key Levels")
        levels = {
            "Current Price":        format_inr(tech.get("current")),
            "20-DMA":               format_inr(tech.get("ma20")),
            "50-DMA":               format_inr(tech.get("ma50")),
            "100-DMA":              format_inr(tech.get("ma100")),
            "200-DMA":              format_inr(tech.get("ma200")),
            "BB Upper":             format_inr(tech.get("bb_upper")),
            "BB Mid":               format_inr(tech.get("bb_mid")),
            "BB Lower":             format_inr(tech.get("bb_lower")),
            "RSI (14)":             f"{tech.get('rsi', 0):.1f}" if tech.get("rsi") else "N/A",
            "ATR (14)":             format_inr(tech.get("atr")),
            "52W High":             format_inr(tech.get("52w_high")),
            "52W Low":              format_inr(tech.get("52w_low")),
            "% From 52W High":      f"{tech.get('pct_from_52w_high', 0):.1f}%",
        }
        lcols = st.columns(4)
        for idx, (k, v) in enumerate(levels.items()):
            with lcols[idx % 4]:
                st.metric(k, v)

# ─ Fundamental Tab ────────────────────────────────────────────────────────────
with tab_fund:
    if financials.get("error"):
        st.warning("Could not load financial statements.")
    else:
        c1, c2 = st.columns(2)
        with c1:
            st.plotly_chart(revenue_chart(financials), use_container_width=True,
                            config={"displayModeBar": False})
        with c2:
            st.plotly_chart(margin_chart(financials), use_container_width=True,
                            config={"displayModeBar": False})

        # Income Statement Table
        with st.expander("📄 Income Statement (Annual)"):
            df_inc = financials.get("income")
            if df_inc is not None and not df_inc.empty:
                df_display = (df_inc / 1e7).round(0)  # ₹ Crore
                df_display.columns = [str(c.year) for c in df_display.columns]
                st.dataframe(df_display.style.format("{:,.0f}"), use_container_width=True)
                st.caption("Values in ₹ Crore")

        with st.expander("🏛️ Balance Sheet (Annual)"):
            df_bs = financials.get("balance")
            if df_bs is not None and not df_bs.empty:
                df_display = (df_bs / 1e7).round(0)
                df_display.columns = [str(c.year) for c in df_display.columns]
                st.dataframe(df_display.style.format("{:,.0f}"), use_container_width=True)
                st.caption("Values in ₹ Crore")

        with st.expander("💸 Cash Flow (Annual)"):
            df_cf = financials.get("cashflow")
            if df_cf is not None and not df_cf.empty:
                df_display = (df_cf / 1e7).round(0)
                df_display.columns = [str(c.year) for c in df_display.columns]
                st.dataframe(df_display.style.format("{:,.0f}"), use_container_width=True)
                st.caption("Values in ₹ Crore")

# ─ AI Analysis Tab ────────────────────────────────────────────────────────────
with tab_ai:
    if not ANTHROPIC_API_KEY:
        st.warning("Add `ANTHROPIC_API_KEY` to your `.env` file to enable AI analysis.")
    else:
        if st.button("🤖 Generate AI Analysis", type="primary", key="sa_ai_btn"):
            with st.spinner("Claude is analysing the stock…"):
                analysis = analyse_stock(ticker, info, tech, financials)
            st.markdown(analysis)
        else:
            st.info("Click the button above to generate educational AI analysis for this stock.")

    st.caption("⚠️ AI analysis is educational only. Not financial advice.")

# ── F&O Section ───────────────────────────────────────────────────────────────
with st.expander("📊 F&O Data (Derivatives)"):
    st.info(
        "Live F&O data (open interest, PCR, max pain, IV) is not available from the "
        "current data source (yfinance). For F&O analytics, refer to NSE website or "
        "specialised platforms."
    )

# ── Disclaimer ────────────────────────────────────────────────────────────────
st.markdown(f'<div class="disclaimer">{DISCLAIMER}</div>', unsafe_allow_html=True)
