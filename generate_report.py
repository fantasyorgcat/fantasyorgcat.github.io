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

IDENTITY_COLUMNS = ['PLAYER_ID','PLAYER_NAME','TEAM_ID','TEAM_ABBREVIATION']

def matchup_badge(opp_abbr, is_home, ratings):
    info=ratings.get(opp_abbr)
    label=escape(f"{'vs' if is_home else '@'} {opp_abbr}")
    if info:
        rank,population=info['Rank'],info['Population']
        color=utils.get_color_for_rank(rank,population)
        note=f"PBP Stats 最近10場已完成例行賽 (可跨季): {info['DefRtg']:.1f}失分/100防守回合; 排名 {rank}/{population}; {info['Games']}/10場; {info['Start']}–{info['End']}"
        detail=f"近10場 {rank}/{population} · {info['Games']}/10"
    else:
        color,note,detail='#eeeeee','最近10場例行賽防守資料暫缺','防守暫缺 · 0/10'
    return f"<div class='matchup' style='background-color:{color};padding:4px;border-radius:4px;text-align:center;font-weight:bold' title='{escape(note,quote=True)}'>{label}<br><small>{escape(detail)}</small></div>"


def scheduled_matchup(row, ratings):
    badge=matchup_badge(row['MATCHUP'].split(' ')[2],'vs.' in row['MATCHUP'],ratings)
    if 'STATUS' not in row:return badge
    labels={'scheduled':'未開賽','in_progress':'進行中','final':'已完賽','postponed':'延賽','cancelled':'取消','suspended':'暫停','delayed':'延遲','unknown':'狀態待確認'}
    stamp=row.get('TIPOFF_UTC')
    if stamp:
        from zoneinfo import ZoneInfo
        instant=datetime.fromisoformat(stamp.replace('Z','+00:00'))
        et=instant.astimezone(ZoneInfo('America/New_York')).strftime('%m/%d %H:%M')
        taipei=instant.astimezone(ZoneInfo('Asia/Taipei')).strftime('%m/%d %H:%M')
        clock=f'美東 {et} · 台北 {taipei}'
    else:clock='開賽時間待定'
    return badge+f"<small class='game-time'>{escape(clock)}<br>{escape(labels[row['STATUS']])}</small>"


