"""Offline, explicitly marked fixture preview. Never replaces tracked production files."""
import functools
import http.server
import json
import os
from pathlib import Path
import shutil
import tempfile
import threading
from datetime import date
from unittest.mock import patch
import pandas as pd
import utils
from generate_report import generate_html_report

ROOT=Path(__file__).resolve().parent

def build_fixture(target):
    target=Path(target);target.mkdir(parents=True,exist_ok=True)
    for name in ['dashboard.css','player_tools.js','schedule_tools.js']:shutil.copyfile(ROOT/name,target/name)
    shutil.copytree(ROOT/'assets',target/'assets',dirs_exist_ok=True)
    records=[]
    # 25 calendar weeks, four-day opening shortcut, cross-year and DST events.
    for eid,stamp,status in [('open','2026-10-21T01:00:00Z','scheduled'),('b2b1','2026-10-27T01:00:00Z','scheduled'),('b2b2','2026-10-28T01:00:00Z','scheduled'),('winter','2027-01-01T02:30:00Z','scheduled'),('final','2026-10-22T01:00:00Z','final'),('late','2026-10-23T01:00:00Z','postponed'),('cancel','2026-10-24T01:00:00Z','cancelled'),('tbd',None,'scheduled'),('closing','2027-04-12T00:30:00Z','scheduled'),
            ('cup-first','2026-12-03T01:00:00Z','scheduled'),('cup-second','2026-12-10T01:00:00Z','scheduled'),
            ('allstar-first','2027-02-19T01:00:00Z','scheduled'),('allstar-second','2027-02-26T01:00:00Z','scheduled')]:
        from datetime import datetime
        from zoneinfo import ZoneInfo
        day=datetime.fromisoformat(stamp.replace('Z','+00:00')).astimezone(ZoneInfo('America/New_York')).date() if stamp else None
        for tid,team,match in [(1,'LAL','LAL vs. BOS'),(2,'BOS','BOS @ LAL')]:
            records.append(dict(TEAM_ID=tid,TEAM_ABBREVIATION=team,GAME_DATE=day,MATCHUP=match,EVENT_ID=eid,TIPOFF_UTC=stamp,STATUS=status,SEASON_TYPE=2,TIME_CONFIRMED=bool(stamp)))
    schedule=pd.DataFrame(records,columns=utils.SCHEDULE_COLUMNS)
    roster=pd.DataFrame([dict(PLAYER_ID=i+1,PLAYER_NAME='Fixture Alpha '+str(i) if i%2==0 else 'Fixture Beta '+str(i),TEAM_ID=1 if i%2==0 else 2,TEAM_ABBREVIATION='LAL' if i%2==0 else 'BOS') for i in range(605)])
    prior=[]
    for row in roster.iloc[:578].to_dict('records'):
        row.update(GP=50,MIN=30,PTS=20+row['PLAYER_ID']/1000,REB=5,AST=4,STL=1,BLK=1,FG_PCT=.5,FT_PCT=.8,FG3M=2,TO=2)
        for key in utils.TOTAL_FIELDS:row[key+'_TOTAL']=int(row[key]*50)
        prior.append(row)
    stats=dict(Season=pd.DataFrame(columns=utils.COLUMNS),L7=pd.DataFrame(columns=utils.COLUMNS),L14=pd.DataFrame(columns=utils.COLUMNS),LastSeason=pd.DataFrame(prior,columns=utils.COLUMNS),Roster=roster,metadata={'season':'2026-27','last_season':'2025-26'})
    old_cwd=Path.cwd();old_provenance=dict(utils.PROVENANCE)
    try:
        os.chdir(target);utils.PROVENANCE.clear();utils.PROVENANCE.update(fixture=True,roster_players=605,schedule=dict(season='2026-27',published_events=12,undated_events=1),players_2026=dict(population=578,source_period_end='2026-04-13'),defense=dict(source='PBP Stats',eligible_teams=0))
        with patch.object(utils,'today',return_value=date(2026,10,1)),patch.object(utils,'get_season_schedule',return_value=schedule),patch.object(utils,'get_player_stats_multi_period',return_value=stats),patch.object(utils,'get_team_defensive_ratings',return_value={}):generate_html_report()
        path=target/'fantasy_nba_report_v2.html';html=path.read_text();html=html.replace('<title>','<title>UI TEST ONLY · ').replace('把下一場，排進你的陣容。','UI TEST ONLY · 合成資料驗證');path.write_text(html)
    finally:os.chdir(old_cwd);utils.PROVENANCE.clear();utils.PROVENANCE.update(old_provenance)
    return target/'fantasy_nba_report_v2.html'

