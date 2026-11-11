from dataclasses import dataclass
import numpy as np
import pandas as pd
from .data import validate
from .serialization import json_safe

ADJUSTED_EXPLORATORY = "adjusted_exploratory"

@dataclass(frozen=True)
class Costs:
    fee_bps: float = 1.0
    spread_bps: float = 5.0  # Full spread, half charged on each side.
    slippage_bps: float = 5.0
    def __post_init__(self):
        values = [self.fee_bps, self.spread_bps, self.slippage_bps]
        if not all(np.isfinite(x) and 0 <= x <= 1000 for x in values):
            raise ValueError("Invalid costs")

@dataclass
class Result:
    equity: pd.Series
    cash: pd.Series
    shares: pd.Series
    journal: pd.DataFrame
    initial: float
    simulation_mode: str = ADJUSTED_EXPLORATORY

def run(bars, targets, initial=2700.0, costs=Costs(), max_allocation=0.95, participation=0.01, *, simulation_mode=ADJUSTED_EXPLORATORY):
    """Adjusted-unit exploration only; no executable-price simulation is implemented."""
    if simulation_mode != ADJUSTED_EXPLORATORY:
        raise ValueError("Executable-price simulation is not implemented; use adjusted_exploratory only")
    validate(bars)
    if not np.isfinite(initial) or initial <= 0 or not 0 < max_allocation <= 1 or not 0 < participation <= 1:
        raise ValueError("Invalid portfolio assumptions")
    if not targets.index.equals(bars.index) or not np.isfinite(targets).all() or not targets.between(0, 1).all():
        raise ValueError("Targets must align and be long-only weights")
    cash, shares = float(initial), 0.0
    equity, cashes, positions, journal = [], [], [], []
    # Targets are decisions after close t; fills use open t+1, never close t.
    pending = targets.shift(1).fillna(0)
    last_target = 0.0
    for date, bar in bars.iterrows():
        target = float(pending.loc[date]) * max_allocation
        if target != last_target:
            nav = cash + shares * bar.open
            delta = target * nav / bar.open - shares
            side = 1 if delta > 0 else -1
            impact = (costs.spread_bps / 2 + costs.slippage_bps) / 10000
            fill = bar.open * (1 + side * impact)
            qty = min(abs(delta), bar.volume * participation)
            if side > 0:
                qty = min(qty, cash / (fill * (1 + costs.fee_bps / 10000)))
            else:
                qty = min(qty, shares)
            fee = qty * fill * costs.fee_bps / 10000
            cash -= side * qty * fill + fee
            shares += side * qty
            journal.append(dict(session=date, side="buy" if side > 0 else "sell", quantity=qty, reference_open=bar.open, fill=fill, fee=fee, spread_cost=qty*bar.open*costs.spread_bps/20000, slippage_cost=qty*bar.open*costs.slippage_bps/10000, status="filled" if qty >= abs(delta)-1e-8 else "partial_or_rejected"))
            # Unfilled remainder expires; no hidden same-session retries.
            last_target = target
        equity.append(cash + shares * bar.close)
        cashes.append(cash)
        positions.append(shares)
    return Result(pd.Series(equity, index=bars.index, name="equity"), pd.Series(cashes,index=bars.index), pd.Series(positions,index=bars.index), pd.DataFrame(journal), initial)

def metrics(result):
    """Undefined or non-finite derived estimates are None, never NaN/Infinity.

    Fewer than two sessions: cumulative accounting remains available, while
    annualized/risk estimates are unavailable. Two sessions is computable,
    not evidence of statistical adequacy; sample size is always reported.
    """
    equity = result.equity
    if equity.empty or not np.isfinite(equity).all() or (equity <= 0).any():
        raise ValueError("Metrics require nonempty, positive finite equity")
    if not np.isfinite(result.initial) or result.initial <= 0:
        raise ValueError("Metrics require positive finite initial cash")
    n = len(equity)
    returns = equity.pct_change()
    returns.iloc[0] = equity.iloc[0]/result.initial-1
    peak = equity.cummax().clip(lower=result.initial)
    dd = equity/peak-1
    vol = returns.std(ddof=1)*np.sqrt(252) if n >= 2 else None
    downside = np.sqrt(np.mean(np.minimum(returns,0)**2))*np.sqrt(252) if n >= 2 else None
    # Extreme short-window annualization can overflow; report it unavailable.
    with np.errstate(over="ignore", invalid="ignore"):
        annual = np.expm1(np.log(equity.iloc[-1]/result.initial)*252/n) if n >= 2 else None
    q = returns.quantile(0.05) if n >= 2 else None
    journal = result.journal
    turnover = 0 if journal.empty else (journal.quantity*journal.reference_open).sum()/result.initial
    values = {"sessions":n, "total_return":equity.iloc[-1]/result.initial-1,
              "annualized_return":annual, "max_drawdown":float(dd.min()),
              "annualized_volatility":vol,
              "sharpe_zero_cash_rate":returns.mean()*252/vol if vol is not None and vol>0 else None,
              "sortino_zero_cash_rate":returns.mean()*252/downside if downside is not None and downside>0 else None,
              "calmar":annual/abs(dd.min()) if annual is not None and dd.min()<0 else None,
              "historical_var_95_loss":-q if q is not None else None,
              "historical_es_95_loss":-returns[returns<=q].mean() if q is not None else None,
              "exposure":float((result.shares>0).mean()), "turnover":float(turnover)}
    return json_safe(values)

def trade_statistics(result):
    """Average-cost realized P&L in adjusted research units; fees included."""
    basis, held, pnl = 0.0, 0.0, []
    for trade in result.journal.itertuples():
        if trade.quantity <= 0:
            continue
        if trade.side == 'buy':
            basis += trade.quantity * trade.fill + trade.fee
            held += trade.quantity
        else:
            released = basis * trade.quantity / held
            pnl.append(trade.quantity * trade.fill - trade.fee - released)
            held -= trade.quantity
            basis -= released
    wins = [x for x in pnl if x > 0]
    losses = [x for x in pnl if x < 0]
    streak = longest = 0
    for value in pnl:
        streak = streak + 1 if value < 0 else 0
        longest = max(longest, streak)
    return {"realized_pnl":sum(pnl), "unrealized_pnl":float(result.equity.iloc[-1]-result.cash.iloc[-1]-basis), "completed_exit_count":len(pnl), "win_rate":len(wins)/len(pnl) if pnl else None, "profit_factor":sum(wins)/abs(sum(losses)) if losses else None, "average_gain":float(np.mean(wins)) if wins else None, "average_loss":float(np.mean(losses)) if losses else None, "exit_expectancy":float(np.mean(pnl)) if pnl else None, "consecutive_losing_exits":longest}
