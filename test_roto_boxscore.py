import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from roto_boxscore import build_boxscore_data,load_source,EXPECTED_SHA,CSV_PATH
from roto_data import read_report

class BoxScore(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog=read_report('index.html');cls.snapshot=json.loads(Path('data_snapshot.json').read_text())
        cls.rows,cls.manifest=load_source();cls.data=build_boxscore_data(cls.catalog,cls.snapshot)
    def test_exact_licensed_bytes_and_complete_same_season_source(self):
        self.assertEqual(hashlib.sha256(CSV_PATH.read_bytes()).hexdigest(),EXPECTED_SHA)
        self.assertEqual(len(self.rows),582);self.assertEqual(len({r['id'] for r in self.rows}),582)
        self.assertTrue(all(0<r['gp']<=82 for r in self.rows))
        self.assertEqual(self.manifest['license'],'CC BY 4.0');self.assertFalse(self.manifest['independent_checks']['official_full_table_verified'])
        with tempfile.TemporaryDirectory() as tmp:
            bad=Path(tmp)/'bad.csv';bad.write_bytes(CSV_PATH.read_bytes()+b' ')
            with self.assertRaisesRegex(ValueError,'byte/hash mismatch'):load_source(bad)
    def test_unique_mapping_and_whole_source_not_mixed(self):
        s=self.data['mapping']['summary'];self.assertEqual((s['matched'],s['not_in_source'],s['ambiguous'],s['source_unmapped']),(481,129,0,101))
        self.assertEqual(s['old_comparable'],479);self.assertEqual(s['old_totals_disagreements'],0)
        byname={r['source_name']:r for r in self.rows}
        for p in self.data['players'].values():
            if p['status']=='matched':
                r=byname[p['source_name']];self.assertEqual(p['totals'],r['totals']);self.assertEqual(p['gp'],r['gp']);self.assertEqual(p['shots'],r['shots'])
            else:self.assertIsNone(p['gp']);self.assertTrue(all(v is None for v in p['totals'].values()))
    def test_suffix_alias_requires_exact_historical_fingerprint(self):
        record=next(m for m in self.data['mapping']['records'] if m['name']=='Bobby Portis')
        self.assertEqual(record['method'],'explicit_suffix_alias_plus_exact_GP_and_seven_totals')
        catalog=copy.deepcopy(self.catalog);catalog[record['id']]['periods']['ls']['tot']['PTS']['value']+=1
        changed=build_boxscore_data(catalog,self.snapshot);self.assertEqual(changed['players'][record['id']]['status'],'not_in_source')
    def test_ambiguous_names_are_unknown_without_blocking_other_applicable_rows(self):
        catalog=copy.deepcopy(self.catalog);p=copy.deepcopy(catalog['1966']);p['id']='99999999';catalog[p['id']]=p
        changed=build_boxscore_data(catalog,self.snapshot)
        self.assertEqual(changed['mapping']['summary']['ambiguous'],2)
        self.assertIsNone(changed['players']['1966']['gp']);self.assertIsNone(changed['players']['99999999']['gp'])
        self.assertTrue(changed['data_ready'])
    def test_conflicting_fga_not_selected_and_reference_is_fixed(self):
        p=self.data['players']['4432639'];self.assertIsNone(p['shots']['FGA']);self.assertEqual(p['shots']['FGM'],438)
        self.assertEqual(p['uncertainties']['FGA']['publisher_value'],975);self.assertEqual(p['uncertainties']['FGA']['cross_check_value'],974)
        self.assertEqual(self.data['reference']['size'],582);self.assertEqual(self.data['reference']['shooting_complete'],581)
        changed=build_boxscore_data({k:p for k,p in self.catalog.items() if k!='1966'},self.snapshot)
        self.assertEqual(changed['benchmark'],self.data['benchmark']);self.assertEqual(changed['reference']['id'],self.data['reference']['id'])
    def test_new_season_does_not_relabel_old_data(self):
        snapshot=copy.deepcopy(self.snapshot);snapshot['schedule']['season']='2027-28'
        with self.assertRaisesRegex(ValueError,'season does not match'):build_boxscore_data(self.catalog,snapshot)

if __name__=='__main__':unittest.main()
