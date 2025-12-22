# Requirements Document

## Introduction

This feature extends the existing session tracking system to support the "Send 3 prompts to email" flow. When a user clicks the email delivery button, the system optimizes their prompt using all three methods (LYRA, CRAFT, GGL) and sends the results via email. Currently, this flow bypasses session tracking entirely. This enhancement ensures comprehensive metrics collection for the email flow including token usage, conversation history, optimization method tracking, and email delivery events.

**Key Design Decisions:**
- Single session per email flow with `optimization_method = "ALL"` to indicate multi-method optimization
- Token counts from all 3 LLM calls are aggregated into existing session token fields
- Single email event logged per email sent (not per method)
- Session marked "successful" only after email is successfully sent; "unsuccessful" if email fails
- Conversation history entries include optional `method` field to identify which optimization produced each response

**Reuse Strategy:**
The implementation maximizes reuse of existing SessionService methods:
- `set_optimization_method()` - reuse to set method to "ALL"
- `add_tokens()` - reuse for each of the 3 LLM calls (called 3 times)
- `add_message()` - extend with optional `method` parameter for conversation history
- `complete_session()` - reuse to mark session successful after email sent
- `reset_session()` - reuse to mark session unsuccessful if email fails
- `log_email_sent()` - reuse for email event logging

## Glossary

- **Email Flow**: The workflow triggered when user clicks "Send 3 prompts to email" button, which optimizes the prompt using all three methods and sends results via email
- **Multi-Method Optimization**: Running LYRA, CRAFT, and GGL optimizations on the same prompt in a single session
- **ALL Method**: Special value for `optimization_method` field indicating all three methods were used
- **EmailFlowOrchestrator**: The service class that coordinates the email-based prompt delivery workflow

## Requirements

### Requirement 1: Session Creation for Email Flow

**User Story:** As a data analyst, I want sessions to be created for email flow interactions, so that I can track all user optimization workflows regardless of delivery method.

#### Acceptance Criteria

1. WHEN a user clicks the "Send 3 prompts to email" button THEN the System SHALL use the existing session that was created when the user submitted their initial prompt
2. WHEN the email flow starts THEN the System SHALL call the existing `set_optimization_method()` with the "ALL" value to update the session
3. WHEN the email flow session is updated THEN the System SHALL verify the session's original prompt is already tracked in conversation history

### Requirement 2: Token Tracking for Multi-Method Optimization

**User Story:** As a data analyst, I want to track cumulative token usage across all three optimization methods, so that I can analyze the total LLM cost for email flow sessions.

#### Acceptance Criteria

1. WHEN the LYRA optimization is executed THEN the System SHALL call the existing `add_tokens()` method with the input and output token counts
2. WHEN the CRAFT optimization is executed THEN the System SHALL call the existing `add_tokens()` method with the input and output token counts
3. WHEN the GGL optimization is executed THEN the System SHALL call the existing `add_tokens()` method with the input and output token counts
4. WHEN all three optimizations complete THEN the session's `tokens_total` SHALL equal the sum of all input and output tokens from all three methods

### Requirement 3: Conversation History with Method Attribution

**User Story:** As a data analyst, I want to identify which optimization method produced each response in the conversation history, so that I can analyze per-method performance.

#### Acceptance Criteria

1. WHEN an LLM response is added to conversation history during email flow THEN the System SHALL call an extended `add_message()` method that accepts an optional `method` parameter
2. WHEN storing conversation messages with method attribution THEN the System SHALL use the format `{"role": "assistant", "content": "...", "timestamp": "...", "method": "LYRA|CRAFT|GGL"}`
3. WHEN storing user messages or system messages THEN the `method` field SHALL be omitted (backward compatible)
4. WHEN querying conversation history THEN the System SHALL return all messages including those with and without method attribution

### Requirement 4: Email Event Logging for Email Flow

**User Story:** As a data analyst, I want to track email delivery events for email flow sessions, so that I can analyze email delivery success rates.

#### Acceptance Criteria

1. WHEN an email containing all three optimized prompts is sent successfully THEN the System SHALL call the existing `log_email_sent()` method to create a single email event record
2. WHEN an email event is created THEN the System SHALL record the timestamp, recipient email address, and delivery status ("sent" or "failed")
3. WHEN the email delivery fails THEN the System SHALL still call `log_email_sent()` with status "failed"

### Requirement 5: Session Completion for Email Flow

**User Story:** As a data analyst, I want email flow sessions to be marked with appropriate completion status, so that I can accurately measure success rates.

#### Acceptance Criteria

1. WHEN the email is successfully sent THEN the System SHALL call the existing `complete_session()` method to mark status as "successful"
2. WHEN the email fails to send THEN the System SHALL call the existing `reset_session()` method to mark status as "unsuccessful"
3. WHEN a session is marked successful or unsuccessful THEN the `finish_time` and `duration_seconds` SHALL be set by the existing methods

### Requirement 6: OptimizationMethod Enum Extension

**User Story:** As a developer, I want the OptimizationMethod enum to support the "ALL" value, so that email flow sessions can be properly categorized.

#### Acceptance Criteria

1. WHEN the OptimizationMethod enum is defined THEN it SHALL include the value "ALL" in addition to LYRA, CRAFT, and GGL
2. WHEN setting optimization method to "ALL" via `set_optimization_method()` THEN the System SHALL accept and store this value without error
3. WHEN querying sessions by optimization method THEN the System SHALL be able to filter by "ALL" to find email flow sessions

### Requirement 7: Graceful Degradation for Email Flow Session Tracking

**User Story:** As a user, I want the email flow to work even if session tracking fails, so that my prompt optimization is not blocked by analytics issues.

#### Acceptance Criteria

1. WHEN session tracking fails during email flow THEN the System SHALL log the error and continue with the email delivery
2. WHEN token tracking fails THEN the System SHALL log the error and continue with the optimization
3. WHEN email event logging fails THEN the System SHALL log the error but not affect the user's email delivery status
4. WHEN any session operation fails THEN the System SHALL NOT display error messages to the user about session tracking

