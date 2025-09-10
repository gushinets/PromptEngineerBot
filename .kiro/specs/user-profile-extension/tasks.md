# Implementation Plan

- [x] 1. Create database migration for user profile fields

  - Create new Alembic migration file to add first_name, last_name, is_bot, is_premium, and language_code columns to users table
  - Add appropriate indexes for performance: ix_users_language_code, ix_users_is_premium, ix_users_bot_premium
  - Ensure all new columns are nullable or have appropriate defaults for backward compatibility
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 5.1, 5.2, 5.3_

- [x] 2. Update User model with new profile fields

  - Add first_name, last_name, is_bot, is_premium, and language_code as mapped columns to User class
  - Update __repr__ method to include first_name in the representation
  - Ensure proper type annotations and nullable/default configurations
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_

- [x] 3. Implement profile data extraction utility

  - Create extract_user_profile function to safely extract profile data from update.effective_user
  - Handle cases where effective_user fields are None or missing using getattr with defaults
  - Return structured dictionary with all profile fields
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 4.3_

- [x] 4. Create profile comparison utility for efficient updates

  - Implement function to compare current database profile with incoming Telegram profile data
  - Determine if meaningful changes exist (name changes, premium status changes) that warrant database update
  - Return boolean indicating whether update is necessary
  - _Requirements: 4.2, 4.6_

- [x] 5. Enhance AuthService to capture profile data during user creation

  - Modify _persist_authentication_state method to extract and store profile data for new users
  - Ensure profile data is populated during User object creation
  - Handle profile extraction errors gracefully without breaking authentication flow
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 4.1, 4.5, 4.6_
-

- [x] 6. Add selective profile update logic for existing users

  - Implement profile update logic in _persist_authentication_state for existing users
  - Only update profile data when meaningful changes are detected using comparison utility
  - Update updated_at timestamp when profile changes are made
  - _Requirements: 4.2, 4.3, 4.4, 4.5_

- [x] 7. Write unit tests for profile extraction functionality

  - Test extract_user_profile with complete Telegram user data
  - Test extraction with partial/missing data and None values
  - Test extraction with various user types (bots, premium users, different languages)
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 4.3_

- [x] 8. Write unit tests for User model extensions

  - Test User model creation with new profile fields
  - Test model validation and default values
  - Test updated __repr__ method with profile data
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_

- [x] 9. Write unit tests for AuthService profile integration

  - Test user creation with profile data extraction and storage
  - Test profile update logic for existing users
  - Test error handling when profile extraction fails
  - _Requirements: 4.1, 4.2, 4.5, 4.6_

- [x] 10. Write integration tests for database migration

  - Test migration up operation adds all columns and indexes correctly
  - Test migration down operation removes columns and indexes cleanly
  - Test data preservation during migration process
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 5.1, 5.2, 5.3_

- [x] 11. Write integration tests for complete profile flow

  - Test end-to-end user registration with profile data capture
  - Test profile updates during subsequent user interactions
  - Test system behavior with various Telegram user types and edge cases
  - _Requirements: 4.1, 4.2, 4.4, 4.6_

- [x] 12. Update documentation for new user profile fields





  - Update database.py module docstrings to document new User model fields
  - Add comments explaining the purpose and source of each new profile field
  - Update any relevant README or documentation files that describe the User model
  - Document the profile update strategy and when updates occur
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 4.2_