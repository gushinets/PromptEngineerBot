# Design Document: Project Restructuring

## Overview

This document outlines the design for reorganizing the Telegram Prompt Engineering Bot from a flat layout to a proper Python package tree structure. The restructuring will improve code organization, maintainability, and follow Python packaging best practices while preserving all existing functionality.

### Goals
- Organize source code into a proper Python package structure
- Separate tests by type (unit, integration, e2e)
- Consolidate documentation in a dedicated directory
- Clean up temporary and generated files
- Update all configuration files to work with the new structure
- Maintain 100% backward compatibility for functionality

### Non-Goals
- Modifying any business logic or implementation
- Changing test behavior or coverage
- Altering deployment processes (only updating paths)

## Architecture

### Current Structure (Flat Layout)
```
PromptEngineerBot/
├── src/                          # Source code
├── tests/                        # Tests (mixed types)
├── tools/                        # Utility scripts
├── docs/                         # Some documentation
├── alembic/                      # Database migrations
├── *.md                          # Documentation scattered at root
├── test_*.py                     # Standalone test files at root
├── *.py                          # Utility scripts at root
└── Configuration files at root
```

### Proposed Structure (Tree Layout)
```
PromptEngineerBot/
├── telegram_bot/                 # Main package (renamed from src)
│   ├── __init__.py
│   ├── core/                     # Core business logic
│   │   ├── __init__.py
│   │   ├── bot_handler.py
│   │   ├── conversation_manager.py
│   │   └── state_manager.py
│   ├── services/                 # External service integrations
│   │   ├── __init__.py
│   │   ├── llm/                  # LLM clients
│   │   │   ├── __init__.py
│   │   │   ├── base.py           # llm_client_base.py
│   │   │   ├── factory.py        # llm_factory.py
│   │   │   ├── openai_client.py
│   │   │   └── openrouter_client.py
│   │   ├── email_service.py
│   │   ├── gsheets_logging.py
│   │   └── redis_client.py
│   ├── auth/                     # Authentication
│   │   ├── __init__.py
│   │   ├── auth_service.py
│   │   └── user_profile_utils.py
│   ├── data/                     # Data layer
│   │   ├── __init__.py
│   │   ├── database.py
│   │   └── models/               # Future: SQLAlchemy models
│   ├── utils/                    # Utilities
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── messages.py
│   │   ├── prompt_loader.py
│   │   ├── email_templates.py
│   │   ├── logging_utils.py
│   │   ├── metrics.py
│   │   ├── health_checks.py
│   │   ├── audit_service.py
│   │   └── graceful_degradation.py
│   ├── flows/                    # User flows
│   │   ├── __init__.py
│   │   ├── email_flow.py
│   │   └── background_tasks.py
│   ├── prompts/                  # Prompt templates
│   │   ├── CRAFT_prompt.txt
│   │   ├── LYRA_prompt.txt
│   │   └── GGL_prompt.txt
│   ├── main.py                   # Application entry point
│   └── dependencies.py           # Dependency injection
│
├── tests/                        # All tests
│   ├── __init__.py
│   ├── conftest.py               # Shared fixtures
│   ├── unit/                     # Unit tests
│   │   ├── __init__.py
│   │   ├── test_config.py
│   │   ├── test_conversation_manager.py
│   │   ├── test_state_manager.py
│   │   ├── test_messages.py
│   │   ├── test_prompt_loader.py
│   │   ├── test_llm_factory.py
│   │   ├── test_llm_client_base.py
│   │   ├── test_email_templates.py
│   │   ├── test_logging_utils.py
│   │   ├── test_metrics.py
│   │   ├── test_graceful_degradation.py
│   │   ├── test_user_profile_utils.py
│   │   └── test_utils.py
│   ├── integration/              # Integration tests
│   │   ├── __init__.py
│   │   ├── test_bot_handler.py
│   │   ├── test_bot_handler_integration.py
│   │   ├── test_bot_handler_health_integration.py
│   │   ├── test_auth_service.py
│   │   ├── test_auth_service_profile_integration.py
│   │   ├── test_database.py
│   │   ├── test_email_service.py
│   │   ├── test_email_service_single_result.py
│   │   ├── test_email_flow_integration.py
│   │   ├── test_email_flow_timeout.py
│   │   ├── test_redis_client.py
│   │   ├── test_gsheets_logging.py
│   │   ├── test_health_checks.py
│   │   ├── test_audit_service.py
│   │   ├── test_background_tasks.py
│   │   ├── test_llm_clients.py
│   │   ├── test_followup_integration.py
│   │   ├── test_followup_error_handling.py
│   │   ├── test_profile_flow_integration.py
│   │   ├── test_post_optimization_integration.py
│   │   ├── test_post_optimization_email.py
│   │   ├── test_migration_integration.py
│   │   └── test_token_accumulation_fix.py
│   ├── e2e/                      # End-to-end tests
│   │   ├── __init__.py
│   │   ├── test_bot.py
│   │   ├── test_performance.py
│   │   ├── test_security.py
│   │   └── test_task8_simple.py
│   └── fixtures/                 # Test fixtures
│       └── (existing fixture files)
│
├── scripts/                      # Utility scripts
│   ├── __init__.py
│   ├── validate_system.py        # Moved from root
│   ├── mock_redis.py             # Moved from root
│   └── tools/                    # Moved from tools/
│       ├── __init__.py
│       ├── diagnose_gsheets.py
│       └── repair_gsheets.py
│
├── docs/                         # Documentation
│   ├── INDEX.md                  # NEW: Documentation index
│   ├── README.md                 # Project overview (copy of root README)
│   ├── guidelines/               # Coding guidelines and standards
│   │   └── AGENTS.md             # Moved from root
│   ├── architecture/             # Architecture documentation
│   │   └── USER_PROFILE_SYSTEM.md
│   ├── deployment/               # Deployment guides
│   │   └── DEPLOYMENT.md         # Moved from root
│   ├── guides/                   # User guides
│   │   └── E2E_USER_PATHS_DOCUMENTATION.md
│   ├── development/              # Development notes
│   │   ├── ASYNC_SYNC_FIX_SUMMARY.md
│   │   ├── FINAL_CODE_CLEANUP_SUMMARY.md
│   │   ├── FINAL_INTEGRATION_VALIDATION_REPORT.md
│   │   ├── FINAL_VALIDATION_REPORT.md
│   │   ├── FIX_SUMMARY.md
│   │   ├── FOLLOWUP_DECLINE_FIX_SUMMARY.md
│   │   ├── POST_OPTIMIZATION_EMAIL_FIX_SUMMARY.md
│   │   └── VALIDATE_POST_OPTIMIZATION_FIX.md
│   └── specs/                    # Feature specifications
│       └── (links to .kiro/specs)
│
├── alembic/                      # Database migrations (unchanged)
│   ├── versions/
│   ├── env.py
│   └── script.py.mako
│
├── .github/                      # GitHub configuration (unchanged)
├── .kiro/                        # Kiro IDE configuration (unchanged)
├── .vscode/                      # VS Code configuration (to be updated)
│
├── run_bot.py                    # Entry point script (updated imports)
├── alembic.ini                   # Alembic configuration
├── pyproject.toml                # Project configuration (updated)
├── pytest.ini                    # Pytest configuration (updated)
├── requirements.txt              # Dependencies
├── README.md                     # Main README (updated)
├── .env.example                  # Environment template
├── .gitignore                    # Git ignore (updated)
├── .dockerignore                 # Docker ignore (updated)
├── Dockerfile                    # Docker build (updated)
├── docker-compose.yml            # Docker compose (updated)
├── docker-compose.override.yml   # Docker compose override (updated)
├── init-db.sql                   # Database initialization
└── google_service_key.json       # Service account key (gitignored)
```

