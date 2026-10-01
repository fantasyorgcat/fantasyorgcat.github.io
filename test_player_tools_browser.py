import sys,json
from pathlib import Path
sys.path.insert(0,str(Path('.test-deps').resolve()))
from playwright.sync_api import sync_playwright
CHROME=r'C:\Users\USER\AppData\Local\ms-playwright\chromium-1228\chrome-win64\chrome.exe'
def run(url):
 results=[]
 with sync_playwright() as p:
  browser=p.chromium.launch(executable_path=CHROME,headless=True)
  for width in [1500,390]:
   ctx=browser.new_context(viewport={'width':width,'height':1000 if width==1500 else 844});page=ctx.new_page();errors=[];failed=[];external=[]
   ctx.add_init_script('''(()=>{const s=localStorage,key='fantasy-nba:hotmilk300/Fantasy-NBA-Streaming-Assistant:roster:v1';const get=Storage.prototype.getItem,set=Storage.prototype.setItem;set.call(s,key,'existing-user-data');window.storageCalls=[];window.savedRoster=()=>get.call(s,key);for(const method of ['getItem','setItem','removeItem','clear'])Storage.prototype[method]=function(){storageCalls.push(method);throw Error('Storage disabled for comparison test');};})();''')
   page.on('pageerror',lambda e:errors.append(str(e)));page.on('requestfailed',lambda r:failed.append(r.url))
   page.on('request',lambda r:external.append(r.url) if not r.url.startswith(url.split('/fantasy_')[0].rstrip('/')+'/') else None)
   assert page.goto(url,wait_until='load',timeout=60000).status==200
   page.wait_for_function('Object.keys(tables).length===4')
   assert page.locator('[data-pick="roster"],#roster-panel,#show-roster,#import-roster,#export-roster').count()==0
   pair=page.evaluate("()=>{const a=Object.keys(playerCatalog)[0];return[a,Object.keys(playerCatalog).find(id=>playerCatalog[id].team!==playerCatalog[a].team)]}")
   for pid in pair:
    page.evaluate('(id)=>tables.W1.search(playerCatalog[id].name).draw()',pid)
    cb=page.locator('#Week1 input[data-pick="compare"][data-player-id="'+pid+'"]');cb.focus();cb.press('Space');assert cb.is_checked()
   assert page.locator('#comparison-body tr').count()==2
   assert page.evaluate('!!(document.querySelector("#comparison-panel").compareDocumentPosition(document.querySelector("#Week1"))&Node.DOCUMENT_POSITION_FOLLOWING)')
   def exact():
    value=page.evaluate('''()=>{const t=tables[activeWeek],headers=Array.from(document.querySelectorAll('#comparison-head th')).slice(2,9).map(n=>n.textContent);const expected=Array.from({length:7},(_,i)=>t.column(i+3).header().textContent);if(JSON.stringify(headers)!==JSON.stringify(expected))throw Error('Date mismatch');for(const tr of document.querySelectorAll('#comparison-body tr')){const team=playerCatalog[tr.dataset.playerId].team,r=t.rows({search:'none'}).data().toArray().find(row=>row[1]===team);if(r){if(tr.cells[1].textContent!==String(r[2]))throw Error('Game count mismatch');for(let i=0;i<7;i++){const tmp=document.createElement('template');tmp.innerHTML=r[i+3];if(tr.cells[i+2].innerHTML!==tmp.innerHTML)throw Error('Opponent/home-away/defense mismatch');}}}return activeWeek;}''');return value
   exact();assert page.locator('#comparison-body tr td:nth-child(2)').first.inner_text()=='0'
   page.locator('#show-all-players').click();exact();assert page.locator('#comparison-body tr').count()==2
   for i in range(4):
    page.locator('.tablinks').nth(i).click();assert exact()=='W'+str(i+1)
    teamrow=page.locator('#teamTableW'+str(i+1)+' .team-row')
    if teamrow.count():teamrow.first.click();exact();assert page.locator('#comparison-body tr').count()==2
    page.locator('#show-all-players').click();exact()
   def ranks():
    return page.evaluate("""()=>{const out={};for(const node of tables[activeWeek].rows({search:'none'}).nodes().toArray()){const id=node.querySelector('[data-player-id]').dataset.playerId,cell=node.querySelector('.rank-ls-avg');out[id]=cell.textContent;if(playerCatalog[id].periods.ls.avg.Rank.value!==null&&Number(cell.textContent)!==playerCatalog[id].periods.ls.avg.Rank.value)throw Error('Global/catalog Rank mismatch');}return out;}""")
   before=ranks();assert min(int(v) for v in before.values() if v!='—')==1
   page.evaluate("tables[activeWeek].order([tables[activeWeek].column('.rank-ls-avg').index(),'asc']).draw()")
   values=page.evaluate("Array.from(tables[activeWeek].column('.rank-ls-avg',{order:'applied'}).nodes()).map(n=>Number(n.dataset.order))");assert values==sorted(values)
   page.locator('#comparison-head button[data-sort="Rank"]').click()
   values=page.locator('#comparison-body tr td').evaluate_all('(nodes)=>nodes.filter(n=>n.cellIndex===19).map(n=>Number(n.dataset.value)).filter(n=>n>0)');assert values==sorted(values)
   weeks=page.evaluate('seasonWeeks');assert len(weeks)==25
   for i in range(len(weeks)):
    page.locator('#season-week').select_option(str(i));assert exact()=='WSeason';assert page.locator('#comparison-body tr').count()==2;assert ranks()==before
   page.locator('#season-week').select_option('0');exact()
   assert page.evaluate('seasonWeeks[0].start') if 'start' in weeks[0] else weeks[0]['number']==1
   page.locator('#comparison-mode').select_option('tot');page.locator('#comparison-head button[data-sort="PTS"]').click()
   vals=page.locator('#comparison-body tr td').evaluate_all('(nodes)=>nodes.filter(n=>n.cellIndex===11).map(n=>Number(n.dataset.value))');assert vals==sorted(vals,reverse=True)
   page.locator('#comparison-period').select_option('l7');assert page.locator('#comparison-body tr td').evaluate_all('(nodes)=>nodes.filter(n=>[11,19].includes(n.cellIndex)).every(n=>n.textContent==="—")')
   page.locator('#comparison-period').select_option('ls');page.locator('#comparison-mode').select_option('avg')
   assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
   if width==390:assert page.locator('.comparison-scroll').evaluate('(e)=>e.scrollWidth>e.clientWidth');page.locator('.comparison-scroll').evaluate('(e)=>e.scrollLeft=e.scrollWidth');assert page.locator('.comparison-scroll').evaluate('(e)=>e.scrollLeft>0')
   page.locator('.comparison-scroll').evaluate('(e)=>e.scrollLeft=0');page.evaluate('window.scrollTo(0,document.querySelector("#comparison-panel").offsetTop-document.querySelector(".workspace-bar").offsetHeight-16)');page.screenshot(path='../comparison-schedule-'+str(width)+'.png',full_page=False)
   original=page.evaluate('(id)=>({name:playerCatalog[id].name,team:playerCatalog[id].team})',pair[0]);page.evaluate('(id)=>{playerCatalog[id].name="<img src=x onerror=alert(1)>";playerCatalog[id].team="UNKNOWN";}',pair[0])
   page.locator('#comparison-mode').select_option('tot');assert page.locator('#comparison-body img').count()==0
   missing=page.locator('#comparison-body tr[data-player-id="'+pair[0]+'"]');assert missing.locator('td').nth(1).inner_text()=='—';assert missing.locator('td.comparison-matchup').count()==7
   page.evaluate('([id,v])=>Object.assign(playerCatalog[id],v)',[pair[0],original]);page.locator('#comparison-mode').select_option('avg');exact()
   page.locator('#comparison-body button').first.click();assert page.locator('#comparison-body tr').count()==1
   page.locator('#clear-comparison').click();assert not page.locator('#comparison-panel').is_visible()
   assert page.evaluate('storageCalls')==[];assert page.evaluate('savedRoster()')=='existing-user-data'
   page.reload(wait_until='load');page.wait_for_function('Object.keys(tables).length===4');assert not page.locator('#comparison-panel').is_visible();assert page.evaluate('storageCalls')==[]
   assert not errors,errors;assert not failed,failed;assert not external,external
   results.append(dict(width=width,season_weeks=len(weeks),cross_team_ids=pair,exact_schedule_all_weeks=True,storage_calls=[],existing_storage_preserved=True,zero_games_and_missing=True,rank_global_and_week_invariant=True,rank_numeric_sort=True,rank_missing_is_unranked=True,js_errors=errors,failed_requests=failed,external_requests=external));ctx.close()
  browser.close()
 result=dict(url=url,results=results);Path('../comparison-schedule-browser-result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result))
if __name__=='__main__':run(sys.argv[1])
