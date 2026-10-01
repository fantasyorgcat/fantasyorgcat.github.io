import unittest
from unittest.mock import patch
import validate_dispatch as v

SHA='a'*40
class Dispatch(unittest.TestCase):
    def event(self):return {'action':'nba-report-ready','repository':{'full_name':v.REPOSITORY},'client_payload':{'report_sha':SHA,'run_id':'123','run_attempt':'1'}}
    def fixture_run(self):return dict(id=123,run_attempt=1,name='Daily NBA Fantasy Update',path='.github/workflows/daily_update.yml',head_branch='main',head_repository={'full_name':v.REPOSITORY},event='workflow_dispatch',status='completed',conclusion='success')
    def test_successful_exact_main(self):
        self.assertEqual(v.verify_payload(self.event(),SHA),(SHA,'123',1));self.assertTrue(v.verify_run(self.fixture_run(),'123',1))
    def test_stale_report_rejected(self):
        with self.assertRaises(ValueError):v.verify_payload(self.event(),'b'*40)
    def test_injected_sha_rejected(self):
        e=self.event();e['client_payload']['report_sha']='$(printenv)'
        with self.assertRaises(ValueError):v.verify_payload(e,e['client_payload']['report_sha'])
    def test_wrong_repo_type_or_run_rejected(self):
        for field,value in [('action','other'),('repository',{'full_name':'other/repo'}),('client_payload',{'report_sha':SHA,'run_id':'../private','run_attempt':'1'})]:
            e=self.event();e[field]=value
            with self.assertRaises(ValueError):v.verify_payload(e,SHA)
    def test_failed_upstream_rejected(self):
        for conclusion in ['failure','cancelled','skipped']:
            r=self.fixture_run();r['conclusion']=conclusion
            with self.assertRaises(ValueError):v.verify_run(r,'123',1)
    def test_cross_repo_branch_workflow_or_attempt_rejected(self):
        for field,value in [('head_repository',{'full_name':'other/repo'}),('head_branch','feature'),('name','Other'),('path','other.yml'),('run_attempt',2),('event','pull_request')]:
            r=self.fixture_run();r[field]=value
            with self.assertRaises(ValueError):v.verify_run(r,'123',1)
    def test_upstream_not_complete_requires_wait(self):
        r=self.fixture_run();r.update(status='in_progress',conclusion=None);self.assertFalse(v.verify_run(r,'123',1))

if __name__=='__main__':unittest.main()
