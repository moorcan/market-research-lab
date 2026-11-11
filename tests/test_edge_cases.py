"""All prices below are synthetic development fixtures, never research findings."""
import json
from dataclasses import replace

import numpy as np
import pandas as pd
import pytest

from market_lab.backtest import Costs, Result, metrics, run, trade_statistics
from market_lab.data import Provenance, require_adjusted_provenance
from market_lab.experiments import record
from market_lab.serialization import dumps
from market_lab.strategies import Strategy


def short_bars(n):
    dates = pd.DatetimeIndex(['2024-01-02', '2024-01-03', '2024-01-04', '2024-01-05', '2024-01-08'])[:n]
    return pd.DataFrame({'open':100., 'close':100., 'high':101., 'low':99., 'volume':10000.},index=dates)


def strict_load(text):
    def reject(token):
        raise AssertionError(f'Nonstandard JSON token: {token}')
    return json.loads(text, parse_constant=reject)


@pytest.mark.parametrize('n',[1,2,5])
@pytest.mark.parametrize('name',['trend','mean_reversion'])
def test_short_history_stays_cash_and_serializes(n,name,tmp_path):
    bars = short_bars(n)
    strategy = Strategy(name,50)
    result = run(bars,strategy.signals(bars))
    assert result.equity.eq(2700).all()
    assert result.journal.empty
    summary = metrics(result)
    assert summary['sessions'] == n
    assert summary['total_return'] == 0
    assert summary['sharpe_zero_cash_rate'] is None
    assert summary['sortino_zero_cash_rate'] is None
    assert summary['calmar'] is None
    if n == 1:
        for key in ['annualized_return','annualized_volatility','historical_var_95_loss','historical_es_95_loss']:
            assert summary[key] is None
    else:
        assert summary['annualized_volatility'] == 0
    provenance = Provenance('TEST FIXTURE','synthetic','none','all','2024-01-09T00:00:00Z','TEST ONLY',True)
    identifier = record(tmp_path,'fixture-version',provenance,strategy,Costs(),result)
    saved = strict_load((tmp_path/f'{identifier}.json').read_text())
    assert saved['metrics'] == summary
    assert saved['simulation_mode'] == 'adjusted_exploratory'
    assert saved['executable_price_simulation'] is False
    assert saved['provenance']['fixture'] is True
    exits = strict_load(dumps(trade_statistics(result)))
    assert exits['win_rate'] is None and exits['profit_factor'] is None


def test_empty_history_rejected_explicitly():
    bars = short_bars(0)
    with pytest.raises(ValueError,match='Empty data'):
        run(bars,pd.Series(dtype=float,index=bars.index))
    result = Result(pd.Series(dtype=float),pd.Series(dtype=float),pd.Series(dtype=float),pd.DataFrame(),2700)
    with pytest.raises(ValueError,match='nonempty'):
        metrics(result)


def test_single_session_does_not_fill_final_signal():
    bars = short_bars(1)
    result = run(bars,pd.Series(1.,index=bars.index))
    assert result.journal.empty and result.equity.iloc[0] == 2700


def test_zero_downside_and_extreme_annualization():
    bars = short_bars(2)
    result = run(bars,pd.Series(0.,index=bars.index))
    result.equity = pd.Series([2700.,3000.],index=bars.index)
    summary = metrics(result)
    assert summary['sortino_zero_cash_rate'] is None
    assert summary['calmar'] is None
    assert summary['sharpe_zero_cash_rate'] is not None
    result.equity.iloc[1] = 1e100
    assert metrics(result)['annualized_return'] is None
    strict_load(dumps(metrics(result)))


def test_json_handles_nested_nonfinite_and_numpy_scalars():
    payload = {'metrics':[np.float64(np.nan),float('inf'),float('-inf'),np.int64(3),np.bool_(True)],'finite':np.float32(1.5)}
    assert strict_load(dumps(payload)) == {'metrics':[None,None,None,3,True],'finite':1.5}
    with pytest.raises(TypeError):
        dumps({'unsupported':object()})


@pytest.mark.parametrize('mode',['raw','executable','realistic'])
def test_executable_mode_cannot_be_enabled(mode):
    bars = short_bars(2)
    with pytest.raises(ValueError,match='not implemented'):
        run(bars,pd.Series(1.,index=bars.index),simulation_mode=mode)


def test_raw_dataset_cannot_enter_exploratory_report(tmp_path):
    provenance = Provenance('TEST FIXTURE','synthetic','none','raw','2024-01-09T00:00:00Z','TEST ONLY',True)
    with pytest.raises(ValueError,match='adjustment=all'):
        require_adjusted_provenance(provenance)
    bars = short_bars(2)
    result = run(bars,pd.Series(0.,index=bars.index))
    with pytest.raises(ValueError,match='adjustment=all'):
        record(tmp_path,'fixture',provenance,Strategy(),Costs(),result)
    assert not list(tmp_path.iterdir())


def test_cli_short_dataset_strict_json(tmp_path,monkeypatch,capsys):
    import sys
    from market_lab.data import Store
    from market_lab.__main__ import main
    provenance=Provenance('TEST FIXTURE','synthetic','none','all','2024-01-09T00:00:00Z','TEST ONLY',True)
    version=Store(tmp_path/'data').save('SPY',short_bars(1),provenance)
    monkeypatch.setattr(sys,'argv',['market_lab','--data-dir',str(tmp_path/'data'),'backtest',version,'--reports-dir',str(tmp_path/'reports')])
    main()
    payload=strict_load(capsys.readouterr().out)
    assert payload['status']=='TEST FIXTURE ONLY'
    assert payload['strategy']['annualized_volatility'] is None
    assert payload['passive']['sortino_zero_cash_rate'] is None


def test_one_session_dashboard_run_and_raw_rejection(tmp_path,monkeypatch):
    from pathlib import Path
    from streamlit.testing.v1 import AppTest
    from market_lab.data import Store
    app_path=Path(__file__).resolve().parents[1]/'app.py'
    monkeypatch.chdir(tmp_path)
    provenance=Provenance('TEST FIXTURE','synthetic','none','all','2024-01-09T00:00:00Z','TEST ONLY',True)
    Store().save('SPY',short_bars(1),provenance)
    app=AppTest.from_file(str(app_path)).run(timeout=15)
    app.sidebar.radio[0].set_value('Strategy Lab').run(timeout=15)
    app.button[0].click().run(timeout=15)
    assert not app.exception
    assert any('Fewer than two sessions' in warning.value for warning in app.warning)
    assert list((tmp_path/'reports').glob('*.json'))
    raw=replace(provenance,adjustment='raw')
    version=Store().save('SPY',short_bars(2),raw)
    app=AppTest.from_file(str(app_path)).run(timeout=15)
    app.sidebar.radio[0].set_value('Strategy Lab').run(timeout=15)
    app.selectbox[0].set_value(version).run(timeout=15)
    assert not app.exception
    assert any('executable-price simulation is not implemented' in error.value for error in app.error)
    assert not app.button
