(function(){
 'use strict';
 const C=RotoCore,data=ROTO_DATA,$=id=>document.getElementById(id),NS='http://www.w3.org/2000/svg';
 const state={base:[],opponent:[],outgoing:[],incoming:[]};let mode='perGame',saved=[],limit=18;
 const names={base:'原陣容',opponent:'對手',simulation:'換人後'},colors={base:'#516a78',opponent:'#b48259',simulation:'#a77581'};
 const allPlayers=Object.values(data.players).sort((a,b)=>a.name.localeCompare(b.name));
 const message=text=>{$('status').textContent=text;};
 function element(tag,text,cls){const e=document.createElement(tag);if(text!==undefined)e.textContent=text;if(cls)e.className=cls;return e;}
 function button(text,action,label){const e=element('button',text,'btn-stat');e.type='button';if(label)e.setAttribute('aria-label',label);e.addEventListener('click',action);return e;}
 function info(id){const p=data.players[id];return p?p.name+' · '+p.team:'未知球員 · ID '+id;}
 function simulation(){return C.simulate(state.base,state.outgoing,state.incoming);}
 function number(v,key){return v===null?'—':v.toFixed(key.endsWith('%')?1:mode==='totals'?0:1)+(key.endsWith('%')?'%':'');}
 function reset(){state.outgoing=[];state.incoming=[];}
 function setRoster(target,values){state[target]=C.ids(values);if(target==='base')reset();render();}
 function add(target,id){const current=target==='incoming'?simulation():state[target];if(current.includes(id)){message('這位球員已在'+(target==='incoming'?'換人後名單':names[target])+'，沒有重複加入。');return;}
  state[target]=C.ids([...state[target],id]);if(target==='base')reset();render();message('已加入 '+info(id));
 }
 function rosterList(target){const host=$(target+'-list');host.replaceChildren();for(const id of state[target]){const row=element('div',undefined,'roster-item'),label=element('span',info(id)),p=data.players[id];row.dataset.playerId=id;
  label.append(element('small',p&&p.gp?'上季 GP '+p.gp+' · 每場分鐘 '+(p.minutes===null?'—':p.minutes.toFixed(1)):'此上季來源無資料／未匹配，統計為未知'));
  row.append(label,button('移除',()=>setRoster(target,state[target].filter(x=>x!==id)),'從'+(target==='incoming'?'模擬加入名單':names[target])+'移除 '+info(id)));host.append(row);
 }if(!state[target].length)host.append(element('small','尚未加入球員'));
 }
 function outgoingList(){const host=$('outgoing-list');host.replaceChildren();for(const id of state.base){const row=element('div',undefined,'roster-item'),label=element('label'),input=element('input');input.type='checkbox';input.dataset.outgoing=id;input.checked=state.outgoing.includes(id);
  input.addEventListener('change',()=>{state.outgoing=input.checked?C.ids([...state.outgoing,id]):state.outgoing.filter(x=>x!==id);render();});label.append(input,element('span',info(id)));row.append(label);host.append(row);
 }if(!state.base.length)host.append(element('small','先建立原陣容再選擇移出球員'));
 }
 function svg(tag,attributes,text){const e=document.createElementNS(NS,tag);for(const [key,v] of Object.entries(attributes))e.setAttribute(key,String(v));if(text!==undefined)e.textContent=text;return e;}
 function radar(teams){const host=$('radar');host.replaceChildren(svg('title',{id:'radar-title'},'固定上季實績參考雷達；未知類別留白'),svg('desc',{id:'radar-description'},'原陣容、對手與換人後最多三組，TO低為佳。實際數字及未知原因在比較表。'));
  const center=[230,184],radius=123,point=(i,score)=>{const angle=-Math.PI/2+i*2*Math.PI/9;return [center[0]+Math.cos(angle)*radius*score/100,center[1]+Math.sin(angle)*radius*score/100];},points=values=>values.map((v,i)=>point(i,v).join(',')).join(' ');
  for(const ring of [20,40,60,80,100])host.append(svg('polygon',{points:points(Array(9).fill(ring)),fill:'none',stroke:'#c9c2b8','stroke-width':1}));
  C.metrics.forEach((key,i)=>{const p=point(i,100),label=point(i,121);host.append(svg('line',{x1:center[0],y1:center[1],x2:p[0],y2:p[1],stroke:'#c9c2b8'}),svg('text',{x:label[0],y:label[1]+4,'text-anchor':'middle',fill:'#35434b','font-size':12},key==='TO'?'TO ↓':key));});
  const legend=$('legend');legend.replaceChildren();let plotted=false;
  for(const [target,team] of Object.entries(teams)){if(!$('show-'+target).checked||!team.size)continue;const scores=C.metrics.map(k=>team.scores[k]),color=colors[target],dash=target==='opponent'?'6 4':target==='simulation'?'2 3':'';const group=svg('g',{'data-series':target});
   if(scores.every(v=>v!==null))group.append(svg('polygon',{points:points(scores),fill:color,'fill-opacity':.1,stroke:color,'stroke-width':2,'stroke-dasharray':dash}));
   else for(let i=0;i<9;i++){const j=(i+1)%9;if(scores[i]!==null&&scores[j]!==null){const a=point(i,scores[i]),b=point(j,scores[j]);group.append(svg('line',{x1:a[0],y1:a[1],x2:b[0],y2:b[1],stroke:color,'stroke-width':2,'stroke-dasharray':dash}));}}
   scores.forEach((score,i)=>{if(score===null)return;const p=point(i,score);group.append(svg('circle',{cx:p[0],cy:p[1],r:3.5,fill:color,'data-metric':C.metrics[i]}));plotted=true;});host.append(group);
   const label=element('span',names[target]+' · '+team.size+' 人','series-'+target);legend.append(label);
  }
  if(!plotted)host.append(svg('text',{x:230,y:190,'text-anchor':'middle',fill:'#5e6364','font-size':13},'加入有上季實績的球員後顯示'));
 }
 function metrics(teams){const host=$('metrics-body'),delta=C.differences(teams.base,teams.simulation);host.replaceChildren();for(const key of C.metrics){const row=element('tr');row.dataset.metric=key;const title=element('th',key==='TO'?'TO ↓':key);title.scope='row';row.append(title);
  for(const target of ['base','opponent','simulation']){const cell=teams[target].cells[key],td=element('td',number(cell.value,key));td.dataset.team=target;td.dataset.value=cell.value===null?'':String(cell.value);
   td.append(element('small',cell.known+'/'+cell.total+' 覆蓋'));if(cell.reason)td.append(element('small',cell.reason));else if(key.endsWith('%'))td.append(element('small',cell.made.toFixed(mode==='totals'?0:1)+' / '+cell.attempts.toFixed(mode==='totals'?0:1)));row.append(td);
  }
  const v=delta[key],good=v!==null&&(key==='TO'?v<0:v>0),td=element('td',v===null?'—':(v>0?'+':'')+v.toFixed(key.endsWith('%')?1:mode==='totals'?0:1)+(key.endsWith('%')?' pp':''),v===null||v===0?'':good?'delta-good':'delta-bad');td.dataset.delta=key;td.dataset.value=v===null?'':String(v);if(v!==null&&v!==0)td.append(element('small',good?'改善':'降低表現'));row.append(td);host.append(row);
 }}
 function search(){const query=$('player-search').value.trim().toLocaleLowerCase(),target=$('add-target').value,selected=target==='incoming'?simulation():state[target],filtered=allPlayers.filter(p=>(p.name+' '+p.team).toLocaleLowerCase().includes(query));
  $('search-count').textContent=filtered.length+' 位符合 · 顯示 '+Math.min(limit,filtered.length)+' 位';const host=$('search-results');host.replaceChildren();for(const p of filtered.slice(0,limit)){const row=element('div',undefined,'search-result'),label=element('span',p.name+' · '+p.team),available=Object.values(p.shots).every(v=>v!==null);
   label.append(element('small',p.gp?'上季 '+p.gp+' 場 · '+(Object.keys(p.uncertainties||{}).length?'來源差異：FGA 未裁定':available?'有投籃分母':'投籃分母缺失'):'無上季實績'));const b=button(selected.includes(p.id)?'已加入':'加入',()=>add(target,p.id),'加入 '+p.name+' 至 '+(target==='incoming'?'換人模擬':names[target]));b.disabled=selected.includes(p.id);row.append(label,b);host.append(row);
  }$('more-results').hidden=limit>=filtered.length;
 }
 function render(){const teams={base:C.aggregate(state.base,data,mode),opponent:C.aggregate(state.opponent,data,mode),simulation:C.aggregate(simulation(),data,mode)};
  $('base-count').textContent=teams.base.size+' 人';$('opponent-count').textContent=teams.opponent.size+' 人';$('simulation-count').textContent=state.outgoing.length+' 移出／'+state.incoming.length+' 加入';
  $('coverage').textContent='原陣容 '+teams.base.size+' 人 · GP資料 '+teams.base.gpKnown+'/'+teams.base.size+' · 上季球員出賽合計 '+teams.base.gp+'（不是聯盟已計入場數）';
  $('unit-note').textContent=mode==='perGame'?'每人 1 場：逐員上季總量 ÷ 個人 GP 後合計；投籃同口徑加權，不平均百分比。':'上季實績總量：逐員真實總量合計，含個人不同出賽數；不是本季可用產量或聯盟已計入成績。';
  radar(teams);metrics(teams);rosterList('base');rosterList('opponent');rosterList('incoming');outgoingList();search();
 }
 function savedOptions(selected=''){const host=$('saved-rosters');host.replaceChildren(element('option','選擇陣容'));host.firstChild.value='';for(const r of saved){const option=element('option',r.name+' · '+r.players.length+' 人');option.value=r.id;host.append(option);}host.value=selected;}
 function storageWarning(error){$('storage-warning').hidden=false;$('storage-warning').textContent='本地保存無法使用：'+error.message+'。本次編輯仍可繼續；既有資料未清除。';}
 $('mode').addEventListener('change',e=>{mode=e.target.value;render();});for(const target of ['base','opponent','simulation'])$('show-'+target).addEventListener('change',render);
 $('player-search').addEventListener('input',()=>{limit=18;search();});$('add-target').addEventListener('change',search);$('more-results').addEventListener('click',()=>{limit+=18;search();});
 $('edit-base').addEventListener('click',()=>{$('base-editor').open=true;$('base-editor').scrollIntoView({behavior:'smooth',block:'start'});});
 $('clear-base').addEventListener('click',()=>setRoster('base',[]));$('clear-opponent').addEventListener('click',()=>setRoster('opponent',[]));$('reset-simulation').addEventListener('click',()=>{reset();render();message('模擬已重設，原陣容不變。');});
 $('save-roster').addEventListener('click',()=>{const name=$('roster-name').value.trim();if(!name){message('請先替陣容命名。');return;}const target=$('save-target').value,players=target==='simulation'?simulation():state[target];if(!players.length){message('空陣容未保存。');return;}
  const existing=saved.find(r=>r.name===name),entry={id:existing?existing.id:crypto.randomUUID(),name,players:[...players],savedAt:new Date().toISOString()},next=[...saved.filter(r=>r.id!==entry.id),entry];
  try{C.save(localStorage,next);saved=next;savedOptions(entry.id);message('已保存「'+name+'」至此裝置。');}catch(e){storageWarning(e);}
 });
 $('load-roster').addEventListener('click',()=>{const entry=saved.find(r=>r.id===$('saved-rosters').value);if(!entry){message('先選擇已保存的陣容。');return;}setRoster($('load-target').value,entry.players);message('已載入「'+entry.name+'」；使用目前快照，未知球員不補零。');});
 $('delete-roster').addEventListener('click',()=>{const entry=saved.find(r=>r.id===$('saved-rosters').value);if(!entry)return;const next=saved.filter(r=>r.id!==entry.id);try{C.save(localStorage,next);saved=next;savedOptions();message('已刪除這份本地保存。');}catch(e){storageWarning(e);}});
 $('period-label').textContent=data.season+' 例行賽實績 · 不代表新季預測或實際聯盟排名';$('snapshot-label').textContent=data.source_info?'來源 build '+data.source_info.publisher_build:'實績快照 '+data.generated_at;
 $('basis-label').textContent='基準 '+data.reference.size+' 位有上季實績的參考球員；來源完整母體 '+data.reference.expected+' 位，已保存分母 '+data.reference.shooting_complete+' 位。基準版本：'+data.reference.id+'。';
 if(data.source_period&&data.source_period.source_period_start&&data.source_period.source_period_end)$('basis-label').textContent+=' 來源 '+data.source+'；統計視窗（'+(data.source_period.timezone||'UTC')+'）：'+data.source_period.source_period_start+' 至 '+data.source_period.source_period_end+'。';
 if(data.fixture){$('data-warning').hidden=false;$('data-warning').textContent='UI TEST ONLY · 合成資料驗證；不可發布或當作真實球員數據。';}
 else if(data.source_info){$('data-warning').hidden=false;const s=data.mapping.summary;$('data-warning').textContent='BoxScore Lab／CC BY 4.0 · 2025–26二手例行賽實績，非官方全表驗證。名單 '+s.matched+'/'+s.catalog+' 唯一映射；其餘 '+s.not_in_source+' 位此來源無適用資料，保持未知。Jabari Smith Jr. FGA 存975／974來源差異，未裁定，選入時FG%未知。';}
 else if(!data.data_ready){$('data-warning').hidden=false;$('data-warning').textContent='資料尚未齊全：目前不能完成完整九項 ROTO 體質分析。FG／FT 缺命中／出手分母，雷達留白；此實績參考群也尚未涵蓋完整來源母體。七項計數仍可檢查，不能用它取代完整九項驗收。';}
 try{saved=C.load(localStorage);savedOptions();}catch(e){storageWarning(e);if(e.code==='ROTO_SAVE_FORMAT'){$('save-roster').disabled=true;$('delete-roster').disabled=true;}}
 try{const fragment=new URLSearchParams(location.hash.slice(1)).get('players');if(fragment)state.base=C.ids(fragment.split(',').filter(Boolean));}catch(e){message('帶入名單無法辨識：'+e.message);}
 if(matchMedia('(max-width:600px)').matches)for(const id of ['base-editor','opponent-editor','simulation-editor'])$(id).open=false;
 render();
})();
