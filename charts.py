"""
lib/charts.py
Plotly chart builders for NSE Market Analyst.
All charts use plotly_dark theme with Indian market conventions.
"""

import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from lib.config import COLOR_GREEN, COLOR_RED, COLOR_ORANGE, COLOR_GOLD, COLOR_BLUE


# ── Shared Layout Helper ──────────────────────────────────────────────────────

def _base_layout(title: str = "", height: int = 450, **kwargs) -> dict:
    return dict(
        template="plotly_dark",
        title=dict(text=title, font=dict(size=16, color="#FAFAFA")),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=height,
        margin=dict(l=50, r=30, t=50, b=40),
        font=dict(family="sans-serif", size=13, color="#FAFAFA"),
        legend=dict(bgcolor="rgba(0,0,0,0)", borderwidth=0),
        **kwargs,
    )


# ── Sparkline ─────────────────────────────────────────────────────────────────

def sparkline(prices: list[float], positive: bool = True) -> go.Figure:
    """Tiny inline sparkline for market cards."""
    color = COLOR_GREEN if positive else COLOR_RED
    fig = go.Figure(
        go.Scatter(
            y=prices,
            mode="lines",
            line=dict(color=color, width=1.5),
            fill="tozeroy",
            fillcolor=f"rgba({'0,200,83' if positive else '255,23,68'},0.15)",
        )
    )
    fig.update_layout(
        height=60,
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        showlegend=False,
    )
    return fig


# ── Price / Performance Chart ─────────────────────────────────────────────────

def price_chart(df: pd.DataFrame, ticker: str, chart_type: str = "Area") -> go.Figure:
    """
    Main price chart supporting: Area, Price (line), Candlestick, Performance.
    """
    if df.empty:
        return _empty_fig("No data available")

    fig = go.Figure()
    close  = df["Close"]
    start  = close.iloc[0]
    end    = close.iloc[-1]
    ret    = (end / start - 1) * 100
    up     = end >= start
    color  = COLOR_GREEN if up else COLOR_RED

    if chart_type == "Candlestick":
        fig.add_trace(go.Candlestick(
            x=df.index, open=df["Open"], high=df["High"],
            low=df["Low"],  close=close,
            increasing_line_color=COLOR_GREEN,
            decreasing_line_color=COLOR_RED,
            name=ticker,
        ))

    elif chart_type == "Performance":
        perf = (close / start - 1) * 100
        # Split green / red fill relative to 0
        fig.add_trace(go.Scatter(
            x=df.index, y=perf,
            mode="lines",
            line=dict(color=color, width=2),
            name="Return (%)",
            fill="tozeroy",
            fillcolor=f"rgba({'0,200,83' if up else '255,23,68'},0.18)",
        ))
        fig.add_hline(y=0, line_color="#555", line_dash="dash")

    elif chart_type == "Area":
        fig.add_trace(go.Scatter(
            x=df.index, y=close,
            mode="lines",
            line=dict(color=color, width=2),
            name=ticker,
            fill="tozeroy",
            fillcolor=f"rgba({'0,200,83' if up else '255,23,68'},0.18)",
        ))
        # Baseline reference
        fig.add_hline(y=start, line_color="#555", line_dash="dash", line_width=1)

    else:  # Plain line
        fig.add_trace(go.Scatter(
            x=df.index, y=close,
            mode="lines",
            line=dict(color=COLOR_BLUE, width=2),
            name=ticker,
        ))

    # Volume subplot
    if "Volume" in df.columns and df["Volume"].sum() > 0:
        vol_colors = [COLOR_GREEN if df["Close"].iloc[i] >= df["Open"].iloc[i]
                      else COLOR_RED for i in range(len(df))]
        fig.add_trace(go.Bar(
            x=df.index, y=df["Volume"],
            marker_color=vol_colors,
            opacity=0.35,
            name="Volume",
            yaxis="y2",
        ))
        fig.update_layout(
            yaxis2=dict(
                overlaying="y",
                side="right",
                showgrid=False,
                showticklabels=False,
            )
        )

    # Return badge annotation
    badge_text = f"{'▲' if up else '▼'} {abs(ret):.2f}%"
    fig.add_annotation(
        x=1, y=1, xref="paper", yref="paper",
        text=badge_text,
        showarrow=False,
        font=dict(size=16, color=color),
        bgcolor="rgba(0,0,0,0.4)",
        bordercolor=color,
        borderwidth=1,
        borderpad=6,
        xanchor="right", yanchor="top",
    )

    fig.update_layout(**_base_layout(ticker, height=430))
    fig.update_xaxis(rangeslider_visible=False, showgrid=False)
    fig.update_yaxis(showgrid=True, gridcolor="rgba(255,255,255,0.05)")
    return fig


