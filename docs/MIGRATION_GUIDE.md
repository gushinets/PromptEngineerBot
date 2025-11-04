# Migration Guide: Project Restructuring

This guide helps developers migrate their code and workflows to the new project structure. The restructuring moves from a flat layout to a proper Python package tree structure following best practices.

## Overview of Changes

### What Changed?

The project has been reorganized from a flat structure with `src/` to a proper package structure with `telegram_bot/`:

**Before:**
```
PromptEngineerBot/
├── src/                    # Source code
├── tests/                  # Mixed test types
├── tools/                  # Utility scripts
├── *.md                    # Documentation at root
└── test_*.py              # Standalone tests at root
```

**After:**
```
PromptEngineerBot/
├── telegram_bot/          # Main package (renamed from src)
│   ├── core/             # Core business logic
│   ├── services/         # External services
│   ├── auth/             # Authentication
│   ├── data/             # Data layer
│   ├── utils/            # Utilities
│   ├── flows/            # User flows
│   └── prompts/          # Prompt templates
├── tests/                # Organized by type
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── scripts/              # Utility scripts
│   └── tools/
└── docs/                 # Documentation
    ├── architecture/
    ├── deployment/
    ├── guides/
    ├── guidelines/
    └── development/
```

### Why This Change?

1. **Better Organization**: Clear separation of concerns with logical grouping
2. **Python Best Practices**: Follows standard Python package structure conventions
3. **Improved Navigation**: Easier to find files and understand project layout
4. **Cleaner Root**: Configuration files at root, everything else organized
5. **Test Organization**: Tests categorized by type (unit/integration/e2e)
6. **Documentation Hub**: All docs in one place with clear structure

## Import Migration

### Import Path Changes

All imports need to be updated from `src.` to `telegram_bot.` with the new module structure.

#### Core Modules

**Before:**
```python
from src.bot_handler import BotHandler
from src.conversation_manager import ConversationManager
from src.state_manager import StateManager
```

**After:**
```python
from telegram_bot.core.bot_handler import BotHandler
from telegram_bot.core.conversation_manager import ConversationManager
from telegram_bot.core.state_manager import StateManager
```

#### LLM Services

**Before:**
```python
from src.llm_factory import LLMClientFactory
from src.llm_client_base import LLMClientBase
from src.openai_client import OpenAIClient
from src.openrouter_client import OpenRouterClient
```

**After:**
```python
from telegram_bot.services.llm.factory import LLMClientFactory
from telegram_bot.services.llm.base import LLMClientBase
from telegram_bot.services.llm.openai_client import OpenAIClient
from telegram_bot.services.llm.openrouter_client import OpenRouterClient
```

#### Other Services

**Before:**
```python
from src.email_service import EmailService
from src.gsheets_logging import GSheetsLogger
from src.redis_client import RedisClient
```

**After:**
```python
from telegram_bot.services.email_service import EmailService
from telegram_bot.services.gsheets_logging import GSheetsLogger
from telegram_bot.services.redis_client import RedisClient
```

#### Authentication

**Before:**
```python
from src.auth_service import AuthService
from src.user_profile_utils import update_user_profile
```

**After:**
```python
from telegram_bot.auth.auth_service import AuthService
from telegram_bot.auth.user_profile_utils import update_user_profile
```

#### Data Layer

**Before:**
```python
from src.database import get_db, User
```

**After:**
```python
from telegram_bot.data.database import get_db, User
```

#### Utilities

**Before:**
```python
from src.config import Config
from src.messages import parse_llm_response
from src.prompt_loader import PromptLoader
from src.email_templates import render_email_template
from src.logging_utils import setup_logging
from src.metrics import track_metric
from src.health_checks import check_service_health
from src.audit_service import log_audit_event
from src.graceful_degradation import handle_service_degradation
```

**After:**
```python
from telegram_bot.utils.config import Config
from telegram_bot.utils.messages import parse_llm_response
from telegram_bot.utils.prompt_loader import PromptLoader
from telegram_bot.utils.email_templates import render_email_template
from telegram_bot.utils.logging_utils import setup_logging
from telegram_bot.utils.metrics import track_metric
from telegram_bot.utils.health_checks import check_service_health
from telegram_bot.utils.audit_service import log_audit_event
from telegram_bot.utils.graceful_degradation import handle_service_degradation
```

#### Flows

