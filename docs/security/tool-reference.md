# Security Tools Reference

This document provides detailed information about each security tool integrated into the pre-commit configuration, including command references, configuration options, and examples of common security issues detected.

## Table of Contents

- [Ruff](#ruff)
- [GitLeaks](#gitleaks)
- [Bandit](#bandit)
- [Safety](#safety)
- [Semgrep](#semgrep)

---

## Ruff

### Overview

Ruff is an extremely fast Python linter and formatter written in Rust. It replaces multiple tools (flake8, pylint, isort, pyupgrade, and more) with a single, high-performance solution. Ruff includes security-focused rules based on Bandit patterns.

**Performance**: 10-100x faster than traditional Python linters  
**Language**: Python  
**Primary Use**: Code quality, formatting, import sorting, security patterns

### Command Reference

```bash
# Lint all Python files
ruff check .

# Lint with auto-fix
ruff check . --fix

# Format all Python files
ruff format .

# Check formatting without modifying files
ruff format --check .

# Run only security rules (S-prefix)
ruff check --select S .

# Show all available rules
ruff rule --all

# Lint specific files
ruff check telegram_bot/main.py telegram_bot/services/

# Output in different formats
ruff check . --output-format=json
ruff check . --output-format=github  # For GitHub Actions

# Show statistics
ruff check . --statistics

# Ignore specific rules
ruff check . --ignore E501,F401
```

### Configuration

Configuration is in `ruff.toml` (or `pyproject.toml` under `[tool.ruff]`).

**Key Configuration Options**:

```toml
# Target Python version
target-version = "py312"

# Line length for formatting
line-length = 100

# Indentation width
indent-width = 4

[lint]
# Enable rule sets
select = [
    "E",      # pycodestyle errors
    "W",      # pycodestyle warnings
    "F",      # pyflakes
    "I",      # isort (import sorting)
    "S",      # flake8-bandit (security)
    "B",      # flake8-bugbear
    "C4",     # flake8-comprehensions
    "UP",     # pyupgrade
]

# Ignore specific rules
ignore = [
    "S101",   # Use of assert (common in tests)
    "S105",   # Possible hardcoded password
]

# Exclude directories
exclude = [
    ".venv",
    "__pycache__",
    "alembic/versions",
]

# Allow autofix for all rules
fixable = ["ALL"]

[lint.per-file-ignores]
# Ignore rules in specific files
"tests/**/*.py" = ["S101", "PLR2004"]
"__init__.py" = ["F401"]

[lint.isort]
# Import sorting configuration
known-first-party = ["telegram_bot"]
force-single-line = false

[format]
# Formatting options
quote-style = "double"
indent-style = "space"
```

### Common Security Issues Detected

#### 1. Hardcoded Passwords (S105, S106, S107)

```python
# ❌ Bad
password = "admin123"
api_key = "sk-1234567890"

# ✅ Good
password = os.getenv("PASSWORD")
api_key = os.getenv("API_KEY")
```

#### 2. Use of exec/eval (S102, S307)

```python
# ❌ Bad
user_input = request.get("code")
exec(user_input)

# ✅ Good
# Avoid exec/eval entirely or use ast.literal_eval for safe evaluation
import ast
data = ast.literal_eval(user_input)
```

#### 3. Insecure Random (S311)

```python
# ❌ Bad
import random
token = random.randint(1000, 9999)

# ✅ Good
import secrets
token = secrets.randbelow(9000) + 1000
```

#### 4. Request Without Timeout (S113)

```python
# ❌ Bad
response = requests.get("https://api.example.com")

# ✅ Good
response = requests.get("https://api.example.com", timeout=30)
```

### Suppressing False Positives

```python
# Suppress specific rule for one line
api_key = get_from_vault()  # noqa: S105

# Suppress multiple rules
result = eval(safe_expression)  # noqa: S307, S102

# Suppress for entire file (add to top of file)
# ruff: noqa: S101
```

---

## GitLeaks

### Overview

GitLeaks is a SAST tool for detecting and preventing hardcoded secrets like passwords, API keys, and tokens in git repositories. It uses regex patterns to identify over 100 types of secrets.

**Performance**: Fast, typically 2-5 seconds for full repository scan  
**Language**: All file types  
**Primary Use**: Secrets detection, credential scanning

### Command Reference

```bash
# Detect secrets in entire repository
gitleaks detect --no-git

# Detect with custom configuration
gitleaks detect --config .gitleaks.toml --no-git

# Scan only staged files (pre-commit mode)
gitleaks protect --staged

# Scan specific directory
gitleaks detect --source telegram_bot/ --no-git

# Output in different formats
gitleaks detect --report-format json --report-path report.json --no-git
gitleaks detect --report-format sarif --report-path report.sarif --no-git

# Verbose output
gitleaks detect --verbose --no-git

# Scan git history (slower)
gitleaks detect

# Baseline scan (create baseline to ignore existing secrets)
gitleaks detect --baseline-path .gitleaks-baseline.json --no-git
```

### Configuration

Configuration is in `.gitleaks.toml`.

**Key Configuration Options**:

```toml
# Custom rule for Telegram bot tokens
[[rules]]
id = "telegram-bot-token"
description = "Telegram Bot API Token"
regex = '''[0-9]{8,10}:[a-zA-Z0-9_-]{35}'''
keywords = ["TELEGRAM_TOKEN", "BOT_TOKEN"]

# Custom rule for OpenAI API keys
[[rules]]
id = "openai-api-key"
description = "OpenAI API Key"
regex = '''sk-[a-zA-Z0-9]{48}'''
keywords = ["OPENAI_API_KEY"]

# Custom rule for OpenRouter API keys
[[rules]]
id = "openrouter-api-key"
description = "OpenRouter API Key"
regex = '''sk-or-v1-[a-zA-Z0-9]{64}'''
keywords = ["OPENROUTER_API_KEY"]

# Allowlist for false positives
[allowlist]
description = "Allowlisted files and patterns"

# Exclude specific files
paths = [
  ".env.example",
  "docs/",
  "tests/fixtures/",
  ".kiro/specs/"
]

# Exclude specific patterns
regexes = [
  "your_.*_token",      # Placeholder values
  "example\\.com",
  "localhost",
  "127\\.0\\.0\\.1"
]

# Exclude specific commits (by hash)
commits = []

# Path exclusions (regex)
[allowlist.paths]
regex = '''(\.env\.example|test_.*\.py|.*_test\.py)'''
```

### Common Security Issues Detected

#### 1. Telegram Bot Tokens

```python
# ❌ Bad - Hardcoded token
TELEGRAM_TOKEN = "123456789:ABCdefGHIjklMNOpqrsTUVwxyz1234567890"

# ✅ Good - Environment variable
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
```

#### 2. API Keys

```python
# ❌ Bad - Hardcoded API key
OPENAI_API_KEY = "sk-1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKL"

# ✅ Good - Environment variable
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
```

#### 3. Database Credentials

```python
# ❌ Bad - Connection string with password
DATABASE_URL = "postgresql://user:password123@localhost/db"

# ✅ Good - Environment variable
DATABASE_URL = os.getenv("DATABASE_URL")
```

#### 4. Private Keys

```
# ❌ Bad - Hardcoded private key in code
-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEA...
-----END RSA PRIVATE KEY-----

# ✅ Good - Load from secure file or environment
with open(os.getenv("PRIVATE_KEY_PATH")) as f:
    private_key = f.read()
```

### Suppressing False Positives

Add to `.gitleaks.toml`:

```toml
[allowlist]
paths = [
  "path/to/file.py",  # Ignore entire file
]

regexes = [
  "specific_pattern_to_ignore",
]
```

---

## Bandit

### Overview

Bandit is a security linter designed to find common security issues in Python code. It performs Abstract Syntax Tree (AST) analysis to identify vulnerabilities like SQL injection, command injection, and insecure cryptography.

**Performance**: Typically 3-8 seconds for medium-sized projects  
**Language**: Python  
**Primary Use**: Python SAST, vulnerability detection

### Command Reference

```bash
# Scan directory recursively
bandit -r telegram_bot/

# Use custom configuration
bandit -c .bandit -r .

# Show only medium+ severity
bandit -ll -r .

# Show only high confidence
bandit -ii -r .

# Output formats
bandit -f json -o report.json -r .
bandit -f csv -o report.csv -r .
bandit -f html -o report.html -r .

# Scan specific files
bandit telegram_bot/main.py telegram_bot/services/ai_service.py

# Show all available tests
bandit -h

# Verbose output
bandit -v -r .

# Exclude directories
bandit -r . -x ./tests,./alembic

# Skip specific tests
bandit -r . -s B101,B601
```

### Configuration

Configuration is in `.bandit` (YAML format).

**Key Configuration Options**:

```yaml
# Exclude directories
exclude_dirs:
  - /tests/
  - /alembic/versions/
  - /.venv/
  - /__pycache__/

# Skip specific tests
skips:
  - B101  # assert_used (common in tests)
  - B601  # paramiko_calls (not used in project)

# Include specific tests (if not using default)
tests:
  - B201  # flask_debug_true
  - B301  # pickle usage
  - B302  # marshal usage
  - B303  # insecure MD5/SHA1
  - B304  # insecure cipher modes
  - B305  # insecure cipher usage
  - B307  # eval usage
  - B308  # mark_safe usage
  - B311  # random for crypto
  - B312  # telnetlib usage
  - B313  # xml parsing vulnerabilities
  - B320  # lxml
  - B323  # unverified SSL context
  - B324  # hashlib with insecure algorithms
  - B501  # request_with_no_cert_validation
  - B502  # ssl_with_bad_version
  - B506  # yaml_load
  - B602  # shell_injection
  - B603  # subprocess_without_shell_equals_true
  - B608  # hardcoded_sql_expressions
  - B609  # linux_commands_wildcard_injection

# Severity threshold
severity: medium

# Confidence threshold
confidence: medium
```

### Common Security Issues Detected

#### 1. SQL Injection (B608)

```python
# ❌ Bad - String formatting in SQL
user_id = request.get("id")
query = f"SELECT * FROM users WHERE id = {user_id}"
cursor.execute(query)

# ✅ Good - Parameterized query
user_id = request.get("id")
query = "SELECT * FROM users WHERE id = %s"
cursor.execute(query, (user_id,))
```

#### 2. Command Injection (B602, B603, B605)

```python
# ❌ Bad - Shell injection risk
filename = request.get("file")
os.system(f"cat {filename}")

# ✅ Good - Use subprocess with list
import subprocess
filename = request.get("file")
subprocess.run(["cat", filename], check=True)
```

#### 3. Insecure Deserialization (B301)

```python
# ❌ Bad - Pickle is unsafe
import pickle
data = pickle.loads(user_input)

# ✅ Good - Use JSON for untrusted data
import json
data = json.loads(user_input)
```

#### 4. Weak Cryptography (B303, B324)

```python
# ❌ Bad - MD5 is cryptographically broken
import hashlib
password_hash = hashlib.md5(password.encode()).hexdigest()

# ✅ Good - Use strong hashing
from argon2 import PasswordHasher
ph = PasswordHasher()
password_hash = ph.hash(password)
```

#### 5. Insecure Random (B311)

```python
# ❌ Bad - random module is not cryptographically secure
import random
session_token = random.randint(100000, 999999)

# ✅ Good - Use secrets module
import secrets
session_token = secrets.randbelow(900000) + 100000
```

#### 6. YAML Load (B506)

```python
# ❌ Bad - yaml.load is unsafe
import yaml
config = yaml.load(file_content)

# ✅ Good - Use safe_load
import yaml
config = yaml.safe_load(file_content)
```

### Suppressing False Positives

```python
# Suppress for one line
result = eval(safe_expression)  # nosec B307

# Suppress with comment explaining why
api_key = get_from_vault()  # nosec B105 - Retrieved from secure vault

# Suppress multiple issues
subprocess.call(command, shell=True)  # nosec B602, B603
```

---

## Safety

### Overview

Safety checks Python dependencies for known security vulnerabilities using the PyUp.io Safety DB. It identifies packages with CVEs and provides remediation guidance.

**Performance**: Typically 2-4 seconds  
**Language**: Python (dependencies)  
**Primary Use**: Dependency vulnerability scanning

### Command Reference

```bash
# Check installed packages
safety check

# Check requirements file
safety check --file requirements.txt

# Check with JSON output
safety check --json

# Check with full report
safety check --full-report

# Ignore specific vulnerabilities
safety check --ignore 51668

# Check with specific database
safety check --db /path/to/safety-db.json

# Check and save report
safety check --output json --file requirements.txt > safety-report.json

# Check with exit code 0 even if vulnerabilities found (for CI)
safety check --continue-on-error
```

### Configuration

Configuration is in `.safety-policy.yml`.

**Key Configuration Options**:

```yaml
security:
  # Ignore specific vulnerabilities with justification
  ignore-vulnerabilities:
    # Example: CVE ID
    51668:
      reason: "False positive - not using affected feature"
      expires: "2024-12-31"
    
    42194:
      reason: "Waiting for upstream fix, mitigated by firewall rules"
      expires: "2025-01-15"

  # Continue on error (don't fail build)
  continue-on-error: false

  # Ignore unpinned requirements
  ignore-unpinned-requirements: false
```

### Common Security Issues Detected

#### 1. Known CVEs in Dependencies

```
# Example output
+==============================================================================+
|                                                                              |
|                               /$$$$$$            /$$                         |
|                              /$$__  $$          | $$                         |
|           /$$$$$$$  /$$$$$$ | $$  \__//$$$$$$  /$$$$$$   /$$   /$$           |
|          /$$_____/ |____  $$| $$$$   /$$__  $$|_  $$_/  | $$  | $$           |
|         |  $$$$$$   /$$$$$$$| $$_/  | $$$$$$$$  | $$    | $$  | $$           |
|          \____  $$ /$$__  $$| $$    | $$_____/  | $$ /$$| $$  | $$           |
|          /$$$$$$$/|  $$$$$$$| $$    |  $$$$$$$  |  $$$$/|  $$$$$$$           |
|         |_______/  \_______/|__/     \_______/   \___/   \____  $$           |
|                                                            /$$  | $$           |
|                                                           |  $$$$$$/           |
|  by pyup.io                                                \______/            |
|                                                                              |
+==============================================================================+

 REPORT 

  Safety is using PyUp's free open-source vulnerability database.

+==============================================================================+
| PACKAGE | INSTALLED | AFFECTED | ID    | CVE                | SEVERITY     |
+==============================================================================+
| urllib3 | 1.26.5    | <1.26.17 | 51668 | CVE-2023-43804     | HIGH         |
+==============================================================================+

 Recommendation: Update urllib3 to version 1.26.17 or later

+==============================================================================+
```

#### 2. Remediation

```bash
# Update specific package
pip install --upgrade urllib3==1.26.17

# Update requirements.txt
# Change: urllib3==1.26.5
# To: urllib3==1.26.17

# Verify fix
safety check --file requirements.txt
```

### Suppressing False Positives

Add to `.safety-policy.yml`:

```yaml
security:
  ignore-vulnerabilities:
    51668:
      reason: "Not using affected urllib3 feature (SOCKS proxy)"
      expires: "2025-12-31"
```

---

## Semgrep

### Overview

Semgrep is a fast, open-source static analysis tool that finds bugs and enforces code standards. It supports custom rules and includes security-focused rulesets for OWASP Top 10 and language-specific vulnerabilities.

**Performance**: Typically 5-10 seconds for medium-sized projects  
**Language**: Multi-language (Python, JavaScript, Go, Java, etc.)  
**Primary Use**: Pattern-based security analysis, custom rules

### Command Reference

```bash
# Scan with custom configuration
semgrep --config .semgrep.yml telegram_bot/

# Scan with community rulesets
semgrep --config "p/owasp-top-ten" .
semgrep --config "p/python" .
semgrep --config "p/security-audit" .

# Scan with multiple rulesets
semgrep --config "p/owasp-top-ten" --config "p/python" .

# Output formats
semgrep --json -o report.json .
semgrep --sarif -o report.sarif .
semgrep --junit-xml -o report.xml .

# Verbose output
semgrep --verbose .

# Dry run (show what would be scanned)
semgrep --dryrun .

# Show metrics
semgrep --metrics=on .

# Exclude paths
semgrep --exclude "tests/" --exclude ".venv/" .

# Set timeout
semgrep --timeout 30 .

# Set max memory
semgrep --max-memory 2048 .

# Auto-fix (experimental)
semgrep --autofix .
```

### Configuration

Configuration is in `.semgrep.yml`.

**Key Configuration Options**:

```yaml
rules:
  # Use community rulesets
  - id: python-security
    patterns:
      - pattern: eval(...)
      - pattern: exec(...)
    message: "Dangerous use of eval/exec"
    severity: ERROR
    languages: [python]
    
  # Custom rule for Telegram token exposure
  - id: telegram-token-exposure
    patterns:
      - pattern: |
          logging.$METHOD(..., $TOKEN, ...)
      - metavariable-regex:
          metavariable: $TOKEN
          regex: ".*token.*"
    message: "Potential token exposure in logs"
    severity: WARNING
    languages: [python]
    
  # SQL injection detection
  - id: sql-injection-risk
    patterns:
      - pattern: |
          $CONN.execute(f"... {$VAR} ...")
    message: "Potential SQL injection via f-string"
    severity: ERROR
    languages: [python]
    
  # Command injection
  - id: command-injection
    patterns:
      - pattern: subprocess.$METHOD($CMD, shell=True)
    message: "Command injection risk with shell=True"
    severity: ERROR
    languages: [python]

# Exclude patterns for performance
exclude:
  - "*.pyc"
  - "__pycache__"
  - ".venv"
  - "tests/fixtures"
  - "alembic/versions"

# Limit to specific file types
paths:
  include:
    - "*.py"
```

### Common Security Issues Detected

#### 1. SQL Injection via F-strings

```python
# ❌ Bad - F-string in SQL query
user_id = request.get("id")
query = f"SELECT * FROM users WHERE id = {user_id}"
conn.execute(query)

# ✅ Good - Parameterized query
user_id = request.get("id")
query = "SELECT * FROM users WHERE id = ?"
conn.execute(query, (user_id,))
```

#### 2. Token Exposure in Logs

```python
# ❌ Bad - Logging sensitive data
telegram_token = os.getenv("TELEGRAM_TOKEN")
logging.info(f"Using token: {telegram_token}")

# ✅ Good - Don't log sensitive data
telegram_token = os.getenv("TELEGRAM_TOKEN")
logging.info("Token loaded successfully")
```

#### 3. Command Injection

```python
# ❌ Bad - shell=True with user input
user_file = request.get("filename")
subprocess.run(f"cat {user_file}", shell=True)

# ✅ Good - Use list without shell
user_file = request.get("filename")
subprocess.run(["cat", user_file], check=True)
```

#### 4. Path Traversal

```python
# ❌ Bad - Unsanitized file path
filename = request.get("file")
with open(f"/data/{filename}") as f:
    content = f.read()

# ✅ Good - Validate and sanitize
import os
filename = os.path.basename(request.get("file"))
safe_path = os.path.join("/data", filename)
if not safe_path.startswith("/data/"):
    raise ValueError("Invalid path")
with open(safe_path) as f:
    content = f.read()
```

### Suppressing False Positives

```python
# Suppress with comment
result = eval(safe_expression)  # nosemgrep: python-security

# Suppress in configuration
# Add to .semgrep.yml:
# exclude:
#   - "path/to/file.py"
```

---

## Tool Comparison Matrix

| Feature | Ruff | GitLeaks | Bandit | Safety | Semgrep |
|---------|------|----------|--------|--------|---------|
| **Speed** | ⚡⚡⚡ Very Fast | ⚡⚡ Fast | ⚡⚡ Fast | ⚡⚡ Fast | ⚡ Moderate |
| **Language** | Python | All | Python | Python | Multi-language |
| **Auto-fix** | ✅ Yes | ❌ No | ❌ No | ❌ No | ⚠️ Experimental |
| **Custom Rules** | ⚠️ Limited | ✅ Yes | ⚠️ Limited | ❌ No | ✅ Yes |
| **IDE Integration** | ✅ Excellent | ⚠️ Limited | ✅ Good | ⚠️ Limited | ✅ Good |
| **False Positives** | Low | Low | Medium | Low | Low-Medium |
| **Learning Curve** | Low | Low | Low | Very Low | Medium |

## Best Practices

1. **Run tools individually during development** to get faster feedback
2. **Use IDE integration** for real-time security feedback
3. **Review all findings** - don't blindly suppress warnings
4. **Keep tools updated** - run `pre-commit autoupdate` monthly
5. **Document suppressions** - always add a comment explaining why
6. **Test in CI** - ensure the same checks run in your CI pipeline
7. **Educate team** - share this reference with all developers

## Additional Resources

- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [GitLeaks Documentation](https://github.com/gitleaks/gitleaks)
- [Bandit Documentation](https://bandit.readthedocs.io/)
- [Safety Documentation](https://pyup.io/safety/)
- [Semgrep Documentation](https://semgrep.dev/docs/)
- [Pre-commit Setup Guide](pre-commit-setup.md)
- [Troubleshooting Guide](troubleshooting.md)
- [CI Integration Guide](ci-integration.md)
