# Manual Test Plan — Telegram Prompt Engineering Bot

**Document Version**: 1.0  
**Created**: January 2026  
**Author**: QA Engineer (Gray-box Testing)  
**Status**: Ready for Execution

---

# DELIVERABLE A — MANUAL TEST PLAN

## 1. Overview

### 1.1 Purpose
This test plan covers functional manual testing of the **Telegram Prompt Engineering Bot** — a Telegram bot that transforms user task descriptions into optimized prompts for AI systems (ChatGPT, Claude, Gemini, etc.).

### 1.2 Features Under Test
- **Onboarding flow** (`/start` command, welcome messages)
- **Single-method prompt optimization** (CRAFT, LYRA, GGL methods)
- **Follow-up question system** (refine prompts through Q&A)
- **Email delivery flow** (OTP authentication, receive all 3 optimized prompts)
- **Post-optimization email** (send final result to email)
- **State management** (user state transitions, conversation context)
- **Error handling** (invalid inputs, timeouts, service failures)
- **Localization** (Russian and English interfaces)

### 1.3 Bot Interaction Methods
- **Command**: `/start`
- **Text messages**: User prompts, email addresses, OTP codes, follow-up answers
- **Reply keyboard buttons**: Method selection, Yes/No, Generate, Reset
- **Inline keyboard buttons**: Follow-up Yes/No (attached to messages)
- **Inline button**: Support link

---

## 2. In-Scope / Out-of-Scope

### 2.1 In-Scope

| Area | Description |
|------|-------------|
| **Functional Testing** | All user-visible features, commands, buttons, and flows |
| **State Transitions** | User state changes between prompt input, method selection, follow-up, email flow |
| **Input Validation** | Email format, OTP format, empty/long messages |
| **Error Handling** | All user-facing error messages and recovery paths |
| **Concurrency/Idempotency** | Repeated button presses, resending commands, out-of-order actions |
| **Email Authentication** | OTP generation, verification, rate limiting, expiry |
| **Timeout Behavior** | OTP expiry, follow-up timeout, LLM processing timeout |
| **Localization** | Russian (default) and English message verification |

### 2.2 Out-of-Scope

| Area | Reason |
|------|--------|
| **Performance/Load Testing** | Requires specialized tools and environment |
| **LLM Response Quality** | AI-generated content varies; focus is on delivery, not content quality |
| **Infrastructure Testing** | Server, database, Redis internals — not accessible to manual tester |
| **API-level Testing** | Direct API calls bypassing Telegram interface |
| **Mobile App Testing** | Testing specific Telegram client behavior (iOS, Android differences) |
| **Google Sheets Logging Verification** | Requires backend access |

---

## 3. Test Environment Setup

### 3.1 Required Environment Variables / Configuration

The bot requires the following environment configuration (tester does not need to set these, but should verify with DevOps):

| Variable | Purpose | Required |
|----------|---------|----------|
| `TELEGRAM_TOKEN` | Bot authentication with Telegram | Yes |
| `LLM_BACKEND` | AI backend (`OPENAI` or `OPENROUTER`) | Yes |
| `OPENAI_API_KEY` or `OPENROUTER_API_KEY` | LLM API access | Yes |
| `DATABASE_URL` | PostgreSQL/SQLite connection | Yes |
| `REDIS_URL` | Redis for OTP/rate limiting | Yes (for email features) |
| `SMTP_HOST`, `SMTP_USERNAME`, `SMTP_PASSWORD` | Email delivery | Yes (for email features) |
| `EMAIL_ENABLED` | Toggle email features | Yes |
| `LANGUAGE` | Default language (`RU` or `EN`) | Optional (default: `EN`) |

### 3.2 External Dependencies

| Service | Purpose | Health Check Indicator |
|---------|---------|------------------------|
| **LLM API** | Prompt optimization | Bot responds to prompts |
| **PostgreSQL/SQLite** | User data, sessions | User authentication persists |
| **Redis** | OTP storage, rate limiting, flow states | Email flow works |
| **SMTP Server** | Email delivery | Emails arrive |

### 3.3 How to Connect to the Bot

1. Open Telegram (mobile app or desktop)
2. Search for the bot username (provided by test environment owner)
3. Tap **Start** or send `/start`
4. Bot should respond with welcome message

**Environment Notes:**
- **Development**: Usually connected to test database, may have relaxed rate limits
- **Staging**: Mirrors production configuration
- **Production**: Real users, strict rate limits, production email server

---

## 4. Test Data Needed

### 4.1 Test User Accounts

| Account Type | Purpose | Requirements |
|--------------|---------|--------------|
| **New user** | First-time interaction tests | Fresh Telegram account that has never interacted with the bot |
| **Existing user (unauthenticated)** | User who used bot but never verified email | Account with history but no email |
| **Existing user (authenticated)** | User with verified email | Account that completed email verification |

### 4.2 Test Email Addresses

| Email Type | Purpose | Notes |
|------------|---------|-------|
| **Valid test email** | Normal OTP verification | Use real email you can access |
| **Invalid format emails** | Validation tests | `notanemail`, `@nodomain`, `missing@.com` |
| **Rate-limited email** | Rate limit tests | Use same email 4+ times within hour |

### 4.3 Sample Test Prompts

```
Short prompt (simple): "Write a marketing email"

Medium prompt (typical): "Create a business plan for a mobile app startup that helps people find local fitness classes and personal trainers"

Long prompt (edge case): [500+ character description with multiple requirements]

Special characters: "Write code for a Python function that calculates n! (factorial) using recursion"

Multi-line prompt:
"I need a prompt for:
1. Writing a blog post
2. About technology trends
3. With SEO optimization"
```

### 4.4 OTP Test Codes

| Code Type | Value | Purpose |
|-----------|-------|---------|
| **Valid OTP** | From email | Normal verification |
| **Invalid OTP** | `000000`, `123456` | Rejection testing |
| **Expired OTP** | Wait 5+ minutes | Expiry testing |
| **Non-numeric** | `abcdef`, `12345a` | Format validation |

---

## 5. Entry / Exit Criteria

### 5.1 Entry Criteria

- [ ] Bot is deployed and responding to `/start`
- [ ] Test Telegram account(s) available
- [ ] Test email address(es) accessible
- [ ] Environment configuration confirmed with DevOps
- [ ] Test data prepared (sample prompts)

### 5.2 Exit Criteria

- [ ] All P0 (Critical) test cases executed
- [ ] All P1 (High) test cases executed
- [ ] P0/P1 pass rate ≥ 95%
- [ ] No blocking defects open
- [ ] All major user flows verified
- [ ] Test results documented

### 5.3 Suspension Criteria

- Bot not responding to commands
- LLM API returning errors on all requests
- Email service completely unavailable (for email flow tests)
- Database connection failures (authentication not working)

---

## 6. Risks & Areas Likely to Break

### 6.1 High-Risk Areas

