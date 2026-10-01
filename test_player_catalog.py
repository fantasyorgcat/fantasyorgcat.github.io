import unittest
import pandas as pd
from player_catalog import build_catalog, add_pr_ranks, METRICS, COUNTING

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
        p.loc[0,'MIN_PR']=float('inf')
        with self.assertRaises(ValueError):add_pr_ranks(p)

if __name__=='__main__':unittest.main()
