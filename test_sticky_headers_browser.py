"""Verify page-scroll player headers on the checked-in real report, without fetching data."""
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
            context = browser.new_context(viewport={'width': width, 'height': height},
                                          is_mobile=width==390, has_touch=width==390)
            page = context.new_page()
            errors, failed = [], []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.on('requestfailed', lambda request: failed.append(request.url))
            assert page.goto(url, wait_until='load', timeout=60000).status == 200
            page.wait_for_function('!!tables[activeWeek]')
            signature = page.evaluate('JSON.stringify([playerCatalog,scheduleEvents,platformPeriods,scheduleGeneratedAt])')
            page.locator('[data-platform="NBA"]').click()
            page.locator('#season-week').select_option('0')
            page.locator('#WeekCustom [data-period="LS"]').click()
            page.locator('#WeekCustom [data-display-setting="schedule"]').check()
            body = page.locator('#playerTableWCustom_wrapper .dt-scroll-body')
            head = page.locator('#playerTableWCustom_wrapper .dt-scroll-head')
            first_row = page.locator('#playerTableWCustom tbody tr:first-child')

            def pinned():
                nav = page.locator('.workspace-bar').bounding_box()
                box = head.bounding_box()
                assert abs(box['y']-(nav['y']+nav['height'])) < 2, (width, nav, box)
                assert box['y']+box['height'] < height
                assert head.evaluate('(e)=>getComputedStyle(e.querySelector("th")).backgroundColor') == 'rgb(215, 222, 223)'
                assert body.evaluate('(e)=>e.scrollTop===0&&e.scrollHeight<=e.clientHeight+1')

            def aligned():
                assert page.evaluate('''()=>{const head=document.querySelector('#playerTableWCustom_wrapper .dt-scroll-head'),row=document.querySelector('#playerTableWCustom tbody tr');
                    const visible=cells=>Array.from(cells).filter(e=>getComputedStyle(e).display!=='none').map(e=>e.getBoundingClientRect());
                    const a=visible(head.querySelectorAll('th')),b=visible(row.cells);
                    const body=document.querySelector('#playerTableWCustom_wrapper .dt-scroll-body');
                    return a.length===b.length&&a.every((r,i)=>Math.abs(r.x-b[i].x)<2&&Math.abs(r.width-b[i].width)<2)&&Math.abs(body.scrollLeft-head.scrollLeft)<2;}''')
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')

            # Keep the original page-scrolling flow: no player-table scrollTop or vertical cap.
            assert body.evaluate('(e)=>getComputedStyle(e).maxHeight==="none"&&e.scrollHeight<=e.clientHeight+1')
            page.evaluate('''()=>{const e=document.querySelector('#playerTableWCustom_wrapper .dt-scroll-head');
                scrollTo({top:e.getBoundingClientRect().top+scrollY-100,behavior:'instant'});}''')
            page.wait_for_timeout(200)
            before_y, before_row = page.evaluate('scrollY'), first_row.bounding_box()['y']
            if width==390:
                cdp = context.new_cdp_session(page)
                cdp.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':[{'x':180,'y':650}]})
                for y in range(600,149,-50):
                    cdp.send('Input.dispatchTouchEvent',{'type':'touchMove','touchPoints':[{'x':180,'y':y}]})
                    page.wait_for_timeout(20)
                cdp.send('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]})
            else:
                page.mouse.move(width/2,height/2)
                page.mouse.wheel(0,600)
            page.wait_for_timeout(400)
            assert page.evaluate('scrollY') > before_y+300, (width,before_y,page.evaluate('scrollY'))
            assert first_row.bounding_box()['y'] < before_row-300
            pinned(); aligned()
            page.screenshot(path=str(output / f'players-{width}.png'))
            page.evaluate('scrollBy({top:350,behavior:"instant"})')
            pinned()
            if width==390:
                cdp.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':[{'x':330,'y':650}]})
                for x in range(300,29,-30):
                    cdp.send('Input.dispatchTouchEvent',{'type':'touchMove','touchPoints':[{'x':x,'y':650}]})
                    page.wait_for_timeout(20)
                cdp.send('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]})
            else:
                body.evaluate('(e)=>{e.scrollLeft=e.scrollWidth;e.dispatchEvent(new Event("scroll"));}')
            page.wait_for_timeout(250)
            assert body.evaluate('(e)=>e.scrollLeft>0')
            pinned(); aligned()
            page.screenshot(path=str(output / f'players-right-{width}.png'))

            # Sort the actual sticky header while the page is deep within the long table.
            body.evaluate('(e)=>{e.scrollLeft=e.scrollWidth;e.dispatchEvent(new Event("scroll"));}')
            for _ in range(2):
                head.locator('th.rank-ls-avg').click()
                page.wait_for_function('''()=>{const t=tables.WCustom,[column,direction]=t.order()[0],v=t.column(column,{order:'applied'}).nodes().toArray().map(n=>Number(n.dataset.order));
                    return v.every((x,i)=>!i||(direction==='asc'?v[i-1]<=x:v[i-1]>=x));}''')
                pinned(); aligned()
            # A responsive navigation height change must update the sticky offset.
            page.locator('#platform-note').evaluate('(e)=>e.textContent+=" "+"導覽高度測試 ".repeat(12)')
            page.wait_for_timeout(200)
            pinned()
            page.locator('[data-platform="YAHOO"]').click()
            page.locator('#season-week').select_option('6')
            page.locator('#WeekCustom [data-mode="TOT"]').click()
            page.locator('#WeekCustom [data-period="L7"]').click()
            assert page.evaluate('''()=>{const t=tables.WCustom,i=t.rows({page:'current'}).indexes()[0],col=t.column('.stat-l7.stat-tot').index(),expected=playerCatalog[t.row(i).data()[0]].periods.l7.tot.MIN.value;return t.cell(i,col).render('sort')===(expected===null?-1:expected)&&Number(t.cell(i,col).node().dataset.order)===(expected===null?-1:expected);}''')
            page.locator('#WeekCustom [data-period="LS"]').click()
            page.locator('#WeekCustom [data-mode="AVG"]').click()
            page.evaluate('''()=>{const e=document.querySelector('#playerTableWCustom_wrapper .dt-scroll-body');
                scrollTo({top:e.getBoundingClientRect().top+scrollY+500,behavior:'instant'});}''')
            pinned(); aligned()
            # Headers stay within their table; below the table the header scrolls away.
            page.locator('.footer').evaluate('(e)=>e.style.marginBottom="2000px"')
            page.evaluate('scrollTo({top:document.body.scrollHeight,behavior:"instant"})')
            assert head.bounding_box()['y']+head.bounding_box()['height'] < 0
            page.locator('.footer').evaluate('(e)=>e.style.marginBottom=""')
            assert head.bounding_box()['y']+head.bounding_box()['height'] <= body.bounding_box()['y']+body.bounding_box()['height']+2
            assert page.locator('#show-all-players').bounding_box()['y'] >= 0

            # Team tables retain their original local vertical scroller and sticky header.
            page.locator('[data-platform="NBA"]').click()
            page.locator('#season-week').select_option('0')
            area = page.locator('#WeekCustom .schedule-scroll')
            team_head = page.locator('#teamTableWCustom thead')
            page.evaluate('''()=>{const e=document.querySelector('#WeekCustom .schedule-scroll');scrollTo({top:e.getBoundingClientRect().top+scrollY-document.querySelector('.workspace-bar').offsetHeight-12,behavior:'instant'});}''')
            before = team_head.bounding_box()['y']
            area.evaluate('(e)=>e.scrollTop=200')
            assert abs(team_head.bounding_box()['y']-before)<2
            page.locator('#teamTableWCustom [data-team-games-sort]').click()
            page.locator('#teamTableWCustom [data-team-games-sort]').press('Enter')
            assert page.locator('#teamTableWCustom [data-games-sort-arrow]').inner_text()=='↑'
            page.screenshot(path=str(output / f'teams-{width}.png'))
            # The navigation observer leaves existing checkbox comparison and storage behavior alone.
            choices=page.locator('#WeekCustom input[data-pick="compare"]').evaluate_all('(nodes)=>nodes.map(n=>n.dataset.playerId)')
            pair=[choices[0],next(pid for pid in choices if page.evaluate('(id)=>playerCatalog[id].team',pid)!=page.evaluate('(id)=>playerCatalog[id].team',choices[0]))]
            for pid in pair:
                page.locator('#WeekCustom input[data-player-id="'+pid+'"]').check()
            assert page.locator('#comparison-body tr').count()==2
            page.locator('#comparison-mode').select_option('tot')
            page.locator('#comparison-period').select_option('l7')
            page.locator('#comparison-period').select_option('ls')
            page.locator('#comparison-mode').select_option('avg')
            assert page.locator('.comparison-scroll').evaluate('(e)=>getComputedStyle(e).maxHeight==="none"&&e.scrollHeight<=e.clientHeight+1')
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
            page.locator('#clear-comparison').click()
            assert signature == page.evaluate('JSON.stringify([playerCatalog,scheduleEvents,platformPeriods,scheduleGeneratedAt])')
            assert not errors, errors
            assert not failed, failed
            results.append(dict(width=width,height=height,real_data=True,page_scroll_verified=True,
                                touch_page_and_horizontal_scroll=width==390,player_vertical_inner_scroll=False,
                                original_header_sticky_below_responsive_nav=True,column_alignment=True,
                                original_palette_and_sort=True,rebuilt_periods_and_modes=True,
                                original_team_scroller_preserved=True,data_preserved=True,js_errors=errors,failed_requests=failed))
            context.close()
        browser.close()
    (output / 'browser-results.json').write_text(json.dumps(results, indent=2))
    print(json.dumps(results))


if __name__=='__main__':
    run(sys.argv[1],Path(sys.argv[2] if len(sys.argv)>2 else '/tmp/nba-sticky-headers'))