| Area | Risk | Indicators |
|------|------|------------|
| **State Management** | User gets stuck in wrong state | Unable to proceed after Reset |
| **Follow-up Flow** | Complex state transitions | Follow-up questions don't appear or get lost |
| **OTP Rate Limiting** | Multiple counters (email, user, spacing) | Users blocked too early or not at all |
| **Inline Button Handling** | Callback query vs text message routing | Buttons don't respond or trigger wrong action |
| **Email Flow Transitions** | Multiple services must coordinate | Flow breaks after OTP verification |
| **Timeout Handling** | 5-minute follow-up timeout | Users lose work or get stuck |
| **Message Parsing** | LLM response parsing for tags | Improved prompt not extracted correctly |

### 6.2 Areas with Complex Logic (Bug-Prone)

1. **Session/State Reset** — Multiple state flags must be reset together
2. **Post-optimization Result Caching** — Result must survive state transitions for email button
3. **Authenticated User Skip Logic** — Already-authenticated users should skip OTP
4. **Follow-up Callback vs Text Buttons** — Both YES/NO inline and text buttons exist
5. **Rate Limit Counter Reset** — Hourly counters, 60-second spacing

### 6.3 External Dependency Failures

| Dependency | Failure Impact | Expected Behavior |
|------------|----------------|-------------------|
| LLM API | Cannot optimize prompts | Error message, suggest retry |
| Redis | Email flow blocked | "Service temporarily unavailable" |
| SMTP | Emails not delivered | Error message (no chat fallback) |
| Database | Auth state lost | May need re-verification |

---

## 7. Test Coverage Map

### 7.1 Feature → Handler → Test Case Mapping

| Feature/Flow | Commands/Buttons/Callbacks | Test Case IDs |
|--------------|---------------------------|---------------|
| **Onboarding** | `/start` | TC-001, TC-002, TC-003 |
| **Welcome Messages** | (automatic) | TC-004, TC-005 |
| **Prompt Input** | Text message | TC-006, TC-007, TC-008 |
| **Method Selection** | `⚡ Quick`, `🛠 Step-by-step`, `🎯 Result-focused` | TC-009, TC-010, TC-011, TC-012 |
| **Optimization Processing** | (automatic) | TC-013, TC-014 |
| **Follow-up Offer** | Inline `✅YES`, `❌NO` | TC-015, TC-016, TC-017, TC-018 |
| **Follow-up Conversation** | Text answers, `🤖Generate Prompt` | TC-019, TC-020, TC-021, TC-022 |
| **Reset Button** | `🔄 Reset Conversation` | TC-023, TC-024, TC-025 |
| **Email Flow Start** | `📧 Send 3 prompts to email` | TC-026, TC-027 |
| **Email Input** | Text email | TC-028, TC-029, TC-030 |
| **OTP Verification** | 6-digit code | TC-031, TC-032, TC-033, TC-034, TC-035 |
| **Email Delivery** | (automatic) | TC-036, TC-037 |
| **Post-optimization Email** | `📧 Send prompt to e-mail` | TC-038, TC-039, TC-040 |
| **Error Handling** | Various | TC-041, TC-042, TC-043, TC-044 |
| **Rate Limiting** | (automatic) | TC-045, TC-046, TC-047 |
| **Timeout Handling** | (automatic) | TC-048, TC-049 |
| **State Persistence** | N/A (after restart) | TC-050, TC-051 |
| **Concurrency/Repeated Actions** | Multiple clicks | TC-052, TC-053, TC-054, TC-055 |
| **Localization** | Language toggle | TC-056, TC-057 |
| **Support Button** | `🆘 Support` | TC-058 |

---

# DELIVERABLE B — MANUAL TEST CASES

---

## SECTION 1: ONBOARDING & WELCOME FLOW

---

### Test Case ID: TC-001
**Title**: First-time user sends /start command  
**Priority**: P0  
**Type**: Positive  
**Preconditions**:
- Telegram account that has never interacted with this bot
- Bot is running and accessible

**Test Data**: None

**Steps**:
1. Open Telegram and search for the bot username
2. Tap on the bot to open chat
3. Send the command `/start`

**Expected Result**:
- Bot sends **two separate messages**:
  1. First message: Welcome/introduction (contains "PromptEngineer" or equivalent)
  2. Second message: Instructions with "How to work" / "Как работать" content
- Second message has inline button "🆘 Support" / "🆘 Техподдержка"
- Reply keyboard is cleared or minimal
- No errors displayed

**Post-conditions (state after test)**:
- User state is "waiting_for_prompt"
- User can type a prompt to continue

**Notes**: Language depends on bot configuration (`LANGUAGE` env var)

---

### Test Case ID: TC-002
**Title**: Existing user sends /start to reset conversation  
**Priority**: P0  
**Type**: Positive  
**Preconditions**:
- User has previously interacted with the bot
- User may be in any state (method selection, follow-up, etc.)

**Test Data**: None

**Steps**:
1. Start any flow (e.g., enter a prompt, select method)
2. Send `/start` command before completing the flow

**Expected Result**:
- Bot sends welcome messages (same as TC-001)
- Previous conversation state is reset
- User is back to "waiting_for_prompt" state
- No error messages

**Post-conditions**:
- All previous state cleared
- User can start fresh

**Notes**: This tests the reset behavior of /start

---

### Test Case ID: TC-003
**Title**: Send /start multiple times consecutively  
**Priority**: P1  
**Type**: Edge  
**Preconditions**:
- Bot is running

**Test Data**: None

**Steps**:
1. Send `/start`
2. Wait for welcome messages
3. Immediately send `/start` again
4. Repeat step 3 two more times

**Expected Result**:
- Each `/start` command triggers welcome messages
- No errors or bot crashes
- Bot remains responsive
- State is properly reset each time

**Post-conditions**:
- User in "waiting_for_prompt" state

**Notes**: Tests idempotency of /start

---

### Test Case ID: TC-004
**Title**: Verify welcome message content (Russian)  
**Priority**: P1  
**Type**: Positive  
**Preconditions**:
- Bot configured with `LANGUAGE=RU`

**Test Data**: None

**Steps**:
1. Send `/start`
2. Read both welcome messages

**Expected Result**:
- First message contains: "Привет", "PromptEngineer", "превращаю"
- Second message contains: "Как работать", "Опишите задачу", "Быстро", "По шагам", "Под результат"
- Support button text: "🆘 Техподдержка"

**Post-conditions**: N/A

**Notes**: Exact text may vary; verify key elements are present

---

### Test Case ID: TC-005
**Title**: Verify welcome message content (English)  
**Priority**: P1  
**Type**: Positive  
**Preconditions**:
- Bot configured with `LANGUAGE=EN`

**Test Data**: None

**Steps**:
1. Send `/start`
2. Read both welcome messages

**Expected Result**:
- First message contains: "Hi", "PromptEngineer", "transform"
- Second message contains: "How to work", "Describe your task", "Quick", "Step-by-step", "Result-focused"
- Support button text: "🆘 Support"

**Post-conditions**: N/A

**Notes**: Exact text may vary; verify key elements are present

---

## SECTION 2: PROMPT INPUT & METHOD SELECTION

---

### Test Case ID: TC-006
**Title**: Enter a valid prompt and see method selection  
**Priority**: P0  
**Type**: Positive  
**Preconditions**:
- User has sent `/start` and is waiting for prompt

**Test Data**: 
```
Write a professional email to request a meeting with a potential client
```

