# Design Document

## Overview

This design outlines the approach for refactoring hardcoded string messages from `src/bot_handler.py` and `src/email_flow.py` into the centralized `src/messages.py` file. The refactoring will follow the existing internationalization pattern and maintain all current functionality while improving code maintainability.

## Architecture

The current architecture already has a centralized message system in place:

```
src/messages.py
├── Language Settings (LANGUAGE = "ru")
├── Translation Helper (_() function)
├── UI Elements (buttons)
├── Welcome/Help Messages
├── Error Messages
├── Status Messages
├── Success Messages
└── Keyboard Layouts
```

The refactoring will extend this existing structure by adding new message constants for all hardcoded strings found in the handler files.

## Components and Interfaces

### Message Categories

Based on the analysis of hardcoded strings, the following new message categories will be added:

#### 1. Email Flow Error Messages
- Email input processing errors
- Email service availability errors
- OTP verification errors
- Flow state errors

#### 2. Follow-up Conversation Error Messages
- Timeout handling messages
- Network error messages
- Rate limit messages
- API error messages
- State recovery messages

#### 3. Processing Status Messages
- Optimization processing messages
- Email delivery status messages

#### 4. System Error Messages
- Generic error messages for various failure scenarios

### Message Constant Naming Convention

The design follows these naming patterns:

```python
# Error messages
ERROR_EMAIL_INPUT_FAILED = _("❌ Email input error. Please try again later.", "❌ Email input error. Please try again later.")
ERROR_EMAIL_SERVICE_UNAVAILABLE = _("❌ Email service not available. Please try again later.", "❌ Email service not available. Please try again later.")

# Success/Info messages
INFO_OPTIMIZATION_PROCESSING = _("🔄 Оптимизируем ваш промпт тремя методами и отправляем на email...", "🔄 Optimizing your prompt with three methods and sending to email...")

# Follow-up specific messages
FOLLOWUP_TIMEOUT_FALLBACK = _("Время ожидания истекло. Используем исходный улучшенный промпт:", "Timeout occurred. Using the original improved prompt:")
```

## Data Models

### Message Structure

Each message constant follows this structure:

```python
CONSTANT_NAME = _(
    "Russian text with emojis and formatting",
    "English text with emojis and formatting"
)
```

### Import Structure

The import statements in handler files will be organized as:

```python
from .messages import (
    # Existing imports (alphabetically ordered)
    BTN_RESET,
    ERROR_EMAIL_INVALID,
    # New imports (alphabetically ordered)
    ERROR_EMAIL_INPUT_FAILED,
    ERROR_EMAIL_SERVICE_UNAVAILABLE,
    # ... other new constants
)
```

## Error Handling

### Backward Compatibility

The refactoring maintains backward compatibility by:

1. **Preserving exact message text**: All user-facing messages will display exactly the same text as before
2. **Maintaining formatting**: All emoji, markdown, and formatting will be preserved
3. **Keeping function signatures**: No changes to `_safe_reply()` call signatures

### Error Prevention

To prevent errors during refactoring:

1. **Systematic replacement**: Each hardcoded string will be replaced one at a time with immediate testing
2. **Import validation**: New imports will be added incrementally to avoid missing import errors
3. **Message validation**: Each new message constant will be validated for correct formatting

## Testing Strategy

### Manual Testing Approach

Since this is a refactoring task that doesn't change functionality:

1. **Message Display Testing**: Verify that each refactored message displays correctly in the bot
2. **Flow Testing**: Test complete user flows to ensure no messages are broken
3. **Import Testing**: Verify that all imports resolve correctly
4. **Language Testing**: Confirm that the Russian language setting still works correctly

### Validation Checklist

For each refactored message:
- [ ] Message constant created in `messages.py`
- [ ] Russian and English translations provided
- [ ] Import added to handler file
- [ ] Hardcoded string replaced with constant
- [ ] Message displays correctly in bot
- [ ] No syntax or import errors

## Implementation Phases

### Phase 1: Message Identification and Categorization
- Catalog all hardcoded strings from both files
- Group messages by category and purpose
- Define naming conventions for new constants

### Phase 2: Message Constant Creation
- Add new message constants to `messages.py`
- Follow existing patterns and naming conventions
- Ensure proper Russian/English translations

### Phase 3: Import Updates
- Add new message imports to `src/bot_handler.py`
- Add new message imports to `src/email_flow.py`
- Maintain alphabetical ordering

### Phase 4: String Replacement
- Replace hardcoded strings with message constants
- Update one file at a time to minimize risk
- Test each replacement immediately

### Phase 5: Cleanup and Validation
- Remove any unused imports
- Verify no hardcoded strings remain
- Perform comprehensive testing

## Specific Messages to Refactor

### From `src/bot_handler.py`:

1. **Email Service Errors**:
   - "❌ Email input error. Please try again later."
   - "❌ Email service not available. Please try again later."
   - "❌ OTP verification error. Please try again later."
   - "❌ Email service error. Please try again later."

2. **Follow-up Error Messages**:
   - "Время ожидания истекло. Используем исходный улучшенный промпт:"
   - "Время ожидания истекло. Попробуйте начать с нового промпта."
   - "Проблемы с сетью. Используем исходный улучшенный промпт:"
   - "Проблемы с сетью. Попробуйте начать с нового промпта."
   - "Превышен лимит запросов. Используем исходный улучшенный промпт:"
   - "Превышен лимит запросов. Попробуйте позже."
   - "Ошибка API. Используем исходный улучшенный промпт:"
   - "Ошибка API. Попробуйте начать с нового промпта."
   - "Произошла ошибка. Попробуйте начать с нового промпта."

3. **State Recovery Messages**:
   - "Не удалось получить улучшенный промпт. Используем исходный:"
   - "Не удалось сгенерировать улучшенный промпт. Попробуйте начать заново."
   - "Восстанавливаем состояние диалога. Используем ваш улучшенный промпт:"
   - "Состояние диалога повреждено. Начните с нового промпта."
   - "Не удалось восстановить состояние. Начните с нового промпта."

### From `src/email_flow.py`:

1. **Flow Error Messages**:
   - "❌ Не удалось найти исходный промпт. Пожалуйста, начните заново."
   - "❌ Произошла ошибка при запуске email-потока. Попробуйте позже."
   - "❌ Произошла ошибка при обработке email. Попробуйте позже."
   - "❌ Произошла ошибка при проверке кода. Попробуйте позже."

2. **Validation Messages**:
   - "❌ Код должен состоять из 6 цифр. Попробуйте еще раз:"

3. **Processing Messages**:
   - "🔄 Оптимизируем ваш промпт тремя методами и отправляем на email..."
   - "🔄 Запускаем оптимизацию промпта всеми тремя методами..."

4. **Success Messages**:
   - "✅ Все оптимизированные промпты отправлены в чат!"

5. **System Messages**:
   - Template strings for optimization method prompts
   - Error messages for optimization failures

## Design Decisions

### 1. Preserve Existing Pattern
**Decision**: Follow the existing `_()` function pattern for all new messages
**Rationale**: Maintains consistency with the current codebase and translation system

### 2. Maintain Message Grouping
**Decision**: Group related messages together in `messages.py` with clear section headers
**Rationale**: Improves maintainability and makes it easier to find related messages

### 3. Incremental Refactoring
**Decision**: Refactor one file at a time, testing each change
**Rationale**: Minimizes risk and makes it easier to identify and fix any issues

### 4. Preserve Exact Text
**Decision**: Keep the exact same text for all messages, including emojis and formatting
**Rationale**: Ensures no functional changes and maintains user experience