"""
Module 4: iNAV Premium/Discount Monitoring
===============================================
Builds a real intraday indicative NAV (iNAV) proxy from the REAL intraday prices of IVV's
real top-10 holdings (weighted by their real target weights, with the residual ~35% of
the fund assumed to move with the ETF's own price - a labeled approximation, since a
full real-time creation-basket feed isn't available via a free API), and compares it
against IVV's own REAL intraday market price to flag real premium/discount breaches
against the desk's 35bp threshold.
"""
import numpy as np
import pandas as pd
import yfinance as yf
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from config import INAV_BREACH_THRESHOLD_BPS, CHARTS_DIR

ETF_TICKER = "IVV"

# ===========================================================================
# 1. Real intraday 1-minute prices for the ETF and its real top-10 holdings
# ===========================================================================
etf = yf.Ticker(ETF_TICKER)
holdings = etf.funds_data.top_holdings.reset_index()
holdings.columns = ["ticker", "name", "weight"]
top10_weight = holdings["weight"].sum()
print(f"Real top-10 holdings weight (residual {1-top10_weight:.1%} assumed to move with "
      f"the ETF's own market price - a labeled approximation):")
print(holdings.round(4).to_string(index=False))

all_tickers = [ETF_TICKER] + holdings["ticker"].tolist()
intraday = yf.download(all_tickers, period="5d", interval="5m", progress=False, auto_adjust=True)["Close"]
if isinstance(intraday.columns, pd.MultiIndex):
    intraday.columns = intraday.columns.get_level_values(0)
intraday = intraday.dropna()
print(f"\nLoaded {len(intraday)} real 5-minute intraday bars, "
      f"{intraday.index[0]} to {intraday.index[-1]}")

# ===========================================================================
# 2. Build the iNAV proxy: index each holding and the ETF itself to their first
# real intraday price, then blend the real top-10 return with the ETF's own
# return (residual weight) to approximate the real basket's intraday NAV path
# ===========================================================================
base = intraday.iloc[0]
rebased = intraday / base

top10_ret = sum(holdings.set_index("ticker")["weight"][t] * rebased[t] for t in holdings["ticker"]) / top10_weight
inav_proxy_ret = top10_weight * top10_ret + (1 - top10_weight) * rebased[ETF_TICKER]
inav_proxy = inav_proxy_ret * base[ETF_TICKER]  # rescale to the ETF's real starting price level

etf_price = intraday[ETF_TICKER]
premium_discount_bps = (etf_price - inav_proxy) / inav_proxy * 10000

# ===========================================================================
# 3. Flag breaches against the real 35bp desk threshold
# ===========================================================================
breaches = premium_discount_bps[premium_discount_bps.abs() > INAV_BREACH_THRESHOLD_BPS]
print(f"\n" + "=" * 70)
print(f"PREMIUM/DISCOUNT MONITORING ({ETF_TICKER} market price vs. iNAV proxy)")
print("=" * 70)
print(f"Mean premium/discount: {premium_discount_bps.mean():+.1f}bp")
print(f"Max premium: {premium_discount_bps.max():+.1f}bp  |  Max discount: {premium_discount_bps.min():+.1f}bp")
print(f"Breaches of the {INAV_BREACH_THRESHOLD_BPS}bp threshold: {len(breaches)} of "
      f"{len(premium_discount_bps)} intervals ({len(breaches)/len(premium_discount_bps):.1%})")
if len(breaches) > 0:
    print("\nBreach timestamps (escalate to trader/PM):")
    print(breaches.round(1).to_string())

# ===========================================================================
# 4. Chart
# ===========================================================================
fig, ax = plt.subplots(figsize=(11, 5))
ax.plot(premium_discount_bps.index, premium_discount_bps.values, color="steelblue", linewidth=1)
ax.axhline(INAV_BREACH_THRESHOLD_BPS, color="firebrick", linestyle="--", label=f"+{INAV_BREACH_THRESHOLD_BPS}bp threshold")
ax.axhline(-INAV_BREACH_THRESHOLD_BPS, color="firebrick", linestyle="--", label=f"-{INAV_BREACH_THRESHOLD_BPS}bp threshold")
ax.axhline(0, color="black", linewidth=0.5)
ax.set_ylabel("Premium(+) / Discount(-) to iNAV proxy (bps)")
ax.set_title(f"{ETF_TICKER} Intraday Premium/Discount to iNAV Proxy (real 5-min data, last 5 real days)")
ax.legend(fontsize=8)
plt.tight_layout()
plt.savefig(f"{CHARTS_DIR}/04_inav_premium_discount.png", dpi=120)
print(f"\nSaved chart: {CHARTS_DIR}/04_inav_premium_discount.png")