**Steps**:
1. After welcome messages, type and send the test prompt
2. Observe bot response

**Expected Result**:
- Bot acknowledges receipt: "📝 **Ваш запрос получен!**" / "📝 **Your request has been received!**"
- Reply keyboard appears with 4 buttons:
  - `📧 Send 3 prompts to email` (or Russian equivalent)
  - `⚡ Quick`, `🛠 Step-by-step`, `🎯 Result-focused` (or Russian)
- Additional row with `🔄 Reset`
- Message explains each method briefly

**Post-conditions**:
- User state is "waiting_for_method"
- Prompt is stored for processing

**Notes**: None

---

### Test Case ID: TC-007
**Title**: Enter an empty message  
**Priority**: P2  
**Type**: Negative  
**Preconditions**:
- User is waiting for prompt input

**Test Data**: (empty message - just spaces)

**Steps**:
1. Send a message containing only spaces

**Expected Result**:
- Telegram may prevent sending empty messages
- If sent: Bot either ignores or shows "Please provide a message"
- Bot should not crash or enter invalid state

**Post-conditions**:
- User still in "waiting_for_prompt" state

**Notes**: Telegram client behavior varies; some clients prevent empty messages

---

### Test Case ID: TC-008
**Title**: Enter a very long prompt (500+ characters)  
**Priority**: P1  
**Type**: Edge  
**Preconditions**:
- User is waiting for prompt input

**Test Data**:
```
I need you to create a comprehensive marketing strategy document for a new SaaS product launch. The product is a project management tool designed for remote teams. Include sections on target audience analysis, competitive landscape, positioning strategy, messaging framework, content marketing plan, social media strategy, email marketing campaigns, paid advertising recommendations, influencer partnerships, launch timeline with key milestones, success metrics and KPIs, budget allocation recommendations, and risk mitigation strategies. The document should be suitable for presenting to C-level executives and should include data-driven recommendations where possible. Consider both B2B and B2C segments.
```

**Steps**:
1. Copy and paste the long prompt
2. Send to bot

**Expected Result**:
- Bot accepts the prompt without truncation
- Method selection appears normally
- No timeout or error messages

**Post-conditions**:
- Full prompt stored for processing

**Notes**: Tests handling of longer inputs

---

### Test Case ID: TC-009
**Title**: Select CRAFT (Step-by-step) method  
**Priority**: P0  
**Type**: Positive  
**Preconditions**:
- User has entered prompt and sees method selection

**Test Data**: Any valid prompt from TC-006

**Steps**:
1. Tap the `🛠 Step-by-step` / `🛠 По шагам` button

**Expected Result**:
- Bot shows "🔄 Processing..." message (or equivalent)
- After processing (5-60 seconds), bot sends optimized prompt
- Optimized prompt is substantially different/better structured than original
- Follow-up offer appears with YES/NO inline buttons
- Reset button visible in keyboard

**Post-conditions**:
- User sees optimized prompt
- User is in "waiting_for_followup_choice" state

**Notes**: Processing time varies based on LLM response time

---

### Test Case ID: TC-010
**Title**: Select LYRA (Quick) method  
**Priority**: P0  
**Type**: Positive  
**Preconditions**:
- User has entered prompt and sees method selection

**Test Data**: Any valid prompt

**Steps**:
1. Tap the `⚡ Quick` / `⚡ Быстро` button

**Expected Result**:
- Bot processes and returns optimized prompt
- Follow-up offer with inline YES/NO buttons
- Reset button available

**Post-conditions**:
- User in "waiting_for_followup_choice" state

**Notes**: LYRA is designed to be faster/simpler

---

### Test Case ID: TC-011
**Title**: Select GGL (Result-focused) method  
**Priority**: P0  
**Type**: Positive  
**Preconditions**:
- User has entered prompt and sees method selection

**Test Data**: Any valid prompt

**Steps**:
1. Tap the `🎯 Result-focused` / `🎯 Под результат` button

**Expected Result**:
- Bot processes and returns optimized prompt
- Follow-up offer with inline YES/NO buttons
- Reset button available

**Post-conditions**:
- User in "waiting_for_followup_choice" state

**Notes**: None

---

### Test Case ID: TC-012
**Title**: Send random text during method selection  
**Priority**: P1  
**Type**: Negative  
**Preconditions**:
- User has entered prompt and sees method selection keyboard

**Test Data**: "hello" or "test"

**Steps**:
1. Instead of clicking a button, type and send "hello"

**Expected Result**:
- Bot re-shows method selection message and buttons
- No error message
- User can then select a valid method

**Post-conditions**:
- User still in "waiting_for_method" state

**Notes**: Tests handling of unexpected input during method selection

---

## SECTION 3: PROMPT OPTIMIZATION PROCESSING

---

### Test Case ID: TC-013
**Title**: Verify processing message appears during optimization  
**Priority**: P1  
**Type**: Positive  
**Preconditions**:
- User has entered prompt and selected a method

**Test Data**: Any prompt

**Steps**:
1. Select any optimization method
2. Immediately observe the chat

**Expected Result**:
- Bot sends a "processing" message within 2 seconds
- Message contains: "🔄" and "Processing" / "Обрабатываю"
- Keyboard shows Reset button during processing

**Post-conditions**: N/A

**Notes**: Important for user feedback during potentially long waits

---

### Test Case ID: TC-014
**Title**: Verify optimized prompt is formatted correctly  
**Priority**: P1  
**Type**: Positive  
**Preconditions**:
- Optimization completed successfully

**Test Data**: Original: "Write a marketing email"

**Steps**:
1. Complete optimization with any method
2. Examine the returned optimized prompt

**Expected Result**:
- Optimized prompt is complete text (not truncated)
- Prompt is different from original (value added)
- No parsing artifacts like `<IMPROVED_PROMPT>` tags visible
- Markdown formatting renders properly (or falls back cleanly)

**Post-conditions**: N/A

**Notes**: If LLM response contains tags, they should be stripped

---

## SECTION 4: FOLLOW-UP QUESTION FLOW

---

### Test Case ID: TC-015
**Title**: Decline follow-up questions (click NO)  
**Priority**: P0  
**Type**: Positive  
**Preconditions**:
- User has received optimized prompt
- Inline YES/NO buttons visible

**Test Data**: N/A

**Steps**:
1. After receiving optimized prompt, click the inline `❌NO` / `❌НЕТ` button

**Expected Result**:
- Button shows checkmark: "✓ ❌NO"
- Both buttons become disabled (clicking does nothing)
- Bot sends completion message: "✅ Done!" / "✅ Готово!"
- Keyboard shows: `📧 Send prompt to e-mail` and `🔄 Reset`
- User can enter new prompt or send to email

**Post-conditions**:
- User in "waiting_for_prompt" state
- Post-optimization result cached for email button

**Notes**: Inline button interaction, not reply keyboard

---

### Test Case ID: TC-016
**Title**: Accept follow-up questions (click YES)  
**Priority**: P0  
**Type**: Positive  
**Preconditions**:
- User has received optimized prompt
- Inline YES/NO buttons visible

**Test Data**: N/A

**Steps**:
1. Click the inline `✅YES` / `✅ДА` button

