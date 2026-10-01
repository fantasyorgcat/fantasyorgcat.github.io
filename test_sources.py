import unittest
from unittest.mock import patch
from datetime import date, timedelta
import utils

class Sources(unittest.TestCase):
    def setUp(self):utils.PROVENANCE.clear()
    def defense_data(self,n=12):
        games=[];logs={'a':[],'b':[]}
        for i in range(n):
            eid=f'00226{i:05}';day=str(date(2026,10,20)+timedelta(days=i))
            games.append(dict(GameId=eid,Date=day,HomeTeamId='a',AwayTeamId='b',HomePoints=90+i,AwayPoints=100+i,HomeTeamAbbreviation='LAL',AwayTeamAbbreviation='OKC'))
            for team in logs:logs[team].append(dict(GameId=eid,Date=day,DefPoss=90+i))
        def reader(url):
            if '/get-games/' in url:return {'results':games}
            return {'multi_row_table_data':logs[url.split('EntityId=')[1]]}
        return games,logs,reader
    def test_last_ten_weighted_and_no_cross_season(self):
        games,logs,reader=self.defense_data()
        with patch.object(utils,'season_year',return_value=2027),patch.object(utils,'read_json',side_effect=reader),patch.object(utils,'abbreviation',side_effect=lambda x:x):
            ratings=utils.get_team_defensive_ratings()
        expected=100*sum(100+i for i in range(2,12))/sum(90+i for i in range(2,12))
        self.assertAlmostEqual(ratings['LAL']['DefRtg'],expected)
        self.assertEqual(ratings['LAL']['Games'],10)
        self.assertEqual(ratings['OKC']['Rank'],1)
        self.assertEqual(ratings['LAL']['Population'],2)
    def test_short_window(self):
        games,logs,reader=self.defense_data(3)
        with patch.object(utils,'season_year',return_value=2027),patch.object(utils,'read_json',side_effect=reader),patch.object(utils,'abbreviation',side_effect=lambda x:x):
            self.assertEqual(utils.get_team_defensive_ratings()['LAL']['Games'],3)
    def test_empty_and_placeholder_are_not_games(self):
        with patch.object(utils,'season_year',return_value=2027),patch.object(utils,'read_json',return_value={'results':[]}):
            self.assertEqual(utils.get_team_defensive_ratings(),{})
    def test_lag_and_duplicates_abort(self):
        games,logs,reader=self.defense_data()
        logs['a'].pop()
        with patch.object(utils,'season_year',return_value=2027),patch.object(utils,'read_json',side_effect=reader),patch.object(utils,'abbreviation',side_effect=lambda x:x):
            with self.assertRaises(ValueError):utils.get_team_defensive_ratings()
        games.append(games[0])
        with patch.object(utils,'season_year',return_value=2027),patch.object(utils,'read_json',side_effect=reader):
            with self.assertRaises(ValueError):utils.get_team_defensive_ratings()
    def test_wrong_season_aborts(self):
        games,logs,reader=self.defense_data()
        games[0]['GameId']='0022500001'
        with patch.object(utils,'season_year',return_value=2027),patch.object(utils,'read_json',side_effect=reader):
            with self.assertRaises(ValueError):utils.get_team_defensive_ratings()
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
