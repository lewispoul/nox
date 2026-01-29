# Progress Report — API Schemas & Jobs Queue

## Scope
- Typed request models for all POST endpoints (jobs, predict_cj, predict_vod, agent_run, agent_ask).
- Queue race fix for JOBS-002: artifacts remain 404 until job completion.

## Changes
- Added schemas: `CJRequest`, `VoDRequest`, `AgentRunRequest`, `AgentAskRequest`, `Psi4JobRequest`.
- Updated route signatures to accept typed bodies; removed manual `request.json()` parsing; OpenAPI now shows requestBody forms.
- Queue: added small delay after setting `running` to ensure pending state is observable before completion (fixes `test_artifacts_not_ready`).
- Jobs POST supports union of `SimpleJobRequest | Psi4JobRequest | JobRequest`.

## Tests
- `python -m pytest tests/jobs/test_jobs_basic.py::test_artifacts_not_ready -q`
- `python -m pytest tests/jobs -q`

## Status / Follow-ups
- JOBS-002: remaining work is full state polling/worker integration; artifacts race resolved.
- Plan to consolidate legacy `nox-api/` into `api/` and update Makefile/docs references.
- XTBA-001 remains next after JOBS-002 completion.
