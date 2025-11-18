# Design Document

## Overview

This design document outlines the architecture and implementation strategy for a performance-optimized pre-commit security configuration for the Telegram Prompt Engineering Bot project. The solution integrates five open-source security tools (GitLeaks, Bandit, Safety, Semgrep, and pre-commit framework) to provide comprehensive Static Application Security Testing (SAST), secrets detection, and dependency vulnerability scanning.

The design prioritizes:
- **Security Coverage**: Multi-layered detection of OWASP Top 10 vulnerabilities, hardcoded secrets, and vulnerable dependencies
- **Performance**: Parallel execution, intelligent file filtering, and caching to minimize impact on developer workflow
- **Developer Experience**: Clear error messages, IDE integration, and automated setup
- **Maintainability**: Centralized configuration, version pinning, and comprehensive documentation

### Project Context

The target project is a Python 3.12+ Telegram bot with the following characteristics:
- **Primary Language**: Python (telegram_bot/, scripts/, tests/, alembic/)
- **Configuration Files**: YAML (docker-compose.yml), TOML (pyproject.toml), INI (alembic.ini, pytest.ini)
- **Environment Files**: .env, .env.example
- **Dependencies**: requirements.txt, pyproject.toml
- **Sensitive Data**: API keys (Telegram, OpenAI, OpenRouter), database credentials, SMTP credentials, Google service account JSON
- **Docker Deployment**: Multi-container setup with PostgreSQL and Redis

## Architecture

### Component Diagram

```mermaid
graph TB
    subgraph "Developer Workflow"
        A[Developer] -->|git commit| B[Git Pre-commit Hook]
    end
    
    subgraph "Pre-commit Framework"
        B --> C[Pre-commit Manager]
        C -->|parallel execution| D[Hook Orchestrator]
    end
    
    subgraph "Security Tools Layer"
        D -->|linting & formatting| E[Ruff]
        D -->|secrets scan| F[GitLeaks]
        D -->|Python SAST| G[Bandit]
        D -->|dependency scan| H[Safety]
        D -->|pattern analysis| I[Semgrep]
    end
    
    subgraph "File System"
        E --> J[Staged Files]
        F --> J
        G --> J
        H --> K[requirements.txt<br/>pyproject.toml]
        I --> J
    end
    
    subgraph "Results & Feedback"
        E --> L[Security Report]
        F --> L
        G --> L
        H --> L
        I --> L
        L -->|pass| M[Commit Allowed]
        L -->|fail| N[Commit Blocked]
        N --> O[Error Details]
    end
    
    subgraph "IDE Integration"
        P[VS Code/Kiro IDE] -->|real-time| E
        P[VS Code/Kiro IDE] -->|real-time| G
        P -->|on-demand| D
    end
```

### System Architecture

The security configuration follows a layered architecture:

1. **Git Hook Layer**: Native git pre-commit hook installed by pre-commit framework
2. **Orchestration Layer**: Pre-commit framework manages tool execution, caching, and parallelization
3. **Security Tools Layer**: Five specialized tools providing complementary security coverage
4. **Configuration Layer**: Centralized configuration files for each tool
5. **Reporting Layer**: Unified output format with actionable feedback

### Tool Selection Rationale

| Tool | Purpose | Why Selected | Coverage |
|------|---------|--------------|----------|
| **Ruff** | Python linting & formatting | 10-100x faster than flake8/pylint, includes security rules | Code quality, import sorting, security patterns |
| **GitLeaks** | Secrets detection | Industry-standard, regex-based, low false positives | API keys, tokens, passwords, private keys |
| **Bandit** | Python SAST | Python-specific, AST-based analysis, OWASP-aligned | SQL injection, command injection, crypto issues |
| **Safety** | Dependency scanning | PyPI-focused, CVE database, actionable fixes | Known vulnerabilities in pip packages |
| **Semgrep** | Pattern matching | Fast, customizable rules, multi-language | Custom security policies, complex patterns |
| **Pre-commit** | Hook framework | Language-agnostic, caching, parallel execution | Hook orchestration and management |

## Components and Interfaces

### 1. Pre-commit Configuration (.pre-commit-config.yaml)

**Purpose**: Central configuration file defining all security hooks, their execution order, and parameters.

