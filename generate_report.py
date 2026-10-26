import pandas as pd
from datetime import datetime, timedelta, timezone
import utils
import webbrowser
import os
import sys
import json
from html import escape
from pathlib import Path
import hashlib
import base64
from player_catalog import build_catalog, add_pr_ranks, metric_pr
from fantasy_periods import build_platform_periods
from roto_data import build_data, source_reference, write_data
from roto_package import build_package
from report_data import pack_catalog, pack_events, write_script, script_tags

IDENTITY_COLUMNS = ['PLAYER_ID','PLAYER_NAME','TEAM_ID','TEAM_ABBREVIATION']

def matchup_badge(opp_abbr, is_home, ratings):
    info=ratings.get(opp_abbr)
    label=escape(f"{'vs' if is_home else '@'} {opp_abbr}")
    if info and info.get('Estimated') and info.get('Rank') is not None:
        rank,population=info['Rank'],info['Population']
        color=utils.get_color_for_rank(rank,population)
        note=f"ESPN 近10場估算防守效率 (可跨季): {info['DefRtg']:.1f}失分/100估算回合; 排名 {rank}/{population}; {info['Games']}/10場; {info['Start']}–{info['End']}"
        detail=f"#{rank}" if population==30 else f"#{rank}/{population}"
    elif info:
        color=utils.get_color_for_rank(None)
        detail=f"{info['Games']}/10"
        note=f"近10場估算防守效率資料未完整：{info['Games']}/10；暫不排名。"
    else:
        color,note,detail=utils.get_color_for_rank(None),'最近10場例行賽防守資料暫缺','—'
    return f"<div class='matchup' style='background-color:{color};padding:4px;border-radius:4px;text-align:center;font-weight:bold' title='{escape(note,quote=True)}'>{label}<br><small>{escape(detail)}</small></div>"


def scheduled_matchup(row, ratings):
    badge=matchup_badge(row['MATCHUP'].split(' ')[2],'vs.' in row['MATCHUP'],ratings)
    if 'STATUS' not in row:return badge
    labels={'scheduled':'未開賽','in_progress':'進行中','final':'已完賽','postponed':'延賽','cancelled':'取消','suspended':'暫停','delayed':'延遲','unknown':'狀態待確認'}
    stamp=row.get('TIPOFF_UTC')
    if not isinstance(stamp,str):stamp=None
    if isinstance(stamp,str) and stamp:
        from zoneinfo import ZoneInfo
        instant=datetime.fromisoformat(stamp.replace('Z','+00:00'))
        clock=instant.astimezone(ZoneInfo('Asia/Taipei')).strftime('%m/%d %H:%M')
    else:clock='時間待定'
    return badge+f"<time class='game-time' datetime='{escape(stamp or '',quote=True)}' title='{escape(labels[row['STATUS']],quote=True)}'>{escape(clock)}</time>"


def schedule_event_payload(schedule, ratings):
    events={}
    for row in schedule.to_dict('records'):
        eid=row.get('EVENT_ID')
        if not eid:continue
        event=events.setdefault(eid,dict(id=eid,date_et=str(row['GAME_DATE']) if pd.notna(row['GAME_DATE']) else None,
            tipoff_utc=row['TIPOFF_UTC'] if pd.notna(row['TIPOFF_UTC']) else None,status=row['STATUS'],season_type=int(row['SEASON_TYPE']),time_confirmed=bool(row['TIME_CONFIRMED'])))
        side='home' if 'vs.' in row['MATCHUP'] else 'away'
        event[side]=row['TEAM_ABBREVIATION'];event[side+'_html']=scheduled_matchup(row,ratings)
    return list(events.values())


