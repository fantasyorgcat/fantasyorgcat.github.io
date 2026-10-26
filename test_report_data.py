"""Public transport is lossless, bounded, and executable only as a JSON assignment."""
import copy
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from report_data import pack_catalog, unpack_catalog, pack_events, unpack_events, read_script, write_script
from roto_data import read_report


class ReportData(unittest.TestCase):
    def test_full_catalog_roundtrip_keeps_exact_prs_missingness_and_totals(self):
        catalog=read_report('index.html');before=copy.deepcopy(catalog)
        packed=pack_catalog(catalog)
        self.assertEqual(unpack_catalog(packed),catalog)
        self.assertEqual(catalog,before)
        self.assertLess(len(json.dumps(packed)),len(json.dumps(catalog))*.5)
        self.assertLess(len(packed['s']),4*len(catalog))

    def test_python_and_browser_codec_agree_exactly(self):
        packed=read_script('report_data.js','REPORT_DATA')['catalog']
        source="const fs=require('fs'),c=require('./data_codec.js');const d=JSON.parse(fs.readFileSync(0,'utf8'));process.stdout.write(JSON.stringify(c.unpackCatalog(d)));"
        decoded=subprocess.check_output(['node','-e',source],input=json.dumps(packed),text=True,encoding='utf-8')
        self.assertEqual(json.loads(decoded),unpack_catalog(packed))

    def test_json_transport_escapes_active_text_and_rejects_executable_suffix(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'data.js';payload={'name':'</script><img src=x onerror=alert(1)>','unknown':None,'zero':0,'precise':1/7}
            write_script(path,'TEST',payload)
            self.assertNotIn('<',path.read_text(encoding='utf-8'))
            self.assertEqual(read_script(path,'TEST'),payload)
            path.write_text(path.read_text(encoding='utf-8')+'alert(1);',encoding='utf-8')
            with self.assertRaises(ValueError):read_script(path,'TEST')

    def test_schedule_pool_is_exact_in_python_and_javascript(self):
        packed=read_script('report_data.js','REPORT_DATA')['events']
        events=unpack_events(packed)
        self.assertEqual(unpack_events(pack_events(events)),events)
        source="const fs=require('fs'),c=require('./data_codec.js');process.stdout.write(JSON.stringify(c.unpackEvents(JSON.parse(fs.readFileSync(0,'utf8')))));"
        decoded=subprocess.check_output(['node','-e',source],input=json.dumps(packed),text=True,encoding='utf-8')
        self.assertEqual(json.loads(decoded),events)
        self.assertLess(len(json.dumps(pack_events(events))),len(json.dumps(events))*.5)

    def test_homepage_size_and_empty_player_bodies(self):
        import re
        html=Path('index.html').read_text(encoding='utf-8')
        self.assertLess(len(html.encode('utf-8')),1_000_000)
        bodies=re.findall(r'<table id="playerTable[^\"]+".*?<tbody>(.*?)</tbody>',html,re.S)
        self.assertEqual(len(bodies),4)
        self.assertTrue(all(not body.strip() for body in bodies))


if __name__=='__main__':unittest.main()
