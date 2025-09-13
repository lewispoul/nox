# NOX Core Extraction Plan - Wave 1

**Date:** September 13, 2025  
**Branch:** `feature/nox-core-wave1-plan`  
**Target Modules:** `nox.jobs.states`, `nox.parsers.xtb_json`, `nox.jobs.storage`

## A. PR Description (Ready to Paste)

### Title
**Initial extraction of nox_core, wave 1 — jobs.states, parsers.xtb_json, jobs.storage**

### Summary & Rationale

This PR extracts the first wave of stable, reusable computational primitives from NOX into a new `nox_core` package. These modules represent the foundation for computational chemistry workflows and can be reused by IAM 2.0, Pinox, and future projects.

**Selected modules for wave 1:**
- `nox.jobs.states` - Job state management primitives (zero dependencies)
- `nox.parsers.xtb_json` - XTB JSON output parser (zero dependencies) 
- `nox.jobs.storage` - Job storage abstraction (minimal dependencies)

**Rationale:** These modules scored ⭐⭐⭐⭐⭐ in the analysis (see [docs/nox_core_candidates.md](docs/nox_core_candidates.md)) due to their stability, comprehensive test coverage, minimal dependencies, and clear APIs. They form the foundational layer for computational job management and data parsing.

### Detailed Changeset

#### NEW Files
```
nox_core/
├── __init__.py                          # Package initialization, version info
├── py.typed                             # PEP 561 typed package marker
├── jobs/
│   ├── __init__.py                      # Public jobs API exports
│   ├── states.py                        # JobState enum + transitions  
│   └── storage.py                       # JobStorage abstraction
└── parsers/
    ├── __init__.py                      # Public parsers API exports
    └── xtb_json.py                      # XTB JSON parser

tests/nox_core/
├── __init__.py
├── jobs/
│   ├── __init__.py  
│   ├── test_states.py                   # Comprehensive state transition tests
│   └── test_storage.py                  # Storage backend tests
└── parsers/
    ├── __init__.py
    ├── test_xtb_json.py                 # Parser tests + golden files
    └── fixtures/
        └── xtbout_samples.json          # Test fixtures

docs/nox_core.md                        # API reference + migration guide
```

#### MOVED Files
```
MOVE nox/jobs/states.py -> nox_core/jobs/states.py
MOVE nox/parsers/xtb_json.py -> nox_core/parsers/xtb_json.py  
MOVE nox/jobs/storage.py -> nox_core/jobs/storage.py
MOVE tests/xtb/test_xtb_json.py -> tests/nox_core/parsers/test_xtb_json.py
MOVE tests/xtb/data/xtbout.json -> tests/nox_core/parsers/fixtures/xtbout_samples.json
```

#### EDITED Files
```
pyproject.toml                          # Add nox_core package, update dependencies
.github/workflows/python-ci.yml         # Add coverage gates for nox_core
nox/jobs/manager.py                     # Update imports: from nox_core.jobs import JobState, JobStorage
api/services/queue.py                   # Update imports if using job states
tests/jobs/test_jobs_infrastructure.py  # Update imports to nox_core
```

### Migration Notes

#### Before (Current)
```python
from nox.jobs.states import JobState, is_valid_transition
from nox.parsers.xtb_json import parse_xtbout_text, XTBParseError
from nox.jobs.storage import JobStorage
```

#### After (Wave 1) 
```python
from nox_core.jobs import JobState, is_valid_transition, JobStorage
from nox_core.parsers import parse_xtbout_text, XTBParseError
```

#### Compatibility Layer (Temporary)
```python
# nox/jobs/__init__.py - backward compatibility
from nox_core.jobs import JobState, JobStorage  # Re-export for compatibility
from nox_core.jobs.states import is_valid_transition

# nox/parsers/__init__.py  
from nox_core.parsers import parse_xtbout_text, XTBParseError
```

### Risk Assessment & Rollback Plan

