"""
pages/4_ _India_Macro.py
India Macro Dashboard.
"""

import streamlit as st
from lib.auth import check_password, logout_button
from streamlit_autorefresh import st_autorefresh
from lib.refresh import market_status, timestamp_ist
import pandas as pd
from lib.config import DISCLAIMER, ANTHROPIC_API_KEY
from lib.market_data import get_quote, get_history
from lib.macro_india import get_india_macro_dict, macro_summary_text
from lib.charts import macro_line
from lib.claude_analyst import macro_pulse

if not check_password(): st.stop()
_ms_status = market_status()
_count_macro = st_autorefresh(interval=_ms_status["interval_ms"], key="macro_autorefresh")
st.set_page_config(page_title="India Macro | NSE Market Analyst",
                   page_icon="🌏", layout="wide")

st.markdown("""
<style>
  html, body, [class*="css"] { font-size: 17px !important; }
  .macro-card { background:#1A1F2E; border-radius:10px; padding:14px 18px;
    border:1px solid rgba(255,255,255,0.06); margin-bottom:8px; text-align:center; }
  .macro-label { font-size:12px; color:#888; text-transform:uppercase; }
  .macro-val { font-size:22px; font-weight:700; color:#FAFAFA; }
  .disclaimer { font-size:11px; color:#555; text-align:center;
    border-top:1px solid #222; padding-top:10px; margin-top:30px; }
</style>
""", unsafe_allow_html=True)

col_h1, col_h2 = st.columns([4,1])
with col_h1:
    st.markdown("🌏 India Macro Dashboard")
    st.caption("Key economic indicators for India — educational reference")
with col_h2:
    st.markdown(f"""
    <div style="text-align:right;padding-top:10px;">
      <span style="font-size:13px;color={_ms_status['color']};font-weight:700;">{_ms_status['label']}</span><br>
      <span style="font-size:11px;color:#555;">{timestamp_ist()}</span>
    </div>""", unsafe_allow_html=True)
    if st.button("🔄 Refresh", key="macro_manual_refresh"):
        st.cache_data.clear()
        st.rerun()

# ── Live data supplements ─────────────────────────────────────────────────────
with st.spinner("Fetching live indicators…"):
    macro = get_india_macro_dict()
    # Live USD/INR
    q_inr = get_quote("INR=X")
    if q_inr.get("price"):
        macro["USD/INR"] = round(q_inr["price"], 2)
    # Live Crude (Brent proxy via CL=F)
    q_crude = get_quote("CL=F")
    if q_crude.get("price"):
        macro["Crude Oil WTI (USD/bbl)"] = round(q_crude["price"], 2)

# ── Macro Cards ───────────────────────────────────────────────────────────────
st.divider()
priority_keys = [
    "RBI Repo Rate (%)", "CPI Inflation (%)", "WPI Inflation (%)",
    "GDP Growth FY25E (%)", "10Y Gsec Yield (%)", "USD/INR",
    "Crude Oil WTI (USD/bbl)", "Forex Reserves (USD B)",
    "GST Collections (₹ Cr)", "Fiscal Deficit (% GDP)",
]

macro_cols = st.columns(5)
for i, key in enumerate(priority_keys):
    val = macro.get(key, "N/A")
    val_str = f"{val:,.2f}" if isinstance(val, float) else str(val)
    with macro_cols[i % 5]:
        st.markdown(f"""
        <div class="macro-card">
          <div class="macro-label">{key}</div>
          <div class="macro-val">{val_str}</div>
        </div>""", unsafe_allow_html=True)

st.caption("Sources: RBI, MOSPI, World Bank, yfinance. Figures are approximate/lagged. Always verify with official sources.")
st.divider()

# ── Trend Charts ──────────────────────────────────────────────────────────────
st.markdown("### Trend Charts")
tab_inr, tab_crude, tab_gold, tab_vix = st.tabs([
    "💱 USD/INR", "🛢️ Crude Oil", "🥇 Gold", "📉 India VIX"
])

