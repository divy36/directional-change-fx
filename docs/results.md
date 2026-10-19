# Validation results

Local replay: 19 October 2026. Four datasets, 5,215,580 retained ticks, 4,201 closed positions across the four scales. Fixed one-way cost: 0.2 pip for EURUSD, 0.4 pip for EURGBP.

| Dataset | Trades | Net return | Original realized-only drawdown | Corrected liquidation drawdown |
| --- | ---: | ---: | ---: | ---: |
| EURUSD October 2025 | 1,495 | -0.9204% | -1.0525% | -1.1058% |
| EURUSD November 2025 | 976 | -0.6729% | -0.7423% | -0.7715% |
| EURUSD December 2025 | 967 | -0.7200% | -0.7340% | -0.7631% |
| EURGBP February 2026 | 763 | -0.8833% | -0.9169% | -0.9123% |

Final returns agree with the original notebook to within 1e-10 percentage points. Updated drawdown may increase or decrease: the old combined series mixed realized balances while ignoring offsetting open positions in other scales.

The old loader discarded 1,494 same-millisecond ticks in October. Retaining them changes neither trade count nor final return in this sample. All other datasets contain no duplicate timestamps; all four have zero rejected rows.

All samples are negative after costs. These are historical research samples, not an independent evaluation of profitability. Sharpe is short-sample descriptive output, with source-clock day and annualization limitations explained in [methodology](methodology.md).

## Reproduce

```bash
python scripts/validate_local_data.py /path/to/HFFCW2 --output results
```

The script runs both timestamp policies, checks portfolio ledger reconciliation, and writes aggregate metrics and daily equity. `results/validation.csv` includes input SHA-256 hashes and row counts. `results/original_summary.csv` preserves the earlier notebook replay for comparison. Vendor tick files must be supplied locally.

The test suite covers hand-calculated long/short P&L, costs, open equity, quantity-weighted entries, inventory sizing across gaps, causal prefixes, multiscale reconciliation, invalid input, no-trade samples and daily metrics. CI runs the tests and synthetic demo on Python 3.11 and 3.12.

An additional 30 comparisons (10 seeded random paths × 3 strategy variants) matched the original notebook’s trade counts and final returns. Tests run locally with Python 3.9.6, NumPy 2.0.2 and pandas 2.3.3.

To regenerate the chart: `pip install -e '.[plots]'`, then `python scripts/plot_results.py`.
