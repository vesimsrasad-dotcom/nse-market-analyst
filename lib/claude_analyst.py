"""
lib/claude_analyst.py
Claude-powered analysis for NSE Market Analyst.
All outputs are educational and explicitly non-advisory.
"""

import anthropic
import streamlit as st
from lib.config import ANTHROPIC_API_KEY, CLAUDE_MODEL, CLAUDE_MAX_TOKENS

SYSTEM_PROMPT = """You are an educational Indian equity market research assistant embedded in the 
NSE Market Analyst dashboard. Your role is to explain market data and provide neutral educational 
analysis for research purposes only.

STRICT RULES:
- Never say "Buy", "Sell", "Hold", "Accumulate", or give any trading recommendation.
- Never give a target price.
- Never promise or imply guaranteed returns.
- Always frame insights as educational observations, not advice.
- Use neutral language: "appears", "suggests", "indicates", "may", "historically".
- Consider Indian market-specific factors: RBI cycle, USD/INR, crude oil, monsoon, GST, SEBI.
- End every analysis with: a brief reminder that this is for educational purposes only.
- Format using markdown with clear sections."""


def _get_client():
    if not ANTHROPIC_API_KEY:
        return None
    return anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


def _call_claude(prompt: str, max_tokens: int = CLAUDE_MAX_TOKENS) -> str:
    client = _get_client()
    if client is None:
        return "⚠️ **Claude API key not configured.** Add `ANTHROPIC_API_KEY` to your `.env` file to enable AI analysis."
    try:
        message = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=max_tokens,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text
    except anthropic.AuthenticationError:
        return "⚠️ **Invalid Claude API key.** Please check your `.env` file."
    except anthropic.RateLimitError:
        return "⚠️ **API rate limit reached.** Please wait a moment and try again."
    except Exception as e:
        return f"⚠️ **Claude API error:** {str(e)}"


# ── Stock Analysis ────────────────────────────────────────────────────────────

def analyse_stock(ticker: str, info: dict, technicals: dict, financials: dict) -> str:
    """Generate educational stock analysis."""
    name        = info.get("longName", ticker)
    sector      = info.get("sector", "Unknown")
    industry    = info.get("industry", "Unknown")
    cmp         = info.get("currentPrice") or info.get("regularMarketPrice", "N/A")
    pe          = info.get("trailingPE", "N/A")
    pb          = info.get("priceToBook", "N/A")
    roe         = info.get("returnOnEquity", "N/A")
    de          = info.get("debtToEquity", "N/A")
    rev_growth  = info.get("revenueGrowth", "N/A")
    earn_growth = info.get("earningsGrowth", "N/A")
    gross_margin= info.get("grossMargins", "N/A")
    net_margin  = info.get("profitMargins", "N/A")
    rsi         = technicals.get("rsi", "N/A")
    ma200       = technicals.get("ma200", "N/A")
    beta        = info.get("beta", "N/A")
    promoter    = info.get("heldPercentInsiders", "N/A")

    prompt = f"""Provide an educational research overview of **{name} ({ticker})** for an Indian retail investor.

## Company Context
- Sector: {sector} | Industry: {industry}
- CMP: ₹{cmp}

## Key Data Points
- Trailing P/E: {pe} | P/B: {pb}
- ROE: {roe} | D/E: {de}
- Revenue Growth (YoY): {rev_growth} | Earnings Growth: {earn_growth}
- Gross Margin: {gross_margin} | Net Margin: {net_margin}
- Beta: {beta} | RSI(14): {rsi}
- 200-DMA: {ma200}
- Promoter Holding: {promoter}

## Structure your analysis with these sections:
1. **Business Overview** — what the company does, its market position in India
2. **Earnings Quality** — revenue/profit trends, margin direction, cash flow observations
3. **Valuation Context** — how current multiples compare to historical norms and peers (educational observation only)
4. **Technical Observations** — price trend, momentum, moving average context
5. **Key Risk Factors** — business, macro, regulatory, competitive risks specific to India
6. **Bull Case** — what could drive positive outcomes
7. **Bear Case** — what could weigh on performance
8. **India-Specific Macro Sensitivity** — impact of RBI rates, INR, crude oil, government policy
9. **Corporate Governance Notes** — any observations on promoter holding, pledging, related-party risk
10. **Research Summary** — neutral conclusion (use: "risk-reward appears...", "valuation appears...", "earnings momentum appears...")

Conclude with: *This analysis is for educational purposes only and does not constitute investment advice.*"""

    return _call_claude(prompt, max_tokens=1800)


# ── Portfolio Analysis ────────────────────────────────────────────────────────

