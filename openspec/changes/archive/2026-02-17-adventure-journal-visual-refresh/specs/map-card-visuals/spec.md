## ADDED Requirements

### Requirement: Map card visual（地圖圖卡）
The UI SHALL display a map card as a primary visual element on the relevant page.
相關頁面需以地圖圖卡作為主要視覺元素。

#### Scenario: Map card presence（圖卡存在）
- **WHEN** the map or progression section is shown
- **THEN** a map card image is displayed with a title or label for the current map

### Requirement: Limited imagery scope（圖片範圍限制）
The UI SHALL only introduce map card imagery for this change, excluding monster and event cards.
本次僅加入地圖圖卡，怪物卡與事件卡暫不加入。

#### Scenario: Image scope enforcement（範圍控制）
- **WHEN** users view tasks or events
- **THEN** no monster or event card imagery is shown, only the map card is present

### Requirement: Consistent image styling（圖卡風格一致）
The map card image SHALL use the same rounded corners, padding, and warm-toned backdrop as other cards.
地圖圖卡需與卡片系統一致（圓角、留白、暖色底）。

#### Scenario: Image styling consistency（風格一致）
- **WHEN** the map card is rendered
- **THEN** its styling matches the adventure journal card system
