import numpy as np
import pandas as pd
import pytest

from dc_fx.backtest import Config, effective_params, run_engine, run_strategy
from dc_fx.directional_change import Detector
from dc_fx.metrics import performance


def run(prices, **kwargs):
    return run_strategy(
        prices,
        pd.date_range("2025-01-01", periods=len(prices), freq="h"),
        Config(
            theta_up=0.1,
            theta_down=0.1,
            inventory_adjustment=False,
            osv_levels=(0.5,),
            one_way_cost=0,
            **kwargs
        ),
    )


def test_long_hand_calculation_and_open_drawdown():
    result = run([100, 111, 117, 120, 116, 107])
    assert len(result.trades) == 1
    assert result.equity[-1] == pytest.approx(1 + 0.25 * (107 - 117) / 117)
    assert result.equity[3] == pytest.approx(1 + 0.25 * (120 - 117) / 117)
    assert result.equity[4] < result.equity[3]
    assert result.trades.iloc[0].result == "DC exit"


def test_short_hand_calculation():
    result = run([100, 89, 84, 80, 90])
    assert result.equity[-1] == pytest.approx(1 + 0.25 * (84 - 90) / 84)
    assert result.trades.iloc[0].direction == "SHORT"


def test_single_event_still_trades_and_liquidates():
    result = run([100, 111, 117, 120])
    assert len(result.trades) == 1
    assert result.trades.iloc[0].result == "End liquidation"
    assert result.equity[-1] > 1


def test_costs_and_quantity_weighted_entry():
    prices = [100, 111, 117, 123, 130]
    times = pd.date_range("2025-01-01", periods=5, freq="h")
    result = run_strategy(prices, times, Config(0.1, 0.1, (0.5, 1), 0.25, 0.01, False))
    q = 0.25 / 117 + 0.25 / 123
    expected = 0.25 * (130 - 117) / 117 + 0.25 * (130 - 123) / 123 - 0.02 * q
    assert result.equity[-1] == pytest.approx(1 + expected)
    assert result.trades.iloc[0].avg_entry_px == pytest.approx(0.5 / q)
    assert result.trades.iloc[0].cost == pytest.approx(0.02 * q)
    assert result.equity[2] == pytest.approx(1 - 0.02 * 0.25 / 117)


def test_recompute_sizing_after_each_gap_entry():
    prices = [100, 111, 150]
    result = run_strategy(
        prices,
        pd.date_range("2025", periods=3),
        Config(0.1, 0.1, (0.5, 1, 1.5), 0.25, 0, True),
    )
    assert result.trades.iloc[0].n_entries == 3
    assert result.trades.iloc[0].total_size == pytest.approx(0.625)


def test_default_inventory_sizing_inactive_but_threshold_skew_active():
    cfg = Config()
    assert effective_params(cfg, 0.25) == (cfg.theta_up, cfg.theta_down, 0.25)
    up, down, unit = effective_params(cfg, 0.5)
    assert (up, down, unit) == (cfg.theta_up * 1.5, cfg.theta_down / 1.5, 0.125)
    assert effective_params(cfg, -1) == (cfg.theta_up / 2, cfg.theta_down * 2, 0.0625)


def test_engine_accounting_and_unique_scales():
    prices = [100, 111, 117, 123, 110, 100, 90, 110]
    times = pd.date_range("2025", periods=len(prices))
    result, scales = run_engine(
        prices, times, scales=((0.1, 0.1), (0.10001, 0.10001)), one_way_cost=0.01
    )
    np.testing.assert_allclose(result.equity, (scales[1].equity + scales[2].equity) / 2)
    assert result.trades.portfolio_pnl.sum() == pytest.approx(result.equity[-1] - 1)
    assert result.trades.exit_time.is_monotonic_increasing
    assert len(scales) == 2


def test_causal_prefix_equity():
    prices = [100, 111, 117, 120, 116, 107, 95, 85, 110]
    full = run(prices)
    for end in range(1, len(prices)):
        np.testing.assert_allclose(run(prices[:end]).equity, full.equity[:end])


@pytest.mark.parametrize("prices", [[], [100], [100, 100, 100]])
def test_empty_and_flat(prices):
    result = run(prices)
    assert result.trades.empty
    np.testing.assert_array_equal(result.equity, np.ones(len(prices)))
    metrics = performance(result, pd.date_range("2025", periods=len(prices)))
    assert metrics["return_pct"] == 0
    assert metrics["daily_sharpe_252"] is None


@pytest.mark.parametrize(
    "kwargs",
    [
        {"theta_up": 0},
        {"theta_down": np.nan},
        {"one_way_cost": -1},
        {"osv_levels": ()},
        {"osv_levels": (1, 0.5)},
        {"position_unit": 0},
    ],
)
def test_invalid_config(kwargs):
    with pytest.raises(ValueError):
        Config(**kwargs)


@pytest.mark.parametrize(
    "prices,times",
    [
        ([1, np.nan], ["2025", "2026"]),
        ([0], ["2025"]),
        ([1, 2], ["2026", "2025"]),
        ([1], []),
        ([1], [None]),
    ],
)
def test_invalid_inputs(prices, times):
    with pytest.raises(ValueError):
        run_strategy(prices, times)


def test_empty_scales():
    with pytest.raises(ValueError):
        run_engine([], [], scales=())


def test_directional_change_extremes():
    detector = Detector(100)
    assert [
        detector.update(p, 0.1, 0.1) for p in [100, 111, 120, 109, 108, 100, 110]
    ] == [0, 1, 0, 0, -1, 0, 1]
