"""
Walk-forward validation: rolling out-of-sample test of the Kalman-filtered
hedge ratio strategy against the static-OLS baseline.

Rationale: fitting beta/alpha (cointegration.py) and theta/half-life (ou_model.py)
on the full sample and then trading over that same sample is look-ahead bias --
every trade would see a hedge ratio estimated using future data. Walk-forward
instead splits the timeline into rolling fit/test folds: parameters are estimated
only on a trailing fit window, then traded on the following out-of-sample test
window, sliding forward until the data runs out. Stitching the out-of-sample
segments together gives an honest, look-ahead-free performance estimate.

Window sizing is derived from the spread's empirical half-life (~68 days, see
ou_model.py): the fit window needs ~10-20 half-lives to estimate theta reliably
(680-1360 days), and the test window needs ~5-10 half-lives to contain enough
complete reversion cycles for the Sharpe estimate to be meaningful (340-680 days).
With ~1631 trading days of ES/NQ data, this affords only 2-3 rolling folds --
a real data constraint, not a tuning choice.

Known simplification: each fold starts flat (no carried-over position from the
previous fold) and does not charge a closing cost for a position still open at
a fold's last test day. With only 2-3 fold boundaries total this is a minor
edge effect, not modelled further here.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from cointegration import fit_ols
from ou_model import estimate_ou, half_life
from kalman_filter import kalman_hedge_ratio
from backtest import (
    build_spread, zscore, generate_signals, compute_returns, compute_metrics,
    ENTRY_THRESHOLD, EXIT_THRESHOLD, COST_BPS,
)

FIT_WINDOW     = 700  # ~10 half-lives -- enough history to estimate beta/theta reliably
TEST_WINDOW    = 350  # ~5 half-lives -- enough to contain several reversion cycles
Q_KALMAN       = 1e-5  # beta drift allowance -- fixed hyperparameter, not fit per fold
ROLLING_WINDOW = 60    # trailing window for the rolling-OLS baseline, ~3 months --
                        # standard choice in the pairs-trading literature, and short
                        # enough (relative to FIT_WINDOW=700) to actually adapt within a fold


def rolling_ols_beta(nq_log: pd.Series, es_log: pd.Series, window: int) -> pd.Series:
    """Rolling-window OLS slope: beta_t = Cov(NQ, ES; trailing window) / Var(ES; trailing window).

    A simpler adaptive alternative to the Kalman filter -- re-estimates beta from
    scratch on each trailing window rather than smoothly filtering it forward.
    Comparing against this is the real test of whether the Kalman filter's added
    sophistication earns its keep: both approaches let beta drift, just via
    different mechanisms (hard window cutoff vs. Bayesian smoothing).
    """
    cov = nq_log.rolling(window).cov(es_log)
    var = es_log.rolling(window).var()
    return cov / var


def make_folds(n: int, fit_window: int, test_window: int) -> list[tuple[int, int, int]]:
    """Generate (fit_start, test_start, test_end) index triples for rolling walk-forward.

    Rolls forward by test_window each time (non-overlapping test periods). The
    final fold's test period is truncated to whatever data remains, as long as
    at least half a test window is left -- otherwise it's dropped.
    """
    folds = []
    fold_start = 0
    while fold_start + fit_window < n:
        test_start = fold_start + fit_window
        test_end   = min(test_start + test_window, n)
        if test_end - test_start >= test_window // 2:
            folds.append((fold_start, test_start, test_end))
        fold_start += test_window
    return folds


def run_fold(nq_log: pd.Series, es_log: pd.Series,
             fit_start: int, test_start: int, test_end: int,
             q_kalman: float = Q_KALMAN, entry_threshold: float = ENTRY_THRESHOLD,
             exit_threshold: float = EXIT_THRESHOLD) -> dict:
    """Fit parameters on [fit_start:test_start), trade on [test_start:test_end).

    The rolling z-score and the Kalman filter are both computed over the full
    [fit_start:test_end) span so they're past their burn-in by the time the
    test period begins, then sliced down to the test period before generating
    signals. Return calculation also uses the full span (so the first test-day
    return has a valid prior day to diff against) before slicing to test-only.

    q_kalman/entry_threshold/exit_threshold default to the module-level
    constants but can be overridden -- used by sensitivity.py to sweep them
    without duplicating this pipeline.
    """
    fit_nq, fit_es   = nq_log.iloc[fit_start:test_start], es_log.iloc[fit_start:test_start]
    full_nq, full_es = nq_log.iloc[fit_start:test_end],   es_log.iloc[fit_start:test_end]
    test_index = nq_log.iloc[test_start:test_end].index

    # --- fit on trailing window only ---
    fit = fit_ols(fit_nq, fit_es)
    beta, alpha = fit["beta"], fit["alpha"]
    ou_params = estimate_ou(fit["spread"])
    window    = half_life(ou_params["theta"])
    r_kalman  = ou_params["sigma"] ** 2

    # --- static OLS leg: fold-fixed beta/alpha, rolling stats warmed up over full span ---
    spread_ols = build_spread(full_nq, full_es, beta, alpha)
    z_ols      = zscore(spread_ols, window).loc[test_index]
    pos_ols    = generate_signals(z_ols, entry_threshold, exit_threshold)
    pos_ols_aligned = pos_ols.reindex(full_nq.index, fill_value=0.0)
    ret_ols    = compute_returns(pos_ols_aligned, full_nq, full_es, beta, COST_BPS).loc[test_index]

    # --- rolling-OLS leg: beta re-estimated from scratch each day on a trailing window ---
    beta_roll  = rolling_ols_beta(full_nq, full_es, ROLLING_WINDOW)
    spread_roll = build_spread(full_nq, full_es, beta_roll, alpha)
    z_roll      = zscore(spread_roll, window).loc[test_index]
    pos_roll    = generate_signals(z_roll, entry_threshold, exit_threshold)
    pos_roll_aligned = pos_roll.reindex(full_nq.index, fill_value=0.0)
    ret_roll    = compute_returns(pos_roll_aligned, full_nq, full_es, beta_roll, COST_BPS).loc[test_index]

    # --- Kalman leg: filter warmed up continuously over full span before test starts ---
    beta_kalman = kalman_hedge_ratio(full_nq, full_es, alpha, q_kalman, r_kalman)
    spread_kal  = build_spread(full_nq, full_es, beta_kalman, alpha)
    z_kal       = zscore(spread_kal, window).loc[test_index]
    pos_kal     = generate_signals(z_kal, entry_threshold, exit_threshold)
    pos_kal_aligned = pos_kal.reindex(full_nq.index, fill_value=0.0)
    ret_kal     = compute_returns(pos_kal_aligned, full_nq, full_es, beta_kalman, COST_BPS).loc[test_index]

    return {
        "beta": beta, "half_life": window,
        "pos_ols": pos_ols, "ret_ols": ret_ols,
        "pos_roll": pos_roll, "ret_roll": ret_roll,
        "pos_kal": pos_kal, "ret_kal": ret_kal,
    }


def run_walk_forward(nq_log: pd.Series, es_log: pd.Series,
                      q_kalman: float = Q_KALMAN, entry_threshold: float = ENTRY_THRESHOLD,
                      exit_threshold: float = EXIT_THRESHOLD) -> dict:
    """Run the full rolling walk-forward loop and stitch out-of-sample results.

    Returns dict with keys: folds, fold_betas, fold_half_lives, pos_ols, ret_ols,
    pos_roll, ret_roll, pos_kal, ret_kal -- the position/return entries are
    pd.Series spanning all folds' stitched test periods.

    q_kalman/entry_threshold/exit_threshold default to the module-level
    constants but can be overridden -- used by sensitivity.py.
    """
    folds = make_folds(len(es_log), FIT_WINDOW, TEST_WINDOW)

    pos_ols_parts, ret_ols_parts   = [], []
    pos_roll_parts, ret_roll_parts = [], []
    pos_kal_parts, ret_kal_parts   = [], []
    fold_betas, fold_half_lives    = [], []

    for fit_start, test_start, test_end in folds:
        r = run_fold(nq_log, es_log, fit_start, test_start, test_end,
                      q_kalman=q_kalman, entry_threshold=entry_threshold,
                      exit_threshold=exit_threshold)
        pos_ols_parts.append(r["pos_ols"]); ret_ols_parts.append(r["ret_ols"])
        pos_roll_parts.append(r["pos_roll"]); ret_roll_parts.append(r["ret_roll"])
        pos_kal_parts.append(r["pos_kal"]); ret_kal_parts.append(r["ret_kal"])
        fold_betas.append(r["beta"]); fold_half_lives.append(r["half_life"])

    return {
        "folds": folds,
        "fold_betas": fold_betas,
        "fold_half_lives": fold_half_lives,
        "pos_ols": pd.concat(pos_ols_parts).sort_index(),
        "ret_ols": pd.concat(ret_ols_parts).sort_index(),
        "pos_roll": pd.concat(pos_roll_parts).sort_index(),
        "ret_roll": pd.concat(ret_roll_parts).sort_index(),
        "pos_kal": pd.concat(pos_kal_parts).sort_index(),
        "ret_kal": pd.concat(ret_kal_parts).sort_index(),
    }


if __name__ == "__main__":
    es = pd.read_csv("data/raw/es_daily.csv", index_col="date", parse_dates=True)
    nq = pd.read_csv("data/raw/nq_daily.csv", index_col="date", parse_dates=True)
    es_log = np.log(es["close"])
    nq_log = np.log(nq["close"])

    wf = run_walk_forward(nq_log, es_log)
    folds = wf["folds"]
    dates = nq_log.index

    print(f"{len(folds)} walk-forward folds (fit={FIT_WINDOW}d, test={TEST_WINDOW}d, Q={Q_KALMAN})\n")
    for i, (fit_start, test_start, test_end) in enumerate(folds):
        print(f"Fold {i+1}: fit [{dates[fit_start].date()} to {dates[test_start-1].date()}]  "
              f"test [{dates[test_start].date()} to {dates[test_end-1].date()}]  "
              f"beta={wf['fold_betas'][i]:.4f}  half_life={wf['fold_half_lives'][i]}d")

    print("\n=== Walk-Forward OOS: Static OLS (refit each fold) ===")
    compute_metrics(wf["ret_ols"], wf["pos_ols"])

    print(f"\n=== Walk-Forward OOS: Rolling OLS ({ROLLING_WINDOW}d window) ===")
    compute_metrics(wf["ret_roll"], wf["pos_roll"])

    print("\n=== Walk-Forward OOS: Kalman Filter (refit each fold) ===")
    compute_metrics(wf["ret_kal"], wf["pos_kal"])

    # --- stitched equity curve, fold boundaries marked ---
    equity_ols  = (1 + wf["ret_ols"]).cumprod()
    equity_roll = (1 + wf["ret_roll"]).cumprod()
    equity_kal  = (1 + wf["ret_kal"]).cumprod()
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(equity_ols.index,  equity_ols,  color="crimson",    linewidth=1.2, label="Static OLS (walk-forward)")
    ax.plot(equity_roll.index, equity_roll, color="darkorange", linewidth=1.2, label=f"Rolling OLS {ROLLING_WINDOW}d (walk-forward)")
    ax.plot(equity_kal.index,  equity_kal,  color="steelblue",  linewidth=1.2, label="Kalman Filter (walk-forward)")
    for _, test_start, _ in folds[1:]:
        ax.axvline(dates[test_start], color="gray", linestyle=":", linewidth=0.8)
    ax.set_title("Walk-Forward Out-of-Sample Equity Curve (dotted = fold boundary)")
    ax.set_xlabel("Date")
    ax.set_ylabel("Cumulative return (start = 1)")
    ax.legend()
    ax.grid(True, linestyle="--", alpha=0.4)
    plt.tight_layout()
    plt.show()
