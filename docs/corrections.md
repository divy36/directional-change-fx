# Corrections and changes

Compared with `HFF_Coursework_II_Final_FIXED.ipynb`. Original files remain unchanged.

## Correctness fixes

1. **Open-position equity:** mark every tick, including reserved round-trip costs. Previously equity changed only on closes, missing open-position risk.
2. **Daily Sharpe:** calculate returns from daily account equity. Previously trade percentages were summed by entry date, excluded no-trade days, and ignored portfolio weights. Undefined values are now null.
3. **Portfolio ledger:** add weighted monetary P&L contributions and chronological trade ordering. Raw per-scale return percentages must not be summed as portfolio returns.
4. **Single-event samples:** remove the baseline/Alpha requirement for at least two future DC events. A first trend can trade and be liquidated at the end without a later reversal.
5. **Inventory sizing:** recalculate sizing after each tranche, including several levels crossed on one tick. Previously all same-tick entries used the inventory before that tick.
6. **Entry cost basis:** use quantity-weighted entry prices, replacing an unweighted mean that misrepresented multi-entry positions.
7. **Timestamp duplicates:** retain distinct same-millisecond quotes in stable source order. The old loader silently discarded all but the first. An explicit legacy comparison option remains.
8. **Data validity:** reject/count malformed timestamps and non-finite or invalid quotes; fail clearly if no valid data remains.
9. **Parameter and sequence validation:** check threshold ranges, increasing OSV levels, nonnegative costs, positive sizes/prices, aligned chronological timestamps, and nonempty scale lists.
10. **Scale identity:** use numeric IDs so rounded threshold labels cannot overwrite another scale's result.
11. **Empty/no-trade handling:** return consistent ledger columns and metrics for empty, flat or one-tick samples. Drawdown includes starting capital.
12. **Final-close labeling:** replace misleading `MTM` trade labels with `End liquidation`; actual mark-to-market now runs throughout the sample.
13. **Account exhaustion:** stop explicitly if configured exposure causes nonpositive equity instead of continuing to trade an invalid account.

## Clarifications and packaging

14. Document that the default two-entry strategy never activates reduced entry sizing, although inventory-adjusted exit thresholds do activate.
15. Rename ambiguous `spread` to `one_way_cost`; state price units, same-tick execution, fixed initial scale allocations, source-clock dates and 252-day Sharpe convention.
16. Extract data, events, execution/accounting, metrics and CLI into reusable modules; share one online engine across baseline, Alpha and inventory-aware variants.
17. Remove notebook-only plotting boilerplate, long cell commentary, hard-coded personal paths, global warning suppression and execution-order dependencies.
18. Add deterministic tests, a seeded demo, replay script, data hashes, aggregate results and Python 3.11/3.12 CI. No AUTHORS.md, vendor ticks or coursework attachments.

The four original scale pairs, overshoot levels, fixed-start bootstrap, cost assumptions and capital fractions are preserved. The strategy has not been tuned to improve these results.

19. **Scaling diagnostics:** retain zero overshoots and zero overshoot durations, and pair each overshoot with its following DC leg. The notebook filtered zeros out and compared differently selected duration samples. Report completed legs explicitly; unfinished final overshoots are excluded.
