# Copilot Instructions for NOX API Repository

## 📋 Repository Overview

**NOX API** is a secure, sandboxed execution platform built on FastAPI for autonomous computational chemistry workflows. It combines secure Python/shell execution with advanced AI agent capabilities, designed for computational chemistry research and automation.

**Project Type:** Python FastAPI web service with async task processing  
**Primary Language:** Python 3.11+ (tested with Python 3.12.3)  
**Framework:** FastAPI 0.116.1 + Uvicorn 0.35.0  
**Key Dependencies:** Dramatiq (task queue), Redis (job storage), pytest (testing)  
**Repository Size:** ~160+ Python files, 162+ markdown documentation files  
**Test Suite:** 60 passing tests, runs in ~2 seconds

### Key Features
- 🤖 **NOX Agent**: Autonomous coding system with file operations and LLM integration
- ⚗️ **XTB Integration**: Quantum chemistry computation workflows with JSON parsing
- 🔒 **Secure Execution**: Sandboxed environment with comprehensive safety guardrails
- 📊 **Job Management**: Asynchronous task processing with Redis-backed state tracking
- 🔑 **OAuth2 + IAM**: Advanced authentication and role-based access control

## 🏗️ Project Architecture

### Directory Structure

```
/home/runner/work/nox/nox/          # Repository root
├── api/                            # FastAPI application (PRIMARY - use this)
│   ├── main.py                     # Application entry point
│   ├── routes/                     # API endpoint routers
│   │   ├── jobs.py                 # Job management endpoints
│   │   ├── predict.py              # Prediction endpoints
│   │   └── agent.py                # Agent control endpoints
│   ├── services/                   # Business logic services
│   │   ├── jobs_store.py           # Redis + InMemory job storage
│   │   └── queue.py                # Job submission & execution
│   └── schemas/                    # Pydantic data models
│
├── nox/                            # Core business logic modules
│   ├── jobs/                       # Job lifecycle management
│   ├── artifacts/                  # Cube generation & artifacts
│   ├── chemistry/                  # Chemistry computation modules
│   ├── parsers/                    # XTB output parsers
│   └── runners/                    # Execution runners
│
├── agent/                          # NOX Agent autonomous system
│   ├── executor.py                 # Agent execution logic
│   ├── planner.py                  # Task planning
│   ├── reporter.py                 # Result reporting
│   ├── payloads/                   # Offline plan files
│   └── tasks/                      # Task backlogs
│
├── workers/                        # Background job processing
│   └── jobs_worker.py              # Dramatiq actors
│
├── tests/                          # Comprehensive test suite
│   ├── test_api_minimal.py         # Basic API tests
│   ├── test_ci_validation.py       # CI smoke tests
│   ├── jobs/                       # Job system tests (27 tests)
│   ├── unit/                       # Unit tests (7 tests)
│   ├── e2e/                        # End-to-end tests
│   ├── agent/                      # Agent tests
│   ├── cube/                       # Cube generation tests
│   └── xtb/                        # XTB integration tests
│
├── scripts/                        # Operational scripts
├── docs/                           # Comprehensive documentation (162+ files)
├── k8s/                           # Kubernetes deployment configs
└── docker-compose.yml             # Docker development setup
```

### Configuration Files

- **pyproject.toml** - Poetry project metadata, ruff/isort/black config
- **pytest.ini** - Pytest configuration (asyncio mode, test paths)
- **.flake8** - Flake8 linting rules (line length 88, ignores E203, W503, E501)
- **.pre-commit-config.yaml** - Pre-commit hooks (ruff, black, isort, mypy)
- **requirements.txt** - Production dependencies
- **dev-requirements.txt** - Development and testing dependencies
- **Makefile** - Development workflow automation
- **.gitignore** - Excludes .venv/, .pytest_cache/, *.log, etc.

## 🔨 Build and Validation Commands

### ⚠️ CRITICAL: Dependencies Must Be Installed First

**ALWAYS run pip install commands before any other operations:**

```bash
# Install production dependencies (REQUIRED)
pip install -r requirements.txt

# Install development dependencies (REQUIRED for testing/linting)
pip install -r dev-requirements.txt
```

**Time:** pip install takes 30-60 seconds for requirements.txt, 45-90 seconds for dev-requirements.txt

### Testing Commands

**Run all tests (PRIMARY command for validation):**
```bash
# Full test suite - 60 tests pass in ~2 seconds
PYTHONPATH=. JOBS_FORCE_LOCAL=1 pytest -q

# Verbose output
PYTHONPATH=. JOBS_FORCE_LOCAL=1 pytest -v
```

