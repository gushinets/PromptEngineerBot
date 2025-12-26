# Design Document: Rename Optimization Methods

## Overview

This design describes the implementation approach for renaming the three optimization methods from technical names (LYRA, CRAFT, GGL) to user-friendly names in Russian and English. The change is purely cosmetic at the user interface level, affecting only display strings while preserving all internal logic and identifiers.

## Architecture

The change follows the existing internationalization pattern in the codebase:
- The `_(text_ru, text_en)` helper function in `messages.py` handles language selection
- The `EmailTemplates` class uses a similar pattern with language parameter
- Button labels, messages, and email templates are centralized in dedicated modules

### Affected Components

```
┌─────────────────────────────────────────────────────────────┐
│                    User-Facing Layer                         │
├─────────────────────────────────────────────────────────────┤
│  telegram_bot/utils/messages.py                              │
│  - BTN_LYRA, BTN_CRAFT, BTN_GGL constants                   │
│  - WELCOME_MESSAGE, WELCOME_MESSAGE_2                        │
│  - SELECT_METHOD_MESSAGE                                     │
│  - IMPROVED_PROMPT_RESPONSE                                  │
├─────────────────────────────────────────────────────────────┤
│  telegram_bot/utils/email_templates.py                       │
│  - get_optimization_html_body()                              │
│  - get_optimization_plain_body()                             │
├─────────────────────────────────────────────────────────────┤
│  tests/unit/test_messages.py                                 │
│  tests/integration/test_bot_handler.py                       │
│  tests/integration/test_post_optimization_integration.py     │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ (unchanged)
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Internal Layer                            │
├─────────────────────────────────────────────────────────────┤
│  OptimizationMethod enum (LYRA, CRAFT, GGL)                 │
│  Prompt files (LYRA_prompt.txt, etc.)                       │
│  Database stored values                                      │
│  Session service method tracking                             │
└─────────────────────────────────────────────────────────────┘
```

## Components and Interfaces

### 1. Button Label Constants (messages.py)

Current:
```python
BTN_CRAFT = _("🛠 CRAFT", "🛠 CRAFT")
BTN_LYRA = _("⚡ LYRA", "⚡ LYRA")
BTN_GGL = _("🔍 GGL", "🔍 GGL")
```

New:
```python
BTN_LYRA = _("⚡ Быстро", "⚡ Quick")
BTN_CRAFT = _("🛠 По шагам", "🛠 Step-by-step")
BTN_GGL = _("🎯 Под результат", "🎯 Result-focused")
```

### 2. Welcome Messages (messages.py)

Update `WELCOME_MESSAGE` and `WELCOME_MESSAGE_2` to use new method names with standardized emojis.

### 3. Method Selection Message (messages.py)

Update `SELECT_METHOD_MESSAGE` to describe methods with new names.

### 4. Email Templates (email_templates.py)

Update method labels in:
- `get_optimization_html_body()` - HTML email body
- `get_optimization_plain_body()` - Plain text email body

### 5. Display Name Mapping

Create a mapping for converting internal identifiers to display names when needed:

| Internal ID | Russian Display | English Display | Emoji |
|-------------|-----------------|-----------------|-------|
| LYRA | Быстро | Quick | ⚡ |
| CRAFT | По шагам | Step-by-step | 🛠 |
| GGL | Под результат | Result-focused | 🎯 |

## Data Models

No data model changes required. The `OptimizationMethod` enum and database schema remain unchanged.

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Emoji-Method Consistency

*For any* user-facing content that references an optimization method, the emoji used SHALL match the standardized mapping:
- LYRA/Быстро/Quick → ⚡
- CRAFT/По шагам/Step-by-step → 🛠
- GGL/Под результат/Result-focused → 🎯

**Validates: Requirements 2.3, 7.1, 7.2, 7.3**

### Property 2: Language Consistency

*For any* language setting (RU or EN), all method display names SHALL use the correct translation while maintaining the same emoji prefix.

**Validates: Requirements 1.1-1.6, 3.4**

## Error Handling

No new error handling required. The changes are purely cosmetic string replacements.

## Testing Strategy

### Unit Tests

Unit tests will verify:
1. Button constants contain expected text and emojis
2. Welcome messages contain new method names
3. Email templates generate correct method labels
4. Legacy emojis (🔍, 🧩) are not present in method-related content

### Property-Based Tests

Due to the nature of this change (static string replacements), property-based testing is not applicable. The correctness properties will be verified through unit tests that check:
- Emoji consistency across all method references
- Language consistency for both RU and EN settings

### Test Files to Update

1. `tests/unit/test_messages.py` - Update button constant assertions
2. `tests/integration/test_bot_handler.py` - Update method button references
3. `tests/integration/test_post_optimization_integration.py` - Update button assertions

### Test Configuration

- Use pytest for all tests
- No property-based testing library needed (changes are deterministic string values)
- Tests should verify both Russian and English translations
