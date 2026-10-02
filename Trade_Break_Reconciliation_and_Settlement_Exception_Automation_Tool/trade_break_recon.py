"""
Trade Break Reconciliation and Settlement Exception Automation Tool
========================================================================
Matches a front-office blotter against a custodian confirmation file (synthetic trade
records, but priced off REAL recent closing prices for a basket of real tickers),
classifies breaks by type and severity, ages unresolved breaks into an escalation
tracker, and ranks counterparties by chronic break rate.
"""
import numpy as np
import pandas as pd
import yfinance as yf
import datetime

np.random.seed(31)
TODAY = datetime.date.today()

# ===========================================================================
# 1. Real recent closing prices for a basket of real tickers (seeds realistic
#    trade prices rather than arbitrary numbers)
# ===========================================================================
TICKERS = ["AAPL", "MSFT", "JPM", "XOM", "JNJ", "PG", "V", "DIS"]
prices = yf.download(TICKERS, period="5d", progress=False, auto_adjust=True)["Close"].iloc[-1]
print("Real recent closing prices used to seed trade records:")
print(prices.round(2).to_string())

COUNTERPARTIES = ["Goldman Sachs", "Morgan Stanley", "JPMorgan", "Citadel Securities",
                   "Virtu Financial", "Jane Street"]

# ===========================================================================
# 2. Generate the front-office blotter (the "true" trades)
# ===========================================================================
N_TRADES = 400
trade_ids = [f"T{100000+i}" for i in range(N_TRADES)]
blotter = pd.DataFrame({
    "trade_id": trade_ids,
    "ticker": np.random.choice(TICKERS, N_TRADES),
    "side": np.random.choice(["BUY", "SELL"], N_TRADES),
    "counterparty": np.random.choice(COUNTERPARTIES, N_TRADES,
                                       p=[0.25, 0.20, 0.20, 0.15, 0.12, 0.08]),
    "trade_date": pd.Timestamp(TODAY) - pd.to_timedelta(np.random.randint(0, 5, N_TRADES), unit="D"),
})
blotter["quantity"] = np.random.randint(1000, 50000, N_TRADES)
blotter["price"] = blotter["ticker"].map(prices) * (1 + np.random.normal(0, 0.001, N_TRADES))
blotter["settlement_date"] = blotter["trade_date"] + pd.Timedelta(days=1)  # real T+1 convention

# ===========================================================================
# 3. Generate the custodian confirmation file - mostly matches, with seeded breaks
# ===========================================================================
custodian = blotter.copy()
break_types_assigned = np.full(N_TRADES, "none", dtype=object)

# Price breaks: 8% of trades, custodian price differs meaningfully
price_break_idx = np.random.choice(N_TRADES, int(N_TRADES * 0.08), replace=False)
custodian.loc[price_break_idx, "price"] *= (1 + np.random.choice([-1, 1], len(price_break_idx)) *
                                              np.random.uniform(0.003, 0.02, len(price_break_idx)))
break_types_assigned[price_break_idx] = "price_break"

# Quantity breaks: 5% of remaining trades
remaining = np.setdiff1d(np.arange(N_TRADES), price_break_idx)
qty_break_idx = np.random.choice(remaining, int(N_TRADES * 0.05), replace=False)
custodian.loc[qty_break_idx, "quantity"] += np.random.choice([-1, 1], len(qty_break_idx)) * \
                                              np.random.randint(50, 2000, len(qty_break_idx))
break_types_assigned[qty_break_idx] = "quantity_break"

# Settlement-date breaks: 4% of remaining trades
remaining2 = np.setdiff1d(remaining, qty_break_idx)
date_break_idx = np.random.choice(remaining2, int(N_TRADES * 0.04), replace=False)
custodian.loc[date_break_idx, "settlement_date"] += pd.Timedelta(days=1)
break_types_assigned[date_break_idx] = "settlement_date_break"

# Missing confirmation: 3% of remaining trades - custodian never received/booked
remaining3 = np.setdiff1d(remaining2, date_break_idx)
missing_idx = np.random.choice(remaining3, int(N_TRADES * 0.03), replace=False)
custodian = custodian.drop(index=missing_idx).reset_index(drop=True)
break_types_assigned[missing_idx] = "missing_confirm"

