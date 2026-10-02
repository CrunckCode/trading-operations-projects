"""
Shared configuration for the ETF / Index Fund Desk Support end-to-end project.
All user-facing inputs live here, at the top, per project convention - every module
imports from this file instead of hardcoding these values inline.
"""

# ===========================================================================
# The 4 mandates ($120mn total, illustrative)
# Each mandate is a scheme that tracks a real benchmark (proxied by a real,
# liquid ETF whose real price history stands in for the real benchmark index level -
# individual Indian-AMC scheme-level NAV data isn't available via any free API, so the
# scheme itself is a modeled overlay on top of the REAL benchmark's REAL returns).
# ===========================================================================
MANDATES = {
    "US_LargeCap": {
        "label": "US Large-Cap Index Scheme",
        "benchmark_ticker": "^GSPC",          # real S&P 500 index level
        "benchmark_name": "S&P 500",
        "aum": 35_000_000,
        "expense_ratio_annual": 0.0003,        # real, typical large passive S&P 500 fund fee
        "cash_buffer_target": 0.003,           # 0.3% cash buffer for redemptions
    },
    "DM_exUS": {
        "label": "Developed Markets ex-US Index Scheme",
        "benchmark_ticker": "EFA",             # real iShares MSCI EAFE ETF (developed ex-US proxy)
        "benchmark_name": "MSCI EAFE",
        "aum": 30_000_000,
        "expense_ratio_annual": 0.0032,        # real, approximate EFA-style net expense ratio
        "cash_buffer_target": 0.004,
    },
    "EM": {
        "label": "Emerging Markets Index Scheme",
        "benchmark_ticker": "VWO",             # real Vanguard FTSE Emerging Markets ETF proxy
        "benchmark_name": "MSCI Emerging Markets",
        "aum": 25_000_000,
        "expense_ratio_annual": 0.0008,        # real, approximate VWO-style net expense ratio
        "cash_buffer_target": 0.005,
    },
    "Global_ACWI": {
        "label": "Global Broad Market Index Scheme",
        "benchmark_ticker": "ACWI",            # real iShares MSCI ACWI ETF (global broad benchmark)
        "benchmark_name": "MSCI ACWI",
        "aum": 30_000_000,
        "expense_ratio_annual": 0.0032,        # real, approximate ACWI-style net expense ratio
        "cash_buffer_target": 0.004,
    },
}
TOTAL_AUM = sum(m["aum"] for m in MANDATES.values())  # $120,000,000

# ===========================================================================
# Shared date ranges / thresholds
# ===========================================================================
HISTORY_START = "2023-01-01"
HISTORY_END = "2025-01-01"
INAV_BREACH_THRESHOLD_BPS = 35
CASH_DRAG_LIMIT = 0.005          # 0.5% of assets, the real desk KPI
REBALANCE_SLIPPAGE_BPS = 4       # real, typical index-fund rebalance execution cost estimate
TCA_TARGET_PARENT_ORDERS = 900
BROKER_PANEL_SIZE = 12
CORPORATE_ACTIONS_TARGET = 200   # per year, matching the real bullet

DATA_DIR = "data"
CHARTS_DIR = "charts"
