import pandas as pd
from datetime import datetime, timedelta
import utils
import webbrowser
import os
import sys
import json

def generate_html_report():
    print("Initializing Fantasy NBA Report Generator V2...")
    
    # 1. Define Date Ranges
    today = datetime.now().date()
    days_until_sunday = (6 - today.weekday()) % 7
    w1_end = today + timedelta(days=days_until_sunday)
    w1_start = today
    
    # Calculate end date for 4 weeks
    final_end = w1_end + timedelta(days=21) # 3 more weeks
    
    print(f"Report Range: {w1_start} to {final_end}")

    # 2. Fetch Data
    print("Fetching Schedule...")
    full_schedule = utils.get_schedule(w1_start, final_end)
    
    # Fallback for Date Mismatch
    if full_schedule.empty:
        print("⚠️ No games found. Trying previous year (Time Travel Mode)...")
        w1_start_fallback = w1_start.replace(year=w1_start.year - 1)
        final_end_fallback = final_end.replace(year=final_end.year - 1)
        full_schedule = utils.get_schedule(w1_start_fallback, final_end_fallback)
        
        if not full_schedule.empty:
            print(f"✅ Found games in {w1_start_fallback.year}! Adjusting display dates...")
            full_schedule['GAME_DATE'] = full_schedule['GAME_DATE'].apply(lambda d: d.replace(year=d.year + 1))

    print("Fetching Player Stats (Multi-Period)...")
    stats_dict = utils.get_player_stats_multi_period()
    
    print("Fetching Defensive Ratings...")
    def_ratings = utils.get_team_defensive_ratings()

    # Counting stats that get a separate TOT (= AVG x GP for the period) view.
    # MIN / FG% / FT% are intentionally excluded: the old FANTASY-SUP page shows
    # them unchanged in TOT mode (rates and minutes-per-game don't sum meaningfully).
    # Shared by process_week_grid (data) and generate_html (rendering) below.
    tot_metrics = ['PTS', 'REB', 'AST', '3PM', 'STL', 'BLK']

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
        # Defensive guard (pre-existing gap, unrelated to PR/Last-Season): schedule_df can
        # come back completely empty (no columns at all) when there are no games in the
        # requested window and the "Time Travel" fallback above also found nothing -- e.g.
        # every NBA off-season, since the fallback shifts by exactly one year and lands on
        # the same off-season month again. That used to raise KeyError('GAME_DATE') here.
        if schedule_df.empty or 'GAME_DATE' not in schedule_df.columns:
            week_games = pd.DataFrame(columns=['TEAM_ID', 'TEAM_ABBREVIATION', 'GAME_DATE', 'MATCHUP'])
        else:
            mask = (schedule_df['GAME_DATE'] >= start_date) & (schedule_df['GAME_DATE'] <= end_date)
            week_games = schedule_df.loc[mask].copy()
        
        # Helper to get badge
        def get_badge_html(opp_abbr, is_home):
            def_info = def_ratings.get(opp_abbr, {'Rank': 15})
            rank = def_info['Rank']
            color = utils.get_color_for_rank(rank)
            prefix = 'vs' if is_home else '@'
            return f"<div style='background-color:{color}; padding: 4px; border-radius: 4px; text-align:center; font-weight:bold;' title='Def Rank: {rank}'>{prefix} {opp_abbr}</div>"

        # --- TEAM SCHEDULE GRID ---
        team_grid_data = []
        all_team_ids = week_games['TEAM_ID'].unique()
        
        for tid in all_team_ids:
            t_games = week_games[week_games['TEAM_ID'] == tid]
            if t_games.empty: continue
            
            abbr = t_games.iloc[0]['TEAM_ABBREVIATION']
            row = {'TEAM_ID': tid, 'Team': abbr, 'Games': len(t_games)}
            
            for d, col_name in zip(days, day_cols):
                g = t_games[t_games['GAME_DATE'] == d]
                if not g.empty:
                    matchup = g.iloc[0]['MATCHUP']
                    opp = matchup.split(' ')[2]
                    is_home = 'vs.' in matchup
                    row[col_name] = get_badge_html(opp, is_home)
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
            'FG%': 'FG_PCT', 'FT%': 'FT_PCT',
        }

        # Base: Season Stats
        base_df = stats_dict['Season'].copy()
        base_df = base_df[base_df['GP'] > 0] # Active only

        # Merge L7, L14 and Last Season
        # Rename columns for L7/L14/LS
        l7 = stats_dict['L7'].copy().add_suffix('_L7')
        l14 = stats_dict['L14'].copy().add_suffix('_L14')

        # --- Last Season pool & its PR (computed BEFORE any roster filtering) ---
        # The LS PR population must be "every player who logged last-season stats
        # (GP > 0)", independent of who has already played THIS season. Computing it
        # here on the full LastSeason fetch keeps the denominator honest early in a
        # new season, when many players haven't appeared in the Season fetch yet.
        ls_pool = stats_dict.get('LastSeason', pd.DataFrame()).copy()
        if not ls_pool.empty:
            ls_pool = ls_pool[ls_pool['GP'] > 0]
            for label, raw_name in pr_metric_map.items():
                if raw_name in ls_pool.columns:
                    ls_pool[f'{label}_PR'] = ls_pool[raw_name].rank(pct=True) * 100
                    # TOT view: derived as AVG x GP (Plan A, zero extra API calls),
                    # with its own PR -- a totals ranking rewards volume/durability,
                    # which is different information than the per-game ranking.
                    if label in tot_metrics:
                        ls_pool[f'{label}_TOT'] = ls_pool[raw_name] * ls_pool['GP']
                        ls_pool[f'{label}_TOT_PR'] = ls_pool[f'{label}_TOT'].rank(pct=True) * 100
        last_season = ls_pool.add_suffix('_LS') # PTS_PR -> PTS_PR_LS etc.

        # Roster union: this season's actives + last season's actives who are still
        # on a roster today (static active list, see utils.get_active_player_ids).
        # Without this, players who haven't played yet this season would vanish from
        # the table entirely -- exactly the players the Last Season view is for.
        # Their Season/L7/L14 columns stay NaN and render with the existing
        # missing-data handling; only identity columns are carried over.
        if not ls_pool.empty:
            active_ids = utils.get_active_player_ids()
            extra_mask = (~ls_pool['PLAYER_ID'].isin(base_df['PLAYER_ID'])) & ls_pool['PLAYER_ID'].isin(active_ids)
            extra_base = ls_pool.loc[extra_mask, ['PLAYER_ID', 'PLAYER_NAME', 'TEAM_ID', 'TEAM_ABBREVIATION']].copy()
            if not extra_base.empty:
                base_df = pd.concat([base_df, extra_base], ignore_index=True)

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

        # --- Percentile Rank (PR) Calculation (Season/L7/L14) ---
        # Must run on RAW numeric values, before the string formatting below turns
        # them into "12.3%" etc. Population = all players with data for that period
        # (rows the roster-union added with NaN stats are excluded from ranking by
        # pandas automatically, so they don't distort denominators and get no PR).
        # LastSeason PR is NOT computed here -- it was already computed on the full
        # ls_pool above, so its population is all of last season's actives.
        # All 9 metrics are "higher is better" for fantasy (no inverted-direction stat
        # like turnovers exists in this stat set), so PR = rank(pct=True) * 100 directly.
        for period_suffix in ['', '_L7', '_L14']:
            gp_col = f"GP{period_suffix}"
            for label, raw_name in pr_metric_map.items():
                raw_col = f"{raw_name}{period_suffix}"
                pr_col = f"{label}_PR{period_suffix}"
                if raw_col in merged.columns:
                    # NaN values (no data for that period) are excluded from ranking
                    # by pandas and stay NaN, so they naturally don't get a PR.
                    merged[pr_col] = merged[raw_col].rank(pct=True) * 100
                    # TOT view: derived as AVG x GP (Plan A, zero extra API calls),
                    # with its own PR -- a totals ranking rewards volume/durability,
                    # which is different information than the per-game ranking.
                    if label in tot_metrics and gp_col in merged.columns:
                        tot_col = f"{label}_TOT{period_suffix}"
                        merged[tot_col] = merged[raw_col] * merged[gp_col]
                        merged[f"{label}_TOT_PR{period_suffix}"] = merged[tot_col].rank(pct=True) * 100
                else:
                    merged[pr_col] = pd.NA

        # Format Player
        merged['Player'] = merged.apply(lambda x: f"<b>{x['PLAYER_NAME']}</b> <br><span style='color:#888'>{x['TEAM_ABBREVIATION']}</span>", axis=1)
        
        # Format Stats (Season)
        merged['FG%'] = (merged['FG_PCT'] * 100).map('{:.1f}%'.format)
        merged['FT%'] = (merged['FT_PCT'] * 100).map('{:.1f}%'.format)
        merged = merged.rename(columns={'FG3M': '3PM'})
        
        # Format Stats (L7)
        if 'FG_PCT_L7' in merged.columns:
            merged['FG%_L7'] = (merged['FG_PCT_L7'] * 100).map('{:.1f}%'.format)
            merged['FT%_L7'] = (merged['FT_PCT_L7'] * 100).map('{:.1f}%'.format)
            merged = merged.rename(columns={'FG3M_L7': '3PM_L7', 'PTS_L7': 'PTS_L7', 'REB_L7': 'REB_L7', 'AST_L7': 'AST_L7', 'STL_L7': 'STL_L7', 'BLK_L7': 'BLK_L7'})
            
        # Format Stats (L14)
        if 'FG_PCT_L14' in merged.columns:
            merged['FG%_L14'] = (merged['FG_PCT_L14'] * 100).map('{:.1f}%'.format)
            merged['FT%_L14'] = (merged['FT_PCT_L14'] * 100).map('{:.1f}%'.format)
            merged = merged.rename(columns={'FG3M_L14': '3PM_L14', 'PTS_L14': 'PTS_L14', 'REB_L14': 'REB_L14', 'AST_L14': 'AST_L14', 'STL_L14': 'STL_L14', 'BLK_L14': 'BLK_L14'})

        # Format Stats (Last Season)
        if 'FG_PCT_LS' in merged.columns:
            merged['FG%_LS'] = (merged['FG_PCT_LS'] * 100).map('{:.1f}%'.format)
            merged['FT%_LS'] = (merged['FT_PCT_LS'] * 100).map('{:.1f}%'.format)
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
                <h3>Team Schedule (Click to Filter Players)</h3>
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
            team_html += "</tbody></table></div>"

        # --- Player Table HTML ---
        # Columns: Player, Games, [Days], [Stats Season], [Stats L7], [Stats L14], [Stats Last Season]
        
        # Stat Columns Definition
        stat_metrics = ['MIN', 'PTS', 'REB', 'AST', '3PM', 'STL', 'BLK', 'FG%', 'FT%']
        
        player_html = f"""
        <div class="player-section">
            <div class="controls">
                <button class="btn-stat active" data-period="Season" onclick="switchStats('Season', '{table_id_suffix}')">Season Avg</button>
                <button class="btn-stat" data-period="L7" onclick="switchStats('L7', '{table_id_suffix}')">Last 7 Days</button>
                <button class="btn-stat" data-period="L14" onclick="switchStats('L14', '{table_id_suffix}')">Last 14 Days</button>
                <button class="btn-stat" data-period="LS" onclick="switchStats('LS', '{table_id_suffix}')">Last Season</button>
                <span style="margin-left:20px">Show:</span>
                <button class="btn-stat active" data-mode="AVG" onclick="switchDisplayMode('AVG', '{table_id_suffix}')">AVG</button>
                <button class="btn-stat" data-mode="TOT" onclick="switchDisplayMode('TOT', '{table_id_suffix}')">TOT</button>
                <button class="btn-reset" onclick="resetTeamFilter('{table_id_suffix}')">Show All Teams</button>
            </div>
            <table id="playerTable{table_id_suffix}" class="display" style="width:100%">
                <thead>
                    <tr>
                        <th>Player</th>
                        <th>Team</th> <!-- Hidden column for filtering -->
                        <th>Games</th>
                        {''.join([f'<th>{d}</th>' for d in day_cols])}
                        <!-- Season Stats Headers (AVG / TOT) -->
                        {''.join([f'<th class="stat-season stat-avg">{m}</th>' for m in stat_metrics])}
                        {''.join([f'<th class="stat-season stat-tot" style="display:none">{m}</th>' for m in stat_metrics])}
                        <!-- L7 Stats Headers (AVG / TOT) -->
                        {''.join([f'<th class="stat-l7 stat-avg" style="display:none">{m}</th>' for m in stat_metrics])}
                        {''.join([f'<th class="stat-l7 stat-tot" style="display:none">{m}</th>' for m in stat_metrics])}
                        <!-- L14 Stats Headers (AVG / TOT) -->
                        {''.join([f'<th class="stat-l14 stat-avg" style="display:none">{m}</th>' for m in stat_metrics])}
                        {''.join([f'<th class="stat-l14 stat-tot" style="display:none">{m}</th>' for m in stat_metrics])}
                        <!-- Last Season Stats Headers (AVG / TOT) -->
                        {''.join([f'<th class="stat-ls stat-avg" style="display:none">{m}</th>' for m in stat_metrics])}
                        {''.join([f'<th class="stat-ls stat-tot" style="display:none">{m}</th>' for m in stat_metrics])}
                    </tr>
                </thead>
                <tbody>
        """
        
        for _, row in player_df.iterrows():
            player_html += f"<tr>"
            player_html += f"<td>{row['Player']}</td>"
            player_html += f"<td>{row['TEAM_ABBREVIATION']}</td>" # Hidden Team
            player_html += f"<td>{row.get('Games', 0)}</td>"
            for d in day_cols:
                player_html += f"<td>{row.get(d, '')}</td>"
            
            # Helper to create stat cell with data-order
            def create_stat_cell(row, metric, suffix, css_class, mode='avg', visible=True):
                # TOT mode swaps in the derived *_TOT columns for counting stats only;
                # MIN / FG% / FT% show the same value in both modes (old-page behavior).
                use_tot = (mode == 'tot' and metric in tot_metrics)
                base_key = f"{metric}_TOT" if use_tot else metric
                key = f"{base_key}_{suffix}" if suffix else base_key
                val = row.get(key, 0)

                # Determine sort value (raw number)
                # Each AVG/TOT cell is its own DataTables column carrying its own raw
                # value here, so sorting stays exact in both display modes.
                sort_val = val
                if isinstance(val, str) and '%' in val: # Handle pre-formatted % strings if any (though we formatted them in process_week_grid)
                     try: sort_val = float(val.strip('%'))
                     except: sort_val = 0

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
    current_start = w1_start
    current_end = w1_end
    
    for i in range(4):
        print(f"Processing Week {i+1} ({current_start} - {current_end})...")
        t, p, d = process_week_grid(current_start, current_end, full_schedule, stats_dict, def_ratings)
        content = generate_html(t, p, d, f'W{i+1}')
        weeks_data.append({
            'id': f'Week{i+1}',
            'label': f'Week {i+1} ({current_start.strftime("%m/%d")} - {current_end.strftime("%m/%d")})',
            'content': content
        })
        
        # Next week
        current_start = current_end + timedelta(days=1)
        current_end = current_start + timedelta(days=6)

    html_template = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Fantasy NBA Streaming Assistant V2</title>
        <link rel="stylesheet" type="text/css" href="https://cdn.datatables.net/1.11.5/css/jquery.dataTables.css">
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f7f6; color: #333; padding: 20px; }}
            h1 {{ color: #2c3e50; }}
            .container {{ max-width: 1600px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
            
            /* Tabs */
            .tab {{ overflow: hidden; border: 1px solid #ccc; background-color: #f1f1f1; border-radius: 8px 8px 0 0; }}
            .tab button {{ background-color: inherit; float: left; border: none; outline: none; cursor: pointer; padding: 14px 16px; transition: 0.3s; font-size: 17px; font-weight: bold; }}
            .tab button:hover {{ background-color: #ddd; }}
            .tab button.active {{ background-color: #3498db; color: white; }}
            .tabcontent {{ display: none; padding: 20px; border: 1px solid #ccc; border-top: none; border-radius: 0 0 8px 8px; }}
            
            /* Tables */
            table {{ width: 100%; border-collapse: collapse; font-size: 0.95em; }}
            th {{ background-color: #3498db; color: white; padding: 10px; text-align: left; }}
            td {{ padding: 8px; border-bottom: 1px solid #eee; vertical-align: middle; }}
            
            /* Team Selection */
            .team-row {{ cursor: pointer; transition: background 0.2s; }}
            .team-row:hover {{ background-color: #eef9ff !important; }}
            .team-row.selected {{ background-color: #d6eaf8 !important; border-left: 4px solid #3498db; }}
            
            /* Controls */
            .controls {{ margin-bottom: 15px; }}
            .btn-stat {{ padding: 8px 15px; border: 1px solid #ddd; background: white; cursor: pointer; border-radius: 4px; margin-right: 5px; }}
            .btn-stat.active {{ background-color: #2ecc71; color: white; border-color: #27ae60; }}
            .btn-reset {{ padding: 8px 15px; border: 1px solid #e74c3c; background: white; color: #e74c3c; cursor: pointer; border-radius: 4px; float: right; }}
            .btn-reset:hover {{ background: #e74c3c; color: white; }}

            /* Legend */
            .legend {{ margin-bottom: 15px; padding: 10px; background: #eee; border-radius: 4px; font-size: 0.9em; }}
            .dot {{ height: 10px; width: 10px; border-radius: 50%; display: inline-block; margin-right: 5px; }}
        </style>
        <script type="text/javascript" charset="utf8" src="https://code.jquery.com/jquery-3.5.1.js"></script>
        <script type="text/javascript" charset="utf8" src="https://cdn.datatables.net/1.11.5/js/jquery.dataTables.js"></script>
        <script>
            var tables = {{}};
            
            $(document).ready( function () {{
                // Initialize DataTables for all weeks
                {''.join([f'''
                tables['W{i+1}'] = $('#playerTableW{i+1}').DataTable({{ "order": [[ 2, "desc" ]], "pageLength": 25 }});
                $('#teamTableW{i+1}').DataTable({{ "paging": false, "info": false, "searching": false }});
                ''' for i in range(4)])}

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
                evt.currentTarget.className += " active";
            }}
            
            // --- Feature: Switch Stats (period x display mode) ---
            // The visible stat columns are the intersection of the active period
            // (Season/L7/L14/LS) and the active display mode (AVG/TOT); both toggles
            // funnel through applyStatView so they stay orthogonal.
            var currentPeriod = 'season';
            var currentMode = 'avg';

            function applyStatView() {{
                var periods = ['season', 'l7', 'l14', 'ls'];
                var modes = ['avg', 'tot'];
                periods.forEach(p => {{
                    modes.forEach(m => {{
                        var display = (p == currentPeriod && m == currentMode) ? 'table-cell' : 'none';
                        $('.stat-' + p + '.stat-' + m).css('display', display);
                    }});
                }});
            }}

            function switchStats(period, suffix) {{
                currentPeriod = period.toLowerCase();
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
                applyStatView();
            }}

            // --- Feature: Switch Display Mode (AVG / TOT) ---
            function switchDisplayMode(mode, suffix) {{
                currentMode = mode.toLowerCase();
                // Scoped to [data-mode] so the period buttons are left alone.
                var container = document.querySelector('#Week' + suffix.replace('W','') + ' .controls');
                var btns = container.querySelectorAll('.btn-stat[data-mode]');
                for (var i = 0; i < btns.length; i++) {{
                    btns[i].classList.remove('active');
                    if (btns[i].getAttribute('data-mode') === mode) {{
                        btns[i].classList.add('active');
                    }}
                }}
                applyStatView();
            }}
            
            // --- Feature: Filter Team ---
            function filterTeam(row, teamAbbr, suffix) {{
                // Highlight Row
                $('#teamTable' + suffix + ' .team-row').removeClass('selected');
                $(row).addClass('selected');
                
                // Filter Player Table
                // Column 1 is Team (index 1)
                tables[suffix].column(1).search(teamAbbr).draw();
            }}
            
            function resetTeamFilter(suffix) {{
                $('#teamTable' + suffix + ' .team-row').removeClass('selected');
                tables[suffix].column(1).search('').draw();
            }}
        </script>
    </head>
    <body>
        <div class="container">
            <h1>🏀 Fantasy NBA Streaming Assistant V2</h1>
            
            <div class="legend">
                <b>Matchup Strength (DvP):</b> 
                <span class="dot" style="background-color:#ccffcc"></span>Easy (Green) 
                <span class="dot" style="background-color:#e5ffcc"></span> 
                <span class="dot" style="background-color:#ffffcc"></span>Average 
                <span class="dot" style="background-color:#ffe5cc"></span> 
                <span class="dot" style="background-color:#ffcccc"></span>Hard (Red)
            </div>

            <div class="tab">
                {''.join([f'<button class="tablinks" onclick="openWeek(event, \'{w["id"]}\')" id="{ "defaultOpen" if i==0 else "" }">{w["label"]}</button>' for i, w in enumerate(weeks_data)])}
            </div>

            {''.join([f'<div id="{w["id"]}" class="tabcontent">{w["content"]}</div>' for w in weeks_data])}
        </div>
    </body>
    </html>
    """
    
    output_file = "fantasy_nba_report_v2.html"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html_template)
        
    print(f"Report generated: {output_file}")
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
