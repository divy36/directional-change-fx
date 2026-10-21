# Reversed DC strategy research

20 October 2026. The selected modification turns all four original development samples positive and has a positive average return on six reserved EURUSD months. It does **not** pass the predeclared robustness gate: only three of six validation months are positive under the fixed-cost model. Doubling costs makes the validation average slightly negative. This is an improved research candidate, not established live profitability.

## What changed

1. Reverse execution: sell on the original buy schedule and buy on the original sell schedule. Trading costs remain deductions.
2. Double all four directional-change threshold pairs: (0.10%, 0.08%), (0.20%, 0.16%), (0.30%, 0.24%), (0.50%, 0.40%).
3. Wait for overshoot multiples 1 and 2 instead of 0.5 and 1 before entering.
4. Disable inventory-based threshold adjustment.

The four subaccounts retain equal starting weights and two 25% entry tranches at most. No increase in tranche allocation was used to manufacture a larger return. This allocation rule is not a hard mark-to-market leverage cap. Original defaults remain unchanged; the new settings are opt-in.

These changes collectively improve the tested results. The experiment does not isolate the contribution of every individual change, and the combined candidate must not be described as the result of reversal alone.

## Original samples: development results

| Development sample | Original | Reverse only | Selected candidate | Candidate trades |
| --- | --- | --- | --- | --- |
| EURUSD-202510 | -0.9204% | -0.1082% | +0.1089% | 177 |
| EURUSD-202511 | -0.6729% | +0.0026% | +0.2250% | 116 |
| EURUSD-202512 | -0.7200% | +0.0607% | +0.3288% | 127 |
| EURGBP-202602 | -0.8833% | -0.5071% | +0.1026% | 95 |

Development mean candidate return: +0.1913% per sample; 515 closed positions across 5,215,580 ticks. Original assumed one-way costs are 0.2 pip EURUSD and 0.4 pip EURGBP. These samples were used for selection, so their profits are in-sample results.

## Frozen candidate on reserved data

| Reserved EURUSD month | Original | Reverse only | Candidate fixed costs | Candidate bid/ask + next tick |
| --- | --- | --- | --- | --- |
| 202501 | -1.4165% | -1.0028% | -0.0643% | +0.0293% |
| 202502 | -0.8678% | -0.8932% | +0.1916% | +0.1820% |
| 202503 | -1.5318% | -0.6166% | +0.6660% | +0.6657% |
| 202505 | -1.2758% | -0.9493% | -0.2172% | -0.2717% |
| 202506 | -1.3678% | -0.3654% | +0.3902% | +0.3951% |
| 202507 | -0.1579% | -1.3142% | -0.4155% | -0.3895% |

The six full-month files contain 12,702,182 retained ticks with no rejected rows. They were not used for candidate selection in this session. They precede the development months chronologically, so this is **retrospective held-out validation**, not a prospective walk-forward test. April and August are not silently included; only the six stated files were tested. Capital and signals reset at each month's start, with forced final liquidation. Monthly returns are not a continuously traded six-month account.

| Validation execution | Mean sample return | Positive months | Worst month | Worst within-month drawdown |
| --- | --- | --- | --- | --- |
| Candidate: fixed 0.4 pip/side | -0.0161% | 3/6 | -0.4972% | -0.9099% |
| Candidate: fixed 0.2 pip/side | +0.0918% | 3/6 | -0.4155% | -0.8635% |
| Candidate: observed bid/ask | +0.0684% | 3/6 | -0.4311% | -0.8747% |
| Candidate: bid/ask + next tick | +0.1018% | 4/6 | -0.3895% | -0.8552% |
| Original | -1.1029% | 0/6 | -1.5318% | -1.7015% |
| Reverse only | -0.8569% | 0/6 | -1.3142% | -1.5274% |

The original strategy and reversal alone lose in all six reserved months. The selected candidate improves average returns substantially, but January, May, and July lose under fixed costs. Its worst within-month drawdown is 0.864% at the selected tranche sizing. Fixed-cost mean return is +0.0918%; observed bid/ask mean is +0.0684%; next-tick bid/ask mean is +0.1018%. Doubled fixed-cost mean is -0.0161%.

The predeclared gate required a positive mean fixed-cost return, a positive majority of the six months, and a positive mean under delayed quote execution. The majority condition fails (3/6). We did not retune on this panel after observing the results.


## Execution stresses

Bid/ask execution charges each entry and exit half-spread around the contemporaneous mid; it does not also subtract the fixed spread assumption. Next-tick execution places each causal signal's order at the next observed quote. It is a one-observation delay, not a calibrated wall-clock latency model. Quantity sizing uses fill-tick mid, consistent with production accounting. A delayed order beyond the sample end is dropped; surviving inventory is liquidated at the last quote. An entry landing on that last quote is immediately closed and pays both half-spreads.

Observed quote execution includes quoted spreads but no additional broker commission, financing/swaps, market impact, or margin constraints. Tick data do not establish fill availability for a particular trade size. These missing expenses matter because the apparent average gain is small and the fixed-cost stress already removes it.

## Selection and verification

Three small agents implemented reversal, researched candidates, and independently audited accounting and execution. The bounded grid contained 18 configurations: threshold multipliers 1.5/2/3, overshoot sets (1,2)/(1.5,2.5)/(2,3), and inventory adjustment on/off. All use reversed execution. The ranking rule and minimum mean trade count of 100 were chosen during development, not preregistered. They favored the highest mean return among candidates positive in all four development samples with that trade count. The selected settings were frozen before validation.

Searching multiple strategies can overfit historical data; the reserved panel and full attempt log make the distinction between selection and validation explicit. See Bailey et al., [The Probability of Backtest Overfitting](https://www.davidhbailey.com/dhbpapers/backtest-prob.pdf).

The compiled search was reconciled to the production Python engine on all four selected-candidate samples: trade counts match and return, drawdown, and descriptive daily Sharpe differ by less than 1e-8. Actual reversed-engine returns match the previous ledger calculation. The independent execution replay matches production full equity curves for both execution signs and inventory settings; the first validation month's four selected scales also match production within 1e-11. The package now passes **56 tests**, including causal prefixes, bid/ask costs, delayed fills, terminal handling, custom scale settings and CLI configuration. No source tick files were modified or copied into the repository.

## Run the candidate

With the package installed, for a local EURUSD HistData CSV:

```bash
dc-fx --input /path/to/ticks.csv --reverse --threshold-multiplier 2 \
  --osv-levels 1 2 --no-inventory-adjustment --one-way-cost 0.00002 \
  --output output/reversal-candidate
```

For EURGBP use `--one-way-cost 0.00004`. To reproduce only the original-side reversal, omit the multiplier, OSV and inventory flags.

To reproduce the six-month validation and all execution stresses from the project directory:

```bash
python scripts/validate_reversal.py \
  --archive-root /path/to/histdata/monthly/archives \
  --output output/reversal-validation
```

The archive folder must contain the six `HISTDATA_COM_ASCII_EURUSD_TYYYYMM.zip` files named in `results/reversal/validation_plan.json`. Config, all 72 development result rows, production conformance, six-month results, hashes, and summary are retained in `results/reversal/`. The original search runner, frozen selection bytes, validation daily equity, and agent audits are also retained in the workspace's `outputs/dc-strategy-research/` directory.

## Decision

Keep this as the preferred experimental candidate from this search, while retaining the baseline for comparison. The backtest is profitable on average under the stated base and quote execution assumptions, but the failed robustness gate and negative doubled-cost result do not justify calling it reliably profitable. Further evidence should come from new, untouched chronological data and broker-specific execution costs, not retuning to the six months already inspected.
