# Project Restructuring - Baseline Documentation

**Date:** November 3, 2025  
**Purpose:** Document current state before restructuring

## Test Results Summary

### Test Execution
- **Total Tests:** 734 tests collected
- **Passed:** 726 tests
- **Failed:** 7 tests
- **Skipped:** 1 test
- **Warnings:** 4 warnings
- **Execution Time:** 39.04 seconds

### Test Coverage
- **Overall Coverage:** 69%
- **Total Statements:** 4554
- **Missed Statements:** 1425

### Coverage by Module (Key Files)

| Module | Statements | Missed | Coverage |
|--------|-----------|--------|----------|
| src/audit_service.py | 136 | 12 | 91% |
| src/auth_service.py | 228 | 26 | 89% |
| src/background_tasks.py | 107 | 57 | 47% |
| src/bot_handler.py | 490 | 64 | 87% |
| src/config.py | 98 | 11 | 89% |
| src/conversation_manager.py | 75 | 1 | 99% |
| src/database.py | 125 | 8 | 94% |
| src/dependencies.py | 49 | 8 | 84% |
| src/email_flow.py | 629 | 451 | 28% |
| src/email_service.py | 409 | 232 | 43% |
| src/email_templates.py | 106 | 26 | 75% |
| src/graceful_degradation.py | 228 | 26 | 89% |
| src/gsheets_logging.py | 176 | 78 | 56% |
| src/health_checks.py | 201 | 5 | 98% |
| src/llm_client_base.py | 18 | 0 | 100% |
| src/llm_factory.py | 16 | 0 | 100% |
| src/logging_utils.py | 184 | 13 | 93% |
| src/main.py | 162 | 81 | 50% |
| src/messages.py | 147 | 0 | 100% |
| src/metrics.py | 202 | 2 | 99% |
| src/openai_client.py | 51 | 18 | 65% |
| src/openrouter_client.py | 46 | 11 | 76% |
| src/prompt_loader.py | 85 | 12 | 86% |
| src/redis_client.py | 205 | 40 | 80% |
| src/state_manager.py | 63 | 4 | 94% |
| src/user_profile_utils.py | 38 | 1 | 97% |

### Known Failing Tests

1. **tests/test_bot.py::TestTimeoutHandling::test_application_timeouts**
   - Error: RuntimeError: Redis write health check failed

2. **tests/test_followup_integration.py::TestFollowupIntegration::test_complete_followup_no_flow_to_reset**
   - Error: AssertionError (message content mismatch)

3. **tests/test_performance.py::TestDatabasePerformance::test_database_connection_pooling**
   - Error: AssertionError: Only 14/50 operations succeeded

4. **tests/test_post_optimization_email.py::TestPostOptimizationEmailFlow::test_get_current_optimization_result_single_method**
   - Error: assert None is not None

5. **tests/test_post_optimization_email.py::TestPostOptimizationFlowValidation::test_current_result_detection_accuracy**
   - Error: assert None is not None

6. **tests/test_post_optimization_email.py::TestPostOptimizationEmailTemplateIntegration::test_email_service_single_result_integration**
   - Error: TypeError: object MagicMock can't be used in 'await' expression

7. **tests/test_post_optimization_integration.py::TestPostOptimizationEmailTemplateValidation::test_email_service_integration_comprehensive**
   - Error: TypeError: object MagicMock can't be used in 'await' expression

## Test Organization

### Current Test Structure
```
tests/
├── conftest.py
├── fixtures/
├── e2e/
├── integration/
├── unit/
└── [Various test files at root level]
```

### Root-Level Test Files (To Be Moved)
- test_audit_service.py
- test_auth_service.py
- test_auth_service_profile_integration.py
- test_background_tasks.py
- test_bot.py
- test_bot_handler.py
- test_bot_handler_health_integration.py
- test_bot_handler_integration.py
- test_config.py
- test_conversation_manager.py
- test_database.py
- test_email_flow_integration.py
- test_email_flow_timeout.py
- test_email_service.py
- test_email_service_single_result.py
- test_followup_error_handling.py
- test_followup_integration.py
- test_graceful_degradation.py
- test_health_checks.py
- test_llm_clients.py
- test_llm_client_base.py
- test_llm_factory.py
- test_logging_utils.py
- test_messages.py
- test_metrics.py
- test_migration_integration.py
- test_performance.py
- test_post_optimization_email.py
- test_post_optimization_integration.py
- test_profile_flow_integration.py
- test_prompt_loader.py
- test_redis_client.py
- test_security.py
- test_state_manager.py
- test_task8_simple.py
- test_token_accumulation_fix.py
- test_user_profile_utils.py

### Standalone Test Files at Project Root (To Be Moved)
- test_audit_standalone.py
- test_health_simple.py
- test_imports.py
- test_logging_simple.py
- test_metrics_standalone.py
- test_simple_auth.py
- test_token_flow.py

## Current Project Structure

```
PromptEngineerBot/
├── src/                          # Source code (to be renamed to telegram_bot/)
│   ├── __init__.py
│   ├── audit_service.py
│   ├── auth_service.py
│   ├── background_tasks.py
│   ├── bot_handler.py
│   ├── config.py
│   ├── conversation_manager.py
│   ├── database.py
│   ├── dependencies.py
│   ├── email_flow.py
│   ├── email_service.py
│   ├── email_templates.py
│   ├── graceful_degradation.py
│   ├── gsheets_logging.py
│   ├── health_checks.py
│   ├── llm_client_base.py
│   ├── llm_factory.py
│   ├── logging_utils.py
│   ├── main.py
│   ├── messages.py
│   ├── metrics.py
│   ├── openai_client.py
│   ├── openrouter_client.py
│   ├── prompt_loader.py
│   ├── redis_client.py
│   ├── state_manager.py
│   ├── user_profile_utils.py
│   └── prompts/
│       ├── CRAFT_prompt.txt
│       ├── LYRA_prompt.txt
│       ├── GGL_prompt.txt
│       ├── followup_prompt.txt
│       ├── CRAFT_email_prompt.txt
│       ├── LYRA_email_prompt.txt
│       └── GGL_email_prompt.txt
├── tests/                        # Tests (mixed organization)
├── tools/                        # Utility scripts (to be moved to scripts/)
├── docs/                         # Some documentation
├── alembic/                      # Database migrations
├── [Various .md files at root]   # Documentation (to be organized)
├── [Various test_*.py at root]   # Standalone tests (to be moved)
└── Configuration files
```

## Notes

- The baseline shows 7 pre-existing test failures that are not related to the restructuring
- These failures should remain consistent after restructuring (no new failures introduced)
- Coverage should remain at or above 69% after restructuring
- All 734 tests should still be discovered and executed after restructuring

## Success Criteria for Restructuring

1. All 734 tests must still be discovered
2. Test pass/fail ratio must remain the same (726 passed, 7 failed)
3. Coverage must remain at or above 69%
4. No new test failures introduced
5. All imports must resolve correctly
6. Docker build must succeed
7. Bot must start successfully
