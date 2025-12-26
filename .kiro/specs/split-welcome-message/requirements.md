# Requirements Document

## Introduction

This feature splits the existing single `WELCOME_MESSAGE` into two separate messages to improve user onboarding experience. The first message introduces the bot, while the second message provides detailed instructions on how to use the service, including a support button linking to the helpdesk bot.

## Glossary

- **Welcome_Message_1**: The introductory greeting message that introduces PromptEngineer and its purpose
- **Welcome_Message_2**: The instructional message explaining how to work with PromptEngineer
- **Support_Button**: An inline keyboard button attached to Welcome_Message_2 that links to the support bot
- **InlineKeyboardMarkup**: Telegram's inline keyboard that attaches buttons directly to messages
- **Bot_Handler**: The component responsible for handling Telegram bot interactions and message processing

## Requirements

### Requirement 1: Split Welcome Message into Two Parts

**User Story:** As a user, I want to receive a clear introduction followed by detailed instructions, so that I can understand what the bot does and how to use it.

#### Acceptance Criteria

1. WHEN a user sends the /start command, THE Bot_Handler SHALL send Welcome_Message_1 first
2. WHEN Welcome_Message_1 is sent, THE Bot_Handler SHALL immediately send Welcome_Message_2 after it
3. THE Welcome_Message_1 SHALL contain the bot introduction in Russian and English following the internationalization pattern
4. THE Welcome_Message_2 SHALL contain the usage instructions in Russian and English following the internationalization pattern

### Requirement 2: Welcome Message 1 Content

**User Story:** As a user, I want to see a friendly introduction that explains what the bot does, so that I understand its purpose immediately.

#### Exact Text (Russian)

```
🤖 Привет. Я PromptEngineer.

Я превращаю вашу задачу в готовый промпт для нейросети —
такой, который можно сразу использовать, без правок и догадок.

Не нужно знать, как «правильно» писать запросы.
Просто опишите, что вам нужно сделать.

✍️ Опишите свою задачу — я сделаю из неё промпт, который сработает сразу.
```

#### Exact Text (English)

```
🤖 Hi. I'm PromptEngineer.

I transform your task into a ready-to-use prompt for AI —
one you can use immediately, without edits or guesswork.

You don't need to know how to write prompts "correctly."
Just describe what you need to do.

✍️ Describe your task — I'll create a prompt that works right away.
```

#### Acceptance Criteria

1. THE Welcome_Message_1 SHALL include the greeting "🤖 Привет. Я PromptEngineer." in Russian
2. THE Welcome_Message_1 SHALL explain that the bot transforms tasks into ready-to-use prompts
3. THE Welcome_Message_1 SHALL reassure users they don't need to know how to write prompts correctly
4. THE Welcome_Message_1 SHALL end with a call-to-action to describe their task
5. THE Welcome_Message_1 SHALL have an equivalent English translation maintaining the same structure and semantics

### Requirement 3: Welcome Message 2 Content

**User Story:** As a user, I want to see step-by-step instructions on how to use the bot, so that I can follow the process easily.

#### Exact Text (Russian)

```
ℹ️ Как работать с PromptEngineer

1️⃣ Опишите задачу своими словами
Не нужно думать о формулировках — пишите как есть.

2️⃣ Выберите подходящий вариант оптимизации:
⚡Быстро — короткий и рабочий запрос без лишних деталей
🛠 По шагам — аккуратно разложенный и структурированный запрос
🎯 Под результат — запрос под конкретный формат или итог

3️⃣ Получите готовый промпт
Его можно сразу использовать в нейросети без доработок.

Если у вас возникнут вопросы по работе сервиса, воспользуйтесь кнопкой «Техподдержка» — мы поможем разобраться.
```

#### Exact Text (English)

```
ℹ️ How to work with PromptEngineer

1️⃣ Describe your task in your own words
No need to think about wording — just write as is.

2️⃣ Choose the right optimization option:
⚡Quick — a short, working prompt without extra details
🛠 Step-by-step — a neatly organized and structured prompt
🎯 Result-focused — a prompt for a specific format or outcome

3️⃣ Get your ready prompt
You can use it immediately in AI without any modifications.

If you have questions about the service, use the «Support» button — we'll help you figure it out.
```

#### Acceptance Criteria

1. THE Welcome_Message_2 SHALL include the header "ℹ️ Как работать с PromptEngineer" in Russian
2. THE Welcome_Message_2 SHALL describe three steps: describe task, choose optimization variant, receive ready prompt
3. THE Welcome_Message_2 SHALL explain the three optimization options with emojis (⚡Быстро, 🛠 По шагам, 🎯 Под результат)
4. THE Welcome_Message_2 SHALL mention the support button for questions about the service
5. THE Welcome_Message_2 SHALL have an equivalent English translation maintaining the same structure and semantics

### Requirement 4: Support Button Implementation

**User Story:** As a user, I want to easily access support if I have questions, so that I can get help when needed.

#### Acceptance Criteria

1. WHEN Welcome_Message_2 is sent, THE Bot_Handler SHALL attach an inline keyboard with a Support_Button
2. THE Support_Button SHALL display "Техподдержка" in Russian or "Support" in English based on language setting
3. WHEN a user clicks the Support_Button, THE system SHALL open the URL https://t.me/prompthelpdesk_bot?start
4. THE Support_Button SHALL use InlineKeyboardMarkup with InlineKeyboardButton containing a URL parameter

### Requirement 5: Backward Compatibility

**User Story:** As a developer, I want the existing code to continue working with minimal changes, so that the refactoring doesn't break other functionality.

#### Acceptance Criteria

1. THE messages.py module SHALL export both WELCOME_MESSAGE_1 and WELCOME_MESSAGE_2
2. THE utils/__init__.py module SHALL be updated to export the new message constants
3. THE Bot_Handler SHALL be updated to send both messages in sequence
4. WHEN the reset button is clicked, THE Bot_Handler SHALL send both welcome messages

### Requirement 6: Test Updates

**User Story:** As a developer, I want the tests to verify the new message structure, so that I can ensure the feature works correctly.

#### Acceptance Criteria

1. THE existing tests for WELCOME_MESSAGE SHALL be updated to test WELCOME_MESSAGE_1 and WELCOME_MESSAGE_2
2. THE tests SHALL verify that both messages are non-empty strings
3. THE tests SHALL verify that WELCOME_MESSAGE_1 contains the expected emoji "🤖"
4. THE tests SHALL verify that WELCOME_MESSAGE_2 contains the expected emoji "ℹ️"
