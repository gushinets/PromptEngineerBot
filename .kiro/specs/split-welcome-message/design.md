# Design Document: Split Welcome Message

## Overview

This design describes the implementation of splitting the existing `WELCOME_MESSAGE` into two separate messages (`WELCOME_MESSAGE_1` and `WELCOME_MESSAGE_2`) with an inline support button attached to the second message. The implementation follows the existing internationalization pattern using the `_()` helper function and introduces `InlineKeyboardMarkup` for the support button.

## Architecture

The feature modifies three main components:

1. **messages.py** - Define new message constants and support button keyboard
2. **bot_handler.py** - Update `handle_start` to send both messages with the support button
3. **utils/__init__.py** - Export new message constants

```
┌─────────────────────────────────────────────────────────────────┐
│                        User sends /start                         │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      BotHandler.handle_start()                   │
│  1. Reset user state                                             │
│  2. Send WELCOME_MESSAGE_1 (no keyboard)                         │
│  3. Send WELCOME_MESSAGE_2 with SUPPORT_KEYBOARD (inline button) │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                         User sees:                               │
│  Message 1: Introduction (🤖 Привет. Я PromptEngineer...)       │
│  Message 2: Instructions (ℹ️ Как работать...) + [Техподдержка]  │
└─────────────────────────────────────────────────────────────────┘
```

## Components and Interfaces

### messages.py Changes

```python
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup

# New message constants
WELCOME_MESSAGE_1 = _(
    "🤖 Привет. Я PromptEngineer.\n\n"
    "Я превращаю вашу задачу в готовый промпт для нейросети —\n"
    "такой, который можно сразу использовать, без правок и догадок.\n\n"
    "Не нужно знать, как «правильно» писать запросы.\n"
    "Просто опишите, что вам нужно сделать.\n\n"
    "✍️ Опишите свою задачу — я сделаю из неё промпт, который сработает сразу.",
    "🤖 Hi. I'm PromptEngineer.\n\n"
    "I transform your task into a ready-to-use prompt for AI —\n"
    "one you can use immediately, without edits or guesswork.\n\n"
    "You don't need to know how to write prompts \"correctly.\"\n"
    "Just describe what you need to do.\n\n"
    "✍️ Describe your task — I'll create a prompt that works right away.",
)

WELCOME_MESSAGE_2 = _(
    "ℹ️ Как работать с PromptEngineer\n\n"
    "1️⃣ Опишите задачу своими словами\n"
    "Не нужно думать о формулировках — пишите как есть.\n\n"
    "2️⃣ Выберите подходящий вариант оптимизации:\n"
    "⚡Быстро — короткий и рабочий запрос без лишних деталей\n"
    "🛠 По шагам — аккуратно разложенный и структурированный запрос\n"
    "🎯 Под результат — запрос под конкретный формат или итог\n\n"
    "3️⃣ Получите готовый промпт\n"
    "Его можно сразу использовать в нейросети без доработок.\n\n"
    "Если у вас возникнут вопросы по работе сервиса, воспользуйтесь кнопкой «Техподдержка» — мы поможем разобраться.",
    "ℹ️ How to work with PromptEngineer\n\n"
    "1️⃣ Describe your task in your own words\n"
    "No need to think about wording — just write as is.\n\n"
    "2️⃣ Choose the right optimization option:\n"
    "⚡Quick — a short, working prompt without extra details\n"
    "🛠 Step-by-step — a neatly organized and structured prompt\n"
    "🎯 Result-focused — a prompt for a specific format or outcome\n\n"
    "3️⃣ Get your ready prompt\n"
    "You can use it immediately in AI without any modifications.\n\n"
    "If you have questions about the service, use the «Support» button — we'll help you figure it out.",
)

# Support button label
BTN_SUPPORT = _("🆘 Техподдержка", "🆘 Support")

# Support URL
SUPPORT_BOT_URL = "https://t.me/prompthelpdesk_bot?start"

# Inline keyboard with support button
SUPPORT_KEYBOARD = InlineKeyboardMarkup([
    [InlineKeyboardButton(BTN_SUPPORT, url=SUPPORT_BOT_URL)]
])
```

### bot_handler.py Changes

