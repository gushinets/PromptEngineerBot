# Security Scan Results

This directory contains temporary JSON output files from security scanning tools.

## Purpose

These files are generated during security scans and contain detailed findings in machine-readable format. They are useful for:

- Debugging security tool configurations
- Integrating with security dashboards
- Generating custom reports
- Auditing scan history

## Files

Typical files in this directory:

- `owasp-scan-results.json` - Semgrep OWASP Top 10 scan results
- `python-security-scan.json` - Semgrep Python security scan results
- `security-audit-scan.json` - Semgrep security audit scan results
- `bandit-owasp-scan.json` - Bandit SAST scan results
- `precommit_benchmark_results.json` - Pre-commit performance benchmarks
- `precommit_cache_verification.json` - Cache validation results
- `project_security_analysis.json` - Project-wide security analysis

## Retention

These files are:

- ✅ **Temporary** - Can be safely deleted
- ✅ **Regenerated** - Created on each scan run
- ✅ **Not committed** - Excluded via .gitignore
- ✅ **Local only** - Not needed in version control

## Cleanup

To clean up old scan results:

```bash
# Remove all JSON scan results
rm docs/security/scan-results/*.json

# Or remove the entire directory
rm -rf docs/security/scan-results/
```

The directory will be recreated automatically on the next security scan.

## CI/CD

In CI/CD pipelines, these files are typically:

1. Generated during the security scan step
2. Uploaded as build artifacts
3. Retained for 30-90 days
4. Used for security dashboard integration

See [CI Integration Guide](../ci-integration.md) for examples.
