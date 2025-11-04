# Implementation Plan

- [x] 1. Preparation and baseline

  - Document current test results and coverage
  - Create backup branch
  - Review and get approval for file cleanup
  - _Requirements: 7.1, 7.2, 7.3_

- [x] 2. Create new package structure






  - [x] 2.1 Create telegram_bot/ root package directory

    - Create main package directory
    - Create __init__.py with package metadata
    - _Requirements: 1.1_


  - [x] 2.2 Create core/ subdirectory structure

    - Create telegram_bot/core/ directory
    - Create __init__.py
    - _Requirements: 1.1_

  - [x] 2.3 Create services/ subdirectory structure


    - Create telegram_bot/services/ directory
    - Create telegram_bot/services/llm/ directory
    - Create __init__.py files
    - _Requirements: 1.1_


  - [x] 2.4 Create auth/, data/, utils/, flows/ subdirectories

    - Create all remaining package directories
    - Create __init__.py files in each
    - _Requirements: 1.1_

  - [x] 2.5 Create prompts/ directory


    - Create telegram_bot/prompts/ directory
    - _Requirements: 1.1_

- [x] 3. Move and update core source files





  - [x] 3.1 Move core business logic files


    - Move bot_handler.py to telegram_bot/core/
    - Move conversation_manager.py to telegram_bot/core/
    - Move state_manager.py to telegram_bot/core/
    - Update imports in moved files from `src.` to `telegram_bot.`
    - _Requirements: 1.1, 2.1, 2.2_

  - [x] 3.2 Move LLM service files


    - Move llm_client_base.py to telegram_bot/services/llm/base.py
    - Move llm_factory.py to telegram_bot/services/llm/factory.py
    - Move openai_client.py to telegram_bot/services/llm/
    - Move openrouter_client.py to telegram_bot/services/llm/
    - Update imports in moved files
    - _Requirements: 1.1, 2.1, 2.2_

  - [x] 3.3 Move other service files


    - Move email_service.py to telegram_bot/services/
    - Move gsheets_logging.py to telegram_bot/services/
    - Move redis_client.py to telegram_bot/services/
    - Update imports in moved files
    - _Requirements: 1.1, 2.1, 2.2_

  - [x] 3.4 Move authentication files


    - Move auth_service.py to telegram_bot/auth/
    - Move user_profile_utils.py to telegram_bot/auth/
    - Update imports in moved files
    - _Requirements: 1.1, 2.1, 2.2_

  - [x] 3.5 Move data layer files


    - Move database.py to telegram_bot/data/
    - Update imports in moved files
    - _Requirements: 1.1, 2.1, 2.2_

  - [x] 3.6 Move utility files


    - Move config.py to telegram_bot/utils/
    - Move messages.py to telegram_bot/utils/
    - Move prompt_loader.py to telegram_bot/utils/
    - Move email_templates.py to telegram_bot/utils/
    - Move logging_utils.py to telegram_bot/utils/
    - Move metrics.py to telegram_bot/utils/
    - Move health_checks.py to telegram_bot/utils/
    - Move audit_service.py to telegram_bot/utils/
    - Move graceful_degradation.py to telegram_bot/utils/
    - Update imports in moved files
    - _Requirements: 1.1, 2.1, 2.2_

  - [x] 3.7 Move flow files


    - Move email_flow.py to telegram_bot/flows/
    - Move background_tasks.py to telegram_bot/flows/
    - Update imports in moved files
    - _Requirements: 1.1, 2.1, 2.2_

  - [x] 3.8 Move main.py and dependencies.py


    - Move main.py to telegram_bot/
    - Move dependencies.py to telegram_bot/
    - Update imports in moved files
    - _Requirements: 1.1, 2.1, 2.2_

  - [x] 3.9 Move prompt template files


    - Move all .txt files from src/prompts/ to telegram_bot/prompts/
    - _Requirements: 1.1_

- [x] 4. Update package __init__.py files






  - [x] 4.1 Update telegram_bot/__init__.py

    - Add package version and metadata
    - Export main public APIs
    - _Requirements: 2.2_


  - [x] 4.2 Update subpackage __init__.py files

    - Update core/__init__.py with exports
    - Update services/__init__.py with exports
    - Update services/llm/__init__.py with exports
    - Update auth/__init__.py with exports
    - Update data/__init__.py with exports
    - Update utils/__init__.py with exports
    - Update flows/__init__.py with exports
    - _Requirements: 2.2_

- [x] 5. Update entry point and root-level imports




  - [x] 5.1 Update run_bot.py


    - Change imports from `src.` to `telegram_bot.`
    - Test that entry point works
    - _Requirements: 2.1, 2.2, 2.3_

