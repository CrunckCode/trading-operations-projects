"""
Transaction Cost Analysis (TCA) and Execution Quality Dashboard
====================================================================
Uses REAL intraday minute-bar price data (yfinance, last available trading days) for
AAPL to simulate synthetic parent orders with realistic child fills, computes arrival-
price and interval-VWAP slippage, decomposes total slippage into timing cost vs. market
impact vs. spread cost, and ranks synthetic broker/algo performance - a quarterly
broker-review TCA discipline built into a reusable tool.
"""
import numpy as np
import pandas as pd
import yfinance as yf

np.random.seed(13)
TICKER = "AAPL"

# ===========================================================================
# 1. Real intraday minute-bar data (yfinance 1m data covers the last ~7 days)
# ===========================================================================
intraday = yf.download(TICKER, period="5d", interval="1m", progress=False, auto_adjust=True)
if isinstance(intraday.columns, pd.MultiIndex):
    intraday.columns = intraday.columns.get_level_values(0)
intraday = intraday.dropna()
print(f"Loaded {len(intraday)} real 1-minute bars for {TICKER}, "
      f"{intraday.index[0]} to {intraday.index[-1]}")

trading_days = pd.Series(intraday.index.date).unique()
print(f"Real trading days covered: {list(trading_days)}")

# ===========================================================================
# 2. Simulate synthetic parent orders against REAL intraday prices
# ===========================================================================
BROKERS = ["Broker_A_Algo", "Broker_B_Algo", "Broker_C_HighTouch", "Broker_D_Algo"]
N_ORDERS = 60
orders = []

for i in range(N_ORDERS):
    day = np.random.choice(trading_days)
    day_bars = intraday[pd.Series(intraday.index.date, index=intraday.index) == day]
    if len(day_bars) < 30:
        continue
    start_idx = np.random.randint(0, len(day_bars) - 20)
    duration = np.random.randint(5, 20)
    window = day_bars.iloc[start_idx:start_idx + duration]
    if len(window) == 0:
        continue
    side = np.random.choice(["BUY", "SELL"])
    broker = np.random.choice(BROKERS)
    arrival_price = float(window["Open"].iloc[0])
    interval_vwap = float((window["Close"] * window["Volume"]).sum() / window["Volume"].sum()) \
        if window["Volume"].sum() > 0 else float(window["Close"].mean())

    # Simulate realistic child fills: broker-specific execution quality on a 0-1 skill
    # scale where 0.5 = neutral (random fill timing, no systematic bias), skill > 0.5
    # biases fills toward favorable prices, skill < 0.5 biases toward UNFAVORABLE prices
    # (an earlier version only ever biased toward good prices at varying strength, which
    # made every broker look artificially favorable on average - fixed by making the low
    # end of the skill scale genuinely bias toward bad prices, not just "less good")
    broker_skill = {"Broker_A_Algo": 0.75, "Broker_B_Algo": 0.55, "Broker_C_HighTouch": 0.30,
                     "Broker_D_Algo": 0.60}[broker]
    price_path = window["Close"].values
    n = len(price_path)
    if side == "BUY":
        rank = np.argsort(price_path)  # rank[0] = index of lowest (best-for-buy) price
    else:
        rank = np.argsort(-price_path)  # rank[0] = index of highest (best-for-sell) price
    # bias_strength in [-1, 1]: positive skews weight toward good-price ranks, negative
    # skews toward bad-price ranks, magnitude controlled by distance from neutral 0.5
    bias_strength = (broker_skill - 0.5) * 2
    rank_position = np.empty(n)
    rank_position[rank] = np.arange(n)  # 0 = best price, n-1 = worst price
    linear_weights = 1 + bias_strength * (1 - 2 * rank_position / max(n - 1, 1))
    linear_weights = np.clip(linear_weights, 0.05, None)
    noise = np.random.dirichlet(np.ones(n)) * 0.4  # execution-timing randomness
    combined_weights = linear_weights / linear_weights.sum() * 0.6 + noise
    combined_weights /= combined_weights.sum()
    avg_fill_price = float(np.average(price_path, weights=combined_weights))

    shares = np.random.randint(5000, 50000)
    orders.append({
        "order_id": i, "date": day, "ticker": TICKER, "side": side, "broker": broker,
        "shares": shares, "arrival_price": arrival_price, "interval_vwap": interval_vwap,
        "avg_fill_price": avg_fill_price, "duration_min": duration,
    })

