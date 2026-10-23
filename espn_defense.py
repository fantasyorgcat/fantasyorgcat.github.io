"""Last-ten regular-season defense using ESPN's estimated possession formula."""
from datetime import datetime
import utils
from espn_boxscores import eastern_date

FORMULA='100 * sum(opponent points) / sum(opponent FGA + 0.4 * FTA - ORB + totalTurnovers)'
METRIC='estimated_defensive_rating'


def number(value):
    result=utils.parse_turnovers(value,total=True)
    if result is None:raise ValueError('Missing required ESPN defense statistic')
    return result


def attempts(value):
    made,taken=[number(v) for v in str(value).split('-')]
    if made>taken:raise ValueError('ESPN shooting makes exceed attempts')
    return taken


def estimated_possessions(stats):
    if 'totalTurnovers' in stats:turnovers=number(stats['totalTurnovers'])
    elif 'turnovers' in stats and 'teamTurnovers' in stats:
        turnovers=number(stats['turnovers'])+number(stats['teamTurnovers'])
    else:raise ValueError('Missing ESPN totalTurnovers or explicit player/team turnover pair')
    possessions=attempts(stats['fieldGoalsMade-fieldGoalsAttempted'])+0.4*attempts(stats['freeThrowsMade-freeThrowsAttempted'])-number(stats['offensiveRebounds'])+turnovers
    if possessions<=0:raise ValueError('Invalid ESPN estimated possessions')
    return possessions


def completed_team_games(tid, year):
    data=utils.read_json(f'{utils.SITE}/teams/{tid}/schedule?season={year}&seasontype=2')
    if not isinstance(data.get('events'),list):raise ValueError('ESPN team schedule events missing')
    games={}
    for event in data['events']:
        if int(event['seasonType']['type'])!=2:continue
        competition=event['competitions'][0]
        if competition['status']['type'].get('completed') is not True:continue
        if int(event['season']['year'])!=year:raise ValueError('ESPN completed event belongs to another season')
        if tid not in {int(c['id']) for c in competition['competitors']}:raise ValueError('ESPN schedule team mismatch')
        stamp=datetime.fromisoformat(event['date'].replace('Z','+00:00'))
        if stamp.tzinfo is None or eastern_date(event['date'])>utils.today():raise ValueError('Invalid completed ESPN event date')
        eid=str(event['id']);record=dict(id=eid,year=year,stamp=stamp,date=str(eastern_date(event['date'])))
        if eid in games and games[eid]!=record:raise ValueError('Conflicting duplicate ESPN schedule event')
        games[eid]=record
    return games


def selected_games(team, year):
    games={};issue=None
    try:
        games=completed_team_games(team['id'],year)
        if len(games)<10:
            previous=completed_team_games(team['id'],year-1)
            if games.keys() & previous.keys():raise ValueError('ESPN event ID reused across seasons')
            games.update(previous)
    except (RuntimeError,ValueError,KeyError,TypeError,IndexError) as error:issue=str(error)
    return team,sorted(games.values(),key=lambda g:(g['stamp'],g['id']),reverse=True)[:10],issue


def game_defense(data, tid, game):
    header=data['header'];competition=header['competitions'][0]
    if str(header['id'])!=game['id'] or int(header['season']['year'])!=game['year'] or int(header['season']['type'])!=2:
        raise ValueError('ESPN defense summary event/season/type mismatch')
    if competition['status']['type'].get('completed') is not True or str(eastern_date(competition['date']))!=game['date']:
        raise ValueError('ESPN defense summary is not the selected completed game')
    competitors=competition['competitors']
    if len(competitors)!=2 or tid not in {int(c['id']) for c in competitors}:raise ValueError('ESPN defense competitors incomplete')
    opponent=next(c for c in competitors if int(c['id'])!=tid)
    side=next(t for t in data['boxscore']['teams'] if int(t['team']['id'])==int(opponent['id']))
    stats={s['name']:s.get('value') if s.get('value') is not None else s.get('displayValue') for s in side['statistics']}
    return number(opponent['score']),estimated_possessions(stats)


def defensive_ratings():
    year=utils.season_year();teams=utils.get_teams()
    selections=utils.parallel_map(lambda team:selected_games(team,year),teams)
    unique={g['id']:g for _,games,_ in selections for g in games}
    def load(eid):
        try:return eid,utils.read_json(f'{utils.SITE}/summary?event={eid}'),None
        except (RuntimeError,ValueError) as error:return eid,None,str(error)
    summaries={eid:(data,error) for eid,data,error in utils.parallel_map(load,sorted(unique))}
    ratings={};valid_count=0
    for team,games,issue in selections:
        valid=[];missing=[]
        for game in games:
            data,error=summaries[game['id']]
            try:
                if error:raise ValueError(error)
                points,possessions=game_defense(data,team['id'],game)
                valid.append((game,points,possessions))
            except (ValueError,KeyError,TypeError,IndexError,StopIteration) as error:
                missing.append(dict(id=game['id'],reason=str(error)))
        n=len(valid);valid_count+=n;complete=n==10 and len(games)==10 and not issue
        points=sum(v[1] for v in valid) if n else None;possessions=sum(v[2] for v in valid) if n else None
        dates=[v[0]['date'] for v in valid]
        ratings[team['abbreviation']]=dict(Estimated=True,Complete=complete,Games=n,
            DefRtg=100*points/possessions if complete else None,Rank=None,Population=0,
            Start=min(dates) if dates else None,End=max(dates) if dates else None,
            Seasons=sorted({utils.season_label(g['year']) for g in games},reverse=True),
            SelectedGameIds=[g['id'] for g in games],GameIds=[v[0]['id'] for v in valid],MissingGames=missing,
            OpponentPoints=points,EstimatedOpponentPossessions=possessions,Issue=issue)
    if not valid_count:
        utils.PROVENANCE['defense']=dict(status='unavailable',source=None,reason='ESPN selected game statistics unavailable',eligible_teams=0,last_game=None,teams={})
        return {}
    ranked=sorted((abbr for abbr,r in ratings.items() if r['Complete']),key=lambda abbr:(ratings[abbr]['DefRtg'],abbr))
    for rank,abbr in enumerate(ranked,1):ratings[abbr].update(Rank=rank,Population=len(ranked))
    utils.PROVENANCE['defense']=dict(source='ESPN',status='available' if len(ranked)==len(teams)==30 else 'partial',
        metric=METRIC,estimated=True,formula=FORMULA,season=utils.season_label(year),
        window='last 10 completed regular-season games per team; previous season carryover',
        eligible_teams=len(ranked),total_teams=30,last_game=max(r['End'] for r in ratings.values() if r['End']),teams=ratings)
    return ratings
