"""Run a reproducible demo or local HistData backtest."""

import argparse
import json
from pathlib import Path

from .backtest import Config, run_engine, run_strategy
from .data import demo_ticks, load_ticks
from .metrics import daily_equity, performance


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--input", type=Path)
    source.add_argument("--demo", action="store_true")
    parser.add_argument(
        "--strategy", choices=["engine", "alpha", "coastline"], default="engine"
    )
    parser.add_argument(
        "--one-way-cost",
        type=float,
        default=0.00002,
        help="Absolute price units per side; 0.00002 = 0.2 pip for EURUSD",
    )
    parser.add_argument(
        "--reverse",
        action="store_true",
        help="Fade detector signals while preserving their timing and thresholds",
    )
    parser.add_argument(
        "--threshold-multiplier",
        type=float,
        default=1.0,
        help="Multiply all configured directional-change thresholds",
    )
    parser.add_argument(
        "--osv-levels",
        type=float,
        nargs="+",
        help="Replace the strategy's default overshoot entry levels",
    )
    parser.add_argument(
        "--no-inventory-adjustment",
        action="store_true",
        help="Disable inventory-based threshold and sizing adjustments",
    )
    parser.add_argument(
        "--deduplicate",
        action="store_true",
        help="Keep first tick per timestamp for legacy comparisons",
    )
    parser.add_argument("--output", type=Path, default=Path("output"))
    args = parser.parse_args()
    if args.demo:
        ticks, audit = demo_ticks(), {"source": "seeded synthetic demo"}
    else:
        ticks, audit = load_ticks(args.input, args.deduplicate)
    if args.strategy == "engine":
        selected_osv_levels = tuple(args.osv_levels or (0.5, 1.0))
        inventory_adjustment = not args.no_inventory_adjustment
    else:
        selected_osv_levels = tuple(
            args.osv_levels
            if args.osv_levels is not None
            else ((1.0, 2.0) if args.strategy == "coastline" else (0.5, 1.0))
        )
        inventory_adjustment = False
    if args.strategy == "engine":
        result, _ = run_engine(
            ticks.mid.to_numpy(),
            ticks.index,
            one_way_cost=args.one_way_cost,
            execution_sign=-1 if args.reverse else 1,
            threshold_multiplier=args.threshold_multiplier,
            osv_levels=selected_osv_levels,
            inventory_adjustment=inventory_adjustment,
        )
    else:
        config = Config(
            theta_up=0.001 * args.threshold_multiplier,
            theta_down=(0.001 if args.strategy == "coastline" else 0.0008)
            * args.threshold_multiplier,
            osv_levels=selected_osv_levels,
            inventory_adjustment=inventory_adjustment,
            one_way_cost=args.one_way_cost,
            execution_sign=-1 if args.reverse else 1,
        )
        result = run_strategy(ticks.mid.to_numpy(), ticks.index, config)
    args.output.mkdir(parents=True, exist_ok=True)
    result.trades.to_csv(args.output / "trades.csv", index=False)
    daily_equity(result.equity, ticks.index).to_csv(
        args.output / "daily_equity.csv", index_label="date"
    )
    report = {
        "strategy": args.strategy,
        "one_way_cost": args.one_way_cost,
        "reverse": args.reverse,
        "threshold_multiplier": args.threshold_multiplier,
        "osv_levels": selected_osv_levels,
        "inventory_adjustment": inventory_adjustment,
        "data_audit": audit,
        **performance(result, ticks.index),
    }
    (args.output / "summary.json").write_text(
        json.dumps(report, indent=2, allow_nan=False) + "\n"
    )
    print(json.dumps(report, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
