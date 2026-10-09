/* NBA events remain in Eastern scoring dates; no platform period is inferred. */
(function(){
 'use strict';
 const byId=id=>document.getElementById(id),DAY=86400000,excluded=new Set(['cancelled','postponed','suspended']);
 const statusLabels={scheduled:'未開賽',in_progress:'進行中',final:'已完賽',postponed:'延賽',cancelled:'取消',suspended:'暫停',delayed:'延遲',unknown:'狀態待確認'};
 let customPeriod=null;
 function parseDate(value){const stamp=Date.parse(value+'T12:00:00Z');return Number.isFinite(stamp)&&new Date(stamp).toISOString().slice(0,10)===value?stamp:null;}
 function dates(start,end){const out=[];for(let stamp=parseDate(start);stamp<=parseDate(end);stamp+=DAY)out.push(new Date(stamp).toISOString().slice(0,10));return out;}
 function selectedPeriod(){
  if(activeWeek==='WCustom')return customPeriod;
  if(activeWeek==='WSeason')return seasonWeeks[Number(byId('season-week').value)];
  return quickPeriods[activeWeek];
 }
 function selectedEvents(period){return scheduleEvents.filter(e=>e.season_type===2&&e.date_et&&e.date_et>=period.start&&e.date_et<=period.end);}
 function eligible(e){return !excluded.has(e.status);}
 function remaining(e,now){return e.status==='scheduled'&&e.time_confirmed&&Date.parse(e.tipoff_utc)>now;}
 function summary(period,now){
  const selected=selectedEvents(period),daily=new Map(),teams=new Map();
  for(const e of scheduleEvents)if(e.date_et&&e.season_type===2&&eligible(e))daily.set(e.date_et,(daily.get(e.date_et)||0)+1);
  for(const e of selected)for(const team of [e.home,e.away]){
   if(!team)continue;
   const row=teams.get(team)||{team,games:0,remaining:0,pending:0,dates:[],light:0};
   if(eligible(e))row.games++;
   if(remaining(e,now)){row.remaining++;row.dates.push(e.date_et);if(daily.get(e.date_et)<=5)row.light++;}
   if(e.status==='unknown'||['postponed','suspended','delayed'].includes(e.status)||e.status==='scheduled'&&(!e.time_confirmed||Date.parse(e.tipoff_utc)<=now))row.pending++;
   teams.set(team,row);
  }
  for(const row of teams.values()){const days=new Set(row.dates);row.b2b=row.dates.filter(d=>days.has(new Date(parseDate(d)+DAY).toISOString().slice(0,10))).length;}
  return {selected,daily,teams};
 }
 function renderInsights(){
  const period=selectedPeriod();if(!period||!byId('schedule-insights'))return;
  const now=Date.now(),result=summary(period,now),box=byId('schedule-insights');box.replaceChildren();
  byId('schedule-period-context').textContent='美東 '+period.start+'–'+period.end+'（含迄日） · '+(activeWeek==='WCustom'?'自訂計分期間':'網站日曆期間')+' · 剩餘場次截止 '+new Date(now).toISOString().slice(0,16).replace('T',' ')+' UTC';
  const table=document.createElement('table'),head=table.createTHead().insertRow();
  for(const label of ['球隊','期間排程','尚未開賽','剩餘 B2B 組','剩餘低比賽日','待確認']){const th=document.createElement('th');th.textContent=label;head.appendChild(th);}
  const body=table.createTBody(),chosen=teamSelection[activeWeek];
  const rows=Array.from(result.teams.values()).filter(r=>!chosen||r.team===chosen).sort((a,b)=>b.remaining-a.remaining||b.light-a.light||a.team.localeCompare(b.team));
  for(const data of rows){const tr=body.insertRow();tr.dataset.team=data.team;for(const value of [data.team,data.games,data.remaining,data.b2b,data.light,data.pending])tr.insertCell().textContent=String(value);}
  if(!rows.length){const td=body.insertRow().insertCell();td.colSpan=6;td.textContent='這個期間沒有已公布日期的球隊賽程。';}box.appendChild(table);
  const pending=scheduleEvents.filter(e=>!e.date_et||excluded.has(e.status)),pendingBox=byId('schedule-pending');pendingBox.replaceChildren();
  if(pending.length){const p=document.createElement('p');p.textContent='當季待定／延賽／取消／暫停：'+pending.length+' 場，未計入尚未開賽。未公布的 NBA Cup 賽事不補造。';pendingBox.appendChild(p);const list=document.createElement('ul');for(const e of pending.slice(0,10)){const li=document.createElement('li');li.textContent=e.away+' @ '+e.home+' · '+(e.date_et||'日期待定')+' · '+statusLabels[e.status];list.appendChild(li);}pendingBox.appendChild(list);}
  const age=(now-Date.parse(scheduleGeneratedAt.replace(' UTC',':00Z').replace(' ','T')))/DAY;
  byId('schedule-freshness').textContent='資料快照：'+scheduleGeneratedAt+(age>2?' · 已超過 48 小時；狀態與改期可能已變更。':' · 賽事狀態以快照為準，非即時比分。');
 }
 function applyCustom(){
  const start=byId('period-start').value,end=byId('period-end').value,a=parseDate(start),b=parseDate(end),error=byId('period-error');
  if(a===null||b===null||b<a||(b-a)/DAY>=31){error.hidden=false;error.textContent='請輸入有效起訖日期，迄日不得早於起日，期間需為 1–31 天。';return;}
  error.hidden=true;customPeriod={start,end,label:'自訂期間 · '+start+'–'+end};
  const dayList=dates(start,end),events=selectedEvents(customPeriod),byTeam=new Map();
  for(const e of events)for(const side of ['home','away']){
   const team=e[side];if(!team)continue;
   const row=byTeam.get(team)||{games:0,days:dayList.map(()=> '')};
   if(eligible(e))row.games++;
   const i=dayList.indexOf(e.date_et);row.days[i]+=e[side+'_html'];byTeam.set(team,row);
  }
  const old=tables.WCustom,state=viewState.WCustom||{period:playerToolsMeta.defaultPeriod,mode:'avg'},search=old?old.search():'',chosen=teamSelection.WCustom;
  function headerKey(h){return h.textContent+'|'+h.className.split(' ').filter(c=>c.startsWith('stat-')||c.startsWith('rank-')).join(' ');}
  let order=null;if(old){order=old.order().map(([i,direction])=>({key:headerKey(old.column(i).header()),direction}));old.destroy();delete tables.WCustom;}
  const section=customPlayerTemplate.cloneNode(true),sourceDays=section.querySelectorAll('th[data-schedule-day]').length;
  for(const node of section.querySelectorAll('[id],[onclick]')){
   if(node.id)node.id=node.id.replace('W1','WCustom');
   if(node.hasAttribute('onclick'))node.setAttribute('onclick',node.getAttribute('onclick').replaceAll('W1','WCustom'));
  }
  const playerTable=section.querySelector('table'),headers=playerTable.tHead.rows[0];
  for(let i=0;i<sourceDays;i++)headers.deleteCell(3);
  dayList.forEach((date,i)=>{const th=document.createElement('th');th.dataset.scheduleDay=String(i);th.textContent=date+' ET';headers.insertBefore(th,headers.cells[3+i]);});
  for(const tr of playerTable.tBodies[0].rows){
   const data=byTeam.get(tr.cells[1].textContent)||{games:0,days:dayList.map(()=> '')};tr.cells[2].textContent=String(data.games);
   for(let i=0;i<sourceDays;i++)tr.deleteCell(3);
   data.days.forEach((html,i)=>{tr.insertCell(3+i).innerHTML=html;});
  }
  const content=byId('custom-period-content');content.replaceChildren();
  const teamSection=document.createElement('section');teamSection.className='team-section';const title=document.createElement('h3');title.textContent='球隊賽程 · 自訂美東期間';teamSection.appendChild(title);
  const scroll=document.createElement('div');scroll.className='schedule-scroll';const teamTable=document.createElement('table');teamTable.id='teamTableWCustom';const head=teamTable.createTHead().insertRow();
  for(const label of ['Team','Games',...dayList.map(d=>d+' ET')]){const th=document.createElement('th');th.textContent=label;head.appendChild(th);}
  const tbody=teamTable.createTBody();for(const [abbr,data] of Array.from(byTeam).sort()){
   const tr=tbody.insertRow();tr.className='team-row';tr.dataset.team=abbr;tr.onclick=()=>filterTeam(tr,abbr,'WCustom');if(chosen===abbr)tr.classList.add('selected');
   tr.insertCell().textContent=abbr;tr.insertCell().textContent=String(data.games);for(const html of data.days)tr.insertCell().innerHTML=html;
  }scroll.appendChild(teamTable);teamSection.appendChild(scroll);content.append(teamSection,section);
  byId('custom-period-heading').textContent=customPeriod.label;
  // Show the panel before DataTables measures its scroll columns.
  openWeek({currentTarget:byId('apply-custom-period')},'WeekCustom');
  const table=$(playerTable).DataTable({order:[[2,'desc']],pageLength:25,scrollX:true});tables.WCustom=table;table.column(1).visible(false);table.on('draw',()=>updateSelection('WCustom'));
  switchStats(state.period==='ls'?'LS':state.period==='season'?'Season':state.period.toUpperCase(),'WCustom');switchDisplayMode(state.mode.toUpperCase(),'WCustom');
  if(chosen)table.column(1).search('^'+$.fn.dataTable.util.escapeRegex(chosen)+'$',true,false);
  table.search(search);
  if(order){const mapped=order.map(o=>{const index=table.columns().indexes().toArray().find(i=>headerKey(table.column(i).header())===o.key);return [index===undefined?2:index,o.direction];});table.order(mapped);}
  table.columns.adjust().draw(false);document.dispatchEvent(new Event('active-week-changed'));
 }
 $(document).ready(function(){byId('apply-custom-period').addEventListener('click',applyCustom);document.addEventListener('active-week-changed',renderInsights);$(document).on('draw.dt',renderInsights);renderInsights();});
})();
