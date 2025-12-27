# Requirements Document

## Introduction

This feature enhances the OTP authentication flow to include user consent for personal data processing. When users receive an OTP code (both in Telegram and via email), they will see a consent message informing them that by entering the verification code, they agree to personal data processing. A link to the full data processing agreement document is provided via an inline button in Telegram and a clickable link in the email.

## Glossary

- **OTP**: One-Time Password - a 6-digit verification code sent to user's email
- **Telegram_Bot**: The Prompt Engineering Bot Telegram application
- **Email_Service**: The service responsible for sending emails to users
- **Consent_Message**: The text informing users about personal data processing agreement
- **Agreement_URL**: The URL to the personal data processing agreement document (https://disk.yandex.ru/i/zGiuY7mtIfOA-Q)
- **Inline_Button**: A Telegram button that appears below a message and can open URLs

## Requirements

### Requirement 1: Update OTP Sent Telegram Message with Consent Text

**User Story:** As a user, I want to be informed about personal data processing consent when I receive an OTP code, so that I understand that entering the code constitutes my agreement.

#### Acceptance Criteria

1. WHEN the Telegram_Bot sends the OTP sent confirmation message, THE Telegram_Bot SHALL append the Consent_Message to the existing EMAIL_OTP_SENT message text
2. THE Consent_Message SHALL be displayed in Russian as: "Вводя код подтверждения, вы даёте согласие на обработку персональных данных"
3. THE Consent_Message SHALL be displayed in English as: "By entering the verification code, you consent to the processing of personal data"
4. THE Consent_Message SHALL follow the existing i18n pattern using the `_()` translation helper function

### Requirement 2: Add Inline Button with Agreement Link in Telegram

**User Story:** As a user, I want to access the full personal data processing agreement document, so that I can review the terms before providing consent.

#### Acceptance Criteria

1. WHEN the Telegram_Bot displays the OTP sent message, THE Telegram_Bot SHALL display an Inline_Button below the message
2. THE Inline_Button SHALL have the text "📄 Согласие на обработку персональных данных" in Russian
3. THE Inline_Button SHALL have the text "📄 Personal Data Processing Agreement" in English
4. WHEN a user clicks the Inline_Button, THE Telegram_Bot SHALL open the Agreement_URL (https://disk.yandex.ru/i/zGiuY7mtIfOA-Q)
5. THE Inline_Button text SHALL follow the existing i18n pattern using the `_()` translation helper function

### Requirement 3: Update OTP Email Template with Consent Section

**User Story:** As a user receiving an OTP email, I want to see the consent information prominently displayed, so that I am aware of the data processing agreement before entering the code.

#### Acceptance Criteria

1. WHEN the Email_Service sends an OTP email, THE Email_Service SHALL include a highlighted consent section at the beginning of the email body (before the greeting)
2. THE consent section SHALL contain the same Consent_Message text as the Telegram message
3. THE consent section SHALL contain a clickable button/link with the same text as the Telegram Inline_Button
4. WHEN a user clicks the link in the email, THE link SHALL open the Agreement_URL
5. THE consent section SHALL be visually highlighted to draw user attention
6. THE Email_Service SHALL include the consent section in both HTML and plain text email formats
7. THE consent section text and link text SHALL match the language setting of the email template

### Requirement 4: Maintain Existing Reply Keyboard Functionality

**User Story:** As a user, I want to still have access to the Reset button while viewing the OTP message, so that I can restart the flow if needed.

#### Acceptance Criteria

1. WHEN the Telegram_Bot displays the OTP sent message with the Inline_Button, THE Telegram_Bot SHALL also display the existing Reply Keyboard with the Reset button
2. THE existing Reset button functionality SHALL remain unchanged
