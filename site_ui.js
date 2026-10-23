/* Shared language and time-zone preferences. No network or roster storage access. */
(function(root){
'use strict';
const EN={
 "把下一場排入你的賽程": "Put the next game on your schedule",
 "時區": "Time zone",
 "時間": "Time",
 "台北": "Taipei",
 "美東": "New York",
 "美西": "Los Angeles",
 "東京": "Tokyo",
 "倫敦": "London",
 "週次依美東計分日": "Scoring weeks use New York dates",
 "球員與賽程": "Players & schedule",
 "九項配隊": "Roster lab",
 "NBA FANTASY 工具箱": "NBA FANTASY TOOLKIT",
 "球員與賽程 | FANTASYORGCAT": "Players & schedule | FANTASYORGCAT",
 "九項配隊分析 · FantasyOrgCat": "Nine-category roster lab · FantasyOrgCat",
 "選擇週次、篩選球隊，再勾選球員一起比較。": "Choose a week, filter teams, and select players to compare.",
 "資料快照與來源 · 本季例行賽尚無球員統計，預設顯示上季": "Snapshot & sources · No regular-season stats yet; showing the previous season",
 "資料快照與來源": "Snapshot & sources",
 "週次": "Week",
 "全體球員": "All players",
 "球員名單 ↓": "Players ↓",
 "選擇週次": "Choose a week",
 "球員名單": "Players",
 "球員比較": "Player comparison",
 "清空比較": "Clear comparison",
 "用勾選配隊 ↗": "Build a roster ↗",
 "統計期間": "Stat period",
 "本季": "This season",
 "近7天": "Last 7 days",
 "近14天": "Last 14 days",
 "上季": "Last season",
 "平均 AVG": "Average AVG",
 "總量 TOT": "Totals TOT",
 "顯示": "Display",
 "數值": "Values",
 "現役球員": "Active players",
 "上季 PR 母體": "Previous-season PR population",
 "四週賽程": "Four-week schedule",
 "球隊賽程": "Team schedule",
 "球隊": "Team",
 "場次": "Games",
 "比較": "Compare",
 "自訂期間／近期快捷": "Custom period / quick ranges",
 "剩餘排程、背靠背與低比賽日": "Remaining games, back-to-backs & light days",
 "起日（美東）": "Start (New York date)",
 "迄日（含，美東）": "End, inclusive (New York date)",
 "套用自訂期間": "Apply custom period",
 "美東日期，含迄日；可依自己的聯盟設定輸入 1–31 天。": "Use New York dates, inclusive; enter 1–31 days to match your league.",
 "依目前快照與瀏覽時間計算球隊排程；未套用傷病、陣容、位置或 GP 上限，不代表可用上場場次。低比賽日指美東當日全聯盟 1–5 場。": "Schedule counts use this snapshot and the current time. Injuries, roster slots, positions and games limits are not applied. A light day has 1–5 NBA games on that New York date.",
 "近10場對手防守": "Opponent defense · last 10 games",
 "對手防守資料暫缺": "Opponent defense unavailable",
 "不影響球員與賽程更新": "Player and schedule updates continue",
 "對手防守資料暫缺：目前固定來源未提供原防守指標所需的回合資料，暫不顯示防守排名；球員統計與賽程正常更新。": "Opponent defense is unavailable: the fixed source does not provide the possession data required for the original metric. Player statistics and schedules continue to update.",
 "較好打": "Easier",
 "稍好打": "Slightly easier",
 "中段": "Average",
 "稍難打": "Slightly harder",
 "較難打": "Harder",
 "暫缺": "Unavailable",
 "點選球隊篩選球員": "Select a team to filter players",
 "預設數據優先；可開啟逐日賽程。勾選「比較」後從上方查看，也可自訂排名項目。": "Stats are shown first. Enable daily fixtures, select players to compare, or choose ranking categories.",
 "FANTASYORGCAT · 每日資料快照 · 球隊防守非位置別 DvP": "FANTASYORGCAT · Daily snapshot · Team defense, not positional DvP",
 "顯示設定": "Display settings",
 "勾選要補強的數據": "Choose categories to strengthen",
 "恢復 9CAT": "Reset to 9CAT",
 "籃板 + FG%": "REB + FG%",
 "9CAT：保留原始全體排名，顯示九項 PR 合計；MIN 不計入。": "9CAT keeps the original full-population rank and sums nine PRs. MIN is excluded.",
 "自訂 Rank：以網站名單中資料完整的球員排名；加總所選 PR，同分並列。搜尋或篩選球隊不改變排名。": "Custom Rank sums selected PRs among website players with complete data. Ties share a rank; search and team filters do not change it.",
 "請至少勾選一項；未選項目時不計算排名。": "Select at least one category to calculate ranks.",
 "使用未四捨五入的 PR 加總；TO 越少 PR 越高，缺值不當成 0。這不是聯盟 ROTO 積分。": "PR sums use full precision. Lower TO earns a higher PR. Missing values are not zero. These are not league ROTO points.",
 "顯示設定儲存在此瀏覽器；可隨時恢復預設。": "Display settings are saved in this browser. Reset them at any time.",
 "瀏覽器無法儲存設定；本次調整仍可使用。": "Settings could not be saved; changes still work for this visit.",
 "數據字級": "Stat font size",
 "列間距": "Row spacing",
 "賽程欄寬": "Fixture column width",
 "恢復預設外觀": "Reset appearance",
 "同時顯示逐日賽程": "Show daily fixtures",
 "欄名與球員固定；左右滑動查看全部欄位。": "Headers and players stay fixed. Scroll horizontally for all columns.",
 "跳至 Rank →": "Jump to Rank →",
 "← 球員": "← Players",
 "尚未選擇": "Nothing selected",
 "搜尋球員": "Search players",
 "姓名或球隊": "Name or team",
 "第一頁": "First",
 "上一頁": "Previous",
 "下一頁": "Next",
 "最後頁": "Last",
 "沒有符合球員，按全體球員清除篩選": "No matching players. Choose All players to clear filters.",
 "0 人": "0 players",
 "跳到球員選取": "Skip to player selection",
 "九項配隊分析": "Nine-category roster lab",
 "所選季別例行賽實績 · 比較陣容體質與換人產效": "Selected-season regular-season stats · Compare rosters and roster moves",
 "選球員": "Pick players",
 "陣容管理": "Manage rosters",
 "看比較": "Compare",
 "儲存庫": "Saved rosters",
 "先選球員，看看你的九項強弱": "Pick players to see your nine-category strengths",
 "在完整數據表勾選原陣容，再新增對手或模擬換人。已保存的陣容可由上方選單載入。": "Select your roster in the full stat table, then add opponents or simulate roster moves. Load saved rosters from the selector above.",
 "開始選球員": "Start picking players",
 "切換原陣容": "Switch base roster",
 "選擇已儲存的聯盟／陣容": "Choose a saved league / roster",
 "統計資料": "Stat dataset",
 "資料口徑": "Units",
 "所選季別整季總量合計": "Selected-season roster totals",
 "每人 1 場合計": "One game per player",
 "雷達顯示": "Radar layers",
 "原陣容": "Base roster",
 "對手": "Opponent",
 "換人後": "After changes",
 "編輯陣容": "Edit roster",
 "怎麼使用 H2H／ROTO 配隊分析？": "How to use the H2H / ROTO roster lab",
 "先用每場產效看陣容強弱，再看換人會補強哪項、犧牲哪項。雷達固定使用每場資料，下方表格可另看整季總量。": "Start with per-game strengths, then compare what a roster move gains and gives up. The radar always uses per-game stats; the table can also show season totals.",
 "H2H 類別制：看體質，再看當週先發場次": "H2H categories: strengths, then weekly starting games",
 "平均產效適合找想贏的類別與換人方向。判斷當週勝負，還要依每位球員可排進每日先發的場次累計；FG／FT 必須先累計命中與出手再計算。本頁尚未計算當週先發、賽程與傷停影響。": "Per-game output helps choose categories and roster moves. Weekly results also depend on games in your daily starting lineup. FG/FT must use combined makes and attempts. This page does not model weekly lineups, schedules or injuries.",
 "ROTO 補強目標：追得到的名次、守得住的分數": "ROTO targets: attainable places and points to defend",
 "先找「距上一名很近」或「領先下一名很少」的類別，再用換人平均產效評估補強與代價；若聯盟有場次上限，也要看剩餘可計入的先發場數。": "Find categories close to the team above or below you, then assess gains and trade-offs using per-game output. If your league limits games, consider remaining eligible starting games.",
 "需要同一時間點的全聯盟各隊累計、FGM／FGA／FTM／FTA，以及剩餘先發場次假設，才能估算分數。本頁尚未提供聯盟名次與 ROTO 積分估算。": "Estimating points needs every league team's totals at the same time, FGM/FGA/FTM/FTA and assumptions about remaining starting games. League standings and ROTO points are not estimated here.",
 "每場九項體質": "Per-game nine-category profile",
 "固定每場 · 同季基準": "Per-game scale · Same-season reference",
 "越外圈越佳；計數看成員每場平均，FG／FT 依出手加權。": "Farther out is better. Counting stats use player per-game averages; FG/FT are weighted by attempts.",
 "勾選要比較的對手": "Choose opponents to compare",
 "滑鼠靠近節點、手機點一下，或用鍵盤聚焦類別名稱，可查看各陣容的實際數據。": "Hover near a point, tap it, or focus a category with the keyboard to see each roster's actual values.",
 "TO：0 失誤在最外圈，失誤越多越靠內。": "TO: zero turnovers is the outer edge. More turnovers move inward.",
 "讀圖方式與固定基準": "Reading the radar and its fixed reference",
 "缺資料時僅顯示已知成員，標為「已知部分」，不當成完整隊伍。這是固定所選季別實績參考尺度，並非球員百分位、真正聯盟 ROTO 積分或預測。人數不等、分鐘與出賽樣本不同時，請一併看表格及覆蓋率。": "Missing data shows known players only and is marked partial. This fixed selected-season reference is not a player percentile, league ROTO score or forecast. Check the table and coverage when roster sizes, minutes or game samples differ.",
 "其他八軸為 50 + 15 × 標準差距，截在 0–100。TO 以 0 失誤對應最外圈 100，同季來源每場平均對應 50，失誤越多持續往內；尺度為 100 ÷（1 + 陣容成員每場平均 TO ÷ 同季來源每場平均 TO）。計數類別先將每位球員總量除以個人 GP，再取陣容成員平均，對照同季完整來源的每場基準。FG／FT 將每位球員命中與出手各除以個人 GP，再合計命中 ÷ 合計出手，不平均球員百分比。基準不隨表格單位、你選的隊伍或換人而改動。": "The other eight axes use 50 + 15 × z-score, clipped to 0–100. TO uses 100 / (1 + roster mean per-game TO / source-season mean per-game TO): zero is 100, the source mean is 50, and more TO moves inward. Counting stats divide each player's totals by individual GP before averaging across the roster. FG/FT combine each player's makes and attempts per GP, then divide combined makes by attempts. Player percentages are never averaged. The reference stays fixed across table units, selected rosters and roster moves.",
 "九項數據與換人差異": "Nine-category stats and roster-move impact",
 "查看數據": "View stats",
 "表格也看平均產效": "Show per-game output in the table",
 "整季總量是這份名單在所選季別的實績合計，不是你的聯盟已計入成績。平均產效則是每位球員各打 1 場的合計，並非球隊每場或當週預測。": "Season totals sum the selected players' season stats, not your league's credited results. Per-game output sums one game per player; it is not a team-game average or weekly forecast.",
 "類別": "Category",
 "換人差異": "Change",
 "缺資料時顯示已知小計與覆蓋率，不把未知球員當成0；不完整類別不畫完整面積，也不計換人差值。命中率差異以百分點呈現，失誤減少為佳。多隊時可左右滑動表格，或取消勾選暫不比較的對手。": "Missing data shows known subtotals and coverage, not zero. Incomplete categories do not get a full radar area or a change estimate. Shooting changes use percentage points; lower TO is better. Scroll horizontally or hide opponents when comparing several teams.",
 "編輯原陣容會重設模擬；多人換人請使用「換人模擬」，原名單不會被改動。": "Editing the base roster resets the simulation. Use Roster moves to test multiple changes while keeping your base roster.",
 "切換已儲存陣容": "Switch saved roster",
 "聯盟／陣容名稱": "League / roster name",
 "例如 H2H A盟、ROTO B盟": "e.g. H2H League A, ROTO League B",
 "儲存原陣容／更新同名": "Save base roster / update name",
 "新增原陣容": "New base roster",
 "不同聯盟可分別命名保存，使用本區選單載入。名單修改後請再儲存；切換會重設換人模擬。只保存在此瀏覽器，亦可到「儲存庫」管理。": "Save a named roster for each league and load it here. Save again after editing; switching resets simulated changes. Rosters stay in this browser and can also be managed in Saved rosters.",
 "勾選／編輯球員": "Select / edit players",
 "清空原陣容": "Clear base roster",
 "對手比較": "Opponents",
 "自由新增、命名與編輯多隊；對手名單自動保存在此裝置，隊數不設固定上限。": "Add, name and edit multiple teams. Opponents save automatically on this device, with no fixed team-count limit.",
 "編輯隊伍": "Edit team",
 "隊伍名稱": "Team name",
 "新增對手": "Add opponent",
 "刪除此隊": "Delete team",
 "選取對手球員": "Pick opponent players",
 "清空對手": "Clear opponent",
 "換人模擬": "Roster moves",
 "勾選多人移出，再從搜尋加入替代球員。模擬不修改原陣容。": "Select players to drop, then search for replacements. The simulation keeps your base roster intact.",
 "編輯換人後名單": "Edit changed roster",
 "從原陣容移出": "Drop from base roster",
 "加入的替代球員": "Replacement players",
 "重設模擬": "Reset moves",
 "球員數據與名單選取": "Player stats and selection",
 "查看比較": "View comparison",
 "搜尋球員／NBA 球隊": "Search players / NBA teams",
 "例如 Jokic 或 DEN": "e.g. Jokic or DEN",
 "正在編輯": "Editing",
 "換人後名單": "Changed roster",
 "只看已選": "Selected only",
 "清除搜尋": "Clear search",
 "此裝置的命名陣容": "Named rosters on this device",
 "儲存在此瀏覽器、此網域；隊數不設固定上限，實際容量依瀏覽器而定，不會上傳或跨裝置同步。只保存球員 ID，統計使用目前快照。": "Saved in this browser on this domain. Team count has no fixed limit; capacity depends on your browser. Nothing is uploaded or synced across devices. Only player IDs are saved; stats use the current snapshot.",
 "保存": "Save",
 "名稱": "Name",
 "我的陣容": "My roster",
 "保存／更新同名": "Save / update name",
 "已保存": "Saved",
 "選擇陣容": "Choose roster",
 "載入至": "Load into",
 "目前對手": "Current opponent",
 "新增為對手隊伍": "Add as new opponent",
 "載入": "Load",
 "刪除此保存": "Delete saved roster",
 "資料來源、覆蓋率與缺值說明": "Sources, coverage and missing data",
 "資料缺漏以「—」或已知小計呈現，不補成 0；歷史表現不等於本季預測。雷達尺度與計算方式可在圖表下方展開。": "Missing data uses a dash or known subtotal, never zero. Historical results are not current-season forecasts. Expand the explanation below the radar for its scale and calculations.",
 "FANTASYORGCAT · 所選季別實績參考 · 無私人聯盟連線、登入或付費來源": "FANTASYORGCAT · Selected-season reference · No private-league connection, login or paid feed",
 "本季資料沿用ESPN既有更新管線；封存資料：": "Current-season data uses the existing ESPN update pipeline. Archived data:",
 "），依發布者稱取自NBA Stats之二手整理。計算衍生每場口徑與雷達；Jabari FGA標未知，未選定衝突值。": "), described by its publisher as a secondary compilation of NBA Stats. Per-game values and radar scales are derived. Jabari's conflicting FGA is marked unknown.",
 "未開賽": "Scheduled",
 "已完賽": "Final",
 "進行中": "Live",
 "延賽": "Postponed",
 "取消": "Cancelled",
 "暫停": "Suspended",
 "延遲": "Delayed",
 "狀態待確認": "Status pending",
 "時間待定": "Time TBD",
 "時間設定未儲存；本次選擇仍可使用。": "Preferences could not be saved; this visit still uses your selection.",
 "期間排程": "Scheduled games",
 "尚未開賽": "Games remaining",
 "剩餘 B2B 組": "Remaining B2Bs",
 "剩餘低比賽日": "Remaining light-day games",
 "待確認": "Pending",
 "日期待定": "Date TBD",
 "自訂期間": "Custom period",
 "自訂計分期間": "Custom scoring period",
 "網站近期期間": "Quick range",
 "近期快捷": "Quick range",
 "這個期間沒有已公布日期的球隊賽程。": "No dated team fixtures in this period.",
 "本期間沒有已公布日期的例行賽賽程。": "No dated regular-season fixtures in this period.",
 "請輸入有效起訖日期，迄日不得早於起日，期間需為 1–31 天。": "Enter a valid 1–31 day range with the end on or after the start.",
 "尚未加入球員": "No players selected",
 "先建立原陣容再選擇移出球員": "Build a base roster before selecting players to drop",
 "尚未建立對手，從「對手比較」新增隊伍。": "No opponents yet. Add a team in Opponents.",
 "尚無對手": "No opponent",
 "移除": "Remove",
 "復原": "Undo",
 "已復原上一個操作。": "Last action restored.",
 "改善": "Improved",
 "降低表現": "Reduced output",
 "此季別來源無資料／未匹配，統計為未知": "No matched data for this season; stats are unknown",
 "未選球員": "No players selected",
 "缺命中／出手分母": "Missing makes / attempts",
 "缺上季實績": "Missing previous-season stats",
 "有球員缺此季別實績": "Some players lack selected-season stats",
 "有球員缺上季實績": "Some players lack previous-season stats",
 "每場產效": "Per-game output",
 "失誤越少越佳": "Lower turnovers are better",
 "已知部分": "Known portion",
 "此季別基準樣本不足，請先查看數值": "Insufficient reference sample for this season; use the numeric table",
 "加入有所選季別實績的球員後顯示": "Add players with selected-season stats to display",
 "固定所選季別每場產效雷達；未知類別留白": "Selected-season per-game radar; missing categories are left blank",
 "原陣容、自訂對手隊伍與換人後，以每場產效比較，TO低為佳。滑鼠靠近節點、手機點選，或聚焦類別名稱，可查看各陣容實際數值；表格單位不改雷達口徑。": "Compare the base roster, named opponents and changed roster per game. Lower TO is better. Hover, tap or focus a category for actual values. Table units do not change the radar scale.",
 "計數節點依成員每場平均定位；命中率依出手量加權。": "Counting points use roster-member per-game averages. Shooting percentages are weighted by attempts.",
 "陣容每場九項標準化雷達": "Normalized per-game nine-category roster radar",
 "未知類別留白，不用零填補；實際數據見下方比較表。": "Missing categories stay blank, not zero. Actual values are in the comparison table.",
 "網站導覽": "Site navigation",
 "配隊工作區": "Roster workspace",
 "開始配隊": "Start building a roster",
 "比較設定": "Comparison settings",
 "雷達顯示，對手選擇也同步表格": "Radar layers; opponent choices also update the table",
 "左右捲動完整球員數據": "Scroll horizontally through player stats",
 "人": "players",
 "場": "games",
 "球員": "Player",
 "搜尋": "Search",
 "每頁": "Show",
 "選取": "Select",
 "MIN／場": "MIN/game",
 "/ 30 隊": "/ 30 teams",
 "尚未選球員": "No players selected",
 "所選季別整季總量：逐員實績總量合計，含個人不同出賽數；不是聯盟每日先發已計入成績。": "Selected-season totals sum each player's actual season stats, with different GP. They are not your league's credited daily starting-lineup results.",
 "每人 1 場：逐員總量 ÷ 個人 GP 後合計；投籃同口徑加權，不平均百分比。": "One game per player: divide each player's totals by individual GP, then combine. Shooting is weighted by attempts; player percentages are not averaged.",
 "這份原陣容尚未儲存；不同聯盟請使用不同名稱。": "This base roster is not saved yet. Use a different name for each league.",
 " · 賽事狀態以快照為準，非即時比分。": " · Game statuses come from the snapshot, not a live score feed.",
 "每人 1 場：逐員所選季別總量 ÷ 個人 GP 後合計；投籃同口徑加權，不平均百分比。": "One game per player: divide each player's selected-season totals by individual GP, then combine. Shooting is weighted by attempts; player percentages are not averaged.",
 "所選季別資料尚未完整，保留已知小計與覆蓋率；缺投籃分母或固定完整母體時，相關雷達留白，不當成0。": "The selected-season dataset is incomplete. Known subtotals and coverage remain available. Missing shooting denominators or a complete reference leave the affected radar values blank, not zero.",
 "某些類別參考母體沒有可用尺度，該雷達軸留白，實際數值仍可查看。": "Some categories lack a usable reference scale. Those radar axes stay blank; actual values remain available.",
 "正在使用本季實績：平均產效反映目前樣本，請搭配 GP 與每場分鐘看。": "Using current-season results. Per-game output reflects the current sample; check GP and minutes per game.",
 "本季尚無例行賽實績，可切到上季參考。新資料更新後會預設使用本季。": "No current-season regular-season stats yet. Use last season as a reference. Valid new data will become the default.",
 "出手來源差異": "Conflicting attempt totals",
 "有球員缺所選季別實績": "Some players lack selected-season stats",
 "此口徑無出手": "No attempts in these units",
 "空陣容未保存。": "An empty roster was not saved.",
 "請先替陣容命名。": "Name the roster first.",
 "隊伍名稱不可留白。": "Team name cannot be empty.",
 "先選擇已保存的陣容。": "Choose a saved roster first.",
 "已建立空白原陣容；已儲存的聯盟／陣容仍保留。": "Created an empty base roster. Saved leagues and rosters are retained.",
 "已清空原陣容。": "Base roster cleared.",
 "模擬已重設，原陣容不變。": "Roster moves reset. The base roster is unchanged.",
 "沒有符合球員；可清除搜尋或關閉「只看已選」": "No matching players. Clear the search or turn off Selected only.",
 "保存格式無法辨識，原內容未修改": "Unrecognized save format; the original data was not modified",
 "保存資料不完整，原內容未修改": "Incomplete saved data; the original data was not modified",
 "對手隊伍 ID 無法辨識，原內容未修改": "Unrecognized opponent ID; the original data was not modified",
 "球員 ID 格式錯誤": "Invalid player ID format",
 "未知單位": "Unknown units",
 "最近10場例行賽防守資料暫缺": "Defense data for the last 10 regular-season games is unavailable",
 "封存": "Archive",
 "失誤越少PR越高": "Lower turnovers earn a higher PR",
 "九項 PR 加總的全體排名；數字越小越前面": "Full-population rank by nine-category PR sum; lower ranks are better",
 "所選 PR 加總的網站名單排名；數字越小越前面": "Website-player rank by selected PR sum; lower ranks are better",
 "所選項目 PR 不完整，無排名": "Selected PRs are incomplete; unranked",
 "依目前勾選的排名項目計算；9CAT 使用原始全體排名，自訂項目使用網站名單排名": "Uses the selected categories. 9CAT keeps the original full-population rank; custom categories rank website players.",
 "目前週次場次": "Games in the selected week",
 "此球隊賽程資料暫缺": "Schedule unavailable for this team",
 "當日無賽程": "No game on this date",
 "賽程資料暫缺": "Schedule unavailable",
 "球員表賽程欄寬": "Player-table fixture width",
 "本次畫面已復原，但對手保存失敗；重新整理會遺失這次恢復。": "The view was restored, but saving opponents failed. Reloading will lose this restoration."
};
const zones=[['Asia/Taipei','台北','Taipei'],['America/New_York','美東','New York'],['America/Los_Angeles','美西','Los Angeles'],['Asia/Tokyo','東京','Tokyo'],['Europe/London','倫敦','London'],['UTC','UTC','UTC']];
const key='fantasyorgcat:site-preferences:v1',dateCache=new Map(),timeCache=new Map();
function validPreferences(value){return {language:value?.language==='en'?'en':'zh-Hant',timezone:zones.some(z=>z[0]===value?.timezone)?value.timezone:'Asia/Taipei'};}
function dateAt(instant,zone){const cacheKey=String(instant)+'|'+zone;if(dateCache.has(cacheKey))return dateCache.get(cacheKey);const parts=new Intl.DateTimeFormat('en-CA',{timeZone:zone,year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(new Date(instant));const v=k=>parts.find(p=>p.type===k).value;const result=v('year')+'-'+v('month')+'-'+v('day');dateCache.set(cacheKey,result);return result;}
function etMidnight(date){const target=Date.parse(date+'T00:00:00Z');let guess=target;for(let i=0;i<3;i++){const parts=new Intl.DateTimeFormat('en-CA',{timeZone:'America/New_York',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',second:'2-digit',hourCycle:'h23'}).formatToParts(new Date(guess)),v=k=>Number(parts.find(p=>p.type===k).value),offset=Date.UTC(v('year'),v('month')-1,v('day'),v('hour'),v('minute'),v('second'))-guess,next=target-offset;if(next===guess)break;guess=next;}return guess;}
function daysInZone(start,end,zone){const a=dateAt(etMidnight(start),zone),b=dateAt(etMidnight(new Date(Date.parse(end+'T12:00Z')+86400000).toISOString().slice(0,10))-1,zone),out=[];for(let n=Date.parse(a+'T12:00Z');n<=Date.parse(b+'T12:00Z');n+=86400000)out.push(new Date(n).toISOString().slice(0,10));return out;}
function formatTime(instant,zone,year=false){const cacheKey=String(instant)+'|'+zone+'|'+year;if(timeCache.has(cacheKey))return timeCache.get(cacheKey);if(!instant||!Number.isFinite(Date.parse(instant)))return '時間待定';const d=new Date(instant),date=dateAt(d,zone),clock=new Intl.DateTimeFormat('en-GB',{timeZone:zone,hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).format(d);const result=(year?date:date.slice(5).replace('-','/'))+' '+clock;timeCache.set(cacheKey,result);return result;}
if(typeof module!=='undefined'&&module.exports){module.exports={validPreferences,dateAt,etMidnight,daysInZone,formatTime};return;}
let prefs=validPreferences(null),storageAvailable=true;
try{prefs=validPreferences(JSON.parse(localStorage.getItem(key)));}catch{storageAvailable=false;}
const originalTitle=document.title;
const textSources=new WeakMap(),attributeSources=new WeakMap(),translationCache=new Map();
let observer=null,flushing=false;
function periodLabel(value){return EN[value]||value.replaceAll('14天','14 days').replaceAll('預設季後賽','Default playoffs').replaceAll('自訂期間','Custom period').replace(/^近(\d)週/,'Quick $1');}
function translate(source){
 if(translationCache.has(source))return translationCache.get(source);
 let value=source;
 if(prefs.language==='en'){
  value=EN[source]||source;
  if(value===source&&source.startsWith('PBP Stats 各隊最近10場')){
   const coverage=source.match(/有效球隊 ([\d/]+)/)?.[1]||'—',latest=source.match(/最新比賽 ([\d-]+)/)?.[1]||'—';
   value='PBP Stats: each team’s last 10 completed regular-season games, continuing across seasons. Preseason and playoffs are excluded. Defense is opponent points / combined game DefPoss × 100; lower is stronger. Coverage '+coverage+', latest game '+latest+'. Samples under 10 games are marked n/10. Missing source data stops the update and preserves the last valid report. This is team defense, not positional DvP.';
  }
  if(value===source&&source.startsWith('選週只切換賽程')){
   const capture=r=>source.match(r)?.[1]||'—',stamp=capture(/報告產生時間：(.+?)。/),season=capture(/當季 ([\d-]+)/),archive=capture(/上季 ([\d-]+)/),through=capture(/來源期間至 ([\d-]+)/),window=capture(/近期窗口為美東日期 ([\d-]+)/),range=capture(/四週範圍 ([\d–-]+)/),counts=source.match(/各期 PR 母體：當季 (\d+)、近7天 (\d+)、近14天 (\d+)、上季 (\d+)/);
   value='Week selection changes schedules only; stats and PRs use the report snapshot. NBA weeks run Monday–Sunday in New York, starting with the first regular-season game’s week. Yahoo uses the verified public default calendar; ESPN uses its verified season Weekly calendar and is disabled for unverified seasons. Custom matchup and playoff dates are supported. Quick week 1 runs from today through Sunday. Only published dates are shown; unannounced games are not invented, and empty weeks remain available. Generated: '+stamp+'. ESPN seasons: '+season+' and previous season '+archive+', source regular-season range through '+through+'. Recent windows cover the complete 7/14 days before '+window+' in New York. Rosters use this ESPN snapshot. Scoring weeks use New York dates; displayed game dates and times use your selected time zone. Quick range: '+range+'. PR populations (season / 7 days / 14 days / prior season): '+(counts?counts.slice(1).join(' / '):'—')+'. '+(source.includes('當季例行賽尚無')?'No current regular-season player stats yet; the previous season is shown by default. ':'')+'Missing values are not fabricated. Redistribution permissions for '+(source.includes('ESPN/NBA/PBP')?'ESPN/NBA/PBP':'ESPN/NBA')+' data remain unconfirmed.';
  }
  if(value===source){
   const rules=[
    [/^球隊賽程 · (.+)$/,(_,label)=>'Team schedule · '+periodLabel(label)],
    [/^(.+) · 14天$/,(_,label)=>label+' · 14 days'],
    [/^(.+) · 預設季後賽$/,(_,label)=>label+' · Default playoffs'],
    [/^Yahoo 公開預設週次；自訂聯盟日期可能不同。週表核對：(.+)。$/,(_,d)=>'Yahoo public default weeks; custom leagues may differ. Calendar checked: '+d+'.'],
    [/^資料快照：(.*) · 賽事狀態以快照為準，非即時比分。$/,(_,d)=>'Snapshot: '+d+' · Snapshot game statuses; not a live score feed.'],
    [/^資料快照：(.*) · 已超過 48 小時；狀態與改期可能已變更。$/,(_,d)=>'Snapshot: '+d+' · Over 48 hours old; statuses and dates may have changed.'],
    [/^美東 (.+)（含迄日） · (.+) · 剩餘場次截止 (.+)$/,(_,d,label,now)=>'New York scoring dates '+d+' (inclusive) · '+periodLabel(label)+' · Remaining games as of '+now],
    [/^([\d-]+) 例行賽實績 · 比較陣容體質與換人產效$/,(_,season)=>season+' regular-season stats · Compare roster strengths and roster moves'],
    [/^正在使用 ([\d-]+) 歷史實績，供配隊參考；並非本季預測。有效本季資料更新後會預設使用本季。$/,(_,season)=>'Using '+season+' historical results as a roster reference, not a forecast. Current-season data becomes the default once valid data is available.'],
    [/^([\d-]+) 本季（尚無例行賽實績）$/,(_,season)=>season+' current season (no regular-season stats yet)'],
    [/^原陣容 (\d+) 人 · GP資料 (\d+\/\d+) · 所選季別球員出賽合計 (\d+)（不是聯盟已計入場數）$/,(_,n,c,gp)=>'Base roster '+n+' players · GP coverage '+c+' · Combined player GP '+gp+' (not credited league games)'],
    [/^對手 (\d+) · (\d+) 人$/,(_,n,p)=>'Opponent '+n+' · '+p+' players'],
    [/^對手：對手 (\d+)$/,(_,n)=>'Opponent: Opponent '+n],
    [/^(\d+) 移出／(\d+) 加入$/,(_,a,b)=>a+' dropped / '+b+' added'],
    [/^正在編輯 (原陣容|對手|換人後名單) · 已選 (\d+) 人$/,(_,target,n)=>'Editing '+EN[target]+' · '+n+' selected'],
    [/^正在編輯 (.+) · 已選 (\d+) 人$/,(_,target,n)=>'Editing '+(EN[target]||target.replace(/^對手 (\d+)$/,'Opponent $1'))+' · '+n+' selected'],
    [/^基準 (\d+) 位有.*?參考球員；來源完整母體 (\d+) 位，已保存分母 (\d+) 位。基準版本：(.+?)。 來源 (.+?)；來源賽季範圍[（(](.+?)[）)]：(.+?) 至 (.+?)。$/,(_,n,p,s,v,source,zone,a,b)=>'Reference: '+n+' players with selected-season stats; full source population '+p+', saved denominators '+s+'. Version: '+v+'. Source: '+source+'; season range ('+zone+'): '+a+' to '+b+'.'],
    [/^BoxScore Lab／CC BY 4.0 · 2025–26二手例行賽實績，非官方全表驗證。名單 (\d+\/\d+) 唯一映射；其餘 (\d+) 位此來源無適用資料，保持未知。Jabari Smith Jr. FGA 存975／974來源差異，未裁定，選入時FG%未知。$/,(_,mapped,n)=>'BoxScore Lab / CC BY 4.0 · 2025–26 secondary regular-season data, without official full-table verification. Unique mappings: '+mapped+'; '+n+' other players have no applicable source data and remain unknown. Jabari Smith Jr. has an unresolved FGA conflict (975 / 974); selecting him leaves FG% unknown.'],

    [/^從(.+?)移除 (.+)$/,(_,target,name)=>'Remove '+name+' from '+(EN[target]||target)],
    [/^這位球員已在(.+)，沒有重複加入。$/,(_,target)=>'This player is already in '+(EN[target]||target)+'. No duplicate was added.'],
    [/^(.+) · (失誤越少越佳|每場產效)$/,(_,metric,meaning)=>metric+' · '+EN[meaning]],
    [/^已勾選 (.+) · (.+)$/,(_,player,target)=>'Selected '+player+' · '+(EN[target]||target)],
    [/^已解除 (.+) · (.+)$/,(_,player,target)=>'Unselected '+player+' · '+(EN[target]||target)],
    [/^目前「(.+)」已儲存；可使用本區的「切換已儲存陣容」。$/,(_,name)=>'“'+name+'” is saved. Load another roster from the saved-roster selector.'],
    [/^目前「(.+)」有未儲存的名單變更，請再按儲存。$/,(_,name)=>'“'+name+'” has unsaved player changes. Save it again.'],
    [/^已保存「(.+)」至此裝置。$/,(_,name)=>'Saved “'+name+'” on this device.'],
    [/^已載入原陣容「(.+)」；換人模擬已重設。$/,(_,name)=>'Loaded base roster “'+name+'”. Roster moves were reset.'],
    [/^已載入「(.+)」；使用目前快照，未知球員不補零。$/,(_,name)=>'Loaded “'+name+'” using the current snapshot. Unknown players are not zero-filled.'],
    [/^已刪除對手「(.+)」。$/,(_,name)=>'Deleted opponent “'+name+'”.'],
    [/^已清空對手「(.+)」。$/,(_,name)=>'Cleared opponent “'+name+'”.'],
    [/^對手自動保存失敗：(.+)。本次編輯仍可繼續，既有保存未清除。$/,(_,error)=>'Could not auto-save opponents: '+(EN[error]||error)+'. You can keep editing; existing saves were retained.'],
    [/^對手保存無法讀取：(.+)。既有內容不會覆寫，本次仍可編輯。$/,(_,error)=>'Could not read saved opponents: '+(EN[error]||error)+'. Existing data will not be overwritten; you can edit for this visit.'],
    [/^本地保存無法使用：(.+)。本次編輯仍可繼續；既有資料未清除。$/,(_,error)=>'Local saving is unavailable: '+(EN[error]||error)+'. You can keep editing; existing data was retained.'],
    [/^選取或解除 (.+)$/,(_,name)=>'Select or unselect '+name],
    [/^PR 合計 ([\d.]+)；(.+)$/,(_,sum,categories)=>'PR sum '+sum+'; '+categories],
    [/^PBP Stats 最近10場已完成例行賽 \(可跨季\): ([\d.]+)失分\/100防守回合; 排名 (\d+)\/(\d+); (\d+)\/10場; (.+)$/,(_,rating,rank,total,n,dates)=>'PBP Stats: last 10 completed regular-season games (may span seasons). '+rating+' points allowed / 100 defensive possessions; rank #'+rank+' of '+total+'; '+n+'/10 games; '+dates],
    [/^排名項目 · (.+)$/,(_,x)=>'Rank categories · '+x],
    [/^比較 (\d+) 人$/,(_,n)=>'Compare '+n+' players'],
    [/^(全體球員|[A-Z]{2,4} 球員) · (\d+) 人$/,(_,s,n)=>(s==='全體球員'?'All players':s.slice(0,-3)+' players')+' · '+n],
    [/^(\d+)–(\d+) \/ (\d+) 人\s*[（(]全體 (\d+) 人[）)]$/,(_,a,b,n,total)=>a+'–'+b+' / '+n+' players (from '+total+' players)'],
    [/^每頁 (.*) 人$/,(_,n)=>'Show '+n+' players'],
    [/^(\d+)–(\d+) \/ (\d+) 人$/,(_,a,b,n)=>a+'–'+b+' / '+n+' players'],
    [/^（全體 (\d+) 人）$/,(_,n)=>'(from '+n+' players)'],
    [/^對手 (\d+)$/,(_,n)=>'Opponent '+n],
    [/^(.+) · (\d+) 人（已知部分）$/,(_,name,n)=>(EN[name]||name)+' · '+n+' players (partial)'],
    [/^(.+) · (\d+) 人$/,(_,s,n)=>(EN[s]||s)+' · '+n+' players'],
    [/^(\d+) 人$/,(_,n)=>n+' players'],
    [/^已加入 (.+)$/,(_,s)=>'Added '+s],
    [/^已移除 (.+)$/,(_,s)=>'Removed '+s],
    [/^已自動保存 (\d+) 支對手隊伍。$/,(_,n)=>n+' opponent teams saved automatically.'],
    [/^(\d+) 隊 · 目前 (\d+) 人$/,(_,n,p)=>n+' teams · '+p+' players in current team'],
    [/^(\d+) 移出 \/ (\d+) 加入$/,(_,a,b)=>a+' dropped / '+b+' added'],
    [/^(\d+)\/(\d+) 覆蓋$/,(_,a,b)=>a+'/'+b+' coverage'],
    [/^已知小計 · (\d+)\/(\d+) 覆蓋$/,(_,a,b)=>'Known subtotal · '+a+'/'+b+' coverage'],
    [/^(\d+)\/(\d+) 人有資料( · 已知部分)?$/,(_,a,b,p)=>a+'/'+b+' players with data'+(p?' · partial':'')],
    [/^GP ([\d.]+) · 每場分鐘 ([\d.—]+)$/,(_,gp,m)=>'GP '+gp+' · MIN/game '+m],
    [/^查看 (\w+%?) 各陣容每場數值$/,(_,m)=>'View '+m+' per-game roster values'],
    [/^近(\d)週 \((.+)\)$/,(_,n,d)=>'Quick '+n+' ('+d+')'],
    [/^防守資料 · 截至 (.+)$/,(_,d)=>'Defense data · through '+d],
    [/^本季 (.+)$/,(_,s)=>'This season '+s],
    [/^上季 (.+)$/,(_,s)=>'Last season '+s],
    [/^(.+) 例行賽實績 · (\d+) 組陣容$/,(_,s,n)=>s+' regular season · '+n+' rosters'],
    [/^命中 ([\d.]+)／出手 ([\d.]+)（每人各 1 場合計）$/,(_,m,a)=>'Makes '+m+' / attempts '+a+' (one game per player)'],
    [/^每人各 1 場合計 ([\d.]+)$/,(_,n)=>'One game per player: '+n],
    [/^從比較移除 (.+)$/,(_,s)=>'Remove '+s+' from comparison']
   ];
   for(const [pattern,render] of rules)if(pattern.test(source)){value=source.replace(pattern,render);break;}
  }
  if(value===source&&/[\u4e00-\u9fff]/.test(value)){
   const phrases={'網站快照':'Site snapshot','已完賽統計至':'Completed games through','未知球員':'Unknown player','資料快照：':'Snapshot: ','更新 ':'Updated ','原陣容':'Base roster','對手：':'Opponent: ','換人後':'After changes','已知小計':'Known subtotal','覆蓋':'coverage','每場產效':'Per-game output','／人／場':' / player / game','每人各 1 場合計':'One game per player','所選季別':'Selected season','整季總量':'Season totals','GP資料':'GP coverage','球員出賽合計':'player games combined','不是聯盟已計入場數':'not credited league games','排名 ':'Rank ','例行賽實績':'regular-season stats','已知部分':'partial','（':' (', '）':')','未選球員':'No players selected','尚未選擇':'Nothing selected','14天':'14 days','預設季後賽':'Default playoffs','自訂期間':'Custom period','每人 1 場':'One game per player','查看 ':'View ','上季':'Last season','本季':'This season','近7天':'Last 7 days','近14天':'Last 14 days','隊伍':'teams','最新比賽':'latest game','時間待定':'Time TBD'};
   for(const [zh,en] of Object.entries(phrases))value=value.split(zh).join(en);
  }
 }
 // Snapshot timestamps remain source-based but display in the selected time zone.
 value=value.replace(/\d{4}-\d{2}-\d{2} \d{2}:\d{2} UTC/g,s=>formatTime(s.replace(' UTC',':00Z').replace(' ','T'),prefs.timezone,true)+' '+zoneLabel());
 translationCache.set(source,value);return value;
}
function zoneLabel(){const z=zones.find(z=>z[0]===prefs.timezone);return z[prefs.language==='en'?2:1];}
function zoneNote(){return zoneLabel()+(prefs.language==='en'?' time · Scoring weeks use New York dates':'時間 · 週次依美東計分日');}
function processText(node){
 if(!textSources.has(node)&&!/[\u4e00-\u9fff]| UTC/.test(node.nodeValue))return;
 if(node.parentElement?.closest('script,style,[data-site-preferences],time[datetime]'))return;
 const current=node.nodeValue,old=textSources.get(node),source=old&&current===old.rendered?old.source:current;
 if(!source.trim())return;
 const start=source.match(/^\s*/)[0],end=source.match(/\s*$/)[0],trim=source.trim(),value=start+translate(trim)+end;
 if(current!==value)node.nodeValue=value;textSources.set(node,{source,rendered:value});
}
function processElement(node){
 if(!node.hasAttribute('title')&&!node.hasAttribute('aria-label')&&!node.hasAttribute('placeholder')&&!node.matches('time.game-time[datetime]'))return;
 if(node.closest('script,style,[data-site-preferences]'))return;
 let saved=attributeSources.get(node);if(!saved){saved={};attributeSources.set(node,saved);}
 for(const attr of ['title','aria-label','placeholder'])if(node.hasAttribute(attr)){
  const current=node.getAttribute(attr),old=saved[attr],source=old&&current===old.rendered?old.source:current,value=translate(source);if(current!==value)node.setAttribute(attr,value);saved[attr]={source,rendered:value};
 }
 if(node.matches('time.game-time[datetime]')){const value=translate(formatTime(node.getAttribute('datetime'),prefs.timezone));if(node.textContent!==value)node.textContent=value;}
}
function localize(rootNode){
 if(rootNode.nodeType===3){processText(rootNode);return;}
 if(rootNode.nodeType!==1||rootNode.matches('script,style'))return;
 processElement(rootNode);
 const walk=document.createTreeWalker(rootNode,NodeFilter.SHOW_TEXT|NodeFilter.SHOW_ELEMENT,{acceptNode:n=>n.nodeType===1&&n.matches('script,style,[data-site-preferences]')?NodeFilter.FILTER_REJECT:NodeFilter.FILTER_ACCEPT});
 while(walk.nextNode()){const n=walk.currentNode;if(n.nodeType===3)processText(n);else processElement(n);}
}
const pending=new Set();let queued=false;
function observe(){observer?.observe(document.body,{subtree:true,childList:true,characterData:true,attributes:true,attributeFilter:['title','aria-label','placeholder']});}
function flush(){queued=false;if(flushing)return;flushing=true;observer?.disconnect();try{const roots=new Set(pending);pending.clear();for(const n of roots){if(!n.isConnected)continue;let ancestor=n.parentNode;while(ancestor&&!roots.has(ancestor))ancestor=ancestor.parentNode;if(!ancestor)localize(n);}}finally{flushing=false;observe();}}
function queue(node){pending.add(node);if(!queued){queued=true;queueMicrotask(flush);}}
function preferencesUI(){
 for(const host of document.querySelectorAll('[data-site-preferences]')){
  host.replaceChildren();const label=document.createElement('label'),caption=document.createElement('span'),select=document.createElement('select');caption.textContent=prefs.language==='en'?'Time zone':'時區';select.dataset.timezone='';select.setAttribute('aria-label',caption.textContent);
  for(const z of zones)select.add(new Option(z[prefs.language==='en'?2:1],z[0]));select.value=prefs.timezone;
  select.addEventListener('change',()=>change({timezone:select.value}));label.append(caption,select);
  const language=document.createElement('button');language.type='button';language.dataset.language='';language.textContent=prefs.language==='en'?'繁體中文':'English';language.setAttribute('aria-label',prefs.language==='en'?'切換為繁體中文':'Switch to English');language.addEventListener('click',()=>change({language:prefs.language==='en'?'zh-Hant':'en'}));host.append(label,language);
  if(!storageAvailable){const note=document.createElement('small');note.textContent=translate('時間設定未儲存；本次選擇仍可使用。');note.setAttribute('role','status');host.append(note);}
 }
}
function change(value){const focused=document.activeElement?.hasAttribute('data-timezone')?'[data-timezone]':document.activeElement?.hasAttribute('data-language')?'[data-language]':null;const previous=prefs;prefs=validPreferences({...prefs,...value});translationCache.clear();try{localStorage.setItem(key,JSON.stringify(prefs));storageAvailable=true;}catch{storageAvailable=false;}
 document.documentElement.lang=prefs.language;preferencesUI();if(focused)document.querySelector(focused)?.focus({preventScroll:true});pending.add(document.body);flush();document.title=translate(originalTitle);document.dispatchEvent(new CustomEvent('site-preferences-changed',{detail:{timezoneChanged:previous.timezone!==prefs.timezone,languageChanged:previous.language!==prefs.language}}));}
root.SiteUI={translate,get language(){return prefs.language;},get timezone(){return prefs.timezone;},zoneLabel,zoneNote,periodDays:(a,b)=>daysInZone(a,b,prefs.timezone),eventDay:e=>e.time_confirmed&&e.tipoff_utc?dateAt(e.tipoff_utc,prefs.timezone):e.date_et,formatTime:s=>formatTime(s,prefs.timezone),refresh:n=>queue(n||document.body)};
function init(){document.documentElement.lang=prefs.language;preferencesUI();observer=new MutationObserver(records=>{for(const r of records){if(r.type==='childList')r.addedNodes.forEach(queue);else queue(r.target);} });const initial=()=>{pending.add(document.body);flush();document.title=translate(originalTitle);};if(root.playerCatalog&&root.jQuery)root.jQuery(document).ready(initial);else initial();}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init,{once:true});else init();
})(typeof window==='undefined'?globalThis:window);
