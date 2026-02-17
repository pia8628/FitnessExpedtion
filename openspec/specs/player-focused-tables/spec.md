## Purpose

TBD: Define player-focused table presentation rules and visible columns.

## Requirements

### Requirement: Player-focused columns（玩家視角欄位）
The UI SHALL display only player-relevant columns in tables and lists.
表格與列表僅顯示玩家需要的欄位。

#### Scenario: Table column reduction（欄位精簡）
- **WHEN** a task or status table is rendered
- **THEN** columns are limited to player-readable fields and exclude internal IDs or system metadata

### Requirement: Emphasize action-critical fields（強調可行動欄位）
The UI SHALL prioritize fields needed for player decisions, such as name, status, deadline, and rewards.
優先顯示可幫助玩家判斷/操作的欄位（名稱、狀態、期限、獎勵）。

#### Scenario: Actionable fields visible（可行動資訊可見）
- **WHEN** a table is shown
- **THEN** the visible columns include the actionable fields required to decide or complete a task

### Requirement: Consistent row readability（可讀性一致）
Tables SHALL use spacing and alignment consistent with the adventure journal theme to improve readability.
表格行距與對齊需符合冒險手帳風格，提升可讀性。

#### Scenario: Row styling（列樣式）
- **WHEN** multiple rows are displayed
- **THEN** row spacing and alignment make it easy to scan without visual clutter
