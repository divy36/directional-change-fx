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
        result, _ = run_engine(
            ticks.mid.to_numpy(), ticks.index, one_way_cost=args.one_way_cost
        )
    else:
        config = Config(
            theta_up=0.001,
            theta_down=0.001 if args.strategy == "coastline" else 0.0008,
            osv_levels=(1.0, 2.0) if args.strategy == "coastline" else (0.5, 1.0),
            inventory_adjustment=False,
            one_way_cost=args.one_way_cost,
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
        "data_audit": audit,
        **performance(result, ticks.index),
    }
    (args.output / "summary.json").write_text(
        json.dumps(report, indent=2, allow_nan=False) + "\n"
    )
    print(json.dumps(report, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
