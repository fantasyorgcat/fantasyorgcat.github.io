# FantasyOrgCat NBA

公開網站：https://fantasyorgcat.github.io/

每日 07:00 UTC 排程（台灣 15:00）；GitHub 排程可能延遲，設定時間不代表實際啟動或完成時間，請核對頁面快照時間及 Actions 結果。daily workflow 先測試、產生真實報告、檢查並提交，再由同一次 workflow 的獨立 deploy job 發布该報告的確切 commit。產生工作維持 contents:write；發布工作限 contents:read、pages:write、id-token:write，使用既有僅允許 main 的 github-pages environment。沒有新增 token。來源失敗時停止產生與發布，保留上次有效網站。

本季、近 7／14 天固定使用 ESPN 同一批已完賽例行賽：按月讀取 scoreboard（`dates=YYYYMM`），依 event 季別、賽事類型與 completed 篩選，再讀取 summary 的球員 boxscore。GP、整季與近期統計由相同出場列計算，不混用更新較慢的聯盟 overview 或 gamelog summary totals。球員沿用 ESPN athlete ID；DNP 排除，有有效 stats 且 didNotPlay=false 的出場仍計入，不以 active 或 reason 排除。近 7／14 天仍按美東完整日期、排除今天；FG／FT 由命中／出手加權，TO 與排名公式不變。snapshot 記錄讀取月份、完賽 event IDs、出場列與球員數。錯季、重複、缺必要統計或 Final 的 summary 不完整時停止發布，保留上次有效報告。上季已結束的歷史統計仍使用原 ESPN 季別來源。

## 操作與閱讀體驗

首頁與九項配隊頁共用「球員與賽程／九項配隊」導覽。首頁固定工具列可跳到球員表與已選比較；橫向捲動仍保留姓名及勾選欄，統計顯示平均／總量中文標籤。首頁來源細節收合，主要文字 14–16px、輔助資料 13px，保留米藍橘粉配色。

配隊頁提供選球員、陣容管理、看比較與儲存庫的固定跳轉；空白陣容可直接開始選球。各陣容的選人按鈕會指定編輯對象，支援只看已選、原地取消與清除搜尋。名單修改與保存會就近回饋，名稱變更也標示未儲存。切換／新建／清空原陣容、移除球員、重設模擬及刪除保存或對手後，可立即復原上一個操作；繼續更新比較或編輯後失效，不是跨重新整理的歷史紀錄。瀏覽器拒絕保存時明示僅本次畫面恢復，不能當作已永久保存。

本輪沿用既有資料、演算法與儲存格式；未加入外部資源或私人聯盟連線。驗證與桌面／手機畫面見 [網站 UX QA](docs/site-ux/QA.md)。

## 資料與介面

- ESPN：全聯盟球員例行賽統計、現役名單與當季賽程。四週賽程以 America/New_York 日期呈現。
- 本季、近 7 天、近 14 天、上季可切換；近 7/14 天使用美東日曆，包含今天之前的完整日期。缺值顯示「—」。
- AVG / TOT 分別計算 PR；各期母體使用完整、有出賽的球員集合，名單過濾不改變 PR。FG% / FT% 使用總命中除以總出手，排序使用未四捨五入值，TOT 使用來源總量。
- 近10場估算防守效率：固定 ESPN，最近十場已完賽例行賽，不足時接續上季。對手估算回合＝FGA＋0.4×FTA－進攻籃板＋總失誤；指標為 100×對手得分合計÷對手估算回合合計，越低排名越前。使用 totalTurnovers；只有球員失誤及球隊失誤兩欄都明確存在時才可相加替代，缺值不補零。這是已標示的估算指標，不是原 PBP 精確 DefPoss。選定十場缺欄位即標 n/10 不完整、不排名，不用第十一場補替。snapshot 保留每隊樣本、日期、選定及缺漏 IDs，僅完整30隊才標示全排名；缺資料不阻止球員更新。
- 暖米色莫蘭迪儀表板以灰藍作主要操作、柔橘與灰粉作少量重點。深灰藍文字、選取底線、鍵盤焦點及排序箭頭保留可讀狀態；估算防守排名沿用難易配色，資料不完整時顯示中性灰色與 n/10。樣式來自 `dashboard.css`，下次產生報表仍保留配色。配色與前後截圖見 [MORANDI_QA.md](MORANDI_QA.md)。
- 儀表板提供收合資料說明。點球隊篩選後，固定的「全體球員」按鈕清除球隊及搜尋條件，保留當週的期間與 AVG/TOT。各週篩選獨立；手機表格可水平捲動查看右側數據。
- `data_snapshot.json` 保留來源、季別、視窗、資料母體、已完賽 event IDs 與估算防守涵蓋率。歷史快照保留當時的原始來源標示；新指標明示 estimated 與公式，不把舊指標改名帶入。

