"""Public ESPN player/schedule data and labeled estimated last-ten defense.
Source failures abort generation; fixtures are never fallback production data.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from zoneinfo import ZoneInfo
import math
import re
import time
import logging
import pandas as pd
import requests

SITE = 'https://site.api.espn.com/apis/site/v2/sports/basketball/nba'
WEB = 'https://site.web.api.espn.com/apis/common/v3/sports/basketball/nba'
ALIASES = {'GS':'GSW', 'NO':'NOP', 'NY':'NYK', 'SA':'SAS', 'UTAH':'UTA', 'WSH':'WAS'}
COLUMNS = ['PLAYER_ID','PLAYER_NAME','TEAM_ID','TEAM_ABBREVIATION','GP','MIN','PTS','REB','AST','STL','BLK','FG_PCT','FT_PCT','FG3M','TO']
TOTAL_FIELDS = {'PTS':'points','REB':'rebounds','AST':'assists','STL':'steals','BLK':'blocks','FG3M':'threePointFieldGoalsMade','TO':'turnovers'}
SHOOTING_FIELDS = {'FGM':'fieldGoalsMade','FGA':'fieldGoalsAttempted','FTM':'freeThrowsMade','FTA':'freeThrowsAttempted'}
COLUMNS += [key+'_TOTAL' for key in TOTAL_FIELDS] + list(SHOOTING_FIELDS)
SCHEDULE_COLUMNS = ['TEAM_ID','TEAM_ABBREVIATION','GAME_DATE','MATCHUP','EVENT_ID','TIPOFF_UTC','STATUS','SEASON_TYPE','TIME_CONFIRMED']
IDENTITY = COLUMNS[:4]
PROVENANCE = {}
LOG = logging.getLogger(__name__)
RECORD_ERRORS = (ValueError, TypeError, KeyError, IndexError, AttributeError, StopIteration, OverflowError)


def source_warning(source, record, reason):
    issue=dict(source=source, record=str(record), reason=str(reason))
    PROVENANCE.setdefault('source_warnings', []).append(issue)
    LOG.warning('%s record=%s: %s',source,record,reason)


def check_coverage(source, total, bad, usable):
    """One isolated anomaly is tolerated, never an empty or broadly broken feed."""
    PROVENANCE.setdefault('source_quality',{})[source]=dict(records=total,anomalous=bad,usable=usable)
    if not usable or (bad > 1 and bad / max(total, 1) > .10):
        recent=PROVENANCE.get('source_warnings',[])[-1:]
        reason=recent[0]['reason'] if recent else 'no usable records'
        raise ValueError(f'{source} globally broken: records={total}; anomalous={bad}; usable={usable}; last issue={reason}')


def optional_number(value, source, record, total=False):
    try:
        result=parse_turnovers(value,total=total)
        if result is None:raise ValueError('missing numeric value')
        return result
    except (ValueError,TypeError,OverflowError):
        source_warning(source,record,f'unknown numeric value {str(value)[:80]!r}')
        return None


def parse_minutes(value, source, record):
    try:
        if isinstance(value,bool):raise ValueError()
        parts=str(value).strip().split(':')
        if len(parts) not in (1,2):raise ValueError()
        minute=float(parts[0]);second=float(parts[1]) if len(parts)==2 else 0
        if not math.isfinite(minute) or minute<0 or not 0<=second<60:raise ValueError()
        return minute+second/60
    except (ValueError,TypeError,OverflowError):
        source_warning(source,record,f'unknown minutes {str(value)[:80]!r}')
        return None


def shooting_pair(value, source, record):
    try:
        made,attempted=[parse_turnovers(v,total=True) for v in str(value).split('-')]
        if made is None or attempted is None or made>attempted:raise ValueError()
        return made,attempted
    except (ValueError,TypeError,OverflowError):
        source_warning(source,record,f'unknown shooting pair {str(value)[:80]!r}')
        return None,None

class StatsSourceLagError(ValueError):
    """League GP and player game logs do not yet form one consistent snapshot."""

def parse_turnovers(value, total=False):
    if value is None or (isinstance(value,str) and value.strip() in ['', '-', '--', 'N/A']):return None
    if isinstance(value,bool):raise ValueError('Invalid turnover statistic')
    value=float(value)
    if not math.isfinite(value) or value<0 or (total and not value.is_integer()):
        raise ValueError('Invalid turnover statistic')
    return value


def today():
    return datetime.now(ZoneInfo('America/New_York')).date()


def season_year():
    league = read_json(SITE + '/teams?limit=100')['sports'][0]['leagues'][0]
    year = int(league['season']['year'])
    d = datetime.now(timezone.utc).date()
    allowed = {d.year, d.year + 1} if d.month >= 7 else {d.year}
    if year not in allowed:
        raise ValueError('ESPN current season outside expected calendar range')
    return year


def season_label(year):
    return f'{year-1}-{str(year)[-2:]}'


def get_last_complete_season_str(reference_date=None):
    d = reference_date or today()
    year = d.year if d.month >= 7 else d.year - 1
    return season_label(year)


def abbreviation(value):
    result = ALIASES.get(value, value)
    if result not in {t['abbreviation'] for t in get_teams()}:
        raise ValueError('Unknown team abbreviation in source data')
    return result


@lru_cache(maxsize=2000)
def read_json(url):
    for attempt in range(3):
        try:
            r = requests.get(url, timeout=(10, 35))
            r.raise_for_status()
            return r.json()
        except (requests.Timeout, requests.ConnectionError):
            if attempt == 2:
                raise RuntimeError('Public data source connection failed; existing report retained') from None
        except requests.HTTPError as error:
            if error.response.status_code not in [429, 500, 502, 503, 504] or attempt == 2:
                raise RuntimeError(f'Public data source HTTP {error.response.status_code}; existing report retained') from None
        except ValueError:
            raise RuntimeError('Public data source returned invalid JSON') from None
        time.sleep(2 ** attempt)


@lru_cache(maxsize=1)
def get_teams():
    league = read_json(SITE + '/teams?limit=100')['sports'][0]['leagues'][0]
    if league['season']['year'] != season_year():
        raise ValueError('ESPN league season does not match current season')
    teams=[];bad=abs(30-len(league['teams']))
    for item in league['teams']:
        try:
            team=item['team'];tid=int(team['id']);abbr=ALIASES.get(team['abbreviation'],team['abbreviation'])
            if not re.fullmatch(r'[A-Z]{3}',abbr):raise ValueError('Invalid NBA abbreviation')
            if any(t['id']==tid or t['abbreviation']==abbr for t in teams):raise ValueError('Duplicate NBA team')
            teams.append(dict(id=tid,abbreviation=abbr))
        except RECORD_ERRORS as error:
            bad+=1;source_warning('teams','identity',error)
    if len(teams)!=30:source_warning('teams','population',f'Expected 30 teams; usable={len(teams)}')
    check_coverage('NBA team population',30,bad,len(teams))
    return teams


def parallel_map(function, values, workers=4):
    with ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(function, values))


@lru_cache(maxsize=1)
def get_roster():
    def team_roster(team):
        d = read_json(f"{SITE}/teams/{team['id']}/roster")
        if d.get('status') != 'success' or d['season']['year'] != season_year() or not d.get('athletes'):
            raise ValueError('Incomplete current ESPN roster')
        rows=[];bad=0
        for a in d['athletes']:
            try:
                pid=int(a['id']);name=a['displayName']
                if not isinstance(name,str) or not name.strip():raise ValueError('Missing player name')
                rows.append(dict(PLAYER_ID=pid,PLAYER_NAME=name,TEAM_ID=team['id'],TEAM_ABBREVIATION=team['abbreviation']))
            except RECORD_ERRORS as error:
                bad+=1;source_warning('roster',team['id'],error)
        check_coverage('roster '+str(team['id']),len(d['athletes']),bad,len(rows))
        return rows
    def load(team):
        try:return team_roster(team)
        except (RuntimeError,*RECORD_ERRORS) as error:
            source_warning('roster team',team['id'],error);return None
    groups=parallel_map(load,get_teams())
    check_coverage('roster teams',len(groups),sum(g is None for g in groups),sum(bool(g) for g in groups))
    rows = [r for group in groups if group is not None for r in group]
    quality=[v for k,v in PROVENANCE.get('source_quality',{}).items() if k.startswith('roster ') and k[7:].isdigit()]
    if quality:check_coverage('roster records',sum(v['records'] for v in quality),sum(v['anomalous'] for v in quality),len(rows))
    df = pd.DataFrame(rows, columns=IDENTITY)
    duplicates=df['PLAYER_ID'].duplicated(keep=False)
    if duplicates.any():
        bad=df.loc[duplicates,'PLAYER_ID'].nunique()
        for pid in df.loc[duplicates,'PLAYER_ID'].unique():source_warning('roster',pid,'Ambiguous current team; omitted from roster')
        check_coverage('roster identities',df['PLAYER_ID'].nunique(),bad,int((~duplicates).sum()))
        df=df.loc[~duplicates].copy()
    PROVENANCE['roster_players'] = len(df)
    return df


def get_active_player_ids():
    return set(get_roster()['PLAYER_ID'])


@lru_cache(maxsize=1)
def get_season_schedule():
    def team_schedule(team):
        d = read_json(f"{SITE}/teams/{team['id']}/schedule?season={season_year()}&seasontype=2")
        if d['season']['year'] != season_year():
            raise ValueError('ESPN schedule season mismatch')
        if not isinstance(d.get('events'), list):raise ValueError('ESPN schedule population missing')
        return d['events']
    def load(team):
        try:return team_schedule(team)
        except (RuntimeError,*RECORD_ERRORS) as error:
            source_warning('schedule team',team['id'],error);return None
    groups=parallel_map(load,get_teams())
    check_coverage('schedule teams',len(groups),sum(g is None for g in groups),sum(g is not None for g in groups))
    events = {};bad_ids=set();total=0
    for group in groups:
        if group is None:continue
        for event in group:
            total+=1
            try:
                if event['season']['year'] != season_year() or event['seasonType']['type'] != 2:continue
                eid=event['id']
                if eid in bad_ids:continue
                if eid in events and events[eid].get('date') != event.get('date'):
                    events.pop(eid);bad_ids.add(eid)
                    raise ValueError('Conflicting schedule event dates; both omitted')
                events[eid]=event
            except RECORD_ERRORS as error:
                bad_ids.add(str(event.get('id',total)) if isinstance(event,dict) else str(total));source_warning('schedule',total,error)
    rows = []
    for e in events.values():
        event_rows=[]
        try:
            competition = e['competitions'][0]
            stamp = datetime.fromisoformat(e['date'].replace('Z','+00:00')) if e.get('date') else None
            if stamp is not None and stamp.tzinfo is None:raise ValueError('Schedule timestamp requires a timezone')
            day = stamp.astimezone(ZoneInfo('America/New_York')).date() if stamp else None
            status_type = competition.get('status',e.get('status',{})).get('type',{})
            name = str(status_type.get('name','')).lower()
            status = ('cancelled' if 'cancel' in name else 'postponed' if 'postpon' in name else
                      'suspended' if 'suspend' in name else 'delayed' if 'delay' in name else
                      'final' if status_type.get('completed') else
                      {'pre':'scheduled','in':'in_progress','post':'final'}.get(status_type.get('state'),'unknown'))
            confirmed = bool(stamp and competition.get('timeValid') is not False)
            tipoff = stamp.astimezone(timezone.utc).isoformat().replace('+00:00','Z') if confirmed else None
            competitors = competition['competitors']
            if len(competitors) != 2:
                raise ValueError('Invalid NBA schedule competition')
            if {c['homeAway'] for c in competitors}!={'home','away'}:raise ValueError('Invalid home/away sides')
            if len({c['id'] for c in competitors})!=2:raise ValueError('Duplicate competition team')
            for c in competitors:
                opponent = next(x for x in competitors if x['id'] != c['id'])
                own, other = abbreviation(c['team']['abbreviation']), abbreviation(opponent['team']['abbreviation'])
                marker = 'vs.' if c['homeAway'] == 'home' else '@'
                event_rows.append(dict(TEAM_ID=int(c['team']['id']),TEAM_ABBREVIATION=own,GAME_DATE=day,MATCHUP=f'{own} {marker} {other}',
                                 EVENT_ID=str(e['id']),TIPOFF_UTC=tipoff,STATUS=status,SEASON_TYPE=2,TIME_CONFIRMED=confirmed))
            rows.extend(event_rows)
        except RECORD_ERRORS as error:
            bad_ids.add(e['id']);source_warning('schedule',e['id'],error)
    if total:check_coverage('season schedule',len(set(events)|bad_ids),len(bad_ids),len(rows)//2)
    dated = [r['GAME_DATE'] for r in rows if r['GAME_DATE'] is not None]
    PROVENANCE['schedule'] = dict(season=season_label(season_year()),timezone='America/New_York',
        completed_events=len(set(r['EVENT_ID'] for r in rows if r['STATUS']=='final')),
        published_events=len(set(r['EVENT_ID'] for r in rows if r['GAME_DATE'] is not None)),
        undated_events=len(set(r['EVENT_ID'] for r in rows if r['GAME_DATE'] is None)),
        first_game=str(min(dated)) if dated else None,last_game=str(max(dated)) if dated else None,
        coverage='All dated regular-season events currently published by ESPN; excludes preseason/postseason')
    return pd.DataFrame(rows, columns=SCHEDULE_COLUMNS)


def get_schedule(start_date, end_date):
    full=get_season_schedule()
    selected=full.loc[(full['GAME_DATE']>=start_date)&(full['GAME_DATE']<=end_date)].copy()
    count=sum(r['STATUS'] not in ['cancelled','postponed','suspended'] for r in selected.to_dict('records'))//2
    PROVENANCE['schedule'].update(start=str(start_date),end=str(end_date),events_in_window=count)
    return selected


def season_weeks(schedule):
    """Monday–Sunday in Eastern dates; opening game's week is 1, without year resets."""
    dates=schedule['GAME_DATE'].dropna() if not schedule.empty else []
    if not len(dates):return []
    first=min(dates);last=max(dates)
    start=first-timedelta(days=first.weekday())
    weeks=[]
    while start<=last:
        end=start+timedelta(days=6)
        weeks.append(dict(number=len(weeks)+1,start=start,end=end,
            label=f'Week {len(weeks)+1} · {start:%Y/%m/%d}–{end:%Y/%m/%d}'))
        start=end+timedelta(days=1)
    return weeks


