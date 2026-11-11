"""Offline provider/safety proof only. No real Robinhood tool names or market data."""
from dataclasses import replace
from types import MappingProxyType
import pytest
import pandas as pd

from market_lab.data import Provenance, Store
from market_lab.providers.routing import ResearchDataService, ProviderUnavailable
from market_lab.providers.robinhood import (
    ResearchOperation, ReadOnlyResearchGateway, RobinhoodDaily, ReviewedReadBinding,
)
from market_lab.comparison import compare_datasets
from market_lab.serialization import dumps


@pytest.fixture
def dataset():
    dates=pd.DatetimeIndex(['2024-03-08','2024-03-11','2024-03-12'])
    bars=pd.DataFrame({'open':100.,'close':100.,'high':101.,'low':99.,'volume':1000.},index=dates)
    meta=Provenance('TEST FIXTURE','synthetic','TEST ONLY','all','2024-03-13T00:00:00Z','No market findings',True,symbol='SPY')
    return bars,meta


class SpyTransport:
    def __init__(self): self.calls=[]
    def invoke_reviewed_tool(self,name,arguments):
        self.calls.append((name,arguments))
        return {'fixture':True}


@pytest.mark.parametrize('operation',list(ResearchOperation))
def test_no_unverified_operation_reaches_transport(operation):
    spy=SpyTransport()
    with pytest.raises(ProviderUnavailable):
        ReadOnlyResearchGateway(spy).read(operation,{'symbol':'SPY'})
    assert spy.calls==[]


@pytest.mark.parametrize('name',['place_order','modify_order','cancel_order','submit_order','transfer_funds','get_account','get_positions','historical_equity_prices','readOnlyHint'])
def test_arbitrary_tool_strings_never_grant_permission(name):
    spy=SpyTransport()
    with pytest.raises(PermissionError):
        ReadOnlyResearchGateway(spy).read(name,{})
    assert spy.calls==[]


def test_allowlist_cannot_be_mutated_from_discovery():
    from market_lab.providers.robinhood import READ_ONLY_BINDINGS
    with pytest.raises(TypeError):
        READ_ONLY_BINDINGS[ResearchOperation.HISTORICAL_EQUITY_PRICES]='server_claims_read_only'


def test_offline_reviewed_binding_validates_before_transport(monkeypatch):
    # Hypothetical test binding ONLY, not a real Robinhood operation/schema.
    def validate(arguments):
        if set(arguments)!={'symbol'} or arguments['symbol']!='SPY':
            raise ValueError('Fixture schema rejected arguments')
    binding=ReviewedReadBinding('FIXTURE_ONLY_daily_bars',validate,'https://example.invalid/TEST_ONLY','TEST_ONLY')
    monkeypatch.setattr('market_lab.providers.robinhood.READ_ONLY_BINDINGS',MappingProxyType({ResearchOperation.HISTORICAL_EQUITY_PRICES:binding}))
    spy=SpyTransport()
    gateway=ReadOnlyResearchGateway(spy)
    with pytest.raises(ValueError):
        gateway.read(ResearchOperation.HISTORICAL_EQUITY_PRICES,{'symbol':'SPY','action':'place_order'})
    assert spy.calls==[]
    assert gateway.read(ResearchOperation.HISTORICAL_EQUITY_PRICES,{'symbol':'SPY'})=={'fixture':True}
    assert spy.calls==[('FIXTURE_ONLY_daily_bars',{'symbol':'SPY'})]


def test_explicit_fallback_preserves_source_provenance(dataset):
    class Fixture:
        def fetch(self,*args): return dataset
    service=ResearchDataService({'candidate':RobinhoodDaily(),'fixture':Fixture()})
    with pytest.raises(ProviderUnavailable): service.fetch('candidate','SPY','2024-03-08','2024-03-12')
    result=service.fetch('candidate','SPY','2024-03-08','2024-03-12',fallback='fixture')
    assert result.used_fallback and result.requested_provider=='candidate' and result.selected_provider=='fixture'
    assert result.provenance.provider=='TEST FIXTURE'


def test_validation_errors_never_trigger_fallback(dataset):
    class Bad:
        def fetch(self,*args): raise ValueError('Invalid provider data')
    class Fallback:
        def fetch(self,*args): pytest.fail('Must not mask corrupt data')
    service=ResearchDataService({'bad':Bad(),'fallback':Fallback()})
    with pytest.raises(ValueError,match='Invalid provider data'):
        service.fetch('bad','SPY','2024-03-08','2024-03-12',fallback='fallback')


