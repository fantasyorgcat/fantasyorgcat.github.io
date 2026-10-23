import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from datetime import date,datetime,timedelta,timezone
from urllib.parse import urlparse,parse_qs
import utils
from espn_defense import defensive_ratings,estimated_possessions,completed_team_games
from generate_report import matchup_badge
from security_gate import PublicHTML,check,check_defense_provenance

class Defense(unittest.TestCase):
    def setUp(self):utils.PROVENANCE.clear()
    def sources(self,count=30):
        names=['LAL','BOS','ATL','BKN','CHA','CHI','CLE','DAL','DEN','DET','GSW','HOU','IND','LAC','MEM','MIA','MIL','MIN','NOP','NYK','OKC','ORL','PHI','PHX','POR','SAC','SAS','TOR','UTA','WAS']
        teams=[dict(id=i+1,abbreviation=name) for i,name in enumerate(names[:count])]
        schedules={};summaries={};calls=[]
        for team in teams:schedules[team['id'],2027]=[];schedules[team['id'],2026]=[]
        for pair in range(count//2):
            ids=[pair*2+1,pair*2+2]
            for year,n in [(2027,2),(2026,12)]:
                for i in range(n):
                    stamp=((datetime(2026,10,22,23,tzinfo=timezone.utc) if year==2027 else datetime(2026,4,12,23,tzinfo=timezone.utc))-timedelta(days=i)).isoformat()
                    eid=f'{year}-{pair}-{i}'
                    competitors=[dict(id=str(tid),score=str(100 if j==0 else 90)) for j,tid in enumerate(ids)]
                    competition=dict(date=stamp,status={'type':{'completed':True}},competitors=competitors)
                    event=dict(id=eid,date=stamp,season={'year':year},seasonType={'type':2},competitions=[competition])
                    for tid in ids:schedules[tid,year].append(copy.deepcopy(event))
                    box=[]
                    for j,tid in enumerate(ids):
                        values={'fieldGoalsMade-fieldGoalsAttempted':'1-82','freeThrowsMade-freeThrowsAttempted':'1-22','offensiveRebounds':'19','totalTurnovers':'22','turnovers':'20','teamTurnovers':'2'}
                        box.append(dict(team={'id':str(tid)},statistics=[dict(name=k,displayValue=v) for k,v in values.items()]))
                    summaries[eid]=dict(header=dict(id=eid,season={'year':year,'type':2},competitions=[competition]),boxscore={'teams':box})
        def read(url):
            calls.append(url);q=parse_qs(urlparse(url).query)
            if '/schedule?' in url:
                tid=int(url.split('/teams/')[1].split('/')[0]);year=int(q['season'][0])
                return dict(season={'year':2027},events=schedules[tid,year]) # misleading root season on prior-season responses
            if '/summary?' in url:return summaries[q['event'][0]]
            raise AssertionError('Defense must use only the existing ESPN schedule/summary path: '+url)
        return teams,schedules,summaries,calls,read
    def calculate(self,source):
        teams,_,_,_,read=source
        with patch.object(utils,'get_teams',return_value=teams),patch.object(utils,'season_year',return_value=2027),patch.object(utils,'today',return_value=date(2026,10,23)),patch.object(utils,'read_json',side_effect=read):
            return defensive_ratings()
    def test_verified_estimate_components_and_explicit_total_turnovers(self):
        den={'fieldGoalsMade-fieldGoalsAttempted':'1-82','freeThrowsMade-freeThrowsAttempted':'1-22','offensiveRebounds':'19','totalTurnovers':'22'}
        self.assertAlmostEqual(estimated_possessions(den),93.8);self.assertAlmostEqual(100*84/estimated_possessions(den),89.55223880597)
        phx={'fieldGoalsMade-fieldGoalsAttempted':'1-101','freeThrowsMade-freeThrowsAttempted':'1-6','offensiveRebounds':'13','totalTurnovers':'13','turnovers':'11','teamTurnovers':'2'}
        self.assertAlmostEqual(estimated_possessions(phx),103.4);self.assertAlmostEqual(100*135/estimated_possessions(phx),130.56092843327)
        del phx['totalTurnovers'];self.assertAlmostEqual(estimated_possessions(phx),103.4)
        del phx['teamTurnovers']
        with self.assertRaises(ValueError):estimated_possessions(phx)
        phx['totalTurnovers']='0';self.assertAlmostEqual(estimated_possessions(phx),90.4)
        phx['totalTurnovers']=None
        with self.assertRaises(ValueError):estimated_possessions(phx)
    def test_full_30_team_cross_season_coverage_deduplicates_and_reuses_summaries(self):
        source=self.sources();teams,schedules,summaries,calls,_=source
        schedules[1,2027].append(copy.deepcopy(schedules[1,2027][0]))
        mixed={'fieldGoalsMade-fieldGoalsAttempted':'1-101','freeThrowsMade-freeThrowsAttempted':'1-6','offensiveRebounds':'13','totalTurnovers':'13'}
        summaries['2027-0-0']['boxscore']['teams'][1]['statistics']=[dict(name=k,displayValue=v) for k,v in mixed.items()]
        ratings=self.calculate(source);meta=utils.PROVENANCE['defense']
        self.assertEqual(len(ratings),30);self.assertEqual(meta['status'],'available');self.assertEqual(meta['eligible_teams'],30)
        self.assertTrue(all(r['Games']==10 and r['Complete'] and len(set(r['GameIds']))==10 for r in ratings.values()))
        self.assertEqual(ratings['LAL']['Seasons'],['2026-27','2025-26'])
        self.assertTrue(ratings['LAL']['SelectedGameIds'][0].startswith('2027-'))
        self.assertEqual(len([u for u in calls if '/summary?' in u]),150)
        self.assertAlmostEqual(ratings['LAL']['DefRtg'],100*900/(9*93.8+103.4))
        self.assertLess(ratings['LAL']['Rank'],ratings['BOS']['Rank'])
        check_defense_provenance(dict(defense_source='ESPN',defense=meta))
    def test_missing_selected_fields_stay_nine_of_ten_without_substituting_eleventh(self):
        source=self.sources();_,_,summaries,calls,_=source
        stats=summaries['2027-0-0']['boxscore']['teams'][1]['statistics']
        stats[:]=[s for s in stats if s['name'] not in ['totalTurnovers','teamTurnovers']]
        ratings=self.calculate(source);row=ratings['LAL'];meta=utils.PROVENANCE['defense']
        self.assertEqual(row['Games'],9);self.assertFalse(row['Complete']);self.assertIsNone(row['Rank']);self.assertIsNone(row['DefRtg'])
        self.assertEqual(row['MissingGames'][0]['id'],'2027-0-0');self.assertNotIn('2026-0-8',row['SelectedGameIds'])
        self.assertEqual(len([u for u in calls if '/summary?' in u]),150)
        self.assertEqual(meta['status'],'partial');self.assertEqual(meta['eligible_teams'],29)
        badge=matchup_badge('LAL',True,ratings);self.assertIn('9/10',badge);self.assertIn('#dedbd5',badge)
        check_defense_provenance(dict(defense_source='ESPN',defense=meta))
    def test_per_event_season_and_completed_regular_filter_ignore_misleading_root(self):
        source=self.sources(2);_,schedules,_,_,read=source
        for kind,done in [(1,True),(3,True),(2,False)]:
            extra=copy.deepcopy(schedules[1,2026][0]);extra['id']=f'ignore-{kind}-{done}';extra['seasonType']['type']=kind;extra['competitions'][0]['status']['type']['completed']=done
            schedules[1,2026].append(extra)
        with patch.object(utils,'read_json',side_effect=read),patch.object(utils,'today',return_value=date(2026,10,23)):
            self.assertEqual(len(completed_team_games(1,2026)),12)
            schedules[1,2026][0]['season']['year']=2027
            with self.assertRaises(ValueError):completed_team_games(1,2026)
    def test_source_outage_is_explicitly_unavailable_without_blocking_player_updates(self):
        with patch.object(utils,'get_teams',return_value=[dict(id=1,abbreviation='LAL')]),patch.object(utils,'season_year',return_value=2027),patch.object(utils,'read_json',side_effect=RuntimeError('ESPN unavailable')):
            self.assertEqual(utils.get_team_defensive_ratings(),{})
        meta=utils.PROVENANCE['defense'];self.assertEqual(meta['status'],'unavailable');self.assertIsNone(meta['source'])
        check_defense_provenance(dict(defense_source=None,defense=meta))
    def test_gate_rejects_unsupported_formula_false_coverage_or_wrong_rating(self):
        ratings=self.calculate(self.sources());meta=utils.PROVENANCE['defense']
        for field,value in [('formula','0.44'),('estimated',False),('eligible_teams',29)]:
            damaged=copy.deepcopy(meta);damaged[field]=value
            with self.assertRaises(ValueError):check_defense_provenance(dict(defense_source='ESPN',defense=damaged))
        damaged=copy.deepcopy(meta);damaged['teams']['LAL']['DefRtg']+=1
        with self.assertRaises(ValueError):check_defense_provenance(dict(defense_source='ESPN',defense=damaged))
    def test_full_generation_labels_estimates_and_never_publishes_fixture_as_real_data(self):
        from test_schedule_browser import build_fixture
        ratings=self.calculate(self.sources());meta=copy.deepcopy(utils.PROVENANCE['defense'])
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(utils,'read_json',side_effect=AssertionError('Fixture renderer must not fetch a source')),patch('builtins.print'):
                report=build_fixture(tmp,(ratings,meta))
            snapshot=Path(tmp)/'data_snapshot.json';saved=json.loads(snapshot.read_text());html=report.read_text()
            check_defense_provenance(saved);parser=PublicHTML();parser.feed(html)
            self.assertTrue(parser.matchups);self.assertTrue(all('近10場估算防守效率' in a['title'] for a in parser.matchups))
            self.assertIn('完整 30/30 隊',html)
            with self.assertRaisesRegex(ValueError,'Test fixture cannot be published'):check(report,snapshot)
    def test_season_resolver_dec_jan_and_new_year(self):
        for now,year in [(datetime(2026,12,31,tzinfo=timezone.utc),2027),(datetime(2027,1,1,tzinfo=timezone.utc),2027),(datetime(2027,10,1,tzinfo=timezone.utc),2028)]:
            class Clock(datetime):
                @classmethod
                def now(cls,tz=None):return now
            with patch.object(utils,'datetime',Clock),patch.object(utils,'read_json',return_value={'sports':[{'leagues':[{'season':{'year':year}}]}]}):self.assertEqual(utils.season_year(),year)

if __name__=='__main__':unittest.main()
