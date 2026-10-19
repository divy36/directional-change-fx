"""Plot daily account equity from the saved validation results."""

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=Path("results"))
    args = parser.parse_args()
    fig, axes = plt.subplots(2, 2, figsize=(10, 6), constrained_layout=True)
    for ax, path in zip(axes.flat, sorted(args.results.glob("*_daily.csv"))):
        daily = pd.read_csv(path, parse_dates=["date"])
        ax.plot(daily.date, (daily.equity - 1) * 100, color="#2563eb", linewidth=1.8)
        ax.axhline(0, color="#64748b", linewidth=0.7)
        ax.set_title(path.stem.replace("_daily", ""))
        ax.set_ylabel("Net return (%)")
        ax.tick_params(axis="x", rotation=20, labelsize=8)
        ax.grid(alpha=0.2)
    fig.suptitle("Alpha Coastline Trader · daily liquidation equity", fontsize=15)
    fig.savefig(args.results / "equity.png", dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    main()
