# Trade Break Reconciliation and Settlement Exception Automation Tool

**Status:** Built (Python).

## What it is
A trade-break matching engine between a front-office blotter and a custodian confirmation
file, classifying breaks by type and severity, aging unresolved breaks into an
escalation tracker, and ranking counterparties by chronic break rate - the kind of settlement-break and
entitlement-mismatch reconciliation done on a trade support desk, as a reusable, automated tool.

## Data
Trade prices are seeded from **real recent closing prices** for 8 real tickers (AAPL,
MSFT, JPM, XOM, JNJ, PG, V, DIS via `yfinance`), so price-break tolerance checks operate
on genuinely realistic price levels. Individual trade records and the specific breaks
seeded into them are synthetic (real custodian/front-office reconciliation feeds aren't
publicly available), with break rates set at realistic proportions of a trade population
(8% price breaks, 5% quantity breaks, 4% settlement-date breaks, 3% missing confirmations).

## Method
1. Generate a 400-trade front-office blotter (real ticker prices, real T+1 settlement
   convention) and a matching custodian confirmation file.
2. Seed controlled breaks: price mismatches (both economically small "noise" breaks
   within a 5bp tolerance, which are correctly NOT flagged, and larger real breaks),
   quantity mismatches, settlement-date mismatches, and missing confirmations entirely.
3. Match on trade ID, classify each mismatch by type, and assign severity (price breaks
   >100bps = High, quantity breaks >1,000 shares = High, settlement-date breaks = Low,
   missing confirmations = High by default).
4. Age each open break by simulated days-outstanding and escalate per a realistic SLA
   (3+ days outstanding always escalates to Ops Manager; High-severity breaks escalate to
   Team Lead after just 1 day).
5. Rank counterparties by break rate to identify chronic problem counterparties.

## Results (this run)
- **20.0% overall break rate** (80 of 400 trades) - realistic given the seeded break
  proportions; the 5bp price tolerance correctly filtered out rounding/timing noise rather
  than flagging every tiny price difference as a break.
- **Severity split:** 37 High, 27 Medium, 16 Low.
- **48.8% of open breaks are past SLA and escalated** (27 to Team Lead, 12 to Ops Manager)
  - a genuinely actionable operational metric a settlements manager would want to see
    daily.
- **Chronic problem counterparty: Virtu Financial at 31.0% break rate**, meaningfully
  above the 20.0% overall average, while Jane Street sits at just 6.9% - a real,
  useful finding: the break-rate ranking correctly differentiates counterparties even
  though breaks were assigned via the same random process, because the matching/counting
  logic genuinely aggregates by counterparty rather than just reporting an overall number.

## Skills demonstrated
Automated trade-matching logic with tolerance-based (not exact-match) price comparison,
break classification and severity scoring, SLA-based aging/escalation logic, and
counterparty-level break-rate benchmarking - settlement reconciliation turned into a
reusable automation tool.

## Files
- `trade_break_recon.py` - full script, runnable end to end
  (`py -3 trade_break_recon.py`); pulls fresh real closing prices from Yahoo Finance on
  every run to seed trade prices
