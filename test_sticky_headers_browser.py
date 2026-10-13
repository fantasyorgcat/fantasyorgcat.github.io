"""Verify fixed headers on the checked-in real NBA report, without fetching data."""
import json
import os
from pathlib import Path
import sys
from playwright.sync_api import sync_playwright


def run(url, output):
    output.mkdir(parents=True, exist_ok=True)
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=os.environ.get('CHROMIUM_PATH', '/usr/bin/chromium'), headless=True)
        for width, height in [(1500, 1000), (390, 844)]:
            page = browser.new_page(viewport={'width': width, 'height': height})
            errors, failed = [], []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.on('requestfailed', lambda request: failed.append(request.url))
            assert page.goto(url, wait_until='load', timeout=60000).status == 200
            page.wait_for_function('Object.keys(tables).length===5')
            signature = page.evaluate('JSON.stringify([playerCatalog,scheduleEvents,platformPeriods,scheduleGeneratedAt])')

            def position(selector):
                page.evaluate('''selector=>{const target=document.querySelector(selector),nav=document.querySelector('.workspace-bar');
                    window.scrollTo({top:target.getBoundingClientRect().top+scrollY-nav.offsetHeight-12,behavior:"instant"});}''', selector)
                page.wait_for_timeout(400)

            def scroll_check(scroller, header, first_row, name):
                area, head, row = page.locator(scroller), page.locator(header), page.locator(first_row)
                area.evaluate('(e)=>{e.scrollTop=0;e.scrollLeft=0;}')
                position(header)
                before_head, before_row = head.bounding_box(), row.bounding_box()
                assert area.evaluate('(e)=>e.scrollHeight>e.clientHeight'), name
                box = area.bounding_box()
                page.mouse.move(box['x']+box['width']/2, box['y']+box['height']/2)
                page.mouse.wheel(0, 300)
                page.wait_for_timeout(350)
                assert area.evaluate('(e)=>e.scrollTop>100'), name
                after_head = head.bounding_box()
                assert abs(before_head['y']-after_head['y']) < 2, (name, before_head, after_head)
                assert row.bounding_box()['y'] < before_row['y']-100, name
                nav = page.locator('.workspace-bar').bounding_box()
                assert after_head['y'] >= nav['y']+nav['height']-1, name
                assert after_head['y']+after_head['height'] < height, name
                assert head.evaluate('(e)=>getComputedStyle(e.querySelector("th")).backgroundColor') == 'rgb(215, 222, 223)'
                page.screenshot(path=str(output / f'{name}-{width}.png'))
                area.evaluate('(e)=>{e.scrollLeft=e.scrollWidth;e.dispatchEvent(new Event("scroll"));}')
                if width==390 or area.evaluate('(e)=>e.scrollWidth>e.clientWidth'):
                    assert area.evaluate('(e)=>e.scrollLeft>0'), name
                if name == 'players':
                    assert abs(area.evaluate('(e)=>e.scrollLeft')-head.evaluate('(e)=>e.scrollLeft')) < 2
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
                assert head.bounding_box()['y'] >= page.locator('.workspace-bar').bounding_box()['height']-1
                page.screenshot(path=str(output / f'{name}-right-{width}.png'))
                area.evaluate('(e)=>{e.scrollLeft=0;e.dispatchEvent(new Event("scroll"));}')

            page.locator('[data-platform="NBA"]').click()
            page.locator('#season-week').select_option('0')
            scroll_check('#playerTableWCustom_wrapper .dt-scroll-body', '#playerTableWCustom_wrapper .dt-scroll-head',
                         '#playerTableWCustom tbody tr:first-child', 'players')
            # Click the original DataTables header while vertically scrolled.
            header = page.locator('#playerTableWCustom_wrapper .dt-scroll-head th.stat-ls.stat-avg').nth(1)
            for _ in range(2):
                header.click()
                page.wait_for_function('''()=>{const t=tables.WCustom,[column,direction]=t.order()[0],v=t.column(column,{order:'applied'}).nodes().toArray().map(n=>Number(n.dataset.order));
                    return v.every((x,i)=>!i||(direction==='asc'?v[i-1]<=x:v[i-1]>=x));}''')
            page.locator('#WeekCustom [data-mode="TOT"]').click()
            page.locator('#WeekCustom [data-period="L7"]').click()
            assert page.locator('#playerTableWCustom td.stat-l7.stat-tot').first.inner_text() == '—'
            page.locator('#WeekCustom [data-period="LS"]').click()
            page.locator('#WeekCustom [data-mode="AVG"]').click()

            scroll_check('#WeekCustom .schedule-scroll', '#teamTableWCustom thead', '#teamTableWCustom tbody tr:first-child', 'teams')
            button = page.locator('#teamTableWCustom [data-team-games-sort]')
            button.click()
            button.focus()
            button.press('Enter')
            assert button.locator('[data-games-sort-arrow]').inner_text() == '↑'
            page.locator('#show-all-players').click()

            # Compare real players; its first column stays fixed during horizontal scrolling.
            for checkbox in page.locator('#WeekCustom input[data-pick="compare"]').all()[:12]:
                checkbox.check()
            assert page.locator('#comparison-body tr').count() == 12
            scroll_check('.comparison-scroll', '#comparison-head', '#comparison-body tr:first-child', 'comparison')
            page.locator('#comparison-head [data-sort="name"]').click()
            assert page.locator('#comparison-body tr').count() == 12
            page.locator('#clear-comparison').click()

            # Dynamic rebuilding retains the same scroll treatment for a 14-day platform week.
            page.locator('[data-platform="YAHOO"]').click()
            page.locator('#season-week').select_option('6')
            assert page.locator('#playerTableWCustom_wrapper .dt-scroll-body').evaluate('(e)=>e.scrollHeight>e.clientHeight')
            page.locator('#schedule-extras summary').click()
            page.locator('.tablinks').nth(3).click()
            assert page.locator('#playerTableW4_wrapper .dt-scroll-body').evaluate('(e)=>e.scrollHeight>e.clientHeight')
            assert signature == page.evaluate('JSON.stringify([playerCatalog,scheduleEvents,platformPeriods,scheduleGeneratedAt])')
            assert not errors, errors
            assert not failed, failed
            results.append(dict(width=width, height=height, real_data=True, actual_wheel_scroll=True,
                                players_teams_comparison_headers_fixed=True, nav_clear=True, original_palette=True,
                                horizontal_scroll_and_header_sync=True, original_sort_and_keyboard=True,
                                period_mode_and_rebuilt_tables=True, data_preserved=True, js_errors=errors, failed_requests=failed))
            page.close()
        browser.close()
    (output / 'browser-results.json').write_text(json.dumps(results, indent=2))
    print(json.dumps(results))


if __name__ == '__main__':
    run(sys.argv[1], Path(sys.argv[2] if len(sys.argv)>2 else '/tmp/nba-sticky-headers'))
