# Requirements Document

## Introduction

This document specifies the requirements for renaming the three optimization methods in the Telegram bot from their current technical names (LYRA, CRAFT, GGL) to user-friendly names in Russian and English. The change affects only user-facing content while preserving all internal code identifiers, prompt files, and system logic.

## Glossary

- **Optimization_Method**: A prompt improvement technique offered to users (LYRA, CRAFT, or GGL internally)
- **User_Facing_Content**: Text displayed to users in the Telegram bot interface, buttons, messages, and emails
- **Button_Label**: Text displayed on keyboard buttons in the Telegram interface
- **Email_Template**: HTML and plain text templates used for sending optimization results via email
- **Messages_Module**: The `telegram_bot/utils/messages.py` file containing all user-facing text
- **Internal_Identifier**: Code-level identifiers (enum values, variable names, file names) that remain unchanged

## Requirements

### Requirement 1: Rename Button Labels

**User Story:** As a user, I want to see descriptive method names on buttons, so that I can understand what each optimization method does without knowing technical terminology.

#### Acceptance Criteria

1. WHEN the method selection keyboard is displayed, THE System SHALL show "⚡ Быстро" for the LYRA method button in Russian
2. WHEN the method selection keyboard is displayed, THE System SHALL show "🛠 По шагам" for the CRAFT method button in Russian
3. WHEN the method selection keyboard is displayed, THE System SHALL show "🎯 Под результат" for the GGL method button in Russian
4. WHEN the language is set to English, THE System SHALL show "⚡ Quick" for the LYRA method button
5. WHEN the language is set to English, THE System SHALL show "🛠 Step-by-step" for the CRAFT method button
6. WHEN the language is set to English, THE System SHALL show "🎯 Result-focused" for the GGL method button

### Requirement 2: Update Welcome and Help Messages

**User Story:** As a user, I want to see consistent method names in welcome and help messages, so that I understand the available optimization options.

#### Acceptance Criteria

1. WHEN the welcome message is displayed, THE System SHALL use the new method names with standardized emojis (⚡, 🛠, 🎯)
2. WHEN the help/instructions message is displayed, THE System SHALL describe methods using the new names
3. THE System SHALL maintain consistency between button labels and message descriptions

### Requirement 3: Update Email Templates

**User Story:** As a user, I want to see the new method names in emails I receive, so that the email content matches what I see in the bot interface.

#### Acceptance Criteria

1. WHEN an optimization email is sent, THE System SHALL use "⚡ Быстро" / "⚡ Quick" for LYRA results in the email body
2. WHEN an optimization email is sent, THE System SHALL use "🛠 По шагам" / "🛠 Step-by-step" for CRAFT results in the email body
3. WHEN an optimization email is sent, THE System SHALL use "🎯 Под результат" / "🎯 Result-focused" for GGL results in the email body
4. THE System SHALL apply the correct language based on the email template language setting

### Requirement 4: Update Method Selection Message

**User Story:** As a user, I want to see the new method names in the method selection prompt, so that I can make an informed choice.

#### Acceptance Criteria

1. WHEN the method selection message is displayed, THE System SHALL list methods with new names and descriptions
2. THE System SHALL use standardized emojis (⚡, 🛠, 🎯) consistently in the selection message

### Requirement 5: Preserve Internal Identifiers

**User Story:** As a developer, I want internal code identifiers to remain unchanged, so that the codebase remains stable and backward compatible.

#### Acceptance Criteria

1. THE System SHALL keep the `OptimizationMethod` enum values as LYRA, CRAFT, GGL
2. THE System SHALL keep prompt file names as `LYRA_prompt.txt`, `CRAFT_prompt.txt`, `GGL_prompt.txt`
3. THE System SHALL keep all internal variable names and function parameters unchanged
4. THE System SHALL keep database field values unchanged (stored method values remain LYRA/CRAFT/GGL)

### Requirement 6: Update Tests

**User Story:** As a developer, I want tests to verify the new button labels, so that the renaming is properly validated.

#### Acceptance Criteria

1. WHEN tests check button constants, THE Test_Suite SHALL verify the new button text values
2. WHEN tests check for method names in UI, THE Test_Suite SHALL use the new display names
3. THE Test_Suite SHALL continue to use internal identifiers (LYRA, CRAFT, GGL) for non-UI assertions

### Requirement 7: Maintain Emoji Consistency

**User Story:** As a user, I want to see consistent emojis across all interfaces, so that I can easily identify each method.

#### Acceptance Criteria

1. THE System SHALL use ⚡ emoji exclusively for the LYRA/Быстро/Quick method
2. THE System SHALL use 🛠 emoji exclusively for the CRAFT/По шагам/Step-by-step method
3. THE System SHALL use 🎯 emoji exclusively for the GGL/Под результат/Result-focused method
4. THE System SHALL remove any legacy emoji usage (🔍, 🧩) for these methods