def season_schedule_payload(schedule, weeks, ratings):
    output=[]
    for week in weeks:
        days=[week['start']+timedelta(days=i) for i in range(7)]
        selected=schedule.loc[(schedule['GAME_DATE']>=days[0])&(schedule['GAME_DATE']<=days[-1])]
        teams={}
        for row in selected.to_dict('records'):
            abbr=row['TEAM_ABBREVIATION']
            data=teams.setdefault(abbr,dict(games=0,days=['']*7))
            index=(row['GAME_DATE']-days[0]).days
            if data['days'][index]:raise ValueError('Multiple same-day NBA games for a team')
            data['games']+=row.get('STATUS') not in ['cancelled','postponed','suspended']
            data['days'][index]=scheduled_matchup(row,ratings)
        output.append(dict(number=week['number'],label=week['label'],start=str(week['start']),end=str(week['end']),headers=[d.strftime('%a (%m/%d)') for d in days],
            teams=teams,events=len(selected)//2))
    return output


def generate_html_report():
    print("Initializing Fantasy NBA Report Generator V2...")

    # 1. Define Date Ranges
    today = utils.today()
    days_until_sunday = (6 - today.weekday()) % 7
    w1_end = today + timedelta(days=days_until_sunday)
    w1_start = today

    # Calculate end date for 4 weeks
    final_end = w1_end + timedelta(days=21) # 3 more weeks

    print(f"Report Range: {w1_start} to {final_end}")

    # 2. Fetch Data
    print("Fetching Schedule...")
    season_schedule = utils.get_season_schedule().copy()
    full_schedule = utils.get_schedule(w1_start, final_end)
    all_weeks = utils.season_weeks(season_schedule)

    print("Fetching Player Stats (Multi-Period)...")
    stats_dict = utils.get_player_stats_multi_period()

    print("Fetching ESPN estimated last-10 defense...")
    def_ratings = utils.get_team_defensive_ratings()

    # Counting stats use exact source totals, not rounded averages multiplied by GP.
    # MIN / FG% / FT% are intentionally excluded: the old FANTASY-SUP page shows
    # them unchanged in TOT mode (rates and minutes-per-game don't sum meaningfully).
    # Shared by process_week_grid (data) and generate_html (rendering) below.
    tot_metrics = ['PTS', 'REB', 'AST', '3PM', 'STL', 'BLK', 'TO']

    # 3. Process Data Helper
    def process_week_grid(start_date, end_date, schedule_df, stats_dict, def_ratings):
        # Create Date Headers
        days = []
        curr = start_date
        while curr <= end_date:
            days.append(curr)
            curr += timedelta(days=1)

        day_cols = [d.strftime('%a (%m/%d)') for d in days]

        # Filter schedule
        # A valid off-season window can contain no games.
        if schedule_df.empty or 'GAME_DATE' not in schedule_df.columns:
            week_games = pd.DataFrame(columns=['TEAM_ID', 'TEAM_ABBREVIATION', 'GAME_DATE', 'MATCHUP'])
        else:
            mask = (schedule_df['GAME_DATE'] >= start_date) & (schedule_df['GAME_DATE'] <= end_date)
            week_games = schedule_df.loc[mask].copy()

        # --- TEAM SCHEDULE GRID ---
        team_grid_data = []
        all_team_ids = week_games['TEAM_ID'].unique()

        for tid in all_team_ids:
            t_games = week_games[week_games['TEAM_ID'] == tid]
            if t_games.empty: continue

            abbr = t_games.iloc[0]['TEAM_ABBREVIATION']
            count=sum(g.get('STATUS') not in ['cancelled','postponed','suspended'] for g in t_games.to_dict('records'))
            row = {'TEAM_ID': tid, 'Team': abbr, 'Games': count}

            for d, col_name in zip(days, day_cols):
                g = t_games[t_games['GAME_DATE'] == d]
                if not g.empty:
                    row[col_name] = scheduled_matchup(g.iloc[0], def_ratings)
                else:
                    row[col_name] = ""
            team_grid_data.append(row)

        team_df = pd.DataFrame(team_grid_data)
        if not team_df.empty:
            team_df = team_df.sort_values('Games', ascending=False, kind='stable')

        # --- PLAYER STATS & SCHEDULE ---
        # Metric label -> raw stat column mapping, shared by all PR calculations below.
        pr_metric_map = {
            'MIN': 'MIN', 'PTS': 'PTS', 'REB': 'REB', 'AST': 'AST',
            '3PM': 'FG3M', 'STL': 'STL', 'BLK': 'BLK',
            'FG%': 'FG_PCT', 'FT%': 'FT_PCT', 'TO':'TO',
        }

        # Complete period populations; no qualification cutoff or current-roster filtering.
        ranked = {}
        for period in ['Season', 'L7', 'L14', 'LastSeason']:
            pool = stats_dict[period].copy()
            pool = pool[pool['GP'] > 0]
            for label, raw in pr_metric_map.items():
                pool[f'{label}_PR'] = metric_pr(pool[raw],label)
                if label in tot_metrics:
                    pool[f'{label}_TOT'] = pool[raw+'_TOTAL']
                    pool[f'{label}_TOT_PR'] = metric_pr(pool[f'{label}_TOT'],label)
            ranked[period] = add_pr_ranks(pool)
        base_df = ranked['Season'].copy()
        roster = stats_dict.get('Roster')
        if roster is None:
            roster = ranked['LastSeason'][IDENTITY_COLUMNS].copy()
        extra = roster.loc[~roster['PLAYER_ID'].isin(base_df['PLAYER_ID']), IDENTITY_COLUMNS]
        base_df = pd.concat([base_df, extra], ignore_index=True)
        # Current roster overrides historical team assignment without altering stats/PR.
        identities = roster.set_index('PLAYER_ID')
        for column in ['PLAYER_NAME', 'TEAM_ID', 'TEAM_ABBREVIATION']:
            mapped = base_df['PLAYER_ID'].map(identities[column])
            base_df[column] = base_df[column].where(mapped.isna(), mapped)
        l7 = ranked['L7'].add_suffix('_L7')
        l14 = ranked['L14'].add_suffix('_L14')
        last_season = ranked['LastSeason'].add_suffix('_LS')

        # Merge on PLAYER_ID
        merged = pd.merge(base_df, l7, left_on='PLAYER_ID', right_on='PLAYER_ID_L7', how='left')
        merged = pd.merge(merged, l14, left_on='PLAYER_ID', right_on='PLAYER_ID_L14', how='left')
        if not last_season.empty:
            merged = pd.merge(merged, last_season, left_on='PLAYER_ID', right_on='PLAYER_ID_LS', how='left')

        # Add Schedule Grid to Players
        if not team_df.empty:
            schedule_cols = ['Games'] + day_cols
            team_schedule = team_df[['Team'] + schedule_cols].rename(columns={'Team': 'TEAM_ABBREVIATION'})
            merged = pd.merge(merged, team_schedule, on='TEAM_ABBREVIATION', how='left')

            # Fill NaN schedule
            for c in schedule_cols:
                if c == 'Games':
                    merged[c] = merged[c].fillna(0).astype(int)
                else:
                    merged[c] = merged[c].fillna('-')

        # Format Player
        merged['Player'] = merged.apply(lambda x: f"<b>{escape(str(x['PLAYER_NAME']))}</b> <br><span style='color:var(--muted)'>{escape(str(x['TEAM_ABBREVIATION']))}</span>", axis=1)

        # Format Stats (Season)
        merged['FG%'] = (merged['FG_PCT'] * 100).map(lambda v: f'{v:.1f}%' if pd.notna(v) else pd.NA)
        merged['FT%'] = (merged['FT_PCT'] * 100).map(lambda v: f'{v:.1f}%' if pd.notna(v) else pd.NA)
        merged = merged.rename(columns={'FG3M': '3PM'})

        # Format Stats (L7)
        if 'FG_PCT_L7' in merged.columns:
            merged['FG%_L7'] = (merged['FG_PCT_L7'] * 100).map(lambda v: f'{v:.1f}%' if pd.notna(v) else pd.NA)
            merged['FT%_L7'] = (merged['FT_PCT_L7'] * 100).map(lambda v: f'{v:.1f}%' if pd.notna(v) else pd.NA)
            merged = merged.rename(columns={'FG3M_L7': '3PM_L7', 'PTS_L7': 'PTS_L7', 'REB_L7': 'REB_L7', 'AST_L7': 'AST_L7', 'STL_L7': 'STL_L7', 'BLK_L7': 'BLK_L7'})

        # Format Stats (L14)
        if 'FG_PCT_L14' in merged.columns:
            merged['FG%_L14'] = (merged['FG_PCT_L14'] * 100).map(lambda v: f'{v:.1f}%' if pd.notna(v) else pd.NA)
            merged['FT%_L14'] = (merged['FT_PCT_L14'] * 100).map(lambda v: f'{v:.1f}%' if pd.notna(v) else pd.NA)
            merged = merged.rename(columns={'FG3M_L14': '3PM_L14', 'PTS_L14': 'PTS_L14', 'REB_L14': 'REB_L14', 'AST_L14': 'AST_L14', 'STL_L14': 'STL_L14', 'BLK_L14': 'BLK_L14'})

        # Format Stats (Last Season)
        if 'FG_PCT_LS' in merged.columns:
            merged['FG%_LS'] = (merged['FG_PCT_LS'] * 100).map(lambda v: f'{v:.1f}%' if pd.notna(v) else pd.NA)
            merged['FT%_LS'] = (merged['FT_PCT_LS'] * 100).map(lambda v: f'{v:.1f}%' if pd.notna(v) else pd.NA)
            merged = merged.rename(columns={'FG3M_LS': '3PM_LS'})

        return team_df, merged, day_cols

    # 4. Generate HTML
    def generate_html(team_df, player_df, day_cols, table_id_suffix):
        if player_df.empty: return "<p>No data.</p>"

        # --- Player Table HTML ---
        # Columns: Player, Games, [Days], [Stats Season], [Stats L7], [Stats L14], [Stats Last Season]

        # Stat Columns Definition
        stat_metrics = ['MIN', 'PTS', 'REB', 'AST', '3PM', 'STL', 'BLK', 'FG%', 'FT%', 'TO', 'Rank']

        player_html = f"""
        <div class="player-section"><div class="player-heading"><h3>球員名單</h3><span id="selection{table_id_suffix}">全體球員</span></div>
            <p class="player-hint">預設數據優先；可開啟逐日賽程。勾選「比較」後從上方查看，也可自訂排名項目。</p>
            <div class="controls">
                <button class="btn-stat active" data-period="Season" onclick="switchStats('Season', '{table_id_suffix}')">本季</button>
                <button class="btn-stat" data-period="L7" onclick="switchStats('L7', '{table_id_suffix}')">近7天</button>
                <button class="btn-stat" data-period="L14" onclick="switchStats('L14', '{table_id_suffix}')">近14天</button>
                <button class="btn-stat" data-period="LS" onclick="switchStats('LS', '{table_id_suffix}')">上季</button>
                <span class="stat-divider">數值</span>
                <button class="btn-stat active" aria-pressed="true" data-mode="AVG" onclick="switchDisplayMode('AVG', '{table_id_suffix}')">平均 AVG</button>
                <button class="btn-stat" aria-pressed="false" data-mode="TOT" onclick="switchDisplayMode('TOT', '{table_id_suffix}')">總量 TOT</button>
                <button class="btn-reset" onclick="resetTeamFilter('{table_id_suffix}')">全體球員</button>
            </div>
            <table id="playerTable{table_id_suffix}" class="display" style="width:100%">
                <thead>
                    <tr>
                        <th>Player</th>
                        <th>Team</th> <!-- Hidden column for filtering -->
                        <th>Games</th>
                        {''.join([f'<th data-schedule-day="{i}">{d}</th>' for i,d in enumerate(day_cols)])}
                        <!-- Season Stats Headers (AVG / TOT) -->
                        {''.join([f'<th class="stat-season stat-avg{ " rank-season-avg" if m=="Rank" else "" }" title="{ "失誤越少PR越高" if m=="TO" else "" }">{m}</th>' for m in stat_metrics])}
                        {''.join([f'<th class="stat-season stat-tot{ " rank-season-tot" if m=="Rank" else "" }" style="display:none" title="{ "失誤越少PR越高" if m=="TO" else "" }">{m}</th>' for m in stat_metrics])}
                        <!-- L7 Stats Headers (AVG / TOT) -->
                        {''.join([f'<th class="stat-l7 stat-avg{ " rank-l7-avg" if m=="Rank" else "" }" style="display:none" title="{ "失誤越少PR越高" if m=="TO" else "" }">{m}</th>' for m in stat_metrics])}
                        {''.join([f'<th class="stat-l7 stat-tot{ " rank-l7-tot" if m=="Rank" else "" }" style="display:none" title="{ "失誤越少PR越高" if m=="TO" else "" }">{m}</th>' for m in stat_metrics])}
                        <!-- L14 Stats Headers (AVG / TOT) -->
                        {''.join([f'<th class="stat-l14 stat-avg{ " rank-l14-avg" if m=="Rank" else "" }" style="display:none" title="{ "失誤越少PR越高" if m=="TO" else "" }">{m}</th>' for m in stat_metrics])}
                        {''.join([f'<th class="stat-l14 stat-tot{ " rank-l14-tot" if m=="Rank" else "" }" style="display:none" title="{ "失誤越少PR越高" if m=="TO" else "" }">{m}</th>' for m in stat_metrics])}
                        <!-- Last Season Stats Headers (AVG / TOT) -->
                        {''.join([f'<th class="stat-ls stat-avg{ " rank-ls-avg" if m=="Rank" else "" }" style="display:none" title="{ "失誤越少PR越高" if m=="TO" else "" }">{m}</th>' for m in stat_metrics])}
                        {''.join([f'<th class="stat-ls stat-tot{ " rank-ls-tot" if m=="Rank" else "" }" style="display:none" title="{ "失誤越少PR越高" if m=="TO" else "" }">{m}</th>' for m in stat_metrics])}
                    </tr>
                </thead>
                <tbody>
        """

        player_html += "</tbody></table></div>"

        return "<hr>" + player_html

    # Generate 4 Weeks
    weeks_data = []
    quick_periods = {}
    comparison_catalog = {}
    current_start = w1_start
    current_end = w1_end

    for i in range(4):
        print(f"Processing Week {i+1} ({current_start} - {current_end})...")
        t, p, d = process_week_grid(current_start, current_end, full_schedule, stats_dict, def_ratings)
        if i == 0:comparison_catalog=build_catalog(p)
        content = generate_html(t, p, d, f'W{i+1}')
        weeks_data.append({
            'id': f'Week{i+1}',
            'label': f'近{i+1}週 ({current_start.strftime("%m/%d")} - {current_end.strftime("%m/%d")})',
            'content': content
        })
        quick_periods[f'W{i+1}']=dict(start=str(current_start),end=str(current_end),label=weeks_data[-1]['label'])

        # Next week
        current_start = current_end + timedelta(days=1)
        current_end = current_start + timedelta(days=6)

    events_payload=schedule_event_payload(season_schedule,def_ratings)
    platform_periods=build_platform_periods(stats_dict['metadata']['season'],all_weeks,events_payload)
    season_payload=platform_periods['NBA']['periods']
    platform_buttons=''.join(
        f'<button type="button" class="platform-button" data-platform="{key}" aria-pressed="false" '
        f'aria-describedby="platform-note" {"disabled" if not platform_periods[key]["available"] else ""}>'
        f'{key}{" <small>待核</small>" if not platform_periods[key]["available"] and key != "NBA" else ""}</button>'
        for key in ['YAHOO','ESPN','NBA'])
    season_select='<label class="season-picker" for="season-week">週次<select id="season-week" onchange="selectSeasonWeek(this.value)" aria-describedby="platform-note"><option value="">選擇週次</option></select></label>'
    tab_buttons = ''.join(
        f"<button class='tablinks' onclick=\"openWeek(event, '{w['id']}')\" "
        f"id='{ 'defaultOpen' if i == 0 else '' }'>{w['label']}</button>"
        for i, w in enumerate(weeks_data)
    )
    week_panels = ''.join(
        f"<div id='{w['id']}' class='tabcontent'>{w['content']}</div>"
        for w in weeks_data
    )
    week_panels += '<div id="WeekCustom" class="tabcontent"><h3 id="custom-period-heading"></h3><div id="custom-period-content"></div></div>'
    metadata = stats_dict['metadata']
    generated_at = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    provenance = dict(utils.PROVENANCE)
    provenance['season_weeks']=[dict(number=w['number'],start=str(w['start']),end=str(w['end']),
        events=season_payload[i]['events']) for i,w in enumerate(all_weeks)]
    provenance.update(generated_at=generated_at, stats_source='ESPN', defense_source=provenance.get('defense',{}).get('source'),
                      period_populations={k:len(stats_dict[k]) for k in ['Season','L7','L14','LastSeason']})
    provenance['roto_references']={key:source_reference(stats_dict[key]) for key in ['Season','LastSeason']}
    provenance['schedule_events']=[{k:v for k,v in e.items() if not k.endswith('_html')} for e in events_payload]
    provenance['fantasy_periods']=dict(timezone='America/New_York',quick_periods=quick_periods,
        platforms=platform_periods)
    last_period = provenance.get('players_' + str(int(metadata['last_season'][:4])+1), {})
    last_end = last_period.get('source_period_end','未查得')[:10]
    data_notice = (
        "選週只切換賽程，統計與PR維持報告更新時的資料。 "
        "NBA 賽程週採美東週一至週日，首場當季例行賽所在週為 Week 1；Yahoo 採經核對的當季公開預設週表；ESPN 採已核實當季的全季 Weekly 週曆，未核實球季不開放。聯盟 matchup／季後賽日期可自訂。近1週從今天起至週日。僅列來源已公布日期，尚未排定賽事不虛構；無比賽週仍保留。 "
        f"報告產生時間：{generated_at}。ESPN 球員資料：當季 {metadata['season']}，上季 {metadata['last_season']} "
        f"例行賽來源期間至 {last_end}。近期窗口為美東日期 {today} 前完整7／14天。"
        f"球隊／球員名單取自本次 ESPN roster；週次依美東計分日；賽事日期與時間依所選時區顯示，四週範圍 {w1_start}–{final_end}。"
        f"各期 PR 母體：當季 {len(stats_dict['Season'])}、近7天 {len(stats_dict['L7'])}、近14天 {len(stats_dict['L14'])}、上季 {len(stats_dict['LastSeason'])} 位有出賽球員。"
    )
    if stats_dict['Season'].empty:
        data_notice += " 當季例行賽尚無球員統計，預設顯示 Last Season；缺值不填造。"
    data_notice += ' ESPN/NBA資料再散布授權仍未確認。'
    defense_meta = provenance.get('defense', {})
    if defense_meta.get('estimated'):
        defense_notice = (
            "近10場估算防守效率：固定使用 ESPN，當季不足十場接續上季例行賽。"
            "估算回合＝對手 FGA＋0.4×FTA－進攻籃板＋總失誤；每百估算回合失分越低，排名越前。"
            f"完整球隊 {defense_meta.get('eligible_teams',0)}/30，最新比賽 {defense_meta.get('last_game') or '暫缺'}。"
            "這是估算值；不足十場或缺少必要欄位以 n/10 標示，不列排名，也不以第十一場補替。"
        )
    else:defense_notice = "近10場估算防守效率暫缺；球員統計與賽程正常更新。"
    defense_legend = f'<b>近10場估算防守效率</b><span>完整 {defense_meta.get("eligible_teams",0)}/30 隊</span>'
    if defense_meta.get('eligible_teams'):
        defense_legend += f'<span><i class="dot" style="background:{utils.get_color_for_rank(30)}"></i>較好打</span><span><i class="dot" style="background:{utils.get_color_for_rank(15)}"></i>中段</span><span><i class="dot" style="background:{utils.get_color_for_rank(1)}"></i>較難打</span>'
    defense_legend += f'<span><i class="dot" style="background:{utils.get_color_for_rank(None)}"></i>暫缺</span>'
    dashboard_css = Path('dashboard.css').read_text(encoding='utf-8-sig')
    roster_count = len(stats_dict.get('Roster', stats_dict['Season']))
    defense_count = defense_meta.get('eligible_teams', len(def_ratings))
    fixture_caption = '本季例行賽尚無球員統計，預設顯示上季' if stats_dict['Season'].empty else f"本季 {metadata['season']} 球員統計"
    def integrity(name):
        return 'sha384-' + base64.b64encode(hashlib.sha384(Path('assets',name).read_bytes()).digest()).decode()
    jquery_sri = integrity('jquery-3.7.1.min.js')
    datatables_sri = integrity('datatables-2.3.7.min.js')
    css_sri = integrity('datatables-2.3.7.min.css')
    default_period = 'Season' if not stats_dict['Season'].empty else 'LS'
    write_script('report_data.js', 'REPORT_DATA', dict(version=1, generated_at=generated_at,
        catalog=pack_catalog(comparison_catalog), events=pack_events(events_payload), weeks=season_payload,
        platforms=platform_periods, quick=quick_periods,
        meta=dict(season=metadata['season'],lastSeason=metadata['last_season'],defaultPeriod=default_period.lower())))

    html_template = f"""
    <!DOCTYPE html>
    <html lang="zh-Hant">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width,initial-scale=1">
        <meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src data:; connect-src 'none'; base-uri 'none'; form-action 'none'">
        <title>球員與賽程 | FANTASYORGCAT</title>
        <link rel="stylesheet" type="text/css" href="assets/datatables-2.3.7.min.css" integrity="{css_sri}">
        <style>{dashboard_css}</style>
        <script type="text/javascript" charset="utf8" src="assets/jquery-3.7.1.min.js" integrity="{jquery_sri}"></script>
        <script type="text/javascript" charset="utf8" src="assets/datatables-2.3.7.min.js" integrity="{datatables_sri}"></script>
        {script_tags()}
    </head>
    <body class="dashboard-page">
        <div class="container">
            <header class="appbar"><div class="brand"><span class="brand-mark">FC</span><div>FANTASYORGCAT<small>NBA FANTASY 工具箱</small></div></div><div class="app-status">ESPN<br>更新 {escape(generated_at)}</div><div class="site-preferences" data-site-preferences></div><nav class="site-nav" aria-label="網站導覽"><a href="index.html" aria-current="page">球員與賽程</a><a href="roto.html">九項配隊</a></nav></header>
            <section class="hero"><div><h1>把下一場排入你的賽程</h1><p>選擇週次、篩選球隊，再勾選球員一起比較。</p></div><div class="hero-meta"><strong>{escape(metadata['season'])} NBA</strong><span id="hero-period-range">{escape(str(w1_start))} — {escape(str(final_end))}</span></div></section>
            <details class="data-details"><summary>資料快照與來源 · {escape(fixture_caption)}</summary><div class="metric-grid">
                <div class="metric-card"><span>現役球員</span><strong>{roster_count}</strong><small>人</small></div>
                <div class="metric-card"><span>四週賽程</span><strong>{provenance.get('schedule',{}).get('events_in_window',0)}</strong><small>場</small></div>
                <div class="metric-card"><span>防守資料 · 截至 {escape(str(defense_meta.get('last_game') or '暫缺'))}</span><strong>{defense_count}<small>/ 30 隊</small></strong></div>
                <div class="metric-card"><span>上季 PR 母體</span><strong>{len(stats_dict['LastSeason'])}</strong><small>人</small></div>
            </div><p class="data-notice">{escape(data_notice)}</p><p class="defense-notice">{escape(defense_notice)}</p></details>
            <div class="workspace-bar"><nav class="platform-switch" aria-label="週次類型">{platform_buttons}</nav>{season_select}<div class="filter-tools"><span id="active-selection" class="selection-label" role="status">全體球員</span><button id="show-all-players" class="global-reset" onclick="resetActiveTeamFilter()" aria-pressed="true" title="清除球隊與搜尋，保留統計期間及AVG/TOT">全體球員</button><button id="jump-players" type="button" class="btn-stat">球員名單 ↓</button><a id="view-comparison" href="#comparison-panel" class="btn-stat" hidden>比較 0 人</a></div></div>
            <section class="period-tools" aria-label="賽程資訊"><details id="schedule-extras"><summary>自訂期間／近期快捷</summary><p id="platform-note" class="platform-note" role="status"></p><nav class="tab" aria-label="近期週次">{tab_buttons}</nav><p>美東日期，含迄日；可依自己的聯盟設定輸入 1–31 天。</p><div class="period-inputs"><label>起日（美東）<input id="period-start" type="date" value="{w1_start}"></label><label>迄日（含，美東）<input id="period-end" type="date" value="{w1_end}"></label><button id="apply-custom-period" class="btn-stat" type="button">套用自訂期間</button></div><p id="period-error" role="alert" hidden></p></details><p id="schedule-freshness" role="status"></p><details id="schedule-metrics"><summary>剩餘排程、背靠背與低比賽日</summary><p>依目前快照與瀏覽時間計算球隊排程；未套用傷病、陣容、位置或 GP 上限，不代表可用上場場次。低比賽日指美東當日全聯盟 1–5 場。</p><p id="schedule-period-context"></p><div id="schedule-insights" class="schedule-scroll"></div><div id="schedule-pending"></div></details></section>
            <div class="legend">{defense_legend}</div>
            <section id="comparison-panel" class="player-section" hidden><div class="player-heading"><h3>球員比較</h3><button id="clear-comparison" type="button" class="btn-stat">清空比較</button><a id="open-roto" href="roto.html" target="_blank" rel="noopener" class="btn-stat roto-link">用勾選配隊 ↗</a></div><div class="controls"><label>統計期間 <select id="comparison-period"><option value="season">本季</option><option value="l7">近7天</option><option value="l14">近14天</option><option value="ls">上季</option></select></label><label>顯示 <select id="comparison-mode"><option value="avg">平均 AVG</option><option value="tot">總量 TOT</option></select></label></div><p id="comparison-meta"></p><div class="comparison-scroll"><table id="comparison-table"><thead id="comparison-head"></thead><tbody id="comparison-body"></tbody></table></div></section>
            {week_panels}
            <footer class="footer">FANTASYORGCAT · 每日資料快照 · 球隊防守非位置別 DvP</footer>
        </div>
    </body>
    </html>
    """

    output_file = "fantasy_nba_report_v2.html"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html_template)

    Path("data_snapshot.json").write_text(json.dumps(provenance, ensure_ascii=False, indent=2), encoding="utf-8")
    write_data(build_data(comparison_catalog,provenance,source_reference(stats_dict['LastSeason']),season=metadata['last_season']) if provenance.get('fixture') else build_package(comparison_catalog,provenance))
    print(f"Report generated: {output_file}")
    if os.environ.get('OPEN_REPORT') == '1':
        webbrowser.open('file://' + os.path.realpath(output_file))

if __name__ == "__main__":
    # Windows consoles often default to a legacy codepage (e.g. cp950) that can't
    # encode the emoji used in the progress prints -> UnicodeEncodeError. Force
    # UTF-8 output; guarded because reconfigure() needs Python 3.7+.
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass
    if '--offline' in sys.argv:
        from offline_report import regenerate
        regenerate()
    else:
        generate_html_report()
