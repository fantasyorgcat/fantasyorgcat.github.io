"""Repackage a retained report without fetching or dating it as a fresh snapshot."""
import json
from pathlib import Path
import re
from report_data import pack_catalog, pack_events, read_script, write_script, script_tags
from roto_data import read_report, write_data
from roto_package import build_package


def regenerate(report='index.html'):
    path = Path(report)
    html = path.read_text(encoding='utf-8')
    snapshot = json.loads(Path('data_snapshot.json').read_text(encoding='utf-8'))
    catalog = read_report(path)
    if 'src="report_data.js"' in html:
        payload = read_script(path.with_name('report_data.js'), 'REPORT_DATA')
    else:
        def embedded(name):
            match = re.search(r'var ' + name + r' = (.*?);\s*\n', html)
            if not match:
                raise ValueError('Offline report missing ' + name)
            return json.loads(match[1])
        payload = dict(version=1, generated_at=snapshot['generated_at'], catalog=pack_catalog(catalog),
                       events=embedded('scheduleEvents'), weeks=embedded('seasonWeeks'),
                       platforms=embedded('platformPeriods'), quick=embedded('quickPeriods'), meta=embedded('playerToolsMeta'))
        # Only the large player bodies are removed. Headers, controls and page copy stay intact.
        html = re.sub(r'(<table id="playerTable[^\"]+".*?<tbody>).*?(</tbody>)', r'\1\2', html, flags=re.S)
        html = re.sub(r'        <script>.*?</script>', '        ' + script_tags(), html, flags=re.S)
    payload['events']=pack_events(payload['events'])
    html=re.sub(r'<div class="team-section">.*?</table></div></div>', '', html, flags=re.S)
    write_script('report_data.js', 'REPORT_DATA', payload)
    write_data(build_package(catalog, snapshot))
    Path('fantasy_nba_report_v2.html').write_text(html, encoding='utf-8')
    print('Offline report repackaged; retained source timestamp: ' + snapshot['generated_at'])


if __name__ == '__main__':
    regenerate()
