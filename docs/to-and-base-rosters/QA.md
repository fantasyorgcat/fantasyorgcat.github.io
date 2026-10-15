# TO 零失誤尺度與多原陣容保存驗收

2026-10-15，基底 `b773df97fc67d49525e0424d21d1f8b777edca85`，同一個 `/workspace/fantasyorgcat.github.io` 執行環境。環境可正常執行修改及測試，無連線阻擋。

## 功能

- TO 每場雷達以 0 失誤對應最外圈 100；同季來源的每場平均對應 50，失誤增加時持續往內。使用 `100 / (1 + 成員每場平均 TO / 同季來源每場平均 TO)`，不把高失誤截成同一個最低值。其他八軸維持原尺度；未知資料與缺有效基準仍留白。
- 以實際資料的 Trevor Keels（GP 8、TO 0）確認 TO 點到中心的距離等於外圈半徑 123；高失誤球員位於內側。資料少的球員仍顯示 GP，並不推論其為最佳球員。
- 原陣容編輯區新增聯盟／陣容名稱、儲存／更新同名及新增原陣容按鈕；比較設定新增切換原陣容選單。名單修改後明示未儲存，切換載入名單並重設換人模擬。
- 共用原本命名陣容的 `fantasyorgcat:roto:rosters:v1`，舊保存無須轉換，可從新選單載入；同名更新沿用原 ID，另取名稱可保存不同聯盟。新增或切換不修改其他保存。各聯盟在本次功能中代表已命名球員名單，對手顯示仍沿用既有勾選管理，未新增私人聯盟連線。
- 保存只在同瀏覽器／網域／裝置，不設固定隊數上限，容量取決於瀏覽器。關閉保存、損壞格式與容量不足時保留既有內容，顯示錯誤，仍可編輯當前名單。

## 必要的發布可重現修正

最新 main 的每日輸出使用 Python 3.11，而發布驗證與本機可能使用其他版本。原先 `sum` 讓六個命中率基準的最後數位不同，嚴格來源重現檢查因而失敗。改以 `math.fsum` 計算加權命中率的加總，再重建衍生資料；並讓各期間的尺度 metadata 說明新的 TO 定義。

已逐欄比對本次 `roto_data.js` 與基底：僅六個 benchmark 浮點末位與兩個 `reference.scale` 說明不同。球員數據、原始來源、catalog、期間、快照時間、映射與基準輸入均未改動。未放寬 gate、未存取新來源、未改 workflow 或每日排程。

現有歷史來源測試原先把候選總數固定為 610、可比舊資料固定為 479；最新 main 已是 622／480。測試改以實際候選人數與有 GP 的匹配者核對這兩個數量，保留來源 582 人、匹配 481 人、0 舊數據差異、投籃分子分母、原始 CSV hash 與固定母體等檢查，並補測新增未知候選不改基準。

## 測試證據

- `node --check roto.js`、`node --check roto_core.js` 與 `node test_roto_core.cjs` 通過。包括 TO 0＝100、同季平均＝50、嚴格遞減、部分已知與未知、加權投籃、換人、1200 隊保存及容量錯誤。
- `PYTHONPATH=.test-deps python -m unittest test_roto_data test_roto_boxscore test_roto_package`：23 項通過，包含完整來源反向排序後的基準完全相同，以及新候選不改封存基準。
- `python security_gate.py --stage /workspace/roto-evidence/zero-to-base-stage`（Python 3.12.14）及 `python3.13 security_gate.py` 均通過。相同衍生檔案在兩個版本下可嚴格重現，來源／CSP／完整性／公開檔案限定均保留。
- `CHROMIUM_PATH=/usr/bin/chromium PYTHONPATH=.test-deps python test_roto_browser.py http://127.0.0.1:8773 /workspace/roto-evidence/zero-to-base-final` 通過，使用實際 checkout 資料於 1500×1000、390×844 Chromium 驗證。除原有完整回歸外，新增：零 TO 外圈、正 TO 內側、編輯區儲存、兩個聯盟重新載入後切換、舊保存、新增空白、同名更新相同 ID、未保存變更不覆寫舊資料、切換重設模擬、容量錯誤不覆寫、損壞格式禁止覆寫。無頁面溢出或 JS 錯誤。

畫面已人工檢視，沿用黑體字、原配色、球員表與排序／就地勾選：

- [手機零 TO 雷達](zero-to-radar-390.png)
- [桌面零 TO 雷達](zero-to-radar-1500.png)
- [桌面原陣容儲存](saved-base-editor-1500.png)
- [手機原陣容儲存](saved-base-editor-390.png)
- [手機原陣容切換](saved-base-switch-390.png)
- [完整瀏覽器結果](browser-results.json)

此為本機驗證與審查版本；本次未合併或部署。未使用實體 iOS／Safari 裝置驗證。
