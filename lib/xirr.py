"""
lib/xirr.py
XIRR (Extended Internal Rate of Return) calculator for NSE Market Analyst.
Supports CSV / Excel upload with transaction history.
"""

import pandas as pd
import numpy as np
from datetime import datetime, date
from scipy.optimize import brentq


# ── XIRR Core ────────────────────────────────────────────────────────────────

def xirr(cashflows: list[tuple[date, float]], guess: float = 0.1) -> float | None:
    """
    Calculate XIRR given a list of (date, cashflow) tuples.
    Negative = outflow (buy), Positive = inflow (sell / current value).
    Returns annualised IRR as a decimal (e.g. 0.15 = 15%).
    """
    if len(cashflows) < 2:
        return None

    dates, amounts = zip(*cashflows)
    dates = [d if isinstance(d, date) else d.date() for d in dates]
    t0 = dates[0]
    days = [(d - t0).days for d in dates]

    def npv(rate):
        return sum(cf / (1 + rate) ** (d / 365.0)
                   for cf, d in zip(amounts, days))

    try:
        return brentq(npv, -0.9999, 100.0, maxiter=1000)
    except Exception:
        return None


def xirr_pct(cashflows: list[tuple[date, float]]) -> str:
    """Return XIRR as formatted percentage string."""
    r = xirr(cashflows)
    if r is None:
        return "N/A"
    return f"{r * 100:.2f}%"


# ── CSV / Excel Template ──────────────────────────────────────────────────────

TEMPLATE_COLUMNS = ["Date", "Ticker", "Type", "Quantity", "Price", "Notes"]
TEMPLATE_TYPES   = ["BUY", "SELL", "DIVIDEND"]

TEMPLATE_EXAMPLE = pd.DataFrame([
    {"Date": "2023-01-15", "Ticker": "RELIANCE", "Type": "BUY",  "Quantity": 10, "Price": 2500.00, "Notes": "Initial buy"},
    {"Date": "2023-06-10", "Ticker": "RELIANCE", "Type": "BUY",  "Quantity": 5,  "Price": 2350.00, "Notes": "Added more"},
    {"Date": "2023-09-01", "Ticker": "RELIANCE", "Type": "DIVIDEND", "Quantity": 15, "Price": 9.00, "Notes": "Interim dividend"},
    {"Date": "2024-03-20", "Ticker": "TCS",      "Type": "BUY",  "Quantity": 8,  "Price": 3800.00, "Notes": ""},
    {"Date": "2024-11-05", "Ticker": "TCS",      "Type": "SELL", "Quantity": 4,  "Price": 4200.00, "Notes": "Partial exit"},
])


# ── Parse Uploaded File ───────────────────────────────────────────────────────

def parse_transaction_file(uploaded_file) -> tuple[pd.DataFrame, list[str]]:
    """
    Parse uploaded CSV or Excel file into a clean transactions DataFrame.
    Returns (df, errors).
    """
    errors = []
    try:
        name = uploaded_file.name.lower()
        if name.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        elif name.endswith((".xlsx", ".xls")):
            df = pd.read_excel(uploaded_file)
        else:
            return pd.DataFrame(), ["Unsupported file type. Please upload CSV or Excel (.xlsx)."]
    except Exception as e:
        return pd.DataFrame(), [f"Could not read file: {e}"]

    # Normalise column names
    df.columns = [c.strip().title() for c in df.columns]

    missing = [c for c in TEMPLATE_COLUMNS if c not in df.columns and c != "Notes"]
    if missing:
        return pd.DataFrame(), [f"Missing columns: {', '.join(missing)}. Required: {', '.join(TEMPLATE_COLUMNS[:-1])}"]

    # Parse dates
    try:
        df["Date"] = pd.to_datetime(df["Date"]).dt.date
    except Exception:
        errors.append("Some dates could not be parsed. Use YYYY-MM-DD format.")

    # Normalise
    df["Ticker"] = df["Ticker"].str.strip().str.upper()
    df["Type"]   = df["Type"].str.strip().str.upper()
    df["Quantity"] = pd.to_numeric(df["Quantity"], errors="coerce").fillna(0)
    df["Price"]    = pd.to_numeric(df["Price"],    errors="coerce").fillna(0)

    invalid_types = df[~df["Type"].isin(TEMPLATE_TYPES)]
    if not invalid_types.empty:
        errors.append(f"Unknown transaction types found: {invalid_types['Type'].unique().tolist()}. Use BUY, SELL, or DIVIDEND.")

    df = df.sort_values("Date").reset_index(drop=True)
    return df, errors


