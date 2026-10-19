"""Metrics from account equity, including days with ticks but no trades."""

import numpy as np
import pandas as pd


def daily_equity(equity, timestamps):
    series = pd.Series(equity, index=pd.DatetimeIndex(timestamps), dtype=float)
    daily = series.groupby(series.index.normalize()).last()
    returns = daily.pct_change()
    if len(daily):
        returns.iloc[0] = daily.iloc[0] - 1
    return pd.DataFrame({"equity": daily, "return": returns})


def performance(result, timestamps):
    equity = result.equity
    daily = daily_equity(equity, timestamps)
    returns = daily["return"]
    std = returns.std(ddof=1)
    sharpe = (
        float(np.sqrt(252) * returns.mean() / std)
        if len(returns) > 1 and std > 1e-15
        else None
    )
    anchored = np.r_[1.0, equity]
    drawdown = anchored / np.maximum.accumulate(anchored) - 1
    return {
        "ticks": len(equity),
        "trades": len(result.trades),
        "return_pct": float((anchored[-1] - 1) * 100),
        "max_drawdown_pct": float(drawdown.min() * 100),
        "daily_sharpe_252": sharpe,
        "observed_days": len(daily),
    }
