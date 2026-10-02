"""
Module 1: Pull real benchmark price history for all 4 mandates and cache to data/.
Every other module reads from these cached CSVs instead of re-hitting Yahoo Finance,
so the whole project runs consistently off one snapshot of real market data.
"""
import os
import pandas as pd
import yfinance as yf
from config import MANDATES, HISTORY_START, HISTORY_END, DATA_DIR

os.makedirs(DATA_DIR, exist_ok=True)

for key, m in MANDATES.items():
    ticker = m["benchmark_ticker"]
    print(f"Pulling real daily price history for {m['label']} (benchmark: {m['benchmark_name']}, "
          f"ticker {ticker})...")
    df = yf.download(ticker, start=HISTORY_START, end=HISTORY_END, progress=False,
                      auto_adjust=True)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df[["Open", "High", "Low", "Close", "Volume"]].dropna()
    out_path = os.path.join(DATA_DIR, f"{key}_benchmark.csv")
    df.to_csv(out_path)
    print(f"  Saved {len(df)} real trading days to {out_path} "
          f"({df.index[0].date()} to {df.index[-1].date()})")

print("\nModule 1 complete: real benchmark data cached for all 4 mandates.")
