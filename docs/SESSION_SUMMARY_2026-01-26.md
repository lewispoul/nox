# Session Summary — 2026-01-26

- Refactored FastAPI POST endpoints to typed Pydantic bodies (jobs, predict_cj/vod, agent_run/ask); OpenAPI now shows requestBody schemas.
- Added CJ/VoD/Agent request schemas and updated queue logic to prevent artifact fetches from returning 200 while jobs are still pending.
- Fixed JOBS-002 regression: `test_artifacts_not_ready` and full `tests/jobs` suite now pass.
- Pushed changes to feature branch `feature/api-schemas-routes` (PR #55).

## Tests
- `python -m pytest tests/jobs/test_jobs_basic.py::test_artifacts_not_ready -q`
- `python -m pytest tests/jobs -q`

## Next Steps
- Finish JOBS-002 (state polling/end-to-end flow), then move to XTBA-001.
- Audit/remove legacy `nox-api/` and update deploy/docs references to use `api/` only.
- Keep docs/backlog in sync with ongoing API unification work.
