"""Real report: stable geometry, custom PR ranks and local display preferences."""
import json, os, sys
from pathlib import Path
from playwright.sync_api import sync_playwright

URL=sys.argv[1] if len(sys.argv)>1 else 'http://127.0.0.1:8776/'
OUT=Path(sys.argv[2] if len(sys.argv)>2 else '../table-preferences-browser')
OUT.mkdir(parents=True,exist_ok=True)
KEY='fantasyorgcat:table-display:v1'
results=[]
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path=os.environ.get('CHROMIUM_PATH','/usr/bin/chromium'),headless=True)
 for width in [1327,1500,390,320]:
  context=browser.new_context(viewport={'width':width,'height':1000 if width>600 else 844})
  page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  page.goto(URL,wait_until='load');page.wait_for_function('document.querySelectorAll(".table-toolbar").length===5')
  section=page.locator('#WeekCustom .player-section')
  def geometry():
   return page.evaluate('''()=>{const c=tables[activeWeek].table().container(),head=c.querySelector('.dt-scroll-head'),body=c.querySelector('.dt-scroll-body');const hs=[...head.querySelectorAll('th')].map(e=>e.getBoundingClientRect()),ds=[...body.querySelector('tbody tr').cells].map(e=>e.getBoundingClientRect());return {available:body.clientWidth,width:body.scrollWidth,aligned:hs.length===ds.length&&hs.every((r,i)=>Math.abs(r.width-ds[i].width)<2&&Math.abs(r.x-ds[i].x)<2),documentFits:document.documentElement.scrollWidth<=innerWidth+1,cols:hs.map(r=>r.width),rankVisible:hs.at(-1).right<=body.getBoundingClientRect().right+1};}''')
  team_widths=page.locator('#teamTableWCustom thead th').evaluate_all('(hs)=>hs.slice(2).map(h=>h.getBoundingClientRect().width)')
  assert all(n>0 for n in team_widths),team_widths
  assert page.locator('#WeekCustom .team-section').evaluate('(e)=>Math.abs(e.getBoundingClientRect().width-e.parentElement.querySelector(".player-section").getBoundingClientRect().width)<2')
  page.locator('#WeekCustom .team-section').screenshot(path=str(OUT/f'schedule-{width}.png'))
  geo=geometry();assert geo['aligned'] and geo['documentFits'],geo
  if width>600:assert geo['rankVisible'] and geo['width']<=geo['available']+1,geo
  else:assert geo['width']>geo['available'],geo
  page.locator('#jump-players').click();page.wait_for_timeout(300)
  page.screenshot(path=str(OUT/f'data-{width}.png'))
  # The two independent axes (stat period and mode) keep the same column widths.
  section.locator('[data-mode="TOT"]').click();assert geometry()['cols']==geo['cols']
  section.locator('[data-mode="AVG"]').click()
  rank=section.locator('.table-options').nth(0);rank.locator('summary').click();rank.get_by_role('button',name='籃板 + FG%').click()
  assert section.locator('[data-rank-category]:checked').count()==2
  def validate():
   return page.evaluate('''()=>{const t=tables[activeWeek],s=viewState[activeWeek],all=Object.values(playerCatalog),valid=all.map(p=>{const d=p.periods[s.period][s.mode];return {id:p.id,sum:d.REB.pr===null||d['FG%'].pr===null?null:d.REB.pr+d['FG%'].pr};}),col=t.column('.rank-'+s.period+'-'+s.mode).index();for(const row of t.rows({search:'none'}).indexes().toArray()){const id=t.row(row).node().querySelector('[data-player-id]').dataset.playerId,expected=valid.find(p=>p.id===id),cell=t.cell(row,col).node(),v=expected.sum===null?null:1+valid.filter(p=>p.sum!==null&&p.sum>expected.sum).length;if(cell.dataset.rankValue!==(v===null?'':String(v))||cell.dataset.rankSum!==(expected.sum===null?'':String(expected.sum)))throw Error('PR sum/rank mismatch '+id);}if(t.order()[0][0]!==col)throw Error('Rank ordering did not follow stat period/mode');const ordered=t.column(col,{order:'applied'}).nodes().toArray().map(c=>Number(c.dataset.order));if(!ordered.every((n,i)=>!i||ordered[i-1]<=n))throw Error('Rank sort stale');return t.rows({search:'applied'}).count();}''')
  assert validate()==622
  page.evaluate("tables[activeWeek].search('Trae Young').draw()");assert validate()==1
  page.evaluate("tables[activeWeek].search('').draw()")
  section.locator('[data-mode="TOT"]').click();validate();assert geometry()['aligned']
  section.locator('[data-period="L7"]').click();validate()
  assert page.evaluate("tables[activeWeek].column('.rank-l7-tot').nodes().toArray().every(td=>td.dataset.rankValue==='')")
  section.locator('[data-period="LS"]').click();section.locator('[data-mode="AVG"]').click()
  page.locator('#season-week').select_option('1');validate()
  assert section.locator('[data-rank-category]:checked').count()==2
  rank=section.locator('.table-options').nth(0);rank.locator('summary').click()
  for key in ['REB','FG%']:rank.locator('[data-rank-category="'+key+'"]').uncheck()
  assert page.evaluate("tables[activeWeek].column('.rank-ls-avg').nodes().toArray().every(td=>td.dataset.rankValue==='')")
  rank.get_by_role('button',name='恢復 9CAT').click()
  assert page.evaluate('''()=>{const t=tables[activeWeek];return t.rows().indexes().toArray().every(i=>{const id=t.row(i).node().querySelector('[data-player-id]').dataset.playerId,expected=playerCatalog[id].periods.ls.avg.Rank.value,cell=t.cell(i,t.column('.rank-ls-avg').index()).node();return cell.dataset.rankValue===(expected===null?'':String(expected));});}''')
  rank.get_by_role('button',name='籃板 + FG%').click();rank.locator('summary').click()
  page.locator('#jump-players').click();page.wait_for_timeout(200);page.screenshot(path=str(OUT/f'custom-rank-{width}.png'))
  # Use full schedule with exact fixed-width columns, accessible end and top scroll sync.
  section.locator('[data-display-setting="schedule"]').check()
  assert geometry()['aligned'] and geometry()['documentFits']
  assert page.evaluate("tables[activeWeek].columns('[data-schedule-day]').visible().toArray().every(Boolean)")
  days=page.evaluate("tables[activeWeek].columns('[data-schedule-day]').header().toArray().map(h=>h.getBoundingClientRect().width)")
  assert all(abs(x-84)<1 for x in days),days
  section.get_by_role('button',name='跳至 Rank →').click();page.wait_for_timeout(100)
  assert page.evaluate("(()=>{const c=tables[activeWeek].table().container();return c.querySelector('.dt-scroll-body').scrollLeft>0&&Math.abs(c.querySelector('.dt-scroll-body').scrollLeft-c.querySelector('.table-x-scroll').scrollLeft)<2})()")
  assert geometry()['rankVisible'] and geometry()['aligned']
  # Keyboard-operable real sliders change font/spacing/width; persistence must not touch rosters.
  page.evaluate("localStorage.setItem('fantasyorgcat:preserve-roster-test','unchanged')")
  display=section.locator('.table-options').nth(1);display.locator('summary').click()
  for key,value in [('font',16),('padding',4),('dayWidth',72)]:
   display.locator('[data-display-setting="'+key+'"]').evaluate('(e,v)=>{e.value=v;e.dispatchEvent(new Event("input",{bubbles:true}));}',value)
  assert geometry()['aligned'] and geometry()['documentFits']
  stored=page.evaluate('(k)=>JSON.parse(localStorage.getItem(k))',KEY)
  assert stored=={'font':16,'padding':4,'dayWidth':72,'schedule':True},stored
  assert page.evaluate("localStorage.getItem('fantasyorgcat:preserve-roster-test')")=='unchanged'
  page.reload(wait_until='load');page.wait_for_function('document.querySelectorAll(".table-toolbar").length===5')
  assert section.locator('[data-display-setting="schedule"]').is_checked()
  assert section.locator('[data-display-setting="font"]').input_value()=='16'
  assert page.evaluate("getComputedStyle(document.querySelector('#playerTableWCustom tbody td')).fontSize")=='16px'
  display=section.locator('.table-options').nth(1);display.locator('summary').click();display.get_by_role('button',name='恢復預設外觀').click()
  assert not section.locator('[data-display-setting="schedule"]').is_checked()
  assert page.evaluate("localStorage.getItem('fantasyorgcat:preserve-roster-test')")=='unchanged'
  assert not errors,errors
  results.append({'width':width,'geometry':geo,'selected_pr_and_scope':True,'period_mode_and_week':True,'missing_and_empty':True,'fixed_schedule_width':84,'preferences_persisted':stored,'js_errors':errors})
  context.close()
 # Restricted storage: preferences work for this visit; no roster writes/clears or crash.
 context=browser.new_context();context.add_init_script("Storage.prototype.getItem=function(){throw Error('blocked')};Storage.prototype.setItem=function(){throw Error('quota')};")
 page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)));page.goto(URL);page.wait_for_function('document.querySelectorAll(".table-toolbar").length===5')
 display=page.locator('#WeekCustom .table-options').nth(1);display.locator('summary').click();display.locator('[data-display-setting="font"]').evaluate('(e)=>{e.value=16;e.dispatchEvent(new Event("input",{bubbles:true}));}')
 assert '無法儲存' in display.locator('[data-display-status]').inner_text();assert not errors,errors
 context.close();browser.close()
assert all(r['geometry']['cols']==results[0]['geometry']['cols'] for r in results), 'Columns must stay fixed across viewport sizes'
(OUT/'browser-results.json').write_text(json.dumps({'results':results,'storage_blocked':True},indent=2,ensure_ascii=False))
print(json.dumps(results,ensure_ascii=False))
