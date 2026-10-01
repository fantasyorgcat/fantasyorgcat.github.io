"""Send an authenticated, version-bound deployment event using the existing job token."""
import json
import os
import re
import subprocess
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

REPOSITORY = 'hotmilk300/Fantasy-NBA-Streaming-Assistant'
EVENT_TYPE = 'nba-report-ready'


def main():
    if os.environ.get('GITHUB_REPOSITORY') != REPOSITORY or os.environ.get('GITHUB_REF') != 'refs/heads/main':
        raise ValueError('Deployment dispatch requires this repository main')
    sha = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True, timeout=20).strip()
    run_id = os.environ['GITHUB_RUN_ID']
    attempt = os.environ['GITHUB_RUN_ATTEMPT']
    if not re.fullmatch(r'[0-9a-f]{40}', sha) or not run_id.isdigit() or not attempt.isdigit():
        raise ValueError('Invalid deployment provenance')
    payload = json.dumps({'event_type': EVENT_TYPE, 'client_payload': {'report_sha': sha, 'run_id': run_id, 'run_attempt': attempt}}).encode()
    request = Request('https://api.github.com/repos/'+REPOSITORY+'/dispatches', data=payload, method='POST', headers={
        'Accept':'application/vnd.github+json', 'User-Agent':'Fantasy-NBA-Streaming-Assistant/2.0',
        'X-GitHub-Api-Version':'2022-11-28', 'Authorization':'Bearer '+os.environ['GH_TOKEN']})
    for retry in range(3):
        try:
            with urlopen(request, timeout=30) as response:
                if response.status != 204:raise RuntimeError('Unexpected dispatch response')
            print('Pages event accepted for report '+sha+' from daily run '+run_id)
            return
        except HTTPError as error:
            if error.code not in [429,500,502,503,504] or retry == 2:
                raise RuntimeError('Pages dispatch HTTP '+str(error.code)+'; token and response suppressed') from None
        except (URLError, TimeoutError):
            if retry == 2:raise RuntimeError('Pages dispatch connection failed; token suppressed') from None
        time.sleep(2 ** retry)


if __name__ == '__main__':main()
