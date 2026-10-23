"""Synthetic ESPN contract cases; never used as production source data."""
import copy
from datetime import date
import unittest
from unittest.mock import patch
import pandas as pd
import utils
from espn_boxscores import current_stats, summary_rows

KEYS=['minutes','points','rebounds','assists','steals','blocks','turnovers',
      'fieldGoalsMade-fieldGoalsAttempted','freeThrowsMade-freeThrowsAttempted',
      'threePointFieldGoalsMade-threePointFieldGoalsAttempted']


def event(eid, stamp, kind=2, completed=True):
    return dict(id=eid,date=stamp,season=dict(year=2027,type=kind),status=dict(type=dict(completed=completed)))


def summary(game, second=False):
    sides=[]
    for tid in ['1','2']:
        stats=['30:30','9','4','3','1','2','2','3-9','2-3','1-4'] if second else ['20','5','2','1','0','1','0','2-4','1-2','0-1']
        athlete=dict(athlete=dict(id=tid,displayName='TEST ONLY '+tid),didNotPlay=False,active=not second,reason='not a participation flag',stats=stats)
        dnp=dict(athlete=dict(id='99',displayName='TEST ONLY DNP'),didNotPlay=True,stats=[])
        sides.append(dict(team=dict(id=tid),statistics=[dict(keys=KEYS,athletes=[athlete,dnp])]))
    return dict(header=dict(id=game['id'],season=game['season'],competitions=[dict(date=game['date'],status=game['status'],competitors=[dict(id='1'),dict(id='2')])]),boxscore=dict(players=sides))