**Expected Result**:
- Button shows checkmark: "✓ ✅YES"
- Both buttons become disabled
- Bot sends one or more clarifying questions
- Keyboard shows: `🤖Generate Prompt` and `🔄 Reset`

**Post-conditions**:
- User in "in_followup_conversation" state
- Follow-up conversation started

**Notes**: Questions are AI-generated and vary

---

### Test Case ID: TC-017
**Title**: Click disabled follow-up button  
**Priority**: P2  
**Type**: Edge  
**Preconditions**:
- User has already clicked YES or NO
- Buttons show disabled state

**Test Data**: N/A

**Steps**:
1. After clicking YES or NO, click the other button (now disabled)

**Expected Result**:
- No error message
- No action taken
- Callback is silently acknowledged (loading indicator disappears)

**Post-conditions**:
- State unchanged

**Notes**: Tests disabled button handler

---

### Test Case ID: TC-018
**Title**: Answer follow-up questions and receive refined prompt  
**Priority**: P0  
**Type**: Positive  
**Preconditions**:
- User clicked YES for follow-up
- Bot asked at least one question

**Test Data**: Answer whatever questions the bot asks with relevant responses

**Steps**:
1. Click YES for follow-up
2. Read the bot's question(s)
3. Type and send an answer
4. If more questions, repeat answering
5. Continue until bot provides refined prompt

**Expected Result**:
- Each answer is acknowledged
- Bot may ask 2-5 questions
- Eventually, bot provides refined prompt (with `<REFINED_PROMPT>` extracted)
- Completion message appears
- Keyboard shows: `📧 Send prompt to e-mail` and `🔄 Reset`

**Post-conditions**:
- User in "waiting_for_prompt" state
- Refined prompt cached for email

**Notes**: Number of questions varies; AI decides when to generate

---

### Test Case ID: TC-019
**Title**: Click Generate Prompt button during follow-up  
**Priority**: P0  
**Type**: Positive  
**Preconditions**:
- User is in follow-up conversation
- At least one question answered

**Test Data**: N/A

**Steps**:
1. Start follow-up by clicking YES
2. Answer at least one question
3. Click `🤖Generate Prompt` / `🤖Сгенерировать промпт` button

**Expected Result**:
- Bot generates refined prompt immediately
- Refined prompt is delivered
- Completion message appears
- Flow ends with email button and reset option

**Post-conditions**:
- User in "waiting_for_prompt" state

**Notes**: Allows user to stop Q&A early

---

### Test Case ID: TC-020
**Title**: Click Generate Prompt without answering any questions  
**Priority**: P1  
**Type**: Edge  
**Preconditions**:
- User clicked YES for follow-up
- Bot sent first question
- User hasn't answered yet

**Test Data**: N/A

**Steps**:
1. Click YES for follow-up
2. Immediately click `🤖Generate Prompt` button

**Expected Result**:
- Bot generates prompt based on context
- Should return improved prompt (possibly same as initial optimization)
- No error

**Post-conditions**:
- User in "waiting_for_prompt" state

**Notes**: Edge case - generating without Q&A

---

### Test Case ID: TC-021
**Title**: Click Reset during follow-up conversation  
**Priority**: P1  
**Type**: Positive  
**Preconditions**:
- User is in middle of follow-up conversation

**Test Data**: N/A

**Steps**:
1. Start follow-up by clicking YES
2. Answer one question
3. Click `🔄 Reset` button

**Expected Result**:
- Bot sends reset confirmation
- Welcome messages appear
- Previous conversation context cleared
- User can start fresh

**Post-conditions**:
- User in "waiting_for_prompt" state
- All follow-up state cleared

**Notes**: Tests reset from mid-conversation

---

### Test Case ID: TC-022
**Title**: Send non-answer text during follow-up  
**Priority**: P2  
**Type**: Negative  
**Preconditions**:
- User is in follow-up conversation

**Test Data**: "asdfghjkl" or random characters

**Steps**:
1. During follow-up Q&A, send random characters as answer

**Expected Result**:
- Bot accepts the input (AI will handle appropriately)
- May ask clarifying question or continue
- No crash or error

**Post-conditions**:
- Still in follow-up conversation

**Notes**: AI handles unexpected content

---

## SECTION 5: RESET FUNCTIONALITY

---

### Test Case ID: TC-023
**Title**: Reset from prompt input state  
**Priority**: P1  
**Type**: Positive  
**Preconditions**:
- User is waiting for prompt (after /start)

**Test Data**: N/A

**Steps**:
1. Send `/start`
2. Before entering prompt, send `/start` again (or click Reset if visible)

**Expected Result**:
- Welcome messages appear
- State reset to beginning
- No errors

**Post-conditions**:
- User in "waiting_for_prompt" state

**Notes**: Reset from initial state

---

### Test Case ID: TC-024
**Title**: Reset from method selection state  
**Priority**: P0  
**Type**: Positive  
**Preconditions**:
- User has entered prompt and sees method selection

**Test Data**: Any prompt

**Steps**:
1. Enter a prompt
2. When method selection appears, click `🔄 Reset` button

**Expected Result**:
- Welcome messages appear
- Entered prompt is cleared
- Method selection disappears
- User can start over

**Post-conditions**:
- User in "waiting_for_prompt" state

**Notes**: Tests reset from method selection

---

### Test Case ID: TC-025
**Title**: Reset from OTP input state (email flow)  
**Priority**: P1  
**Type**: Positive  
**Preconditions**:
- User started email flow
- User entered email and waiting for OTP

**Test Data**: N/A

**Steps**:
1. Start email flow
2. Enter email address
3. When OTP prompt appears, click `🔄 Reset`

**Expected Result**:
- OTP session is abandoned
- Welcome messages appear
- User can start fresh

**Post-conditions**:
- User in "waiting_for_prompt" state
- OTP data cleared from Redis

**Notes**: Tests reset from mid-email-flow

---

## SECTION 6: EMAIL DELIVERY FLOW

---

### Test Case ID: TC-026
**Title**: Start email delivery flow (new user)  
**Priority**: P0  
**Type**: Positive  
**Preconditions**:
- User has never verified email with this bot
- User has entered a prompt
- Redis and SMTP services healthy

**Test Data**: 
- Prompt: "Write a product description for a new smartphone"

**Steps**:
1. Enter the prompt
2. Click `📧 Send 3 prompts to email` button

**Expected Result**:
- Bot asks for email address
- Message: "📧 Please enter your email address..." / Russian equivalent
- Keyboard shows only Reset button

**Post-conditions**:
- User in "waiting_for_email_input" state

**Notes**: First step of email authentication

---

### Test Case ID: TC-027
**Title**: Start email delivery flow (already authenticated user)  
**Priority**: P0  
**Type**: Positive  
**Preconditions**:
- User has previously verified email with this bot
- User has entered a prompt

**Test Data**: Any prompt

**Steps**:
1. Enter a prompt
2. Click `📧 Send 3 prompts to email` button

**Expected Result**:
- Bot shows "✅ You're already authenticated! Your email xxx@xxx.com" (masked)
- Bot immediately processes all 3 optimization methods
- Shows "🔄 Sending prompt to email" message
- After processing: "✅ Done! I sent your prompt to email"