## 本機產生與檢查

```sh
pip install -r requirements.txt
python -m unittest test_sources test_espn_boxscores test_defense test_schedule test_player_catalog
python generate_report.py
python security_gate.py --generated
```

輸出 `fantasy_nba_report_v2.html` 與 `data_snapshot.json`。需要自動開啟報告時設定 `OPEN_REPORT=1`。

部署 gate 檢查 HTML 資產完整性、公開來源摘要、測試資料排除與發布檔案中的秘密模式。Pages 僅上傳首頁、資料摘要、三個固定版本本地 JS/CSS 與 `.nojekyll`。瀏覽器互動測試可使用已安裝的 Playwright 執行 `python test_dashboard_browser.py <網址>`；該測試不屬於網站發布內容。

週次控制只保留 YAHOO／ESPN／NBA 三個按鈕及一個下拉選單。NBA 是本站美東週一至週日的賽程週：開季第一場所在週為 Week 1，跨年不歸零，換季重設。Yahoo 使用經核對的當季公開 Game Dates 預設週表；ESPN 使用官方全季 Weekly 週曆，聯盟 matchup／季後賽日期可自訂。未核實球季的按鈕停用並標示「待核」，可依聯盟設定套用自訂期間。NBA 比賽事件仍取自 ESPN sports API，選擇平台不會更換比賽資料源。平台切換用選週時的起日定位，首次載入用美東今天；保留該定位日，長週往返切換不丟失原NBA週。無包含週時找下一週／季末週，不保留可能代表不同日期的週號。

