# 每日更新穩定性與首頁效能驗收

日期：2026-10-26。基準為本機分支 `fix/daily-update-and-perf` 的原始 HEAD `7dbd0da`。本次工作沒有推送、開 PR、觸發 Actions 或部署。

## 結果與原因

| 問題 | 修改 | 效果／邊界 |
|---|---|---|
| ESPN 單筆缺欄、分鐘字串、重複紀錄會直接中止 | 集中數值解析；逐筆隔離球隊、球員名單、賽程、league stats、scoreboard、summary、gamelog；寫入 `source_warnings` 與 `source_quality` | 身分不明者略過；數值不明保留 `null`，保留已確認的 GP，不補零；大範圍毀損仍失敗 |
| 單筆失敗與整批毀損沒有明確區別 | 每來源與彙總層檢查有效筆數、異常筆數 | 零有效筆直接失敗；異常超過 1 筆且超過 10% 失敗。容許一筆異常，避免開季小樣本再次整天中止 |
| 部署階段曾間接載入 pandas | 確認既有 `defense_contract.py` 的純標準函式庫邊界；新資料 codec 也只用標準函式庫 | 乾淨 `venv --without-pip` 實跑 stage 通過；沒有把既有 PR #21 修正冒充本次新增修正 |
| 舊版 Actions | checkout v4、setup-python v5，加入 pip cache | 維持既有工作流程與發布方式；更新新檔案的 git add、SHA 清單 |
| HTML 重複包含所有球員、週次與完整資料 | 同源 `report_data.js`，DataTables data arrays + deferRender；只初始化目前週次 | HTML 72,592 bytes；初始只有一個球員 DataTable，未顯示列保留為資料 |
| 重複欄位、相同期間、賽程 HTML 佔大量空間 | 固定欄位陣列、AVG/TOT 共用相同值、相同期間與 badge/time 字串共用；ROTO 同樣壓縮 catalog | Python／JS 解壓完整相等；只縮短整數浮點字串，保留 PR 原始精度與未知值 |
| 延後渲染後每次 draw 重複寫 88 個統計欄屬性 | 屬性移到 `createdCell`，排名變動時只更新受影響欄 | 保留完整排序、DOM 屬性與自訂排名，消除換頁／搜尋的重複成本 |
| Windows 自動換行破壞固定 SRI | `.gitattributes` 對既有 `assets/*` 關閉文字換行轉換 | 三個既有套件檔案的位元組與 HEAD blob 相同；沒有更新套件或改 CDN |

防守效率原本即為可缺資料來源，維持缺資料／不排名的行為並補警告。HTTP 重試耗盡、錯季根節點、分頁總數不一致等來源整體錯誤仍拒絕；賽程事件先完整解析雙方，再一次加入，避免半場資料。當已有已完賽賽程或例行賽已進入 11 月，scoreboard 卻零場時拒絕產出；休賽季合法空值仍保留。

`data_snapshot.json` 既有外部欄位意義不變；診斷為新增欄位。`completed_events` 仍代表 scoreboard 的已完賽事件，新增 `included_events`／`skipped_events` 分開記錄納入情形。缺值會傳遞成未知平均／總量，並不把部分缺漏當成完整資料。

## 實際資料產出

完整連網產生只執行一次，時間 `2026-10-26 12:15 UTC`（台灣 20:15），統計最後比賽日 `2026-10-25`。Season／L7／L14 各 401 人，上季 ESPN 母體 578 人；現役 catalog 518 人。

唯一來源警告為 `boxscore record=401909095/5211983: unknown minutes '--'`。產出已完成且印出 `Report generated: fantasy_nba_report_v2.html`。PowerShell 對這筆 stderr 警告包成 `NativeCommandError`，外層執行回報 exit 1；當時未另外保存 Python 的 exit code，因此不宣稱該次命令 exit 0。保留其新產出，再以 `--generated` 與無 pandas/numpy 的 `--stage _site` 重新驗證，兩者 exit 0。沒有為此重抓全季。

另提供 `python generate_report.py --offline`：以已保留的報表／資料檔重封裝，保留來源時間，絕不把離線重封裝標成今日抓取。此路徑曾用於建立相同快照的效能對照；最後交付使用上述實抓資料。

檔案 SHA 與來源診斷見 [generated-evidence.json](generated-evidence.json)。

## 檔案大小與首載量

以下均為未壓縮 bytes；基準是原 HEAD，交付檔是 10/26 新快照。

| 檔案／資源 | 修改前 | 修改後 |
|---|---:|---:|
| index.html | 27,234,161 | 72,592 |
| roto_data.js | 3,093,335 | 983,482 |
| report_data.js（新增） | — | 686,558 |
| report.js（抽出既有程式） | — | 10,334 |
| data_codec.js（新增） | — | 1,626 |
| data_snapshot.json | 733,589 | 747,872 |
| 首頁第一次載入全部 HTML／JS／CSS | 27,451,288 | 1,074,174 |

