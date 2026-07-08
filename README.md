# Fantasy-NBA-Streaming-Assistant

Quickly filtering players and schedules for NBA fantasy leagues

## 🏀 網頁工具（每日自動更新）

**👉 直達連結：https://hotmilk300.github.io/Fantasy-NBA-Streaming-Assistant/**

每天台灣時間 16:00 由 GitHub Actions 自動抓取 NBA 官方數據重新產生報告頁。

## 功能簡介

- **每週賽程過濾**：依 NBA 賽程列出各隊當週出賽場次，快速找出多賽球員
- **球員數據總表**：MIN / PTS / REB / AST / 3PM / STL / BLK / FG% / FT% 九項指標
- **四種數據期間**：Season（本季）／ Last 7 ／ Last 14 ／ Last Season（上季，新賽季初期沒數據時用）
- **AVG / TOT 切換**：場均與總和兩種視角，各自獨立排序
- **PR 百分位排名**：每項數據附全聯盟百分位（PR 0–100），一眼看出相對強弱
- **對位防守強度著色**：依對手防守評級為球隊上色，輔助 streaming 決策

## 本地執行

```bash
pip install -r requirements.txt
python generate_report.py
# 產出 fantasy_nba_report_v2.html，瀏覽器開啟即可
```

資料來源：[nba_api](https://github.com/swar/nba_api)（NBA 官方統計）
