"""
Stage 1: Static OLS baseline strategy.

Constructs a spread using fixed OLS hedge ratio, fits an OU model to estimate
mean-reversion speed, then z-scores the spread, generates signals, and computes
P&L and performance metrics.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from ou_model import estimate_ou, half_life
from kalman_filter import kalman_hedge_ratio

# --- OLS coefficients from cointegration.py ---
BETA  = 1.2383755893144004   # slope on log(ES) — the hedge ratio
ALPHA = -0.7949431887427696  # intercept (const)

ENTRY_THRESHOLD = 2.0  # z-score level to open a trade
EXIT_THRESHOLD  = 0.0  # z-score level to close a trade
COST_BPS        = 1.0  # one-way transaction cost in basis points


def build_spread(nq_log: pd.Series, es_log: pd.Series, beta: float, alpha: float) -> pd.Series:
    return nq_log - beta * es_log - alpha


def zscore(spread: pd.Series, window: int) -> pd.Series:
    rolling_mean = spread.rolling(window=window).mean()
    rolling_std = spread.rolling(window=window).std()
    return (spread - rolling_mean) / rolling_std


def generate_signals(z: pd.Series, entry: float, exit_threshold: float) -> pd.Series:
    position = pd.Series(0.0, index=z.index)
    current  = 0.0

    for i, z_val in enumerate(z):
        if pd.isna(z_val):
            continue

        if current == 0:
            if z_val < -entry:
                current = 1.0
            elif z_val > entry:
                current = -1.0
        elif current == 1.0:
            if z_val >= exit_threshold:
                current = 0.0
        elif current == -1.0:
            if z_val <= -exit_threshold:
                current = 0.0

        position.iloc[i] = current

    return position.shift(1).fillna(0.0)


def compute_returns(position: pd.Series, nq_log: pd.Series, es_log: pd.Series,
                    beta: float, cost_bps: float) -> pd.Series:
    # beta_t is estimated using the price observed at t, so scaling the return over
    # [t-1, t] with beta_t would use information not available until the end of that
    # same period. Lag it one day -- yesterday's belief hedges today's return, not
    # today's freshly-updated one. (Static OLS passes a single float, not a Series,
    # so there's nothing to lag in that case.)
    beta_lag = beta.shift(1) if isinstance(beta, pd.Series) else beta
    daily_spread_return   = nq_log.diff() - beta_lag * es_log.diff()
    daily_strategy_return = position * daily_spread_return
    trade_days            = (position.diff().abs() > 0).astype(float)
    daily_strategy_return -= (cost_bps / 10000) * trade_days
    return daily_strategy_return.fillna(0.0)
    


def compute_metrics(returns: pd.Series, position: pd.Series) -> dict:
    annual_sharpe     = returns.mean() / returns.std() * np.sqrt(252)
    cumulative_equity = (1 + returns).cumprod()
    max_drawdown      = (cumulative_equity / cumulative_equity.cummax() - 1).min()
    hit_rate          = (returns[returns != 0] > 0).mean()
    turnover          = position.diff().abs().sum() / (len(position) / 252)

    print(f"Annualised Sharpe : {annual_sharpe:.4f}")
    print(f"Max Drawdown      : {max_drawdown:.4f}")
    print(f"Hit Rate          : {hit_rate:.4f}")
    print(f"Annual Turnover   : {turnover:.1f} round trips")

    return {
        "annual_sharpe": annual_sharpe,
        "max_drawdown":  max_drawdown,
        "hit_rate":      hit_rate,
        "turnover":      turnover,
    }


if __name__ == "__main__":
    # --- load data ---
    es = pd.read_csv("data/raw/es_daily.csv", index_col="date", parse_dates=True)
    nq = pd.read_csv("data/raw/nq_daily.csv", index_col="date", parse_dates=True)
    es_log = np.log(es["close"])
    nq_log = np.log(nq["close"])

    # --- fit OU model to derive rolling window from half-life ---
    spread    = build_spread(nq_log, es_log, BETA, ALPHA)
    ou_params = estimate_ou(spread)
    window    = half_life(ou_params["theta"])
    print(f"OU half-life: {window} days  (theta={ou_params['theta']:.4f})")

    # --- static OLS pipeline ---
    print("\n=== Static OLS ===")
    z_ols        = zscore(spread, window)
    pos_ols      = generate_signals(z_ols, ENTRY_THRESHOLD, EXIT_THRESHOLD)
    ret_ols      = compute_returns(pos_ols, nq_log, es_log, BETA, COST_BPS)
    metrics_ols  = compute_metrics(ret_ols, pos_ols)

    # --- Kalman filter pipeline ---
    Q = 1e-5  # allow beta to drift slowly
    R = (0.005780) ** 2
    beta_kalman   = kalman_hedge_ratio(nq_log, es_log, ALPHA, Q, R)
    spread_kalman = build_spread(nq_log, es_log, beta_kalman, ALPHA)
    z_kal         = zscore(spread_kalman, window)
    pos_kal       = generate_signals(z_kal, ENTRY_THRESHOLD, EXIT_THRESHOLD)
    ret_kal       = compute_returns(pos_kal, nq_log, es_log, beta_kalman, COST_BPS)
    print("\n=== Kalman Filter ===")
    metrics_kal   = compute_metrics(ret_kal, pos_kal)

    # --- scatter plot: log(NQ) vs log(ES) with OLS regression line ---
    fig_s, ax_s = plt.subplots(figsize=(8, 6))
    ax_s.scatter(es_log, nq_log, alpha=0.3, s=8, color="steelblue", label="Daily observations")
    es_line = np.linspace(es_log.min(), es_log.max(), 200)
    ax_s.plot(es_line, ALPHA + BETA * es_line, color="crimson", linewidth=1.5, label=f"OLS fit  (β={BETA:.3f})")
    ax_s.set_title("OLS Regression: log(NQ) on log(ES)")
    ax_s.set_xlabel("log(ES close)")
    ax_s.set_ylabel("log(NQ close)")
    ax_s.legend()
    ax_s.grid(True, linestyle="--", alpha=0.4)
    fig_s.tight_layout()
    plt.show()

    # --- cost sensitivity sweep ---
    cost_range  = [0.5, 1.0, 2.0, 5.0, 10.0]
    sharpe_ols  = []
    sharpe_kal  = []

    print("\n=== Cost Sensitivity (Annualised Sharpe) ===")
    print(f"{'Cost (bps)':<14} {'Static OLS':>12} {'Kalman':>12}")
    print("-" * 40)
    for c in cost_range:
        r_ols = compute_returns(pos_ols, nq_log, es_log, BETA,         c)
        r_kal = compute_returns(pos_kal, nq_log, es_log, beta_kalman,  c)
        s_ols = r_ols.mean() / r_ols.std() * np.sqrt(252)
        s_kal = r_kal.mean() / r_kal.std() * np.sqrt(252)
        sharpe_ols.append(s_ols)
        sharpe_kal.append(s_kal)
        print(f"{c:<14.1f} {s_ols:>12.4f} {s_kal:>12.4f}")

    fig_c, ax_c = plt.subplots(figsize=(9, 5))
    ax_c.plot(cost_range, sharpe_ols, color="crimson",   marker="o", linewidth=1.5, label="Static OLS")
    ax_c.plot(cost_range, sharpe_kal, color="steelblue", marker="o", linewidth=1.5, label="Kalman Filter")
    ax_c.axhline(0, color="black", linestyle="--", linewidth=0.8)
    ax_c.set_title("Sharpe Ratio vs Transaction Cost")
    ax_c.set_xlabel("One-way transaction cost (bps)")
    ax_c.set_ylabel("Annualised Sharpe")
    ax_c.legend()
    ax_c.grid(True, linestyle="--", alpha=0.4)
    fig_c.tight_layout()
    plt.show()

    # --- equity curve comparison ---
    equity_ols = (1 + ret_ols).cumprod()
    equity_kal = (1 + ret_kal).cumprod()
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(equity_ols.index, equity_ols, color="crimson",   linewidth=1.2, label="Static OLS")
    ax.plot(equity_kal.index, equity_kal, color="steelblue", linewidth=1.2, label="Kalman Filter")
    ax.set_title("Equity Curve Comparison: Static OLS vs Kalman Filter")
    ax.set_xlabel("Date")
    ax.set_ylabel("Cumulative return (start = 1)")
    ax.legend()
    ax.grid(True, linestyle="--", alpha=0.4)
    plt.tight_layout()
    plt.show()
