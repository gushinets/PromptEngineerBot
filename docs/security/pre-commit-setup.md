# Pre-commit Security Setup

## Overview

This document provides comprehensive guidance for setting up and using the automated security scanning configuration for the Telegram Prompt Engineering Bot project. The security configuration uses the pre-commit framework to run multiple security tools before each commit, catching vulnerabilities early in the development process.

### What is Pre-commit?

Pre-commit is a framework for managing and maintaining multi-language pre-commit hooks. It automatically runs security checks before code is committed to version control, preventing security vulnerabilities from entering the codebase.

### Security Tools Integrated

Our configuration integrates five complementary security tools:

1. **Ruff** - Fast Python linting and formatting with security rules (10-100x faster than traditional linters)
2. **GitLeaks** - Secrets detection to prevent hardcoded credentials and API keys
3. **Bandit** - Python-specific Static Application Security Testing (SAST)
4. **Safety** - Dependency vulnerability scanning against known CVEs
5. **Semgrep** - Pattern-based security analysis with OWASP Top 10 rules

### Security Coverage

The integrated tools provide comprehensive coverage for:

- **OWASP Top 10 Vulnerabilities**: SQL injection, command injection, authentication bypasses
- **Secrets Detection**: API keys, tokens, passwords, private keys, connection strings
- **Python Security Issues**: Insecure cryptography, unsafe deserialization, weak random number generation
- **Dependency Vulnerabilities**: Known CVEs in third-party packages
- **Code Quality**: Import sorting, formatting, type hints, complexity analysis

### Performance Characteristics

- **Single file commit**: < 5 seconds
- **10 file commit**: < 15 seconds
- **50 file commit**: < 45 seconds
- **Full repository scan**: < 2 minutes

Performance is optimized through parallel execution, intelligent file filtering, and caching.

## Installation

### Prerequisites

Before installing the security configuration, ensure you have:

- **Python 3.12 or higher** installed
- **Git 2.30 or higher** installed
- **pip** package manager available
- **4GB RAM minimum** (8GB recommended for optimal performance)
- **Multi-core CPU** for parallel execution

Verify your Python version:

```bash
python --version
# Should output: Python 3.12.x or higher
```

### Automated Installation (Recommended)

The easiest way to set up the security configuration is using the automated installation script:

```bash
python scripts/setup_security_tools.py
```

This script will:
1. Detect your Python version and verify compatibility (Python 3.12+)
2. Detect your environment (OS, Git availability, virtual environment)
3. Install the pre-commit framework
4. Install all security tools (Ruff, GitLeaks, Bandit, Safety, Semgrep)
5. Validate each tool installation
6. Configure git hooks to run on every commit
7. Install pre-commit hook dependencies
8. Provide a detailed installation summary and next steps

The script includes:
- **Progress indicators** showing installation progress (1/10, 2/10, etc.)
- **Clear error messages** if any installation step fails
- **Validation checks** to ensure all tools are working correctly
- **Platform detection** with platform-specific installation guidance
- **Completion summary** showing which tools were successfully installed

The entire setup process typically completes in under 2 minutes.

### Manual Installation

If you prefer manual installation or the automated script is not available, follow these steps:

#### Step 1: Install Pre-commit Framework

```bash
pip install pre-commit
```

Verify installation:

```bash
pre-commit --version
# Should output: pre-commit 3.x.x
```

#### Step 2: Install Security Tools

Install all required security tools via pip:

```bash
pip install ruff bandit safety semgrep
```

For GitLeaks, download the appropriate binary for your platform:

**Windows:**
```powershell
# Download from GitHub releases
Invoke-WebRequest -Uri "https://github.com/gitleaks/gitleaks/releases/latest/download/gitleaks_windows_amd64.zip" -OutFile "gitleaks.zip"
Expand-Archive -Path "gitleaks.zip" -DestinationPath "$env:USERPROFILE\bin"
# Add to PATH
```

**macOS:**
```bash
brew install gitleaks
```

**Linux:**
```bash
# Download and install from GitHub releases
wget https://github.com/gitleaks/gitleaks/releases/latest/download/gitleaks_linux_amd64.tar.gz
tar -xzf gitleaks_linux_amd64.tar.gz
sudo mv gitleaks /usr/local/bin/
```

