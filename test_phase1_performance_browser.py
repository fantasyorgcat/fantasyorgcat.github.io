"""Real-snapshot regression checks for batched table updates and schedule sharing."""
from playwright.sync_api import sync_playwright
import json,sys,os
from pathlib import Path
URL=sys.argv[1] if len(sys.argv)>1 else 'http://127.0.0.1:8790/'
out=Path(sys.argv[2] if len(sys.argv)>2 else '/tmp/phase1-browser');out.mkdir(exist_ok=True,parents=True)
results=[]
with sync_playwright() as p:
 b=p.chromium.launch(executable_path=os.environ.get('CHROMIUM_PATH','/usr/bin/chromium'),headless=True,args=['--no-sandbox'])
 for width in [1440,390]:
  c=b.new_context(viewport={'width':width,'height':900});page=c.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  page.add_init_script('''window.__resizeTargets=new Map();const NativeResizeObserver=window.ResizeObserver;window.ResizeObserver=class extends NativeResizeObserver{constructor(cb){super(cb);this.targets=new Set();}observe(target,options){if(!this.targets.has(target)){this.targets.add(target);__resizeTargets.set(target,(__resizeTargets.get(target)||0)+1);}super.observe(target,options);}unobserve(target){if(this.targets.delete(target)){const n=__resizeTargets.get(target)-1;if(n)__resizeTargets.set(target,n);else __resizeTargets.delete(target);}super.unobserve(target);}disconnect(){for(const target of [...this.targets])this.unobserve(target);super.disconnect();}};''')
  page.goto(URL);page.wait_for_function("tables.WCustom&&document.querySelectorAll('.table-toolbar').length>=1");page.wait_for_timeout(200)
  assert page.evaluate('Object.keys(tables).length===1 && tables.WCustom.rows().nodes().length < tables.WCustom.rows().count()'), 'Hidden weeks/rows must remain deferred'
  page.evaluate('''()=>{const i=appliedSeasonWeek;openWeek({currentTarget:document.querySelectorAll('.tablinks')[1]},'Week2');selectPlatformWeek(String(i));}''')
  page.evaluate('''()=>{window.__insights=document.querySelector('#schedule-insights table');window.__draws=[];$(document).on('draw.dt.phase1',(_,s)=>__draws.push(s.nTable.id));window.__rosterBefore=JSON.stringify(localStorage);window.__dataBefore=JSON.stringify([playerCatalog,scheduleEvents]);}''')
  # The actual data is immutable and numeric/order values agree across all eight views.
  for period in ['season','l7','l14','ls']:
   for mode in ['avg','tot']:
    page.evaluate('''([period,mode])=>{__draws=[];switchStats(period,activeWeek,false);switchDisplayMode(mode,activeWeek,false);applyStatView(activeWeek);}''',[period,mode])
    page.wait_for_timeout(20)
    page.evaluate('''()=>{const t=tables[activeWeek],s=viewState[activeWeek],visible=t.columns().indexes().toArray().filter(i=>t.column(i).visible()),stat=visible.filter(i=>t.column(i).header().className.includes('stat-'));if(stat.length!==11)throw Error('Wrong visible stats '+stat.length);for(const i of stat){const h=t.column(i).header();if(!h.classList.contains('stat-'+s.period)||!h.classList.contains('stat-'+s.mode))throw Error('Wrong period/mode');}if(__draws.length!==1)throw Error('Duplicate draw '+__draws);for(const i of t.rows().indexes().toArray()){const pid=t.row(i).data()[0],p=playerCatalog[pid];for(const j of stat){const h=t.column(j).header(),metric=h.querySelector('.dt-column-title').textContent.trim(),cell=t.cell(i,j).node(),expected=p.periods[s.period][s.mode][metric];if(metric==='Rank'){if(t.cell(i,j).data().value!==expected.value || cell && cell.dataset.rankValue!==(expected.value===null?'':String(expected.value)))throw Error('Rank mismatch '+pid);}else{const actual=Number(t.cell(i,j).render('sort'));if(cell && Number(cell.dataset.order)!==actual)throw Error('DOM numeric mismatch');if(expected.value!==null&&Math.abs(actual-expected.value)>1e-6)throw Error('Numeric mismatch '+pid+' '+metric+' '+actual+' '+expected.value);}}}if(document.querySelector('#schedule-insights table')!==__insights)throw Error('Stats unnecessarily rebuilt insights');}''')
  page.evaluate('''()=>{const t=tables[activeWeek],col=t.column('.rank-ls-tot').index(),i=t.rows({page:'current'}).indexes()[0],saved=t.cell(i,col).node().firstChild;switchDisplayMode('AVG',activeWeek);switchDisplayMode('TOT',activeWeek);if(t.cell(i,col).node().firstChild!==saved)throw Error('Cached rank cells rewritten on view roundtrip');}''')
  # Pagination/search/order and even hidden table draws do not rebuild insights.
  page.evaluate("tables[activeWeek].search('Trae Young').draw();tables[activeWeek].search('').draw();tables[activeWeek].page('next').draw('page');tables.W2.draw(false)")
  assert page.evaluate("document.querySelector('#schedule-insights table')===__insights")
  page.evaluate("tables[activeWeek].page('first').draw('page')")
  # Every row's shared team schedule, including teams without games, matches the table data.
  page.evaluate('''()=>{const t=tables[activeWeek],shared=scheduleForTable(t.table().node()),days=t.columns('[data-schedule-day]').indexes().toArray();for(const row of t.rows().data().toArray()){const v=shared.get(row[1]);if(!v||String(v[0])!==String(row[2])||days.some((col,i)=>{const a=document.createElement('template'),b=document.createElement('template');a.innerHTML=v[i+1];b.innerHTML=row[col];return a.innerHTML!==b.innerHTML;}))throw Error('Shared schedule mismatch '+row[1]);}}''')
  # Comparison selection and custom ranks survive period/week/quick-tab transitions.
  page.locator('#WeekCustom input[data-pick="compare"]').first.check();pid=page.locator('#comparison-body tr').first.get_attribute('data-player-id')
  page.locator('#WeekCustom .table-options').first.locator('summary').click();page.locator('#WeekCustom').get_by_role('button',name='籃板 + FG%').click()
  page.evaluate('''()=>{const t=tables[activeWeek],s=viewState[activeWeek],r=Object.values(playerCatalog).map(p=>{const d=p.periods[s.period][s.mode];return{id:p.id,sum:d.REB.pr===null||d['FG%'].pr===null?null:d.REB.pr+d['FG%'].pr};});for(const v of r){const p=playerCatalog[v.id],rank=playerRank(p,s.period,s.mode);if(rank.sum!==v.sum||rank.value!==(v.sum===null?null:1+r.filter(x=>x.sum!==null&&x.sum>v.sum).length))throw Error('Custom rank incorrect');}}''')
  page.locator('#WeekCustom').get_by_role('button',name='恢復 9CAT').click()
  page.evaluate('''()=>{const t=tables[activeWeek],s=viewState[activeWeek],col=t.column('.rank-'+s.period+'-'+s.mode).index();for(const i of t.rows().indexes().toArray()){const id=t.row(i).data()[0],expected=playerCatalog[id].periods[s.period][s.mode].Rank.value;if(t.cell(i,col).data().value!==expected || t.cell(i,col).node() && t.cell(i,col).node().dataset.rankValue!==(expected===null?'':String(expected)))throw Error('Rank category cache failed to invalidate');}}''')
  page.locator('#WeekCustom').get_by_role('button',name='籃板 + FG%').click()
  page.locator('#season-week').select_option('1');page.wait_for_timeout(50)
  assert page.locator('#comparison-body tr[data-player-id="'+pid+'"]').count()==1
  page.locator('#schedule-extras summary').click();page.locator('#defaultOpen').click();page.wait_for_timeout(100)
  assert page.evaluate("activeWeek==='W1'&&tables.W1.columns('.stat-'+viewState.W1.period+'.stat-'+viewState.W1.mode).visible().toArray().every(Boolean)")
  assert page.locator('#comparison-body tr[data-player-id="'+pid+'"]').count()==1
  page.locator('#season-week').select_option('0')
  page.evaluate("document.querySelector('#teamTableWCustom tbody tr[data-team]').click()")
  assert page.locator('#schedule-insights tbody tr').count()==1
  page.locator('#show-all-players').click();assert page.locator('#schedule-insights tbody tr').count()>1
  page.evaluate("switchStats('L7',activeWeek);switchDisplayMode('AVG',activeWeek)")
  assert page.evaluate("tables[activeWeek].columns('.stat-l7.stat-avg').visible().toArray().every(Boolean)")
  assert page.evaluate("JSON.stringify([playerCatalog,scheduleEvents])===__dataBefore")
  assert page.evaluate("JSON.stringify(localStorage)===__rosterBefore")
  page.locator('#WeekCustom [data-display-setting="schedule"]').check()
  page.wait_for_timeout(50)
  page.evaluate('''()=>{const t=tables[activeWeek],dates=t.columns('[data-schedule-day]').header().toArray().map(h=>h.textContent),comparison=[...document.querySelectorAll('#comparison-head th')].slice(2,2+dates.length).map(h=>h.textContent);if(JSON.stringify(dates)!==JSON.stringify(comparison))throw Error('Comparison headers lag after deferred sizing');}''')
  page.locator('#WeekCustom [data-display-setting="schedule"]').uncheck()
  page.screenshot(path=str(out/f'phase1-{width}.png'))
  assert page.evaluate('[...__resizeTargets.keys()].every(t=>t.isConnected)'), 'Retired table still has a resize observer'
  assert not errors,errors
  results.append({'width':width,'all_eight_views_exact':True,'single_draw_per_view_change':True,'insights_not_rebuilt_on_search_sort_page':True,'shared_schedule_including_zero_games':True,'custom_rank':True,'comparison_week_and_quick_tab_preserved':True,'filter_refresh':True,'data_and_storage_unchanged':True,'errors':errors})
  c.close()
 b.close()
(out/'functional-results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2));print(json.dumps(results))