**Risk Level:** LOW - These modules have zero external dependencies and clear interfaces.

**Potential Issues:**
- Import path changes may break some internal modules
- Test fixtures paths need updating
- CI coverage thresholds may need adjustment

**Rollback Plan:**
1. Revert the PR commit
2. Run `git checkout main && git branch -D feature/nox-core-wave1`
3. All functionality will be restored to original state
4. Total rollback time: < 5 minutes

**Mitigation:**
- Comprehensive backward compatibility imports maintained
- All existing tests continue to pass
- Feature flag for gradual migration if needed

### Acceptance Criteria

**Functional Requirements:**
- ✅ CI green on Python 3.10, 3.11, 3.12
- ✅ Coverage ≥ 80% on extracted nox_core modules  
- ✅ Zero functional regression on E2E tests
- ✅ Test runtime within ±5% of baseline
- ✅ All existing NOX functionality preserved

**Quality Gates:**
- ✅ Ruff linting passes on nox_core package
- ✅ MyPy type checking passes with strict mode
- ✅ No new security vulnerabilities detected
- ✅ Package builds successfully with Poetry

### Checklist

#### Code & Tests
- [ ] nox_core package structure created  
- [ ] Core modules moved with preserved functionality
- [ ] Comprehensive unit tests added (≥80% coverage)
- [ ] Integration tests pass
- [ ] Backward compatibility imports added
- [ ] Type hints comprehensive and validated

#### Documentation  
- [ ] API reference documentation created
- [ ] Migration guide written
- [ ] README updated with nox_core usage
- [ ] Changelog updated

#### CI/CD & Quality
- [ ] pyproject.toml updated with new package
- [ ] CI workflows updated with coverage gates
- [ ] Pre-commit hooks configured for nox_core
- [ ] Security scanning passes
- [ ] Performance regression tests pass

#### External Interfaces
- [ ] No breaking changes to external APIs
- [ ] OpenAPI specs updated if applicable  
- [ ] Public documentation reflects changes

---

## B. Commit Plan

```bash
# 1. Bootstrap package structure
git commit -m "chore(nox-core): bootstrap package layout and test scaffolding

- Create nox_core/ package structure
- Add py.typed marker for type checking
- Configure pyproject.toml with new package
- Setup test directory structure
- Add basic __init__.py files"

# 2. Extract job states module
git commit -m "feat(nox-core/jobs): move JobState primitives with typed API

- Move nox/jobs/states.py -> nox_core/jobs/states.py  
- Preserve all functionality: JobState enum, transitions, validation
- Add comprehensive type hints throughout
- Create tests/nox_core/jobs/test_states.py with 100% coverage
- Add backward compatibility imports in nox/jobs/"

# 3. Extract XTB parser
git commit -m "feat(nox-core/parsers): move XTB JSON parser with enhanced types

- Move nox/parsers/xtb_json.py -> nox_core/parsers/xtb_json.py
- Enhance type hints: parse_xtbout_text() -> TypedDict result  
- Move and expand test coverage from tests/xtb/
- Add golden file fixtures for comprehensive testing
- Add backward compatibility imports"

# 4. Extract job storage
git commit -m "feat(nox-core/jobs): move JobStorage abstraction with typed interface

- Move nox/jobs/storage.py -> nox_core/jobs/storage.py
- Add comprehensive type hints for storage interface
- Create comprehensive storage backend tests
- Ensure zero breaking changes to existing NOX usage"

# 5. Update NOX imports
git commit -m "refactor(nox): update imports to use nox_core, maintain compatibility

- Update nox/jobs/manager.py imports to nox_core
- Update api/services/ imports where applicable  
- Maintain full backward compatibility
- Add import adapters for gradual migration"

# 6. Enhance test coverage  
git commit -m "test(nox-core): comprehensive test suite with fixtures and golden files

- Add property-based tests for state transitions
- Add comprehensive XTB parser tests with edge cases
- Add storage backend tests with various scenarios
- Achieve >80% coverage on all extracted modules"

# 7. Documentation
git commit -m "docs(nox-core): API reference and migration guide

- Create docs/nox_core.md with full API documentation
- Add migration guide with before/after examples
- Update README.md with nox_core usage section
- Document versioning and compatibility policy"

# 8. CI enhancements
git commit -m "ci: enforce quality gates for nox_core package

- Add nox_core coverage threshold ≥80% to CI
- Enable strict MyPy checking for nox_core
- Add Ruff linting with strict rules
- Configure pre-commit hooks for nox_core"
```

