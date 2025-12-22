# Implementation Plan

## Bug Fixes (Priority)

- [x] 14. Fix session lifecycle timing issues





  - [x] 14.1 Move session creation to prompt input handler





    - Move `start_session()` call from `_process_method_selection()` to `_handle_prompt_input()`
    - Create session with `optimization_method=None` initially
    - Track initial prompt in conversation history immediately after session creation
    - _Requirements: 1.1, 1.5, 1.6_

  - [x] 14.2 Add set_optimization_method() to SessionService




    - Implement method to update `optimization_method` field after session creation
    - Call from `_process_method_selection()` instead of creating new session
    - _Requirements: 6.1_
  - [x] 14.3 Update start_session() to make method parameter optional





    - Change `method` parameter to `Optional[OptimizationMethod]` with default `None`
    - Update Session model to allow nullable `optimization_method`
    - _Requirements: 1.5_
  - [x] 14.4 Clear session_id when user sends new initial prompt





    - In `_handle_prompt_input()`, clear previous session_id from state before creating new session
    - _Requirements: 1.7_

- [x] 15. Fix post-completion tracking (followup and email)





  - [x] 15.1 Don't clear session_id on session completion





    - Remove line that clears session_id from state in `_complete_current_session()`
    - Session_id should remain available for post-completion tracking
    - _Requirements: 6.2, 7.4_
  - [x] 15.2 Implement start_followup() method in SessionService





    - Set `used_followup=True` and `followup_start_time` to current UTC timestamp
    - Replace `set_followup_used()` calls with `start_followup()`
    - _Requirements: 6a.1_
  - [x] 15.3 Implement complete_followup() method in SessionService





    - Set `followup_finish_time` to current UTC timestamp
    - Calculate `followup_duration_seconds`
    - Call from `_complete_followup_conversation()`
    - _Requirements: 6a.2, 6a.3_
  - [x] 15.4 Implement add_followup_tokens() method in SessionService





    - Accumulate `followup_input_tokens` and `followup_output_tokens`
    - Recalculate `followup_tokens_total`
    - _Requirements: 6a.4, 6a.5, 6a.6_
  - [x] 15.5 Update bot handler to use followup token tracking









    - When in followup mode, call `add_followup_tokens()` instead of `add_tokens()`
    - Add state check to determine if in followup mode
    - _Requirements: 6a.4, 6a.5_

- [x] 16. Fix email event tracking





  - [x] 16.1 Pass session_id to email sending functions





    - Get session_id from state in `_send_post_optimization_email()`
    - Pass session_id to `send_single_result_email()` call
    - _Requirements: 7.1, 7.4_

  - [x] 16.2 Update log_email_sent() to work on any session status




    - Remove any status checks in `log_email_sent()` (if present)
    - Ensure email events can be logged on "successful" sessions
    - _Requirements: 7.4_

- [x] 17. Database migration for new followup fields




  - [x] 17.1 Create Alembic migration for followup tracking fields





    - Add `followup_start_time`, `followup_finish_time`, `followup_duration_seconds`
    - Add `followup_input_tokens`, `followup_output_tokens`, `followup_tokens_total`
    - Make `optimization_method` nullable
    - _Requirements: 6a.1, 6a.2, 6a.3, 6a.4, 6a.5, 6a.6, 1.5_
  - [x] 17.2 Update Session model in database.py





    - Add new followup fields to Session class
    - Change `optimization_method` to nullable
    - _Requirements: 6a.1, 6a.2, 6a.3, 6a.4, 6a.5, 6a.6, 1.5_

- [x] 18. Checkpoint - Ensure all bug fix tests pass





  - Ensure all tests pass, ask the user if questions arise.

## Original Implementation (Completed)

