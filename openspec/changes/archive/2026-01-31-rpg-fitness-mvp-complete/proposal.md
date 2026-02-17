## Why
目前 MVP 已有核心流程與部分 UI，但仍有多個關鍵功能缺口（事件觸發、死亡/懲罰、BOSS/地圖、遊戲建立/進入）。缺口導致流程無法完整跑完一週，且無法對外測試。需以 openspec 完整補齊規格與落地實作，讓 MVP 可實際運行與驗證。

## What Changes
- 補齊「事件觸發/執行流程」規格與實作，包含條件式事件、被動觸發與記錄。
- 完成 HP 歸零/死亡與懲罰流程（包含觸發條件、效果、回復與紀錄）。
- 建立「創建遊戲 / 進入遊戲」頁面與流程，對接既有資料結構與角色初始化。
- 完善 BOSS/地圖系統（週數、進度、重玩/前進選擇與結算一致性）。
- 針對現有 UI 與資料層做必要調整，確保流程一致且可測試。

## Capabilities

### New Capabilities
- `game-setup-and-entry`: 創建新遊戲與進入既有遊戲流程（角色/職業/人數/初始化）。
- `death-and-penalty-flow`: HP 歸零後的懲罰事件、狀態更新與復原規則。

### Modified Capabilities
- `boss-and-map-progression`: BOSS 週結算、地圖進度與選擇流程一致化。
- `event-trigger-and-resolution`: 事件觸發條件、被動觸發點與結算紀錄完善。

## Impact
- 影響 UI：`program/app.py`、`program/ui/dashboard.py`、`program/ui/tasks.py`、`program/ui/skills_view.py`、`program/ui/logs.py`、`program/ui/draws.py`
- 影響 Domain：`program/domain/logic.py`、`program/domain/effects.py`、`program/domain/skills.py`
- 影響 Data：`program/data/repositories.py`、`program/data/sheets_client.py`
- 影響 Google Sheet：首頁、角色狀態、任務列表、紀錄頁面、地圖/BOSS 表
