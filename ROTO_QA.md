# ROTO與固定表頭整包驗收｜2026-10-14

接續既有`fix/sticky-table-headers`，保留b4e072d固定表頭及既有ROTO UI。此文件記錄部署前的可審查版本。PR #5已建立但未合併；自動核准審查指出可驗證指示尚未授權merge／部署，因此停止發布，正式網站未變更，沒有部署或正式頁新版本驗證證據。沒有改其他投資專案、登入、費用、帳密或存取／分享設定。

## 真實來源與精確覆蓋

來源是合法交付的 **BoxScore Lab 2025–26例行賽二手整理**，CC BY4.0；不是官方全表逐列驗證。頁面／repo source manifest保留署名、授權、來源URL、build字串與修改說明。

CSV實際95,924 bytes、582列、32欄；SHA256：`629839481dcb087aac9aa27f97fc1ef355cd93bc11e561b598ad680c38e446ee`。Library附件下載輔助程式未成功，但同一已授權檔案的native內容可讀；只去除讀取器產生的index欄，得到的UTF8/LF原始bytes與指定大小／SHA完全一致，再套用Library來源metadata。沒有重試任何被拒體育URL，也沒有以近似轉換替代hash驗證。

全582列同季、GP>0且≤82，必要總量為非負整數、made≤attempt、`PTS=2FGM+3PM+FTM`全通過；完整姓名與保守正規化姓名各582唯一。GP、七項、四個投籃量及平均分鐘均整套採同一CSV；不拼接舊七項與新分母、不使用rounded百分比重建出手。

| 覆蓋項目 | 精確數量／規則 |
| --- | --- |
| 現有首頁候選 | 610 ESPN ID，不是上季benchmark分母 |
| 唯一映射 | 481；保守完整姓名480，加Bobby Portis的明確suffix alias1 |
| 可與舊上季GP／七項比對 | 479，全項一致，0個差異 |
| 舊catalog缺實績、新來源有資料 | Noa Essengue／Chucky Hepburn2位，使用同份來源完整實績 |
| 來源無適用資料／未匹配 | 129，保留unknown；不稱全部是新秀或確定0場 |
| 姓名歧義 | 0；如果出現將保留unknown、另報數，不猜配 |
| 來源僅用於benchmark、未映射至當前名單 | 101，仍為同季參考群的一部分 |
| 固定benchmark母體 | 本來源582位；不強湊舊ESPN578，也不要求610候選都具上季資料 |
| 宣告衝突 | Jabari Smith Jr.1位FGA：BoxScore Lab975／父端RealGM核對974，未裁定，FGA與其FG%unknown；其他同來源欄位保留 |
| 完整原始投籃量／宣告未知 | 581人完整、1筆FGA未知；19人真實FTA=0，比率未知，不當0% |

Bobby alias僅在GP及七項整數總量完全一致時採用，從不廣泛刪除Jr/III或模糊猜配。資料沒有NBA PLAYER_ID；搜尋／保存仍使用原ESPN ID。benchmark使用穩定的發布者姓名ID，並非冒稱官方ID。來源last team只是標示；Harden70場已含44LAC+26CLE，Kuminga36場已含20GSW+16ATL，不再疊加stint。

父端六人RealGM計數抽查與轉隊合計證據保留在manifest，清楚標示外部研究與非官方全表驗證。原始CSV中的Jabari975未改；只在計算衍生檔中將FGA標null及保留兩個來源值／原因。

## 計算與保存保持原設計

- 上季總量加總真實計數，FG／FT為Σmade/Σattempt。
- 每人1場合計先各自除GP，再合計計數／made／attempt；不平均球員百分比，沒有混合不同單位。
- 輸入缺值或零出手保持unknown；原陣容、對手及多人模擬最多三組，原名單不被模擬改寫，可重設。
- 計數圖值取每員平均貢獻，相對固定參考均值／population SD取50+15z；TO反向、0–100截斷。FG／FT的均值及SD按同口徑出手加權。不是百分位、新季預測或真實聯盟積分。
- reference完整records、內容hash、各軸有效樣本可重現；選名單不改尺，Jabari不確定FG項排除於該軸基準。
- 命名保存用新本地key，沒有登入／私人聯盟；格式損壞不覆寫、停用時仍可編輯，舊儲存不碰。

## 管線與發布gate

`roto_boxscore.py`只讀已核archive，不自行網搜或重試拒絕URL。首頁generator在真正報告時使用該來源；隔離fixture明確UI TEST ONLY。每日工作仍用原權限，只新增相同資料契約／數學測試與ROTO輸出提交。換季需要新、合法且核過的資料，不能把2025–26改名成下一季。

gate重新從已核CSV、manifest與待發布首頁catalog完整重建ROTO資料，逐字／數值比對來源、映射、未知、benchmark與provenance。已宣告的129不適用與1衝突不是偽造零值，也不會造成永久阻擋；未宣告篡改會失敗。CSP只允許原本地程式／樣式資產，以及兩個明確署名／授權的外部anchor。Pages staging仍是allowlist，不含原始CSV／測試或QA檔案；原網站存取／分享設定不變。

## 驗證

60項Python source／defense／schedule／catalog／ROTO契約／BoxScore測試通過；Node加權FG／FT、GP口徑、TO、缺值、去重、替換／復原、保存讀回、固定基準及原隊排序通過。JS／Python syntax與diff check通過。

真實桌機1500×1000／手機390×844ROTO測試已通過：完整分母加權、最多三組、多人替換／復原、原隊不變、命名保存／讀回、未知球員、Jabari衝突、source署名、手機無頁面溢出、CSP無錯誤及首頁勾選新頁帶入。[結果](docs/roto/boxscore-browser-results.json)。合成完整九軸公式只做route隔離，不替代真實CSV。

原網頁下捲表頭／手機觸控、表頭欄位同步／排序、導航高度、動態長週及比較、原儀表板／球隊排序已通過。[表頭](docs/roto/boxscore-sticky-results.json)、[球隊](docs/roto/boxscore-team-results.json)、[儀表板](docs/roto/boxscore-dashboard-results.json)。[整季真實頁](docs/roto/boxscore-season-results.json)已逐一驗證NBA25／Yahoo23／ESPN24期間的日期、對手、排序和統計保持原值；[隔離賽程回歸](docs/roto/boxscore-schedule-results.json)桌機及手機已驗證跨年、長週、三平台來回、custom 1／7／14／31日、tipoff／foreground重算、無效區間，以及舊DataTable事件／jQuery資料釋放。各瀏覽器結果均無JS錯誤或失敗請求。

目前真實畫面：[桌機](docs/roto/boxscore-real-1500.png)、[手機圖](docs/roto/boxscore-real-390.png)、[手機九項表](docs/roto/boxscore-real-table-390.png)、[來源與限制](docs/roto/boxscore-real-top-390.png)。未驗iOS/Safari真機。

## 保留的來源限制

[先前來源錯誤](docs/roto/source-access.json)與[當時阻擋版本](docs/roto/blocked-qa-2026-10-14.md)保留作歷史證據。NBA／CBS／ESPN是本環境CONNECT代理403；BRef工具報403但無原始header以歸因origin。沒有再請求這些來源。新來源合法artifact不等於解除那些URL限制；不宣稱NBA官方全表核對。正式頁應顯示BoxScore Lab二手來源、Jabari未知及GP／分鐘／覆蓋限制，不能包裝成預測或真正ROTO積分。
