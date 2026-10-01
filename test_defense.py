import unittest
from unittest.mock import patch
from datetime import date,datetime,timedelta,timezone
from urllib.parse import urlparse,parse_qs
import utils

class Defense(unittest.TestCase):
    def setUp(self):utils.PROVENANCE.clear()
    def data(self,current=0,previous=12,year=2027):
        games={};logs={}
        for end_year,n in [(year,current),(year-1,previous)]:
            label=utils.season_label(end_year);games[label]=[];logs[label]={team:[] for team in ['a','b']}
            for i in range(n):
                gid=f'002{str(end_year-1)[-2:]}{i:05}'
                day=str((date(end_year-1,10,20) if end_year==year else date(end_year,4,1))+timedelta(days=i))
                game=dict(GameId=gid,Date=day,HomeTeamId='a',AwayTeamId='b',HomePoints=90+i,AwayPoints=100+i,HomeTeamAbbreviation='LAL',AwayTeamAbbreviation='OKC')
                games[label].append(game)
                for team in logs[label]:logs[label][team].append(dict(GameId=gid,Date=day,DefPoss=90+i))
        def reader(url):
            q=parse_qs(urlparse(url).query);season=q['Season'][0]
            if '/get-games/' in url:return {'results':games[season]}
            return {'multi_row_table_data':logs[season][q['EntityId'][0]]}
        return games,logs,reader
    def ratings(self,reader,year=2027,cutoff=None):
        with patch.object(utils,'season_year',return_value=year),patch.object(utils,'today',return_value=cutoff or date(year-1,11,30)),patch.object(utils,'read_json',side_effect=reader),patch.object(utils,'abbreviation',side_effect=lambda x:x):
            return utils.get_team_defensive_ratings()
    def test_new_season_0_1_9_10_11_current_games(self):
        for n in [0,1,9,10,11]:
            with self.subTest(current=n):
                games,logs,reader=self.data(n);ratings=self.ratings(reader)
                allgames=[g for group in games.values() for g in group]
                selected=sorted(allgames,key=lambda g:(g['Date'],g['GameId']),reverse=True)[:10]
                lookup={r['GameId']:r for group in logs.values() for r in group['a']}
                expected=100*sum(g['AwayPoints'] for g in selected)/sum(lookup[g['GameId']]['DefPoss'] for g in selected)
                self.assertAlmostEqual(ratings['LAL']['DefRtg'],expected)
                self.assertEqual(ratings['LAL']['Games'],10)
                self.assertEqual(ratings['LAL']['GameIds'],[g['GameId'] for g in selected])
                self.assertEqual(ratings['OKC']['Rank'],1)
                self.assertEqual(len(ratings['LAL']['Seasons']),2 if 0<n<10 else 1)
    def test_0_1_9_10_11_total_available_games(self):
        for n in [0,1,9,10,11]:
            with self.subTest(total=n):
                games,logs,reader=self.data(n,0);ratings=self.ratings(reader)
                if n==0:self.assertEqual(ratings,{})
                else:self.assertEqual(ratings['LAL']['Games'],min(n,10))
    def test_2027_28_is_dynamic(self):
        games,logs,reader=self.data(1,12,2028);r=self.ratings(reader,2028)
        self.assertEqual(r['LAL']['Seasons'],['2027-28','2026-27'])
        self.assertTrue(r['LAL']['GameIds'][0].startswith('00227'))
    def test_dec31_to_jan1_same_season(self):
        games,logs,reader=self.data(8)
        label='2026-27'
        for i,g in enumerate(games[label]):
            day=str(date(2026,12,25)+timedelta(days=i));g['Date']=day
            for team in ['a','b']:logs[label][team][i]['Date']=day
        dec=self.ratings(reader,cutoff=date(2026,12,31));jan=self.ratings(reader,cutoff=date(2027,1,1))
        self.assertEqual(dec['LAL']['End'],'2026-12-31');self.assertEqual(jan['LAL']['End'],'2027-01-01')
        self.assertEqual(dec['LAL']['Games'],10);self.assertEqual(jan['LAL']['Games'],10)
        self.assertEqual(dec['LAL']['Seasons'],jan['LAL']['Seasons'])
    def test_season_resolver_dec_jan_and_new_year(self):
        for now,year in [(datetime(2026,12,31,tzinfo=timezone.utc),2027),(datetime(2027,1,1,tzinfo=timezone.utc),2027),(datetime(2027,10,1,tzinfo=timezone.utc),2028)]:
            class Clock(datetime):
                @classmethod
                def now(cls,tz=None):return now
            with patch.object(utils,'datetime',Clock),patch.object(utils,'read_json',return_value={'sports':[{'leagues':[{'season':{'year':year}}]}]}):self.assertEqual(utils.season_year(),year)
    def test_preseason_postseason_future_and_unfinished_excluded(self):
        games,logs,reader=self.data(1)
        games['2026-27'].extend([{'GameId':'0012600001'},{'GameId':'0042600001'}])
        template=dict(games['2026-27'][0])
        for gid,day,scores in [('0022600010','2026-12-01',(120,110)),('0022600011','2026-10-21',(None,None)),('0022600012','2026-10-22',(0,0))]:
            games['2026-27'].append(dict(template,GameId=gid,Date=day,HomePoints=scores[0],AwayPoints=scores[1]))
        r=self.ratings(reader)
        self.assertFalse(any(gid in r['LAL']['GameIds'] for gid in ['0022600010','0022600011','0022600012']))
    def test_identical_game_and_log_duplicates_deduplicated(self):
        games,logs,reader=self.data(1)
        games['2026-27'].append(dict(games['2026-27'][0]))
        for team in ['a','b']:logs['2026-27'][team].append(dict(logs['2026-27'][team][0]))
        r=self.ratings(reader);self.assertEqual(len(set(r['LAL']['GameIds'])),10)
    def test_missing_or_invalid_selected_possessions_abort(self):
        for damage in ['missing','zero','nan','date','conflict']:
            games,logs,reader=self.data(1)
            row=logs['2026-27']['a'][0]
            if damage=='missing':logs['2026-27']['a']=[]
            elif damage=='zero':row['DefPoss']=0
            elif damage=='nan':row['DefPoss']=float('nan')
            elif damage=='date':row['Date']='2026-10-19'
            else:logs['2026-27']['a'].append(dict(row,DefPoss=1))
            with self.subTest(damage=damage):
                with self.assertRaises(ValueError):self.ratings(reader)
    def test_missing_prior_source_aborts(self):
        games,logs,reader=self.data(1)
        def missing(url):
            if 'Season=2025-26' in url:raise RuntimeError('source unavailable')
            return reader(url)
        with self.assertRaises(RuntimeError):self.ratings(missing)
    def test_wrong_regular_season_and_conflicting_score_abort(self):
        for damage in ['season','score','missing-score']:
            games,logs,reader=self.data(1)
            if damage=='season':games['2026-27'][0]['GameId']='0022500000'
            elif damage=='score':games['2026-27'].append(dict(games['2026-27'][0],HomePoints=999))
            else:del games['2026-27'][0]['AwayPoints']
            with self.subTest(damage=damage):
                with self.assertRaises((ValueError,KeyError)):self.ratings(reader)

if __name__=='__main__':unittest.main()
