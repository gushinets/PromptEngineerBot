# Implementation Plan

- [x] 1. Remove duplicate logging functions from main.py


  - Remove `log_method_selection_to_file()` function that duplicates BotHandler._log_method_selection()
  - Remove `log_llm_exchange_to_sheets()` function as this functionality is covered by BotHandler logging
  - Remove `log_conversation_totals_to_sheets()` function that duplicates BotHandler._log_conversation_totals()
  - Remove helper functions `_compose_llm_name()`, `_parse_bot_id_from_token()`, `_get_bot_identifier()` that are no longer needed
  - _Requirements: 1.1, 1.2, 1.3_

- [x] 2. Remove duplicate state management functions from main.py


  - Remove `reset_user_state()` function that duplicates BotHandler.reset_user_state()
  - Ensure all state management goes through BotHandler instance
  - _Requirements: 3.1, 3.2, 3.3_



- [ ] 3. Remove duplicate message handling functions from main.py
  - Remove `safe_reply()` function that duplicates BotHandler._safe_reply()
  - Remove associated constants like `MAX_RETRIES` that are only used by the duplicate function


  - _Requirements: 4.1, 4.2, 4.3_

- [ ] 4. Clean up imports and fix undefined variables
  - Remove unused import `ReplyKeyboardMarkup` from telegram imports


  - Move module imports (`BotConfig`, `LLMClientFactory`, `BotHandler`) to the top of the file
  - Remove references to undefined variables `llm_backend`, `conversation_manager`, `state_manager`
  - _Requirements: 2.1, 2.2, 2.3_


- [ ] 5. Remove obsolete comments and clean up main.py structure
  - Remove outdated TODO comments about logging decisions
  - Remove commented-out code blocks if any exist
  - Simplify main.py to focus only on application bootstrap and coordination
  - _Requirements: 5.1, 5.2, 5.3_

- [x] 6. Update handler functions to use BotHandler exclusively

  - Ensure `start()` and `handle_message()` functions only delegate to BotHandler
  - Remove any direct references to state managers or conversation managers
  - Verify all bot logic routes through BotHandler instance
  - _Requirements: 3.3, 4.3_

- [x] 7. Run regression tests to ensure functionality is preserved


  - Execute existing test suite to verify no functionality is broken
  - Test message handling still works after removing duplicate functions
  - Test state management functions correctly through BotHandler only
  - Test logging continues to work after removing duplicate logging functions
  - _Requirements: All requirements verification_

- [x] 8. Validate code cleanup and architectural improvements



  - Verify main.py is simplified and focuses on application lifecycle
  - Confirm BotHandler is the single source of truth for bot interactions
  - Ensure error handling maintains the same user experience
  - Validate improved code clarity and maintainability
  - _Requirements: All requirements verification_