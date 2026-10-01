/* Embedded in the generated report. No fetch, backend, telemetry, or stored HTML. */
(function () {
  'use strict';
  const KEY='fantasy-nba:hotmilk300/Fantasy-NBA-Streaming-Assistant:roster:v1', LIMIT=100, MAX_BYTES=32768;
  const compared=new Set();
  let roster=new Map(), persistent=true, storedSeason=playerToolsMeta.season;
  let period=playerToolsMeta.defaultPeriod, mode='avg', sortKey='name', descending=false;
  const metrics=['GP','MIN','PTS','REB','AST','3PM','STL','BLK','FG%','FT%'];
  const byId=id=>document.getElementById(id);
  const say=text=>{byId('roster-status').textContent=text;};
  function validate(raw) {
    if (typeof raw!=='string' || raw.length>MAX_BYTES) throw Error('size');
    const d=JSON.parse(raw);
    if (!d || typeof d!=='object' || Array.isArray(d) || Object.keys(d).sort().join(',')!=='players,season,version' || d.version!==1 || typeof d.season!=='string' || !/^\d{4}-\d{2}$/.test(d.season) || !Array.isArray(d.players) || d.players.length>LIMIT) throw Error('schema');
    const seen=new Set();
    for (const p of d.players) {
      if (!p || typeof p!=='object' || Array.isArray(p) || Object.keys(p).sort().join(',')!=='id,name' || typeof p.id!=='string' || !/^\d{1,12}$/.test(p.id) || typeof p.name!=='string' || p.name.length>120 || seen.has(p.id)) throw Error('player');
      seen.add(p.id);
    }
    return d;
  }
  function backup(raw) {
    if(typeof raw!=='string'||raw.length>MAX_BYTES)throw Error('size');
    const d=JSON.parse(raw);
    if(!d||typeof d!=='object'||Array.isArray(d)||Object.keys(d).sort().join(',')!=='players,schemaVersion,season'||d.schemaVersion!==1)throw Error('schema');
    return validate(JSON.stringify({version:d.schemaVersion,season:d.season,players:d.players}));
  }
  function load() {
    try {
      const raw=localStorage.getItem(KEY);
      if (raw!==null) {const d=validate(raw);roster=new Map(d.players.map(p=>[p.id,p.name]));storedSeason=d.season;}
    } catch (_) {persistent=false;say('本機儲存無法使用或內容損壞。本次可暫存陣容，關閉或重新整理後可能無法保留；原內容未覆寫。');}
  }
  function save(preserveSeason=false) {
    if (!persistent) return;
    try {
      const season=preserveSeason?storedSeason:playerToolsMeta.season;
      localStorage.setItem(KEY,JSON.stringify({version:1,season,players:Array.from(roster,([id,name])=>({id,name}))}));
      storedSeason=season;say('陣容已儲存在此瀏覽器。');
    } catch (_) {persistent=false;say('儲存失敗（可能已停用或空間不足）。本次陣容仍可使用，重新開啟可能回到上次儲存內容。');}
  }
  function sync() {
    document.querySelectorAll('input[data-pick]').forEach(input=>{
      const selected=input.dataset.pick==='compare'?compared.has(input.dataset.playerId):roster.has(input.dataset.playerId);
      input.checked=selected;
    });
    byId('show-roster').textContent='查看我的陣容（'+roster.size+'）';
    byId('reset-roster-storage').hidden=persistent;
  }
  function button(text,action,label) {
    const b=document.createElement('button');b.type='button';b.textContent=text;b.className='btn-stat';
    if (label)b.setAttribute('aria-label',label);b.addEventListener('click',action);return b;
  }
  function rosterView() {
    const list=byId('roster-list');list.replaceChildren();
    if (!roster.size) {const p=document.createElement('p');p.textContent='陣容尚無球員，請在名單勾選「陣容」。';list.appendChild(p);}
    for (const [id,savedName] of roster) {
      const p=playerCatalog[id],row=document.createElement('div');row.className='roster-member';row.dataset.playerId=id;
      const name=document.createElement('span');name.textContent=p?p.name+' · '+p.team:'未匹配球員 ID '+id+'（原名：'+savedName+'）';
      row.append(name,button('移除',()=>{roster.delete(id);save();render();},'從陣容移除 '+(p?p.name:savedName)));
      list.appendChild(row);
    }
    byId('roster-season-note').textContent=storedSeason!==playerToolsMeta.season?'此陣容從 '+storedSeason+' 保留。依球員ID匹配目前 '+playerToolsMeta.season+' 名單；轉隊顯示目前球隊，未匹配者不會改配同名球員。':'';
  }
  function value(p,key) {return key==='name'?p.name:key==='GP'?p.periods[period].gp:p.periods[period][mode][key].value;}
  function compareView() {
    const panel=byId('comparison-panel');panel.hidden=!compared.size;
    if (!compared.size) {byId('comparison-body').replaceChildren();return;}
    const rows=Array.from(compared,id=>playerCatalog[id]).filter(Boolean);
    rows.sort((a,b)=>{
      const x=value(a,sortKey),y=value(b,sortKey);
      if (x===null)return y===null?0:1;if (y===null)return -1;
      const n=typeof x==='number'?x-y:String(x).localeCompare(String(y));return (descending?-n:n)||a.id.localeCompare(b.id);
    });
    const body=byId('comparison-body');body.replaceChildren();
    for (const p of rows) {
      const tr=document.createElement('tr');tr.dataset.playerId=p.id;
      const name=tr.insertCell();name.textContent=p.name+' · '+p.team;
      name.appendChild(button('移除',()=>{compared.delete(p.id);render();},'從比較移除 '+p.name));
      for (const metric of metrics) {
        const td=tr.insertCell(),v=value(p,metric);td.dataset.value=v===null?'':String(v);
        td.textContent=v===null?'—':metric==='GP'||(mode==='tot'&&['PTS','REB','AST','3PM','STL','BLK'].includes(metric))?String(v):v.toFixed(1)+(metric.endsWith('%')?'%':'');
        if (metric!=='GP' && v!==null) {
          const pr=p.periods[period][mode][metric].pr;
          if (pr!==null) {const small=document.createElement('small');small.textContent='PR '+Math.round(pr);td.appendChild(small);}
        }
      }
      body.appendChild(tr);
    }
    const names={season:'本季 '+playerToolsMeta.season,l7:'近7天',l14:'近14天',ls:'上季 '+playerToolsMeta.lastSeason};
    byId('comparison-meta').textContent=names[period]+' · '+mode.toUpperCase()+' · 更新 '+playerToolsMeta.generatedAt+' · 缺值為 —；PR使用完整聯盟母體，GP沒有PR。';
    document.querySelectorAll('#comparison-head button').forEach(b=>b.setAttribute('aria-label',b.textContent+'，'+(sortKey===b.dataset.sort?(descending?'目前降序':'目前升序'):'可排序')));
  }
  function render() {sync();rosterView();compareView();}
  $(document).ready(function () {
    load();
    const head=byId('comparison-head'),tr=document.createElement('tr');
    for (const key of ['name',...metrics]) {const th=document.createElement('th'),b=button(key==='name'?'球員':key,()=>{descending=sortKey===key?!descending:key!=='name';sortKey=key;compareView();});b.dataset.sort=key;th.appendChild(b);tr.appendChild(th);}
    head.appendChild(tr);
    byId('comparison-period').value=period;
    byId('storage-origin').textContent=location.origin;
    byId('comparison-period').addEventListener('change',e=>{period=e.target.value;compareView();});
    byId('comparison-mode').addEventListener('change',e=>{mode=e.target.value;compareView();});
    byId('clear-comparison').addEventListener('click',()=>{compared.clear();render();});
    byId('show-roster').addEventListener('click',()=>{const p=byId('roster-panel');p.hidden=!p.hidden;byId('show-roster').setAttribute('aria-expanded',String(!p.hidden));});
    byId('clear-roster').addEventListener('click',()=>{if(roster.size&&window.confirm('清空此瀏覽器儲存的陣容？')) {roster.clear();save();render();}});
    byId('export-roster').addEventListener('click',()=>{
      const raw=JSON.stringify({schemaVersion:1,season:storedSeason,players:Array.from(roster,([id,name])=>({id,name}))});
      if(new Blob([raw]).size>MAX_BYTES){say('備份超過32KB，請先減少陣容內容；未產生不完整備份。');return;}
      const url=URL.createObjectURL(new Blob([raw],{type:'application/json'})),a=document.createElement('a');
      a.href=url;a.download='fantasy-nba-roster-'+storedSeason+'.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
      say('已匯出陣容JSON備份；檔案包含球員ID與名稱，請自行保管。');
    });
    byId('import-roster').addEventListener('change',async e=>{
      const file=e.target.files[0];if(!file)return;
      try {
        if(file.size>MAX_BYTES)throw Error('size');
        const d=backup(await file.text()),unknown=d.players.filter(p=>!playerCatalog[p.id]).length;
        if(!window.confirm('以備份取代目前陣容？共 '+d.players.length+' 人，未匹配 '+unknown+' 人。未匹配ID保留提示，不會改配同名球員。'))return;
        roster=new Map(d.players.map(p=>[p.id,playerCatalog[p.id]?playerCatalog[p.id].name:p.name]));storedSeason=d.season;
        save(true);render();say('已匯入 '+roster.size+' 人；未匹配 '+unknown+' 人'+(persistent?'，已儲存。':'，僅本次暫存，無法儲存。'));
      } catch (_) {say('無法匯入：須為32KB以內、schemaVersion 1、最多100位、不重複的有效球員ID清單。原陣容未變動。');}
      finally {e.target.value='';}
    });
    byId('reset-roster-storage').addEventListener('click',()=>{
      if (!window.confirm('重設此網站的本機陣容儲存，並保存目前暫存陣容？')) return;
      try {localStorage.removeItem(KEY);persistent=true;save();} catch (_) {persistent=false;say('此瀏覽器仍無法使用儲存；請保留本次暫存，或調整瀏覽器設定。');}sync();
    });
    document.addEventListener('change',e=>{
      const input=e.target;if(!input.matches('input[data-pick]'))return;
      const id=input.dataset.playerId,p=playerCatalog[id];if(!p)return;
      if (input.dataset.pick==='compare') {if(input.checked)compared.add(id);else compared.delete(id);}
      else {if(input.checked) {if(roster.size>=LIMIT&&!roster.has(id)){input.checked=false;say('陣容最多 '+LIMIT+' 位球員。');return;}roster.set(id,p.name);}else roster.delete(id);save();}
      render();
    });
    $(document).on('draw.dt',sync);
    window.addEventListener('storage',e=>{
      if(e.key!==KEY&&e.key!==null)return;
      try {
        const raw=localStorage.getItem(KEY);
        const candidate=raw===null?{season:playerToolsMeta.season,players:[]}:validate(raw);
        const next=new Map(candidate.players.map(p=>[p.id,p.name]));
        roster=next;storedSeason=candidate.season;persistent=true;
      } catch (_) {persistent=false;say('其他分頁的儲存無法讀取或已損壞；目前暫存陣容保留，未覆寫任何內容。');}
      render();
    });
    render();
  });
})();
