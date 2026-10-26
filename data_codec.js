/* Lossless counterpart of report_data.pack_catalog. No requests or eval. */
(function(root){
 'use strict';
 function unpackCatalog(data){
  if(data.v!==1)return data;
  const metrics=['MIN','PTS','REB','AST','3PM','STL','BLK','FG%','FT%','TO','Rank'],periods=['season','l7','l14','ls'],shots=['FGM','FGA','FTM','FTA'];
  const cells=values=>Object.fromEntries(metrics.map((m,i)=>[m,m==='Rank'?{value:values[i][0],pr:null,sum:values[i][1]}:{value:values[i][0],pr:values[i][1]}]));
  return Object.fromEntries(data.p.map(([id,name,team,...indices])=>[id,{id,name,team,periods:Object.fromEntries(indices.map((index,i)=>{
   const [gp,s,avg,tot]=data.s[index];
   return [periods[i],{gp,shooting:Object.fromEntries(shots.map((k,j)=>[k,s[j]])),avg:cells(avg),tot:cells(tot.map((v,j)=>v===null?avg[j]:v))}];
  }))}]));
 }
 root.unpackCatalog=unpackCatalog;
 function unpackEvents(data){
  if(Array.isArray(data))return data;
  if(data.v!==1)throw Error('Unsupported schedule transport');
  const fields=['id','date_et','tipoff_utc','status','season_type','time_confirmed','home','away'];
  return data.e.map(row=>({...Object.fromEntries(fields.map((key,i)=>[key,row[i]])),home_html:data.b[row[8]]+data.t[row[9]],away_html:data.b[row[10]]+data.t[row[11]]}));
 }
 if(root.REPORT_DATA){root.REPORT_DATA.catalog=unpackCatalog(root.REPORT_DATA.catalog);root.REPORT_DATA.events=unpackEvents(root.REPORT_DATA.events);}
 if(root.ROTO_DATA?.catalog)root.ROTO_DATA.catalog=unpackCatalog(root.ROTO_DATA.catalog);
 if(typeof module!=='undefined')module.exports={unpackCatalog,unpackEvents};
})(typeof window==='undefined'?globalThis:window);
