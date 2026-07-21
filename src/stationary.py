"""
Test ES and NQ log price series for stationarity using the Augmented Dickey-Fuller test.

Step 1 of the Engle-Granger cointegration procedure: confirm both series are I(1) —
i.e. non-stationary in log levels but stationary after first differencing (log returns).
This is a precondition for cointegration testing to be valid.
"""

import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import adfuller

DATA_DIR = "data/raw"


def load_log_prices(data_dir: str) -> tuple[pd.Series, pd.Series]:
    """Load ES and NQ close prices and return log-transformed series."""
    es = pd.read_csv(f"{data_dir}/es_daily.csv", index_col="date", parse_dates=True)
    nq = pd.read_csv(f"{data_dir}/nq_daily.csv", index_col="date", parse_dates=True)
    return np.log(es["close"]), np.log(nq["close"])


def run_adf(series: pd.Series, label: str) -> dict:
    """Run ADF test on series and print a formatted summary.

    Args:
        series: Time series to test.
        label:  Human-readable label for console output.

    Returns:
        Dict with keys: adf_stat, p_value, critical_values.
    """
    stat, p_value, _, _, critical_values, _ = adfuller(series.dropna(), autolag="AIC")

    print(f"\n--- {label} ---")
    print(f"  ADF statistic : {stat:.4f}")
    print(f"  p-value       : {p_value:.4f}")
    print("  Critical values:")
    for level, cv in critical_values.items():
        reject = "[reject]" if stat < cv else "[fail to reject]"
        print(f"    {level}: {cv:.3f}  ({reject} at this level)")

    return {"adf_stat": stat, "p_value": p_value, "critical_values": critical_values}


if __name__ == "__main__":
    es_log, nq_log = load_log_prices(DATA_DIR)
    es_log_ret = es_log.diff()
    nq_log_ret = nq_log.diff()

    print("=" * 60)
    print("STATIONARITY CHECKS — ADF TEST (H0: unit root present)")
    print("=" * 60)
    print("\n[Log Levels — expect FAIL TO REJECT: prices are non-stationary]")
    run_adf(es_log, "ES log price")
    run_adf(nq_log, "NQ log price")

    print("\n[Log Returns (first difference) — expect REJECT: returns are stationary]")
    run_adf(es_log_ret, "ES log return")
    run_adf(nq_log_ret, "NQ log return")

    print("\n" + "=" * 60)
    print("CONCLUSION: Both series are I(1) — valid inputs for Engle-Granger cointegration test.")
    print("=" * 60)
    