2026–27 Yahoo 預設共23週，首週10/20–10/25，第7週11/30–12/13、第17週2/15–2/28各14天，預設季後賽為第20–22週（3/15–4/4）；NBA 賽程週共25週，首週10/19–10/25。來源：[Yahoo Game Dates](https://basketball.fantasysports.yahoo.com/nba/gamedates)，2026-10-10核對；明確日期保存於 `yahoo_game_dates_2026_27.json`。`fantasy_periods.py` 驗證連續、無重疊與週號，季別不同時不沿用舊表、不推算未核實新賽季。snapshot 逐平台保留來源與核對時間。

2026–27 ESPN 全季 Weekly 週曆共24個例行週，source season為2027。首週10/20–10/25；Cup第7週11/30–12/6與第8週12/7–12/13分開；明星賽第18週2/15–2/28合併；末週4/5–4/11。來源為官方 [season-level metadata](https://lm-api-reads.fantasy.espn.com/apis/v3/games/fba/seasons/2027?view=chui_default) 與 [pro-team schedules](https://lm-api-reads.fantasy.espn.com/apis/v3/games/fba/seasons/2027?view=proTeamSchedules_wl)，2026-10-10核對。日期、scoring period與來源摘要保存在 `espn_weekly_dates_2026_27.json`；postSeason scoring period175排除，沒有推定私人聯盟的季後賽輪次。核對方法與回歸見 [ESPN_WEEK_QA.md](ESPN_WEEK_QA.md)。

所有平台和自訂期間共用一個動態球員表，沿用原始統計及PR；不再輸出額外完整的整季球員HTML。平台切換保留搜尋、球隊、統計期間、AVG/TOT、按統計欄位排序及比較名單。來源尚未安排日期的 NBA Cup 等賽事不虛構，不保證开季前已有每隊82場。可執行 `python test_season_browser.py <網址>` 核對所有25個NBA週、23個Yahoo週及24個ESPN週的實際日期、場數、對手及手機操作。

球隊場次排序：點選「球隊賽程」的 Games 表頭，第一次由多到少（↓），再點由少到多（↑），也可使用 Enter 或空白鍵。相同場次維持原始次序，未知場次置後，真正的 0 場正常排序。週次／平台重建表格後使用新期間的場次，箭頭回到 ↕；不改球員 Rank、篩選或資料快照。檢查：`node test_team_tools.cjs`、`CHROMIUM_PATH=/usr/bin/chromium python test_team_sort_browser.py`（使用目前真實 index.html，不下載資料）。

球員比較：勾選「比較」，即可在名單上方比較跨隊球員。賽程直接沿用目前週次主表的日期、場次、主客與防守標示；近四週與整季切換後同步。統計可獨立切換期間、AVG/TOT及排序，PR沿用完整聯盟母體。比較僅保留在本次頁面，不讀寫瀏覽器儲存；移除陣容與備份功能，不刪除使用者原本儲存的資料。

ESPN/NBA資料再散布授權仍未確認，技術檢查不代表資料使用授權。

本機球員工具檢查：`python -m unittest test_sources test_defense test_schedule test_player_catalog`、`node --check player_tools.js`、`python test_player_tools_browser.py <預覽網址>`；原四週/整季瀏覽器測試亦須通過。

Rank：九個PR（PTS、REB、AST、3PM、STL、BLK、FG%、FT%、TO）未四捨五入加總，不含MIN／出賽時間PR；MIN及其PR仍顯示。各統計期及AVG/TOT在完整聯盟母體排名，最高第1，同分採1,2,2,4。缺任一納入PR不列Rank，缺MIN不影響；球隊與比較篩選不重編。


TO（失誤）：AVG使用ESPN avgTurnovers，TOT使用原始turnovers總數，近7/14天沿既有完整日曆窗口的逐場失誤計算。失誤越少PR越高；缺失誤資料不當0、不推估，不新增出賽門檻。Rank含TO、排除MIN。

## 賽程與自訂期間

NBA 比賽事件與 Fantasy 計分期間分開：保留 ESPN event ID、UTC 開賽時間、狀態、例行賽類型與時間確認旗標；美東日期決定歸屬，格內同時顯示美東／台北時間。未排定日期／時間不補造；延賽、取消與暫停保留提示，排程場數排除這三種狀態。下次成功產生時，改期沿同一 event ID 的新日期呈現；沒有宣稱即時更新或保留完整改期歷史。

「自訂期間／近期快捷」預設收合，可依聯盟設定輸入 1–31 天自訂美東起訖（含迄日），或切回原四個近期快捷。主表與比較表同步日期／對手／場數，統計期間、AVG/TOT 與 PR 不隨期間重算。第一個快捷區段不足七天時，比較表只列真實日期欄。平台與自訂控制均保留既有比較名單。

收合的排程資訊提供球隊期間場數、尚未開賽、剩餘背靠背組數與低比賽日（全聯盟美東當日 1–5 場）。尚未開賽只納入快照狀態為 scheduled、時間已確認、UTC 開賽時間晚於瀏覽時間的場次。每分鐘及頁面回到前景時重算，並顯示計算截止 UTC；重算不會抓取新的比分或狀態。時間已過但狀態仍未開賽、未知狀態、延賽、暫停與開賽時間待定另列待確認；取消不算剩餘。資料超過 48 小時會提示。這些是球隊排程，未套用使用者陣容、健康、位置資格、增員或 GP 上限，不能當成可用先發場數／最佳化結果。

離線合成資料驗收（需 Python requirements、已安裝 Playwright 與 Chromium）：

```sh
CHROMIUM_PATH=/path/to/chromium python test_schedule_browser.py /tmp/fantasy-schedule-preview
```

該測試將預覽、snapshot、桌面／手機截圖和結果寫入指定的隔離目錄，不改正式 index.html 或 data_snapshot.json。預覽醒目標示 UI TEST ONLY，發布 gate 會拒絕它。不能將這個合成預覽當作當日真資料驗收。測試涵蓋短週、1／7／14／31 天、跨年、無賽程、剩餘／背靠背／低比賽日、跨開賽時間的自動更新、背景回前景更新、空白整季選項保留已套用週次、非法期間、統計不變與 390px 水平捲動；UTC／DST／未排定／取消狀態另由 test_schedule 單元測試驗證。

資料补強與實作順序見 [DATA_CAPABILITIES.md](DATA_CAPABILITIES.md)。現有 ESPN gamelog 已解析逐場分鐘、命中及出手，尚未完整持久化；保存分母／逐場資料不必先找另一家廠商。先做賽程與低場次日、自訂排名／counting points、小樣本，再補分母與聯盟已計入總量後做 H2H／ROTO。沒有傷病、usage 或私人聯盟來源時，不推斷角色變化的因果，也不承諾二換一的空格價值或最佳先發已可計算。

## 九項配隊分析（H2H／ROTO 共用）

`roto.html` 延伸現有比較勾選，以所選季別實績比較原陣容、自訂多隊對手與多人換人後的雷達。雷達固定使用每場產效及同季每場基準，表格切換總量不改變雷達；計數類別為陣容成員每場貢獻的平均，FG／FT 合計每人命中／GP與出手／GP再加權，不平均百分比。表格保留預設整季總量合計，支援每人1場合計與一鍵切到平均產效；這是名單球員實績，不是聯盟每日先發已計入的累計。資料表重用原球員catalog、Rank／PR和本地DataTables，在同一列勾選／解除；名單與換人後編輯目標明示。缺值顯示已知小計／覆蓋率，圖表標已知部分、不畫完整面積，不完整資料不計換人差值。黑體字、小字至少13px，對手可自由新增、命名、刪除與勾選比較；對手名單自動保存在獨立localStorage key，既有命名陣容可載入為新對手。保存／對手隊數不設固定上限，實際容量依瀏覽器儲存空間而定；損壞保存不覆寫，停用或滿額仍可在本次頁面編輯。

TO 雷達以 0 失誤對應最外圈 100，同季來源每場平均對應 50，依 `100 / (1 + 每位成員平均 TO / 同季來源平均 TO)` 持續遞減；未知值或缺有效基準仍留白。其他八軸維持原尺度。原陣容編輯區可直接命名儲存／更新同名，並從上方比較設定切換聯盟／原陣容；新增空白名單不刪除已存資料，未儲存變更會提示。沿用既有命名陣容格式與 key，不複製或遷移舊保存；切換只載入球員名單並重設換人模擬，對手仍由既有比較勾選管理。

雷達節點可用滑鼠靠近、手機點選或鍵盤聚焦類別名稱查看數值；同類別同時列出目前顯示的所有陣容，節點重疊也可比較。主值為成員每場平均，另列名單每人各1場合計；命中率依出手加權，未知／已知部分與覆蓋率明示。提示跟隨雷達每場口徑，不隨總量表切換；重繪清除舊提示。

頁面提供 H2H 類別制與 ROTO 用途說明，以及本季／歷史資料提示。H2H 當週結果需球員可排進每日先發的場次；ROTO 補強目標需同一時間點全聯盟各隊已計入累計、FGM／FGA／FTM／FTA與剩餘先發假設，才能推估名次與分數。目前未實作聯盟累計輸入、當週先發預測或 ROTO 積分計算，換人差異僅代表所選季別產效差異。路徑與既有 localStorage key 保留，舊連結／陣容可繼續使用。

2025–26封存CSV（582人）保留於`data/roto/`，同份資料整套計算，不拼接舊七項與新分母。610候選唯一匹配481，129不適用／未匹配保留unknown，0姓名歧義；benchmark不強湊舊ESPN578。封存來源、署名、映射見 [ROTO_QA.md](ROTO_QA.md)；新介面與季別迭代驗收見 [整合QA](docs/roto/named-opponents/QA.md)。本地匯出：`python roto_data.py`；數學：`node test_roto_core.cjs`；契約：`python -m unittest test_roto_data test_roto_boxscore test_roto_package`。年度來源須合法取得與核hash後更新，不重試被拒URL或硬改ready flag。

`roto_package.py`串接既有每日管線的本季／上季及完整來源reference；有效本季例行賽實績出現後預設切到本季，封存資料保留真實季別，不跨季混用計數、投籃分母或基準。完整來源reference寫入snapshot供gate重現，未完整保存的母體不畫推定基準。來源更新失敗仍停更並保留有效報告，不保證来源永遠可用。本次沿用名單球員整季總量，未新增每日先發歷史或私人聯盟累計台帳。
