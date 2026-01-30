## ADDED Requirements

### Requirement: Event classification
The system SHALL classify events as passive effects or task-based events.

#### Scenario: Event has a classification
- **WHEN** an event is loaded for the week
- **THEN** the system identifies it as passive or task-based

### Requirement: Passive event application
The system SHALL apply passive event effects once at weekly initialization.

#### Scenario: Passive event at week start
- **WHEN** the weekly initialization runs with a passive event
- **THEN** the system applies its effects to all relevant players exactly once

### Requirement: Task-based event listing
The system SHALL list task-based events in a dedicated task section separate from monster tasks.

#### Scenario: Task event appears in task list
- **WHEN** the weekly tasks view is shown and the event is task-based
- **THEN** the event appears in a separate task list section from monster tasks

### Requirement: Task-based event triggering
The system SHALL trigger a task-based event when its condition is met and SHALL apply its reward.

#### Scenario: First monster defeated
- **WHEN** the first monster task of the week is completed by a player
- **THEN** the system grants the configured bonus to that player and marks the event as completed

### Requirement: Resolution order for task-based events
The system SHALL apply task-based event rewards after the base task resolution and before level-up checks.

#### Scenario: Task completion with event reward
- **WHEN** a task completion triggers a task-based event reward
- **THEN** the system applies base rewards, then event rewards, then evaluates level-up

### Requirement: Event logging and idempotency
The system SHALL log event application and SHALL prevent duplicate application within the same week.

#### Scenario: Event logged once
- **WHEN** an event effect is applied
- **THEN** the system writes a log entry with event code and affected player(s)

#### Scenario: Duplicate trigger attempt
- **WHEN** the same event condition is evaluated again in the same week
- **THEN** the system does not apply the effect a second time

