import unittest
from datetime import date,timedelta
from unittest.mock import patch
import pandas as pd
import utils
from generate_report import season_schedule_payload

class Schedule(unittest.TestCase):
    def setUp(self):
        utils.get_season_schedule.cache_clear();utils.PROVENANCE.clear()
    def tearDown(self):utils.get_season_schedule.cache_clear()
    def frame(self,days):
        return pd.DataFrame([dict(TEAM_ID=1,TEAM_ABBREVIATION='LAL',GAME_DATE=d,MATCHUP='LAL vs. BOS') for d in days],columns=['TEAM_ID','TEAM_ABBREVIATION','GAME_DATE','MATCHUP'])
    def test_opening_partial_week(self):
        weeks=utils.season_weeks(self.frame([date(2026,10,20),date(2026,10,27)]))
        self.assertEqual((weeks[0]['number'],weeks[0]['start'],weeks[0]['end']),(1,date(2026,10,19),date(2026,10,25)))
        self.assertEqual(weeks[1]['number'],2)
    def test_cross_year_continuous_and_new_season_resets(self):
        weeks=utils.season_weeks(self.frame([date(2026,10,20),date(2027,1,4)]))
        self.assertEqual(weeks[-1]['number'],12)
        self.assertEqual(weeks[-2]['start'],date(2026,12,28))
        newer=utils.season_weeks(self.frame([date(2027,10,21),date(2028,1,3)]))
        self.assertEqual(newer[0]['number'],1)
        self.assertEqual(newer[0]['start'],date(2027,10,18))
    def test_empty_season_and_empty_week(self):
        self.assertEqual(utils.season_weeks(self.frame([])),[])
        frame=self.frame([date(2026,10,20),date(2026,11,3)])
        payload=season_schedule_payload(frame,utils.season_weeks(frame),{})
        self.assertEqual(payload[1]['events'],0);self.assertEqual(payload[1]['teams'],{})
        self.assertEqual(len(payload[1]['headers']),7)
        self.assertEqual(payload[0]['teams']['LAL']['days'][0],'')
        self.assertIn('BOS',payload[0]['teams']['LAL']['days'][1])
    def event(self,eid,day,season=2027,kind=2):
        return dict(id=eid,date=day,season={'year':season},seasonType={'type':kind},competitions=[{'competitors':[
            dict(id='1',homeAway='home',team={'id':'1','abbreviation':'LAL'}),
            dict(id='2',homeAway='away',team={'id':'2','abbreviation':'BOS'})]}])
    def source(self,events):return dict(season={'year':2027},events=events)
    def patches(self,reader):
        return (patch.object(utils,'season_year',return_value=2027),patch.object(utils,'get_teams',return_value=[{'id':1},{'id':2}]),patch.object(utils,'abbreviation',side_effect=lambda x:x),patch.object(utils,'read_json',side_effect=reader))
    def test_full_source_eastern_dates_dedup_and_cached_windows(self):
        events=[self.event('1','2026-10-21T01:00Z'),self.event('2','2027-04-12T00:30Z'),self.event('pre','2026-10-01T01:00Z',kind=1),self.event('post','2027-04-15T01:00Z',kind=3)]
        a,b,c,d=self.patches(lambda url:self.source(events))
        with a,b,c,d as reader:
            full=utils.get_season_schedule()
            self.assertEqual(len(full),4)
            self.assertEqual(min(full.GAME_DATE),date(2026,10,20))
            self.assertEqual(max(full.GAME_DATE),date(2027,4,11))
            opening=utils.get_schedule(date(2026,10,19),date(2026,10,25))
            closing=utils.get_schedule(date(2027,4,5),date(2027,4,11))
            self.assertEqual(len(opening),2);self.assertEqual(len(closing),2)
            self.assertEqual(reader.call_count,2)
            self.assertEqual(utils.PROVENANCE['schedule']['published_events'],2)
    def test_valid_empty_source_is_not_failure(self):
        a,b,c,d=self.patches(lambda url:self.source([]))
        with a,b,c,d:
            self.assertTrue(utils.get_schedule(date(2026,10,1),date(2026,10,4)).empty)
            self.assertIsNone(utils.PROVENANCE['schedule']['first_game'])
    def test_invalid_source_and_conflicting_dates_abort(self):
        for source in [dict(season={'year':2026},events=[]),dict(season={'year':2027}),self.source([self.event('1','2026-10-21T01:00Z'),self.event('1','2026-10-22T01:00Z')])]:
            utils.get_season_schedule.cache_clear()
            a,b,c,d=self.patches(lambda url:source)
            with a,b,c,d,self.assertRaises((ValueError,KeyError)):utils.get_season_schedule()
    def test_payload_keeps_cross_season_defense_badge(self):
        ratings={'BOS':dict(Rank=3,Population=30,DefRtg=108.5,Games=10,Start='2026-03-24',End='2026-04-12')}
        frame=self.frame([date(2026,10,20)])
        badge=season_schedule_payload(frame,utils.season_weeks(frame),ratings)[0]['teams']['LAL']['days'][1]
        self.assertIn('可跨季',badge);self.assertIn('10/10',badge);self.assertIn('108.5',badge)

if __name__=='__main__':unittest.main()
