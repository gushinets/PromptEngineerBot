# End-to-End User Paths Documentation
## Telegram Prompt Optimization Bot

**Document Version**: 1.0  
**Last Updated**: 2025-01-03  
**Purpose**: Complete E2E testing documentation for AI-QA agent verification

---

## Table of Contents

1. [Overview](#overview)
2. [Testing Guidelines](#testing-guidelines)
3. [System Components](#system-components)
4. [Path Category 1: Single Method Optimization](#path-category-1-single-method-optimization)
5. [Path Category 2: Follow-up Enhancement](#path-category-2-follow-up-enhancement)
6. [Path Category 3: Email Delivery](#path-category-3-email-delivery)
7. [Path Category 4: State Management & Errors](#path-category-4-state-management--errors)
8. [Validation Checklists](#validation-checklists)

---

## Overview

This document provides comprehensive end-to-end testing documentation for the Telegram bot that optimizes user prompts using AI-powered methodologies (CRAFT, LYRA, GGL). The bot supports:

- **3 Optimization Methods**: По шагам (CRAFT), Быстро (LYRA), Под результат (GGL)
- **Follow-up Questions**: Interactive refinement of prompts
- **Email Delivery**: Authentication and multi-method optimization via email
- **Robust Error Handling**: Graceful degradation and state recovery

### Total User Paths Documented

- **Category 1**: Single Method Optimization (4 paths)
- **Category 2**: Follow-up Enhancement (8 paths)
- **Category 3**: Email Delivery (6 paths)
- **Category 4**: State Management & Errors (4 paths)
- **Total**: 22+ distinct user paths

---

## Testing Guidelines

### Test Environment Requirements

**Required Services:**
- Telegram Bot API (active bot token)
- LLM Backend (OpenAI or OpenRouter)
- PostgreSQL Database (user data, auth events)
- Redis (OTP storage, rate limiting, flow state)
- SMTP Server (email delivery)

**Test Coverage:**
- ✅ Normal operation (all services healthy)
- ✅ Service degradation scenarios
- ✅ Network timeouts and retries
- ✅ Rate limiting enforcement
- ✅ State corruption recovery

### Validation Approach

**Bot Messages:**
- Verify exact message text matches expected constants
- Check Markdown parsing and formatting
- Validate keyboard button layouts

**State Transitions:**
- Verify internal state flags at each step
- Check Redis flow state data
- Validate database records

**Email Verification:**
- Manual inbox check for OTP and optimization emails
- Verify email subject lines and structure
- Check timing (should arrive within 30 seconds)

**LLM Response Quality:**
- Technical: Proper tags, structure, completeness
- Semantic: Relevance, improvements, method-specific traits
- Edge cases: Handle very short/long prompts appropriately

---

## System Components

### State Flags

| Flag | Type | Description |
|------|------|-------------|
| `waiting_for_prompt` | bool | User needs to provide initial prompt |
| `waiting_for_method` | bool | User needs to select optimization method |
| `waiting_for_followup_choice` | bool | User deciding on follow-up questions (YES/NO) |
| `in_followup_conversation` | bool | Active follow-up Q&A session |
| `waiting_for_email_input` | bool | User needs to provide email address |
| `waiting_for_otp_input` | bool | User needs to provide OTP code |
| `improved_prompt_cache` | str | Cached optimized prompt for follow-up |
| `cached_method_name` | str | Method name for cached prompt |
| `email_flow_data` | dict | Email flow context data |
| `post_optimization_result` | dict | Result for post-optimization email |

### Button Constants

**Method Selection:**
- `BTN_CRAFT` = "🛠 По шагам"
- `BTN_LYRA` = "⚡ Быстро"
- `BTN_GGL` = "🎯 Под результат"
- `BTN_EMAIL_DELIVERY` = "📧 Отправить 3 промпта на email"

**Follow-up:**
- `BTN_YES` = "✅ДА"
- `BTN_NO` = "❌НЕТ"
- `BTN_GENERATE_PROMPT` = "🤖Сгенерировать промпт"

**Navigation:**
- `BTN_RESET` = "🔄 Сбросить диалог"
- `BTN_POST_OPTIMIZATION_EMAIL` = "📧 Отправить промпт на e-mail"

### Service Dependencies

**Redis Keys:**
- `otp:{telegram_id}` - OTP data (hash, email, expiry, attempts)
- `rate:email:{email}` - Email-based rate limit counter
- `rate:user:{telegram_id}` - User-based rate limit counter
- `spacing:{telegram_id}` - Last OTP send timestamp
- `flow:{telegram_id}` - Follow-up conversation state

**Database Tables:**
- `users` - User authentication and profile data
- `auth_events` - Authentication audit trail

**LLM Response Tags:**
- `<QUESTION>...</QUESTION>` - Bot asking for clarification
- `<IMPROVED_PROMPT>...</IMPROVED_PROMPT>` - Optimized result
- `<REFINED_PROMPT>...</REFINED_PROMPT>` - Follow-up refined result

---

## Path Category 1: Single Method Optimization

### Path 1A: CRAFT Method Optimization

**Description**: User optimizes prompt using CRAFT (structured approach) method

**Preconditions:**
- User has started bot (`/start` command)
- State: `waiting_for_prompt = True`
- No active conversations

**Steps and Expected Outcomes:**

| Step | User Action | System Response | State After | Verification Points |
|------|------------|-----------------|-------------|---------------------|
| 1 | Send `/start` command | WELCOME_MESSAGE with instructions | `waiting_for_prompt=True` | ✓ Welcome message displays<br>✓ No keyboard buttons shown<br>✓ Message in Markdown format |
| 2 | Send text: "Write a blog post about AI" | SELECT_METHOD_MESSAGE with method buttons | `waiting_for_prompt=False`<br>`waiting_for_method=True`<br>User prompt stored | ✓ Method selection message<br>✓ 4 buttons: По шагам, Быстро, Под результат, Email<br>✓ Reset button shown<br>✓ Conversation transcript initialized |
| 3 | Click "🛠 CRAFT" button | Processing message: "🔄 Обрабатываю ваш промпт с помощью метода *CRAFT*..." | `waiting_for_method=False`<br>`current_method=CRAFT` | ✓ Processing message sent<br>✓ Method logged<br>✓ System prompt added to transcript |
| 4 | (Bot processing) | LLM returns optimized prompt | Transcript updated with LLM response | ✓ LLM API called with CRAFT system prompt<br>✓ Token usage tracked<br>✓ Response parsed correctly |
| 5 | (Bot sends result) | Optimized prompt message (no tags) | `improved_prompt_cache` set<br>`cached_method_name=CRAFT` | ✓ Clean prompt without XML tags<br>✓ Markdown formatted<br>✓ Reset button shown<br>✓ Prompt cached |
| 6 | (Bot offers follow-up) | FOLLOWUP_OFFER_MESSAGE with YES/NO buttons | `waiting_for_followup_choice=True` | ✓ Follow-up offer message<br>✓ YES and NO buttons shown<br>✓ Tokens logged to sheets |

**Success Criteria:**
- ✅ Optimized prompt shows CRAFT characteristics (structured with clear sections)
- ✅ Semantic improvements: More specific, actionable, context-rich
- ✅ Token usage recorded in conversation manager
- ✅ User can proceed to follow-up or decline
- ✅ All state transitions correct

**LLM Quality Checks:**
- Prompt is more structured than original
- Contains specific requirements/context
- Clear role definition if applicable
- Actionable instructions

---

### Path 1B: LYRA Basic Method Optimization

**Description**: User optimizes prompt using LYRA Basic (quick results) method

**Preconditions:**
- User has started bot
- State: `waiting_for_prompt = True`

**Steps and Expected Outcomes:**

| Step | User Action | System Response | State After | Verification Points |
|------|------------|-----------------|-------------|---------------------|
| 1-2 | Same as Path 1A (start and provide prompt) | Same as Path 1A | Same as Path 1A | Same verification as Path 1A |
| 3 | Click "⚡ LYRA" button | Processing message: "🔄 Обрабатываю ваш промпт с помощью метода *LYRA*..." | `waiting_for_method=False`<br>`current_method=LYRA Basic` | ✓ Processing message sent<br>✓ Additional context message: "BASIC using ChatGPT" added to transcript |
| 4-6 | Same as Path 1A (LLM processing and result) | Same as Path 1A with LYRA-optimized prompt | Same as Path 1A | ✓ LYRA system prompt used<br>✓ Cached method name: "LYRA Basic" |

**Success Criteria:**
- ✅ Optimized prompt shows LYRA characteristics (concise, focused)
- ✅ Semantic improvements: Clear, direct, efficient
- ✅ Method logged as "LYRA Basic"
- ✅ Follows same flow as CRAFT

**LLM Quality Checks:**
- More concise than CRAFT version
- Focused on essential elements
- Quick to understand and use
- Still maintains clarity

---

### Path 1C: GGL Method Optimization (Под результат)

**Description**: User optimizes prompt using GGL (goal-focused) method

**Preconditions:**
- User has started bot
- State: `waiting_for_prompt = True`

**Steps and Expected Outcomes:**

| Step | User Action | System Response | State After | Verification Points |
|------|------------|-----------------|-------------|---------------------|
| 1-2 | Same as Path 1A | Same as Path 1A | Same as Path 1A | Same verification as Path 1A |
| 3 | Click "🎯 Под результат" button | Processing message: "🔄 Обрабатываю ваш промпт с помощью метода *GGL*..." | `waiting_for_method=False`<br>`current_method=GGL` | ✓ Processing message sent<br>✓ GGL system prompt used |
| 4-6 | Same as Path 1A | Same as Path 1A with GGL-optimized prompt | Same as Path 1A | ✓ Cached method name: "GGL" |

**Success Criteria:**
- ✅ Optimized prompt shows GGL characteristics (goal-oriented)
- ✅ Clear objectives and expected outcomes
- ✅ Minimal unnecessary elaboration

**LLM Quality Checks:**
- Strong focus on goals/outcomes
- Clear success criteria
- Efficient, goal-driven language
- Measurable objectives when applicable

---

## Path Category 2: Follow-up Enhancement

### Path 2A: Accept Follow-up + Complete Conversation

**Description**: User completes full follow-up conversation to refine prompt

**Preconditions:**
- User completed single method optimization (any method)
- State: `waiting_for_followup_choice = True`
- `improved_prompt_cache` contains optimized prompt

**Steps and Expected Outcomes:**

| Step | User Action | System Response | State After | Verification Points |
|------|------------|-----------------|-------------|---------------------|
| 1 | Click "✅ДА" button | Bot initializes follow-up conversation | `waiting_for_followup_choice=False`<br>`in_followup_conversation=True`<br>Follow-up transcript initialized | ✓ Follow-up system prompt loaded<br>✓ Improved prompt added to transcript<br>✓ Token totals reset for new session |
| 2 | (Bot asks first question) | LLM-generated clarifying question | Generate button shown | ✓ Question relevant to original prompt<br>✓ Question clear and specific<br>✓ "🤖Сгенерировать промпт" button<br>✓ Reset button shown |
| 3 | User types answer: "Focus on technical audience" | Bot processes answer and asks next question | Answer added to transcript | ✓ User response logged<br>✓ Token usage accumulated<br>✓ Next question contextual |
| 4 | User types answer: "Include code examples" | Bot processes answer | Answer added to transcript | ✓ Conversation building context<br>✓ LLM adapting questions |
| 5 | Click "🤖Сгенерировать промпт" button | Bot sends generate signal to LLM | `<GENERATE_PROMPT>` added to transcript | ✓ Generate signal sent correctly<br>✓ Bot processes final refinement |
| 6 | (Bot generates refined prompt) | LLM returns refined prompt with `<REFINED_PROMPT>` tags | Bot detects refined prompt tag | ✓ Refined prompt extracted from tags<br>✓ Tags removed from user-facing message |
| 7 | (Bot sends refined prompt) | Clean refined prompt message | `post_optimization_result` set with follow-up type | ✓ No XML tags visible<br>✓ Prompt shows improvements from Q&A<br>✓ Reset button shown |
| 8 | (Bot sends completion message) | PROMPT_READY_FOLLOW_UP message | `waiting_for_prompt=True`<br>`in_followup_conversation=False`<br>Follow-up tokens logged | ✓ Completion message shown<br>✓ Post-optimization email button<br>✓ Tokens logged separately for follow-up<br>✓ User ready for new prompt |

**Success Criteria:**
- ✅ Bot asks 2-4 relevant clarifying questions
- ✅ Questions build on previous answers
- ✅ Refined prompt incorporates user feedback
- ✅ Semantic improvement over initial optimized prompt
- ✅ Follow-up tokens logged separately from initial optimization
- ✅ State properly reset for next interaction

**LLM Quality Checks:**
- Questions are specific and relevant
- Refined prompt shows clear improvements
- User's answers integrated meaningfully
- Final prompt more tailored to user's needs

**Alternative Flow - Questions Complete Without Generate Button:**

| Step | Variation | System Response | Verification Points |
|------|-----------|-----------------|---------------------|
| 4a | Bot decides enough info gathered | LLM returns refined prompt automatically | ✓ `<REFINED_PROMPT>` tag detected<br>✓ Flow completes without generate button |

---

### Path 2B: Decline Follow-up Questions

**Description**: User declines follow-up questions and keeps initial optimized prompt

**Preconditions:**
- User completed single method optimization
- State: `waiting_for_followup_choice = True`
- `improved_prompt_cache` contains optimized prompt

**Steps and Expected Outcomes:**

| Step | User Action | System Response | State After | Verification Points |
|------|------------|-----------------|-------------|---------------------|
| 1 | Click "❌НЕТ" button | FOLLOWUP_DECLINED_MESSAGE | `waiting_for_followup_choice=False`<br>`waiting_for_prompt=True`<br>`post_optimization_result` set | ✓ Decline message shown<br>✓ Post-optimization email button<br>✓ Reset button shown |
| 2 | (Bot stores result) | Cached prompt stored for email | Result type: "single_method"<br>Original prompt preserved | ✓ Cached prompt stored<br>✓ Method name cached<br>✓ Original prompt saved for email<br>✓ State reset except post_optimization_result |

**Success Criteria:**
- ✅ User retains initial optimized prompt
- ✅ Post-optimization email button available
- ✅ Result stored correctly for email delivery
- ✅ State ready for new prompt or email action

**Verification Points:**
- Cached prompt matches initial optimization
- Method name correctly stored
- User can proceed to email or new prompt

---

### Path 2C: Follow-up Timeout/Error Fallback

**Description**: Follow-up conversation times out or encounters error, falls back to cached prompt

**Preconditions:**
- User in active follow-up conversation
- State: `in_followup_conversation = True`
- Timeout threshold: 300 seconds (5 minutes)

**Steps and Expected Outcomes:**

| Step | Scenario | System Response | State After | Verification Points |
|------|----------|-----------------|-------------|---------------------|
| 1a | User inactive for >5 minutes | Timeout detected before LLM call | Timeout check returns true | ✓ Redis timeout tracking working<br>✓ Elapsed time > `followup_timeout_seconds` |
| 1b | LLM API error during follow-up | Exception caught in `_process_followup_llm_request` | Error classified (timeout/network/rate/api/generic) | ✓ Error handler invoked<br>✓ Error type identified |
| 2 | (Bot handles fallback) | Fallback message sent | `improved_prompt_cache` retrieved | ✓ Appropriate error message shown<br>✓ Cached prompt available |
| 3 | (Bot sends cached prompt) | Original optimized prompt from cache | `in_followup_conversation=False`<br>State reset | ✓ Cached prompt sent<br>✓ Reset button shown<br>✓ User can continue |

**Error-Specific Messages:**

| Error Type | Message Constant | User Action Available |
|------------|------------------|----------------------|
| Timeout | `FOLLOWUP_TIMEOUT_FALLBACK` | Gets cached prompt |
| Network | `FOLLOWUP_NETWORK_FALLBACK` | Gets cached prompt |
| Rate Limit | `FOLLOWUP_RATE_LIMIT_FALLBACK` | Gets cached prompt |
| API Error | `FOLLOWUP_API_ERROR_FALLBACK` | Gets cached prompt |
| Generic | Uses cached prompt silently | Gets cached prompt |

**Success Criteria:**
- ✅ User always gets a usable prompt
- ✅ No data loss from timeout/error
- ✅ Appropriate error message shown
- ✅ Graceful degradation to cached version

**Alternative Flow - No Cached Prompt:**

| Step | Scenario | System Response | Verification Points |
|------|----------|-----------------|---------------------|
| 3a | No cached prompt available | Error message + reset | ✓ State fully reset<br>✓ User returns to prompt input |

---

### Path 2D: Post-Optimization Email After Decline

**Description**: User declined follow-up, then uses post-optimization email button

**Preconditions:**
- User declined follow-up (Path 2B completed)
- State: `post_optimization_result` contains single_method result
- `waiting_for_prompt = True`

**Steps and Expected Outcomes:**

| Step | User Action | System Response | State After | Verification Points |
|------|------------|-----------------|-------------|---------------------|
| 1 | Click "📧 Отправить промпт на e-mail" button | Check if user authenticated | Email flow data initialized | ✓ Post-optimization result retrieved<br>✓ Flow type: "post_optimization" |
| 2a | User NOT authenticated | EMAIL_INPUT_MESSAGE | `waiting_for_email_input=True` | ✓ Email input prompt shown<br>✓ Reset button available |
| 2b | User IS authenticated | EMAIL_ALREADY_AUTHENTICATED message | Skip to step 5 | ✓ Existing email retrieved<br>✓ OTP skipped |
| 3 | User enters email: "user@example.com" | Email format validated | Email validation passed | ✓ Format validation passed<br>✓ No injection attempts |
| 4 | (Bot sends OTP) | OTP generated, stored, and sent via email | `waiting_for_otp_input=True`<br>OTP in Redis | ✓ OTP email sent<br>✓ EMAIL_OTP_SENT message shown<br>✓ Rate limits checked |
| 5 | User enters OTP: "123456" | OTP verified | `is_authenticated=True`<br>User record created/updated | ✓ OTP verification success<br>✓ OTP_VERIFICATION_SUCCESS message<br>✓ Auth event logged |
| 6 | (Bot sends email) | Single result email sent | Email contains single optimized prompt | ✓ Email delivered to inbox<br>✓ Subject: Contains method name<br>✓ Body: Original prompt + optimized version |
| 7 | (Bot confirms) | EMAIL_OPTIMIZATION_SUCCESS message | All states reset<br>Ready for new prompt | ✓ Success message shown<br>✓ Reset button available<br>✓ Can start new optimization |

**Email Content Verification:**
- Subject line includes method name (CRAFT/LYRA/GGL)
- Email contains original prompt
- Email contains single optimized result
- Professional formatting
- No technical errors or tags visible

**Success Criteria:**
- ✅ Authentication flow works correctly
- ✅ Email delivered successfully
- ✅ Single method result sent (not all 3 methods)
- ✅ State properly reset after completion

---

### Path 2E: Post-Optimization Email After Follow-up Completion

**Description**: User completed follow-up conversation, then uses post-optimization email button

**Preconditions:**
- User completed follow-up conversation (Path 2A)
- State: `post_optimization_result` contains follow_up result
- `waiting_for_prompt = True`

**Steps and Expected Outcomes:**

Same flow as Path 2D, but email content differs:

| Step | Difference from Path 2D | Verification Points |
|------|-------------------------|---------------------|
| 6 | Email contains refined prompt from follow-up | ✓ Method name: "Follow-up Optimization"<br>✓ Original prompt included<br>✓ Refined prompt (not initial optimization) |

**Email Content Verification:**
- Subject: "Follow-up Optimization"
- Contains original user prompt
- Contains refined prompt from follow-up Q&A
- Shows improvement from user feedback
- Professional formatting

**Success Criteria:**
- ✅ Refined prompt sent (not initial optimization)
- ✅ Follow-up improvements visible in email
- ✅ Original prompt for comparison

---

### Path 2F: Follow-up with Generate Button Mid-Conversation

**Description**: User clicks generate button before bot naturally concludes

**Preconditions:**
- User in follow-up conversation
- Bot has asked 1-2 questions
- User answered at least 1 question

**Steps and Expected Outcomes:**

| Step | User Action | System Response | State After | Verification Points |
|------|------------|-----------------|-------------|---------------------|
| 1-3 | Follow Path 2A steps 1-3 | Same as Path 2A | Same as Path 2A | Same verification |
| 4 | Click "🤖Сгенерировать промпт" instead of answering | `<GENERATE_PROMPT>` signal sent to LLM | Signal added to transcript | ✓ Generate signal in conversation<br>✓ No user answer added |
| 5 | (Bot generates from current context) | LLM returns refined prompt based on answers so far | Refined prompt extracted | ✓ Prompt incorporates existing answers<br>✓ Quality reasonable despite fewer answers |
| 6-8 | Same as Path 2A steps 7-8 | Same as Path 2A | Same as Path 2A | Same verification |

**Success Criteria:**
- ✅ Generate button works at any conversation stage
- ✅ Refined prompt uses available context
- ✅ Quality proportional to information gathered

---

### Path 2G: Follow-up Conversation State Recovery

**Description**: System recovers from corrupted follow-up state

**Preconditions:**
- Follow-up conversation in progress
- State becomes corrupted or inconsistent

**Corruption Scenarios:**

| Scenario | Detection | Recovery Action | Verification Points |
|----------|-----------|-----------------|---------------------|
| Missing cached prompt | `improved_prompt_cache` is None | Return ERROR_STATE_RECOVERY_FAILED | ✓ User prompted to restart<br>✓ State fully reset |
| Invalid transcript | System prompt missing or wrong | Return ERROR_STATE_CORRUPTED_RESTART | ✓ Recovery attempted<br>✓ State reset if fails |
| State flag mismatch | `in_followup_conversation` doesn't match conversation manager | Validate and attempt recovery | ✓ Cached prompt used if available<br>✓ ERROR_STATE_RECOVERY_SUCCESS if successful |

**Success Criteria:**
- ✅ Corruption detected early
- ✅ Recovery attempted with cached data
- ✅ User informed of issue
- ✅ Graceful fallback to restart

---

### Path 2H: Follow-up Response Parsing Edge Cases

**Description**: Handle malformed LLM responses during follow-up

**Edge Cases:**

| Edge Case | Detection | Handling | Verification Points |
|-----------|-----------|----------|---------------------|
| Empty `<REFINED_PROMPT>` tags | Tags present but no content | Fallback parsing attempted | ✓ Content extraction from alternative markers<br>✓ Falls back to original response if extraction fails |
| Malformed closing tags | `</REFINED_PROMPT>` variations | Pattern matching for variants | ✓ Handles `<END REFINED_PROMPT>`, `[END REFINED_PROMPT]`, etc. |
| No tags in final response | Expected refined prompt but no tags | Return original response as question | ✓ Continue conversation<br>✓ No premature completion |
| Multiple tag blocks | Multiple `<REFINED_PROMPT>` sections | Use first complete block | ✓ First valid block extracted<br>✓ Clean output |

**Success Criteria:**
- ✅ Robust parsing handles variants
- ✅ Never shows XML tags to user
- ✅ Graceful fallback for unparseable responses

---

## Path Category 3: Email Delivery

### Path 3A: Email Delivery - New User (Full Authentication)

**Description**: First-time user requests all 3 methods via email with full OTP flow

**Preconditions:**
- User has provided initial prompt
- State: `waiting_for_method = True`
- User NOT authenticated (no prior email verification)
- All services healthy (Redis, SMTP, PostgreSQL)

**Steps and Expected Outcomes:**

| Step | User Action | System Response | State After | Verification Points |
|------|------------|-----------------|-------------|---------------------|
| 1 | Click "📧 Отправить 3 промпта на email" button | Health checks performed | Health monitor checked | ✓ Redis health: OK<br>✓ SMTP health: OK (or warning if unhealthy) |
| 2 | (Bot checks auth status) | User not authenticated detected | Email flow initiated | ✓ Original prompt stored in email_flow_data<br>✓ Flow type: regular (not post-optimization) |
| 3 | (Bot requests email) | EMAIL_INPUT_MESSAGE | `waiting_for_prompt=False`<br>`waiting_for_email_input=True` | ✓ Email input prompt shown<br>✓ Reset button available |
| 4 | User types: "user@example.com" | Email format validation | Email normalized | ✓ Format validation passes<br>✓ No injection detected<br>✓ Email normalized (lowercase, trimmed) |
| 5 | (Bot checks rate limits) | All rate limit checks pass | Rate limits OK | ✓ Email limit: <3/hour<br>✓ User limit: <5/hour<br>✓ Spacing: >60s since last send |
| 6 | (Bot generates OTP) | 6-digit OTP generated | OTP hashed with Argon2id | ✓ OTP is 6 digits (100000-999999)<br>✓ Cryptographically secure<br>✓ Hash stored in Redis |
| 7 | (Bot stores OTP) | OTP data stored in Redis | TTL: 300 seconds<br>Attempts: 0 | ✓ Key: `otp:{telegram_id}`<br>✓ Data: hash, normalized_email, original_email, expires_at<br>✓ TTL set correctly |
| 8 | (Bot sends OTP email) | Email service sends OTP | Email sent | ✓ **Manual Check**: Email arrives in inbox<br>✓ Subject: "Your Verification Code"<br>✓ Body contains 6-digit OTP<br>✓ Arrival time: <30 seconds |
| 9 | (Bot shows OTP prompt) | EMAIL_OTP_SENT message with masked email | `waiting_for_email_input=False`<br>`waiting_for_otp_input=True` | ✓ Message shows masked email (u***@example.com)<br>✓ Instructions clear<br>✓ Reset button available |
| 10 | (Bot increments counters) | Rate limit counters incremented | Counters updated | ✓ Email counter +1<br>✓ User counter +1<br>✓ Spacing timestamp set |
| 11 | (Bot logs event) | Auth event logged | AuthEvent record created | ✓ Event type: OTP_SENT<br>✓ Success: true<br>✓ Masked email logged |
| 12 | User types: "123456" (correct OTP) | OTP format validation | Format valid | ✓ 6 digits<br>✓ Numeric only |
| 13 | (Bot retrieves OTP data) | OTP data fetched from Redis | OTP data found | ✓ OTP exists<br>✓ Not expired (expires_at > current_time) |
| 14 | (Bot verifies OTP) | OTP hash verification | Hash matches | ✓ Argon2id verification successful<br>✓ Attempts: 1 |
| 15 | (Bot persists auth) | User record created in PostgreSQL | User authenticated | ✓ User record created with telegram_id, email<br>✓ is_authenticated: true<br>✓ email_verified_at: current_time<br>✓ Profile data extracted if available |
| 16 | (Bot cleans up) | OTP deleted from Redis | OTP removed | ✓ Redis key deleted<br>✓ Reason: verification_success |
| 17 | (Bot logs success) | Auth event logged | AuthEvent created | ✓ Event type: OTP_VERIFIED<br>✓ Success: true |
| 18 | (Bot confirms) | OTP_VERIFICATION_SUCCESS message | `waiting_for_otp_input=False` | ✓ Verification success message shown |
| 19 | (Bot shows processing) | INFO_ALL_METHODS_OPTIMIZATION message | Processing all 3 methods | ✓ Processing message clear<br>✓ Reset button shown |
| 20 | (Bot runs CRAFT) | CRAFT optimization executed | CRAFT result obtained | ✓ CRAFT system prompt (email variant) used<br>✓ Original prompt as input<br>✓ Response captured |
| 21 | (Bot runs LYRA) | LYRA optimization executed | LYRA result obtained | ✓ LYRA system prompt (email variant) used<br>✓ Same prompt as input<br>✓ Response captured |
| 22 | (Bot runs GGL) | GGL optimization executed | GGL result obtained | ✓ GGL system prompt (email variant) used<br>✓ Same prompt as input<br>✓ Response captured |
| 23 | (Bot sends email) | Optimization results email sent | Email delivered | ✓ **Manual Check**: Email arrives<br>✓ Subject: "Your Optimized Prompts"<br>✓ Contains original prompt<br>✓ Contains all 3 optimized versions<br>✓ Clear section headings<br>✓ Professional formatting |
| 24 | (Bot confirms) | EMAIL_OPTIMIZATION_SUCCESS message | All states reset | ✓ Success message shown<br>✓ `waiting_for_prompt=True`<br>✓ Email flow data cleared<br>✓ Ready for new interaction |

**Email Content Verification (Step 23):**

**Subject Line:**
- "Your Optimized Prompts - Telegram Prompt Bot" or similar

**Email Structure:**
```
Hello,

Here are your optimized prompts using all three methods:

ORIGINAL PROMPT:
[User's original prompt]

---

🛠 CRAFT OPTIMIZED PROMPT:
[CRAFT optimization result]

---

⚡ LYRA OPTIMIZED PROMPT:
[LYRA optimization result]

---

🎯 GGL OPTIMIZED PROMPT:
[GGL optimization result]

---

Choose the version that best fits your needs!
```

**Quality Checks:**
- All 3 methods present and labeled clearly
- No XML tags visible
- Original prompt for comparison
- Professional formatting (HTML email preferred)
- No technical errors

**Success Criteria:**
- ✅ Complete authentication flow successful
- ✅ OTP email delivered and verified
- ✅ All 3 optimizations completed
- ✅ Results email delivered with all content
- ✅ User authenticated for future use
- ✅ All rate limits respected
- ✅ Audit trail complete
- ✅ State properly reset

**Database Verification:**
```sql
-- Verify user created
SELECT telegram_id, email, is_authenticated, email_verified_at 
FROM users WHERE telegram_id = {user_id};

-- Verify auth events
SELECT event_type, success, reason, created_at 
FROM auth_events 
WHERE telegram_id = {user_id} 
ORDER BY created_at DESC;

-- Expected events: OTP_SENT (success), OTP_VERIFIED (success)
```

**Redis Verification:**
```
-- OTP should be deleted after success
GET otp:{telegram_id}  # Should return null

-- Rate limit counters should be incremented
GET rate:email:{normalized_email}  # Should show 1
GET rate:user:{telegram_id}  # Should show 1
```

---

### Path 3B: Email Delivery - Authenticated User (Skip OTP)

**Description**: Returning user with verified email requests email delivery, skips OTP

**Preconditions:**
- User previously completed Path 3A
- User record exists with `is_authenticated = True`
- User has provided initial prompt
- State: `waiting_for_method = True`

**Steps and Expected Outcomes:**

| Step | User Action | System Response | State After | Verification Points |
|------|------------|-----------------|-------------|---------------------|
| 1 | Click "📧 Отправить 3 промпта на email" button | Health checks performed | Health monitor OK | ✓ Same as Path 3A step 1 |
| 2 | (Bot checks auth status) | User IS authenticated detected | Email retrieved from database | ✓ User query successful<br>✓ is_authenticated: true<br>✓ Email retrieved |
| 3 | (Bot confirms) | EMAIL_ALREADY_AUTHENTICATED message with masked email | Email flow data set with existing email | ✓ Message: "✅ Вы уже авторизованы! Ваш email u***@example.com"<br>✓ Reset button shown |
| 4 | (Bot proceeds directly) | SKIP steps 3-18 from Path 3A | Jump to optimization | ✓ No email input needed<br>✓ No OTP flow<br>✓ Direct to processing |
| 5-11 | Same as Path 3A steps 19-24 | Same optimization and email delivery | Same end state | ✓ All 3 methods executed<br>✓ Email delivered<br>✓ Success message shown |

**Success Criteria:**
- ✅ Authentication bypassed correctly
- ✅ Existing email used automatically
- ✅ Same quality results as new user
- ✅ Faster flow (no OTP steps)
- ✅ User experience improved

**Time Comparison:**
- New user (Path 3A): ~24 steps
- Authenticated user (Path 3B): ~11 steps
- Time saved: ~60-90 seconds

---

### Path 3C: OTP Verification Failures

**Description**: Various OTP verification failure scenarios

**Preconditions:**
- User in OTP input stage (Path 3A step 12)
- OTP stored in Redis
- State: `waiting_for_otp_input = True`

#### Scenario 3C-1: Invalid OTP Code (Attempts Remaining)

| Step | User Action | System Response | State After | Verification Points |
|------|------------|-----------------|-------------|---------------------|
| 1 | User types: "000000" (wrong OTP) | OTP validation fails | Attempts incremented to 1 | ✓ Hash verification fails<br>✓ Attempts < max (3) |
| 2 | (Bot logs failure) | Auth event logged | Event: OTP_MISMATCH | ✓ Event logged<br>✓ Reason: "attempt_1" |
| 3 | (Bot shows error) | ERROR_OTP_INVALID with attempts remaining | Still waiting for OTP | ✓ Message: "❌ Неверный код. Попробуйте еще раз (осталось попыток: 2)"<br>✓ Can retry |
| 4 | User types: "111111" (wrong again) | Same validation failure | Attempts incremented to 2 | ✓ Attempts: 2<br>✓ Still can retry |
| 5 | (Bot shows error) | ERROR_OTP_INVALID | Still waiting | ✓ Message shows 1 attempt remaining |
| 6 | User types: "123456" (correct) | Verification succeeds | Auth successful | ✓ User authenticated<br>✓ Proceeds to Path 3A step 15 |

**Success Criteria:**
- ✅ Up to 3 attempts allowed
- ✅ Attempt counter accurate
- ✅ User can recover with correct OTP
- ✅ Clear feedback on remaining attempts

#### Scenario 3C-2: OTP Attempts Exceeded

| Step | User Action | System Response | State After | Verification Points |
|------|------------|-----------------|-------------|---------------------|
| 1-5 | Same as 3C-1 steps 1-5 | 2 failed attempts | Attempts: 2 | Same as 3C-1 |
| 6 | User types: "999999" (wrong, 3rd attempt) | Verification fails, limit exceeded | Attempts: 3<br>OTP deleted | ✓ Attempts reached max (3)<br>✓ OTP removed from Redis |
| 7 | (Bot logs failure) | Auth event logged | Event: OTP_FAILED | ✓ Event type: OTP_FAILED<br>✓ Reason: "attempt_limit_exceeded" |
| 8 | (Bot shows error) | ERROR_OTP_ATTEMPTS_EXCEEDED | State reset | ✓ Message: "❌ Превышено количество попыток ввода кода. Пожалуйста, запросите новый код."<br>✓ Reset button shown |
| 9 | (User must restart) | Must start email flow again | Return to beginning | ✓ OTP deleted<br>✓ Must request new OTP |

**Success Criteria:**
- ✅ 3-attempt limit enforced
- ✅ OTP deleted after max attempts
- ✅ Clear error message
- ✅ User must restart flow

**Redis Verification:**
```
GET otp:{telegram_id}  # Should return null after max attempts
```

#### Scenario 3C-3: OTP Expired

| Step | User Action | System Response | State After | Verification Points |
|------|------------|-----------------|-------------|---------------------|
| 1 | (Wait >5 minutes after OTP sent) | TTL expires | OTP may still exist but expired | ✓ Time elapsed > 300 seconds |
| 2 | User types: "123456" (correct but expired) | Expiry check fails | OTP deleted | ✓ expires_at < current_time<br>✓ OTP removed from Redis |
| 3 | (Bot logs expiry) | Auth event logged | Event: OTP_EXPIRED | ✓ Event type: OTP_EXPIRED<br>✓ Reason: "expired" |
| 4 | (Bot shows error) | ERROR_OTP_EXPIRED | State reset | ✓ Message: "❌ Код истек. Пожалуйста, запросите новый код."<br>✓ Reset button shown |

**Success Criteria:**
- ✅ 5-minute expiry enforced
- ✅ Expired OTP rejected even if correct
- ✅ Clear expiry message
- ✅ OTP cleaned up

#### Scenario 3C-4: OTP Not Found

| Step | User Action | System Response | State After | Verification Points |
|------|------------|-----------------|-------------|---------------------|
| 1 | User types OTP but Redis cleared | OTP lookup returns None | No OTP data | ✓ Redis key doesn't exist<br>✓ Could be expired, deleted, or never sent |
| 2 | (Bot logs event) | Auth event logged | Event: OTP_NOT_FOUND | ✓ Event type: OTP_NOT_FOUND<br>✓ Reason: "no_otp_stored" |
| 3 | (Bot shows error) | Generic error message | State reset | ✓ User informed<br>✓ Must restart |

**Success Criteria:**
- ✅ Missing OTP handled gracefully
- ✅ No system crashes
- ✅ User guided to restart

---

### Path 3D: Rate Limiting Scenarios

**Description**: Various rate limit enforcement scenarios

**Preconditions:**
- User attempting to send OTP
- Rate limit counters may be elevated

#### Scenario 3D-1: Email Rate Limit (3/hour per email)

| Step | User Action | System Response | State After | Verification Points |
|------|------------|-----------------|-------------|---------------------|
| 1 | User requests OTP for "user@example.com" (1st time) | Rate check passes | Counter: 1 | ✓ Email counter incremented<br>✓ OTP sent successfully |
| 2 | User requests OTP for same email (2nd time) | Rate check passes | Counter: 2 | ✓ Still under limit<br>✓ OTP sent |
| 3 | User requests OTP for same email (3rd time) | Rate check passes (last allowed) | Counter: 3 | ✓ At limit<br>✓ OTP sent |
| 4 | User requests OTP for same email (4th time) | Rate check FAILS | Counter: 3 (not incremented) | ✓ Rate limit exceeded<br>✓ OTP NOT sent |
| 5 | (Bot logs rate limit) | Auth event logged | Event: OTP_RATE_LIMITED | ✓ Event type: OTP_RATE_LIMITED<br>✓ Reason: "email_limit_exceeded_4/3" |
| 6 | (Bot shows error) | ERROR_EMAIL_RATE_LIMITED | Email input reset | ✓ Message: "⚠️ Слишком много попыток отправки кода. Попробуйте позже."<br>✓ Reset button shown |
| 7 | (Wait 1 hour) | Counter expires in Redis | Counter resets to 0 | ✓ TTL: 3600 seconds<br>✓ Key auto-deleted after expiry |

**Redis Verification:**
```
# Check email rate limit
GET rate:email:user@example.com  # Returns counter value
TTL rate:email:user@example.com  # Returns remaining seconds

# After 1 hour
GET rate:email:user@example.com  # Should return null
```

**Success Criteria:**
- ✅ 3 OTPs per email per hour enforced
- ✅ Counter accurate across attempts
- ✅ TTL auto-cleanup working
- ✅ Clear error message

#### Scenario 3D-2: User Rate Limit (5/hour per telegram_id)

| Step | User Action | System Response | Verification Points |
|------|------------|-----------------|---------------------|
| 1-5 | User requests OTP 5 times with different emails | All pass | ✓ 5 different emails used<br>✓ All OTPs sent |
| 6 | User requests OTP (6th time, new email) | User rate limit exceeded | ✓ User counter: 6/5<br>✓ OTP NOT sent<br>✓ ERROR_EMAIL_RATE_LIMITED shown |

**Success Criteria:**
- ✅ 5 OTPs per user per hour enforced
- ✅ Prevents abuse via multiple emails
- ✅ Counter independent of email counter

#### Scenario 3D-3: Spacing Enforcement (60 seconds between sends)

| Step | User Action | System Response | Verification Points |
|------|------------|-----------------|---------------------|
| 1 | User requests OTP | OTP sent | ✓ Spacing timestamp set |
| 2 | User requests OTP again after 30 seconds | Spacing check FAILS | ✓ Elapsed: 30s < 60s required<br>✓ OTP NOT sent<br>✓ Error message with remaining time |

**Success Criteria:**
- ✅ 60-second spacing enforced
- ✅ Prevents rapid-fire requests
- ✅ Error shows remaining wait time

---

### Path 3E: SMTP Fallback Scenarios

**Description**: Email delivery fails, system falls back or blocks gracefully

**Preconditions:**
- User requesting email delivery
- SMTP service may be unhealthy

#### Scenario 3E-1: SMTP Unhealthy - Block Email Flow

| Step | System State | System Response | Verification Points |
|------|-------------|-----------------|---------------------|
| 1 | User clicks email delivery button | Health check performed | ✓ Health monitor checked |
| 2 | SMTP health check FAILS | Flow blocked | ✓ `is_service_healthy("smtp")` returns false |
| 3 | (Bot shows error) | ERROR_SMTP_UNAVAILABLE | ✓ Message: "⚠️ Не удается отправить email. Попробуйте позже."<br>✓ Reset button shown<br>✓ No prompt sharing in chat |

**Success Criteria:**
- ✅ Email flow blocked when SMTP unhealthy
- ✅ Clear error message
- ✅ No fallback to chat (security requirement)
- ✅ User can try again later

#### Scenario 3E-2: SMTP Fails During Send

| Step | System State | System Response | Verification Points |
|------|-------------|-----------------|---------------------|
| 1-22 | Path 3A steps 1-22 complete | All optimizations done | ✓ 3 results ready to send |
| 23 | Email send fails | `email_result.success = False` | ✓ SMTP error occurred<br>✓ Error logged |
| 24 | (Bot shows error) | ERROR_EMAIL_OPTIMIZATION_FAILED | ✓ Error message shown<br>✓ NO prompts shown in chat<br>✓ User must retry later |

**Success Criteria:**
- ✅ Email failure handled gracefully
- ✅ No data exposed in chat
- ✅ User informed to retry
- ✅ Optimization work not lost (can retry)

**Security Note:**
- Optimized prompts are NOT sent to Telegram chat as fallback
- This prevents potential data leakage
- User must wait for SMTP recovery

---

### Path 3F: Post-Optimization Email - Authenticated User

**Description**: Quick path for authenticated user sending single result

**Preconditions:**
- User completed single method or follow-up
- `post_optimization_result` is set
- User IS authenticated

**Steps and Expected Outcomes:**

| Step | User Action | System Response | State After | Verification Points |
|------|------------|-----------------|-------------|---------------------|
| 1 | Click "📧 Отправить промпт на e-mail" button | Auth check | User authenticated | ✓ Email retrieved from DB |
| 2 | (Bot confirms auth) | EMAIL_ALREADY_AUTHENTICATED | Skip OTP flow | ✓ Masked email shown |
| 3 | (Bot sends email) | Single result email sent | Email delivered | ✓ **Manual Check**: Email arrives<br>✓ Contains single result (not 3 methods)<br>✓ Method name in subject |
| 4 | (Bot confirms) | EMAIL_OPTIMIZATION_SUCCESS | States reset | ✓ Success message<br>✓ Ready for new prompt |

**Email Content:**
- Subject: "[Method Name] Optimized Prompt"
- Body: Original + single optimized result
- Faster delivery than Path 3A

**Success Criteria:**
- ✅ Fast path for authenticated users
- ✅ Single result email format
- ✅ No OTP delay

---

## Path Category 4: State Management & Errors

### Path 4A: Reset Conversation at Any Point

**Description**: User clicks reset button at any stage of interaction

**Test Scenarios:**

| Scenario | Starting State | Reset Action | Expected Outcome | Verification Points |
|----------|---------------|--------------|------------------|---------------------|
| 4A-1 | Method selection screen | Click "🔄 Сбросить диалог" | Return to welcome | ✓ WELCOME_MESSAGE shown<br>✓ All states reset<br>✓ `waiting_for_prompt=True` |
| 4A-2 | During LLM processing | Click "🔄 Сбросить диалог" | Interrupt and reset | ✓ Processing stopped (if possible)<br>✓ Fresh start<br>✓ Token counters reset |
| 4A-3 | Follow-up conversation | Click "🔄 Сбросить диалог" | Exit follow-up, reset | ✓ Follow-up state cleared<br>✓ Cached prompt cleared<br>✓ Fresh start |
| 4A-4 | Email input stage | Click "🔄 Сбросить диалог" | Cancel email flow | ✓ Email flow data cleared<br>✓ OTP not sent<br>✓ Fresh start |
| 4A-5 | OTP input stage | Click "🔄 Сбросить диалог" | Cancel authentication | ✓ OTP remains in Redis (expires naturally)<br>✓ Flow cancelled<br>✓ Fresh start |
| 4A-6 | Post-optimization | Click "🔄 Сбросить диалог" | Clear cached result | ✓ `post_optimization_result` cleared<br>✓ Fresh start |

**Universal Reset Behavior:**

| Component | Reset Action | Verification |
|-----------|-------------|--------------|
| State Manager | All flags reset to defaults | ✓ `waiting_for_prompt=True`<br>✓ All other flags False<br>✓ Caches cleared |
| Conversation Manager | Transcript cleared | ✓ Empty transcript<br>✓ User prompt cleared<br>✓ Method selection reset<br>✓ Token totals reset |
| Email Flow | Flow data cleared | ✓ `email_flow_data=None`<br>✓ `post_optimization_result=None` |
| Redis | Flow state deleted (OTP preserved) | ✓ `flow:{telegram_id}` deleted<br>✓ OTP expires naturally |

**Success Criteria:**
- ✅ Reset works from ANY state
- ✅ Clean slate for new interaction
- ✅ No lingering state bugs
- ✅ User can always escape

---

### Path 4B: State Corruption Recovery

**Description**: System detects and recovers from corrupted state

#### Scenario 4B-1: Corrupted Follow-up State

| Step | Detection | System Response | Verification Points |
|------|-----------|-----------------|---------------------|
| 1 | Follow-up flag set but no transcript | `_validate_followup_state()` fails | ✓ Validation detects inconsistency |
| 2 | (Bot attempts recovery) | Check for cached prompt | ✓ Recovery method called |
| 3a | Cached prompt available | Send ERROR_STATE_RECOVERY_SUCCESS + cached prompt | ✓ User gets usable prompt<br>✓ State reset<br>✓ Can continue |
| 3b | No cached prompt | Send ERROR_STATE_CORRUPTED_RESTART | ✓ User informed to restart<br>✓ State fully reset |

**Success Criteria:**
- ✅ Corruption detected early
- ✅ Recovery attempted
- ✅ User not stuck
- ✅ Data loss minimized

#### Scenario 4B-2: Invalid Transcript Structure

| Trigger | Detection | Recovery | Verification Points |
|---------|-----------|----------|---------------------|
| Missing system prompt | First message not "system" role | Validation fails | ✓ `_validate_followup_transcript()` catches<br>✓ Recovery initiated |
| Empty transcript | Transcript length < 2 | Validation fails | ✓ Detected<br>✓ Reset triggered |
| Missing follow-up indicator | System prompt doesn't contain expected text | Validation fails | ✓ String match fails<br>✓ State recovered |

**Success Criteria:**
- ✅ Transcript validation comprehensive
- ✅ Invalid structures caught
- ✅ Safe fallback behavior

---

### Path 4C: LLM API Errors and Retry Logic

**Description**: Handle various LLM API error scenarios

#### Scenario 4C-1: Temporary Network Error

| Step | Error Type | System Response | Verification Points |
|------|-----------|-----------------|---------------------|
| 1 | LLM API call fails with network error | Tenacity retry triggered | ✓ Error classified as network<br>✓ `_is_network_error()` returns true |
| 2 | (Retry attempt 1) | Wait 1 second, retry | ✓ Exponential backoff: 1s<br>✓ Warning logged |
| 3 | (Retry attempt 2) | Wait 2 seconds, retry | ✓ Backoff: 2s<br>✓ Still retrying |
| 4 | (Retry attempt 3 succeeds) | LLM returns response | ✓ Total attempts: 3<br>✓ Success after retries<br>✓ User sees result |

**Success Criteria:**
- ✅ Up to 3 retries for network errors
- ✅ Exponential backoff (1s, 2s, 4s)
- ✅ Success after transient failure
- ✅ User unaware of retries

#### Scenario 4C-2: Rate Limit Error

| Step | Error Type | System Response | Verification Points |
|------|-----------|-----------------|---------------------|
| 1 | LLM API returns 429 (rate limit) | Error caught | ✓ Rate limit detected |
| 2 | (No retries for rate limits) | Show ERROR_RATE_LIMIT | ✓ No retries attempted<br>✓ Error message: "⚠️ Слишком много запросов. Подождите."<br>✓ User informed |

**Success Criteria:**
- ✅ Rate limits not retried (would fail anyway)
- ✅ Clear user message
- ✅ User waits and retries manually

#### Scenario 4C-3: All Retries Exhausted

| Step | Error Type | System Response | Verification Points |
|------|-----------|-----------------|---------------------|
| 1-4 | Network errors on all 3 retry attempts | All retries fail | ✓ 3 attempts made<br>✓ All failed |
| 5 | (RetryError raised) | Generic error shown | ✓ ERROR_GENERIC message<br>✓ Reset button available<br>✓ Error logged |

**Success Criteria:**
- ✅ Retries exhausted gracefully
- ✅ User informed of failure
- ✅ Can retry manually

#### Scenario 4C-4: Invalid API Response

| Step | Issue | System Response | Verification Points |
|------|-------|-----------------|---------------------|
| 1 | LLM returns empty string | Response validation fails | ✓ Empty check catches<br>✓ Logged as warning |
| 2 | (Fallback handling) | ERROR_GENERIC shown | ✓ User informed<br>✓ State reset<br>✓ Can retry |

**Success Criteria:**
- ✅ Invalid responses caught
- ✅ No crashes
- ✅ Clear error handling

---

### Path 4D: Network Timeout and Fallback

**Description**: Handle network timeouts during critical operations

#### Scenario 4D-1: Telegram API Timeout (Message Send)

| Step | Error Type | System Response | Verification Points |
|------|-----------|-----------------|---------------------|
| 1 | Bot tries to send message | Network timeout | ✓ Timeout detected |
| 2 | (Retry logic) | Tenacity retries up to 3 times | ✓ Message send retried<br>✓ Backoff applied |
| 3a | Retry succeeds | Message delivered | ✓ User receives message<br>✓ Flow continues normally |
| 3b | All retries fail | Error logged, flow continues | ✓ Failure logged<br>✓ Bot continues (best effort) |

**Success Criteria:**
- ✅ Message sending retried
- ✅ Flow not blocked by single failure
- ✅ Graceful degradation

#### Scenario 4D-2: LLM API Timeout

| Step | Error Type | System Response | Verification Points |
|------|-----------|-----------------|---------------------|
| 1 | LLM API call times out (>60s) | Timeout exception raised | ✓ Request timeout configured<br>✓ Exception caught |
| 2 | (Classification) | Classified as timeout error | ✓ "timeout" in error string |
| 3 | (User notification) | ERROR_NETWORK shown | ✓ Message: "🌐 Ошибка сети. Проверьте подключение."<br>✓ Reset button |

**Success Criteria:**
- ✅ Timeouts don't crash bot
- ✅ User informed
- ✅ Can retry operation

#### Scenario 4D-3: Redis Connection Timeout

| Step | Error Type | System Response | Verification Points |
|------|-----------|-----------------|---------------------|
| 1 | Redis operation times out | Exception in Redis client | ✓ Connection timeout |
| 2 | (For email flow) | Email flow blocked | ✓ Health check fails<br>✓ ERROR_REDIS_UNAVAILABLE shown |
| 3 | (For OTP operations) | Operation fails gracefully | ✓ Error logged<br>✓ User informed |

**Success Criteria:**
- ✅ Redis failures don't crash bot
- ✅ Critical flows blocked when Redis unavailable
- ✅ Clear user messaging

---

## Validation Checklists

### Pre-Test Setup Checklist

- [ ] **Services Running**
  - [ ] Telegram Bot API accessible
  - [ ] PostgreSQL database running and migrated
  - [ ] Redis server running and accessible
  - [ ] SMTP server configured and accessible
  - [ ] LLM API (OpenAI/OpenRouter) accessible with valid key

- [ ] **Database State**
  - [ ] Tables created: `users`, `auth_events`
  - [ ] Indexes created: `ix_users_language_code`, `ix_users_is_premium`, etc.
  - [ ] Test user data cleared (if needed)

- [ ] **Configuration**
  - [ ] `.env` file complete with all required variables
  - [ ] `TELEGRAM_TOKEN` valid
  - [ ] LLM backend configured (`LLM_BACKEND`, API keys)
  - [ ] Email configuration set (SMTP settings)
  - [ ] Google service account configured (if using sheets logging)

- [ ] **Testing Tools**
  - [ ] Telegram client ready for manual testing
  - [ ] Email inbox accessible for manual verification
  - [ ] Database client for verification queries
  - [ ] Redis CLI for state inspection
  - [ ] Logs accessible (console or file)

### Post-Test Cleanup Checklist

- [ ] **Database Cleanup**
  - [ ] Remove test users from `users` table
  - [ ] Clear `auth_events` for test users
  - [ ] Reset sequences if needed

- [ ] **Redis Cleanup**
  - [ ] Delete test OTP keys: `otp:{telegram_id}`
  - [ ] Clear test rate limit counters
  - [ ] Remove test flow states

- [ ] **Rate Limit Reset**
  - [ ] Wait for TTL expiry or manually clear
  - [ ] Verify counters reset for next test run

### Per-Path Validation Checklist

For each user path tested:

- [ ] **Message Verification**
  - [ ] All bot messages display correctly
  - [ ] Markdown formatting renders properly
  - [ ] Button layouts match specifications
  - [ ] No error messages visible to user

- [ ] **State Verification**
  - [ ] All state flags accurate after each step
  - [ ] Conversation transcripts properly maintained
  - [ ] Redis data matches expected structure
  - [ ] Database records created/updated correctly

- [ ] **Functional Verification**
  - [ ] All buttons work as expected
  - [ ] User input handled correctly
  - [ ] LLM responses appropriate and formatted
  - [ ] Email delivery successful (if applicable)
  - [ ] Token usage tracked accurately

- [ ] **Error Handling Verification**
  - [ ] Rate limits enforced
  - [ ] Invalid input rejected gracefully
  - [ ] Timeouts handled appropriately
  - [ ] Service failures trigger correct fallbacks

- [ ] **Security Verification**
  - [ ] Emails masked in logs
  - [ ] Telegram IDs masked in logs
  - [ ] OTPs hashed in Redis
  - [ ] Rate limiting prevents abuse
  - [ ] No sensitive data exposed

### LLM Response Quality Checklist

For each optimization result:

- [ ] **Technical Quality**
  - [ ] No XML tags visible to user
  - [ ] Proper markdown formatting
  - [ ] Response is complete (not truncated)
  - [ ] No system errors in output

- [ ] **Semantic Quality**
  - [ ] Prompt is more specific than original
  - [ ] Adds useful context or structure
  - [ ] Maintains user's intent
  - [ ] Actionable and clear

- [ ] **Method-Specific Traits**
  - [ ] По шагам (CRAFT): Structured sections, comprehensive
  - [ ] Быстро (LYRA): Concise, focused, efficient
  - [ ] Под результат (GGL): Goal-oriented, outcome-focused

- [ ] **Edge Case Handling**
  - [ ] Very short prompts: Adds appropriate detail
  - [ ] Very long prompts: Maintains coherence
  - [ ] Ambiguous prompts: Seeks clarification or makes reasonable assumptions

### Email Verification Checklist

For email delivery tests:

- [ ] **OTP Email**
  - [ ] Arrives within 30 seconds
  - [ ] Subject line clear
  - [ ] OTP code visible (6 digits)
  - [ ] Professional formatting
  - [ ] No broken HTML/formatting

- [ ] **Optimization Results Email**
  - [ ] Arrives within 60 seconds of send
  - [ ] Subject line descriptive
  - [ ] Original prompt included
  - [ ] All 3 methods present (or single method for post-opt)
  - [ ] Clear section headings
  - [ ] No XML tags visible
  - [ ] Professional HTML formatting
  - [ ] Readable on mobile and desktop

### Database Verification Queries

```sql
-- Check user authentication status
SELECT telegram_id, email, is_authenticated, 
       email_verified_at, last_authenticated_at,
       first_name, is_premium, language_code
FROM users 
WHERE telegram_id = {test_user_id};

-- Check authentication events
SELECT event_type, success, reason, created_at
FROM auth_events
WHERE telegram_id = {test_user_id}
ORDER BY created_at DESC
LIMIT 10;

-- Verify no duplicate emails
SELECT email, COUNT(*) as count
FROM users
GROUP BY email
HAVING COUNT(*) > 1;

-- Check profile data capture
SELECT COUNT(*) as total,
       COUNT(first_name) as with_first_name,
       COUNT(language_code) as with_language,
       SUM(CASE WHEN is_premium = true THEN 1 ELSE 0 END) as premium_users
FROM users;
```

### Redis Verification Commands

```bash
# Check OTP data
GET otp:{telegram_id}

# Check rate limit counters
GET rate:email:{email}
GET rate:user:{telegram_id}
GET spacing:{telegram_id}

# Check TTLs
TTL otp:{telegram_id}
TTL rate:email:{email}

# Check flow state
GET flow:{telegram_id}

# Clear test data
DEL otp:{telegram_id}
DEL rate:email:{test_email}
DEL rate:user:{test_telegram_id}
DEL spacing:{telegram_id}
DEL flow:{telegram_id}
```

---

## Appendix: Constants Reference

### Message Constants (from `src/messages.py`)

**Welcome & Instructions:**
- `WELCOME_MESSAGE`: Initial greeting and instructions
- `SELECT_METHOD_MESSAGE`: Method selection prompt
- `ENTER_PROMPT_MESSAGE`: Prompt input request

**Processing:**
- `get_processing_message(method)`: Dynamic processing message

**Follow-up:**
- `FOLLOWUP_OFFER_MESSAGE`: Offer for follow-up questions
- `FOLLOWUP_DECLINED_MESSAGE`: Confirmation of decline
- `PROMPT_READY_FOLLOW_UP`: Completion message after follow-up

**Email:**
- `EMAIL_INPUT_MESSAGE`: Request for email address
- `EMAIL_OTP_SENT`: OTP sent confirmation
- `EMAIL_ALREADY_AUTHENTICATED`: Skip OTP message
- `EMAIL_OPTIMIZATION_SUCCESS`: Email delivery success
- `OTP_VERIFICATION_SUCCESS`: OTP verified message

**Errors:**
- `ERROR_GENERIC`: Generic error message
- `ERROR_EMAIL_INVALID`: Invalid email format
- `ERROR_OTP_INVALID`: Invalid OTP code
- `ERROR_OTP_EXPIRED`: OTP expired
- `ERROR_OTP_ATTEMPTS_EXCEEDED`: Too many OTP attempts
- `ERROR_EMAIL_RATE_LIMITED`: Rate limit exceeded
- `ERROR_REDIS_UNAVAILABLE`: Redis service unavailable
- `ERROR_SMTP_UNAVAILABLE`: SMTP service unavailable
- `ERROR_STATE_CORRUPTED_RESTART`: State corruption detected
- `FOLLOWUP_TIMEOUT_FALLBACK`: Follow-up timeout with fallback

### Configuration Constants

**Rate Limits:**
- `email_rate_limit_per_hour`: 3 OTPs per email per hour
- `user_rate_limit_per_hour`: 5 OTPs per user per hour
- `otp_spacing_seconds`: 60 seconds between sends
- `otp_max_attempts`: 3 attempts per OTP
- `otp_ttl_seconds`: 300 seconds (5 minutes)

**Timeouts:**
- `followup_timeout_seconds`: 300 seconds (5 minutes)
- `openai_request_timeout`: 60.0 seconds
- `openrouter_timeout`: 60.0 seconds

### State Flag Reference

| Flag | Type | Purpose |
|------|------|---------|
| `waiting_for_prompt` | bool | Expecting user's initial prompt |
| `waiting_for_method` | bool | Expecting method selection |
| `waiting_for_followup_choice` | bool | Expecting YES/NO for follow-up |
| `in_followup_conversation` | bool | Active follow-up Q&A |
| `waiting_for_email_input` | bool | Expecting email address |
| `waiting_for_otp_input` | bool | Expecting OTP code |
| `improved_prompt_cache` | Optional[str] | Cached optimized prompt |
| `cached_method_name` | Optional[str] | Method name for cached prompt |
| `email_flow_data` | Optional[dict] | Email flow context |
| `post_optimization_result` | Optional[dict] | Result for post-opt email |

---

## Testing Summary

### Coverage Overview

| Category | Paths Documented | Normal Scenarios | Error Scenarios | Total Test Cases |
|----------|------------------|------------------|-----------------|------------------|
| Single Method Optimization | 4 | 4 | 0 | 4 |
| Follow-up Enhancement | 8 | 5 | 3 | 12+ |
| Email Delivery | 6 | 3 | 3 | 15+ |
| State Management & Errors | 4 | 1 | 3 | 10+ |
| **TOTAL** | **22** | **13** | **9** | **41+** |

### Test Execution Priority

**Priority 1 (Critical Paths - Must Pass):**
1. Path 1A: CRAFT method optimization
2. Path 2B: Decline follow-up
3. Path 3A: Email delivery - new user
4. Path 4A: Reset conversation

**Priority 2 (Core Features):**
5. Path 1B, 1C, 1D: Other methods
6. Path 2A: Complete follow-up conversation
7. Path 3B: Email delivery - authenticated user
8. Path 3C: OTP failures

**Priority 3 (Advanced Features):**
9. Path 2D, 2E: Post-optimization email
10. Path 3D: Rate limiting
11. Path 4C, 4D: Error handling

**Priority 4 (Edge Cases):**
12. Path 2F, 2G, 2H: Follow-up edge cases
13. Path 3E: SMTP fallback
14. Path 4B: State corruption

### Success Metrics

**Functional Success:**
- All Priority 1 paths pass 100%
- All Priority 2 paths pass ≥90%
- All Priority 3 paths pass ≥80%
- No critical security issues
- No data corruption issues

**Quality Success:**
- LLM responses semantically improved prompts in ≥90% of cases
- Email delivery success rate ≥95%
- OTP delivery within 30 seconds in ≥95% of cases
- Rate limiting prevents abuse in 100% of attempts

**User Experience Success:**
- Clear error messages in all failure scenarios
- State recovery successful in ≥90% of corruption cases
- Reset button works from all states 100% of time
- No user stuck states (100% escapable)

---

## Document Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-01-03 | Initial comprehensive documentation |

---

**End of E2E User Paths Documentation**

For questions or clarifications, refer to:
- Source code: `src/bot_handler.py`, `src/email_flow.py`, `src/auth_service.py`
- Message constants: `src/messages.py`
- State management: `src/state_manager.py`, `src/conversation_manager.py`