**Structure**:
```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.8.4  # Latest stable as of design
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
        
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.29.0  # Latest stable as of design
    hooks:
      - id: gitleaks
        
  - repo: https://github.com/PyCQA/bandit
    rev: 1.8.6  # Latest stable as of design
    hooks:
      - id: bandit
        
  - repo: local
    hooks:
      - id: safety  # Will use latest via pip
      - id: semgrep  # Will use latest via pip
```

**Note**: During implementation, these versions will be updated to the latest stable releases available at that time.

**Key Design Decisions**:
- **Version Pinning**: All tools use latest stable versions (rev) to ensure reproducibility and security
- **Hook Ordering**: Fast checks first (Ruff, GitLeaks, Bandit) before slower ones (Semgrep)
- **Ruff Integration**: Replaces flake8, pylint, isort, and pyupgrade with a single fast tool
- **Parallel Execution**: Hooks without dependencies run concurrently
- **File Filtering**: Each hook specifies file patterns to minimize unnecessary scans

### 2. GitLeaks Configuration (.gitleaks.toml)

**Purpose**: Define patterns for detecting hardcoded secrets with project-specific exclusions.

**Key Features**:
- **Pattern Library**: Pre-configured regexes for 100+ secret types
- **Custom Rules**: Project-specific patterns for Telegram tokens, OpenAI keys, OpenRouter keys
- **Allowlist**: Exclude false positives (.env.example, test fixtures, documentation)
- **Path Filtering**: Skip .git/, .venv/, __pycache__/, node_modules/

**Custom Rules for This Project**:
```toml
[[rules]]
id = "telegram-bot-token"
description = "Telegram Bot API Token"
regex = '''[0-9]{8,10}:[a-zA-Z0-9_-]{35}'''
keywords = ["TELEGRAM_TOKEN"]

[[rules]]
id = "openai-api-key"
description = "OpenAI API Key"
regex = '''sk-[a-zA-Z0-9]{48}'''
keywords = ["OPENAI_API_KEY"]

[[rules]]
id = "google-service-account"
description = "Google Service Account JSON"
regex = '''"type":\s*"service_account"'''
path = '''google_service_key\.json'''
```

**Allowlist Strategy**:
```toml
[allowlist]
paths = [
  ".env.example",
  "docs/",
  "tests/fixtures/",
  ".kiro/specs/"
]
regexes = [
  "your_.*_token",  # Placeholder values
  "example\\.com",
  "localhost"
]
```

### 3. Bandit Configuration (.bandit)

**Purpose**: Configure Python security linting with severity thresholds and exclusions.

**Configuration Strategy**:
```yaml
# .bandit
exclude_dirs:
  - /tests/
  - /alembic/versions/
  - /.venv/
  - /__pycache__/
  
skips:
  - B101  # assert_used (common in tests)
  - B601  # paramiko_calls (not used in project)

tests:
  - B201  # flask_debug_true
  - B301  # pickle usage
  - B302  # marshal usage
  - B303  # insecure MD5/SHA1
  - B304  # insecure cipher modes
  - B305  # insecure cipher usage
  - B306  # insecure mktemp
  - B307  # eval usage
  - B308  # mark_safe usage
  - B309  # HTTPSConnection without cert verification
  - B310  # urllib with file:// scheme
  - B311  # random for crypto
  - B312  # telnetlib usage
  - B313  # xml parsing vulnerabilities
  - B314  # xml.etree.ElementTree
  - B315  # xml.etree.cElementTree
  - B316  # xml.sax
  - B317  # xml.expat
  - B318  # xml.dom.minidom
  - B319  # xml.dom.pulldom
  - B320  # lxml
  - B321  # ftplib
  - B322  # input usage
  - B323  # unverified SSL context
  - B324  # hashlib with insecure algorithms
  - B401  # import_telnetlib
  - B402  # import_ftplib
  - B403  # import_pickle
  - B404  # import_subprocess
  - B405  # import_xml_etree
  - B406  # import_xml_sax
  - B407  # import_xml_expat
  - B408  # import_xml_minidom
  - B409  # import_xml_pulldom
  - B410  # import_lxml
  - B411  # import_xmlrpclib
  - B501  # request_with_no_cert_validation
  - B502  # ssl_with_bad_version
  - B503  # ssl_with_bad_defaults
  - B504  # ssl_with_no_version
  - B505  # weak_cryptographic_key
  - B506  # yaml_load
  - B507  # ssh_no_host_key_verification
  - B601  # paramiko_calls
  - B602  # shell_injection
  - B603  # subprocess_without_shell_equals_true
  - B604  # any_other_function_with_shell_equals_true
  - B605  # start_process_with_a_shell
  - B606  # start_process_with_no_shell
  - B607  # start_process_with_partial_path
  - B608  # hardcoded_sql_expressions
  - B609  # linux_commands_wildcard_injection

severity: medium
confidence: medium
```

