# Security Tools - Quick Start Guide

Get up and running with security scanning in under 5 minutes.

## Prerequisites

- Python 3.12 or higher
- Git 2.30 or higher
- pip package manager

## Installation Methods

### Method 1: Automated Setup (Recommended) ⚡

The fastest way to get started:

```bash
# Run the automated installation script
python scripts/setup_security_tools.py
```

This script will:
- ✅ Install all security tools
- ✅ Configure git hooks
- ✅ Validate installation
- ✅ Provide next steps

**Time**: ~2 minutes

---

### Method 2: Manual pip Install

Install security tools directly:

```bash
# Install security tools
pip install pre-commit ruff bandit safety semgrep

# Install git hooks
pre-commit install

# Verify installation
pre-commit run --all-files
```

**Time**: ~3 minutes

---

### Method 3: Individual Tool Installation

Install each tool separately:

```bash
# Install pre-commit framework
pip install pre-commit

# Install security tools
pip install ruff bandit safety semgrep

# Install GitLeaks (platform-specific)
# Windows: Download from https://github.com/gitleaks/gitleaks/releases
# macOS: brew install gitleaks
# Linux: wget + tar (see pre-commit-setup.md)

# Install git hooks
pre-commit install

# Verify
pre-commit run --all-files
```

**Time**: ~5 minutes

---

## Quick Verification

After installation, verify everything works:

```bash
# Check tool versions
pre-commit --version
ruff --version
gitleaks version
bandit --version
safety --version
semgrep --version

# Run security scan
pre-commit run --all-files
```

Expected output: All tools should pass (or show findings to address).

---

## Daily Usage

Once installed, security checks run automatically:

```bash
# Make changes to code
git add file.py

# Commit (hooks run automatically)
git commit -m "Your message"
```

If security issues are found:
1. Review the error messages
2. Fix the issues in your code
3. Stage the fixes: `git add file.py`
4. Commit again: `git commit -m "Your message"`

---

## Manual Scans

Run security checks without committing:

```bash
# Scan all files
pre-commit run --all-files

# Scan specific files
pre-commit run --files path/to/file.py

# Run specific tool
pre-commit run ruff --all-files
pre-commit run gitleaks --all-files
```

---

## IDE Integration

### Visual Studio Code

1. Install recommended extensions:
   - Ruff (charliermarsh.ruff)
   - Python (ms-python.python)

2. Settings are pre-configured in `.vscode/settings.json`

3. Features:
   - ✅ Real-time linting
   - ✅ Format on save
   - ✅ Security warnings in Problems panel

### Other IDEs

See [pre-commit-setup.md](pre-commit-setup.md#ide-integration) for other IDE configurations.

---

## Troubleshooting

### Hooks not running?

```bash
pre-commit install
```

### Tool not found?

```bash
pip install <tool-name>
# or
pre-commit install --install-hooks
```

### Slow performance?

```bash
# Clear cache
pre-commit clean

# Run on specific files only
pre-commit run --files path/to/file.py
```

### More help?

See [troubleshooting.md](troubleshooting.md) for detailed solutions.

---

## What Gets Checked?

| Tool | What It Checks | Time |
|------|----------------|------|
| **Ruff** | Python code quality & security patterns | 1-3s |
| **GitLeaks** | Hardcoded secrets (API keys, passwords) | 2-5s |
| **Bandit** | Python security vulnerabilities | 3-8s |
| **Safety** | Vulnerable dependencies | 2-4s |
| **Semgrep** | OWASP Top 10 security patterns | 5-10s |

**Total**: 15-30 seconds for typical commits

---

## Security Coverage

✅ **OWASP Top 10** - All categories covered  
✅ **Secrets Detection** - API keys, tokens, passwords  
✅ **SQL Injection** - String-based queries  
✅ **Command Injection** - shell=True usage  
✅ **Weak Cryptography** - MD5, SHA1, weak random  
✅ **Dependency CVEs** - Known vulnerabilities  

---

## Next Steps

1. ✅ **Installation complete** - You're ready to go!
2. 📖 **Read the docs** - See [pre-commit-setup.md](pre-commit-setup.md) for details
3. 🔍 **Review findings** - Address any security issues found
4. 👥 **Share with team** - Help others get set up
5. 🔄 **Keep updated** - Run `pre-commit autoupdate` monthly

---

## Quick Reference

```bash
# Install
python scripts/setup_security_tools.py

# Run all checks
pre-commit run --all-files

# Run specific tool
pre-commit run ruff --all-files

# Skip hooks (emergency only)
git commit --no-verify -m "message"

# Update tools
pre-commit autoupdate

# Clear cache
pre-commit clean
```

---

## Documentation

- **[Pre-commit Setup](pre-commit-setup.md)** - Comprehensive installation guide
- **[Tool Reference](tool-reference.md)** - Detailed tool documentation
- **[Troubleshooting](troubleshooting.md)** - Common issues and solutions
- **[CI Integration](ci-integration.md)** - CI/CD setup examples
- **[OWASP Report](OWASP_TOP10_TEST_REPORT.md)** - Security test results

---

## Support

Need help? Check:
1. [Troubleshooting Guide](troubleshooting.md)
2. [Tool Reference](tool-reference.md)
3. Project documentation
4. Team chat/Slack

---

**You're all set!** 🎉 Security scanning is now active on every commit.