## Components and Interfaces

### Package Organization

#### 1. telegram_bot/core/
**Purpose**: Core business logic and bot orchestration
- `bot_handler.py`: Main bot logic and command handling
- `conversation_manager.py`: Conversation state and token tracking
- `state_manager.py`: User state management

#### 2. telegram_bot/services/
**Purpose**: External service integrations
- `llm/`: LLM client implementations
  - `base.py`: Abstract base class for LLM clients
  - `factory.py`: Factory for creating LLM clients
  - `openai_client.py`: OpenAI API integration
  - `openrouter_client.py`: OpenRouter API integration
- `email_service.py`: Email sending functionality
- `gsheets_logging.py`: Google Sheets logging
- `redis_client.py`: Redis integration

#### 3. telegram_bot/auth/
**Purpose**: Authentication and user management
- `auth_service.py`: Authentication logic
- `user_profile_utils.py`: User profile utilities

#### 4. telegram_bot/data/
**Purpose**: Data access layer
- `database.py`: Database connection and session management
- `models/`: Future home for SQLAlchemy models

#### 5. telegram_bot/utils/
**Purpose**: Shared utilities and helpers
- Configuration, logging, metrics, health checks, etc.

#### 6. telegram_bot/flows/
**Purpose**: User interaction flows
- `email_flow.py`: Email verification flow
- `background_tasks.py`: Background task management

