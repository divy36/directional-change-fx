"""HistData tick loading; timestamps remain in the source clock."""

import numpy as np
import pandas as pd


def load_ticks(path, deduplicate=False):
    raw = pd.read_csv(
        path,
        header=None,
        names=["timestamp", "bid", "ask", "volume"],
        dtype={"timestamp": str},
    )
    stamp = raw.timestamp.str.replace(" ", "", regex=False)
    valid_format = stamp.str.fullmatch(r"\d{17}").fillna(False)
    dates = pd.to_datetime(
        stamp.str[:14].where(valid_format), format="%Y%m%d%H%M%S", errors="coerce"
    )
    millis = pd.to_numeric(stamp.str[14:].where(valid_format), errors="coerce")
    dates = dates + pd.to_timedelta(millis.fillna(0), unit="ms")
    bid = pd.to_numeric(raw.bid, errors="coerce")
    ask = pd.to_numeric(raw.ask, errors="coerce")
    valid = (
        dates.notna() & np.isfinite(bid) & np.isfinite(ask) & (bid > 0) & (ask >= bid)
    )
    ticks = pd.DataFrame(
        {"bid": bid[valid].to_numpy(), "ask": ask[valid].to_numpy()},
        index=pd.DatetimeIndex(dates[valid], name="timestamp"),
    )
    ticks = ticks.sort_index(kind="stable")
    duplicates = int(ticks.index.duplicated().sum())
    if deduplicate:
        ticks = ticks[~ticks.index.duplicated(keep="first")]
    ticks["mid"] = (ticks.bid + ticks.ask) / 2
    audit = {
        "input_rows": len(raw),
        "invalid_rows": int((~valid).sum()),
        "duplicate_timestamps": duplicates,
        "retained_rows": len(ticks),
        "deduplicate": deduplicate,
    }
    if ticks.empty:
        raise ValueError("No valid ticks in input")
    return ticks, audit


def demo_ticks():
    rng = np.random.default_rng(42)
    mid = 1.1 * np.exp(np.cumsum(rng.normal(0, 0.00015, 10000)))
    return pd.DataFrame(
        {"mid": mid}, index=pd.date_range("2025-01-06", periods=len(mid), freq="min")
    )
