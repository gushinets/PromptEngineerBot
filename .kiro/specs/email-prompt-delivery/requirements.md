# Requirements Document

## Introduction

This feature introduces email-based authentication and prompt delivery functionality to the existing Telegram bot. Users will be able to authenticate with their email address using a one-time password (OTP) system, and receive optimized prompts via email after completing the optimization process. The feature adds a new "Send 3 prompts to email" button that appears after users enter optimization mode, enabling them to receive results from all three optimization methods (CRAFT, LYRA, GGL) directly in their inbox.

## Requirements

### Requirement 1

**User Story:** As a user, I want to see a "Send 3 prompts to email" button after entering optimization mode, so that I can choose to receive optimized prompts via email instead of just viewing them in the chat.

#### Acceptance Criteria

1. WHEN user enters a prompt and reaches the method selection screen THEN system SHALL display a "Send 3 prompts to email" button above the existing three optimization method buttons (CRAFT, LYRA, GGL)
2. WHEN user clicks the "Send 3 prompts to email" button THEN system SHALL prompt the user to enter their email address
3. IF user has not been authenticated before THEN system SHALL require email verification process
4. IF user has been previously authenticated THEN system SHALL proceed directly to prompt optimization and email delivery

### Requirement 2

**User Story:** As a user, I want to authenticate my email address securely so that I can receive optimized prompts without unauthorized access to my email.

#### Acceptance Criteria

1. WHEN user clicks "Send 3 prompts to email" button THEN system SHALL ask the user for their email address and **normalize/canonicalize** it for storage and uniqueness checks.
2. WHEN user provides an email address THEN system SHALL validate the email format using basic regex validation.
3. IF email format is invalid THEN system SHALL display an error message and request a valid email address.
4. WHEN valid email is provided THEN system SHALL generate a random **6 digit numeric OTP**, hash it (Argon2id recommended, bcrypt acceptable), and store the **hash in Redis only** under the user’s telegram_id along with the normalized email, a 5-minute expiry and an attempts counter (starting at 0). **No OTPs are persisted in the database.**
5. WHEN OTP is sent THEN system SHALL apply Redis-backed rate limits:
   - maximum **3 OTP sends per normalized email per hour**,
   - maximum **5 OTP sends per telegram_id per hour**,
   - minimum **60 seconds spacing** between OTP sends per telegram_id.
6. WHEN user submits the OTP THEN system SHALL compare against the stored hash, failing after **more than 3** attempts or after expiry; on success the Redis entry SHALL be deleted.
7. WHEN OTP verification succeeds THEN system SHALL mark user as authenticated and remember across restarts (see Requirement 6).

### Requirement 3

**User Story:** As a user, I want the system to remember my email authentication, so that I don't have to verify my email every time I use the email delivery feature.

#### Acceptance Criteria

1. WHEN OTP verification succeeds for the **first** time THEN system SHALL set `is_authenticated=true` and `email_verified_at` for the user.
2. WHEN OTP verification succeeds **any time** THEN system SHALL set `last_authenticated_at` to the current timestamp.
3. WHEN system restarts THEN user’s authenticated state SHALL remain based on persisted DB fields.

### Requirement 4

**User Story:** As a user, I want my original prompt to be sent directly to optimization methods without follow-up questions, so that I can quickly receive optimized versions without additional refinement steps.

#### Acceptance Criteria

1. WHEN user completes email verification and authentication THEN system SHALL skip the follow-up questions system and proceed directly to prompt optimization
2. WHEN system begins optimization THEN system SHALL use the original user prompt as input for all three optimization methods (CRAFT, LYRA, GGL)
3. WHEN sending prompts to LLM for optimization THEN system SHALL take the current system prompt for each method and append the following message exactly: "### ВАЖНО\nНи в коем случае не задавай ни одного уточняющего вопроса. Твоя задача улучшить промпт пользователя по имеющимся данным. Твой ответ должен содержать только улучшенный промпт и ничего больше"
4. WHEN optimization methods are executed THEN each method SHALL receive the modified system prompt with the appended instruction
5. WHEN optimization is complete THEN system SHALL proceed directly to email delivery with the three optimized results
6. WHEN system processes the original prompt THEN system SHALL NOT initiate any follow-up questions or prompt refinement processes

### Requirement 5

