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
        definitions={'general':['gamesPlayed','avgMinutes','rebounds','avgRebounds'],'offensive':['avgPoints','fieldGoalPct','freeThrowPct','avgAssists','avgThreePointFieldGoalsMade','points','assists','threePointFieldGoalsMade'],'defensive':['avgSteals','avgBlocks','steals','blocks']}
        def athlete(pid):
            return {'athlete':{'id':str(pid),'displayName':'Test','teams':[{'abbreviation':'LAL'}]},'categories':[{'name':'general','values':[67,30,100,100/67]},{'name':'offensive','values':[31.597015,50,80,3,2,2117,201,134]},{'name':'defensive','values':[1.4179104,1,95,67]}]}
        page={'requestedSeason':{'year':2026,'type':{'type':2,'startDate':'s','endDate':'e'}},'pagination':{'pages':2,'count':2},'categories':[{'name':k,'names':v} for k,v in definitions.items()],'athletes':[athlete(1)]}
        other=deepcopy(page);other['athletes']=[athlete(2)]
        with patch.object(utils,'read_json',side_effect=[page,other]),patch.object(utils,'get_teams',return_value=[{'id':1,'abbreviation':'LAL'}]),patch.object(utils,'abbreviation',return_value='LAL'):
            df=utils.league_stats(2026)
        self.assertEqual(len(df),2);self.assertEqual(df.iloc[0]['PTS_TOTAL'],2117);self.assertEqual(df.iloc[0]['STL_TOTAL'],95)
        other['athletes']=[athlete(1)]
        with patch.object(utils,'read_json',side_effect=[page,other]):
            with self.assertRaises(ValueError):utils.league_stats(2026)
    def test_color_missing_is_neutral(self):
        self.assertEqual(utils.get_color_for_rank(None,0),'#eeeeee')
        self.assertEqual(utils.get_color_for_rank(1,30),'#ffcccc')
        self.assertEqual(utils.get_color_for_rank(30,30),'#ccffcc')

if __name__=='__main__':unittest.main()