Verify all tools are installed:

```bash
ruff --version
gitleaks version
bandit --version
safety --version
semgrep --version
```

#### Step 3: Install Git Hooks

Navigate to the project root directory and install the pre-commit hooks:

```bash
pre-commit install
```

This creates a git hook at `.git/hooks/pre-commit` that will run automatically on every commit.

#### Step 4: Install Hook Environments

Pre-commit needs to set up isolated environments for each tool:

```bash
pre-commit install --install-hooks
```

This may take a few minutes on first run as it downloads and caches tool dependencies.

#### Step 5: Validate Installation

Run a test to ensure everything is working:

```bash
pre-commit run --all-files
```

This runs all security checks on your entire codebase. You may see some findings that need to be addressed.

## Quick Start Guide

### Basic Usage

Once installed, pre-commit runs automatically when you commit code:

```bash
# Stage your changes
git add file.py

# Commit (hooks run automatically)
git commit -m "Add new feature"
```

If any security issues are detected, the commit will be blocked and you'll see detailed error messages.

### Running Hooks Manually

You can run hooks manually without committing:

```bash
# Run all hooks on all files
pre-commit run --all-files

# Run all hooks on staged files only
pre-commit run

# Run specific hook on all files
pre-commit run ruff --all-files
pre-commit run gitleaks --all-files
pre-commit run bandit --all-files

# Run on specific files
pre-commit run --files telegram_bot/main.py telegram_bot/utils.py
```

### Understanding Hook Output

When a hook fails, you'll see output like this:

```
Ruff....................................................................Failed
- hook id: ruff
- exit code: 1

telegram_bot/services/ai_service.py:45:1: S608 Possible SQL injection vector through string-based query construction
telegram_bot/utils/helpers.py:12:5: F401 'os' imported but unused

GitLeaks................................................................Passed
Bandit..................................................................Failed
- hook id: bandit
- exit code: 1

>> Issue: [B608:hardcoded_sql_expressions] Possible SQL injection vector through string-based query construction
   Severity: Medium   Confidence: Low
   Location: telegram_bot/services/ai_service.py:45
```

### Fixing Issues

1. **Review the findings**: Read the error messages carefully to understand what was detected
2. **Fix the code**: Address the security issues or code quality problems
3. **Re-stage changes**: `git add <fixed-files>`
4. **Commit again**: `git commit -m "Your message"`

### Emergency Bypass

In rare cases where you need to commit without running hooks (e.g., emergency hotfix):

```bash
git commit --no-verify -m "Emergency fix"
```

**⚠️ Warning**: Bypassed commits still need to pass security checks in CI. Use this sparingly and only when absolutely necessary.

## Architecture Overview

### Configuration Files

The security setup consists of several configuration files:

```
project-root/
├── .pre-commit-config.yaml    # Main pre-commit configuration
├── ruff.toml                  # Ruff linting and formatting rules
├── .gitleaks.toml            # GitLeaks secrets detection patterns
├── .bandit                   # Bandit security analysis configuration
├── .safety-policy.yml        # Safety vulnerability exceptions
├── .semgrep.yml              # Semgrep custom security rules
└── .vscode/
    ├── settings.json         # IDE integration settings
    └── tasks.json            # VS Code tasks for manual tool execution
```

### Hook Execution Flow

```
Developer commits code
         ↓
Git pre-commit hook triggered
         ↓
Pre-commit framework orchestrates tools
         ↓
    ┌────┴────┬────────┬────────┬────────┐
    ↓         ↓        ↓        ↓        ↓
  Ruff   GitLeaks  Bandit   Safety  Semgrep
    ↓         ↓        ↓        ↓        ↓
    └────┬────┴────────┴────────┴────────┘
         ↓
  All tools pass? ──Yes──> Commit allowed
         │
        No
         ↓
  Commit blocked with error details
```

### Tool Responsibilities

| Tool | What It Checks | When It Runs | Typical Execution Time |
|------|----------------|--------------|----------------------|
| **Ruff** | Python syntax, imports, formatting, security patterns | Every commit on .py files | 1-3 seconds |
| **GitLeaks** | Hardcoded secrets, API keys, tokens | Every commit on all files | 2-5 seconds |
| **Bandit** | Python security vulnerabilities (SQL injection, etc.) | Every commit on .py files | 3-8 seconds |
| **Safety** | Known vulnerabilities in dependencies | Every commit when requirements.txt changes | 2-4 seconds |
| **Semgrep** | Custom security patterns, OWASP Top 10 | Every commit on .py files | 5-10 seconds |

