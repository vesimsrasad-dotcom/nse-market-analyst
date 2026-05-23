"""
lib/risk.py
Risk metrics for NSE Market Analyst.
"""

import numpy as np
import pandas as pd


def max_drawdown(prices: pd.Series) -> float:
    """Maximum drawdown from peak (as negative %)."""
    roll_max = prices.cummax()
    drawdown = (prices - roll_max) / roll_max
    return float(drawdown.min() * 100)


def annualised_volatility(prices: pd.Series, trading_days: int = 252) -> float:
    """Annualised volatility (%) from daily returns."""
    returns = prices.pct_change().dropna()
    return float(returns.std() * np.sqrt(trading_days) * 100)


def sharpe_ratio(prices: pd.Series, risk_free: float = 0.065,
                 trading_days: int = 252) -> float:
    """Simplified Sharpe ratio (daily returns vs risk-free rate)."""
    returns = prices.pct_change().dropna()
    excess  = returns - (risk_free / trading_days)
    std     = returns.std()
    if std == 0:
        return 0.0
    return float(excess.mean() / std * np.sqrt(trading_days))


def portfolio_volatility_score(df_portfolio: pd.DataFrame) -> str:
    """
    Very rough portfolio volatility score based on individual stock beta values.
    """
    if df_portfolio.empty or "Beta" not in df_portfolio.columns:
        return "Unavailable"
    betas = df_portfolio["Beta"].dropna()
    if betas.empty:
        return "Unavailable"
    avg_beta = betas.mean()
    if avg_beta < 0.7:
        return "Lower volatility portfolio"
    if avg_beta < 1.1:
        return "Market-aligned volatility"
    return "Higher volatility portfolio"


def drawdown_risk_label(dd: float) -> str:
    if dd > -10:
        return "Low drawdown"
    if dd > -25:
        return "Moderate drawdown"
    if dd > -40:
        return "Elevated drawdown"
    return "Severe drawdown"
