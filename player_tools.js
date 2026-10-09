/* Active-table schedule comparison; no storage, telemetry or requests. */
(function(){
 'use strict';
 const compared=new Set(),metrics=['GP','MIN','PTS','REB','AST','3PM','STL','BLK','FG%','FT%','TO','Rank'],byId=id=>document.getElementById(id);
 let period=playerToolsMeta.defaultPeriod,mode='avg',sortKey='name',descending=false;
 function sync(){document.querySelectorAll('input[data-pick="compare"]').forEach(i=>{i.checked=compared.has(i.dataset.playerId);});}
 function button(text,action,label){const b=document.createElement('button');b.type='button';b.textContent=text;b.className='btn-stat';if(label)b.setAttribute('aria-label',label);b.addEventListener('click',action);return b;}
 function value(p,key){return key==='name'?p.name:key==='GP'?p.periods[period].gp:p.periods[period][mode][key].value;}
 function render(){
  if(!byId('comparison-head'))return;sync();byId('comparison-panel').hidden=!compared.size;
  const body=byId('comparison-body');body.replaceChildren();if(!compared.size)return;
  const table=tables[activeWeek],head=byId('comparison-head');head.replaceChildren();const tr=document.createElement('tr');
  function sortable(key,label){const th=document.createElement('th'),b=button(label,()=>{descending=sortKey===key?!descending:!['name','Rank','TO'].includes(key);sortKey=key;render();});if(key==='TO')b.title='失誤越少PR越高';b.dataset.sort=key;b.setAttribute('aria-label',label+'，'+(sortKey===key?(descending?'目前降序':'目前升序'):'可排序'));th.appendChild(b);tr.appendChild(th);}
  sortable('name','球員');const games=document.createElement('th');games.textContent='場次';tr.appendChild(games);
  const dayColumns=table?table.columns('[data-schedule-day]').indexes().toArray():[];
  const schedule=new Map();if(table)table.rows({search:'none'}).data().toArray().forEach(row=>{if(!schedule.has(row[1]))schedule.set(row[1],[row[2],...dayColumns.map(i=>row[i])]);});
  for(const column of dayColumns){const th=document.createElement('th');th.textContent=table.column(column).header().textContent;tr.appendChild(th);}
  for(const key of metrics)sortable(key,key);tr.lastChild.title='九項PR加總（含TO、不含MIN）的全體排名；同分並列，缺納入PR無排名';head.appendChild(tr);
  const rows=Array.from(compared,id=>playerCatalog[id]).filter(Boolean);
  rows.sort((a,b)=>{const x=value(a,sortKey),y=value(b,sortKey);if(x===null)return y===null?0:1;if(y===null)return -1;const n=typeof x==='number'?x-y:String(x).localeCompare(String(y));return(descending?-n:n)||a.id.localeCompare(b.id);});
  for(const p of rows){
   const row=document.createElement('tr');row.dataset.playerId=p.id;const name=row.insertCell();name.textContent=p.name+' · '+p.team;name.appendChild(button('移除',()=>{compared.delete(p.id);render();},'從比較移除 '+p.name));
   const fixtures=schedule.get(p.team),count=row.insertCell();count.textContent=fixtures?String(fixtures[0]):'—';count.title=fixtures?'目前週次場次':'此球隊賽程資料暫缺';
   for(let d=0;d<dayColumns.length;d++){const td=row.insertCell();td.className='comparison-matchup';if(fixtures){const template=document.createElement('template');template.innerHTML=fixtures[d+1];td.appendChild(template.content.cloneNode(true));if(!td.textContent.trim())td.title='當日無賽程';}else{td.textContent='—';td.title='賽程資料暫缺';}}
   for(const metric of metrics){const td=row.insertCell(),v=value(p,metric);td.dataset.metric=metric;td.dataset.value=v===null?'':String(v);td.textContent=v===null?'—':['GP','Rank'].includes(metric)||(mode==='tot'&&['PTS','REB','AST','3PM','STL','BLK','TO'].includes(metric))?String(v):v.toFixed(1)+(metric.endsWith('%')?'%':'');if(metric!=='GP'&&v!==null){const pr=p.periods[period][mode][metric].pr;if(pr!==null){const small=document.createElement('small');small.textContent='PR '+Math.round(pr);td.appendChild(small);}}}body.appendChild(row);
  }
  const names={season:'本季 '+playerToolsMeta.season,l7:'近7天',l14:'近14天',ls:'上季 '+playerToolsMeta.lastSeason};
  const label=activeWeek==='WSeason'?byId('season-week-heading').textContent:activeWeek==='WCustom'?byId('custom-period-heading').textContent:document.querySelector('.tablinks.active').textContent;
  byId('comparison-meta').textContent=label+' · '+names[period]+' · '+mode.toUpperCase();
 }
 $(document).ready(function(){
  byId('comparison-period').value=period;byId('comparison-period').addEventListener('change',e=>{period=e.target.value;render();});byId('comparison-mode').addEventListener('change',e=>{mode=e.target.value;render();});byId('clear-comparison').addEventListener('click',()=>{compared.clear();render();});
  document.addEventListener('change',e=>{const input=e.target;if(!input.matches('input[data-pick="compare"]'))return;const id=input.dataset.playerId;if(!playerCatalog[id])return;if(input.checked)compared.add(id);else compared.delete(id);render();});
  $(document).on('draw.dt',render);document.addEventListener('active-week-changed',render);sync();
 });
})();
