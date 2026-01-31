## 1. Entry Gate And Game Setup

- [x] 1.1 Add entry-state gating so only setup/entry pages are available before a player enters
- [x] 1.2 Build game creation flow with 1–5 players and required name/class validation
- [x] 1.3 Implement enter-existing-game flow with player selection validation
- [x] 1.4 Initialize game state on creation (player stats, week=1, map=first, weekly skill counters)

## 2. Event Classification And Resolution

- [x] 2.1 Extend event data model to classify events as passive vs task-based
- [x] 2.2 Apply passive events once during weekly initialization and log application idempotently
- [x] 2.3 List task-based events in a separate task section from monster tasks
- [x] 2.4 Trigger task-based events after base task resolution and before level-up checks
- [x] 2.5 Prevent duplicate task-based event application within the same week and log outcomes

## 3. Death And Penalty Flow

- [x] 3.1 Clamp HP to 0 on failure, trigger penalty, and record penalty source in logs
- [x] 3.2 Add penalty counter state (2 weeks) and enforce MP=0 while active
- [x] 3.3 On weekly reset, revive dead players at half max HP and decrement penalty counter
- [x] 3.4 Display penalty status and remaining weeks in player status UI

## 4. Boss And Map Progression

- [x] 4.1 Detect boss phase when map week limit reached and block new weekly draws
- [x] 4.2 Record per-player boss contributions and show team progress in UI
- [x] 4.3 On boss completion, allocate EXP by contribution and prompt advance or replay
- [x] 4.4 Advance: move to next map and reset week to 1
- [x] 4.5 Replay: reset map progress and week to 1 on the same map
- [x] 4.6 Keep map/week values consistent across dashboard, weekly flow, and logs

## 5. Verification

- [x] 5.1 Manual flow check: entry gating, create/enter, and initialization
  - 2026-01-31: verified OK after fixes (entry page, skill page, task flow).
- [x] 5.2 Manual flow check: passive/task-based events and idempotent logging
  - 2026-01-31: task-based event completes once; passive event EXP+3 OK.
- [x] 5.3 Manual flow check: HP 0 penalty, weekly revive, MP lock, and UI visibility
  - 2026-01-31: verified HP 0 triggers penalty weeks.
- [x] 5.4 Manual flow check: boss completion, advance/replay, and map/week consistency
  - 2026-01-31: verified OK after fixes (E01 -> E02).

## 6. Follow-up Fixes (from 2026-01-31 manual verification)

- [x] 6.1 Skill availability mismatch: skill page reports no active skills while status lists 急救/合體技.
  - 2026-01-31: fixed; skill page shows active skills.
- [x] 6.2 Weekly usage count mismatch: skill status shows unlimited uses but should be 1/week.
  - 2026-01-31: fixed; remaining uses read from weekly count.
- [x] 6.3 Task resolution lag: monster task remains "in progress" after first defeat; only ends after second defeat.
  - 2026-01-31: fixed; refresh and status update after completion.
- [x] 6.4 Boss map advance skips: after boss clear, map advances E01 -> E03 instead of E02.
  - 2026-01-31: fixed; next map uses map order.