# ── Build Cashflows from Transactions ─────────────────────────────────────────

def build_cashflows(df: pd.DataFrame, current_prices: dict[str, float]) -> dict[str, list]:
    """
    Build cashflow lists per ticker and for the whole portfolio.
    current_prices: {ticker: current_price}
    Returns dict with per-ticker and portfolio cashflows.
    """
    result = {}
    all_flows = []

    for ticker, group in df.groupby("Ticker"):
        flows = []
        remaining_qty = 0

        for _, row in group.iterrows():
            d   = row["Date"]
            qty = row["Quantity"]
            px  = row["Price"]
            typ = row["Type"]

            if typ == "BUY":
                flows.append((d, -(qty * px)))   # outflow
                all_flows.append((d, -(qty * px)))
                remaining_qty += qty
            elif typ == "SELL":
                flows.append((d, qty * px))       # inflow
                all_flows.append((d, qty * px))
                remaining_qty -= qty
            elif typ == "DIVIDEND":
                flows.append((d, qty * px))       # inflow
                all_flows.append((d, qty * px))

        # Add current market value as final inflow
        norm_ticker = ticker if ticker.endswith(".NS") or ticker.endswith(".BO") else ticker + ".NS"
        cur_price = current_prices.get(norm_ticker) or current_prices.get(ticker, 0)
        if remaining_qty > 0 and cur_price > 0:
            today = date.today()
            flows.append((today, remaining_qty * cur_price))
            all_flows.append((today, remaining_qty * cur_price))

        result[ticker] = flows

    result["__portfolio__"] = all_flows
    return result


# ── Summary Table ─────────────────────────────────────────────────────────────

def xirr_summary(df: pd.DataFrame, current_prices: dict[str, float]) -> pd.DataFrame:
    """Build a per-ticker XIRR summary DataFrame."""
    cashflows = build_cashflows(df, current_prices)
    rows = []

    for ticker, flows in cashflows.items():
        if ticker == "__portfolio__":
            continue
        norm = ticker if ticker.endswith(".NS") else ticker + ".NS"
        cur  = current_prices.get(norm) or current_prices.get(ticker, 0)

        # Quantities
        buys  = df[(df["Ticker"] == ticker) & (df["Type"] == "BUY")]
        sells = df[(df["Ticker"] == ticker) & (df["Type"] == "SELL")]
        divs  = df[(df["Ticker"] == ticker) & (df["Type"] == "DIVIDEND")]

        total_invested = (buys["Quantity"] * buys["Price"]).sum()
        total_sold     = (sells["Quantity"] * sells["Price"]).sum()
        total_divs     = (divs["Quantity"] * divs["Price"]).sum()
        remaining_qty  = buys["Quantity"].sum() - sells["Quantity"].sum()
        cur_value      = remaining_qty * cur if cur else 0

        xi = xirr(flows)
        rows.append({
            "Ticker":          ticker,
            "Invested (₹)":    round(total_invested, 0),
            "Realised (₹)":    round(total_sold, 0),
            "Dividends (₹)":   round(total_divs, 0),
            "Current Value (₹)": round(cur_value, 0),
            "Remaining Qty":   remaining_qty,
            "XIRR (%)":        round(xi * 100, 2) if xi else None,
        })

    return pd.DataFrame(rows)
