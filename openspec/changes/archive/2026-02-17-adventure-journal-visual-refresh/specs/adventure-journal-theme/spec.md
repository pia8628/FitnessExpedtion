## ADDED Requirements

### Requirement: Adventure journal visual system（冒險手帳視覺系統）
The UI SHALL apply a consistent "adventure journal" visual theme across all pages.
UI 必須在所有頁面套用一致的「冒險手帳」視覺主題。

#### Scenario: Consistent theme application（一致主題呈現）
- **WHEN** a user navigates across pages
- **THEN** headers, cards, tables, and buttons share the same visual language and layout rhythm

### Requirement: Typography pairing（字體搭配）
The UI SHALL use a serif display font for headings and a legible sans-serif font for body text.
標題使用襯線展示字體，內文使用清晰易讀的無襯線字體。

#### Scenario: Heading and body typography（標題/內文字體）
- **WHEN** headings and body content are rendered
- **THEN** headings appear in the display font and body text appears in the sans-serif font with clear hierarchy

### Requirement: Core color system with accent highlights（核心配色與重點色）
The UI SHALL use a warm neutral base palette with bright orange and coral red as accent highlights.
基底為暖色中性調，亮橘與珊瑚紅作為重點點綴色。

#### Scenario: Accent usage（重點色使用）
- **WHEN** primary actions, key labels, or status highlights are shown
- **THEN** bright orange or coral red is used as the accent color while base backgrounds remain warm and soft

### Requirement: Card-based layout（卡片化版面）
The UI SHALL present key content in card-like containers with padding, border radius, and subtle separation from the background.
關鍵內容以卡片容器呈現，包含留白、圓角與柔和分隔。

#### Scenario: Card presentation（卡片呈現）
- **WHEN** tasks, status, or event summaries are displayed
- **THEN** they appear in card containers with consistent spacing and visual separation

### Requirement: Copy terminology consistency（用語一致）
The UI SHALL use the term "回合" instead of "週" in user-facing copy.
介面文案統一使用「回合」，不使用「週」。

#### Scenario: Terminology update（用語更新）
- **WHEN** any page displays time progression labels
- **THEN** the label uses "回合" consistently
