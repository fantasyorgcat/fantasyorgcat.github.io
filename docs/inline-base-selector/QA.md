# 原陣容卡片內切換選單

2026-10-15；基底 `de17c3ea6d8943aaa88521e45a45964366523509`。

原本選單只位於雷達圖上方的比較設定，使用者在原陣容卡片儲存後，卡片內看不到切換入口。現在在卡片內、聯盟／陣容名稱上方加入「切換已儲存陣容」。卡片及頁面上方選單共用相同的已存名單與目前選取狀態；儲存後立即同步，任一處切換都載入相同名單。提示文案改成指向卡片內選單。

沒有改動保存格式／key、球員資料、雷達算法、來源或每日排程。

驗證通過：

- `node --check roto.js`。
- `python security_gate.py`：來源重現、CSP、靜態資源及發布限定檔案檢查。
- `CHROMIUM_PATH=/usr/bin/chromium PYTHONPATH=.test-deps python test_roto_browser.py http://127.0.0.1:8774 /workspace/roto-evidence/inline-base-selector-browser`：桌面 1500×1000、手機 390×844 實際資料完整回歸；新增確認卡片內選單可見、儲存後兩處同步、從卡片切換、從上方反向同步與重新載入後切換。既有舊保存、同名更新、未知值、換人重設、容量／損壞保護及手機無整頁溢出檢查均通過。

已人工檢視 [手機卡片](saved-base-editor-390.png) 與 [桌面卡片](saved-base-editor-1500.png)。[完整瀏覽器結果](browser-results.json)；畫面證據為本機實際頁面驗證。
