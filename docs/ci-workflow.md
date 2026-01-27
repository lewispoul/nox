# Python CI Workflow

This document describes the Python CI workflow implemented for the Nox API project.

## Overview

The `python-ci.yml` workflow provides comprehensive continuous integration for Python code including:

- **Code Quality**: Black formatting, isort import sorting, flake8 linting, ruff checking
- **Security Scanning**: Bandit, Safety, and pip-audit vulnerability detection
- **Testing**: pytest with coverage reporting and database/Redis services
- **SBOM Generation**: Software Bill of Materials for supply chain security

## Implementation

The workflow is designed as a reusable standard that can be:
1. Called by other workflows (e.g., docker-build.yml)
2. Run independently on code changes
3. Used as a quality gate for pull requests

## Workflow Jobs

### 1. Lint - Code Quality & Linting
- **Black**: Code formatting validation (88-character line length)
- **isort**: Import sorting validation (Black-compatible profile)
- **flake8**: Linting for critical errors (configured in `.flake8`)
- **Ruff**: Fast Python linter for additional checks
- **Scope**: Focuses on `api/` and `tests/` directories
- **Behavior**: All linting checks continue on error to show all issues

### 2. Security - Security Scanning
- **Bandit**: Security vulnerability scanning in code
- **Safety**: Dependency vulnerability checking against safety DB
- **pip-audit**: Supply chain security analysis using PyPI advisory database
- **Outputs**: JSON reports for each tool
- **Artifacts**: Security reports uploaded with 30-day retention

### 3. Test - Testing
- Runs pytest with database and Redis services
- Includes coverage reporting with pytest-cov
- Uses focused test execution with proper environment setup
- **Services**:
  - PostgreSQL 15 (test database)
  - Redis 7 (cache/queue testing)
- **Environment**: Configured for CI with test credentials
- **Artifacts**: Coverage reports (XML and HTML) uploaded with 30-day retention

### 4. SBOM - Software Bill of Materials Generation
- Generates CycloneDX-format SBOM in JSON
- Captures all installed dependencies with versions
- Runs only on main branch to avoid unnecessary processing
- Provides compliance and security transparency
- **Artifacts**: SBOM and frozen requirements uploaded with 90-day retention

### 5. Summary - CI Summary
- Aggregates results from all jobs
- Provides clear success/failure reporting
- Runs even if previous jobs fail (if: always())
- Includes next steps guidance

## Reusable Actions

The workflow uses composite actions for common setup tasks:

### setup-python-env
Location: `.github/actions/setup-python-env/action.yml`
- Sets up Python with specified version (default: 3.11)
- Enables pip caching for faster builds
- Installs production dependencies
- Optionally installs dev dependencies

### setup-test-db
Location: `.github/actions/setup-test-db/action.yml`
- Initializes test database if init script exists
- Handles database connection with proper credentials
- Skips gracefully if no initialization needed

## Configuration

### Linting Configuration
- **flake8**: Configured in `.flake8` with 88-character line length
- **isort**: Configured in `pyproject.toml` with Black-compatible settings
- **Black**: Uses default 88-character line length
- **Ruff**: Configured in `pyproject.toml` for additional checks

### Focused Approach
The workflow focuses on `api/` and `tests/` directories to:
- Avoid overwhelming CI with legacy code issues
- Enable gradual adoption of code quality standards
- Provide immediate value for new development

## Artifacts

The workflow generates several artifacts:
- **Security Reports**: bandit-report.json, safety-report.json, pip-audit-report.json (30 days)
- **Test Results**: coverage.xml, htmlcov/ (30 days)
- **SBOM**: sbom.json, requirements-frozen.txt (90 days)

## Usage

The workflow runs automatically on:
- Push to `main` or `develop` branches
- Pull requests to `main` branch
- Manual workflow dispatch

### As a Reusable Workflow

Other workflows can call python-ci.yml:

```yaml
jobs:
  ci:
    uses: ./.github/workflows/python-ci.yml
```

This pattern is used by `docker-build.yml` to avoid duplicating test infrastructure.

## Integration with Other Workflows

### docker-build.yml
Calls python-ci.yml as a reusable workflow to run all CI checks before building Docker images.

### agent-nightly.yml
Uses the `setup-python-env` reusable action for consistent Python setup.

## Customization

To adapt the workflow:
1. Modify directory focus in linting steps (currently `api/` and `tests/`)
2. Adjust security scanning scope
3. Update test execution parameters
4. Configure artifact retention policies
5. Add/remove linting tools as needed

## Best Practices

1. **Incremental Adoption**: Start with warnings, gradually enforce rules
2. **Focused Scope**: Target active development areas first
3. **Artifact Retention**: Balance storage costs with debugging needs
4. **Reusability**: Extract common patterns into composite actions
5. **Security First**: Multiple layers of security scanning

This workflow provides a solid foundation for maintaining code quality and security in the Nox API project while being adaptable to future needs.