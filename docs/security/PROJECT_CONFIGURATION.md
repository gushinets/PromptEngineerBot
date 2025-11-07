# Project Configuration Overview

This document explains the configuration files in the Telegram Prompt Bot project and their purposes.

## Configuration Files

### Dependency Management

**`requirements.txt`** - Primary dependency file
- **Purpose**: Lists all Python package dependencies
- **Used by**: `pip install -r requirements.txt`, Dockerfile, Safety scanner
- **Contains**: Production + development + testing dependencies
- **Format**: Standard pip requirements format

**`pyproject.toml`** - Tool configuration only
- **Purpose**: Configures development tools (pytest, coverage, ruff, bandit)
- **NOT used for**: Package installation or dependency management
- **Contains**: Tool settings for pytest, coverage, ruff, bandit
- **Note**: Simplified version - only tool config, no package metadata

### Security Tools

**`.pre-commit-config.yaml`** - Pre-commit hook configuration
- **Purpose**: Defines which security tools run on git commit
- **Tools**: Ruff, GitLeaks, Bandit, Safety, Semgrep
- **Execution**: Automatic on `git commit`, manual via `pre-commit run`

**`ruff.toml`** - Ruff linter and formatter configuration
- **Purpose**: Python linting, formatting, and security rules
- **Rules**: 100+ enabled rules including security patterns
- **Performance**: 10-100x faster than traditional linters

**`.gitleaks.toml`** - GitLeaks secrets detection
- **Purpose**: Detect hardcoded secrets (API keys, passwords, tokens)
- **Custom rules**: Telegram tokens, OpenAI keys, OpenRouter keys, database URLs
- **Allowlist**: Test files, examples, documentation

**`.bandit`** - Bandit security analysis
- **Purpose**: Python SAST for security vulnerabilities
- **Checks**: SQL injection, command injection, weak crypto, etc.
- **Exclusions**: Test directories, migration files

**`.safety-policy.yml`** - Safety vulnerability exceptions
- **Purpose**: Document known/accepted vulnerabilities
- **Format**: YAML with vulnerability IDs and justifications
- **Usage**: Safety reads this to ignore documented exceptions

**`.semgrep.yml`** - Semgrep custom security rules
- **Purpose**: Pattern-based security analysis
- **Rules**: OWASP Top 10, custom project-specific patterns
- **Scope**: Python files, configuration files

### Testing

**`pytest.ini`** - Pytest configuration (primary)
- **Purpose**: Test discovery, execution, and reporting
- **Also in**: `pyproject.toml` (backup/alternative location)
- **Settings**: Test paths, file patterns, asyncio mode, timeout

**`.coveragerc`** or `pyproject.toml` - Coverage configuration
- **Purpose**: Code coverage measurement settings
- **Location**: Currently in `pyproject.toml` under `[tool.coverage]`
- **Settings**: Source paths, omit patterns, exclusion lines

### Application

**`.env`** - Environment variables (not in git)
- **Purpose**: Secrets and configuration for local development
- **Contains**: API keys, database URLs, SMTP credentials
- **Security**: Listed in `.gitignore`, never committed

**`.env.example`** - Environment template
- **Purpose**: Documents required environment variables
- **Contains**: Placeholder values, no real secrets
- **Usage**: Copy to `.env` and fill in real values

**`alembic.ini`** - Database migration configuration
- **Purpose**: Alembic database migration settings
- **Contains**: Database connection, migration paths

**`docker-compose.yml`** - Docker orchestration
- **Purpose**: Multi-container setup (app, PostgreSQL, Redis)
- **Environment**: Development/testing environment

**`Dockerfile`** - Container image definition
- **Purpose**: Builds application container image
- **Dependencies**: Installs from `requirements.txt`

### IDE

**`.vscode/settings.json`** - VS Code configuration
- **Purpose**: IDE integration for security tools
- **Features**: Real-time linting, format on save, Ruff integration

**`.vscode/tasks.json`** - VS Code tasks
- **Purpose**: Manual security scan tasks
- **Tasks**: Run individual security tools from command palette

### Git

**`.gitignore`** - Git exclusions
- **Purpose**: Files/directories not tracked by git
- **Excludes**: `.env`, `*.pyc`, `.venv/`, `__pycache__/`, scan results