**Project-Specific Considerations**:
- **Exclude Tests**: Test files often use patterns flagged by Bandit (assert, hardcoded values)
- **Exclude Migrations**: Alembic migrations contain auto-generated SQL
- **Focus on HIGH/MEDIUM**: Reduce noise from low-severity findings
- **Command Injection**: Critical for bot that processes user input
- **SQL Injection**: Important for database operations
- **Crypto Issues**: Relevant for password hashing (argon2-cffi)

### 4. Ruff Configuration (ruff.toml or pyproject.toml)

**Purpose**: Configure Ruff for fast Python linting, formatting, and code quality checks.

**Why Ruff Over flake8/pylint**:
- **Performance**: 10-100x faster than traditional linters (written in Rust)
- **All-in-One**: Replaces flake8, pylint, isort, pyupgrade, and more
- **Security Rules**: Includes security-focused rules (S-prefix) for common vulnerabilities
- **Auto-Fix**: Automatically fixes many issues including import sorting and code formatting
- **Modern**: Built for Python 3.12+ with excellent type hint support

**Configuration Strategy (ruff.toml)**:
```toml
# Ruff configuration for security and code quality
target-version = "py312"
line-length = 100
indent-width = 4

[lint]
# Enable security-focused rule sets
select = [
    "E",      # pycodestyle errors
    "W",      # pycodestyle warnings
    "F",      # pyflakes
    "I",      # isort (import sorting)
    "N",      # pep8-naming
    "UP",     # pyupgrade
    "S",      # flake8-bandit (security)
    "B",      # flake8-bugbear
    "C4",     # flake8-comprehensions
    "DTZ",    # flake8-datetimez
    "T10",    # flake8-debugger
    "EM",     # flake8-errmsg
    "ISC",    # flake8-implicit-str-concat
    "ICN",    # flake8-import-conventions
    "PIE",    # flake8-pie
    "PT",     # flake8-pytest-style
    "Q",      # flake8-quotes
    "RSE",    # flake8-raise
    "RET",    # flake8-return
    "SIM",    # flake8-simplify
    "TID",    # flake8-tidy-imports
    "ARG",    # flake8-unused-arguments
    "PTH",    # flake8-use-pathlib
    "PL",     # pylint
    "TRY",    # tryceratops
    "RUF",    # ruff-specific rules
]

# Ignore specific rules that conflict with project style or cause false positives
ignore = [
    "S101",   # Use of assert (common in tests)
    "S104",   # Possible binding to all interfaces
    "S105",   # Possible hardcoded password (handled by GitLeaks)
    "S106",   # Possible hardcoded password (handled by GitLeaks)
    "S107",   # Possible hardcoded password (handled by GitLeaks)
    "TRY003", # Avoid specifying long messages outside exception class
    "PLR0913", # Too many arguments
    "PLR2004", # Magic value used in comparison
]

# Exclude directories
exclude = [
    ".venv",
    "venv",
    "__pycache__",
    ".git",
    "alembic/versions",
    "build",
    "dist",
]

# Allow autofix for all enabled rules
fixable = ["ALL"]
unfixable = []

# Allow unused variables when underscore-prefixed
dummy-variable-rgx = "^(_+|(_+[a-zA-Z0-9_]*[a-zA-Z0-9]+?))$"

[lint.per-file-ignores]
# Ignore certain rules in test files
"tests/**/*.py" = [
    "S101",   # assert usage
    "PLR2004", # magic values
    "S105",   # hardcoded passwords in tests
    "S106",
]

# Ignore import rules in __init__.py
"__init__.py" = ["F401", "F403"]

[lint.isort]
known-first-party = ["telegram_bot"]
force-single-line = false
lines-after-imports = 2

[lint.mccabe]
max-complexity = 10

[format]
quote-style = "double"
indent-style = "space"
skip-magic-trailing-comma = false
line-ending = "auto"
```

