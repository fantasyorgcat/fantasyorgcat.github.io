"""Audited user-provided CC BY 4.0 season CSV; never fetches rejected source URLs."""
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import re
import unicodedata
from roto_data import COUNTING, SHOTS, benchmark, read_report, write_data

ROOT=Path(__file__).resolve().parent
CSV_PATH=ROOT/'data/roto/2025-26-player-season-totals.csv'
MANIFEST_PATH=ROOT/'data/roto/source_manifest.json'
EXPECTED_SHA='629839481dcb087aac9aa27f97fc1ef355cd93bc11e561b598ad680c38e446ee'
FIELDS={'PTS':'points','REB':'rebounds','AST':'assists','3PM':'three_point_makes','STL':'steals','BLK':'blocks','TO':'turnovers',
        'FGM':'field_goals_made','FGA':'field_goal_attempts','FTM':'free_throws_made','FTA':'free_throw_attempts'}
# A single suffix difference, accepted only with exact GP + all seven old totals.
ALIASES={'Bobby Portis':'Bobby Portis Jr.'}


def normalized_name(value):
    value=unicodedata.normalize('NFKD',value).encode('ascii','ignore').decode().casefold()
    return re.sub(r'[^a-z0-9]','',value)


def integer(raw):
    if raw is None or not re.fullmatch(r'\d+',str(raw)):raise ValueError('Source total must be a nonnegative integer')
    return int(raw)


def load_source(csv_path=CSV_PATH,manifest_path=MANIFEST_PATH):
    raw=Path(csv_path).read_bytes();manifest=json.loads(Path(manifest_path).read_text())
    if hashlib.sha256(raw).hexdigest()!=EXPECTED_SHA or manifest['sha256']!=EXPECTED_SHA or len(raw)!=manifest['size_bytes']:
        raise ValueError('Season source byte/hash mismatch')
    rows=list(csv.DictReader(io.StringIO(raw.decode('utf-8-sig'))))
    if len(rows)!=manifest['row_count'] or len(rows[0])!=32:raise ValueError('Season source row/column count mismatch')
    if manifest['season_type']!='Regular Season' or manifest['season']!='2025-26' or manifest['license']!='CC BY 4.0':raise ValueError('Source period/license mismatch')
    result=[];seen=set()
    for row in rows:
        name=row['player_name'];key=normalized_name(name)
        if not name or key in seen:raise ValueError('Duplicate normalized source name')
        seen.add(key)
        if row['season']!=manifest['season']:raise ValueError('Mixed source seasons')
        gp=integer(row['games_played']);values={k:integer(row[v]) for k,v in FIELDS.items()}
        if not 0<gp<=82 or values['FGM']>values['FGA'] or values['FTM']>values['FTA'] or values['3PM']>values['FGM']:
            raise ValueError('Invalid source games/shooting totals')
        if values['PTS']!=2*values['FGM']+values['3PM']+values['FTM']:raise ValueError('Source scoring identity mismatch')
        minutes=float(row['minutes'])
        if not math.isfinite(minutes) or minutes<0:raise ValueError('Invalid source minutes')
        record=dict(id='bsl:'+key,source_name=name,team=row['team'],gp=gp,minutes=minutes/gp,
                    totals={k:values[k] for k in COUNTING},shots={k:values[k] for k in SHOTS},uncertainties={})
        for issue in manifest['uncertainties']:
            if issue['name']==name:
                if record['shots'][issue['field']]!=issue['publisher_value']:raise ValueError('Declared uncertainty no longer matches source')
                record['shots'][issue['field']]=None;record['uncertainties'][issue['field']]=dict(issue)
        result.append(record)
    if sum(bool(r['uncertainties']) for r in result)!=len(manifest['uncertainties']):raise ValueError('Uncertainty declaration not located')
    return result,manifest


def old_differences(player,record):
    period=player['periods']['ls'];result={}
    for key in COUNTING:
        old=period['tot'][key]['value']
        if old is not None and old!=record['totals'][key]:result[key]=[old,record['totals'][key]]
    if period['gp'] is not None and period['gp']!=record['gp']:result['GP']=[period['gp'],record['gp']]
    return result