### Import Path Changes

#### Before (Flat Structure)
```python
from src.bot_handler import BotHandler
from src.config import Config
from src.llm_factory import LLMClientFactory
```

#### After (Tree Structure)
```python
from telegram_bot.core.bot_handler import BotHandler
from telegram_bot.utils.config import Config
from telegram_bot.services.llm.factory import LLMClientFactory
```

### File Movement Strategy

#### Phase 1: Create New Structure
1. Create all new directories under `telegram_bot/`
2. Create `__init__.py` files in all packages
3. Keep original `src/` intact during migration

#### Phase 2: Move and Update Files
1. Copy files to new locations
2. Update imports within each file
3. Update `__init__.py` files to expose public APIs

#### Phase 3: Update Tests
1. Move test files to appropriate subdirectories
2. Update test imports
3. Update `conftest.py` and fixtures

#### Phase 4: Update Configuration
1. Update `pyproject.toml`
2. Update `pytest.ini`
3. Update Docker files
4. Update `.gitignore` and `.dockerignore`
5. Update VS Code configuration

#### Phase 5: Cleanup
1. Remove old `src/` directory
2. Remove temporary files
3. Verify all tests pass

## Data Models

No changes to data models. All SQLAlchemy models and database schemas remain unchanged.

## Error Handling

### Migration Risks and Mitigation

1. **Import Errors**
   - Risk: Broken imports after file moves
   - Mitigation: Systematic import updates with verification at each step
   - Validation: Run tests after each phase

2. **Path Resolution Issues**
   - Risk: Relative paths breaking after restructure
   - Mitigation: Use absolute imports and update path resolution logic
   - Validation: Test file loading (prompts, configs)

3. **Docker Build Failures**
   - Risk: Docker unable to find files in new locations
   - Mitigation: Update Dockerfile COPY commands incrementally
   - Validation: Test Docker build after each change

4. **Test Discovery Issues**
   - Risk: Pytest unable to discover tests in new structure
   - Mitigation: Update pytest.ini configuration
   - Validation: Run pytest with verbose output

## Testing Strategy

### Test Organization

#### Unit Tests (`tests/unit/`)
- Tests for individual functions and classes
- No external dependencies
- Fast execution
- Examples: config, messages, prompt_loader

#### Integration Tests (`tests/integration/`)
- Tests for component interactions
- May use mocked external services
- Database and Redis integration
- Examples: bot_handler, email_service, auth_service

#### E2E Tests (`tests/e2e/`)
- Full system tests
- Real or near-real external services
- Performance and security tests
- Examples: test_bot, test_performance

### Test Execution

```bash
# Run all tests
pytest

# Run only unit tests
pytest tests/unit/

# Run only integration tests
pytest tests/integration/

# Run only e2e tests
pytest tests/e2e/

# Run with coverage
pytest --cov=telegram_bot --cov-report=html
```

### Validation Steps

1. **Pre-Migration Baseline**
   - Run full test suite
   - Record coverage percentage
   - Document any existing failures

2. **Post-Migration Validation**
   - Run full test suite
   - Verify coverage matches baseline
   - Ensure no new failures

3. **Docker Validation**
   - Build Docker image
   - Run container
   - Verify bot starts successfully

4. **Import Validation**
   - Test all entry points
   - Verify module imports
   - Check for circular dependencies

## File Cleanup Analysis

### Files to Review for Removal

#### Temporary/Generated Files (Recommend Removal)
- `bot.db` - Local SQLite database (regenerated)
- `bot.log` - Log file (regenerated)
- `htmlcov/` - Coverage reports (regenerated)
- `__pycache__/` - Python cache (regenerated)
- `.pytest_cache/` - Pytest cache (regenerated)

#### Standalone Test Files (Recommend Moving or Removal)
- `test_audit_standalone.py` - Move to tests/integration/
- `test_health_simple.py` - Move to tests/integration/
- `test_imports.py` - Keep at root or move to scripts/
- `test_logging_simple.py` - Move to tests/unit/
- `test_metrics_standalone.py` - Move to tests/integration/
- `test_simple_auth.py` - Move to tests/integration/
- `test_token_flow.py` - Move to tests/integration/