**Run specific test suites:**
```bash
# Job system tests (27 tests, ~1s)
PYTHONPATH=. pytest tests/jobs -v

# Unit tests (7 tests, <1s)
PYTHONPATH=. pytest tests/unit -v

# CI validation tests (3 tests, <1s)
PYTHONPATH=. pytest tests/test_ci_validation.py -v

# End-to-end tests
PYTHONPATH=. JOBS_FORCE_LOCAL=1 pytest tests/e2e -v
```

**⚠️ CRITICAL Environment Variables:**
- `PYTHONPATH=.` - Required to resolve imports
- `JOBS_FORCE_LOCAL=1` - Forces local execution, prevents Redis connection errors
- Use these for ALL pytest commands

### Linting and Formatting

**Check code formatting (does not modify files):**
```bash
# Check black formatting (7 files need reformatting as of baseline)
black --check .

# Run flake8 linting (multiple whitespace/unused var issues in baseline)
flake8 .

# Check import sorting
isort --check-only .
```

**Fix formatting issues:**
```bash
# Auto-format with black
black .

# Fix import order
isort .

# Run ruff with auto-fix
ruff check --fix .
```

**Expected baseline state:** Some files have formatting issues - this is normal. Only fix files you modify.

### Running the API Server

**Development mode (recommended):**
```bash
# Using Makefile (starts in background, port 8080)
make run

# Or manually with reload (foreground, port 8080)
PYTHONPATH=. python -m uvicorn api.main:app --reload --port 8080
```

**Check API health:**
```bash
curl http://localhost:8080/health
# Expected: {"status":"ok"}
```

**Stop background server:**
```bash
make api-stop
```

### Background Workers

**Start Dramatiq worker (requires Redis):**
```bash
# Start Redis first
make redis  # or: redis-server --daemonize yes

# Start worker
make worker
# Or: python -m dramatiq api.routes.jobs --processes 1 --threads 1
```

**Note:** Tests work without Redis when using `JOBS_FORCE_LOCAL=1`

### Makefile Targets

The Makefile provides convenient shortcuts:

```bash
make help      # Show all available commands
make test      # Run pytest test suite (PYTHONPATH set automatically)
make run       # Start API server on port 8080
make worker    # Start background worker
make redis     # Start Redis (local or Docker)
make status    # Check service status
make clean     # Clean temporary files (*.pyc, __pycache__, etc.)
make validate  # Run environment validation script
```

## 🔍 CI/CD Pipeline

### GitHub Actions Workflows

**Primary CI Workflow:** `.github/workflows/docker-build.yml`

**Test Job** (runs on every push/PR):
1. Starts PostgreSQL and Redis services
2. Sets up Python 3.11
3. Installs dependencies: `pip install -r requirements.txt` and `pip install -r dev-requirements.txt`
4. Initializes test database (if `scripts/init-db.sql` exists)
5. Runs tests: `python -m pytest tests/ -v`
6. **Environment variables set:**
   - `DATABASE_URL=postgresql://test_user:test_password@localhost:5432/nox_test`
   - `JWT_SECRET_KEY=test_secret_key_for_ci`
   - `REDIS_URL=redis://localhost:6379/0`
   - `JOBS_FORCE_LOCAL=true`
   - `DISABLE_MULTINODE=true`
   - `CI_ENVIRONMENT=true`

**Build Job:**
- Builds multi-platform Docker images (linux/amd64, linux/arm64)
- Pushes to GitHub Container Registry (ghcr.io)
- Uses Docker layer caching for efficiency

**Security Scan Job:**
- Runs Trivy security scanning on built images
- Uploads results to GitHub Security tab

**Other Workflows:**
- `cd.yml` - Continuous deployment (staging/production simulation)
- `deploy-pi.yml` - Raspberry Pi deployment
- `dependabot-automerge.yml` - Auto-merge Dependabot PRs
- `agent-nightly.yml` - Nightly agent tests
- `auto-label.yml` - PR auto-labeling

### Pre-commit Hooks

