const assert=require('node:assert/strict'),C=require('./roto_core.js');
const p=(id,gp,m,a,ftm=0,fta=0,to=1)=>({id,name:id,team:'TEST',gp,minutes:20,totals:{PTS:gp*10,REB:gp*2,AST:gp,STL:gp,BLK:0,'3PM':gp,TO:gp*to},shots:{FGM:m,FGA:a,FTM:ftm,FTA:fta}});
const data={players:{'1':p('1',10,1,2,2,4,1),'2':p('2',20,9,10,4,4,3),'3':p('3',2,0,0,0,0,0)},benchmark:{perGame:{},totals:{}}};
for(const mode of ['perGame','totals'])for(const k of C.metrics)data.benchmark[mode][k]={mean:2,sd:1};
let a=C.aggregate(['1','2'],data,'totals');assert.equal(a.cells['FG%'].value,100*10/12);assert.equal(a.cells['FT%'].value,75);assert.notEqual(a.cells['FG%'].value,(50+90)/2);
assert.equal(a.cells.PTS.value,300);assert.equal(C.aggregate(['1','2'],data,'perGame').cells.PTS.value,20);
assert.equal(C.aggregate(['1','2'],data,'perGame').cells['FG%'].value,100*(1/10+9/20)/(2/10+10/20));
assert.equal(C.aggregate(['1','1'],data,'totals').cells.PTS.value,100);
assert.equal(C.aggregate(['3'],data,'totals').cells['FG%'].value,null);assert.equal(C.aggregate(['3'],data,'totals').cells['FG%'].known,1);
const missing={...data,players:{...data.players,'4':{...p('4',5,1,2),shots:{FGM:null,FGA:2,FTM:null,FTA:null}}}};
a=C.aggregate(['1','4','999'],missing,'totals');assert.equal(a.cells.PTS.value,null);assert.equal(a.cells.PTS.known,2);assert.equal(a.cells.PTS.subtotal,150);assert.equal(a.cells['FG%'].value,null);assert.equal(a.cells['FG%'].known,1);assert.equal(a.scores['FG%'],null);
assert.equal(C.aggregate([],data,'totals').cells.TO.value,null);
const low=C.aggregate(['1'],data,'perGame'),high=C.aggregate(['2'],data,'perGame');assert.ok(low.scores.TO>high.scores.TO);assert.equal(low.scores.TO,65);assert.equal(high.scores.TO,35);
const frozen=JSON.stringify(data.benchmark);C.aggregate(['1','2','3'],data,'totals');assert.equal(JSON.stringify(data.benchmark),frozen);
const base=['1','2'];assert.deepEqual(C.simulate(base,['1'],['3','3']),['2','3']);assert.deepEqual(base,['1','2']);assert.deepEqual(C.simulate(base,[],[]),base);assert.deepEqual(C.simulate(base,['1','2'],['1','2']),base);assert.deepEqual(C.simulate(base,[],['2']),base);
assert.throws(()=>C.ids(['__proto__']));
const cells=C.differences(low,high);assert.equal(cells.TO,2);assert.equal(C.differences(low,C.aggregate(['999'],data,'perGame')).TO,null);
const memory=new Map([['unrelated-existing-key','untouched']]);const store={getItem:k=>memory.get(k),setItem:(k,v)=>memory.set(k,v)};
const roster=[{id:'a',name:'Named',players:['1','2','2','999'],savedAt:'2026-10-14'}];C.save(store,roster);assert.deepEqual(C.load(store)[0].players,['1','2','999']);assert.equal(memory.get('unrelated-existing-key'),'untouched');assert.equal(C.load(store)[0].name,'Named');
assert.throws(()=>C.decodeSaved('{bad'));assert.throws(()=>C.decodeSaved('{"version":2,"rosters":[]}'));
assert.throws(()=>C.save({setItem(){throw Error('Storage blocked');}},roster));
console.log('Weighted FG/FT, per-player GP units, reverse TO, unknowns/coverage, duplicates, immutable replacements/reset, fixed baseline and local save/load passed.');

// Hundreds of named opponents have no artificial count cap and keep legacy saves separate.
const many=Array.from({length:1200},(_,i)=>({id:'opponent-'+i,name:'對手 '+i,players:['1','2','2'],savedAt:'2026-10-14'}));
const legacy=memory.get(C.storageKey);C.saveOpponents(store,many);assert.equal(C.loadOpponents(store).length,1200);assert.deepEqual(C.loadOpponents(store)[1199].players,['1','2']);assert.equal(memory.get(C.storageKey),legacy);
C.saveOpponents(store,[]);assert.deepEqual(C.loadOpponents(store),[]);
memory.set(C.opponentsKey,C.encodeSaved([{...many[0],id:'base'}]));assert.throws(()=>C.loadOpponents(store));assert.equal(memory.get(C.storageKey),legacy);
C.saveOpponents(store,many);const prior=memory.get(C.opponentsKey);assert.throws(()=>C.saveOpponents({setItem(){throw Error('QuotaExceededError');}},[]));assert.equal(memory.get(C.opponentsKey),prior);
console.log('1200 named opponents, separate legacy storage, empty roster restoration, invalid IDs and storage quota failures passed.');

const mixed=C.aggregate(['1','2','999'],data,'totals'),preview=C.knownView(mixed,data,'totals');
assert.equal(mixed.cells.PTS.value,null);assert.equal(preview.cells.PTS.value,300);assert.equal(preview.cells.PTS.partial,true);assert.equal(preview.cells['FG%'].value,100*10/12);assert.equal(preview.size,3);assert.equal(preview.cells.PTS.known,2);assert.equal(preview.scores.PTS,C.aggregate(['1','2'],data,'totals').scores.PTS);
assert.equal(C.differences(preview,C.knownView(C.aggregate(['1'],data,'totals'),data,'totals')).PTS,null);assert.equal(C.knownView(C.aggregate(['999'],data,'totals'),data,'totals').cells.PTS.value,null);
console.log('Known subtotal remains usable with unknown members; weighted known denominators and incomplete deltas are explicit.');
