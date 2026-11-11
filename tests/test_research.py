from dataclasses import replace
from datetime import datetime, timedelta, timezone
import numpy as np
import pandas as pd
import pytest
import exchange_calendars as xcals
from market_lab.data import validate, Store, Provenance, AlpacaDaily
from market_lab.strategies import Strategy
from market_lab.backtest import run, Costs, metrics
from market_lab.events import PublicEvent, known_events
from market_lab.experiments import record

@pytest.fixture
def bars():
    """SYNTHETIC DEVELOPMENT FIXTURE. Never research findings."""
    dates = xcals.get_calendar('XNYS').sessions_in_range('2024-01-02','2024-06-28').tz_localize(None)
    close = 100 + np.arange(len(dates))*.1 + 5*np.sin(np.arange(len(dates))/4)
    return pd.DataFrame({'open':close-0.2,'high':close+1,'low':close-1,'close':close,'volume':100000},index=dates)

def test_data_quality_and_missing_sessions(bars):
    validate(bars)
    with pytest.raises(ValueError,match='Missing'):
        validate(bars.drop(bars.index[3]))
    bad = bars.copy(); bad.iloc[0,bad.columns.get_loc('low')] = 1000
    with pytest.raises(ValueError,match='OHLC'): validate(bad)
    bad = bars.copy(); bad.iloc[2,0] = np.nan
    with pytest.raises(ValueError,match='Invalid'): validate(bad)
    with pytest.raises(ValueError): validate(pd.concat([bars,bars]))

@pytest.mark.parametrize('name',['trend','mean_reversion'])
def test_strategy_future_invariance(bars,name):
    strategy = Strategy(name,10)
    original = strategy.signals(bars)
    changed = bars.copy(); changed.iloc[70:,changed.columns.get_loc('close')] *= 5
    pd.testing.assert_series_equal(original.iloc[:70], strategy.signals(changed).iloc[:70])
    assert original.iloc[:9].eq(0).all()

def test_next_open_and_gap_execution(bars):
    targets = pd.Series(0.0,index=bars.index);targets.iloc[10:]=1
    bars = bars.copy();bars.iloc[11] = [150,155,145,151,100000]
    result = run(bars,targets,costs=Costs(0,0,0))
    trade = result.journal.iloc[0]
    assert trade.session == bars.index[11]
    assert trade.fill == 150
    assert result.shares.iloc[10] == 0
    assert trade.quantity == pytest.approx(2700*.95/150)

def test_costs_and_cash_accounting(bars):
    targets = pd.Series(0.0,index=bars.index);targets.iloc[1:5]=1
    costs = Costs(10,20,30)
    result = run(bars,targets,costs=costs)
    cash, shares = 2700., 0.
    for trade in result.journal.itertuples():
        side = 1 if trade.side == 'buy' else -1
        assert trade.fill == pytest.approx(trade.reference_open*(1+side*.004))
        assert trade.fee == pytest.approx(trade.quantity*trade.fill*.001)
        cash -= side*trade.quantity*trade.fill + trade.fee
        shares += side*trade.quantity
    assert shares == pytest.approx(0)
    assert cash == pytest.approx(result.cash.iloc[-1])
    assert result.cash.min() >= -1e-8
    assert result.shares.min() >= -1e-8
    assert run(bars,targets,costs=Costs(0,0,0)).equity.iloc[-1] > result.equity.iloc[-1]

def test_liquidity_rejection_and_expiry(bars):
    bars = bars.copy();bars.iloc[1,bars.columns.get_loc('volume')]=0
    result = run(bars,pd.Series(1.,index=bars.index))
    assert result.journal.iloc[0].status == 'partial_or_rejected'
    assert result.shares.eq(0).all()
    assert len(result.journal)==1

def test_long_only_reject_invalid_inputs(bars):
    with pytest.raises(ValueError): run(bars,pd.Series(-1.,index=bars.index))
    with pytest.raises(ValueError): Costs(-1,0,0)
    with pytest.raises(ValueError): run(bars,pd.Series(0.,index=bars.index),initial=-1)

def test_benchmark_and_risk_identity(bars):
    result = run(bars,pd.Series(0.,index=bars.index))
    assert result.equity.eq(2700).all()
    report = metrics(result)
    assert report['max_drawdown']==0
    assert report['total_return']==0
    assert report['sharpe_zero_cash_rate'] is None

