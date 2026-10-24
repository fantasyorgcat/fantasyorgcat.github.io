"""One completed ESPN game ledger for current-season and recent statistics."""
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
import math
import pandas as pd
import utils


def eastern_date(stamp):
    instant=datetime.fromisoformat(stamp.replace('Z','+00:00'))
    if instant.tzinfo is None:raise ValueError('ESPN game timestamp requires a timezone')
    return instant.astimezone(ZoneInfo('America/New_York')).date()


def completed_events(year, cutoff):
    month=date(year-1,7,1);events={};months=[]
    while month<=cutoff:
        label=month.strftime('%Y%m');months.append(label)
        data=utils.read_json(f'{utils.SITE}/scoreboard?dates={label}&limit=1000')
        if not isinstance(data.get('events'),list):raise ValueError('ESPN scoreboard event population missing')
        for event in data['events']:
            season=event['season']
            if int(season['year'])!=year or int(season['type'])!=2:continue
            if event['status']['type'].get('completed') is not True:continue
            day=eastern_date(event['date'])
            if day>cutoff:raise ValueError('Completed ESPN game is after the report date')
            eid=str(event['id'])
            if eid in events:raise ValueError('Duplicate completed ESPN game')
            events[eid]=day
        month=(month.replace(day=28)+timedelta(days=4)).replace(day=1)
    return events,months


def summary_rows(eid, day, year, teams):
    data=utils.read_json(f'{utils.SITE}/summary?event={eid}')
    header=data['header'];season=header['season'];competition=header['competitions'][0]
    if str(header['id'])!=eid or int(season['year'])!=year or int(season['type'])!=2:
        raise ValueError(f'ESPN summary event/season/type mismatch: {eid}')
    if competition['status']['type'].get('completed') is not True or eastern_date(competition['date'])!=day:
        raise ValueError(f'ESPN summary is not the expected completed game: {eid}')
    sides=data['boxscore']['players']
    if len(sides)!=2 or {int(s['team']['id']) for s in sides}!={int(c['id']) for c in competition['competitors']}:
        raise ValueError(f'ESPN boxscore teams incomplete: {eid}')
    rows=[];seen=set()
    for side in sides:
        tid=int(side['team']['id'])
        if tid not in teams:raise ValueError(f'Unknown ESPN boxscore team: {eid}')
        count=0
        for group in side['statistics']:
            keys=group['keys']
            for player in group['athletes']:
                if player.get('didNotPlay') is True:continue
                if player.get('didNotPlay') is not False:raise ValueError(f'ESPN appearance flag missing: {eid}')
                if len(keys)!=len(player['stats']):raise ValueError(f'ESPN player stats incomplete: {eid}')
                athlete=player['athlete'];pid=int(athlete['id'])
                if pid in seen:raise ValueError(f'Duplicate ESPN player appearance: {eid}/{pid}')
                seen.add(pid);raw=dict(zip(keys,player['stats']))
                row=dict(PLAYER_ID=pid,PLAYER_NAME=athlete['displayName'],TEAM_ID=tid,TEAM_ABBREVIATION=teams[tid],date=day,event_id=eid)
                value=raw.get('minutes')
                if value is None or str(value).strip() in ['', '-', '--', 'N/A']:
                    row['MIN']=None
                else:
                    try:
                        minutes=str(value).strip().split(':')
                        if len(minutes) not in [1,2]:raise ValueError()
                        seconds=float(minutes[1]) if len(minutes)==2 else 0
                        if not 0<=seconds<60:raise ValueError()
                        row['MIN']=float(minutes[0])+seconds/60
                        if not math.isfinite(row['MIN']) or row['MIN']<0:raise ValueError()
                    except (ValueError,TypeError):
                        raise ValueError(f'Invalid ESPN minutes: event={eid}; player={pid} ({athlete["displayName"]}); value={value!r}') from None
                for key,name in [('PTS','points'),('REB','rebounds'),('AST','assists'),('STL','steals'),('BLK','blocks'),('TO','turnovers')]:
                    if name=='rebounds' and name not in raw:name='totalRebounds'
                    value=utils.parse_turnovers(raw[name],total=True)
                    if value is None:raise ValueError(f'Missing ESPN {name}: {eid}/{pid}')
                    row[key]=value
                for prefix,name in [('FG','fieldGoalsMade-fieldGoalsAttempted'),('FT','freeThrowsMade-freeThrowsAttempted'),('FG3','threePointFieldGoalsMade-threePointFieldGoalsAttempted')]:
                    made,attempts=[utils.parse_turnovers(v,total=True) for v in str(raw[name]).split('-')]
                    if made is None or attempts is None or made>attempts:raise ValueError(f'Invalid ESPN shooting pair: {eid}/{pid}')
                    row[prefix+'M']=made;row[prefix+'A']=attempts
                rows.append(row);count+=1
        if not count:raise ValueError(f'ESPN completed team has no player stats: {eid}/{tid}')
    return rows


def current_stats(year):
    cutoff=utils.today();events,months=completed_events(year,cutoff)
    teams={int(t['id']):t['abbreviation'] for t in utils.get_teams()}
    ordered=sorted(events.items(),key=lambda item:(item[1],item[0]))
    games=utils.parallel_map(lambda item:summary_rows(item[0],item[1],year,teams),ordered)
    players={};logs={}
    for game in games:
        for row in game:
            pid=row['PLAYER_ID'];players[pid]=row;logs.setdefault(pid,[]).append(row)
    season=pd.DataFrame([utils.aggregate_games(players[pid],logs[pid]) for pid in sorted(players)],columns=utils.COLUMNS)
    recent=utils.recent_stats(season,year,game_logs=logs)
    dates=list(events.values())
    utils.PROVENANCE[f'players_{year}']=dict(season=utils.season_label(year),population=len(season),season_type='Regular Season',
        source_period_start=str(min(dates)) if dates else None,source_period_end=str(max(dates)) if dates else None,
        shooting_complete=len(season),source='ESPN completed game boxscores')
    utils.PROVENANCE['current_stats_source']=dict(source='ESPN scoreboard + summary',season=utils.season_label(year),
        months=months,completed_events=[eid for eid,_ in ordered],player_game_rows=sum(len(g) for g in games),players=len(players),
        minutes_unknown_player_games=[dict(event_id=row['event_id'],player_id=row['PLAYER_ID'],player_name=row['PLAYER_NAME'],date=str(row['date']))
            for game in games for row in game if row['MIN'] is None],
        latest_completed_game=str(max(dates)) if dates else None)
    return season,*recent
