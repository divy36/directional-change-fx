"""Run the frozen candidate once on the predeclared retrospective holdout panel."""
from pathlib import Path
import argparse
import hashlib
import json
import sys
import zipfile
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from dc_fx.backtest import Config, SCALES, Result, run_strategy
from dc_fx.data import load_ticks
from dc_fx.metrics import performance, daily_equity
from reversal_execution import trace_orders, replay



def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--selection', type=Path, default=ROOT/'results/reversal/selected.json')
    parser.add_argument('--archive-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=Path('output/reversal-validation'))
    args=parser.parse_args()
    OUT=args.output
    DATA=args.archive_root
    OUT.mkdir(parents=True, exist_ok=True)
    selection_bytes=args.selection.read_bytes()
    choice=json.loads(selection_bytes)
    (OUT/'frozen_selection.json').write_bytes(selection_bytes)
    plan=json.loads((ROOT/'results/reversal/validation_plan.json').read_text())
    records=[]
    for ds in plan['validation']:
        month=ds.split('-')[1]
        archive=DATA/f'HISTDATA_COM_ASCII_EURUSD_T{month}.zip'
        with zipfile.ZipFile(archive) as z:
            names=[n for n in z.namelist() if n.endswith('.csv')]
            assert len(names)==1, names
            with z.open(names[0]) as member:
                ticks,audit=load_ticks(member)
        p=ticks.mid.to_numpy()
        half=(ticks.ask.to_numpy()-ticks.bid.to_numpy())/2
        curves={k:np.zeros(len(p)) for k in ['original','reverse_only','candidate_fixed','candidate_double_cost','candidate_quotes','candidate_quotes_next_tick']}
        counts={k:0 for k in curves}
        configs=[Config(theta_up=u*choice['threshold_multiplier'],theta_down=d*choice['threshold_multiplier'],
                        osv_levels=tuple(choice['osv_levels']),inventory_adjustment=choice['inventory_adjustment'],execution_sign=-1)
                 for u,d in SCALES]
        modes=[('candidate_fixed',np.full(len(p),.00002),0),('candidate_double_cost',np.full(len(p),.00004),0),
               ('candidate_quotes',half,0),('candidate_quotes_next_tick',half,1)]
        for scale,cfg in enumerate(configs):
            orders=trace_orders(p,cfg)
            for label,spread,delay in modes:
                eq,ledger=replay(p,spread,orders,delay)
                if ds==plan['validation'][0] and label=='candidate_fixed':
                    expected=run_strategy(p,ticks.index,cfg)
                    np.testing.assert_allclose(eq,expected.equity,atol=1e-11,rtol=0)
                    assert len(ledger)==len(expected.trades)
                curves[label]+=eq/len(configs)
                counts[label]+=len(ledger)
            cfg=Config(theta_up=SCALES[scale][0],theta_down=SCALES[scale][1])
            original=trace_orders(p,cfg)
            for label,orders in [('original',original),('reverse_only',[(i,k,-d,u) for i,k,d,u in original])]:
                eq,ledger=replay(p,np.full(len(p),.00002),orders)
                curves[label]+=eq/len(configs)
                counts[label]+=len(ledger)
        for label,eq in curves.items():
            metrics=performance(Result(pd.DataFrame(index=range(counts[label])),eq),ticks.index)
            record={'dataset':ds,'variant':label,**metrics,**audit,
                    'selection_sha256':hashlib.sha256(selection_bytes).hexdigest(),
                    'archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),
                    'start':str(ticks.index[0]),'end':str(ticks.index[-1]),
                    'median_spread_pips':float(np.median(half)*2/1e-4),
                    'p99_spread_pips':float(np.quantile(half,.99)*2/1e-4)}
            records.append(record)
            daily_equity(eq,ticks.index).to_csv(OUT/f'{ds}_{label}_daily.csv',index_label='date')
        pd.DataFrame(records).to_csv(OUT/'holdout_results.csv',index=False)
        print(json.dumps({'dataset':ds,'ticks':len(p),**{r['variant']:r['return_pct'] for r in records if r['dataset']==ds}}),flush=True)
    results=pd.DataFrame(records)
    summary=results.groupby('variant').agg(mean_month_return_pct=('return_pct','mean'),positive_months=('return_pct',lambda x:int((x>0).sum())),worst_month_pct=('return_pct','min'),worst_drawdown_pct=('max_drawdown_pct','min'),total_trades=('trades','sum'))
    summary.to_csv(OUT/'summary.csv')
    print(summary.to_string(),flush=True)

if __name__=='__main__':
    main()
