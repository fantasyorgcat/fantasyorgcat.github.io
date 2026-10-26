"""One completed ESPN game ledger for current-season and recent statistics."""
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
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
        bad=0
        for event in data['events']:
            try:
                season=event['season']
                if int(season['year'])!=year or int(season['type'])!=2:continue
                if event['status']['type'].get('completed') is not True:continue
                day=eastern_date(event['date'])
                if day>cutoff:raise ValueError('Completed ESPN game is after the report date')
                eid=str(event['id'])
                if eid in events:raise ValueError('Duplicate completed ESPN game')
                events[eid]=day
            except utils.RECORD_ERRORS as error:
                bad+=1;utils.source_warning('scoreboard',event.get('id','unknown') if isinstance(event,dict) else 'unknown',error)
        if bad:utils.check_coverage('scoreboard',len(data['events']),bad,len(data['events'])-bad)
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
    rows=[];seen=set();bad=0;total=0
    for side in sides:
        tid=int(side['team']['id'])
        if tid not in teams:raise ValueError(f'Unknown ESPN boxscore team: {eid}')
        for group in side['statistics']:
            keys=group['keys']
            for player in group['athletes']:
                total+=1
                try:
                    if player.get('didNotPlay') is True:
                        total-=1;continue
                    if player.get('didNotPlay') is not False:raise ValueError('ESPN appearance flag missing')
                    athlete=player['athlete'];pid=int(athlete['id'])
                    if pid in seen:raise ValueError('Duplicate ESPN player appearance')
                    name=athlete['displayName']
                    if not isinstance(name,str) or not name.strip():raise ValueError('Missing player name')
                    seen.add(pid)
                    raw=dict(zip(keys,player.get('stats',[])))
                    if len(keys)!=len(player.get('stats',[])):
                        utils.source_warning('boxscore',f'{eid}/{pid}','ESPN player stats incomplete; absent values unknown')
                    row=dict(PLAYER_ID=pid,PLAYER_NAME=name,TEAM_ID=tid,TEAM_ABBREVIATION=teams[tid],date=day,event_id=eid)
                    row['MIN']=utils.parse_minutes(raw.get('minutes'),'boxscore',f'{eid}/{pid}')
                    for key,name in [('PTS','points'),('REB','rebounds'),('AST','assists'),('STL','steals'),('BLK','blocks'),('TO','turnovers')]:
                        if name=='rebounds' and name not in raw:name='totalRebounds'
                        row[key]=utils.optional_number(raw.get(name),'boxscore',f'{eid}/{pid}/{name}',total=True)
                    for prefix,name in [('FG','fieldGoalsMade-fieldGoalsAttempted'),('FT','freeThrowsMade-freeThrowsAttempted'),('FG3','threePointFieldGoalsMade-threePointFieldGoalsAttempted')]:
                        row[prefix+'M'],row[prefix+'A']=utils.shooting_pair(raw.get(name),'boxscore',f'{eid}/{pid}/{name}')
                    rows.append(row)
                    if any(row[k] is None for k in ['PTS','REB','AST','STL','BLK','TO','FGM','FGA','FTM','FTA','FG3M','FG3A']):bad+=1
                except utils.RECORD_ERRORS as error:
                    bad+=1;utils.source_warning('boxscore',eid,error)
    # A missing optional minute is not a missing appearance or a fabricated zero.
    usable=sum(any(row[k] is not None for k in ['PTS','REB','AST','STL','BLK','TO']) for row in rows)
    utils.check_coverage('ESPN boxscore '+eid,total,bad,usable)

    return rows


def current_stats(year):
    cutoff=utils.today();events,months=completed_events(year,cutoff)
    teams={int(t['id']):t['abbreviation'] for t in utils.get_teams()}
    ordered=sorted(events.items(),key=lambda item:(item[1],item[0]))
    def load(item):
        try:return summary_rows(item[0],item[1],year,teams)
        except (RuntimeError,*utils.RECORD_ERRORS) as error:
            utils.source_warning('summary',item[0],error)
            return []
    games=utils.parallel_map(load,ordered)
    if ordered:utils.check_coverage('ESPN summaries',len(ordered),sum(not g for g in games),sum(bool(g) for g in games))
    elif cutoff>=date(year-1,11,1) or utils.PROVENANCE.get('schedule',{}).get('completed_events',0):
        raise ValueError('ESPN scoreboard globally broken: no completed regular-season games')
    quality=[utils.PROVENANCE['source_quality']['ESPN boxscore '+eid] for (eid,_),game in zip(ordered,games) if game]
    if quality:utils.check_coverage('ESPN player appearances',sum(q['records'] for q in quality),sum(q['anomalous'] for q in quality),sum(q['usable'] for q in quality))
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
        months=months,completed_events=[eid for eid,_ in ordered],
        included_events=[eid for (eid,_),game in zip(ordered,games) if game],
        skipped_events=[eid for (eid,_),game in zip(ordered,games) if not game],player_game_rows=sum(len(g) for g in games),players=len(players),
        minutes_unknown_player_games=[dict(event_id=row['event_id'],player_id=row['PLAYER_ID'],player_name=row['PLAYER_NAME'],date=str(row['date']))
            for game in games for row in game if row['MIN'] is None],
        latest_completed_game=str(max(dates)) if dates else None)
    return season,*recent
