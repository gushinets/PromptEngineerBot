# Implementation Plan: Split Welcome Message

## Overview

This implementation splits the existing `WELCOME_MESSAGE` into two separate messages with an inline support button. The tasks are ordered to ensure incremental progress with no orphaned code.

## Tasks

- [x] 1. Update messages.py with new message constants and support button
  - [x] 1.1 Add InlineKeyboardButton and InlineKeyboardMarkup imports from telegram
    - Update the import statement at the top of the file
    - _Requirements: 4.4_
  - [x] 1.2 Create WELCOME_MESSAGE_1 constant with RU/EN translations
    - Use the _() helper function following existing pattern
    - Include exact text from requirements
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_
  - [x] 1.3 Create WELCOME_MESSAGE_2 constant with RU/EN translations
    - Use the _() helper function following existing pattern
    - Include exact text from requirements
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_
  - [x] 1.4 Create BTN_SUPPORT button label constant
    - Localized label: "🆘 Техподдержка" / "🆘 Support"
    - _Requirements: 4.2_
  - [x] 1.5 Create SUPPORT_BOT_URL constant
    - URL: https://t.me/prompthelpdesk_bot?start
    - _Requirements: 4.3_
  - [x] 1.6 Create SUPPORT_KEYBOARD InlineKeyboardMarkup
    - Single button with URL parameter
    - _Requirements: 4.1, 4.4_
  - [x] 1.7 Remove or deprecate old WELCOME_MESSAGE constant
    - Keep backward compatibility if needed elsewhere
    - _Requirements: 5.1_

- [x] 2. Update utils/__init__.py exports
  - [x] 2.1 Add WELCOME_MESSAGE_1 to imports and __all__
    - _Requirements: 5.2_
  - [x] 2.2 Add WELCOME_MESSAGE_2 to imports and __all__
    - _Requirements: 5.2_
  - [x] 2.3 Add SUPPORT_KEYBOARD to imports and __all__
    - _Requirements: 5.2_
  - [x] 2.4 Add BTN_SUPPORT to imports and __all__
    - _Requirements: 5.2_
  - [x] 2.5 Remove WELCOME_MESSAGE from exports if deprecated
    - _Requirements: 5.2_

- [x] 3. Update bot_handler.py to send both messages
  - [x] 3.1 Update imports to include new message constants
    - Import WELCOME_MESSAGE_1, WELCOME_MESSAGE_2, SUPPORT_KEYBOARD
    - Remove WELCOME_MESSAGE import if deprecated
    - _Requirements: 5.3_
  - [x] 3.2 Modify handle_start to send WELCOME_MESSAGE_1 first
    - Keep existing parse_mode and reply_markup for first message
    - _Requirements: 1.1_
  - [x] 3.3 Add second _safe_reply call for WELCOME_MESSAGE_2
    - Use SUPPORT_KEYBOARD as reply_markup
    - Send immediately after first message
    - _Requirements: 1.2, 4.1_

- [x] 4. Checkpoint - Verify basic functionality
  - Ensure bot starts without errors
  - Ensure all imports resolve correctly
  - Ask the user if questions arise

- [x] 5. Update unit tests in test_messages.py
  - [x] 5.1 Update test_welcome_message_exists to test both new messages
    - Test WELCOME_MESSAGE_1 is non-empty and contains "🤖"
    - Test WELCOME_MESSAGE_2 is non-empty and contains "ℹ️"
    - _Requirements: 6.2, 6.3, 6.4_
  - [x] 5.2 Add test for WELCOME_MESSAGE_1 content
    - Verify key phrases are present
    - _Requirements: 2.1, 2.2, 2.3, 2.4_
  - [x] 5.3 Add test for WELCOME_MESSAGE_2 content
    - Verify step markers (1️⃣, 2️⃣, 3️⃣) are present
    - Verify optimization options are present
    - _Requirements: 3.1, 3.2, 3.3, 3.4_
  - [x] 5.4 Add test for BTN_SUPPORT label
    - Verify label contains expected text
    - _Requirements: 4.2_
  - [x] 5.5 Add test for SUPPORT_KEYBOARD configuration
    - Verify it's an InlineKeyboardMarkup
    - Verify button has correct URL
    - _Requirements: 4.1, 4.3, 4.4_

- [x] 6. Update integration tests
  - [x] 6.1 Update test_post_optimization_integration.py imports
    - Replace WELCOME_MESSAGE with WELCOME_MESSAGE_1, WELCOME_MESSAGE_2
    - Update assertions to check new constants
    - _Requirements: 6.1_
  - [x] 6.2 Update any other tests referencing WELCOME_MESSAGE
    - Search for and update all references
    - _Requirements: 6.1_

- [x] 7. Final checkpoint - Ensure all tests pass
  - Run full test suite
  - Verify no regressions
  - Ask the user if questions arise

## Notes

- The implementation follows the existing internationalization pattern using `_(ru_text, en_text)`
- InlineKeyboardMarkup is used for the support button (different from ReplyKeyboardMarkup used elsewhere)
- The support button opens a URL directly, no callback handling needed
- Both messages are sent in immediate sequence with no delay