**Before:**
```python
from src.email_flow import handle_email_flow
from src.background_tasks import schedule_task
```

**After:**
```python
from telegram_bot.flows.email_flow import handle_email_flow
from telegram_bot.flows.background_tasks import schedule_task
```

### Quick Migration Script

If you have feature branches with old imports, use this find-and-replace pattern:

```bash
# Find all Python files with old imports
grep -r "from src\." --include="*.py"

# Example sed command to update imports (use with caution, test first!)
# This is a starting point - you'll need to adjust for specific modules
find . -name "*.py" -type f -exec sed -i 's/from src\./from telegram_bot./g' {} +
```

**Important:** The above is a starting point. You'll need to manually adjust imports based on the new module structure (core, services, auth, data, utils, flows).

## Test Migration

### Test File Locations

Tests have been reorganized by type:

**Unit Tests** (`tests/unit/`):
- `test_config.py`
- `test_conversation_manager.py`
- `test_state_manager.py`
- `test_messages.py`
- `test_prompt_loader.py`
- `test_llm_factory.py`
- `test_llm_client_base.py`
- `test_logging_utils.py`
- `test_metrics.py`
- `test_graceful_degradation.py`
- `test_user_profile_utils.py`
- `test_utils.py`

**Integration Tests** (`tests/integration/`):
- `test_bot_handler.py`
- `test_bot_handler_integration.py`
- `test_bot_handler_health_integration.py`
- `test_auth_service.py`
- `test_auth_service_profile_integration.py`
- `test_database.py`
- `test_email_service.py`
- `test_email_service_single_result.py`
- `test_email_flow_integration.py`
- `test_email_flow_timeout.py`
- `test_redis_client.py`
- `test_health_checks.py`
- `test_audit_service.py`
- `test_background_tasks.py`
- `test_llm_clients.py`
- `test_followup_integration.py`
- `test_followup_error_handling.py`
- `test_profile_flow_integration.py`
- `test_post_optimization_integration.py`
- `test_post_optimization_email.py`
- `test_migration_integration.py`
- `test_token_accumulation_fix.py`

**E2E Tests** (`tests/e2e/`):
- `test_bot.py`
- `test_performance.py`
- `test_security.py`
- `test_task8_simple.py`

### Running Tests

**Before:**
```bash
# Run all tests
pytest tests/

# Run specific test
pytest tests/test_config.py
```

**After:**
```bash
# Run all tests
pytest tests/

# Run by category
pytest tests/unit/
pytest tests/integration/
pytest tests/e2e/

# Run specific test
pytest tests/unit/test_config.py
pytest tests/integration/test_bot_handler.py
```

## Configuration Changes

### pyproject.toml

The package name has changed from `src` to `telegram_bot`:

**Before:**
```toml
[project]
name = "src"

[tool.coverage.run]
source = ["src"]
```

**After:**
```toml
[project]
name = "telegram_bot"

[tool.coverage.run]
source = ["telegram_bot"]
```

### Docker

**Dockerfile Changes:**

**Before:**
```dockerfile
COPY src ./src
```

**After:**
```dockerfile
COPY telegram_bot ./telegram_bot
```

**docker-compose.yml Changes:**

Volume mounts and paths have been updated to reference `telegram_bot/` instead of `src/`.

### VS Code / Kiro IDE

**launch.json Changes:**

**Before:**
```json
{
  "module": "src.main"
}
```

**After:**
```json
{
  "module": "telegram_bot.main"
}
```

## Entry Points

### Running the Bot

**Before:**
```bash
python run_bot.py
python -m src.main
```

**After:**
```bash
python run_bot.py
python -m telegram_bot.main
```

Both methods still work, but imports inside have been updated.

### Running Scripts

**Before:**
```bash
python validate_system.py
python tools/diagnose_gsheets.py
```

**After:**
```bash
python scripts/validate_system.py
python scripts/tools/diagnose_gsheets.py
```

## Documentation

### Documentation Structure

All documentation has been moved to `docs/` with clear organization:

- **`docs/INDEX.md`**: Central documentation hub with links to everything
- **`docs/architecture/`**: System architecture and design documents
- **`docs/deployment/`**: Deployment guides and instructions
- **`docs/guides/`**: User guides and tutorials
- **`docs/guidelines/`**: Development guidelines and standards
- **`docs/development/`**: Development notes and fix summaries

### Finding Documentation

