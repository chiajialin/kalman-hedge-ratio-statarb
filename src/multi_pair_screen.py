"""
Engle-Granger cointegration screen across all six ES/NQ/YM/RTY index-future pairs.

Loops fit_ols() (cointegration.py) + run_adf() (stationary.py) -- the same two-step
Engle-Granger procedure already validated on ES/NQ -- over every pair, using a
regression direction fixed in advance rather than picked after seeing results:
breadth order ES > RTY > NQ > YM, broader index always the regressor (X), narrower
one the dependent variable (Y). Engle-Granger's ADF-on-residual test is not symmetric
under swapping X and Y, so a direction chosen post-hoc could silently make a pair look
cointegrated (or not) by chance rather than by picking the direction blind.
"""

import pandas as pd
import numpy as np
from stationary import run_adf
from cointegration import fit_ols


if __name__ == "__main__":
    nq = pd.read_csv("data/raw/nq_daily.csv", index_col="date", parse_dates=True)
    es = pd.read_csv("data/raw/es_daily.csv", index_col="date", parse_dates=True)
    ym = pd.read_csv("data/raw/ym_daily.csv", index_col="date", parse_dates=True)
    rty = pd.read_csv("data/raw/rty_daily.csv", index_col="date", parse_dates=True)

    nq_log = np.log(nq["close"])
    es_log = np.log(es["close"])
    ym_log = np.log(ym["close"])
    rty_log = np.log(rty["close"])

    # (y_log, x_log, label) -- x is always the higher-priority ticker per ES > RTY > NQ > YM
    pairs = [
        (nq_log, es_log,  "ES / NQ"),
        (ym_log, es_log,  "ES / YM"),
        (rty_log, es_log, "ES / RTY"),
        (nq_log, rty_log, "RTY / NQ"),
        (ym_log, rty_log, "RTY / YM"),
        (ym_log, nq_log,  "NQ / YM"),
    ]
    for y_log, x_log, label in pairs:
        fit = fit_ols(y_log, x_log)
        print(f"\n--- {label} ---")
        print(f"Beta (slope coefficient): {fit['beta']}")
        print(f"Alpha (intercept): {fit['alpha']}")
        run_adf(fit["spread"], f"Spread ({label})")

