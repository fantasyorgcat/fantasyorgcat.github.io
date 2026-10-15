"""Season-aware ROTO data from the existing report pipeline; no network requests."""
import copy
import hashlib
import json
from roto_data import COUNTING, SHOTS, RADAR_SCALE, benchmark, numeric, records_from_catalog
from roto_boxscore import build_boxscore_data, load_source


def live_period(catalog,snapshot,period,season):
    players=records_from_catalog(catalog,period)
    population_key='Season' if period=='season' else 'LastSeason'
    expected=snapshot.get('period_populations',{}).get(population_key,0)
    source_meta=snapshot.get('players_'+str(int(season[:4])+1),{})
    if expected and (source_meta.get('season')!=season or source_meta.get('season_type')!='Regular Season'):
        raise ValueError('ROTO live source season/type mismatch')
    raw=snapshot.get('roto_references',{}).get(population_key)
    reference=copy.deepcopy(raw) if raw is not None else [dict(id=p['id'],gp=p['gp'],totals=p['totals'],shots=p['shots']) for p in players.values() if p['gp'] and p['gp']>0]
    if len({r['id'] for r in reference})!=len(reference):raise ValueError('Duplicate live reference ID')
    for record in [*players.values(),*reference]:
        gp=numeric(record['gp'])
        if gp is not None and not float(gp).is_integer():raise ValueError('Live games must be integer')
        for key in [*COUNTING,*SHOTS]:
            value=numeric(record['totals'].get(key) if key in COUNTING else record['shots'].get(key))
            if value is not None and not value.is_integer():raise ValueError('Live totals must be integer')
        for prefix in ['FG','FT']:
            made,attempts=record['shots'].get(prefix+'M'),record['shots'].get(prefix+'A')
            if made is not None and attempts is not None and made>attempts:raise ValueError('Live makes exceed attempts')
    if any(not r['gp'] or r['gp']<=0 for r in reference):raise ValueError('Reference requires real appearances')
    for r in reference:
        p=players.get(r['id'])
        if p and (p['gp']!=r['gp'] or p['totals']!=r['totals'] or p['shots']!=r['shots']):raise ValueError('Live reference/catalog mismatch')
    reference.sort(key=lambda r:int(r['id']))
    complete=len(reference)==expected and expected>0
    shooting_complete=sum(all(r['shots'].get(k) is not None for k in SHOTS) for r in reference)
    scales=benchmark(reference if complete else [])
    return dict(version=1,season=season,source='ESPN',fixture=bool(snapshot.get('fixture')),generated_at=snapshot['generated_at'],
        source_period={**{k:source_meta.get(k) for k in ['source_period_start','source_period_end']},'timezone':'UTC','stats_through_game':snapshot.get('current_stats_last_game') if period=='season' else None},
        stats_available=any(p['gp'] and p['gp']>0 for p in players.values()),data_ready=complete and shooting_complete==expected,
        reference=dict(size=len(reference),expected=expected,shooting_complete=shooting_complete,
            id='season-v1:'+season+':'+hashlib.sha256(json.dumps(reference,sort_keys=True).encode()).hexdigest()[:12],records=reference,
            scale=RADAR_SCALE),
        benchmark=scales,players=players)


def build_package(catalog,snapshot):
    current=snapshot['schedule']['season'];previous=f'{int(current[:4])-1}-{current[2:4]}'
    archive,manifest=load_source()
    # Archived bytes keep their original season label even after the website rolls over.
    data=build_boxscore_data(catalog,snapshot,archive,manifest,allow_historical=True)
    data['period_key']='ls' if previous==manifest['season'] else 'archive'
    data['catalog']=catalog
    data['extra_periods']={'season':live_period(catalog,snapshot,'season',current)}
    if data['period_key']=='archive':data['extra_periods']['ls']=live_period(catalog,snapshot,'ls',previous)
    data['default_period']='season' if data['extra_periods']['season']['stats_available'] else 'ls' if data['extra_periods'].get('ls',{}).get('stats_available') else data['period_key']
    data['current_season']=current
    return data
