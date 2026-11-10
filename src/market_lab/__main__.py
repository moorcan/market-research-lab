"""Repeatable local retrieval and historical research commands."""
import argparse
import json
from dataclasses import asdict
import pandas as pd
from .data import AlpacaDaily, Store, UNIVERSE
from .strategies import Strategy
from .backtest import run, Costs, metrics, trade_statistics
from .experiments import record


def main():
    parser = argparse.ArgumentParser(description='Research only; never submits orders')
    parser.add_argument('--data-dir',default='data')
    sub = parser.add_subparsers(dest='command',required=True)
    fetch = sub.add_parser('fetch')
    fetch.add_argument('symbol',choices=UNIVERSE)
    fetch.add_argument('start')
    fetch.add_argument('end')
    test = sub.add_parser('backtest')
    test.add_argument('version')
    test.add_argument('--strategy',choices=['trend','mean_reversion'],default='trend')
    test.add_argument('--window',type=int,default=50)
    test.add_argument('--threshold',type=float,default=.03)
    test.add_argument('--cash',type=float,default=2700)
    test.add_argument('--fee-bps',type=float,default=1)
    test.add_argument('--spread-bps',type=float,default=5)
    test.add_argument('--slippage-bps',type=float,default=5)
    test.add_argument('--reports-dir',default='reports')
    args = parser.parse_args()
    store = Store(args.data_dir)
    if args.command == 'fetch':
        start,end=pd.Timestamp(args.start),pd.Timestamp(args.end)
        if start > end or end >= pd.Timestamp.now(tz='America/New_York').tz_localize(None).normalize():
            parser.error('Use ordered completed historical dates')
        bars,meta=AlpacaDaily().fetch(args.symbol,start.date().isoformat(),end.date().isoformat())
        print(store.save(args.symbol,bars,meta))
    else:
        bars,meta=store.load(args.version)
        strategy=Strategy(args.strategy,args.window,args.threshold)
        costs=Costs(args.fee_bps,args.spread_bps,args.slippage_bps)
        result=run(bars,strategy.signals(bars),args.cash,costs)
        passive=run(bars,pd.Series(1.,index=bars.index),args.cash,costs)
        identifier=record(args.reports_dir,args.version,meta,strategy,costs,result)
        print(json.dumps({'status':'TEST FIXTURE ONLY' if meta.fixture else 'exploratory historical simulation; not holdout validated','experiment':identifier,'strategy':metrics(result),'passive':metrics(passive),'exits':trade_statistics(result),'beats_passive_and_cash':bool(result.equity.iloc[-1]>max(passive.equity.iloc[-1],args.cash))},indent=2,allow_nan=False))

if __name__ == '__main__':
    main()
