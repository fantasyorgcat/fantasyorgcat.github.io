import unittest
from datetime import date,timedelta
from unittest.mock import patch
import pandas as pd
import utils
from fantasy_periods import build_platform_periods, validate_calendar, validate_espn_calendar, YAHOO_DATES, ESPN_DATES
import copy, json
from generate_report import season_schedule_payload, schedule_event_payload, scheduled_matchup

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

    def normalized(self,event):
        a,b,c,d=self.patches(lambda url:self.source([event]))
        with a,b,c,d:return utils.get_season_schedule().copy()

    def test_event_id_utc_status_and_two_display_dates(self):
        event=self.event('midnight','2027-01-01T02:30:00Z')
        event['competitions'][0]['status']={'type':{'name':'STATUS_SCHEDULED','state':'pre','completed':False}}
        frame=self.normalized(event);row=frame.iloc[0]
        self.assertEqual(row.EVENT_ID,'midnight');self.assertEqual(row.TIPOFF_UTC,'2027-01-01T02:30:00Z')
        self.assertEqual(row.GAME_DATE,date(2026,12,31));self.assertEqual(row.STATUS,'scheduled')
        payload=schedule_event_payload(frame,{})
        self.assertEqual(len(payload),1);self.assertEqual(payload[0]['date_et'],'2026-12-31')
        self.assertEqual(payload[0]['season_type'],2)
        self.assertIn('美東 12/31 21:30',payload[0]['home_html']);self.assertIn('台北 01/01 10:30',payload[0]['home_html'])

    def test_dst_changes_clock_without_changing_eastern_date(self):
        for stamp,et in [('2026-10-31T23:30:00Z','10/31 19:30'),('2026-11-02T00:30:00Z','11/01 19:30')]:
            utils.get_season_schedule.cache_clear();frame=self.normalized(self.event('dst',stamp))
            self.assertIn('美東 '+et,scheduled_matchup(frame.iloc[0],{}))

    def test_undated_and_time_tbd_do_not_invent_tipoff(self):
        event=self.event('tbd',None)
        frame=self.normalized(event)
        self.assertEqual(utils.season_weeks(frame),[]);self.assertIsNone(frame.iloc[0].TIPOFF_UTC)
        self.assertEqual(utils.PROVENANCE['schedule']['undated_events'],1)
        self.assertTrue(utils.get_schedule(date(2026,10,1),date(2027,4,11)).empty)
        utils.get_season_schedule.cache_clear()
        event=self.event('tbd-clock','2026-10-21T00:00Z');event['competitions'][0]['timeValid']=False
        row=self.normalized(event).iloc[0];self.assertIsNone(row.TIPOFF_UTC)
        self.assertIn('開賽時間待定',scheduled_matchup(row,{}))

    def test_postponed_cancelled_final_states_and_scheduled_count(self):
        for name,state,completed,expected,count in [('STATUS_POSTPONED','pre',False,'postponed',0),('STATUS_CANCELED','pre',False,'cancelled',0),('STATUS_FINAL','post',True,'final',1)]:
            utils.get_season_schedule.cache_clear();event=self.event(name,'2026-10-21T01:00Z')
            event['competitions'][0]['status']={'type':dict(name=name,state=state,completed=completed)}
            frame=self.normalized(event);self.assertEqual(frame.iloc[0].STATUS,expected)
            utils.get_schedule(date(2026,10,19),date(2026,10,25))
            self.assertEqual(utils.PROVENANCE['schedule']['events_in_window'],count)
            payload=season_schedule_payload(frame,utils.season_weeks(frame),{})
            self.assertEqual(payload[0]['teams']['LAL']['games'],count)

    def test_naive_timestamp_rejected(self):
        with self.assertRaisesRegex(ValueError,'timezone'):self.normalized(self.event('bad','2026-10-20T19:00:00'))

    def test_platform_calendars_use_verified_distinct_boundaries(self):
        weeks=utils.season_weeks(self.frame([date(2026,10,20),date(2027,4,11)]))
        groups=build_platform_periods('2026-27',weeks,[])
        yahoo,nba=groups['YAHOO']['periods'],groups['NBA']['periods']
        self.assertEqual((len(yahoo),len(nba)),(23,25))
        self.assertEqual((yahoo[0]['start'],nba[0]['start']),('2026-10-20','2026-10-19'))
        self.assertEqual((yahoo[6]['start'],yahoo[6]['end']),('2026-11-30','2026-12-13'))
        self.assertEqual((yahoo[16]['start'],yahoo[16]['end']),('2027-02-15','2027-02-28'))
        self.assertEqual((yahoo[9]['start'],yahoo[9]['end']),('2026-12-28','2027-01-03'))
        self.assertEqual([p['number'] for p in yahoo if p['default_playoff']],[20,21,22])
        self.assertTrue(groups['YAHOO']['official_platform_mapping'])
        self.assertFalse(groups['NBA']['official_platform_mapping'])
        self.assertTrue(groups['ESPN']['available'])
        self.assertTrue(groups['ESPN']['official_platform_mapping'])
        self.assertEqual(len(groups['ESPN']['periods']),24)

    def test_future_season_never_reuses_verified_platform_dates(self):
        weeks=utils.season_weeks(self.frame([date(2027,10,20)]))
        groups=build_platform_periods('2027-28',weeks,[])
        self.assertFalse(groups['YAHOO']['available'])
        self.assertEqual(groups['YAHOO']['periods'],[])
        self.assertFalse(groups['ESPN']['available'])
        self.assertEqual(groups['ESPN']['periods'],[])
        self.assertTrue(groups['NBA']['available'])
        self.assertEqual(groups['NBA']['periods'][0]['number'],1)

    def test_calendar_rejects_gap_overlap_length_and_number_errors(self):
        calendar=json.loads(YAHOO_DATES.read_text())
        for key,value in [('start','2026-10-25'),('start','2026-10-27'),('end','2026-12-01'),('number',7)]:
            invalid=copy.deepcopy(calendar);invalid['periods'][1][key]=value
            with self.assertRaises(ValueError):validate_calendar(invalid)

    def test_espn_weekly_boundaries_and_source_scope(self):
        group=build_platform_periods('2026-27',[],[])['ESPN'];weeks=group['periods']
        self.assertEqual(group['source_season'],2027)
        self.assertEqual(group['period_type'],dict(id=2,description='Weekly'))
        self.assertIn('?view=chui_default',group['source_url'])
        self.assertIn('league matchup',group['scope'])
        self.assertEqual((weeks[0]['start'],weeks[0]['end']),('2026-10-20','2026-10-25'))
        self.assertEqual((weeks[6]['start'],weeks[6]['end']),('2026-11-30','2026-12-06'))
        self.assertEqual((weeks[7]['start'],weeks[7]['end']),('2026-12-07','2026-12-13'))
        self.assertEqual((weeks[17]['start'],weeks[17]['end']),('2027-02-15','2027-02-28'))
        self.assertEqual((weeks[-1]['number'],weeks[-1]['start'],weeks[-1]['end'],weeks[-1]['scoring_period_end']),(24,'2027-04-05','2027-04-11',174))
        self.assertTrue(all('default_playoff' not in w for w in weeks))

    def test_espn_calendar_rejects_wrong_source_and_postseason(self):
        calendar=json.loads(ESPN_DATES.read_text())
        invalid=copy.deepcopy(calendar);invalid['source_season']=2026
        with self.assertRaisesRegex(ValueError,'source season'):validate_espn_calendar(invalid)
        invalid=copy.deepcopy(calendar);invalid['period_type']['id']=1
        with self.assertRaisesRegex(ValueError,'period type'):validate_espn_calendar(invalid)
        invalid=copy.deepcopy(calendar);invalid['periods'][-1].update(end='2027-04-12',scoring_period_end=175)
        with self.assertRaisesRegex(ValueError,'non-regular'):validate_espn_calendar(invalid)
        invalid=copy.deepcopy(calendar);invalid['periods'][-1]['scoring_period_start']=167
        with self.assertRaisesRegex(ValueError,'do not match'):validate_espn_calendar(invalid)

    def test_unpublished_nba_dates_do_not_invent_games(self):
        groups=build_platform_periods('2026-27',[],[])
        self.assertFalse(groups['NBA']['available'])
        self.assertEqual(groups['NBA']['periods'],[])
        self.assertEqual(len(groups['YAHOO']['periods']),23)

if __name__=='__main__':unittest.main()
