import unittest
import pandas as pd
from player_catalog import build_catalog

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

if __name__=='__main__':unittest.main()
