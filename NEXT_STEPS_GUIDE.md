# NOX Project - Next Steps Guide
**Date**: January 27, 2026  
**Status**: Current Repository State Analysis & Recommendations  
**Version**: 1.0

---

## 📋 Executive Summary

This guide provides a comprehensive overview of the NOX project's current state and actionable next steps. The NOX API is a secure, sandboxed execution platform for autonomous computational chemistry workflows, featuring FastAPI-based architecture with job management, XTB integration, and AI agent capabilities.

**Current State**: Production-ready core system with recent API schema refactoring completed. Multiple development tracks are ready for advancement.

---

## 🎯 Current Project Status

### ✅ Recently Completed (January 2026)
- **API Schema Refactoring** - All POST endpoints now use typed Pydantic models
- **Legacy Code Cleanup** - Removed deprecated `nox-api/` directory
- **Test Suite** - 56 passing tests, 2 skipped, 0 warnings
- **JOBS-002 Fix** - Cross-process synchronization with Redis backend
- **Queue Improvements** - Proper artifact status handling and error responses

### 🏗️ Core Architecture (Stable)
- **API Layer**: FastAPI with routes for jobs, predictions (CJ/VoD), and agents
- **Job System**: Redis-backed with Dramatiq workers for distributed processing
- **XTB Integration**: Quantum chemistry computation workflows
- **Agent System**: Autonomous coding capabilities with file operations
- **Testing**: Comprehensive test suite with 44+ job system tests

### 📂 Repository Organization
```
nox/
├── api/                    # FastAPI application
│   ├── main.py            # Application entry point
│   ├── routes/            # Endpoints (jobs, predict, agent)
│   ├── services/          # Business logic
│   └── schemas/           # Pydantic models
├── nox/                   # Core modules
│   ├── jobs/              # Job management
│   ├── artifacts/         # Cube generation
│   ├── chemistry/         # Chemistry computations
│   ├── parsers/           # Data parsers
│   └── runners/           # Execution engines
├── workers/               # Background processing
├── tests/                 # Test suite (60+ tests)
├── docs/                  # Comprehensive documentation
└── scripts/               # Development & deployment tools
```

---

## 🚀 Recommended Next Steps - Priority Order

### Priority 1: Merge Pending Pull Requests (IMMEDIATE)

**Context**: There are 5 open PRs ready to merge according to `MERGE_PLAN_2025-01-26.md`

**Action Items**:
1. ✅ **PR #55** - Feature/api-schemas-routes (READY - merge first)
   - 8 new modules, 1000+ LOC, complete test coverage
   - Risk: LOW
   
2. ✅ **PR #51** - GitHub Actions updates (CI/CD only)
   - 7 version bumps for Actions (checkout v5→v6, setup-python v4→v6)
   - Risk: MINIMAL
   
3. ✅ **PR #54** - authlib 1.6.3 → 1.6.6 (patch update)
   - Risk: MINIMAL
   
4. ✅ **PR #53** - Python dependencies (21 packages including Dramatiq 2.0)
   - dramatiq 1.14.2 → 2.0.0, redis 6.4.0 → 7.1.0, pytest 8.4.2 → 9.0.2
   - **Already tested**: All 60 tests pass with these versions
   - Risk: MEDIUM (but verified)
   
5. ❌ **PR #52** - Close (superseded by PR #53)

**Command Sequence**:
```bash
# Merge in order: PR #55 → #51 → #54 → #53
# Close PR #52 with comment explaining supersession
# After all merges, tag release: git tag -a v0.2.0 -m "Feature release with Dramatiq 2.0"
```

**Estimated Time**: 30-60 minutes  
**Impact**: HIGH - Unblocks development, updates dependencies, improves CI/CD

---

### Priority 2: Repository Hygiene - Stage 1 (HIGH PRIORITY)

**Context**: Repository contains multiple documentation and configuration files that need organization per `triage_nox.md` and `PR_HYGIENE_STAGE1.md`

**Phase 1: Documentation Consolidation** (1-2 days)
- ✅ `docs/INDEX.md` exists - centralized documentation index
- ⏳ Move legacy reports to `docs/legacy/` (session-reports, progress-reports, milestone-reports)
- ⏳ Update `docs/README.md` to reference only active documentation
- ⏳ Verify all links in documentation

