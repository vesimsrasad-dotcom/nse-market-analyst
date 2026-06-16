"""
lib/portfolio.py
Portfolio CRUD helpers for NSE Market Analyst.
Persists to data/portfolio.json (gitignored).
"""
import json
import pathlib
import pandas as pd

DATA_DIR  = pathlib.Path("data")
PORT_FILE = DATA_DIR / "portfolio.json"


def _ensure_dir():
    DATA_DIR.mkdir(exist_ok=True)


def load_portfolio() -> list[dict]:
    _ensure_dir()
    if not PORT_FILE.exists():
        return []
    try:
        with open(PORT_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return []


def save_portfolio(holdings: list[dict]):
    _ensure_dir()
    with open(PORT_FILE, "w") as f:
        json.dump(holdings, f, indent=2)


def add_holding(holdings: list[dict], ticker: str, qty: float,
                avg_cost: float, sector: str = "", notes: str = "") -> list[dict]:
    for h in holdings:
        if h["ticker"].upper() == ticker.upper():
            old_qty  = h["qty"]
            old_cost = h["avg_cost"]
            total_qty = old_qty + qty
            new_cost  = (old_qty * old_cost + qty * avg_cost) / total_qty
            h["qty"]      = total_qty
            h["avg_cost"] = round(new_cost, 2)
            if sector:
                h["sector"] = sector
            if notes:
                h["notes"] = notes
            return holdings
    holdings.append({
        "ticker":   ticker,
        "qty":      qty,
        "avg_cost": round(avg_cost, 2),
        "sector":   sector,
        "notes":    notes,
    })
    return holdings


def remove_holding(holdings: list[dict], ticker: str) -> list[dict]:
    return [h for h in holdings if h["ticker"].upper() != ticker.upper()]


def portfolio_summary_text(df: pd.DataFrame) -> str:
    if df.empty:
        return "Empty portfolio."
    total_invested = df["Invested (₹)"].sum()
    total_value    = df["Value (₹)"].sum()
    total_pnl      = total_value - total_invested
    total_pnl_pct  = (total_pnl / total_invested * 100) if total_invested else 0
    lines = [
        f"Total Invested: ₹{total_invested:,.0f}",
        f"Current Value: ₹{total_value:,.0f}",
        f"Overall P&L: ₹{total_pnl:,.0f} ({total_pnl_pct:+.1f}%)",
        "",
        "Holdings:",
    ]
    for _, row in df.iterrows():
        lines.append(
            f"  {row['Name']} ({row['Ticker']}) — "
            f"Qty: {row['Qty']}, Avg: ₹{row['Avg Cost']:,.1f}, "
            f"CMP: ₹{row['CMP']:,.1f}, "
            f"Weight: {row['Value (₹)']/total_value*100:.1f}%, "
            f"P&L: {row['P&L (%)']:+.1f}%"
        )
    return "\n".join(lines)


def concentration_warnings(df: pd.DataFrame) -> list[str]:
    if df.empty:
        return []
    total    = df["Value (₹)"].sum()
    warnings = []
    for _, row in df.iterrows():
        wt = row["Value (₹)"] / total * 100
        if wt > 25:
            warnings.append(f"⚠️ {row['Name']} has a large weight of {wt:.1f}% in the portfolio.")
    if "Sector" in df.columns:
        sector_alloc = df.groupby("Sector")["Value (₹)"].sum() / total * 100
        for sec, wt in sector_alloc.items():
            if wt > 40 and sec != "Unknown":
                warnings.append(f"⚠️ Sector '{sec}' represents {wt:.1f}% of the portfolio.")
    if len(df) < 5:
        warnings.append("⚠️ Portfolio has fewer than 5 stocks — consider diversification.")
    return warnings
