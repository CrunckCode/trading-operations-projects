"""
Module 8: Execution Algo Simulation (VWAP, TWAP, POV, DMA)
===============================================================
Simulates the same real parent order (a real rebalance-basket-sized trade in a real
top-10 holding) executed via 4 real algo strategies against REAL intraday 5-minute price
and volume data, comparing each strategy's resulting slippage vs. arrival price and
interval VWAP - the exact real "under trader supervision" execution-strategy decision.
"""
import numpy as np
import pandas as pd
import yfinance as yf
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from config import CHARTS_DIR

TICKER = "MSFT"           # real name, the largest rebalance trade found in Module 3
ORDER_SHARES = 1136        # real size from Module 3's MSFT sell trade
ORDER_SIDE = "SELL"

intraday = yf.download(TICKER, period="5d", interval="5m", progress=False, auto_adjust=True)
if isinstance(intraday.columns, pd.MultiIndex):
    intraday.columns = intraday.columns.get_level_values(0)
intraday = intraday.dropna()

# Use the most recent real full trading day
last_day = pd.Series(intraday.index.date).unique()[-1]
day_mask = pd.Series(intraday.index.date, index=intraday.index) == last_day
day_bars = intraday.loc[day_mask]
print(f"Real intraday data for {TICKER}, {last_day} ({len(day_bars)} real 5-min bars)")

prices = day_bars["Close"].values
volumes = day_bars["Volume"].values
n_bars = len(prices)
arrival_price = prices[0]
interval_vwap = np.average(prices, weights=volumes) if volumes.sum() > 0 else prices.mean()

sign = 1 if ORDER_SIDE == "BUY" else -1

def slippage(fill_price, benchmark):
    return sign * (fill_price - benchmark) / benchmark * 10000

# ===========================================================================
# Strategy 1: TWAP - equal shares in each real time bar
# ===========================================================================
twap_shares_per_bar = np.full(n_bars, ORDER_SHARES / n_bars)
twap_fill = np.average(prices, weights=twap_shares_per_bar)

# ===========================================================================
# Strategy 2: VWAP - shares proportional to real observed volume in each bar
# ===========================================================================
vwap_weights = volumes / volumes.sum() if volumes.sum() > 0 else np.full(n_bars, 1 / n_bars)
vwap_shares_per_bar = ORDER_SHARES * vwap_weights
vwap_fill = np.average(prices, weights=vwap_shares_per_bar)

# ===========================================================================
# Strategy 3: POV (Percentage of Volume) - participate at 10% of each bar's
# real volume, order completes once cumulative participation reaches order size
# ===========================================================================
POV_RATE = 0.10
pov_shares_per_bar = np.minimum(volumes * POV_RATE, ORDER_SHARES)
cum = np.cumsum(pov_shares_per_bar)
completion_idx = np.searchsorted(cum, ORDER_SHARES)
pov_bars_used = min(completion_idx + 1, n_bars)
pov_shares_actual = pov_shares_per_bar[:pov_bars_used].copy()
if cum[min(completion_idx, n_bars - 1)] > ORDER_SHARES:
    pov_shares_actual[-1] -= (cum[min(completion_idx, n_bars - 1)] - ORDER_SHARES)
pov_fill = np.average(prices[:pov_bars_used], weights=pov_shares_actual)
pov_completion_pct = pov_shares_actual.sum() / ORDER_SHARES

# ===========================================================================
# Strategy 4: DMA (Direct Market Access) - aggressive, front-loaded execution
# (most of the order in the first few real bars, mimicking an urgent DMA fill)
# ===========================================================================
dma_weights = np.exp(-np.arange(n_bars) / 3)  # exponentially front-loaded
dma_weights /= dma_weights.sum()
dma_shares_per_bar = ORDER_SHARES * dma_weights
dma_fill = np.average(prices, weights=dma_shares_per_bar)

results = pd.DataFrame([
    {"strategy": "TWAP", "fill_price": twap_fill,
     "arrival_slippage_bps": slippage(twap_fill, arrival_price),
     "vwap_slippage_bps": slippage(twap_fill, interval_vwap)},
    {"strategy": "VWAP", "fill_price": vwap_fill,
     "arrival_slippage_bps": slippage(vwap_fill, arrival_price),
     "vwap_slippage_bps": slippage(vwap_fill, interval_vwap)},
    {"strategy": f"POV ({POV_RATE:.0%})", "fill_price": pov_fill,
     "arrival_slippage_bps": slippage(pov_fill, arrival_price),
     "vwap_slippage_bps": slippage(pov_fill, interval_vwap)},
    {"strategy": "DMA (aggressive)", "fill_price": dma_fill,
     "arrival_slippage_bps": slippage(dma_fill, arrival_price),
     "vwap_slippage_bps": slippage(dma_fill, interval_vwap)},
])

print(f"\nOrder: {ORDER_SIDE} {ORDER_SHARES} shares {TICKER}, real arrival price "
      f"${arrival_price:.2f}, real interval VWAP ${interval_vwap:.2f}")
print(f"POV strategy completion: {pov_completion_pct:.1%} of order filled within the "
      f"real trading day at a 10% participation cap "
      f"({'full completion' if pov_completion_pct >= 0.999 else 'PARTIAL - real volume was insufficient to complete at this participation rate, a genuine execution-strategy constraint'})")
print("\n" + "=" * 80)
print("EXECUTION STRATEGY COMPARISON (real intraday data)")
print("=" * 80)
print(results.round(3).to_string(index=False))

best = results.loc[results["arrival_slippage_bps"].idxmax() if sign == 1 else results["arrival_slippage_bps"].idxmax()]
print(f"\nBest arrival-price performance: {best['strategy']} ({best['arrival_slippage_bps']:+.2f}bp)")

fig, ax = plt.subplots(figsize=(9, 5))
ax.bar(results["strategy"], results["arrival_slippage_bps"], color="steelblue")
ax.axhline(0, color="black", linewidth=0.5)
ax.set_ylabel("Arrival-price slippage (bps)")
ax.set_title(f"Execution Strategy Comparison - {ORDER_SIDE} {ORDER_SHARES} {TICKER} "
             f"(real intraday data, {last_day})")
plt.tight_layout()
plt.savefig(f"{CHARTS_DIR}/08_execution_algos.png", dpi=120)
print(f"\nSaved chart: {CHARTS_DIR}/08_execution_algos.png")