def add_ma_overlays(fig: go.Figure, df: pd.DataFrame, mas: list[int]) -> go.Figure:
    """Overlay moving averages on an existing price chart figure."""
    colors = {20: "#FFF176", 50: "#80DEEA", 100: "#CE93D8", 200: "#FF8A65"}
    for ma in mas:
        if len(df) >= ma:
            series = df["Close"].rolling(ma).mean()
            fig.add_trace(go.Scatter(
                x=df.index, y=series,
                mode="lines",
                line=dict(color=colors.get(ma, "#FFFFFF"), width=1.2, dash="dot"),
                name=f"{ma}-DMA",
            ))
    return fig


# ── Sector Bar Chart ──────────────────────────────────────────────────────────

def sector_bar(df_sector: pd.DataFrame, period: str = "1M") -> go.Figure:
    """Horizontal bar chart for sector returns."""
    if df_sector.empty:
        return _empty_fig("No sector data")

    df = df_sector.sort_values("Return (%)")
    colors = [COLOR_GREEN if v >= 0 else COLOR_RED for v in df["Return (%)"]]

    fig = go.Figure(go.Bar(
        x=df["Return (%)"],
        y=df["Sector"],
        orientation="h",
        marker_color=colors,
        text=[f"{v:+.2f}%" for v in df["Return (%)"]],
        textposition="outside",
    ))
    fig.update_layout(**_base_layout(f"NSE Sector Returns — {period}", height=380))
    fig.update_xaxis(zeroline=True, zerolinecolor="#555", ticksuffix="%")
    return fig


# ── Fundamental Charts ────────────────────────────────────────────────────────

def revenue_chart(financials: dict) -> go.Figure:
    """Bar chart of annual revenues."""
    df = financials.get("income")
    if df is None or df.empty:
        return _empty_fig("Revenue data unavailable")
    try:
        rev_row = df.loc[df.index.str.contains("Total Revenue|Revenue", case=False, na=False)]
        if rev_row.empty:
            return _empty_fig("Revenue row not found")
        rev = rev_row.iloc[0].dropna().sort_index() / 1e7  # Convert to Crore
        fig = go.Figure(go.Bar(
            x=[str(d.year) for d in rev.index],
            y=rev.values,
            marker_color=COLOR_BLUE,
            text=[f"₹{v:,.0f} Cr" for v in rev.values],
            textposition="outside",
        ))
        fig.update_layout(**_base_layout("Annual Revenue (₹ Cr)", height=320))
        return fig
    except Exception:
        return _empty_fig("Could not render revenue chart")


def margin_chart(financials: dict) -> go.Figure:
    """Line chart of operating and net margins."""
    df = financials.get("income")
    if df is None or df.empty:
        return _empty_fig("Margin data unavailable")
    try:
        rev_row = df.loc[df.index.str.contains("Total Revenue|Revenue", case=False, na=False)]
        op_row  = df.loc[df.index.str.contains("Operating Income|EBIT", case=False, na=False)]
        net_row = df.loc[df.index.str.contains("Net Income", case=False, na=False)]
        if rev_row.empty:
            return _empty_fig("Insufficient data for margin chart")

        rev = rev_row.iloc[0].dropna().sort_index()
        fig = go.Figure()

        if not op_row.empty:
            op = op_row.iloc[0].dropna().sort_index()
            shared_idx = rev.index.intersection(op.index)
            op_margin = (op[shared_idx] / rev[shared_idx] * 100).fillna(0)
            fig.add_trace(go.Scatter(
                x=[str(d.year) for d in shared_idx],
                y=op_margin.values, mode="lines+markers",
                name="Operating Margin", line=dict(color=COLOR_BLUE, width=2),
            ))

        if not net_row.empty:
            net = net_row.iloc[0].dropna().sort_index()
            shared_idx = rev.index.intersection(net.index)
            net_margin = (net[shared_idx] / rev[shared_idx] * 100).fillna(0)
            fig.add_trace(go.Scatter(
                x=[str(d.year) for d in shared_idx],
                y=net_margin.values, mode="lines+markers",
                name="Net Margin", line=dict(color=COLOR_GREEN, width=2),
            ))

        fig.update_layout(**_base_layout("Margin Trends (%)", height=320))
        fig.update_yaxis(ticksuffix="%")
        return fig
    except Exception:
        return _empty_fig("Could not render margin chart")


# ── Portfolio Charts ──────────────────────────────────────────────────────────

def portfolio_pie(df: pd.DataFrame, value_col: str = "Value (₹)",
                  label_col: str = "Name", title: str = "Portfolio Allocation") -> go.Figure:
    fig = go.Figure(go.Pie(
        labels=df[label_col],
        values=df[value_col],
        hole=0.45,
        marker=dict(line=dict(color="#0E1117", width=2)),
        textinfo="label+percent",
    ))
    fig.update_layout(**_base_layout(title, height=360))
    return fig


