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
            assert page.locator('#mode').input_value()=='totals'
            assert page.locator('#table-mode').input_value()=='totals'
            assert page.title()=='九項配隊分析 · FantasyOrgCat'
            assert '歷史實績' in page.locator('#season-context').inner_text()
            assert page.locator('.format-guides summary').count()==2
            page.locator('.format-guides summary').last.click()
            assert 'FGM／FGA／FTM／FTA' in page.locator('.format-guides details').last.inner_text()
            assert '尚未提供聯盟名次' in page.locator('.format-guides details').last.inner_text()
            page.locator('.format-guides summary').last.click()
            radar_positions=page.locator('#radar [data-series="base"] circle').evaluate_all('(nodes)=>nodes.map(n=>[n.dataset.metric,n.getAttribute("cx"),n.getAttribute("cy")])')
            page.locator('#compare-efficiency').click()
            assert page.locator('#mode').input_value()=='perGame'
            assert page.locator('#table-mode').input_value()=='perGame'
            assert page.locator('#radar [data-series="base"] circle').evaluate_all('(nodes)=>nodes.map(n=>[n.dataset.metric,n.getAttribute("cx"),n.getAttribute("cy")])')==radar_positions
            assert page.locator('#base-count').inner_text()=='2 人'
            assert 'Noto Sans' in page.locator('body').evaluate('(e)=>getComputedStyle(e).fontFamily')
            assert float(page.locator('.category-table td small').first.evaluate('(e)=>getComputedStyle(e).fontSize').removesuffix('px'))>=13
            assert page.locator('#data-warning').is_visible()
            assert page.evaluate('ROTO_DATA.data_ready')
            assert page.evaluate('ROTO_DATA.reference.size')==582
            assert page.evaluate('ROTO_DATA.source')=='BoxScore Lab'
            assert '二手' in page.locator('#data-warning').inner_text()
            for metric in ['FG%','FT%']:
                actual=float(page.locator('tr[data-metric="'+metric+'"] td[data-team="base"]').get_attribute('data-value'))
                expected=page.evaluate('(metric)=>RotoCore.aggregate(["1966","3195"],ROTO_DATA,"perGame").cells[metric].value',metric)
                assert abs(actual-expected)<1e-10
            assert page.locator('#radar [data-series="base"] circle').count()==9
            assert page.locator('#radar polygon[fill-opacity]').count()>=1
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
                page.locator('#player-search').fill(name);page.locator('#roto-player-table tbody input[data-roto-pick]').first.check()
            assert page.locator('#incoming-list .roster-item').count()==2
            assert page.locator('#base-list .roster-item').evaluate_all('(nodes)=>nodes.map(n=>n.dataset.playerId)')==original
            assert page.locator('#radar [data-series]').count()==3
            assert page.locator('#radar [data-series="simulation"] circle').count()==9
            assert page.evaluate('JSON.stringify(ROTO_DATA.benchmark)')==baseline
            radar_positions=page.locator('#radar [data-series]').evaluate_all('(nodes)=>nodes.map(n=>n.innerHTML)')
            page.locator('#table-mode').select_option('totals')
            assert page.locator('#radar [data-series]').evaluate_all('(nodes)=>nodes.map(n=>n.innerHTML)')==radar_positions
            assert page.locator('#mode').input_value()=='totals'
            values=page.locator('tr[data-metric="PTS"] td').evaluate_all('(nodes)=>nodes.map(n=>n.dataset.value)')
            assert all(v and float(v).is_integer() for v in values[:3])
            assert abs(float(values[2])-float(values[0])-float(values[3]))<1e-6
            page.locator('#save-target').select_option('simulation');page.locator('#roster-name').fill('換人方案')
            page.locator('#save-roster').click();assert len(page.evaluate('JSON.parse(localStorage.getItem(RotoCore.storageKey)).rosters'))==2
            page.locator('#mode').select_option('perGame');assert page.locator('#table-mode').input_value()=='perGame'
            page.locator('#mode').select_option('totals')
            page.locator('#reset-simulation').click()
            assert page.locator('#incoming-list .roster-item').count()==0
            assert page.locator('td[data-delta="PTS"]').get_attribute('data-value')=='0'
            assert page.locator('#base-list .roster-item').evaluate_all('(nodes)=>nodes.map(n=>n.dataset.playerId)')==original
            # Named multi-opponent editing, overlays, old-save import and auto persistence.
            if width==390:page.locator('#opponent-editor summary').click()
            first_opponent=page.locator('#active-opponent').input_value()
            for name,query in [('台北狐狸','Curry'),('<img src=x onerror=alert(1)>南區隊','Jokic')]:
                page.locator('#add-opponent').click()
                assert page.locator('#add-target').input_value()=='opponent'
                page.locator('#opponent-name').fill(name);page.locator('#opponent-name').press('Tab')
                page.locator('#add-target').select_option('opponent');page.locator('#player-search').fill(query)
                page.locator('#roto-player-table tbody input[data-roto-pick]').first.check()
            third=page.locator('#active-opponent').input_value()
            assert page.locator('#active-opponent option').count()==3
            assert page.locator('#radar [data-series]').count()==5
            assert page.locator('#metrics-head th').count()==7
            assert '台北狐狸' in page.locator('#legend').inner_text()
            assert page.locator('#legend img').count()==0
            assert page.locator('#base-list .roster-item').evaluate_all('(nodes)=>nodes.map(n=>n.dataset.playerId)')==original
            opponent_storage=page.evaluate('JSON.parse(localStorage.getItem(RotoCore.opponentsKey))')
            assert len(opponent_storage['rosters'])==3
            assert opponent_storage['rosters'][1]['name']=='台北狐狸'
            assert opponent_storage['rosters'][2]['name'].startswith('<img')
            page.locator('[data-opponent-layer="'+third+'"]').uncheck()
            assert page.locator('#radar [data-series]').count()==4
            assert page.locator('#metrics-head th').count()==6
            page.locator('#show-opponent').uncheck()
            assert page.locator('#radar [data-series]').count()==2
            assert page.locator('#metrics-head th').count()==4
            page.locator('#show-opponent').check()
            page.reload(wait_until='load')
            assert page.locator('#active-opponent option').count()==3
            assert page.locator('#saved-rosters option').count()==3
            assert page.evaluate('JSON.parse(localStorage.getItem(RotoCore.opponentsKey))')==opponent_storage
            if width==390:page.locator('#opponent-editor summary').click()
            page.locator('#active-opponent').select_option(first_opponent)
            assert page.locator('#opponent-list .roster-item').count()==2
            page.locator('#saved-rosters').select_option(saved['rosters'][0]['id'])
            page.locator('#load-target').select_option('new-opponent');page.locator('#load-roster').click()
            assert page.locator('#active-opponent option').count()==4
            assert page.locator('#opponent-name').input_value()=='我的測試陣容'
            assert page.locator('#opponent-list .roster-item').count()==2
            page.locator('#delete-opponent').click()
            assert page.locator('#active-opponent option').count()==3
            page.locator('#load-target').select_option('base')
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
            page.locator('#active-opponent').select_option(third)
            page.locator('#opponent-name').fill('南區白鷺');page.locator('#opponent-name').press('Tab')
            page.evaluate('scrollTo({top:document.querySelector(".radar-card").getBoundingClientRect().top+scrollY-10,behavior:"instant"})')
            page.screenshot(path=str(output/f'roto-multi-{width}.png'))
            if width==390:
                page.evaluate('scrollTo({top:document.querySelector(".differences-card").getBoundingClientRect().top+scrollY-10,behavior:"instant"})')
                page.screenshot(path=str(output/'roto-multi-table-390.png'))
                scroller=page.locator('.category-table');cell=page.locator('#metrics-body tr:first-child th')
                before=cell.bounding_box()['x'];scroller.evaluate('(e)=>{e.scrollLeft=e.scrollWidth;}')
                assert scroller.evaluate('(e)=>e.scrollLeft>0')
                assert abs(cell.bounding_box()['x']-before)<2
                page.screenshot(path=str(output/'roto-multi-table-right-390.png'))
            # Select and deselect in the original-style data table without leaving the row.
            page.locator('#add-target').select_option('base');page.locator('#player-search').fill('LeBron')
            pick=page.locator('#roto-player-table tbody input[data-roto-pick="1966"]')
            assert pick.is_checked();pick.focus();pick.press('Space');assert page.locator('#base-count').inner_text()=='1 人'
            assert pick.evaluate('(e)=>e===document.activeElement')
            assert not pick.is_checked();pick.check();assert page.locator('#base-count').inner_text()=='2 人'
            assert page.locator('#roto-player-table_wrapper .dt-scroll-head th').count()==14
            # Search resets pagination; the page-scroll header and left selection stay accessible.
            page.locator('#player-search').fill('');page.locator('#roto-player-table_wrapper select').select_option('10')
            page.locator('#roto-player-table_wrapper button.next').click()
            page.locator('#player-search').fill('Jokic');assert page.locator('#roto-player-table tbody input[data-roto-pick="3112335"]').is_visible()
            page.locator('#player-search').fill('');page.locator('#roto-player-table_wrapper select').select_option('25')
            head=page.locator('#roto-player-table_wrapper .dt-scroll-head');body=page.locator('#roto-player-table_wrapper .dt-scroll-body')
            page.evaluate('scrollTo({top:document.querySelector("#roto-player-table_wrapper .dt-scroll-head").getBoundingClientRect().top+scrollY-50,behavior:"instant"})')
            page.mouse.move(width/2,height/2);page.mouse.wheel(0,350);page.wait_for_timeout(300)
            controls=page.locator('.picker-controls').bounding_box();box=head.bounding_box()
            assert abs(box['y']-(controls['y']+controls['height']))<2
            assert body.evaluate('(e)=>e.scrollTop===0&&e.scrollHeight<=e.clientHeight+1')
            cell=page.locator('#roto-player-table tbody tr:first-child td:first-child');left=cell.bounding_box()['x']
            body.evaluate('(e)=>{e.scrollLeft=e.scrollWidth;e.dispatchEvent(new Event("scroll"));}')
            assert abs(cell.bounding_box()['x']-left)<2
            page.screenshot(path=str(output/f'roto-picker-right-{width}.png'))
            body.evaluate('(e)=>{e.scrollLeft=0;e.dispatchEvent(new Event("scroll"));}')
            page.locator('#player-search').fill('LeBron')
            page.screenshot(path=str(output/f'roto-picker-{width}.png'))
            # A player missing historical data keeps the known team subtotal/graph usable.
            missing=page.evaluate('Object.values(ROTO_DATA.players).find(p=>p.gp===null).id')
            missing_name=page.evaluate('(id)=>ROTO_DATA.players[id].name',missing)
            page.locator('#player-search').fill(missing_name)
            missing_pick=page.locator('#roto-player-table tbody input[data-roto-pick="'+missing+'"]');missing_pick.check()
            cell=page.locator('tr[data-metric="PTS"] td[data-team="base"]')
            assert cell.get_attribute('data-value') and '已知小計 · 2/3 覆蓋' in cell.inner_text()
            assert page.locator('#radar [data-series="base"] circle').count()==9
            assert page.locator('#radar [data-series="base"] polygon[fill-opacity]').count()==0
            assert page.locator('td[data-delta="PTS"]').get_attribute('data-value')==''
            missing_pick.uncheck();assert page.locator('#base-count').inner_text()=='2 人'
            # Available choices can change while keeping selection; preseason stays unknown.
            page.locator('#data-period').select_option('season');assert '2026-27' in page.locator('#period-label').inner_text()
            assert page.locator('#base-count').inner_text()=='2 人'
            assert page.locator('tr[data-metric="PTS"] td[data-team="base"]').get_attribute('data-value')==''
            page.locator('#data-period').select_option('ls');assert page.locator('tr[data-metric="PTS"] td[data-team="base"]').get_attribute('data-value')
            zero=page.evaluate('Object.values(ROTO_DATA.players).find(p=>p.gp&&p.shots.FTA===0)')
            page.locator('#player-search').fill(zero['name'])
            assert '—' in page.locator('#roto-player-table tbody tr:first-child td').nth(12).inner_text()
            assert page.evaluate('Array.from(document.querySelectorAll(".search-controls input,.search-controls select,.save-controls input,.save-controls select,.load-controls select")).every(e=>{const a=e.getBoundingClientRect(),b=e.parentElement.getBoundingClientRect();return a.left>=b.left-1&&a.right<=b.right+1;})')
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
            # A declared conflict remains unknown even though the dataset is publishable.
            page.goto(origin+'/roto.html#players=4432639',wait_until='load');page.reload(wait_until='load')
            cell=page.locator('tr[data-metric="FG%"] td[data-team="base"]')
            assert cell.get_attribute('data-value')=='' and '975／974' in cell.inner_text()
            assert page.locator('#radar [data-series="base"] circle').count()==8
            assert page.locator('#radar [data-series="base"] polygon[fill-opacity]').count()==0
            page.locator('#roster-name').fill('<img src=x onerror=alert(1)>');page.locator('#save-roster').click()
            assert page.locator('#saved-rosters img').count()==0
            assert page.locator('#saved-rosters option').count()==4
            assert not errors,errors;assert not failed,failed;assert not external,external;assert not console_errors,console_errors
            results.append(dict(width=width,real_checked_in_data=True,real_weighted_denominators=True,declared_conflicts_preserved=True,
                                release_data_complete=True,default_three_series=True,readable_sans_serif_text=True,full_stat_table_in_place_toggle=True,checkbox_keyboard_focus_preserved=True,picker_page_scroll_header=True,picker_horizontal_selection_sticky=True,search_resets_paging=True,unknown_member_known_subtotal=True,season_switch_preserves_roster=True,nearby_total_mode_switch=True,named_multiple_opponents=True,old_save_import_as_new_opponent=True,opponent_auto_save_reload=True,selectable_overlays=True,fixed_benchmark=True,multi_replace_base_unchanged=True,
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
        # Corrupt opponent storage is not overwritten; edits stay in memory.
        ctx=browser.new_context(viewport={'width':390,'height':844})
        ctx.add_init_script("localStorage.setItem('fantasyorgcat:roto:opponents:v1','{bad');")
        page=ctx.new_page();page.goto(origin+'/roto.html#players=1966',wait_until='load')
        page.locator('#opponent-editor summary').click();page.locator('#add-opponent').click()
        assert page.locator('#active-opponent option').count()==2
        assert page.evaluate('localStorage.getItem(RotoCore.opponentsKey)')=='{bad'
        assert '不會覆寫' in page.locator('#opponents-status').inner_text();ctx.close()
        # Removing every opponent restores an empty set, then can add again.
        ctx=browser.new_context(viewport={'width':390,'height':844})
        page=ctx.new_page();page.goto(origin+'/roto.html#players=1966',wait_until='load')
        page.locator('#opponent-editor summary').click();page.locator('#delete-opponent').click()
        assert page.locator('#active-opponent option').count()==0
        page.reload(wait_until='load');assert page.locator('#active-opponent option').count()==0
        page.locator('#opponent-editor summary').click();page.locator('#add-opponent').click()
        assert page.locator('#active-opponent option').count()==1;ctx.close()
        # A quota failure preserves previously stored opponents and all legacy saves.
        ctx=browser.new_context(viewport={'width':390,'height':844})
        ctx.add_init_script("localStorage.setItem('fantasyorgcat:roto:opponents:v1',JSON.stringify({version:1,rosters:[{id:'opponent',name:'原保存',players:['1966'],savedAt:''}]}));localStorage.setItem('fantasyorgcat:roto:rosters:v1',JSON.stringify({version:1,rosters:[{id:'old',name:'舊陣容',players:['3195'],savedAt:''}]}));Storage.prototype.setItem=function(){throw new DOMException('Storage full','QuotaExceededError');};")
        page=ctx.new_page();page.goto(origin+'/roto.html#players=1966',wait_until='load')
        before=page.evaluate('[localStorage.getItem(RotoCore.opponentsKey),localStorage.getItem(RotoCore.storageKey)]')
        page.locator('#opponent-editor summary').click();page.locator('#add-opponent').click()
        assert '自動保存失敗' in page.locator('#opponents-status').inner_text()
        assert page.locator('#active-opponent option').count()==2
        assert page.evaluate('[localStorage.getItem(RotoCore.opponentsKey),localStorage.getItem(RotoCore.storageKey)]')==before
        ctx.close();results.append(dict(corrupt_opponents_preserved=True,delete_all_restore_and_readd=True,quota_preserves_prior_storage=True))
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
        # UI TEST ONLY: the existing producer's first current-season dataset becomes default.
        from test_roto_package import RotoPackage
        from roto_package import build_package
        catalog,snapshot=RotoPackage().sample();snapshot['fixture']=True
        future=build_package(catalog,snapshot)
        ctx=browser.new_context(viewport={'width':390,'height':844})
        ctx.route('**/roto_data.js',lambda route:route.fulfill(status=200,content_type='text/javascript',body='window.ROTO_DATA = '+json.dumps(future)+';'))
        page=ctx.new_page();page.goto(origin+'/roto.html#players=1,2',wait_until='load')
        assert page.locator('#data-period').input_value()=='season'
        assert '2026-27' in page.locator('#period-label').inner_text()
        assert '正在使用本季實績' in page.locator('#season-context').inner_text()
        assert 'UI TEST ONLY' in page.locator('#data-warning').inner_text()
        assert page.locator('tr[data-metric="PTS"] td[data-team="base"]').get_attribute('data-value')=='8'
        page.locator('#player-search').fill('Test 1')
        assert page.locator('#roto-player-table tbody input[data-roto-pick="1"]').is_checked()
        page.locator('#roto-player-table tbody input[data-roto-pick="1"]').uncheck()
        assert page.locator('tr[data-metric="PTS"] td[data-team="base"]').get_attribute('data-value')=='6'
        ctx.close();results.append(dict(synthetic_current_season_auto_default=True,production_data_unchanged=True))
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
        # Radar always weights each player's per-game shots, even with a totals table.
        circle=page.locator('#radar [data-series="base"] circle[data-metric="FG%"]')
        radius=((float(circle.get_attribute('cx'))-230)**2+(float(circle.get_attribute('cy'))-184)**2)**.5
        per_game_fg=100*(1/10+9/20)/(2/10+10/20)
        assert abs(radius/123*100-(50+15*(per_game_fg-60)/20))<1e-10
        radar_positions=page.locator('#radar [data-series="base"]').inner_html()
        page.locator('#table-mode').select_option('perGame')
        assert page.locator('#radar [data-series="base"]').inner_html()==radar_positions
        assert abs(float(page.locator('tr[data-metric="FG%"] td[data-team="base"]').get_attribute('data-value'))-per_game_fg)<1e-10
        page.locator('#table-mode').select_option('totals')
        assert page.locator('#radar [data-series="base"] circle').count()==9
        assert page.locator('#radar polygon[fill-opacity]').count()>=1
        page.screenshot(path=str(output/'roto-synthetic-math-390.png'))
        ctx.close();results.append(dict(synthetic_math_only=True,production_data_unchanged=True,weighted_FG_pct=value,nine_axis_rendering=True,radar_always_per_game=True,weighted_radar_FG_pct=per_game_fg))
        browser.close()
    (output/'browser-results.json').write_text(json.dumps(results,indent=2))
    print(json.dumps(results))


if __name__=='__main__':run(sys.argv[1].rstrip('/'),Path(sys.argv[2]))
