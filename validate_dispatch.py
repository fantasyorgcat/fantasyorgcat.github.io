"""Validate a repository_dispatch before the existing privileged Pages deployment."""
import json
import os
from pathlib import Path
import re
import subprocess
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

REPOSITORY = 'hotmilk300/Fantasy-NBA-Streaming-Assistant'


def verify_payload(event, checkout_sha):
    payload=event.get('client_payload',{})
    sha=payload.get('report_sha','');run_id=payload.get('run_id','');attempt=payload.get('run_attempt','')
    if event.get('action')!='nba-report-ready' or event.get('repository',{}).get('full_name')!=REPOSITORY:
        raise ValueError('Unexpected dispatch repository/type')
    if not isinstance(sha,str) or not re.fullmatch(r'[0-9a-f]{40}',sha) or sha!=checkout_sha:
        raise ValueError('Dispatch SHA must equal current main checkout; stale or invalid event rejected')
    if not isinstance(run_id,str) or not run_id.isdigit() or not isinstance(attempt,str) or not attempt.isdigit():
        raise ValueError('Invalid upstream run provenance')
    return sha,run_id,int(attempt)


def verify_run(run,run_id,attempt):
    if (str(run.get('id'))!=run_id or run.get('run_attempt')!=attempt or
        run.get('name')!='Daily NBA Fantasy Update' or run.get('path')!='.github/workflows/daily_update.yml' or
        run.get('head_branch')!='main' or run.get('head_repository',{}).get('full_name')!=REPOSITORY or
        run.get('event') not in ['schedule','workflow_dispatch']):
        raise ValueError('Dispatch upstream workflow provenance mismatch')
    if run.get('status')=='completed' and run.get('conclusion')!='success':
        raise ValueError('Upstream daily workflow did not succeed')
    return run.get('status')=='completed'


def main():
    if os.environ.get('GITHUB_EVENT_NAME')!='repository_dispatch' or os.environ.get('GITHUB_REF')!='refs/heads/main':
        raise ValueError('Unexpected deployment context')
    event=json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text(encoding='utf-8'))
    checkout_sha=subprocess.check_output(['git','rev-parse','HEAD'],text=True,timeout=20).strip()
    sha,run_id,attempt=verify_payload(event,checkout_sha)
    # Public repository metadata needs no token; preserve Pages permissions unchanged.
    request=Request('https://api.github.com/repos/'+REPOSITORY+'/actions/runs/'+run_id,headers={
        'Accept':'application/vnd.github+json','User-Agent':'Fantasy-NBA-Streaming-Assistant/2.0'})
    for poll in range(6):
        try:
            with urlopen(request,timeout=20) as response:run=json.load(response)
        except (HTTPError,URLError,TimeoutError,ValueError):
            raise RuntimeError('Public upstream run verification failed; deployment stopped') from None
        if verify_run(run,run_id,attempt):
            print('Verified successful daily run '+run_id+' and current main report '+sha)
            return
        if poll<5:time.sleep(10)
    raise RuntimeError('Upstream daily workflow not completed within bounded verification window')


if __name__=='__main__':main()
