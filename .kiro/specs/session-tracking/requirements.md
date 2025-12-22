# Requirements Document

## Introduction

This feature introduces a "Session" entity to track user prompt optimization workflows from start to finish. A session begins when a user submits a prompt for optimization and ends when the improved prompt is delivered back to the user. Sessions can also end unsuccessfully via manual reset ("reset dialog" button) or automatic timeout after configurable inactivity period. The system captures comprehensive metrics for each session including timing, token usage, optimization method, and email delivery events to enable analysis of user interactions with the bot.

**Important Lifecycle Notes:**
- Session starts immediately when user sends their initial prompt (before method selection)
- Session is marked "successful" when improved prompt is delivered
- Post-completion tracking: Even after session is "successful", the system continues to track followup conversations and email events on the same session
- Session ID is cleared from state only on reset button click or when user sends a new initial prompt

## Glossary

- **Session**: A discrete unit of user interaction representing a complete prompt optimization workflow, from initial prompt submission to final delivery or termination
- **Session ID**: Auto-increment integer primary key uniquely identifying each session in the database
- **Successful Session**: A session that completes normally with the improved prompt delivered to the user
- **Unsuccessful Session**: A session terminated by user reset ("reset dialog" button) or automatic timeout
- **Session Timeout**: Configurable period of user inactivity (in seconds) after which a session automatically terminates as unsuccessful
- **Optimization Method**: The prompt improvement technique selected by the user (LYRA, CRAFT, or GGL). May be NULL initially when session is created before method selection.
- **FOLLOWUP**: Secondary optimization phase where user answers clarifying questions to further improve an already-optimized prompt. Tracked on the same session with separate timing and token metrics.
- **Input Tokens**: Cumulative count of all tokens sent to the LLM during initial optimization phase
- **Output Tokens**: Cumulative count of all tokens received from the LLM during initial optimization phase
- **Followup Input Tokens**: Cumulative count of all tokens sent to the LLM during followup conversation
- **Followup Output Tokens**: Cumulative count of all tokens received from the LLM during followup conversation
- **Session Duration**: Time elapsed between session start and session finish, stored in seconds for precision
- **Followup Duration**: Time elapsed between followup start and followup finish, stored in seconds for precision
- **Email Event**: A record of an email sent containing the optimized prompt, linked to the session (can be recorded even after session is marked successful)
- **User**: A Telegram user identified by `telegram_id`, stored in the existing `users` table
- **User ID (Foreign Key)**: Reference to `users.id` that links each session to its owner user record
- **Conversation History**: Complete record of all messages exchanged between user and LLM during a session (including both initial optimization and followup phases), stored as JSONB array in the sessions table
- **Model Name**: The LLM model identifier used for prompt optimization (e.g., "openai/gpt-4", "gpt-4o")

## Requirements

### Requirement 1

**User Story:** As a system administrator, I want sessions to be created automatically when users submit prompts for optimization, so that I can track the beginning of each optimization workflow.

#### Acceptance Criteria

1. WHEN a user sends a prompt for optimization THEN the System SHALL create a new session record with a unique auto-increment session ID immediately (before method selection)
2. WHEN a new session is created THEN the System SHALL record the `user_id` as a foreign key reference to the `users.id` column to associate the session with the user
3. WHEN a new session is created THEN the System SHALL set the `start_time` to the current UTC timestamp
4. WHEN a new session is created THEN the System SHALL set the session status to "in_progress"
5. WHEN a new session is created THEN the System SHALL set `optimization_method` to NULL (to be updated when user selects method)
6. WHEN a new session is created THEN the System SHALL immediately track the user's initial prompt in the conversation history
7. WHEN a user sends a new initial prompt while having an existing session THEN the System SHALL clear the previous session ID from state before creating a new session

### Requirement 2

**User Story:** As a system administrator, I want sessions to be marked as successful when users receive their improved prompts, so that I can measure successful optimization completions.

#### Acceptance Criteria

1. WHEN the improved prompt is sent back to the user THEN the System SHALL update the session status to "successful"
2. WHEN a session is marked successful THEN the System SHALL set the `finish_time` to the current UTC timestamp
3. WHEN a session is marked successful THEN the System SHALL calculate and store the `duration_seconds` as the difference between `finish_time` and `start_time` in seconds

### Requirement 3

**User Story:** As a system administrator, I want sessions to be marked as unsuccessful when users reset the dialog, so that I can track abandoned optimization attempts.

#### Acceptance Criteria

1. WHEN a user presses the "reset dialog" button THEN the System SHALL update the current session status to "unsuccessful"
2. WHEN a session is marked unsuccessful via reset THEN the System SHALL set the `finish_time` to the current UTC timestamp
3. WHEN a session is marked unsuccessful THEN the System SHALL preserve all collected metrics (tokens, method) for analysis

### Requirement 4

**User Story:** As a system administrator, I want sessions to automatically timeout after configurable inactivity, so that abandoned sessions are properly closed.

#### Acceptance Criteria

1. WHEN a user is inactive for N seconds (where N is configurable) THEN the System SHALL automatically mark the session as "unsuccessful"
2. WHEN a session times out THEN the System SHALL set the `finish_time` to the timeout detection timestamp
3. WHEN configuring the timeout THEN the System SHALL read the timeout value in seconds from the SESSION_TIMEOUT_SECONDS environment variable
4. WHEN the SESSION_TIMEOUT_SECONDS variable is not set THEN the System SHALL use a default value of 86400 seconds (24 hours)