with tab_inr:
    df_inr = get_history("INR=X", "1Y")
    if not df_inr.empty:
        fig = macro_line(df_inr.index, df_inr["Close"].tolist(),
                         "USD/INR Rate", unit=" ₹", color="#FFD600")
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

with tab_crude:
    df_crude = get_history("CL=F", "1Y")
    if not df_crude.empty:
        fig = macro_line(df_crude.index, df_crude["Close"].tolist(),
                         "Crude Oil WTI (USD/bbl)", unit=" $", color="#FF6B00")
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

with tab_gold:
    df_gold = get_history("GC=F", "1Y")
    if not df_gold.empty:
        fig = macro_line(df_gold.index, df_gold["Close"].tolist(),
                         "Gold Price (USD/oz)", unit=" $", color="#FFD600")
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

with tab_vix:
    df_vix = get_history("^INDIAVIX", "1Y")
    if not df_vix.empty:
        fig = macro_line(df_vix.index, df_vix["Close"].tolist(),
                         "India VIX", color="#CE93D8")
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    else:
        st.info("India VIX data not available via yfinance at this time.")

st.divider()

# ── Manual Data Upload ────────────────────────────────────────────────────────
with st.expander("📂 Upload Custom Macro CSV"):
    st.markdown("""
    You can upload a CSV with columns `Date` and `Value` for any macro indicator.
    """)
    uploaded = st.file_uploader("Upload CSV", type=["csv"], key="macro_upload")
    if uploaded:
        df_uploaded = pd.read_csv(uploaded)
        st.dataframe(df_uploaded.head(20), use_container_width=True)
        if "Date" in df_uploaded.columns and "Value" in df_uploaded.columns:
            label = st.text_input("Indicator label", value="Custom Indicator")
            fig = macro_line(pd.to_datetime(df_uploaded["Date"]),
                             df_uploaded["Value"].tolist(), label)
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

# ── Sector Impact Matrix ──────────────────────────────────────────────────────
st.markdown("### Macro — Sectoral Sensitivity")
impact_data = {
    "Sector": ["Banks / NBFCs", "IT", "Automobiles", "FMCG", "Metals",
                "Capital Goods", "Real Estate", "PSUs"],
    "RBI Rate ↑": ["⚠️ Margins pressure", "✅ Neutral", "⚠️ EMI rises",
                   "✅ Neutral", "✅ Neutral", "⚠️ Cost rises",
                   "⚠️ Demand falls", "✅ Neutral"],
    "USD/INR ↑ (Weaker ₹)": ["⚠️ Import costs", "✅ Positive (export)", "⚠️ Import cost",
                               "⚠️ Input costs", "✅ Export benefit", "⚠️ Input costs",
                               "⚠️ Negative", "Varies"],
    "Crude ↑": ["✅ Neutral", "✅ Neutral", "⚠️ Input costs", "⚠️ Logistics cost",
                 "✅ Positive (energy)", "✅ Positive", "✅ Neutral", "✅ Positive (oil PSUs)"],
    "High Inflation": ["⚠️ Policy tightening", "✅ Neutral", "⚠️ Demand hit",
                        "✅ Pricing power", "Varies", "⚠️ Cost pressure",
                        "⚠️ Affordability", "✅ Neutral"],
}
st.dataframe(pd.DataFrame(impact_data), use_container_width=True, hide_index=True)
st.caption("✅ = Generally positive  |  ⚠️ = Generally negative  |  Educational reference only")

st.divider()

# ── AI Macro Pulse ────────────────────────────────────────────────────────────
with st.expander("🤖 AI Macro Pulse Check"):
    if not ANTHROPIC_API_KEY:
        st.warning("Add `ANTHROPIC_API_KEY` to enable AI macro analysis.")
    else:
        if st.button("Generate Macro Pulse", type="primary", key="macro_ai_btn"):
            with st.spinner("Claude is generating macro analysis…"):
                summary = macro_summary_text(macro)
                analysis = macro_pulse(summary)
            st.markdown(analysis)

st.markdown(f'<div class="disclaimer">{DISCLAIMER}</div>', unsafe_allow_html=True)
