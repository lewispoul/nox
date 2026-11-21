# NOx — assistant modulaire de laboratoire

Le projet principal est **NOx**. Le pilote laboratoire ChemLab, GasCalc et la
preuve RMN/FID sont des modules de ce projet.

- [Plan des travaux et branches](docs/nox/WORK_PLAN.md)
- [Lancer le pilote local et son interface](docs/nox/RUN_LOCAL.md)
- [Validation du lot courant](docs/nox/VALIDATION.md)
- [Preuve FID et limites de licence/traitement](docs/nox/NMR_FID_SPIKE.md)

La documentation historique ci-dessous décrit d'autres étapes de NOX; ses
affirmations de maturité ne constituent pas une validation du lot courant.

---

# NOX API

Developer tooling: [local code knowledge graph with Graphify](docs/dev/GRAPHIFY.md).

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
- 📖 **[Documentation Index](./docs/README.md)** - Complete documentation overview
- ⭐ **[NEXT STEPS GUIDE](./NEXT_STEPS_GUIDE.md)** - **NEW!** Prioritized roadmap and action items
- 🎯 **[Current Project Status](./docs/PROJECT_STATUS_2025-08-19.md)** - Latest development status
- 📋 **[Latest Session Summary](./docs/SESSION_SUMMARY_2025-08-19.md)** - Recent achievements
- 🚀 **[Deployment Guides](./docs/deployment-guides/)** - Production setup instructions

**Recent Major Achievements (August 19, 2025):**
- ✅ **File-Operations System v0.2** - Revolutionary 24x performance improvement
- ✅ **XTBA-001 XTB Integration** - Complete quantum chemistry workflow automation
- ✅ **Offline Plan Injection** - Deterministic execution without external API dependencies
- ✅ **Comprehensive Documentation** - 91+ organized documentation files

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

For detailed status, see [PROJECT_STATUS_2025-08-19.md](./docs/PROJECT_STATUS_2025-08-19.md).

## 🤝 Contributing

1. Review the [Documentation Index](./docs/README.md) for project context
2. Check [Current Project Status](./docs/PROJECT_STATUS_2025-08-19.md) for active development areas
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

## ChemLab Assistant local pilot

An isolated, simulation-only laboratory prototype is available in
[`chemlab/`](chemlab/README.md): device registry, durable observations, draft notes,
inventory arithmetic, and a local `thesis_ai` JSONL literature-export bridge.
Run `python -m chemlab.demo` after installing the documented dependencies.
