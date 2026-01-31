## ADDED Requirements

### Requirement: HP floor and penalty trigger
The system SHALL clamp HP at 0 on task failure that would reduce HP to 0 or below, and trigger the penalty flow when HP reaches 0.

#### Scenario: HP would drop below zero on failure
- **WHEN** a task failure would reduce HP below 0
- **THEN** the system sets HP to 0 and triggers the penalty flow

### Requirement: Fixed penalty rule
The system SHALL apply a fixed penalty of two consecutive weeks of MP set to 0 when a player reaches HP 0.

#### Scenario: Penalty applied on HP 0
- **WHEN** a player reaches HP 0
- **THEN** the system sets the player's penalty counter to 2 weeks and sets current MP to 0

### Requirement: Next-week revive with half HP
The system SHALL revive a player in the next week with HP set to half of their max HP after reaching HP 0.

#### Scenario: Weekly reset after death
- **WHEN** the weekly reset runs and the player is marked as having reached HP 0 in the prior week
- **THEN** the system revives the player and sets current HP to half of max HP (rounded down)

### Requirement: Weekly penalty countdown
The system SHALL decrement the penalty counter at each weekly reset and enforce MP at 0 while the counter is greater than 0.

#### Scenario: Weekly reset during penalty
- **WHEN** the weekly reset runs and a player penalty counter is greater than 0
- **THEN** the system decrements the counter by 1 and keeps MP at 0

#### Scenario: Penalty ends
- **WHEN** the weekly reset runs and the player penalty counter reaches 0
- **THEN** the system allows normal MP recovery in subsequent weeks

### Requirement: Penalty visibility and logging
The system SHALL display penalty status and record penalty events in the log.

#### Scenario: Penalty applied
- **WHEN** a penalty is triggered
- **THEN** the system records the event with reason and remaining weeks

#### Scenario: Penalty displayed
- **WHEN** a player views their status during penalty
- **THEN** the UI shows remaining penalty weeks and MP locked at 0
