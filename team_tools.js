/* Sort the existing team table by its current period's game counts. */
(function(){
 'use strict';
 function gameCount(value){
  if(typeof value==='number')return Number.isFinite(value)&&Number.isInteger(value)&&value>=0?value:null;
  const text=String(value??'').trim();
  if(!/^\d+(?:\.0+)?$/.test(text))return null;
  const number=Number(text);return Number.isFinite(number)&&Number.isInteger(number)?number:null;
 }
 function compare(a,b,direction){
  if(a===null)return b===null?0:1;
  if(b===null)return -1;
  return direction==='desc'?b-a:a-b;
 }
 if(typeof module==='object'&&module.exports){module.exports={gameCount,compare};return;}
 const order=$.fn.dataTable.ext.type.order,records=new WeakMap();
 window.teamGamesSortValue=(value,index)=>({games:gameCount(value),index});
 order['team-games-pre']=value=>value&&typeof value==='object'?value:{games:gameCount(value),index:0};
 order['team-games-asc']=(a,b)=>compare(a.games,b.games,'asc')||a.index-b.index;
 order['team-games-desc']=(a,b)=>compare(a.games,b.games,'desc')||a.index-b.index;
 window.setupTeamGamesSort=function(table){
  if(records.has(table))return;
  const header=table.tHead.rows[0].cells[1],title=header.querySelector('.dt-column-title')||header;
  const button=document.createElement('button'),arrow=document.createElement('span');
  button.type='button';button.className='team-games-sort';button.dataset.teamGamesSort='';button.append('Games ');
  arrow.dataset.gamesSortArrow='';arrow.setAttribute('aria-hidden','true');button.appendChild(arrow);title.replaceChildren(button);
  const rows=Array.from(table.tBodies[0].querySelectorAll('.team-row')),positions=new WeakMap(rows.map((row,index)=>[row,index]));
  const api=$.fn.dataTable.isDataTable(table)?$(table).DataTable():null;
  const record={direction:null};records.set(table,record);button.disabled=!rows.length;
  function display(){
   header.setAttribute('aria-sort',record.direction===null?'none':record.direction==='desc'?'descending':'ascending');
   arrow.textContent=record.direction===null?'↕':record.direction==='desc'?'↓':'↑';
   button.setAttribute('aria-label','比賽場次，'+(record.direction===null?'目前未排序；點選由多到少':record.direction==='desc'?'目前由多到少；點選由少到多':'目前由少到多；點選由多到少'));
  }
  if(api)api.on('order.dt',()=>{const current=api.order()[0];record.direction=current&&current[0]===1?current[1]:null;display();});
  button.addEventListener('click',event=>{
   event.stopPropagation();record.direction=record.direction==='desc'?'asc':'desc';
   if(api)api.order([[1,record.direction]]).draw(false);
   else{
    const current=Array.from(table.tBodies[0].querySelectorAll('.team-row'));
    current.sort((a,b)=>compare(gameCount(a.cells[1].textContent),gameCount(b.cells[1].textContent),record.direction)||positions.get(a)-positions.get(b));
    table.tBodies[0].append(...current);
   }
   display();
  });
  display();
 };
})();
