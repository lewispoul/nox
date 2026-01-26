# Python CI Workflow

This document describes the Python CI workflow implemented for the Nox API project.

## Overview

The `python-ci.yml` workflow provides comprehensive continuous integration for Python code including:

- **Code Quality**: Black formatting, isort import sorting, flake8 linting
- **Security Scanning**: Bandit, Safety, and pip-audit vulnerability detection
- **Testing**: pytest with coverage reporting
- **SBOM Generation**: Software Bill of Materials for supply chain security

## Workflow Jobs

### 1. Code Quality & Security
- **Black**: Code formatting validation
- **isort**: Import sorting validation  
- **flake8**: Linting for critical errors
- **Bandit**: Security vulnerability scanning
- **Safety**: Dependency vulnerability checking
- **pip-audit**: Supply chain security analysis

### 2. Testing
- Runs pytest with database and Redis services
- Includes coverage reporting when pytest-cov is available
- Uses focused test execution with proper environment setup

### 3. SBOM Generation
- Generates Software Bill of Materials in JSON and XML formats
- Runs only on main branch to avoid unnecessary processing
- Provides compliance and security transparency

### 4. CI Summary
- Aggregates results from all jobs
- Provides clear success/failure reporting
- Includes next steps guidance

## Configuration

### Linting Configuration
- **flake8**: Configured in `.flake8` with 88-character line length
- **isort**: Configured in `pyproject.toml` with Black-compatible settings
- **Black**: Uses default 88-character line length

### Focused Approach
The workflow focuses on `api/` and `tests/` directories to:
- Avoid overwhelming CI with legacy code issues
- Enable gradual adoption of code quality standards
- Provide immediate value for new development

## Artifacts

The workflow generates several artifacts:
- **Security Reports**: bandit-report.json, safety-report.json, pip-audit-report.json
- **Test Results**: HTML coverage reports, XML coverage files
- **SBOM**: JSON and XML software bills of materials

## Usage

The workflow runs automatically on:
- Push to `main` or `develop` branches
- Pull requests to `main` branch
- Manual workflow dispatch

### Skipping Lint Action

You can skip the code quality and linting checks in several ways:

1. **Via Commit Message**: Include `[skip lint]` or `[no lint]` in your commit message
   ```bash
   git commit -m "Quick fix [skip lint]"
   ```

2. **Via Manual Workflow Dispatch**: When manually triggering the workflow from GitHub Actions UI, check the "Skip lint action" option

**Note**: When lint is skipped, the test job will still run to ensure code functionality. The CI pipeline will note that code quality checks were skipped in the summary.

**Use Cases for Skipping Lint**:
- Urgent hotfixes that need quick deployment
- Work-in-progress commits to development branches
- Documentation-only changes
- When linting issues are being addressed in a separate PR

## Customization

To adapt the workflow:
1. Modify directory focus in linting steps
2. Adjust security scanning scope
3. Update test execution parameters
4. Configure artifact retention policies

This workflow provides a solid foundation for maintaining code quality and security in the Nox API project while being adaptable to future needs.