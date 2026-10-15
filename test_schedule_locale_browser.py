"""Real-data bilingual UI, localized event dates, six-row schedule and shared preferences."""
import json,os,sys
from datetime import datetime,timezone
from pathlib import Path
from playwright.sync_api import sync_playwright
ORIGIN=(sys.argv[1] if len(sys.argv)>1 else 'http://127.0.0.1:8776').rstrip('/')
OUT=Path(sys.argv[2] if len(sys.argv)>2 else '../schedule-locale-browser');OUT.mkdir(parents=True,exist_ok=True)
KEY='fantasyorgcat:site-preferences:v1'

def untranslated(page):
 return page.evaluate('''()=>{const set=new Set(),w=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);while(w.nextNode()){const n=w.currentNode;if(!n.parentElement.closest('script,style,[data-site-preferences]')&&/[\\u4e00-\\u9fff]/.test(n.textContent))set.add(n.textContent.trim());}return [...set].filter(Boolean);}''')

def validate_schedule(page,zone):
 return page.evaluate('''zone=>{const table=document.querySelector('#teamTableWCustom'),calendar=[...table.tHead.rows[0].cells].slice(2).map(h=>h.dataset.fullDate||h.textContent),fmt=new Intl.DateTimeFormat('en-CA',{timeZone:zone,year:'numeric',month:'2-digit',day:'2-digit'}),date=d=>{const p=fmt.formatToParts(d),v=k=>p.find(x=>x.type===k).value;return v('year')+'-'+v('month')+'-'+v('day');},clock=new Intl.DateTimeFormat('en-GB',{timeZone:zone,hour:'2-digit',minute:'2-digit',hourCycle:'h23'});for(const td of table.tBodies[0].querySelectorAll('td'))for(const time of td.querySelectorAll('time[datetime]')){if(!time.dateTime)continue;const d=new Date(time.dateTime),expected=date(d).slice(5).replace('-','/')+' '+clock.format(d);if(time.textContent!==expected)throw Error('Wrong local clock '+time.textContent+' / '+expected);if(calendar[td.cellIndex-2].slice(0,10)!==date(d))throw Error('Clock and date column disagree');}return {games:[...table.tBodies[0].rows].map(r=>[r.dataset.team,r.cells[1].textContent]),dates:calendar};}''',zone)
