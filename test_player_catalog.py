import unittest
import pandas as pd
from player_catalog import build_catalog, add_pr_ranks, METRICS, COUNTING, metric_pr

class Catalog(unittest.TestCase):
    def row(self):return dict(PLAYER_ID=123,PLAYER_NAME='Test <script>',TEAM_ABBREVIATION='LAL',GP_LS=7,PTS_LS=11/7,PTS_TOT_LS=11,PTS_PR_LS=43.2,PTS_TOT_PR_LS=68.9,FG_PCT_LS=.40041,**{'FG%_PR_LS':92.3})
    def test_exact_values_totals_rates_and_pr(self):
        p=build_catalog(pd.DataFrame([self.row()]))['123']
        self.assertEqual(p['name'],'Test <script>');self.assertEqual(p['periods']['ls']['gp'],7)
        self.assertEqual(p['periods']['ls']['avg']['PTS']['value'],11/7)
        self.assertEqual(p['periods']['ls']['tot']['PTS'],{'value':11.0,'pr':68.9})
        self.assertAlmostEqual(p['periods']['ls']['avg']['FG%']['value'],40.041)
        self.assertEqual(p['periods']['ls']['avg']['FG%'],p['periods']['ls']['tot']['FG%'])
    def test_missing_periods_not_zero_or_fake_pr(self):
        p=build_catalog(pd.DataFrame([self.row()]))['123']
        self.assertIsNone(p['periods']['season']['gp'])
        self.assertEqual(p['periods']['l7']['tot']['PTS'],dict(value=None,pr=None))
    def test_duplicate_id_and_nonfinite_rejected(self):
        with self.assertRaises(ValueError):build_catalog(pd.DataFrame([self.row(),self.row()]))
        row=self.row();row['PTS_LS']=float('inf')
        with self.assertRaises(ValueError):build_catalog(pd.DataFrame([row]))

class Rank(unittest.TestCase):
    def pool(self):
        rows=[]
        for pid,score in enumerate([100,80,80,60,50],1):
            r=dict(PLAYER_ID=pid)
            for m in METRICS:
                r[m+'_PR']=score if m=='PTS' else 0.0
                if m in COUNTING:r[m+'_TOT_PR']=score if m=='PTS' else 0.0
            rows.append(r)
        return pd.DataFrame(rows).astype({c:float for c in rows[0] if c!="PLAYER_ID"})
    def test_global_competition_ties_and_no_reindex(self):
        p=self.pool();original=p.copy();add_pr_ranks(p)
        self.assertEqual(p.PR_RANK.tolist(),[1,2,2,4,5])
        self.assertEqual(p.loc[p.PLAYER_ID.isin([2,3,4]),'PR_RANK'].tolist(),[2,2,4])
        pd.testing.assert_frame_equal(p[original.columns],original)
    def test_unrounded_sum_missing_pr_and_no_double_count(self):
        p=self.pool();p.loc[1,'PTS_PR']=80.00001;p.loc[4,'FT%_PR']=float('nan')
        p['SOME_TOTAL_PR']=10000;add_pr_ranks(p)
        self.assertEqual(p.PR_RANK.iloc[1],2);self.assertEqual(p.PR_RANK.iloc[2],3)
        self.assertIsNone(None if pd.isna(p.PR_RANK.iloc[4]) else p.PR_RANK.iloc[4])
        self.assertEqual(p.PR_SUM.iloc[0],100)
    def test_tot_uses_existing_tot_pr_and_empty_population(self):
        p=self.pool();p.loc[3,'PTS_TOT_PR']=200;add_pr_ranks(p)
        self.assertEqual(p.PR_RANK_TOT.iloc[3],1);self.assertEqual(p.PR_RANK.iloc[3],4)
        self.assertEqual(len(add_pr_ranks(p.iloc[:0].copy())),0)
        p.loc[0,'PTS_PR']=float('inf')
        with self.assertRaises(ValueError):add_pr_ranks(p)
    def test_minutes_changes_and_missing_minutes_do_not_affect_rank(self):
        baseline=add_pr_ranks(self.pool())
        changed=self.pool();changed['MIN_PR']=[0,100,999,55,float('nan')]
        add_pr_ranks(changed)
        for key in ['PR_SUM','PR_SUM_TOT','PR_RANK','PR_RANK_TOT']:
            pd.testing.assert_series_equal(baseline[key],changed[key])
        missing=self.pool().drop(columns='MIN_PR');add_pr_ranks(missing)
        self.assertEqual(missing.PR_RANK.tolist(),[1,2,2,4,5])
        self.assertEqual(missing.PR_RANK_TOT.tolist(),[1,2,2,4,5])
    def test_nine_included_prs_are_required_and_sum_without_minutes(self):
        p=self.pool()
        for m in METRICS:
            p[m+'_PR']=10.0 if m!='MIN' else 100.0
            if m in COUNTING:p[m+'_TOT_PR']=10.0
        p.loc[0,'PTS_PR']=11.0;p.loc[0,'PTS_TOT_PR']=11.0
        p.loc[4,'FT%_PR']=float('nan');add_pr_ranks(p)
        self.assertEqual(p.PR_SUM.iloc[0],91);self.assertEqual(p.PR_SUM_TOT.iloc[0],91)
        self.assertEqual(p.PR_RANK.tolist()[:4],[1,2,2,2])
        self.assertTrue(pd.isna(p.PR_RANK.iloc[4]));self.assertTrue(pd.isna(p.PR_RANK_TOT.iloc[4]))

class TurnoverPR(unittest.TestCase):
    def test_low_high_ties_zero_and_null_single_reversal(self):
        values=pd.Series([0.0,1.0,1.0,4.0,float('nan')])
        pr=metric_pr(values,'TO')
        self.assertEqual(pr.tolist()[:4],[100.0,62.5,62.5,25.0])
        self.assertTrue(pd.isna(pr.iloc[4]))
        self.assertEqual(metric_pr(values,'PTS').tolist()[:4],[25.0,62.5,62.5,100.0])
    def test_rank_includes_to_once_and_excludes_minutes(self):
        pool=Rank().pool()
        for m in METRICS:
            pool[m+'_PR']=10.0
            if m in COUNTING:pool[m+'_TOT_PR']=10.0
        pool['MIN_PR']=1000.0;pool.loc[0,'TO_PR']=100.0;pool.loc[0,'TO_TOT_PR']=100.0
        pool.loc[4,'TO_PR']=float('nan');pool.loc[4,'TO_TOT_PR']=float('nan');add_pr_ranks(pool)
        self.assertEqual(pool.PR_SUM.iloc[0],180);self.assertEqual(pool.PR_SUM_TOT.iloc[0],180)
        self.assertEqual(pool.PR_RANK.iloc[0],1);self.assertTrue(pd.isna(pool.PR_RANK.iloc[4]))

if __name__=='__main__':unittest.main()