**Post-conditions**:
- User in "waiting_for_prompt" state
- Email with 3 prompts sent

**Notes**: Skips OTP for authenticated users

---

### Test Case ID: TC-028
**Title**: Enter valid email address  
**Priority**: P0  
**Type**: Positive  
**Preconditions**:
- User is in email input state

**Test Data**: A valid email you can access (e.g., your test email)

**Steps**:
1. Type and send your email address

**Expected Result**:
- Bot sends OTP to email
- Message: "📧 Verification code sent to xxx@xxx.com" (masked)
- Message includes note about data processing consent
- Inline button for "📄 Personal Data Processing Agreement" appears
- Real email arrives in inbox (within 1-2 minutes)

**Post-conditions**:
- User in "waiting_for_otp_input" state
- OTP stored in Redis with 5-min TTL

**Notes**: Check spam folder if email doesn't arrive

---

### Test Case ID: TC-029
**Title**: Enter invalid email format  
**Priority**: P0  
**Type**: Negative  
**Preconditions**:
- User is in email input state

**Test Data**: "notanemail", "missing@", "@nodomain.com", "test@.com"

**Steps**:
1. Send an invalid email format

**Expected Result**:
- Bot shows error: "❌ Invalid email format. Please enter a valid email address"
- User remains in email input state
- Can try again with correct format

**Post-conditions**:
- User still in "waiting_for_email_input" state

**Notes**: Tests email validation

---

### Test Case ID: TC-030
**Title**: Enter email with special characters  
**Priority**: P2  
**Type**: Edge  
**Preconditions**:
- User is in email input state

**Test Data**: "test+label@gmail.com", "user.name@domain.co.uk"

**Steps**:
1. Send email with + or multiple dots

**Expected Result**:
- Valid formats should be accepted
- OTP sent successfully
- Email normalized for storage

**Post-conditions**:
- User in "waiting_for_otp_input" state

**Notes**: Tests email normalization

---

### Test Case ID: TC-031
**Title**: Enter correct OTP code  
**Priority**: P0  
**Type**: Positive  
**Preconditions**:
- User entered valid email
- OTP email received
- OTP not expired (within 5 minutes)

**Test Data**: The 6-digit code from email

**Steps**:
1. Copy the 6-digit code from the received email
2. Paste/type it in Telegram chat
3. Send

**Expected Result**:
- Bot shows "✅ Your Email verified" / "✅ Ваш Email подтвержден"
- Bot immediately starts processing all 3 optimization methods
- Email with results is sent
- Success message: "✅ Done! I sent your prompt to email"

**Post-conditions**:
- User authenticated in database
- User in "waiting_for_prompt" state

**Notes**: Core email verification flow

---

### Test Case ID: TC-032
**Title**: Enter incorrect OTP code  
**Priority**: P0  
**Type**: Negative  
**Preconditions**:
- User entered valid email
- OTP sent

**Test Data**: "000000" or any wrong 6-digit code

**Steps**:
1. Enter a wrong 6-digit code

**Expected Result**:
- Bot shows error: "❌ Invalid code. Please try again (attempts remaining: X)"
- User can try again
- Attempt counter incremented

**Post-conditions**:
- User still in "waiting_for_otp_input" state
- One attempt used

**Notes**: Tests OTP rejection

---

### Test Case ID: TC-033
**Title**: Enter OTP code with invalid format  
**Priority**: P1  
**Type**: Negative  
**Preconditions**:
- User is waiting for OTP input

**Test Data**: "12345", "1234567", "abcdef", "12345a"

**Steps**:
1. Enter non-6-digit or non-numeric code

**Expected Result**:
- Bot shows: "❌ Code must consist of 6 digits"
- User can try again
- Does NOT count as a verification attempt

**Post-conditions**:
- User still in "waiting_for_otp_input" state

**Notes**: Format validation before verification

---

### Test Case ID: TC-034
**Title**: Exceed OTP attempt limit (3 wrong attempts)  
**Priority**: P0  
**Type**: Negative  
**Preconditions**:
- User entered valid email
- OTP sent

**Test Data**: "000000", "111111", "222222" (3 wrong codes)

**Steps**:
1. Enter wrong code #1
2. Enter wrong code #2
3. Enter wrong code #3

**Expected Result**:
- After 3rd wrong attempt:
  - Message: "❌ Too many attempts. Please request a new code"
  - OTP is invalidated
  - User state reset to prompt input

**Post-conditions**:
- User in "waiting_for_prompt" state
- Must restart email flow

**Notes**: Tests brute-force protection

---

### Test Case ID: TC-035
**Title**: OTP expires after 5 minutes  
**Priority**: P0  
**Type**: Negative  
**Preconditions**:
- User entered valid email
- OTP sent

**Test Data**: The correct OTP code

**Steps**:
1. Note the OTP code from email
2. Wait 5+ minutes
3. Enter the code

**Expected Result**:
- Message: "❌ Code has expired. Please request a new code"
- User state reset

**Post-conditions**:
- User in "waiting_for_prompt" state

**Notes**: Tests OTP TTL enforcement

---

### Test Case ID: TC-036
**Title**: Receive email with all 3 optimized prompts  
**Priority**: P0  
**Type**: Positive  
**Preconditions**:
- User completed email verification
- Email delivery succeeded

**Test Data**: Check email inbox

**Steps**:
1. Complete email flow (TC-031)
2. Check email inbox

**Expected Result**:
- Email arrives from "Prompt Engineering Bot" (or configured sender)
- Email contains:
  - Original prompt
  - CRAFT optimized version
  - LYRA optimized version
  - GGL optimized version
- All 3 optimizations are different from each other
- Formatting is readable

**Post-conditions**: N/A

**Notes**: Verify email content quality

---

### Test Case ID: TC-037  
**Title**: Email service unavailable during email flow  
**Priority**: P1  
**Type**: Negative  
**Preconditions**:
- SMTP service is down (coordinate with DevOps)
- OR test when SMTP health check fails

**Test Data**: N/A (environment condition)

**Steps**:
1. Start email flow
2. Observe bot behavior

**Expected Result**:
- Bot shows error message about email service
- Does NOT fall back to showing prompts in chat
- User advised to try later

**Post-conditions**:
- User in "waiting_for_prompt" state

**Notes**: Email fallback is disabled for security; Bug-risk if prompts are shown in chat

**Assumption**: This test requires DevOps coordination to simulate SMTP failure

---

## SECTION 7: POST-OPTIMIZATION EMAIL

---

### Test Case ID: TC-038
**Title**: Send single result to email after declining follow-up  
**Priority**: P0  
**Type**: Positive  
**Preconditions**:
- User completed optimization with single method
- Declined follow-up (clicked NO)
- Sees `📧 Send prompt to e-mail` button

**Test Data**: N/A

**Steps**:
1. Complete any single-method optimization
2. Click NO for follow-up
3. Click `📧 Send prompt to e-mail` button
4. (If not authenticated) Complete email verification
5. Wait for email

**Expected Result**:
- Processing message shown
- Email sent with single optimized prompt
- Success message displayed

**Post-conditions**:
- Email received with one optimized prompt
- User in "waiting_for_prompt" state

**Notes**: Different from 3-prompt email

