"""Synthetic fixtures only: retention/quality contracts, not Robinhood responses."""
from dataclasses import replace
import json

import pandas as pd
import pytest

from market_lab.backtest import run
from market_lab.comparison import compare_datasets
from market_lab.data import Provenance, Store, validate


@pytest.fixture
def annotated():
    dates=pd.DatetimeIndex(['2024-03-08','2024-03-11','2024-03-12'])
    bars=pd.DataFrame({'open':100.,'high':101.,'low':99.,'close':100.,'volume':1000.},index=dates)
    bars['provider_timestamp']=pd.to_datetime(['2024-03-08T05:00:00Z','2024-03-11T04:00:00Z','2024-03-12T04:00:00Z'],utc=True)
    bars['is_interpolated']=pd.array([False,True,pd.NA],dtype='boolean')
    meta=Provenance('TEST FIXTURE','synthetic','none','all','2024-03-13T00:00:00Z','TEST ONLY',True,symbol='SPY',session_timezone='America/New_York',timestamp_semantics='bar start; not first-public availability',interpolation_policy='source flags preserved, including unknown')
    return bars,meta


def test_parquet_duckdb_retains_source_metadata_and_flags(tmp_path,annotated):
    bars,meta=annotated
    store=Store(tmp_path)
    version=store.save('SPY',bars,meta)
    restored,provenance=store.load(version)
    pd.testing.assert_frame_equal(restored,bars.rename_axis('session'))
    assert provenance==meta
    assert restored.is_interpolated.tolist()[:2]==[False,True]
    assert pd.isna(restored.is_interpolated.iloc[2])
    catalog=json.loads(store.versions().iloc[0].metadata)
    assert catalog['session_timezone']=='America/New_York'
    assert catalog['adjustment']=='all'
    assert catalog['timestamp_semantics']==meta.timestamp_semantics


def test_interpolation_changes_dataset_version(tmp_path,annotated):
    bars,meta=annotated
    store=Store(tmp_path)
    first=store.save('SPY',bars,meta)
    changed=bars.copy();changed.iloc[1,changed.columns.get_loc('is_interpolated')]=False
    second=store.save('SPY',changed,meta)
    assert first!=second
    assert store.load(first)[0].is_interpolated.iloc[1]


def test_known_interpolation_is_stored_but_refused_for_backtests(annotated):
    bars,_=annotated
    validate(bars)
    with pytest.raises(ValueError,match='Interpolated'):
        run(bars,pd.Series(1.,index=bars.index))


def test_unknown_interpolation_stays_unknown_not_false(annotated):
    bars,_=annotated
    bars=bars.copy();bars['is_interpolated']=pd.array([pd.NA]*len(bars),dtype='boolean')
    result=run(bars,pd.Series(0.,index=bars.index))
    assert result.equity.eq(2700).all()
    assert bars.is_interpolated.isna().all()


@pytest.mark.parametrize('fault',['naive','missing','wrong_session','string_flags'])
def test_bad_timestamp_or_flag_metadata_rejected(annotated,fault):
    bars,_=annotated
    bars=bars.copy()
    if fault=='naive': bars['provider_timestamp']=bars.provider_timestamp.dt.tz_localize(None)
    if fault=='missing': bars.iloc[0,bars.columns.get_loc('provider_timestamp')]=pd.NaT
    if fault=='wrong_session': bars.iloc[0,bars.columns.get_loc('provider_timestamp')]=pd.Timestamp('2024-03-11T04:00:00Z')
    if fault=='string_flags': bars['is_interpolated']=['false','true','unknown']
    with pytest.raises(ValueError): validate(bars)


def test_comparison_exposes_interpolation_and_unknown_counts(annotated):
    bars,meta=annotated
    report=compare_datasets(bars,meta,bars,meta,'2024-03-08','2024-03-12')
    for dataset in report['datasets']:
        assert dataset['interpolated_sessions']==1
        assert dataset['interpolation_unknown_sessions']==1
        assert dataset['provider_timestamps_preserved']
    assert not report['research_ready']
