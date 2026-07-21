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
from stationary import run_adf


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


if __name__ == "__main__":
    nq = pd.read_csv("data/raw/nq_daily.csv", index_col="date", parse_dates=True)
    es = pd.read_csv("data/raw/es_daily.csv", index_col="date", parse_dates=True)
    nq_log = np.log(nq["close"])
    es_log = np.log(es["close"])

    fit = fit_ols(nq_log, es_log)

    run_adf(fit["spread"], "Spread (NQ log price - ES log price)")
    print(f"Beta (slope coefficient): {fit['beta']}")
    print(f"Alpha (intercept): {fit['alpha']}")