def test_comparison_reports_observed_differences_without_accuracy_claim(dataset):
    bars,meta=dataset
    other=bars.copy();other['close']=100.5
    report=compare_datasets(bars,meta,other,meta,'2024-03-08','2024-03-12')
    assert report['fixture'] and not report['research_ready']
    assert report['common_sessions']==3
    assert report['differences']['ohlc_differing_sessions']==3
    assert report['differences']['max_absolute_price_difference']==.5
    assert 'No accuracy winner' in report['interpretation']
    assert 'NaN' not in dumps(report)


def test_comparison_exposes_truncated_ranges(dataset):
    bars,meta=dataset
    report=compare_datasets(bars,meta,bars.iloc[1:],meta,'2024-03-08','2024-03-12')
    assert not report['datasets'][1]['complete_requested_range']
    assert report['datasets'][1]['missing_sessions']==['2024-03-08']
    assert report['common_sessions']==2


@pytest.mark.parametrize('change',[{'symbol':'QQQ'},{'symbol':None},{'adjustment':'raw'},{'adjustment':'unknown'}])
def test_comparison_rejects_incompatible_datasets(dataset,change):
    bars,meta=dataset
    with pytest.raises(ValueError):
        compare_datasets(bars,meta,bars,replace(meta,**change),'2024-03-08','2024-03-12')


def test_store_stamps_symbol_and_rejects_conflicting_identity(tmp_path,dataset):
    bars,meta=dataset
    store=Store(tmp_path)
    version=store.save('SPY',bars,replace(meta,symbol=None))
    assert store.load(version)[1].symbol=='SPY'
    with pytest.raises(ValueError,match='symbol'):
        store.save('QQQ',bars,meta)


def test_dashboard_robinhood_selection_never_silently_calls_alpaca(tmp_path,monkeypatch):
    from pathlib import Path
    from streamlit.testing.v1 import AppTest
    def forbidden(*args,**kwargs): pytest.fail('Implicit Alpaca access is forbidden')
    monkeypatch.setattr('market_lab.data.AlpacaDaily.fetch',forbidden)
    monkeypatch.chdir(tmp_path)
    path=Path(__file__).resolve().parents[1]/'app.py'
    app=AppTest.from_file(str(path)).run(timeout=15)
    app.selectbox[0].set_value('robinhood_mcp').run(timeout=15)
    assert app.checkbox[0].value is False
    app.button[0].click().run(timeout=15)
    assert not app.exception
    assert any('ProviderUnavailable' in error.value for error in app.error)
    assert Store().versions().empty


def test_cli_explicit_fallback_is_reported(tmp_path,monkeypatch,capsys,dataset):
    import sys,json
    from market_lab.__main__ import main
    class Fixture:
        def fetch(self,*args): return dataset
    monkeypatch.setattr('market_lab.__main__.AlpacaDaily',Fixture)
    monkeypatch.setattr(sys,'argv',['market_lab','--data-dir',str(tmp_path),'fetch','SPY','2024-03-08','2024-03-12','--provider','robinhood_mcp','--fallback','alpaca'])
    main()
    report=json.loads(capsys.readouterr().out)
    assert report['requested_provider']=='robinhood_mcp'
    assert report['selected_provider']=='alpaca' and report['used_fallback']
    assert Store(tmp_path).load(report['dataset_version'])[1].provider=='TEST FIXTURE'


def test_comparison_cli_retains_versions_and_fixture_label(tmp_path,monkeypatch,capsys,dataset):
    import sys,json
    from market_lab.comparison import main
    bars,meta=dataset
    store=Store(tmp_path/'data')
    left=store.save('SPY',bars,meta)
    right=store.save('SPY',bars,replace(meta,provider='SECOND TEST FIXTURE'))
    output=tmp_path/'comparison.json'
    monkeypatch.setattr(sys,'argv',['comparison','--data-dir',str(tmp_path/'data'),'--left-version',left,'--right-version',right,'--start','2024-03-08','--end','2024-03-12','--output',str(output)])
    main()
    report=json.loads(output.read_text())
    assert report['dataset_versions']==[left,right]
    assert report['fixture'] and not report['research_ready']
    assert json.loads(capsys.readouterr().out)==report
