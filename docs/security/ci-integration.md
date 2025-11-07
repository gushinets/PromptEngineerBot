# CI/CD Integration Guide

This guide provides examples for integrating the pre-commit security configuration into various CI/CD platforms. Running security checks in CI ensures that all code is validated, even if developers bypass local hooks.

## Table of Contents

- [General Principles](#general-principles)
- [GitHub Actions](#github-actions)
- [GitLab CI](#gitlab-ci)
- [Azure Pipelines](#azure-pipelines)
- [Jenkins](#jenkins)
- [CircleCI](#circleci)
- [Bitbucket Pipelines](#bitbucket-pipelines)
- [Best Practices](#best-practices)

---

## General Principles

### Why Run Security Checks in CI?

1. **Enforcement**: Ensures checks run even if developers bypass local hooks
2. **Consistency**: Same environment and configuration for all developers
3. **Visibility**: Centralized reporting and tracking of security issues
4. **Automation**: Automatic checks on every pull request and merge
5. **Compliance**: Audit trail for security scanning

### Key Differences from Local Execution

| Aspect | Local (Pre-commit) | CI/CD |
|--------|-------------------|-------|
| **Scope** | Only changed files | All files (`--all-files`) |
| **Frequency** | Every commit | Every push/PR |
| **Bypass** | Possible with `--no-verify` | Cannot be bypassed |
| **Performance** | Optimized for speed | Can take longer |
| **Caching** | Local cache | CI cache (if configured) |

### Common Configuration

All CI platforms should:

1. **Install Python 3.12+** and required tools
2. **Cache dependencies** to speed up builds
3. **Run `pre-commit run --all-files`** to check entire codebase
4. **Fail the build** if security issues are found
5. **Upload reports** as artifacts for review

---

## GitHub Actions

### Basic Configuration

Create `.github/workflows/security.yml`:

```yaml
name: Security Checks

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

jobs:
  security:
    runs-on: ubuntu-latest
    
    steps:
    - name: Checkout code
      uses: actions/checkout@v4
      with:
        fetch-depth: 0  # Full history for GitLeaks
    
    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: '3.12'
        cache: 'pip'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install pre-commit
    
    - name: Cache pre-commit environments
      uses: actions/cache@v4
      with:
        path: ~/.cache/pre-commit
        key: pre-commit-${{ hashFiles('.pre-commit-config.yaml') }}
    
    - name: Run pre-commit hooks
      run: pre-commit run --all-files --show-diff-on-failure
```

### Advanced Configuration with Reporting

```yaml
name: Security Checks

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]
  schedule:
    - cron: '0 0 * * 0'  # Weekly full scan

jobs:
  security:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      security-events: write  # For uploading SARIF
    
    steps:
    - name: Checkout code
      uses: actions/checkout@v4
      with:
        fetch-depth: 0
    
    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: '3.12'
        cache: 'pip'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install pre-commit ruff bandit safety semgrep
    
    - name: Install GitLeaks
      run: |
        wget https://github.com/gitleaks/gitleaks/releases/latest/download/gitleaks_linux_amd64.tar.gz
        tar -xzf gitleaks_linux_amd64.tar.gz
        sudo mv gitleaks /usr/local/bin/
        gitleaks version
    
    - name: Cache pre-commit environments
      uses: actions/cache@v4
      with:
        path: ~/.cache/pre-commit
        key: pre-commit-${{ hashFiles('.pre-commit-config.yaml') }}
    
    - name: Run pre-commit hooks
      run: pre-commit run --all-files --show-diff-on-failure
      continue-on-error: true
      id: precommit
    
    - name: Run Semgrep with SARIF output
      run: |
        semgrep --config "p/owasp-top-ten" --config "p/python" \
          --sarif -o semgrep-results.sarif .
      continue-on-error: true
    
    - name: Upload Semgrep results to GitHub Security
      uses: github/codeql-action/upload-sarif@v3
      if: always()
      with:
        sarif_file: semgrep-results.sarif
    
    - name: Run Bandit with JSON output
      run: bandit -r . -f json -o bandit-report.json
      continue-on-error: true
    
    - name: Run Safety check
      run: safety check --json --output safety-report.json
      continue-on-error: true
    
    - name: Upload security reports
      uses: actions/upload-artifact@v4
      if: always()
      with:
        name: security-reports
        path: |
          semgrep-results.sarif
          bandit-report.json
          safety-report.json
    
    - name: Fail if security issues found
      if: steps.precommit.outcome == 'failure'
      run: exit 1
```

### Matrix Strategy for Multiple Python Versions

```yaml
jobs:
  security:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.12', '3.13']
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v5
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install and run security checks
      run: |
        pip install pre-commit
        pre-commit run --all-files
```

---

## GitLab CI

### Basic Configuration

Create `.gitlab-ci.yml`:

```yaml
stages:
  - security

security-checks:
  stage: security
  image: python:3.12
  
  before_script:
    - python --version
    - pip install --upgrade pip
    - pip install pre-commit ruff bandit safety semgrep
    - wget https://github.com/gitleaks/gitleaks/releases/latest/download/gitleaks_linux_amd64.tar.gz
    - tar -xzf gitleaks_linux_amd64.tar.gz
    - mv gitleaks /usr/local/bin/
  
  script:
    - pre-commit run --all-files --show-diff-on-failure
  
  cache:
    key: ${CI_COMMIT_REF_SLUG}
    paths:
      - .cache/pre-commit
  
  only:
    - merge_requests
    - main
    - develop
```

### Advanced Configuration with Artifacts

```yaml
stages:
  - security
  - report

variables:
  PIP_CACHE_DIR: "$CI_PROJECT_DIR/.cache/pip"
  PRE_COMMIT_HOME: "$CI_PROJECT_DIR/.cache/pre-commit"

security-checks:
  stage: security
  image: python:3.12
  
  before_script:
    - pip install --upgrade pip
    - pip install pre-commit ruff bandit safety semgrep
    - wget -q https://github.com/gitleaks/gitleaks/releases/latest/download/gitleaks_linux_amd64.tar.gz
    - tar -xzf gitleaks_linux_amd64.tar.gz
    - mv gitleaks /usr/local/bin/
  
  script:
    - echo "Running security checks..."
    - pre-commit run --all-files --show-diff-on-failure || true
    - semgrep --config "p/owasp-top-ten" --json -o semgrep-report.json . || true
    - bandit -r . -f json -o bandit-report.json || true
    - safety check --json --output safety-report.json || true
    - |
      if pre-commit run --all-files; then
        echo "All security checks passed"
      else
        echo "Security issues found"
        exit 1
      fi
  
  artifacts:
    when: always
    paths:
      - semgrep-report.json
      - bandit-report.json
      - safety-report.json
    reports:
      sast: semgrep-report.json
    expire_in: 30 days
  
  cache:
    key: ${CI_COMMIT_REF_SLUG}
    paths:
      - .cache/pip
      - .cache/pre-commit
  
  only:
    - merge_requests
    - main
    - develop

security-report:
  stage: report
  image: python:3.12
  
  script:
    - echo "Security scan complete. Review artifacts for details."
  
  dependencies:
    - security-checks
  
  only:
    - merge_requests
    - main
```

### GitLab Security Dashboard Integration

```yaml
security-sast:
  stage: security
  image: python:3.12
  
  script:
    - pip install semgrep
    - semgrep --config "p/owasp-top-ten" --gitlab-sast -o gl-sast-report.json .
  
  artifacts:
    reports:
      sast: gl-sast-report.json
  
  only:
    - merge_requests
    - main
```

---

## Azure Pipelines

### Basic Configuration

Create `azure-pipelines.yml`:

```yaml
trigger:
  - main
  - develop

pr:
  - main
  - develop

pool:
  vmImage: 'ubuntu-latest'

variables:
  python.version: '3.12'

steps:
- task: UsePythonVersion@0
  inputs:
    versionSpec: '$(python.version)'
  displayName: 'Use Python $(python.version)'

- script: |
    python -m pip install --upgrade pip
    pip install pre-commit ruff bandit safety semgrep
  displayName: 'Install dependencies'

- script: |
    wget https://github.com/gitleaks/gitleaks/releases/latest/download/gitleaks_linux_amd64.tar.gz
    tar -xzf gitleaks_linux_amd64.tar.gz
    sudo mv gitleaks /usr/local/bin/
  displayName: 'Install GitLeaks'

- task: Cache@2
  inputs:
    key: 'precommit | "$(Agent.OS)" | .pre-commit-config.yaml'
    path: $(HOME)/.cache/pre-commit
  displayName: 'Cache pre-commit environments'

- script: |
    pre-commit run --all-files --show-diff-on-failure
  displayName: 'Run security checks'

- task: PublishTestResults@2
  condition: always()
  inputs:
    testResultsFormat: 'JUnit'
    testResultsFiles: '**/test-results.xml'
  displayName: 'Publish test results'
```

### Advanced Configuration with Reports

```yaml
trigger:
  - main
  - develop

pool:
  vmImage: 'ubuntu-latest'

steps:
- task: UsePythonVersion@0
  inputs:
    versionSpec: '3.12'

- script: |
    pip install pre-commit ruff bandit safety semgrep
    wget -q https://github.com/gitleaks/gitleaks/releases/latest/download/gitleaks_linux_amd64.tar.gz
    tar -xzf gitleaks_linux_amd64.tar.gz
    sudo mv gitleaks /usr/local/bin/
  displayName: 'Install security tools'

- script: |
    pre-commit run --all-files || true
    semgrep --config "p/owasp-top-ten" --json -o $(Build.ArtifactStagingDirectory)/semgrep.json . || true
    bandit -r . -f json -o $(Build.ArtifactStagingDirectory)/bandit.json || true
    safety check --json --output $(Build.ArtifactStagingDirectory)/safety.json || true
  displayName: 'Run security scans'

- task: PublishBuildArtifacts@1
  condition: always()
  inputs:
    PathtoPublish: '$(Build.ArtifactStagingDirectory)'
    ArtifactName: 'security-reports'
  displayName: 'Publish security reports'

- script: |
    if pre-commit run --all-files; then
      echo "Security checks passed"
    else
      echo "##vso[task.logissue type=error]Security issues found"
      exit 1
    fi
  displayName: 'Validate security'
```

---

## Jenkins

### Declarative Pipeline

Create `Jenkinsfile`:

```groovy
pipeline {
    agent {
        docker {
            image 'python:3.12'
            args '-u root:root'
        }
    }
    
    environment {
        PRE_COMMIT_HOME = "${WORKSPACE}/.cache/pre-commit"
    }
    
    stages {
        stage('Setup') {
            steps {
                sh '''
                    python --version
                    pip install --upgrade pip
                    pip install pre-commit ruff bandit safety semgrep
                    wget -q https://github.com/gitleaks/gitleaks/releases/latest/download/gitleaks_linux_amd64.tar.gz
                    tar -xzf gitleaks_linux_amd64.tar.gz
                    mv gitleaks /usr/local/bin/
                '''
            }
        }
        
        stage('Security Checks') {
            steps {
                sh 'pre-commit run --all-files --show-diff-on-failure'
            }
        }
        
        stage('Generate Reports') {
            steps {
                sh '''
                    semgrep --config "p/owasp-top-ten" --json -o semgrep-report.json . || true
                    bandit -r . -f json -o bandit-report.json || true
                    safety check --json --output safety-report.json || true
                '''
            }
        }
    }
    
    post {
        always {
            archiveArtifacts artifacts: '*-report.json', allowEmptyArchive: true
        }
        failure {
            echo 'Security checks failed!'
        }
        success {
            echo 'All security checks passed!'
        }
    }
}
```

### Scripted Pipeline with Parallel Execution

```groovy
node {
    docker.image('python:3.12').inside('-u root:root') {
        stage('Checkout') {
            checkout scm
        }
        
        stage('Setup') {
            sh '''
                pip install pre-commit ruff bandit safety semgrep
                wget -q https://github.com/gitleaks/gitleaks/releases/latest/download/gitleaks_linux_amd64.tar.gz
                tar -xzf gitleaks_linux_amd64.tar.gz
                mv gitleaks /usr/local/bin/
            '''
        }
        
        stage('Security Scans') {
            parallel(
                'Ruff': {
                    sh 'ruff check . --output-format=json > ruff-report.json || true'
                },
                'GitLeaks': {
                    sh 'gitleaks detect --no-git --report-format json --report-path gitleaks-report.json || true'
                },
                'Bandit': {
                    sh 'bandit -r . -f json -o bandit-report.json || true'
                },
                'Safety': {
                    sh 'safety check --json --output safety-report.json || true'
                },
                'Semgrep': {
                    sh 'semgrep --config "p/owasp-top-ten" --json -o semgrep-report.json . || true'
                }
            )
        }
        
        stage('Validate') {
            sh 'pre-commit run --all-files'
        }
        
        stage('Archive') {
            archiveArtifacts artifacts: '*-report.json', allowEmptyArchive: true
        }
    }
}
```

---

## CircleCI

### Basic Configuration

Create `.circleci/config.yml`:

```yaml
version: 2.1

orbs:
  python: circleci/python@2.1.1

jobs:
  security-checks:
    docker:
      - image: cimg/python:3.12
    
    steps:
      - checkout
      
      - restore_cache:
          keys:
            - pre-commit-{{ checksum ".pre-commit-config.yaml" }}
      
      - run:
          name: Install dependencies
          command: |
            pip install --upgrade pip
            pip install pre-commit ruff bandit safety semgrep
      
      - run:
          name: Install GitLeaks
          command: |
            wget https://github.com/gitleaks/gitleaks/releases/latest/download/gitleaks_linux_amd64.tar.gz
            tar -xzf gitleaks_linux_amd64.tar.gz
            sudo mv gitleaks /usr/local/bin/
      
      - save_cache:
          key: pre-commit-{{ checksum ".pre-commit-config.yaml" }}
          paths:
            - ~/.cache/pre-commit
      
      - run:
          name: Run security checks
          command: pre-commit run --all-files --show-diff-on-failure
      
      - store_artifacts:
          path: ~/project/security-reports
          destination: security-reports

workflows:
  security:
    jobs:
      - security-checks:
          filters:
            branches:
              only:
                - main
                - develop
```

---

## Bitbucket Pipelines

### Basic Configuration

Create `bitbucket-pipelines.yml`:

```yaml
image: python:3.12

definitions:
  caches:
    precommit: ~/.cache/pre-commit

pipelines:
  default:
    - step:
        name: Security Checks
        caches:
          - pip
          - precommit
        script:
          - pip install --upgrade pip
          - pip install pre-commit ruff bandit safety semgrep
          - wget -q https://github.com/gitleaks/gitleaks/releases/latest/download/gitleaks_linux_amd64.tar.gz
          - tar -xzf gitleaks_linux_amd64.tar.gz
          - mv gitleaks /usr/local/bin/
          - pre-commit run --all-files --show-diff-on-failure
        artifacts:
          - security-reports/**
  
  pull-requests:
    '**':
      - step:
          name: Security Checks
          caches:
            - pip
            - precommit
          script:
            - pip install pre-commit
            - pre-commit run --all-files
  
  branches:
    main:
      - step:
          name: Security Checks with Reports
          caches:
            - pip
            - precommit
          script:
            - pip install pre-commit ruff bandit safety semgrep
            - wget -q https://github.com/gitleaks/gitleaks/releases/latest/download/gitleaks_linux_amd64.tar.gz
            - tar -xzf gitleaks_linux_amd64.tar.gz
            - mv gitleaks /usr/local/bin/
            - mkdir -p security-reports
            - pre-commit run --all-files || true
            - semgrep --config "p/owasp-top-ten" --json -o security-reports/semgrep.json . || true
            - bandit -r . -f json -o security-reports/bandit.json || true
            - safety check --json --output security-reports/safety.json || true
          artifacts:
            - security-reports/**
```

---

## Best Practices

### 1. Caching

Always cache pre-commit environments and pip packages to speed up builds:

```yaml
# GitHub Actions
- uses: actions/cache@v4
  with:
    path: ~/.cache/pre-commit
    key: pre-commit-${{ hashFiles('.pre-commit-config.yaml') }}

# GitLab CI
cache:
  key: ${CI_COMMIT_REF_SLUG}
  paths:
    - .cache/pre-commit
```

### 2. Fail Fast vs. Complete Scan

**Fail Fast** (stop on first failure):
```yaml
script:
  - pre-commit run --all-files
```

**Complete Scan** (run all tools, then fail):
```yaml
script:
  - pre-commit run --all-files || true
  - semgrep --config "p/owasp-top-ten" . || true
  - bandit -r . || true
  - |
    if pre-commit run --all-files; then
      exit 0
    else
      exit 1
    fi
```

### 3. Artifact Retention

Store security reports for audit and review:

```yaml
# GitHub Actions
- uses: actions/upload-artifact@v4
  with:
    name: security-reports
    path: |
      semgrep-report.json
      bandit-report.json
    retention-days: 90
```

### 4. Scheduled Scans

Run full security scans on a schedule:

```yaml
# GitHub Actions
on:
  schedule:
    - cron: '0 0 * * 0'  # Weekly on Sunday
```

### 5. Branch Protection

Configure branch protection rules to require security checks:

**GitHub**:
- Settings → Branches → Branch protection rules
- Require status checks: "Security Checks"

**GitLab**:
- Settings → Repository → Protected branches
- Require pipeline to succeed

### 6. Notifications

Set up notifications for security failures:

```yaml
# GitHub Actions
- name: Notify on failure
  if: failure()
  uses: 8398a7/action-slack@v3
  with:
    status: ${{ job.status }}
    text: 'Security checks failed!'
    webhook_url: ${{ secrets.SLACK_WEBHOOK }}
```

### 7. Security Dashboard Integration

Upload results to security dashboards:

```yaml
# GitHub Security
- uses: github/codeql-action/upload-sarif@v3
  with:
    sarif_file: semgrep-results.sarif

# GitLab Security
artifacts:
  reports:
    sast: gl-sast-report.json
```

### 8. Performance Optimization

- Use Docker layer caching
- Cache tool installations
- Run only on changed files for PRs (optional)
- Use parallel execution where possible

### 9. Environment Variables

Store sensitive configuration in CI secrets:

```yaml
env:
  SAFETY_API_KEY: ${{ secrets.SAFETY_API_KEY }}
  SEMGREP_APP_TOKEN: ${{ secrets.SEMGREP_APP_TOKEN }}
```

### 10. Versioning

Pin tool versions for reproducibility:

```yaml
script:
  - pip install pre-commit==3.5.0 ruff==0.1.6 bandit==1.7.5
```

---

## Troubleshooting CI Issues

### Build Timeout

**Solution**: Increase timeout or optimize scans
```yaml
# GitHub Actions
timeout-minutes: 30

# GitLab CI
timeout: 30m
```

### Cache Issues

**Solution**: Clear cache or update cache key
```bash
# GitHub Actions: Settings → Actions → Caches → Delete
# GitLab CI: CI/CD → Pipelines → Clear runner caches
```

### Tool Installation Failures

**Solution**: Use pre-built Docker images
```yaml
# Use image with tools pre-installed
image: returntocorp/semgrep:latest
```

### Network Issues

**Solution**: Use mirrors or offline mode
```yaml
script:
  - pip install --index-url https://mirror.example.com/pypi pre-commit
```

---

## Additional Resources

- [Pre-commit Setup Guide](pre-commit-setup.md)
- [Tool Reference](tool-reference.md)
- [Troubleshooting Guide](troubleshooting.md)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [GitLab CI Documentation](https://docs.gitlab.com/ee/ci/)
- [Azure Pipelines Documentation](https://docs.microsoft.com/en-us/azure/devops/pipelines/)

---

This guide should help you integrate security checks into your CI/CD pipeline. Adjust the examples based on your specific requirements and platform capabilities.
