# Implementation Plan: OTP Consent Agreement

## Overview

This implementation adds personal data processing consent messaging to the OTP authentication flow in both Telegram messages and email templates. The implementation follows the existing i18n patterns and module structure.

## Tasks

- [x] 1. Add consent constants to messages module
  - Add `EMAIL_OTP_CONSENT_MESSAGE` constant with Russian and English translations
  - Add `BTN_DATA_AGREEMENT` button text constant with Russian and English translations
  - Add `DATA_AGREEMENT_URL` constant with the agreement link
  - Add `DATA_AGREEMENT_KEYBOARD` InlineKeyboardMarkup with the agreement button
  - _Requirements: 1.2, 1.3, 1.4, 2.2, 2.3, 2.4, 2.5_

- [x] 2. Update EMAIL_OTP_SENT message
  - [x] 2.1 Modify EMAIL_OTP_SENT to append consent message text
    - Update Russian text to include consent message
    - Update English text to include consent message
    - _Requirements: 1.1, 1.2, 1.3_

  - [x] 2.2 Write unit tests for updated EMAIL_OTP_SENT message
    - Test Russian message contains consent text
    - Test English message contains consent text
    - _Requirements: 1.1, 1.2, 1.3_

- [x] 3. Update email flow to include inline keyboard
  - [x] 3.1 Modify handle_email_input in email_flow.py to send inline keyboard
    - Import DATA_AGREEMENT_KEYBOARD from messages module
    - Update _safe_reply call to include inline_keyboard parameter
    - Ensure reply keyboard with Reset button is still sent
    - _Requirements: 2.1, 4.1, 4.2_

  - [x] 3.2 Write unit tests for email flow inline keyboard
    - Test that OTP sent message includes inline keyboard
    - Test that inline keyboard has correct URL
    - _Requirements: 2.1, 2.4_

- [x] 4. Update OTP email HTML template
  - [x] 4.1 Add consent section to get_otp_html_body method
    - Add CSS styles for consent section
    - Add consent section HTML before greeting
    - Include consent message text with i18n support
    - Include clickable button/link with agreement URL
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.7_

  - [x] 4.2 Write unit tests for HTML email consent section
    - Test consent section appears in HTML output
    - Test consent message text matches language setting
    - Test link URL is correct
    - Test link text matches language setting
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.7_

- [x] 5. Update OTP email plain text template
  - [x] 5.1 Add consent section to get_otp_plain_body method
    - Add consent message text before greeting
    - Include agreement URL as plain text link
    - _Requirements: 3.6, 3.7_

  - [x] 5.2 Write unit tests for plain text email consent section
    - Test consent section appears in plain text output
    - Test consent message text matches language setting
    - Test URL is included
    - _Requirements: 3.6, 3.7_

- [x] 6. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Write property-based tests for consent feature
  - [x] 7.1 Write property test for OTP message consent text
    - **Property 1: OTP Message Contains Consent Text**
    - **Validates: Requirements 1.1, 1.2, 1.3**

  - [x] 7.2 Write property test for agreement button URL
    - **Property 2: Agreement Button Has Correct URL**
    - **Validates: Requirements 2.1, 2.4**

  - [x] 7.3 Write property test for email consent section
    - **Property 3: Email Consent Section Contains Required Elements**
    - **Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.6, 3.7**

  - [x] 7.4 Write property test for language consistency
    - **Property 4: Language Consistency**
    - **Validates: Requirements 1.2, 1.3, 2.2, 2.3, 3.7**

- [x] 8. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- All tasks are required for comprehensive testing
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties
- Unit tests validate specific examples and edge cases
- The implementation uses the existing `hypothesis` library for property-based testing
