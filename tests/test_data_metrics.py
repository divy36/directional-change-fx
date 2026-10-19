import numpy as np
import pandas as pd
import pytest

from dc_fx.backtest import Result
from dc_fx.data import load_ticks
from dc_fx.metrics import daily_equity, performance


def test_loader_preserves_same_millisecond_order_and_audits_bad_rows(tmp_path):
    path = tmp_path / "ticks.csv"
    path.write_text(
        "20250101 000001000,1,1.1,0\n20250101 000000000,1,1.2,0\n"
        "20250101 000000000,1.1,1.3,0\nbad,1,2,0\n"
        "20250101 000002000,inf,inf,0\n20250101 000003000,2,1,0\n"
    )
    ticks, audit = load_ticks(path)
    assert ticks.bid.tolist() == [1, 1.1, 1]
    assert audit["invalid_rows"] == 3
    assert audit["duplicate_timestamps"] == 1
    dedup, _ = load_ticks(path, deduplicate=True)
    assert len(dedup) == 2


def test_reject_all_invalid(tmp_path):
    path = tmp_path / "bad.csv"
    path.write_text("bad,1,2,0\n")
    with pytest.raises(ValueError, match="No valid"):
        load_ticks(path)


def test_daily_returns_include_zero_trade_days_and_first_day():
    times = pd.to_datetime(
        ["2025-01-01 01:00", "2025-01-01 02:00", "2025-01-02", "2025-01-03"],
        format="mixed",
    )
    equity = np.array([0.99, 1.02, 1.02, 1.01])
    daily = daily_equity(equity, times)
    expected = np.array([0.02, 0, 1.01 / 1.02 - 1])
    np.testing.assert_allclose(daily["return"], expected)
    metrics = performance(Result(pd.DataFrame(), equity), times)
    assert metrics["daily_sharpe_252"] == pytest.approx(
        np.sqrt(252) * expected.mean() / expected.std(ddof=1)
    )
    assert metrics["max_drawdown_pct"] == pytest.approx(-1)