print(f"\nGenerated {len(blotter)} front-office trades and {len(custodian)} custodian "
      f"confirmations ({N_TRADES - len(custodian)} intentionally missing)")

# ===========================================================================
# 4. Matching engine: join on trade_id, flag mismatches within tolerance
# ===========================================================================
PRICE_TOLERANCE_BPS = 5  # breaks smaller than this are not flagged (rounding/timing noise)
merged = blotter.merge(custodian, on="trade_id", how="left", suffixes=("_fo", "_custodian"))

def classify_break(row):
    if pd.isna(row["price_custodian"]):
        return "missing_confirm", "High"
    price_diff_bps = abs(row["price_fo"] - row["price_custodian"]) / row["price_fo"] * 10000
    qty_diff = abs(row["quantity_fo"] - row["quantity_custodian"])
    date_diff = abs((row["settlement_date_fo"] - row["settlement_date_custodian"]).days)
    breaks = []
    if price_diff_bps > PRICE_TOLERANCE_BPS:
        breaks.append(("price_break", "High" if price_diff_bps > 100 else "Medium"))
    if qty_diff > 0:
        breaks.append(("quantity_break", "High" if qty_diff > 1000 else "Medium"))
    if date_diff > 0:
        breaks.append(("settlement_date_break", "Low"))
    if not breaks:
        return "none", "N/A"
    # Return the highest-severity break type
    severity_rank = {"High": 3, "Medium": 2, "Low": 1}
    breaks.sort(key=lambda b: severity_rank[b[1]], reverse=True)
    return breaks[0]

merged[["break_type", "severity"]] = merged.apply(
    lambda r: pd.Series(classify_break(r)), axis=1)

break_summary = merged[merged["break_type"] != "none"]
print("\n" + "=" * 80)
print("BREAK CLASSIFICATION SUMMARY")
print("=" * 80)
print(break_summary["break_type"].value_counts().to_string())
print(f"\nTotal breaks: {len(break_summary)} of {len(merged)} trades "
      f"({len(break_summary)/len(merged):.1%} break rate)")
print("\nBy severity:")
print(break_summary["severity"].value_counts().to_string())

# ===========================================================================
# 5. Aging / escalation: unresolved breaks get escalated by days outstanding
# ===========================================================================
np.random.seed(41)
break_summary = break_summary.copy()
break_summary["days_outstanding"] = np.random.choice([0, 1, 2, 3, 4, 5], len(break_summary),
                                                        p=[0.35, 0.25, 0.15, 0.10, 0.08, 0.07])

def escalation_tier(days, severity):
    if days >= 3:
        return "ESCALATED - Ops Manager"
    elif days >= 1 and severity == "High":
        return "ESCALATED - Team Lead"
    elif days >= 2:
        return "ESCALATED - Team Lead"
    else:
        return "Normal queue"

break_summary["escalation_status"] = break_summary.apply(
    lambda r: escalation_tier(r["days_outstanding"], r["severity"]), axis=1)

print("\n" + "=" * 80)
print("AGING / ESCALATION REPORT")
print("=" * 80)
print(break_summary["escalation_status"].value_counts().to_string())
escalated = break_summary[break_summary["escalation_status"] != "Normal queue"]
print(f"\n{len(escalated)} of {len(break_summary)} open breaks are past SLA and escalated "
      f"({len(escalated)/len(break_summary):.1%})")

# ===========================================================================
# 6. Counterparty break-rate ranking (chronic problem counterparties)
# ===========================================================================
print("\n" + "=" * 80)
print("COUNTERPARTY BREAK-RATE RANKING")
print("=" * 80)
cpty_total = merged.groupby("counterparty_fo").size()
cpty_breaks = break_summary.groupby("counterparty_fo").size()
cpty_rate = (cpty_breaks / cpty_total).fillna(0).sort_values(ascending=False)
cpty_report = pd.DataFrame({"total_trades": cpty_total, "breaks": cpty_breaks.reindex(cpty_total.index, fill_value=0),
                              "break_rate": cpty_rate.reindex(cpty_total.index, fill_value=0)}).sort_values("break_rate", ascending=False)
print(cpty_report.round(3).to_string())
print(f"\nChronic problem counterparty: {cpty_report.index[0]} "
      f"({cpty_report.iloc[0]['break_rate']:.1%} break rate, "
      f"vs. overall average {len(break_summary)/len(merged):.1%})")
