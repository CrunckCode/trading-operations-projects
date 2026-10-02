"""
Module 3: Index Rebalance Basket Preparation
=================================================
Pulls the REAL current top-10 holdings and weights for the US Large-Cap mandate's real
underlying benchmark ETF (IVV, an S&P 500 tracker), simulates one quarter of real price
drift causing portfolio weights to deviate from the real target weights, and builds the
exact buy/sell basket (shares and dollar notional) the trader needs ahead of the close to
bring the scheme back to its real target weights - the actual "prepare rebalance baskets"
desk task.
"""
import numpy as np
import pandas as pd
import yfinance as yf
from config import MANDATES

SCHEME_KEY = "US_LargeCap"
scheme = MANDATES[SCHEME_KEY]
AUM = scheme["aum"]

# ===========================================================================
# 1. Real current top-10 holdings and weights (IVV, real S&P 500 tracker - using
# IVV rather than ^GSPC here since only a real fund vehicle exposes real holdings %)
# ===========================================================================
etf = yf.Ticker("IVV")
holdings = etf.funds_data.top_holdings
holdings = holdings.reset_index()
holdings.columns = ["ticker", "name", "target_weight"]
print(f"Real current top-10 holdings and weights (IVV, real S&P 500 tracker):")
print(holdings.round(4).to_string(index=False))

# ===========================================================================
# 2. Real 1-quarter (63 trading day) price history for each real holding, to
# simulate genuine price-driven weight drift
# ===========================================================================
tickers = holdings["ticker"].tolist()
prices = yf.download(tickers, period="6mo", progress=False, auto_adjust=True)["Close"].dropna()
quarter_start = prices.iloc[-63]
quarter_end = prices.iloc[-1]
real_qtr_return = (quarter_end / quarter_start - 1)
print(f"\nReal 1-quarter price returns per real holding "
      f"({prices.index[-63].date()} to {prices.index[-1].date()}):")
print(real_qtr_return.round(4).to_string())

# ===========================================================================
# 3. Simulate drifted weights: target dollar position grown by each name's real
# quarterly return, then renormalized to see how weights actually drifted
# ===========================================================================
holdings["target_dollar"] = holdings["target_weight"] * AUM
holdings["real_qtr_return"] = holdings["ticker"].map(real_qtr_return)
holdings["drifted_dollar"] = holdings["target_dollar"] * (1 + holdings["real_qtr_return"])
total_drifted = holdings["drifted_dollar"].sum()
# Other (non-top-10) holdings assumed to drift at the average of the top-10 return,
# a reasonable simplification for this illustrative basket
other_target_dollar = AUM - holdings["target_dollar"].sum()
other_drifted_dollar = other_target_dollar * (1 + real_qtr_return.mean())
total_scheme_value = total_drifted + other_drifted_dollar

holdings["drifted_weight"] = holdings["drifted_dollar"] / total_scheme_value
holdings["weight_drift_bps"] = (holdings["drifted_weight"] - holdings["target_weight"]) * 10000

# ===========================================================================
# 4. Build the rebalance trade basket: bring drifted weights back to real target
# weights, using the scheme's actual (drifted) total value as the new AUM base
# ===========================================================================
holdings["rebalanced_target_dollar"] = holdings["target_weight"] * total_scheme_value
holdings["trade_dollar"] = holdings["rebalanced_target_dollar"] - holdings["drifted_dollar"]
holdings["trade_side"] = np.where(holdings["trade_dollar"] > 0, "BUY", "SELL")
holdings["trade_shares"] = (holdings["trade_dollar"].abs() / quarter_end[holdings["ticker"]].values).round(0)

print("\n" + "=" * 90)
print(f"REBALANCE BASKET - {scheme['label']} (scheme value after real quarterly drift: "
      f"${total_scheme_value:,.0f})")
print("=" * 90)
print(holdings[["ticker", "target_weight", "drifted_weight", "weight_drift_bps",
                 "trade_side", "trade_dollar", "trade_shares"]].round(4).to_string(index=False))

total_turnover = holdings["trade_dollar"].abs().sum()
print(f"\nTotal basket turnover: ${total_turnover:,.0f} "
      f"({total_turnover/total_scheme_value:.2%} of scheme value)")
biggest_drift = holdings.loc[holdings["weight_drift_bps"].abs().idxmax()]
print(f"Largest weight drift: {biggest_drift['ticker']} at {biggest_drift['weight_drift_bps']:+.1f}bp "
      f"(real quarterly return {biggest_drift['real_qtr_return']:+.1%}) - the biggest single "
      f"rebalance trade in the basket")