- [x] 6. Reorganize test files






  - [x] 6.1 Move unit tests

    - Move test_config.py to tests/unit/
    - Move test_conversation_manager.py to tests/unit/
    - Move test_state_manager.py to tests/unit/
    - Move test_messages.py to tests/unit/
    - Move test_prompt_loader.py to tests/unit/
    - Move test_llm_factory.py to tests/unit/
    - Move test_llm_client_base.py to tests/unit/
    - Move test_logging_utils.py to tests/unit/
    - Move test_metrics.py to tests/unit/
    - Move test_graceful_degradation.py to tests/unit/
    - Move test_user_profile_utils.py to tests/unit/
    - Move test_utils.py to tests/unit/
    - Update imports from `src.` to `telegram_bot.`
    - _Requirements: 1.2, 2.1, 2.2, 3.2_


  - [x] 6.2 Move integration tests

    - Move test_bot_handler.py to tests/integration/
    - Move test_bot_handler_integration.py to tests/integration/
    - Move test_bot_handler_health_integration.py to tests/integration/
    - Move test_auth_service.py to tests/integration/
    - Move test_auth_service_profile_integration.py to tests/integration/
    - Move test_database.py to tests/integration/
    - Move test_email_service.py to tests/integration/
    - Move test_email_service_single_result.py to tests/integration/
    - Move test_email_flow_integration.py to tests/integration/
    - Move test_email_flow_timeout.py to tests/integration/
    - Move test_redis_client.py to tests/integration/
    - Move test_health_checks.py to tests/integration/
    - Move test_audit_service.py to tests/integration/
    - Move test_background_tasks.py to tests/integration/
    - Move test_llm_clients.py to tests/integration/
    - Move test_followup_integration.py to tests/integration/
    - Move test_followup_error_handling.py to tests/integration/
    - Move test_profile_flow_integration.py to tests/integration/
    - Move test_post_optimization_integration.py to tests/integration/
    - Move test_post_optimization_email.py to tests/integration/
    - Move test_migration_integration.py to tests/integration/
    - Move test_token_accumulation_fix.py to tests/integration/
    - Update imports from `src.` to `telegram_bot.`
    - _Requirements: 1.2, 2.1, 2.2, 3.2_


  - [x] 6.3 Move e2e tests

    - Move test_bot.py to tests/e2e/
    - Move test_performance.py to tests/e2e/
    - Move test_security.py to tests/e2e/
    - Move test_task8_simple.py to tests/e2e/
    - Update imports from `src.` to `telegram_bot.`
    - _Requirements: 1.2, 2.1, 2.2, 3.2_


  - [x] 6.4 Move standalone test files from root

    - Move test_audit_standalone.py to tests/integration/
    - Move test_health_simple.py to tests/integration/
    - Move test_logging_simple.py to tests/unit/
    - Move test_metrics_standalone.py to tests/integration/
    - Move test_simple_auth.py to tests/integration/
    - Move test_token_flow.py to tests/integration/
    - Update imports from `src.` to `telegram_bot.`
    - _Requirements: 1.2, 2.1, 2.2, 3.2, 7.1, 7.2, 7.3_


  - [x] 6.5 Update conftest.py

    - Update imports from `src.` to `telegram_bot.`
    - Ensure fixtures work with new structure
    - _Requirements: 2.1, 2.2, 3.2_

- [x] 7. Move documentation files




  - [x] 7.1 Create docs/ subdirectory structure

    - Create docs/guidelines/ directory
    - Create docs/architecture/ directory
    - Create docs/deployment/ directory
    - Create docs/guides/ directory
    - Create docs/development/ directory
    - _Requirements: 1.3, 5.1, 5.4_


  - [x] 7.2 Move guidelines and architecture documentation

    - Move AGENTS.MD to docs/guidelines/AGENTS.md
    - Move docs/USER_PROFILE_SYSTEM.md to docs/architecture/
    - _Requirements: 5.1, 5.3_



  - [x] 7.3 Move deployment documentation

    - Move DEPLOYMENT.md to docs/deployment/


    - _Requirements: 5.1, 5.3_

  - [x] 7.4 Move user guides

    - Move E2E_USER_PATHS_DOCUMENTATION.md to docs/guides/

    - _Requirements: 5.1, 5.3_

  - [x] 7.5 Move development notes

    - Move ASYNC_SYNC_FIX_SUMMARY.md to docs/development/
    - Move FINAL_CODE_CLEANUP_SUMMARY.md to docs/development/
    - Move FINAL_INTEGRATION_VALIDATION_REPORT.md to docs/development/
    - Move FINAL_VALIDATION_REPORT.md to docs/development/
    - Move FIX_SUMMARY.md to docs/development/
    - Move FOLLOWUP_DECLINE_FIX_SUMMARY.md to docs/development/
    - Move POST_OPTIMIZATION_EMAIL_FIX_SUMMARY.md to docs/development/
    - Move VALIDATE_POST_OPTIMIZATION_FIX.md to docs/development/
    - _Requirements: 5.1, 5.3_


  - [x] 7.6 Create documentation index

    - Create docs/INDEX.md with links to all documentation
    - Include links to .kiro/specs/ features
    - Organize by category (architecture, deployment, features, guides)
    - _Requirements: 5.5, 5.6, 5.7_


  - [x] 7.7 Update README.md


    - Update architecture section with new structure
    - Update file paths in examples
    - Add link to docs/INDEX.md
    - _Requirements: 5.2, 5.3, 8.1, 8.2_

