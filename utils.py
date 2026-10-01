"""Public ESPN player/schedule data and PBP Stats last-10 defense.
Source failures abort generation; fixtures are never fallback production data.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from zoneinfo import ZoneInfo
import math
import re
import time
import pandas as pd
import requests

SITE = 'https://site.api.espn.com/apis/site/v2/sports/basketball/nba'
WEB = 'https://site.web.api.espn.com/apis/common/v3/sports/basketball/nba'
PBP = 'https://api.pbpstats.com'
ALIASES = {'GS':'GSW', 'NO':'NOP', 'NY':'NYK', 'SA':'SAS', 'UTAH':'UTA', 'WSH':'WAS'}
COLUMNS = ['PLAYER_ID','PLAYER_NAME','TEAM_ID','TEAM_ABBREVIATION','GP','MIN','PTS','REB','AST','STL','BLK','FG_PCT','FT_PCT','FG3M']
TOTAL_FIELDS = {'PTS':'points','REB':'rebounds','AST':'assists','STL':'steals','BLK':'blocks','FG3M':'threePointFieldGoalsMade'}
COLUMNS += [key+'_TOTAL' for key in TOTAL_FIELDS]
IDENTITY = COLUMNS[:4]
PROVENANCE = {}


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
            headers = {'User-Agent':'Fantasy-NBA-Streaming-Assistant/2.0 (public data report)'} if url.startswith(PBP+'/') else {}
            r = requests.get(url, headers=headers, timeout=(10, 35))
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
    teams = [dict(id=int(x['team']['id']), abbreviation=ALIASES.get(x['team']['abbreviation'],x['team']['abbreviation'])) for x in league['teams']]
    if any(not re.fullmatch(r'[A-Z]{3}', t['abbreviation']) for t in teams):raise ValueError('Invalid NBA abbreviation')
    if len(teams) != 30 or len({x['id'] for x in teams}) != 30 or len({x['abbreviation'] for x in teams}) != 30:
        raise ValueError('Incomplete NBA team population')
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
        return [dict(PLAYER_ID=int(a['id']), PLAYER_NAME=a['displayName'], TEAM_ID=team['id'], TEAM_ABBREVIATION=team['abbreviation']) for a in d['athletes']]
    rows = [r for group in parallel_map(team_roster, get_teams()) for r in group]
    df = pd.DataFrame(rows, columns=IDENTITY)
    if df['PLAYER_ID'].duplicated().any():
        raise ValueError('Player assigned to multiple current rosters; retry after source reconciliation')
    PROVENANCE['roster_players'] = len(df)
    return df


def get_active_player_ids():
    return set(get_roster()['PLAYER_ID'])


def get_schedule(start_date, end_date):
    def team_schedule(team):
        d = read_json(f"{SITE}/teams/{team['id']}/schedule?season={season_year()}&seasontype=2")
        if d['season']['year'] != season_year():
            raise ValueError('ESPN schedule season mismatch')
        return d['events']
    events = {}
    for group in parallel_map(team_schedule, get_teams()):
        for event in group:
            if event['season']['year'] != season_year() or event['seasonType']['type'] != 2:
                continue
            eid = event['id']
            if eid in events and events[eid]['date'] != event['date']:
                raise ValueError('Conflicting schedule event dates')
            events[eid] = event
    if not events:
        raise ValueError('No current-season regular-season schedule available')
    rows = []
    for e in events.values():
        day = datetime.fromisoformat(e['date'].replace('Z','+00:00')).astimezone(ZoneInfo('America/New_York')).date()
        if not start_date <= day <= end_date:
            continue
        competitors = e['competitions'][0]['competitors']
        if len(competitors) != 2:
            raise ValueError('Invalid NBA schedule competition')
        for c in competitors:
            opponent = next(x for x in competitors if x['id'] != c['id'])
            own, other = abbreviation(c['team']['abbreviation']), abbreviation(opponent['team']['abbreviation'])
            marker = 'vs.' if c['homeAway'] == 'home' else '@'
            rows.append(dict(TEAM_ID=int(c['team']['id']),TEAM_ABBREVIATION=own,GAME_DATE=day,MATCHUP=f'{own} {marker} {other}'))
    PROVENANCE['schedule'] = dict(season=season_label(season_year()),timezone='America/New_York',start=str(start_date),end=str(end_date),events_in_window=len(rows)//2)
    return pd.DataFrame(rows, columns=['TEAM_ID','TEAM_ABBREVIATION','GAME_DATE','MATCHUP'])


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
        raise ValueError('ESPN statistics season/type mismatch')
    athletes = list(d['athletes'])
    for page in range(2,d['pagination']['pages']+1):
        extra=read_json(base+f'&page={page}')
        if extra['requestedSeason']['year'] != year or extra['pagination']['count'] != d['pagination']['count']:
            raise ValueError('League pagination changed during read')
        athletes.extend(extra['athletes'])
    if len(athletes) != d['pagination']['count'] or len({a['athlete']['id'] for a in athletes}) != len(athletes):
        raise ValueError('Incomplete or duplicated league PR population')
    definitions={c['name']:c['names'] for c in d['categories'] if 'names' in c}
    fields={'GP':'gamesPlayed','MIN':'avgMinutes','PTS':'avgPoints','REB':'avgRebounds','AST':'avgAssists','STL':'avgSteals','BLK':'avgBlocks','FG_PCT':'fieldGoalPct','FT_PCT':'freeThrowPct','FG3M':'avgThreePointFieldGoalsMade'}
    team_lookup={t['abbreviation']:t['id'] for t in get_teams()}
    rows=[]
    for a in athletes:
        raw={name:float(value) for c in a['categories'] for name,value in zip(definitions[c['name']],c['values'])}
        if raw['gamesPlayed'] <= 0:continue
        identity=a['athlete'];team=abbreviation(identity['teams'][-1]['abbreviation'])
        row=dict(PLAYER_ID=int(identity['id']),PLAYER_NAME=identity['displayName'],TEAM_ID=team_lookup[team],TEAM_ABBREVIATION=team)
        row.update({key:raw[value] for key,value in fields.items()})
        row.update({key+'_TOTAL':raw[name] for key,name in TOTAL_FIELDS.items()})
        if any(not math.isfinite(row[key+'_TOTAL']) or row[key+'_TOTAL'] < 0 or not row[key+'_TOTAL'].is_integer() for key in TOTAL_FIELDS):
            raise ValueError('Invalid source integer totals')
        row['FG_PCT']/=100;row['FT_PCT']/=100
        if not all(math.isfinite(row[k]) for k in fields):raise ValueError('Nonfinite statistics')
        rows.append(row)
    PROVENANCE[f'players_{year}']=dict(season=season_label(year),population=len(rows),season_type='Regular Season',source_period_start=requested['type']['startDate'],source_period_end=requested['type']['endDate'])
    return pd.DataFrame(rows,columns=COLUMNS)


def player_gamelog(player, year):
    d=read_json(f"{WEB}/athletes/{int(player['PLAYER_ID'])}/gamelog?season={year}&seasontype=2")
    season_filter=next(f for f in d['filters'] if f['name']=='season')
    if str(season_filter['value']) != str(year):raise ValueError('Player log season mismatch')
    rows={}
    for group in d.get('seasonTypes',[]):
        if group['displayName'] != season_label(year)+' Regular Season':continue
        for category in group['categories']:
            if category.get('type') != 'event':continue
            for event in category['events']:
                eid=event['eventId']
                if eid in rows:raise ValueError('Duplicated player game log')
                info=d['events'][eid]
                day=datetime.fromisoformat(info['gameDate']).astimezone(ZoneInfo('America/New_York')).date()
                raw=dict(zip(d['names'],event['stats']))
                row={'date':day}
                for key,name in [('MIN','minutes'),('PTS','points'),('REB','totalRebounds'),('AST','assists'),('STL','steals'),('BLK','blocks')]:
                    value=raw[name];row[key]=float(value.split(':')[0])+float(value.split(':')[1])/60 if ':' in value else float(value)
                for prefix,name in [('FG','fieldGoalsMade-fieldGoalsAttempted'),('FT','freeThrowsMade-freeThrowsAttempted'),('FG3','threePointFieldGoalsMade-threePointFieldGoalsAttempted')]:
                    made,attempted=map(float,raw[name].split('-'));row[prefix+'M']=made;row[prefix+'A']=attempted
                rows[eid]=row
    return list(rows.values())


def recent_stats(season_df, year):
    cutoff=today();output={7:[],14:[]};latest=None
    for player,logs in parallel_map(lambda item:(item,player_gamelog(item,year)),season_df.to_dict('records')):
        if len(logs)!=int(player['GP']):raise ValueError('Player game log not complete for league statistics; source lag')
        if logs:latest=max(latest or logs[0]['date'],max(x['date'] for x in logs))
        for days in [7,14]:
            selected=[x for x in logs if cutoff-timedelta(days=days)<=x['date']<cutoff]
            if not selected:continue
            n=len(selected);row={k:player[k] for k in IDENTITY};row['GP']=n
            for k in ['MIN','PTS','REB','AST','STL','BLK','FG3M']:row[k]=sum(x[k] for x in selected)/n
            for key in TOTAL_FIELDS:row[key+'_TOTAL']=sum(x[key] for x in selected)
            for prefix in ['FG','FT']:
                attempts=sum(x[prefix+'A'] for x in selected);row[prefix+'_PCT']=sum(x[prefix+'M'] for x in selected)/attempts if attempts else 0
            output[days].append(row)
    PROVENANCE['current_stats_last_game']=str(latest) if latest else None
    PROVENANCE['recent_windows']=dict(start_7=str(cutoff-timedelta(days=7)),start_14=str(cutoff-timedelta(days=14)),end_exclusive=str(cutoff),timezone='America/New_York')
    return pd.DataFrame(output[7],columns=COLUMNS),pd.DataFrame(output[14],columns=COLUMNS)


def get_player_stats_multi_period():
    year=season_year();last_label=get_last_complete_season_str();last_year=int(last_label[:4])+1
    season=league_stats(year);last=season.copy() if last_year==year else league_stats(last_year)
    if last.empty:raise ValueError('Last-season population missing')
    l7,l14=recent_stats(season,year)
    return dict(Season=season,L7=l7,L14=l14,LastSeason=last,Roster=get_roster().copy(),metadata={'season':season_label(year),'last_season':last_label})


def get_team_defensive_ratings():
    year = season_year()
    cutoff = today()
    seasons = {}
    byid = {}

    def load_games(end_year):
        label = season_label(end_year)
        data = read_json(f'{PBP}/get-games/nba?Season={label}&SeasonType=Regular%20Season')
        if not isinstance(data.get('results'), list):raise ValueError('PBP completed game population missing')
        prefix = '002'+str(end_year-1)[-2:]
        accepted = {}
        for game in data['results']:
            gid = game['GameId']
            if not re.fullmatch(r'002[0-9]{7}', gid):continue  # Exclude preseason/postseason.
            if not gid.startswith(prefix):raise ValueError('PBP regular game belongs to wrong requested season')
            day = datetime.fromisoformat(game['Date']).date()
            if not datetime(end_year-1,7,1).date() <= day <= datetime(end_year,6,30).date():
                raise ValueError('PBP regular game date outside requested season')
            if day > cutoff:continue
            scores = [game['HomePoints'],game['AwayPoints']]
            if any(value is None for value in scores):continue  # API unfinished-game sentinel.
            if any(isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or value<0 for value in scores):
                raise ValueError('Invalid PBP scoreboard points')
            if any(value == 0 for value in scores):continue
            if game['HomeTeamId']==game['AwayTeamId']:raise ValueError('Invalid PBP competition')
            if gid in accepted and accepted[gid] != game:raise ValueError('Conflicting duplicate PBP game')
            accepted[gid] = game
        seasons[label] = accepted
        for gid,game in accepted.items():
            if gid in byid and byid[gid]!=game:raise ValueError('Cross-season GameId conflict')
            byid[gid] = game

    load_games(year)
    counts = {}
    for game in byid.values():
        for key in ['HomeTeamId','AwayTeamId']:counts[game[key]]=counts.get(game[key],0)+1
    # Until every NBA team has 10 completed current-season games, carry in last season.
    if len(counts)<30 or any(count<10 for count in counts.values()):load_games(year-1)
    teamids={g[key] for g in byid.values() for key in ['HomeTeamId','AwayTeamId']}

    def team_rating(tid):
        selected = sorted([g for g in byid.values() if tid in [g['HomeTeamId'],g['AwayTeamId']]],
                          key=lambda g:(g['Date'],g['GameId']),reverse=True)[:10]
        points = 0;poss = 0
        selected_seasons = []
        for label,games in seasons.items():
            needed = [g for g in selected if g['GameId'] in games]
            if not needed:continue
            selected_seasons.append(label)
            try:
                raw = read_json(f'{PBP}/get-game-logs/nba?Season={label}&SeasonType=Regular%20Season&EntityType=Team&EntityId={tid}')
            except RuntimeError as error:
                raise RuntimeError(f'PBP Stats public team {tid}, season {label}: {error}') from None
            if not isinstance(raw.get('multi_row_table_data'),list):raise ValueError('PBP team log population missing')
            logs = {}
            prefix = '002'+label[:4][-2:]
            for row in raw['multi_row_table_data']:
                gid=row.get('GameId')
                if not gid:continue
                if not re.fullmatch(r'002[0-9]{7}',gid):continue
                if not gid.startswith(prefix):raise ValueError('PBP team log season mismatch')
                if gid in logs and logs[gid]!=row:raise ValueError('Conflicting duplicate PBP team log')
                logs[gid]=row
                if row['Date'] <= str(cutoff) and gid not in games:raise ValueError('PBP scoreboard lags completed team logs')
            for game in needed:
                row=logs.get(game['GameId'])
                if row is None:raise ValueError('PBP defense possession log missing for selected game')
                defense_poss=row.get('DefPoss')
                if row['Date']!=game['Date'] or isinstance(defense_poss,bool) or not isinstance(defense_poss,(int,float)) or not math.isfinite(defense_poss) or defense_poss<=0:
                    raise ValueError('Invalid PBP defense possession log')
                points += game['AwayPoints'] if game['HomeTeamId']==tid else game['HomePoints']
                poss += defense_poss
        newest=selected[0]
        abbr=newest['HomeTeamAbbreviation'] if newest['HomeTeamId']==tid else newest['AwayTeamAbbreviation']
        return abbreviation(abbr),dict(DefRtg=100*points/poss,Games=len(selected),Start=selected[-1]['Date'],End=newest['Date'],
            Seasons=selected_seasons,GameIds=[g['GameId'] for g in selected],OpponentPoints=points,DefPoss=poss)

    # Keep this public endpoint sequential; parallel team logs intermittently return 503.
    ratings=dict(team_rating(tid) for tid in sorted(teamids))
    if len(ratings)!=len(teamids):raise ValueError('PBP team identity collision')
    count=len(ratings)
    for rank,(abbr,row) in enumerate(sorted(ratings.items(),key=lambda item:(item[1]['DefRtg'],item[0])),1):
        row['Rank']=rank;row['Population']=count
    PROVENANCE['defense']=dict(source='PBP Stats',season=season_label(year),
        seasons_considered=list(seasons),window='last 10 completed team regular-season games; previous season carryover',
        formula='100 * sum(opponent scoreboard points) / sum(team game-log DefPoss)',eligible_teams=count,
        last_game=max((g['Date'] for g in byid.values()),default=None),teams=ratings)
    return ratings


def get_color_for_rank(rank, population=30):
    if not rank or not population:return '#eeeeee'
    fraction=(rank-1)/population
    return ['#ffcccc','#ffe5cc','#ffffcc','#e5ffcc','#ccffcc'][min(4,int(fraction*5))]