def league_stats(year):
    base = f'{WEB}/statistics/byathlete?season={year}&seasontype=2&limit=1000'
    d = read_json(base)
    if 'athletes' not in d:
        current = d.get('currentSeason',{})
        if year == season_year() and current.get('year') == year and str(current.get('type',{}).get('id')) == '1':
            return pd.DataFrame(columns=COLUMNS)
        raise ValueError('ESPN season statistics unexpectedly missing')
    requested = d['requestedSeason']
    if requested['year'] != year or requested['type']['type'] != 2:
        current = d.get('currentSeason',{})
        raise ValueError('ESPN statistics season/type mismatch: '
                         f'expected season={year}, type=2; '
                         f"returned season={requested['year']!r}, type={requested['type']['type']!r}; "
                         f"current season={current.get('year')!r}, type={current.get('type')!r}; "
                         f"athletes={len(d['athletes'])}; source={base}")
    athletes = list(d['athletes'])
    for page in range(2,d['pagination']['pages']+1):
        extra=read_json(base+f'&page={page}')
        if extra['requestedSeason']['year'] != year or extra['pagination']['count'] != d['pagination']['count']:
            raise ValueError('League pagination changed during read')
        athletes.extend(extra['athletes'])
    if len(athletes) != d['pagination']['count']:
        raise ValueError('Incomplete or duplicated league PR population')
    definitions={c['name']:c['names'] for c in d['categories'] if 'names' in c}
    fields={'GP':'gamesPlayed','MIN':'avgMinutes','PTS':'avgPoints','REB':'avgRebounds','AST':'avgAssists','STL':'avgSteals','BLK':'avgBlocks','FG_PCT':'fieldGoalPct','FT_PCT':'freeThrowPct','FG3M':'avgThreePointFieldGoalsMade','TO':'avgTurnovers'}
    team_lookup={t['abbreviation']:t['id'] for t in get_teams()}
    rows=[];seen=set();bad=0
    for a in athletes:
        try:
            identity=a['athlete'];pid=int(identity['id'])
            if pid in seen:raise ValueError('Duplicate league athlete; ignored repeat')
            seen.add(pid)
            raw={}
            for category in a['categories']:
                names=definitions[category['name']]
                if len(names)!=len(category['values']):source_warning('league',pid,'Category length mismatch; absent fields unknown')
                for name,value in zip(names,category['values']):
                    raw[name]=optional_number(value,'league',f'{pid}/{name}',total=name in ['gamesPlayed',*TOTAL_FIELDS.values(),*SHOOTING_FIELDS.values()])
            missing=[name for name in [*fields.values(),*TOTAL_FIELDS.values(),*SHOOTING_FIELDS.values()] if name not in raw]
            if missing:source_warning('league',pid,'Missing fields remain unknown: '+', '.join(sorted(set(missing))))
            if raw.get('gamesPlayed') is None:raise ValueError('Missing games played')
            if raw['gamesPlayed'] <= 0:continue
            identity=a['athlete'];team=abbreviation(identity['teams'][-1]['abbreviation'])
            row=dict(PLAYER_ID=int(identity['id']),PLAYER_NAME=identity['displayName'],TEAM_ID=team_lookup[team],TEAM_ABBREVIATION=team)
            row.update({key:raw.get(value) for key,value in fields.items()})
            row.update({key+'_TOTAL':raw.get(name) for key,name in TOTAL_FIELDS.items()})
            row.update({key:parse_turnovers(raw.get(name),total=True) for key,name in SHOOTING_FIELDS.items()})
            for prefix in ['FG','FT']:
                if row[prefix+'M'] is not None and row[prefix+'A'] is not None and row[prefix+'M']>row[prefix+'A']:
                    source_warning('league',pid,'Shooting makes exceed attempts; pair unknown');row[prefix+'M']=None;row[prefix+'A']=None
            for k in ['FG_PCT','FT_PCT']:
                if row[k] is not None:row[k]/=100
            if any(row[k] is None for k in fields if k not in ['MIN','TO','FG_PCT','FT_PCT']):bad+=1
            rows.append(row)
        except RECORD_ERRORS as error:
            bad+=1;source_warning('league',year,error)
    usable=sum(any(r[k] is not None for k in ['PTS','REB','AST','STL','BLK','FG3M']) for r in rows)
    check_coverage('league statistics',len(athletes),bad,usable)
    PROVENANCE[f'players_{year}']=dict(season=season_label(year),population=len(rows),season_type='Regular Season',source_period_start=requested['type']['startDate'],source_period_end=requested['type']['endDate'],shooting_complete=sum(all(r[k] is not None for k in SHOOTING_FIELDS) for r in rows))
    return pd.DataFrame(rows,columns=COLUMNS)


