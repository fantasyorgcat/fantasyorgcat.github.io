# 九項配隊分析驗收

2026-10-14；以 `origin/main` 的 `f1ec7628b83374de99971e522e3a95cb420d4c43` 為基底。

## 變更結果

- 首頁入口與 `roto.html` 改稱「九項配隊分析」，H2H／ROTO 共用。既有路徑、球員 ID、命名對手與陣容保存 key 保留。
- 雷達固定使用所選季別的每場資料與每場完整來源基準；計數類別比較成員每場平均，FG／FT 以每人命中／GP及出手／GP合計後加權，TO 反向。
- 表格仍預設整季總量，可另切到每人1場合計；上方按鈕可一鍵查看平均產效。兩個表格單位控制同步，雷達不受表格切換影響。
- 本季／歷史資料提示與可展開的 H2H／ROTO 用途說明。歷史數據僅供參考；ROTO 名次與分數需要實際全聯盟已計入累計、投籃分子分母與剩餘先發假設。本次未建立聯盟台帳、先發預測或積分計算器。
- 缺資料的小計、覆蓋率、不畫完整面積、不完整換人差值、舊陣容儲存與現有季別更新管線均保留。沒有修改統計快照、封存來源、雷達算法核心或來源存取方式。

## 驗證

`node --check roto.js`、`node test_roto_core.cjs` 通過：投籃加權、個人 GP、TO 方向、未知資料、換人、固定基準、1200 隊儲存與損壞／容量錯誤處理。

`PYTHONPATH=.test-deps python -m unittest test_player_catalog test_roto_package`：16 項通過，核對球員 catalog、資料期間及季別切換。

`python security_gate.py --stage /workspace/roto-evidence/nine-category-stage` 通過：原始公開資源與完整性、來源可重現、既有 CSP、合成資料排除、限定發布檔案。

`CHROMIUM_PATH=/usr/bin/chromium PYTHONPATH=.test-deps python test_roto_browser.py http://127.0.0.1:8772 /workspace/roto-evidence/nine-category-browser` 通過，使用實際 checkout 資料於 1500×1000 與 390×844 Chromium 驗證：

- 共用頁名與使用說明、一鍵平均、保留總量預設、兩個控制同步。
- 表格單位切換前後的所有雷達曲線座標完全相同。
- 完整球員表就地勾選／解除、鍵盤焦點、排序／搜尋／分頁、固定表頭與橫捲選取欄。
- 多對手、自訂隊名、疊圖顯示、舊保存匯入、重新載入、換人／重設不改原陣容。
- 未知球員、已知小計與圖表、不完整差值、零出手、已聲明來源差異、資料期間切換。
- 手機沒有整頁水平溢出；沒有 JS、CSP、請求失敗或額外外網請求。

另外以明確隔離的合成資料驗證投籃：總量表 FG%＝83.3333%，但雷達固定使用每場加權 FG%＝78.5714%；切換表格只改表格數字。合成資料不寫入發布檔案。本季第一份有效資料自動成為預設亦用隔離資料驗證。

另用實際本季（2026–27 尚無例行賽資料）確認提示「本季尚無例行賽實績」，無數據的雷達不畫曲線。人工檢視下列桌面與手機截圖，黑體字、莫蘭迪配色與橫捲表格保留。

- [桌面首頁](nine-category-1500.png)
- [手機首頁](nine-category-390.png)
- [桌面平均比較](nine-category-average-1500.png)
- [手機平均比較](nine-category-average-390.png)
- [完整瀏覽器結果](browser-results.json)

本輪驗證範圍為本機實際頁面，未合併或部署，未聲稱已完成正式網站操作驗證。未以實體 iOS／Safari 裝置驗證。