---

### Test Case ID: TC-039
**Title**: Send single result to email after follow-up completion  
**Priority**: P0  
**Type**: Positive  
**Preconditions**:
- User completed follow-up questions
- Received refined prompt
- Sees `📧 Send prompt to e-mail` button

**Test Data**: N/A

**Steps**:
1. Complete optimization
2. Click YES for follow-up
3. Complete follow-up Q&A
4. Click `📧 Send prompt to e-mail` button

**Expected Result**:
- Email sent with refined prompt (from follow-up)
- Success message displayed

**Post-conditions**:
- Email received with refined prompt

**Notes**: Sends follow-up result, not initial optimization

---

### Test Case ID: TC-040
**Title**: Click post-optimization email without available result  
**Priority**: P1  
**Type**: Negative / Bug-risk  
**Preconditions**:
- User has sent /start but not completed any optimization
- Somehow sees the email button (e.g., from previous session's keyboard)

**Test Data**: N/A

**Steps**:
1. Send `/start`
2. Enter a prompt
3. Instead of selecting method, manually type the email button text (edge case)

**Expected Result**:
- Bot shows error: "❌ No prompt available to send to email"
- Bot suggests completing optimization first

**Post-conditions**:
- User in method selection state

**Notes**: Bug-risk - Tests handling of invalid state for post-optimization email

---

## SECTION 8: ERROR HANDLING

---

### Test Case ID: TC-041
**Title**: LLM processing timeout  
**Priority**: P1  
**Type**: Negative  
**Preconditions**:
- Bot connected to LLM API

**Test Data**: Very complex or long prompt that might cause timeout

**Steps**:
1. Enter a very long and complex prompt
2. Select optimization method
3. Wait for response (up to 60 seconds)

**Expected Result**:
- If timeout occurs: Error message displayed
- Reset button available
- User can try again

**Post-conditions**:
- User can retry or reset

**Notes**: Actual timeout depends on LLM response time

**Assumption**: Timeout behavior may vary; verify with DevOps

---

### Test Case ID: TC-042
**Title**: Network error during message sending  
**Priority**: P2  
**Type**: Negative  
**Preconditions**:
- Unstable network connection

**Test Data**: N/A

**Steps**:
1. Start bot interaction
2. Disable network briefly
3. Re-enable and continue

**Expected Result**:
- Bot has retry logic for sending messages
- May see brief delays
- Eventually messages are delivered
- State remains consistent

**Post-conditions**:
- Conversation can continue

**Notes**: Tests network resilience

---

### Test Case ID: TC-043
**Title**: Redis unavailable during email flow  
**Priority**: P1  
**Type**: Negative  
**Preconditions**:
- Redis service down (coordinate with DevOps)

**Test Data**: N/A

**Steps**:
1. Enter prompt
2. Click email delivery button

**Expected Result**:
- Bot shows: "⚠️ Service temporarily unavailable"
- Email flow is blocked
- Reset button available

**Post-conditions**:
- User advised to try later

**Notes**: Tests graceful degradation

**Assumption**: Requires environment coordination

---

### Test Case ID: TC-044
**Title**: Invalid callback query from inline button  
**Priority**: P2  
**Type**: Negative / Security  
**Preconditions**:
- User is in follow-up choice state

**Test Data**: N/A (simulated by clicking old buttons)

**Steps**:
1. Complete optimization, see YES/NO buttons
2. Send `/start` to reset
3. If old message with buttons is visible, try clicking YES button from it

**Expected Result**:
- Button click is ignored or shows "Invalid state"
- No action taken on stale callback
- No error or crash

**Post-conditions**:
- State remains consistent

**Notes**: Tests stale callback handling

---

## SECTION 9: RATE LIMITING

---

### Test Case ID: TC-045
**Title**: Email rate limit - 3 per hour per email  
**Priority**: P0  
**Type**: Negative  
**Preconditions**:
- Fresh rate limit window (no recent OTP requests)

**Test Data**: Same email address used 4 times

**Steps**:
1. Start email flow, enter email, get OTP, click Reset (don't verify)
2. Repeat step 1 two more times
3. On 4th attempt, enter same email

**Expected Result**:
- First 3 attempts: OTP sent successfully
- 4th attempt: "⚠️ Too many code sending attempts. Please try again later"

**Post-conditions**:
- Email blocked for ~1 hour

**Notes**: Tests per-email rate limiting

---

### Test Case ID: TC-046
**Title**: User rate limit - 5 per hour per user  
**Priority**: P1  
**Type**: Negative  
**Preconditions**:
- Fresh rate limit window

**Test Data**: Different email addresses (5+)

**Steps**:
1. Request OTP with email1@test.com
2. Request OTP with email2@test.com
3. Continue with different emails until limit
4. On 6th attempt with another new email

**Expected Result**:
- First 5 different emails: OTP sent
- 6th email: "⚠️ Too many code sending attempts"

**Post-conditions**:
- User blocked for ~1 hour

**Notes**: Tests per-user rate limiting

---

### Test Case ID: TC-047
**Title**: OTP spacing - 60 seconds between requests  
**Priority**: P1  
**Type**: Negative  
**Preconditions**:
- Just sent OTP request

**Test Data**: Same email

**Steps**:
1. Enter email, OTP sent
2. Click Reset
3. Immediately (within 60 seconds) start email flow again with same email

**Expected Result**:
- Message: "⚠️ Too many code sending attempts. Please try again later"
- Wait indicator would show seconds remaining

**Post-conditions**:
- Must wait 60 seconds

**Notes**: Tests spacing enforcement

---

## SECTION 10: TIMEOUT HANDLING

---

### Test Case ID: TC-048
**Title**: Follow-up conversation timeout (5 minutes)  
**Priority**: P0  
**Type**: Negative  
**Preconditions**:
- User is in follow-up conversation

**Test Data**: N/A

**Steps**:
1. Start follow-up (click YES)
2. Answer one question
3. Wait 5+ minutes without any action
4. Try to send another answer

**Expected Result**:
- Bot detects timeout
- Falls back to cached improved prompt
- Delivers that prompt to user
- Flow completes gracefully

**Post-conditions**:
- User in "waiting_for_prompt" state
- Cached prompt was used

**Notes**: Tests graceful degradation on timeout

---

### Test Case ID: TC-049
**Title**: OTP verification timeout (5 minutes)  
**Priority**: P1  
**Type**: Negative  
**Preconditions**:
- User requested OTP

**Test Data**: Valid OTP code

**Steps**:
1. Enter email, receive OTP
2. Wait 5+ minutes
3. Try to enter the correct OTP

**Expected Result**:
- "❌ Code has expired. Please request a new code"
- State reset

**Post-conditions**:
- User in "waiting_for_prompt" state

**Notes**: Same as TC-035 but focused on timeout handling

---

## SECTION 11: STATE PERSISTENCE

---

### Test Case ID: TC-050
**Title**: User authentication persists across sessions  
**Priority**: P0  
**Type**: Positive  
**Preconditions**:
- User has previously verified email

**Test Data**: N/A

**Steps**:
1. Close Telegram app completely
2. Reopen Telegram
3. Send `/start` to bot
4. Enter prompt
5. Click email delivery button

**Expected Result**:
- Bot recognizes user as authenticated
- Shows "✅ You're already authenticated!"
- Skips OTP verification

**Post-conditions**:
- Email flow proceeds without re-verification

**Notes**: Tests database persistence

---

### Test Case ID: TC-051
**Title**: In-memory state lost after bot restart  
**Priority**: P1  
**Type**: Edge / Bug-risk  
**Preconditions**:
- Bot has been restarted (coordinate with DevOps)

**Test Data**: N/A

**Steps**:
1. Start optimization flow (enter prompt)
2. DevOps restarts the bot
3. Try to select method

**Expected Result**:
- Bot may not recognize previous state
- User should be able to continue with `/start`
- No crash or undefined behavior

**Post-conditions**:
- User can start fresh after reset

**Notes**: Tests in-memory state handling after restart

**Assumption**: Requires DevOps coordination

---

## SECTION 12: CONCURRENCY & REPEATED ACTIONS

---

### Test Case ID: TC-052
**Title**: Click same method button multiple times rapidly  
**Priority**: P1  
**Type**: Edge  
**Preconditions**:
- User sees method selection keyboard

**Test Data**: Any prompt

**Steps**:
1. Enter prompt
2. Rapidly tap `⚡ Quick` button 3 times in quick succession

**Expected Result**:
- Only one optimization triggered
- No duplicate processing messages
- Single optimized prompt returned

**Post-conditions**:
- Normal follow-up flow

**Notes**: Tests idempotency of method selection

---

### Test Case ID: TC-053
**Title**: Click both YES and NO inline buttons rapidly  
**Priority**: P1  
**Type**: Edge  
**Preconditions**:
- Follow-up offer displayed with inline buttons

**Test Data**: N/A

**Steps**:
1. When YES/NO buttons appear, rapidly click YES then NO (or vice versa)

**Expected Result**:
- Only first click is processed
- Second click finds buttons disabled
- Consistent state (either in follow-up or declined)

**Post-conditions**:
- State matches first clicked button

**Notes**: Tests race condition handling

---

### Test Case ID: TC-054
**Title**: Send multiple messages during processing  
**Priority**: P2  
**Type**: Edge  
**Preconditions**:
- User has triggered optimization

**Test Data**: "test1", "test2", "test3"

**Steps**:
1. Select optimization method
2. While "Processing..." is showing, send multiple text messages

**Expected Result**:
- Messages are queued or ignored
- Optimization completes normally
- No interference with the current processing
- Bot doesn't process queued messages as prompts

**Post-conditions**:
- Normal follow-up flow after optimization

**Notes**: Tests message queue handling

---

### Test Case ID: TC-055
**Title**: Send Reset while processing  
**Priority**: P1  
**Type**: Edge  
**Preconditions**:
- Optimization in progress

**Test Data**: N/A

**Steps**:
1. Select method, processing starts
2. Immediately click Reset button

**Expected Result**:
- Reset takes effect
- Welcome messages appear
- Any in-flight optimization is abandoned
- No partial results delivered

**Post-conditions**:
- User in "waiting_for_prompt" state

**Notes**: Tests reset during async operation

---

## SECTION 13: LOCALIZATION

---

### Test Case ID: TC-056
**Title**: Verify all buttons display in configured language (Russian)  
**Priority**: P1  
**Type**: Positive  
**Preconditions**:
- Bot configured with `LANGUAGE=RU`

**Test Data**: N/A

**Steps**:
1. Go through entire flow: start, prompt, method selection, follow-up

**Expected Result**:
- All buttons are in Russian:
  - "🔄 Сбросить диалог"
  - "⚡ Быстро"
  - "🛠 По шагам"
  - "🎯 Под результат"
  - "📧 Отправить 3 промпта на email"
  - "✅ДА", "❌НЕТ"
  - "🤖Сгенерировать промпт"
  - "📧 Отправить промпт на e-mail"
  - "🆘 Техподдержка"

**Post-conditions**: N/A

**Notes**: Complete Russian UI verification

---

### Test Case ID: TC-057
**Title**: Verify all buttons display in configured language (English)  
**Priority**: P1  
**Type**: Positive  
**Preconditions**:
- Bot configured with `LANGUAGE=EN`

**Test Data**: N/A

**Steps**:
1. Go through entire flow: start, prompt, method selection, follow-up

**Expected Result**:
- All buttons are in English:
  - "🔄 Reset Conversation"
  - "⚡ Quick"
  - "🛠 Step-by-step"
  - "🎯 Result-focused"
  - "📧 Send 3 prompts to email"
  - "✅YES", "❌NO"
  - "🤖Generate Prompt"
  - "📧 Send prompt to e-mail"
  - "🆘 Support"

**Post-conditions**: N/A

**Notes**: Complete English UI verification

---

## SECTION 14: SUPPORT BUTTON

---

### Test Case ID: TC-058
**Title**: Support button opens support bot  
**Priority**: P2  
**Type**: Positive  
**Preconditions**:
- Bot is running

**Test Data**: N/A

**Steps**:
1. Send `/start`
2. Click the inline "🆘 Support" / "🆘 Техподдержка" button

**Expected Result**:
- Telegram opens a new chat or link
- URL: `https://t.me/prompthelpdesk_bot?start` (or configured URL)
- Support bot or channel is accessible

**Post-conditions**: N/A

**Notes**: Tests support button functionality

---

## SECTION 15: ADDITIONAL BUG-RISK TESTS

---

### Test Case ID: TC-059
**Title**: (Bug-risk) Email injection attempt  
**Priority**: P1  
**Type**: Security  
**Preconditions**:
- User is in email input state

**Test Data**: 
- `test@example.com\nBcc: attacker@evil.com`
- `test@example.com%0ABcc:attacker@evil.com`

**Steps**:
1. Enter email with injection characters
2. Observe response

**Expected Result**:
- Bot rejects the email as invalid format
- Error: "❌ Invalid email format"
- No OTP sent

**Post-conditions**:
- User still in email input state

**Notes**: Tests email injection protection

---

### Test Case ID: TC-060
**Title**: (Bug-risk) Concurrent OTP verification attempts  
**Priority**: P2  
**Type**: Security / Edge  
**Preconditions**:
- OTP sent to user

**Test Data**: Correct OTP code

**Steps**:
1. Enter OTP in two Telegram clients simultaneously (same account)

**Expected Result**:
- Only one verification succeeds
- Second attempt fails (OTP already used/deleted)
- No duplicate email sends

**Post-conditions**:
- User authenticated (if first succeeded)

**Notes**: Tests OTP single-use enforcement

---

### Test Case ID: TC-061
**Title**: (Bug-risk) Post-optimization email button available after reset  
**Priority**: P1  
**Type**: Bug-risk  
**Preconditions**:
- User completed optimization and declined follow-up
- Post-optimization email button visible

**Test Data**: N/A

**Steps**:
1. Complete optimization, decline follow-up
2. See the email button
3. Send `/start` to reset
4. Try to tap the email button from old keyboard (if still visible on some clients)

**Expected Result**:
- Either: Button is no longer functional (keyboard replaced)
- Or: Bot shows "No prompt available to send"
- State is not corrupted

**Post-conditions**:
- User in clean "waiting_for_prompt" state

**Notes**: Tests state cleanup for cached results

---

### Test Case ID: TC-062
**Title**: (Bug-risk) Message split for very long optimized prompt  
**Priority**: P2  
**Type**: Edge  
**Preconditions**:
- User requests optimization that returns 4000+ character result

**Test Data**: Complex prompt that generates long output

**Steps**:
1. Enter prompt that will result in long optimization
2. Complete optimization

**Expected Result**:
- If response exceeds 4096 chars, it's split into multiple messages
- All parts are delivered
- Follow-up offer appears after last part
- No truncation or data loss

**Post-conditions**:
- Complete optimized prompt received

**Notes**: Tests Telegram message length handling

---

### Test Case ID: TC-063
**Title**: (Bug-risk) Markdown parsing failure in optimized prompt  
**Priority**: P2  
**Type**: Edge  
**Preconditions**:
- LLM returns response with broken Markdown

**Test Data**: Prompt likely to generate code blocks or special formatting

**Steps**:
1. Enter: "Write Python code for a REST API endpoint"
2. Complete optimization

**Expected Result**:
- If Markdown parsing fails, bot retries without parse_mode
- Message is delivered (may lose formatting)
- No "parse entities" error shown to user
- Flow continues normally

**Post-conditions**:
- User can proceed

**Notes**: Tests Markdown fallback handling

---

## SECTION 16: END-TO-END FLOW TESTS

---

### Test Case ID: TC-064
**Title**: Complete happy path - Single method optimization  
**Priority**: P0  
**Type**: E2E / Positive  
**Preconditions**:
- New or existing user
- All services healthy

**Test Data**: "Write a job application cover letter for a software engineer position"

**Steps**:
1. Send `/start`
2. Read welcome messages
3. Send the test prompt
4. Click `🛠 Step-by-step` button
5. Wait for optimization
6. Click `❌NO` to decline follow-up
7. Verify completion message

**Expected Result**:
- All steps complete without errors
- Optimized prompt received
- Completion message with "✅ Done!" / "✅ Готово!"
- Email button and Reset button visible
- Can enter new prompt

**Post-conditions**:
- User ready for next interaction

**Notes**: Tests most common user journey

---

### Test Case ID: TC-065
**Title**: Complete happy path - With follow-up questions  
**Priority**: P0  
**Type**: E2E / Positive  
**Preconditions**:
- New or existing user
- All services healthy

**Test Data**: "Create a project plan for launching a new mobile app"

**Steps**:
1. Send `/start`
2. Send the test prompt
3. Click `🎯 Result-focused` button
4. Wait for optimization
5. Click `✅YES` to accept follow-up
6. Answer 2-3 questions from the bot
7. Click `🤖Generate Prompt` button
8. Verify refined prompt received

**Expected Result**:
- All steps complete without errors
- Refined prompt is more specific than initial optimization
- Completion message appears
- Email button visible

**Post-conditions**:
- User ready for next interaction

**Notes**: Tests follow-up flow end-to-end

---

### Test Case ID: TC-066
**Title**: Complete happy path - Email delivery with new user  
**Priority**: P0  
**Type**: E2E / Positive  
**Preconditions**:
- User has never verified email
- All services healthy
- Valid test email available

**Test Data**: 
- Prompt: "Write a business proposal for a consulting service"
- Email: (your test email)

**Steps**:
1. Send `/start`
2. Send the test prompt
3. Click `📧 Send 3 prompts to email`
4. Enter email address
5. Check email inbox, get 6-digit code
6. Enter OTP in Telegram
7. Wait for processing
8. Verify success message

**Expected Result**:
- OTP email arrives
- Verification succeeds
- All 3 optimized prompts sent to email
- "✅ Done! I sent your prompt to email"

**Post-conditions**:
- User authenticated
- Email received with 3 prompts

**Notes**: Complete email flow for new user

---

### Test Case ID: TC-067
**Title**: Complete happy path - Post-optimization email  
**Priority**: P0  
**Type**: E2E / Positive  
**Preconditions**:
- User has verified email (from previous test)
- All services healthy

**Test Data**: "Create a social media content calendar"

**Steps**:
1. Send `/start`
2. Send the test prompt
3. Click `⚡ Quick` button
4. Wait for optimization
5. Click `❌NO` to decline follow-up
6. Click `📧 Send prompt to e-mail`
7. (Should skip OTP since already authenticated)
8. Wait for email

**Expected Result**:
- "✅ You're already authenticated!"
- Processing message
- Email sent with single optimized prompt
- Success message

**Post-conditions**:
- Email received with one prompt

**Notes**: Tests post-optimization email for returning user

---

## Test Summary

| Priority | Count | Description |
|----------|-------|-------------|
| P0 | 24 | Critical path tests - Must pass |
| P1 | 27 | High priority - Should pass |
| P2 | 16 | Medium priority - Nice to pass |

**Total Test Cases**: 67

### Test Categories Breakdown

| Category | Test Cases |
|----------|------------|
| Onboarding & Welcome | TC-001 to TC-005 |
| Prompt Input & Method Selection | TC-006 to TC-012 |
| Optimization Processing | TC-013 to TC-014 |
| Follow-up Questions | TC-015 to TC-022 |
| Reset Functionality | TC-023 to TC-025 |
| Email Delivery Flow | TC-026 to TC-037 |
| Post-optimization Email | TC-038 to TC-040 |
| Error Handling | TC-041 to TC-044 |
| Rate Limiting | TC-045 to TC-047 |
| Timeout Handling | TC-048 to TC-049 |
| State Persistence | TC-050 to TC-051 |
| Concurrency/Repeated Actions | TC-052 to TC-055 |
| Localization | TC-056 to TC-057 |
| Support Button | TC-058 |
| Bug-risk Tests | TC-059 to TC-063 |
| E2E Flow Tests | TC-064 to TC-067 |

---

## Appendix A: Quick Test Execution Checklist

### Smoke Test (P0 only, ~30 minutes)

- [ ] TC-001: /start works
- [ ] TC-006: Prompt input works
- [ ] TC-009: CRAFT optimization works
- [ ] TC-015: Follow-up decline works
- [ ] TC-016: Follow-up accept works
- [ ] TC-019: Generate Prompt button works
- [ ] TC-024: Reset from method selection works
- [ ] TC-026: Email flow starts
- [ ] TC-028: Email validation works
- [ ] TC-031: OTP verification works
- [ ] TC-036: Email received with 3 prompts
- [ ] TC-038: Post-optimization email works

### Regression Test (All P0 + P1, ~2-3 hours)

Execute all test cases marked P0 and P1.

### Full Test (All test cases, ~4-5 hours)

Execute all 67 test cases.

---

## Appendix B: Test Environment Checklist

Before testing, verify:

- [ ] Bot responds to `/start`
- [ ] LLM API is operational (optimization returns results)
- [ ] Email service is operational (OTP emails arrive)
- [ ] Redis is operational (email flow doesn't show "Service unavailable")
- [ ] Database is operational (authenticated users are remembered)
- [ ] Test email account is accessible
- [ ] Test Telegram account is ready

---

*Document End*