**Security Rules Enabled (S-prefix)**:
- **S102**: exec usage
- **S103**: Bad file permissions
- **S108**: Hardcoded temp file
- **S110**: try-except-pass
- **S112**: try-except-continue
- **S113**: Request without timeout
- **S301-S324**: Various security issues (pickle, yaml.load, etc.)
- **S501-S508**: SSL/TLS issues
- **S601-S612**: Shell injection and subprocess issues
- **S701**: jinja2 autoescape

**Integration with Bandit**:
- Ruff's S-rules are based on Bandit but run faster
- Keep Bandit for deeper AST analysis and additional checks
- Ruff provides quick feedback, Bandit provides comprehensive analysis
- No conflicts - they complement each other

### 5. Safety Configuration

**Purpose**: Scan Python dependencies for known vulnerabilities using PyUp.io Safety DB.

**Implementation Approach**:
- **No Configuration File**: Safety uses command-line arguments
- **Scan Targets**: requirements.txt and pyproject.toml
- **Severity Threshold**: Fail on HIGH and CRITICAL vulnerabilities
- **Ignore File**: .safety-policy.yml for documented exceptions

**Pre-commit Hook Configuration**:
```yaml
- repo: local
  hooks:
    - id: safety
      name: Safety - Dependency Vulnerability Scanner
      entry: safety check --json --file
      language: system
      files: ^(requirements\.txt|pyproject\.toml)$
      pass_filenames: true
```

**Ignore Policy (.safety-policy.yml)**:
```yaml
security:
  ignore-vulnerabilities:
    # Example: Ignore specific CVE with justification
    # 51668:
    #   reason: "False positive - not using affected feature"
    #   expires: "2024-12-31"
```

### 6. Semgrep Configuration (.semgrep.yml)

**Purpose**: Advanced pattern matching for custom security rules and OWASP Top 10 detection.

**Ruleset Strategy**:
```yaml
rules:
  # Use community rulesets
  - id: python-security
    patterns:
      - pattern: eval(...)
      - pattern: exec(...)
    message: "Dangerous use of eval/exec"
    severity: ERROR
    
  # Custom rules for Telegram bot
  - id: telegram-token-exposure
    patterns:
      - pattern: |
          logging.$METHOD(..., $TOKEN, ...)
      - metavariable-regex:
          metavariable: $TOKEN
          regex: ".*token.*"
    message: "Potential token exposure in logs"
    severity: WARNING
    
  # SQL injection detection
  - id: sql-injection-risk
    patterns:
      - pattern: |
          $CONN.execute(f"... {$VAR} ...")
    message: "Potential SQL injection via f-string"
    severity: ERROR
```

**Ruleset Sources**:
- **p/owasp-top-ten**: OWASP Top 10 vulnerabilities
- **p/python**: Python-specific security issues
- **p/security-audit**: General security audit rules
- **Custom Rules**: Project-specific patterns

**Performance Optimization**:
```yaml
# Exclude patterns for performance
exclude:
  - "*.pyc"
  - "__pycache__"
  - ".venv"
  - "tests/fixtures"
  - "alembic/versions"

# Limit to Python files
paths:
  include:
    - "*.py"
```

### 7. Documentation Structure

**Purpose**: Provide comprehensive documentation for the security configuration, tool usage, and troubleshooting.

**Documentation Location**: `/docs/security/`

**Required Documentation Files**:

1. **docs/security/pre-commit-setup.md**
   - Overview of the security configuration
   - Installation instructions
   - Quick start guide
   - Architecture overview with references to configuration files

2. **docs/security/tool-reference.md**
   - Detailed documentation for each security tool
   - Command reference for running tools individually
   - Configuration options and customization
   - Examples of common security issues detected

3. **docs/security/troubleshooting.md**
   - Common issues and solutions
   - Performance optimization tips
   - How to handle false positives
   - Emergency bypass procedures

4. **docs/security/ci-integration.md**
   - GitHub Actions integration
   - GitLab CI integration
   - Other CI/CD platform examples

**Tool Command Reference (to be included in tool-reference.md)**:

