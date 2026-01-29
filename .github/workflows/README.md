# GitHub Actions Workflows

This directory contains the GitHub Actions workflows for the Nox project.

## Workflow Architecture

The workflows are designed with a standardized, reusable approach to minimize duplication and ensure consistency.

### 🏗️ Reusable Actions

Located in `.github/actions/`:

- **setup-python-env**: Standardized Python environment setup with dependency caching
- **setup-test-db**: Database initialization for testing

### 🔧 Core Workflows

#### python-ci.yml
**Purpose**: Comprehensive Python CI pipeline (standard baseline for all Python projects)
- **Triggers**: Push to main/develop branches, pull requests to main, manual dispatch
- **Jobs**:
  - `lint`: Code quality checks (black, isort, flake8, ruff)
  - `security`: Security scanning (bandit, safety, pip-audit)
  - `test`: Unit tests with PostgreSQL and Redis services
  - `sbom`: Software Bill of Materials generation (main branch only)
  - `summary`: Aggregated CI results
- **Artifacts**: Security reports, coverage reports, SBOM

#### docker-build.yml
**Purpose**: Docker image building and security scanning
- **Triggers**: Push to main/develop branches, pull requests to main, version tags
- **Jobs**:
  - `ci`: Calls python-ci.yml for testing (reusable workflow)
  - `build`: Builds multi-architecture Docker images (linux/amd64, linux/arm64)
  - `security-scan`: Performs Trivy security scanning on built images
- **Outputs**: Docker images pushed to GitHub Container Registry (GHCR)

#### cd.yml
**Purpose**: Continuous Deployment pipeline
- **Triggers**: Completion of "Docker Build and Deploy" workflow, manual dispatch
- **Jobs**:
  - `check-readiness`: Validates deployment prerequisites
  - `deploy-staging`: Deploys to staging environment with health checks
  - `deploy-production`: Deploys to production with validation
  - `monitor`: Post-deployment monitoring and validation
- **Dependencies**: Waits for successful completion of docker-build.yml

#### agent-nightly.yml
**Purpose**: Automated agent execution for maintenance tasks
- **Triggers**: Daily cron schedule (3 AM UTC), manual dispatch
- **Jobs**:
  - `agent`: Runs the Nox agent for automated maintenance and tasks
- **Requirements**: OPENAI_API_KEY secret must be configured
- **Implementation**: Uses reusable setup-python-env action

### 🏷️ Utility Workflows

#### auto-label.yml
**Purpose**: Automatic PR labeling based on content and author
- **Triggers**: Pull request events (opened, synchronized)
- **Labels**: dependencies, automerge-candidate, ci, workflow, hygiene, docs, triage

#### dependabot-automerge.yml
**Purpose**: Automatic merging of Dependabot PRs
- **Triggers**: Pull request target events, check suite completion
- **Behavior**: Enables auto-merge for Dependabot PRs with "automerge-candidate" label

#### deploy-pi.yml
**Purpose**: Deployment to Raspberry Pi
- **Triggers**: Push to main, manual dispatch
- **Requires**: PI_HOST, PI_USER, PI_SSH_KEY secrets

#### super-linter.yml
**Purpose**: Multi-language linting
- **Triggers**: Push to main, pull requests to main
- **Behavior**: Runs GitHub Super-Linter on changed files

## Workflow Dependencies

```
python-ci.yml (Base CI)
       ↓
docker-build.yml (CI + Docker) → cd.yml (CD) → Production Deployment
       ↓
agent-nightly.yml (Maintenance)
```

## Configuration Requirements

### Secrets Required
- `OPENAI_API_KEY`: For agent workflow functionality
- `GITHUB_TOKEN`: Automatically provided by GitHub Actions
- `PI_HOST`, `PI_USER`, `PI_SSH_KEY`: For Raspberry Pi deployment (optional)

### Repository Settings
- Container Registry: Configured to use GitHub Container Registry (ghcr.io)
- Branch Protection: Main branch should be protected to ensure workflows run on PRs

## Design Principles

1. **Reusability**: Common setup steps extracted into composite actions
2. **Standardization**: python-ci.yml serves as the base for all Python CI
3. **Modularity**: Each workflow has a single, clear responsibility
4. **Efficiency**: Workflow reuse reduces duplication and maintenance burden
5. **Security**: Multiple layers of security scanning (code, dependencies, containers)

## Recent Refactoring (2026-01-27)

**Standardization Phase**: Implemented standardized workflow architecture:
- ✅ Created `python-ci.yml` as standard Python CI workflow
- ✅ Created reusable composite actions for common setup tasks
- ✅ Refactored `docker-build.yml` to call python-ci.yml workflow
- ✅ Refactored `agent-nightly.yml` to use reusable actions
- ✅ Eliminated code duplication across workflows
- ✅ Improved maintainability and consistency

**Previous Cleanup (2025-08-20)**: Removed duplicate workflows to eliminate CI/CD pipeline conflicts:
- ❌ Removed `ci.yml` (duplicate of docker-build.yml functionality)
- ❌ Removed `ci-fixed.yml` (duplicate of ci.yml)