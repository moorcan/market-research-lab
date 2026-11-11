"""Offline tests of the smoke harness, not genuine Alpaca validation."""
from dataclasses import replace
import json
import sys

import exchange_calendars as xcals
import pandas as pd
import pytest

from market_lab.data import Provenance
from market_lab.smoke import check_provider, main


class MockProvider:
    def fetch(self,symbol,start,end,*,adjustment):
        dates=xcals.get_calendar('XNYS').sessions_in_range(start,end).tz_localize(None)
        price=100. if adjustment=='raw' else 98.
        frame=pd.DataFrame({'open':price,'close':price,'high':price+1,'low':price-1,'volume':10000.},index=dates)
        # These metadata imitate the real adapter only to exercise harness assertions.
        meta=Provenance('Alpaca','stocks/v2 daily IEX','IEX only, not consolidated SIP',adjustment,'2024-04-08T00:00:00Z','MOCK RESPONSE ONLY',request_start=start,request_end=end,source_url=f'https://data.alpaca.markets/v2/stocks/{symbol}/bars')
        return frame,meta


def test_smoke_verifies_calendar_holiday_dst_and_provenance():
    report=check_provider(MockProvider(),'SPY','2024-03-01','2024-04-05')
    assert report['status']=='passed_provider_checks'
    assert report['session_count']==25
    assert '2024-03-29' not in report['adjustment_comparison']['changed_session_dates']
    assert report['adjustment_comparison']['ohlc_changed_sessions']==25
    assert report['provenance']['raw']['adjustment']=='raw'
    assert report['provenance']['all']['adjustment']=='all'
    assert report['executable_price_simulation'] is False


@pytest.mark.parametrize('fault',['missing_session','fixture','wrong_adjustment','wrong_request','missing_timezone'])
def test_smoke_fails_bad_data_or_provenance(fault):
    class BadProvider(MockProvider):
        def fetch(self,*args,**kwargs):
            frame,meta=super().fetch(*args,**kwargs)
            if fault=='missing_session': frame=frame.drop(frame.index[3])
            if fault=='fixture': meta=replace(meta,fixture=True)
            if fault=='wrong_adjustment': meta=replace(meta,adjustment='unknown')
            if fault=='wrong_request': meta=replace(meta,request_end='2024-01-01')
            if fault=='missing_timezone': meta=replace(meta,retrieved_at='2024-04-08T00:00:00')
            return frame,meta
    with pytest.raises(ValueError):
        check_provider(BadProvider(),'SPY','2024-03-01','2024-04-05')


def test_identical_adjustments_are_inconclusive():
    class Identical(MockProvider):
        def fetch(self,symbol,start,end,*,adjustment):
            frame,meta=super().fetch(symbol,start,end,adjustment='raw')
            return frame,replace(meta,adjustment=adjustment)
    assert check_provider(Identical(),'SPY','2024-03-01','2024-04-05')['status']=='inconclusive_adjustment'


def test_missing_keys_block_before_any_request(tmp_path,monkeypatch):
    monkeypatch.delenv('APCA_API_KEY_ID',raising=False)
    monkeypatch.delenv('APCA_API_SECRET_KEY',raising=False)
    path=tmp_path/'evidence.json'
    monkeypatch.setattr(sys,'argv',['smoke','--start','2024-03-01','--end','2024-04-05','--evidence',str(path)])
    monkeypatch.setattr('market_lab.smoke.AlpacaDaily',lambda: pytest.fail('No request without credentials'))
    assert main()==2
    assert json.loads(path.read_text())['status']=='blocked_missing_credentials'


@pytest.mark.parametrize('adjustment',['raw','all'])
def test_actual_adapter_preserves_dst_session_dates_and_request(monkeypatch,adjustment):
    from market_lab.data import AlpacaDaily
    class Response:
        def raise_for_status(self): pass
        def json(self):
            return {'bars':[dict(t=stamp,o=100,h=101,l=99,c=100,v=1000) for stamp in ['2024-03-08T05:00:00Z','2024-03-11T04:00:00Z']]}
    def get(url,**kwargs):
        assert url=='https://data.alpaca.markets/v2/stocks/SPY/bars'
        assert kwargs['params']['adjustment']==adjustment
        assert kwargs['params']['feed']=='iex'
        return Response()
    monkeypatch.setenv('APCA_API_KEY_ID','TEST_ONLY')
    monkeypatch.setenv('APCA_API_SECRET_KEY','TEST_ONLY')
    monkeypatch.setattr('market_lab.data.requests.get',get)
    frame,meta=AlpacaDaily().fetch('SPY','2024-03-08','2024-03-11',adjustment=adjustment)
    assert list(frame.index)==[pd.Timestamp('2024-03-08'),pd.Timestamp('2024-03-11')]
    assert meta.request_start=='2024-03-08' and meta.request_end=='2024-03-11'
    assert meta.adjustment==adjustment and meta.source_url.endswith('/SPY/bars')


def test_adapter_does_not_silently_normalize_intraday_bar(monkeypatch):
    from market_lab.data import AlpacaDaily
    class Response:
        def raise_for_status(self): pass
        def json(self):
            return {'bars':[dict(t='2024-03-08T15:00:00Z',o=100,h=101,l=99,c=100,v=1000)]}
    monkeypatch.setenv('APCA_API_KEY_ID','TEST_ONLY')
    monkeypatch.setenv('APCA_API_SECRET_KEY','TEST_ONLY')
    monkeypatch.setattr('market_lab.data.requests.get',lambda *args,**kwargs: Response())
    with pytest.raises(ValueError,match='session midnight'):
        AlpacaDaily().fetch('SPY','2024-03-08','2024-03-08')


def test_request_failure_evidence_never_emits_exception_contents(tmp_path,monkeypatch,capsys):
    monkeypatch.setenv('APCA_API_KEY_ID','TEST_KEY_SENTINEL')
    monkeypatch.setenv('APCA_API_SECRET_KEY','TEST_SECRET_SENTINEL')
    def fail(*args,**kwargs):
        raise RuntimeError('TEST_SECRET_SENTINEL in provider error body')
    monkeypatch.setattr('market_lab.smoke.check_provider',fail)
    path=tmp_path/'failed.json'
    monkeypatch.setattr(sys,'argv',['smoke','--start','2024-03-01','--end','2024-04-05','--evidence',str(path)])
    assert main()==1
    payload=json.loads(path.read_text())
    assert payload=={'status':'failed','error_type':'RuntimeError'}
    assert 'TEST_SECRET_SENTINEL' not in capsys.readouterr().out
    assert 'TEST_SECRET_SENTINEL' not in path.read_text()
