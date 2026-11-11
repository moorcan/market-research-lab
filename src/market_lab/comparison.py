"""Coverage/consistency diagnostics. Differences do not establish data accuracy."""
from dataclasses import asdict
import argparse
from pathlib import Path

import exchange_calendars as xcals
import numpy as np
import pandas as pd

from .data import Provenance, Store, validate
from .serialization import dumps


def compare_datasets(left, left_meta, right, right_meta, start, end):
    if not left_meta.symbol or left_meta.symbol != right_meta.symbol:
        raise ValueError("Comparison requires the same verified instrument symbol")
    if left_meta.adjustment != right_meta.adjustment or left_meta.adjustment not in ('raw','all'):
        raise ValueError('Comparison requires matching, known adjustment modes')
    expected = xcals.get_calendar('XNYS').sessions_in_range(start,end).tz_localize(None)
    if expected.empty:
        raise ValueError('Range must contain trading sessions')
    quality = []
    for frame, meta in ((left,left_meta),(right,right_meta)):
        # First validate complete returned data; completeness against requested
        # bounds is separately diagnosed below, never silently filled.
        validate(frame)
        missing = expected.difference(frame.index)
        unexpected = frame.index.difference(expected)
        quality.append({
            'provider':meta.provider, 'sessions_returned':len(frame),
            'missing_sessions':[str(day.date()) for day in missing],
            'unexpected_sessions':[str(day.date()) for day in unexpected],
            'complete_requested_range':len(missing)==0 and len(unexpected)==0,
            'provenance':asdict(meta),
        })
    common = expected.intersection(left.index).intersection(right.index)
    differences = None
    if len(common):
        a=left.loc[common,['open','high','low','close']].to_numpy()
        b=right.loc[common,['open','high','low','close']].to_numpy()
        differences={
            'ohlc_differing_sessions':int((~np.isclose(a,b,rtol=1e-7,atol=1e-8).all(axis=1)).sum()),
            'max_absolute_price_difference':float(np.abs(a-b).max()),
            'max_absolute_relative_price_difference_vs_left':float((np.abs(a-b)/a).max()),
            'volume_differing_sessions':int((left.loc[common].volume!=right.loc[common].volume).sum()),
        }
    return {
        'status':'coverage_and_consistency_only',
        'fixture':bool(left_meta.fixture or right_meta.fixture),
        'symbol':left_meta.symbol, 'requested_range':[start,end], 'expected_sessions':len(expected),
        'common_sessions':len(common), 'datasets':quality, 'differences':differences,
        'interpretation':'No accuracy winner inferred. Exchange coverage, adjustment conventions and retrieval vintages may differ. Independent reference reconciliation is required.',
        'research_ready':False,
    }


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir',default='data')
    parser.add_argument('--left-version',required=True)
    parser.add_argument('--right-version',required=True)
    parser.add_argument('--start',required=True)
    parser.add_argument('--end',required=True)
    parser.add_argument('--output',default='reports/provider-comparison.json')
    args=parser.parse_args()
    store=Store(args.data_dir)
    left,lmeta=store.load(args.left_version)
    right,rmeta=store.load(args.right_version)
    result=compare_datasets(left,lmeta,right,rmeta,args.start,args.end)
    result['dataset_versions']=[args.left_version,args.right_version]
    path=Path(args.output)
    path.parent.mkdir(parents=True,exist_ok=True)
    text=dumps(result,indent=2)
    path.write_text(text,encoding='utf-8')
    print(text)


if __name__ == '__main__':
    main()
