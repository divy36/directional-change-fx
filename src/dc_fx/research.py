"""Descriptive scaling diagnostics and baseline threshold sensitivity."""

import numpy as np
import pandas as pd

from .backtest import Config, run_strategy, validate_inputs
from .directional_change import Detector
from .metrics import performance


def events(prices, timestamps, theta):
    prices, _ = validate_inputs(prices, timestamps)
    Config(theta_up=theta, theta_down=theta)
    rows = []
    if len(prices):
        detector = Detector(prices[0])
        for i, price in enumerate(prices):
            direction = detector.update(price, theta, theta)
            if direction:
                rows.append(
                    {
                        "index": i,
                        "direction": direction,
                        "price": price,
                        "extreme_index": detector.event_origin_index,
                    }
                )
    return rows


def scaling_diagnostics(prices, timestamps, thresholds):
    prices, times = validate_inputs(prices, timestamps)
    rows = []
    for theta in thresholds:
        ev = events(prices, times, theta)
        overshoots, os_ticks, dc_ticks = [], [], []
        for start, end in zip(ev, ev[1:]):
            extreme = end["extreme_index"]
            overshoots.append(
                start["direction"] * (prices[extreme] - start["price"]) / start["price"]
            )
            os_ticks.append(extreme - start["index"])
            dc_ticks.append(end["index"] - extreme)
        mean_os = float(np.mean(overshoots)) if overshoots else None
        rows.append(
            {
                "theta": theta,
                "events": len(ev),
                "completed_legs": len(overshoots),
                "mean_overshoot": mean_os,
                "overshoot_theta_ratio": (
                    mean_os / theta if mean_os is not None else None
                ),
                "os_dc_tick_ratio": (
                    float(np.mean(os_ticks) / np.mean(dc_ticks)) if dc_ticks else None
                ),
            }
        )
    return pd.DataFrame(
        rows,
        columns=[
            "theta",
            "events",
            "completed_legs",
            "mean_overshoot",
            "overshoot_theta_ratio",
            "os_dc_tick_ratio",
        ],
    )


def baseline_sensitivity(prices, timestamps, thresholds, one_way_cost=0.00002):
    rows = []
    for theta in thresholds:
        result = run_strategy(
            prices, timestamps, Config(theta, theta, (1, 2), 0.25, one_way_cost, False)
        )
        rows.append({"theta": theta, **performance(result, timestamps)})
    return pd.DataFrame(rows)
