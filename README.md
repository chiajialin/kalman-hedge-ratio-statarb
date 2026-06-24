# Project: Kalman-Filtered Dynamic Statistical Arbitrage — Testing SMT Divergence on ES/NQ

## Status: Anchor project (primary). Second project (Regime-Gated VRP Harvesting) sits behind it, sharing infrastructure.

---

## 1. Origin & Motivation (the story)

This project began from a real encounter with retail day-trading content, specifically a technique called **"SMT divergence" (Smart Money Technique divergence)**. The retail claim: when two correlated assets — classically ES (S&P 500 E-mini) and NQ (Nasdaq-100 E-mini) futures, or FX pairs like EUR/USD and GBP/USD — diverge, with one making a higher high while the other fails to (makes a lower high), this divergence signals the move is weak and likely to reverse. The retail narrative attributes this to "smart money" revealing its hand through the lagging asset.

The motivating question is a researcher's instinct: **is this a real, tradeable phenomenon when formalised mathematically, or is it just post-hoc chart-reading?**

Stripped of the narrative, SMT divergence is a claim about **two correlated assets temporarily decoupling, followed by reversion** — which is, almost exactly, the spread-divergence-and-reversion idea that statistical arbitrage formalises. The retail trader eyeballs "one made a higher high, one didn't"; the quant writes down the spread between the two assets and asks: when it stretches abnormally wide, does it revert? Same underlying phenomenon — one expressed as chart-pattern intuition, the other as a testable statistical statement.

This origin matters because it answers "why did you do this project?" with a genuine, compelling answer rather than a manufactured one: *"I encountered a specific retail claim and wanted to test it rigorously."*

### Honest caveats baked into the framing (these are strengths, not weaknesses)
- SMT is usually framed on price **levels** (highs and lows); stat-arb works on the **spread**. Translating "higher high vs lower high" into a precise spread definition is a real modelling choice that must be made and defended.
- Timeframe matters enormously. SMT is an intraday, often sub-hourly, discretionary signal. Whether it survives as a systematic rule — with costs, at whatever frequency data permits — is the open question.
- The retail version has no statistical test of significance. This project's entire upgrade is replacing "I can see it on the chart" with "here's whether it's distinguishable from noise."
- Much SMT-divergence content is genuinely junk — post-hoc pattern-matching on cherry-picked charts, no out-of-sample testing, survivorship in the examples shown. The project goes in prepared for the real result to be "weaker than advertised, or not surviving costs." That is not a failed project — that IS the project. The value is in the rigorous test, whichever way it falls.

---

## 2. The Research Question

> "Retail traders use SMT divergence as a discretionary signal. Is the phenomenon it points at — correlated-index divergence and reversion — real and tradeable when you formalise it mathematically, and does a proper state-space treatment of the divergence beat the eyeball version? And critically: at what frequency and cost level does the edge survive or break down?"

---

## 3. Why the Kalman Filter (precise framing)

