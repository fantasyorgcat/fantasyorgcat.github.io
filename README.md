# Fantasy NBA Streaming Assistant

公開網站：https://hotmilk300.github.io/Fantasy-NBA-Streaming-Assistant/

每日 08:00 UTC 更新。daily workflow 先測試、產生真實報告、檢查並提交，再由同一次 workflow 的獨立 deploy job 發布该報告的確切 commit。產生工作維持 contents:write；發布工作限 contents:read、pages:write、id-token:write，使用既有僅允許 main 的 github-pages environment。沒有新增 token。來源失敗時停止產生與發布，保留上次有效網站。

## 資料與介面

- ESPN：全聯盟球員例行賽統計、現役名單與當季賽程。四週賽程以 America/New_York 日期呈現。
- 本季、近 7 天、近 14 天、上季可切換；近 7/14 天使用美東日曆，包含今天之前的完整日期。缺值顯示「—」。
- AVG / TOT 分別計算 PR；各期母體使用完整、有出賽的球員集合，名單過濾不改變 PR。FG% / FT% 使用總命中除以總出手，排序使用未四捨五入值，TOT 使用來源總量。
- PBP Stats：各隊最近 10 場已完成例行賽，當季不足時接續上季。排除季前賽、季後賽及未完成賽事；GameId 去重。防守效率為 100 × 對手總得分 ÷ 該隊逐場 DefPoss 合計。各隊獨立取樣；不到 10 場標示 n/10，無資料呈現中性灰色。必要來源缺漏或不一致即停止發布。
- 灰底儀表板提供收合資料說明。點球隊篩選後，固定的「全體球員」按鈕清除球隊及搜尋條件，保留當週的期間與 AVG/TOT。各週篩選獨立；手機表格可水平捲動查看右側數據。
- `data_snapshot.json` 保留來源、季別、視窗、資料母體與各隊最近 10 場 GameId／得分／回合數。防守效率是球隊指標，並非位置 DvP。

## 本機產生與檢查

```sh
pip install -r requirements.txt
python -m unittest test_sources test_defense
python generate_report.py
python security_gate.py --generated
```

輸出 `fantasy_nba_report_v2.html` 與 `data_snapshot.json`。需要自動開啟報告時設定 `OPEN_REPORT=1`。

部署 gate 檢查 HTML 資產完整性、公開來源摘要、測試資料排除與發布檔案中的秘密模式。Pages 僅上傳首頁、資料摘要、三個固定版本本地 JS/CSS 與 `.nojekyll`。瀏覽器互動測試可使用已安裝的 Playwright 執行 `python test_dashboard_browser.py <網址>`；該測試不屬於網站發布內容。
