# 固定表頭驗收｜2026-10-13

核對 remote 為 `https://github.com/fantasyorgcat/fantasyorgcat.github.io.git`，基準 main 與 `origin/main` 皆為 `dbe5622b118184d5ca1ec4e7a6e437b2e87e1cbd`；完成前再讀 remote main，仍相同。初始環境 `/workspace/taigoofantasy` 是另一個專案，本次另建正確 checkout，未改該專案。`/workspace`／目標 checkout 未找到 `AGENTS.md` 或 `.agents/skills`；環境 `/workspace/.agents` 為空。依已讀 Karpathy Guidelines 只修改本項必要樣式。

## 修改

- `dashboard.css` 新增 4 行規則／說明及一行分隔；`index.html` 只同步其既有內嵌 CSS。下次 generator 仍從 `dashboard.css` 讀取樣式，未改產生器或重新抓資料。
- 球員表沿用 DataTables 既有獨立表頭與橫捲同步，表身最大高度為 `min(60dvh,640px)`，支援 `60vh` fallback。長表在表身內上下捲動，原表頭保持在捲動區上方；沒有新增浮動副本、外掛或排序事件。
- 比較表同樣限高，thead 在自己的捲動區固定；球隊表原有 330px／手機 280px 捲動區繼續生效，固定 thead 規則也涵蓋排程資訊表。原莫蘭迪表頭背景、表頭排序、比較表左側球員欄保留。
- 三種表格的 overscroll containment 防止到達上下邊界時繼續推動外層頁面。頂部導航仍沿原 sticky 規則；本次「固定」是表格區內的垂直捲動，外層頁面仍可上下移動至其他區域。

[資料保存核對](docs/sticky-headers/data-preservation.json)：將新內嵌 CSS 還原後，`index.html` 與基準 main 的整份 HTML 完全一致，故所有腳本、球員資料、排名、賽程及日期皆未變。`data_snapshot.json` SHA256 為 `6cde860d32e31b257ab739c2b06072903e59bf237d28a59d2e4ce01a1ace1894`，前後相同。

## 固定表頭實際頁面驗證

使用本地 HTTP 提供 checked-in 真實 `index.html`，Chromium／Playwright 分別在 1500×1000 與 390×844 驗證；不是合成資料或正式發布後的 CDN 驗收。新增 `test_sticky_headers_browser.py`。

```sh
CHROMIUM_PATH=/usr/bin/chromium python test_sticky_headers_browser.py http://127.0.0.1:8765/index.html /tmp/nba-sticky-headers
```

實際 wheel 下捲後，球員／球隊／比較表首行向上移動超過 100px，表頭垂直位置差小於 2px；表頭在 viewport 內且低於頂部導航。手機橫捲後沒有頁面溢出、球員表表頭與表身 scrollLeft 同步。核對原表頭背景 `rgb(215,222,223)`、點選原統計表頭的升降排序、Games 的 Enter 鍵排序、期間／AVG/TOT 切換、14日 Yahoo 週重建及近期表格。球員 catalog／賽程／平台週次／快照時間的前後序列化完全相同，JS errors 與失敗請求均為空。[結果 JSON](docs/sticky-headers/browser-results.json)。

未修改 main 在同一固定表頭測試的球員表垂直溢出斷言失敗：[回歸反證](docs/sticky-headers/baseline-regression.txt)。

| 畫面 | 修改前 | 修改後 |
| --- | --- | --- |
| 桌面真實球員表下捲 | [1500px](docs/sticky-headers/before-players-1500.png) | [1500px](docs/sticky-headers/players-1500.png) |
| 手機真實球員表下捲 | [390px](docs/sticky-headers/before-players-390.png) | [390px](docs/sticky-headers/players-390.png) |

另外核對 [手機右側 FG%／FT%／TO／Rank](docs/sticky-headers/players-right-390.png)、[手機球隊場次表](docs/sticky-headers/teams-390.png)、[手機比較表](docs/sticky-headers/comparison-390.png)。本輪未驗證 Safari／iOS 真機。

## 其他驗證

- Python 單元測試 `test_sources test_defense test_schedule test_player_catalog`：45 項全通過。環境初始缺 `requests`，於 `/tmp/nba-sticky-test-deps` 安裝 requirements 所指定 `requests==2.34.2` 後執行，不改專案 requirements。
- `node test_team_tools.cjs`：數值雙向排序、同分穩定、未知置後、0場有效均通過。
- `python security_gate.py`：公開 HTML／資產完整性、來源、排除合成資料及既有 bounded scan 通過，未執行 staging 或發布。
- 既有 `test_dashboard_browser.py` 與 `test_team_sort_browser.py`：桌面／手機及13個跨平台代表期間通過。

- `test_schedule_browser.py`：隔離合成預覽驗證桌面／手機、自訂 1／7／14／31 日、跨年、長週、平台往返、剩餘場次及計時器等全通過；預覽仍標示 UI TEST ONLY，未混入正式 index／snapshot。

- `test_season_browser.py`：NBA 25週、Yahoo 23週、ESPN 24週，日期、場次、對手、統計／PR、排序及手機橫捲全部通過。[結果](docs/sticky-headers/season-browser-result.json)。
- `test_player_tools_browser.py`：桌面與手機、全部72個平台期間、跨隊球員勾選、缺值與零場、Rank／TO排序、無Storage呼叫、保留舊儲存及無外部請求全部通過。[結果](docs/sticky-headers/comparison-schedule-browser-result.json)。該既有測試的來源判別以 `/fantasy_` URL 切割，因此用忽略的本地 `fantasy_nba_report_v2.html` symlink 指向同一 `index.html` 執行；驗收後移除 alias，未產生新的真實報告。
- 所有瀏覽器驗證的 JS errors／failed requests 為空。除了明確標示的合成排程驗證，其他測試使用同一份未更新資料的真實 index。
- `git diff --check` 通過。

## ROTO 盤點

[ROTO_READONLY.md](ROTO_READONLY.md) 說明現有資料、缺少的投籃分母、ID 勾選重用、手機分頁及不同單位／期間的共同基準。沒有 ROTO 功能、localStorage、登入或新資料源的實作。

## 交付範圍

僅本地修改／測試與可審查本地版本。未 push、merge、部署或直接修改遠端 main。公開網站仍是原版本。ESPN 上游唯讀 API 請求遇環境代理 403；不影響使用已保存真實頁面的上述驗收，亦未以不完整來源重建資料。
