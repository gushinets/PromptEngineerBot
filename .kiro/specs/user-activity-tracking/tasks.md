# Implementation Plan

- [x] 1. Update User model and create database migration





  - [x] 1.1 Add activity tracking fields to User model


    - Add `first_interaction_at: Mapped[datetime]` field with timezone-aware DateTime
    - Add `last_interaction_at: Mapped[datetime]` field with timezone-aware DateTime
    - Modify `email: Mapped[str | None]` to allow null values
    - Add index definitions for the new timestamp fields
    - _Requirements: 2.1, 2.3, 3.1, 3.3, 8.1_


  - [x] 1.2 Create Alembic migration for activity tracking

    - Create `alembic/versions/003_add_activity_tracking_fields.py`
    - Add `first_interaction_at` column (nullable initially)
    - Add `last_interaction_at` column (nullable initially)
    - Backfill existing records with `created_at` value
    - Create indexes `ix_users_first_interaction_at` and `ix_users_last_interaction_at`
    - Modify `email` column to allow null values
    - Handle unique constraint on `email` for null values
    - Implement complete `downgrade()` function
    - _Requirements: 6.1, 6.2, 6.3, 8.1, 8.2, 8.3_


  - [x] 1.3 Write property test for timestamp fields

    - **Property 8: Timestamps are timezone-aware UTC**
    - **Validates: Requirements 2.3, 3.3, 7.2**

- [x] 2. Implement UserTrackingService





  - [x] 2.1 Create UserTrackingService class





    - Create `telegram_bot/services/user_tracking.py`
    - Implement `__init__` with database session management
    - Use existing `extract_user_profile` function for profile extraction
    - Use existing `should_update_user_profile` function for update detection
    - _Requirements: 1.1, 1.4_

  - [x] 2.2 Implement get_or_create_user method





    - Query for existing user by `telegram_id`
    - Create new user with `email=null`, `is_authenticated=false` if not found
    - Set `first_interaction_at` and `last_interaction_at` to current UTC time for new users
    - Extract and store profile data using `extract_user_profile`
    - Return tuple of (User, was_created)
    - _Requirements: 1.1, 1.2, 1.3, 2.1, 3.1_


  - [x] 2.3 Write property test for new user creation




    - **Property 1: New user creation sets both timestamps equally**
    - **Validates: Requirements 2.1, 3.1, 4.1**


  - [x] 2.4 Write property test for no duplicate users




    - **Property 5: No duplicate users created**
    - **Validates: Requirements 1.3**

  - [x] 2.5 Write property test for unauthenticated user state





    - **Property 6: Unauthenticated users have null email**
    - **Validates: Requirements 1.2, 8.1**


  - [x] 2.6 Implement track_user_interaction method




    - Call `get_or_create_user` to get or create user
    - Update `last_interaction_at` to current UTC time for existing users
    - Check if profile update needed using `should_update_user_profile`
    - Update profile data if changes detected
    - Return tuple of (User, is_first_time_user)
    - Implement error handling with logging and graceful degradation
    - _Requirements: 3.2, 7.1, 7.2, 7.3, 7.4_

  - [x] 2.7 Write property test for first interaction timestamp immutability





    - **Property 2: First interaction timestamp is immutable**
    - **Validates: Requirements 2.2, 5.3**


  - [x] 2.8 Write property test for last interaction timestamp updates




    - **Property 3: Last interaction timestamp updates on each interaction**
    - **Validates: Requirements 3.2, 7.1**

  - [x] 2.9 Implement is_first_time_user method





    - Compare `first_interaction_at` with `last_interaction_at`
    - Return `True` if equal, `False` otherwise
    - _Requirements: 4.1, 4.2, 4.3_


  - [x] 2.10 Write property test for first-time user identification




    - **Property 4: First-time user identification**
    - **Validates: Requirements 4.1, 4.2, 4.3**


  - [x] 2.11 Add global service initialization functions




    - Implement `init_user_tracking_service()` function
    - Implement `get_user_tracking_service()` function
    - Follow existing pattern from `auth_service.py`
    - _Requirements: 1.4_

- [x] 3. Checkpoint - Ensure all tests pass





  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Update AuthService for email verification flow


  - [x] 4.1 Modify _persist_authentication_state to handle existing users





    - Update logic to find user by `telegram_id` first (already does this)
    - Ensure `first_interaction_at` is preserved when updating existing user
    - Ensure `created_at` is preserved when updating existing user
    - Handle case where user was created on first interaction (email=null)
    - _Requirements: 5.1, 5.2, 5.3, 5.4_

  - [x] 4.2 Write property test for email verification preserving history




    - **Property 7: Email verification preserves activity history**
    - **Validates: Requirements 5.3**

- [x] 5. Integrate UserTrackingService with BotHandler


  - [x] 5.1 Add UserTrackingService to BotHandler





    - Import and initialize `UserTrackingService` in `BotHandler.__init__`
    - Add `user_tracking_service` attribute
    - _Requirements: 7.1_

  - [x] 5.2 Call track_user_interaction in handle_message









    - Add call to `track_user_interaction()` early in `handle_message()`
    - Pass `update.effective_user.id` and `update.effective_user`
    - Handle None return gracefully (database error case)
    - _Requirements: 7.1, 7.3_


  - [x] 5.3 Call track_user_interaction in handle_start







    - Add call to `track_user_interaction()` in `handle_start()`
    - Ensure first interaction is tracked for /start command
    - _Requirements: 7.1_

- [x] 6. Checkpoint - Ensure all tests pass





  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Write property test for multiple null emails





  - **Property 9: Multiple null emails allowed**
  - **Validates: Requirements 8.2**


- [x] 8. Final Checkpoint - Ensure all tests pass




  - Ensure all tests pass, ask the user if questions arise.
