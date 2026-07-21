"""
Extends the walk-forward + significance pipeline (walk_forward.py, significance.py),
already validated on ES/NQ, to the two other pairs that passed the Section 11
cointegration screen (multi_pair_screen.py): ES/YM and NQ/YM. RTY was dropped there --
it failed to reject the unit-root null against every other index. ES/NQ is included
here too, as a rerun sanity check against Stage 6-8's original numbers, not a fresh
result.

Same regression direction convention as multi_pair_screen.py (breadth order
ES > RTY > NQ > YM, broader index always the regressor): NQ is the dependent
variable against ES, YM is the dependent variable against both ES and NQ.

Reuses run_walk_forward()/test_significance() as-is -- both are pair-agnostic
(they operate on whichever two log-price series are passed in), so this is the
existing pipeline pointed at different data, not new modelling logic.

Note: ROLLING_WINDOW (60d, the rolling-OLS baseline's beta window) and Q_KALMAN
(1e-5, imported as run_walk_forward's default) are held at their ES/NQ-derived
values here, not re-tuned per pair. Both were calibrated only against ES/NQ
(Stage 7's window convention, Stage 10's sensitivity sweep) -- re-tuning them
per pair after seeing each pair's result would be exactly the kind of after-the-
fact parameter search Stage 10 was designed to avoid. If Kalman looks flat or
rolling-OLS looks unstable on ES/YM or NQ/YM, that's a candidate real finding
about hyperparameter transfer, not evidence of a bug.
"""

import numpy as np
import pandas as pd

from cointegration import fit_ols
from ou_model import estimate_ou, half_life
from walk_forward import run_walk_forward, ROLLING_WINDOW
from significance import test_significance


if __name__ == "__main__":
    es = pd.read_csv("data/raw/es_daily.csv", index_col="date", parse_dates=True)
    nq = pd.read_csv("data/raw/nq_daily.csv", index_col="date", parse_dates=True)
    ym = pd.read_csv("data/raw/ym_daily.csv", index_col="date", parse_dates=True)

    es_log = np.log(es["close"])
    nq_log = np.log(nq["close"])
    ym_log = np.log(ym["close"])

    # (y_log, x_log, label) -- y is the dependent variable, x the regressor
    pairs = [
        (nq_log, es_log, "ES/NQ"),  # sanity-check rerun, not a fresh result
        (ym_log, es_log, "ES/YM"),
        (ym_log, nq_log, "NQ/YM"),
    ]

    for y_log, x_log, label in pairs:
        print("\n" + "=" * 70)
        print(label)
        print("=" * 70)

        # --- full-sample OU/half-life, same as Stage 3 for ES/NQ ---
        fit = fit_ols(y_log, x_log)
        ou_params = estimate_ou(fit["spread"])
        hl = half_life(ou_params["theta"])
        print(f"Full-sample beta={fit['beta']:.4f}  alpha={fit['alpha']:.4f}")
        print(f"OU fit: theta={ou_params['theta']:.4f}  half-life={hl}d")

        # --- walk-forward: static OLS, rolling OLS, Kalman ---
        wf = run_walk_forward(y_log, x_log)

        test_significance(wf["ret_ols"], f"Static OLS ({label})")
        test_significance(wf["ret_roll"], f"Rolling OLS {ROLLING_WINDOW}d ({label})")
        test_significance(wf["ret_kal"], f"Kalman Filter ({label})")
