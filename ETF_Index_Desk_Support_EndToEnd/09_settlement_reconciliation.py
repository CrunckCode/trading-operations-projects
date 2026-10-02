"""
Module 9: Settlement Break Reconciliation
==============================================
Matches the front-office blotter (the Module 7 TCA order set, real tickers/prices) against
a simulated custodian confirmation file, classifies breaks by type/severity, and ages
unresolved breaks into an escalation tracker - the same real desk task as reconciling
settlement breaks and entitlement mismatches with custody and fund accounting.
"""
import numpy as np
import pandas as pd
from config import DATA_DIR

np.random.seed(51)

# Reuse the real-priced order blotter generated conceptually in Module 7's pattern -
# rebuild a comparable real-ticker-priced blotter here so this module is self-contained
import yfinance as yf
etf = yf.Ticker("IVV")
holdings = etf.funds_data.top_holdings.reset_index()
holdings.columns = ["ticker", "name", "weight"]
tickers = holdings["ticker"].tolist()
prices = yf.download(tickers, period="5d", progress=False, auto_adjust=True)["Close"].iloc[-1]

N_TRADES = 400
blotter = pd.DataFrame({
    "trade_id": [f"T{200000+i}" for i in range(N_TRADES)],
    "ticker": np.random.choice(tickers, N_TRADES),
    "side": np.random.choice(["BUY", "SELL"], N_TRADES),
    "quantity": np.random.randint(100, 3000, N_TRADES),
})
blotter["price"] = blotter["ticker"].map(prices) * (1 + np.random.normal(0, 0.0008, N_TRADES))
blotter["settlement_date_offset"] = 1  # real T+1 settlement convention

custodian = blotter.copy()
n = N_TRADES
price_break_idx = np.random.choice(n, int(n * 0.07), replace=False)
custodian.loc[price_break_idx, "price"] *= (1 + np.random.choice([-1, 1], len(price_break_idx)) *
                                              np.random.uniform(0.003, 0.015, len(price_break_idx)))
remaining = np.setdiff1d(np.arange(n), price_break_idx)
qty_break_idx = np.random.choice(remaining, int(n * 0.04), replace=False)
custodian.loc[qty_break_idx, "quantity"] += np.random.choice([-1, 1], len(qty_break_idx)) * \
                                              np.random.randint(20, 300, len(qty_break_idx))
remaining2 = np.setdiff1d(remaining, qty_break_idx)
date_break_idx = np.random.choice(remaining2, int(n * 0.03), replace=False)
custodian.loc[date_break_idx, "settlement_date_offset"] += 1
remaining3 = np.setdiff1d(remaining2, date_break_idx)
missing_idx = np.random.choice(remaining3, int(n * 0.02), replace=False)
custodian = custodian.drop(index=missing_idx).reset_index(drop=True)

merged = blotter.merge(custodian, on="trade_id", how="left", suffixes=("_fo", "_custodian"))

PRICE_TOLERANCE_BPS = 5

def classify(row):
    if pd.isna(row["price_custodian"]):
        return "missing_confirm", "High"
    price_diff_bps = abs(row["price_fo"] - row["price_custodian"]) / row["price_fo"] * 10000
    qty_diff = abs(row["quantity_fo"] - row["quantity_custodian"])
    date_diff = abs(row["settlement_date_offset_fo"] - row["settlement_date_offset_custodian"])
    breaks = []
    if price_diff_bps > PRICE_TOLERANCE_BPS:
        breaks.append(("price_break", "High" if price_diff_bps > 100 else "Medium"))
    if qty_diff > 0:
        breaks.append(("quantity_break", "High" if qty_diff > 200 else "Medium"))
    if date_diff > 0:
        breaks.append(("settlement_date_break", "Low"))
    if not breaks:
        return "none", "N/A"
    rank = {"High": 3, "Medium": 2, "Low": 1}
    breaks.sort(key=lambda b: rank[b[1]], reverse=True)
    return breaks[0]

merged[["break_type", "severity"]] = merged.apply(lambda r: pd.Series(classify(r)), axis=1)
breaks = merged[merged["break_type"] != "none"]

print(f"Reconciled {len(blotter)} real-ticker-priced front-office trades against custodian "
      f"confirmations ({N_TRADES - len(custodian)} intentionally missing)")
print(f"\nBreak rate: {len(breaks)}/{len(merged)} ({len(breaks)/len(merged):.1%})")
print(breaks["break_type"].value_counts().to_string())
print("\nBy severity:")
print(breaks["severity"].value_counts().to_string())

np.random.seed(61)
breaks = breaks.copy()
breaks["days_outstanding"] = np.random.choice([0, 1, 2, 3, 4], len(breaks), p=[0.4, 0.25, 0.15, 0.12, 0.08])
breaks["escalation"] = np.where(breaks["days_outstanding"] >= 3, "ESCALATED - Ops Manager",
                          np.where((breaks["days_outstanding"] >= 1) & (breaks["severity"] == "High"),
                                   "ESCALATED - Team Lead", "Normal queue"))
print("\nEscalation status:")
print(breaks["escalation"].value_counts().to_string())

ticker_break_rate = merged.groupby("ticker_fo").apply(
    lambda g: (g["break_type"] != "none").mean(), include_groups=False)
print("\nBreak rate by real ticker:")
print(ticker_break_rate.sort_values(ascending=False).round(3).to_string())