**Before:**
```
AGENTS.MD                              # At root
DEPLOYMENT.md                          # At root
E2E_USER_PATHS_DOCUMENTATION.md       # At root
*_SUMMARY.md                          # Various at root
```

**After:**
```
docs/guidelines/AGENTS.md
docs/deployment/DEPLOYMENT.md
docs/guides/E2E_USER_PATHS_DOCUMENTATION.md
docs/development/*_SUMMARY.md
```

**Quick Access:** Start at `docs/INDEX.md` for links to all documentation.

## Common Migration Scenarios

### Scenario 1: Working on a Feature Branch

You have a feature branch with code using old imports:

1. **Merge or rebase** your branch with the restructured main branch
2. **Update imports** in your feature code using the patterns above
3. **Run tests** to verify everything works:
   ```bash
   pytest tests/
   ```
4. **Fix any import errors** that appear

### Scenario 2: Adding New Code

When adding new code to the restructured project:

1. **Place files in the correct package**:
   - Business logic → `telegram_bot/core/`
   - External services → `telegram_bot/services/`
   - Utilities → `telegram_bot/utils/`
   - User flows → `telegram_bot/flows/`

2. **Use correct imports**:
   ```python
   from telegram_bot.core.bot_handler import BotHandler
   from telegram_bot.utils.config import Config
   ```

3. **Add tests in the right location**:
   - Unit tests → `tests/unit/`
   - Integration tests → `tests/integration/`
   - E2E tests → `tests/e2e/`

### Scenario 3: Updating Documentation

When updating or adding documentation:

1. **Place docs in the correct category**:
   - Architecture docs → `docs/architecture/`
   - Deployment guides → `docs/deployment/`
   - User guides → `docs/guides/`
   - Development notes → `docs/development/`

2. **Update `docs/INDEX.md`** with links to new documentation

3. **Update `README.md`** if the changes affect the main project overview

## Benefits of New Structure

### For Developers

1. **Clearer Organization**: Easy to find related code
2. **Better IDE Support**: Proper package structure improves autocomplete
3. **Easier Navigation**: Logical grouping reduces cognitive load
4. **Standard Conventions**: Follows Python packaging best practices

### For Testing

1. **Test Organization**: Clear separation of unit/integration/e2e tests
2. **Faster Test Runs**: Easy to run specific test categories
3. **Better Coverage**: Organized structure makes gaps more visible

### For Documentation

1. **Central Hub**: All docs in one place with clear index
2. **Logical Grouping**: Easy to find relevant documentation
3. **Better Maintenance**: Organized structure easier to keep updated

### For Deployment

1. **Cleaner Builds**: Only necessary files in Docker images
2. **Better Caching**: Organized structure improves Docker layer caching
3. **Easier Configuration**: Clear separation of code and config

## Troubleshooting

### Import Errors

**Error:** `ModuleNotFoundError: No module named 'src'`

**Solution:** Update imports from `src.` to `telegram_bot.` with the new module structure.

### Test Discovery Issues

**Error:** `pytest` not finding tests

**Solution:** Tests are now in subdirectories. Use:
```bash
pytest tests/unit/
pytest tests/integration/
pytest tests/e2e/
```

### Docker Build Failures

**Error:** Docker can't find source files

**Solution:** Ensure Dockerfile uses `COPY telegram_bot ./telegram_bot` instead of `COPY src ./src`

### Path Resolution Issues

**Error:** Can't find prompt files or other resources

**Solution:** Path resolution should work the same, but verify that relative paths are resolved from the correct base directory.

## Getting Help

If you encounter issues during migration:

1. **Check this guide** for common scenarios
2. **Review the documentation** at `docs/INDEX.md`
3. **Look at existing code** for import examples
4. **Run tests** to verify your changes work correctly
5. **Check the design document** at `.kiro/specs/project-restructuring/design.md` for detailed structure information

## Summary

The restructuring improves project organization while maintaining all functionality. Key changes:

- ✅ `src/` → `telegram_bot/` with logical subpackages
- ✅ Tests organized by type (unit/integration/e2e)
- ✅ Documentation centralized in `docs/`
- ✅ Scripts moved to `scripts/`
- ✅ All imports updated to new structure
- ✅ Configuration files updated
- ✅ 100% backward compatibility for functionality

The new structure follows Python best practices and makes the codebase more maintainable and easier to navigate.
