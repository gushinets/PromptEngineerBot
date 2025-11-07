# Pull Request

## Description

<!-- Provide a clear and concise description of your changes -->

## Type of Change

<!-- Mark the relevant option with an "x" -->

- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update
- [ ] Performance improvement
- [ ] Code refactoring
- [ ] Security fix

## Related Issues

<!-- Link to related issues using #issue_number -->

Fixes #
Relates to #

## Changes Made

<!-- List the main changes in bullet points -->

- 
- 
- 

## Testing

<!-- Describe the tests you ran and how to reproduce them -->

### Test Coverage

- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] End-to-end tests added/updated
- [ ] All tests pass locally (`pytest tests/`)

### Manual Testing

<!-- Describe manual testing performed -->

1. 
2. 
3. 

## Security Checklist

<!-- All items must be checked before merging -->

- [ ] Pre-commit security checks pass (`pre-commit run --all-files`)
- [ ] No hardcoded secrets, API keys, or credentials
- [ ] User input is properly validated and sanitized
- [ ] SQL queries use parameterization (no string concatenation)
- [ ] No use of `shell=True` in subprocess calls
- [ ] Dependencies are up to date and scanned for vulnerabilities
- [ ] Error messages don't expose sensitive information
- [ ] Authentication and authorization are properly implemented (if applicable)

## Code Quality Checklist

- [ ] Code follows project style guidelines
- [ ] Type hints are used for function parameters and return values
- [ ] Docstrings are added for public functions and classes
- [ ] Error handling is comprehensive and appropriate
- [ ] Code is modular and follows single responsibility principle
- [ ] No code duplication (DRY principle)
- [ ] Performance considerations addressed (if applicable)

## Documentation

- [ ] README.md updated (if needed)
- [ ] Docstrings added/updated
- [ ] Architecture documentation updated (if needed)
- [ ] User guides updated (if needed)
- [ ] CHANGELOG.md updated (if applicable)

## Deployment Considerations

<!-- Check all that apply -->

- [ ] No database migrations required
- [ ] Database migrations included and tested
- [ ] Environment variables added/changed (documented in .env.example)
- [ ] No breaking changes to existing APIs
- [ ] Backward compatible with existing data
- [ ] No infrastructure changes required

## Screenshots/Examples

<!-- If applicable, add screenshots or code examples to demonstrate the changes -->

## Additional Notes

<!-- Any additional information that reviewers should know -->

## Reviewer Checklist

<!-- For reviewers - do not modify -->

- [ ] Code review completed
- [ ] Security review completed (for sensitive changes)
- [ ] Tests are adequate and pass
- [ ] Documentation is clear and complete
- [ ] No obvious performance issues
- [ ] Follows project architecture and patterns

---

**By submitting this pull request, I confirm that:**

- [ ] I have read and followed the [Contributing Guidelines](../CONTRIBUTING.md)
- [ ] My code follows the project's coding standards
- [ ] I have tested my changes thoroughly
- [ ] I have updated documentation as needed
- [ ] All security checks pass
