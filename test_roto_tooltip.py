"""Real-data mouse, touch and keyboard coverage for the radar value panel."""
import json
import os
from pathlib import Path
import sys
from playwright.sync_api import sync_playwright


def run(origin, output):
    output.mkdir(parents=True, exist_ok=True)
    results=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path=os.environ.get('CHROMIUM_PATH','/usr/bin/chromium'), headless=True)
        for width in [1500,390]:
            touch=width==390
            ctx=browser.new_context(viewport={'width':width,'height':844 if touch else 1000},has_touch=touch,is_mobile=touch)
            page=ctx.new_page();errors=[];console_errors=[];external=[]
            page.on('pageerror',lambda e:errors.append(str(e)))
            page.on('console',lambda m:console_errors.append(m.text) if m.type=='error' else None)
            page.on('request',lambda r:external.append(r.url) if not r.url.startswith(origin+'/') else None)
            page.goto(origin+'/roto.html#players=1966,3195',wait_until='load')
            archive=page.evaluate('ROTO_DATA.period_key||"ls"')
            page.locator('#data-period').select_option(archive)
            tip=page.locator('#radar-tooltip')

            def near_node(key='PTS'):
                page.locator('#radar').scroll_into_view_if_needed()
                point=page.locator('#radar [data-series="base"] circle[data-metric="'+key+'"]')
                box=point.bounding_box();x=box['x']+box['width']/2+10;y=box['y']+box['height']/2
                if touch:page.touchscreen.tap(x,y)
                else:page.mouse.move(x,y)
                assert tip.is_visible()
                assert tip.get_attribute('data-metric')==key

            def focus_metric(key):
                page.locator('#radar [data-radar-metric="'+key+'"]').focus()
                assert tip.is_visible()
                assert tip.get_attribute('data-metric')==key

            expected=page.evaluate('()=>{const p=[ROTO_DATA.players["1966"],ROTO_DATA.players["3195"]];return {PTS:p.reduce((s,r)=>s+r.totals.PTS/r.gp,0),FG:100*p.reduce((s,r)=>s+r.shots.FGM/r.gp,0)/p.reduce((s,r)=>s+r.shots.FGA/r.gp,0)};}')
            near_node()
            page.keyboard.press('Escape');assert tip.is_hidden()
            near_node()
            assert tip.locator('[data-tooltip-team]').count()==2
            assert abs(float(tip.locator('[data-tooltip-team="base"]').get_attribute('data-value'))-expected['PTS']/2)<1e-10
            assert abs(float(tip.locator('[data-tooltip-team="base"]').get_attribute('data-total'))-expected['PTS'])<1e-10
            assert tip.locator('[data-tooltip-team="simulation"]').get_attribute('data-value')==tip.locator('[data-tooltip-team="base"]').get_attribute('data-value')
            assert '／人／場' in tip.inner_text() and '每人各 1 場合計' in tip.inner_text()
            assert '2/2 人有資料' in tip.inner_text()
            page.locator('#radar-plot').screenshot(path=str(output/f'overlap-values-{width}.png'))
            focus_metric('FG%')
            assert abs(float(tip.locator('[data-tooltip-team="base"]').get_attribute('data-value'))-expected['FG'])<1e-10
            assert '命中' in tip.inner_text() and '出手' in tip.inner_text()
            page.keyboard.press('Escape');assert tip.is_hidden()
            page.keyboard.press('Enter');assert tip.is_visible()
            page.locator('h1').click();assert tip.is_hidden()
            near_node()
            page.locator('#table-mode').select_option('perGame');assert tip.is_hidden()
            near_node()
            assert abs(float(tip.locator('[data-tooltip-team="base"]').get_attribute('data-value'))-expected['PTS']/2)<1e-10
            page.locator('#data-period').select_option('season');assert tip.is_hidden()
            focus_metric('PTS')
            current=page.evaluate('()=>{const d=ROTO_DATA.extra_periods.season,rows=[d.players["1966"],d.players["3195"]].filter(p=>p&&p.gp>0&&p.totals.PTS!==null);return {known:rows.length,value:rows.length?rows.reduce((s,p)=>s+p.totals.PTS/p.gp,0)/rows.length:null};}')
            current_value=tip.locator('[data-tooltip-team="base"]').get_attribute('data-value')
            if current['value'] is None:assert current_value==''
            else:assert abs(float(current_value)-current['value'])<1e-10
            assert str(current['known'])+'/2 人有資料' in tip.locator('[data-tooltip-team="base"]').inner_text()
            page.locator('#data-period').select_option(archive)
            missing=page.evaluate('Object.values(ROTO_DATA.players).find(p=>p.gp===null)')
            page.locator('#player-search').fill(missing['name'])
            page.locator('input[data-roto-pick="'+missing['id']+'"]').check()
            near_node()
            assert '2/3 人有資料 · 已知部分' in tip.locator('[data-tooltip-team="base"]').inner_text()
            assert abs(float(tip.locator('[data-tooltip-team="base"]').get_attribute('data-value'))-expected['PTS']/2)<1e-10
            page.locator('#roster-name').fill('重疊隊');page.locator('#save-roster').click()
            page.locator('#load-target').select_option('opponent');page.locator('#load-roster').click()
            near_node()
            assert tip.locator('[data-tooltip-team]').count()==3
            assert '3 組陣容' in tip.inner_text()
            values=tip.locator('[data-tooltip-team]').evaluate_all('(nodes)=>nodes.map(n=>n.dataset.value)')
            assert len(set(values))==1
            if touch:page.locator('#opponent-editor summary').click()
            page.locator('#opponent-name').fill('<img src=x onerror=alert(1)>');page.locator('#opponent-name').press('Tab')
            near_node()
            assert '<img src=x' in tip.inner_text() and tip.locator('img').count()==0
            bounds=tip.bounding_box()
            assert bounds['x']>=0 and bounds['x']+bounds['width']<=width+1
            page.locator('#radar-plot').screenshot(path=str(output/f'partial-multi-values-{width}.png'))
            page.locator('[data-opponent-layer="opponent"]').uncheck();near_node()
            assert tip.locator('[data-tooltip-team]').count()==2
            page.locator('#show-base').uncheck()
            focus_metric('PTS');assert tip.locator('[data-tooltip-team]').count()==1
            page.locator('#show-simulation').uncheck()
            page.locator('#radar [data-radar-metric="PTS"]').focus();assert tip.is_hidden()
            page.goto(origin+'/roto.html#players=4432639',wait_until='load');page.reload(wait_until='load')
            page.locator('#data-period').select_option(archive)
            focus_metric('FG%')
            assert tip.locator('[data-tooltip-team="base"]').get_attribute('data-value')==''
            assert '975／974' in tip.locator('[data-tooltip-team="base"]').inner_text()
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
            assert not errors and not console_errors and not external
            results.append(dict(width=width,touch=touch,nearby_node_values=True,overlap_lists_all_visible_teams=True,weighted_shooting=True,units_and_known_coverage=True,keyboard_and_escape=True,outside_dismiss=True,table_unit_independent=True,period_change_clears_stale_values=True,partial_unknown_not_zero=True,hidden_series_excluded=True,unresolved_shots_unknown=True,names_safe_as_text=True,no_overflow=True,js_errors=errors,csp_errors=console_errors,external_requests=external))
            ctx.close()
        browser.close()
    (output/'browser-results.json').write_text(json.dumps(results,indent=2))
    print(json.dumps(results))


if __name__=='__main__':run(sys.argv[1].rstrip('/'),Path(sys.argv[2]))
