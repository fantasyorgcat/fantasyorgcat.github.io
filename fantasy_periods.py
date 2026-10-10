"""Explicit platform periods, kept separate from NBA event dates."""
import json
from datetime import date, timedelta
from pathlib import Path

YAHOO_DATES = Path(__file__).with_name('yahoo_game_dates_2026_27.json')


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


def build_platform_periods(season, weeks, events, yahoo_path=YAHOO_DATES):
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
    return output