- [x] 1. Set up database models and migration





  - [x] 1.1 Add Session model to database.py





    - Create Session class with all fields (id, user_id, start_time, finish_time, duration_seconds, status, optimization_method, model_name, used_followup, input_tokens, output_tokens, tokens_total, conversation_history)
    - Add JSONB import for conversation_history field
    - Add relationship to User model
    - _Requirements: 1.1, 1.2, 5.1, 6.3, 6.4, 10.1_
  - [x] 1.2 Add SessionEmailEvent model to database.py





    - Create SessionEmailEvent class with fields (id, session_id, sent_at, recipient_email, delivery_status)
    - Add relationship to Session model
    - _Requirements: 7.1, 7.2_
  - [x] 1.3 Update User model with sessions relationship




    - Add `sessions` relationship field to User class
    - _Requirements: 1.2_
  - [x] 1.4 Add database indexes for sessions and session_email_events





    - Create indexes on user_id, status, start_time, and composite user_id+status
    - Create index on session_email_events.session_id
    - _Requirements: 9.1, 9.2, 9.3_
  - [x] 1.5 Create Alembic migration for session tables





    - Generate migration file for sessions and session_email_events tables
    - Include upgrade and downgrade functions
    - _Requirements: 9.4_

- [x] 2. Add configuration for session timeout






  - [x] 2.1 Add session_timeout_seconds to BotConfig

    - Add field with default value 86400 (24 hours)
    - Add environment variable reading in from_env()
    - Add validation in validate()
    - _Requirements: 4.3, 4.4_

  - [x] 2.2 Update .env.example with SESSION_TIMEOUT_SECONDS

    - Add commented example with description
    - _Requirements: 4.3_

- [x] 3. Implement SessionService core functionality




  - [x] 3.1 Create SessionService class with enums





    - Create session_service.py in telegram_bot/services/
    - Define SessionStatus and OptimizationMethod enums
    - Initialize service with database session
    - _Requirements: 1.4, 6.1_
  - [x] 3.2 Implement start_session() method








    - Create new session with defaults (status=in_progress, tokens=0, used_followup=False, conversation_history=[])
    - Link to user via user_id foreign key
    - Return None on error with logging
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 5.1, 6.3, 6.4_
  - [x] 3.3 Write property test for start_session defaults









    - **Property 1: New sessions initialize with correct defaults**
    - **Validates: Requirements 1.3, 1.4, 5.1, 6.3**
  - [x] 3.4 Implement complete_session() method








    - Set status to "successful", finish_time to now
    - Calculate duration_seconds from start_time
    - Return None on error with logging
    - _Requirements: 2.1, 2.2, 2.3_
  - [x] 3.5 Write property test for complete_session





    - **Property 4: Successful completion sets finish time and duration**
    - **Validates: Requirements 2.1, 2.2, 2.3**
  - [x] 3.6 Implement reset_session() method





    - Set status to "unsuccessful", finish_time to now
    - Preserve all metrics (tokens, method, conversation)
    - Return None on error with logging
    - _Requirements: 3.1, 3.2, 3.3_
  - [x] 3.7 Write property test for reset_session preserves metrics





    - **Property 5: Reset preserves metrics**
    - **Validates: Requirements 3.1, 3.2, 3.3**

- [x] 4. Checkpoint - Ensure all tests pass





  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Implement token and message tracking





  - [x] 5.1 Implement add_tokens() method





    - Accumulate input_tokens and output_tokens
    - Recalculate tokens_total
    - Return None on error with logging
    - _Requirements: 5.2, 5.3, 5.4, 5.5_
  - [x] 5.2 Write property test for token accumulation





    - **Property 3: Token accumulation is additive**
    - **Validates: Requirements 5.2, 5.3, 5.4, 5.5**
  - [x] 5.3 Implement add_message() method





    - Append message object to conversation_history JSONB
    - Include role, content, and ISO8601 timestamp
    - Return None on error with logging
    - _Requirements: 10.1, 10.2, 10.3_
  - [x] 5.4 Write property test for conversation history ordering





    - **Property 10: Conversation history preserves message order**
    - **Validates: Requirements 10.1, 10.2, 10.3, 10.4**
  - [x] 5.5 Implement set_followup_used() method





    - Set used_followup flag to True
    - Return None on error with logging
    - _Requirements: 6.2_
  - [x] 5.6 Implement get_conversation_history() method





    - Return conversation_history JSONB as list[dict]
    - _Requirements: 10.4_