```bash
# Ruff - Fast Python linting and formatting
ruff check .                    # Lint all Python files
ruff check . --fix              # Lint and auto-fix issues
ruff format .                   # Format all Python files
ruff check --select S .         # Run only security rules

# GitLeaks - Secrets detection
gitleaks detect --no-git        # Scan all files for secrets
gitleaks detect --config .gitleaks.toml --no-git  # With custom config
gitleaks protect --staged       # Scan only staged files

# Bandit - Python security linter
bandit -r telegram_bot/         # Scan directory recursively
bandit -c .bandit -r .          # Use custom config
bandit -ll -r .                 # Show only medium+ severity
bandit -f json -o report.json -r .  # JSON output

# Safety - Dependency vulnerability scanner
safety check                    # Scan installed packages
safety check --file requirements.txt  # Scan requirements file
safety check --json             # JSON output
safety check --ignore 51668     # Ignore specific CVE

# Semgrep - Pattern-based security analysis
semgrep --config .semgrep.yml telegram_bot/  # Custom config
semgrep --config "p/owasp-top-ten" .         # OWASP ruleset
semgrep --config "p/python" .                # Python ruleset
semgrep --json -o report.json .              # JSON output

# Pre-commit - Run all hooks
pre-commit run --all-files      # Run on all files
pre-commit run --files file.py  # Run on specific file
pre-commit run ruff             # Run specific hook
pre-commit run --hook-stage manual  # Run manual hooks
pre-commit clean                # Clear cache
pre-commit autoupdate           # Update hook versions
```

**Integration with Main Documentation**:
- Add reference in main README.md under "Security" section
- Link to docs/security/pre-commit-setup.md from CONTRIBUTING.md
- Include security checklist in pull request template

### 8. IDE Integration

**Purpose**: Provide real-time security feedback within VS Code and Kiro IDE.

**VS Code Settings (.vscode/settings.json)**:
```json
{
  "python.linting.enabled": true,
  "python.linting.banditEnabled": true,
  "python.linting.banditArgs": [
    "--configfile", ".bandit"
  ],
  
  "[python]": {
    "editor.defaultFormatter": "charliermarsh.ruff",
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.fixAll": true,
      "source.organizeImports": true
    }
  },
  
  "ruff.lint.enable": true,
  
  "files.associations": {
    ".gitleaks.toml": "toml",
    ".bandit": "yaml",
    ".semgrep.yml": "yaml",
    "ruff.toml": "toml"
  }
}
```

**VS Code Tasks (.vscode/tasks.json)**:
```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "Run Security Scan",
      "type": "shell",
      "command": "pre-commit run --all-files",
      "problemMatcher": [],
      "group": {
        "kind": "test",
        "isDefault": true
      }
    },
    {
      "label": "Run Ruff Lint",
      "type": "shell",
      "command": "ruff check . --fix",
      "problemMatcher": []
    },
    {
      "label": "Run Ruff Format",
      "type": "shell",
      "command": "ruff format .",
      "problemMatcher": []
    },
    {
      "label": "Run GitLeaks",
      "type": "shell",
      "command": "pre-commit run gitleaks --all-files"
    },
    {
      "label": "Run Bandit",
      "type": "shell",
      "command": "pre-commit run bandit --all-files"
    },
    {
      "label": "Run Safety",
      "type": "shell",
      "command": "pre-commit run safety --all-files"
    }
  ]
}
```

## Data Models

### Security Finding Model

Each security tool produces findings that are normalized into a common structure:

```python
@dataclass
class SecurityFinding:
    """Normalized security finding from any tool"""
    tool: str  # "gitleaks", "bandit", "safety", "semgrep"
    severity: str  # "CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"
    rule_id: str  # Tool-specific rule identifier
    message: str  # Human-readable description
    file_path: str  # Relative path to affected file
    line_number: Optional[int]  # Line number if applicable
    code_snippet: Optional[str]  # Relevant code context
    remediation: Optional[str]  # Fix suggestion
    cve_id: Optional[str]  # CVE identifier for vulnerabilities
    confidence: Optional[str]  # "HIGH", "MEDIUM", "LOW"
```

### Configuration Model

```python
@dataclass
class SecurityConfig:
    """Security configuration settings"""
    enable_gitleaks: bool = True
    enable_bandit: bool = True
    enable_safety: bool = True
    enable_semgrep: bool = True
    
    parallel_execution: bool = True
    fail_on_severity: str = "HIGH"  # Minimum severity to block commit
    
    bandit_severity: str = "medium"
    bandit_confidence: str = "medium"
    
    safety_ignore_ids: List[str] = field(default_factory=list)
    
    semgrep_rulesets: List[str] = field(default_factory=lambda: [
        "p/owasp-top-ten",
        "p/python",
        "p/security-audit"
    ])
```

