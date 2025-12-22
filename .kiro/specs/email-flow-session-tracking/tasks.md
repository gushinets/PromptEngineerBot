# Implementation Plan: Email Flow Session Tracking

## Overview

This implementation extends the existing session tracking system to support the "Send 3 prompts to email" flow. The approach maximizes reuse of existing `SessionService` methods with minimal code changes:

1. Add "ALL" value to `OptimizationMethod` enum
2. Extend `add_message()` with optional `method` parameter
3. Integrate session tracking calls into `EmailFlowOrchestrator`

## Tasks

- [x] 1. Extend OptimizationMethod enum with "ALL" value
  - Add `ALL = "ALL"` to the `OptimizationMethod` enum in `telegram_bot/services/session_service.py`
  - This enables email flow sessions to be categorized distinctly from single-method sessions
  - _Requirements: 6.1, 6.2_

- [x] 2. Extend add_message() method with optional method parameter
  - [x] 2.1 Add optional `method` parameter to `add_message()` signature
    - Modify `telegram_bot/services/session_service.py`
    - Add `method: str | None = None` parameter
    - Include `method` field in message dict only when provided
    - _Requirements: 3.1, 3.2, 3.3_

  - [x] 2.2 Write unit tests for add_message() method extension
    - Test with `method` parameter adds field to JSONB
    - Test without `method` parameter (backward compatibility)
    - Test method field values (LYRA, CRAFT, GGL)
    - _Requirements: 3.1, 3.2, 3.3, 3.4_

- [x] 3. Checkpoint - Verify enum and method extension
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Integrate session tracking into EmailFlowOrchestrator
  - [x] 4.1 Add SessionService import and initialization
    - Import `get_session_service`, `OptimizationMethod` in `telegram_bot/flows/email_flow.py`
    - Add session service access in orchestrator methods
    - _Requirements: 1.1, 1.2_

  - [x] 4.2 Modify `_run_direct_optimization_and_email_delivery()` for session tracking
    - Get `session_id` from `StateManager.get_current_session_id(user_id)`
    - Call `set_optimization_method(session_id, OptimizationMethod.ALL)` at flow start
    - Call `complete_session(session_id)` on email success
    - Call `reset_session(session_id)` on email failure
    - Call `log_email_sent(session_id, email, status)` for email event
    - Wrap all session calls in try/except for graceful degradation
    - _Requirements: 1.2, 5.1, 5.2, 5.3, 4.1, 4.2, 4.3, 7.1, 7.3_

  - [x] 4.3 Modify `_run_all_optimizations_with_modified_prompts()` for token/message tracking
    - After each LLM call, extract token usage from response
    - Call `add_tokens(session_id, input_tokens, output_tokens)` for each method
    - Call `add_message(session_id, "assistant", response, method=method_name)` for each method
    - Wrap all session calls in try/except for graceful degradation
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 3.1, 3.2, 7.2_

- [x] 5. Checkpoint - Verify integration
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Write property-based tests for email flow session tracking
  - [x] 6.1 Write property test for token accumulation
    - **Property 2: Token accumulation across all methods**
    - *For any* email flow session, the final `tokens_total` SHALL equal the sum of input and output tokens from all three optimization methods
    - **Validates: Requirements 2.1, 2.2, 2.3, 2.4**

  - [x] 6.2 Write property test for conversation history method attribution
    - **Property 3: Conversation history contains all method responses**
    - *For any* completed email flow session, the conversation history SHALL contain exactly 3 assistant messages with `method` field set to "LYRA", "CRAFT", and "GGL"
    - **Validates: Requirements 3.1, 3.2**

  - [x] 6.3 Write property test for backward compatibility
    - **Property 6: Backward compatibility of add_message**
    - *For any* call to `add_message()` without the `method` parameter, the resulting conversation history entry SHALL NOT contain a `method` field
    - **Validates: Requirements 3.3, 3.4**

- [x] 7. Write integration tests for email flow session tracking
  - [x] 7.1 Test full email flow with session tracking ✓
    - Start session → email flow → verify method="ALL"
    - Verify tokens accumulated from all 3 methods
    - Verify conversation history has 3 method-attributed messages
    - Verify single email event created
    - Verify session status based on email result
    - _Requirements: 1.1, 1.2, 2.4, 3.1, 4.1, 5.1, 5.2_

  - [x] 7.2 Test graceful degradation
    - Simulate session service failures
    - Verify email flow completes successfully despite tracking failures
    - _Requirements: 7.1, 7.2, 7.3, 7.4_

- [x] 8. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- All tasks are required for comprehensive testing
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties
- Unit tests validate specific examples and edge cases
- All session tracking calls must be wrapped in try/except to ensure graceful degradation
- The implementation reuses existing `SessionService` methods wherever possible
