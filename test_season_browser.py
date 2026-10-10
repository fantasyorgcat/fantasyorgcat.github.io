"""Check every platform period against the same published NBA events."""
import os, sys, json
from datetime import date, timedelta
from pathlib import Path
from playwright.sync_api import sync_playwright


def run(url):
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path=os.environ.get('CHROMIUM_PATH','/usr/bin/chromium'),headless=True)
        page=browser.new_page(viewport={'width':1500,'height':1000});errors=[];failed=[]
        page.on('pageerror',lambda e:errors.append(str(e)));page.on('requestfailed',lambda r:failed.append(r.url))
        assert page.goto(url,wait_until='load',timeout=60000).status==200
        page.wait_for_function('Object.keys(tables).length===5',timeout=30000)
        assert page.locator('.tablinks').count()==4
        select=page.locator('#season-week')
        events=page.evaluate('scheduleEvents');groups=page.evaluate('platformPeriods')
        signature=page.evaluate("JSON.stringify(Object.values(playerCatalog).map(p=>p.periods))")
        tested={}
        for key in ['NBA','YAHOO']:
            page.locator('[data-platform="'+key+'"]').click()
            weeks=groups[key]['periods'];tested[key]=len(weeks)
            assert select.locator('option').count()==len(weeks)+1
            for index,week in enumerate(weeks):
                assert week['number']==index+1
                select.select_option(str(index))
                assert page.locator('#custom-period-heading').inner_text()==week['label']
                start,end=date.fromisoformat(week['start']),date.fromisoformat(week['end'])
                dates=[str(start+timedelta(days=i)) for i in range((end-start).days+1)]
                headers=page.evaluate("tables.WCustom.columns('[data-schedule-day]').indexes().toArray().map(i=>tables.WCustom.column(i).header().textContent)")
                assert headers==[d+' ET' for d in dates]
                rows=page.evaluate("tables.WCustom.rows().data().toArray().map(r=>({team:r[1],games:Number(r[2]),days:r.slice(3,3+tables.WCustom.columns('[data-schedule-day]').count())}))")
                expected={}
                for team in {row['team'] for row in rows}:
                    selected=[e for e in events if e['date_et'] in dates and team in [e.get('home'),e.get('away')]]
                    html=[''.join(e['home_html'] if e.get('home')==team else e['away_html'] for e in selected if e['date_et']==d) for d in dates]
                    expected[team]=dict(games=sum(e['status'] not in ['cancelled','postponed','suspended'] for e in selected),days=html)
                expected=page.evaluate("teams=>{for(const row of Object.values(teams))row.days=row.days.map(s=>{const t=document.createElement('template');t.innerHTML=s;return t.innerHTML;});return teams;}",expected)
                for row in rows:
                    assert row['games']==expected[row['team']]['games']
                    assert row['days']==expected[row['team']]['days'],(key,index,row['team'])
                page.evaluate("tables.WCustom.order([2,'desc']).draw()")
                counts=page.evaluate("Array.from(tables.WCustom.column(2,{order:'applied'}).data()).map(Number)")
                assert counts==sorted(counts,reverse=True)
                assert signature==page.evaluate("JSON.stringify(Object.values(playerCatalog).map(p=>p.periods))")
                assert page.evaluate("""()=>{const a=tables.W1.rows().data().toArray(),b=tables.WCustom.rows().data().toArray();const lookup=new Map(a.map(r=>[r[0],r.slice(3+tables.W1.columns('[data-schedule-day]').count())]));return b.every(r=>JSON.stringify(r.slice(3+tables.WCustom.columns('[data-schedule-day]').count()))===JSON.stringify(lookup.get(r[0])));} """)
        page.locator('[data-platform="NBA"]').click();select.select_option('0')
        page.locator('#WeekCustom [data-period="LS"]').click()
        for offset in [7,8]:
            page.evaluate(f"tables.WCustom.order([tables.WCustom.column('.stat-ls.stat-avg').index()+{offset},'desc']).draw()")
            values=page.evaluate("Array.from(tables.WCustom.column(tables.WCustom.order()[0][0],{order:'applied'}).nodes()).map(n=>Number(n.dataset.order))")
            assert values==sorted(values,reverse=True)
        page.locator('#teamTableWCustom .team-row').first.click()
        n=page.evaluate('tables.WCustom.rows({search:"applied"}).count()');assert n>0
        page.locator('#WeekCustom [data-mode="TOT"]').click();select.select_option('24')
        assert page.evaluate('tables.WCustom.rows({search:"applied"}).count()')==n
        page.locator('[data-platform="YAHOO"]').click()
        assert page.evaluate('tables.WCustom.rows({search:"applied"}).count()')==n
        page.locator('#show-all-players').click()
        assert page.evaluate('tables.WCustom.rows({search:"applied"}).count()===tables.WCustom.rows().count()')
        page.set_viewport_size({'width':390,'height':844})
        page.evaluate('tables.WCustom.columns.adjust().draw(false)')
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
        scroll=page.locator('#playerTableWCustom_wrapper .dt-scroll-body')
        scroll.evaluate('(e)=>{e.scrollLeft=e.scrollWidth;e.dispatchEvent(new Event("scroll"));}')
        assert scroll.evaluate('(e)=>e.scrollLeft>0')
        assert page.locator('#playerTableWCustom_wrapper .dt-scroll-head').evaluate('(e)=>e.scrollLeft>0')
        page.evaluate('window.scrollTo(0,document.body.scrollHeight)')
        for selector in ['#show-all-players','[data-platform="YAHOO"]','#season-week']:
            box=page.locator(selector).bounding_box();assert 0<=box['y']<844
        assert not errors,errors;assert not failed,failed
        result=dict(url=url,tested_periods=tested,checks='Every period: actual dates/counts/opponents, exact unchanged statistics/PR, numeric game sorting; platform filter/mode preservation, mobile horizontal scrolling and sticky controls',js_errors=errors,failed_requests=failed)
        Path('../season-browser-result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(result,ensure_ascii=False))
        browser.close()


if __name__=='__main__':run(sys.argv[1])
