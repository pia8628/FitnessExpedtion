# Codex 開發紀錄

## 2026-01-10
- 閱讀專案檔案與 Excel `RPG運動冒險系統.xlsx`，確認各工作表結構（首頁、角色狀態、任務列表、技能狀態、事件/怪物表、紀錄、等級、職業技能、清單）。
- 更新 `SDD_codex.md`：加入 Task List、專案架構（模組職責、流程切面），修正編碼亂碼。
- 建立虛擬環境 `.venv`，升級 pip，安裝主要套件：`streamlit`, `gspread`, `google-auth`, `python-dotenv`（含相依 pandas/pyarrow 等）。
- 建置專案骨架：
- 入口/UI：`app.py`、`ui/{dashboard,tasks,skills_view,logs}.py`
  - 設定：`config/settings.py`（讀 .env：SHEET_ID、TIMEZONE、SERVICE_ACCOUNT）
  - 資料層：`data/sheets_client.py`（gspread 封裝，含 safe_update stub）、`data/repositories.py`（工作表 CRUD stub）
  - Domain：`domain/{models,effects,skills,logic}.py`（模型解析、事件/技能 handler stub、核心流程 stub）
  - Utils：`utils/{time,concurrency,validators}.py`
- 尚未完成：事件/技能實作、任務結算流程、與 Sheet 的行索引/版本欄位對應；待下一步填寫。***

### 後續同日進度
- 加強資料層：`sheets_client.py` 增 header 讀取、safe_update；`repositories.py` 依表頭動態映射，提供任務/玩家狀態更新與日誌追加；`settings.py` 支援 .env 載入。
- Domain 進展：`logic.py` 任務完成/失敗雛形（寫回與日誌）；`skills.py` 新增 SkillContext 並要求 context；`logic.use_skill` 接 SkillContext。
- 下一步：填入事件/技能實作、任務結算完整規則，補 requirements/.env 範本，完善 repositories 的版本欄處理。

### 補充
- `domain/effects.py` 事件處理器雛形（ALL_MP+1、ALL_HP+2、戶外條件加 EXP、時限 -1 等）；未知代碼 no-op。
- `domain/skills.py` 增基本主動技能處理：急救/治療扣 MP 並回 HP；延長時限標記 extra_days；弱化怪物降一級；遠距支援標記 shield_fail；合體技僅扣 MP 其餘由結算處理。SkillContext 強制使用。
- 新增 `requirements.txt`、`.env.example`，列出必要套件與環境變數範本。
- `domain/logic.py`：失敗時若有 shield_fail 不扣 HP（並清除旗標）；完成任務時增加 EXP 後呼叫 _check_level_up（待實作）；_check_level_up 留 TODO。
- `data/repositories.py` 新增 `get_level_table` 以讀取等級資料表。
- `domain/logic.py` 的 `_check_level_up` 改用等級表累計規則（從表抓累計上限增量與所需 EXP），達門檻則調整上限並回滿。
- `utils/time.py` 增 Excel 序號轉日期；`logic.mark_overdue_tasks` 初步逾時判斷（截止日 + extra_days/time_bonus → fail_task），仍待綁定 UI/呼叫點。
- 對接 Google Sheet 連線設定：建立 `program/.env`，加入 `program/.gitignore` 排除金鑰與虛擬環境；修正 `.env` 讀取路徑與 BOM 問題，避免 `SHEET_ID` 讀不到。
- 補齊資料模型與表頭對應：支援事件/怪物/技能狀態、地圖表、BOSS 表解析；怪物名稱/難度欄位增加變體對應。
- 抽卡與回合流程：新增「週抽卡」頁面，事件與怪物抽卡自任務頁分離，依地圖機率加權並依地圖難度抽 N 隻；回合（週數）改為自動遞增（依紀錄最大週數 +1）。
- 任務結算更新：完成/失敗會寫入紀錄（擊敗怪物/任務失敗）、計算 EXP、並從任務列表刪除，避免重複執行。
- 技能流程更新：技能顯示名稱/描述、依玩家可用技能過濾，使用後扣次數並寫回；MP 消耗可讀取技能狀態表。