results=[]
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path=os.environ.get('CHROMIUM_PATH','/usr/bin/chromium'))
 for width in [1440,390]:
  ctx=browser.new_context(viewport={'width':width,'height':1000 if width>600 else 844},reduced_motion='reduce');page=ctx.new_page();errors=[];external=[]
  page.on('pageerror',lambda e:errors.append(str(e)));page.on('request',lambda r:external.append(r.url) if not r.url.startswith(ORIGIN+'/') else None)
  page.goto(ORIGIN+'/');page.wait_for_function('()=>window.SiteUI&&Object.keys(tables).length===5');page.wait_for_timeout(200)
  assert page.locator('[data-platform="YAHOO"]').get_attribute('aria-pressed')=='true'
  assert page.locator('[data-timezone]').input_value()=='Asia/Taipei'
  assert page.locator('.hero h1').inner_text()=='把下一場排入你的賽程'
  original=page.evaluate('JSON.stringify(playerCatalog)')
  area=page.locator('#WeekCustom .schedule-scroll')
  assert area.evaluate('''e=>{const rows=[...e.querySelectorAll('tbody tr')].slice(0,7),rect=e.getBoundingClientRect();return rows.length>=7&&rows[5].getBoundingClientRect().bottom<=rect.bottom+1&&rows[6].getBoundingClientRect().bottom>rect.bottom+20;}''')
  assert page.evaluate('''()=>{const s=document.querySelector('#WeekCustom .team-section'),p=document.querySelector('#WeekCustom .player-section');return Math.abs(s.getBoundingClientRect().width-p.getBoundingClientRect().width)<2;}''')
  for text in page.locator('#WeekCustom .matchup').all_text_contents():assert not any(s in text for s in ['難打','好打','中段','10/10','/30']),text
  before=validate_schedule(page,'Asia/Taipei');page.screenshot(path=str(OUT/f'home-zh-{width}.png'))
  area.scroll_into_view_if_needed();page.locator('#WeekCustom .team-section').screenshot(path=str(OUT/f'schedule-taipei-{width}.png'))
  page.locator('#WeekCustom input[data-pick="compare"]').first.check();pid=page.locator('#comparison-body tr').first.get_attribute('data-player-id')
  page.locator('[data-timezone]').select_option('America/New_York');page.wait_for_timeout(250)
  after=validate_schedule(page,'America/New_York');assert before['games']==after['games'];assert before['dates']!=after['dates']
  assert page.locator('#comparison-body tr').get_attribute('data-player-id')==pid
  assert original==page.evaluate('JSON.stringify(playerCatalog)')
  page.locator('[data-timezone]').select_option('UTC');page.wait_for_timeout(250);validate_schedule(page,'UTC')
  page.locator('[data-language]').click();page.wait_for_function('()=>document.documentElement.lang==="en"');page.wait_for_timeout(250)
  missing=untranslated(page);(OUT/f'home-untranslated-{width}.json').write_text(json.dumps(missing,ensure_ascii=False,indent=2));assert not missing,missing
  assert page.locator('.hero h1').inner_text()=='Put the next game on your schedule'
  page.locator('#season-week').select_option('1');page.wait_for_timeout(200);validate_schedule(page,'UTC')
  page.locator('#season-week').select_option('6');page.wait_for_timeout(200);validate_schedule(page,'UTC');assert not untranslated(page),untranslated(page)
  rank=page.locator('#WeekCustom .table-options').nth(0);rank.locator('summary').click();rank.get_by_role('button',name='REB + FG%').click();rank.locator('summary').click()
  assert page.locator('#WeekCustom [data-rank-category]:checked').count()==2
  page.locator('#WeekCustom [data-mode="TOT"]').click();assert original==page.evaluate('JSON.stringify(playerCatalog)')
  page.evaluate('scrollTo({top:0,behavior:"instant"})');page.screenshot(path=str(OUT/f'home-en-{width}.png'))
  page.locator('.site-nav a[href="roto.html"]').click();page.wait_for_function('()=>document.querySelector("#roto-player-table tbody input")');page.wait_for_timeout(200)
  assert page.locator('html').get_attribute('lang')=='en';assert page.locator('[data-timezone]').input_value()=='UTC'
  missing=untranslated(page);(OUT/f'roto-untranslated-{width}.json').write_text(json.dumps(missing,ensure_ascii=False,indent=2));assert not missing,missing
  page.locator('#player-search').fill('Nikola Jokic');page.locator('#roto-player-table [data-roto-pick]').first.check();page.wait_for_timeout(200)
  page.locator('#table-mode').select_option('perGame');page.wait_for_timeout(200)
  page.locator('#radar [data-radar-metric="TO"]').focus();page.wait_for_timeout(200)
  missing=untranslated(page);(OUT/f'roto-active-untranslated-{width}.json').write_text(json.dumps(missing,ensure_ascii=False,indent=2));assert not missing,missing
  page.evaluate('scrollTo({top:0,behavior:"instant"})');page.screenshot(path=str(OUT/f'roto-en-{width}.png'))
  # User-entered names and saved player IDs are not translated or rewritten.
  page.locator('#base-editor').evaluate('(e)=>e.open=true');page.locator('#base-roster-name').fill('測試聯盟 / League');page.locator('#save-base-roster').click()
  saved=page.evaluate('localStorage.getItem(RotoCore.storageKey)');assert saved
  page.locator('[data-language]').click();page.wait_for_function('()=>document.documentElement.lang==="zh-Hant"');page.wait_for_timeout(200)
  assert page.locator('#base-roster-name').input_value()=='測試聯盟 / League'
  assert saved==page.evaluate('localStorage.getItem(RotoCore.storageKey)')
  page.locator('.site-nav a[href="index.html"]').click();page.wait_for_function('()=>window.SiteUI&&Object.keys(tables).length===5')
  assert page.locator('[data-timezone]').input_value()=='UTC';assert page.locator('.hero h1').inner_text()=='把下一場排入你的賽程'
  page.locator('#schedule-extras summary').click();page.locator('#defaultOpen').click()
  assert page.locator('#Week1').is_visible();assert original==page.evaluate('JSON.stringify(playerCatalog)')
  assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
  assert not errors,errors;assert not external,external
  results.append(dict(width=width,default_yahoo=True,default_taipei=True,six_complete_rows=True,full_width_schedule=True,compact_cards=True,localized_dates_and_times=True,language_roundtrip=True,roto_and_dynamic_ui=True,roster_and_stats_preserved=True,js_errors=errors,external_requests=external));ctx.close()
 # Default week must use the current Yahoo scoring date, including its merged Cup week.
 ctx=browser.new_context();page=ctx.new_page();page.clock.install(time=datetime(2026,12,2,15,tzinfo=timezone.utc));page.goto(ORIGIN+'/');page.wait_for_function('()=>Object.keys(tables).length===5')
 assert page.locator('[data-platform="YAHOO"]').get_attribute('aria-pressed')=='true';assert page.locator('#season-week').input_value()=='6';ctx.close()
 # Preference write failures leave the selected language/timezone usable.
 ctx=browser.new_context();ctx.add_init_script("Storage.prototype.getItem=function(){throw Error('blocked')};Storage.prototype.setItem=function(){throw Error('quota')}");page=ctx.new_page();page.goto(ORIGIN+'/');page.wait_for_function('()=>Object.keys(tables).length===5');page.locator('[data-language]').click();page.wait_for_timeout(200);assert page.locator('html').get_attribute('lang')=='en';assert page.locator('[data-site-preferences] [role="status"]').count()==1;ctx.close();browser.close()
(OUT/'browser-results.json').write_text(json.dumps({'results':results,'yahoo_current_date_verified':True,'storage_failure_verified':True},ensure_ascii=False,indent=2));print(json.dumps(results))
