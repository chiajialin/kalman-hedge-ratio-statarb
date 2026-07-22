# Corrections

This file exists because a review surfaced real bugs in the statistical pipeline
after the headline numbers were already written up throughout the notebook. Rather
than quietly patching the numbers, the pre-fix values are
recorded here verbatim, alongside a fix-by-fix attribution of how each correction
moved the result. Written *before* any of the fixes were applied, specifically so the
"before" column can't be revised with hindsight once the corrected numbers exist.

## Pre-registration (written before any fix was applied, before seeing any corrected number)

**What I will report if the Kalman edge on ES/NQ goes to zero once the bugs are fixed:**

I report it as the project's headline finding: across three estimators
(static OLS, rolling OLS, Kalman) and three cointegrated pairs, tested
walk-forward with transaction costs, no edge distinguishable from zero.
Section 13 becomes a null result, not a weakened positive one.

Ruled out in advance, if the number comes back at or near zero:
- retuning Q_KALMAN, ROLLING_WINDOW, or ENTRY_THRESHOLD after seeing the
  corrected numbers
- extending or shifting the sample window
- switching pair, frequency, or entry rule and reporting that result instead
- leading with the pre-fix 0.31 and relegating the correction to a footnote
The one thing that does justify re-running: discovering a further genuine
error in the pipeline. "I found a bug" is a legitimate reason to redo a
calculation; "I didn't like the number" is not. If I do find another error,
it gets its own row in the attribution table below, with the same before/after
treatment as fixes A-D.

## Bugs being corrected (see conversation / review for full detail)

- **Fix A — double lag** in `generate_signals` (`backtest.py`): position updates were
  delayed 2 days instead of 1.
- **Fix B — beta look-ahead** in `compute_returns` (`backtest.py`): time-varying beta
  wasn't lagged before scaling same-day returns.
- **Fix C — wrong critical values** in the cointegration screen (`cointegration.py`,
  `multi_pair_screen.py`): plain ADF critical values were used on regression
  residuals, which need Engle-Granger (MacKinnon) critical values instead. Does not
  affect the walk-forward table below, only the cointegration screen.
- **Fix D — Kalman R mislabeled** (`kalman_filter.py`, `walk_forward.py`): `R` was set
  to the OU/AR(1) innovation variance (`sigma**2`), not the cointegrating regression's
  residual variance (`Var(spread)`) as the docstring claimed — off by ~62x.
