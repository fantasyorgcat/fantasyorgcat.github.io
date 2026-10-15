/* Fixed data columns, selected-category PR ranks and device-local display preferences. */
(function(root){
 'use strict';
 const categories=['PTS','REB','AST','3PM','STL','BLK','FG%','FT%','TO'];
 const defaults={font:14,padding:6,dayWidth:84,schedule:false};
 const storageKey='fantasyorgcat:table-display:v1';
 function preferences(value){
  const p={...defaults};
  if(value&&typeof value==='object'){
   for(const [key,min,max] of [['font',13,18],['padding',4,14],['dayWidth',64,120]])
    if(Number.isFinite(value[key]))p[key]=Math.max(min,Math.min(max,Math.round(value[key])));
   if(typeof value.schedule==='boolean')p.schedule=value.schedule;
  }
  return p;
 }
 function rankPlayers(catalog,period,mode,selected){
  const keys=categories.filter(k=>selected.includes(k)),original=keys.length===categories.length,result={};
  for(const p of Object.values(catalog)){
   const cells=p.periods[period][mode],values=keys.map(k=>cells[k].pr);
   const sum=keys.length&&values.every(Number.isFinite)?values.reduce((a,b)=>a+b,0):null;
   result[p.id]=original?{...cells.Rank}:{value:null,sum};
  }
  if(!original){
   const complete=Object.values(result).filter(c=>c.sum!==null).sort((a,b)=>b.sum-a.sum);
   let previous=null,rank=0;
   complete.forEach((c,i)=>{if(c.sum!==previous)rank=i+1;c.value=rank;previous=c.sum;});
  }
  return result;
 }
 if(typeof module!=='undefined'&&module.exports){module.exports={categories,rankPlayers,preferences};return;}
 let selected=[...categories],prefs={...defaults},ready=false,storageAvailable=true;
 const rankCache=new Map(),updatedRanks=new WeakMap(),installed=new WeakSet(),sized=new WeakSet();
 function ranks(period,mode){
  const key=period+'|'+mode+'|'+selected.join(',');
  if(!rankCache.has(key))rankCache.set(key,rankPlayers(playerCatalog,period,mode,selected));
  return rankCache.get(key);
 }
 root.playerRank=(player,period,mode)=>ranks(period,mode)[player.id];
 root.playerRankLabel=()=>selectionLabel();
 function node(tag,text,className){const e=document.createElement(tag);if(text)e.textContent=text;if(className)e.className=className;return e;}
 function button(text,action){const e=node('button',text,'btn-stat');e.type='button';e.addEventListener('click',action);return e;}
 function activeTable(){return tables[activeWeek];}
 function selectionLabel(){return selected.length===9?'9CAT':selected.length?selected.join(' + '):'尚未選擇';}
 function updateLabels(){
  document.querySelectorAll('[data-rank-category]').forEach(e=>{e.checked=selected.includes(e.dataset.rankCategory);});
  document.querySelectorAll('[data-rank-summary]').forEach(e=>{e.textContent='排名項目 · '+selectionLabel();});
  document.querySelectorAll('[data-rank-description]').forEach(e=>{e.textContent=selected.length===9?'9CAT：保留原始全體排名，顯示九項 PR 合計；MIN 不計入。':selected.length?'自訂 Rank：以網站名單中資料完整的球員排名；加總所選 PR，同分並列。搜尋或篩選球隊不改變排名。':'請至少勾選一項；未選項目時不計算排名。';});
  document.querySelectorAll('[data-display-setting]').forEach(e=>{const key=e.dataset.displaySetting;if(e.type==='checkbox')e.checked=prefs[key];else e.value=String(prefs[key]);const output=e.parentElement.querySelector('output');if(output)output.textContent=String(prefs[key])+' px';});
  document.querySelectorAll('[data-display-status]').forEach(e=>{e.textContent=storageAvailable?'顯示設定儲存在此瀏覽器；可隨時恢復預設。':'瀏覽器無法儲存設定；本次調整仍可使用。';});
 }
 function choose(keys){
  selected=categories.filter(k=>keys.includes(k));rankCache.clear();updateLabels();
  const table=activeTable();if(table){updateRank(table,activeWeek);const state=viewState[activeWeek];table.order([table.column('.rank-'+state.period+'-'+state.mode).index(),'asc']).draw(false);}
  document.dispatchEvent(new Event('player-rank-changed'));
 }
 function updateRank(table,suffix){
  const state=viewState[suffix]||{period:playerToolsMeta.defaultPeriod,mode:'avg'},selector='.rank-'+state.period+'-'+state.mode;
  const index=table.column(selector).index();if(index===undefined)return;
  const container=table.table().container(),signature=state.period+'|'+state.mode+'|'+selected.join(',');
  if(updatedRanks.get(container)===signature)return;
  const values=ranks(state.period,state.mode),header=table.column(index).header();
  header.title=selected.length===9?'九項 PR 加總的全體排名；數字越小越前面':'所選 PR 加總的網站名單排名；數字越小越前面';
  table.rows().every(function(){
   const row=this.node(),id=row.querySelector('[data-player-id]')?.dataset.playerId,c=values[id];if(!c)return;
   const td=table.cell(this.index(),index).node(),order=String(c.value??1000000000);
   td.dataset.order=order;td.dataset.rankValue=c.value===null?'':String(c.value);td.dataset.rankSum=c.sum===null?'':String(c.sum);
   td.replaceChildren(node('span',c.value===null?'—':String(c.value),'rank-value'));
   if(c.sum!==null)td.appendChild(node('small','Σ PR '+c.sum.toFixed(1),'rank-sum'));
   td.title=c.sum===null?'所選項目 PR 不完整，無排名':'PR 合計 '+String(c.sum)+'；'+selectionLabel();
   table.cell(this.index(),index).invalidate('dom');
  });
  updatedRanks.set(container,signature);
 }
 function setPreferences(){
  const body=document.body;body.style.setProperty('--table-font',prefs.font+'px');body.style.setProperty('--table-padding',prefs.padding+'px');body.style.setProperty('--schedule-width',prefs.dayWidth+'px');
  updateLabels();
  Object.entries(tables).forEach(([suffix,table])=>{table.columns('[data-schedule-day]').visible(prefs.schedule,false);table.columns.adjust().draw(false);sizeTable(table);});
  sizeTeams();
 }
 function savePreferences(){
  try{localStorage.setItem(storageKey,JSON.stringify(prefs));storageAvailable=true;}catch{storageAvailable=false;}
  setPreferences();
 }
 function install(table){
  const container=table.table().container();if(installed.has(container))return;installed.add(container);
  const playerTitle=table.column(0).header().querySelector('.dt-column-title');if(playerTitle)playerTitle.textContent='球員';
  const games=table.column(2).header().querySelector('.dt-column-title');if(games)games.textContent='場次';
  const toolbar=node('div',null,'table-toolbar'),rankDetails=node('details',null,'table-options');
  const rankSummary=node('summary');rankSummary.dataset.rankSummary='';rankDetails.appendChild(rankSummary);
  const choices=node('fieldset',null,'rank-choices');choices.appendChild(node('legend','勾選要補強的數據'));
  for(const key of categories){const label=node('label'),input=node('input');input.type='checkbox';input.dataset.rankCategory=key;input.checked=selected.includes(key);input.addEventListener('change',()=>choose(input.checked?[...selected,key]:selected.filter(k=>k!==key)));label.append(input,node('span',key==='TO'?'TO ↓':key));choices.appendChild(label);}
  rankDetails.append(choices,button('恢復 9CAT',()=>choose(categories)),button('籃板 + FG%',()=>choose(['REB','FG%'])));
  const explanation=node('p');explanation.dataset.rankDescription='';rankDetails.append(explanation,node('p','使用未四捨五入的 PR 加總；TO 越少 PR 越高，缺值不當成 0。這不是聯盟 ROTO 積分。'));
  const display=node('details',null,'table-options');display.appendChild(node('summary','顯示設定'));
  const controls=node('div',null,'display-controls');
  for(const [key,title,min,max] of [['font','數據字級',13,18],['padding','列間距',4,14],['dayWidth','球員表賽程欄寬',64,120]]){
   const label=node('label'),input=node('input');input.type='range';input.min=min;input.max=max;input.step=1;input.dataset.displaySetting=key;input.setAttribute('aria-label',title);
   input.addEventListener('input',()=>{prefs[key]=Number(input.value);savePreferences();});label.append(node('span',title),input,node('output'));controls.appendChild(label);
  }
  display.append(controls,button('恢復預設外觀',()=>{prefs={...defaults};savePreferences();}));const status=node('p');status.dataset.displayStatus='';status.setAttribute('role','status');display.appendChild(status);
  const schedule=node('label',null,'schedule-toggle'),input=node('input');input.type='checkbox';input.dataset.displaySetting='schedule';input.addEventListener('change',()=>{prefs.schedule=input.checked;savePreferences();});schedule.append(input,node('span','同時顯示逐日賽程'));
  toolbar.append(rankDetails,display,schedule);container.before(toolbar);
  const scroll=container.querySelector('.dt-scroll'),body=scroll.querySelector('.dt-scroll-body'),bar=node('div',null,'table-x-scroll');bar.tabIndex=0;bar.setAttribute('role','region');bar.setAttribute('aria-label','左右捲動完整球員數據');bar.appendChild(node('div'));scroll.before(bar);
  bar.addEventListener('scroll',()=>{if(Math.abs(body.scrollLeft-bar.scrollLeft)>1)body.scrollLeft=bar.scrollLeft;});body.addEventListener('scroll',()=>{if(Math.abs(bar.scrollLeft-body.scrollLeft)>1)bar.scrollLeft=body.scrollLeft;});
  const hint=node('div',null,'table-scroll-hint');hint.append(node('span','欄名與球員固定；左右滑動查看全部欄位。'),button('跳至 Rank →',()=>{body.scrollLeft=body.scrollWidth;}),button('← 球員',()=>{body.scrollLeft=0;}));bar.before(hint);
  table.on('column-sizing',()=>sizeTable(table));
  new ResizeObserver(()=>sizeTable(table)).observe(container);
  updateLabels();
 }
 function shortDate(header){
  const text=header.textContent.trim();if(/^\d{4}-\d{2}-\d{2}/.test(text)){header.title=text;header.setAttribute('aria-label',text);header.dataset.fullDate=text;const label=header.querySelector('.dt-column-title')||header;label.textContent=text.slice(5).replace('-','/');}
 }
 function sizeTable(table){
  const container=table.table().container();if(!container.offsetWidth||sized.has(container))return;sized.add(container);
  try{
   const visible=table.columns().indexes().toArray().filter(i=>table.column(i).visible());
   const available=container.clientWidth-2,rankWidth=Math.ceil(prefs.font*7),numberWidth=Math.ceil(prefs.font*6.25);
   const widths=visible.map(i=>{const h=table.column(i).header();if(h.hasAttribute('data-schedule-day')){shortDate(h);return prefs.dayWidth;}return i===0?160:i===2?64:h.textContent.trim()==='Rank'?rankWidth:numberWidth;});
   const width=widths.reduce((a,b)=>a+b,0);
   const frame=container.querySelector('.dt-scroll');frame.style.width=Math.min(width+2,container.clientWidth)+'px';frame.style.maxWidth='100%';
   container.querySelectorAll('.dt-scroll table').forEach(t=>{t.style.setProperty('width',width+'px','important');t.style.tableLayout='fixed';t.style.margin='0';const cols=t.querySelectorAll('colgroup col');cols.forEach((col,i)=>{col.style.setProperty('width',widths[i]+'px','important');col.style.setProperty('min-width',widths[i]+'px','important');});});
   const inner=container.querySelector('.dt-scroll-headInner');inner.style.width=width+'px';
   const bar=container.querySelector('.table-x-scroll');if(bar){bar.style.width=Math.min(width,available)+'px';bar.firstChild.style.width=width+'px';bar.hidden=width<=available+1;bar.previousElementSibling.hidden=bar.hidden;bar.scrollLeft=container.querySelector('.dt-scroll-body').scrollLeft;}
  }finally{sized.delete(container);}
 }
 function sizeTeams(){
  document.querySelectorAll('.team-section').forEach(section=>{
   const table=section.querySelector('table');if(!table)return;
   table.style.width='100%';table.style.tableLayout='auto';
   const headers=Array.from(table.tHead?.rows[0]?.cells||[]);
   table.style.minWidth=(128+Math.max(0,headers.length-2)*100)+'px';
   headers.forEach((h,i)=>{h.style.width=i<2?'64px':'';if(i>=2)shortDate(h);});
   table.querySelectorAll('colgroup col').forEach((col,i)=>{col.style.width=i<2?'64px':'';col.style.minWidth='';});
   const rows=Array.from(table.tBodies[0]?.rows||[]).slice(0,6);
   const scroll=section.querySelector('.schedule-scroll'),gutter=Math.max(0,scroll.offsetHeight-scroll.clientHeight-2);
   scroll.style.height=(table.tHead.getBoundingClientRect().height+rows.reduce((sum,row)=>sum+row.getBoundingClientRect().height,0)+2+gutter)+'px';
  });
 }
 function enhance(suffix){
  const table=tables[suffix];if(!table)return;install(table);updateRank(table,suffix);
  const state=viewState[suffix]||{period:playerToolsMeta.defaultPeriod,mode:'avg'},rankColumn=table.column('.rank-'+state.period+'-'+state.mode).index();
  table.order(table.order().map(([index,direction])=>[table.column(index).header().className.includes('rank-')?rankColumn:index,direction]));
  table.columns('[data-schedule-day]').visible(prefs.schedule,false);table.columns.adjust().draw(false);sizeTable(table);sizeTeams();
 }
 const apply=root.applyStatView;root.applyStatView=function(suffix){apply(suffix);if(ready)enhance(suffix);};
 $(document).ready(function(){
  try{prefs=preferences(JSON.parse(localStorage.getItem(storageKey)));}catch{storageAvailable=false;}
  ready=true;Object.keys(tables).forEach(enhance);setPreferences();
  $(document).on('draw.dt',(_,settings)=>{if(settings.nTable.id.startsWith('playerTable'))sizeTable(new $.fn.dataTable.Api(settings));});
  document.addEventListener('active-week-changed',()=>{enhance(activeWeek);updateLabels();});
 });
})(typeof window==='undefined'?globalThis:window);
