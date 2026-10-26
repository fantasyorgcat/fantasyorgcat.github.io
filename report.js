var tables = {};
var activeWeek = "W1";
var teamSelection = {};
var seasonWeeks = REPORT_DATA.weeks;
var platformPeriods = REPORT_DATA.platforms;
var appliedSeasonWeek = null;
var playerCatalog = REPORT_DATA.catalog;
var playerToolsMeta = REPORT_DATA.meta;
var scheduleEvents = REPORT_DATA.events;
var quickPeriods = REPORT_DATA.quick;
var scheduleGeneratedAt = REPORT_DATA.generated_at;
var customPlayerTemplate;


$(document).ready( function () {
    // Shared labels also apply to dynamically built season/custom tables.
    $.extend(true, $.fn.dataTable.defaults, {language:{search:'搜尋球員',searchPlaceholder:'姓名或球隊',lengthMenu:'每頁 _MENU_ 人',info:'_START_–_END_ / _TOTAL_ 人',infoFiltered:'（全體 _MAX_ 人）',zeroRecords:'沒有符合球員，按全體球員清除篩選',infoEmpty:'0 人',paginate:{first:'第一頁',previous:'上一頁',next:'下一頁',last:'最後頁'}}});
    customPlayerTemplate=document.querySelector('#Week1 .player-section').cloneNode(true);
});

function openWeek(evt, weekName, notify = true) {
    var i, tabcontent, tablinks;
    tabcontent = document.getElementsByClassName("tabcontent");
    for (i = 0; i < tabcontent.length; i++) {
        tabcontent[i].style.display = "none";
    }
    tablinks = document.getElementsByClassName("tablinks");
    for (i = 0; i < tablinks.length; i++) {
        tablinks[i].className = tablinks[i].className.replace(" active", "");
    }
    document.getElementById(weekName).style.display = "block";
    document.getElementById('season-week').classList.remove('active');
    document.getElementById('apply-custom-period').classList.remove('active');
    evt.currentTarget.className += " active";
    activeWeek = weekName.replace('Week','W');
    if (activeWeek !== 'WCustom' && window.clearPlatformSelection) window.clearPlatformSelection();
    updateSelection(activeWeek);
    if (notify) document.dispatchEvent(new Event('active-week-changed'));
}

function selectSeasonWeek(value) {
    if (window.selectPlatformWeek) window.selectPlatformWeek(value);
}

// --- Feature: Switch Stats (period x display mode) ---
// The visible stat columns are the intersection of the active period
// (Season/L7/L14/LS) and the active display mode (AVG/TOT); both toggles
// funnel through applyStatView so they stay orthogonal.
var viewState = {};
function playerTableOptions(node, suffix, pageLength = 25) {
    var state = viewState[suffix] || {period:playerToolsMeta.defaultPeriod,mode:'avg'};
    var hidden = [];
    Array.from(node.tHead.rows[0].cells).forEach(function(header,index) {
        var stat = header.className.indexOf('stat-') !== -1;
        if (index === 1 || (header.hasAttribute('data-schedule-day') && !window.playerScheduleVisible()) ||
            (stat && !(header.classList.contains('stat-' + state.period) && header.classList.contains('stat-' + state.mode)))) hidden.push(index);
    });
    const headers=Array.from(node.tHead.rows[0].cells),fixtures=node._fixtures||new Map();
    const columns=headers.map((h,i)=>({
        className:h.className, createdCell:function(cell,value){
            if(!h.className.includes('stat-'))return;
            const rank=h.textContent.trim()==='Rank';
            cell.dataset.order=String(value.value??(rank?1000000000:-1));
            if(rank)decorateRank(cell,value);
        }, render:function(value,type,row){
            if(i===0){const p=playerCatalog[value];return type==='display'?playerIdentity(p):p.name+' '+p.team;}
            if(!h.className.includes('stat-'))return value;
            const rank=h.textContent.trim()==='Rank',v=value.value;
            if(type==='sort'||type==='type')return v===null?(rank?1000000000:-1):v;
            if(type!=='display')return v===null?'':v;
            if(rank)return rankMarkup(value);
            return v===null?'—':Number(v).toFixed(1)+(h.textContent.trim().endsWith('%')?'%':'')+
                (value.pr===null?'':"<br><span class='stat-pr'>PR "+Math.round(value.pr)+'</span>');
        }
    }));
    const data=Object.values(playerCatalog).map(p=>headers.map((h,i)=>{
        if(i===0)return p.id;if(i===1)return p.team;
        const schedule=fixtures.get(p.team)||[0,...headers.filter(h=>h.hasAttribute('data-schedule-day')).map(()=> '')];
        if(i===2)return schedule[0];if(h.hasAttribute('data-schedule-day'))return schedule[1+Number(h.dataset.scheduleDay)];
        const period=['season','l7','l14','ls'].find(k=>h.classList.contains('stat-'+k)),mode=h.classList.contains('stat-tot')?'tot':'avg';
        return {...p.periods[period][mode][h.textContent.trim()]};
    }));
    return {data,columns,deferRender:true,order:[[2,'desc']],pageLength:pageLength,scrollX:true,
        columnDefs:[{targets:hidden,visible:false}]};
}

