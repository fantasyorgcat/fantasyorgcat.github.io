import pandas as pd
from datetime import datetime, timedelta
from nba_api.stats.endpoints import leaguegamefinder, leaguedashplayerstats, leaguedashteamstats
from nba_api.stats.static import teams, players
import time
import requests

# Constants
CACHE_DURATION = 3600 # 1 hour

def get_schedule(start_date, end_date):
    """
    Fetches schedule between start_date and end_date.
    Returns a DataFrame with columns: [TEAM_ID, TEAM_ABBREVIATION, GAME_DATE, MATCHUP]
    """
    # LeagueGameFinder contains played games, not the future league schedule.
    response = requests.get(
        'https://cdn.nba.com/static/json/staticData/scheduleLeagueV2.json',
        timeout=30,
    )
    response.raise_for_status()
    league_schedule = response.json()['leagueSchedule']
    start_year = start_date.year if start_date.month >= 10 else start_date.year - 1
    expected_season = f'{start_year}-{str(start_year + 1)[-2:]}'
    if str(league_schedule['seasonYear']) != expected_season:
        raise RuntimeError(f"Official schedule is for {league_schedule['seasonYear']}, expected {expected_season}; refusing stale schedule")
    game_dates = league_schedule['gameDates']
    rows = []
    for date_group in game_dates:
        for game in date_group['games']:
            game_date = pd.to_datetime(game['gameDateTimeEst']).date()
            # Schedule includes preseason: regular-season NBA game IDs start 002.
            if not str(game['gameId']).startswith('002'):
                continue
            if not start_date <= game_date <= end_date:
                continue
            home, away = game['homeTeam'], game['awayTeam']
            for team, opponent, marker in [(home, away, 'vs.'), (away, home, '@')]:
                rows.append(dict(TEAM_ID=int(team['teamId']),
                                 TEAM_ABBREVIATION=team['teamTricode'],
                                 GAME_DATE=game_date,
                                 MATCHUP=f"{team['teamTricode']} {marker} {opponent['teamTricode']}"))
    return pd.DataFrame(rows, columns=['TEAM_ID', 'TEAM_ABBREVIATION', 'GAME_DATE', 'MATCHUP'])


def get_active_player_ids():
    """
    Returns a set of PLAYER_IDs for players currently on an NBA roster,
    from nba_api's bundled static player list (no network call).

    Trade-off: the static list ships with the installed nba_api version, so it
    can lag real roster moves by a package release. Chosen anyway because it is
    zero-cost and can't fail at runtime; it's only used as a coarse filter to
    keep long-retired players out of the report, not for any stat math.
    """
    return {p['id'] for p in players.get_active_players()}

def get_last_complete_season_str(reference_date=None):
    """
    Returns the most recently *completed* NBA regular season as "YYYY-YY"
    (e.g. "2025-26"), computed from the current date rather than relying on
    nba_api's own default season resolution.

    NBA seasons run roughly October -> June. We use July 1st as the cutoff:
    from July onward, the Finals of the season that started the previous
    October have already concluded, so that season counts as "last complete
    season". Before July, that season may still be in progress, so we step
    back one more year.
    """
    d = reference_date or datetime.now().date()
    if d.month >= 7:
        start_year = d.year - 1
    else:
        start_year = d.year - 2
    return f"{start_year}-{str(start_year + 1)[-2:]}"

def get_player_stats_multi_period():
    """
    Fetches stats for:
    1. Explicit current regular season
    2. Last 7 Days
    3. Last 14 Days
    4. Last Season (previous full completed season - useful early in a new
       season, or in the off-season, when Season/L7/L14 are thin or empty)

    Returns a dictionary of DataFrames: {'Season': df, 'L7': df, 'L14': df, 'LastSeason': df}
    """

    today = datetime.now().date()
    start_year = today.year if today.month >= 10 else today.year - 1
    current_season = f"{start_year}-{str(start_year + 1)[-2:]}"
    last_season = get_last_complete_season_str(today)
    columns = ['PLAYER_ID', 'PLAYER_NAME', 'TEAM_ID', 'TEAM_ABBREVIATION', 'GP',
               'MIN', 'PTS', 'REB', 'AST', 'STL', 'BLK', 'FG_PCT', 'FT_PCT', 'FG3M']

    def fetch_stats(season, date_from=None):
        stats = leaguedashplayerstats.LeagueDashPlayerStats(
            season=season, per_mode_detailed='PerGame',
            season_type_all_star='Regular Season',
            date_from_nullable=date_from.strftime('%m/%d/%Y') if date_from else '',
            date_to_nullable=today.strftime('%m/%d/%Y'), timeout=30,
        )
        df = stats.get_data_frames()[0].reindex(columns=columns)
        df['TEAM_ID'] = df['TEAM_ID'].astype(int)
        return df[df['GP'] > 0].copy()

    print(f"Fetching current regular season {current_season}; last completed {last_season}")
    season_data = fetch_stats(current_season)
    last_data = season_data.copy() if current_season == last_season else fetch_stats(last_season)
    if season_data.empty and last_data.empty:
        raise RuntimeError('NBA returned no current or last-season player statistics; refusing to publish an empty report')
    return {
        'Season': season_data,
        'L7': fetch_stats(current_season, today - timedelta(days=7)),
        'L14': fetch_stats(current_season, today - timedelta(days=14)),
        'LastSeason': last_data,
        'metadata': {'season': current_season, 'last_season': last_season},
    }


def get_team_defensive_ratings():
    """
    Fetches team defensive ratings.
    Returns a dict: {TeamAbbr: {'Rank': int, 'DefRtg': float}}
    """
    # Use 'Advanced' to get DEF_RATING
    stats_adv = leaguedashteamstats.LeagueDashTeamStats(
        per_mode_detailed='PerGame',
        season_type_all_star='Regular Season',
        measure_type_detailed_defense='Advanced',
        season=get_last_complete_season_str(), timeout=30
    )
    df = stats_adv.get_data_frames()[0]

    # Create ID -> Abbr map
    nba_teams = teams.get_teams()
    id_to_abbr = {team['id']: team['abbreviation'] for team in nba_teams}

    # Sort by DEF_RATING
    if 'DEF_RATING' in df.columns:
        df = df.sort_values('DEF_RATING', ascending=True) # 1=Best
    else:
        # Fallback: Sort by W_PCT (Better teams are usually harder)
        df = df.sort_values('W_PCT', ascending=False)

    df['DEF_RANK'] = range(1, len(df) + 1)

    # Create map: ABBR -> Rank
    def_map = {}
    for _, row in df.iterrows():
        tid = row['TEAM_ID']
        abbr = id_to_abbr.get(tid, 'UNK')

        def_map[abbr] = {
            'Rank': row['DEF_RANK'],
            'DefRtg': row.get('DEF_RATING', 0.0)
        }

    return def_map

def get_color_for_rank(rank):
    """
    Returns a hex color based on rank (1-30).
    Rank 1 (Best Def) -> Red (Bad for Fantasy)
    Rank 30 (Worst Def) -> Green (Good for Fantasy)
    """
    # 5-step scale
    if rank <= 6:
        return "#ffcccc" # Red (Hard)
    elif rank <= 12:
        return "#ffe5cc" # Orange
    elif rank <= 18:
        return "#ffffcc" # Yellow
    elif rank <= 24:
        return "#e5ffcc" # Light Green
    else:
        return "#ccffcc" # Green (Easy)