## Configuration Hierarchy

### Tool Configuration Priority

Most tools check multiple locations in this order:

**Ruff:**
1. `ruff.toml` (primary)
2. `pyproject.toml` under `[tool.ruff]` (fallback)
3. Command-line arguments (override)

**Bandit:**
1. `.bandit` (primary)
2. `pyproject.toml` under `[tool.bandit]` (fallback)
3. Command-line arguments (override)

**Pytest:**
1. `pytest.ini` (primary)
2. `pyproject.toml` under `[tool.pytest.ini_options]` (fallback)
3. Command-line arguments (override)

**Coverage:**
1. `.coveragerc` (if exists)
2. `pyproject.toml` under `[tool.coverage]` (current)
3. Command-line arguments (override)

## Why This Structure?

### Dedicated Config Files (Preferred)

**Advantages:**
- ✅ Clear separation of concerns
- ✅ Tool-specific documentation
- ✅ Easier to find and modify
- ✅ Better for large configurations

**Used for:**
- Ruff (`ruff.toml`)
- GitLeaks (`.gitleaks.toml`)
- Bandit (`.bandit`)
- Safety (`.safety-policy.yml`)
- Semgrep (`.semgrep.yml`)

### pyproject.toml (Backup)

**Advantages:**
- ✅ Single file for multiple tools
- ✅ Python community standard (PEP 518/621)
- ✅ IDE recognition

**Used for:**
- pytest (also in `pytest.ini`)
- coverage (only location)
- Ruff (backup to `ruff.toml`)
- Bandit (backup to `.bandit`)

### Why Not Use pyproject.toml for Everything?

1. **Clarity** - Dedicated files are easier to find and understand
2. **Size** - Large configs (like Ruff) would make pyproject.toml huge
3. **Separation** - Security configs separate from test configs
4. **Flexibility** - Can use different formats (TOML, YAML, INI)
5. **Documentation** - Each file can have detailed comments

## Installation Workflow

### Development Setup

```bash
# 1. Clone repository
git clone <repo-url>
cd telegram-prompt-bot

# 2. Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Install security tools
python scripts/setup_security_tools.py

# 5. Configure environment
cp .env.example .env
# Edit .env with your credentials

# 6. Run tests
pytest

# 7. Start development
python run_bot.py
```

### Docker Setup

```bash
# 1. Configure environment
cp .env.example .env
# Edit .env with your credentials

# 2. Build and run
docker-compose up --build

# Security tools run in pre-commit hooks (not in container)
```

## Configuration Best Practices

### DO ✅

- Keep secrets in `.env` (never commit)
- Use dedicated config files for complex tools
- Document configuration changes
- Test configuration changes locally
- Keep configurations in sync across environments

### DON'T ❌

- Commit `.env` file
- Hardcode secrets in config files
- Mix production and development configs
- Ignore security tool warnings without investigation
- Disable security checks without documentation

## Troubleshooting

### Tool Not Reading Configuration

**Problem**: Tool ignores configuration file

**Solutions:**
1. Check file name and location (must be in project root)
2. Verify file format (TOML, YAML, INI)
3. Check for syntax errors: `python -c "import tomli; tomli.load(open('file.toml', 'rb'))"`
4. Try command-line arguments as override
5. Check tool documentation for config file precedence

### Configuration Conflicts

**Problem**: Multiple config files with conflicting settings

**Solutions:**
1. Understand tool's config priority (see hierarchy above)
2. Use one primary config location per tool
3. Remove or comment out conflicting settings
4. Use command-line arguments to override temporarily

### Missing Configuration

**Problem**: Tool complains about missing configuration

**Solutions:**
1. Check if config file exists: `ls -la .tool-config`
2. Verify file permissions: `chmod 644 .tool-config`
3. Ensure file is not in `.gitignore`
4. Check if tool requires specific config format

## Additional Resources

- [Pre-commit Setup Guide](pre-commit-setup.md) - Security tool installation
- [Tool Reference](tool-reference.md) - Detailed tool documentation
- [Troubleshooting Guide](troubleshooting.md) - Common issues
- [Quick Start](QUICK_START.md) - 5-minute setup guide

---

**Last Updated**: November 7, 2025  
**Configuration Version**: 1.0 (Simplified pyproject.toml)