### Requirement 5

**User Story:** As a data analyst, I want to track cumulative token usage per session, so that I can analyze the total LLM cost for each prompt optimization workflow.

#### Acceptance Criteria

1. WHEN a new session is created THEN the System SHALL initialize `input_tokens`, `output_tokens`, and `tokens_total` to zero
2. WHEN any LLM call is made within the session THEN the System SHALL add the call's input token count to the session's `input_tokens`
3. WHEN any LLM response is received within the session THEN the System SHALL add the response's output token count to the session's `output_tokens`
4. WHEN token counts are updated THEN the System SHALL recalculate `tokens_total` as the sum of `input_tokens` and `output_tokens`
5. WHEN multiple LLM interactions occur (initial optimization, clarifying questions, follow-up answers, final improvement) THEN the System SHALL accumulate all token counts to reflect total session cost

### Requirement 6

**User Story:** As a data analyst, I want to track which optimization method and LLM model were used in each session, so that I can analyze method popularity, model usage, and effectiveness.

#### Acceptance Criteria

1. WHEN a user selects an optimization method THEN the System SHALL update the session's `optimization_method` field with the selected method (LYRA, CRAFT, or GGL)
2. WHEN a user opts for FOLLOWUP optimization THEN the System SHALL set the `used_followup` flag to true and record `followup_start_time`
3. WHEN a session is created THEN the System SHALL initialize `used_followup` to false
4. WHEN a session is created THEN the System SHALL record the `model_name` of the LLM used for optimization
5. WHEN a followup conversation completes THEN the System SHALL record `followup_finish_time` and calculate `followup_duration_seconds`

### Requirement 6a

**User Story:** As a data analyst, I want to track followup conversation metrics separately, so that I can analyze the cost and duration of followup optimization phases.

#### Acceptance Criteria

1. WHEN a user starts a followup conversation THEN the System SHALL record `followup_start_time` to the current UTC timestamp
2. WHEN a followup conversation completes THEN the System SHALL record `followup_finish_time` to the current UTC timestamp
3. WHEN a followup conversation completes THEN the System SHALL calculate and store `followup_duration_seconds` as the difference between `followup_finish_time` and `followup_start_time`
4. WHEN any LLM call is made during followup THEN the System SHALL add the call's input token count to the session's `followup_input_tokens`
5. WHEN any LLM response is received during followup THEN the System SHALL add the response's output token count to the session's `followup_output_tokens`
6. WHEN followup token counts are updated THEN the System SHALL recalculate `followup_tokens_total` as the sum of `followup_input_tokens` and `followup_output_tokens`
7. WHEN followup messages are exchanged THEN the System SHALL append them to the same `conversation_history` JSONB field (not a separate field)

### Requirement 7

**User Story:** As a data analyst, I want to track email deliveries per session, so that I can analyze how often users request email delivery of optimized prompts.

#### Acceptance Criteria

1. WHEN an email containing the optimized prompt is sent THEN the System SHALL create an email event record linked to the session
2. WHEN an email event is created THEN the System SHALL record the timestamp, recipient email address, and delivery status
3. WHEN querying session data THEN the System SHALL provide access to all email events associated with that session
4. WHEN logging email events THEN the System SHALL allow email events to be recorded on any session regardless of session status (including "successful" sessions)

### Requirement 8

**User Story:** As a database administrator, I want session data to be stored indefinitely, so that historical analysis can be performed without data loss.

#### Acceptance Criteria

1. WHEN session records are created THEN the System SHALL store them permanently without automatic deletion
2. WHEN querying historical sessions THEN the System SHALL return all sessions regardless of age

### Requirement 9

**User Story:** As a developer, I want session data to be properly indexed, so that queries filtering by user, status, or time range perform efficiently.

#### Acceptance Criteria

1. WHEN the database migration runs THEN the System SHALL create an index on the `user_id` foreign key column for user-based queries
2. WHEN the database migration runs THEN the System SHALL create an index on the `status` column for status-based filtering
3. WHEN the database migration runs THEN the System SHALL create an index on the `start_time` column for time-range queries
4. WHEN the migration is rolled back THEN the System SHALL remove the session tables and their indexes

### Requirement 10

**User Story:** As a data analyst, I want to store the full conversation history within each session, so that I can analyze user-LLM interactions and improve prompt optimization quality.

#### Acceptance Criteria

1. WHEN a user sends a message to the LLM THEN the System SHALL append the message to the session's `conversation_history` JSONB field with role "user"
2. WHEN the LLM responds THEN the System SHALL append the response to the session's `conversation_history` JSONB field with role "assistant"
3. WHEN storing conversation messages THEN the System SHALL record the timestamp and message content for each entry in the JSONB array
4. WHEN querying session data THEN the System SHALL return the complete conversation history in chronological order as stored in the JSONB array

### Requirement 11

**User Story:** As a developer, I want a pretty-printer for session data, so that session records can be serialized and deserialized for logging and API responses.

#### Acceptance Criteria

1. WHEN a session is serialized to JSON THEN the System SHALL produce a valid JSON string containing all session fields including conversation history
2. WHEN a JSON string is parsed back to a session THEN the System SHALL reconstruct an equivalent session object
3. WHEN serializing datetime fields THEN the System SHALL use ISO 8601 format with timezone information
