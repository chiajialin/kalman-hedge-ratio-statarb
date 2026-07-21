"""
Block-bootstrap significance testing for the walk-forward strategy Sharpe ratios.

Answers two related but distinct questions, both via block bootstrap (resampling
contiguous chunks of returns, not individual days, to preserve the autocorrelation
that comes from holding a position for multiple days at a time):

1. Confidence interval: how uncertain is the observed Sharpe estimate itself?
   Resample the actual returns and look at the spread of bootstrap Sharpes.

2. Null-hypothesis test: could a process with zero true edge -- but the same
   volatility and autocorrelation structure as the strategy -- produce a Sharpe
   this high by chance? Resample from the DE-MEANED return series (same
   vol/autocorrelation, zero true mean) and see what fraction of bootstrap
   Sharpes match or exceed the observed one. That fraction is the p-value.

Block length is set to ~20 trading days (one month), close to the average
holding period implied by both legs' turnover in walk_forward.py (roughly
252 / annual_turnover =~ 14-24 trading days), so blocks are long enough to
preserve position-persistence autocorrelation without leaving too few
independent blocks to resample from.
"""

import numpy as np
import pandas as pd

from walk_forward import run_walk_forward, ROLLING_WINDOW

BLOCK_SIZE = 20
N_BOOT     = 5000
SEED       = 0


def sharpe(returns: np.ndarray) -> float:
    """Annualised Sharpe ratio from a daily return array."""
    std = returns.std()
    if std == 0:
        return 0.0
    return returns.mean() / std * np.sqrt(252)


def block_bootstrap(returns: np.ndarray, block_size: int, n_boot: int,
                     rng: np.random.Generator) -> np.ndarray:
    """Resample `returns` into n_boot synthetic series of the same length,
    built from contiguous blocks drawn with replacement, and return the
    Sharpe ratio of each synthetic series.
    """
    n = len(returns)
    n_blocks = int(np.ceil(n / block_size))
    boot_sharpes = np.empty(n_boot)

    for b in range(n_boot):
        starts = rng.integers(0, n - block_size + 1, size=n_blocks)
        sample = np.concatenate([returns[s:s + block_size] for s in starts])[:n]
        boot_sharpes[b] = sharpe(sample)

    return boot_sharpes


def test_significance(returns: pd.Series, label: str, block_size: int = BLOCK_SIZE,
                       n_boot: int = N_BOOT, seed: int = SEED) -> dict:
    """Run both the CI and null-hypothesis bootstrap tests on a return series.

    Returns dict with keys: sharpe, ci_low, ci_high, p_value.
    """
    rng = np.random.default_rng(seed)
    r = returns.dropna().values
    observed_sharpe = sharpe(r)

    # --- confidence interval: bootstrap the actual returns ---
    ci_sharpes = block_bootstrap(r, block_size, n_boot, rng)
    ci_low, ci_high = np.percentile(ci_sharpes, [5, 95])

    # --- null hypothesis: bootstrap the de-meaned returns (zero true edge) ---
    r_demeaned = r - r.mean()
    null_sharpes = block_bootstrap(r_demeaned, block_size, n_boot, rng)
    p_value = (null_sharpes >= observed_sharpe).mean()

    print(f"\n--- {label} ---")
    print(f"  Observed Sharpe        : {observed_sharpe:.4f}")
    print(f"  90% bootstrap CI       : [{ci_low:.4f}, {ci_high:.4f}]")
    print(f"  p-value (H0: no edge)  : {p_value:.4f}")

    return {"sharpe": observed_sharpe, "ci_low": ci_low, "ci_high": ci_high, "p_value": p_value}


if __name__ == "__main__":
    es = pd.read_csv("data/raw/es_daily.csv", index_col="date", parse_dates=True)
    nq = pd.read_csv("data/raw/nq_daily.csv", index_col="date", parse_dates=True)
    es_log = np.log(es["close"])
    nq_log = np.log(nq["close"])

    wf = run_walk_forward(nq_log, es_log)

    print("=" * 60)
    print(f"BLOCK-BOOTSTRAP SIGNIFICANCE TEST (block={BLOCK_SIZE}d, n_boot={N_BOOT})")
    print("=" * 60)
    test_significance(wf["ret_ols"], "Static OLS (walk-forward OOS)")
    test_significance(wf["ret_roll"], f"Rolling OLS {ROLLING_WINDOW}d (walk-forward OOS)")
    test_significance(wf["ret_kal"], "Kalman Filter (walk-forward OOS)")
