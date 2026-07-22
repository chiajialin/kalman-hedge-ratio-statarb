# Phase 2 Protocol — Intraday Extension (Pre-Registered)

Committed BEFORE sourcing any intraday data or running any intraday analysis, in the
same spirit as CORRECTIONS.md: the questions, methods, cost assumptions, and reporting
commitments are fixed here so they cannot be adjusted after seeing results.

## Motivation

The daily-frequency result (README) is a null: no estimator shows a statistically
significant edge on any cointegrated pair. But that null is ambiguous between two
explanations:

1. The divergence-reversion phenomenon is absent (or too weak to matter), or
2. The daily test is underpowered: 931 out-of-sample days against a ~68-day spread
   half-life gives each walk-forward fold only a handful of complete reversion cycles,
   which is why the bootstrap confidence intervals are wide (e.g. ES/NQ Kalman 90% CI
   [-0.30, +1.09] around a 0.28 point estimate).

Intraday data discriminates between these: if the intraday half-life is on the order of
hours, the same calendar span contains far more independent reversion cycles and the
significance test gains real power. Separately, sub-hourly is the timeframe at which
the retail "SMT divergence" claim is actually used — the daily test never addressed the
claim at its native resolution (noted in README Limitations).

## Scope

- Frequencies: hourly and 5-minute bars. 1-minute is explicitly EXCLUDED (compute cost
  and microstructure realism do not justify one more curve point).
- Instruments: ES and NQ continuous front-month only. No new pairs.
- Session convention: regular trading hours (RTH) bars only. Overnight gaps would
  distort rolling z-scores and the OU fit; excluding them is the simplest defensible
  choice and is fixed here in advance.
- Roll handling: same unadjusted-continuous caveat as daily (README Limitations); a
  one-line check that the largest intraday spread moves do not cluster on roll dates
  will be reported, mirroring the daily check.

## Methods — everything re-derived per frequency

Reusing daily-calibrated constants at intraday frequency would be a bug, not a
convenience (this is exactly what the README's original descope note warned against).
Per frequency, from fit windows only:

- OU half-life re-estimated in BARS at that frequency; rolling z-score window set from it.
- Walk-forward fit/test windows re-sized in bars using the same half-life multiples as
  daily (fit ~10 half-lives, test ~5), subject to data availability.
- Kalman R re-estimated from that frequency's own fit-window spread variance; Q swept
  (one 1-D sweep at hourly only) rather than assumed transferable from daily.
- Block-bootstrap block length re-set to the average holding period in bars at that
  frequency.
- Entry/exit thresholds unchanged (z = +/-2.0 / 0.0) — held fixed across frequencies to
  avoid a new degree of freedom.

## Cost model (fixed in advance)

OHLCV bars contain no bid-ask; costs are therefore stated assumptions, stress-tested:

- Baseline half-spread assumptions per leg: ES ~0.4 bps of notional (1 tick = 0.25 pts
  on an index near 6,000), NQ ~0.1 bps (1 tick = 0.25 pts on an index near 25,000).
- Charged per unit of spread traded, same convention as daily (README Limitations),
  with the per-leg equivalence stated alongside.
- Stress grid: 0.5, 1, 2, 5, 10 bps one-way per spread unit, identical to daily, so the
  edge-vs-frequency comparison is apples-to-apples.
- Slippage beyond the half-spread is NOT modelled; this is a stated limitation, not an
  implicit assumption of perfect fills.

## Pre-registered outcomes and what will be reported

1. Null at all frequencies, gross and net: reported as the headline — the phenomenon is
   not detectable even where the test has power and at the claim's native timeframe.
   This is the strongest possible version of the daily null.
2. Gross-significant but net-of-cost negative: reported as "statistically real but not
   tradeable" — the classic decomposition the retail version conflates, with the
   turnover x cost mechanism quantified.
3. Net-positive and significant: treated with maximum suspicion given the daily null —
   reported alongside explicit multiple-testing accounting (frequencies x estimators x
   pairs now tested) and NOT promoted to a headline claim without surviving it.

Ruled out in advance, regardless of outcome: retuning thresholds after seeing intraday
results; switching session conventions, pairs, or cost assumptions post hoc; reporting
only the frequency that looks best. The one legitimate reason to deviate from this
protocol is discovering a genuine pipeline error — which, per CORRECTIONS.md precedent,
gets its own documented before/after entry.

## Data stop-loss

Matched ES intraday bars must be sourced to pair with the available NQ minute data.
Decision rule, fixed now: if matched 5-minute-or-finer ES data cannot be sourced,
fall back to hourly-only (still a valid power test); if no usable intraday ES data
exists at all, this protocol is closed out with a note and the daily descope stands.
Hard deadline for a go/no-go on data: within one week of this commit.
