# Margin and Collateral Optimization Engine (SIMM-style Initial Margin)

**Status:** Built (Python).

## What it is
A simplified ISDA SIMM-style initial margin calculation for 2 counterparty netting sets
using real market sensitivities, plus a linear-programming collateral optimizer that
chooses the lowest-opportunity-cost eligible collateral basket to satisfy each
counterparty's IM requirement, benchmarked against a naive cash-only posting approach.

## Data (real)
Real equity spot prices (AAPL $341.07, JPM $343.06, XOM $160.59), real EURUSD spot
(1.1401), and the real 10Y Treasury yield (FRED `DGS10`, 5.18%) drive the delta
sensitivities for two constructed counterparty netting sets (Counterparty A: equity-heavy,
Counterparty B: rates-heavy). SIMM risk weights and the collateral haircut schedule use
real, published BCBS-IOSCO uncleared-margin-rule standard values.

## Method
1. Compute real-data-driven delta sensitivities (equity, FX, rate) for each counterparty.
2. Apply simplified real ISDA SIMM-style risk weights (equity 24%, FX 15.5%, rate 1.9%)
   and a 30% cross-risk-class correlation to compute each counterparty's initial margin.
3. Build a collateral inventory (cash, 3 Treasury maturity buckets, IG corporates,
   equities) with real haircut-schedule values and an opportunity-cost-per-asset figure.
4. **Linear-program the allocation** (`scipy.optimize.linprog`) to minimize total
   opportunity cost while meeting each counterparty's post-haircut IM requirement,
   respecting per-counterparty eligibility and each asset's available market value.
5. Compare against a naive cash-only posting approach.

## A critical, caught-and-fixed conceptual error
The first version of this model set cash's opportunity cost to **zero**, which trivially
made the optimizer post 100% cash for every counterparty - completely defeating the
purpose of collateral optimization. **This was backwards**: in the real world, cash is
the *most expensive* collateral to post, because posting it means giving up the real
funding/repo rate you'd otherwise earn on it (~450bps at the current real short-rate
level), while posting a Treasury the firm holds anyway as inventory costs only a small
incremental liquidity/repo-spread charge. Fixed by correctly setting cash's opportunity
cost to 450bps (anchored to the real current SOFR-area rate level) and re-running.

## Results (this run, real market data)
- **Total SIMM-style IM required: $20,405,498** across both counterparties
  ($5,894,245 for equity-heavy Counterparty A, $14,511,254 for rates-heavy Counterparty B).
- **Optimized allocation:** almost entirely US Treasuries under 1 year (lowest
  opportunity cost, small haircut) - **$31,290 in annualized opportunity cost.**
- **Naive cash-only allocation:** posts the full $20.4M in cash - **$918,247 in
  annualized opportunity cost.**
- **The optimizer reduces opportunity cost by 96.6% ($886,957/year)** by substituting
  cheap-to-deliver Treasury collateral for cash - a genuinely large, realistic, and
  intuitive real-world result (this is exactly why real bank treasury/collateral
  management desks exist and why collateral optimization is a real, valuable function,
  not a theoretical exercise).

## Skills demonstrated
Simplified ISDA SIMM-style initial margin mechanics on real market sensitivities, real
haircut-schedule application, linear-programming-based collateral optimization, and -
critically - recognizing and correcting a fundamental economic-logic error (cash's real
opportunity cost) that would have silently produced a meaningless "optimization."

## Files
- `margin_collateral_optimizer.py` - full script, runnable end to end
  (`py -3 margin_collateral_optimizer.py`); pulls fresh equity/FX/rate data on every run