def portfolio_bar(df: pd.DataFrame) -> go.Figure:
    colors = [COLOR_GREEN if v >= 0 else COLOR_RED for v in df["P&L (%)"]]
    fig = go.Figure(go.Bar(
        x=df["Name"], y=df["P&L (%)"],
        marker_color=colors,
        text=[f"{v:+.1f}%" for v in df["P&L (%)"]],
        textposition="outside",
    ))
    fig.update_layout(**_base_layout("Unrealized P&L (%)", height=340))
    fig.update_yaxis(ticksuffix="%", zeroline=True, zerolinecolor="#555")
    return fig


# ── Gauge Charts ──────────────────────────────────────────────────────────────

def gauge_chart(value: float, title: str, min_val: float = 0,
                max_val: float = 100, threshold: float = 50) -> go.Figure:
    """Generic gauge for technical / fundamental strength (0-100)."""
    if value <= 33:
        color = COLOR_RED
    elif value <= 66:
        color = COLOR_GOLD
    else:
        color = COLOR_GREEN

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        title=dict(text=title, font=dict(size=14)),
        gauge=dict(
            axis=dict(range=[min_val, max_val], tickfont=dict(size=10)),
            bar=dict(color=color),
            bgcolor="rgba(255,255,255,0.05)",
            steps=[
                dict(range=[0,   33],  color="rgba(255,23,68,0.15)"),
                dict(range=[33,  66],  color="rgba(255,214,0,0.15)"),
                dict(range=[66, 100],  color="rgba(0,200,83,0.15)"),
            ],
            threshold=dict(
                line=dict(color="white", width=2),
                thickness=0.75,
                value=threshold,
            ),
        ),
        number=dict(font=dict(size=28)),
    ))
    fig.update_layout(
        height=230,
        margin=dict(l=20, r=20, t=50, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        template="plotly_dark",
    )
    return fig


# ── RSI Chart ─────────────────────────────────────────────────────────────────

def rsi_chart(df: pd.DataFrame) -> go.Figure:
    if df.empty:
        return _empty_fig("RSI unavailable")
    close  = df["Close"]
    delta  = close.diff()
    gain   = delta.clip(lower=0)
    loss   = -delta.clip(upper=0)
    avg_g  = gain.ewm(com=13, min_periods=14).mean()
    avg_l  = loss.ewm(com=13, min_periods=14).mean()
    rs     = avg_g / avg_l.replace(0, np.nan)
    rsi    = 100 - (100 / (1 + rs))

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df.index, y=rsi, mode="lines",
        line=dict(color=COLOR_ORANGE, width=1.8), name="RSI(14)",
    ))
    fig.add_hrect(y0=70, y1=100, fillcolor="rgba(255,23,68,0.08)", line_width=0)
    fig.add_hrect(y0=0,  y1=30,  fillcolor="rgba(0,200,83,0.08)",  line_width=0)
    fig.add_hline(y=70, line_dash="dash", line_color="#FF1744", line_width=1)
    fig.add_hline(y=30, line_dash="dash", line_color="#00C853", line_width=1)
    fig.add_hline(y=50, line_dash="dot",  line_color="#555",    line_width=1)
    fig.update_layout(**_base_layout("RSI (14)", height=200))
    fig.update_yaxis(range=[0, 100])
    return fig


# ── MACD Chart ────────────────────────────────────────────────────────────────

def macd_chart(df: pd.DataFrame) -> go.Figure:
    if df.empty:
        return _empty_fig("MACD unavailable")
    close  = df["Close"]
    ema12  = close.ewm(span=12, adjust=False).mean()
    ema26  = close.ewm(span=26, adjust=False).mean()
    macd   = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    hist   = macd - signal

    fig = go.Figure()
    hist_colors = [COLOR_GREEN if v >= 0 else COLOR_RED for v in hist]
    fig.add_trace(go.Bar(x=df.index, y=hist, marker_color=hist_colors, name="Histogram", opacity=0.7))
    fig.add_trace(go.Scatter(x=df.index, y=macd,   mode="lines", line=dict(color="#80DEEA", width=1.5), name="MACD"))
    fig.add_trace(go.Scatter(x=df.index, y=signal, mode="lines", line=dict(color="#FF8A65", width=1.5), name="Signal"))
    fig.add_hline(y=0, line_color="#555", line_dash="dash")
    fig.update_layout(**_base_layout("MACD (12,26,9)", height=220))
    return fig


# ── Macro Line Chart ──────────────────────────────────────────────────────────

def macro_line(dates: list, values: list, title: str,
               unit: str = "", color: str = COLOR_BLUE) -> go.Figure:
    fig = go.Figure(go.Scatter(
        x=dates, y=values, mode="lines+markers",
        line=dict(color=color, width=2),
        name=title,
    ))
    fig.update_layout(**_base_layout(title, height=300))
    if unit:
        fig.update_yaxis(ticksuffix=unit)
    return fig


# ── Helper ────────────────────────────────────────────────────────────────────

def _empty_fig(message: str = "No data") -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(
        text=message, x=0.5, y=0.5,
        xref="paper", yref="paper",
        showarrow=False, font=dict(size=14, color="#888"),
    )
    fig.update_layout(
        height=300,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        template="plotly_dark",
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
    )
    return fig
