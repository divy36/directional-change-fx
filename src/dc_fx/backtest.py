"""Mid-price fills with explicit fixed one-way costs and liquidation equity."""

from dataclasses import dataclass
from typing import Tuple

import numpy as np
import pandas as pd

from .directional_change import Detector

SCALES = ((0.0005, 0.0004), (0.001, 0.0008), (0.0015, 0.0012), (0.0025, 0.002))
TRADE_COLUMNS = [
    "entry_time",
    "exit_time",
    "direction",
    "n_entries",
    "total_size",
    "avg_entry_px",
    "exit_px",
    "pnl_pct",
    "pnl",
    "cost",
    "result",
]


@dataclass(frozen=True)
class Config:
    theta_up: float = 0.0005
    theta_down: float = 0.0004
    osv_levels: Tuple[float, ...] = (0.5, 1.0)
    position_unit: float = 0.25
    one_way_cost: float = 0.00002
    inventory_adjustment: bool = True

    def __post_init__(self):
        values = [self.theta_up, self.theta_down, self.position_unit, self.one_way_cost]
        if not np.isfinite(values).all() or not (
            0 < self.theta_up < 0.5 and 0 < self.theta_down < 0.5
        ):
            raise ValueError("Finite thresholds must be between 0 and 0.5")
        if self.position_unit <= 0 or self.one_way_cost < 0:
            raise ValueError("Position unit must be positive and cost nonnegative")
        levels = np.asarray(self.osv_levels, dtype=float)
        if (
            levels.ndim != 1
            or not len(levels)
            or not np.isfinite(levels).all()
            or np.any(levels <= 0)
            or np.any(np.diff(levels) <= 0)
        ):
            raise ValueError(
                "OSV levels must be positive, finite and strictly increasing"
            )


@dataclass
class Result:
    trades: pd.DataFrame
    equity: np.ndarray


def effective_params(config, inventory):
    up, down, unit = config.theta_up, config.theta_down, config.position_unit
    if not config.inventory_adjustment or abs(inventory) < 0.5:
        return up, down, unit
    skew, divisor = (2, 4) if abs(inventory) >= 1 else (1.5, 2)
    if inventory > 0:
        up, down = up * skew, down / skew
    else:
        up, down = up / skew, down * skew
    return up, down, unit / divisor


def validate_inputs(prices, timestamps):
    prices = np.asarray(prices, dtype=float)
    times = pd.DatetimeIndex(timestamps)
    if prices.ndim != 1 or len(prices) != len(times):
        raise ValueError(
            "Prices and timestamps must be aligned one-dimensional sequences"
        )
    if not np.isfinite(prices).all() or np.any(prices <= 0):
        raise ValueError("Prices must be finite and positive")
    if times.hasnans or not times.is_monotonic_increasing:
        raise ValueError("Timestamps must be valid and nondecreasing")
    return prices, times


def run_strategy(prices, timestamps, config=None):
    config = config or Config()
    prices, times = validate_inputs(prices, timestamps)
    curve = np.ones(len(prices))
    trades = []
    if not len(prices):
        return Result(pd.DataFrame(columns=TRADE_COLUMNS), curve)
    detector = Detector(prices[0])
    capital = 1.0
    direction, anchor, next_level, inventory = 0, 0.0, 0, 0.0
    entries = []
    quantity = basis = costs = 0.0

    def close(i, reason):
        pnl = direction * (quantity * prices[i] - basis) - costs
        trades.append(
            {
                "entry_time": entries[0][2],
                "exit_time": times[i],
                "direction": "LONG" if direction == 1 else "SHORT",
                "n_entries": len(entries),
                "total_size": sum(e[1] for e in entries),
                "avg_entry_px": basis / quantity,
                "exit_px": prices[i],
                "pnl_pct": pnl / capital * 100,
                "pnl": pnl,
                "cost": costs,
                "result": reason,
            }
        )
        return capital + pnl

    for i, price in enumerate(prices):
        up, down, _ = effective_params(config, inventory)
        event = detector.update(price, up, down)
        if entries and event == -direction:
            capital = close(i, "DC exit")
            entries = []
            quantity = basis = costs = inventory = 0.0
            direction = 0
        # Reset a flat watcher before entries: an opposite event cancels its signal.
        if event and not entries:
            direction, anchor, next_level = event, price, 0
        if direction and next_level < len(config.osv_levels):
            theta = config.theta_up if direction == 1 else config.theta_down
            osv = direction * (price - anchor) / (anchor * theta)
            while (
                next_level < len(config.osv_levels)
                and osv >= config.osv_levels[next_level]
            ):
                _, _, unit = effective_params(config, inventory)
                entries.append((price, unit, times[i]))
                units = capital * unit / price
                quantity += units
                basis += units * price
                costs += units * 2 * config.one_way_cost
                inventory += direction * unit
                next_level += 1
        curve[i] = capital + direction * (quantity * price - basis) - costs
        if curve[i] <= 0:
            raise ValueError(
                "Account exhausted; reduce exposure before running this configuration"
            )
    if entries:
        capital = close(len(prices) - 1, "End liquidation")
        curve[-1] = capital
    return Result(pd.DataFrame(trades, columns=TRADE_COLUMNS), curve)


def run_engine(prices, timestamps, scales=SCALES, one_way_cost=0.00002):
    prices, times = validate_inputs(prices, timestamps)
    scales = tuple(scales)
    if not scales:
        raise ValueError("At least one scale is required")
    configs = [
        Config(theta_up=u, theta_down=d, one_way_cost=one_way_cost) for u, d in scales
    ]
    equity = np.zeros(len(prices))
    frames = []
    per_scale = {}
    weight = 1 / len(scales)
    for i, config in enumerate(configs, 1):
        result = run_strategy(prices, times, config)
        per_scale[i] = result
        equity += weight * result.equity
        frame = result.trades.copy()
        frame["scale"] = i
        frame["capital_weight"] = weight
        frame["portfolio_pnl"] = frame.pnl * weight
        frames.append(frame)
    trades = pd.concat(frames, ignore_index=True)
    trades = trades.sort_values(["exit_time", "scale"], kind="stable").reset_index(
        drop=True
    )
    return Result(trades, equity), per_scale
