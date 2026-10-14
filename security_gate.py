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

ROTO_FILES = ['roto.html','roto_data.js','roto_core.js','roto.js','roto.css','dashboard.css']
ASSETS = ['jquery-3.7.1.min.js','datatables-2.3.7.min.js','datatables-2.3.7.min.css']
ATTRIBUTION_URLS={'https://www.boxscorelab.com/downloads/2025-26-player-season-totals.csv','https://creativecommons.org/licenses/by/4.0/'}
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
                if not (tag=='a' and key=='href' and value in ATTRIBUTION_URLS and attrs.get('rel')=='noopener' and attrs.get('target')=='_blank'):
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
    if 'Fixture Alpha' in data or 'Fixture Beta' in data or 'UI TEST ONLY' in data:raise ValueError('Test fixture cannot be published')
    meta=json.loads(snapshot.read_text(encoding='utf-8'))
    if meta.get('stats_source')!='ESPN' or meta.get('defense_source')!='PBP Stats':raise ValueError('Source provenance absent')
    if meta.get('fixture') or meta.get('defense',{}).get('source')!='PBP Stats':raise ValueError('Defense provenance absent or test fixture')
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


def check_roto(require_ready=True,report=None):
    html=Path('roto.html').read_text(encoding='utf-8');parser=PublicHTML();parser.feed(html)
    csp="default-src 'none'; script-src 'self'; style-src 'self'; img-src data:; connect-src 'none'; base-uri 'none'; form-action 'none'"
    if parser.errors or parser.csp!=csp:raise ValueError('ROTO public content/CSP check failed')
    expected=(set(ROTO_FILES)-{'roto.html'})|{'assets/'+name for name in ASSETS}
    actual={a.get('src',a.get('href')) for a in parser.external}
    if actual!=expected or parser.scripts!=5:raise ValueError('ROTO asset allowlist mismatch')
    for asset in ASSETS:
        expected_integrity='sha384-'+base64.b64encode(hashlib.sha384(Path('assets',asset).read_bytes()).digest()).decode()
        attrs=next(a for a in parser.external if a.get('src',a.get('href'))=='assets/'+asset)
        if attrs.get('integrity')!=expected_integrity:raise ValueError('ROTO pinned asset integrity mismatch')
    for name in ROTO_FILES:
        if not Path(name).is_file():raise ValueError('Missing ROTO public file: '+name)
        content=Path(name).read_text(encoding='utf-8')
        if any(re.search(pattern,content) for pattern in SECRET_PATTERNS):raise ValueError('Potential secret in '+name+'; value suppressed')
        if name in ['roto.html','roto_data.js'] and ('UI TEST ONLY' in content or 'Fixture Alpha' in content):raise ValueError('ROTO test fixture cannot be published')
    raw=Path('roto_data.js').read_text(encoding='utf-8')
    match=re.fullmatch(r'window\.ROTO_DATA = (.*);\s*',raw)
    if not match:raise ValueError('ROTO data format invalid')
    data=json.loads(match[1]);snapshot=json.loads(Path('data_snapshot.json').read_text())
    if data.get('version')!=1 or data.get('generated_at')!=snapshot['generated_at'] or data.get('source') not in ['ESPN','BoxScore Lab']:raise ValueError('ROTO snapshot provenance mismatch')
    if data.get('fixture'):raise ValueError('ROTO test fixture cannot be published')
    if require_ready:
        if data.get('source')=='BoxScore Lab':
            from roto_package import build_package
            from roto_data import read_report
            expected_data=build_package(read_report(report or 'index.html'),snapshot)
            active=data.get('extra_periods',{}).get(data.get('default_period'),data)
            applicable=active.get('data_ready') or active.get('stats_available') and active['reference']['size']==active['reference']['expected']>0
            if data!=expected_data or not applicable:
                raise ValueError('ROTO release blocked: source/mapping/uncertainty/reference provenance does not reproduce')
            if data['source_info']['independent_checks']['official_full_table_verified']:
                raise ValueError('Secondary source must not claim official full-table verification')
            if 'BoxScore Lab' not in html or 'CC BY 4.0' not in html or 'Jabari' not in html:
                raise ValueError('ROTO attribution or uncertainty disclosure missing')
        else:
            reference=data['reference'];expected=snapshot['period_populations']['LastSeason']
            if not data.get('data_ready') or expected<=0 or reference['size']!=expected or reference['shooting_complete']!=expected:
                raise ValueError('ROTO release blocked: full last-season reference and shooting denominators are incomplete')
            from roto_data import benchmark
            records=reference.get('records',[])
            if len(records)!=expected or len({r['id'] for r in records})!=expected or benchmark(records)!=data['benchmark']:
                raise ValueError('ROTO release blocked: fixed reference cannot be reproduced')
            for p in data['players'].values():
                if not p['gp'] or p['gp']<=0:continue
                for prefix in ['FG','FT']:
                    made,attempts=p['shots'].get(prefix+'M'),p['shots'].get(prefix+'A')
                    if made is None or attempts is None or not all(isinstance(v,(int,float)) and not isinstance(v,bool) and v>=0 and float(v).is_integer() for v in [made,attempts]) or made>attempts:
                        raise ValueError('ROTO release blocked: invalid/missing player shooting totals')
            for mode in ['perGame','totals']:
                for metric in ['PTS','REB','AST','3PM','STL','BLK','FG%','FT%','TO']:
                    b=data['benchmark'][mode][metric]
                    if b['mean'] is None or b['sd'] is None or b['sd']<=0:raise ValueError('ROTO release blocked: incomplete nine-category reference')
    print('ROTO static assets/CSP/provenance passed'+('; applicable source coverage and declared unknowns passed' if require_ready and data.get('source')=='BoxScore Lab' else '; complete nine-category release data passed' if require_ready else '; readiness deliberately not asserted'))


def main():
    p=argparse.ArgumentParser();p.add_argument('--generated',action='store_true');p.add_argument('--stage');a=p.parse_args()
    report=Path('fantasy_nba_report_v2.html' if a.generated else 'index.html');snapshot=Path('data_snapshot.json')
    check(report,snapshot)
    check_roto(report=report)
    if a.stage:
        stage=Path(a.stage)
        if stage.exists():raise ValueError('Publish staging directory must start empty')
        stage.mkdir();shutil.copyfile(report,stage/'index.html');shutil.copyfile(snapshot,stage/'data_snapshot.json')
        (stage/'assets').mkdir()
        for name in ASSETS:shutil.copyfile(Path('assets',name),stage/'assets'/name)
        for name in ROTO_FILES:shutil.copyfile(Path(name),stage/name)
        (stage/'.nojekyll').touch()
        expected={'index.html','data_snapshot.json','.nojekyll'}|{'assets/'+x for x in ASSETS}|set(ROTO_FILES)
        actual={str(x.relative_to(stage)).replace('\\','/') for x in stage.rglob('*') if x.is_file()}
        if actual!=expected:raise ValueError('Unexpected publish artifact files')
        print('Publish allowlist: '+', '.join(sorted(actual)))

if __name__=='__main__':main()