#### Utility Scripts (Recommend Moving)
- `validate_system.py` - Move to scripts/
- `mock_redis.py` - Move to scripts/ or tests/fixtures/

#### Documentation Files (Recommend Moving)
- All `*_SUMMARY.md` files - Move to docs/development/
- `DEPLOYMENT.md` - Move to docs/deployment/
- `AGENTS.MD` - Move to docs/architecture/
- `E2E_USER_PATHS_DOCUMENTATION.md` - Move to docs/guides/

#### Configuration Files (Keep at Root)
- `.dockerignore`
- `.env`, `.env.example`
- `.gitignore`
- `alembic.ini`
- `docker-compose.yml`, `docker-compose.override.yml`
- `Dockerfile`
- `init-db.sql`
- `pyproject.toml`
- `pytest.ini`
- `README.md`
- `requirements.txt`
- `run_bot.py`

#### Sensitive Files (Keep, Ensure Gitignored)
- `google_service_key.json`
- `.env`

## Documentation Updates

### INDEX.md Structure

```markdown
# Documentation Index

## Architecture
- [System Architecture](architecture/README.md)
- [Agent System](architecture/AGENTS.md)
- [User Profile System](architecture/USER_PROFILE_SYSTEM.md)

## Deployment
- [Deployment Guide](deployment/DEPLOYMENT.md)
- [Docker Setup](deployment/DOCKER.md)

## User Guides
- [End-to-End User Paths](guides/E2E_USER_PATHS_DOCUMENTATION.md)

## Development
- [Development Notes](development/)
- [Fix Summaries](development/)

## Feature Specifications
- [Email Prompt Delivery](../.kiro/specs/email-prompt-delivery/)
- [Follow-up Questions](../.kiro/specs/follow-up-questions/)
- [Message Internationalization](../.kiro/specs/message-internationalization/)
- [User Profile Extension](../.kiro/specs/user-profile-extension/)
- [Code Cleanup](../.kiro/specs/code-cleanup/)
- [Project Restructuring](../.kiro/specs/project-restructuring/)

## Tools
- [Google Sheets Diagnostics](../scripts/tools/)
```

### README.md Updates

Update the architecture section to reflect the new structure:

```markdown
## 🏗️ Architecture

The bot follows clean architecture principles with clear separation of concerns:

```
telegram_bot/
├── core/              # Core business logic
├── services/          # External service integrations
│   └── llm/          # LLM client implementations
├── auth/             # Authentication and user management
├── data/             # Data access layer
├── utils/            # Shared utilities
├── flows/            # User interaction flows
└── prompts/          # Optimization method prompts
```
```

## Implementation Phases

### Phase 1: Preparation (No Code Changes)
1. Create design document
2. Get user approval for file cleanup
3. Document current test results

### Phase 2: Create New Structure
1. Create `telegram_bot/` directory
2. Create all subdirectories
3. Create `__init__.py` files

### Phase 3: Move Source Files
1. Move files to new locations
2. Update imports in moved files
3. Update `__init__.py` exports

### Phase 4: Move Test Files
1. Categorize tests (unit/integration/e2e)
2. Move to appropriate directories
3. Update test imports

### Phase 5: Move Documentation
1. Move markdown files to docs/
2. Create INDEX.md
3. Update README.md

### Phase 6: Move Scripts
1. Move utility scripts to scripts/
2. Update script imports
3. Test script execution

### Phase 7: Update Configuration
1. Update pyproject.toml
2. Update pytest.ini
3. Update Docker files
4. Update .gitignore and .dockerignore
5. Update VS Code configuration

### Phase 8: Cleanup
1. Remove old src/ directory
2. Remove approved temporary files
3. Remove standalone test files

### Phase 9: Validation
1. Run full test suite
2. Build Docker image
3. Test Docker container
4. Verify all entry points

## Rollback Strategy

If issues are encountered:

1. **Git Reset**: All changes are tracked in git
2. **Phase Rollback**: Each phase is a separate commit
3. **Backup**: Keep `src/` directory until final validation
4. **Test Gating**: Don't proceed to next phase if tests fail

## Success Criteria

1. All tests pass with same coverage as before
2. Docker builds successfully
3. Bot starts and responds to commands
4. All imports resolve correctly
5. Documentation is complete and accurate
6. No temporary files in repository
7. Clean, organized directory structure