df = pd.DataFrame(orders)
sign = np.where(df["side"] == "BUY", 1, -1)
df["arrival_slippage_bps"] = sign * (df["avg_fill_price"] - df["arrival_price"]) / df["arrival_price"] * 10000
df["vwap_slippage_bps"] = sign * (df["avg_fill_price"] - df["interval_vwap"]) / df["interval_vwap"] * 10000

print(f"\nSimulated {len(df)} parent orders against real intraday {TICKER} prices")

# ===========================================================================
# 3. Slippage decomposition: timing cost vs. market impact vs. spread cost
#    (simplified real practitioner decomposition)
# ===========================================================================
# Timing cost: price drift from arrival to the order's mid-execution time (before the
# order itself could plausibly have moved the market) - approximated via the first-half
# vs. second-half price drift within the window
df["timing_cost_bps"] = sign * (df["interval_vwap"] - df["arrival_price"]) / df["arrival_price"] * 10000
df["market_impact_bps"] = df["arrival_slippage_bps"] - df["timing_cost_bps"]
SPREAD_COST_BPS = 1.5  # typical real large-cap effective half-spread proxy
df["spread_cost_bps"] = SPREAD_COST_BPS

print("\n" + "=" * 80)
print("SLIPPAGE DECOMPOSITION (average across all orders)")
print("=" * 80)
print(f"Average arrival-price slippage: {df['arrival_slippage_bps'].mean():+.2f} bps")
print(f"  - Timing cost component: {df['timing_cost_bps'].mean():+.2f} bps")
print(f"  - Market impact component: {df['market_impact_bps'].mean():+.2f} bps")
print(f"  - Spread cost (fixed proxy): {SPREAD_COST_BPS:+.2f} bps")
print(f"Average interval-VWAP slippage: {df['vwap_slippage_bps'].mean():+.2f} bps")

# ===========================================================================
# 4. Broker/algo performance ranking (quarterly broker review, same discipline
#    as a real broker-review TCA)
# ===========================================================================
print("\n" + "=" * 80)
print("BROKER/ALGO PERFORMANCE RANKING")
print("=" * 80)
broker_summary = df.groupby("broker").agg(
    n_orders=("order_id", "count"),
    avg_shares=("shares", "mean"),
    avg_arrival_slippage_bps=("arrival_slippage_bps", "mean"),
    avg_vwap_slippage_bps=("vwap_slippage_bps", "mean"),
    avg_market_impact_bps=("market_impact_bps", "mean"),
).sort_values("avg_arrival_slippage_bps")
print(broker_summary.round(2).to_string())

best_broker = broker_summary.index[0]
worst_broker = broker_summary.index[-1]
print(f"\nBest execution quality: {best_broker} "
      f"({broker_summary.loc[best_broker, 'avg_arrival_slippage_bps']:+.2f} bps avg slippage)")
print(f"Worst execution quality: {worst_broker} "
      f"({broker_summary.loc[worst_broker, 'avg_arrival_slippage_bps']:+.2f} bps avg slippage)")

# ===========================================================================
# 5. Dollar cost impact of the slippage gap
# ===========================================================================
avg_notional = (df["shares"] * df["arrival_price"]).mean()
slippage_gap_bps = broker_summary.loc[worst_broker, "avg_arrival_slippage_bps"] - \
                    broker_summary.loc[best_broker, "avg_arrival_slippage_bps"]
annual_volume_estimate = avg_notional * len(df) * 4  # rough quarterly-to-annual scale-up
dollar_cost_of_gap = annual_volume_estimate * slippage_gap_bps / 10000
print(f"\nAverage order notional: ${avg_notional:,.0f}")
print(f"Slippage gap between best and worst broker: {slippage_gap_bps:.2f} bps")
print(f"Estimated annualized dollar cost of routing all flow to the worst broker instead "
      f"of the best (illustrative, scaled from this sample): ${dollar_cost_of_gap:,.0f}")