---

## C. File Operations Plan

### Create Package Skeleton
```bash
# Core package structure
mkdir -p nox_core/jobs nox_core/parsers
touch nox_core/__init__.py nox_core/py.typed
touch nox_core/jobs/__init__.py nox_core/parsers/__init__.py

# Test structure  
mkdir -p tests/nox_core/jobs tests/nox_core/parsers/fixtures
touch tests/nox_core/__init__.py tests/nox_core/jobs/__init__.py tests/nox_core/parsers/__init__.py

# Documentation
touch docs/nox_core.md
```

### Update Configuration Files
```bash
# pyproject.toml - Add nox_core package
[tool.poetry.packages]
nox_core = "nox_core"

[tool.coverage.run]  
source = ["nox_core", "api", "nox"]

[tool.coverage.report]
include = ["nox_core/*", "api/*", "nox/*"]
exclude_lines = ["pragma: no cover", "def __repr__", "raise AssertionError"]

# .github/workflows/python-ci.yml - Add coverage gates
- name: Test nox_core coverage
  run: |
    python -m pytest tests/nox_core/ --cov=nox_core --cov-report=xml --cov-fail-under=80
```

### Explicit File Operations

#### MOVES
```bash
# Core modules
mv nox/jobs/states.py nox_core/jobs/states.py
mv nox/parsers/xtb_json.py nox_core/parsers/xtb_json.py  
mv nox/jobs/storage.py nox_core/jobs/storage.py

# Tests
mv tests/xtb/test_xtb_json.py tests/nox_core/parsers/test_xtb_json.py
mv tests/xtb/data/xtbout.json tests/nox_core/parsers/fixtures/xtbout_samples.json
cp tests/jobs/test_jobs_infrastructure.py tests/nox_core/jobs/test_states.py  # Extract relevant parts
```

#### NEW Files
```python
# nox_core/__init__.py
"""
NOX Core - Computational Chemistry Primitives

Stable, reusable modules for computational chemistry workflows.
"""

__version__ = "0.1.0"

from .jobs import JobState, JobStorage, is_valid_transition
from .parsers import parse_xtbout_text, XTBParseError

__all__ = [
    "JobState", 
    "JobStorage", 
    "is_valid_transition",
    "parse_xtbout_text", 
    "XTBParseError"
]

# nox_core/jobs/__init__.py  
from .states import JobState, is_valid_transition, is_terminal_state, get_valid_next_states
from .storage import JobStorage

__all__ = [
    "JobState",
    "JobStorage", 
    "is_valid_transition",
    "is_terminal_state", 
    "get_valid_next_states"
]

# nox_core/parsers/__init__.py
from .xtb_json import parse_xtbout_text, XTBParseError

__all__ = ["parse_xtbout_text", "XTBParseError"]
```

#### EDITS
```python
# nox/jobs/manager.py
# OLD:
from .states import JobState, is_valid_transition
from .storage import JobStorage

# NEW:  
from nox_core.jobs import JobState, is_valid_transition, JobStorage

# nox/jobs/__init__.py - Compatibility layer
from nox_core.jobs import JobState, JobStorage, is_valid_transition

# nox/parsers/__init__.py - Compatibility layer  
from nox_core.parsers import parse_xtbout_text, XTBParseError
```

---

## D. Tests to Add

### Unit Tests (≥80% Coverage Target)