## Error Handling

### Error Categories and Responses

1. **Tool Installation Errors**
   - **Cause**: Missing dependencies, network issues, incompatible versions
   - **Detection**: Installation script validates each tool
   - **Response**: Clear error message with installation instructions
   - **Fallback**: Continue with available tools, warn about missing coverage

2. **Configuration Errors**
   - **Cause**: Invalid YAML/TOML syntax, missing required fields
   - **Detection**: Pre-commit validates configuration on first run
   - **Response**: Syntax error with line number and expected format
   - **Fallback**: Use default configuration with warning

3. **Scan Execution Errors**
   - **Cause**: Tool crashes, timeout, resource exhaustion
   - **Detection**: Non-zero exit code from tool
   - **Response**: Log full error output, suggest troubleshooting steps
   - **Fallback**: Mark hook as failed but allow manual override

4. **False Positive Handling**
   - **Cause**: Legitimate code flagged as vulnerable
   - **Detection**: Developer review of findings
   - **Response**: Add to tool-specific ignore list with justification
   - **Fallback**: Use inline comments to suppress specific findings

### Error Recovery Strategies

```python
# Pseudo-code for error handling in installation script
def install_security_tools():
    results = {
        "gitleaks": False,
        "bandit": False,
        "safety": False,
        "semgrep": False,
        "pre-commit": False
    }
    
    for tool in results.keys():
        try:
            install_tool(tool)
            validate_tool(tool)
            results[tool] = True
        except InstallationError as e:
            log_error(f"Failed to install {tool}: {e}")
            log_warning(f"Continuing without {tool}")
            continue
    
    if not results["pre-commit"]:
        raise CriticalError("Pre-commit framework is required")
    
    if sum(results.values()) < 3:
        log_warning("Less than 3 security tools installed")
        prompt_user_continue()
    
    return results
```

## Testing Strategy

### 1. Installation Testing

**Objective**: Verify all tools install correctly across different environments.

**Test Cases**:
- Fresh Python 3.12+ environments (3.12, 3.13)
- Windows, macOS, Linux platforms
- With and without existing pre-commit installation
- Network failure scenarios (cached vs. fresh install)

**Validation**:
```bash
# Verify each tool is accessible
ruff --version
gitleaks version
bandit --version
safety --version
semgrep --version
pre-commit --version

# Verify pre-commit hooks are installed
pre-commit install --install-hooks
```

### 2. Configuration Testing

**Objective**: Ensure all configuration files are valid and tools respect settings.

**Test Cases**:
- Valid YAML/TOML syntax for all config files
- GitLeaks detects secrets in test files
- Bandit respects exclusion patterns
- Safety ignores specified vulnerabilities
- Semgrep runs only on Python files

**Validation**:
```bash
# Test configuration syntax
pre-commit validate-config
yamllint .pre-commit-config.yaml
toml-sort --check .gitleaks.toml

# Test individual tools with config
ruff check telegram_bot/
ruff format --check telegram_bot/
gitleaks detect --config .gitleaks.toml --no-git
bandit -c .bandit -r telegram_bot/
safety check --file requirements.txt
semgrep --config .semgrep.yml telegram_bot/
```

### 3. Detection Testing

**Objective**: Verify each tool correctly identifies security issues.

**Test Files**:

**tests/security/test_secrets.py** (should be detected by GitLeaks):
```python
# This file intentionally contains test secrets for validation
TELEGRAM_TOKEN = "123456789:ABCdefGHIjklMNOpqrsTUVwxyz1234567890"
OPENAI_KEY = "sk-1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKL"
DATABASE_URL = "postgresql://user:password123@localhost/db"
```

**tests/security/test_vulnerabilities.py** (should be detected by Bandit):
```python
import pickle
import subprocess

# SQL Injection
def unsafe_query(user_input):
    query = f"SELECT * FROM users WHERE id = {user_input}"
    return query

# Command Injection
def unsafe_command(filename):
    subprocess.call(f"cat {filename}", shell=True)

# Insecure Deserialization
def unsafe_pickle(data):
    return pickle.loads(data)

# Weak Cryptography
import hashlib
def weak_hash(password):
    return hashlib.md5(password.encode()).hexdigest()
```

