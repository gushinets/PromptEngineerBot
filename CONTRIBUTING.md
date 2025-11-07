# Contributing to Telegram Prompt Engineering Bot

Thank you for your interest in contributing to the Telegram Prompt Engineering Bot! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Security Requirements](#security-requirements)
- [Development Workflow](#development-workflow)
- [Coding Standards](#coding-standards)
- [Testing Guidelines](#testing-guidelines)
- [Pull Request Process](#pull-request-process)
- [Documentation](#documentation)

## Code of Conduct

This project follows a professional code of conduct. We expect all contributors to:

- Be respectful and inclusive
- Focus on constructive feedback
- Prioritize the project's goals and quality
- Help maintain a welcoming environment

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/your-username/telegram-prompt-bot.git
   cd telegram-prompt-bot
   ```
3. **Add upstream remote**:
   ```bash
   git remote add upstream https://github.com/original-owner/telegram-prompt-bot.git
   ```

## Development Setup

### Prerequisites

- Python 3.12 or higher
- Git 2.30 or higher
- Docker (optional, for containerized development)
- PostgreSQL (optional, for local database development)

### Installation

1. **Create a virtual environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Install pre-commit hooks** (required):
   ```bash
   pip install pre-commit
   pre-commit install
   ```

5. **Run initial security scan**:
   ```bash
   pre-commit run --all-files
   ```

## Security Requirements

**All contributions must pass automated security checks before being merged.**

### Pre-commit Hooks

This project uses pre-commit hooks to enforce security and code quality standards. The hooks run automatically on every commit and check for:

- **Secrets Detection** (GitLeaks): Prevents hardcoded API keys, tokens, passwords
- **Python Security** (Bandit): Identifies SQL injection, command injection, crypto issues
- **Code Quality** (Ruff): Enforces Python best practices and security patterns
- **Dependency Vulnerabilities** (Safety): Scans for known CVEs in packages
- **Security Patterns** (Semgrep): Detects OWASP Top 10 vulnerabilities

### Installation

```bash
# Install pre-commit framework
pip install pre-commit

# Install git hooks
pre-commit install

# Verify installation
pre-commit run --all-files
```

### Running Security Checks

```bash
# Run all security checks
pre-commit run --all-files

# Run specific check
pre-commit run ruff --all-files
pre-commit run gitleaks --all-files
pre-commit run bandit --all-files

# Run on specific files
pre-commit run --files path/to/file.py
```

### Handling Security Findings

If security checks fail:

1. **Review the findings** carefully
2. **Fix legitimate issues** in your code
3. **Document false positives** with inline comments:
   ```python
   # nosec B101 - Assert is safe in test context
   api_key = get_from_vault()  # noqa: S105 - Retrieved from secure vault
   ```
4. **Re-run checks** after fixes
5. **Never bypass checks** without justification

For detailed information, see:
- [Pre-commit Setup Guide](docs/security/pre-commit-setup.md)
- [Security Tools Reference](docs/security/tool-reference.md)
- [Troubleshooting Guide](docs/security/troubleshooting.md)

### Emergency Bypass

In rare emergency situations, you can bypass hooks:

```bash
git commit --no-verify -m "Emergency hotfix for issue #123"
```

**⚠️ Important**: Bypassed commits must still pass security review before merging.

## Development Workflow

### Creating a Feature Branch

```bash
# Update your local main branch
git checkout main
git pull upstream main

# Create a feature branch
git checkout -b feature/your-feature-name
```

### Making Changes

1. **Write code** following the project's architecture and patterns
2. **Add tests** for new functionality
3. **Update documentation** as needed
4. **Run tests** to ensure nothing breaks:
   ```bash
   python -m pytest tests/ -v
   ```
5. **Commit changes** (hooks run automatically):
   ```bash
   git add .
   git commit -m "Add feature: description"
   ```

### Keeping Your Branch Updated

```bash
# Fetch upstream changes
git fetch upstream

# Rebase your branch
git rebase upstream/main

# Resolve conflicts if any
# Then continue
git rebase --continue
```

## Coding Standards

### Python Style Guide

- Follow **PEP 8** style guidelines
- Use **type hints** for function parameters and return values
- Write **docstrings** for all public functions and classes
- Keep functions **focused and small** (single responsibility)
- Use **meaningful variable names**

### Code Organization

- Follow the existing **modular architecture**
- Place new features in appropriate directories:
  - `telegram_bot/core/` - Core business logic
  - `telegram_bot/services/` - External service integrations
  - `telegram_bot/utils/` - Utility functions
  - `telegram_bot/flows/` - Complex workflows
- Use **dependency injection** for testability
- Implement **proper error handling**

### Security Best Practices

- **Never hardcode secrets** - use environment variables
- **Validate all user input** before processing
- **Use parameterized queries** for database operations
- **Avoid shell=True** in subprocess calls
- **Use secure random** for cryptographic operations
- **Keep dependencies updated** and scan for vulnerabilities

### Example Code

```python
from typing import Optional
import os
from telegram_bot.utils.config import Config

class ExampleService:
    """Service for handling example operations.
    
    Args:
        config: Application configuration
        api_key: API key from environment (never hardcoded)
    """
    
    def __init__(self, config: Config, api_key: Optional[str] = None):
        self.config = config
        self.api_key = api_key or os.getenv("API_KEY")
        
        if not self.api_key:
            raise ValueError("API_KEY environment variable is required")
    
    def process_data(self, user_input: str) -> dict:
        """Process user input safely.
        
        Args:
            user_input: Raw user input (must be validated)
            
        Returns:
            Processed data dictionary
            
        Raises:
            ValueError: If input is invalid
        """
        # Validate input
        if not user_input or len(user_input) > 1000:
            raise ValueError("Invalid input length")
        
        # Process safely
        result = self._safe_process(user_input)
        return result
```

## Testing Guidelines

### Test Coverage Requirements

- **Minimum 80% coverage** for new code
- **100% coverage** for critical paths (authentication, payment, etc.)
- All tests must pass before merging

### Writing Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=telegram_bot --cov-report=html

# Run specific test file
python -m pytest tests/unit/test_your_feature.py -v

# Run specific test function
python -m pytest tests/unit/test_your_feature.py::test_specific_function -v
```

### Test Structure

```python
import pytest
from telegram_bot.services.example_service import ExampleService

class TestExampleService:
    """Tests for ExampleService."""
    
    @pytest.fixture
    def service(self, mock_config):
        """Create service instance for testing."""
        return ExampleService(mock_config, api_key="test-key")
    
    def test_process_data_success(self, service):
        """Test successful data processing."""
        result = service.process_data("valid input")
        assert result["status"] == "success"
    
    def test_process_data_invalid_input(self, service):
        """Test handling of invalid input."""
        with pytest.raises(ValueError, match="Invalid input"):
            service.process_data("")
```

### Test Categories

- **Unit Tests** (`tests/unit/`): Test individual components in isolation
- **Integration Tests** (`tests/integration/`): Test component interactions
- **End-to-End Tests** (`tests/e2e/`): Test complete user workflows

## Pull Request Process

### Before Submitting

1. ✅ All tests pass locally
2. ✅ Security checks pass (pre-commit hooks)
3. ✅ Code follows style guidelines
4. ✅ Documentation is updated
5. ✅ Commit messages are clear and descriptive

### Submitting a Pull Request

1. **Push your branch** to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```

2. **Create a pull request** on GitHub:
   - Use a clear, descriptive title
   - Fill out the pull request template
   - Reference related issues
   - Add screenshots/examples if applicable

3. **Respond to feedback**:
   - Address review comments promptly
   - Make requested changes
   - Push updates to the same branch

### Pull Request Checklist

Use this checklist when creating a pull request:

- [ ] Code follows project style guidelines
- [ ] All tests pass (`pytest tests/`)
- [ ] Security checks pass (`pre-commit run --all-files`)
- [ ] New tests added for new functionality
- [ ] Documentation updated (README, docstrings, etc.)
- [ ] No hardcoded secrets or credentials
- [ ] Error handling is comprehensive
- [ ] Commit messages are clear and descriptive
- [ ] Branch is up to date with main

### Review Process

1. **Automated checks** run on every PR (CI/CD)
2. **Code review** by maintainers
3. **Security review** for sensitive changes
4. **Approval required** before merging
5. **Squash and merge** to keep history clean

## Documentation

### When to Update Documentation

Update documentation when you:

- Add new features or functionality
- Change existing behavior
- Add new configuration options
- Fix bugs that affect usage
- Improve error messages or user experience

### Documentation Locations

- **README.md**: Project overview, setup, quick start
- **docs/**: Detailed documentation
  - `docs/architecture/`: System design and architecture
  - `docs/guides/`: User guides and tutorials
  - `docs/security/`: Security configuration and best practices
  - `docs/deployment/`: Deployment guides
- **Docstrings**: In-code documentation for functions and classes
- **Comments**: Explain complex logic or non-obvious decisions

### Documentation Style

- Use **clear, concise language**
- Include **code examples** where helpful
- Add **diagrams** for complex concepts
- Keep documentation **up to date** with code changes
- Use **Markdown** formatting consistently

## Getting Help

### Resources

- **[Documentation](docs/INDEX.md)**: Comprehensive project documentation
- **[Security Guide](docs/security/pre-commit-setup.md)**: Security setup and best practices
- **[Architecture Docs](docs/architecture/)**: System design and patterns
- **[Issue Tracker](https://github.com/your-repo/issues)**: Report bugs or request features

### Questions?

- Check existing **documentation** first
- Search **closed issues** for similar questions
- Open a **new issue** with the "question" label
- Be specific and provide context

## License

By contributing to this project, you agree that your contributions will be licensed under the same license as the project.

## Thank You!

Thank you for contributing to the Telegram Prompt Engineering Bot! Your efforts help make this project better for everyone.
