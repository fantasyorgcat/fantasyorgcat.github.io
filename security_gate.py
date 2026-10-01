"""Bounded release gate. It is not a claim of absolute security."""
import argparse
import base64
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import shutil
import subprocess

ASSETS = ['jquery-3.7.1.min.js','datatables-2.3.7.min.js','datatables-2.3.7.min.css']
SECRET_PATTERNS = [r'gh[pousr]_[A-Za-z0-9]{30,}', r'github_pat_[A-Za-z0-9_]{40,}', r'AKIA[0-9A-Z]{16}', r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----']


class PublicHTML(HTMLParser):
    def __init__(self):
        super().__init__(); self.errors=[]; self.external=[]; self.scripts=0; self.csp=None
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if tag in ['iframe','object','embed','base','form','img']:
            self.errors.append('Unexpected active content tag: '+tag)
        if tag=='meta' and attrs.get('http-equiv','').lower()=='content-security-policy':self.csp=attrs.get('content')
        if tag=='script':
            self.scripts+=1
            if 'src' in attrs:self.external.append(attrs)
        if tag=='link':self.external.append(attrs)
        for key,value in attrs.items():
            if key in ['src','href'] and value and (value.startswith(('http:','https:','//','javascript:')) or '..' in value):
                self.errors.append('Unexpected external/unsafe resource URL')


def check(report, snapshot):
    data=report.read_text(encoding='utf-8'); parser=PublicHTML();parser.feed(data)
    if parser.errors:raise ValueError('; '.join(parser.errors))
    if parser.csp != "default-src 'none'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src data:; connect-src 'none'; base-uri 'none'; form-action 'none'":raise ValueError('Expected CSP missing or changed')
    if parser.scripts!=3 or len(parser.external)!=3:raise ValueError('Unexpected script/resource count')
    for asset in ASSETS:
        path=Path('assets',asset)
        expected='sha384-'+base64.b64encode(hashlib.sha384(path.read_bytes()).digest()).decode()
        attrs=next((a for a in parser.external if a.get('src',a.get('href'))=='assets/'+asset),None)
        if not attrs or attrs.get('integrity')!=expected:raise ValueError('Asset integrity mismatch')
    if hashlib.sha256(Path('assets/jquery-3.7.1.min.js').read_bytes()).digest()!=base64.b64decode('/JqT3SQfawRcv/BIHPThkBvs0OEvtFFmqPF/lYI/Cxo='):
        raise ValueError('Official pinned jQuery digest mismatch')
    if 'Fixture Alpha' in data or 'Fixture Beta' in data:raise ValueError('Test fixture cannot be published')
    meta=json.loads(snapshot.read_text(encoding='utf-8'))
    if meta.get('stats_source')!='ESPN' or meta.get('defense_source')!='PBP Stats':raise ValueError('Source provenance absent')
    if not meta.get('roster_players') or not meta.get('schedule',{}).get('season'):raise ValueError('Roster/schedule provenance absent')
    if not any(k.startswith('players_') and v.get('population',0)>0 for k,v in meta.items() if isinstance(v,dict)):
        raise ValueError('Complete league statistics provenance absent')
    # Scan only tracked project files and explicitly public/generated files; print no matching values.
    paths=[Path(x) for x in subprocess.check_output(['git','ls-files'],text=True).splitlines()]
    paths += [report,snapshot]+[Path('assets',a) for a in ASSETS]
    for path in set(paths):
        if not path.is_file():continue
        if path.suffix.lower() in ['.pem','.key','.p12','.pfx'] or path.name=='.env':raise ValueError('Credential file tracked')
        content=path.read_text(encoding='utf-8',errors='replace')
        if any(re.search(pattern,content) for pattern in SECRET_PATTERNS):
            raise ValueError('Potential secret in '+str(path)+'; value suppressed')
    print('Public HTML/resource integrity, provenance, fixture exclusion, and bounded tracked-file secret scan passed')


def main():
    p=argparse.ArgumentParser();p.add_argument('--generated',action='store_true');p.add_argument('--stage');a=p.parse_args()
    report=Path('fantasy_nba_report_v2.html' if a.generated else 'index.html');snapshot=Path('data_snapshot.json')
    check(report,snapshot)
    if a.stage:
        stage=Path(a.stage)
        if stage.exists():raise ValueError('Publish staging directory must start empty')
        stage.mkdir();shutil.copyfile(report,stage/'index.html');shutil.copyfile(snapshot,stage/'data_snapshot.json')
        (stage/'assets').mkdir()
        for name in ASSETS:shutil.copyfile(Path('assets',name),stage/'assets'/name)
        (stage/'.nojekyll').touch()
        expected={'index.html','data_snapshot.json','.nojekyll'}|{'assets/'+x for x in ASSETS}
        actual={str(x.relative_to(stage)).replace('\\','/') for x in stage.rglob('*') if x.is_file()}
        if actual!=expected:raise ValueError('Unexpected publish artifact files')
        print('Publish allowlist: '+', '.join(sorted(actual)))

if __name__=='__main__':main()
