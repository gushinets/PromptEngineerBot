# Requirements Document

## Introduction

This feature involves refactoring the codebase to move all hardcoded string messages from `src/bot_handler.py` and `src/email_flow.py` to the centralized `src/messages.py` file, following the existing internationalization pattern. This will improve code maintainability, consistency, and make it easier to manage translations.

## Requirements

### Requirement 1

**User Story:** As a developer, I want all user-facing messages to be centralized in the messages module, so that I can easily manage translations and maintain consistency across the application.

#### Acceptance Criteria

1. WHEN reviewing the codebase THEN all hardcoded string messages in `src/bot_handler.py` SHALL be moved to `src/messages.py`
2. WHEN reviewing the codebase THEN all hardcoded string messages in `src/email_flow.py` SHALL be moved to `src/messages.py`
3. WHEN adding new messages to `src/messages.py` THEN they SHALL follow the existing internationalization pattern using the `_()` helper function
4. WHEN adding new messages THEN they SHALL include both Russian and English translations

### Requirement 2

**User Story:** As a developer, I want consistent naming conventions for message constants, so that I can easily identify and use the appropriate messages in the code.

#### Acceptance Criteria

1. WHEN creating new message constants THEN they SHALL follow the existing naming pattern (e.g., `ERROR_*`, `SUCCESS_*`, `INFO_*`)
2. WHEN creating error message constants THEN they SHALL start with `ERROR_` prefix
3. WHEN creating success message constants THEN they SHALL start with `SUCCESS_` or use descriptive names
4. WHEN creating informational message constants THEN they SHALL use descriptive names that clearly indicate their purpose

### Requirement 3

**User Story:** As a developer, I want all message references in the code to use the centralized constants, so that there are no hardcoded strings remaining in the handler files.

#### Acceptance Criteria

1. WHEN calling `_safe_reply()` in `src/bot_handler.py` THEN it SHALL use message constants from `src/messages.py` instead of hardcoded strings
2. WHEN calling `_safe_reply()` in `src/email_flow.py` THEN it SHALL use message constants from `src/messages.py` instead of hardcoded strings
3. WHEN the refactoring is complete THEN there SHALL be no hardcoded user-facing strings in `src/bot_handler.py`
4. WHEN the refactoring is complete THEN there SHALL be no hardcoded user-facing strings in `src/email_flow.py`

### Requirement 4

**User Story:** As a developer, I want proper imports to be added to the handler files, so that the new message constants are available for use.

#### Acceptance Criteria

1. WHEN new message constants are created THEN they SHALL be added to the import statements in `src/bot_handler.py`
2. WHEN new message constants are created THEN they SHALL be added to the import statements in `src/email_flow.py`
3. WHEN imports are updated THEN they SHALL maintain alphabetical ordering within the messages import block
4. WHEN imports are updated THEN unused message imports SHALL be removed

### Requirement 5

**User Story:** As a developer, I want the existing functionality to remain unchanged, so that the refactoring doesn't break any existing features.

#### Acceptance Criteria

1. WHEN the refactoring is complete THEN all existing bot functionality SHALL work exactly as before
2. WHEN messages are displayed to users THEN they SHALL show the same text as before the refactoring
3. WHEN the bot is in Russian mode THEN it SHALL display Russian messages
4. WHEN the bot is in English mode THEN it SHALL display English messages (if language is changed)