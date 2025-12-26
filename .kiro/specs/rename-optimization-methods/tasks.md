# Implementation Plan: Rename Optimization Methods

## Overview

This plan implements the renaming of optimization methods from technical names (LYRA, CRAFT, GGL) to user-friendly names (Быстро/Quick, По шагам/Step-by-step, Под результат/Result-focused) in all user-facing content.

## Tasks

- [x] 1. Update button labels in messages.py
  - Change BTN_LYRA from "⚡ LYRA" to "⚡ Быстро" / "⚡ Quick"
  - Change BTN_CRAFT from "🛠 CRAFT" to "🛠 По шагам" / "🛠 Step-by-step"
  - Change BTN_GGL from "🔍 GGL" to "🎯 Под результат" / "🎯 Result-focused"
  - Remove BTN_LYRA_DETAIL if no longer needed or update accordingly
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 7.1, 7.2, 7.3_

- [x] 2. Update welcome and help messages in messages.py
  - [x] 2.1 Update WELCOME_MESSAGE with new method names and standardized emojis
    - Replace LYRA references with "Быстро" / "Quick"
    - Replace CRAFT references with "По шагам" / "Step-by-step"
    - Replace GGL references with "Под результат" / "Result-focused"
    - Standardize emojis to ⚡, 🛠, 🎯
    - _Requirements: 2.1, 2.2, 7.1, 7.2, 7.3_
  - [x] 2.2 Update WELCOME_MESSAGE_2 with new method names (already partially done, verify consistency)
    - _Requirements: 2.1, 2.2, 2.3_

- [x] 3. Update method selection message in messages.py
  - Update SELECT_METHOD_MESSAGE with new method names and descriptions
  - Ensure emojis are standardized (⚡, 🛠, 🎯)
  - _Requirements: 4.1, 4.2, 7.1, 7.2, 7.3_

- [x] 4. Update email templates in email_templates.py
  - [x] 4.1 Update get_optimization_html_body() method labels
    - Change craft_label to use "По шагам" / "Step-by-step"
    - Change lyra_label to use "Быстро" / "Quick"
    - Change ggl_label to use "Под результат" / "Result-focused"
    - Standardize emojis to ⚡, 🛠, 🎯
    - _Requirements: 3.1, 3.2, 3.3, 3.4_
  - [x] 4.2 Update get_optimization_plain_body() method labels
    - Apply same changes as HTML body
    - _Requirements: 3.1, 3.2, 3.3, 3.4_

- [x] 5. Update unit tests in test_messages.py
  - Update test_button_constants_exist() to check for new button text
  - Verify tests check for "Быстро"/"Quick", "По шагам"/"Step-by-step", "Под результат"/"Result-focused"
  - Remove assertions for old names (LYRA, CRAFT, GGL in button text)
  - _Requirements: 6.1, 6.2_

- [x] 6. Update integration tests
  - [x] 6.1 Update test_bot_handler.py
    - Update any assertions that check for old button text
    - _Requirements: 6.1, 6.2_
  - [x] 6.2 Update test_post_optimization_integration.py
    - Update test_existing_button_definitions_not_modified() to check new values
    - _Requirements: 6.1, 6.2_
  - [x] 6.3 Update test_bot_handler_integration.py if needed
    - Check for any hardcoded method name references
    - _Requirements: 6.1, 6.2_

- [x] 7. Verify legacy emoji removal
  - Search for and remove any remaining 🔍 emoji usage for GGL method
  - Search for and remove any 🧩 emoji usage for LYRA detail
  - _Requirements: 7.4_

- [x] 8. Final checkpoint
  - Ensure all tests pass
  - Verify no remaining references to old display names in user-facing content
  - Ask the user if questions arise

## Notes

- Tasks are ordered to minimize conflicts (messages.py first, then templates, then tests)
- Internal identifiers (LYRA, CRAFT, GGL) in code logic and tests remain unchanged
- Only user-facing display strings are modified
