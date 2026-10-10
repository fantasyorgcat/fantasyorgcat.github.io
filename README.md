# FantasyOrgCat NBA

公開網站：https://fantasyorgcat.github.io/

每日 08:17 UTC 排程（台灣 16:17）；排程設定不代表每次已成功更新，請核對頁面快照時間及 Actions 結果。daily workflow 先測試、產生真實報告、檢查並提交，再由同一次 workflow 的獨立 deploy job 發布该報告的確切 commit。產生工作維持 contents:write；發布工作限 contents:read、pages:write、id-token:write，使用既有僅允許 main 的 github-pages environment。沒有新增 token。來源失敗時停止產生與發布，保留上次有效網站。

## 資料與介面

- ESPN：全聯盟球員例行賽統計、現役名單與當季賽程。四週賽程以 America/New_York 日期呈現。
- 本季、近 7 天、近 14 天、上季可切換；近 7/14 天使用美東日曆，包含今天之前的完整日期。缺值顯示「—」。
- AVG / TOT 分別計算 PR；各期母體使用完整、有出賽的球員集合，名單過濾不改變 PR。FG% / FT% 使用總命中除以總出手，排序使用未四捨五入值，TOT 使用來源總量。
- PBP Stats：各隊最近 10 場已完成例行賽，當季不足時接續上季。排除季前賽、季後賽及未完成賽事；GameId 去重。防守效率為 100 × 對手總得分 ÷ 該隊逐場 DefPoss 合計。各隊獨立取樣；不到 10 場標示 n/10，無資料呈現中性灰色。必要來源缺漏或不一致即停止發布。
- 灰底儀表板提供收合資料說明。點球隊篩選後，固定的「全體球員」按鈕清除球隊及搜尋條件，保留當週的期間與 AVG/TOT。各週篩選獨立；手機表格可水平捲動查看右側數據。
- `data_snapshot.json` 保留來源、季別、視窗、資料母體與各隊最近 10 場 GameId／得分／回合數。防守效率是球隊指標，並非位置 DvP。

## 本機產生與檢查

```sh
pip install -r requirements.txt
python -m unittest test_sources test_defense test_schedule test_player_catalog
python generate_report.py
python security_gate.py --generated
```

輸出 `fantasy_nba_report_v2.html` 與 `data_snapshot.json`。需要自動開啟報告時設定 `OPEN_REPORT=1`。

部署 gate 檢查 HTML 資產完整性、公開來源摘要、測試資料排除與發布檔案中的秘密模式。Pages 僅上傳首頁、資料摘要、三個固定版本本地 JS/CSS 與 `.nojekyll`。瀏覽器互動測試可使用已安裝的 Playwright 執行 `python test_dashboard_browser.py <網址>`；該測試不屬於網站發布內容。

週次控制只保留 YAHOO／ESPN／NBA 三個按鈕及一個下拉選單。NBA 是本站美東週一至週日的賽程週：開季第一場所在週為 Week 1，跨年不歸零，換季重設。Yahoo 使用經核對的當季公開 Game Dates 預設週表，私人聯盟可能自訂；ESPN fantasy 完整當季週表未核實，按鈕停用並標示「待核」。NBA 比賽事件仍取自 ESPN sports API，選擇 Yahoo 不會更換比賽資料源。平台切換用選週時的起日定位，首次載入用美東今天；保留該定位日，長週往返切換不丟失原NBA週。無包含週時找下一週／季末週，不保留可能代表不同日期的週號。

2026–27 Yahoo 預設共23週，首週10/20–10/25，第7週11/30–12/13、第17週2/15–2/28各14天，預設季後賽為第20–22週（3/15–4/4）；NBA 賽程週共25週，首週10/19–10/25。來源：[Yahoo Game Dates](https://basketball.fantasysports.yahoo.com/nba/gamedates)，2026-10-10核對；明確日期保存於 `yahoo_game_dates_2026_27.json`。`fantasy_periods.py` 驗證連續、無重疊與週號，季別不同時不沿用舊表、不推算未核實新賽季。snapshot 逐平台保留來源與核對時間。

所有平台和自訂期間共用一個動態球員表，沿用原始統計及PR；不再輸出額外完整的整季球員HTML。平台切換保留搜尋、球隊、統計期間、AVG/TOT、按統計欄位排序及比較名單。來源尚未安排日期的 NBA Cup 等賽事不虛構，不保證开季前已有每隊82場。可執行 `python test_season_browser.py <網址>` 核對所有25個NBA週與23個Yahoo週的實際日期、場數、對手及手機操作。

球員比較：勾選「比較」，即可在名單上方比較跨隊球員。賽程直接沿用目前週次主表的日期、場次、主客與防守標示；近四週與整季切換後同步。統計可獨立切換期間、AVG/TOT及排序，PR沿用完整聯盟母體。比較僅保留在本次頁面，不讀寫瀏覽器儲存；移除陣容與備份功能，不刪除使用者原本儲存的資料。

ESPN/NBA/PBP資料再散布授權仍未確認，技術檢查不代表資料使用授權。

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