### Parallel Execution

Tools run in parallel when possible to minimize total execution time. The pre-commit framework automatically manages parallelization based on tool dependencies and system resources.

### Caching Strategy

Pre-commit caches tool installations and scan results to improve performance:

- **Tool binaries**: Cached in `~/.cache/pre-commit/`
- **Scan results**: Only changed files are re-scanned
- **Cache invalidation**: Automatic when tool versions or configurations change

To manually clear the cache:

```bash
pre-commit clean
```

## Configuration Customization

### Updating Tool Versions

Tool versions are pinned in `.pre-commit-config.yaml` for reproducibility. To update to the latest versions:

```bash
pre-commit autoupdate
```

This updates the `rev` field for each tool to the latest stable release.

### Modifying Security Rules

Each tool has its own configuration file where you can customize rules:

- **Ruff**: Edit `ruff.toml` to enable/disable specific rules
- **GitLeaks**: Edit `.gitleaks.toml` to add custom patterns or allowlists
- **Bandit**: Edit `.bandit` to adjust severity thresholds or exclusions
- **Safety**: Edit `.safety-policy.yml` to ignore specific vulnerabilities
- **Semgrep**: Edit `.semgrep.yml` to add custom security rules

See [tool-reference.md](tool-reference.md) for detailed configuration options.

### Adding Exceptions

To allow specific code patterns that are flagged as false positives:

**Inline suppression (Ruff/Bandit)**:
```python
# noqa: S608  # Suppress specific Ruff rule
api_key = get_key()  # nosec B105  # Suppress Bandit warning
```

**Configuration-based suppression**:
Add patterns to the appropriate configuration file (see tool-reference.md for details).

## IDE Integration

### Visual Studio Code

The project includes VS Code configuration for real-time security feedback:

1. **Install recommended extensions**:
   - Ruff (charliermarsh.ruff)
   - Python (ms-python.python)

2. **Configuration is automatic**: Settings are in `.vscode/settings.json`

3. **Features enabled**:
   - Real-time linting with Ruff
   - Format on save
   - Automatic import sorting
   - Security warnings in Problems panel

4. **Manual tool execution**: Press `Ctrl+Shift+P` and search for:
   - "Tasks: Run Task" → "Run Security Scan"
   - "Tasks: Run Task" → "Run Ruff Lint"
   - "Tasks: Run Task" → "Run GitLeaks"

### Kiro IDE

Kiro IDE has built-in support for pre-commit hooks and will automatically detect the configuration.

## Troubleshooting

For common issues and solutions, see [troubleshooting.md](troubleshooting.md).

### Quick Fixes

**Hooks not running**:
```bash
pre-commit install
```

**Slow performance**:
```bash
pre-commit run --files <specific-file>  # Test single file
pre-commit clean  # Clear cache
```

**Tool not found**:
```bash
pip install <tool-name>
# or
pre-commit install --install-hooks
```

## CI/CD Integration

The same security checks run in CI to ensure consistency. See [ci-integration.md](ci-integration.md) for platform-specific examples.

## Next Steps

1. **Review findings**: Run `pre-commit run --all-files` and review any security issues
2. **Fix issues**: Address legitimate security vulnerabilities
3. **Configure exceptions**: Add false positives to allowlists
4. **Educate team**: Share this documentation with your team
5. **Monitor performance**: Track hook execution time and optimize if needed

## Additional Resources

- [Tool Reference](tool-reference.md) - Detailed documentation for each security tool
- [Troubleshooting Guide](troubleshooting.md) - Common issues and solutions
- [CI Integration](ci-integration.md) - Setting up security checks in CI/CD pipelines
- [Pre-commit Documentation](https://pre-commit.com/) - Official pre-commit framework docs

## Support

For questions or issues:

1. Check the [troubleshooting guide](troubleshooting.md)
2. Review tool-specific documentation in [tool-reference.md](tool-reference.md)
3. Consult the main project documentation
4. Open an issue in the project repository
