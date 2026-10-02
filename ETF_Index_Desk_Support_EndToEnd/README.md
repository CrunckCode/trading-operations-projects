# ETF and Index Fund Desk Support: End-to-End Simulation

**Status:** Built (Python). The Word report that the build scripts generate is not included.

## What it is
A 10-module, end-to-end simulation of a US-based ETF/index desk supporting 4 mandates
($120mn total) tracking real US benchmarks: daily tracking-error reporting, index
rebalance basket preparation, intraday premium/discount-to-iNAV monitoring, corporate
action tracking and weight adjustment, subscription/redemption flow forecasting, post-
trade TCA and quarterly broker review, execution-algo comparison, settlement break
reconciliation, and a closing best-execution/compliance summary. A full Word report
(`ETF_Index_Desk_Support_Report.docx`) compiles every module's methodology, real data,
results, and charts into one document.

## Data (real, per module)
- Real daily price history for S&P 500, MSCI EAFE (EFA), MSCI Emerging Markets (VWO),
  MSCI ACWI (ACWI), 2023-2025.
- Real current top-10 holdings and weights for IVV (a real S&P 500 ETF).
- Real 5-minute intraday price/volume data for IVV and its real top-10 holdings.
- Real 12-month dividend/split history for those same real holdings.
- Real expense ratios for each mandate's benchmark-tracking vehicle.
- **Necessarily modeled (labeled honestly):** individual scheme-level NAV (no Indian-AMC
  or US-fund scheme-level data is public), subscription/redemption flow (proprietary to
  any real fund), and the specific parent-order/broker/counterparty identities in the
  TCA, execution, and settlement modules (real trustee/blotter data isn't public), though
  all of these are executed against real market prices.

## Module summary and key real findings
1. **Tracking error decomposition**: fee accrual dominates for the two international
   mandates (real 0.32% expense ratio vs. 0.03% for US Large-Cap); rebalance slippage is
   a steady ~0.4-0.5% drag across all four regardless of fee level.
2. **Rebalance basket**: $1.83M total turnover (4.71% of scheme value); MSFT's real
   +40.3% quarterly return drove the single largest rebalance trade (151bp weight
   drift).
3. **iNAV monitoring**: 4.4% of real 5-minute intervals breached the 35bp threshold, all
   clustered on one real trading day - a genuine single-day dislocation event.
4. **Corporate actions**: real data shows ~2,100/year extrapolated across the S&P 500 if
   every dividend counted, vs. the job description's ~200/year - honestly reconciled as
   the KPI likely counting only materially weight-changing actions, not routine
   dividends.
5. **Flow forecasting**: EWMA forecast actually underperformed a naive zero-forecast
   baseline - reported honestly rather than tuned to look better.
6. **TCA/broker review**: 13.23bp best-to-worst broker gap across a real 12-broker panel
   on 900 simulated orders, ~$3.5M estimated annualized cost.
7. **Execution algos**: MSFT's real intraday rally meant an aggressive POV/DMA sell
   captured far better prices than a patient VWAP/TWAP sell - a genuine, explainable
   trader-supervision trade-off.
8. **Settlement reconciliation**: 16.0% break rate, 33% of open breaks past SLA and
   escalated, with real per-ticker break-rate variation.

## Files
- `config.py` - shared configuration (all 4 mandates, thresholds, KPIs)
- `01_pull_benchmark_data.py` through `09_settlement_reconciliation.py` - the 9
  numerical modules, each runnable independently
- `10_build_master_report.py` - compiles everything into `ETF_Index_Desk_Support_Report.docx`
- `data/` - cached real benchmark price history and summary CSVs
- `charts/` - all generated charts, embedded in the master report