- [x] 6. Implement email event logging


  - [x] 6.1 Implement log_email_sent() method





    - Create SessionEmailEvent record linked to session
    - Record timestamp, recipient_email, delivery_status
    - Return None on error with logging
    - _Requirements: 7.1, 7.2_
  - [x] 6.2 Write property test for email events linked to sessions





    - **Property 6: Email events are linked to sessions**
    - **Validates: Requirements 7.1, 7.3**
  - [x] 6.3 Implement get_session_with_emails() method




    - Load session with email_events relationship
    - _Requirements: 7.3_

- [x] 7. Implement session queries and timeout

  - [x] 7.1 Implement get_user_current_session() method





    - Query for session with user_id and status="in_progress"
    - Return None if not found or on error
    - _Requirements: 1.1_
  - [x] 7.2 Write property test for one active session per user





    - **Property 9: One active session per user**
    - **Validates: Requirements 1.1**
  - [x] 7.3 Implement timeout_stale_sessions() method





    - Query sessions with status="in_progress" and start_time older than timeout
    - Mark each as "unsuccessful" with finish_time
    - Process in batches, continue on individual failures
    - Return count of timed out sessions
    - _Requirements: 4.1, 4.2_

  - [x] 7.4 Write property test for timeout behavior




    - **Property 8: Timeout marks sessions unsuccessful**
    - **Validates: Requirements 4.1, 4.2**

- [x] 8. Checkpoint - Ensure all tests pass





  - Ensure all tests pass, ask the user if questions arise.

- [x] 9. Implement session serialization

  - [x] 9.1 Implement to_dict() method on Session model


    - Serialize all fields including conversation_history
    - Use ISO8601 format for datetime fields
    - _Requirements: 11.1, 11.3_

  - [x] 9.2 Implement from_dict() class method on Session model
    - Deserialize JSON dict to Session object
    - Parse ISO8601 datetime strings
    - _Requirements: 11.2_
  - [x] 9.3 Write property test for serialization round-trip


    - **Property 7: Session serialization round-trip**
    - **Validates: Requirements 11.1, 11.2, 11.3**

- [x] 10. Integrate SessionService with bot handlers




  - [x] 10.1 Add SessionService to dependencies





    - Initialize SessionService in telegram_bot/dependencies.py
    - Make available to handlers
    - _Requirements: 1.1_
  - [x] 10.2 Integrate start_session() in prompt optimization flow





    - Call when user submits prompt for optimization
    - Pass user_id, method, and model_name
    - _Requirements: 1.1, 1.2, 1.3, 6.1, 6.4_
  - [x] 10.3 Integrate add_tokens() after LLM calls





    - Call after each LLM interaction with token counts
    - _Requirements: 5.2, 5.3_

  - [x] 10.4 Integrate add_message() for conversation logging




    - Call after user messages and LLM responses
    - _Requirements: 10.1, 10.2_

  - [x] 10.5 Integrate complete_session() on prompt delivery




    - Call when improved prompt is sent to user
    - _Requirements: 2.1_
  - [x] 10.6 Integrate reset_session() on dialog reset





    - Call when user presses "reset dialog" button
    - _Requirements: 3.1_
  - [x] 10.7 Integrate set_followup_used() on followup opt-in





    - Call when user opts for FOLLOWUP optimization
    - _Requirements: 6.2_

- [x] 11. Integrate email logging with EmailService






  - [x] 11.1 Call log_email_sent() from EmailService

    - Log email events when optimized prompts are sent
    - Pass session_id, recipient_email, and delivery status
    - _Requirements: 7.1, 7.2_

- [x] 12. Set up session timeout background task






  - [x] 12.1 Create background task for session timeout

    - Periodically call timeout_stale_sessions()
    - Use configured session_timeout_seconds
    - Log results (count of timed out sessions)
    - _Requirements: 4.1, 4.2_

- [x] 13. Final Checkpoint - Ensure all tests pass





  - Ensure all tests pass, ask the user if questions arise.
