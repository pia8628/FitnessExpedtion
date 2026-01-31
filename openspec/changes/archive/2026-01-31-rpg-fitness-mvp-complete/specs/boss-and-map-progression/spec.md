## ADDED Requirements

### Requirement: Boss entry after map weeks
The system SHALL enter the boss phase when the current map week count reaches its limit.

#### Scenario: Map weeks completed
- **WHEN** the week count reaches the map's configured total weeks
- **THEN** the system marks the game as in boss phase and blocks new weekly draws

### Requirement: Boss contribution tracking
The system SHALL allow each player to update their boss contribution and SHALL display team progress.

#### Scenario: Player updates contribution
- **WHEN** a player submits a boss contribution update
- **THEN** the system records the update, refreshes the boss progress view, and checks whether boss completion criteria are met

#### Scenario: Team views boss status
- **WHEN** any player opens the boss status view
- **THEN** the system shows per-player contribution and overall completion

### Requirement: Boss resolution choice
The system SHALL require a choice to advance or replay after boss completion.

#### Scenario: Boss completed
- **WHEN** boss completion criteria are met
- **THEN** the system allocates experience points to players based on their contributions and prompts to advance to the next map or replay the current map

### Requirement: Advance to next map
The system SHALL move to the next map and reset week to 1 when advancing.

#### Scenario: Advance selected
- **WHEN** the team selects advance
- **THEN** the system sets the map to the next map and resets the week to 1

### Requirement: Replay current map
The system SHALL reset map progress and week to 1 when replay is selected.

#### Scenario: Replay selected
- **WHEN** the team selects replay
- **THEN** the system resets map progress and sets the week to 1 while keeping the same map

### Requirement: Map and week consistency
The system SHALL keep map and week values consistent across dashboard, weekly flow, and logs.

#### Scenario: Consistent display after decision
- **WHEN** a boss resolution choice is applied
- **THEN** the dashboard and weekly flow show the same map and week values as the stored state