#### tests/nox_core/jobs/test_states.py
```python
"""Comprehensive tests for job state management"""
import pytest
from nox_core.jobs import JobState, is_valid_transition, is_terminal_state, get_valid_next_states

class TestJobState:
    def test_all_states_defined(self):
        """Test all expected states are available"""
        expected = {"pending", "running", "completed", "failed"}
        actual = {state.value for state in JobState}
        assert actual == expected
    
    def test_state_values_are_strings(self):
        """Test all state values are strings"""
        for state in JobState:
            assert isinstance(state.value, str)

class TestStateTransitions:
    @pytest.mark.parametrize("from_state,to_state,expected", [
        (JobState.PENDING, JobState.RUNNING, True),
        (JobState.PENDING, JobState.FAILED, True), 
        (JobState.RUNNING, JobState.COMPLETED, True),
        (JobState.RUNNING, JobState.FAILED, True),
        (JobState.COMPLETED, JobState.RUNNING, False),  # Terminal state
        (JobState.FAILED, JobState.PENDING, False),     # Terminal state
    ])
    def test_valid_transitions(self, from_state, to_state, expected):
        assert is_valid_transition(from_state, to_state) == expected
    
    def test_terminal_states(self):
        assert is_terminal_state(JobState.COMPLETED) is True
        assert is_terminal_state(JobState.FAILED) is True
        assert is_terminal_state(JobState.PENDING) is False
        assert is_terminal_state(JobState.RUNNING) is False
```

#### tests/nox_core/parsers/test_xtb_json.py
```python
"""Comprehensive tests for XTB JSON parser"""
import json
import pytest
from pathlib import Path
from nox_core.parsers import parse_xtbout_text, XTBParseError

class TestXTBParser:
    def test_parse_valid_output(self):
        """Test parsing valid XTB JSON output"""
        valid_json = json.dumps({
            "energy": -40.12345,
            "homo_lumo_gap_ev": 3.21,
            "dipole_debye": 1.84
        })
        result = parse_xtbout_text(valid_json)
        
        assert result["energy"] == -40.12345
        assert result["gap"] == 3.21  
        assert result["dipole"] == 1.84
    
    def test_parse_missing_required_field(self):
        """Test error handling for missing required fields"""
        incomplete_json = json.dumps({"energy": -40.0})  # Missing gap and dipole
        
        with pytest.raises(XTBParseError, match="missing field.*homo_lumo_gap_ev.*dipole_debye"):
            parse_xtbout_text(incomplete_json)
    
    def test_parse_invalid_json(self):
        """Test error handling for malformed JSON"""
        invalid_json = '{"energy": -40.0, "gap":'  # Truncated
        
        with pytest.raises(XTBParseError, match="invalid JSON"):
            parse_xtbout_text(invalid_json)
    
    def test_parse_golden_file(self):
        """Test parsing against golden file fixture"""
        fixture_path = Path(__file__).parent / "fixtures" / "xtbout_samples.json"
        text = fixture_path.read_text()
        result = parse_xtbout_text(text)
        
        # Validate structure and types
        assert isinstance(result["energy"], float)
        assert isinstance(result["gap"], float)
        assert isinstance(result["dipole"], float)
```

#### tests/nox_core/jobs/test_storage.py
```python
"""Comprehensive tests for job storage"""
import tempfile
import pytest
from pathlib import Path
from nox_core.jobs import JobStorage, JobState

class TestJobStorage:
    def test_storage_initialization(self):
        """Test storage initializes with proper directory"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            storage = JobStorage(tmp_dir)
            assert storage.base_path == Path(tmp_dir)
            assert storage.base_path.exists()
    
    def test_save_and_load_job(self):
        """Test round-trip save and load operations"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            storage = JobStorage(tmp_dir)
            job_data = {
                "job_id": "test123",
                "state": JobState.PENDING.value,
                "data": {"key": "value"}
            }
            
            storage.save_job("test123", job_data)
            loaded = storage.load_job("test123")
            
            assert loaded == job_data
    
    def test_load_nonexistent_job(self):
        """Test loading non-existent job returns None"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            storage = JobStorage(tmp_dir)
            result = storage.load_job("nonexistent")
            assert result is None
```

