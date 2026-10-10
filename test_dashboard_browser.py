import sys,json,os
from pathlib import Path
sys.path.insert(0,str(Path('.test-deps').resolve()))
from playwright.sync_api import sync_playwright

def run(url):
 with sync_playwright() as p:
  browser=p.chromium.launch(executable_path=os.environ.get('CHROMIUM_PATH',r'C:\Users\USER\AppData\Local\ms-playwright\chromium-1228\chrome-win64\chrome.exe'),headless=True)
  page=browser.new_page(viewport={'width':1500,'height':1000});errors=[];failed=[]
  page.on('pageerror',lambda e:errors.append(str(e)));page.on('requestfailed',lambda r:failed.append(r.url))
  response=page.goto(url,wait_until='load',timeout=90000);assert response.status==200
  page.wait_for_function('Object.keys(tables).length>=4',timeout=30000)
  page.locator('#schedule-extras summary').click()
  assert not page.locator('.data-notice').is_visible() and not page.locator('.defense-notice').is_visible()
  page.locator('.data-details summary').click();assert page.locator('.data-notice').is_visible();page.locator('.data-details summary').click()
  total=page.evaluate('tables.W4.rows().count()');assert total>500
  for i in range(1,5):
   page.locator('.tablinks').nth(i-1).click();assert page.locator(f'#Week{i}').is_visible()
   page.locator(f'#Week{i} [data-period="LS"]').click();page.locator(f'#Week{i} [data-mode="TOT"]').click()
   assert page.evaluate(f'tables.W{i}.columns(":visible").count()')>=11
   page.locator(f'#Week{i} [data-period="L7"]').click()
   assert page.locator(f'#Week{i} td.stat-l7.stat-tot').first.inner_text()=='—'
   page.locator(f'#Week{i} [data-period="LS"]').click();page.locator(f'#Week{i} [data-mode="AVG"]').click()
  page.locator('.tablinks').nth(3).click();rows=page.locator('#teamTableW4 .team-row');assert rows.count()>=2
  team_a=rows.nth(0).get_attribute('data-team');team_b=rows.nth(1).get_attribute('data-team')
  rows.nth(0).click();a_count=page.evaluate('tables.W4.rows({search:"applied"}).count()');assert 0<a_count<total
  page.locator('#show-all-players').click();assert page.evaluate('tables.W4.rows({search:"applied"}).count()')==total
  rows.nth(1).click();b_count=page.evaluate('tables.W4.rows({search:"applied"}).count()');assert 0<b_count<total
  page.locator('#Week4 [data-period="L14"]').click();page.locator('#Week4 [data-mode="TOT"]').click()
  assert page.evaluate('tables.W4.rows({search:"applied"}).count()')==b_count
  page.locator('.tablinks').first.click();assert page.evaluate('tables.W1.rows({search:"applied"}).count()')==total
  assert '全體球員' in page.locator('#active-selection').inner_text()
  page.locator('.tablinks').nth(3).click();assert team_b in page.locator('#active-selection').inner_text()
  assert page.locator('#Week4 [data-period="L14"]').get_attribute('class').find('active')>=0
  assert page.locator('#Week4 [data-mode="TOT"]').get_attribute('class').find('active')>=0
  name=page.locator('#playerTableW4 tbody td b').first.inner_text()
  search=page.locator('#playerTableW4_wrapper input[type="search"]');search.fill(name);search.press('Enter')
  page.wait_for_function('tables.W4.rows({search:"applied"}).count()===1')
  page.locator('#show-all-players').click();assert search.input_value()==''
  assert page.evaluate('tables.W4.rows({search:"applied"}).count()')==total
  assert page.locator('#Week4 [data-period="L14"]').get_attribute('class').find('active')>=0
  assert page.locator('#Week4 [data-mode="TOT"]').get_attribute('class').find('active')>=0
  # The all-player control remains reachable after scrolling through the roster.
  page.evaluate('window.scrollTo(0,document.body.scrollHeight)')
  box=page.locator('#show-all-players').bounding_box();assert 0<=box['y']<1000
  page.locator('#Week4 [data-period="LS"]').click();page.locator('#Week4 [data-mode="AVG"]').click()
  page.evaluate("tables.W4.order([tables.W4.column('.stat-ls.stat-avg').index()+7,'desc']).draw()")
  values=page.evaluate("Array.from(tables.W4.column(tables.W4.column('.stat-ls.stat-avg').index()+7,{order:'applied'}).nodes()).map(n=>Number(n.getAttribute('data-order')))")
  assert values==sorted(values,reverse=True)
  for index in range(1,7):
   vals=page.evaluate(f"Array.from(tables.W4.column(tables.W4.column('.stat-ls.stat-tot').index()+{index}).nodes()).map(n=>Number(n.getAttribute('data-order'))).filter(v=>v>=0)")
   assert all(float(v).is_integer() for v in vals)
  page.evaluate('window.scrollTo(0,0)');page.screenshot(path='../dashboard-desktop.png',full_page=False)
  page.set_viewport_size({'width':390,'height':844});page.evaluate('window.scrollTo(0,0)')
  page.evaluate('tables.W4.columns.adjust().draw(false)')
  assert page.evaluate('document.documentElement.scrollWidth<=window.innerWidth+1')
  scroll=page.locator('#playerTableW4_wrapper .dt-scroll-body')
  assert scroll.evaluate('(e)=>e.scrollWidth>e.clientWidth')
  scroll.evaluate('(e)=>{e.scrollLeft=e.scrollWidth;e.dispatchEvent(new Event("scroll"));}')
  assert scroll.evaluate('(e)=>e.scrollLeft>0')
  assert page.locator('#playerTableW4_wrapper .dt-scroll-head').evaluate('(e)=>e.scrollLeft>0')
  page.screenshot(path='../dashboard-mobile.png',full_page=False)
  page.evaluate('window.scrollTo(0,document.body.scrollHeight)');box=page.locator('#show-all-players').bounding_box();assert 0<=box['y']<844
  rows.nth(0).click();page.locator('#show-all-players').click();assert page.evaluate('tables.W4.rows({search:"applied"}).count()')==total
  assert not errors,errors;assert not failed,failed
  result=dict(url=url,status=response.status,players=total,team_a=team_a,team_b=team_b,team_a_count=a_count,team_b_count=b_count,checks='A→all→B, week isolation, period/mode preservation, search clears, sticky all button, exact FG sort/integer TOT, collapsed details, mobile no page overflow and reachable right columns',js_errors=errors,failed_requests=failed)
  Path('../dashboard-browser-result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(result,ensure_ascii=False))
  browser.close()
if __name__=='__main__':run(sys.argv[1])
