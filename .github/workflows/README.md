# GitHub Actions Workflows

This directory contains the GitHub Actions workflows for the Nox project.

## Active Workflows

### 🔧 docker-build.yml
**Purpose**: Docker container building and publishing
- **Triggers**: Push to main/develop branches, pull requests to main, version tags
- **Jobs**:
  - `test`: Runs unit tests with PostgreSQL and Redis services
  - `build`: Builds multi-architecture Docker images (linux/amd64, linux/arm64)
  - `security-scan`: Performs Trivy security scanning on built images
- **Python Version**: 3.13-alpine (updated)
- **Outputs**: Docker images pushed to GitHub Container Registry (GHCR)

### 🚀 cd.yml
**Purpose**: Continuous Deployment pipeline
- **Triggers**: Completion of "Docker Build and Deploy" workflow, manual dispatch
- **Jobs**:
  - `check-readiness`: Validates deployment prerequisites
  - `deploy-staging`: Deploys to staging environment with health checks
  - `deploy-production`: Deploys to production with validation
  - `monitor`: Post-deployment monitoring and validation
- **Dependencies**: Waits for successful completion of docker-build.yml

### 🤖 agent-nightly.yml
**Purpose**: Automated agent execution for maintenance tasks
- **Triggers**: Daily cron schedule (3 AM UTC), manual dispatch
- **Jobs**:
  - `agent`: Runs the Nox agent for automated maintenance and tasks
- **Python Version**: 3.13 (updated)
- **Requirements**: OPENAI_API_KEY secret must be configured

### 🚀 deploy-pi.yml (disabled)
**Purpose**: Deployment to Raspberry Pi environment  
- **Status**: Manually disabled
- **SSH Action**: Updated to v1.2.2
- **Python Version**: 3.13 ready

## Workflow Dependencies

```
docker-build.yml (CI) → cd.yml (CD) → Production Deployment
                    ↓
              agent-nightly.yml (Maintenance)
```

## Configuration Requirements

### Secrets Required
- `OPENAI_API_KEY`: For agent workflow functionality
- `GITHUB_TOKEN`: Automatically provided by GitHub Actions

### Repository Settings
- Container Registry: Configured to use GitHub Container Registry (ghcr.io)
- Branch Protection: Main branch should be protected to ensure workflows run on PRs

## Recent Modernization (2024-09-14)

**Major Infrastructure Update**: Complete modernization of CI/CD pipelines and Python ecosystem:

### ✅ Python 3.13 Adoption
- **All workflows** upgraded from Python 3.11 → 3.13
- **Docker images** updated to python:3.13-alpine
- **Agent workflows** modernized for latest Python features
- **Performance benefits** from Python 3.13 improvements

### ✅ GitHub Actions Security Update  
- **actions/setup-python** v5 → v6 (Node.js 20, enhanced caching)
- **tj-actions/changed-files** v45 → v47 (latest file detection)
- **appleboy/ssh-action** v0.1.10 → v1.2.2 (security patches)
- **docker/build-push-action** v5 → v6 (build summaries, attestations)

### ✅ New Workflows Added
- **lint.yml**: Dedicated linting pipeline with black, isort, flake8, ruff
- **Enhanced auto-labeling**: Improved PR categorization and Dependabot handling
- **Non-blocking quality**: Linting warnings don't block development

### ✅ Workflow Consolidation
- **python-ci.yml**: Comprehensive CI with security scanning and SBOM generation
- **Reduced duplication**: Eliminated redundant workflow patterns
- **Consistent tooling**: All workflows use same Python and action versions

## Previous Cleanup (2025-08-20)

**Workflow Duplication Cleanup**: Removed duplicate workflows to eliminate CI/CD pipeline conflicts:
- ❌ Removed `ci.yml` (duplicate of docker-build.yml functionality)
- ❌ Removed `ci-fixed.yml` (duplicate of ci.yml)
- ✅ Kept `docker-build.yml` as primary CI pipeline (referenced by CD workflow)
- ✅ Kept `cd.yml` as deployment pipeline
- ✅ Kept `agent-nightly.yml` for automated maintenance

This cleanup eliminates workflow duplication while maintaining all required functionality.