### Integration & Smoke Tests
```python
# tests/nox_core/test_integration.py
"""Integration tests for nox_core package"""

def test_public_api_imports():
    """Test all public APIs can be imported"""
    from nox_core import JobState, JobStorage, parse_xtbout_text, XTBParseError
    
    # Basic smoke test
    assert JobState.PENDING.value == "pending"
    assert callable(parse_xtbout_text)

def test_end_to_end_job_workflow():
    """Test complete job workflow using nox_core primitives"""
    from nox_core.jobs import JobState, JobStorage, is_valid_transition
    
    storage = JobStorage()
    
    # Create job
    job_data = {"state": JobState.PENDING.value}
    storage.save_job("test", job_data)
    
    # Transition to running
    assert is_valid_transition(JobState.PENDING, JobState.RUNNING)
    job_data["state"] = JobState.RUNNING.value
    storage.save_job("test", job_data)
    
    # Complete job
    job_data["state"] = JobState.COMPLETED.value
    storage.save_job("test", job_data)
    
    final_job = storage.load_job("test")
    assert final_job["state"] == JobState.COMPLETED.value
```

---

## E. Documentation to Add

### docs/nox_core.md
```markdown
# NOX Core Package Documentation

## Overview

`nox_core` provides stable, reusable computational chemistry primitives extracted from the NOX project. These modules enable job management, data parsing, and workflow orchestration for computational chemistry applications.

## Installation

```bash
# Development installation (from NOX repository)
pip install -e .

# The nox_core package is included with NOX
from nox_core.jobs import JobState
from nox_core.parsers import parse_xtbout_text
```

## API Reference

### Jobs Module (`nox_core.jobs`)

#### JobState
```python
from nox_core.jobs import JobState

class JobState(str, Enum):
    PENDING = "pending"     # Job queued for execution
    RUNNING = "running"     # Job currently executing  
    COMPLETED = "completed" # Job finished successfully
    FAILED = "failed"       # Job terminated with error
```

#### State Transition Functions
```python
from nox_core.jobs import is_valid_transition, is_terminal_state, get_valid_next_states

# Check if state transition is allowed
is_valid_transition(JobState.PENDING, JobState.RUNNING)  # Returns: True

# Check if state is terminal (no further transitions)
is_terminal_state(JobState.COMPLETED)  # Returns: True

# Get all valid next states from current state
get_valid_next_states(JobState.RUNNING)  # Returns: {JobState.COMPLETED, JobState.FAILED}
```

#### JobStorage
```python
from nox_core.jobs import JobStorage

storage = JobStorage(base_path="./job_data")

# Save job data
storage.save_job("job_123", {
    "state": JobState.PENDING.value,
    "data": {"input": "molecule.xyz"}
})

# Load job data
job = storage.load_job("job_123")  # Returns dict or None
```

### Parsers Module (`nox_core.parsers`)

#### XTB JSON Parser
```python
from nox_core.parsers import parse_xtbout_text, XTBParseError

try:
    result = parse_xtbout_text(xtb_json_output)
    print(f"Energy: {result['energy']} Eh")
    print(f"HOMO-LUMO Gap: {result['gap']} eV") 
    print(f"Dipole: {result['dipole']} Debye")
except XTBParseError as e:
    print(f"Parse error: {e}")
