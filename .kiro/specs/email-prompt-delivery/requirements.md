# Requirements Document

## Introduction

This feature extends the existing email-based authentication and prompt delivery functionality in the Telegram bot. The existing "Send 3 prompts to email" button (which appears at method selection and sends all three optimization results) will remain unchanged. This feature adds a new "Отправить промпт на e-mail" button that appears in two specific cases: (1) after successfully completing the follow-up optimization process, or (2) after successfully completing optimization by one method (CRAFT, LYRA, or GGL) and declining the follow-up optimization process. In both cases, clicking the new button triggers the existing email flow with registration and authentication, then sends the current optimization result to the user's email.

## Requirements

### Requirement 1

**User Story:** As a user, I want to see a new "Отправить промпт на e-mail" button after completing specific optimization scenarios, so that I can receive the current optimization result via email while keeping the existing email functionality unchanged.

#### Acceptance Criteria

1. WHEN user successfully completes follow-up optimization process THEN system SHALL display new "Отправить промпт на e-mail" button alongside the final optimized result
2. WHEN user successfully completes optimization by one method (CRAFT, LYRA, or GGL) AND declines follow-up optimization THEN system SHALL display new "Отправить промпт на e-mail" button alongside that method's result
3. WHEN user clicks the new "Отправить промпт на e-mail" button THEN system SHALL trigger the existing email authentication flow
4. WHEN existing "Send 3 prompts to email" button functionality is used THEN system SHALL continue to work exactly as before (unchanged)
5. IF user has not been authenticated before THEN system SHALL require email verification process using existing authentication system
6. IF user has been previously authenticated THEN system SHALL proceed directly to email delivery of the current optimization result

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

**User Story:** As a user, I want to receive the current optimization result via email, so that I can access it outside of the chat interface.

#### Acceptance Criteria

1. WHEN user clicks "Отправить промпт на e-mail" after follow-up optimization completion THEN system SHALL send the final follow-up optimized result via email
2. WHEN user clicks "Отправить промпт на e-mail" after declining follow-up optimization THEN system SHALL send the single method result (CRAFT, LYRA, or GGL) via email
3. WHEN system sends email THEN email SHALL contain the original user prompt for reference
4. WHEN system sends email after follow-up completion THEN email SHALL contain the final optimized prompt from follow-up process
5. WHEN system sends email after declining follow-up THEN email SHALL contain the result from the selected optimization method (CRAFT, LYRA, or GGL)
6. WHEN email is sent THEN system SHALL trigger the existing email flow with registration and authentication process
7. WHEN email delivery is complete THEN system SHALL notify user of successful delivery in chat

### Requirement 5

**User Story:** As a user, I want to receive the current optimization result via email with proper formatting, so that I can easily read and use the optimized content.

#### Acceptance Criteria

1. WHEN email sending succeeds THEN system SHALL notify success in chat
2. WHEN email sending fails THEN system SHALL post only an error message in chat and SHALL NOT share any optimized prompts
3. WHEN email contains code blocks or technical content THEN email SHALL preserve formatting using appropriate HTML tags (e.g., `<pre><code>`)
4. WHEN email is sent after follow-up completion THEN email SHALL include the original prompt and the final follow-up optimized result
5. WHEN email is sent after declining follow-up THEN email SHALL include the original prompt and the single method result (CRAFT, LYRA, or GGL)
6. WHEN email is composed THEN email SHALL include clear labeling of which optimization result is being sent

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

**User Story:** As a user, I want the existing "Send 3 prompts to email" functionality to remain completely unchanged, so that current workflows are not disrupted.

#### Acceptance Criteria

1. WHEN user uses existing "Send 3 prompts to email" button THEN system SHALL continue to work exactly as currently implemented
2. WHEN existing email flow is triggered THEN system SHALL send all three optimization results (CRAFT, LYRA, GGL) as before
3. WHEN existing button is displayed THEN system SHALL show it in the same location and with same behavior as current implementation
4. WHEN new "Отправить промпт на e-mail" functionality is added THEN existing functionality SHALL NOT be modified or affected

### Requirement 10

**User Story:** As an operator, I want an audit trail for authentication and email delivery to analyze abuse and debug issues.

#### Acceptance Criteria

1. WHEN an OTP is sent, verified, failed, expired, or rate-limited THEN system SHALL record an event with: `telegram_id`, normalized `email`, `event_type`, `success`, optional `reason`, and timestamp.
2. WHEN an email send succeeds or fails THEN system SHALL record `EMAIL_SEND_OK` / `EMAIL_SEND_FAIL` events (include provider error info where available).
3. System MAY purge events older than a configurable retention (default 90 days).
