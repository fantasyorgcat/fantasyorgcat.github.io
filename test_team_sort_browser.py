"""Exercise the checked-in real report without fetching or replacing NBA data."""
import functools
import http.server
import json
import os
from pathlib import Path
import threading
from playwright.sync_api import sync_playwright


def run(url, output):
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=os.environ.get('CHROMIUM_PATH', '/usr/bin/chromium'), headless=True)
        for width, height in [(1500, 1000), (390, 844)]:
            context = browser.new_context(viewport={'width': width, 'height': height})
            page = context.new_page()
            errors, failed = [], []
            page.on('pageerror', lambda e: errors.append(str(e)))
            page.on('requestfailed', lambda r: failed.append(r.url))
            assert page.goto(url, wait_until='load', timeout=60000).status == 200
            page.wait_for_function('Object.keys(tables).length===5')
            signature = page.evaluate('JSON.stringify([playerCatalog,scheduleEvents,platformPeriods,scheduleGeneratedAt])')
            assert page.evaluate('scheduleEvents.length') == 1200
            assert page.evaluate('Object.keys(playerCatalog).length') == 610
            assert page.locator('#rank-settings').count() == 0

            def rows(selector='#teamTableWCustom'):
                return page.locator(selector + ' tbody tr.team-row').evaluate_all('(rows)=>rows.map(r=>[r.dataset.team,Number(r.cells[1].textContent)])')

            def verify_sort(selector='#teamTableWCustom'):
                original = rows(selector)
                button = page.locator(selector + ' [data-team-games-sort]')
                assert button.get_attribute('type') == 'button'
                assert button.locator('[data-games-sort-arrow]').inner_text() == '↕'
                button.click()
                assert rows(selector) == sorted(original, key=lambda row: -row[1])
                assert button.locator('[data-games-sort-arrow]').inner_text() == '↓'
                assert page.locator(selector + ' th').nth(1).get_attribute('aria-sort') == 'descending'
                button.focus()
                button.press('Enter')
                assert rows(selector) == sorted(original, key=lambda row: row[1])
                assert button.locator('[data-games-sort-arrow]').inner_text() == '↑'
                button.press('Space')
                assert rows(selector) == sorted(original, key=lambda row: -row[1])
                return button

            # Distinct dates, Cup gaps and merged fantasy periods, using all original events.
            tested = {}
            for platform, indices in [('NBA', [0, 6, 7, 24]), ('YAHOO', [0, 6, 16, 22]), ('ESPN', [0, 6, 7, 17, 23])]:
                page.locator('[data-platform="' + platform + '"]').click()
                expected_options = {'NBA': 26, 'YAHOO': 24, 'ESPN': 25}[platform]
                assert page.locator('#season-week option').count() == expected_options
                for index in indices:
                    page.locator('#season-week').select_option(str(index))
                    expected = page.evaluate('''([key,index])=>{const period=platformPeriods[key].periods[index],out={};
                        for(const e of scheduleEvents)if(e.season_type===2&&e.date_et&&e.date_et>=period.start&&e.date_et<=period.end)
                        for(const team of [e.home,e.away])if(team){if(!(team in out))out[team]=0;if(!['cancelled','postponed','suspended'].includes(e.status))out[team]++;}
                        return out;}''', [platform, index])
                    assert dict(rows()) == expected
                    verify_sort()
                    assert page.evaluate('''()=>{for(const node of tables.WCustom.rows({search:'none'}).nodes().toArray()){
                        const id=node.querySelector('[data-player-id]').dataset.playerId;
                        const actual=node.querySelector('.rank-ls-avg').textContent;
                        const expected=playerCatalog[id].periods.ls.avg.Rank.value;
                        if(actual!==(expected===null?'—':String(expected)))return false;}return true;}''')
                tested[platform] = indices

            page.locator('[data-platform="NBA"]').click()
            page.locator('#season-week').select_option('0')
            button = verify_sort()
            selected_team = rows()[0][0]
            page.locator('#teamTableWCustom tr[data-team="' + selected_team + '"]').click()
            assert page.evaluate('teamSelection.WCustom') == selected_team
            button.click()
            assert page.evaluate('teamSelection.WCustom') == selected_team
            page.locator('#show-all-players').click()
            page.evaluate("window.scrollTo(0,document.querySelector('#teamTableWCustom').getBoundingClientRect().top+scrollY-document.querySelector('.workspace-bar').offsetHeight-28)")
            page.screenshot(path=str(output / ('games-real-' + str(width) + '.png')))
            page.locator('#WeekCustom input[data-pick="compare"]').first.check()
            assert page.locator('#comparison-body tr').count() == 1
            assert page.evaluate('''()=>{const tr=document.querySelector('#comparison-body tr'),team=playerCatalog[tr.dataset.playerId].team;
                const source=tables.WCustom.rows({search:'none'}).data().toArray().find(row=>row[1]===team);
                return tr.cells[1].textContent===String(source[2]);}''')
            page.locator('#comparison-mode').select_option('tot')
            page.locator('#comparison-mode').select_option('avg')
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
            page.locator('#comparison-panel').scroll_into_view_if_needed()
            page.screenshot(path=str(output / ('comparison-real-' + str(width) + '.png')))
            page.locator('#clear-comparison').click()
            page.locator('#schedule-extras summary').click()
            page.locator('.tablinks').nth(3).click()
            verify_sort('#teamTableW4')
            page.evaluate("$('#teamTableW4').DataTable().order([[0,'asc']]).draw(false)")
            assert page.locator('#teamTableW4 [data-games-sort-arrow]').inner_text() == '↕'
            assert signature == page.evaluate('JSON.stringify([playerCatalog,scheduleEvents,platformPeriods,scheduleGeneratedAt])')

            # Edge cases mutate only a separate final test table, never the report file/events.
            page.evaluate('''()=>{const t=$('#teamTableW4').DataTable();t.clear();
                const columns=t.columns().count();for(const [team,games] of [['BOS',2],['LAL',2],['MIA',3],['NYK','—'],['CLE',0],['PHI','']]){
                const row=Array(columns).fill('');row[0]=team;row[1]=games;t.row.add(row);}t.order([]).draw(false);}''')
            button = page.locator('#teamTableW4 [data-team-games-sort]')
            button.click()
            names = lambda: page.evaluate("$('#teamTableW4').DataTable().rows({order:'applied'}).data().toArray().map(r=>r[0])")
            assert names() == ['MIA', 'BOS', 'LAL', 'CLE', 'NYK', 'PHI']
            button.click()
            assert names() == ['CLE', 'BOS', 'LAL', 'MIA', 'NYK', 'PHI']
            assert not errors, errors
            assert not failed, failed
            results.append(dict(width=width, real_data=True, tested_platforms=tested, stable_ties=True,
                                keyboard=True, unknown_last_and_zero_valid=True, original_rank_and_data_preserved=True,
                                team_filter_and_comparison=True, recent_datatable=True, no_page_overflow=True,
                                js_errors=errors, failed_requests=failed))
            context.close()
        browser.close()
    (output / 'browser-results.json').write_text(json.dumps(results, indent=2))
    print(json.dumps(results))


if __name__ == '__main__':
    import sys
    root = Path(__file__).resolve().parent
    output = Path(sys.argv[1] if len(sys.argv) > 1 else '/tmp/nba-games-browser').resolve()
    output.mkdir(parents=True, exist_ok=True)
    class QuietHandler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *_args):
            pass
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(QuietHandler, directory=str(root)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        run('http://127.0.0.1:' + str(server.server_port) + '/index.html', output)
    finally:
        server.shutdown()
