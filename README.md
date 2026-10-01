# Fantasy NBA Streaming Assistant

公開網站：https://hotmilk300.github.io/Fantasy-NBA-Streaming-Assistant/

每日 08:00 UTC 更新，成功產生並通過檢查、push 後，用既有 GITHUB_TOKEN 送出版本綁定的 repository_dispatch，由 GitHub Pages 自動發布。Pages 會驗證報告 SHA 等於當前 main，及每日 workflow 確實成功；過期、失敗或來源不符的事件會停止部署。兩個 workflow 的權限宣告保持原值，沒有新增 token。來源失敗時保留上一份有效報告。

## 資料與功能

- ESPN：全聯盟球員例行賽統計、現役名單及當季賽程。四週賽程以 America/New_York 日期呈現。
- Season、Last 7、Last 14、Last Season 可切換；近 7/14 天使用美東完整日曆日，不包含當天。缺值顯示「—」。
- AVG / TOT 分別計算 PR；各期間使用完整、該期間有出賽的球員母體，不因球隊篩選改變 PR。FG% / FT% 的近況使用總命中數除以總出手數。
- PBP Stats：各隊當季最近 10 場例行賽的防守效率，100 × 對手總得分 ÷ 該隊 game-log DefPoss 合計。各隊獨立選場；不足 10 場標示 n/10，無資料顯示灰色暫缺，不使用去年或其他代理指標。分母來源與比分來源需對得上相同場次。
- `data_snapshot.json` 記錄來源、季別、窗口、資料母體與防守計算摘要。防守效率是球隊指標，並非位置別 DvP。

## 本機產生與檢查

```sh
pip install -r requirements.txt
python generate_report.py
python test_sources.py
python test_dispatch.py
python security_gate.py --generated
```

輸出 `fantasy_nba_report_v2.html` 與 `data_snapshot.json`。需要自動開啟報告時設定 `OPEN_REPORT=1`。

發布 gate 檢查 HTML 資產完整性、公開資料來源摘要、測試資料排除及追蹤檔案的有限憑證模式。Pages 僅上傳首頁、資料摘要、三個固定版本本地 JS/CSS 與 `.nojekyll`，不發布整個 repository。這些檢查不代表絕對沒有安全風險。
