import pandas as pd
import pytest

from dc_fx.research import baseline_sensitivity, scaling_diagnostics


def test_complete_scaling_legs_include_zero_overshoot():
    prices = [100, 111, 120, 108, 120]
    times = pd.date_range("2025", periods=len(prices))
    row = scaling_diagnostics(prices, times, [0.1]).iloc[0]
    assert row.events == 3
    assert row.completed_legs == 2
    assert row.mean_overshoot == pytest.approx((9 / 111) / 2)
    assert row.os_dc_tick_ratio == pytest.approx(0.5)


def test_scaling_without_complete_legs():
    row = scaling_diagnostics([100, 111], pd.date_range("2025", periods=2), [0.1]).iloc[
        0
    ]
    assert row.completed_legs == 0
    assert row.mean_overshoot is None


def test_baseline_sensitivity_no_trades():
    result = baseline_sensitivity(
        [100, 100], pd.date_range("2025", periods=2), [0.01, 0.02]
    )
    assert result.return_pct.tolist() == [0, 0]
