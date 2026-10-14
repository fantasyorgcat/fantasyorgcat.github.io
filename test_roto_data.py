import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import pandas as pd
import utils
from player_catalog import build_catalog
from roto_data import build_data, records_from_catalog, source_reference, write_data

class RotoData(unittest.TestCase):
    def catalog(self):
        rows=[]
        for i,gp in [(1,10),(2,20)]:
            r=dict(PLAYER_ID=i,PLAYER_NAME='Real <name>',TEAM_ABBREVIATION='LAL',GP_LS=gp,MIN_LS=20,FGM_LS=gp*3,FGA_LS=gp*6,FTM_LS=gp,FTA_LS=gp*2)
            for key in ['PTS','REB','AST','3PM','STL','BLK','TO']:
                r[key+'_TOT_LS']=gp*(i+1);r[key+'_LS']=i+1
            rows.append(r)
        return build_catalog(pd.DataFrame(rows))
    def snapshot(self):return dict(period_populations={'LastSeason':2},players_2026={'season':'2025-26','source_period_start':'2025-10-21','source_period_end':'2026-04-13'},schedule={'season':'2026-27'},generated_at='2026-10-10 17:34 UTC',stats_source='ESPN')
    def test_complete_same_season_and_immutable_benchmark(self):
        c=self.catalog();original=copy.deepcopy(c);d=build_data(c,self.snapshot());self.assertTrue(d['data_ready']);self.assertEqual(d['reference']['shooting_complete'],2);self.assertEqual(d['season'],'2025-26');self.assertEqual(d['benchmark']['perGame']['PTS']['mean'],2.5);self.assertEqual(d['players']['1']['shots']['FGA'],60);self.assertEqual(c,original)
    def test_missing_denominators_not_inferred_from_percent(self):
        c=self.catalog();c['1']['periods']['ls']['shooting']['FGA']=None;c['1']['periods']['ls']['avg']['FG%']['value']=50
        d=build_data(c,self.snapshot());self.assertFalse(d['data_ready']);self.assertIsNone(d['players']['1']['shots']['FGA']);self.assertEqual(d['reference']['shooting_complete'],1)
    def test_reference_population_is_not_silently_changed(self):
        snapshot=self.snapshot();snapshot['period_populations']['LastSeason']=3;d=build_data(self.catalog(),snapshot);self.assertFalse(d['data_ready']);self.assertEqual(d['reference']['expected'],3)
    def test_integer_shots_validation_and_no_active_content(self):
        c=self.catalog();c['1']['periods']['ls']['shooting']['FGM']=100
        with self.assertRaises(ValueError):build_data(c,self.snapshot())
        c=self.catalog();c['1']['periods']['ls']['shooting']['FGM']=1.5
        with self.assertRaises(ValueError):build_data(c,self.snapshot())
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'data.js';write_data(build_data(self.catalog(),self.snapshot()),path);self.assertNotIn('<name>',path.read_text());self.assertIn('\\u003c',path.read_text())
    def test_raw_source_reference_shots_and_zero_attempts(self):
        frame=pd.DataFrame([dict(PLAYER_ID=1,GP=1,FGM=0,FGA=0,FTM=0,FTA=0,PTS_TOTAL=0,REB_TOTAL=0,AST_TOTAL=0,FG3M_TOTAL=0,STL_TOTAL=0,BLK_TOTAL=0,TO_TOTAL=0)])
        r=source_reference(frame);self.assertEqual(r[0]['shots']['FGA'],0);self.assertEqual(r[0]['totals']['3PM'],0)
    def test_bulk_preserves_optional_shooting_totals_and_missing_pairs(self):
        names=['gamesPlayed','avgMinutes','avgPoints','avgRebounds','avgAssists','avgSteals','avgBlocks','fieldGoalPct','freeThrowPct','avgThreePointFieldGoalsMade','avgTurnovers','points','rebounds','assists','steals','blocks','threePointFieldGoalsMade','turnovers','fieldGoalsMade','fieldGoalsAttempted','freeThrowsMade','freeThrowsAttempted']
        values=[2,20,10,2,1,1,0,50,80,1,1,20,4,2,2,0,2,2,6,12,4,5]
        d={'requestedSeason':{'year':2026,'type':{'type':2,'startDate':'s','endDate':'e'}},'pagination':{'pages':1,'count':1},'categories':[{'name':'stats','names':names}],
           'athletes':[{'athlete':{'id':'1','displayName':'Test','teams':[{'abbreviation':'LAL'}]},'categories':[{'name':'stats','values':values}]}]}
        with patch.object(utils,'read_json',return_value=d),patch.object(utils,'get_teams',return_value=[{'id':1,'abbreviation':'LAL'}]),patch.object(utils,'abbreviation',return_value='LAL'):
            row=utils.league_stats(2026).iloc[0];self.assertEqual(row.FGM,6);self.assertEqual(row.FGA,12);self.assertEqual(row.FTM,4);self.assertEqual(row.FTA,5)
            names.pop();values.pop();row=utils.league_stats(2026).iloc[0];self.assertTrue(pd.isna(row.FTA))

    def test_release_gate_checks_real_columns_not_only_ready_flag(self):
        import os,shutil
        from security_gate import check_roto,ROTO_FILES
        root=Path.cwd();catalog=self.catalog()
        catalog['2']['periods']['ls']['shooting'].update(FGM=10,FTM=5)
        data=build_data(catalog,self.snapshot());self.assertTrue(data['data_ready'])
        with tempfile.TemporaryDirectory() as tmp:
            target=Path(tmp)
            for name in ROTO_FILES:
                if name!='roto_data.js':shutil.copyfile(root/name,target/name)
            shutil.copytree(root/'assets',target/'assets')
            (target/'data_snapshot.json').write_text(json.dumps(self.snapshot()))
            write_data(data,target/'roto_data.js')
            try:
                os.chdir(target);check_roto()
                changed=copy.deepcopy(data);changed['benchmark']['perGame']['PTS']['mean']+=1;write_data(changed)
                with self.assertRaisesRegex(ValueError,'reference cannot be reproduced'):check_roto()
                data['players']['1']['shots']['FGA']=None;write_data(data)
                with self.assertRaisesRegex(ValueError,'missing player shooting'):check_roto()
                data['data_ready']=False;write_data(data)
                with self.assertRaisesRegex(ValueError,'reference and shooting denominators are incomplete'):check_roto()
            finally:os.chdir(root)

    def test_missing_recent_attempts_remain_unknown(self):
        from datetime import date
        player=dict(PLAYER_ID=1,PLAYER_NAME='Test',TEAM_ID=1,TEAM_ABBREVIATION='LAL',GP=1)
        logs=[dict(date=date(2026,10,10),MIN=20,PTS=2,REB=0,AST=0,STL=0,BLK=0,FG3M=None,FGM=1,FGA=None,FTM=None,FTA=None,TO=0)]
        with patch.object(utils,'today',return_value=date(2026,10,11)),patch.object(utils,'player_gamelog',return_value=logs):l7,_=utils.recent_stats(pd.DataFrame([player]),2027)
        self.assertEqual(l7.iloc[0].FGM,1);self.assertTrue(pd.isna(l7.iloc[0].FGA));self.assertTrue(pd.isna(l7.iloc[0].FG_PCT));self.assertTrue(pd.isna(l7.iloc[0].FG3M_TOTAL))

    def test_recent_keeps_shooting_totals_and_zero_is_unknown_rate(self):
        from datetime import date
        player=dict(PLAYER_ID=1,PLAYER_NAME='Test',TEAM_ID=1,TEAM_ABBREVIATION='LAL',GP=1)
        logs=[dict(date=date(2026,10,10),MIN=20,PTS=0,REB=0,AST=0,STL=0,BLK=0,FG3M=0,FGM=0,FGA=0,FTM=0,FTA=0,TO=0)]
        with patch.object(utils,'today',return_value=date(2026,10,11)),patch.object(utils,'player_gamelog',return_value=logs):l7,_=utils.recent_stats(pd.DataFrame([player]),2027)
        self.assertEqual(l7.iloc[0].FGA,0);self.assertTrue(pd.isna(l7.iloc[0].FG_PCT));self.assertTrue(pd.isna(l7.iloc[0].FT_PCT))

if __name__=='__main__':unittest.main()