- [x] 8. Move utility scripts





  - [x] 8.1 Move scripts to scripts/ directory


    - Move validate_system.py to scripts/
    - Move mock_redis.py to scripts/
    - Move test_imports.py to scripts/
    - Update imports from `src.` to `telegram_bot.`
    - _Requirements: 6.1, 6.2, 6.4_



  - [x] 8.2 Move tools/ to scripts/tools/


    - Move tools/diagnose_gsheets.py to scripts/tools/
    - Move tools/repair_gsheets.py to scripts/tools/
    - Move tools/README.md to scripts/tools/
    - Update imports from `src.` to `telegram_bot.`
    - _Requirements: 6.1, 6.2, 6.4_

- [x] 9. Update configuration files





  - [x] 9.1 Update pyproject.toml



    - Change package name from "src" to "telegram_bot"
    - Update tool.coverage.run source paths
    - Update project.scripts entry point
    - _Requirements: 4.1, 4.2, 4.3_

  - [x] 9.2 Update pytest.ini


    - Update testpaths to reflect new test structure
    - Ensure test discovery works for unit/integration/e2e
    - _Requirements: 3.3, 3.4_

  - [x] 9.3 Update .gitignore


    - Update paths for new structure
    - Ensure telegram_bot/__pycache__/ is ignored
    - _Requirements: 4.4_

  - [x] 9.4 Update .dockerignore


    - Update paths to exclude tests/, docs/, scripts/
    - Update to exclude .kiro/, .vscode/
    - _Requirements: 4.3, 4.4_

  - [x] 9.5 Update Dockerfile


    - Change COPY src ./src to COPY telegram_bot ./telegram_bot
    - Update any other path references
    - _Requirements: 4.1, 4.2_

  - [x] 9.6 Update docker-compose.yml


    - Update volume mounts if any reference src/
    - Update environment variables if needed
    - _Requirements: 4.2_

  - [x] 9.7 Update docker-compose.override.yml


    - Update volume mounts for development
    - Update any src/ references to telegram_bot/
    - _Requirements: 4.2_

  - [x] 9.8 Update .vscode/launch.json


    - Update module paths from src.main to telegram_bot.main
    - Update any other configuration references
    - _Requirements: 4.1, 4.2_

  - [x] 9.9 Update .vscode/settings.json


    - Update python.analysis paths if needed
    - Update any src/ references
    - _Requirements: 4.1, 4.2_

- [x] 10. Clean up old structure and temporary files




  - [x] 10.1 Review and remove temporary files (with user approval)


    - Identify files: bot.db, bot.log, htmlcov/, __pycache__/
    - Request user approval for each removal
    - Remove approved files
    - _Requirements: 7.1, 7.2, 7.3, 7.4_

  - [x] 10.2 Remove old src/ directory

    - Verify all files have been moved
    - Remove src/ directory
    - _Requirements: 1.1, 2.1, 2.2_


  - [x] 10.3 Remove old tools/ directory
    - Verify all files have been moved to scripts/tools/
    - Remove tools/ directory
    - _Requirements: 6.1, 6.2_


  - [x] 10.4 Clean up root directory

    - Verify no orphaned test files remain
    - Verify no orphaned documentation files remain
    - _Requirements: 7.5_

- [x] 11. Validation and testing






  - [x] 11.1 Run full test suite


    - Execute pytest with all tests
    - Verify all tests pass
    - Compare coverage with baseline
    - _Requirements: 3.1, 3.4, 3.5_

  - [x] 11.2 Test Docker build






    - Build Docker image
    - Verify build succeeds
    - _Requirements: 4.1, 4.5_





  - [x] 11.3 Test Docker container





    - Run container from built image
    - Verify bot starts successfully
    - Test basic bot functionality
    - _Requirements: 4.1, 4.5_


  - [x] 11.4 Verify entry points

    - Test run_bot.py execution
    - Test python -m telegram_bot.main execution
    - Verify all imports resolve
    - _Requirements: 2.3, 2.4, 2.5_


  - [x] 11.5 Verify script execution

    - Test scripts/validate_system.py
    - Test scripts/tools/diagnose_gsheets.py
    - Test scripts/tools/repair_gsheets.py
    - _Requirements: 6.3, 6.5_

- [x] 12. Documentation finalization






  - [x] 12.1 Review and update all documentation

    - Verify all links work
    - Verify all code examples are correct
    - Verify structure diagrams are accurate
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_


  - [x] 12.2 Create migration guide

    - Document changes for developers
    - Provide import migration examples
    - Document new structure benefits
    - _Requirements: 8.4_
