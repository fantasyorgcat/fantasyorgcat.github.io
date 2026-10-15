# 網站操作與 UI 完善

檢查日期：2026-10-15（台灣）。正式基準 `9d6a6c7`，本輪亦包含尚未發布的雷達節點數值提示（原 PR #10，`3a391ec`）。僅處理 fantasyorgcat/fantasyorgcat.github.io。

## 檢查結果與改動

| 原本的操作問題 | 現在的操作 |
| --- | --- |
| 390px 空白配隊頁的選球表在約 y=3337px，首次不易知道如何開始 | 首屏出現「開始選球員」，固定區段導覽一鍵到選球、陣容管理、比較與儲存庫 |
| 首頁有 9–12px 輔助字、英文控制項；摘要佔用大量首屏 | 黑體主要 14–16px／輔助資料 13px、平均／總量與搜尋分頁中文化；來源摘要可展開 |
| 在首頁長表勾選後，要回上方才能找到比較；橫捲後不見姓名 | 固定工作列顯示「比較 n 人」；姓名與勾選首欄保留，配隊入口仍帶原球員 ID |
| 配隊頁不易找到各陣容的選人方式或已選球員 | 各陣容有明確選人按鈕；「只看已選」可原地解除，清除搜尋可回完整名單，選取列明顯標示 |
| 修改名稱仍顯示已保存，切換後未存編輯無法找回 | 名稱與名單均檢查未保存狀態；切換／新增／清空及移除後提供單步復原 |
| 操作訊息在頁面另一端，保存或刪除不容易確認 | 就近選人回饋與可見操作提示；對手保存失敗明示僅本次畫面恢復 |
| 手機固定控制與表頭高度容易互相遮住 | 導覽與控制列依實際尺寸量測表頭位置；320–390px 均保持頁面無橫向溢出 |

圖表保留「每場成員平均／加權命中率」；表格預設整季總量，單位切換不改雷達。保留未知資料、覆蓋率、TO 越低越好與零失誤在外圈。來源／歷史限制與 H2H／ROTO 用途仍可展開閱讀。

## 畫面

- [手機首頁](home-390.png)
- [首頁固定姓名、比較入口與橫捲](home-players-390.png)
- [手機配隊首屏與開始選球](roto-start-390.png)
- [手機選人控制與固定表頭](roto-picker-390.png)
- [桌面雷達與九項比較](comparison-1500.png)

畫面使用本機實際網站與已提交的真實資料，操作中的名單是測試用選擇，並非使用者私人聯盟成績。沒有呼叫新資料來源；合成案例與真資料驗證分開記錄。

## 驗證

全部通過：

- `node --check roto.js`、`node --check player_tools.js`、Python 語法及 `git diff --check`。
- `PYTHONPATH=.test-deps python -m unittest test_sources test_defense test_schedule test_player_catalog test_roto_data test_roto_boxscore test_roto_package`：68 tests。
- `node test_roto_core.cjs`、`node test_team_tools.cjs`：投籃加權、TO 方向、缺值、模擬、保存及排序。
- `test_dashboard_browser.py`、`test_sticky_headers_browser.py`：桌面／手機固定表頭、手機橫捲、排序及欄位對齊。見 [sticky 結果](sticky-results.json)。
- `test_player_tools_browser.py`：NBA 25／Yahoo 23／ESPN 24 週，桌面與手機各完整核對，包含比較與保存資料不被清除。[結果](home-regression-results.json)
- `test_roto_browser.py`：桌面／手機既有選球、多人換人、多隊、季別、資料口徑、已知小計、本地陣容與資料異常回歸；另以合成資料驗證新季自動預設與投籃加權。[結果](roto-regression-results.json)
- `test_roto_tooltip.py`：滑鼠靠近、手機點選、重疊數據、單位、缺值、鍵盤、關閉提示與名稱安全。[結果](tooltip-results.json)
- `test_site_ux_browser.py`：1500／390／360／320px 的導航、鍵盤焦點、選球篩選、操作回饋及恢復未存名稱／名單／換人模擬。[結果](site-ux-results.json)
- `test_site_ux_edges.py`：1500／390px 的固定層對齊、只看已選末頁解除、換隊分頁、恢復 active ID 與保存順序、quota／停用時的正確提示。[結果](edge-results.json)
- `test_schedule_browser.py`：獨立合成預覽驗證 1／7／14／31 日、跨年、空賽程、取消／延賽、排程刷新與跨平台週次。[結果](schedule-results.json)
- `python security_gate.py --stage ...`：來源重現、CSP、固定資產、秘密掃描及 13 個檔案發布白名單。

瀏覽器最終結果均無 JS／CSP 錯誤、整頁橫向溢出或非預期外部請求。生成器、`dashboard.css`、`player_tools.js` 與 `index.html` 內嵌版本同步；資料、統計、來源時間、每日 workflow 與儲存 key 未修改。

## 實用限制

- 復原為本次頁面的上一個操作；後續編輯／重繪會失效，不跨重新整理。原陣容仍需按儲存，對手依原設計自動保存。
- 本機保存仍受瀏覽器容量與允許儲存狀態限制，未增加登入或跨裝置同步。
- 首頁仍沿用既有完整靜態資料輸出；本輪沒有重做資料載入架構或宣稱網路載入速度提升。
- 未 merge／部署。截圖是本地實頁驗證，不能視為正式站已更新。
