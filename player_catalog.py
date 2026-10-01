"""Comparison values from the same already-ranked population used by the report."""
import math
import pandas as pd

METRICS=['MIN','PTS','REB','AST','3PM','STL','BLK','FG%','FT%']
COUNTING={'PTS','REB','AST','3PM','STL','BLK'}

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
                modes[mode]=cells
            player['periods'][period]=dict(gp=number(row.get('GP'+suffix)),**modes)
        catalog[pid]=player
    return catalog
