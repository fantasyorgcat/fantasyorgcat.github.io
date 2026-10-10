"""Explicit platform periods, kept separate from NBA event dates."""
import json
from datetime import date, timedelta
from pathlib import Path

YAHOO_DATES = Path(__file__).with_name('yahoo_game_dates_2026_27.json')
ESPN_DATES = Path(__file__).with_name('espn_weekly_dates_2026_27.json')


def validate_calendar(calendar):
    """Reject broken calendar edits; never infer missing or future-season weeks."""
    if calendar['timezone'] != 'America/New_York':
        raise ValueError('Unsupported fantasy calendar timezone')
    previous = None
    for number, period in enumerate(calendar['periods'], 1):
        start, end = date.fromisoformat(period['start']), date.fromisoformat(period['end'])
        if period['number'] != number or not 1 <= (end - start).days + 1 <= 31:
            raise ValueError('Invalid fantasy week number or length')
        if previous and start != previous + timedelta(days=1):
            raise ValueError('Fantasy periods must be continuous without overlaps')
        previous = end
    return calendar


def validate_espn_calendar(calendar):
    validate_calendar(calendar)
    source_season = calendar['source_season']
    if calendar['season'] != f'{source_season - 1}-{str(source_season)[-2:]}' or calendar['period_type'] != {'id': 2, 'description': 'Weekly'}:
        raise ValueError('Invalid ESPN source season or Weekly period type')
    anchor = date.fromisoformat(calendar['scoring_period_1_date'])
    lower, upper = calendar['regular_scoring_period_range']
    for period in calendar['periods']:
        first, last = period['scoring_period_start'], period['scoring_period_end']
        if not lower <= first <= last <= upper:
            raise ValueError('ESPN calendar includes non-regular scoring periods')
        expected = (str(anchor + timedelta(days=first - 1)), str(anchor + timedelta(days=last - 1)))
        if (period['start'], period['end']) != expected:
            raise ValueError('ESPN dates do not match verified scoring periods')
    return calendar


def build_platform_periods(season, weeks, events, yahoo_path=YAHOO_DATES, espn_path=ESPN_DATES):
    nba = [dict(number=w['number'], start=str(w['start']), end=str(w['end']),
                label=f'NBA Week {w["number"]} · {w["start"]}–{w["end"]}',
                platform='NBA', kind='site_eastern_calendar',
                events=sum(e['date_et'] is not None and str(w['start']) <= e['date_et'] <= str(w['end']) for e in events))
           for w in weeks]
    output = {
        'NBA': dict(available=bool(nba), official_platform_mapping=False, periods=nba,
                    note='NBA 賽程週：美東週一至週日；首場例行賽所在週為 Week 1。'),
        'YAHOO': dict(available=False, official_platform_mapping=False, periods=[],
                     note=f'Yahoo {season} 公開預設週表待核；可用自訂期間。'),
        'ESPN': dict(available=False, official_platform_mapping=False, periods=[],
                    note=f'ESPN {season} fantasy 週表待核；可用自訂期間。'),
    }
    calendar = validate_calendar(json.loads(yahoo_path.read_text(encoding='utf-8')))
    if calendar['season'] == season:
        periods = []
        for original in calendar['periods']:
            period = dict(original, platform='YAHOO', kind='yahoo_public_default')
            days = (date.fromisoformat(period['end']) - date.fromisoformat(period['start'])).days + 1
            playoff = calendar['default_playoffs']['start'] <= period['start'] <= calendar['default_playoffs']['end']
            period['default_playoff'] = playoff
            note = ' · 14天' if days == 14 else ''
            if playoff:
                note += ' · 預設季後賽'
            period['label'] = f'Yahoo Week {period["number"]} · {period["start"]}–{period["end"]}{note}'
            periods.append(period)
        output['YAHOO'] = dict(available=bool(periods), official_platform_mapping=True, periods=periods,
                               source_url=calendar['source_url'], verified_at=calendar['verified_at'],
                               scope=calendar['scope'], default_playoffs=calendar['default_playoffs'],
                               note='Yahoo 公開預設週次；自訂聯盟日期可能不同。週表核對：2026-10-10。')
    calendar = validate_espn_calendar(json.loads(espn_path.read_text(encoding='utf-8')))
    if calendar['season'] == season:
        periods = []
        for original in calendar['periods']:
            days = (date.fromisoformat(original['end']) - date.fromisoformat(original['start'])).days + 1
            note = ' · 14天' if days == 14 else ''
            periods.append(dict(original, platform='ESPN', kind='espn_public_weekly',
                                label=f'ESPN Week {original["number"]} · {original["start"]}–{original["end"]}{note}'))
        output['ESPN'] = dict(available=bool(periods), official_platform_mapping=True, periods=periods,
                              source_url=calendar['source_url'], verified_at=calendar['verified_at'],
                              source_season=calendar['source_season'], period_type=calendar['period_type'],
                              source_sha256=calendar['source_sha256'], scope=calendar['scope'],
                              note='ESPN 官方全季 Weekly 週曆；聯盟 matchup／季後賽日期可自訂，請核對聯盟設定或使用自訂期間。週表核對：2026-10-10。')
    return output
