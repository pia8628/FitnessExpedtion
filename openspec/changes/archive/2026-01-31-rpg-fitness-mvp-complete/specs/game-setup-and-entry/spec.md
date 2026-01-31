## ADDED Requirements

### Requirement: Entry gate before game access
The system SHALL hide all in-game pages and data until a player completes game entry.

#### Scenario: Player has not entered a game
- **WHEN** the app loads without an active player session
- **THEN** only the game setup and entry views are available

#### Scenario: Player completes entry
- **WHEN** a player successfully selects or creates a game and enters
- **THEN** the in-game pages become available for that session

### Requirement: Create new game with validation
The system SHALL allow creating a new game with 1 to 5 players, each with a name and class, and SHALL validate required inputs.

#### Scenario: Missing name or class
- **WHEN** the user attempts to create a game with any missing player name or class
- **THEN** the system shows a validation error and blocks creation

#### Scenario: Player count out of range
- **WHEN** the user sets fewer than 1 or more than 5 players
- **THEN** the system blocks creation and shows a validation error

#### Scenario: Create game overwrites existing progress
- **WHEN** the user confirms creating a new game
- **THEN** the system resets existing progress and initializes a new game state

### Requirement: Enter existing game
The system SHALL allow selecting a player from existing roster to enter the game.

#### Scenario: No player selected
- **WHEN** the user attempts to enter without selecting a player
- **THEN** the system blocks entry and shows an error

#### Scenario: Player selected
- **WHEN** the user selects an existing player and confirms entry
- **THEN** the system enters the game using that player context

### Requirement: Initialize game state
The system SHALL initialize game state on creation, including player stats, week, map, and skill counters.

#### Scenario: New game created
- **WHEN** a new game is created
- **THEN** player HP/MP/EXP and level are set to defaults, week is set to 1, map is set to the first map, and weekly skill counters are reset

