"""Dump the headline results table to CSV. Run after each bugfix commit
to attribute the change in results to a specific fix."""
import sys
import numpy as np, pandas as pd
from walk_forward import run_walk_forward, ROLLING_WINDOW
from significance import test_significance

TAG = sys.argv[1] if len(sys.argv) > 1 else "untagged"

def load(t):
    return np.log(pd.read_csv(f"data/raw/{t}_daily.csv",
                              index_col="date", parse_dates=True)["close"])

es, nq, ym = load("es"), load("nq"), load("ym")
rows = []
for y, x, label in [(nq, es, "ES/NQ"), (ym, es, "ES/YM"), (ym, nq, "NQ/YM")]:
    wf = run_walk_forward(y, x)
    for method, key in [("Static OLS", "ret_ols"),
                        (f"Rolling OLS {ROLLING_WINDOW}d", "ret_roll"),
                        ("Kalman", "ret_kal")]:
        sig = test_significance(wf[key], f"{method} ({label})")
        rows.append({"tag": TAG, "pair": label, "method": method, **sig})

pd.DataFrame(rows).to_csv(f"data/processed/snapshot_{TAG}.csv", index=False)
print(f"\nWrote data/processed/snapshot_{TAG}.csv")