def player_gamelog(player, year):
    source=f"{WEB}/athletes/{int(player['PLAYER_ID'])}/gamelog?season={year}&seasontype=2"
    d=read_json(source)
    season_filter=next(f for f in d['filters'] if f['name']=='season')
    if str(season_filter['value']) != str(year):raise ValueError('Player log season mismatch')
    if player.get('GP',0)>0 and not any(g['displayName']==season_label(year)+' Regular Season' for g in d.get('seasonTypes',[])):
        raise StatsSourceLagError(f"Player regular-season log group missing; player={int(player['PLAYER_ID'])}; season={year}; GP={int(player['GP'])}; available groups={[g.get('displayName') for g in d.get('seasonTypes',[])]}; source={source}")
    rows={}
    for group in d.get('seasonTypes',[]):
        if group['displayName'] != season_label(year)+' Regular Season':continue
        for category in group['categories']:
            if category.get('type') != 'event':continue
            for event in category['events']:
                try:
                    eid=event['eventId']
                    if eid in rows:raise ValueError('Duplicated player game log')
                    info=d['events'][eid]
                    stamp=datetime.fromisoformat(info['gameDate'])
                    if stamp.tzinfo is None:raise ValueError('Player log timestamp requires a timezone')
                    day=stamp.astimezone(ZoneInfo('America/New_York')).date()
                    raw=dict(zip(d['names'],event['stats']))
                    row={'date':day}
                    for key,name in [('MIN','minutes'),('PTS','points'),('REB','totalRebounds'),('AST','assists'),('STL','steals'),('BLK','blocks')]:
                        row[key]=parse_minutes(raw.get(name),'gamelog',eid) if key=='MIN' else optional_number(raw.get(name),'gamelog',f'{eid}/{name}',total=True)
                    row['TO']=optional_number(raw.get('turnovers'),'gamelog',f'{eid}/turnovers',total=True)
                    for prefix,name in [('FG','fieldGoalsMade-fieldGoalsAttempted'),('FT','freeThrowsMade-freeThrowsAttempted'),('FG3','threePointFieldGoalsMade-threePointFieldGoalsAttempted')]:
                        row[prefix+'M'],row[prefix+'A']=shooting_pair(raw.get(name),'gamelog',f'{eid}/{name}')
                    rows[eid]=row
                except RECORD_ERRORS as error:source_warning('gamelog',player['PLAYER_ID'],error)
    result=list(rows.values())
    if result:
        fields=['PTS','REB','AST','STL','BLK']
        check_coverage('player gamelog '+str(player['PLAYER_ID']),len(result),
            sum(any(r[k] is None for k in fields) for r in result),
            sum(any(r[k] is not None for k in fields) for r in result))
    return result


