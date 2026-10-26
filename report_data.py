"""Lossless public catalog packing, shared by generation and the stdlib release gate.

Fixed arrays omit repeated metric keys and identical AVG/TOT cells. Periods are
interned (especially no-appearance periods). Only integral floats are shortened;
PR precision is retained because rounding can change tied custom rankings.
"""
import json
from pathlib import Path
import re

PERIODS = ['season', 'l7', 'l14', 'ls']
METRICS = ['MIN', 'PTS', 'REB', 'AST', '3PM', 'STL', 'BLK', 'FG%', 'FT%', 'TO', 'Rank']
SHOTS = ['FGM', 'FGA', 'FTM', 'FTA']
EVENT_FIELDS = ['id','date_et','tipoff_utc','status','season_type','time_confirmed','home','away']
PUBLIC_SCRIPTS = ['report_data.js', 'data_codec.js', 'report.js', 'site_ui.js',
                  'team_tools.js', 'player_tools.js', 'schedule_tools.js', 'table_tools.js']


def compact(value):
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, list):
        return [compact(v) for v in value]
    if isinstance(value, dict):
        return {k: compact(v) for k, v in value.items()}
    return value


def pack_catalog(catalog):
    periods, lookup, players = [], {}, []
    for p in catalog.values():
        indices = []
        for key in PERIODS:
            v = p['periods'][key]
            avg = [[v['avg'][m]['value'], v['avg'][m].get('sum') if m == 'Rank' else v['avg'][m]['pr']] for m in METRICS]
            tot = [None if v['tot'][m] == v['avg'][m] else
                   [v['tot'][m]['value'], v['tot'][m].get('sum') if m == 'Rank' else v['tot'][m]['pr']] for m in METRICS]
            row = compact([v['gp'], [v['shooting'][k] for k in SHOTS], avg, tot])
            identity = json.dumps(row, separators=(',', ':'), allow_nan=False)
            if identity not in lookup:
                lookup[identity] = len(periods)
                periods.append(row)
            indices.append(lookup[identity])
        players.append([p['id'], p['name'], p['team'], *indices])
    return {'v': 1, 'p': players, 's': periods}


def unpack_catalog(data):
    if data.get('v') != 1:
        return data
    result = {}
    for pid, name, team, *indices in data['p']:
        periods = {}
        for key, index in zip(PERIODS, indices):
            gp, shots, avg, tot = data['s'][index]
            def cells(values):
                return {m: dict(value=c[0], pr=None, sum=c[1]) if m == 'Rank' else dict(value=c[0], pr=c[1])
                        for m, c in zip(METRICS, values)}
            periods[key] = dict(gp=gp, shooting=dict(zip(SHOTS, shots)), avg=cells(avg),
                                tot=cells([a if t is None else t for a, t in zip(avg, tot)]))
        result[pid] = dict(id=pid, name=name, team=team, periods=periods)
    return result


def pack_events(events):
    if isinstance(events,dict):return events
    badges,times,rows=[],[],[]
    badge_ids,time_ids={},{}
    def intern(value,pool,lookup):
        if value not in lookup:
            lookup[value]=len(pool);pool.append(value)
        return lookup[value]
    for event in events:
        row=[event[k] for k in EVENT_FIELDS]
        for side in ['home','away']:
            badge,sep,time=event[side+'_html'].partition('<time')
            row.extend([intern(badge,badges,badge_ids),intern(sep+time,times,time_ids)])
        rows.append(row)
    return dict(v=1,b=badges,t=times,e=rows)


def unpack_events(data):
    if isinstance(data,list):return data
    if data.get('v')!=1:raise ValueError('Unsupported schedule transport')
    events=[]
    for row in data['e']:
        event=dict(zip(EVENT_FIELDS,row[:8]))
        event['home_html']=data['b'][row[8]]+data['t'][row[9]]
        event['away_html']=data['b'][row[10]]+data['t'][row[11]]
        events.append(event)
    return events


def write_script(path, variable, data):
    text = json.dumps(compact(data), ensure_ascii=False, separators=(',', ':'), allow_nan=False).replace('<', '\\u003c')
    Path(path).write_text('window.' + variable + ' = ' + text + ';\n', encoding='utf-8')


def read_script(path, variable):
    match = re.fullmatch(r'window\.' + re.escape(variable) + r' = (.*);\s*', Path(path).read_text(encoding='utf-8'))
    if not match:
        raise ValueError('Invalid public data script: ' + str(path))
    return json.loads(match[1])


def script_tags():
    return '\n'.join('<script src="' + name + '"></script>' for name in PUBLIC_SCRIPTS)