HTML 減少 99.73%，ROTO 資料減少 68.21%，首頁首載資源總量減少 96.09%。ROTO 資料與 snapshot JSON 不在首頁首載清單中。完整逐檔清單見 [sizes.json](sizes.json)。這是可重現的本機未壓縮資源總量，沒有把它當成 GitHub Pages 的實際 gzip/Brotli 傳輸量。

## 效能量測

沿用 `test_performance_benchmark.py`，保留每版本／寬度 5 次 cold + 5 次 warm、每種操作 30 次。兩版使用同一份 `2026-10-25 12:16 UTC` snapshot 與完整相同 player catalog，排除更新球員統計造成的差異；正式新快照在效能測完後才換入。cold 是新 browser context；warm 是同 context 重新導覽。1440px 使用原速，390px 使用 CPU 4x 模擬。本機伺服器，量測時沒有並行跑其他瀏覽器測試。

首次完整量測抓到逐格屬性重寫造成的操作成本，修正後以既有 `--resume` 重用完全相同的 baseline groups，只重測兩組 after；外部 JS／CSS／HTML 合併指紋不同才重新量測。原始紀錄的 `index_sha256` 欄現代表這個整體指紋，並非僅 index.html。

| 首次載入中位數（ms） | 桌機前 → 後 | 手機 CPU4x 前 → 後 |
|---|---:|---:|
| FCP | 176 → 120 | 692 → 664 |
| load event | 706.4 → 116.6 | 3,351 → 692.3 |
| 長任務總時間 | 1,691 → 264 | 12,926 → 1,651 |
| 最後長任務結束 | 2,185.9 → 379.5 | 13,879.7 → 2,357.4 |

| 操作 p95（ms） | 桌機前 → 後 | 手機 CPU4x 前 → 後 |
|---|---:|---:|
| AVG／TOT | 77 → 85 | 553.6 → 456 |
| 統計期間 | 146.4 → 112.7 | 1,066.2 → 824.7 |
| 換頁 | 28.9 → 29.2 | 163.9 → 147.1 |
| 搜尋 | 36 → 31.5 | 206.2 → 153.2 |
| 換週 | 639.4 → 304.7 | 4,041.1 → 1,644.7 |

四組量測皆無 JavaScript error。不是所有指標都改善：桌機 warm FCP 為 80 → 268ms，桌機 AVG／TOT p95 為 77 → 85ms；沒有宣稱每個互動都變快。手機仍有約 1.45 秒的最大單一啟動長任務。load event／最後長任務時間不是正式 TTI，也沒有量測正式站網路延遲。

原始樣本：[benchmark-results.json](benchmark-results.json)；摘要：[benchmark-summary.json](benchmark-summary.json)。原本 `docs/performance-phase1/` 未修改。

## 驗收紀錄

| 驗收 | 實際結果 |
|---|---|
| 指定 8 個 Python unittest 模組 | PASS：`Ran 88 tests in 4.835s`、`OK` |
| 新 transport 測試 | PASS：`Ran 5 tests in 0.435s`、`OK` |
| test_team_tools.cjs | PASS：numeric directions、stable ties、unknown last、real zero |
| test_roto_core.cjs | PASS：weighted FG/FT、GP、TO、unknowns、immutable replacements、storage、known subtotal |
| test_site_ui.cjs | PASS：preferences、UTC/local、year boundaries、DST、scoring spans |
| test_table_tools.cjs | PASS：PR full precision、ties、unknown/empty categories、TO、9CAT、preferences |
| security_gate.py --generated | PASS：資源完整性、來源、fixture 排除、ROTO coverage／unknowns |
| 乾淨 venv 缺套件查證 | PASS：`pandas: None`、`numpy: None` |
| 乾淨 venv security_gate.py --stage _site | PASS：20 檔白名單，含新資料／解碼／主程式檔 |
| index.html < 1MB | PASS：72,592 < 1,000,000 bytes |
| git diff --check | PASS：exit 0，無輸出 |
| 全部 test_*_browser.py + tooltip/edges | PASS：11 支 `test_*_browser.py` 加 2 支 tooltip／UX edges，共 13 支全部 exit 0 |
| 本機 commit | BLOCKED：`git add -- .gitattributes` exit 1，無法建立 `.git/index.lock`：`Permission denied`。目前環境把 `.git` 設為唯讀；未嘗試繞過，尚未建立 commit |

逐命令 exit code 見 [checks.json](checks.json) 與同目錄 `.log`。瀏覽器使用本機 Chrome、測試依賴 Playwright 僅裝於忽略的 `.test-deps`，未修改 production requirements，也未新增第三方前端套件。