def aggregate_games(player, selected):
    n=len(selected);row={k:player[k] for k in IDENTITY};row['GP']=n
    for k in ['MIN','PTS','REB','AST','STL','BLK','FG3M']:
        values=[x.get(k) for x in selected];row[k]=sum(values)/n if all(v is not None for v in values) else None
    turnovers=[x.get('TO') for x in selected]
    row['TO']=sum(turnovers)/n if all(v is not None for v in turnovers) else None
    for key in TOTAL_FIELDS:row[key+'_TOTAL']=(sum(turnovers) if all(v is not None for v in turnovers) else None) if key=='TO' else (sum(x[key] for x in selected) if all(x.get(key) is not None for x in selected) else None)
    for prefix in ['FG','FT']:
        for suffix in ['M','A']:
            values=[x.get(prefix+suffix) for x in selected]
            row[prefix+suffix]=sum(values) if all(v is not None for v in values) else None
        attempts=row[prefix+'A'];made=row[prefix+'M']
        row[prefix+'_PCT']=made/attempts if made is not None and attempts is not None and attempts>0 else None
    return row


def recent_stats(season_df, year, game_logs=None):
    cutoff=today();output={7:[],14:[]};latest=None
    players=season_df.to_dict('records')
    def load(player):
        try:return player,player_gamelog(player,year)
        except (RuntimeError,*RECORD_ERRORS) as error:
            source_warning('gamelog',player['PLAYER_ID'],error)
            return player,[]
    pairs=parallel_map(load,players) if game_logs is None else [(p,game_logs[int(p['PLAYER_ID'])]) for p in players]
    bad=0
    for player,logs in pairs:
        if len(logs)!=int(player['GP']):
            dates=sorted(str(x['date']) for x in logs)
            bad+=1;source_warning('gamelog',player['PLAYER_ID'],f"Player game log not complete for league statistics; source lag; player={int(player['PLAYER_ID'])} ({player['PLAYER_NAME']}); season={year}; GP={int(player['GP'])}; logs={len(logs)}; dates={dates}; group={season_label(year)} Regular Season; source={WEB}/athletes/{int(player['PLAYER_ID'])}/gamelog?season={year}&seasontype=2")
            continue
        if logs:latest=max(latest or logs[0]['date'],max(x['date'] for x in logs))
        for days in [7,14]:
            selected=[x for x in logs if cutoff-timedelta(days=days)<=x['date']<cutoff]
            if not selected:continue
            output[days].append(aggregate_games(player,selected))
    if pairs:check_coverage('recent player logs',len(pairs),bad,len(pairs)-bad)
    PROVENANCE['current_stats_last_game']=str(latest) if latest else None
    PROVENANCE['recent_windows']=dict(start_7=str(cutoff-timedelta(days=7)),start_14=str(cutoff-timedelta(days=14)),end_exclusive=str(cutoff),timezone='America/New_York')
    return pd.DataFrame(output[7],columns=COLUMNS),pd.DataFrame(output[14],columns=COLUMNS)


def get_player_stats_multi_period():
    from espn_boxscores import current_stats
    year=season_year();last_label=get_last_complete_season_str();last_year=int(last_label[:4])+1
    season,l7,l14=current_stats(year)
    last=season.copy() if last_year==year else league_stats(last_year)
    if last.empty:raise ValueError('Last-season population missing')
    return dict(Season=season,L7=l7,L14=l14,LastSeason=last,Roster=get_roster().copy(),metadata={'season':season_label(year),'last_season':last_label})


def get_team_defensive_ratings():
    from espn_defense import defensive_ratings
    return defensive_ratings()


def get_color_for_rank(rank, population=30):
    if not rank or not population:return '#dedbd5'
    fraction=(rank-1)/population
    return ['#dfc5c8','#e4cfbb','#e7dfcf','#d7e0df','#c5d5dc'][min(4,int(fraction*5))]
