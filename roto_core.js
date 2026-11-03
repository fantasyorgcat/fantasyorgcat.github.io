/* Pure last-season aggregation and roster transitions, shared by browser and Node tests. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.RotoCore=api;})(globalThis,function(){
 'use strict';
 const counting=['PTS','REB','AST','3PM','STL','BLK','TO'],metrics=['PTS','REB','AST','3PM','STL','BLK','FG%','FT%','TO'],storageKey='fantasyorgcat:roto:rosters:v1',opponentsKey='fantasyorgcat:roto:opponents:v1';
 function ids(values){return [...new Set(values.map(v=>{const id=String(v);if(!/^\d+$/.test(id))throw Error('球員 ID 格式錯誤');return id;}))];}
 const valid=v=>typeof v==='number'&&Number.isFinite(v)&&v>=0,absent=p=>!!p&&p.gp===0;
 function score(value,key,baseline){
  if(!valid(value)||!baseline||!valid(baseline.mean))return null;
  if(key==='TO')return baseline.mean>0?100/(1+value/baseline.mean):null;
  return !valid(baseline.sd)||!baseline.sd?null:Math.max(0,Math.min(100,50+15*(value-baseline.mean)/baseline.sd));
 }
 function aggregate(values,data,mode){
  if(!['perGame','totals'].includes(mode))throw Error('未知單位');
  const roster=ids(values),rows=roster.map(id=>data.players[id]),n=roster.length,cells={},out=rows.filter(absent).length;
  // Confirmed non-appearances are known but excluded; `counted` is the divisor for per-member values.
  for(const key of counting){let known=out,counted=0,sum=0;for(const p of rows)if(p&&valid(p.gp)&&p.gp>0&&valid(p.totals[key])){known++;counted++;sum+=p.totals[key]/(mode==='perGame'?p.gp:1);}
   cells[key]={value:n&&known===n&&counted?sum:null,known,counted,absent:out,total:n,subtotal:sum,reason:!n?'尚未選球員':known<n?'有球員缺所選季別實績':!counted?'名單球員皆未出賽':null};
  }
  for(const prefix of ['FG','FT']){let known=out,counted=0,made=0,attempts=0;for(const p of rows)if(p&&valid(p.gp)&&p.gp>0&&valid(p.shots[prefix+'M'])&&valid(p.shots[prefix+'A'])&&p.shots[prefix+'M']<=p.shots[prefix+'A']){known++;counted++;const scale=mode==='perGame'?p.gp:1;made+=p.shots[prefix+'M']/scale;attempts+=p.shots[prefix+'A']/scale;}
   cells[prefix+'%']={value:n&&known===n&&attempts>0?100*made/attempts:null,known,counted,absent:out,total:n,made,attempts,reason:!n?'尚未選球員':known<n?'缺命中／出手分母':!attempts?'此口徑無出手':null};
   if(rows.some(p=>p&&Object.keys(p.uncertainties||{}).some(k=>k.startsWith(prefix))))cells[prefix+'%'].reason='來源差異未裁定，命中率未知';
  }
  const scores={};for(const key of metrics){const v=cells[key].value,b=data.benchmark[mode][key];
   const comparable=key.endsWith('%')?v:v===null?null:v/cells[key].counted;
   scores[key]=score(comparable,key,b);
  }
  return {ids:roster,size:n,cells,scores,gp:rows.filter(p=>p&&valid(p.gp)).reduce((s,p)=>s+p.gp,0),gpKnown:rows.filter(p=>p&&valid(p.gp)).length,
   minutesKnown:rows.filter(p=>p&&valid(p.minutes)).length};
 }
 function knownView(team,data,mode){const cells={},scores={};let partial=false;for(const key of metrics){const cell=team.cells[key],isPartial=cell.known<cell.total;
   const value=cell.value!==null?cell.value:!cell.counted?null:key.endsWith('%')?(cell.attempts>0?100*cell.made/cell.attempts:null):cell.subtotal;
   cells[key]={...cell,value,partial:isPartial};partial=partial||isPartial;const b=data.benchmark[mode][key],v=key.endsWith('%')?value:value===null?null:value/cell.counted;
   scores[key]=score(v,key,b);
  }return {...team,cells,scores,partial};}
 function simulate(base,outgoing,incoming){const remove=new Set(ids(outgoing));return ids([...ids(base).filter(id=>!remove.has(id)),...ids(incoming)]);}
 function contribution(p,key,mode){if(absent(p))return 0;return p&&valid(p.gp)&&p.gp>0&&valid(p.totals[key])?p.totals[key]/(mode==='perGame'?p.gp:1):null;}
 // Counting changes come from moved players only, so an unknown player kept on both rosters cancels out.
 function moved(base,other,key,data,mode){const before=new Set(base.ids),after=new Set(other.ids);let sum=0;
  for(const [list,keep,sign] of [[other.ids,before,1],[base.ids,after,-1]])for(const id of list)if(!keep.has(id)){const v=contribution(data.players[id],key,mode);if(v===null)return null;sum+=sign*v;}
  return sum;}
 function differences(base,other,data,mode){return Object.fromEntries(metrics.map(k=>{const a=base.cells[k],b=other.cells[k];
  if(!a.partial&&!b.partial&&a.value!==null&&b.value!==null)return [k,b.value-a.value];
  return [k,data&&counting.includes(k)&&base.ids?.length&&other.ids?.length?moved(base,other,k,data,mode):null];}));}
 function encodeSaved(rosters){return JSON.stringify({version:1,rosters:rosters.map(r=>({id:String(r.id),name:String(r.name).trim().slice(0,80),players:ids(r.players),savedAt:String(r.savedAt)}))});}
 function decodeSaved(text){if(!text)return[];let saved;try{saved=JSON.parse(text);}catch(e){e.code='ROTO_SAVE_FORMAT';throw e;}if(!saved||saved.version!==1||!Array.isArray(saved.rosters))throw Object.assign(Error('保存格式無法辨識，原內容未修改'),{code:'ROTO_SAVE_FORMAT'});
  const seen=new Set();return saved.rosters.map(r=>{if(!r||typeof r.id!=='string'||seen.has(r.id)||typeof r.name!=='string'||!r.name.trim()||!Array.isArray(r.players))throw Object.assign(Error('保存資料不完整，原內容未修改'),{code:'ROTO_SAVE_FORMAT'});seen.add(r.id);let players;try{players=ids(r.players);}catch(e){e.code='ROTO_SAVE_FORMAT';throw e;}return {id:r.id,name:r.name.slice(0,80),players,savedAt:String(r.savedAt||'')};});
 }
 function load(storage){return decodeSaved(storage.getItem(storageKey));}
 function save(storage,rosters){storage.setItem(storageKey,encodeSaved(rosters));}
 function loadOpponents(storage){const rosters=decodeSaved(storage.getItem(opponentsKey));if(rosters.some(r=>r.id!=='opponent'&&!/^opponent-[a-z0-9-]+$/i.test(r.id)))throw Object.assign(Error('對手隊伍 ID 無法辨識，原內容未修改'),{code:'ROTO_SAVE_FORMAT'});return rosters;}
 function saveOpponents(storage,rosters){storage.setItem(opponentsKey,encodeSaved(rosters));}
 return {counting,metrics,storageKey,opponentsKey,ids,aggregate,knownView,simulate,differences,encodeSaved,decodeSaved,load,save,loadOpponents,saveOpponents};
});