**Validation**:
```bash
# Run pre-commit on test files
pre-commit run --files tests/security/test_secrets.py
# Expected: GitLeaks should detect 3 secrets

pre-commit run --files tests/security/test_vulnerabilities.py
# Expected: Bandit should detect 4+ issues
```

### 4. Performance Testing

**Objective**: Ensure hooks complete within acceptable time limits.

**Environment Requirements**:
- Python 3.12 or higher
- Git 2.30 or higher
- 4GB RAM minimum, 8GB recommended
- Multi-core CPU for parallel execution

**Benchmarks**:
- Single file commit: < 5 seconds
- 10 file commit: < 15 seconds
- 50 file commit: < 45 seconds
- Full repository scan: < 2 minutes

**Test Methodology**:
```bash
# Measure hook execution time
time pre-commit run --files telegram_bot/main.py

# Measure parallel vs. sequential
time pre-commit run --all-files  # parallel
time pre-commit run --all-files --show-diff-on-failure  # sequential

# Profile individual tools
time ruff check telegram_bot/
time gitleaks detect --no-git
time bandit -r telegram_bot/
time safety check --file requirements.txt
time semgrep --config .semgrep.yml telegram_bot/
```

### 5. Integration Testing

**Objective**: Verify hooks work correctly in real git workflow.

**Test Scenarios**:
1. **Normal Commit**: Clean code should pass all hooks
2. **Blocked Commit**: Code with secrets should be blocked
3. **Bypass Commit**: `git commit --no-verify` should skip hooks
4. **Partial Staging**: Only staged files should be scanned
5. **CI Integration**: Hooks should work in GitHub Actions

**Validation**:
```bash
# Test normal commit
echo "print('hello')" > test.py
git add test.py
git commit -m "test"  # Should succeed

# Test blocked commit
echo "API_KEY = 'sk-1234567890abcdef'" > test.py
git add test.py
git commit -m "test"  # Should fail

# Test bypass
git commit -m "test" --no-verify  # Should succeed

# Test partial staging
echo "safe code" > file1.py
echo "API_KEY = 'secret'" > file2.py
git add file1.py
git commit -m "test"  # Should succeed (file2.py not staged)
```

### 6. False Positive Testing

**Objective**: Minimize false positives through proper configuration.

**Common False Positives**:
- Example credentials in .env.example
- Test fixtures with mock data
- Documentation with example code
- Comments explaining security issues

**Mitigation Strategy**:
```toml
# .gitleaks.toml
[allowlist]
paths = [
  ".env.example",
  "tests/fixtures/",
  "docs/examples/"
]

regexes = [
  "your_.*_key",
  "example\\.com",
  "test_.*_token"
]
```

## Performance Optimization

### 1. Parallel Execution

**Strategy**: Run independent hooks concurrently to reduce total execution time.

**Implementation**:
```yaml
# .pre-commit-config.yaml
default_stages: [commit]
fail_fast: false  # Run all hooks even if one fails

repos:
  # These hooks can run in parallel
  - repo: https://github.com/gitleaks/gitleaks
    hooks:
      - id: gitleaks
        stages: [commit]
  
  - repo: https://github.com/PyCQA/bandit
    hooks:
      - id: bandit
        stages: [commit]
```

**Expected Improvement**: 40-60% reduction in total execution time for multi-file commits.

### 2. File Filtering

**Strategy**: Each hook only processes relevant file types.

**Implementation**:
```yaml
- id: bandit
  files: \.py$  # Only Python files
  exclude: ^tests/|^alembic/versions/

- id: safety
  files: ^(requirements\.txt|pyproject\.toml)$  # Only dependency files

- id: gitleaks
  exclude: ^\.venv/|^__pycache__/  # Skip generated directories
```

**Expected Improvement**: 30-50% reduction in scan time by avoiding irrelevant files.

### 3. Caching Strategy

**Strategy**: Pre-commit framework caches tool installations and results.

**Cache Locations**:
- Tool binaries: `~/.cache/pre-commit/`
- Hook results: `.git/hooks/pre-commit` (git staging area)

**Cache Invalidation**:
- Tool version changes (rev in .pre-commit-config.yaml)
- Configuration file changes
- Manual: `pre-commit clean`