**Phase 2: Refactoring Issues** (Create GitHub issues)
According to `REFACTOR_ISSUES.md`, create these issues with labels `[refactor, hygiene]`:

1. **Refactor: requirements-phase2.txt**
   - Consolidate into `pyproject.toml` with optional dependency groups
   - Remove duplication between `requirements.txt`, `requirements-phase2.txt`, and `pyproject.toml`

2. **Refactor: agent/tools/**
   - Prepare for `nox_core` extraction
   - Define clear public interfaces
   - Add comprehensive type hints and tests

3. **Refactor: ai/**
   - Isolate AI interfaces
   - Add unit tests and type hints
   - Document all public APIs

4. **Refactor: .github/workflows/**
   - Standardize all workflows using python-ci pattern
   - Reduce duplication across workflow files

5. **Refactor: scripts/*.sh**
   - Add documentation headers
   - Implement environment validation
   - Improve error handling

**Command to Create Issues**:
```bash
gh issue create --title "Refactor: requirements-phase2.txt" \
  --label "refactor,hygiene" \
  --body "Consolidate requirements-phase2.txt into pyproject.toml for dependency management"
# Repeat for other refactor tasks
```

**Estimated Time**: 2-3 days for full hygiene pass  
**Impact**: MEDIUM - Improves maintainability and onboarding

---

### Priority 3: Outstanding Technical Tasks (HIGH PRIORITY)

**JOBS-002: Enhanced Job Polling** (Partially Complete)
- ✅ Redis-backed storage implemented
- ✅ Cross-process synchronization working
- ⏳ End-to-end workflow testing needed
- ⏳ State polling optimization

**Action**: Add comprehensive E2E tests for job lifecycle
```bash
# Test scenarios to implement:
# 1. Job submission → execution → completion flow
# 2. Error handling and retry logic
# 3. Artifact generation and retrieval
# 4. Multiple concurrent jobs
```

**XTBA-001: XTB Integration** (Partially Complete)
- ✅ XTB parser implemented
- ✅ Offline plan injection working
- ⏳ Runner integration needs verification
- ⏳ Full E2E XTB workflow testing

**Action**: Complete XTB integration testing
```bash
make test-e2e  # Run end-to-end XTB tests
# Document XTB workflow in docs/guides/
```

**File-Operations System v0.2** (Complete but needs documentation)
- ✅ 24x performance improvement achieved
- ⏳ User documentation needed
- ⏳ Migration guide for users of old system

**Estimated Time**: 3-5 days  
**Impact**: HIGH - Core functionality stability

---

### Priority 4: Developer Experience Improvements (MEDIUM PRIORITY)

**A. Enhanced Development Workflow** (1-2 days)

Current state: Good Makefile with api-start/stop commands

Improvements:
1. **Add development documentation**
   ```bash
   # Create docs/dev/GETTING_STARTED.md with:
   # - Quick setup instructions
   # - Common development commands
   # - Troubleshooting guide
   ```

2. **Improve local development setup**
   ```bash
   # Add to Makefile:
   dev-setup:  ## One-command development setup
       @pip install -r requirements.txt -r dev-requirements.txt
       @pre-commit install
       @make redis
       @echo "✅ Development environment ready"
   
   dev-all:    ## Start all services for development
       @make redis
       @make api-start
       @make worker
       @echo "🚀 All services running"
   ```

3. **Add hot-reload for worker**
   - Current: Worker requires manual restart
   - Improvement: Use watchdog for auto-reload during development

**B. Testing Improvements** (1-2 days)

1. **Test organization**
   - Create test categories: unit, integration, e2e
   - Add pytest markers for selective test running
   ```python
   # pytest.ini
   [pytest]
   markers =
       unit: Unit tests (fast, no external dependencies)
       integration: Integration tests (requires Redis/services)
       e2e: End-to-end tests (full system)
       slow: Tests that take >1 second
   ```

2. **Coverage improvements**
   - Current: Coverage tracking exists
   - Target: 80%+ coverage for core modules
   ```bash
   make test-coverage:  ## Run tests with coverage report
       @pytest --cov=api --cov=nox --cov-report=html --cov-report=term
       @echo "Coverage report: htmlcov/index.html"
   ```

**Estimated Time**: 2-3 days  
**Impact**: MEDIUM - Improves developer productivity

---

### Priority 5: Feature Development (MEDIUM-LOW PRIORITY)

**A. API Extensions** (2-3 days)

Add useful endpoints for file management and monitoring:

```python
# api/routes/files.py
GET  /api/files              # List sandbox files
GET  /api/files/{path}       # Get file content
DELETE /api/files/{path}     # Delete file
POST /api/files/search       # Search in files

# api/routes/system.py  
GET  /api/system/stats       # System statistics
GET  /api/system/health      # Detailed health check
POST /api/sandbox/clean      # Clean temporary files
GET  /api/history            # Execution history
```

**B. CLI Enhancements** (1-2 days)

Extend `scripts/noxctl` with additional commands:

```bash
noxctl ls [path]                 # List sandbox files
noxctl cat <file>                # Show file content
noxctl rm <file>                 # Remove file/directory
noxctl logs [--tail=N]           # Show API logs
noxctl status --full             # Detailed system status
noxctl sandbox-clean             # Clean temporary files
noxctl backup <name>             # Backup sandbox
noxctl restore <backup>          # Restore backup
```

**C. Monitoring & Observability** (2-3 days)

Implement production-grade monitoring:

```python
# Add Prometheus metrics
GET /metrics                     # Prometheus format metrics

# Add structured logging
from structlog import get_logger
logger = get_logger()

# Add request tracing
# - Request ID propagation
# - Execution time tracking
# - Error rate monitoring
```

**Estimated Time**: 5-7 days total  
**Impact**: MEDIUM - Enhances usability and operations

---

### Priority 6: Production Readiness (LOW PRIORITY - Future)

**A. Containerization Improvements** (1-2 days)
- Current: Basic Dockerfile exists
- Improvements:
  - Multi-stage builds for smaller images
  - Non-root user for security
  - Health checks in docker-compose
  - Volume management best practices

**B. Security Hardening** (2-3 days)
- Input validation improvements
- Rate limiting implementation
- API key rotation mechanism
- Audit logging enhancements

**C. Documentation Completion** (2-3 days)
- API documentation (OpenAPI/Swagger)
- Architecture diagrams
- Deployment guides (Docker, K8s)
- Troubleshooting playbook

**Estimated Time**: 5-8 days  
**Impact**: MEDIUM - Required for production deployment

---

## 🔄 Integration with Other Repositories

### Context: NOX + IAM 2.0 Integration

According to project documentation, NOX is designed to integrate with other services:
- **IAM 2.0**: Authentication and authorization service
- **XTB**: Quantum chemistry computation backend

**Integration Strategy** (Option A - Separate Repos):
1. Keep repositories separate
2. Integrate via SDK packages and API calls
3. Use OAuth2 for authentication flow
4. Publish SDKs to GitHub Packages for distribution

**Note**: This guide focuses on NOX repository. For IAM 2.0 and other repositories, please:
1. Review their respective documentation
2. Check integration points defined in `docs/planning/CONNECTING_NOX_IAM.md`
3. Coordinate OAuth2 configuration between services
4. Test end-to-end authentication flows

---

## 📊 Progress Tracking

### Current Milestone Status

**Phase 3.3: Interactive Documentation**
- Progress: ~67% complete (4/6 milestones)
- ✅ M9.1: Base UI (Next.js + TypeScript SDK)
- ✅ M9.2: AI Helper & Payload Suggestions
- ✅ M9.3: Live API Explorer + Auth
- ✅ M9.4: SDK Generator
- ⏳ M9.5: Advanced UI Polish
- ⏳ M9.6: Performance Optimization

**Upcoming Phases**:
- M10: Jobs Core + Database with IAM integration
- M11: Multi-node architecture
- M12: Production deployment

### Weekly Action Plan

**Week 1: Foundation & Cleanup**
- Day 1: Merge all pending PRs
- Day 2-3: Repository hygiene (move legacy docs, create refactor issues)
- Day 4-5: Complete JOBS-002 and XTBA-001 E2E testing

**Week 2: Developer Experience**
- Day 1-2: Improve development workflow and documentation
- Day 3-4: Enhance testing infrastructure
- Day 5: Test coverage improvements

**Week 3: Features & Extensions**
- Day 1-2: API extensions (file management, system endpoints)
- Day 3: CLI enhancements
- Day 4-5: Monitoring and observability

**Week 4: Polish & Documentation**
- Day 1-2: Production readiness (containerization, security)
- Day 3-4: Documentation completion
- Day 5: Release preparation and tagging

---

## 🛠️ Quick Start Commands

### Development Setup
```bash
# Clone repository (if not already done)
git clone https://github.com/lewispoul/nox.git
cd nox

# Install dependencies
pip install -r requirements.txt -r dev-requirements.txt

# Start services
make redis           # Start Redis for job queue
make api-start       # Start API in background
make worker          # Start Dramatiq worker

# Run tests
make test           # Run all tests
make test-e2e       # Run end-to-end tests

# View logs
make api-logs       # Tail API logs

# Stop services
make api-stop       # Stop API server
```

### Common Development Tasks
```bash
# Check service status
make status

# Clean up
make clean

# Run specific test suite
pytest tests/jobs/ -v

# Check test coverage
pytest --cov=api --cov=nox --cov-report=html

# Format code
black api/ nox/ tests/
isort api/ nox/ tests/

# Lint code
ruff check api/ nox/ tests/
```

---

## 📚 Key Documentation References

### Project Documentation
- **README.md** - Project overview and quick start
- **PROJECT_STRUCTURE.md** - Detailed architecture (v8.0.0)
- **MasterPlan** - Original French master plan with detailed steps
- **docs/README.md** - Documentation index

### Technical Documentation
- **docs/SESSION_SUMMARY_2026-01-26.md** - Latest session summary
- **docs/PROJECT_STATUS_2025-08-19.md** - Comprehensive project status
- **MERGE_PLAN_2025-01-26.md** - PR merge strategy and verification

### Development Guides
- **Makefile** - Development commands and targets
- **pyproject.toml** - Project configuration
- **pytest.ini** - Test configuration

### Planning Documents
- **docs/planning/IMMEDIATE_NEXT_STEPS.md** - Quick win recommendations
- **docs/planning/PROJECT_NEXT_STEPS.md** - Milestone roadmap
- **triage_nox.md** - Repository organization plan
- **REFACTOR_ISSUES.md** - Planned refactoring tasks

---

## ⚠️ Known Issues & Limitations

### Current Known Issues
1. **Test Coverage**: Some modules lack comprehensive tests (target: 80%+)
2. **Documentation**: Some modules need inline documentation
3. **Error Handling**: Some edge cases need better error messages
4. **Performance**: Job polling could be optimized for high load

### Technical Debt
1. **requirements-phase2.txt**: Should be consolidated into pyproject.toml
2. **agent/tools/**: Needs refactoring for nox_core extraction
3. **Legacy Code**: Some deprecated scripts still present in archive/
4. **Workflow Duplication**: GitHub Actions workflows need standardization

---

## 🎯 Success Criteria

### Definition of Done for Next Phase
- [ ] All 5 pending PRs merged successfully
- [ ] Repository hygiene issues created and tracked
- [ ] Test coverage at 80%+ for core modules
- [ ] JOBS-002 and XTBA-001 fully tested end-to-end
- [ ] Development documentation complete and accessible
- [ ] All critical paths have integration tests
- [ ] Monitoring and logging in place for production use

### Quality Gates
- All tests passing (target: 60+ tests, 0 failures)
- No security vulnerabilities in dependencies
- Code coverage above 80% for new code
- Documentation updated for all new features
- PR reviews completed before merge

---

## 🤝 Contributing Guidelines

### Before Starting Work
1. Check open issues and PRs to avoid duplication
2. Review relevant documentation in `docs/`
3. Set up development environment using commands above
4. Run tests to ensure baseline is working

### Development Workflow
1. Create feature branch from `main`
2. Make changes following existing code style
3. Add tests for new functionality
4. Update documentation as needed
5. Run full test suite before committing
6. Create PR with clear description and context

### Code Style
- Follow PEP 8 for Python code
- Use Black for formatting (line length: 88)
- Use isort for import organization
- Add type hints for all functions
- Write docstrings for public APIs

---

## 📞 Getting Help

### Resources
1. **Documentation**: Check `docs/` directory first
2. **Issues**: Search existing GitHub issues
3. **Code Examples**: Review `tests/` for usage patterns
4. **Architecture**: See `PROJECT_STRUCTURE.md` for system design

### Debugging Tips
```bash
# Check service health
curl http://127.0.0.1:8000/health

# View API logs with context
make api-logs

# Run tests in verbose mode
pytest tests/ -v -s

# Check Redis connection
redis-cli ping

# Verify environment
./verify_env.sh
```

---

## 🎓 Learning Path for New Contributors

### Level 1: Setup & Familiarization (Day 1)
1. Clone repository and install dependencies
2. Run development services (Redis, API, Worker)
3. Run test suite and verify all passing
4. Explore API using Swagger UI at http://127.0.0.1:8000/docs

### Level 2: Code Understanding (Days 2-3)
1. Read `PROJECT_STRUCTURE.md` to understand architecture
2. Review main API routes in `api/routes/`
3. Examine job system in `nox/jobs/`
4. Study test patterns in `tests/`

### Level 3: First Contribution (Days 4-5)
1. Pick a "good first issue" from GitHub
2. Implement fix or feature
3. Add tests for your changes
4. Submit PR with clear description

---

## 🚀 Immediate Action Items (This Week)

### Monday
- [ ] Merge PR #55 (Feature/api-schemas-routes)
- [ ] Merge PR #51 (GitHub Actions updates)

### Tuesday  
- [ ] Merge PR #54 (authlib patch)
- [ ] Merge PR #53 (Python dependencies)
- [ ] Close PR #52 with explanation
- [ ] Tag release v0.2.0

### Wednesday
- [ ] Create all 5 refactoring issues from REFACTOR_ISSUES.md
- [ ] Begin moving legacy docs to docs/legacy/

### Thursday
- [ ] Complete JOBS-002 E2E testing
- [ ] Verify XTBA-001 integration

### Friday
- [ ] Write/update development documentation
- [ ] Review and update this guide as needed

---

## 📝 Notes on Other Repositories

**Important**: This guide focuses exclusively on the NOX repository. You mentioned other repositories:

### IAM / IAM-2.0 Repository
- **Purpose**: Authentication and authorization service
- **Integration**: Via SDK and OAuth2
- **Documentation**: See `docs/planning/CONNECTING_NOX_IAM.md` for integration strategy
- **Action Required**: Access IAM repository separately to review its status and next steps

### XTB Repository
- **Purpose**: Quantum chemistry computation backend
- **Integration**: Via API calls and job submissions
- **Current Status**: Parser and offline plan injection working in NOX
- **Action Required**: Access XTB repository for backend-specific work

**To review progress in other repositories**, you would need to:
1. Clone/access each repository separately
2. Review their respective documentation and status
3. Check integration points defined in NOX's planning documents
4. Coordinate feature development across repositories

---

## 📅 Long-Term Roadmap (3-6 Months)

### Month 1: Stability & Testing
- Complete all pending PRs and refactoring
- Achieve 80%+ test coverage
- Full E2E testing for all workflows

### Month 2: Features & Extensions
- API enhancements (file management, monitoring)
- CLI improvements
- Enhanced documentation

### Month 3: Integration & Production
- IAM 2.0 integration completion
- Production deployment preparation
- Performance optimization

### Months 4-6: Scale & Advanced Features
- Multi-node architecture (M11)
- Advanced monitoring and alerting
- Production deployment and operations

---

## ✅ Summary & Recommendations

### Top 3 Immediate Priorities
1. **Merge Pending PRs** (30-60 min) - Unblocks development
2. **Complete JOBS-002/XTBA-001 Testing** (2-3 days) - Ensures stability
3. **Repository Hygiene** (2-3 days) - Improves maintainability

### Quick Wins (Can Start Today)
1. Merge PR #55 and #51 (low risk, high value)
2. Create refactoring issues for tracking
3. Run full test suite to verify current state
4. Update this guide based on findings

### Medium-Term Goals (Next 2 Weeks)
1. Complete all PRs and hygiene work
2. Enhance developer experience
3. Improve test coverage to 80%+
4. Document all major systems

### Success Metrics
- All PRs merged by end of Week 1
- Test coverage at 80%+ by end of Week 2
- Zero critical bugs in production paths
- Complete development documentation

---

**Last Updated**: January 27, 2026  
**Version**: 1.0  
**Maintainer**: NOX Development Team

**Note**: This is a living document. Update after completing major milestones or when priorities change.