- **Smaller fixes (no separate letter, bundled as one commit):**
  - Turnover in `compute_metrics` was labelled "round trips" but counted raw position
    changes (2 per round trip, since entry and exit each count once) -- divided by 2.
  - `beta[0]` in `kalman_hedge_ratio` was a comment-mislabelled "OLS beta" that was
    actually `log(NQ)/log(ES)` at the first observation. Added an `initial_beta`
    parameter and pass the real `fit_ols()` beta from every caller. Zero effect on
    results (verified: identical to Fix D's snapshot), since the 700-day fit-window
    runway already burns off any influence of the seed before the test period starts.
  - Checked, not changed: the review's "flip undercharged ~4x" cost-model claim
    doesn't apply here -- verified directly that position changes are always
    magnitude 1 across all three legs (`generate_signals` always exits through 0
    before reversing, so a direct 2-unit flip structurally cannot occur).

## Pre-fix numbers (verbatim, before any correction)

### Cointegration screen (Section 11) — plain ADF critical values on residuals (WRONG, Fix C not yet applied)

| Pair | Beta | Alpha | ADF p-value | Cointegrated (p&lt;0.10) |
|------|------|-------|-------------|--------------------------|
| ES/NQ | 1.2384 | -0.7949 | 0.0260 | True |
| ES/YM | 0.7544 | 4.1187 | 0.0002 | True |
| ES/RTY | 0.6258 | 2.3210 | 0.2297 | False |
| RTY/NQ | 1.4700 | -1.5184 | 0.1436 | False |
| RTY/YM | 0.9253 | 3.4516 | 0.3527 | False |
| NQ/YM | 0.5897 | 4.7914 | 0.0007 | True |

### Cointegration screen (Section 11) — corrected, Engle-Granger/MacKinnon critical values (Fix C)

| Pair | Beta | Alpha | EG p-value | Cointegrated (p&lt;0.10) |
|------|------|-------|------------|--------------------------|
| ES/NQ | 1.2384 | -0.7949 | 0.0882 | True |
| ES/YM | 0.7544 | 4.1187 | 0.0010 | True |
| ES/RTY | 0.6258 | 2.3210 | 0.4560 | False |
| RTY/NQ | 1.4700 | -1.5184 | 0.3286 | False |
| RTY/YM | 0.9253 | 3.4516 | 0.6015 | False |
| NQ/YM | 0.5897 | 4.7914 | 0.0041 | True |

**Which pairs clear the p&lt;0.10 bar is unchanged** (ES/NQ/YM cointegrate, RTY doesn't), but
ES/NQ's own number was overstated by more than 3x (0.026 vs the real 0.088) — and 0.088 is
barely under the 10% threshold, not "real but not overwhelming" as originally framed. Also
worth noting for the write-up: under the corrected numbers, the walk-forward edge was found
on the *weakest*-cointegrated pair (ES/NQ, p=0.088) and was absent on the two that cointegrate
far more strongly (ES/YM p=0.001, NQ/YM p=0.004) — an inversion worth a paragraph either way
this lands, since it's either a hint the ES/NQ result was noise, or evidence that strength of
cointegration and tradeable divergence aren't the same property.

### Walk-forward + bootstrap significance (Sections 6-8, 12) — Fixes A, B, D not yet applied

| Pair  | Method | Sharpe | 90% CI low | 90% CI high | p-value (H0: no edge) |
|-------|--------|--------|------------|-------------|-----------------------|
| ES/NQ | Static OLS | -0.1756 | -0.9778 | 0.7067 | 0.6966 |
| ES/NQ | Rolling OLS 60d | 0.3927 | -0.5285 | 1.2344 | 0.2152 |
| ES/NQ | Kalman | 0.3096 | -0.2518 | 0.7985 | 0.0770 |
| ES/YM | Static OLS | -0.1520 | -0.7119 | 0.8899 | 0.7896 |
| ES/YM | Rolling OLS 60d | 1.1374 | 0.3724 | 1.9360 | 0.0068 |
| ES/YM | Kalman | -0.0263 | -0.8227 | 0.7658 | 0.5150 |
| NQ/YM | Static OLS | 0.2468 | -0.4786 | 1.1733 | 0.3956 |
| NQ/YM | Rolling OLS 60d | -0.8850 | -1.8802 | 0.0905 | 0.9310 |
| NQ/YM | Kalman | -0.0230 | -0.8006 | 0.8037 | 0.5622 |

## Fix-by-fix attribution (filled in as each fix lands)

To be populated from `data/processed/snapshot_*.csv` after each commit in Step 3.

| Stage | ES/NQ Kalman Sharpe | ES/NQ Kalman p-value | Notes |
|-------|---------------------|----------------------|-------|
| baseline (pre-fix) | 0.3096 | 0.0770 | matches table above |
| + Fix A (lag) | 0.2764 | 0.1920 | Sharpe barely moved, p-value alone crossed above the 10% threshold |
| + Fix B (beta look-ahead) | 0.2818 | 0.1854 | small movement, as expected for a same-day-only look-ahead |
| + Fix C (EG critical values) | 0.2818 | 0.1854 | unchanged, as expected -- this fix only touches the cointegration screen, not the walk-forward table |
| + Fix D (R correction) | 0.2821 | 0.2486 | Sharpe barely moved (contrary to the naive expectation that 62x larger R would collapse Kalman toward static OLS); p-value moved enough to fail even the 10% bar |

### Full cross-pair picture after all four fixes

| Pair | Method | Sharpe (baseline &rarr; corrected) | p-value (baseline &rarr; corrected) |
|------|--------|-------------------------------------|----------------------------------------|
| ES/NQ | Static OLS | -0.1756 &rarr; -0.1942 | 0.6966 &rarr; 0.7384 |
| ES/NQ | Rolling OLS 60d | 0.3927 &rarr; 0.6325 | 0.2152 &rarr; 0.1142 |
| ES/NQ | Kalman | 0.3096 &rarr; 0.2821 | 0.0770 &rarr; 0.2486 |
| ES/YM | Static OLS | -0.1520 &rarr; -0.3683 | 0.7896 &rarr; 0.9150 |
| ES/YM | Rolling OLS 60d | 1.1374 &rarr; 1.3615 | 0.0068 &rarr; 0.0022 |
| ES/YM | Kalman | -0.0263 &rarr; -0.4582 | 0.5150 &rarr; 0.8956 |
| NQ/YM | Static OLS | 0.2468 &rarr; 0.0142 | 0.3956 &rarr; 0.5816 |
| NQ/YM | Rolling OLS 60d | -0.8850 &rarr; -0.9750 | 0.9310 &rarr; 0.9486 |
| NQ/YM | Kalman | -0.0230 &rarr; -0.8878 | 0.5622 &rarr; 0.9754 |

**Reading this against the pre-registration above:** ES/NQ Kalman's point estimate did
not go to zero, but its p-value (0.249) no longer clears even the 10% threshold --
per the pre-registration's own definition ("no edge distinguishable from zero"), this
counts as the null-result outcome, not a weakened-but-still-significant one. Kalman's
results on the other two pairs, already weak at baseline, got uniformly worse after
correction. Rolling OLS remains the most unstable across pairs (still swinging from a
strongly significant +1.36 to a strongly negative -0.98 to -0.19-ish depending on
pair) -- if anything, more evidence for noise than before.

## Sensitivity sweep, rerun on the corrected pipeline (Q range recentred per above)

The original sensitivity story (Stage 10 / notebook Section 9) doesn't survive either:

- **Q_KALMAN** no longer shows a clean ramp-then-plateau. The middle of the recentred
  range (~3e-5 to ~6e-4) is noisy, bouncing between slightly negative and modestly
  positive Sharpe, before settling into a new plateau above ~8e-4 (Sharpe~0.30,
  p~0.18 -- still not significant). The actual default (1e-5) sits at the noisy low
  end: Sharpe 0.2821, p=0.2475.
- **ENTRY_THRESHOLD** no longer shows the sharp cliff at ~1.7 with consistently
  positive, sometimes-significant results above it. Now: negative-to-flat from 1.0
  through 1.8, a brief positive patch at 1.9-2.3 (best single point: 1.9, Sharpe
  0.36, p=0.13 -- still short of even 10% significance), noisy again through 3.0.
  **No point in the entire swept range reaches conventional significance.**

Honest reframe for the write-up: the old story was "mostly robust (Q) with one known
fragility (ENTRY_THRESHOLD)." The corrected story is closer to "no combination of
these two parameters, across the ranges tested, produces a statistically significant
result" -- consistent with, not contradicted by, Fix D's finding at the single
default configuration.

## Disclosed Q/R reparameterisation from Fix D (added 2026-07-22)

Fix D corrected `R` (Kalman observation noise) from ~3.34e-5 (the AR(1)/OU innovation
variance, used in error) to ~2.08e-3 (the cointegrating regression's actual residual
variance) -- a ~62x increase. `Q_KALMAN` (`walk_forward.py`, `1e-5`) was never adjusted
to match, so holding it fixed means the corrected filter runs at Q/R ~= 0.0048, roughly
62x less adaptive than the pre-fix filter's Q/R ~= 0.30. Left undisclosed, this looked
concealed: the sweep range in `sensitivity.py` had the default sitting exactly on its
left boundary, and the Q/R ratio that would reproduce the pre-fix filter's adaptivity
fell inside a region of the sweep with better-looking Sharpe/p-values.

Two things were done about this, both pre-specified before looking at any result:
1. Widened `Q_KALMAN_RANGE` / `HEATMAP_Q_RANGE` in `sensitivity.py` from
   `logspace(-5, -1.5, ...)` to `logspace(-6, -1.5, ...)` so the default no longer sits
   on a boundary.
2. Added `q_kalman_equivalent()` (`walk_forward.py`) -- computed directly from the
   pre/post-Fix-D R ratio (`PRE_FIX_Q_OVER_R = 1e-5 / 3.34e-5`, applied to each pair's
   own corrected R), not selected by inspecting the sweep. Tested identically across
   all three pairs (notebook Section 9b), not just ES/NQ.

**Actual finding (notebook Section 9b):** `Q_KALMAN_EQUIVALENT` = 6.22e-04 (ES/NQ's R).
At this Q, none of the three pairs improve on their current-default numbers -- ES/NQ is
slightly worse (Sharpe 0.18, p=0.27 vs. 0.28/0.25 at default), and ES/YM, NQ/YM are both
strongly negative and far from significant (Sharpe -0.73/p=0.98, Sharpe -0.52/p=0.88).
The concern motivating this check -- an undisclosed, favourable-looking operating point
-- does not materialise numerically. Section 13's null conclusion is unchanged, and if
anything reinforced by this check, not weakened by it.

**Correction to this entry (same day):** the first commit of `snapshot_q_equivalent_check.csv`
did not actually run at `Q_KALMAN_EQUIVALENT` -- `results_snapshot.py` had no way to
override `Q_KALMAN`, so `python src/results_snapshot.py q_equivalent_check` silently
reran at the default and produced a byte-for-byte duplicate of `snapshot_fix_e_smaller.csv`
under a new tag. `results_snapshot.py` now takes a `--q-equiv` flag (computes
`Q_KALMAN_EQUIVALENT` from ES/NQ's R via `q_kalman_equivalent()`, same as the notebook,
and applies it to all three pairs); the snapshot has been regenerated for real via
`python src/results_snapshot.py q_equivalent_check --q-equiv` and its Kalman-leg numbers
now match the notebook figures above exactly. The numbers themselves were already
correct (computed directly in the notebook, not from the broken snapshot) -- only the
committed CSV artifact was wrong, and only in a direction that would have looked more
favourable to the project than the truth, not less.
