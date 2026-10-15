# 雷達節點實際數值提示

2026-10-15；基底 `9d6a6c7c25e763cb53996a36ec1c736685533c69`。原陣容卡片內切換選單的修正已由 PR #9 部署；本紀錄為後續節點提示功能。

## 行為與口徑

- 滑鼠距節點 16 CSS px 內即可查看；手機觸控點選使用 24 px 範圍，並保留頁面正常捲動。點類別名稱、鍵盤聚焦／Enter／Space 也可查看。Escape、點圖外或滑鼠離開圖區可關閉。
- 每個類別同時列出目前顯示的所有已選陣容，重疊時仍各有一列。只顯示已勾選曲線；標題顯示陣容組數，內容較多時可在提示框內捲動。
- 計數的主值是每位已知成員每場平均，與節點定位相符；副值是這份名單的每人各1場合計。FG／FT 顯示加權百分比及同口徑命中／出手，不平均百分比。TO 仍越低越佳。
- 每列顯示資料覆蓋率與「已知部分」。未知或來源衝突顯示破折號與原因，並不補0。雷達標準化分數不當作實際球員數值展示。
- 提示固定使用所選季別的每場資料，表格改成整季總量不改提示口徑。切換陣容、勾選、季別或其他重繪會清掉舊提示，防止顯示過期內容。
- 新增本機 HTML／SVG 提示，沒有新套件、外網請求、來源、保存格式、統計算法或每日排程變更。

## 驗證

`node --check roto.js`、`python security_gate.py` 通過，保留來源可重現、CSP 與公開資源限定。

`CHROMIUM_PATH=/usr/bin/chromium python test_roto_tooltip.py http://127.0.0.1:8774 /workspace/roto-evidence/radar-tooltip-final` 通過，使用實際來源於桌面 1500×1000 與手機 390×844（啟用觸控）驗證：靠近節點、兩個／三個陣容重疊仍分列、加權命中率、主副數值單位、覆蓋率、鍵盤與 Escape、圖外關閉、表格口徑切換、季別清除舊提示、未知成員、隱藏曲線、未裁定 FGA、隊名當純文字處理；無 JS／CSP 錯誤、額外外網請求或整頁溢出。

`CHROMIUM_PATH=/usr/bin/chromium PYTHONPATH=.test-deps python test_roto_browser.py http://127.0.0.1:8774 /workspace/roto-evidence/radar-tooltip-regression` 完整既有桌面／手機回歸通過：原陣容儲存與兩處切換、多對手、就地勾選／解除、固定表頭、橫捲、換人重設、未知小計、保存／損壞／容量保護、資料季別與首頁帶入。

人工檢視 [桌面重疊節點](overlap-values-1500.png) 與 [手機重疊節點](overlap-values-390.png)。[提示專項結果](tooltip-results.json)、[既有回歸結果](regression-results.json)。畫面為本機實際頁面驗證，未用實體 iOS／Safari 裝置驗證。

本次節點提示功能尚未合併或部署。
