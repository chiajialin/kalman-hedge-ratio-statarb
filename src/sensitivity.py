"""
Sensitivity sweep for the walk-forward pipeline's hand-picked hyperparameters.

Not a parameter search / optimization -- deliberately does NOT pick whichever
value performs best. Searching for the best-performing parameter using the same
out-of-sample data the walk-forward test is supposed to be honest about would
silently reintroduce the exact look-ahead problem walk-forward was built to
eliminate (see walk_forward.py's module docstring).

Instead: rerun the full walk-forward pipeline across a range of reasonable
values for one parameter at a time, holding everything else at its default,
and report how the Kalman leg's Sharpe and bootstrap significance p-value move.
The question being answered is "is the headline result fragile, or does it hold
up across a range of defensible choices" -- not "what's the best number."

Two parameters swept:
  - Q_KALMAN: controls how fast the Kalman filter lets beta drift. Arguably the
    single most consequential hyperparameter in the whole pipeline.
  - ENTRY_THRESHOLD: the core z-score trading rule threshold.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm

from walk_forward import run_walk_forward, Q_KALMAN, ENTRY_THRESHOLD
from significance import sharpe, block_bootstrap, BLOCK_SIZE

SWEEP_N_BOOT = 2000  # lower than significance.py's 5000 -- sweeping many values,
                      # the precision needed here is "does this move a lot," not
                      # a publication-precise p-value
SEED = 0

# Log-spaced over Q_KALMAN's 3 orders of magnitude -- linear spacing would waste
# almost all points on the (uninteresting, flat) high end.
#
# Range recentred after CORRECTIONS.md Fix D: R increased ~62x (was the OU/AR(1)
# innovation variance, corrected to the cointegrating regression's actual residual
# variance). Q is only meaningful relative to R, so the old logspace(-6, -3) window
# now covers a filter up to 62x less adaptive than what it swept before -- it no
# longer brackets the same Q/R territory. Shifted up by roughly that factor. This
# is a recentring to match the corrected R, not a search for a better-looking value
# -- the range was chosen before rerunning the sweep, same discipline as always.
# Lower bound extended to -5 (not exactly -4.5) specifically so the actual current
# Q_KALMAN default (1e-5) is an included, swept data point rather than sitting just
# outside the range -- otherwise this sweep couldn't confirm the real configuration
# behaves the way the rest of the range suggests, only points near it.
Q_KALMAN_RANGE        = np.logspace(-5, -1.5, 25)
ENTRY_THRESHOLD_RANGE = np.arange(1.0, 3.01, 0.1)

# Coarser grid for the joint sweep -- one-at-a-time sweeps above hold the other
# parameter at its default, which silently assumes the two don't interact. This
# checks that assumption. Coarser than the 1D sweeps (12x11=132 points instead of
# 25 or 21) and fewer bootstrap draws, purely to keep runtime reasonable -- the
# goal here is spotting an interaction pattern, not precise per-cell values.
HEATMAP_N_BOOT      = 1000
HEATMAP_Q_RANGE     = np.logspace(-5, -1.5, 12)
HEATMAP_ENTRY_RANGE = np.arange(1.0, 3.01, 0.2)


def kalman_leg_stats(nq_log: pd.Series, es_log: pd.Series,
                      q_kalman: float = Q_KALMAN, entry_threshold: float = ENTRY_THRESHOLD,
                      n_boot: int = SWEEP_N_BOOT) -> dict:
    """Run the walk-forward pipeline with the given parameters and return the
    Kalman leg's Sharpe and bootstrap significance p-value (H0: no true edge).
    """
    wf = run_walk_forward(nq_log, es_log, q_kalman=q_kalman, entry_threshold=entry_threshold)
    r = wf["ret_kal"].dropna().values

    observed_sharpe = sharpe(r)

    rng = np.random.default_rng(SEED)
    r_demeaned = r - r.mean()
    null_sharpes = block_bootstrap(r_demeaned, BLOCK_SIZE, n_boot, rng)
    p_value = (null_sharpes >= observed_sharpe).mean()

    return {"sharpe": observed_sharpe, "p_value": p_value}


def heatmap_sweep(nq_log: pd.Series, es_log: pd.Series,
                   q_range: np.ndarray, e_range: np.ndarray, n_boot: int) -> tuple:
    """Joint sweep over Q_KALMAN x ENTRY_THRESHOLD. Returns (sharpe_grid, pvalue_grid),
    each shaped (len(q_range), len(e_range))."""
    sharpe_grid = np.empty((len(q_range), len(e_range)))
    pvalue_grid = np.empty((len(q_range), len(e_range)))
    for i, q in enumerate(q_range):
        for j, e in enumerate(e_range):
            r = kalman_leg_stats(nq_log, es_log, q_kalman=q, entry_threshold=e, n_boot=n_boot)
            sharpe_grid[i, j] = r["sharpe"]
            pvalue_grid[i, j] = r["p_value"]
    return sharpe_grid, pvalue_grid


if __name__ == "__main__":
    es = pd.read_csv("data/raw/es_daily.csv", index_col="date", parse_dates=True)
    nq = pd.read_csv("data/raw/nq_daily.csv", index_col="date", parse_dates=True)
    es_log = np.log(es["close"])
    nq_log = np.log(nq["close"])

    print("=" * 60)
    print(f"SENSITIVITY SWEEP: Q_KALMAN (entry_threshold fixed at {ENTRY_THRESHOLD})")
    print("=" * 60)
    print(f"{'Q_KALMAN':<12} {'Sharpe':>10} {'p-value':>10}")
    q_sharpes, q_pvalues = [], []
    for q in Q_KALMAN_RANGE:
        r = kalman_leg_stats(nq_log, es_log, q_kalman=q)
        q_sharpes.append(r["sharpe"]); q_pvalues.append(r["p_value"])
        marker = "  <- current default" if np.isclose(q, Q_KALMAN) else ""
        print(f"{q:<12.2e} {r['sharpe']:>10.4f} {r['p_value']:>10.4f}{marker}")

    print()
    print("=" * 60)
    print(f"SENSITIVITY SWEEP: ENTRY_THRESHOLD (Q_KALMAN fixed at {Q_KALMAN:.0e})")
    print("=" * 60)
    print(f"{'ENTRY_THRESHOLD':<16} {'Sharpe':>10} {'p-value':>10}")
    e_sharpes, e_pvalues = [], []
    for e in ENTRY_THRESHOLD_RANGE:
        r = kalman_leg_stats(nq_log, es_log, entry_threshold=e)
        e_sharpes.append(r["sharpe"]); e_pvalues.append(r["p_value"])
        marker = "  <- current default" if np.isclose(e, ENTRY_THRESHOLD) else ""
        print(f"{e:<16.2f} {r['sharpe']:>10.4f} {r['p_value']:>10.4f}{marker}")

    # --- plot: Sharpe and p-value against each parameter, default marked ---
    fig, axes = plt.subplots(2, 2, figsize=(13, 8))

    ax = axes[0, 0]
    ax.plot(Q_KALMAN_RANGE, q_sharpes, color="steelblue", marker="o", markersize=3, linewidth=1.2)
    ax.axvline(Q_KALMAN, color="gray", linestyle=":", linewidth=1)
    ax.axhline(0, color="black", linestyle="--", linewidth=0.8)
    ax.set_xscale("log")
    ax.set_title("Kalman Sharpe vs Q_KALMAN")
    ax.set_xlabel("Q_KALMAN (log scale)")
    ax.set_ylabel("Annualised Sharpe")
    ax.grid(True, linestyle="--", alpha=0.4)

    ax = axes[1, 0]
    ax.plot(Q_KALMAN_RANGE, q_pvalues, color="darkorange", marker="o", markersize=3, linewidth=1.2)
    ax.axvline(Q_KALMAN, color="gray", linestyle=":", linewidth=1)
    ax.axhline(0.05, color="crimson", linestyle="--", linewidth=0.8, label="p=0.05")
    ax.axhline(0.10, color="crimson", linestyle=":", linewidth=0.8, label="p=0.10")
    ax.set_xscale("log")
    ax.set_title("Bootstrap p-value vs Q_KALMAN")
    ax.set_xlabel("Q_KALMAN (log scale)")
    ax.set_ylabel("p-value (H0: no edge)")
    ax.legend()
    ax.grid(True, linestyle="--", alpha=0.4)

    ax = axes[0, 1]
    ax.plot(ENTRY_THRESHOLD_RANGE, e_sharpes, color="steelblue", marker="o", markersize=3, linewidth=1.2)
    ax.axvline(ENTRY_THRESHOLD, color="gray", linestyle=":", linewidth=1)
    ax.axhline(0, color="black", linestyle="--", linewidth=0.8)
    ax.set_title("Kalman Sharpe vs ENTRY_THRESHOLD")
    ax.set_xlabel("ENTRY_THRESHOLD")
    ax.set_ylabel("Annualised Sharpe")
    ax.grid(True, linestyle="--", alpha=0.4)

    ax = axes[1, 1]
    ax.plot(ENTRY_THRESHOLD_RANGE, e_pvalues, color="darkorange", marker="o", markersize=3, linewidth=1.2)
    ax.axvline(ENTRY_THRESHOLD, color="gray", linestyle=":", linewidth=1)
    ax.axhline(0.05, color="crimson", linestyle="--", linewidth=0.8, label="p=0.05")
    ax.axhline(0.10, color="crimson", linestyle=":", linewidth=0.8, label="p=0.10")
    ax.set_title("Bootstrap p-value vs ENTRY_THRESHOLD")
    ax.set_xlabel("ENTRY_THRESHOLD")
    ax.set_ylabel("p-value (H0: no edge)")
    ax.legend()
    ax.grid(True, linestyle="--", alpha=0.4)

    fig.suptitle("Parameter Sensitivity: Kalman Leg, Walk-Forward OOS (dotted grey = current default)")
    fig.tight_layout()
    fig.savefig("data/processed/sensitivity_sweep.png", dpi=150)
    print("\nSaved plot to data/processed/sensitivity_sweep.png")

    # --- joint sweep: do Q_KALMAN and ENTRY_THRESHOLD interact? ---
    print()
    print("=" * 60)
    print(f"JOINT SWEEP: Q_KALMAN x ENTRY_THRESHOLD ({len(HEATMAP_Q_RANGE)}x{len(HEATMAP_ENTRY_RANGE)} grid)")
    print("=" * 60)
    sharpe_grid, pvalue_grid = heatmap_sweep(nq_log, es_log, HEATMAP_Q_RANGE, HEATMAP_ENTRY_RANGE, HEATMAP_N_BOOT)

    X, Y = np.meshgrid(HEATMAP_ENTRY_RANGE, HEATMAP_Q_RANGE)
    fig2, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5.5))

    # Sharpe: diverging -- polarity (positive vs negative) is the meaningful split, zero is
    # a real, meaningful midpoint, not just the low end of a magnitude scale.
    norm = TwoSlopeNorm(vcenter=0, vmin=sharpe_grid.min(), vmax=sharpe_grid.max())
    pcm1 = ax1.pcolormesh(X, Y, sharpe_grid, cmap="RdBu", norm=norm, shading="auto")
    ax1.set_yscale("log")
    ax1.scatter([ENTRY_THRESHOLD], [Q_KALMAN], color="black", marker="*", s=200,
                edgecolor="white", linewidth=1, zorder=5, label="current default")
    ax1.set_title("Kalman Sharpe")
    ax1.set_xlabel("ENTRY_THRESHOLD")
    ax1.set_ylabel("Q_KALMAN (log scale)")
    ax1.legend(loc="upper left", fontsize=8, framealpha=0.9)
    fig2.colorbar(pcm1, ax=ax1, label="Annualised Sharpe")

    # p-value: sequential -- a magnitude (how far from "no edge"), one hue light-to-dark,
    # plus explicit contour lines at the two conventional significance thresholds so the
    # boundary is a line you can read, not just a colour gradient you have to guess at.
    pcm2 = ax2.pcolormesh(X, Y, pvalue_grid, cmap="viridis", shading="auto")
    cs = ax2.contour(X, Y, pvalue_grid, levels=[0.05, 0.10], colors="white", linewidths=1.4,
                      linestyles=["--", ":"])
    ax2.clabel(cs, fmt={0.05: "p=0.05", 0.10: "p=0.10"}, fontsize=8, colors="white")
    ax2.set_yscale("log")
    ax2.scatter([ENTRY_THRESHOLD], [Q_KALMAN], color="white", marker="*", s=200,
                edgecolor="black", linewidth=1, zorder=5, label="current default")
    ax2.set_title("Bootstrap p-value")
    ax2.set_xlabel("ENTRY_THRESHOLD")
    ax2.set_ylabel("Q_KALMAN (log scale)")
    ax2.legend(loc="upper left", fontsize=8, framealpha=0.9)
    fig2.colorbar(pcm2, ax=ax2, label="p-value (H0: no edge)")

    fig2.suptitle("Joint Sensitivity: Do Q_KALMAN and ENTRY_THRESHOLD Interact?")
    fig2.tight_layout()
    fig2.savefig("data/processed/sensitivity_heatmap.png", dpi=150)
    print("Saved heatmap to data/processed/sensitivity_heatmap.png")
    plt.show()