def schedule_event_payload(schedule, ratings):
    events={}
    for row in schedule.to_dict('records'):
        eid=row.get('EVENT_ID')
        if not eid:continue
        event=events.setdefault(eid,dict(id=eid,date_et=str(row['GAME_DATE']) if row['GAME_DATE'] is not None else None,
            tipoff_utc=row['TIPOFF_UTC'],status=row['STATUS'],season_type=int(row['SEASON_TYPE']),time_confirmed=bool(row['TIME_CONFIRMED'])))
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

    print("Fetching Defensive Ratings...")
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
            team_df = team_df.sort_values('Games', ascending=False)

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
        merged['Player'] = merged.apply(lambda x: f"<b>{escape(str(x['PLAYER_NAME']))}</b> <br><span style='color:#888'>{escape(str(x['TEAM_ABBREVIATION']))}</span>", axis=1)

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

        # --- Team Table HTML ---
        team_html = ""
        if not team_df.empty:
            team_html = f"""
            <div class="team-section">
                <h3>球隊賽程 <small>點選球隊篩選球員</small></h3><div class="schedule-scroll">
                <table id="teamTable{table_id_suffix}" class="display compact" style="width:100%">
                    <thead>
                        <tr>
                            <th>Team</th>
                            <th>Games</th>
                            {''.join([f'<th>{d}</th>' for d in day_cols])}
                        </tr>
                    </thead>
                    <tbody>
            """
            for _, row in team_df.iterrows():
                team_html += f"<tr class='team-row' data-team='{row['Team']}' onclick='filterTeam(this, \"{row['Team']}\", \"{table_id_suffix}\")'>"
                team_html += f"<td><b>{row['Team']}</b></td><td>{row['Games']}</td>"
                for d in day_cols:
                    team_html += f"<td>{row[d]}</td>"
                team_html += "</tr>"
            team_html += "</tbody></table></div></div>"

        # --- Player Table HTML ---
        # Columns: Player, Games, [Days], [Stats Season], [Stats L7], [Stats L14], [Stats Last Season]

        # Stat Columns Definition
        stat_metrics = ['MIN', 'PTS', 'REB', 'AST', '3PM', 'STL', 'BLK', 'FG%', 'FT%', 'TO', 'Rank']

        player_html = f"""
        <div class="player-section"><div class="player-heading"><h3>球員名單</h3><span id="selection{table_id_suffix}">全體球員</span></div>
            <div class="controls">
                <button class="btn-stat active" data-period="Season" onclick="switchStats('Season', '{table_id_suffix}')">本季</button>
                <button class="btn-stat" data-period="L7" onclick="switchStats('L7', '{table_id_suffix}')">近7天</button>
                <button class="btn-stat" data-period="L14" onclick="switchStats('L14', '{table_id_suffix}')">近14天</button>
                <button class="btn-stat" data-period="LS" onclick="switchStats('LS', '{table_id_suffix}')">上季</button>
                <span style="margin-left:20px">數值</span>
                <button class="btn-stat active" data-mode="AVG" onclick="switchDisplayMode('AVG', '{table_id_suffix}')">AVG</button>
                <button class="btn-stat" data-mode="TOT" onclick="switchDisplayMode('TOT', '{table_id_suffix}')">TOT</button>
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

        for _, row in player_df.iterrows():
            player_html += f"<tr>"
            pid=str(int(row['PLAYER_ID']))
            accessible=escape(str(row['PLAYER_NAME']),quote=True)
            picks=f"<div class='pick-controls'><label><input type='checkbox' data-pick='compare' data-player-id='{pid}' aria-label='比較 {accessible}'>比較</label></div>"
            player_html += f"<td>{row['Player']}{picks}</td>"
            player_html += f"<td>{escape(str(row['TEAM_ABBREVIATION']))}</td>" # Hidden Team
            player_html += f"<td>{row.get('Games', 0)}</td>"
            for d in day_cols:
                player_html += f"<td>{row.get(d, '')}</td>"

            # Helper to create stat cell with data-order
            def create_stat_cell(row, metric, suffix, css_class, mode='avg', visible=True):
                if metric == 'Rank':
                    ending=('_TOT' if mode=='tot' else '')+('_'+suffix if suffix else '')
                    rank=row.get('PR_RANK'+ending)
                    present=rank is not None and pd.notna(rank)
                    total=row.get('PR_SUM'+ending)
                    title='九項PR加總（含TO、不含MIN）；全體排名，同分並列1,2,2,4' if present else '九項PR不完整，無排名（不含MIN）'
                    if present:title+=f'; PR合計 {float(total):.6f}'
                    style='' if visible else 'display:none'
                    return f"<td class='{css_class} rank-{suffix.lower() or 'season'}-{mode}' style='{style}' data-order='{int(rank) if present else 1000000000}' title='{escape(title,quote=True)}'>{int(rank) if present else '—'}</td>"
                # TOT mode swaps in the derived *_TOT columns for counting stats only;
                # MIN / FG% / FT% show the same value in both modes (old-page behavior).
                use_tot = (mode == 'tot' and metric in tot_metrics)
                base_key = f"{metric}_TOT" if use_tot else metric
                key = f"{base_key}_{suffix}" if suffix else base_key
                val = row.get(key)
                if val is None or pd.isna(val):
                    style = '' if visible else 'display:none'
                    return f"<td class='{css_class}' style='{style}' data-order='-1'>—</td>"

                # Determine sort value (raw number)
                # Each AVG/TOT cell is its own DataTables column carrying its own raw
                # value here, so sorting stays exact in both display modes.
                sort_val = val
                if metric in ['FG%', 'FT%']:
                    raw_key = {'FG%':'FG_PCT', 'FT%':'FT_PCT'}[metric]
                    raw_key = f'{raw_key}_{suffix}' if suffix else raw_key
                    sort_val = float(row[raw_key]) * 100

                # Determine display value
                display_val = val
                if isinstance(val, float):
                    display_val = f"{val:.1f}"

                # --- PR (Percentile Rank) sub-label ---
                # Looked up from the *_PR / *_TOT_PR [_L7/_L14/_LS] column computed in
                # process_week_grid (raw-value based, before formatting). AVG and TOT
                # have independent PRs: the totals ranking reflects volume/durability.
                # Skipped when the player has no data for this stat/period (NaN) so no
                # "PR nan" ever renders.
                pr_base = f"{metric}_TOT_PR" if use_tot else f"{metric}_PR"
                pr_key = f"{pr_base}_{suffix}" if suffix else pr_base
                pr_val = row.get(pr_key)
                pr_html = ""
                if pr_val is not None and not pd.isna(pr_val):
                    pr_html = f"<br><span style='font-size:0.75em; color:#999;'>PR {int(round(pr_val))}</span>"

                style = "" if visible else "display:none"
                return f"<td class='{css_class}' style='{style}' data-order='{sort_val}'>{display_val}{pr_html}</td>"

            # Season Stats (AVG then TOT)
            for m in stat_metrics:
                player_html += create_stat_cell(row, m, "", "stat-season stat-avg", 'avg', True)
            for m in stat_metrics:
                player_html += create_stat_cell(row, m, "", "stat-season stat-tot", 'tot', False)

            # L7 Stats (AVG then TOT)
            for m in stat_metrics:
                player_html += create_stat_cell(row, m, "L7", "stat-l7 stat-avg", 'avg', False)
            for m in stat_metrics:
                player_html += create_stat_cell(row, m, "L7", "stat-l7 stat-tot", 'tot', False)

            # L14 Stats (AVG then TOT)
            for m in stat_metrics:
                player_html += create_stat_cell(row, m, "L14", "stat-l14 stat-avg", 'avg', False)
            for m in stat_metrics:
                player_html += create_stat_cell(row, m, "L14", "stat-l14 stat-tot", 'tot', False)

            # Last Season Stats (AVG then TOT)
            for m in stat_metrics:
                player_html += create_stat_cell(row, m, "LS", "stat-ls stat-avg", 'avg', False)
            for m in stat_metrics:
                player_html += create_stat_cell(row, m, "LS", "stat-ls stat-tot", 'tot', False)

            player_html += "</tr>"

        player_html += "</tbody></table></div>"

        return team_html + "<hr>" + player_html

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

    season_payload=season_schedule_payload(season_schedule,all_weeks,def_ratings)
    events_payload=schedule_event_payload(season_schedule,def_ratings)
    season_json=json.dumps(season_payload,ensure_ascii=False).replace('<','\\u003c')
    season_content=''
    if all_weeks:
        first=all_weeks[0]
        t,p,d=process_week_grid(first['start'],first['end'],season_schedule,stats_dict,def_ratings)
        season_content=generate_html(t,p,d,'WSeason')
    season_options=''.join(f'<option value="{i}">{escape(w["label"])}</option>' for i,w in enumerate(all_weeks))
    season_select=(f'<label class="season-picker" for="season-week">美東日曆週<select id="season-week" onchange="selectSeasonWeek(this.value)" {"disabled" if not all_weeks else ""}><option value="">{"選擇整季日曆週" if all_weeks else "當季尚無已公布賽程"}</option>{season_options}</select></label>')
    tab_buttons = ''.join(
        f"<button class='tablinks' onclick=\"openWeek(event, '{w['id']}')\" "
        f"id='{ 'defaultOpen' if i == 0 else '' }'>{w['label']}</button>"
        for i, w in enumerate(weeks_data)
    )
    week_panels = ''.join(
        f"<div id='{w['id']}' class='tabcontent'>{w['content']}</div>"
        for w in weeks_data
    )
    week_panels += f'<div id="WeekSeason" class="tabcontent"><h3 id="season-week-heading"></h3><p id="season-week-empty" hidden>本週沒有已公布的例行賽賽程。</p>{season_content}</div>'
    week_panels += '<div id="WeekCustom" class="tabcontent"><h3 id="custom-period-heading"></h3><div id="custom-period-content"></div></div>'
    table_initializers = ''.join(
        f"tables['W{i+1}'] = $('#playerTableW{i+1}').DataTable({{order:[[2,'desc']],pageLength:25,scrollX:true,language:{{search:'搜尋',lengthMenu:'每頁 _MENU_ 人',info:'_START_–_END_ / _TOTAL_ 人',infoFiltered:'（全體 _MAX_ 人）',zeroRecords:'沒有符合球員，按全體球員清除篩選',infoEmpty:'0 人'}}}});"
        f"if ($('#teamTableW{i+1}').length) $('#teamTableW{i+1}').DataTable({{paging:false,info:false,searching:false}});"
        for i in range(4)
    )
    metadata = stats_dict['metadata']
    generated_at = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    provenance = dict(utils.PROVENANCE)
    provenance['season_weeks']=[dict(number=w['number'],start=str(w['start']),end=str(w['end']),
        events=season_payload[i]['events']) for i,w in enumerate(all_weeks)]
    provenance.update(generated_at=generated_at, stats_source='ESPN', defense_source='PBP Stats',
                      period_populations={k:len(stats_dict[k]) for k in ['Season','L7','L14','LastSeason']})
    provenance['schedule_events']=[{k:v for k,v in e.items() if not k.endswith('_html')} for e in events_payload]
    provenance['fantasy_periods']=dict(kind='site_eastern_calendar',official_platform_mapping=False,
        timezone='America/New_York',quick_periods=quick_periods)
    last_period = provenance.get('players_' + str(int(metadata['last_season'][:4])+1), {})
    last_end = last_period.get('source_period_end','未查得')[:10]
    data_notice = (
        "選週只切換賽程，統計與PR維持報告更新時的資料。 "
        "整季採美東日期週一至週日，首場當季例行賽所在週為 Week 1；跨年連續，換季重設。近1週從今天起至週日。僅列來源已公布日期，尚未排定賽事不虛構；無比賽週仍保留。 "
        f"報告產生時間：{generated_at}。ESPN 球員資料：當季 {metadata['season']}，上季 {metadata['last_season']} "
        f"例行賽來源期間至 {last_end}。近期窗口為美東日期 {today} 前完整7／14天。"
        f"球隊／球員名單取自本次 ESPN roster；比賽日期使用美東時間，四週範圍 {w1_start}–{final_end}。"
        f"各期 PR 母體：當季 {len(stats_dict['Season'])}、近7天 {len(stats_dict['L7'])}、近14天 {len(stats_dict['L14'])}、上季 {len(stats_dict['LastSeason'])} 位有出賽球員。"
    )
    if stats_dict['Season'].empty:
        data_notice += " 當季例行賽尚無球員統計，預設顯示 Last Season；缺值不填造。"
    data_notice += ' ESPN/NBA/PBP資料再散布授權仍未確認。'
    defense_meta = provenance.get('defense', {})
    defense_notice = (
        "PBP Stats 各隊最近10場已完成例行賽，可跨季接續上季；排除季前與季後賽。"
        "以對手總得分 ÷ 逐場 DefPoss 合計 ×100 計算，越低防守越強，再對有資料球隊排名。"
        f"有效球隊 {defense_meta.get('eligible_teams',len(def_ratings))}/30，最新比賽 {defense_meta.get('last_game') or '暫無資料'}。"
        "不足10場標示 n/10；來源缺漏會停止更新並保留有效報告。這是球隊防守，並非位置別 DvP。"
    )
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
    catalog_json=json.dumps(comparison_catalog,ensure_ascii=False,allow_nan=False).replace('<','\\u003c')
    tools_meta_json=json.dumps(dict(season=metadata['season'],lastSeason=metadata['last_season'],
        defaultPeriod=default_period.lower()),ensure_ascii=False).replace('<','\\u003c')
    tools_js=Path('player_tools.js').read_text(encoding='utf-8')
    schedule_js=Path('schedule_tools.js').read_text(encoding='utf-8')
    events_json=json.dumps(events_payload,ensure_ascii=False,allow_nan=False).replace('<','\\u003c')
    periods_json=json.dumps(quick_periods,ensure_ascii=False).replace('<','\\u003c')

    html_template = f"""
    <!DOCTYPE html>
    <html lang="zh-Hant">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width,initial-scale=1">
        <meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src data:; connect-src 'none'; base-uri 'none'; form-action 'none'">
        <title>Fantasy NBA Streaming Assistant V2</title>
        <link rel="stylesheet" type="text/css" href="assets/datatables-2.3.7.min.css" integrity="{css_sri}">
        <style>{dashboard_css}</style>
        <script type="text/javascript" charset="utf8" src="assets/jquery-3.7.1.min.js" integrity="{jquery_sri}"></script>
        <script type="text/javascript" charset="utf8" src="assets/datatables-2.3.7.min.js" integrity="{datatables_sri}"></script>
        <script>
            var tables = {{}};
            var activeWeek = "W1";
            var teamSelection = {{}};
            var seasonWeeks = {season_json};
            var playerCatalog = {catalog_json};
            var playerToolsMeta = {tools_meta_json};
            var scheduleEvents = {events_json};
            var quickPeriods = {periods_json};
            var scheduleGeneratedAt = '{generated_at}';
            var customPlayerTemplate;

            $(document).ready( function () {{
                // Initialize DataTables for all weeks
                customPlayerTemplate=document.querySelector('#Week1 .player-section').cloneNode(true);
                {table_initializers}

                Object.keys(tables).forEach(function(suffix) {{ tables[suffix].column(1).visible(false); switchStats('{default_period}',suffix); }});
                Object.keys(tables).forEach(function(suffix) {{ tables[suffix].on('draw',function() {{ updateSelection(suffix); }}); }});
                // Open default tab
                document.getElementById("defaultOpen").click();
            }});

            function openWeek(evt, weekName) {{
                var i, tabcontent, tablinks;
                tabcontent = document.getElementsByClassName("tabcontent");
                for (i = 0; i < tabcontent.length; i++) {{
                    tabcontent[i].style.display = "none";
                }}
                tablinks = document.getElementsByClassName("tablinks");
                for (i = 0; i < tablinks.length; i++) {{
                    tablinks[i].className = tablinks[i].className.replace(" active", "");
                }}
                document.getElementById(weekName).style.display = "block";
                document.getElementById('season-week').classList.remove('active');
                document.getElementById('apply-custom-period').classList.remove('active');
                evt.currentTarget.className += " active";
                activeWeek = weekName.replace('Week','W');
                if (activeWeek !== 'WSeason') document.getElementById('season-week').value = '';
                if (tables[activeWeek]) tables[activeWeek].columns.adjust();
                updateSelection(activeWeek);
                document.dispatchEvent(new Event('active-week-changed'));
            }}

            function selectSeasonWeek(value) {{
                if (value === '') return;
                var week = seasonWeeks[Number(value)];
                if (!week) return;
                openWeek({{currentTarget:document.getElementById('season-week')}}, 'WeekSeason');
                document.getElementById('season-week-heading').textContent=week.label;
                document.getElementById('season-week-empty').hidden=week.events !== 0;
                if (!tables.WSeason) {{
                    tables.WSeason=$('#playerTableWSeason').DataTable({{order:[[2,'desc']],pageLength:25,scrollX:true}});
                    tables.WSeason.column(1).visible(false);
                    tables.WSeason.on('draw',function() {{ updateSelection('WSeason'); }});
                    switchStats('{default_period}','WSeason');
                }}
                var table=tables.WSeason;
                for (var day=0;day<7;day++) $(table.column(day+3).header()).text(week.headers[day]);
                table.rows().every(function() {{
                    var row=this.data();
                    var team=week.teams[row[1]] || {{games:0,days:['','','','','','','']}};
                    row[2]=String(team.games);
                    for (var day=0;day<7;day++) row[day+3]=team.days[day];
                    this.data(row);
                }});
                var teamTable=document.getElementById('teamTableWSeason');
                if (teamTable) {{
                    for (var day=0;day<7;day++) teamTable.tHead.rows[0].cells[day+2].textContent=week.headers[day];
                    teamTable.tBodies[0].replaceChildren();
                    Object.keys(week.teams).sort().forEach(function(abbr) {{
                        var data=week.teams[abbr],tr=document.createElement('tr');
                        tr.className='team-row';tr.dataset.team=abbr;
                        tr.onclick=function() {{ filterTeam(tr,abbr,'WSeason'); }};
                        [abbr,String(data.games)].forEach(function(text) {{ var td=tr.insertCell();td.textContent=text; }});
                        data.days.forEach(function(html) {{ tr.insertCell().innerHTML=html; }});
                        if (teamSelection.WSeason===abbr) tr.classList.add('selected');
                        teamTable.tBodies[0].appendChild(tr);
                    }});
                }}
                table.columns.adjust().draw(false);
                updateSelection('WSeason');
                document.dispatchEvent(new Event('active-week-changed'));
            }}

            // --- Feature: Switch Stats (period x display mode) ---
            // The visible stat columns are the intersection of the active period
            // (Season/L7/L14/LS) and the active display mode (AVG/TOT); both toggles
            // funnel through applyStatView so they stay orthogonal.
            var viewState = {{}};
            function applyStatView(suffix) {{
                var state = viewState[suffix] || {{period:'season',mode:'avg'}};
                var table = tables[suffix];
                table.columns().every(function () {{
                    var header = this.header();
                    if (header.className.indexOf('stat-') !== -1) {{
                        $(header).css('display', '');
                        this.nodes().to$().css('display', '');
                        this.visible(header.classList.contains('stat-' + state.period) &&
                                     header.classList.contains('stat-' + state.mode), false);
                    }}
                }});
                table.columns.adjust().draw(false);
            }}

            function switchStats(period, suffix) {{
                viewState[suffix] = viewState[suffix] || {{period:'season',mode:'avg'}};
                viewState[suffix].period = period.toLowerCase();
                // Update Buttons
                // NOTE: matched via the button's data-period attribute (exact match), not
                // innerText substring matching -- the old innerText-substring check broke
                // once a "Last Season" button was added, since its label also contains the
                // literal word "Season" and would falsely light up alongside "Season Avg".
                // Scoped to [data-period] so the AVG/TOT buttons are left alone.
                var container = document.querySelector('#Week' + suffix.replace('W','') + ' .controls');
                var btns = container.querySelectorAll('.btn-stat[data-period]');
                for (var i = 0; i < btns.length; i++) {{
                    btns[i].classList.remove('active');
                    if (btns[i].getAttribute('data-period') === period) {{
                        btns[i].classList.add('active');
                    }}
                }}
                applyStatView(suffix);
            }}

            // --- Feature: Switch Display Mode (AVG / TOT) ---
            function switchDisplayMode(mode, suffix) {{
                viewState[suffix] = viewState[suffix] || {{period:'season',mode:'avg'}};
                viewState[suffix].mode = mode.toLowerCase();
                // Scoped to [data-mode] so the period buttons are left alone.
                var container = document.querySelector('#Week' + suffix.replace('W','') + ' .controls');
                var btns = container.querySelectorAll('.btn-stat[data-mode]');
                for (var i = 0; i < btns.length; i++) {{
                    btns[i].classList.remove('active');
                    if (btns[i].getAttribute('data-mode') === mode) {{
                        btns[i].classList.add('active');
                    }}
                }}
                applyStatView(suffix);
            }}

            function updateSelection(suffix) {{
                var table = tables[suffix];
                if (!table) return;
                var team = teamSelection[suffix];
                var count = table.rows({{search:'applied'}}).count();
                var text = (team ? team + ' 球員' : '全體球員') + ' · ' + count + ' 人';
                $('#selection'+suffix).text(text);
                if (suffix === activeWeek) {{
                    $('#active-selection').text(text);
                    $('#show-all-players').attr('aria-pressed', !team && !table.search() ? 'true' : 'false');
                }}
            }}
            function filterTeam(row, teamAbbr, suffix) {{
                $('#teamTable' + suffix + ' .team-row').removeClass('selected');
                $(row).addClass('selected');
                teamSelection[suffix] = teamAbbr;
                tables[suffix].column(1).search('^' + $.fn.dataTable.util.escapeRegex(teamAbbr) + '$', true, false).draw();
                updateSelection(suffix);
            }}
            function resetTeamFilter(suffix) {{
                var table = tables[suffix];
                if (!table) return;
                $('#teamTable' + suffix + ' .team-row').removeClass('selected');
                delete teamSelection[suffix];
                table.search('').columns().search('').draw();
                $(table.table().container()).find('input[type="search"]').val('');
                updateSelection(suffix);
            }}
            function resetActiveTeamFilter() {{ resetTeamFilter(activeWeek); }}
            {tools_js}
            {schedule_js}
        </script>
    </head>
    <body>
        <div class="container">
            <header class="appbar"><div class="brand"><span class="brand-mark">FC</span><div>FANTASYORGCAT<small>NBA · WEEKLY PLANNER</small></div></div><div class="app-status">ESPN + PBP Stats<br>更新 {escape(generated_at)}</div></header>
            <section class="hero"><div><div class="eyebrow">WEEKLY COMPARISON</div><h1>把下一場，排進你的陣容。</h1><p>四週賽程、球員表現與對手防守，一起看清楚。</p></div><div class="hero-meta"><strong>{escape(metadata['season'])} NBA</strong>{escape(str(w1_start))} — {escape(str(final_end))}</div></section>
            <div class="metric-grid">
                <div class="metric-card"><span>現役球員</span><strong>{roster_count}</strong><small>人</small></div>
                <div class="metric-card"><span>四週賽程</span><strong>{provenance.get('schedule',{}).get('events_in_window',0)}</strong><small>場</small></div>
                <div class="metric-card"><span>防守資料 · 截至 {escape(str(defense_meta.get('last_game') or '暫缺'))}</span><strong>{defense_count}<small>/ 30 隊</small></strong></div>
                <div class="metric-card"><span>上季 PR 母體</span><strong>{len(stats_dict['LastSeason'])}</strong><small>人</small></div>
            </div>
            <details class="data-details"><summary>資料說明 · {escape(fixture_caption)} · 防守近10場跨季接續</summary><p class="data-notice">{escape(data_notice)}</p><p class="defense-notice">{escape(defense_notice)}</p></details>
            <div class="workspace-bar"><nav class="tab" aria-label="選擇週次">{tab_buttons}</nav>{season_select}<div class="filter-tools"><span id="active-selection" class="selection-label">全體球員</span><button id="show-all-players" class="global-reset" onclick="resetActiveTeamFilter()" aria-pressed="true" title="清除球隊與搜尋，保留統計期間及AVG/TOT">全體球員</button></div></div>
            <section class="period-tools" aria-label="自訂計分期間"><p>日期以美東歸屬；日曆週未對應 Yahoo／ESPN 官方計分週。可依聯盟設定輸入 1–31 天期間。</p><div class="period-inputs"><label>起日（美東）<input id="period-start" type="date" value="{w1_start}"></label><label>迄日（含，美東）<input id="period-end" type="date" value="{w1_end}"></label><button id="apply-custom-period" class="btn-stat" type="button">套用自訂期間</button></div><p id="period-error" role="alert" hidden></p><p id="schedule-freshness" role="status"></p><details><summary>剩餘排程、背靠背與低比賽日</summary><p>依目前快照與瀏覽時間計算球隊排程；未套用傷病、陣容、位置或 GP 上限，不代表可用上場場次。低比賽日指美東當日全聯盟 1–5 場。</p><p id="schedule-period-context"></p><div id="schedule-insights" class="schedule-scroll"></div><div id="schedule-pending"></div></details></section>
            <div class="legend"><b>近10場對手防守</b><span><i class="dot" style="background:#ccffcc"></i>較好打</span><span><i class="dot" style="background:#ffffcc"></i>中段</span><span><i class="dot" style="background:#ffcccc"></i>較難打</span><span><i class="dot" style="background:#eee"></i>暫缺</span></div>
            <section id="comparison-panel" class="player-section" hidden><div class="player-heading"><h3>球員比較</h3><button id="clear-comparison" type="button" class="btn-stat">清空比較</button></div><div class="controls"><label>統計期間 <select id="comparison-period"><option value="season">本季</option><option value="l7">近7天</option><option value="l14">近14天</option><option value="ls">上季</option></select></label><label>顯示 <select id="comparison-mode"><option value="avg">AVG</option><option value="tot">TOT</option></select></label></div><p id="comparison-meta"></p><div class="comparison-scroll"><table id="comparison-table"><thead id="comparison-head"></thead><tbody id="comparison-body"></tbody></table></div></section>
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
    generate_html_report()
