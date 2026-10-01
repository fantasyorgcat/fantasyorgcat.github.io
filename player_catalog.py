"""Comparison values from the same already-ranked population used by the report."""
import math
import pandas as pd

METRICS=['MIN','PTS','REB','AST','3PM','STL','BLK','FG%','FT%','TO']
RANK_METRICS=[metric for metric in METRICS if metric != 'MIN']
COUNTING={'PTS','REB','AST','3PM','STL','BLK','TO'}

def metric_pr(values, metric):
    return values.rank(pct=True,ascending=metric!='TO')*100

def add_pr_ranks(pool):
    """Rank the full period population by nine PRs including TO, excluding minutes."""
    for mode in ['avg','tot']:
        keys=[m+('_TOT_PR' if mode=='tot' and m in COUNTING else '_PR') for m in RANK_METRICS]
        values=pool.reindex(columns=keys)
        if not values.empty and not values.apply(lambda col: col.dropna().map(math.isfinite).all()).all():
            raise ValueError('Nonfinite PR cannot be ranked')
        suffix='_TOT' if mode=='tot' else ''
        pool['PR_SUM'+suffix]=values.sum(axis=1,min_count=len(RANK_METRICS))
        pool['PR_RANK'+suffix]=pool['PR_SUM'+suffix].rank(method='min',ascending=False)
    return pool

def number(value):
    if value is None or pd.isna(value):return None
    value=float(value)
    if not math.isfinite(value):raise ValueError('Invalid comparison statistic')
    return value

def build_catalog(frame):
    catalog={}
    for row in frame.to_dict('records'):
        pid=str(int(row['PLAYER_ID']))
        if pid in catalog:raise ValueError('Duplicate comparison player ID')
        player=dict(id=pid,name=str(row['PLAYER_NAME']),team=str(row['TEAM_ABBREVIATION']),periods={})
        for period,suffix in [('season',''),('l7','_L7'),('l14','_L14'),('ls','_LS')]:
            modes={}
            for mode in ['avg','tot']:
                cells={}
                for metric in METRICS:
                    summed=mode=='tot' and metric in COUNTING
                    key=metric+'_TOT' if summed else metric
                    if metric in ['FG%','FT%']:
                        value=number(row.get({'FG%':'FG_PCT','FT%':'FT_PCT'}[metric]+suffix))
                        if value is not None:value*=100
                    else:value=number(row.get(key+suffix))
                    pr=number(row.get(metric+('_TOT_PR' if summed else '_PR')+suffix)) if value is not None else None
                    cells[metric]=dict(value=value,pr=pr)
                rank_suffix='_TOT' if mode=='tot' else ''
                cells['Rank']=dict(value=number(row.get('PR_RANK'+rank_suffix+suffix)),pr=None,
                    sum=number(row.get('PR_SUM'+rank_suffix+suffix)))
                modes[mode]=cells
            player['periods'][period]=dict(gp=number(row.get('GP'+suffix)),**modes)
        catalog[pid]=player
    return catalog
