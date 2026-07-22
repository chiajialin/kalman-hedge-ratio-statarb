"""
Fit an Ornstein-Uhlenbeck (OU) process to the OLS spread and extract
mean-reversion parameters to inform backtest signal design.

The OU process in continuous time:
    dX_t = theta * (mu - X_t) dt + sigma * dW_t

where:
    theta  — speed of mean reversion (higher = faster snap-back)
    mu     — long-run equilibrium level the spread reverts to
    sigma  — volatility of the spread

In discrete time (daily), this becomes an AR(1) regression:
    X_{t+dt} = c + phi * X_t + epsilon_t

from which OU parameters are recovered as:
    theta = -log(phi)        (reversion speed per day)
    mu    = c / (1 - phi)    (long-run mean)
    sigma = std(epsilon)     (spread volatility)
"""

import statsmodels.api as sm
import numpy as np
import pandas as pd


def estimate_ou(spread: pd.Series) -> dict:
    """Estimate OU parameters from a spread series via OLS AR(1) regression.

    Args:
        spread: Stationary spread time series (e.g. OLS residuals).

    Returns:
        Dict with keys: theta, mu, sigma.
    """
    X_t   = spread[1:].values   # current values
    X_lag = spread[:-1].values  # lagged values,
    result = sm.OLS(X_t, sm.add_constant(X_lag)).fit()
    c = result.params[0]  # intercept
    phi = result.params[1]  # slope
    if phi >= 1:
        raise ValueError(
            f"AR(1) coefficient phi={phi:.4f} >= 1: no mean reversion detected in "
            "this window, so OU parameters (and a half-life) are undefined. Treat "
            "the fold as untradeable rather than forcing a window through -log(phi)."
        )
    theta = -np.log(phi)
    mu = c / (1 - phi)
    sigma = np.std(result.resid)
    return {"theta": theta, "mu": mu, "sigma": sigma}



def half_life(theta: float) -> int:
    """Convert OU theta to half-life in days, rounded to nearest integer.

    Half-life is the expected time for the spread to revert halfway to mu.
    Formula: half_life = log(2) / theta

    Args:
        theta: Mean-reversion speed from estimate_ou.

    Returns:
        Half-life in trading days (integer), used as rolling window length.
    """
    return int(round(np.log(2) / theta))


if __name__ == "__main__":
    es = pd.read_csv("data/raw/es_daily.csv", index_col="date", parse_dates=True)
    nq = pd.read_csv("data/raw/nq_daily.csv", index_col="date", parse_dates=True)

    BETA  = 1.2383755893144004
    ALPHA = -0.7949431887427696
    spread = np.log(nq["close"]) - BETA * np.log(es["close"]) - ALPHA

    params = estimate_ou(spread)
    hl     = half_life(params["theta"])

    print(f"theta  (reversion speed) : {params['theta']:.4f}")
    print(f"mu     (long-run mean)   : {params['mu']:.6f}")
    print(f"sigma  (spread vol)      : {params['sigma']:.6f}")
    print(f"half-life                : {hl} days")
