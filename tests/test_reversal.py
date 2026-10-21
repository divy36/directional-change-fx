import json
import sys

import numpy as np
import pandas as pd
import pytest

from dc_fx.backtest import Config, run_engine, run_strategy
from dc_fx.cli import main as cli_main


TIMES = pd.date_range("2025-01-01", periods=9, freq="h")
PRICES = [100, 111, 117, 120, 116, 107, 95, 85, 110]


def config(**kwargs):
    values = dict(
        theta_up=0.1,
        theta_down=0.1,
        osv_levels=(0.5, 1.0),
        position_unit=0.25,
        one_way_cost=0,
        inventory_adjustment=False,
    )
    values.update(kwargs)
    return Config(**values)


def schedule(trades):
    return trades[["entry_time", "exit_time", "n_entries", "total_size", "result"]]


def test_reversed_trade_matches_hand_calculation():
    prices = [100, 111, 117, 120, 116, 107]
    times = pd.date_range("2025", periods=len(prices), freq="h")
    result = run_strategy(prices, times, config(execution_sign=-1))

    trade = result.trades.iloc[0]
    expected_pnl = 0.25 * (117 - 107) / 117
    assert trade.direction == "SHORT"
    assert trade.entry_time == times[2]
    assert trade.exit_time == times[5]
    assert trade.pnl == pytest.approx(expected_pnl)
    assert result.equity[-1] == pytest.approx(1 + expected_pnl)


def test_reverse_preserves_signal_schedule_and_costs_remain_negative_pnl():
    cfg = config(one_way_cost=0.01)
    follow = run_strategy(PRICES, TIMES, cfg)
    fade = run_strategy(PRICES, TIMES, config(one_way_cost=0.01, execution_sign=-1))

    pd.testing.assert_frame_equal(schedule(follow.trades), schedule(fade.trades))
    assert fade.trades.direction.tolist() == [
        "SHORT" if direction == "LONG" else "LONG"
        for direction in follow.trades.direction
    ]
    # The first trade starts from identical capital; later costs can differ
    # because each mode compounds its own execution P&L.
    assert fade.trades.iloc[0].cost == pytest.approx(follow.trades.iloc[0].cost)
    assert (fade.trades.cost > 0).all()
    gross_fade_pnl = fade.trades.pnl + fade.trades.cost
    assert np.all(gross_fade_pnl != fade.trades.pnl)
    assert np.all(fade.trades.pnl <= gross_fade_pnl)


def test_reversed_equity_is_causal_under_prefixes():
    full = run_strategy(PRICES, TIMES, config(execution_sign=-1))
    for end in range(1, len(PRICES)):
        prefix = run_strategy(PRICES[:end], TIMES[:end], config(execution_sign=-1))
        np.testing.assert_allclose(prefix.equity, full.equity[:end])


def test_reversed_multiscale_engine_keeps_scale_schedules_and_accounting():
    scales = ((0.1, 0.1), (0.08, 0.12), (0.12, 0.08))
    follow, follow_scales = run_engine(PRICES, TIMES, scales=scales, one_way_cost=0.001)
    fade, fade_scales = run_engine(
        PRICES, TIMES, scales=scales, one_way_cost=0.001, execution_sign=-1
    )

    assert len(fade_scales) == len(scales)
    for scale_id in fade_scales:
        pd.testing.assert_frame_equal(
            schedule(follow_scales[scale_id].trades),
            schedule(fade_scales[scale_id].trades),
        )
        assert fade_scales[scale_id].trades.iloc[0].cost == pytest.approx(
            follow_scales[scale_id].trades.iloc[0].cost
        )
    np.testing.assert_allclose(
        fade.equity,
        np.mean([result.equity for result in fade_scales.values()], axis=0),
    )
    assert fade.trades.portfolio_pnl.sum() == pytest.approx(fade.equity[-1] - 1)


def test_custom_engine_matches_average_of_configured_scale_strategies():
    scales = ((0.08, 0.12), (0.1, 0.1), (0.12, 0.08))
    multiplier = 1.25
    levels = (0.75, 1.5)
    engine, per_scale = run_engine(
        PRICES,
        TIMES,
        scales=scales,
        one_way_cost=0.001,
        execution_sign=-1,
        threshold_multiplier=multiplier,
        osv_levels=levels,
        inventory_adjustment=False,
    )
    constituent_results = [
        run_strategy(
            PRICES,
            TIMES,
            Config(
                theta_up=up * multiplier,
                theta_down=down * multiplier,
                osv_levels=levels,
                one_way_cost=0.001,
                execution_sign=-1,
                inventory_adjustment=False,
            ),
        )
        for up, down in scales
    ]

    np.testing.assert_allclose(
        engine.equity,
        np.mean([result.equity for result in constituent_results], axis=0),
    )
    for scale_id, expected in enumerate(constituent_results, start=1):
        np.testing.assert_allclose(per_scale[scale_id].equity, expected.equity)
        pd.testing.assert_frame_equal(per_scale[scale_id].trades, expected.trades)


def test_cli_demo_records_custom_reversal_configuration(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "dc-fx",
            "--demo",
            "--strategy",
            "alpha",
            "--reverse",
            "--threshold-multiplier",
            "1.25",
            "--osv-levels",
            "0.75",
            "1.5",
            "--no-inventory-adjustment",
            "--output",
            str(tmp_path),
        ],
    )
    cli_main()
    capsys.readouterr()

    report = json.loads((tmp_path / "summary.json").read_text())
    assert report["reverse"] is True
    assert report["threshold_multiplier"] == 1.25
    assert report["osv_levels"] == [0.75, 1.5]
    assert report["inventory_adjustment"] is False


@pytest.mark.parametrize("threshold_multiplier", [0, -1, np.nan, np.inf, True, "bad"])
def test_engine_rejects_invalid_threshold_multiplier(threshold_multiplier):
    with pytest.raises(ValueError, match="Threshold multiplier"):
        run_engine([], [], threshold_multiplier=threshold_multiplier)


@pytest.mark.parametrize("execution_sign", [0, 2, -2, 1.5, True])
def test_invalid_execution_sign(execution_sign):
    with pytest.raises(ValueError, match="Execution sign"):
        Config(execution_sign=execution_sign)