If using pre-commit hooks (`.pre-commit-config.yaml`):
```bash
# Install hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

**Hooks configured:** ruff, black, isort, mypy, detect-secrets

## 🚨 Common Issues and Workarounds

### Issue: Redis Connection Errors During Tests

**Symptom:** `redis.exceptions.ConnectionError: Error 111 connecting to localhost:6379`

**Workaround:** Use `JOBS_FORCE_LOCAL=1` environment variable:
```bash
JOBS_FORCE_LOCAL=1 pytest tests/
```

This forces local execution without Redis, suitable for testing.

### Issue: Import Errors

**Symptom:** `ModuleNotFoundError: No module named 'api'` or similar

**Solution:** Always set `PYTHONPATH=.` before running Python commands:
```bash
PYTHONPATH=. pytest tests/
PYTHONPATH=. python -m uvicorn api.main:app
```

### Issue: Black Formatting Conflicts

**Symptom:** Black reports files would be reformatted

**Expected:** Baseline has ~7 files that need formatting. Only reformat files you modify.

**Fix specific files:**
```bash
black path/to/modified/file.py
```

### Issue: Tests Timeout or Hang

**Common cause:** XTB binary not found, tests waiting for external process

**Solution:** Use hermetic/local mode with `JOBS_FORCE_LOCAL=1` to bypass XTB dependency

### Issue: Port Already in Use

**Symptom:** `Address already in use` when starting API

**Solution:**
```bash
# Check what's using port 8080
lsof -i :8080

# Kill the process (use specific PID, not pkill)
kill <PID>

# Or use different port
uvicorn api.main:app --port 8081
```

## 📝 Making Changes

### Workflow for Code Changes

1. **Understand current state:**
   ```bash
   git status
   git branch
   ```

2. **Install dependencies if not already done:**
   ```bash
   pip install -r requirements.txt
   pip install -r dev-requirements.txt
   ```

3. **Make your changes** to relevant files

4. **Run targeted tests:**
   ```bash
   # Test specific area you changed
   PYTHONPATH=. pytest tests/jobs -v  # if you changed job code
   PYTHONPATH=. pytest tests/unit -v  # if you changed core logic
   ```

5. **Format your changes:**
   ```bash
   black path/to/changed/file.py
   isort path/to/changed/file.py
   ```

6. **Run full test suite before committing:**
   ```bash
   PYTHONPATH=. JOBS_FORCE_LOCAL=1 pytest -q
   ```

7. **Check for obvious linting issues:**
   ```bash
   flake8 path/to/changed/file.py
   ```

### Testing Philosophy

- **Tests are fast:** Full suite runs in ~2 seconds
- **Run tests early and often:** After each significant change
- **Use targeted tests:** Run specific test files while developing
- **Full suite before commit:** Always run full suite to catch regressions
- **CI will catch issues:** But local testing saves time

### API Structure Note

**IMPORTANT:** Use the `api/` directory structure. Do not consolidate or move code between `api/`, `nox_api/`, or `nox-api/` directories unless explicitly requested. The current canonical structure uses `api/` as the main application package.

## 🔐 Security Considerations

- **Sandboxed Execution:** All code execution happens in restricted environments
- **File Operation Allowlists:** Agent has restricted file access
- **No Secrets in Code:** Use environment variables, never hardcode credentials
- **Safety Guardrails:** Agent operations have comprehensive safety checks

## 🎯 Quick Reference

**Most common commands you'll use:**

```bash
# Setup (once)
pip install -r requirements.txt
pip install -r dev-requirements.txt

# Testing (frequent)
PYTHONPATH=. JOBS_FORCE_LOCAL=1 pytest -q

# Development
PYTHONPATH=. python -m uvicorn api.main:app --reload --port 8080

# Code quality
black .
flake8 .
```

**Always remember:**
- Set `PYTHONPATH=.` for Python commands
- Set `JOBS_FORCE_LOCAL=1` for tests
- Install dependencies first thing
- Tests run in ~2 seconds - use them frequently
- Format code with `black` before committing

## 📚 Additional Resources

- **Comprehensive docs:** `docs/` directory has 162+ documentation files
- **Project status:** `docs/PROJECT_STATUS_2025-08-19.md`
- **README:** `README.md` for quick overview
- **Project structure:** `PROJECT_STRUCTURE.md` for detailed architecture
- **Development workflow:** `docs/dev/DEV-WORKFLOW.md`
- **Root .copilot-instructions.md:** Contains session protocols and documentation standards

## ✅ Trust These Instructions

These instructions have been validated by:
- Running complete dependency installation
- Executing full test suite (60 tests pass)
- Testing linting tools (black, flake8, isort)
- Verifying CI workflow configuration
- Testing common development commands
- Documenting observed issues and workarounds

If something doesn't work as documented, first verify:
1. Dependencies are installed (`pip list | grep -E "pytest|fastapi"`)
2. You're using `PYTHONPATH=.` for Python commands
3. You're using `JOBS_FORCE_LOCAL=1` for tests
4. You're in the repository root directory (`/home/runner/work/nox/nox`)

If issues persist, you may need to search/explore further, but these instructions cover 95% of common development tasks.
