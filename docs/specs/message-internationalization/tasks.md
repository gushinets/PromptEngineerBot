# Implementation Plan

- [x] 1. Create new message constants in messages.py

  - Add all identified hardcoded strings as properly internationalized message constants
  - Follow existing naming conventions and grouping patterns
  - Ensure both Russian and English translations are provided
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 2.1, 2.2, 2.3, 2.4_

- [x] 2. Update imports in bot_handler.py

  - Add imports for all new message constants that will be used in bot_handler.py
  - Maintain alphabetical ordering within the messages import block
  - Remove any unused message imports if found
  - _Requirements: 4.1, 4.3, 4.4_

- [x] 3. Replace hardcoded strings in bot_handler.py

  - Replace all email service error messages with message constants
  - Replace all follow-up conversation error messages with message constants
  - Replace all state recovery messages with message constants
  - Replace any remaining hardcoded user-facing strings with message constants
  - _Requirements: 3.1, 3.3_
-

- [x] 4. Update imports in email_flow.py

  - Add imports for all new message constants that will be used in email_flow.py
  - Maintain alphabetical ordering within the messages import block
  - Remove any unused message imports if found
  - _Requirements: 4.2, 4.3, 4.4_

- [x] 5. Replace hardcoded strings in email_flow.py

  - Replace all flow error messages with message constants
  - Replace all validation messages with message constants
  - Replace all processing status messages with message constants
  - Replace all success messages with message constants
  - Replace optimization error template strings with message constants
  - _Requirements: 3.2, 3.4_

- [x] 6. Run existing tests and fix any issues

  - Execute all existing test suites to verify no functionality is broken
  - Fix any test failures or import errors caused by the refactoring
  - Ensure all tests pass before considering the refactoring complete
  - _Requirements: 5.1, 5.2_

- [x] 7. Validate refactoring completion

  - Verify no hardcoded user-facing strings remain in bot_handler.py
  - Verify no hardcoded user-facing strings remain in email_flow.py
  - Test that all messages display correctly in the bot
  - Confirm all imports resolve without errors
  - _Requirements: 3.3, 3.4, 5.1, 5.2, 5.3, 5.4_