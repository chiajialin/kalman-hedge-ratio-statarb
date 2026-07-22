"""
Kalman filter estimation of a time-varying hedge ratio for ES/NQ pairs trading.

State-space formulation:
    Transition  : beta_t = beta_{t-1} + w_t        w_t ~ N(0, Q)
    Observation : NQ_t   = beta_t * ES_t + alpha + v_t   v_t ~ N(0, R)

The filter tracks how the hedge ratio drifts over time, producing a daily
beta estimate that adapts to structural shifts in the ES/NQ relationship.
"""

import numpy as np
import pandas as pd


def kalman_hedge_ratio(
    nq_log: pd.Series,
    es_log: pd.Series,
    alpha: float,
    Q: float,
    R: float,
    initial_beta: float | None = None,
) -> pd.Series:
    """Estimate time-varying hedge ratio via Kalman filter predict-update loop.

    Args:
        nq_log: Log prices of NQ (observation).
        es_log: Log prices of ES (regressor / observation matrix).
        alpha:  Fixed intercept from OLS (held constant).
        Q:      Transition noise variance — controls how fast beta is allowed to drift.
        R:      Observation noise variance — set to variance of OLS residuals.
        initial_beta: Seed for beta[0]. Should be the fit_ols() beta for the same
            window; falls back to a crude log-price ratio if not given (previously
            the only behaviour, and mislabelled as "OLS beta" though it wasn't one --
            see CORRECTIONS.md). With P[0]=1.0 (high uncertainty) and the fit window's
            length of runway before the test period starts, the filter converges away
            from this seed regardless, so the fallback's practical effect is small --
            but passing the real OLS beta costs nothing and is simply more correct.

    Returns:
        pd.Series of daily beta estimates, same index as inputs.
    """
    n         = len(nq_log)
    beta      = np.zeros(n)   # filtered beta estimates
    P         = np.zeros(n)   # error covariance estimates

    # --- initialise at (ideally) OLS beta and high uncertainty ---
    beta[0] = initial_beta if initial_beta is not None else nq_log.iloc[0] / es_log.iloc[0]
    P[0]    = 1.0

    for t in range(1, n):
        x_t = es_log.iloc[t]    # regressor (ES log price)
        y_t = nq_log.iloc[t]    # observation (NQ log price)

        # --- predict ---
        beta_pred = beta[t - 1]
        P_pred    = P[t - 1] + Q

        # --- innovation: how wrong was the prediction ---
        y_hat  = beta_pred * x_t + alpha
        innov  = y_t - y_hat

        # --- innovation variance and Kalman gain ---
        S = P_pred * x_t ** 2 + R
        K = P_pred * x_t / S

        # --- update ---
        beta[t] = beta_pred + K * innov
        P[t]    = (1 - K * x_t) * P_pred

    return pd.Series(beta, index=nq_log.index, name="beta_kalman")


if __name__ == "__main__":
    import matplotlib.pyplot as plt
    import sys, os
    sys.path.insert(0, os.path.dirname(__file__))
    from cointegration import fit_ols

    es = pd.read_csv("data/raw/es_daily.csv", index_col="date", parse_dates=True)
    nq = pd.read_csv("data/raw/nq_daily.csv", index_col="date", parse_dates=True)
    es_log = np.log(es["close"])
    nq_log = np.log(nq["close"])

    fit   = fit_ols(nq_log, es_log)
    ALPHA = fit["alpha"]
    Q     = 1e-5                    # allow beta to drift slowly
    R     = fit["spread"].var()     # variance of the cointegrating regression's OLS
                                     # residuals (the spread itself) -- see CORRECTIONS.md
                                     # Fix D. Previously used the OU/AR(1) innovation
                                     # variance instead, which is a different, ~62x
                                     # smaller quantity.

    beta_kalman = kalman_hedge_ratio(nq_log, es_log, ALPHA, Q, R, initial_beta=fit["beta"])

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(beta_kalman.index, beta_kalman, color="steelblue", linewidth=1)
    ax.axhline(fit["beta"], color="crimson", linestyle="--", linewidth=1, label="Static OLS beta")
    ax.set_title("Kalman Filter — Time-Varying Hedge Ratio (beta_t)")
    ax.set_xlabel("Date")
    ax.set_ylabel("Beta")
    ax.legend()
    ax.grid(True, linestyle="--", alpha=0.4)
    plt.tight_layout()
    plt.show()