function escapePlayer(value){return String(value).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
function playerIdentity(p){return '<b>'+escapePlayer(p.name)+"</b> <br><span style='color:var(--muted)'>"+escapePlayer(p.team)+
    "</span><div class='pick-controls'><label><input type='checkbox' data-pick='compare' data-player-id='"+escapePlayer(p.id)+
    "' aria-label='比較 "+escapePlayer(p.name)+"'>比較</label></div>";}
function rankMarkup(c){return '<span class="rank-value">'+(c.value??'—')+'</span>'+(c.sum===null?'':'<small class="rank-sum">Σ PR '+c.sum.toFixed(1)+'</small>');}
function decorateRank(td,c){td.dataset.rankValue=c.value===null?'':String(c.value);td.dataset.rankSum=c.sum===null?'':String(c.sum);
    td.title=c.sum===null?'所選項目 PR 不完整，無排名':'PR 合計 '+String(c.sum)+'；'+(window.playerRankLabel?.()||'9CAT');}

function applyStatView(suffix) {
    var state = viewState[suffix] || {period:'season',mode:'avg'};
    var table = tables[suffix];
    // Hidden views keep their state; synchronize when shown, not on every setting change.
    if (!table || !table.table().container().offsetWidth) return;
    table.columns().every(function () {
        var header = this.header();
        if (header.classList.contains('stat-season') || header.classList.contains('stat-l7') ||
            header.classList.contains('stat-l14') || header.classList.contains('stat-ls')) {
            var visible = header.classList.contains('stat-' + state.period) &&
                          header.classList.contains('stat-' + state.mode);
            // Clear the generated inline hiding only on the first use of these cells.
            if (visible && header.style.display === 'none') {
                header.style.display = '';
                this.nodes().to$().css('display', '');
            }
            if (this.visible() !== visible) this.visible(visible, false);
        }
    });
    if (window.preparePlayerTable) window.preparePlayerTable(suffix);
    table.columns.adjust().draw(false);
}

function switchStats(period, suffix, refresh = true) {
    viewState[suffix] = viewState[suffix] || {period:'season',mode:'avg'};
    viewState[suffix].period = period.toLowerCase();
    // Update Buttons
    // NOTE: matched via the button's data-period attribute (exact match), not
    // innerText substring matching -- the old innerText-substring check broke
    // once a "Last Season" button was added, since its label also contains the
    // literal word "Season" and would falsely light up alongside "Season Avg".
    // Scoped to [data-period] so the AVG/TOT buttons are left alone.
    var container = document.querySelector('#Week' + suffix.replace('W','') + ' .controls');
    var btns = container.querySelectorAll('.btn-stat[data-period]');
    for (var i = 0; i < btns.length; i++) {
        btns[i].classList.remove('active');
        btns[i].setAttribute('aria-pressed','false');
        if (btns[i].getAttribute('data-period') === period) {
            btns[i].classList.add('active');
            btns[i].setAttribute('aria-pressed','true');
        }
    }
    if (refresh) applyStatView(suffix);
}

// --- Feature: Switch Display Mode (AVG / TOT) ---
function switchDisplayMode(mode, suffix, refresh = true) {
    viewState[suffix] = viewState[suffix] || {period:'season',mode:'avg'};
    viewState[suffix].mode = mode.toLowerCase();
    // Scoped to [data-mode] so the period buttons are left alone.
    var container = document.querySelector('#Week' + suffix.replace('W','') + ' .controls');
    var btns = container.querySelectorAll('.btn-stat[data-mode]');
    for (var i = 0; i < btns.length; i++) {
        btns[i].classList.remove('active');
        btns[i].setAttribute('aria-pressed','false');
        if (btns[i].getAttribute('data-mode') === mode) {
            btns[i].classList.add('active');
            btns[i].setAttribute('aria-pressed','true');
        }
    }
    if (refresh) applyStatView(suffix);
}

function updateSelection(suffix) {
    var table = tables[suffix];
    if (!table) return;
    var team = teamSelection[suffix];
    var count = table.rows({search:'applied'}).count();
    var text = (team ? team + ' 球員' : '全體球員') + ' · ' + count + ' 人';
    $('#selection'+suffix).text(text);
    if (suffix === activeWeek) {
        $('#active-selection').text(text);
        $('#show-all-players').attr('aria-pressed', !team && !table.search() ? 'true' : 'false');
    }
}
function filterTeam(row, teamAbbr, suffix) {
    $('#teamTable' + suffix + ' .team-row').removeClass('selected');
    $(row).addClass('selected');
    teamSelection[suffix] = teamAbbr;
    tables[suffix].column(1).search('^' + $.fn.dataTable.util.escapeRegex(teamAbbr) + '$', true, false).draw();
    updateSelection(suffix);
    document.dispatchEvent(new Event('team-filter-changed'));
}
function resetTeamFilter(suffix) {
    var table = tables[suffix];
    if (!table) return;
    $('#teamTable' + suffix + ' .team-row').removeClass('selected');
    delete teamSelection[suffix];
    table.search('').columns().search('').draw();
    $(table.table().container()).find('input[type="search"]').val('');
    updateSelection(suffix);
    document.dispatchEvent(new Event('team-filter-changed'));
}
function resetActiveTeamFilter() { resetTeamFilter(activeWeek); }