**Expected Improvement**: 80-90% faster on subsequent runs with unchanged files.

### 4. Incremental Scanning

**Strategy**: Only scan files changed in current commit, not entire repository.

**Implementation**:
```bash
# Pre-commit automatically scans only staged files
git add file1.py file2.py
git commit  # Only scans file1.py and file2.py

# For full repository scan (CI or manual)
pre-commit run --all-files
```

**Expected Improvement**: 95%+ reduction in scan time for typical commits (1-5 files).

### 5. Resource Limits

**Strategy**: Prevent tools from consuming excessive resources.

**Implementation**:
```yaml
# .pre-commit-config.yaml
- id: semgrep
  args: ['--config', '.semgrep.yml', '--timeout', '30', '--max-memory', '2048']
```

**Timeout Configuration**:
- GitLeaks: 30 seconds
- Bandit: 60 seconds
- Safety: 30 seconds
- Semgrep: 60 seconds
- Total hook timeout: 120 seconds

## Security Considerations

### 1. Tool Supply Chain Security

**Risk**: Malicious code in security tools or dependencies.

**Mitigation**:
- Pin exact versions in .pre-commit-config.yaml
- Use official repositories only
- Verify tool signatures when available
- Regular security audits of tool dependencies

### 2. Sensitive Data in Logs

**Risk**: Security tools may log sensitive data found during scans.

**Mitigation**:
- GitLeaks redacts secret values in output
- Configure tools to output findings without full content
- Avoid committing pre-commit logs
- Use `--quiet` mode in CI environments

### 3. Configuration File Security

**Risk**: Attackers could modify configuration to disable checks.

**Mitigation**:
- Include configuration files in code review
- Use branch protection to require reviews
- Monitor changes to .pre-commit-config.yaml
- Validate configuration in CI

### 4. Bypass Prevention

**Risk**: Developers bypassing hooks with --no-verify.

**Mitigation**:
- Run same checks in CI (mandatory)
- Educate team on security importance
- Monitor git logs for --no-verify usage
- Require CI passing for merge

## Deployment Strategy

### Phase 1: Installation and Setup (Week 1)

1. Install pre-commit framework
2. Create .pre-commit-config.yaml with all tools
3. Install git hooks
4. Validate installation

### Phase 2: Configuration (Week 1-2)

1. Create tool-specific configuration files
2. Test on existing codebase
3. Tune rules to minimize false positives
4. Document exceptions and allowlists

### Phase 3: IDE Integration (Week 2)

1. Create VS Code settings and tasks
2. Configure Bandit for real-time linting
3. Test IDE integration
4. Document IDE setup for team

### Phase 4: Documentation (Week 2-3)

1. Create `/docs/security/` directory structure
2. Write `docs/security/pre-commit-setup.md` with installation and quick start
3. Write `docs/security/tool-reference.md` with command reference and examples
4. Write `docs/security/troubleshooting.md` with common issues and solutions
5. Write `docs/security/ci-integration.md` with CI/CD examples
6. Update main `README.md` with security section linking to documentation
7. Update `CONTRIBUTING.md` with pre-commit requirements
8. Add security checklist to pull request template

### Phase 5: Team Rollout (Week 3-4)

1. Announce security configuration to team
2. Provide training on using hooks
3. Monitor for issues and feedback
4. Iterate on configuration based on feedback

### Phase 6: CI Integration (Week 4)

1. Add pre-commit to CI pipeline
2. Configure to run on all files
3. Set up failure notifications
4. Enforce passing checks for merges

## Maintenance Plan

### Regular Updates

- **Monthly**: Update tool versions in .pre-commit-config.yaml to latest stable releases
- **Quarterly**: Review and update custom rules
- **Annually**: Audit entire security configuration

### Version Management Strategy

- **Initial Setup**: Use latest stable versions of all tools at time of implementation
- **Version Pinning**: Pin to specific versions (not version ranges) for reproducibility
- **Update Process**: Test new versions in development before updating team-wide
- **Security Patches**: Apply critical security updates immediately
- **Breaking Changes**: Review release notes before major version updates

### Monitoring

- Track false positive rate
- Monitor hook execution time
- Review bypassed commits
- Analyze security findings trends

### Continuous Improvement

- Add new rules based on discovered vulnerabilities
- Optimize performance based on metrics
- Update documentation based on team feedback
- Integrate new security tools as they emerge
