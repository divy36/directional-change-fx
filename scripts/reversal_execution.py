"""Independent signal trace and vectorized execution stress replay.

Signal schedule uses signal-side inventory, as in the production reversal.
Quotes are marketable bid/ask; quote stress does not also charge fixed spread.
"""
import numpy as np
from dc_fx.backtest import effective_params
from dc_fx.directional_change import Detector


def trace_orders(prices, config):
    if not len(prices):
        return []
    detector = Detector(prices[0])
    direction, anchor, next_level, inventory, count = 0, 0., 0, 0., 0
    orders = []
    for i, price in enumerate(prices):
        up, down, _ = effective_params(config, inventory)
        event = detector.update(price, up, down)
        if count and event == -direction:
            orders.append((i, 'close', 0, 0.))
            count, inventory, direction = 0, 0., 0
        if event and not count:
            direction, anchor, next_level = event, price, 0
        if direction and next_level < len(config.osv_levels):
            theta = config.theta_up if direction == 1 else config.theta_down
            osv = direction * (price-anchor)/(anchor*theta)
            while next_level < len(config.osv_levels) and osv >= config.osv_levels[next_level]:
                _, _, unit = effective_params(config, inventory)
                orders.append((i, 'entry', direction*config.execution_sign, unit))
                inventory += direction * unit
                count += 1
                next_level += 1
    return orders


def replay(prices, half_spread, orders, delay=0):
    """Replay fixed signals; reserve entry and current estimated exit friction.

    Unit quantities use executed tick mid, matching production fixed-cost sizing.
    A delayed signal fills at the next observed tick, before that tick's signals.
    Signals whose delayed fills fall beyond sample end are not filled. Remaining
    inventory is liquidated on the last quote. This is a tick-delay stress, not
    a wall-clock latency or market impact model.
    """
    n = len(prices)
    if not n:
        return np.array([]), []
    scheduled = [(i+delay, kind, d, unit) for i,kind,d,unit in orders if i+delay < n]
    scheduled.append((n-1, 'close', 0, 0.))
    curve = np.ones(n)
    capital, quantity, basis, entry_cost, direction = 1., 0., 0., 0., 0
    ledger = []
    start = 0
    for i, kind, d, unit in scheduled:
        if i > start:
            curve[start:i] = capital + direction*(quantity*prices[start:i]-basis)-entry_cost-quantity*half_spread[start:i]
        if kind == 'entry':
            if quantity and d != direction:
                raise AssertionError('Opposite entry without close')
            direction = d
            q = capital * unit / prices[i]
            quantity += q
            basis += q*prices[i]
            entry_cost += q*half_spread[i]
        elif quantity:
            cost = entry_cost+quantity*half_spread[i]
            pnl = direction*(quantity*prices[i]-basis)-cost
            ledger.append((i,pnl,cost))
            capital += pnl
            quantity = basis = entry_cost = 0.
            direction = 0
        start = i
    curve[start:] = capital + direction*(quantity*prices[start:]-basis)-entry_cost-quantity*half_spread[start:]
    if np.any(curve <= 0):
        raise ValueError('Account exhausted')
    assert abs(sum(row[1] for row in ledger)-(curve[-1]-1)) < 1e-10
    return curve, ledger
