# Kalman-Filtered Dynamic Hedge Ratio Pairs Trading

Testing whether "SMT divergence" — a retail trading claim that correlated index
futures diverging predicts a reversal — is a real, tradeable statistical phenomenon
once formalised rigorously, rather than an eyeballed chart pattern.

## Result

**No.** Across three hedge-ratio estimators (static OLS, rolling OLS, Kalman filter)
and three cointegrated index-future pairs (ES/NQ, ES/YM, NQ/YM), tested walk-forward
with transaction costs, no result reaches conventional statistical significance. The
closest is a Kalman-filtered spread on ES/NQ (Sharpe 0.28, bootstrap p≈0.25) — a
positive point estimate, not a significant one.

This is a corrected result. An external code review found four real bugs in the
pipeline after an earlier version of this analysis had reported a modest,
borderline-significant edge (p≈0.08). Fixing them changed the headline finding.
`CORRECTIONS.md` records the pre-fix numbers verbatim, a pre-registered statement
(written before any fix was applied) of what would be reported if the edge
disappeared, and a fix-by-fix attribution of how each bug moved the result.

## Method

1. **Cointegration** (`cointegration.py`, `stationary.py`) — confirm ES and NQ are
   I(1) (Augmented Dickey-Fuller), then test whether `log(NQ) = alpha + beta*log(ES)
   + spread` has a stationary residual, using Engle-Granger/MacKinnon critical
   values (not plain ADF critical values — residuals from an estimated regression
   need the more conservative test).
2. **Mean-reversion speed** (`ou_model.py`) — fit an Ornstein-Uhlenbeck process to the
   spread to get a half-life, which sets the rolling z-score window rather than
   picking one arbitrarily.
3. **Hedge ratio estimation** — three methods, compared head-to-head:
   - Static OLS: one beta, fit once, held fixed.
   - Rolling OLS (`walk_forward.py`): beta re-estimated from scratch each day on a
     trailing 60-day window.
   - Kalman filter (`kalman_filter.py`): beta as a hidden state in a linear
     state-space model, updated via the standard predict/update recursion.
4. **Walk-forward validation** (`walk_forward.py`) — parameters estimated on a
   trailing fit window (700 days), traded only on the following out-of-sample test
   window (350 days), rolled forward. A single fit-and-test on the full sample would
   be look-ahead bias.
5. **Significance testing** (`significance.py`) — block bootstrap (not a naive
   t-test, since positions are held for multiple days and returns are
   autocorrelated) to get a confidence interval and a p-value against the null of no
   edge.
6. **Parameter sensitivity** (`sensitivity.py`) — sweep the two hand-picked
   hyperparameters (Kalman process noise, entry threshold) across a range of values,
   reporting how the result moves, rather than optimising over them (which would
   silently turn the out-of-sample test data into training data).
7. **Multi-pair extension** (`multi_pair_screen.py`) — repeat the cointegration
   screen across ES, NQ, YM, and RTY; carry forward only pairs that pass, to test
   whether any result generalises beyond ES/NQ.

## Data

Daily OHLCV for ES, NQ, YM, and RTY continuous front-month futures, 2020-01-02 to
2026-06-25 (1,631 trading days), pulled from Yahoo's chart API (`fetch_data.py`) and
committed under `data/raw/` for reproducibility — Yahoo's API revises history, so
re-fetching would not reproduce the exact numbers below.

## Results

**Cointegration screen** (Engle-Granger, direction fixed in advance: broader index
always the regressor):

| Pair | p-value | Cointegrated (p&lt;0.10)? |
|---|---|---|
| ES/NQ | 0.088 | Yes (weakest of the three) |
| ES/YM | 0.001 | Yes |
| NQ/YM | 0.004 | Yes |
| ES/RTY | 0.456 | No |
| RTY/NQ | 0.329 | No |
| RTY/YM | 0.602 | No |

RTY (Russell 2000) is dropped — a sustained small-cap underperformance regime over
this sample, not a mean-reverting relationship. ES/NQ/YM carried forward.

**Walk-forward, out-of-sample, after transaction costs:**

| Pair | Method | Sharpe | p-value (H0: no edge) |
|---|---|---|---|
| ES/NQ | Static OLS | -0.19 | 0.738 |
| ES/NQ | Rolling OLS | 0.63 | 0.114 |
| ES/NQ | Kalman | 0.28 | 0.249 |
| ES/YM | Static OLS | -0.37 | 0.915 |
| ES/YM | Rolling OLS | 1.36 | 0.002 |
| ES/YM | Kalman | -0.46 | 0.896 |
| NQ/YM | Static OLS | 0.01 | 0.582 |
| NQ/YM | Rolling OLS | -0.98 | 0.949 |
| NQ/YM | Kalman | -0.89 | 0.975 |

Rolling OLS's apparent significance on ES/YM (p=0.002) does not replicate on NQ/YM
(strongly negative instead) — the signature of a high-variance estimator getting
lucky or unlucky against a specific realised price path, not a real effect. Kalman
shows no significant edge on any pair.

## Honest conclusion

The retail claim is not supported. A Kalman-filtered dynamic hedge ratio does not
produce a statistically significant mean-reversion edge on any of the three
cointegrated pairs tested, at daily frequency, once look-ahead bias, proper
significance testing, and pipeline bugs are all accounted for. The full reasoning,
including the multi-pair generalisation test and the parameter sensitivity analysis,
is in `notebooks/pairs_trading_analysis.ipynb` (fully self-contained, executes
end-to-end).

## Limitations

- Only 3 walk-forward folds (~830 out-of-sample days) — a real constraint from the
  spread's ~68-day half-life relative to the available sample, not a design choice.
- Daily frequency only. SMT divergence is, in its retail form, an intraday signal;
  testing it at that frequency was considered and explicitly descoped, not left
  ambiguous — it needs a different data source (this project's daily OHLCV source has
  no multi-year intraday history), its own half-life re-derivation, and realistic
  bid-ask/slippage cost modelling, rather than reusing the daily pipeline's constants.
- No purged/embargoed cross-validation or deflated Sharpe ratio correction for
  multiple testing (three estimators, three pairs) — named as the more rigorous
  approach in `LEARNING_NOTES.md`, not implemented, given the small number of
  genuinely independent pairs available.

## Reproducing this

```
pip install -r requirements.txt
python src/stationary.py          # I(1) checks
python src/cointegration.py       # Engle-Granger test, ES/NQ
python src/ou_model.py            # half-life
python src/backtest.py            # naive full-sample backtest, both hedge-ratio methods
python src/walk_forward.py        # walk-forward validation
python src/significance.py        # block-bootstrap significance
python src/sensitivity.py         # parameter sensitivity sweep (several minutes)
python src/multi_pair_screen.py   # cointegration screen across all 4 instruments
python src/multi_pair_backtest.py # walk-forward on ES/YM, NQ/YM
```

Or open `notebooks/pairs_trading_analysis.ipynb` directly — it runs the same `src/`
code and contains the full write-up.
