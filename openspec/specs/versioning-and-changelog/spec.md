# Capability: versioning-and-changelog

## Purpose
TBD

## Requirements

### Requirement: Version display
The system SHALL display the current game version as `0.1.1 beta` in the UI.

#### Scenario: Version appears in UI
- **WHEN** a user opens any major page
- **THEN** the page shows the current version string `0.1.1 beta`

### Requirement: Changelog page
The system SHALL provide a "版本更新" page that lists version updates in reverse chronological order.

#### Scenario: Changelog page is accessible
- **WHEN** a user navigates to the "版本更新" page
- **THEN** the page displays the latest version entries first

### Requirement: Home image on entry page
The system SHALL display `ui/assets/home/home_image.png` on the game entry page.

#### Scenario: Entry page shows home image
- **WHEN** a user opens the game entry page
- **THEN** the home image is visible above the entry controls
