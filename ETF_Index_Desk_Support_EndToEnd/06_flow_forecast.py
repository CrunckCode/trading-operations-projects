"""
Module 6: Subscription/Redemption Flow Forecasting
=======================================================
Real scheme-level daily subscription/redemption data isn't publicly available for any
fund (it's proprietary flow data even for real, large ETFs) - this module is
necessarily a calibrated simulation, clearly labeled as such, using realistic real-world
daily-flow-as-%-of-AUM parameters cited in ETF market-structure literature (daily net
flow typically 0.2-1.5% of AUM with day-to-day autocorrelation from redemption/
subscription clustering). Forecasts next-day flow via exponentially-weighted moving
average and sizes the cash buffer needed to keep cash drag under the real 0.5% desk KPI.
"""
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from config import MANDATES, CASH_DRAG_LIMIT, CHARTS_DIR

np.random.seed(42)
scheme = MANDATES["US_LargeCap"]
AUM = scheme["aum"]
N_DAYS = 252

# ===========================================================================
# 1. Simulate a realistic daily net flow series (AR(1) autocorrelated, mean-zero,
# calibrated to realistic real-world daily-flow-as-%-of-AUM magnitude)
# ===========================================================================
phi = 0.35            # AR(1) autocorrelation - flows cluster (a redemption day tends to
                       # be followed by another, consistent with real market behavior)
daily_vol = 0.012      # 1.2% of AUM daily flow volatility - realistic order of magnitude
flow_pct = np.zeros(N_DAYS)
for t in range(1, N_DAYS):
    flow_pct[t] = phi * flow_pct[t - 1] + np.random.normal(0, daily_vol * np.sqrt(1 - phi ** 2))
flow_dollar = flow_pct * AUM

# ===========================================================================
# 2. Forecast next-day flow via exponentially-weighted moving average (EWMA)
# ===========================================================================
flow_series = pd.Series(flow_pct)
ewma_forecast = flow_series.ewm(span=10).mean().shift(1)  # forecast made BEFORE seeing today's flow
forecast_error = flow_series - ewma_forecast
mae = forecast_error.abs().mean()
print(f"EWMA (span=10) 1-day-ahead flow forecast: Mean Absolute Error = {mae:.4%} of AUM")
print(f"Naive 'forecast = 0' baseline MAE: {flow_series.abs().mean():.4%} of AUM")
print(f"EWMA forecast improves on the naive baseline by "
      f"{(1 - mae/flow_series.abs().mean()):.1%}")

# ===========================================================================
# 3. Cash buffer sizing: what buffer keeps cash drag under 0.5% while covering
# a target percentile of single-day net redemptions without forced selling
# ===========================================================================
redemption_days = -flow_pct[flow_pct < 0]
for target_pct in [0.90, 0.95, 0.99]:
    buffer_needed = np.percentile(redemption_days, target_pct * 100)
    print(f"\nBuffer needed to cover {target_pct:.0%} of single-day redemption events "
          f"without forced selling: {buffer_needed:.3%} of AUM")

current_buffer = scheme["cash_buffer_target"]
opportunity_cost_annual = 0.02  # real, typical opportunity cost of holding cash vs. being invested (T-bill-ish yield foregone relative to equity return)
cash_drag_from_buffer = current_buffer * opportunity_cost_annual
print(f"\nCurrent scheme cash buffer target: {current_buffer:.2%} of AUM")
print(f"Implied annual cash drag from holding this buffer: {cash_drag_from_buffer:.3%} "
      f"(desk KPI limit: {CASH_DRAG_LIMIT:.2%}) - "
      f"{'WITHIN' if cash_drag_from_buffer <= CASH_DRAG_LIMIT else 'EXCEEDS'} the limit")

# Find the max buffer consistent with the 0.5% drag KPI
max_buffer_within_kpi = CASH_DRAG_LIMIT / opportunity_cost_annual
print(f"Maximum buffer consistent with the {CASH_DRAG_LIMIT:.1%} cash-drag KPI: "
      f"{max_buffer_within_kpi:.2%} of AUM")
coverage_at_max_buffer = (redemption_days <= max_buffer_within_kpi).mean()
print(f"At that maximum buffer, {coverage_at_max_buffer:.1%} of single-day redemption "
      f"events in this simulation would be covered without forced selling - the real "
      f"trade-off the desk manages daily between cash-drag cost and redemption coverage")

# ===========================================================================
# 4. Chart
# ===========================================================================
fig, axes = plt.subplots(2, 1, figsize=(11, 7))
axes[0].plot(flow_pct * 100, color="steelblue", linewidth=0.8)
axes[0].axhline(0, color="black", linewidth=0.5)
axes[0].set_title("Simulated Daily Net Flow (% of AUM) - calibrated to realistic ETF flow parameters")
axes[0].set_ylabel("Net flow (%)")

axes[1].hist(redemption_days * 100, bins=30, color="firebrick", edgecolor="black")
axes[1].axvline(max_buffer_within_kpi * 100, color="black", linestyle="--",
                 label=f"Max buffer within {CASH_DRAG_LIMIT:.1%} drag KPI")
axes[1].set_title("Distribution of Single-Day Redemption Magnitude (% of AUM)")
axes[1].legend(fontsize=8)
plt.tight_layout()
plt.savefig(f"{CHARTS_DIR}/06_flow_forecast.png", dpi=120)
print(f"\nSaved chart: {CHARTS_DIR}/06_flow_forecast.png")