### 已完成
- 串接地圖/回合流程：週抽卡頁顯示地圖/ BOSS 資訊，依「地圖難度」為每位玩家抽 N 隻怪物，並依 Easy/Medium/Hard 機率加權。
- 回合自動推進：以紀錄表最大週數 +1 作為本週回合，避免手動選回合。
- 週初始化流程：抽事件 + 抽怪物 + 重置技能次數（依技能狀態表「每週可用總次數」與「重置規則」）。
- 事件顯示修正：事件名稱（含事件類型）、事件敘述與說明顯示在週抽卡頁。
- 任務流程修正：完成/失敗皆寫紀錄並刪除任務，避免重複執行。
- 技能頁強化：顯示技能描述、顯示使用者/目標 HP/MP、減少重讀造成 429；MP 消耗與剩餘次數寫回技能狀態表。
- 低配額問題調整：重置技能改為一次讀取 + 批量更新，減少讀取次數。
- 首頁同步：週初始化後寫回 `首頁!C2`（目前週數）與 `首頁!G2`（地圖編號）。
- 修復 `data/repositories.py` 亂碼問題，確保工作表名稱與欄位名稱正常。

### 未完成 / 待確認
- 429 讀取配額仍可能在高頻操作時出現；若仍困擾可加 30 秒快取。
- 是否需要「手動抽事件/怪物」也同步寫回首頁（C2/G2）。
- 抽怪物前是否要清掉上一週未完成任務（規則未定）。
- BOSS 週結算流程尚未實作（累計運動時數、指定任務、額外 EXP、最後一擊獎勵）。
- 被動技能觸發與事件條件（戶外、合體技、額外運動等）尚未接入任務結算。

### 重要設定 / 備註
- 服務帳號金鑰已搬到 `C:\Users\user\service-account.json`，`.env` 內 `GOOGLE_APPLICATION_CREDENTIALS` 指向該路徑。
- `.env` 必須無 BOM，否則 `SHEET_ID` 讀不到。

## 2026-01-11
- 週結算流程與 BOSS 流程調整：BOSS 結算後顯示結果、地圖選擇（進入下一張/重玩），並修正 BOSS 結算後卡住週結算的狀況。
- 地圖進度與 BOSS 判定修正：重玩地圖可重置進度，地圖進度統計排除重置前紀錄。
- 週結算與抽卡修正：事件影響抽怪物（難度提升/時限縮短/重抽/選擇事件），並修正抽卡後任務未同步與只抽到單一玩家的問題。
- UI/頁面更新：任務頁事件任務依本週事件顯示；紀錄頁新增週數分組與遊玩總週數顯示；儀表板與週結算頁顯示 BOSS 狀態。
- 配額/讀取修正：首頁讀取改為表格快取，修正首頁更新與快取失效。
- 待處理：玩家升級與死亡流程尚未完整處理。
- 週結算與 BOSS 後續：BOSS 結算後新增地圖選擇（前進/重玩），重玩會重置進度並將首頁週數歸 1；BOSS 已結算後才能週結算。
- 被動技能觸發系統擴充：on_complete/on_fail/on_combo/on_support_used/on_supported_complete/on_rescued_complete 等集中處理；PrP001/PrP002 觸發邏輯改走被動觸發。
- 事件任務擴充：新增 EXTRA_WORKOUT_MVP_EXP+5 任務與 UI，REST_MP_RECOVERY_DISABLED 會阻擋戶外事件回 MP。
- 配額寫入改善：事件套用玩家改為批次寫入以降低 429 寫入配額。

### 待辦
- 補齊其餘事件代碼（REST_MP_RECOVERY_DISABLED、EXTRA_WORKOUT_MVP_EXP+5 之外）與觸發點。
- 完整 HP 歸零/死亡與懲罰流程（含 HP 歸零原因追蹤）。
- 檢查 BOSS 地圖選擇後的週數/地圖顯示一致性。

## 2026-01-27
- 新增 openspec change：`rpg-fitness-mvp-complete`，完成 proposal 與 design。
- proposal 強化：補齊 Capabilities（game-setup-and-entry、death-and-penalty-flow、boss-and-map-progression、event-trigger-and-resolution）與實際影響檔案路徑（`program/`）。
- design 決策：先進入遊戲才可看到內容；事件分成被動影響/任務式事件；HP 歸零固定懲罰；BOSS 結算後可前進或重玩且週數歸 1。
- specs 建立（4 份）：`game-setup-and-entry`、`death-and-penalty-flow`、`boss-and-map-progression`、`event-trigger-and-resolution`。
- 死亡懲罰規則補充：任務失敗扣 HP 至 0 觸發；下一回合復活，HP 為上限一半；啟動連續兩週 MP 歸零懲罰。
- BOSS 規格文字修正：貢獻更新需檢查完成條件；完成後依貢獻分配 EXP 並提示前進/重玩。
