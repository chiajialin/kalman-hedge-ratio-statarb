"""
Engle-Granger cointegration test between ES and NQ log prices.

Step 2 of the Engle-Granger procedure: regress NQ log price on ES log price via OLS
and test the residual spread for stationarity. A stationary spread means the two
series share a stable long-run linear relationship -- i.e. they are cointegrated --
which is the precondition for treating the spread as a tradeable, mean-reverting
quantity.
"""

import statsmodels.api as sm
import pandas as pd
import numpy as np
from statsmodels.tsa.stattools import coint


def fit_ols(nq_log: pd.Series, es_log: pd.Series) -> dict:
    """Fit OLS hedge ratio of NQ log price on ES log price.

    Args:
        nq_log: Log prices of NQ (dependent variable).
        es_log: Log prices of ES (regressor).

    Returns:
        Dict with keys: beta, alpha, spread.
    """
    x = sm.add_constant(es_log)
    result = sm.OLS(nq_log, x).fit()
    alpha = result.params.iloc[0]
    beta  = result.params.iloc[1]
    spread = nq_log - beta * es_log - alpha
    return {"beta": beta, "alpha": alpha, "spread": spread}


def eg_cointegration(y_log: pd.Series, x_log: pd.Series) -> dict:
    """Engle-Granger cointegration test using proper MacKinnon critical values.

    Residuals from an estimated cointegrating regression are NOT a plain
    stationary series -- the regression already minimised residual variance,
    which makes plain ADF critical values (as in stationary.run_adf) too
    lenient and overstate significance. statsmodels.tsa.stattools.coint()
    runs the same regression internally and applies the correct, more
    conservative critical values for exactly this case.

    Args:
        y_log: Log prices of the dependent series.
        x_log: Log prices of the regressor series.

    Returns:
        Dict with keys: stat, p_value, crit_values.
    """
    stat, p_value, crit_values = coint(y_log, x_log)
    return {"stat": stat, "p_value": p_value, "crit_values": crit_values}


if __name__ == "__main__":
    nq = pd.read_csv("data/raw/nq_daily.csv", index_col="date", parse_dates=True)
    es = pd.read_csv("data/raw/es_daily.csv", index_col="date", parse_dates=True)
    nq_log = np.log(nq["close"])
    es_log = np.log(es["close"])

    fit = fit_ols(nq_log, es_log)
    eg = eg_cointegration(nq_log, es_log)

    print("--- Engle-Granger cointegration test (NQ log price on ES log price) ---")
    print(f"  EG statistic  : {eg['stat']:.4f}")
    print(f"  p-value       : {eg['p_value']:.4f}")
    print("  Critical values (1%, 5%, 10%):", eg["crit_values"])
    print(f"Beta (slope coefficient): {fit['beta']}")
    print(f"Alpha (intercept): {fit['alpha']}")