```python
from telegram_bot.utils.messages import (
    # ... existing imports ...
    WELCOME_MESSAGE_1,
    WELCOME_MESSAGE_2,
    SUPPORT_KEYBOARD,
)

async def handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /start command or New Prompt button."""
    user_id = update.effective_user.id

    # Track user interaction (existing code)
    if self.user_tracking_service:
        tracked_user, is_first_time = self.user_tracking_service.track_user_interaction(
            user_id, update.effective_user
        )
        if tracked_user is None:
            logger.warning(
                f"User tracking returned None for user_id={user_id} in handle_start, continuing with request"
            )

    # Reset user state
    self.reset_user_state(user_id)

    # Send welcome message 1 (introduction)
    await self._safe_reply(
        update,
        WELCOME_MESSAGE_1,
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup([[]], resize_keyboard=True),
    )

    # Send welcome message 2 (instructions) with support button
    await self._safe_reply(
        update,
        WELCOME_MESSAGE_2,
        parse_mode="Markdown",
        reply_markup=SUPPORT_KEYBOARD,
    )
```

### utils/__init__.py Changes

```python
from telegram_bot.utils.messages import (
    SELECT_METHOD_MESSAGE,
    WELCOME_MESSAGE_1,
    WELCOME_MESSAGE_2,
    SUPPORT_KEYBOARD,
    BTN_SUPPORT,
    # ... other existing exports ...
)

__all__ = [
    "SELECT_METHOD_MESSAGE",
    "WELCOME_MESSAGE_1",
    "WELCOME_MESSAGE_2",
    "SUPPORT_KEYBOARD",
    "BTN_SUPPORT",
    # ... other existing exports ...
]
```

## Data Models

No new data models are required. The feature uses existing Telegram types:

- `InlineKeyboardMarkup` - Container for inline keyboard buttons
- `InlineKeyboardButton` - Button with URL parameter for external links

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

Based on the prework analysis, most acceptance criteria are example-based tests for specific content or behavior. The feature has limited scope for property-based testing since:

1. Language options are finite (only 'ru' and 'en')
2. Message content is static and deterministic
3. Button configuration is fixed

**Property 1: Language-consistent button label**

*For any* valid language setting ('ru' or 'en'), the BTN_SUPPORT label SHALL match the expected localized text for that language.

**Validates: Requirements 4.2**

**Property 2: Message content consistency**

*For any* language setting, WELCOME_MESSAGE_1 and WELCOME_MESSAGE_2 SHALL be non-empty strings containing their respective identifying emojis (🤖 and ℹ️).

**Validates: Requirements 2.1, 3.1, 6.2, 6.3, 6.4**

## Error Handling

| Error Scenario | Handling Strategy |
|----------------|-------------------|
| First message send fails | Log error, attempt to send second message anyway |
| Second message send fails | Log error, user still received first message |
| InlineKeyboard creation fails | Fall back to sending message without keyboard |

The `_safe_reply` method already handles Telegram API errors gracefully, so no additional error handling is required.

## Testing Strategy

### Unit Tests

Unit tests will verify:

1. **Message content tests** (test_messages.py)
   - WELCOME_MESSAGE_1 is non-empty and contains "🤖"
   - WELCOME_MESSAGE_2 is non-empty and contains "ℹ️"
   - WELCOME_MESSAGE_1 contains key phrases for both languages
   - WELCOME_MESSAGE_2 contains step markers (1️⃣, 2️⃣, 3️⃣)
   - BTN_SUPPORT contains expected text

2. **Keyboard configuration tests** (test_messages.py)
   - SUPPORT_KEYBOARD is an InlineKeyboardMarkup
   - Support button has correct URL

3. **Module export tests**
   - WELCOME_MESSAGE_1 importable from utils
   - WELCOME_MESSAGE_2 importable from utils
   - SUPPORT_KEYBOARD importable from utils

### Integration Tests

Integration tests will verify:

1. **Bot handler tests** (test_bot_handler_integration.py)
   - handle_start sends both messages in sequence
   - Second message includes inline keyboard
   - Reset button triggers both welcome messages

### Property-Based Tests

Given the limited scope (2 language options, static content), property-based testing provides minimal additional value over example-based tests. The properties identified above will be implemented as parameterized tests covering both language settings.

### Test Configuration

- Use pytest for test execution
- Mock Telegram API calls in unit tests
- Use existing test fixtures for bot handler integration tests
