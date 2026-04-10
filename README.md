# NOX API

A secure, sandboxed execution platform built on **FastAPI** for autonomous computational chemistry workflows.

## 🚀 Overview

NOX API combines secure Python/shell execution with advanced AI agent capabilities, designed for computational chemistry research and automation.

**Key Features:**
- 🤖 **NOX Agent**: Autonomous coding system with file operations and LLM integration
- ⚗️ **XTB Integration**: Quantum chemistry computation workflows with JSON parsing
- 🔒 **Secure Execution**: Sandboxed environment with comprehensive safety guardrails
- 📊 **Job Management**: Asynchronous task processing with state tracking
- 🔑 **OAuth2 + IAM**: Advanced authentication and role-based access control

## 📚 Documentation

All documentation has been comprehensively organized in the [`docs/`](./docs/) directory.

**Quick Start:**
- 📖 **[Documentation Index](./docs/INDEX.md)** - Complete documentation overview
- ⭐ **[NEXT STEPS GUIDE](./NEXT_STEPS_GUIDE.md)** - **NEW!** Prioritized roadmap and action items
- 🎯 **[Repository Status](./docs/REPOSITORY_STATUS_SUMMARY.md)** - Current project status
- 📋 **[Latest Session Summary](./docs/SESSION_SUMMARY_2026-01-26.md)** - Recent achievements
- 🚀 **[Deployment Guides](./docs/deployment-guides/)** - Production setup instructions

**Recent Major Achievements (January 2026):**
- ✅ **Documentation Consolidation** - Organized all docs with active/legacy separation
- ✅ **Repository Hygiene** - Cleaned up outdated and duplicate files
- ✅ **IAM 2.0 Integration** - Advanced authentication and role-based access control
- ✅ **Agent System Enhancement** - Improved autonomous coding capabilities
- ✅ **API Stability** - Secure execution platform with comprehensive safeguards

## 🛠️ Quick Setup

```bash
# Clone the repository
git clone https://github.com/lewispoul/nox.git
cd nox

# Install dependencies
pip install -r requirements.txt

# Run the API
python -m uvicorn nox_api:app --host 0.0.0.0 --port 8080
```

## 🎯 Architecture

- **`/api`** - FastAPI application with REST endpoints
- **`/agent`** - NOX Agent system with autonomous coding capabilities  
- **`/nox`** - Core computation modules (XTB, parsers, runners)
- **`/tests`** - Comprehensive test suite with async testing
- **`/docs`** - Complete documentation library (91+ files)
- **`/docs-interactive`** - Interactive documentation website (Next.js)

## 📊 Current Status

**Development Phase:** Advanced autonomous agent integration with production-ready systems.

For detailed status, see [Repository Status](./docs/REPOSITORY_STATUS_SUMMARY.md).

## 🤝 Contributing

1. Review the [Documentation Index](./docs/INDEX.md) for project context
2. Check [Repository Status](./docs/REPOSITORY_STATUS_SUMMARY.md) for active development areas
3. Follow the development protocols in [.copilot-instructions.md](./.copilot-instructions.md)

## 🔒 Security & Safety

NOX API implements comprehensive security measures:
- Sandboxed execution environments with path restrictions
- Bearer token authentication with configurable permissions
- File operation allowlists and size limits
- Comprehensive audit logging and monitoring

## 📄 License

See LICENSE file for details.

---

*For the most current information, always refer to the organized documentation in [`docs/`](./docs/).*
