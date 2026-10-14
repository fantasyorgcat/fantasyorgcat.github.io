import copy
import json
from pathlib import Path
import unittest
from player_catalog import build_catalog
import pandas as pd
from roto_data import read_report,records_from_catalog
from roto_package import build_package,live_period

class RotoPackage(unittest.TestCase):
    def sample(self,year='2026-27'):
        rows=[]
        for pid,gp in [(1,2),(2,3)]:
            row=dict(PLAYER_ID=pid,PLAYER_NAME='Test '+str(pid),TEAM_ABBREVIATION='LAL')
            for suffix in ['', '_LS']:
                row.update({'GP'+suffix:gp,'MIN'+suffix:20,'FGM'+suffix:gp*2,'FGA'+suffix:gp*5,'FTM'+suffix:gp,'FTA'+suffix:gp*2})
                for k in ['PTS','REB','AST','3PM','STL','BLK','TO']:row[k+'_TOT'+suffix]=gp*pid;row[k+suffix]=pid
            rows.append(row)
        catalog=build_catalog(pd.DataFrame(rows));previous=f'{int(year[:4])-1}-{year[2:4]}'
        snapshot=dict(schedule={'season':year},generated_at='TEST ONLY',stats_source='ESPN',period_populations={'Season':2,'LastSeason':2},roto_references={})
        for season,period,pop in [(year,'season','Season'),(previous,'ls','LastSeason')]:
            snapshot['players_'+str(int(season[:4])+1)]=dict(season=season,season_type='Regular Season',source_period_start='start',source_period_end='end')
            snapshot['roto_references'][pop]=[dict(id=p['id'],gp=p['gp'],totals=p['totals'],shots=p['shots']) for p in records_from_catalog(catalog,period).values()]
        return catalog,snapshot
    def test_checked_in_preseason_has_no_fake_current_data(self):
        d=build_package(read_report('index.html'),json.loads(Path('data_snapshot.json').read_text()))
        self.assertEqual(d['default_period'],'ls');self.assertEqual(d['season'],'2025-26');self.assertEqual(d['extra_periods']['season']['season'],'2026-27')
        self.assertFalse(d['extra_periods']['season']['stats_available']);self.assertEqual(d['catalog'],read_report('index.html'))
    def test_new_regular_season_automatically_becomes_default(self):
        c,s=self.sample();d=build_package(c,s)
        self.assertEqual(d['default_period'],'season');current=d['extra_periods']['season']
        self.assertTrue(current['data_ready']);self.assertEqual(current['season'],'2026-27');self.assertEqual(current['players']['1']['totals']['PTS'],2)
        self.assertEqual(current['players']['1']['shots']['FGA'],10)
    def test_full_reference_can_include_outside_current_catalog(self):
        c,s=self.sample();extra=copy.deepcopy(s['roto_references']['Season'][0]);extra['id']='999';extra['totals']['PTS']=50
        s['roto_references']['Season'].append(extra);s['period_populations']['Season']=3
        d=live_period(c,s,'season','2026-27');self.assertEqual(d['reference']['size'],3);self.assertTrue(d['data_ready'])
        self.assertEqual(d['benchmark']['totals']['PTS']['mean'],(2+6+50)/3)
        del s['roto_references']['Season'];d=live_period(c,s,'season','2026-27');self.assertFalse(d['data_ready']);self.assertIsNone(d['benchmark']['totals']['PTS']['mean'])
    def test_rollover_retains_archive_label_and_uses_new_source(self):
        c,s=self.sample('2027-28');d=build_package(c,s)
        self.assertEqual(d['season'],'2025-26');self.assertEqual(d['period_key'],'archive')
        self.assertEqual(d['default_period'],'season');self.assertEqual(d['extra_periods']['season']['season'],'2027-28');self.assertEqual(d['extra_periods']['ls']['season'],'2026-27')
        s['period_populations']['Season']=0;s['roto_references']['Season']=[]
        for p in c.values():p['periods']['season']['gp']=None
        d=build_package(c,s);self.assertEqual(d['default_period'],'ls')
    def test_mismatched_source_and_reference_are_rejected(self):
        c,s=self.sample();s['players_2027']['season']='2025-26'
        with self.assertRaisesRegex(ValueError,'season/type'):live_period(c,s,'season','2026-27')
        c,s=self.sample();s['roto_references']['Season'][0]['shots']['FGA']+=1
        with self.assertRaisesRegex(ValueError,'reference/catalog'):live_period(c,s,'season','2026-27')
    def test_missing_attempts_never_inferred_from_percentage(self):
        c,s=self.sample();c['1']['periods']['season']['shooting']['FGA']=None;s['roto_references']['Season'][0]['shots']['FGA']=None
        d=live_period(c,s,'season','2026-27');self.assertFalse(d['data_ready']);self.assertIsNone(d['players']['1']['shots']['FGA'])

if __name__=='__main__':unittest.main()