def test_immutable_cache_roundtrip_and_registry(bars,tmp_path):
    store = Store(tmp_path/'data')
    meta = Provenance('TEST FIXTURE','synthetic','none','all','2024-07-01T00:00:00Z','TEST ONLY',True)
    v1 = store.save('SPY',bars,meta)
    assert store.save('SPY',bars,meta)==v1
    loaded, provenance = store.load(v1)
    pd.testing.assert_frame_equal(loaded,bars.rename_axis('session'),check_freq=False)
    changed = bars.copy();changed.iloc[-1,4]+=1
    v2 = store.save('SPY',changed,meta)
    assert v2!=v1 and len(store.versions())==2
    strategy=Strategy('trend',10)
    result=run(loaded,strategy.signals(loaded))
    identifier=record(tmp_path/'reports',v1,provenance,strategy,Costs(),result)
    import json
    payload=json.loads((tmp_path/'reports'/f'{identifier}.json').read_text())
    assert payload['provenance']['fixture'] is True
    assert payload['dataset_version']==v1

@pytest.fixture
def event():
    utc=timezone.utc
    return PublicEvent('form4-1','https://www.sec.gov/example','sec_form4','SPY',datetime(2024,1,1,tzinfo=utc),datetime(2024,1,5,22,tzinfo=utc),datetime(2024,1,5,22,5,tzinfo=utc),'TEST disclosure','P',timedelta(minutes=1))

def test_first_public_availability_and_deduplication(event):
    assert known_events([event],event.occurred_at)==[]
    assert known_events([event],event.published_at)==[]
    assert known_events([event],event.ingested_at)==[]
    assert known_events([event,event],event.available_at)==[event]
    assert event.open_market_purchase
    assert not replace(event,transaction_code='M').open_market_purchase
    with pytest.raises(ValueError): replace(event,published_at=datetime(2024,1,1))

def test_adapter_pagination_and_metadata(monkeypatch,bars):
    source=bars.iloc[:4]
    rows=[dict(t=str(date.date())+'T05:00:00Z',o=row.open,h=row.high,l=row.low,c=row.close,v=row.volume) for date,row in source.iterrows()]
    calls=[]
    class Response:
        def raise_for_status(self): pass
        def json(self):
            return {'bars':rows[:2], 'next_page_token':'page2'} if len(calls)==1 else {'bars':rows[2:]}
    def fake_get(url,**kwargs):
        assert url.startswith('https://data.alpaca.markets/v2/stocks/')
        assert kwargs['params']['adjustment']=='all'
        calls.append(dict(kwargs['params']))
        return Response()
    monkeypatch.setenv('APCA_API_KEY_ID','TEST_ONLY')
    monkeypatch.setenv('APCA_API_SECRET_KEY','TEST_ONLY')
    monkeypatch.setattr('market_lab.data.requests.get',fake_get)
    fetched,meta=AlpacaDaily().fetch('SPY',str(source.index[0].date()),str(source.index[-1].date()))
    assert len(fetched)==4 and calls[1]['page_token']=='page2'
    assert meta.adjustment=='all' and not meta.fixture

def test_realized_unrealized_reconciliation(bars):
    from market_lab.backtest import trade_statistics
    targets=pd.Series(0.,index=bars.index);targets.iloc[2:20]=1.;targets.iloc[40:]=1.
    result=run(bars,targets)
    stats=trade_statistics(result)
    assert stats['completed_exit_count']==1
    assert stats['realized_pnl']+stats['unrealized_pnl']==pytest.approx(result.equity.iloc[-1]-2700)

def test_dashboard_fixture_simulation_is_labeled(bars,tmp_path,monkeypatch):
    from pathlib import Path
    from streamlit.testing.v1 import AppTest
    app_path=Path(__file__).resolve().parents[1]/'app.py'
    monkeypatch.chdir(tmp_path)
    meta=Provenance('TEST FIXTURE','synthetic','none','all','2024-07-01T00:00:00Z','TEST ONLY',True)
    Store().save('SPY',bars,meta)
    app=AppTest.from_file(str(app_path)).run(timeout=15)
    app.sidebar.radio[0].set_value('Strategy Lab').run(timeout=15)
    assert any('SYNTHETIC TEST FIXTURE' in e.value for e in app.error)
    app.button[0].click().run(timeout=15)
    assert not app.exception
    assert list((tmp_path/'reports').glob('*.json'))

def test_flat_price_roundtrip_matches_analytic_costs(bars):
    # Independent closed-form reference, not the simulator's update loop.
    bars=bars.copy()
    bars['open']=100.;bars['close']=100.;bars['high']=101.;bars['low']=99.
    targets=pd.Series(0.,index=bars.index);targets.iloc[0:3]=1.
    result=run(bars,targets,costs=Costs(10,20,30))
    quantity=2700*.95/100
    expected=2700-quantity*(100*1.004*1.001)+quantity*(100*.996*.999)
    assert result.equity.iloc[-1]==pytest.approx(expected)
    assert result.shares.iloc[-1]==pytest.approx(0)
