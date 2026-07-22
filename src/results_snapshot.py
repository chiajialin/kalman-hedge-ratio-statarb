"""Dump the headline results table to CSV. Run after each bugfix commit
to attribute the change in results to a specific fix."""
import sys
import numpy as np, pandas as pd
from cointegration import fit_ols
from walk_forward import run_walk_forward, ROLLING_WINDOW, q_kalman_equivalent
from significance import test_significance

TAG = sys.argv[1] if len(sys.argv) > 1 else "untagged"
USE_Q_EQUIV = "--q-equiv" in sys.argv

def load(t):
    return np.log(pd.read_csv(f"data/raw/{t}_daily.csv",
                              index_col="date", parse_dates=True)["close"])

es, nq, ym = load("es"), load("nq"), load("ym")

# --q-equiv: run the Kalman leg at Q_KALMAN_EQUIVALENT (see CORRECTIONS.md's
# "Disclosed Q/R reparameterisation" entry) instead of the default Q_KALMAN.
# Derived once from ES/NQ's own R and applied identically to all three pairs,
# same as notebook Section 9b -- not re-derived per pair.
q_kalman_kwargs = {}
if USE_Q_EQUIV:
    q_equiv = q_kalman_equivalent(fit_ols(nq, es)["spread"])
    q_kalman_kwargs = {"q_kalman": q_equiv}
    print(f"Using Q_KALMAN_EQUIVALENT = {q_equiv:.2e} (derived from ES/NQ, applied to all pairs)\n")

rows = []
for y, x, label in [(nq, es, "ES/NQ"), (ym, es, "ES/YM"), (ym, nq, "NQ/YM")]:
    wf = run_walk_forward(y, x, **q_kalman_kwargs)
    for method, key in [("Static OLS", "ret_ols"),
                        (f"Rolling OLS {ROLLING_WINDOW}d", "ret_roll"),
                        ("Kalman", "ret_kal")]:
        sig = test_significance(wf[key], f"{method} ({label})")
        rows.append({"tag": TAG, "pair": label, "method": method, **sig})

pd.DataFrame(rows).to_csv(f"data/processed/snapshot_{TAG}.csv", index=False)
print(f"\nWrote data/processed/snapshot_{TAG}.csv")