def analyse_portfolio(summary: str) -> str:
    prompt = f"""Provide an educational portfolio review for an Indian investor based on the following holdings data:

{summary}

Structure the response as:
1. **Portfolio Composition Overview** — sector and stock concentration observations
2. **Diversification Assessment** — gaps, over-concentration, correlation risks
3. **Risk Profile Observations** — beta, volatility, drawdown characteristics of the portfolio
4. **Conservative Perspective** — what a risk-averse analyst might observe
5. **Balanced Perspective** — what a moderate-risk analyst might observe
6. **Growth-Oriented Perspective** — what an aggressive analyst might observe
7. **Key Risks** — top 3-5 risks for this specific portfolio combination
8. **Macro Sensitivity** — how this portfolio might respond to RBI rate changes, INR moves, crude oil, election cycle

Do NOT suggest buying or selling any specific security.
Conclude with: *This analysis is for educational purposes only and does not constitute investment advice.*"""
    return _call_claude(prompt, max_tokens=1500)


# ── News Analysis ─────────────────────────────────────────────────────────────

def analyse_news(ticker: str, company: str, news_items: list[dict]) -> str:
    if not news_items:
        return "No recent news found for this ticker."

    news_text = "\n".join([
        f"- [{n.get('publisher','?')}] {n.get('title','')}"
        for n in news_items[:8]
    ])

    prompt = f"""Categorise and explain the educational significance of these recent news headlines for {company} ({ticker}):

{news_text}

Structure response:
1. **News Categorisation** — label each headline: [Price-Sensitive / Earnings / Corporate Action / Sector / Macro / Regulatory / Noise]
2. **Key Themes** — what are the dominant narratives emerging
3. **Potential Financial Metric Impact** — which metrics (revenue, margin, debt) could be affected and how (educational observation)
4. **Temporary vs Structural** — for each major item, is the issue likely short-term noise or a longer-term structural change?
5. **India Market Context** — how does this news interact with current Indian macro environment

No buy/sell recommendations.
Conclude with: *This analysis is for educational purposes only.*"""
    return _call_claude(prompt, max_tokens=1200)


# ── Macro Pulse ───────────────────────────────────────────────────────────────

def macro_pulse(macro_data: dict) -> str:
    prompt = f"""Provide an educational macro analysis for Indian equity markets based on current indicators:

{macro_data}

Structure your response:
1. **Macro Environment Summary** — overall assessment of the Indian economy
2. **RBI & Interest Rate Outlook** — impact on borrowing costs, banking sector, NBFCs
3. **Inflation Context** — CPI/WPI trends and sectoral implications
4. **Currency & External** — USD/INR, crude oil, forex reserves impact
5. **Sectoral Impact Matrix**:
   - Banks & NBFCs
   - Information Technology (INR hedging, global demand)
   - Automobiles (commodity costs, financing rates)
   - FMCG (rural demand, inflation pass-through)
   - Metals & Mining (global cycles, China demand)
   - Capital Goods / Infrastructure (government capex)
   - Real Estate (interest rates, affordability)
   - PSUs (government ownership, divestment)
6. **Key Risks on the Horizon** — top 3-5 macro risks for Indian markets

Educational framing only. No investment recommendations.
Conclude with: *This analysis is for educational purposes only.*"""
    return _call_claude(prompt, max_tokens=1500)


# ── ETF / Index Analysis ──────────────────────────────────────────────────────

def analyse_etf(name: str, ticker: str, info: dict, hist_summary: str) -> str:
    prompt = f"""Provide an educational analysis of the Indian ETF/Index: **{name} ({ticker})**

Info: {info}
Historical Performance Summary: {hist_summary}

Cover:
1. **What This ETF/Index Tracks** — underlying index, methodology
2. **Historical Return Context** — periods of outperformance and underperformance
3. **Cost & Efficiency** — expense ratio observations (if available)
4. **Risk Characteristics** — sector concentration, volatility profile
5. **Macro Sensitivity** — what conditions tend to favour or hinder this index
6. **India-Specific Notes** — regulatory changes, rebalancing effects, liquidity

No buy/sell recommendations.
Conclude with: *This analysis is for educational purposes only.*"""
    return _call_claude(prompt, max_tokens=1000)


# ── Corporate Action Explainer ────────────────────────────────────────────────

def explain_corporate_action(action_type: str, company: str, details: str) -> str:
    prompt = f"""Explain the following corporate action in simple educational terms for an Indian retail investor:

Company: {company}
Action: {action_type}
Details: {details}

Cover:
1. **What is a {action_type}?** — simple definition
2. **Mechanics** — how this specific action works
3. **Impact on Share Count** — how total shares outstanding change
4. **Price Adjustment** — how stock price is typically adjusted
5. **Impact on Cost Basis** — for existing shareholders, how does their average cost change
6. **Impact on Market Cap** — does total market cap change?
7. **Tax Implications** — general educational note (not tax advice) on Indian taxation
8. **Retail Investor Considerations** — what retail investors typically note about such actions

Conclude with: *This explanation is for educational purposes only. Consult a SEBI-registered adviser for advice specific to your situation.*"""
    return _call_claude(prompt, max_tokens=900)
