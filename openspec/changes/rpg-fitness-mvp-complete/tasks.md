## 1. Entry Gate And Game Setup

- [ ] 1.1 Add entry-state gating so only setup/entry pages are available before a player enters
- [ ] 1.2 Build game creation flow with 1–5 players and required name/class validation
- [ ] 1.3 Implement enter-existing-game flow with player selection validation
- [ ] 1.4 Initialize game state on creation (player stats, week=1, map=first, weekly skill counters)

## 2. Event Classification And Resolution

- [ ] 2.1 Extend event data model to classify events as passive vs task-based
- [ ] 2.2 Apply passive events once during weekly initialization and log application idempotently
- [ ] 2.3 List task-based events in a separate task section from monster tasks
- [ ] 2.4 Trigger task-based events after base task resolution and before level-up checks
- [ ] 2.5 Prevent duplicate task-based event application within the same week and log outcomes

## 3. Death And Penalty Flow

- [ ] 3.1 Clamp HP to 0 on failure, trigger penalty, and record penalty source in logs
- [ ] 3.2 Add penalty counter state (2 weeks) and enforce MP=0 while active
- [ ] 3.3 On weekly reset, revive dead players at half max HP and decrement penalty counter
- [ ] 3.4 Display penalty status and remaining weeks in player status UI

## 4. Boss And Map Progression

- [ ] 4.1 Detect boss phase when map week limit reached and block new weekly draws
- [ ] 4.2 Record per-player boss contributions and show team progress in UI
- [ ] 4.3 On boss completion, allocate EXP by contribution and prompt advance or replay
- [ ] 4.4 Advance: move to next map and reset week to 1
- [ ] 4.5 Replay: reset map progress and week to 1 on the same map
- [ ] 4.6 Keep map/week values consistent across dashboard, weekly flow, and logs

## 5. Verification

- [ ] 5.1 Manual flow check: entry gating, create/enter, and initialization
- [ ] 5.2 Manual flow check: passive/task-based events and idempotent logging
- [ ] 5.3 Manual flow check: HP 0 penalty, weekly revive, MP lock, and UI visibility
- [ ] 5.4 Manual flow check: boss completion, advance/replay, and map/week consistency
