(function(){
 'use strict';
 const C=RotoCore,packageData=ROTO_DATA,$=id=>document.getElementById(id),NS='http://www.w3.org/2000/svg';
 let period=packageData.default_period||packageData.period_key||'ls',data=packageData.extra_periods?.[period]||packageData,picker=null;
 const state={base:[],opponent:[],outgoing:[],incoming:[]};let mode='totals',saved=[],activeBase='';
 let opponents=[{id:'opponent',name:'對手 1',players:[],savedAt:''}],activeOpponent='opponent',opponentsWritable=true;const hiddenOpponents=new Set();
 const opponentColors=['#b48259','#798979','#9286a2','#829da1','#b99770'];
 const names={base:'原陣容',opponent:'對手',simulation:'換人後'},colors={base:'#516a78',simulation:'#a77581'};
 let radarEntries=[],radarPoints=[],radarLabels={},tooltipMetric=null,touchStart=null;
 const allPlayers=Object.values(packageData.players).sort((a,b)=>a.name.localeCompare(b.name));
 const selection=target=>target==='incoming'?simulation():state[target];
 const message=text=>{$('status').textContent=text;};
 function element(tag,text,cls){const e=document.createElement(tag);if(text!==undefined)e.textContent=text;if(cls)e.className=cls;return e;}
 function button(text,action,label){const e=element('button',text,'btn-stat');e.type='button';if(label)e.setAttribute('aria-label',label);e.addEventListener('click',action);return e;}
 function info(id){const p=data.players[id];return p?p.name+' · '+p.team:'未知球員 · ID '+id;}
 function simulation(){return C.simulate(state.base,state.outgoing,state.incoming);}
 function number(v,key){return v===null?'—':v.toFixed(key.endsWith('%')?1:mode==='totals'?0:1)+(key.endsWith('%')?'%':'');}
 function activeTeam(){return opponents.find(t=>t.id===activeOpponent);}
 function syncOpponent(){const team=activeTeam();state.opponent=team?team.players:[];names.opponent=team?team.name:'對手';}
 function persistOpponents(){if(!opponentsWritable)return;try{C.saveOpponents(localStorage,opponents.map(t=>({...t,savedAt:new Date().toISOString()})));$('opponents-status').textContent='已自動保存 '+opponents.length+' 支對手隊伍。';}catch(e){$('opponents-status').textContent='對手自動保存失敗：'+e.message+'。本次編輯仍可繼續，既有保存未清除。';}}
 function newOpponent(name,players=[]){if(!name){let n=1;do{name='對手 '+n++;}while(opponents.some(t=>t.name===name));}const id='opponent-'+crypto.randomUUID();opponents.push({id,name,players:C.ids(players),savedAt:''});activeOpponent=id;syncOpponent();$('add-target').value='opponent';persistOpponents();render();return id;}
 function opponentControls(){const select=$('active-opponent');select.replaceChildren();for(const team of opponents){const option=element('option',team.name+' · '+team.players.length+' 人');option.value=team.id;select.append(option);}select.value=activeOpponent;
  const team=activeTeam();$('opponent-name').value=team?team.name:'';$('opponent-name').disabled=!team;$('delete-opponent').disabled=!team;$('clear-opponent').disabled=!team;
  for(const id of ['add-target','save-target','load-target']){const option=$(id).querySelector('option[value="opponent"]');option.disabled=!team;option.textContent=team?'對手：'+team.name:'尚無對手';}
  const host=$('opponent-layers');host.replaceChildren();for(const team of opponents){const label=element('label'),input=element('input');input.type='checkbox';input.dataset.opponentLayer=team.id;input.checked=!hiddenOpponents.has(team.id);
   input.addEventListener('change',()=>{if(input.checked)hiddenOpponents.delete(team.id);else hiddenOpponents.add(team.id);render();});label.append(input,element('span',team.name+' · '+team.players.length+' 人'));host.append(label);
  }if(!opponents.length)host.append(element('small','尚未建立對手，從「對手比較」新增隊伍。'));
 }
 function reset(){state.outgoing=[];state.incoming=[];}
 function setRoster(target,values){if(target==='opponent'&&!activeTeam()){newOpponent('',values);return;}state[target]=C.ids(values);if(target==='base')reset();if(target==='opponent'){activeTeam().players=state.opponent;persistOpponents();}render();}
 function add(target,id){const current=target==='incoming'?simulation():state[target];if(current.includes(id)){message('這位球員已在'+(target==='incoming'?'換人後名單':names[target])+'，沒有重複加入。');return;}
  setRoster(target,[...state[target],id]);message('已加入 '+info(id));
 }
 function rosterList(target){const host=$(target+'-list');host.replaceChildren();for(const id of state[target]){const row=element('div',undefined,'roster-item'),label=element('span',info(id)),p=data.players[id];row.dataset.playerId=id;
  label.append(element('small',p&&p.gp?'GP '+p.gp+' · 每場分鐘 '+(p.minutes===null?'—':p.minutes.toFixed(1)):'此季別來源無資料／未匹配，統計為未知'));
  row.append(label,button('移除',()=>setRoster(target,state[target].filter(x=>x!==id)),'從'+(target==='incoming'?'模擬加入名單':names[target])+'移除 '+info(id)));host.append(row);
 }if(!state[target].length)host.append(element('small','尚未加入球員'));
 }
 function outgoingList(){const host=$('outgoing-list');host.replaceChildren();for(const id of state.base){const row=element('div',undefined,'roster-item'),label=element('label'),input=element('input');input.type='checkbox';input.dataset.outgoing=id;input.checked=state.outgoing.includes(id);
  input.addEventListener('change',()=>{state.outgoing=input.checked?C.ids([...state.outgoing,id]):state.outgoing.filter(x=>x!==id);render();});label.append(input,element('span',info(id)));row.append(label);host.append(row);
 }if(!state.base.length)host.append(element('small','先建立原陣容再選擇移出球員'));
 }
 function svg(tag,attributes,text){const e=document.createElementNS(NS,tag);for(const [key,v] of Object.entries(attributes))e.setAttribute(key,String(v));if(text!==undefined)e.textContent=text;return e;}
 function hideRadarTooltip(){tooltipMetric=null;$('radar-tooltip').hidden=true;}
 function showRadarTooltip(key,anchor){if(!radarEntries.length||!anchor){hideRadarTooltip();return;}const tip=$('radar-tooltip');
  if(tooltipMetric!==key||tip.hidden){tip.replaceChildren(element('strong',key==='TO'?'TO · 失誤越少越佳':key+' · 每場產效'),element('p',data.season+' 例行賽實績 · '+radarEntries.length+' 組陣容'));const list=element('ul');
   for(const entry of radarEntries){const cell=entry.team.cells[key],percent=key.endsWith('%'),value=cell.value===null?null:percent?cell.value:cell.value/cell.known,row=element('li');row.dataset.tooltipTeam=entry.target;row.dataset.value=value===null?'':String(value);row.dataset.total=cell.value===null?'':String(cell.value);
    const name=element('span',entry.name,'tooltip-team');name.style.setProperty('--series',entry.color);row.append(name,element('strong',value===null?'—':value.toFixed(2)+(percent?'%':'／人／場'),'tooltip-value'));
    row.append(element('small',cell.known+'/'+cell.total+' 人有資料'+(cell.partial?' · 已知部分':'')));
    if(cell.value!==null)row.append(element('small',percent?'命中 '+cell.made.toFixed(2)+'／出手 '+cell.attempts.toFixed(2)+'（每人各 1 場合計）':'每人各 1 場合計 '+cell.value.toFixed(2)));
    if(cell.reason)row.append(element('small',cell.reason));list.append(row);
   }tip.append(list,element('small','計數節點依成員每場平均定位；命中率依出手量加權。'));tooltipMetric=key;tip.dataset.metric=key;
  }
  tip.hidden=false;const host=$('radar'),matrix=host.getScreenCTM(),rect=$('radar-plot').getBoundingClientRect();if(!matrix)return;
  tip.style.maxHeight=Math.max(120,rect.height-16)+'px';const x=matrix.a*anchor.x+matrix.c*anchor.y+matrix.e-rect.left,y=matrix.b*anchor.x+matrix.d*anchor.y+matrix.f-rect.top;
  tip.style.left=Math.max(8,Math.min(x+14,rect.width-tip.offsetWidth-8))+'px';tip.style.top=Math.max(8,Math.min(y+14,rect.height-tip.offsetHeight-8))+'px';
 }
 function radarHit(event,radius=16){const label=event.target.closest?.('[data-radar-metric]');if(label)return {key:label.dataset.radarMetric,...radarLabels[label.dataset.radarMetric]};
  const matrix=$('radar').getScreenCTM();if(!matrix)return null;let nearest=null,distance=radius*radius;
  for(const p of radarPoints){const dx=matrix.a*p.x+matrix.c*p.y+matrix.e-event.clientX,dy=matrix.b*p.x+matrix.d*p.y+matrix.f-event.clientY,d=dx*dx+dy*dy;if(d<=distance){nearest=p;distance=d;}}return nearest;
 }
 $('radar').addEventListener('pointermove',e=>{if(e.pointerType==='touch')return;const hit=radarHit(e);if(hit)showRadarTooltip(hit.key,hit);else hideRadarTooltip();});
 $('radar-plot').addEventListener('pointerleave',e=>{if(e.pointerType!=='touch')hideRadarTooltip();});
 $('radar').addEventListener('pointerdown',e=>{if(e.pointerType==='touch')touchStart={x:e.clientX,y:e.clientY};});
 $('radar').addEventListener('pointercancel',()=>{touchStart=null;});
 $('radar').addEventListener('pointerup',e=>{if(e.pointerType!=='touch')return;const start=touchStart;touchStart=null;if(!start||Math.hypot(e.clientX-start.x,e.clientY-start.y)>8)return;const hit=radarHit(e,24);if(hit)showRadarTooltip(hit.key,hit);else hideRadarTooltip();});
 $('radar').addEventListener('focusin',e=>{const key=e.target.dataset.radarMetric;if(key)showRadarTooltip(key,radarLabels[key]);});
 $('radar').addEventListener('focusout',e=>{if(!$('radar-plot').contains(e.relatedTarget))hideRadarTooltip();});
 $('radar').addEventListener('keydown',e=>{const key=e.target.dataset.radarMetric;if(key&&['Enter',' '].includes(e.key)){e.preventDefault();showRadarTooltip(key,radarLabels[key]);}});
 document.addEventListener('keydown',e=>{if(e.key==='Escape')hideRadarTooltip();});document.addEventListener('pointerdown',e=>{if(!$('radar-plot').contains(e.target))hideRadarTooltip();});window.addEventListener('resize',hideRadarTooltip);
 function radar(teams){hideRadarTooltip();radarEntries=[];radarPoints=[];radarLabels={};const host=$('radar');host.replaceChildren(svg('title',{id:'radar-title'},'固定所選季別每場產效雷達；未知類別留白'),svg('desc',{id:'radar-description'},'原陣容、自訂對手隊伍與換人後，以每場產效比較，TO低為佳。滑鼠靠近節點、手機點選，或聚焦類別名稱，可查看各陣容實際數值；表格單位不改雷達口徑。'));
  const center=[230,184],radius=123,point=(i,score)=>{const angle=-Math.PI/2+i*2*Math.PI/9;return [center[0]+Math.cos(angle)*radius*score/100,center[1]+Math.sin(angle)*radius*score/100];},points=values=>values.map((v,i)=>point(i,v).join(',')).join(' ');
  for(const ring of [20,40,60,80,100])host.append(svg('polygon',{points:points(Array(9).fill(ring)),fill:'none',stroke:'#c9c2b8','stroke-width':1}));
  C.metrics.forEach((key,i)=>{const p=point(i,100),label=point(i,121);radarLabels[key]={x:label[0],y:label[1]};host.append(svg('line',{x1:center[0],y1:center[1],x2:p[0],y2:p[1],stroke:'#c9c2b8'}),svg('text',{x:label[0],y:label[1]+4,'text-anchor':'middle',fill:'#35434b','font-size':12,tabindex:0,role:'button','data-radar-metric':key,'aria-label':'查看 '+key+' 各陣容每場數值','aria-describedby':'radar-tooltip'},key==='TO'?'TO ↓':key));});
  const legend=$('legend');legend.replaceChildren();let plotted=false;
  for(const [target,team] of Object.entries(teams)){const opponent=opponents.find(t=>t.id===target);if(!(opponent?$('show-opponent').checked&&!hiddenOpponents.has(target):$('show-'+target).checked)||!team.size)continue;const scores=C.metrics.map(k=>team.scores[k]),color=opponent?opponentColors[opponents.indexOf(opponent)%opponentColors.length]:colors[target],dash=opponent?'6 4':target==='simulation'?'2 3':'';const group=svg('g',{'data-series':target});
   radarEntries.push({target,team,name:opponent?opponent.name:names[target],color});
   if(!team.partial&&scores.every(v=>v!==null))group.append(svg('polygon',{points:points(scores),fill:color,'fill-opacity':.1,stroke:color,'stroke-width':2,'stroke-dasharray':dash}));
   else for(let i=0;i<9;i++){const j=(i+1)%9;if(scores[i]!==null&&scores[j]!==null){const a=point(i,scores[i]),b=point(j,scores[j]);group.append(svg('line',{x1:a[0],y1:a[1],x2:b[0],y2:b[1],stroke:color,'stroke-width':2,'stroke-dasharray':dash}));}}
   scores.forEach((score,i)=>{if(score===null)return;const p=point(i,score);radarPoints.push({key:C.metrics[i],x:p[0],y:p[1]});group.append(svg('circle',{cx:p[0],cy:p[1],r:3.5,fill:color,'data-metric':C.metrics[i]}));plotted=true;});host.append(group);
   const label=element('span',(opponent?opponent.name:names[target])+' · '+team.size+' 人'+(team.partial?'（已知部分）':''));label.style.setProperty('--series',color);legend.append(label);
  }
  if(!plotted)host.append(svg('text',{x:230,y:190,'text-anchor':'middle',fill:'#5e6364','font-size':13},Object.values(teams).some(t=>C.metrics.some(k=>t.cells[k].value!==null))?'此季別基準樣本不足，請先查看數值':'加入有所選季別實績的球員後顯示'));
 }
 function metrics(teams){const targets=['base',...opponents.filter(t=>$('show-opponent').checked&&!hiddenOpponents.has(t.id)).map(t=>t.id),'simulation'],head=element('tr');for(const target of ['category',...targets,'delta']){const th=element('th',target==='category'?'類別':target==='delta'?'換人差異':opponents.find(t=>t.id===target)?.name||names[target]);th.scope='col';head.append(th);}$('metrics-head').replaceChildren(head);$('metrics-body').closest('table').style.minWidth=Math.max(320,85*(targets.length+2))+'px';const host=$('metrics-body'),delta=C.differences(teams.base,teams.simulation);host.replaceChildren();for(const key of C.metrics){const row=element('tr');row.dataset.metric=key;const title=element('th',key==='TO'?'TO ↓':key);title.scope='row';row.append(title);
  for(const target of targets){const cell=teams[target].cells[key],td=element('td',number(cell.value,key));td.dataset.team=target;td.dataset.value=cell.value===null?'':String(cell.value);
   td.append(element('small',(cell.partial?'已知小計 · ':'')+cell.known+'/'+cell.total+' 覆蓋'));if(cell.reason)td.append(element('small',cell.reason));else if(key.endsWith('%'))td.append(element('small',cell.made.toFixed(mode==='totals'?0:1)+' / '+cell.attempts.toFixed(mode==='totals'?0:1)));row.append(td);
  }
  const v=delta[key],good=v!==null&&(key==='TO'?v<0:v>0),td=element('td',v===null?'—':(v>0?'+':'')+v.toFixed(key.endsWith('%')?1:mode==='totals'?0:1)+(key.endsWith('%')?' pp':''),v===null||v===0?'':good?'delta-good':'delta-bad');td.dataset.delta=key;td.dataset.value=v===null?'':String(v);if(v!==null&&v!==0)td.append(element('small',good?'改善':'降低表現'));row.append(td);host.append(row);
 }}
 function togglePlayer(id,checked){const target=$('add-target').value;if(target==='incoming'){
   if(state.base.includes(id))state.outgoing=checked?state.outgoing.filter(v=>v!==id):C.ids([...state.outgoing,id]);
   else state.incoming=checked?C.ids([...state.incoming,id]):state.incoming.filter(v=>v!==id);render();
  }else setRoster(target,checked?[...state[target],id]:state[target].filter(v=>v!==id));
  message((checked?'已勾選 ':'已解除 ')+info(id)+' · '+(target==='incoming'?'換人後名單':names[target]));
 }
 function playerValue(player,key){const p=data.players[player.id],catalog=packageData.catalog?.[player.id]?.periods[period];
  if(key==='Rank')return catalog?.[mode==='totals'?'tot':'avg'].Rank.value??null;
  if(key==='GP')return p?.gp??null;if(key==='MIN')return p?.minutes??null;
  if(key.endsWith('%')&&p?.shots?.[key.slice(0,2)+'A']===0)return null;
  if(catalog&&catalog[mode==='totals'?'tot':'avg'][key].value!==null)return catalog[mode==='totals'?'tot':'avg'][key].value;
  return C.aggregate([player.id],data,mode).cells[key].value;
 }
 function playerDisplay(player,key){const value=playerValue(player,key),span=element('span',value===null?'—':key==='Rank'||key==='GP'?value.toFixed(0):number(value,key));
  const original=packageData.catalog?.[player.id]?.periods[period]?.[mode==='totals'?'tot':'avg']?.[key];
  if(value!==null&&original?.pr!==undefined&&original.pr!==null)span.append(element('small','PR '+original.pr.toFixed(1)));
  if(key==='FG%'&&data.players[player.id]?.uncertainties?.FGA)span.append(element('small','出手來源差異'));
  return span.outerHTML;
 }
 function syncPicks(){const selected=new Set(selection($('add-target').value));for(const input of document.querySelectorAll('[data-roto-pick]'))input.checked=selected.has(input.dataset.rotoPick);}
 function search(rebuild=false){if(!picker){const columns=[{title:'選取',data:'id',orderable:false,render:(id,type)=>{if(type!=='display')return id;const input=element('input');input.type='checkbox';input.dataset.rotoPick=id;input.setAttribute('aria-label','選取或解除 '+info(id));return input.outerHTML;}},
   {title:'球員',data:null,render:(p,type)=>{if(type!=='display')return p.name+' '+p.team;const label=element('span',p.name);label.append(element('small',p.team));return label.outerHTML;}}];
   for(const key of ['Rank','GP','MIN',...C.metrics])columns.push({title:key==='TO'?'TO ↓':key==='MIN'?'MIN／場':key,data:null,render:(p,type)=>type==='display'?playerDisplay(p,key):key==='Rank'&&playerValue(p,key)===null?Number.MAX_SAFE_INTEGER:playerValue(p,key)});
   picker=jQuery('#roto-player-table').DataTable({data:allPlayers,columns,pageLength:25,scrollX:true,order:[[2,'asc']],layout:{topStart:'pageLength',topEnd:null,bottomStart:'info',bottomEnd:'paging'},language:{lengthMenu:'每頁 _MENU_ 人',info:'_START_–_END_ / _TOTAL_ 人',infoFiltered:'（全體 _MAX_ 人）',zeroRecords:'沒有符合球員',infoEmpty:'0 人'}});
   picker.on('draw',syncPicks);
   const controls=document.querySelector('.picker-controls');new ResizeObserver(()=>document.documentElement.style.setProperty('--roto-picker-height',controls.getBoundingClientRect().height+'px')).observe(controls);
  }else if(rebuild)picker.rows().invalidate().draw(false).columns.adjust();
  const query=$('player-search').value;if(picker.search()!==query)picker.search(query).draw();syncPicks();
  $('search-count').textContent='正在編輯 '+($('add-target').value==='incoming'?'換人後名單':names[$('add-target').value])+' · 已勾選 '+selection($('add-target').value).length+' 人 · '+data.season+' · '+(mode==='totals'?'整季總量':'每人1場');
 }
 function render(rebuild=false){$('mode').value=mode;$('table-mode').value=mode;baseOptions();syncOpponent();opponentControls();const teams={base:C.knownView(C.aggregate(state.base,data,mode),data,mode)};for(const t of opponents)teams[t.id]=C.knownView(C.aggregate(t.players,data,mode),data,mode);teams.simulation=C.knownView(C.aggregate(simulation(),data,mode),data,mode);
  $('base-count').textContent=teams.base.size+' 人';$('opponent-count').textContent=opponents.length+' 隊 · 目前 '+state.opponent.length+' 人';$('simulation-count').textContent=state.outgoing.length+' 移出／'+state.incoming.length+' 加入';
  $('coverage').textContent='原陣容 '+teams.base.size+' 人 · GP資料 '+teams.base.gpKnown+'/'+teams.base.size+' · 所選季別球員出賽合計 '+teams.base.gp+'（不是聯盟已計入場數）';
  $('unit-note').textContent=mode==='perGame'?'每人 1 場：逐員所選季別總量 ÷ 個人 GP 後合計；投籃同口徑加權，不平均百分比。':'所選季別整季總量：逐員實績總量合計，含個人不同出賽數；不是聯盟每日先發已計入成績。';
  const radarTeams=mode==='perGame'?teams:Object.fromEntries(Object.entries(teams).map(([target,team])=>[target,C.knownView(C.aggregate(team.ids,data,'perGame'),data,'perGame')]));
  radar(radarTeams);metrics(teams);rosterList('base');rosterList('opponent');rosterList('incoming');outgoingList();search(rebuild);
 }
 function baseOptions(){if(!saved.some(r=>r.id===activeBase))activeBase='';for(const id of ['base-roster-select','base-roster-select-inline']){const host=$(id);host.replaceChildren(element('option','選擇已儲存的聯盟／陣容'));host.firstChild.value='';for(const r of saved){const option=element('option',r.name+' · '+r.players.length+' 人');option.value=r.id;host.append(option);}host.value=activeBase;}
  const entry=saved.find(r=>r.id===activeBase),dirty=entry&&JSON.stringify(entry.players)!==JSON.stringify(state.base);
  $('base-save-status').textContent=entry?'目前「'+entry.name+'」'+(dirty?'有未儲存的名單變更，請再按儲存。':'已儲存；可使用本區的「切換已儲存陣容」。'):'這份原陣容尚未儲存；不同聯盟請使用不同名稱。';
 }
 function savedOptions(selected=''){const host=$('saved-rosters');host.replaceChildren(element('option','選擇陣容'));host.firstChild.value='';for(const r of saved){const option=element('option',r.name+' · '+r.players.length+' 人');option.value=r.id;host.append(option);}host.value=selected;baseOptions();}
 function storageWarning(error){for(const id of ['storage-warning','base-storage-warning']){$(id).hidden=false;$(id).textContent='本地保存無法使用：'+error.message+'。本次編輯仍可繼續；既有資料未清除。';}}
 function saveRoster(name,players){if($('save-roster').disabled)return null;if(!name){message('請先替陣容命名。');return null;}if(!players.length){message('空陣容未保存。');return null;}
  const existing=saved.find(r=>r.name===name),entry={id:existing?existing.id:crypto.randomUUID(),name,players:[...players],savedAt:new Date().toISOString()},next=[...saved.filter(r=>r.id!==entry.id),entry];
  try{C.save(localStorage,next);saved=next;savedOptions(entry.id);for(const id of ['storage-warning','base-storage-warning'])$(id).hidden=true;message('已保存「'+name+'」至此裝置。');return entry;}catch(e){storageWarning(e);return null;}
 }
 function loadBase(entry){activeBase=entry.id;$('base-roster-name').value=entry.name;$('add-target').value='base';setRoster('base',entry.players);message('已載入原陣容「'+entry.name+'」；換人模擬已重設，其他保存未改動。');}
 for(const id of ['base-roster-select','base-roster-select-inline'])$(id).addEventListener('change',e=>{const entry=saved.find(r=>r.id===e.target.value);if(entry)loadBase(entry);else baseOptions();});
 $('save-base-roster').addEventListener('click',()=>{const entry=saveRoster($('base-roster-name').value.trim(),state.base);if(entry){activeBase=entry.id;render();}});
 $('new-base-roster').addEventListener('click',()=>{activeBase='';$('base-roster-name').value='';$('add-target').value='base';setRoster('base',[]);message('已建立空白原陣容；已儲存的聯盟／陣容仍保留。');});
 function setMode(value){mode=value;describeData();render(true);}
 for(const id of ['mode','table-mode'])$(id).addEventListener('change',e=>setMode(e.target.value));$('compare-efficiency').addEventListener('click',()=>setMode('perGame'));for(const target of ['base','opponent','simulation'])$('show-'+target).addEventListener('change',render);
 $('player-search').addEventListener('input',()=>search());$('add-target').addEventListener('change',search);
 $('roto-player-table').addEventListener('change',e=>{if(e.target.dataset.rotoPick)togglePlayer(e.target.dataset.rotoPick,e.target.checked);});
 $('view-roto-comparison').addEventListener('click',()=>document.querySelector('.roto-overview').scrollIntoView({behavior:'smooth'}));
 $('data-period').addEventListener('change',e=>{period=e.target.value;data=packageData.extra_periods?.[period]||packageData;describeData();render(true);});
 $('edit-base').addEventListener('click',()=>{$('base-editor').open=true;$('base-editor').scrollIntoView({behavior:'smooth',block:'start'});});
 $('active-opponent').addEventListener('change',e=>{activeOpponent=e.target.value;syncOpponent();$('add-target').value='opponent';render();});
 $('opponent-name').addEventListener('change',e=>{const team=activeTeam();if(!team)return;const name=e.target.value.trim();if(!name){e.target.value=team.name;message('隊伍名稱不可留白。');return;}team.name=name.slice(0,80);syncOpponent();persistOpponents();render();});
 $('add-opponent').addEventListener('click',()=>newOpponent());$('delete-opponent').addEventListener('click',()=>{opponents=opponents.filter(t=>t.id!==activeOpponent);hiddenOpponents.delete(activeOpponent);activeOpponent=opponents[0]?.id||'';syncOpponent();persistOpponents();render();});
 $('clear-base').addEventListener('click',()=>setRoster('base',[]));$('clear-opponent').addEventListener('click',()=>setRoster('opponent',[]));$('reset-simulation').addEventListener('click',()=>{reset();render();message('模擬已重設，原陣容不變。');});
 $('save-target').addEventListener('change',e=>{if(e.target.value==='opponent'&&activeTeam())$('roster-name').value=activeTeam().name;});
 $('save-roster').addEventListener('click',()=>{const target=$('save-target').value,entry=saveRoster($('roster-name').value.trim(),target==='simulation'?simulation():state[target]);if(entry&&target==='base'){activeBase=entry.id;$('base-roster-name').value=entry.name;}baseOptions();});
 $('load-roster').addEventListener('click',()=>{const entry=saved.find(r=>r.id===$('saved-rosters').value);if(!entry){message('先選擇已保存的陣容。');return;}const target=$('load-target').value;if(target==='base'){loadBase(entry);return;}if(target==='new-opponent')newOpponent(entry.name,entry.players);else{if(target==='opponent'&&activeTeam())activeTeam().name=entry.name;setRoster(target,entry.players);}message('已載入「'+entry.name+'」；使用目前快照，未知球員不補零。');});
 $('delete-roster').addEventListener('click',()=>{const entry=saved.find(r=>r.id===$('saved-rosters').value);if(!entry)return;const next=saved.filter(r=>r.id!==entry.id);try{C.save(localStorage,next);saved=next;savedOptions();message('已刪除這份本地保存。');}catch(e){storageWarning(e);}});
 function describeData(){$('period-label').textContent=data.season+' 例行賽實績 · 比較陣容體質與換人產效';$('snapshot-label').textContent=data.source_info?'來源 build '+data.source_info.publisher_build:'實績快照 '+data.generated_at;
 $('season-context').textContent=period==='season'?(data.stats_available?'正在使用本季實績：平均產效反映目前樣本，請搭配 GP 與每場分鐘看。':'本季尚無例行賽實績。可切到上季參考歷史體質，開季後有有效資料時預設使用本季。'):'正在使用 '+data.season+' 歷史實績：適合回顧體質，球員角色、分鐘與健康可能改變；不能直接當作本季或剩餘球季預測。有效本季資料出現後，重新開啟此頁會預設使用本季。';
 $('data-warning').hidden=true;$('basis-label').textContent='基準 '+data.reference.size+' 位有所選季別實績的參考球員；來源完整母體 '+data.reference.expected+' 位，已保存分母 '+data.reference.shooting_complete+' 位。基準版本：'+data.reference.id+'。';
 if(data.source_period&&data.source_period.source_period_start&&data.source_period.source_period_end)$('basis-label').textContent+=' 來源 '+data.source+'；來源賽季範圍（'+(data.source_period.timezone||'UTC')+'）：'+data.source_period.source_period_start+' 至 '+data.source_period.source_period_end+'。';
 if(data.source_period?.stats_through_game)$('snapshot-label').textContent+=' · 已完賽統計至 '+data.source_period.stats_through_game;
 if(data.fixture){$('data-warning').hidden=false;$('data-warning').textContent='UI TEST ONLY · 合成資料驗證；不可發布或當作真實球員數據。';}
 else if(data.source_info){$('data-warning').hidden=false;const s=data.mapping.summary;$('data-warning').textContent='BoxScore Lab／CC BY 4.0 · 2025–26二手例行賽實績，非官方全表驗證。名單 '+s.matched+'/'+s.catalog+' 唯一映射；其餘 '+s.not_in_source+' 位此來源無適用資料，保持未知。Jabari Smith Jr. FGA 存975／974來源差異，未裁定，選入時FG%未知。';}
 else if(!data.data_ready){$('data-warning').hidden=false;$('data-warning').textContent='所選季別資料尚未完整，保留已知小計與覆蓋率；缺投籃分母或固定完整母體時，相關雷達留白，不當成0。';}
  if(data.stats_available&&C.metrics.some(k=>k==='TO'?data.benchmark.perGame[k].mean===0:data.benchmark.perGame[k].sd===0)){$('data-warning').hidden=false;$('data-warning').textContent+=' 某些類別參考母體沒有可用尺度，該雷達軸留白，實際數值仍可查看。';}
 }
 const options=[...Object.entries(packageData.extra_periods||{}),[packageData.period_key||'ls',packageData]];for(const [key,entry] of options){const option=element('option',entry.season+(key==='season'?' 本季':key==='ls'?' 上季':' 封存')+(entry.stats_available===false?'（尚無例行賽實績）':''));option.value=key;$('data-period').append(option);}$('data-period').value=period;describeData();
 try{const stored=localStorage.getItem(C.opponentsKey);if(stored!==null){opponents=C.loadOpponents(localStorage);activeOpponent=opponents[0]?.id||'';}syncOpponent();}catch(e){opponentsWritable=false;$('opponents-status').textContent='對手保存無法讀取：'+e.message+'。既有內容不會覆寫，本次仍可編輯。';}
 try{saved=C.load(localStorage);savedOptions();}catch(e){storageWarning(e);if(e.code==='ROTO_SAVE_FORMAT'){$('save-roster').disabled=true;$('save-base-roster').disabled=true;$('delete-roster').disabled=true;}}
 try{const fragment=new URLSearchParams(location.hash.slice(1)).get('players');if(fragment)state.base=C.ids(fragment.split(',').filter(Boolean));}catch(e){message('帶入名單無法辨識：'+e.message);}
 if(matchMedia('(max-width:600px)').matches)for(const id of ['base-editor','opponent-editor','simulation-editor'])$(id).open=false;
 render();
})();
