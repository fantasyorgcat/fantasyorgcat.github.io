# ROTO 本地實作與驗收｜2026-10-14

**尚未完成完整九項真實資料驗收，沒有 push／merge／部署。** 使用者已批准固定表頭與 ROTO 一次完成後一起上線；此批准保留，不需再次核准，但目前資料缺口仍不符合發布條件。

接續 `/workspace/fantasyorgcat.github.io` 的 `fix/sticky-table-headers`，保留 `b4e072d4c5d493fb929063d2e2ccf8969e65cd19` 的網頁下捲固定表頭。remote 為 `fantasyorgcat/fantasyorgcat.github.io`，本輪開始 main 為 `dbe5622`、工作樹乾淨，未開新專案或修改其他投資專案；未新增登入、費用、來源帳密或存取權限。

## 已實作與本機驗證

- `roto.html` 是同站獨立頁，首頁有入口；既有比較勾選的 ESPN ID 可透過 `roto.html#players=…` 在新分頁帶入。沒有複製整張 26 MB 首頁資料，ROTO 使用獨立本地 `roto_data.js`。
- 原陣容、手動對手及多人換人模擬；最多三組 SVG 雷達疊圖及九項數據／模擬差異。搜尋／加入／移除／去重，原名單不被模擬改寫，重設模擬可還原；手機名單編輯預設收合，保留莫蘭迪米、灰藍、柔橘與灰粉。
- 只使用 **2025–26 例行賽上季實績**，來源快照 **2026-10-10 17:34 UTC**；不是新季預測、可先發產量、增員資格或私人聯盟已計入成績。顯示 GP、平均分鐘、各類覆蓋與缺值原因。
- 此裝置的多份命名陣容，保存原隊／對手／模擬後名單，載入至原隊或對手，更新同名與刪除。使用新 key `fantasyorgcat:roto:rosters:v1`，只保存 ID／名稱／時間，統計用當前快照；不碰舊比較／陣容 key。儲存停用時維持頁面操作，格式損壞時禁止覆寫原內容。

## 聚合與固定尺度

`roto_core.js` 是瀏覽器／Node 共用純函數，不依賴付費圖表或第三方 CDN：

- **上季實績總量**：七項 counting 相加真實來源總量；FG／FT 為 `Σmade / Σattempt ×100`。相同季別但不同個人 GP 的歷史曝光差異在介面明確說明。
- **每人1場合計**：逐員 `total / 個人GP` 再相加；投籃亦將每人 made／attempt 除以 GP，按相同口徑相加後求比率。這是等量出賽的歷史實績聚合，不是預測，不平均球員百分比。
- 任一選入球員缺該類數據，整隊該類為未知，另列 `known / roster size` 覆蓋；零出手時百分比未知。未知項不畫點／完整填色，不當0；計數欄真實0保留0。
- 雷達為 `50 + 15 × z`、截於0–100。計數類先取每名成員平均貢獻，相對固定上季參考球員的均值／標準差；百分比參考亦同口徑按出手加權。**TO 反向**。名單人數不同另明示，真實合計與差值留在表格。這不是百分位或真實 ROTO 聯盟積分。
- 參考 records、有效樣本數、均值／標準差及內容 hash 保存在資料檔；更換原隊／對手／模擬不改尺。發布 gate 可從已保存 reference records 重算基準並比對，拒絕無法重現的尺度。

## 資料管線與不可發布的缺口

`utils.py` 已新增 FGM/FGA/FTM/FTA 的 bulk 原始欄位讀取、非負整數與 made≤attempt 驗證；missing保留None。近期逐場總量亦保存四欄，零出手／缺分母不填0%。`player_catalog.py` 保存每期間 shooting，`generate_report.py` 同次輸出 `roto_data.js` 並用完整上季來源母體建固定參考；每日 workflow 一併測試、驗證及提交該檔。**以上契約透過單元／隔離生成驗證，這輪沒有拿到真的投籃分母。**

現有真實首頁為610人目錄，其中479人有上季實績；來源完整母體578人。沒有完整578人的原始數據或任何已持久化投籃分母。因此目前 ROTO reference 為479／578，shooting complete **0／578**，`data_ready=false`，FG／FT全為未知。沒有從百分比、GP或點數方程反推分母，也沒有改拿更舊賽季或假資料。

[來源存取紀錄](docs/roto/source-access.json)：

