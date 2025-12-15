# Requirements Document

## Introduction

This feature modifies the user lifecycle and extends the Users table to track user activity timestamps. Currently, users are only created in the database when they verify their email. This feature changes the behavior so that users are created on their first interaction with the bot (before email verification), and their record is updated when they later provide and verify their email. Additionally, the feature adds fields to track first and last interaction timestamps, enabling the system to distinguish between first-time users and returning users.

## Glossary

- **User**: A Telegram user who interacts with the bot, represented by a record in the `users` database table
- **First Interaction**: The initial point in time when a user sends their first message or command to the bot
- **Last Interaction**: The most recent point in time when a user sent a message or command to the bot
- **First-Time User**: A user whose `first_interaction_at` timestamp equals their `last_interaction_at` timestamp (only one interaction recorded)
- **Returning User**: A user whose `last_interaction_at` timestamp is later than their `first_interaction_at` timestamp
- **Unauthenticated User**: A user record that exists in the database but has not yet verified their email (`is_authenticated` = false, `email` may be null)
- **Authenticated User**: A user record with a verified email address (`is_authenticated` = true)
- **Bot Handler**: The component (`telegram_bot/core/bot_handler.py`) that processes incoming Telegram messages and commands
- **AuthService**: The authentication service (`telegram_bot/auth/auth_service.py`) that handles user creation and email verification
- **extract_user_profile**: Existing utility function (`telegram_bot/auth/user_profile_utils.py`) that extracts Telegram profile data from `effective_user`
- **should_update_user_profile**: Existing utility function that determines if profile data needs updating

## Requirements

### Requirement 1

**User Story:** As a system administrator, I want users to be created in the database on their first bot interaction, so that I can track all users regardless of their authentication status.

#### Acceptance Criteria

1. WHEN a user interacts with the bot for the first time THEN the System SHALL create a new user record with the `telegram_id` and profile data extracted using the existing `extract_user_profile` function
2. WHEN creating a new user record before email verification THEN the System SHALL set `email` to null and `is_authenticated` to false
3. WHEN a user already exists in the database THEN the System SHALL retrieve the existing record instead of creating a duplicate
4. WHEN creating or retrieving a user THEN the System SHALL leverage the existing user creation pattern from `AuthService._persist_authentication_state` method

### Requirement 2

**User Story:** As a system administrator, I want to track when users first interact with the bot, so that I can identify new users and analyze user acquisition patterns.

#### Acceptance Criteria

1. WHEN a new user record is created in the database THEN the System SHALL set the `first_interaction_at` field to the current UTC timestamp
2. WHEN an existing user interacts with the bot THEN the System SHALL preserve the original `first_interaction_at` value without modification
3. WHEN querying user data THEN the System SHALL return the `first_interaction_at` field as a timezone-aware datetime value

### Requirement 3

**User Story:** As a system administrator, I want to track when users last interacted with the bot, so that I can monitor user engagement and identify inactive users.

#### Acceptance Criteria

1. WHEN a new user record is created in the database THEN the System SHALL set the `last_interaction_at` field to the current UTC timestamp
2. WHEN an existing user interacts with the bot THEN the System SHALL update the `last_interaction_at` field to the current UTC timestamp
3. WHEN querying user data THEN the System SHALL return the `last_interaction_at` field as a timezone-aware datetime value

### Requirement 4

**User Story:** As a developer, I want to distinguish first-time users from returning users, so that I can implement personalized welcome messages or onboarding flows.

#### Acceptance Criteria

1. WHEN a user has only one recorded interaction THEN the System SHALL identify that user as a first-time user by having equal `first_interaction_at` and `last_interaction_at` values
2. WHEN a user has multiple recorded interactions THEN the System SHALL identify that user as a returning user by having `last_interaction_at` later than `first_interaction_at`
3. WHEN the bot handler processes a message THEN the System SHALL provide a method to check if the current user is a first-time user

### Requirement 5

**User Story:** As a developer, I want the email verification process to update existing user records, so that user activity history is preserved when users authenticate.

#### Acceptance Criteria

1. WHEN a user verifies their email THEN the System SHALL update the existing user record with the verified email address using the existing `AuthService._persist_authentication_state` method
2. WHEN a user verifies their email THEN the System SHALL set `is_authenticated` to true and update `email_verified_at`
3. WHEN updating a user record during email verification THEN the System SHALL preserve the original `first_interaction_at` and `created_at` values
4. WHEN updating profile data during verification THEN the System SHALL use the existing `should_update_user_profile` function to determine if updates are needed

### Requirement 6

**User Story:** As a database administrator, I want the activity tracking fields to be properly indexed, so that queries filtering by activity timestamps perform efficiently.

#### Acceptance Criteria

1. WHEN the database migration runs THEN the System SHALL create an index on the `first_interaction_at` column
2. WHEN the database migration runs THEN the System SHALL create an index on the `last_interaction_at` column
3. WHEN the migration is rolled back THEN the System SHALL remove the activity tracking columns and their indexes

### Requirement 7

**User Story:** As a developer, I want activity timestamps to be updated automatically during user interactions, so that tracking happens transparently without manual intervention.

#### Acceptance Criteria

1. WHEN the bot handler processes any user message or command THEN the System SHALL call a user tracking service to update the `last_interaction_at` timestamp
2. WHEN updating activity timestamps THEN the System SHALL use UTC timezone for consistency with existing timestamp handling in `AuthService`
3. WHEN a database error occurs during activity update THEN the System SHALL log the error and continue processing the user request without interruption
4. WHEN updating user profile data during interactions THEN the System SHALL use the existing `should_update_user_profile` function to avoid unnecessary database writes

### Requirement 8

**User Story:** As a database administrator, I want the email field to allow null values for unauthenticated users, so that users can be tracked before they provide their email.

#### Acceptance Criteria

1. WHEN the database schema is updated THEN the System SHALL modify the `email` column to allow null values
2. WHEN the database schema is updated THEN the System SHALL remove or modify the unique constraint on `email` to allow multiple null values
3. WHEN migrating existing data THEN the System SHALL preserve all existing user records with their current email values
