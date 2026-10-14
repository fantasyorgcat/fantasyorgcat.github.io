"""ROTO reference helpers and legacy fixtures; missing shots are never inferred from rates."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import statistics

COUNTING = ['PTS','REB','AST','3PM','STL','BLK','TO']
SHOTS = ['FGM','FGA','FTM','FTA']
METRICS = COUNTING[:6]+['FG%','FT%','TO']


def numeric(value):
    if value is None:return None
    if isinstance(value,bool):raise ValueError('Boolean is not a ROTO statistic')
    value=float(value)
    if not math.isfinite(value) or value<0:raise ValueError('Invalid ROTO source value')
    return value


def records_from_catalog(catalog,period_key="ls"):
    result={}
    for pid,p in catalog.items():
        period=p['periods'][period_key]
        result[pid]=dict(id=pid,name=p['name'],team=p['team'],gp=numeric(period['gp']),
            minutes=numeric(period['avg']['MIN']['value']),
            totals={key:numeric(period['tot'][key]['value']) for key in COUNTING},
            shots={key:numeric(period.get('shooting',{}).get(key)) for key in SHOTS})
    return result


def source_reference(frame):
    rows=[]
    for p in frame.to_dict('records'):
        def n(key):
            v=p.get(key)
            return None if v is None or (isinstance(v,float) and math.isnan(v)) else numeric(v)
        rows.append(dict(id=str(int(p['PLAYER_ID'])),gp=n('GP'),
            totals={key:n(('FG3M' if key=='3PM' else key)+'_TOTAL') for key in COUNTING},
            shots={key:n(key) for key in SHOTS}))
    return rows


def benchmark(reference):
    result={'perGame':{},'totals':{}}
    for mode in result:
        for key in COUNTING:
            values=[r['totals'][key]/(r['gp'] if mode=='perGame' else 1) for r in reference
                    if r['gp'] and r['gp']>0 and r['totals'].get(key) is not None]
            result[mode][key]=dict(mean=statistics.mean(values) if values else None,
                sd=statistics.pstdev(values) if values else None,samples=len(values))
        for prefix in ['FG','FT']:
            pairs=[(r['shots'].get(prefix+'M'),r['shots'].get(prefix+'A'),r['gp']) for r in reference]
            pairs=[(m/(gp if mode=='perGame' else 1),a/(gp if mode=='perGame' else 1)) for m,a,gp in pairs if m is not None and a is not None and a>0 and gp and gp>0]
            mean=100*sum(m for m,a in pairs)/sum(a for m,a in pairs) if pairs else None
            sd=math.sqrt(sum(a*(100*m/a-mean)**2 for m,a in pairs)/sum(a for m,a in pairs)) if pairs else None
            result[mode][prefix+'%']=dict(mean=mean,sd=sd,samples=len(pairs))
    return result


def build_data(catalog,snapshot,reference=None,season=None):
    players=records_from_catalog(catalog)
    reference=reference if reference is not None else [p for p in players.values() if p['gp'] and p['gp']>0]
    reference=sorted([dict(id=str(p['id']),gp=p['gp'],totals=dict(p['totals']),shots=dict(p['shots'])) for p in reference],key=lambda p:int(p['id']))
    expected=snapshot['period_populations']['LastSeason']
    source_period=snapshot['players_'+str(int(snapshot['schedule']['season'][:4]))]
    season=season or source_period['season']
    if source_period.get('season') and source_period['season']!=season:raise ValueError('ROTO season mismatch')
    fixture=bool(snapshot.get('fixture'))
    if len({p['id'] for p in reference})!=len(reference):raise ValueError('Duplicate ROTO reference ID')
    if any(not p['gp'] or p['gp']<=0 for p in reference):raise ValueError('Reference requires actual player appearances')
    for p in [*players.values(),*reference]:
        if p['gp'] is not None and not float(p['gp']).is_integer():raise ValueError('Player appearances must be integers')
        for key,v in p['shots'].items():
            if v is not None and not float(v).is_integer():raise ValueError('Shooting totals must be integers')
        for prefix in ['FG','FT']:
            m,a=p['shots'].get(prefix+'M'),p['shots'].get(prefix+'A')
            if m is not None and a is not None and m>a:raise ValueError('Shooting makes exceed attempts')
    complete=sum(all(p['shots'].get(k) is not None for k in SHOTS) for p in reference)
    return dict(version=1,season=season,fixture=fixture,
        generated_at=snapshot['generated_at'],source=snapshot['stats_source'],
        source_period={k:snapshot['players_'+str(int(snapshot['schedule']['season'][:4]))].get(k) for k in ['source_period_start','source_period_end']},
        data_ready=not fixture and len(reference)==expected and expected>0 and complete==expected,
        reference=dict(size=len(reference),expected=expected,shooting_complete=complete,
            id='last-season-v1:'+season+':'+hashlib.sha256(json.dumps(reference,sort_keys=True,allow_nan=False).encode()).hexdigest()[:12],records=reference,scale='50 + 15 × z; clipped 0–100; counting uses roster average per member; TO reversed'),
        benchmark=benchmark(reference),players=players)


def write_data(data,path='roto_data.js'):
    Path(path).write_text('window.ROTO_DATA = '+json.dumps(data,ensure_ascii=False,allow_nan=False).replace('<','\\u003c')+';\n')


def read_report(path):
    html=Path(path).read_text()
    match=re.search(r'var playerCatalog = (.*?);\s*\n',html)
    if not match:raise ValueError('Report player catalog absent')
    return json.loads(match[1])


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--from-report',default='index.html');parser.add_argument('--output',default='roto_data.js');parser.add_argument('--legacy-espn',action='store_true');args=parser.parse_args()
    if args.legacy_espn:data=build_data(read_report(args.from_report),json.loads(Path('data_snapshot.json').read_text()))
    else:
        from roto_package import build_package
        data=build_package(read_report(args.from_report),json.loads(Path('data_snapshot.json').read_text()))
    write_data(data,args.output)
    summary={k:data[k] for k in ['season','generated_at','data_ready']};summary['reference']={k:v for k,v in data['reference'].items() if k!='records'}
    print(json.dumps(summary,ensure_ascii=False))
