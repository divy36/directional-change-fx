# Methodology

## Strategy

- Detect the first directional change relative to the initial price; subsequent changes use the running trend extreme. Events use only prices seen so far.
- Baseline: symmetric 0.10% thresholds; enter at overshoot multiples 1 and 2.
- Alpha: 0.10% up / 0.08% down; enter at overshoot multiples 0.5 and 1.
- Engine: four independent Alpha accounts with threshold pairs (0.05%, 0.04%), (0.10%, 0.08%), (0.15%, 0.12%), (0.25%, 0.20%). Each starts with one quarter of total capital; no periodic rebalancing.
- Each tranche allocates 25% of its account's capital at the start of that position. Close on an opposite directional change or at the final tick.

## Inventory adjustment

Inventory is signed allocated capital fraction, not currency units. At absolute inventory 0.5, divide the next entry size by 2 and skew reversal thresholds by 1.5. At 1.0, divide size by 4 and skew thresholds by 2. A long inventory lowers the downward exit threshold; a short inventory lowers the upward exit threshold.

Sizing is recalculated after every entry, including multiple levels crossed on one tick. Default settings allow only two 0.25 entries: threshold adjustment is active at 0.5, but reduced entry sizing is never reached for a third entry. OSV thresholds remain the base thresholds, as in the original model.

## Accounting and execution

For capital C, tranche fraction s, entry price e and direction d (+1 or -1), quantity q = C × s / e. At mark price p, net liquidation P&L is d × q × (p − e) − 2 × q × c, where c is the fixed one-way cost in absolute price units. Both entry and estimated exit costs are reserved immediately. Account equity includes open P&L on every tick. Capital compounds when positions close.

Trade `pnl` and `cost` are amounts in a subaccount initially worth 1. `pnl_pct` is relative to that trade's starting subaccount capital. Engine `portfolio_pnl` multiplies the amount by the fixed initial capital weight. Its sum equals final portfolio equity minus 1. Average entry price is weighted by currency quantity.

Fills occur at the signal tick's mid price; gaps fill all crossed levels at that observed price. The fixed cost represents total assumed one-way friction, so the observed bid/ask spread is not charged again. There is no latency, queue, financing, market impact, margin or broker execution model. Exposure settings that exhaust an account raise an error.

## Data and statistics

Input rows are `YYYYMMDD HHMMSSmmm,bid,ask,volume`. Invalid timestamps, non-finite quotes, nonpositive bids and crossed quotes are excluded and counted. Stable sorting preserves source order for identical timestamps. Duplicate timestamps are retained by default; `--deduplicate` reproduces the old first-tick policy.

Timestamps stay timezone-naive in the source clock. No timezone or FX trading-calendar conversion is inferred. Weekend records are retained. Daily returns use the last equity on each date containing ticks, including dates without trades; missing dates are not fabricated. The first date starts from capital 1. Sharpe uses these daily returns, sample standard deviation, zero risk-free rate and a stated 252-day annualization convention. It is descriptive, especially for short samples and source-clock Sunday records. Undefined Sharpe is null.

Drawdown uses tick-level liquidation equity with initial capital 1 included in the high-water mark. End liquidation is a forced close, not a new observation of open-position risk.

## Research helpers

`dc_fx.research.scaling_diagnostics(prices, timestamps, thresholds)` reports event counts, mean completed overshoot/threshold ratios, and paired OS/DC duration ratios in tick counts. Zero overshoots are included; incomplete final legs are excluded. These are empirical diagnostics, not proof of universal scaling laws. `baseline_sensitivity` replays symmetric baseline thresholds using the corrected accounting and metrics.

## Reversed execution and experimental settings

`execution_sign=-1` (CLI `--reverse`) reverses executed LONG/SHORT labels and
price-movement P&L while costs remain expenses. Detector direction, overshoot
measurement, exit timing, and signal-side inventory stay unchanged. Consequently,
reverse execution does not mean feeding actual reversed inventory back into the
original threshold adjustment. The researched candidate disables that adjustment.
Each account compounds its own net returns; reversed quantities can differ from
baseline quantities after the first completed position.

`--threshold-multiplier`, `--osv-levels`, and `--no-inventory-adjustment` expose
experimental settings without changing defaults. The reversal research candidate
uses multiplier 2, levels 1 and 2, and no inventory adjustment. Tranche allocation
remains 25% of each subaccount's capital at the position start, at most two
tranches. This is an entry-budget limit, not a hard mark-to-market leverage limit.
See [reversal research](reversal-research.md) for results and execution stresses.
