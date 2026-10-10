# NBA Fantasy 資料盤點與補強方案｜2026-10-10

這份盤點以當日已發布的 NBA 倉庫 main `906579ff04e09bf68b25bfc95799c581f9e49f5b` 為基準，與本次平台週次草稿分開。沒有要求把下列所有功能塞入本次賽程修改。

## 實際生效來源與更新

NBA 公開站是 https://fantasyorgcat.github.io/ ，來源為 [fantasyorgcat/fantasyorgcat.github.io](https://github.com/fantasyorgcat/fantasyorgcat.github.io/tree/906579ff04e09bf68b25bfc95799c581f9e49f5b)（repo ID 1101177706）。環境設定中的 [taigoofantasy](https://github.com/fantasyorgcat/taigoofantasy/blob/f0f60ba2ae9a855c7b268b33da5325dd186e1838/README.md)（repo ID 1402564855）是另一個台股合成原型，網址為 `/taigoofantasy/`，不是 NBA 網站的新倉庫或資料源。

最新可讀真實 [snapshot](https://github.com/fantasyorgcat/fantasyorgcat.github.io/blob/906579ff04e09bf68b25bfc95799c581f9e49f5b/data_snapshot.json) 為 **2026-10-10 11:28 UTC**：現役名單610人、上季2025–26統計母體578人；本季2026–27與L7/L14皆0人。不是沿用10月1日快照。當季賽程1200個已公布日期的例行賽事件，未定日期0個，首場2026-10-20、末場2027-04-11（美東）。四週視窗2026-10-10至11-01有92場。NBA官方先公布每隊80場，兩場待Cup配對；30×80÷2=1200為推算，數量符合已公布範圍。[NBA公告](https://www.nba.com/news/2026-27-nba-regular-season-schedule)

[Daily run #11 / 38048334584](https://github.com/fantasyorgcat/fantasyorgcat.github.io/actions/runs/38048334584) 的產生與部署已完成成功，更新時間2026-10-10 11:28:55 UTC；它由前一來源commit `23b794a` 執行，產生真實報告commit `906579f`。每日 [workflow](https://github.com/fantasyorgcat/fantasyorgcat.github.io/blob/906579ff04e09bf68b25bfc95799c581f9e49f5b/.github/workflows/daily_update.yml) 設定08:17 UTC，並發布當次產生的確切report SHA。本次executor的公開Pages HTTP讀回遭網路代理403，web讀取亦無法開啟，故沒有在此重做CDN位元組比對；母執行緒已核對公開頁面與snapshot的11:28時間。草稿UI尚未合併、產生正式報告或部署。

## 現有功能、資料與 fallback

| 資料／功能 | 程式實際使用及保存內容 | 現有限制 |
|---|---|---|
| 名單與球員統計 | ESPN sports API：球員／球隊ID、現役球隊、GP、MIN平均、PTS/REB/AST/STL/BLK/3PM/TO平均與七項counting總量、FG%/FT%。本季、完整L7/L14、上季；AVG/TOT、搜尋、球隊篩選、跨隊比較。 | 不包含Fantasy位置資格、私人聯盟持有／FA、先發配置或傷病。MIN在TOT模式仍為平均，百分比不相加。 |
| 逐場 gamelog | `player_gamelog` 已從同一ESPN來源讀取美東date、MIN、PTS/REB/AST/STL/BLK/TO、FGM/FGA、FTM/FTA、FG3M/FG3A。去重並檢查逐場數與GP一致。 | 逐場rows在運算後未持久化；回傳丟掉event ID。`recent_stats`保留GP、counting平均／總量及比率，未保留命中／出手分母。並非需要新增逐場資料廠商才做得到。 |
| 實際NBA比賽 | ESPN各隊 `/schedule?season=…&seasontype=2`，按event ID去重；保存UTC tipoff、美東date、status、season_type、time_confirmed、主客球隊；格內顯示美東與台北時間。 | 不直接讀Yahoo賽程或NBA CDN。快照更新時改期沿同ID的新日期呈現，沒有完整改期歷史；不含NBA季後賽事件。 |
| 對手防守 | PBP Stats各隊最近10場已完成例行賽，當季不足接續上季；100×對手總得分÷DefPoss總和。snapshot保存GameId、樣本區間與得分／回合證據。 | 球隊防守，非位置DvP、usage、傷病或球員角色。跨季接續是明確規則，不能當成新賽季狀態。 |
| 排程工具 | 已有自訂1–31日、剩餘未開賽、剩餘B2B、全聯盟1–5場低比賽日、待定／延賽標示、超過48小時提示；每60秒／回前景重算截止。 | 依靜態事件與瀏覽時間重算，不更新比分；不是球員可用先發場次或合法FA最佳化。 |

當日PBP防守有效30隊，最新完成例行賽為2026-04-12，明確接續2025–26，並非10月已有當季比賽。本次L7/L14完整日期窗口分别从2026-10-03／09-26起，至10-10（不含）止，皆無當季例行賽樣本。

程式證據：[utils.py來源／期間／逐場](https://github.com/fantasyorgcat/fantasyorgcat.github.io/blob/906579ff04e09bf68b25bfc95799c581f9e49f5b/utils.py#L15)、[球員資料欄位](https://github.com/fantasyorgcat/fantasyorgcat.github.io/blob/906579ff04e09bf68b25bfc95799c581f9e49f5b/utils.py#L191)、[gamelog與recent聚合](https://github.com/fantasyorgcat/fantasyorgcat.github.io/blob/906579ff04e09bf68b25bfc95799c581f9e49f5b/utils.py#L231)、[schedule_tools.js](https://github.com/fantasyorgcat/fantasyorgcat.github.io/blob/906579ff04e09bf68b25bfc95799c581f9e49f5b/schedule_tools.js)、[產生與比較](https://github.com/fantasyorgcat/fantasyorgcat.github.io/blob/906579ff04e09bf68b25bfc95799c581f9e49f5b/generate_report.py#L108)。

`read_json`最多三次讀取，對暫時性連線／429／5xx退避重試。沒有改讀另一家賽程供應商、假資料或固定舊賽季的fallback。失敗會停止產生／發布，留下上次有效報告。本季季前沒有例行賽統計時，UI預設顯示Last Season；本季/L7/L14仍為缺值，不把上季複製成當季。PBP防守不足10場的跨季接續是另一個明確fallback。

## 比賽日期與 fantasy matchup period

NBA比賽事件是一場實際比賽；fantasy period是聯盟把哪些日期合併計分。兩者不同，平台週號不是同一把尺。美東晚間比賽在台北通常是隔天，夏令時間影響時鐘顯示；來源更新時點、Cup待排場與延賽也會造成日程畫面不同。Yahoo／ESPN私人聯盟還可能自訂季後賽與matchup期間，不能只看NBA星期幾推回官方週號。

當前正式main的`fantasy_periods.official_platform_mapping=false`，只有本站美東日曆週與自訂日期：首場當季例行賽所在週為Week1，週一至週日，跨年連續，換季重設；目前25週。近期第一個快捷則是產生當日起至週日，可能不足7天。日期起訖含迄日；L7/L14統計另外取美東今天以前完整7／14日 `[today-N,today)`，與選擇賽程週獨立。

**本次草稿新增**經實讀的 [Yahoo 2026–27 Game Dates](https://basketball.fantasysports.yahoo.com/nba/gamedates) 公開預設23週（2026-10-10核對），並把明確日期寫入JSON。Yahoo W1是10/20–25，而NBA W1是10/19–25；Yahoo W7是11/30–12/13，W17是2/15–28；W10跨年12/28–1/3；Yahoo預設Fantasy季後賽W20–22為3/15–4/4，最後W23至4/11。這些是Fantasy季後賽日期，不是NBA季後賽比賽清單。Yahoo W8對應NBA W9的日期，不能切換時保留相同數字。

ESPN官方 [Standard Leagues regular/playoff schedule help](https://support.espn.com/hc/en-us/articles/360004139952-Regular-Season-and-Playoffs-Schedule-in-Standard-Leagues) 是一般规则，不能据此推造2026–27 Cup／明星賽長週；本次未取得可核實完整當季表，因此按鈕停用「待核」。NBA按鈕明確標示本站美東賽程週，沒有冒稱NBA官方Fantasy計分週。Yahoo公開表亦不代表某個私人聯盟的真正設定。[Yahoo Fantasy API](https://sports.yahoo.com/developer/docs/)提供game weeks／league settings等路徑，但需要OAuth；本次不新增。

## PR、TO與百分比的算法／局限

[PR與Rank程式](https://github.com/fantasyorgcat/fantasyorgcat.github.io/blob/906579ff04e09bf68b25bfc95799c581f9e49f5b/player_catalog.py#L6)：每個統計期完整GP>0母體，`pandas.rank(pct=True)`×100，等值PR採平均；TO反向，越少越高。PTS、REB、AST、3PM、STL、BLK、FG%、FT%、TO九個未四捨五入PR等權加總，不含MIN，Rank最高為1，同分1,2,2,4。缺任一纳入PR则无Rank；AVG与TOT的counting PR各自計算；百分比和MIN不变。球隊／比較篩選不重編，沒有最低GP樣本門檻。

這是聯盟球員相對排名，不是ROTO聯盟積分、對手勝率或points分數。等權PR會忽略投籃量及隊伍目前缺口；低出手高百分比可能被高估；低分鐘球員低TO也可能有高TO PR。已有TO資料缺值保留缺值、不補0。但近期FG/FT零出手目前會回填0；未來百分比影響工具應保留缺值與原因，別把未嘗試當成0%命中。

近期百分比確實是總命中／總出手，並非逐場百分比平均；全季百分比直接沿用ESPN。但FGM/A與FTM/A沒有完整保留在現有產物，不能用球員百分比直接平均成球隊百分比，也不能靠GP重建分母。百分比貢獻需用 `(隊伍made+新增made)/(隊伍attempts+新增attempts)`。現有counting整數總量仍保留，不能把「丟掉投籃分母」說成所有TOT都已丟失。

## 最小變更面與優先順序

估級是相對工程規模，非工時或速度保證；「小」是既有資料上的單一UI／計算，「中」需擴充資料契約與聚合，「大」涉及聯盟狀態、持久化或最佳化。

| 優先 | 功能／估級 | 最小資料與變更 | 需要新增資料源嗎 |
|---|---|---|---|
| 1 | 平台週／排程及低場次補人候選，小（本次先做週控制） | 現有event日期／狀態／球隊與已核實期間；同一期間渲染主表、比較及排程。候選可按剩餘／B2B／低場次日排序，明示仍須核對FA與陣容。 | 不需新廠商。Yahoo只加公開預設週表；ESPN完整週表需核實。 |
| 2 | 自訂類別偏好／punt ranking、counting points，小 | 現有九項PR與七項counting平均／總量；權重、方向、統計期間、GP／缺值提示。Points只對實際支援項目算 `Σw×stat`，保留TO負權重；不對FG%直接當counting總分。 | 不需新源。若聯盟有FGM/FGA、FTM/FTA、DD/TD等加分，先擴欄或逐場計算，不能假裝現有全支援。 |
| 3 | GP／小樣本與分鐘趨勢，小→中 | 現有GP與各期MIN均值先做期間比較／樣本提示；要逐場曲線需保存已有gamelog、event ID、取得時間及缺值理由。 | 同一ESPN逐場來源已可讀，不需先换廠商。歷史季逐場需另抓同源；不能仅由目前摘要画每日线。 |
| 4 | 分母補強與百分比貢獻，中 | 保存FGM/FGA/FTM/FTA（含季總量與近期），驗證made≤attempts與聚合對帳，零出手缺值；队伍基準made/attempts。近期已在記憶體有，季總量需核對ESPN實際回應欄位或同源逐場彙總。 | 先擴既有擷取與持久化。供應商理論提供不等於網站已保存；無需預設購買新API。 |
| 5 | H2H categories影響，中→大 | 真正matchup period、當前我隊／對手已計入總量與比率分母、選定categories／ties、剩餘合法先發與每日換人規則。先支持手動輸入；预测可使用明示的per-game×eligible future games假设。 | 球員基本統計夠做粗略候選比較；真實聯盟ledger／陣容需使用者輸入或後續授權league API。無法只用全聯盟PR算勝率。 |
| 6 | ROTO standings／GP pacing，中→大 | 全聯盟每隊已計入季總量、百分比分母、有效隊數、同分規則、各位置／全隊GP用量與上限、最低出手限制、未來可用先發。按各類別聯盟名次分配積分，再估邊際變化。 | 不必另買球員統計；需新增聯盟狀態輸入／來源。現有賽程場數不是ROTO已用GP，球員季總量不是Fantasy已計入總量。 |
| 7 | 合法streamer／先發最佳化，大 | 候選FA／waiver狀態、平台位置資格、健康、日名額、锁定时间、增員次數／交易／FAAB规则、上限與目標函数；建立球員ID對照及constraint model。 | 需要真實聯盟與资格／伤病资料（手動亦可）；再選可授權可維護的來源。這些不是目前ESPN roster摘要或PBP防守已有的欄位。 |

既有資料先做的核心順序為 **賽程 → 補人低場次日 → 自訂排名 → 分母／聯盟ledger → H2H／ROTO**。完整傷病、Fantasy位置、持有／FA、lineup與usage的來源不在目前產物，若產品真的要用，才核實新來源或聯盟授權；不因補保存逐場資料就引入付費服務。

## 載入負擔與本次邊界

當前main `index.html` 實際33,074,512 bytes（約33.1MB，31.5MiB）。本次移除額外整季球員HTML，平台與自訂共用動態表，不另輸出23份Yahoo球員表。相同605人／578上季、9事件的隔離fixture，修改前30,165,745 bytes、修改後24,166,200 bytes，减少5,999,545 bytes（約19.9%）；這只證明該fixture的產物較小，不是正式再生大小或瀏覽器速度保證。沒有無關重構。

草稿只更改來源程式、明確Yahoo日期、說明與本地驗證。正式`index.html`／`data_snapshot.json`維持`906579f`。原workflow沒有PR測試trigger，本輪測試由雲端executor本地跑，未dispatch、merge或deploy。要上線仍须審閱草稿，再由既有授權真資料產生流程發佈並驗收實際站點。
