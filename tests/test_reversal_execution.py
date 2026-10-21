"""Causality, execution friction and terminal-fill checks for research replay."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from dc_fx.backtest import Config, run_strategy  # noqa: E402
from reversal_execution import replay, trace_orders  # noqa: E402


@pytest.mark.parametrize("execution_sign", [1, -1])
@pytest.mark.parametrize("inventory_adjustment", [True, False])
def test_zero_delay_fixed_cost_matches_package(execution_sign, inventory_adjustment):
    prices = np.array([100, 111, 117, 120, 116, 107, 95, 85, 110.0])
    times = pd.date_range("2025-01-01", periods=len(prices), freq="h")
    cfg = Config(
        theta_up=0.1,
        theta_down=0.1,
        osv_levels=(0.5, 1.0),
        one_way_cost=0.01,
        inventory_adjustment=inventory_adjustment,
        execution_sign=execution_sign,
    )
    orders = trace_orders(prices, cfg)
    equity, ledger = replay(prices, np.full(len(prices), cfg.one_way_cost), orders)
    expected = run_strategy(prices, times, cfg)
    np.testing.assert_allclose(equity, expected.equity, atol=1e-12, rtol=0)
    assert len(ledger) == len(expected.trades)


def test_one_tick_delay_uses_next_tick_quote_and_delays_close():
    prices = np.array([100.0, 102.0, 105.0, 110.0])
    half_spread = np.full(4, 0.5)
    orders = [(0, "entry", 1, 0.25), (2, "close", 0, 0.0)]
    equity, ledger = replay(prices, half_spread, orders, delay=1)
    # Entry at tick 1, close at tick 3; both half-spreads are charged.
    q = 0.25 / prices[1]
    expected = 1 + q * (prices[3] - prices[1]) - q * half_spread[1] - q * half_spread[3]
    assert equity[-1] == pytest.approx(expected)
    assert len(ledger) == 1
    assert ledger[0][0] == 3


def test_delayed_entry_beyond_end_is_dropped_and_last_tick_entry_is_not_filled():
    prices = np.array([100.0, 101.0, 102.0])
    equity, ledger = replay(
        prices, np.full(3, 0.5), [(2, "entry", 1, 0.25)], delay=1
    )
    np.testing.assert_array_equal(equity, np.ones(3))
    assert ledger == []


def test_delayed_entry_on_last_quote_is_force_liquidated_there():
    prices = np.array([100.0, 100.0, 100.0])
    half_spread = np.full(3, 0.5)
    equity, ledger = replay(
        prices, half_spread, [(1, "entry", 1, 0.25)], delay=1
    )
    q = 0.25 / prices[-1]
    assert equity[-1] == pytest.approx(1 - 2 * q * half_spread[-1])
    assert len(ledger) == 1 and ledger[0][0] == len(prices) - 1


def test_order_trace_prefix_is_causal():
    prices = np.array([100, 111, 117, 120, 116, 107, 95, 85, 110.0])
    cfg = Config(theta_up=0.1, theta_down=0.1, one_way_cost=0)
    full = trace_orders(prices, cfg)
    for end in range(1, len(prices)):
        prefix = trace_orders(prices[:end], cfg)
        assert prefix == [order for order in full if order[0] < end]


def test_quote_cost_matches_symmetric_bid_ask_round_trip():
    prices = np.array([100.0, 101.0])
    half_spread = np.array([0.25, 0.25])
    equity, ledger = replay(
        prices,
        half_spread,
        [(0, "entry", 1, 0.25), (1, "close", 0, 0.0)],
    )
    q = 0.25 / prices[0]
    expected = 1 + q * (prices[1] - prices[0]) - q * 0.25 - q * 0.25
    assert equity[-1] == pytest.approx(expected)
    assert ledger[0][2] == pytest.approx(q * 0.5)
