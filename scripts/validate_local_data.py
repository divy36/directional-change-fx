"""Replay the four research datasets without distributing vendor tick data."""

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd

from dc_fx.backtest import run_engine
from dc_fx.data import load_ticks
from dc_fx.metrics import daily_equity, performance

DATASETS = [
    (
        "EURUSD-202510",
        "HISTDATA_COM_ASCII_EURUSD_T202510/DAT_ASCII_EURUSD_T_202510.csv",
        0.00002,
    ),
    (
        "EURUSD-202511",
        "HISTDATA_COM_ASCII_EURUSD_T202511/DAT_ASCII_EURUSD_T_202511.csv",
        0.00002,
    ),
    (
        "EURUSD-202512",
        "HISTDATA_COM_ASCII_EURUSD_T202512/DAT_ASCII_EURUSD_T_202512.csv",
        0.00002,
    ),
    ("EURGBP-202602", "DAT_ASCII_EURGBP_T_202602.csv", 0.00004),
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("data_root", type=Path)
    parser.add_argument("--output", type=Path, default=Path("results"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    rows = []
    for name, filename, cost in DATASETS:
        path = args.data_root / filename
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        for dedup in (True, False):
            ticks, audit = load_ticks(path, deduplicate=dedup)
            result, _ = run_engine(ticks.mid.to_numpy(), ticks.index, one_way_cost=cost)
            row = {
                "dataset": name,
                "one_way_cost": cost,
                "sha256": digest,
                **audit,
                **performance(result, ticks.index),
            }
            assert (
                abs(result.trades.portfolio_pnl.sum() - (result.equity[-1] - 1)) < 1e-10
            )
            rows.append(row)
            pd.DataFrame(rows).to_csv(args.output / "validation.csv", index=False)
            if not dedup:
                daily_equity(result.equity, ticks.index).to_csv(
                    args.output / f"{name}_daily.csv", index_label="date"
                )
            print(json.dumps(row, allow_nan=False), flush=True)


if __name__ == "__main__":
    main()
