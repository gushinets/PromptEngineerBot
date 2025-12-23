# Requirements Document

## Introduction

This feature fixes a critical bug in the session tracking system where successfully completed sessions can be incorrectly overwritten to "unsuccessful" status when users click the "Reset" button after receiving their optimized prompts. This issue affects both the regular chat flow and the email flow, and has significant implications for:

1. **Analytics accuracy**: Session success rates are incorrectly reported
2. **Future payment system**: Users could be incorrectly charged or not charged for optimizations they received

The fix implements a "terminal state protection" pattern where sessions that have already reached a terminal state (successful or unsuccessful) cannot be modified by subsequent reset operations.

## Glossary

- **Terminal State**: A session status that represents the final outcome of a session. Terminal states are `successful` and `unsuccessful`.
- **Non-Terminal State**: A session status that indicates the session is still active. The only non-terminal state is `in_progress`.
- **Session Status Protection**: The mechanism that prevents terminal states from being overwritten by reset operations.
- **Defense-in-Depth**: A security/reliability pattern where protection is implemented at multiple layers to ensure robustness.

## Requirements

### Requirement 1: SessionService Reset Protection

**User Story:** As a system administrator, I want the SessionService to protect terminal session states from being overwritten, so that session analytics remain accurate.

#### Acceptance Criteria

1. WHEN `reset_session()` is called on a session with status "successful" THEN the System SHALL NOT modify the session status
2. WHEN `reset_session()` is called on a session with status "unsuccessful" THEN the System SHALL NOT modify the session status
3. WHEN `reset_session()` is called on a session with status "in_progress" THEN the System SHALL update the session status to "unsuccessful"
4. WHEN `reset_session()` is called on a terminal-state session THEN the System SHALL log a debug message indicating the skip
5. WHEN `reset_session()` is called on a terminal-state session THEN the System SHALL return the existing session object without modification

### Requirement 2: BotHandler Reset Protection

**User Story:** As a developer, I want the BotHandler to check session status before attempting reset, so that unnecessary database operations are avoided and intent is clearly logged.

#### Acceptance Criteria

1. WHEN `_reset_current_session()` is called THEN the System SHALL first retrieve the current session status
2. WHEN the session status is "successful" THEN the System SHALL skip the reset operation and log an info message
3. WHEN the session status is "unsuccessful" THEN the System SHALL skip the reset operation and log an info message
4. WHEN the session status is "in_progress" THEN the System SHALL proceed with the reset operation
5. WHEN no session exists for the user THEN the System SHALL skip the reset operation gracefully

### Requirement 3: Email Flow Compatibility

**User Story:** As a user, I want my email flow sessions to be protected from accidental status overwrites, so that my successful email deliveries are correctly tracked.

#### Acceptance Criteria

1. WHEN an email is successfully sent and session is marked "successful" THEN subsequent reset button clicks SHALL NOT change the session status
2. WHEN an email fails and session is marked "unsuccessful" THEN subsequent reset button clicks SHALL NOT change the session status
3. WHEN the email flow is in progress and user clicks reset THEN the System SHALL mark the session as "unsuccessful"

### Requirement 4: Graceful Degradation

**User Story:** As a user, I want the reset button to always work for resetting my conversation, even if session status protection encounters errors.

#### Acceptance Criteria

1. WHEN session status check fails due to database error THEN the System SHALL log the error and proceed with state reset
2. WHEN session status protection is applied THEN the System SHALL NOT display any error messages to the user
3. WHEN session tracking is unavailable THEN the System SHALL proceed with normal state reset without errors

### Requirement 5: Logging and Observability

**User Story:** As a system administrator, I want clear logging of session status protection events, so that I can monitor and debug the system.

#### Acceptance Criteria

1. WHEN a session reset is skipped due to terminal state THEN the System SHALL log the session_id, current status, and reason for skip
2. WHEN a session reset proceeds normally THEN the System SHALL log the session_id and status change
3. WHEN session status protection encounters an error THEN the System SHALL log the error with full context