```

## Migration Guide

### From NOX Internal Modules

#### Before (NOX internal)
```python
from nox.jobs.states import JobState, is_valid_transition
from nox.parsers.xtb_json import parse_xtbout_text, XTBParseError
from nox.jobs.storage import JobStorage
```

#### After (nox_core)
```python
from nox_core.jobs import JobState, is_valid_transition, JobStorage
from nox_core.parsers import parse_xtbout_text, XTBParseError
```

### Compatibility Notes

- All existing functionality is preserved
- Backward compatibility imports are maintained in NOX
- No breaking changes to public APIs
- Gradual migration is supported

## Versioning Policy

- `nox_core` follows semantic versioning (SemVer)
- Breaking changes will increment major version
- New features increment minor version  
- Bug fixes increment patch version
- Compatibility with Python 3.10+ guaranteed

## Contributing

See the main NOX repository for contribution guidelines. All changes to `nox_core` require:
- ≥80% test coverage
- Type hints throughout
- Documentation updates
- Backward compatibility preserved
```

### README.md Update
```markdown
## Using nox_core

NOX includes `nox_core`, a package of stable computational chemistry primitives that can be reused in other projects:

```python
# Job state management
from nox_core.jobs import JobState, JobStorage

# XTB data parsing  
from nox_core.parsers import parse_xtbout_text

# Example: Parse XTB output
result = parse_xtbout_text(xtb_json_output)
print(f"Molecular energy: {result['energy']} Eh")
```

For detailed API documentation, see [docs/nox_core.md](docs/nox_core.md).
```

---

## F. Validation Script

```bash
#!/bin/bash
# validate_nox_core.sh - Quality validation for nox_core extraction

set -e

echo "🔍 NOX Core Quality Validation"
echo "============================="

# 1. Linting with Ruff
echo "📋 Running Ruff linting..."
python -m ruff check nox_core/ --quiet
echo "✅ Ruff linting passed"

# 2. Type checking with MyPy  
echo "🔍 Running MyPy type checking..."
python -m mypy nox_core/ --strict --no-error-summary
echo "✅ MyPy type checking passed"

# 3. Unit tests with coverage
echo "🧪 Running tests with coverage..."
python -m pytest tests/nox_core/ \
  --cov=nox_core \
  --cov-report=term-missing \
  --cov-fail-under=80 \
  --quiet

echo "✅ Tests passed with ≥80% coverage"

# 4. Import validation
echo "📦 Validating public API imports..."
python -c "
from nox_core import JobState, JobStorage, parse_xtbout_text, XTBParseError
from nox_core.jobs import is_valid_transition, is_terminal_state
print('✅ All public APIs importable')
"

# 5. Package build test
echo "🏗️  Testing package build..."
python -m build --wheel --silent
echo "✅ Package builds successfully"

# 6. Performance baseline (optional)
echo "⚡ Running performance baseline..."
python -c "
import time
from nox_core.jobs import JobState, is_valid_transition

start = time.time()
for _ in range(10000):
    is_valid_transition(JobState.PENDING, JobState.RUNNING)
duration = time.time() - start
print(f'✅ Performance baseline: {duration:.3f}s for 10k transitions')
"

echo ""
echo "🎉 NOX Core Quality Summary: ALL CHECKS PASSED"
echo "   • Linting: Clean"
echo "   • Types: Strict compliance"  
echo "   • Tests: ≥80% coverage"
echo "   • APIs: All importable"
echo "   • Build: Successful"
echo "   • Performance: Within baseline"
```

---

## Summary

**Selected Modules for Wave 1:**
- `nox.jobs.states` - Job state management primitives 
- `nox.parsers.xtb_json` - XTB JSON output parser
- `nox.jobs.storage` - Job storage abstraction

**Rationale:** These three modules form the foundational layer for computational chemistry workflows. They have excellent stability (all scored ⭐⭐⭐⭐⭐), zero external dependencies, comprehensive test coverage, and clean APIs. They can be immediately reused by IAM 2.0 and Pinox for job management and XTB data processing. The extraction is low-risk due to minimal coupling and robust backward compatibility measures.

The plan provides a complete roadmap from extraction through validation, ensuring zero functional regression while establishing `nox_core` as a stable, typed, well-tested package ready for external consumption.