def run(url,output):
    from playwright.sync_api import sync_playwright
    results=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path=os.environ.get('CHROMIUM_PATH','/usr/bin/chromium'),headless=True)
        for width in [1500,390]:
            context=browser.new_context(viewport={'width':width,'height':1000 if width==1500 else 844})
            page=context.new_page();errors=[];failed=[]
            page.clock.install(time='2026-10-25T12:00:00Z')
            page.on('pageerror',lambda e:errors.append(str(e)));page.on('requestfailed',lambda r:failed.append(r.url))
            assert page.goto(url,wait_until='load').status==200
            page.wait_for_function('Object.keys(tables).length===5')
            assert page.locator('[data-platform]').count()==3
            assert page.locator('[data-platform="NBA"]').get_attribute('aria-pressed')=='true'
            assert page.locator('[data-platform="ESPN"]').is_enabled()
            assert '待核' not in page.locator('[data-platform="ESPN"]').inner_text()
            assert page.locator('#season-week option').count()==26
            assert 'active' not in page.locator('#apply-custom-period').get_attribute('class')
            assert not page.locator('#schedule-extras').get_attribute('open')
            page.locator('#schedule-extras summary').click()
            page.locator('#defaultOpen').click()
            # Opening shortcut has four real date columns, no statistics masquerading as dates.
            assert page.evaluate("tables.W1.columns('[data-schedule-day]').count()") == 4
            page.evaluate("tables.W1.search('Fixture Alpha 0',false,false).draw()")
            page.locator('#Week1 input[data-player-id="1"]').check()
            assert page.locator('#comparison-body .comparison-matchup').count()==4
            original=page.evaluate("JSON.stringify(playerCatalog['1'].periods)")
            def apply(start,end):
                page.locator('#period-start').fill(start);page.locator('#period-end').fill(end);page.locator('#apply-custom-period').click()
            apply('2026-10-20','2026-11-02')
            assert page.evaluate('activeWeek')=='WCustom'
            assert page.evaluate("tables.WCustom.columns('[data-schedule-day]').count()") == 14
            assert page.locator('#comparison-body .comparison-matchup').count()==14
            headers=page.evaluate("tables.WCustom.columns('[data-schedule-day]').indexes().toArray().map(i=>tables.WCustom.column(i).header().textContent)")
            assert headers==page.locator('#comparison-head th').all_text_contents()[2:16]
            assert '美東 10/20 21:00' in page.locator('#comparison-body').inner_text()
            assert '台北 10/21 09:00' in page.locator('#comparison-body').inner_text()
            assert '延賽' in page.locator('#comparison-body').inner_text()
            # Scheduled open + two B2B + final; postponed/cancelled do not inflate total.
            assert page.locator('#comparison-body tr td').nth(1).inner_text()=='4'
            page.locator('#schedule-metrics summary').click()
            values=page.locator('#schedule-insights tr[data-team="LAL"] td').all_text_contents()
            assert values==['LAL','4','2','1','2','2'],values
            # Crossing tipoff needs no click or table redraw: the minute timer removes
            # the started game and its now-ineligible future B2B pair.
            page.clock.set_system_time('2026-10-27T00:59:30Z')
            assert page.locator('#schedule-insights tr[data-team="LAL"] td').nth(2).inner_text()=='2'
            page.clock.fast_forward(60000)
            values=page.locator('#schedule-insights tr[data-team="LAL"] td').all_text_contents()
            assert values==['LAL','4','1','0','1','3'],values
            assert '2026-10-27 01:00 UTC' in page.locator('#schedule-period-context').inner_text()
            # Background tabs can throttle timers. Returning to visible refreshes
            # the cutoff immediately, even before the next interval.
            page.clock.set_system_time('2026-10-28T01:00:30Z')
            page.evaluate("Object.defineProperty(document,'visibilityState',{configurable:true,value:'hidden'});document.dispatchEvent(new Event('visibilitychange'))")
            assert page.locator('#schedule-insights tr[data-team="LAL"] td').nth(2).inner_text()=='1'
            page.evaluate("Object.defineProperty(document,'visibilityState',{configurable:true,value:'visible'});document.dispatchEvent(new Event('visibilitychange'))")
            values=page.locator('#schedule-insights tr[data-team="LAL"] td').all_text_contents()
            assert values==['LAL','4','0','0','0','4'],values
            assert '2026-10-28 01:00 UTC' in page.locator('#schedule-period-context').inner_text()
            page.clock.set_system_time('2026-10-25T12:00:00Z')
            assert 'tbd' not in page.locator('#schedule-pending').inner_text() # IDs are retained in data, not noisy product labels.
            assert '日期待定' in page.locator('#schedule-pending').inner_text()
            page.locator('#WeekCustom [data-period="LS"]').click();page.locator('#WeekCustom [data-mode="TOT"]').click()
            page.evaluate("tables.WCustom.order([tables.WCustom.column('.rank-ls-tot').index(),'asc']).draw()")
            page.locator('#teamTableWCustom .team-row[data-team="LAL"]').click()
            apply('2026-12-28','2027-01-03')
            assert '台北 01/01 10:30' in page.locator('#comparison-body').inner_text()
            assert page.evaluate("viewState.WCustom.mode==='tot'&&viewState.WCustom.period==='ls'&&teamSelection.WCustom==='LAL'")
            assert page.evaluate("tables.WCustom.column(tables.WCustom.order()[0][0]).header().classList.contains('rank-ls-tot')")
            assert original==page.evaluate("JSON.stringify(playerCatalog['1'].periods)")
            apply('2027-01-11','2027-01-24')
            assert page.locator('#comparison-body tr td').nth(1).inner_text()=='0'
            assert page.locator('#comparison-body .comparison-matchup').count()==14
            assert '沒有已公布日期' in page.locator('#teamTableWCustom').inner_text()
            apply('2027-02-15','2027-02-28') # A custom range alone is not an official platform claim.
            assert page.locator('#comparison-body tr td').nth(1).inner_text()=='2'
            apply('2026-11-02','2026-11-01');assert page.locator('#period-error').is_visible()
            assert page.evaluate('activeWeek')=='WCustom'
            apply('2026-10-01','2026-11-01');assert page.locator('#period-error').is_visible()
            apply('2026-10-26','2026-10-26');assert page.locator('#comparison-body .comparison-matchup').count()==1
            apply('2026-10-20','2026-11-19');assert page.locator('#comparison-body .comparison-matchup').count()==31
            page.locator('.tablinks').nth(3).click();assert page.evaluate('activeWeek')=='W4'
            assert page.locator('#comparison-body .comparison-matchup').count()==7
            page.locator('[data-platform="NBA"]').click()
            page.locator('#season-week').select_option('0');assert page.evaluate('activeWeek')=='WCustom'
            assert page.locator('#comparison-body .comparison-matchup').count()==7
            # The empty placeholder cannot become numeric index zero on a draw.
            # All three surfaces keep the applied closing week.
            page.locator('#season-week').select_option('24')
            season_before=page.evaluate("JSON.stringify({headers:tables.WCustom.columns('[data-schedule-day]').indexes().toArray().map(i=>tables.WCustom.column(i).header().textContent),rows:tables.WCustom.rows().data().toArray(),comparison:document.getElementById('comparison-body').innerHTML,heading:document.getElementById('custom-period-heading').textContent})")
            page.locator('#season-week').select_option('')
            page.evaluate('tables.WCustom.draw(false)')
            assert page.locator('#season-week').input_value()=='24'
            assert page.evaluate('appliedSeasonWeek')==24
            assert '2027-04-05–2027-04-11' in page.locator('#schedule-period-context').inner_text()
            assert page.locator('#schedule-insights tr[data-team="LAL"] td').all_text_contents()==['LAL','1','1','0','1','0']
            assert season_before==page.evaluate("JSON.stringify({headers:tables.WCustom.columns('[data-schedule-day]').indexes().toArray().map(i=>tables.WCustom.column(i).header().textContent),rows:tables.WCustom.rows().data().toArray(),comparison:document.getElementById('comparison-body').innerHTML,heading:document.getElementById('custom-period-heading').textContent})")
            # Official Yahoo defaults have their own week numbers and day counts.
            page.locator('[data-platform="YAHOO"]').focus();page.locator('[data-platform="YAHOO"]').press('Enter')
            assert page.locator('#season-week option').count()==24
            assert page.locator('#season-week').input_value()=='22' # Apr 5 belongs to Yahoo 23, NBA 25.
            page.locator('#season-week').select_option('0')
            assert page.evaluate("tables.WCustom.columns('[data-schedule-day]').count()") == 6
            assert page.locator('#comparison-body .comparison-matchup').count()==6
            assert '2026-10-20–2026-10-25' in page.locator('#comparison-meta').inner_text()
            long_week_results=[]
            for index,start,end,nba_indices,event_dates in [
                    ('6','2026-11-30','2026-12-13',['6','7'],['2026-12-02','2026-12-09']),
                    ('16','2027-02-15','2027-02-28',['17','18'],['2027-02-18','2027-02-25'])]:
                page.locator('#season-week').select_option(index)
                assert page.evaluate("tables.WCustom.columns('[data-schedule-day]').count()") == 14
                assert page.locator('#comparison-body .comparison-matchup').count()==14
                for selector in ['#custom-period-heading','#comparison-meta','#schedule-period-context']:
                    assert start+'–'+end in page.locator(selector).inner_text()
                def merged_schedule():
                    return page.evaluate("""()=>{const t=tables.WCustom,columns=t.columns('[data-schedule-day]').indexes().toArray(),r=t.rows({search:'none'}).data().toArray().find(r=>r[1]==='LAL');return {games:Number(r[2]),dates:columns.filter(i=>r[i]).map(i=>t.column(i).header().textContent.slice(0,10)),comparisonGames:Number(document.querySelector('#comparison-body tr').cells[1].textContent),comparisonDates:Array.from(document.querySelector('#comparison-body tr').cells).filter(c=>c.classList.contains('comparison-matchup')&&c.innerHTML).map(c=>document.querySelector('#comparison-head tr').cells[c.cellIndex].textContent.slice(0,10))};}""")
                merged=merged_schedule()
                assert merged==dict(games=2,dates=event_dates,comparisonGames=2,comparisonDates=event_dates),merged
                assert page.locator('#teamTableWCustom tr[data-team="LAL"] td').nth(1).inner_text()=='2'
                assert page.locator('#schedule-insights tr[data-team="LAL"] td').all_text_contents()==['LAL','2','2','0','2','0']
                for nba_index,event_date in zip(nba_indices,event_dates):
                    page.locator('[data-platform="NBA"]').click();page.locator('#season-week').select_option(nba_index)
                    single=merged_schedule()
                    assert single==dict(games=1,dates=[event_date],comparisonGames=1,comparisonDates=[event_date]),single
                    page.locator('[data-platform="YAHOO"]').click()
                    assert page.locator('#season-week').input_value()==index
                    assert merged_schedule()==merged
                    page.locator('[data-platform="NBA"]').click()
                    assert page.locator('#season-week').input_value()==nba_index
                    assert merged_schedule()==single
                    page.locator('[data-platform="YAHOO"]').click()
                long_week_results.append(dict(yahoo_week=int(index)+1,nba_weeks=[int(i)+1 for i in nba_indices],event_dates=event_dates,merged_games=2,nba_games=[1,1],comparison_verified=True,roundtrips_verified=True))
            # ESPN's source Weekly calendar has 24 regular periods, not Yahoo's 23.
            page.locator('[data-platform="ESPN"]').focus();page.locator('[data-platform="ESPN"]').press('Enter')
            assert page.locator('#season-week option').count()==25
            assert '聯盟 matchup／季後賽日期可自訂' in page.locator('#platform-note').inner_text()
            assert '待核' not in page.locator('#platform-note').inner_text()
            espn_periods=page.evaluate('platformPeriods.ESPN.periods');events=page.evaluate('scheduleEvents')
            for index,period in enumerate(espn_periods):
                page.evaluate('window.retiredPeriodTable=tables.WCustom.table().node()')
                page.locator('#season-week').select_option(str(index))
                assert page.evaluate('!retiredPeriodTable.isConnected&&!$.hasData(retiredPeriodTable)')
                selected=[e for e in events if e['date_et'] and period['start']<=e['date_et']<=period['end'] and 'LAL' in [e['home'],e['away']]]
                expected=dict(games=sum(e['status'] not in ['cancelled','postponed','suspended'] for e in selected),dates=sorted({e['date_et'] for e in selected}))
                current=merged_schedule()
                assert current==dict(**expected,comparisonGames=expected['games'],comparisonDates=expected['dates']),current
                assert page.locator('#custom-period-heading').inner_text()==period['label']
                assert original==page.evaluate("JSON.stringify(playerCatalog['1'].periods)")
            # Both Cup halves stay separate in ESPN; both All-Star halves map to ESPN18.
            espn_roundtrips=[]
            for nba_index,espn_index,yahoo_index in [('6','6','6'),('7','7','6'),('17','17','16'),('18','17','16')]:
                page.locator('[data-platform="NBA"]').click();page.locator('#season-week').select_option(nba_index)
                single=merged_schedule();assert single['games']==1
                page.locator('[data-platform="ESPN"]').click()
                assert page.locator('#season-week').input_value()==espn_index
                expected_espn=merged_schedule()
                assert expected_espn['games']==(2 if espn_index=='17' else 1)
                assert page.evaluate("tables.WCustom.columns('[data-schedule-day]').count()") == (14 if espn_index=='17' else 7)
                page.locator('[data-platform="YAHOO"]').click();assert page.locator('#season-week').input_value()==yahoo_index
                assert merged_schedule()['games']==2
                page.locator('[data-platform="ESPN"]').click();assert page.locator('#season-week').input_value()==espn_index
                assert merged_schedule()==expected_espn
                page.locator('[data-platform="NBA"]').click();assert page.locator('#season-week').input_value()==nba_index
                assert merged_schedule()==single
                espn_roundtrips.append(dict(nba_week=int(nba_index)+1,espn_week=int(espn_index)+1,yahoo_week=int(yahoo_index)+1,espn_games=expected_espn['games'],verified=True))
            page.locator('[data-platform="YAHOO"]').click()
            page.locator('#season-week').select_option('19')
            assert '預設季後賽' in page.locator('#comparison-meta').inner_text()
            page.locator('#season-week').select_option('7')
            page.evaluate("filterTeam(null,'LAL','WCustom')")
            page.locator('#WeekCustom [data-period="LS"]').click();page.locator('#WeekCustom [data-mode="TOT"]').click()
            page.evaluate("tables.WCustom.page.len(50).search('Fixture Alpha',false,false).order([tables.WCustom.column('.rank-ls-tot').index(),'asc']).draw()")
            page.locator('[data-platform="ESPN"]').click()
            assert page.locator('#season-week').input_value()=='8'
            assert page.evaluate("viewState.WCustom.mode==='tot'&&viewState.WCustom.period==='ls'&&teamSelection.WCustom==='LAL'&&tables.WCustom.search()==='Fixture Alpha'")
            # Date anchoring maps Yahoo 8 to NBA 9 rather than preserving a number.
            page.locator('[data-platform="NBA"]').click()
            assert page.locator('#season-week').input_value()=='8'
            assert page.evaluate("viewState.WCustom.mode==='tot'&&viewState.WCustom.period==='ls'&&teamSelection.WCustom==='LAL'&&tables.WCustom.search()==='Fixture Alpha'")
            assert page.evaluate("tables.WCustom.column(tables.WCustom.order()[0][0]).header().classList.contains('rank-ls-tot')")
            assert page.evaluate('tables.WCustom.page.len()')==50
            page.locator('[data-platform="YAHOO"]').click()
            assert page.locator('#season-week').input_value()=='7'
            # A merged Yahoo week must not lose the second NBA week's anchor
            # when switching back to NBA.
            page.locator('[data-platform="NBA"]').click();page.locator('#season-week').select_option('18')
            page.locator('[data-platform="YAHOO"]').click();assert page.locator('#season-week').input_value()=='16'
            page.locator('[data-platform="NBA"]').click();assert page.locator('#season-week').input_value()=='18'
            assert original==page.evaluate("JSON.stringify(playerCatalog['1'].periods)")
            apply('2026-10-20','2026-11-02');page.locator('#show-all-players').click()
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
            page.screenshot(path=str(Path(output)/('schedule-preview-'+str(width)+'.png')),full_page=False)
            assert not errors,errors;assert not failed,failed
            results.append(dict(width=width,nba_weeks=25,yahoo_weeks=23,espn_weeks=24,yahoo_short_opening_and_double_weeks=True,long_week_event_regressions=long_week_results,espn_all_periods_verified=True,retired_table_jquery_data_released=True,three_platform_roundtrips=espn_roundtrips,date_anchored_platform_switch=True,filters_search_mode_order_preserved=True,custom_days=[1,7,14,31],cross_year=True,invalid_range_rejected=True,remaining_b2b_light_verified=True,tipoff_timer_refresh=True,foreground_refresh=True,empty_season_selection_preserves_applied_period=True,statistics_unchanged=True,js_errors=errors,failed_requests=failed))
            context.close()
        browser.close()
    Path(output,'schedule-browser-result.json').write_text(json.dumps(dict(fixture=True,url=url,results=results),indent=2))
    print(json.dumps(results))

if __name__=='__main__':
    import sys
    output=Path(sys.argv[1] if len(sys.argv)>1 else tempfile.mkdtemp(prefix='fantasy-schedule-preview-')).resolve()
    path=build_fixture(output)
    handler=functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(output))
    server=http.server.ThreadingHTTPServer(('127.0.0.1',0),handler)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    try:run('http://127.0.0.1:'+str(server.server_port)+'/'+path.name,output)
    finally:server.shutdown()