The Kalman filter is **not itself an arbitrage technique**. It is a general **state-space estimation tool** that tracks a hidden quantity that changes over time from noisy observations (it was originally built for problems like tracking a rocket's position from noisy radar). It has no inherent connection to trading.

The connection here is specific: in pairs trading, the **hedge ratio** between two cointegrated assets is the hidden quantity that drifts over time, and the prices are the noisy observations. The Kalman filter tracks that drifting hedge ratio.

Correct framing: *not* "Kalman is an arbitrage method," but "the hedge ratio in stat-arb is exactly the kind of slowly-evolving hidden state a Kalman filter is built to estimate."

The accurate one-liner: **"I use a Kalman filter to track a time-varying hedge ratio between cointegrated assets, and trade mean-reversion on the resulting spread."**

### Two precision points (interview-critical)
- **"Statistical arbitrage" is not true arbitrage.** True arbitrage is risk-free — simultaneous offsetting trades locking in guaranteed profit. Stat-arb is a *statistical bet on mean reversion*: the spread might not revert (the relationship can break permanently — cointegration fails out of sample, a company gets acquired, etc.). Calling it "arbitrage" is industry convention, not literal. Do not oversell it as riskless.
- **The Kalman filter is the *estimation* layer, not the strategy.** The strategy is mean-reversion trading on the spread. The filter's job is to give a better, adaptive estimate of the hedge ratio (and hence a cleaner spread) than static OLS. The edge, if any, comes from the adaptivity being worth its cost — which must be *proven* against simpler baselines, not assumed.

### Why Kalman is necessary, not decorative
The ES/NQ relationship genuinely drifts (e.g. with sector rotation between tech-heavy NQ and broader ES), so a static hedge ratio would mis-measure divergence over time. A time-varying estimate is required to define "abnormal divergence" correctly. This is also where a biomedical signal-processing background does work a CS-background applicant cannot easily replicate — state-space estimation is signal-processing-native territory (directly tied to the Parkinson's signal-processing work and the Statistical Signal Processing module).

---

## 4. The Pair & Data

**Pair:** ES (S&P 500 E-mini) and NQ (Nasdaq-100 E-mini) continuous front-month futures — the classic SMT pair. Both indices are tech-heavy and highly correlated, which is *why* SMT traders pair them, and also why divergences are usually small and short-lived (to be quantified).

**Data availability (as established):**
- **Free, research-grade minute data exists** — e.g. a Kaggle dataset of ~1.05 million rows of NQ 1-minute OHLCV bars covering Dec 2022–Dec 2025, including regular and extended hours, explicitly for research/educational use, spanning multiple regimes (trends, vol spikes, consolidation). A matched ES dataset should be sourced from the same/similar provider.
- **Daily data** is trivially accessible free (Investing.com, EODData, yfinance-style sources).
- Most paid providers (FirstRate, Portara, Barchart Premier) gate intraday behind subscriptions; the free path is **Kaggle-type minute data + free daily as fallback.**

**Data caveat:** OHLCV bars hide execution detail — there is no bid-ask or order-book information. This limits how literally the intraday microstructure can be modelled, which is itself part of the honest story.

---

## 5. Two-Phase Structure

The chosen approach is **"phenomenon first cleanly, then push to intraday and show where it breaks down."** This is structurally the strongest version because the *breakdown is the finding*: a strategy that works at daily but decays toward intraday isolates the exact point where costs, microstructure, and execution friction consume the edge. That demonstrates an edge is not binary but frequency- and cost-dependent — exactly how a real desk evaluates tradeability. The two-phase structure is the mechanism that generates the project's single most impressive insight.

**Discipline note (named risk):** "Do both" is the version most exposed to scope creep. The failure mode is that Phase 1 never reaches a defensible standard because Phase 2 is shinier. **Phase 1 must be genuinely interview-ready before Phase 2 begins** — a complete, defensible result on its own, such that if time runs out, there is still a finished project. Phase 2 is the upgrade, not the goal.

### Phase 1: The phenomenon, tested cleanly (daily, then hourly)

**Step 1 — Data and pair.** ES and NQ continuous front-month. Start daily (trivially accessible), then hourly.

**Step 2 — Establish the relationship (stats showcase).** Test for cointegration (Engle-Granger). Be explicit about correlation vs cointegration: ES and NQ are strongly *correlated* in returns, but a stable long-run *level* relationship is needed to define a tradeable spread. Report honestly whether they are genuinely cointegrated over the sample or only locally — the relationship between two equity indices can shift with sector rotation (tech-heavy NQ vs broader ES).

**Step 3 — The Kalman core (the moat).** Estimate a *time-varying* hedge ratio between ES and NQ via a Kalman filter, rather than a static OLS regression. The hedge ratio is the hidden state; prices are the noisy observations; the filter tracks how the relationship drifts.

**Step 4 — Define divergence precisely (the key modelling decision).** This replaces the eyeball. SMT's "higher high in one, not the other" becomes: *the Kalman-filtered spread (actual minus predicted relationship) stretches beyond X standard deviations.* This translates a discretionary chart pattern into a falsifiable statistical statement. Defending this translation — why this definition faithfully captures what SMT traders see — is a high-value interview moment.

**Step 5 — Test reversion and significance (stats).** When divergence occurs, does the spread revert? Measure the reversion and — critically — test whether it is distinguishable from noise (the retail version never does this). Report effect size, not just "it reverts sometimes."

**Step 6 — Trade and evaluate.** Trade the filtered residual with entry/exit thresholds, transaction costs, walk-forward validation. Benchmark Kalman against static OLS and rolling-window regression — proving the state-space sophistication earns its keep (and honestly reporting if it sometimes does not).

### Phase 2: Push to intraday, find where it breaks

**Step 7 — Go to 5-minute, then 1-minute** using the Kaggle-type minute data. Re-run the whole pipeline at each frequency.

**Step 8 — The microstructure reckoning.** As frequency increases, layer in increasingly realistic frictions: bid-ask spread assumptions, slippage, and the fact that OHLCV bars hide execution detail. Show how the apparent edge changes as costs bite.

**Step 9 — The headline finding.** Plot edge (risk-adjusted return after costs) against frequency. Likely shape: a phenomenon that looks real and significant at daily/hourly, then decays — possibly vanishing — at minute frequency once realistic costs apply. *That curve is the project's signature result.* It answers "is SMT real?" with the honest, sophisticated answer: the divergence-reversion phenomenon is statistically real, but whether it is *tradeable* depends entirely on frequency and costs — and at the timeframe retail traders actually use it, the edge is largely consumed by frictions.

---

## 6. How the Components Map to the Three Required Skill Areas

- **Machine Learning / comparison discipline:** benchmarking Kalman dynamic hedge ratio against static OLS and rolling-window regression on identical data, costs, and evaluation.
- **Data Analytics:** pair selection, spread construction, frequency sweeps, P&L curves, edge-vs-frequency analysis.
- **Statistics:** cointegration testing (Engle-Granger), correlation vs cointegration distinction, time-varying state-space estimation (Kalman), significance testing of reversion, walk-forward validation against non-stationarity.

---

## 7. Defensibility — Three Levels Deep

- *Why Kalman?* Because the relationship drifts; static mis-measures divergence. → *Why does drift matter?* Sector rotation between tech-heavy NQ and broader ES. → *Why state-space over rolling window?* Benchmarked exactly that and report the answer.
- *Why these stats?* Cointegration defines the tradeable spread; significance testing separates signal from noise. → *Why walk-forward / out-of-sample rigour?* Non-stationarity; a single split would overstate the edge.
- *Why the frequency sweep?* Because tradeability is not binary — it is where the real insight lives (the edge-vs-frequency breakdown curve).

---

## 8. Relationship to the Second Project (Regime-Gated VRP Harvesting)

This Kalman/SMT project is the **anchor** — it carries the personal origin story, the signal-processing moat, and the cleanest "this is me" narrative. The **Regime-Gated Variance Risk Premium Harvesting** project is the **second piece**, deliberately designed to **share infrastructure**: the same backtesting engine, walk-forward harness, and transaction-cost-modelling discipline built here are reused there. Build this anchor to interview-ready state first; add the VRP project if time before the October application cycle allows.

**Unifying career narrative across both projects (and the Parkinson's work):** *"I extract tradeable signal from noisy data — whether the right tool is state-space (Kalman for stat-arb) or econometric (GARCH/HMM for VRP)."* This single thread ties the biomedical signal-processing background, the SMT/Kalman project, and the VRP project into one coherent quant identity: a person who pulls signal from noise.

---

## 9. Tools & Stack

- **Python** (primary): pandas, numpy; `statsmodels` (cointegration / Engle-Granger); a Kalman implementation (`pykalman` or hand-rolled); scikit-learn for benchmark regressions; matplotlib for the edge-vs-frequency curve.
- **Data:** Kaggle-type ES/NQ 1-minute OHLCV (Dec 2022–Dec 2025); free daily data as fallback.
- **Evaluation:** walk-forward validation; risk-adjusted metrics (Sharpe, max drawdown); transaction-cost and slippage modelling.

---

## 10. Likely / Acceptable Outcomes (set expectations honestly)

The credible, impressive outcome is NOT "I found a money-printing strategy." It is most likely: *the divergence-reversion phenomenon is statistically real at lower frequencies, but the tradeable edge decays and is largely consumed by transaction costs and microstructure frictions as frequency increases toward the intraday timeframe retail SMT traders actually use.* Reporting this honestly — with the edge-vs-frequency curve as evidence — is more impressive than a fabricated positive result, and demonstrates exactly the judgment quant desks value.