最後一輪皆使用交付的新快照與最終程式，結果見 [browser-results.json](browser-results.json)，完整輸出在 `browser/`。Phase 1 功能檢查、欄位偏好、球員比較、合成賽程、時區、全季 25／23／24 週、sticky header、球隊排序、ROTO、UX、tooltip 與 UX edge cases 全數通過。已實際檢視桌機與 390px 手機截圖，表格、原色系、日期、控制與水平捲動正常。

## 既有測試的等價轉換

沒有刪除既有測試。以下列出所有涉及舊 HTML／舊快照假設的修改，並保留對應行為檢查。

| 測試檔 | 轉換與仍檢查的內容 |
|---|---|
| test_dashboard_browser.py | 等待目前表格而非全部週次；L7 改依真實 catalog 檢查顯示／排序值，不再假設休賽季全空；仍逐一開四週與篩選 |
| test_phase1_performance_browser.py | 新增初始只有一表與未產生全部 DOM 的斷言；所有球員仍逐一比對 8 個統計視圖、排序值、排名；已有 DOM 再核對屬性；先建立隱藏 W2 再檢查 hidden draw，保留單次 draw、cache、observer、共享賽程檢查 |
| test_player_tools_browser.py | 等待目前表格；賽程數、L7 排名改核對當期來源，保留全母體 PR、TO、跨週比較與資料不變性 |
| test_schedule_browser.py | fixture 同時複製新外部程式；等待目前表格；原合成賽程、時鐘、跨年、DST、平台與日期邊界檢查不變 |
| test_schedule_locale_browser.py | 僅調整等待條件；所有語言、時區、週次、日期、storage 失敗檢查保留 |
| test_season_browser.py | 明確進入快捷週並選 ET；從完整日期屬性核對日期；所有球員先檢查同隊賽程完全一致，再回傳 30 隊資料與來源逐日比對，避免傳回 518 份重複 HTML；保留所有平台週次 |
| test_sticky_headers_browser.py | 明確選 LS 進行固定版面檢查；L7 由全空假設改成 catalog 精確值；sticky 幾何斷言保留 |
| test_table_preferences_browser.py | 對全量 data rows 核對 PR 總和、排名與排序；已 materialize 的 cell 同時核對 DOM；L7 空值改來源值；保留 1327／1500／390／320px 幾何、設定與 storage 檢查 |
| test_team_sort_browser.py | 固定 610 人改核對 catalog 與表格完整母體；全量排名用資料核對並檢查已有 DOM；額外建一個真 DataTable 保留原 helper adapter 的排序箭頭測試 |
| test_roto_browser.py | 頁面載入先檢查真實預設期間與 catalog 解碼；歷史固定算例明確切回歷史來源；新增／保留本季 known subtotal 與 partial 標記；sticky 先捲到計算出的實際固定邊界，原幾何要求不變；所有 storage／替換／權重／tooltip 檢查保留 |
| test_defense.py | 原 matchup title／color 檢查讀取解壓後外部 events，不依賴已移除的靜態表格 cells |
| test_performance_benchmark.py | 舊 body bytes 相同不再適用，改要求 snapshot JSON 與完整 catalog 相等；指紋涵蓋外部 JS／CSS；採樣數不變 |
| test_sources.py、test_espn_boxscores.py、test_schedule.py | 單筆必定 raise 的舊預期依本次需求改為 unknown／skip＋警告，補 GP／總量保留及零有效／大範圍毀損拒絕案例；保留季別、分頁、整數、時區與原完整資料算例 |

## 保留風險與未執行

- 未部署，因此 GitHub Actions 自然排程與正式 Pages 速度尚未驗證。本機測試不能替代自然執行收據。
- 來源未知仍會顯示未知，異常比例過高仍會停止；新 guard 的 10% 是明確可審閱的工程容忍界線，不是來源正確率保證。
- 第一個開啟的新週次仍需建立 DataTable；手機 CPU4x 換週 p95 約 1.64 秒，後續若要再改善可專門處理資料欄建立成本。
- CSP 保持原值，`connect-src 'none'` 沒改；所有新增資料與程式透過同源 script 載入。首頁既有 unsafe-inline 沒有擴張，ROTO 仍僅允許 self。
- Playwright 是為完成指定瀏覽器驗收所必需的測試依賴，僅放忽略目錄。沒有增加正式執行依賴。
- Git 工作分支仍為 `fix/daily-update-and-perf`，程式與產物留在工作目錄；commit message 已備於 [commit-message.txt](commit-message.txt)，最後一行含指定 Co-Authored-By。待環境允許寫入 `.git` 才能提交，目前沒有新 commit hash。