class ESPNBoxscores(unittest.TestCase):
    def setUp(self):
        utils.PROVENANCE.clear()
        self.games=[event('g1','2026-10-21T01:50:00Z'),event('g2','2026-10-23T01:30:00Z')]
        self.summaries={g['id']:summary(g,i==1) for i,g in enumerate(self.games)}
        self.calls=[]
    def read(self,url):
        self.calls.append(url)
        if '/scoreboard?' in url:
            return {'events':self.games if 'dates=202610&' in url else []}
        if '/summary?event=' in url:return self.summaries[url.split('event=')[1]]
        raise AssertionError('Current statistics must use only scoreboard/summary: '+url)
    def run_source(self):
        with patch.object(utils,'today',return_value=date(2026,10,23)),patch.object(utils,'read_json',side_effect=self.read),patch.object(utils,'get_teams',return_value=[dict(id=1,abbreviation='LAL'),dict(id=2,abbreviation='BOS')]):
            return current_stats(2027)
    def test_one_game_ledger_produces_all_periods_with_weighted_rates_and_real_zero(self):
        season,l7,l14=self.run_source();row=season.set_index('PLAYER_ID').loc[1]
        self.assertEqual(row.GP,2);self.assertEqual(row.PTS_TOTAL,14);self.assertEqual(row.PTS,7)
        self.assertEqual(row.TO_TOTAL,2);self.assertEqual(row.TO,1)
        self.assertAlmostEqual(row.FG_PCT,5/13);self.assertAlmostEqual(row.FT_PCT,3/5)
        self.assertEqual(row.MIN,(20+30.5)/2)
        self.assertEqual(set(season.PLAYER_ID),{1,2})
        self.assertEqual(l7.to_dict('records'),season.to_dict('records'));self.assertEqual(l14.to_dict('records'),season.to_dict('records'))
        self.assertEqual(utils.PROVENANCE['current_stats_last_game'],'2026-10-22')
        self.assertEqual(utils.PROVENANCE['current_stats_source']['completed_events'],['g1','g2'])
        self.assertEqual(utils.PROVENANCE['current_stats_source']['player_game_rows'],4)
    def test_current_day_is_in_season_but_excluded_from_recent_complete_day_windows(self):
        self.games=[event('g1','2026-10-09T23:00:00Z'),event('g2','2026-10-16T23:00:00Z'),event('g3','2026-10-23T05:00:00Z')]
        self.summaries={g['id']:summary(g) for g in self.games}
        season,l7,l14=self.run_source()
        self.assertTrue((season.GP==3).all());self.assertTrue((l7.GP==1).all());self.assertTrue((l14.GP==2).all())
    def test_new_appearance_enters_the_full_population_without_overview_or_roster_filtering(self):
        group=self.summaries['g2']['boxscore']['players'][0]['statistics'][0]
        newcomer=copy.deepcopy(group['athletes'][0]);newcomer['athlete']={'id':'3','displayName':'TEST ONLY newcomer'}
        group['athletes'].append(newcomer)
        season,l7,l14=self.run_source()
        self.assertEqual(set(season.PLAYER_ID),{1,2,3})
        self.assertEqual(season.set_index('PLAYER_ID').loc[3].GP,1)
        self.assertEqual(set(l7.PLAYER_ID),{1,2,3});self.assertEqual(set(l14.PLAYER_ID),{1,2,3})
    def test_preseason_and_unfinished_games_are_excluded(self):
        self.games.extend([event('pre','2026-10-10T23:00:00Z',kind=1),event('live','2026-10-23T05:00:00Z',completed=False)])
        season,_,_=self.run_source();self.assertTrue((season.GP==2).all())
        self.assertFalse(any('event=pre' in u or 'event=live' in u for u in self.calls))
    def test_duplicate_events_or_appearances_are_rejected(self):
        self.games.append(copy.deepcopy(self.games[0]))
        with self.assertRaisesRegex(ValueError,'Duplicate completed'):self.run_source()
        self.games.pop();players=self.summaries['g1']['boxscore']['players'][0]['statistics'][0]['athletes']
        players.append(copy.deepcopy(players[0]))
        with self.assertRaisesRegex(ValueError,'Duplicate ESPN player'):self.run_source()
    def test_wrong_summary_season_and_nonfinal_summary_are_rejected(self):
        self.summaries['g1']['header']['season']={'year':2026,'type':2}
        with self.assertRaisesRegex(ValueError,'season/type mismatch'):self.run_source()
        self.summaries['g1']=summary(self.games[0]);self.summaries['g1']['header']['competitions'][0]['status']={'type':{'completed':False}}
        with self.assertRaisesRegex(ValueError,'expected completed game'):self.run_source()
    def test_missing_played_player_stats_are_not_zero_filled(self):
        player=self.summaries['g1']['boxscore']['players'][0]['statistics'][0]['athletes'][0]
        player['stats'][1]='--'
        with self.assertRaisesRegex(ValueError,'Missing ESPN points'):self.run_source()
        player['stats']=[]
        with self.assertRaisesRegex(ValueError,'stats incomplete'):self.run_source()
    def test_no_completed_games_has_no_fabricated_current_statistics(self):
        self.games=[];frames=self.run_source()
        self.assertTrue(all(f.empty for f in frames));self.assertIsNone(utils.PROVENANCE['current_stats_last_game'])
        self.assertFalse(any('/summary?' in u for u in self.calls))
    def test_pipeline_keeps_historical_bulk_separate_from_current_ledger(self):
        current,l7,l14=self.run_source();old=current.copy();old['GP']=50
        with patch.object(utils,'season_year',return_value=2027),patch.object(utils,'get_last_complete_season_str',return_value='2025-26'),patch('espn_boxscores.current_stats',return_value=(current,l7,l14)),patch.object(utils,'league_stats',return_value=old) as historical,patch.object(utils,'get_roster',return_value=current[utils.IDENTITY]):
            data=utils.get_player_stats_multi_period()
        historical.assert_called_once_with(2026)
        self.assertEqual(data['Season'].iloc[0].GP,2);self.assertEqual(data['LastSeason'].iloc[0].GP,50)


if __name__=='__main__':unittest.main()