def build_boxscore_data(catalog,snapshot,source=None,manifest=None,allow_historical=False):
    if source is None:source,manifest=load_source()
    expected_season=f"{int(snapshot['schedule']['season'][:4])-1}-{snapshot['schedule']['season'][2:4]}"
    if not allow_historical and manifest['season']!=expected_season:raise ValueError('Archived ROTO season does not match last season; supply a new audited source')
    source_names={normalized_name(r['source_name']):r for r in source};catalog_names={}
    for p in catalog.values():catalog_names.setdefault(normalized_name(p['name']),[]).append(p)
    players={};mapping=[];matched_source=set();disagreements=[]
    for pid,p in catalog.items():
        key=normalized_name(p['name']);record=source_names.get(key);method='unique_normalized_full_name'
        status='matched'
        if len(catalog_names[key])!=1:record=None;status='ambiguous_name'
        if record is None and status!='ambiguous_name' and p['name'] in ALIASES:
            candidate=source_names.get(normalized_name(ALIASES[p['name']]))
            if candidate and p['periods']['ls']['gp'] is not None and not old_differences(p,candidate):
                record=candidate;method='explicit_suffix_alias_plus_exact_GP_and_seven_totals'
        if record is None and status!='ambiguous_name':status='not_in_source'
        item=dict(id=pid,name=p['name'],team=p['team'],gp=None,minutes=None,
                  totals={k:None for k in COUNTING},shots={k:None for k in SHOTS},uncertainties={},status=status)
        if record is not None:
            if record['id'] in matched_source:raise ValueError('One source row mapped to multiple ESPN IDs')
            matched_source.add(record['id']);diff=old_differences(p,record)
            comparison='unavailable' if p['periods']['ls']['gp'] is None else 'different' if diff else 'same_GP_and_seven_totals'
            item.update(gp=record['gp'],minutes=record['minutes'],totals=dict(record['totals']),shots=dict(record['shots']),
                        uncertainties=dict(record['uncertainties']),source_name=record['source_name'],last_season_team=record['team'],status='matched')
            if diff:disagreements.append(dict(id=pid,name=p['name'],differences=diff))
            mapping.append(dict(id=pid,name=p['name'],source_name=record['source_name'],status='matched',method=method,old_comparison=comparison))
        else:mapping.append(dict(id=pid,name=p['name'],source_name=None,status=status,old_GP=p['periods']['ls']['gp']))
        players[pid]=item
    reference=[dict(id=r['id'],source_name=r['source_name'],gp=r['gp'],totals=dict(r['totals']),shots=dict(r['shots']),uncertainties=dict(r['uncertainties'])) for r in source]
    reference.sort(key=lambda r:r['id']);ref_hash=hashlib.sha256(json.dumps(reference,sort_keys=True).encode()).hexdigest()[:12]
    summary=dict(catalog=len(catalog),matched=sum(m['status']=='matched' for m in mapping),
                 not_in_source=sum(m['status']=='not_in_source' for m in mapping),ambiguous=sum(m['status']=='ambiguous_name' for m in mapping),
                 source_unmapped=len(source)-len(matched_source),declared_conflicts=len(manifest['uncertainties']),old_totals_disagreements=len(disagreements),
                 old_comparable=sum(m.get('old_comparison')=='same_GP_and_seven_totals' for m in mapping))
    return dict(version=1,season=manifest['season'],fixture=False,generated_at=snapshot['generated_at'],source='BoxScore Lab',
        source_info=manifest,source_period={'source_period_start':'2025-10-21','source_period_end':'2026-04-12','timezone':'America/New_York','season_type':'Regular Season'},
        data_ready=summary['matched']>0,
        reference=dict(size=len(reference),expected=len(reference),shooting_complete=sum(all(r['shots'][k] is not None for k in SHOTS) for r in reference),
                       declared_conflicts=manifest['uncertainties'],id='boxscore-lab-v1:'+manifest['season']+':'+ref_hash,records=reference,
                       scale='50 + 15 × z; clipped 0–100; counting uses roster average per member; TO reversed'),
        benchmark=benchmark(reference),players=players,mapping=dict(summary=summary,records=mapping,old_disagreements=disagreements))


if __name__=='__main__':
    data=build_boxscore_data(read_report('index.html'),json.loads(Path('data_snapshot.json').read_text()))
    write_data(data)
    print(json.dumps(data['mapping']['summary'],ensure_ascii=False))
