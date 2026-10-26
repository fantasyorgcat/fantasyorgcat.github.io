import unittest
from unittest.mock import patch
from datetime import date, timedelta
import utils

class Sources(unittest.TestCase):
    def setUp(self):utils.PROVENANCE.clear()
    def test_unknown_team_aborts(self):
        with patch.object(utils,'get_teams',return_value=[{'abbreviation':'LAL'}]):
            self.assertEqual(utils.abbreviation('LAL'),'LAL')
            with self.assertRaises(ValueError):utils.abbreviation("<script>")

    def test_single_malformed_team_record_and_global_team_corruption(self):
        teams=[dict(team=dict(id=str(i),abbreviation='A'+chr(65+i//26)+chr(65+i%26))) for i in range(30)]
        response=dict(sports=[dict(leagues=[dict(season={'year':2027},teams=teams)])])
        utils.get_teams.cache_clear()
        try:
            with patch.object(utils,'season_year',return_value=2027),patch.object(utils,'read_json',return_value=response):
                teams[0]={}
                self.assertEqual(len(utils.get_teams()),29)
                self.assertTrue(utils.PROVENANCE['source_warnings'])
                utils.get_teams.cache_clear();teams[1:5]=[{}]*4
                with self.assertRaisesRegex(ValueError,'globally broken'):utils.get_teams()
        finally:utils.get_teams.cache_clear()

    def test_roster_missing_fields_and_single_team_failure_are_bounded(self):
        utils.get_roster.cache_clear()
        teams=[dict(id=i,abbreviation='AAA') for i in [1,2,3]]
        def read(url):
            tid=int(url.split('/teams/')[1].split('/')[0])
            return dict(status='success',season={'year':2027},athletes=[dict(id=tid*10,displayName='Player'),{} if tid==1 else dict(id=tid*10+1,displayName='Another')])
        try:
            with patch.object(utils,'season_year',return_value=2027),patch.object(utils,'get_teams',return_value=teams),patch.object(utils,'read_json',side_effect=read):
                frame=utils.get_roster();self.assertEqual(set(frame.PLAYER_ID),{10,20,21,30,31})
                self.assertEqual(len([w for w in utils.PROVENANCE['source_warnings'] if w['source']=='roster']),1)
            utils.get_roster.cache_clear()
            with patch.object(utils,'season_year',return_value=2027),patch.object(utils,'get_teams',return_value=teams),patch.object(utils,'read_json',return_value={}):
                with self.assertRaisesRegex(ValueError,'globally broken'):utils.get_roster()
        finally:utils.get_roster.cache_clear()

    def test_external_numbers_are_unknown_with_diagnostics_and_never_zero(self):
        for v in ['DNP','weird',None,'',float('nan'),True,{},'1:60']:
            with self.subTest(value=v):
                self.assertIsNone(utils.parse_minutes(v,'test','player-1'))
                self.assertIsNone(utils.optional_number(v,'test','player-1',total=True))
        self.assertTrue(all(w['record']=='player-1' for w in utils.PROVENANCE['source_warnings']))
    def test_recent_calendar_window_weighted_rates_and_exact_totals(self):
        import pandas as pd
        player=dict(PLAYER_ID=1,PLAYER_NAME='Test',TEAM_ID=1,TEAM_ABBREVIATION='LAL',GP=3)
        logs=[]
        for day,made,attempted,pts in [(date(2026,10,22),1,2,5),(date(2026,10,28),9,10,23),(date(2026,10,29),2,4,9)]:
            row=dict(date=day,MIN=30,PTS=pts,REB=3,AST=2,STL=1,BLK=0,FG3M=1,FGM=made,FGA=attempted,FTM=1,FTA=2)
            logs.append(row)
        with patch.object(utils,'today',return_value=date(2026,10,29)),patch.object(utils,'player_gamelog',return_value=logs):
            l7,l14=utils.recent_stats(pd.DataFrame([player]),2027)
        self.assertEqual(l7.iloc[0]['GP'],2)
        self.assertEqual(l7.iloc[0]['PTS_TOTAL'],28)
        self.assertAlmostEqual(l7.iloc[0]['FG_PCT'],10/12)
        self.assertEqual(l14.iloc[0]['GP'],2)
        with patch.object(utils,'today',return_value=date(2026,10,29)),patch.object(utils,'player_gamelog',return_value=logs[:2]):
            with self.assertRaises(ValueError):utils.recent_stats(pd.DataFrame([player]),2027)
    def test_paginated_full_population_and_source_integer_totals(self):
        from copy import deepcopy
        definitions={'general':['gamesPlayed','avgMinutes','rebounds','avgRebounds'],'offensive':['avgPoints','fieldGoalPct','freeThrowPct','avgAssists','avgThreePointFieldGoalsMade','points','assists','threePointFieldGoalsMade','avgTurnovers','turnovers'],'defensive':['avgSteals','avgBlocks','steals','blocks']}
        def athlete(pid):
            return {'athlete':{'id':str(pid),'displayName':'Test','teams':[{'abbreviation':'LAL'}]},'categories':[{'name':'general','values':[67,30,100,100/67]},{'name':'offensive','values':[31.597015,50,80,3,2,2117,201,134,'1.492537','100']},{'name':'defensive','values':[1.4179104,1,95,67]}]}
        page={'requestedSeason':{'year':2026,'type':{'type':2,'startDate':'s','endDate':'e'}},'pagination':{'pages':2,'count':2},'categories':[{'name':k,'names':v} for k,v in definitions.items()],'athletes':[athlete(1)]}
        other=deepcopy(page);other['athletes']=[athlete(2)]
        with patch.object(utils,'read_json',side_effect=[page,other]),patch.object(utils,'get_teams',return_value=[{'id':1,'abbreviation':'LAL'}]),patch.object(utils,'abbreviation',return_value='LAL'):
            df=utils.league_stats(2026)
        self.assertEqual(len(df),2);self.assertEqual(df.iloc[0]['PTS_TOTAL'],2117);self.assertEqual(df.iloc[0]['STL_TOTAL'],95)
        self.assertEqual(df.iloc[0]['TO'],1.492537);self.assertEqual(df.iloc[0]['TO_TOTAL'],100)
        other['athletes']=[athlete(1)]
        with patch.object(utils,'read_json',side_effect=[page,other]),patch.object(utils,'get_teams',return_value=[{'id':1,'abbreviation':'LAL'}]),patch.object(utils,'abbreviation',return_value='LAL'):
            deduplicated=utils.league_stats(2026)
        self.assertEqual(len(deduplicated),1);self.assertEqual(deduplicated.iloc[0]['PTS_TOTAL'],2117)
        self.assertIn('Duplicate league',utils.PROVENANCE['source_warnings'][-1]['reason'])
    def test_color_missing_is_neutral(self):
        self.assertEqual(utils.get_color_for_rank(None,0),'#dedbd5')
        self.assertEqual(utils.get_color_for_rank(1,30),'#dfc5c8')
        self.assertEqual(utils.get_color_for_rank(30,30),'#c5d5dc')
    def test_season_type_mismatch_reports_source_context_and_still_aborts(self):
        for returned_year,returned_type in [(2026,2),(2027,1),(2027,3)]:
            with self.subTest(year=returned_year,season_type=returned_type):
                response={'requestedSeason':{'year':returned_year,'type':{'type':returned_type}},
                          'currentSeason':{'year':2027,'type':{'id':'1','type':1}},'athletes':[]}
                with patch.object(utils,'read_json',return_value=response):
                    with self.assertRaises(ValueError) as caught:utils.league_stats(2027)
                message=str(caught.exception)
                self.assertIn('expected season=2027, type=2',message)
                self.assertIn(f'returned season={returned_year!r}, type={returned_type!r}',message)
                self.assertIn("current season=2027, type={'id': '1', 'type': 1}",message)
                self.assertIn('athletes=0',message)
                self.assertIn('season=2027&seasontype=2&limit=1000',message)
    def test_turnover_numeric_strings_zero_null_and_invalid(self):
        self.assertEqual(utils.parse_turnovers('0',total=True),0)
        self.assertEqual(utils.parse_turnovers(' 2.5 '),2.5)
        for value in [None,'','--','N/A']:
            self.assertIsNone(utils.parse_turnovers(value))
        for value in [-1,'bad',float('inf'),True]:
            with self.assertRaises(ValueError):utils.parse_turnovers(value)
        with self.assertRaises(ValueError):utils.parse_turnovers('2.5',total=True)
    def test_recent_turnovers_per_game_exact_total_and_missing_not_zero(self):
        import pandas as pd
        player=dict(PLAYER_ID=1,PLAYER_NAME='Test',TEAM_ID=1,TEAM_ABBREVIATION='LAL',GP=2)
        logs=[dict(date=date(2026,10,27+i),MIN=20,PTS=5,REB=1,AST=1,STL=0,BLK=0,FG3M=0,FGM=1,FGA=2,FTM=1,FTA=2,TO=to) for i,to in enumerate([0,4])]
        with patch.object(utils,'today',return_value=date(2026,10,29)),patch.object(utils,'player_gamelog',return_value=logs):
            l7,_=utils.recent_stats(pd.DataFrame([player]),2027)
        self.assertEqual(l7.iloc[0].TO,2);self.assertEqual(l7.iloc[0].TO_TOTAL,4)
        logs[1]['TO']=None
        with patch.object(utils,'today',return_value=date(2026,10,29)),patch.object(utils,'player_gamelog',return_value=logs):
            l7,_=utils.recent_stats(pd.DataFrame([player]),2027)
        self.assertTrue(pd.isna(l7.iloc[0].TO));self.assertTrue(pd.isna(l7.iloc[0].TO_TOTAL))
    def test_player_log_turnovers_real_key_and_missing(self):
        d={'filters':[{'name':'season','value':'2026'}],
           'names':['minutes','points','totalRebounds','assists','steals','blocks','fieldGoalsMade-fieldGoalsAttempted','freeThrowsMade-freeThrowsAttempted','threePointFieldGoalsMade-threePointFieldGoalsAttempted','turnovers'],
           'events':{'game':{'gameDate':'2026-04-01T23:00:00Z'}},
           'seasonTypes':[{'displayName':'2025-26 Regular Season','categories':[{'type':'event','events':[{'eventId':'game','stats':['20','5','1','1','0','0','1-2','1-2','0-1','0']}]}]}]}
        with patch.object(utils,'read_json',return_value=d):
            self.assertEqual(utils.player_gamelog({'PLAYER_ID':1},2026)[0]['TO'],0)
        d['names'].pop();d['seasonTypes'][0]['categories'][0]['events'][0]['stats'].pop()
        with patch.object(utils,'read_json',return_value=d):
            self.assertIsNone(utils.player_gamelog({'PLAYER_ID':1},2026)[0]['TO'])
        d['seasonTypes'][0]['displayName']='2026-27 Regular Season'
        with patch.object(utils,'read_json',return_value=d):
            with self.assertRaisesRegex(ValueError,'available groups=.*2026-27 Regular Season'):
                utils.player_gamelog({'PLAYER_ID':1,'GP':1},2026)

if __name__=='__main__':unittest.main()
