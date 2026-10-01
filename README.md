# FantasyOrgCat NBA

公開網站：https://fantasyorgcat.github.io/

每日 08:00 UTC 更新。daily workflow 先測試、產生真實報告、檢查並提交，再由同一次 workflow 的獨立 deploy job 發布该報告的確切 commit。產生工作維持 contents:write；發布工作限 contents:read、pages:write、id-token:write，使用既有僅允許 main 的 github-pages environment。沒有新增 token。來源失敗時停止產生與發布，保留上次有效網站。

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
python -m unittest test_sources test_defense test_schedule
python generate_report.py
python security_gate.py --generated
```

輸出 `fantasy_nba_report_v2.html` 與 `data_snapshot.json`。需要自動開啟報告時設定 `OPEN_REPORT=1`。

部署 gate 檢查 HTML 資產完整性、公開來源摘要、測試資料排除與發布檔案中的秘密模式。Pages 僅上傳首頁、資料摘要、三個固定版本本地 JS/CSS 與 `.nojekyll`。瀏覽器互動測試可使用已安裝的 Playwright 執行 `python test_dashboard_browser.py <網址>`；該測試不屬於網站發布內容。

整季週次選單列出 ESPN 已公布的當季例行賽，與近四週快捷控制並存。以 America/New_York 日期、週一至週日編號：開季第一場所在週為 Week 1，跨年不歸零，換季重設。近1週仍從今天起至週日；整季第一週可有開季前的空白日期，無比賽週仍可選。來源尚未安排日期的 NBA Cup 等賽事不虛構；選單是已公布整季賽程，不保證開季前已有每隊82場。當季尚無已公布賽程時選單停用。來源失敗或缺漏仍中止生成。

整季資料透過同一次產生程序中的記憶體快取共用30隊API回應；每日重新產生時重新讀取來源。前端僅加一個延後初始化的整季表格，切換週次更新日期、場數與對手，沿用原始統計與PR。可執行 `python test_season_browser.py <網址>` 驗證下拉實際資料與手機操作。

球員比較：勾選「比較」，即可在名單上方比較跨隊球員。賽程直接沿用目前週次主表的日期、場次、主客與防守標示；近四週與整季切換後同步。統計可獨立切換期間、AVG/TOT及排序，PR沿用完整聯盟母體。比較僅保留在本次頁面，不讀寫瀏覽器儲存；移除陣容與備份功能，不刪除使用者原本儲存的資料。

ESPN/NBA/PBP資料再散布授權仍未確認，技術檢查不代表資料使用授權。

本機球員工具檢查：`python -m unittest test_sources test_defense test_schedule test_player_catalog`、`node --check player_tools.js`、`python test_player_tools_browser.py <預覽網址>`；原四週/整季瀏覽器測試亦須通過。

Rank：九個既有PR（MIN、PTS、REB、AST、3PM、STL、BLK、FG%、FT%）未四捨五入加總；各統計期及AVG/TOT在完整聯盟母體排名，最高第1，同分採1,2,2,4。缺任何PR不列Rank；球隊與比較篩選不重編。