**User Story:** As a user, I want to receive optimized prompts from all three methods via email, so that I can compare different optimization approaches and choose the best one for my needs.

#### Acceptance Criteria

1. WHEN email sending succeeds THEN system SHALL notify success in chat.
2. WHEN email sending fails THEN system SHALL post only an error message in chat and SHALL NOT share any optimized prompts.
3. WHEN email contains code blocks or technical content THEN email SHALL preserve formatting using appropriate HTML tags (e.g., `<pre><code>`).
4. WHEN email is sent THEN email SHALL include the original prompt for user reference, as well as all three optimized prompts (CRAFT, LYRA, GGL).
5. WHEN email is composed THEN email SHALL NOT include any follow-up improved prompt since no follow-up questions are asked.

### Requirement 6

**User Story:** As a system administrator, I want user authentication data to be stored securely and persistently, so that the system can maintain user sessions across bot restarts, support fast lookups and provide reliable service.

#### Acceptance Criteria

1. WHEN user is authenticated THEN system SHALL update users table fields: `is_authenticated`, `email_verified_at` (first success), and `last_authenticated_at` (every success).
2. The database SHALL enforce **UNIQUE** normalized `email` and **UNIQUE** `telegram_id`.
3. The users table SHALL track `created_at` and `updated_at` timestamps.
4. WHEN system initializes THEN system SHALL support both SQLite (development) and PostgreSQL (production) databases using SQLAlchemy 2.0 ORM.
5. WHEN database schema changes THEN system SHALL use Alembic migrations for schema evolution with rollback capability.
6. The database schema SHALL include:
   - **users table**: `id`, `telegram_id` (unique), `email` (unique, normalized), `email_original`, `is_authenticated`, `email_verified_at`, `last_authenticated_at`, `created_at`, `updated_at`
   - **auth_events table**: `id`, `telegram_id`, `email`, `event_type`, `success`, `reason`, `created_at`
7. WHEN database operations are performed THEN system SHALL NEVER use raw SQL queries, only ORM operations.

### Requirement 7

**User Story:** As a user, I want to receive properly formatted emails with clear subject lines and professional presentation, so that I can easily identify and use the optimized prompts.

#### Acceptance Criteria

1. WHEN system sends optimization email THEN email SHALL have a clear subject line indicating it contains optimized prompts
2. WHEN email is composed THEN email SHALL include the original user prompt at the top for reference
3. WHEN email contains optimized prompts THEN each method's result SHALL be clearly labeled with method name (CRAFT, LYRA, GGL)
4. WHEN email is formatted THEN email SHALL use proper HTML formatting for readability
5. WHEN email is sent THEN email SHALL include a professional signature identifying the Prompt Engineering Bot
6. WHEN email contains code blocks or technical content THEN email SHALL preserve formatting using appropriate HTML tags
7. WHEN email is sent THEN email SHALL include only the original prompt for user reference (no follow-up improved prompt)

### Requirement 8

**User Story:** As a user, I want to receive messages in my preferred language (Russian or English), so that I can understand all authentication prompts and email content clearly.

#### Acceptance Criteria

1. WHEN system displays authentication messages THEN system SHALL use the global LANGUAGE setting from configuration to show messages in Russian or English.
2. WHEN system sends OTP email THEN email subject and body SHALL be translated according to the global language setting.
3. WHEN system displays error messages during authentication THEN messages SHALL be available in both Russian and English.
4. WHEN system sends email with optimized prompts THEN email content SHALL be formatted according to the global language setting.
5. WHEN adding new messages for email authentication feature THEN email templates SHALL be created in separate `email_templates.py` file using the same `_(ru, en)` translation pattern.
6. WHEN system configuration changes THEN language setting SHALL be moved to environment variable (LANGUAGE) for easier deployment configuration.

### Requirement 9

**User Story:** As an operator, I want an audit trail for authentication and email delivery to analyze abuse and debug issues.

#### Acceptance Criteria

1. WHEN an OTP is sent, verified, failed, expired, or rate-limited THEN system SHALL record an event with: `telegram_id`, normalized `email`, `event_type`, `success`, optional `reason`, and timestamp.
2. WHEN an email send succeeds or fails THEN system SHALL record `EMAIL_SEND_OK` / `EMAIL_SEND_FAIL` events (include provider error info where available).
3. System MAY purge events older than a configurable retention (default 90 days).
