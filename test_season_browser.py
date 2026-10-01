import os,sys,json
from pathlib import Path
sys.path.insert(0,str(Path('.test-deps').resolve()))
from playwright.sync_api import sync_playwright

def run(url):
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path=os.environ.get('CHROMIUM_PATH',r'C:\Users\USER\AppData\Local\ms-playwright\chromium-1228\chrome-win64\chrome.exe'),headless=True)
        page=browser.new_page(viewport={'width':1500,'height':1000});errors=[];failed=[]
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.on('requestfailed',lambda r:failed.append(r.url))
        response=page.goto(url,wait_until='load',timeout=60000);assert response.status==200
        page.wait_for_function('Object.keys(tables).length===4',timeout=30000)
        select=page.locator('#season-week')
        weeks=page.evaluate('seasonWeeks')
        assert page.locator('.tablinks').count()==4
        if not weeks:
            assert select.is_disabled()
            assert not errors and not failed
            browser.close();print('Empty season: disabled selector, four shortcuts and roster intact');return
        assert select.locator('option').count()==len(weeks)+1
        assert weeks[0]['number']==1
        for i,w in enumerate(weeks):assert w['number']==i+1 and f'Week {i+1}' in w['label']
        select.select_option('0')
        assert page.locator('#WeekSeason').is_visible()
        assert page.evaluate('Object.keys(tables).length')==5
        signature=page.evaluate("JSON.stringify(tables.WSeason.rows().data().toArray().map(r=>[r[0],r.slice(10)]).sort((a,b)=>String(a[0]).localeCompare(String(b[0]))))")
        indices={0,len(weeks)//2,len(weeks)-1}
        first_year=weeks[0]['label'].split(' · ')[1][:4]
        indices.update(i for i,w in enumerate(weeks) if first_year not in w['label'].split(' · ')[1][:4])
        indices.update(i for i,w in enumerate(weeks) if w['events']==0)
        for index in sorted(indices):
            select.select_option(str(index));w=weeks[index]
            assert page.locator('#season-week-heading').inner_text()==w['label']
            assert page.locator('#season-week-empty').is_visible()==(w['events']==0)
            headers=page.evaluate('Array.from({length:7},(_,i)=>tables.WSeason.column(i+3).header().textContent.trim())')
            assert headers==w['headers'],(index,headers,w['headers'])
            rows=page.evaluate('tables.WSeason.rows().data().toArray().map(r=>({team:r[1],games:Number(r[2]),days:r.slice(3,10)}))')
            for row in rows:
                expected=w['teams'].get(row['team'],dict(games=0,days=['']*7))
                assert row['games']==expected['games'] and row['days']==expected['days']
            page.evaluate("tables.WSeason.order([2,'desc']).draw()")
            counts=page.evaluate("Array.from(tables.WSeason.column(2,{order:'applied'}).data()).map(Number)")
            assert counts==sorted(counts,reverse=True),'Games sorting cache stale after changing week'
            now=page.evaluate("JSON.stringify(tables.WSeason.rows().data().toArray().map(r=>[r[0],r.slice(10)]).sort((a,b)=>String(a[0]).localeCompare(String(b[0]))))")
            assert signature==now,'Exact statistics/PR changed on schedule selection'
        page.evaluate("switchStats('LS','WSeason')")
        for offset in [7,8]:
            page.evaluate(f"tables.WSeason.order([tables.WSeason.column('.stat-ls.stat-avg').index()+{offset},'desc']).draw()")
            values=page.evaluate(f"Array.from(tables.WSeason.column(tables.WSeason.column('.stat-ls.stat-avg').index()+{offset},{{order:'applied'}}).nodes()).map(n=>Number(n.getAttribute('data-order')))")
            assert values==sorted(values,reverse=True),'Exact FG/FT sort changed on schedule selection'
        select.select_option('0')
        team=page.locator('#teamTableWSeason .team-row').first
        if team.count():
            team.click();n=page.evaluate('tables.WSeason.rows({search:"applied"}).count()')
            assert n>0
            page.locator('#WeekSeason [data-period="LS"]').click();page.locator('#WeekSeason [data-mode="TOT"]').click()
            select.select_option(str(len(weeks)-1))
            assert page.evaluate('tables.WSeason.rows({search:"applied"}).count()')==n
        page.locator('#show-all-players').click()
        assert page.evaluate('tables.WSeason.rows({search:"applied"}).count()===tables.WSeason.rows().count()')
        page.locator('.tablinks').nth(3).click();assert select.input_value()==''
        assert page.locator('#Week4').is_visible()
        assert page.evaluate('tables.W4.rows({search:"applied"}).count()===tables.W4.rows().count()')
        select.select_option('0');page.set_viewport_size({'width':390,'height':844})
        page.evaluate('tables.WSeason.columns.adjust().draw(false)')
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
        select.select_option(str(len(weeks)-1))
        scroll=page.locator('#playerTableWSeason_wrapper .dt-scroll-body')
        scroll.evaluate('(e)=>{e.scrollLeft=e.scrollWidth;e.dispatchEvent(new Event("scroll"));}')
        assert scroll.evaluate('(e)=>e.scrollLeft>0')
        assert page.locator('#playerTableWSeason_wrapper .dt-scroll-head').evaluate('(e)=>e.scrollLeft>0')
        page.evaluate('window.scrollTo(0,document.body.scrollHeight)')
        box=page.locator('#show-all-players').bounding_box();assert 0<=box['y']<844
        page.locator('#show-all-players').click()
        assert not errors,errors;assert not failed,failed
        result=dict(url=url,weeks=len(weeks),opening=weeks[0]['label'],closing=weeks[-1]['label'],tested_indices=sorted(indices),checks='actual schedule dates/counts/opponents, cross-year options, empty weeks, unchanged exact stats/PR, preserved period/mode/team, all-player reset, quick shortcuts, lazy one-table reuse, mobile selector/horizontal scroll/sticky control',js_errors=errors,failed_requests=failed)
        Path('../season-browser-result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(result,ensure_ascii=False))
        browser.close()
if __name__=='__main__':run(sys.argv[1])