| 來源／目標 | 結果與處理 |
| --- | --- |
| ESPN `site.web.api.espn.com/.../statistics/byathlete?season=2026&seasontype=2&limit=1000` | 前輪已發生代理 CONNECT 403，這輪未重試／換路徑。 |
| NBA 官方 `stats.nba.com/stats/leaguedashplayerstats`，Season2025–26、Regular Season、Totals | 普通公開GET遭環境代理 CONNECT 403；未換 headers、代理或端點繞過。 |
| Basketball Reference `NBA_2026_totals.html` | web.open回403，停止。 |
| CBS `.../stats/player/all/nba/regular/2025/...` | 普通公開GET遭環境代理 CONNECT403，停止。 |

NBA公開stats頁亦無法透過web工具讀取，Fox公開頁回406，沒有對其改header繞過。repo現有各branch／歷史只找到snapshot／平台週表／測試JSON，沒有可用的2025–26 made/attempt raw資料。**未驗證到可用替代來源**；下一個可接受路徑是合法取得既有ESPN bulk或官方完整季末匯出，保留來源／季別／GP與ID對照，再重建完整reference。不能把上述候選來源說成已可用。

[實際發布 gate](docs/roto/release-gate.json) 的錯誤為：`ROTO release blocked: full last-season reference and shooting denominators are incomplete`。靜態資產／CSP／provenance檢查通過，但完整資料gate失敗；這是程式發布條件失敗，尚未觸發任何遠端發布動作。不得略過這個gate或將 `data_ready` 手動改true。

`security_gate.py --stage` 已準備在原有發布 allowlist 追加 ROTO六個自有檔案；現有Pages與daily部署工作仍使用原權限、環境及存取設定。CLI現有GH_TOKEN失效，GitHub連接器的唯讀get_repo已成功、回報既有push權限；沒有新增帳密或權限，也尚未嘗試寫入。

## 測試與真實畫面

- Python：`test_sources test_defense test_schedule test_player_catalog test_roto_data` **54項通過**。包括bulk made/attempt保存、zero／missing、季別、完整參考群、整數／made≤attempt、可重現基準及gate不能只信ready flag。gate的「完整資料通過」案例只存在隔離的單元測試目錄，不是真實數據驗收。
- `node test_roto_core.cjs`：加權FG／FT、兩種GP口徑、TO反向、缺值／覆蓋、重複球員、原名單不變、替換／復原、固定基準及保存讀回通過；`node test_team_tools.cjs`／JS syntax亦通過。
- [ROTO browser結果](docs/roto/browser-results.json)：1500×1000與390×844、最多三組疊圖、多人換人不改原隊、重設、保存／重新載入、多份命名、unknown球員、手機收合、無頁面橫向溢出、儲存停用／損壞、XSS文字、首頁勾選開新分頁均通過；JS／failed requests／external requests／CSP errors均空。這裡使用的是目前不完整但真實的checked-in資料，不是完整九項驗收。
- 完整九軸與83.3333%加權FG另由明確 `UI TEST ONLY` 的 route隔離合成資料驗證，不修改 `roto_data.js`，沒有列作真實分母。
- [原頁儀表板](docs/roto/dashboard-regression.json)、[球隊排序](docs/roto/team-regression.json)、[原網頁下捲表頭／手機觸控](docs/roto/sticky-regression.json) 通過；保留 `b4e072d` 修正。
- [隔離賽程生成與回歸](docs/roto/schedule-synthetic-regression.json) 通過：1／7／14／31日、跨年、25個NBA週／23個Yahoo週／24個ESPN週與長週／平台往返、比較同步與計時重算。合成預覽維持UI TEST ONLY，未替換正式頁。
- `git diff --check` 通過；[data-status](docs/roto/data-status.json) 記錄原snapshot前後完全一致，首頁playerCatalog／統計未改，只同步新增入口與腳本／CSS。

畫面：[桌機真實資料](docs/roto/roto-real-1500.png)、[手機圖表](docs/roto/roto-real-390.png)、[手機九項數值](docs/roto/roto-real-table-390.png)、[手機資料缺口標示](docs/roto/roto-real-top-390.png)。未驗證Safari／iOS真機。

## 待完成的正式驗收

取得可核對的2025–26完整made/attempt來源、檢查球員ID及GP／計數總量的一致性、重建578人完整reference，並通過9項真實資料／發布gate後，才能一次push／合併原分支及Pages部署。之後仍須監看部署到terminal、讀回正式首頁與`/roto.html`核對commit／快照及功能。**現在沒有部署run／正式新頁版本證據，沒有把表頭先單獨上線。**
