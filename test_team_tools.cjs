const assert=require('node:assert/strict');
const {gameCount,compare}=require('./team_tools.js');
for(const value of [0,1,7,'0',' 3 ','4.0'])assert.equal(gameCount(value),Number(value));
for(const value of [null,undefined,'','—','N/A','1 game',-1,NaN,Infinity,true,false,'-2','2.5'])assert.equal(gameCount(value),null);
const rows=[['BOS',2],['LAL',2],['MIA',3],['NYK',null],['CLE',0]];
function sort(direction){return rows.map(([team,games],index)=>({team,games,index})).sort((a,b)=>compare(a.games,b.games,direction)||a.index-b.index).map(row=>row.team);}
assert.deepEqual(sort('desc'),['MIA','BOS','LAL','CLE','NYK']);
assert.deepEqual(sort('asc'),['CLE','BOS','LAL','MIA','NYK']);
assert.equal(compare(null,null,'asc'),0);
assert.equal(compare(2,2,'desc'),0);
console.log('Team game count sorting: numeric directions, stable ties, unknown last and real zero passed');
