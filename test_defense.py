import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from datetime import datetime,timezone
import utils
from generate_report import matchup_badge
from security_gate import PublicHTML,check,check_defense_provenance

class Defense(unittest.TestCase):
    def setUp(self):utils.PROVENANCE.clear()
    def unavailable(self):
        utils.get_team_defensive_ratings()
        return dict(defense_source=None,defense=copy.deepcopy(utils.PROVENANCE['defense']))
    def test_defense_is_explicitly_unavailable_without_network_or_previous_values(self):
        utils.PROVENANCE['defense']=dict(source='PBP Stats',teams={'LAL':{'DefRtg':100}},last_game='2026-10-20',eligible_teams=1)
        with patch.object(utils,'read_json',side_effect=AssertionError('Optional defense must not fetch a source')):
            self.assertEqual(utils.get_team_defensive_ratings(),{})
        meta=utils.PROVENANCE['defense']
        self.assertEqual(meta['status'],'unavailable');self.assertIsNone(meta['source']);self.assertTrue(meta['reason'])
        self.assertEqual(meta['teams'],{});self.assertEqual(meta['eligible_teams'],0);self.assertIsNone(meta['last_game'])
        badge=matchup_badge('LAL',True,{})
        self.assertIn('#dedbd5',badge);self.assertIn('防守資料暫缺',badge);self.assertNotIn('排名',badge)
    def test_gate_rejects_stale_values_or_false_source_in_unavailable_defense(self):
        meta=self.unavailable();check_defense_provenance(meta)
        for field,value in [('source','ESPN'),('teams',{'LAL':{'DefRtg':100}}),('eligible_teams',1),('last_game','2026-10-20'),('reason','')]:
            with self.subTest(field=field):
                damaged=copy.deepcopy(meta);damaged['defense'][field]=value
                with self.assertRaises(ValueError):check_defense_provenance(damaged)
        meta['defense_source']='PBP Stats'
        with self.assertRaises(ValueError):check_defense_provenance(meta)
    def test_legacy_snapshot_retains_only_its_original_source_attribution(self):
        meta=dict(defense_source='PBP Stats',defense={'source':'PBP Stats'})
        check_defense_provenance(meta)
        meta['defense_source']=None
        with self.assertRaises(ValueError):check_defense_provenance(meta)
    def test_full_generation_finishes_with_unavailable_defense_and_fixture_still_cannot_publish(self):
        from test_schedule_browser import build_fixture
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(utils,'read_json',side_effect=AssertionError('Fixture generation must not fetch any source')),patch('builtins.print'):
                report=build_fixture(tmp)
            snapshot=Path(tmp)/'data_snapshot.json';meta=json.loads(snapshot.read_text());html=report.read_text()
            self.assertIsNone(meta['defense_source']);check_defense_provenance(meta)
            parser=PublicHTML();parser.feed(html)
            self.assertTrue(parser.matchups)
            self.assertTrue(all(a['title']=='最近10場例行賽防守資料暫缺' and '#dedbd5' in a['style'] for a in parser.matchups))
            self.assertIn('class="app-status">ESPN<br>',html);self.assertIn('對手防守資料暫缺',html)
            with self.assertRaisesRegex(ValueError,'Test fixture cannot be published'):check(report,snapshot)
    def test_season_resolver_dec_jan_and_new_year(self):
        for now,year in [(datetime(2026,12,31,tzinfo=timezone.utc),2027),(datetime(2027,1,1,tzinfo=timezone.utc),2027),(datetime(2027,10,1,tzinfo=timezone.utc),2028)]:
            class Clock(datetime):
                @classmethod
                def now(cls,tz=None):return now
            with patch.object(utils,'datetime',Clock),patch.object(utils,'read_json',return_value={'sports':[{'leagues':[{'season':{'year':year}}]}]}):self.assertEqual(utils.season_year(),year)

if __name__=='__main__':unittest.main()
