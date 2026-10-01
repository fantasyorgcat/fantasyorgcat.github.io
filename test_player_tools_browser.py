import sys,json,tempfile
from pathlib import Path
sys.path.insert(0,str(Path('.test-deps').resolve()))
from playwright.sync_api import sync_playwright
KEY='fantasy-nba:hotmilk300/Fantasy-NBA-Streaming-Assistant:roster:v1'
CHROME=r'C:\Users\USER\AppData\Local\ms-playwright\chromium-1228\chrome-win64\chrome.exe'

def run(url):
    errors=[];external=[]
    def ready(page):
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.on('request',lambda r:external.append(r.url) if not r.url.startswith(url.split('/fantasy_')[0].rstrip('/')+'/') and not r.url.startswith('blob:') else None)
        page.goto(url,wait_until='load',timeout=60000)
        page.wait_for_function('Object.keys(tables).length===4 && document.querySelector("#comparison-head tr")',timeout=30000)
    def upload(page,data):
        page.locator('#import-roster').set_input_files(dict(name='backup.json',mimeType='application/json',buffer=json.dumps(data).encode()))
    with tempfile.TemporaryDirectory(prefix='nba-tools-',dir=str(Path('..').resolve())) as tmp,sync_playwright() as p:
        profile1=str(Path(tmp)/'profile1');profile2=str(Path(tmp)/'profile2')
        c=p.chromium.launch_persistent_context(profile1,executable_path=CHROME,headless=True,viewport={'width':1500,'height':1000});page=c.pages[0];ready(page)
        picks=page.locator('#playerTableW1 tbody input[data-pick="compare"]');a=picks.nth(0).get_attribute('data-player-id');b=picks.nth(1).get_attribute('data-player-id')
        picks.nth(0).focus();picks.nth(0).press('Space');picks.nth(1).check()
        assert page.locator('#comparison-body tr').count()==2
        assert page.evaluate('Boolean(document.querySelector("#comparison-panel").compareDocumentPosition(document.querySelector("#Week1 .player-section")) & Node.DOCUMENT_POSITION_FOLLOWING)')
        page.locator(f'#Week1 input[data-pick="roster"][data-player-id="{a}"]').check()
        assert page.locator('#show-roster').inner_text().endswith('（1）')
        page.locator('#comparison-mode').select_option('tot');page.locator('#comparison-head [data-sort="PTS"]').click()
        values=[float(v) for v in page.locator('#comparison-body tr td:nth-child(4)').evaluate_all('(nodes)=>nodes.map(n=>n.dataset.value)').copy() if v]
        assert values==sorted(values,reverse=True)
        page.locator('#comparison-period').select_option('l7');assert page.locator('#comparison-body td:nth-child(4)').first.inner_text()=='—'
        page.locator('#comparison-period').select_option('ls')
        page.locator('.tablinks').nth(3).click();page.locator('#teamTableW4 .team-row').first.click();page.locator('#show-all-players').click()
        assert page.locator('#comparison-body tr').count()==2
        page.locator('#season-week').select_option('24')
        page.evaluate('tables.WSeason.search(playerCatalog['+json.dumps(a)+'].name).draw()')
        assert page.locator(f'#WeekSeason input[data-pick="compare"][data-player-id="{a}"]').is_checked()
        assert page.locator(f'#WeekSeason input[data-pick="roster"][data-player-id="{a}"]').is_checked()
        page.locator('#show-all-players').click();assert page.locator('#comparison-body tr').count()==2
        page.locator('#comparison-body tr button').first.click();assert page.locator('#comparison-body tr').count()==1
        page.locator('#clear-comparison').click();assert not page.locator('#comparison-panel').is_visible()
        page.reload(wait_until='load');page.wait_for_function('document.querySelector("#show-roster").textContent.endsWith("（1）")')
        page.locator('#show-roster').click();assert page.locator('#roster-list .roster-member').count()==1
        with page.expect_download() as download:page.locator('#export-roster').click()
        file=Path('..')/'roster-test-backup.json';download.value.save_as(str(file.resolve()))
        backup=json.loads(file.read_text(encoding='utf-8'));assert backup['schemaVersion']==1 and backup['players'][0]['id']==a
        page.once('dialog',lambda d:d.dismiss());page.locator('#clear-roster').click();assert page.locator('#roster-list .roster-member').count()==1
        page.once('dialog',lambda d:d.accept());page.locator('#clear-roster').click();assert page.locator('#roster-list .roster-member').count()==0
        page.once('dialog',lambda d:d.accept());upload(page,backup);page.wait_for_function('document.querySelector("#roster-list .roster-member")')
        page.evaluate('(key)=>{localStorage.setItem(key,"{broken");window.dispatchEvent(new StorageEvent("storage",{key,newValue:"{broken"}));}',KEY)
        assert page.locator('#roster-list .roster-member').count()==1
        assert '保留' in page.locator('#roster-status').inner_text()
        page.once('dialog',lambda d:d.accept());page.locator('#reset-roster-storage').click()
        for bad in [dict(backup,schemaVersion=2),dict(backup,extra='x'),dict(backup,players={}),dict(backup,players=backup['players']*2),dict(backup,players=[dict(id='javascript:alert(1)',name='X')]),dict(backup,players=[dict(id=a,name='X')]*101)]:
            upload(page,bad);page.wait_for_function('document.querySelector("#roster-status").textContent.startsWith("無法匯入")')
            assert page.locator('#roster-list .roster-member').count()==1
        page.locator('#import-roster').set_input_files(dict(name='big.json',mimeType='application/json',buffer=b' '*32769));assert page.locator('#roster-list .roster-member').count()==1
        c.close()
        c=p.chromium.launch_persistent_context(profile2,executable_path=CHROME,headless=True);page2=c.pages[0];ready(page2);assert page2.locator('#show-roster').inner_text().endswith('（0）');c.close()
        c=p.chromium.launch_persistent_context(profile1,executable_path=CHROME,headless=True);page=c.pages[0];ready(page);assert page.locator('#show-roster').inner_text().endswith('（1）')
        page.evaluate('(key)=>localStorage.setItem(key,JSON.stringify({version:1,season:"2025-26",players:[{id:'+json.dumps(a)+',name:"Previous team/name"},{id:"999999999999",name:"<img src=x onerror=alert(1)>"}]}))',KEY)
        page.reload(wait_until='load');page.wait_for_function('document.querySelector("#show-roster").textContent.endsWith("（2）")');page.locator('#show-roster').click()
        assert '2025-26' in page.locator('#roster-season-note').inner_text()
        assert '未匹配球員 ID 999999999999' in page.locator('#roster-list').inner_text()
        assert page.locator('#roster-list img').count()==0
        actual=page.evaluate('playerCatalog['+json.dumps(a)+'].name');assert actual in page.locator('#roster-list').inner_text()
        page.once('dialog',lambda d:d.accept())
        upload(page,dict(schemaVersion=1,season='2025-26',players=[dict(id=a,name='Untrusted same ID'),dict(id='999999999999',name='<img src=x onerror=alert(1)>')]))
        page.wait_for_function('document.querySelector("#roster-status").textContent.startsWith("已匯入")')
        assert '未匹配 1' in page.locator('#roster-status').inner_text()
        assert actual in page.locator('#roster-list').inner_text() and page.locator('#roster-list img').count()==0
        page.evaluate('(key)=>localStorage.setItem(key,"{broken")',KEY);page.reload(wait_until='load');page.wait_for_function('document.querySelector("#reset-roster-storage").hidden===false')
        assert page.evaluate('(key)=>localStorage.getItem(key)',KEY)=='{broken'
        page.locator('#show-roster').click();page.once('dialog',lambda d:d.accept());page.locator('#reset-roster-storage').click();assert page.locator('#reset-roster-storage').is_hidden();c.close()
        browser=p.chromium.launch(executable_path=CHROME,headless=True)
        for kind,init in [('blocked',"Storage.prototype.getItem=function(){throw new DOMException('Blocked','SecurityError')};"),('quota',"Storage.prototype.setItem=function(){throw new DOMException('Full','QuotaExceededError')};")]:
            ctx=browser.new_context(viewport={'width':390,'height':844});ctx.add_init_script(init);page=ctx.new_page();ready(page)
            first=page.locator('#Week1 input[data-pick="roster"]').first;first.check();assert page.locator('#show-roster').inner_text().endswith('（1）')
            page.locator('#show-roster').click()
            assert page.locator('#reset-roster-storage').is_visible()
            if kind=='blocked':
                page.evaluate('(key)=>window.dispatchEvent(new StorageEvent("storage",{key,newValue:"{broken"}))',KEY)
                assert page.locator('#show-roster').inner_text().endswith('（1）')
            page.locator('#Week1 input[data-pick="compare"]').first.check();assert page.locator('#comparison-body tr').count()==1
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
            assert page.locator('.comparison-scroll').evaluate('(e)=>e.scrollWidth>e.clientWidth')
            page.screenshot(path='../player-tools-'+kind+'-mobile.png',full_page=False);ctx.close()
        ctx=browser.new_context();page=ctx.new_page();ready(page);page.locator('#Week1 input[data-pick="roster"]').first.check();ctx.close()
        ctx=browser.new_context();page=ctx.new_page();ready(page);assert page.locator('#show-roster').inner_text().endswith('（0）');ctx.close();browser.close()
        assert not errors,errors
        assert not external,external
        result=dict(url=url,tests='keyboard checkbox; independent compare/roster; exact TOT sorting/missing periods; filter/all/season selection retention; single remove/clear; reload/reopen persistence; two independent profiles; JSON export/import strict version/size/duplicates/IDs/count; cancel clear; previous season/unknown ID/transfer ID; literal imported text; malformed storage/reset; blocked/quota graceful memory fallback; incognito disposal; mobile scrolling; zero external requests',js_errors=errors,external_requests=external)
        Path('../player-tools-browser-result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(result))
if __name__=='__main__':run(sys.argv[1])
