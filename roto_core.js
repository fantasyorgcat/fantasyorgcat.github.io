/* Pure last-season aggregation and roster transitions, shared by browser and Node tests. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.RotoCore=api;})(globalThis,function(){
 'use strict';
 const counting=['PTS','REB','AST','3PM','STL','BLK','TO'],metrics=['PTS','REB','AST','3PM','STL','BLK','FG%','FT%','TO'],storageKey='fantasyorgcat:roto:rosters:v1';
 function ids(values){return [...new Set(values.map(v=>{const id=String(v);if(!/^\d+$/.test(id))throw Error('球員 ID 格式錯誤');return id;}))];}
 const valid=v=>typeof v==='number'&&Number.isFinite(v)&&v>=0;
 function aggregate(values,data,mode){
  if(!['perGame','totals'].includes(mode))throw Error('未知單位');
  const roster=ids(values),rows=roster.map(id=>data.players[id]),n=roster.length,cells={};
  for(const key of counting){let known=0,sum=0;for(const p of rows)if(p&&valid(p.gp)&&p.gp>0&&valid(p.totals[key])){known++;sum+=p.totals[key]/(mode==='perGame'?p.gp:1);}
   cells[key]={value:n&&known===n?sum:null,known,total:n,subtotal:sum,reason:!n?'尚未選球員':known<n?'有球員缺上季實績':null};
  }
  for(const prefix of ['FG','FT']){let known=0,made=0,attempts=0;for(const p of rows)if(p&&valid(p.gp)&&p.gp>0&&valid(p.shots[prefix+'M'])&&valid(p.shots[prefix+'A'])&&p.shots[prefix+'M']<=p.shots[prefix+'A']){known++;const scale=mode==='perGame'?p.gp:1;made+=p.shots[prefix+'M']/scale;attempts+=p.shots[prefix+'A']/scale;}
   cells[prefix+'%']={value:n&&known===n&&attempts>0?100*made/attempts:null,known,total:n,made,attempts,reason:!n?'尚未選球員':known<n?'缺命中／出手分母':!attempts?'此口徑無出手':null};
  }
  const scores={};for(const key of metrics){const v=cells[key].value,b=data.benchmark[mode][key];
   const comparable=key.endsWith('%')?v:v===null?null:v/n;
   scores[key]=comparable===null||!b||b.mean===null||!b.sd?null:Math.max(0,Math.min(100,50+(key==='TO'?-15:15)*(comparable-b.mean)/b.sd));
  }
  return {ids:roster,size:n,cells,scores,gp:rows.filter(p=>p&&valid(p.gp)).reduce((s,p)=>s+p.gp,0),gpKnown:rows.filter(p=>p&&valid(p.gp)).length,
   minutesKnown:rows.filter(p=>p&&valid(p.minutes)).length};
 }
 function simulate(base,outgoing,incoming){const remove=new Set(ids(outgoing));return ids([...ids(base).filter(id=>!remove.has(id)),...ids(incoming)]);}
 function differences(base,other){return Object.fromEntries(metrics.map(k=>[k,base.cells[k].value===null||other.cells[k].value===null?null:other.cells[k].value-base.cells[k].value]));}
 function encodeSaved(rosters){return JSON.stringify({version:1,rosters:rosters.map(r=>({id:String(r.id),name:String(r.name).trim().slice(0,80),players:ids(r.players),savedAt:String(r.savedAt)}))});}
 function decodeSaved(text){if(!text)return[];let saved;try{saved=JSON.parse(text);}catch(e){e.code='ROTO_SAVE_FORMAT';throw e;}if(!saved||saved.version!==1||!Array.isArray(saved.rosters))throw Object.assign(Error('保存格式無法辨識，原內容未修改'),{code:'ROTO_SAVE_FORMAT'});
  const seen=new Set();return saved.rosters.map(r=>{if(!r||typeof r.id!=='string'||seen.has(r.id)||typeof r.name!=='string'||!r.name.trim()||!Array.isArray(r.players))throw Object.assign(Error('保存資料不完整，原內容未修改'),{code:'ROTO_SAVE_FORMAT'});seen.add(r.id);let players;try{players=ids(r.players);}catch(e){e.code='ROTO_SAVE_FORMAT';throw e;}return {id:r.id,name:r.name.slice(0,80),players,savedAt:String(r.savedAt||'')};});
 }
 function load(storage){return decodeSaved(storage.getItem(storageKey));}
 function save(storage,rosters){storage.setItem(storageKey,encodeSaved(rosters));}
 return {counting,metrics,storageKey,ids,aggregate,simulate,differences,encodeSaved,decodeSaved,load,save};
});
