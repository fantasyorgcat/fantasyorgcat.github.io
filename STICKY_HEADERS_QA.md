# 網頁下捲固定表頭驗收｜2026-10-13

核對 remote 為 `https://github.com/fantasyorgcat/fantasyorgcat.github.io.git`，基準 main 與 `origin/main` 皆為 `dbe5622b118184d5ca1ec4e7a6e437b2e87e1cbd`。初始環境 `/workspace/taigoofantasy` 是另一個專案，本次另建正確 checkout，未改該專案。`/`、`/workspace`、目標 checkout 未找到相關 `AGENTS.md` 或 `.agents/skills`；環境 `/workspace/.agents` 為空。

## 最終行為與最小變更

原 main 的球員表僅設定 `scrollX:true`，沒有 `scrollY` 或表身限高；原本依網頁垂直捲動查看球員。最終版本保留這個流程：**往下滑網頁時，原欄名固定在既有頂部導覽下方，球員主表沒有垂直內捲盒。** 上一版本新增的主表／比較表限高及 overscroll containment 已全部移除。

- `dashboard.css` 新增 3 行規則及說明：讓球員 section／DataTables 外層的 overflow 為 visible，使原本的 `.dt-scroll-head` 能對網頁 sticky；表身維持原有水平捲動。固定的是真正有排序事件的原表頭，未新增浮動副本、外掛或點擊代理。
- 原表頭的上方位置取自 CSS `--workspace-height`；`player_tools.js` ready handler 新增 3 行，量測既有導航高度並以 `ResizeObserver` 同步。手機換行、內容高度及 viewport 變更不依靠硬編碼高度。導航 z-index 20、表頭 10，表頭背景沿原灰藍 `#d7dedf`，原莫蘭迪米／藍／橘／粉保留。
- 球隊表本來就有 330px／手機 280px 的局部垂直捲動及固定 thead；保留既有流程，並將同一 thead 規則涵蓋排程資訊表。比較表恢復原先只有水平捲動的樣式，沒有新增垂直限高。
- `index.html` 只同步既有內嵌 CSS 與上述導航高度 JS。generator 已讀這兩個來源檔，因此無須改產生器或重新抓資料，下次正常產生仍保留修正。

[資料保存證據](docs/sticky-headers/data-preservation.json)：將兩個修改後的內嵌來源還原，整份 HTML 與基準 main 完全一致。所有球員 catalog、排名、賽程、日期、平台週表及其他腳本皆未變。`data_snapshot.json` 前後 SHA256 相同：`6cde860d32e31b257ab739c2b06072903e59bf237d28a59d2e4ce01a1ace1894`。

## 原本網頁捲動方式的驗收

使用本地 HTTP 提供 checked-in 真實 `index.html`，Chromium／Playwright 在桌面 1500×1000 及手機 390×844 驗證；不是合成資料或發布後 CDN 驗收。`test_sticky_headers_browser.py` 直接測網頁捲動。

```sh
CHROMIUM_PATH=/usr/bin/chromium python test_sticky_headers_browser.py http://127.0.0.1:8766/index.html /tmp/nba-sticky-headers
```

- 桌面用 wheel，手機啟用 mobile／touch emulation 並送出真實 CDP touchStart／touchMove／touchEnd 上滑事件。確認**網頁 scrollY 增加超過 300px、球員行向上超過 300px，而表身 scrollTop 始終 0、scrollHeight 等於 clientHeight、max-height 為 none**。這不是表格 scrollTop 測試。
- 網頁繼續下捲，表頭頂端與導航底部相差小於 2px；修改導航說明使其換行增高後，位置仍同步。核對原背景及表頭／資料欄位 x、width 逐欄相差小於 2px。
- 手機 touch 橫滑使球員表 scrollLeft 增加，原 DataTables 表頭 scrollLeft 同步，沒有頁面水平溢出；深處的原 Rank 表頭升降排序均可點擊。
- Yahoo 14日長週動態重建及期間／AVG/TOT 切換後仍適用；離開表格後表頭不繼續漂浮。原球隊局部內捲固定表頭及 Games Enter 鍵排序照常。
- 比較功能另作跨隊勾選、期間／模式切換與移除驗證；不存在比較表垂直限高。所有資料序列化前後相同，JS errors／failed requests 均為空。[最新結果](docs/sticky-headers/browser-results.json)。

未修改 main 在相同網頁捲動測試中，表頭已移出 viewport，無法固定於導航下方：[回歸反證](docs/sticky-headers/baseline-regression.txt)。

| 真實球員表下捲 | 修改前 | 最終修改後 |
| --- | --- | --- |
| 桌面 | [1500px](docs/sticky-headers/before-players-1500.png) | [1500px](docs/sticky-headers/players-1500.png) |
| 手機 | [390px](docs/sticky-headers/before-players-390.png) | [390px](docs/sticky-headers/players-390.png) |

另見[手機表格橫滑](docs/sticky-headers/players-right-390.png)、[原手機球隊場次表](docs/sticky-headers/teams-390.png)。未驗證 Safari／iOS 真機。

## 最終版本其他檢查

- Python `test_sources test_defense test_schedule test_player_catalog`：45 項通過；初始缺 requests，於 `/tmp/nba-sticky-test-deps` 安裝 requirements 指定版本後執行，不改 requirements。
- `node --check player_tools.js`、`node test_team_tools.cjs`：通過。
- `test_dashboard_browser.py`：球隊篩選、搜尋、統計模式、排序、手機橫捲與導航可達通過。[最終結果](docs/sticky-headers/dashboard-browser-result.json)。
- `test_team_sort_browser.py`：桌面／手機、13個跨平台代表期間、同分及未知場次、鍵盤排序與比較通過。[最終結果](docs/sticky-headers/team-sort-browser-results.json)。
- `test_schedule_browser.py`：最終 CSS／JS 的隔離生成及桌面／手機合成賽程回歸通過，包含自訂1／7／14／31日、跨年、平台長週、比較同步、計時／回前景更新。[最終結果](docs/sticky-headers/synthetic-schedule-browser-result.json)。預覽明確標示 UI TEST ONLY，不替換正式資料。
- `python security_gate.py`：HTML／資產完整性、來源、合成資料排除及 bounded scan 通過，未 staging 或發布；`git diff --check` 通過。

先前限高版本的完整整季及比較回歸 JSON 不再作為最終版本證據；本頁列出的結果均針對最終網頁捲動方案。

## 交付範圍

[ROTO_READONLY.md](ROTO_READONLY.md) 的唯讀資料盤點與方案不變；未實作 ROTO、保存、登入或新增來源。僅本地修改／測試／版本，未 push、merge 或部署，遠端 main 不變。ESPN 上游唯讀 API 請求遇環境代理 403；不影響已保存真實頁面的驗收，沒有用不完整來源重建資料。
