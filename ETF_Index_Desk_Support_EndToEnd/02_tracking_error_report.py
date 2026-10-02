"""
Module 2: Daily Tracking Error Report
=========================================
Simulates each scheme's daily NAV as the REAL benchmark return, minus three real drag
sources the desk actually manages day to day: cash drag (holding a cash buffer against
redemptions), fee accrual (the real expense ratio), and rebalance slippage (execution
cost incurred at quarterly index-reconstitution dates). Decomposes total tracking error
into these three sources for the trader/PM, exactly like the real daily report.
"""
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from config import MANDATES, DATA_DIR, CHARTS_DIR, REBALANCE_SLIPPAGE_BPS

os.makedirs(CHARTS_DIR, exist_ok=True)

def get_rebalance_dates(index_dates):
    """Real MSCI/S&P-style quarterly reconstitution convention: third Friday of
    March, June, September, December."""
    dates = pd.DatetimeIndex(index_dates)
    rebal = []
    for year in dates.year.unique():
        for month in [3, 6, 9, 12]:
            fridays = pd.date_range(f"{year}-{month}-01", f"{year}-{month}-28", freq="W-FRI")
            if len(fridays) >= 3:
                rebal.append(fridays[2])
    return pd.DatetimeIndex(rebal)

all_reports = {}
summary_rows = []

for key, m in MANDATES.items():
    df = pd.read_csv(os.path.join(DATA_DIR, f"{key}_benchmark.csv"), index_col=0, parse_dates=True)
    bench_ret = df["Close"].pct_change().dropna()

    daily_fee = m["expense_ratio_annual"] / 252
    cash_buffer = m["cash_buffer_target"]
    rebal_dates = get_rebalance_dates(bench_ret.index)

    scheme_ret = bench_ret * (1 - cash_buffer) - daily_fee
    rebal_hit = pd.Series(0.0, index=bench_ret.index)
    actual_rebal_dates = rebal_dates.intersection(bench_ret.index)
    rebal_hit.loc[actual_rebal_dates] = -REBALANCE_SLIPPAGE_BPS / 10000
    scheme_ret = scheme_ret + rebal_hit

    bench_cum = (1 + bench_ret).cumprod()
    scheme_cum = (1 + scheme_ret).cumprod()
    tracking_error_cum = scheme_cum - bench_cum

    cash_drag_cum = ((1 + bench_ret * (1 - cash_buffer)).cumprod() - bench_cum)
    fee_drag_cum = ((1 + bench_ret * (1 - cash_buffer) - daily_fee).cumprod() -
                     (1 + bench_ret * (1 - cash_buffer)).cumprod())
    rebal_drag_cum = tracking_error_cum - cash_drag_cum - fee_drag_cum

    annualized_te = scheme_ret.sub(bench_ret).std() * np.sqrt(252)

    report = pd.DataFrame({
        "benchmark_cum_return": bench_cum - 1, "scheme_cum_return": scheme_cum - 1,
        "tracking_error_cum": tracking_error_cum,
        "cash_drag_contribution": cash_drag_cum, "fee_drag_contribution": fee_drag_cum,
        "rebalance_slippage_contribution": rebal_drag_cum,
    })
    all_reports[key] = report

    final = report.iloc[-1]
    print(f"\n--- {m['label']} (real benchmark: {m['benchmark_name']}) ---")
    print(f"  Real benchmark cumulative return: {final['benchmark_cum_return']:.2%}")
    print(f"  Modeled scheme cumulative return: {final['scheme_cum_return']:.2%}")
    print(f"  Total tracking error (2Y cumulative): {final['tracking_error_cum']:.2%}")
    print(f"    - Cash drag contribution: {final['cash_drag_contribution']:.3%}")
    print(f"    - Fee accrual contribution: {final['fee_drag_contribution']:.3%}")
    print(f"    - Rebalance slippage contribution: {final['rebalance_slippage_contribution']:.3%} "
          f"({len(actual_rebal_dates)} real quarterly rebalance dates hit)")
    print(f"  Annualized tracking error (volatility of daily scheme-vs-benchmark return diff): "
          f"{annualized_te:.2%}")

    summary_rows.append({
        "Mandate": m["label"], "Benchmark": m["benchmark_name"], "AUM": m["aum"],
        "TotalTE_2Y": final["tracking_error_cum"], "CashDrag": final["cash_drag_contribution"],
        "FeeDrag": final["fee_drag_contribution"], "RebalSlippage": final["rebalance_slippage_contribution"],
        "AnnualizedTE": annualized_te,
    })

summary_df = pd.DataFrame(summary_rows)
summary_df.to_csv(os.path.join(DATA_DIR, "tracking_error_summary.csv"), index=False)
print("\n" + "=" * 90)
print("TRACKING ERROR SUMMARY - ALL 4 MANDATES")
print("=" * 90)
print(summary_df.round(4).to_string(index=False))

# Chart: tracking error decomposition for the largest mandate (US Large-Cap)
key = "US_LargeCap"
report = all_reports[key]
fig, ax = plt.subplots(figsize=(11, 6))
ax.plot(report.index, report["tracking_error_cum"] * 100, label="Total tracking error", color="black", linewidth=1.5)
ax.plot(report.index, report["cash_drag_contribution"] * 100, label="Cash drag", color="steelblue")
ax.plot(report.index, report["fee_drag_contribution"] * 100, label="Fee accrual", color="firebrick")
ax.plot(report.index, report["rebalance_slippage_contribution"] * 100, label="Rebalance slippage", color="darkorange")
ax.set_ylabel("Cumulative drag (%)")
ax.set_title(f"Tracking Error Decomposition - {MANDATES[key]['label']} "
             f"(real {MANDATES[key]['benchmark_name']} benchmark)")
ax.legend(fontsize=8)
plt.tight_layout()
plt.savefig(os.path.join(CHARTS_DIR, "02_tracking_error_decomposition.png"), dpi=120)
print(f"\nSaved chart: {CHARTS_DIR}/02_tracking_error_decomposition.png")
