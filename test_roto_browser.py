"""Real checked-in data UI QA; separately identifies synthetic math fixtures."""
import json
import os
from pathlib import Path
import sys
from playwright.sync_api import sync_playwright


def run(origin,output):
    output.mkdir(parents=True,exist_ok=True)
    results=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path=os.environ.get('CHROMIUM_PATH','/usr/bin/chromium'),headless=True)
        for width,height in [(1500,1000),(390,844)]:
            ctx=browser.new_context(viewport={'width':width,'height':height})
            page=ctx.new_page();errors=[];failed=[];external=[];console_errors=[]
            page.on('pageerror',lambda e:errors.append(str(e)))
            page.on('requestfailed',lambda r:failed.append(r.url))
            page.on('request',lambda r:external.append(r.url) if not r.url.startswith(origin+'/') else None)
            page.on('console',lambda m:console_errors.append(m.text) if m.type=='error' else None)
            assert page.goto(origin+'/roto.html#players=1966,3195',wait_until='load').status==200
            assert page.locator('#base-count').inner_text()=='2 人'
            assert page.locator('#data-warning').is_visible()
            assert page.locator('tr[data-metric="FG%"] td[data-team="base"]').get_attribute('data-value')==''
            assert page.locator('tr[data-metric="FT%"] td[data-team="base"]').get_attribute('data-value')==''
            assert page.locator('#radar [data-metric="FG%"],#radar [data-metric="FT%"],#radar polygon[fill-opacity]').count()==0
            baseline=page.evaluate('JSON.stringify(ROTO_DATA.benchmark)')
            original=page.locator('#base-list .roster-item').evaluate_all('(nodes)=>nodes.map(n=>n.dataset.playerId)')
            if width==390:
                assert not page.locator('#base-editor').evaluate('(e)=>e.open')
                page.locator('#base-editor summary').click()
            assert page.locator('#base-list .roster-item').count()==2
            page.locator('#save-target').select_option('base');page.locator('#roster-name').fill('我的測試陣容')
            page.locator('#save-roster').click();assert '已保存' in page.locator('#status').inner_text()
            saved=page.evaluate('JSON.parse(localStorage.getItem(RotoCore.storageKey))');assert saved['rosters'][0]['players']==['1966','3195']
            # Load the same team as an opponent and simulate a multi-player replacement.
            page.locator('#load-target').select_option('opponent');page.locator('#load-roster').click()
            if width==390:page.locator('#simulation-editor summary').click()
            for pid in ['1966','3195']:page.locator('[data-outgoing="'+pid+'"]').check()
            page.locator('#add-target').select_option('incoming')
            for name in ['Jokic','Curry']:
                page.locator('#player-search').fill(name);page.locator('#search-results button').first.click()
            assert page.locator('#incoming-list .roster-item').count()==2
            assert page.locator('#base-list .roster-item').evaluate_all('(nodes)=>nodes.map(n=>n.dataset.playerId)')==original
            assert page.locator('#radar [data-series]').count()==3
            assert page.locator('#radar [data-series="simulation"] circle').count()==7
            assert page.evaluate('JSON.stringify(ROTO_DATA.benchmark)')==baseline
            page.locator('#mode').select_option('totals')
            values=page.locator('tr[data-metric="PTS"] td').evaluate_all('(nodes)=>nodes.map(n=>n.dataset.value)')
            assert all(v and float(v).is_integer() for v in values[:3])
            assert abs(float(values[2])-float(values[0])-float(values[3]))<1e-6
            page.locator('#save-target').select_option('simulation');page.locator('#roster-name').fill('換人方案')
            page.locator('#save-roster').click();assert len(page.evaluate('JSON.parse(localStorage.getItem(RotoCore.storageKey)).rosters'))==2
            page.locator('#reset-simulation').click()
            assert page.locator('#incoming-list .roster-item').count()==0
            assert page.locator('td[data-delta="PTS"]').get_attribute('data-value')=='0'
            assert page.locator('#base-list .roster-item').evaluate_all('(nodes)=>nodes.map(n=>n.dataset.playerId)')==original
            page.locator('#player-search').fill('Shaq');page.locator('#add-target').select_option('base')
            # Missing-season player remains unknown, not fabricated zero.
            missing=page.evaluate('Object.values(ROTO_DATA.players).find(p=>p.gp===null).id')
            page.goto(origin+'/roto.html#players='+missing,wait_until='load');page.reload(wait_until='load')
            assert page.locator('tr[data-metric="PTS"] td[data-team="base"]').get_attribute('data-value')==''
            assert '0/1 覆蓋' in page.locator('tr[data-metric="PTS"] td[data-team="base"]').inner_text()
            assert page.locator('#saved-rosters option').count()==3
            page.locator('#saved-rosters').select_option(saved['rosters'][0]['id']);page.locator('#load-roster').click()
            assert page.locator('#base-count').inner_text()=='2 人'
            # Responsive graph and all nine rows are readable without whole-page horizontal overflow.
            assert page.locator('#metrics-body tr').count()==9
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
            page.evaluate('scrollTo({top:document.querySelector(".radar-card").getBoundingClientRect().top+scrollY-10,behavior:"instant"})')
            page.screenshot(path=str(output/f'roto-real-{width}.png'))
            if width==390:
                page.evaluate('scrollTo({top:document.querySelector(".differences-card").getBoundingClientRect().top+scrollY-10,behavior:"instant"})')
                page.screenshot(path=str(output/'roto-real-table-390.png'))
                page.evaluate('scrollTo({top:0,behavior:"instant"})');page.screenshot(path=str(output/'roto-real-top-390.png'))
            page.locator('#roster-name').fill('<img src=x onerror=alert(1)>');page.locator('#save-roster').click()
            assert page.locator('#saved-rosters img').count()==0
            assert page.locator('#saved-rosters option').count()==4
            assert not errors,errors;assert not failed,failed;assert not external,external;assert not console_errors,console_errors
            results.append(dict(width=width,real_checked_in_data=True,denominators_missing_and_not_filled=True,
                                release_data_complete=False,three_series_max=True,fixed_benchmark=True,multi_replace_base_unchanged=True,
                                reset_restores_base=True,local_named_save_reload=True,unknown_player_coverage=True,
                                no_page_overflow=True,js_errors=errors,failed_requests=failed,external_requests=external,csp_errors=console_errors))
            ctx.close()
        # Storage-denied mode is usable and does not touch legacy roster data.
        ctx=browser.new_context(viewport={'width':390,'height':844})
        ctx.add_init_script("for(const method of ['getItem','setItem'])Storage.prototype[method]=function(){throw Error('Storage blocked');};")
        page=ctx.new_page();page.goto(origin+'/roto.html#players=1966',wait_until='load')
        assert page.locator('#storage-warning').is_visible();page.locator('#roster-name').fill('Blocked');page.locator('#save-roster').click()
        assert page.locator('#base-count').inner_text()=='1 人';ctx.close()
        # Malformed/versioned storage is retained rather than silently overwritten.
        ctx=browser.new_context(viewport={'width':390,'height':844})
        ctx.add_init_script("localStorage.setItem('fantasyorgcat:roto:rosters:v1','{bad');")
        page=ctx.new_page();page.goto(origin+'/roto.html#players=1966',wait_until='load')
        assert page.locator('#save-roster').is_disabled()
        assert page.evaluate('localStorage.getItem(RotoCore.storageKey)')=='{bad'
        ctx.close()
        # Existing checkbox entry opens a new same-origin ROTO page with canonical ESPN IDs.
        ctx=browser.new_context(viewport={'width':390,'height':844});page=ctx.new_page()
        page.goto(origin+'/index.html',wait_until='load',timeout=60000);page.wait_for_function('Object.keys(tables).length===5')
        for pid in ['1966','3195']:
            page.evaluate('(id)=>tables[activeWeek].column(0).search(playerCatalog[id].name).draw()',pid)
            page.locator('.tabcontent:visible input[data-player-id="'+pid+'"]').check()
        assert page.locator('#open-roto').get_attribute('href')=='roto.html#players=1966,3195'
        with page.expect_popup() as popup:page.locator('#open-roto').click()
        roto=popup.value;roto.wait_for_load_state('load');assert roto.locator('#base-count').inner_text()=='2 人'
        ctx.close();results.append(dict(homepage_checkbox_entry=True,same_origin_new_page=True,canonical_ids=['1966','3195']))
        # UI TEST ONLY: complete denominators verify rendering/math, never production coverage.
        ctx=browser.new_context(viewport={'width':390,'height':844})
        def player(pid,gp,m,a,ftm,fta,to):
            return dict(id=pid,name='UI TEST ONLY '+pid,team='TEST',gp=gp,minutes=20,
                totals={'PTS':gp*10,'REB':gp*2,'AST':gp,'3PM':gp,'STL':gp,'BLK':0,'TO':gp*to},shots={'FGM':m,'FGA':a,'FTM':ftm,'FTA':fta})
        fixture=dict(version=1,fixture=True,season='UI TEST ONLY',generated_at='UI TEST ONLY',source='UI TEST ONLY',data_ready=False,
            reference=dict(size=2,expected=2,shooting_complete=2,id='UI TEST ONLY'),
            players={'1':player('1',10,1,2,2,4,1),'2':player('2',20,9,10,4,4,3)},
            benchmark={mode:{metric:dict(mean=60 if metric.endswith('%') else 2,sd=20 if metric.endswith('%') else 2) for metric in ['PTS','REB','AST','3PM','STL','BLK','FG%','FT%','TO']} for mode in ['perGame','totals']})
        ctx.route('**/roto_data.js',lambda route:route.fulfill(status=200,content_type='text/javascript',body='window.ROTO_DATA = '+json.dumps(fixture)+';'))
        page=ctx.new_page();page.goto(origin+'/roto.html#players=1,2',wait_until='load')
        assert 'UI TEST ONLY' in page.locator('#data-warning').inner_text()
        page.locator('#mode').select_option('totals')
        value=float(page.locator('tr[data-metric="FG%"] td[data-team="base"]').get_attribute('data-value'))
        assert abs(value-100*10/12)<1e-10
        assert page.locator('#radar [data-series="base"] circle').count()==9
        assert page.locator('#radar polygon[fill-opacity]').count()>=1
        page.screenshot(path=str(output/'roto-synthetic-math-390.png'))
        ctx.close();results.append(dict(synthetic_math_only=True,production_data_unchanged=True,weighted_FG_pct=value,nine_axis_rendering=True))
        browser.close()
    (output/'browser-results.json').write_text(json.dumps(results,indent=2))
    print(json.dumps(results))


if __name__=='__main__':run(sys.argv[1].rstrip('/'),Path(sys.argv[2]))
