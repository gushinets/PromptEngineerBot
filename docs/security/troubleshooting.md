# Troubleshooting Guide

This guide provides solutions to common issues encountered when setting up and using the pre-commit security configuration.

## Table of Contents

- [Installation Issues](#installation-issues)
- [Hook Execution Issues](#hook-execution-issues)
- [Performance Issues](#performance-issues)
- [False Positives](#false-positives)
- [Tool-Specific Issues](#tool-specific-issues)
- [Emergency Bypass Procedures](#emergency-bypass-procedures)

---

## Installation Issues

### Pre-commit Not Found

**Symptom**: `pre-commit: command not found` or `'pre-commit' is not recognized`

**Cause**: Pre-commit framework is not installed or not in PATH

**Solution**:

```bash
# Install pre-commit
pip install pre-commit

# Verify installation
pre-commit --version

# If still not found, check if pip bin directory is in PATH
python -m pip show pre-commit

# On Windows, add to PATH:
# %USERPROFILE%\AppData\Local\Programs\Python\Python312\Scripts

# On macOS/Linux, add to PATH:
# export PATH="$HOME/.local/bin:$PATH"
```

### GitLeaks Binary Not Found

**Symptom**: `gitleaks: command not found` or hook fails with "executable not found"

**Cause**: GitLeaks binary is not installed or not in PATH

**Solution**:

**Windows**:
```powershell
# Download and install GitLeaks
$url = "https://github.com/gitleaks/gitleaks/releases/latest/download/gitleaks_windows_amd64.zip"
Invoke-WebRequest -Uri $url -OutFile "gitleaks.zip"
Expand-Archive -Path "gitleaks.zip" -DestinationPath "$env:USERPROFILE\bin"
# Add %USERPROFILE%\bin to PATH
```

**macOS**:
```bash
brew install gitleaks
```

**Linux**:
```bash
wget https://github.com/gitleaks/gitleaks/releases/latest/download/gitleaks_linux_amd64.tar.gz
tar -xzf gitleaks_linux_amd64.tar.gz
sudo mv gitleaks /usr/local/bin/
```

### Python Version Incompatibility

**Symptom**: `This package requires Python 3.12 or higher`

**Cause**: Using an older Python version

**Solution**:

```bash
# Check Python version
python --version

# If < 3.12, upgrade Python
# Windows: Download from python.org
# macOS: brew install python@3.12
# Linux: Use your package manager (apt, yum, etc.)

# Use specific Python version
python3.12 -m pip install pre-commit
```

### Permission Denied Errors

**Symptom**: `Permission denied` when installing tools or running hooks

**Cause**: Insufficient permissions or file ownership issues

**Solution**:

```bash
# On macOS/Linux, use --user flag
pip install --user pre-commit ruff bandit safety semgrep

# Or use virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install pre-commit ruff bandit safety semgrep

# Fix git hooks permissions
chmod +x .git/hooks/pre-commit
```

### Network/Proxy Issues

**Symptom**: `Connection timeout` or `Unable to download` during installation

**Cause**: Network restrictions or proxy configuration

**Solution**:

```bash
# Configure pip proxy
pip install --proxy http://proxy.example.com:8080 pre-commit

# Or set environment variables
export HTTP_PROXY=http://proxy.example.com:8080
export HTTPS_PROXY=http://proxy.example.com:8080

# For pre-commit tool downloads
export PRE_COMMIT_HOME=/path/to/cache
pre-commit install --install-hooks

# Use offline mode (if tools are cached)
pre-commit run --all-files --offline
```

---

## Hook Execution Issues

### Hooks Not Running on Commit

**Symptom**: Committing code without any security checks running

**Cause**: Git hooks not installed

**Solution**:

```bash
# Install hooks
pre-commit install

# Verify hooks are installed
ls -la .git/hooks/pre-commit

# Re-install if necessary
pre-commit uninstall
pre-commit install
```

### Hook Fails with "No module named 'X'"

**Symptom**: `ModuleNotFoundError: No module named 'ruff'` (or other tool)

**Cause**: Tool not installed in the correct Python environment

**Solution**:

```bash
# Install missing tool
pip install ruff bandit safety semgrep

# Or install all tools at once
pip install -r requirements.txt

# If using virtual environment, ensure it's activated
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Verify tools are installed
ruff --version
bandit --version
safety --version
semgrep --version
```

### Configuration File Syntax Errors

**Symptom**: `Error: Invalid configuration` or `YAML parse error`

**Cause**: Syntax error in configuration files

**Solution**:

```bash
# Validate pre-commit configuration
pre-commit validate-config

# Validate YAML files
python -c "import yaml; yaml.safe_load(open('.bandit'))"
python -c "import yaml; yaml.safe_load(open('.semgrep.yml'))"

# Validate TOML files
python -c "import tomli; tomli.load(open('.gitleaks.toml', 'rb'))"
python -c "import tomli; tomli.load(open('ruff.toml', 'rb'))"

# Common issues:
# - Incorrect indentation in YAML
# - Missing quotes around strings with special characters
# - Trailing commas in TOML arrays
```

### Hook Timeout

**Symptom**: Hook execution exceeds time limit and is killed

**Cause**: Large codebase or slow tool execution

**Solution**:

```bash
# Run on specific files only
pre-commit run --files path/to/changed/file.py

# Increase timeout in .pre-commit-config.yaml
# Add to hook configuration:
# args: ['--timeout', '60']

# Skip slow hooks temporarily
SKIP=semgrep git commit -m "message"

# Or disable specific hook
# Comment out in .pre-commit-config.yaml
```

---

## Performance Issues

### Slow Hook Execution

**Symptom**: Hooks take longer than 30 seconds for small commits

**Cause**: Various performance bottlenecks

**Solutions**:

#### 1. Enable Parallel Execution

Ensure `.pre-commit-config.yaml` doesn't have `fail_fast: true`:

```yaml
# .pre-commit-config.yaml
fail_fast: false  # Allow parallel execution
```

#### 2. Optimize File Filtering

Add file type filters to each hook:

```yaml
- id: bandit
  files: \.py$  # Only Python files
  exclude: ^tests/|^alembic/versions/
```

#### 3. Clear Cache

```bash
# Clear pre-commit cache
pre-commit clean

# Clear tool-specific caches
rm -rf ~/.cache/pre-commit/
rm -rf .ruff_cache/
```

#### 4. Exclude Large Directories

Update configuration files to exclude unnecessary directories:

```toml
# ruff.toml
exclude = [
    ".venv",
    "venv",
    "__pycache__",
    ".git",
    "alembic/versions",
    "build",
    "dist",
    "node_modules",
]
```

#### 5. Use Incremental Scanning

```bash
# Only scan staged files (default)
git commit

# Avoid scanning all files unless necessary
# pre-commit run --all-files  # Only in CI or initial setup
```

#### 6. Benchmark Individual Tools

```bash
# Measure each tool's execution time
time pre-commit run ruff --all-files
time pre-commit run gitleaks --all-files
time pre-commit run bandit --all-files
time pre-commit run safety --all-files
time pre-commit run semgrep --all-files

# Identify and optimize the slowest tool
```

### High Memory Usage

**Symptom**: System becomes unresponsive or tools crash with memory errors

**Cause**: Large files or too many files being scanned simultaneously

**Solution**:

```bash
# Limit Semgrep memory usage
# Add to .pre-commit-config.yaml:
- id: semgrep
  args: ['--max-memory', '2048']  # Limit to 2GB

# Process files in batches
pre-commit run --files file1.py file2.py file3.py

# Exclude large generated files
# Add to tool configurations:
exclude: ['**/generated/**', '**/*.min.js']
```

### Disk Space Issues

**Symptom**: `No space left on device` errors

**Cause**: Pre-commit cache consuming too much disk space

**Solution**:

```bash
# Check cache size
du -sh ~/.cache/pre-commit/

# Clear cache
pre-commit clean
rm -rf ~/.cache/pre-commit/

# Set cache location to larger disk
export PRE_COMMIT_HOME=/path/to/larger/disk/pre-commit-cache
```

---

## False Positives

### Handling False Positive Secrets

**Symptom**: GitLeaks flags example credentials or test data as secrets

**Solution**:

Add to `.gitleaks.toml`:

```toml
[allowlist]
paths = [
  ".env.example",
  "tests/fixtures/",
  "docs/examples/",
]

regexes = [
  "your_.*_token",      # Placeholder patterns
  "example\\.com",
  "test_.*_password",
  "dummy_.*_key",
]
```

Or use inline comments:

```python
# gitleaks:allow
EXAMPLE_TOKEN = "123456789:ABCdefGHIjklMNOpqrsTUVwxyz1234567890"
```

### Handling False Positive Security Issues

**Symptom**: Bandit or Ruff flags safe code as vulnerable

**Solution**:

#### Inline Suppression

```python
# Suppress specific rule
result = eval(safe_expression)  # nosec B307
api_key = get_from_vault()  # noqa: S105

# Suppress with explanation
subprocess.call(cmd, shell=True)  # nosec B602 - cmd is sanitized above
```

#### Configuration-Based Suppression

Add to `.bandit`:

```yaml
skips:
  - B101  # assert_used (common in tests)

exclude_dirs:
  - /tests/
```

Add to `ruff.toml`:

```toml
[lint.per-file-ignores]
"tests/**/*.py" = ["S101", "S105", "S106"]
"scripts/**/*.py" = ["T201"]  # Allow print in scripts
```

### Handling False Positive Dependency Vulnerabilities

**Symptom**: Safety flags vulnerabilities in features you don't use

**Solution**:

Add to `.safety-policy.yml`:

```yaml
security:
  ignore-vulnerabilities:
    51668:
      reason: "Not using affected urllib3 SOCKS proxy feature"
      expires: "2025-12-31"
    
    42194:
      reason: "Vulnerability only affects Windows, we deploy on Linux"
      expires: "2025-06-30"
```

**Best Practice**: Always include:
- Clear reason for ignoring
- Expiration date for review
- Link to issue tracker if applicable

### Too Many False Positives

**Symptom**: Overwhelming number of false positives making tools unusable

**Solution**:

1. **Adjust Severity Thresholds**:

```yaml
# .bandit
severity: high  # Only show high severity (was: medium)
confidence: high  # Only show high confidence (was: medium)
```

2. **Start with Strict Rules, Gradually Relax**:

```bash
# Run tools individually to identify problematic rules
bandit -r . -ll -ii  # High severity and confidence only

# Disable specific rules causing issues
# Add to .bandit:
skips:
  - B101  # assert_used
  - B601  # paramiko_calls
```

3. **Use Baseline**:

```bash
# Create baseline of existing issues
gitleaks detect --baseline-path .gitleaks-baseline.json --no-git

# Only flag new issues
gitleaks detect --baseline-path .gitleaks-baseline.json --no-git
```

---

## Tool-Specific Issues

### Ruff Issues

#### Ruff Not Formatting Code

**Symptom**: Code not formatted after running `ruff format`

**Solution**:

```bash
# Check if file is excluded
ruff check --show-files

# Verify ruff.toml configuration
cat ruff.toml

# Run with verbose output
ruff format --verbose .

# Check for syntax errors
ruff check .
```

#### Conflicting Rules

**Symptom**: Ruff reports conflicting rule violations

**Solution**:

```toml
# ruff.toml
[lint]
# Disable conflicting rules
ignore = [
    "D203",  # Conflicts with D211
    "D213",  # Conflicts with D212
]
```

### GitLeaks Issues

#### GitLeaks Scanning Git History Takes Too Long

**Symptom**: `gitleaks detect` (without --no-git) is very slow

**Solution**:

```bash
# Use --no-git to scan only current files
gitleaks detect --no-git

# Or limit depth
gitleaks detect --log-opts="--since='1 month ago'"

# In pre-commit, always use protect mode
gitleaks protect --staged
```

#### GitLeaks False Positives in Binary Files

**Symptom**: GitLeaks flags binary files as containing secrets

**Solution**:

```toml
# .gitleaks.toml
[allowlist]
paths = [
  "**/*.png",
  "**/*.jpg",
  "**/*.pdf",
  "**/*.zip",
]
```

### Bandit Issues

#### Bandit Scanning Test Files

**Symptom**: Bandit reports issues in test files (assert usage, hardcoded values)

**Solution**:

```yaml
# .bandit
exclude_dirs:
  - /tests/
  - /test/

# Or skip specific tests
skips:
  - B101  # assert_used
```

### Safety Issues

#### Safety Database Update Failures

**Symptom**: `Unable to load Safety DB` or outdated vulnerability data

**Solution**:

```bash
# Update Safety
pip install --upgrade safety

# Use specific database
safety check --db https://pyup.io/safety/safety-db/

# Check with local database
safety check --db /path/to/safety-db.json
```

#### Safety Fails on Unpinned Requirements

**Symptom**: Safety reports errors for requirements without version pins

**Solution**:

```bash
# Pin all versions in requirements.txt
pip freeze > requirements.txt

# Or allow unpinned (not recommended)
# Add to .safety-policy.yml:
security:
  ignore-unpinned-requirements: true
```

### Semgrep Issues

#### Semgrep Timeout on Large Files

**Symptom**: Semgrep times out on specific files

**Solution**:

```bash
# Increase timeout
semgrep --timeout 60 .

# Exclude problematic files
# Add to .semgrep.yml:
exclude:
  - "path/to/large/file.py"

# Or in .pre-commit-config.yaml:
- id: semgrep
  args: ['--timeout', '60']
```

#### Semgrep Custom Rules Not Working

**Symptom**: Custom rules in `.semgrep.yml` not being applied

**Solution**:

```bash
# Validate configuration
semgrep --validate --config .semgrep.yml

# Test specific rule
semgrep --config .semgrep.yml --test

# Check rule syntax
# Ensure proper indentation and pattern syntax
```

---

## Emergency Bypass Procedures

### When to Bypass Hooks

Use bypass procedures only in these situations:

1. **Critical Production Hotfix**: Urgent fix needed immediately
2. **CI/CD Pipeline Failure**: Hooks work locally but fail in CI
3. **Tool Malfunction**: Security tool has a bug causing false failures
4. **Infrastructure Issues**: Network or system issues preventing tool execution

**⚠️ Important**: Bypassed commits must still pass security review before merging.

### Bypass Single Commit

```bash
# Bypass all hooks for one commit
git commit --no-verify -m "Emergency hotfix for production issue #123"

# Or use environment variable
SKIP=all git commit -m "Emergency fix"
```

### Bypass Specific Hook

```bash
# Skip only GitLeaks
SKIP=gitleaks git commit -m "Commit message"

# Skip multiple hooks
SKIP=gitleaks,semgrep git commit -m "Commit message"

# Skip all except one
SKIP=ruff,bandit,safety,semgrep git commit -m "Only run GitLeaks"
```

### Temporarily Disable Hooks

```bash
# Uninstall hooks
pre-commit uninstall

# Make commits without hooks
git commit -m "Commit 1"
git commit -m "Commit 2"

# Re-install hooks
pre-commit install

# Run checks on all commits
pre-commit run --all-files
```

### Bypass in CI/CD

```yaml
# GitHub Actions - skip pre-commit
- name: Commit changes
  run: |
    git commit --no-verify -m "Automated commit"

# Or disable specific job
- name: Run pre-commit
  if: github.event_name != 'emergency'
  run: pre-commit run --all-files
```

### Post-Bypass Procedures

After bypassing hooks:

1. **Document the bypass**: Add comment in commit message explaining why
2. **Create tracking issue**: Open issue to address the bypassed checks
3. **Manual review**: Have another developer review the security implications
4. **Run checks manually**: Execute security tools manually and review findings
5. **Fix in follow-up**: Create follow-up PR to address any security issues

```bash
# After emergency bypass, run full security scan
pre-commit run --all-files

# Review findings
git diff HEAD~1 HEAD | grep -E "(password|token|key|secret)"

# Create follow-up issue
# Document any security concerns found
```

---

## Getting Help

### Diagnostic Information

When reporting issues, include:

```bash
# System information
python --version
git --version
pre-commit --version

# Tool versions
ruff --version
gitleaks version
bandit --version
safety --version
semgrep --version

# Configuration validation
pre-commit validate-config

# Verbose output
pre-commit run --all-files --verbose
```

### Common Commands for Debugging

```bash
# Show which files would be checked
pre-commit run --all-files --verbose --show-diff-on-failure

# Run single hook with full output
pre-commit run ruff --all-files --verbose

# Check hook installation
ls -la .git/hooks/

# View hook script
cat .git/hooks/pre-commit

# Test hook manually
.git/hooks/pre-commit
```

### Resources

- [Pre-commit Documentation](https://pre-commit.com/)
- [Pre-commit Setup Guide](pre-commit-setup.md)
- [Tool Reference](tool-reference.md)
- [CI Integration Guide](ci-integration.md)
- Project issue tracker for bug reports

### Escalation Path

1. **Check this troubleshooting guide**
2. **Review tool-specific documentation** in [tool-reference.md](tool-reference.md)
3. **Search project issues** for similar problems
4. **Ask team members** who have successfully set up the configuration
5. **Open new issue** with diagnostic information if problem persists

---

## Performance Optimization Tips

### Quick Wins

1. **Use file filtering**: Ensure each hook only processes relevant files
2. **Enable caching**: Don't run `pre-commit clean` unless necessary
3. **Exclude generated files**: Add build artifacts to exclude patterns
4. **Run incrementally**: Only scan changed files during development
5. **Parallel execution**: Ensure `fail_fast: false` in configuration

### Advanced Optimization

1. **Profile tool execution**: Identify slowest tools and optimize their configuration
2. **Reduce rule sets**: Disable rules that don't apply to your project
3. **Use baseline scans**: For large codebases, create baselines to only flag new issues
4. **Optimize CI**: Use caching in CI pipelines to speed up tool installation
5. **Split large files**: Break down large files that cause timeouts

### Monitoring Performance

```bash
# Benchmark full scan
time pre-commit run --all-files

# Benchmark individual tools
for hook in ruff gitleaks bandit safety semgrep; do
  echo "Testing $hook..."
  time pre-commit run $hook --all-files
done

# Track over time
echo "$(date),$(time pre-commit run --all-files 2>&1 | grep real)" >> performance.log
```

---

## Preventive Maintenance

### Regular Tasks

**Weekly**:
- Review any bypassed commits
- Check for tool updates: `pre-commit autoupdate --freeze`

**Monthly**:
- Update tools: `pre-commit autoupdate`
- Review false positive suppressions
- Clean cache: `pre-commit clean`

**Quarterly**:
- Audit security configuration
- Review and update custom rules
- Benchmark performance
- Update documentation

### Health Checks

```bash
# Validate configuration
pre-commit validate-config

# Test all hooks
pre-commit run --all-files

# Check for outdated tools
pre-commit autoupdate --freeze

# Review suppressed findings
grep -r "nosec\|noqa\|gitleaks:allow" .
```

This troubleshooting guide should help you resolve most common issues. For additional help, consult the other documentation files or reach out to your team.
